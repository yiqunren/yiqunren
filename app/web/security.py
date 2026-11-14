"""NFR-3 本機安全：Host 檢查、配對與 Cookie、CSRF、請求大小與頻率限制。

所有 HTTP 請求都先經過 Guard 這個 ASGI 中介層，各路由不必自己檢查。檢查順序：
Host → CSRF（GET、HEAD 以外）→ 配對（開放端點與網頁介面的檔案除外）→ 請求大小 → 頻率（GET、HEAD 以外）。
所有回應（含被擋下的）都加上安全標頭。
配對碼與瀏覽器憑證不寫進 log 或錯誤訊息；資料庫只存雜湊（app/storage/pairing.py）。
"""
from __future__ import annotations

from collections import deque
from contextlib import closing
import ipaddress
import math
import re
import secrets
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders

from app.storage import db, pairing


CSRF_HEADER = 'X-Yiqunren-CSRF'   # 改變狀態的請求必須帶，值是 1；跨來源的網頁加不了自訂標頭（會先被瀏覽器預檢擋下）
CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'   # 不用 0、O、1、I
CODE_LENGTH = 8
# 瀏覽器端的 Cookie 期限取瀏覽器允許的上限（約 400 天）；30 天沒使用的失效由伺服器判斷。
COOKIE_MAX_AGE = 400 * 24 * 3600
# 32,000 字的訊息最壞每字 12 位元組（JSON 的 \uXXXX 代理對），加上其他欄位仍在上限內。
MAX_BODY_BYTES = 512 * 1024
RATE_WINDOW = 60.0
RATE_LIMIT_TOTAL = 60   # 改變狀態的請求合計每分鐘
RATE_LIMIT_TURNS = 20   # 其中送出私聊回合每分鐘
TURN_PATH = '/api/turns'
SAFE_METHODS = frozenset({'GET', 'HEAD'})
# 不必配對就能用的端點：健康檢查、配對、查詢配對狀態與登出。
OPEN = frozenset({('GET', '/api/health'), ('HEAD', '/api/health'), ('POST', '/api/pair'),
                  ('GET', '/api/session'), ('HEAD', '/api/session'), ('DELETE', '/api/session')})
# /api/ 以外的路徑是網頁介面本身的檔案（不含使用者資料），沒配對也能讀，否則配對畫面顯示不出來。
API_PREFIX = '/api/'
# 所有回應都帶。只允許本站的程式、樣式與連線，禁止行內程式碼與被其他網站嵌入。
# Referrer-Policy 不能用 no-referrer：瀏覽器會把同源 POST 的 Origin 送成 null，被上面的 CSRF 檢查擋下。
SECURITY_HEADERS = (
    ('Content-Security-Policy',
     "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
     "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
    ('X-Content-Type-Options', 'nosniff'),
    ('Referrer-Policy', 'same-origin'),
)

_HOST = re.compile(r'(?:\[([0-9a-f:.]+)\]|([0-9a-z.-]+))(?::([0-9]{1,5}))?')

router = APIRouter()


def cookie_name(port: int) -> str:
    # Cookie 不分埠：名稱帶埠號，同一台電腦跑兩個實例時才不會互相蓋掉。
    return 'yiqunren_session_%d' % port


def new_code() -> str:
    return ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(text: str) -> str | None:
    """接受小寫、連字號與空白；格式不對回傳 None。"""
    code = text.replace('-', '').replace(' ', '').upper()
    if len(code) != CODE_LENGTH or any(ch not in CODE_ALPHABET for ch in code):
        return None
    return code


def issue_code(db_path, *, now: float | None = None) -> str:
    """產生一組新的配對碼（舊的作廢），回傳顯示用的格式，例如 ABCD-EFGH。"""
    code = new_code()
    with closing(db.connect(db_path)) as connection:
        pairing.issue_code(connection, pairing.digest(code), time.time() if now is None else now)
    return code[:4] + '-' + code[4:]


def revoke_all(db_path) -> int:
    with closing(db.connect(db_path)) as connection:
        return pairing.revoke_all(connection)


def has_sessions(db_path, *, now: float | None = None) -> bool:
    with closing(db.connect(db_path)) as connection:
        return pairing.has_sessions(connection, time.time() if now is None else now)


def host_allowed(value: str | None, port: int) -> bool:
    """只接受 IP 位址或 localhost 加上設定的埠：DNS rebinding 一定要用網域名稱，這樣就擋下來了。"""
    match = _HOST.fullmatch(value.lower()) if value else None
    if match is None:
        return False
    ipv6, name, raw_port = match.groups()
    try:
        if ipv6 is not None:
            ipaddress.IPv6Address(ipv6)
        elif name != 'localhost':
            ipaddress.IPv4Address(name)
    except ValueError:
        return False
    return (int(raw_port) if raw_port else 80) == port


def same_origin(headers) -> bool:
    """CSRF：要有自訂標頭；Origin、Sec-Fetch-Site 有帶就必須是同源（127.0.0.1 不同埠也算不同源）。"""
    if headers.get(CSRF_HEADER) != '1':
        return False
    origin = headers.get('origin')
    if origin is not None and origin.lower() != 'http://' + headers['host'].lower():
        return False
    site = headers.get('sec-fetch-site')
    return site is None or site == 'same-origin'


class RateLimiter:
    """滑動視窗：記下最近 60 秒內放行的請求時間。只在這個行程的記憶體裡，伺服器重啟就重新計算。"""

    def __init__(self, clock):
        self.clock = clock
        self.total: deque[float] = deque()
        self.turns: deque[float] = deque()

    def admit(self, is_turn: bool) -> float | None:
        """放行就記下並回傳 None；超過上限回傳幾秒後可以再試（被擋下的不計入）。"""
        now = self.clock()
        buckets = [(self.total, RATE_LIMIT_TOTAL)] + ([(self.turns, RATE_LIMIT_TURNS)] if is_turn else [])
        wait = 0.0
        for times, limit in buckets:
            while times and times[0] <= now - RATE_WINDOW:
                times.popleft()
            if len(times) >= limit:
                wait = max(wait, times[0] + RATE_WINDOW - now)
        if wait > 0:
            return wait
        for times, _ in buckets:
            times.append(now)
        return None


class Security:
    def __init__(self, port: int, db_path, clock=time.time):
        """db_path：回傳資料庫路徑的函式（伺服器啟動後才確定）。clock 只供測試控制期限與頻率視窗。"""
        self.port = port
        self.cookie = cookie_name(port)
        self.clock = clock
        self.limiter = RateLimiter(clock)
        self._db_path = db_path

    def connect(self):
        return db.connect(self._db_path())

    def session(self, token: str) -> str | None:
        """Cookie 裡的憑證有效時回傳它的雜湊。"""
        token_hash = pairing.digest(token)
        with closing(self.connect()) as connection:
            return token_hash if pairing.check_session(connection, token_hash, self.clock()) else None


class _Disconnected(Exception):
    pass


async def _read_body(receive, limit: int) -> bytes | None:
    """讀完整個請求本體；超過上限回傳 None。"""
    chunks, size = [], 0
    while True:
        message = await receive()
        if message['type'] == 'http.disconnect':
            raise _Disconnected
        chunk = message.get('body', b'')
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
        if not message.get('more_body', False):
            return b''.join(chunks)


def _replay(body: bytes, receive):
    pending = True

    async def replay():
        nonlocal pending
        if pending:
            pending = False
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return await receive()  # 之後交回原本的通道，才收得到連線中斷
    return replay


def _with_security_headers(send):
    async def wrapped(message):
        if message['type'] == 'http.response.start':
            headers = MutableHeaders(raw=message.setdefault('headers', []))
            for name, value in SECURITY_HEADERS:
                headers[name] = value
        await send(message)
    return wrapped


class Guard:
    """ASGI 中介層：所有 HTTP 請求先經過這裡。"""

    def __init__(self, app, *, security: Security):
        self.app = app
        self.security = security

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        send = _with_security_headers(send)  # 被擋下的回應也帶
        request = Request(scope)
        headers, method, path = request.headers, scope['method'], scope['path']
        unsafe = method not in SAFE_METHODS
        page_file = not unsafe and not path.startswith(API_PREFIX)
        if not host_allowed(headers.get('host'), self.security.port):
            return await self._reject(scope, receive, send, 400, '不接受這個 Host，請用 127.0.0.1 或 localhost 連線')
        if unsafe and not same_origin(headers):
            return await self._reject(scope, receive, send, 403, '請求來源不符')
        token = request.cookies.get(self.security.cookie)
        session = await run_in_threadpool(self.security.session, token) if token else None
        scope.setdefault('state', {})['session'] = session
        if session is None and not page_file and (method, path) not in OPEN:
            return await self._reject(scope, receive, send, 401, '尚未配對')
        length = headers.get('content-length')
        if length is not None and (not length.isascii() or not length.isdigit()):
            return await self._reject(scope, receive, send, 400, '請求長度無效')
        if length is not None and int(length) > MAX_BODY_BYTES:
            return await self._reject(scope, receive, send, 413, '請求太大')
        if unsafe:
            try:
                body = await _read_body(receive, MAX_BODY_BYTES)
            except _Disconnected:
                return
            if body is None:
                return await self._reject(scope, receive, send, 413, '請求太大')
            wait = self.security.limiter.admit(method == 'POST' and path == TURN_PATH)
            if wait is not None:
                return await self._reject(scope, receive, send, 429, '請求太頻繁，請稍後再試',
                                          {'Retry-After': str(max(1, math.ceil(wait)))})
            receive = _replay(body, receive)
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope, receive, send, status: int, detail: str, headers=None):
        await JSONResponse({'detail': detail}, status_code=status, headers=headers)(scope, receive, send)


class PairRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    code: str = Field(max_length=32)


def _security(request: Request) -> Security:
    return request.app.state.security


@router.post('/api/pair')
def pair(body: PairRequest, request: Request):
    security = _security(request)
    code = normalize_code(body.code)
    if code is None:
        raise HTTPException(status_code=422, detail='配對碼格式不對')
    token = secrets.token_urlsafe(32)
    with closing(security.connect()) as connection:
        outcome = pairing.redeem(connection, pairing.digest(code), pairing.digest(token), security.clock())
    if outcome != pairing.PAIRED:
        return JSONResponse({'detail': '配對碼不對或已失效，請在本機執行 python -m app.web pair 取得新的'},
                            status_code=403)
    response = JSONResponse({'paired': True})
    response.set_cookie(security.cookie, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite='strict')
    return response


@router.get('/api/session')
def session(request: Request):
    return {'paired': request.state.session is not None}


@router.delete('/api/session', status_code=204)
def logout(request: Request):
    """登出這個瀏覽器：只撤銷它自己的憑證，其他已配對的瀏覽器不受影響。"""
    security = _security(request)
    if request.state.session is not None:
        with closing(security.connect()) as connection:
            pairing.revoke(connection, request.state.session)
    response = Response(status_code=204)
    response.delete_cookie(security.cookie, httponly=True, samesite='strict')
    return response
