"""轉接器登記處（SPEC NFR-7 › MVP）：本體唯一列出「有哪些轉接器」的地方。

回合協定、回合狀態顯示與連線位置、調度現況快照、調度提示詞、群聊發言者與主持人候選、
診斷檔的錯誤分類，都從這裡取得轉接器清單與資料，不在各自的程式裡列出固定幾家。
新增或移除一個轉接器只改 DEFAULT_ADAPTERS（或之後的擴充）。

只含資料與純函式，App 與主機端都 import；不 import 本專案其他模組。
API key 與訂閱 CLI 是同一個轉接器的兩種認證模式（FR-1），不另外登記成一家；
回合請求帶 auth_mode，欄位＝共同欄位（turn_fields）＋該模式的專屬欄位（mode_fields）。
登記資料一律是不可變型別（frozen dataclass、tuple、frozenset、MappingProxyType），避免執行中被改動。
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

CODE = re.compile(r"[a-z][a-z0-9_]{0,31}")
FIELD = re.compile(r"[a-z][a-z0-9_]{0,39}")
SOCKET_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,59}\.sock")
AUTH_MODES = ("api_key", "subscription_cli")
# 主持人格位的輸出方式：schema＝CLI 原生的輸出格式約束；prompt＝只靠提示詞約束、App 端再驗。None＝不能當主持人。
HOST_OUTPUTS = ("schema", "prompt")
# 診斷檔的錯誤分類規則名稱；實作在 scripts/host_diagnostics.py 的 ERROR_CLASS_RULES，兩邊須一致。
ERROR_CLASS_RULES = ("claude_events",)


def _texts(value, *, allow_empty: bool = False) -> bool:
    return (isinstance(value, tuple) and (allow_empty or bool(value))
            and all(isinstance(item, str) and item.strip() for item in value))


@dataclass(frozen=True)
class Adapter:
    """一個轉接器的登記資料。

    strengths／weaknesses／choose_when 是給調度與主持人看的能力描述：描述本專案的工作方式，
    不代表各供應商的普遍強弱或測得的品質。model_tiers 依序對應 light／standard／deep；
    沒登記時提示詞不出現該轉接器的模型名稱。socket_name 是預設 socket 檔名（空字串＝<code>.sock）。
    mode_fields 是某個認證模式才有的回合欄位（{模式: frozenset}），登記後轉成唯讀的 MappingProxyType。
    """

    code: str
    name: str
    turn_fields: frozenset
    auth_modes: tuple
    strengths: tuple
    weaknesses: tuple
    choose_when: str
    model_tiers: tuple | None = None
    tier_note: str = ""
    host_output: str | None = None
    error_class_rule: str | None = None
    socket_name: str = ""
    # MappingProxyType 不能 hash，所以不列入 hash（比較時仍列入）。
    mode_fields: object = field(default_factory=lambda: MappingProxyType({}), hash=False)

    def __post_init__(self):
        if not isinstance(self.code, str) or not CODE.fullmatch(self.code):
            raise ValueError("轉接器代號只能用小寫英文開頭，後接小寫英文、數字與底線，最長 32 字")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 40 or "\n" in self.name:
            raise ValueError("轉接器顯示名稱無效")
        if (not isinstance(self.turn_fields, frozenset) or not self.turn_fields
                or any(not isinstance(key, str) or not FIELD.fullmatch(key) for key in self.turn_fields)):
            raise ValueError("轉接器回合欄位無效")
        if (not isinstance(self.auth_modes, tuple) or not self.auth_modes
                or len(set(self.auth_modes)) != len(self.auth_modes)
                or any(mode not in AUTH_MODES for mode in self.auth_modes)):
            raise ValueError("轉接器認證模式無效")
        if (not _texts(self.strengths) or not _texts(self.weaknesses)
                or not isinstance(self.choose_when, str) or not self.choose_when.strip()):
            raise ValueError("轉接器能力描述無效")
        if self.model_tiers is not None and not (_texts(self.model_tiers) and len(self.model_tiers) == 3):
            raise ValueError("模型等級必須依序列出 light、standard、deep 三項")
        if not isinstance(self.tier_note, str) or (self.tier_note and self.model_tiers is None):
            raise ValueError("模型等級備註只能搭配已登記的模型等級")
        if self.host_output is not None and self.host_output not in HOST_OUTPUTS:
            raise ValueError("主持人輸出方式無效")
        if self.error_class_rule is not None and self.error_class_rule not in ERROR_CLASS_RULES:
            raise ValueError("診斷錯誤分類規則無效")
        if not isinstance(self.socket_name, str) or (self.socket_name and not SOCKET_NAME.fullmatch(self.socket_name)):
            raise ValueError("socket 檔名無效")
        if not self.socket_name:
            object.__setattr__(self, "socket_name", f"{self.code}.sock")
        if not isinstance(self.mode_fields, (dict, MappingProxyType)):
            raise ValueError("認證模式專屬欄位無效")
        for mode, extra in self.mode_fields.items():
            if (mode not in self.auth_modes or not isinstance(extra, frozenset) or not extra
                    or extra & self.turn_fields
                    or any(not isinstance(key, str) or not FIELD.fullmatch(key) for key in extra)):
                raise ValueError("認證模式專屬欄位無效")
        object.__setattr__(self, "mode_fields", MappingProxyType(dict(self.mode_fields)))

    def fields_for(self, auth_mode: object) -> frozenset:
        """該認證模式的回合欄位；未登記的模式一律拒絕。"""
        if not isinstance(auth_mode, str) or auth_mode not in self.auth_modes:
            raise ValueError("轉接器不支援這個認證模式")
        return self.turn_fields | self.mode_fields.get(auth_mode, frozenset())


# 預設登記：順序依 SPEC NFR-7（Codex、Grok、Claude Code），也是群聊發言與主持人預設候選的順序。
DEFAULT_ADAPTERS = (
    Adapter(
        code="codex", name="Codex",
        turn_fields=frozenset({"message", "thread_id", "workspace", "model", "effort"}),
        auth_modes=("api_key", "subscription_cli"),
        strengths=("程式碼與檔案修改", "依現有程式追蹤資料流", "執行獲准的本機驗證"),
        weaknesses=("缺需求、程式或環境證據時不能證明根因", "文字回報不能代替實際驗證", "不共享其他 AI 的工作區"),
        choose_when="任務以既有程式與可執行驗證為核心，且相關內容能在此工作區取得。",
        model_tiers=("Luna Max", "Sol Medium", "Astra High"), tier_note="Luna 只能搭配 Max",
        host_output="schema",
    ),
    Adapter(
        code="grok", name="Grok",
        turn_fields=frozenset({"message", "session_id", "workspace", "model", "effort"}),
        auth_modes=("api_key", "subscription_cli"),
        strengths=("獨立工作區中的檔案與文件處理", "分析已提供的資料", "依明確問題提出另一種解釋"),
        weaknesses=("未確認資料來源不能宣稱掌握即時資訊", "另一個 AI 的意見不等於獨立來源", "不共享其他 AI 的工作區"),
        choose_when="需要此工作區的材料或另一條可核對的分析路徑，且已設定可用模型。",
    ),
    Adapter(
        code="claude_code", name="Claude Code",
        turn_fields=frozenset({"message", "session_id", "workspace", "model", "effort"}),
        # 訂閱 CLI 模式等 Anthropic 確認後再開放（SPEC 第 7 節第 3 項）。
        auth_modes=("api_key",),
        mode_fields={"api_key": frozenset({"max_budget_usd"})},
        strengths=("程式碼與檔案修改", "文字撰寫及結構整理", "綜合已提供的材料"),
        weaknesses=("缺來源時不能補造事實或引用", "整理得完整不代表主張正確", "不共享其他 AI 的工作區"),
        choose_when="任務需要程式實作或文件整理，且材料與專案上下文已在此工作區。",
        model_tiers=("Sonnet Low", "Sonnet Medium", "Opus High"), tier_note="最低模型為 Sonnet，不使用 Haiku",
        host_output="prompt", error_class_rule="claude_events",
    ),
)


def _checked(entries) -> tuple:
    entries = tuple(entries)
    if not entries or any(not isinstance(entry, Adapter) for entry in entries):
        raise ValueError("登記處至少要有一個轉接器")
    if len({entry.code for entry in entries}) != len(entries):
        raise ValueError("轉接器代號重複")
    return entries


_active: tuple = _checked(DEFAULT_ADAPTERS)


def adapters() -> tuple:
    """目前登記的轉接器，依登記順序。"""
    return _active


def codes() -> tuple:
    return tuple(entry.code for entry in _active)


def is_registered(code: object) -> bool:
    return isinstance(code, str) and any(entry.code == code for entry in _active)


def get(code: object) -> Adapter:
    """取登記資料；未登記的代號一律拒絕，不猜測、不改用別家。錯誤訊息不帶入原值。"""
    for entry in _active:
        if isinstance(code, str) and entry.code == code:
            return entry
    raise ValueError("未登記的轉接器")


@contextmanager
def override(entries):
    """暫時換掉整份登記資料，離開區塊時還原。僅供測試使用。

    換上的資料須全是 Adapter 且代號不重複。它改的是模組層級的全域狀態，不是多執行緒安全，
    不要在正式執行中呼叫。擴充怎麼安裝、載入，SPEC 要等做第一個功能型擴充前才補，這裡不預設。"""
    global _active
    previous, _active = _active, _checked(entries)
    try:
        yield _active
    finally:
        _active = previous


def socket_env(code: str) -> str:
    return f"PANELROOM_{get(code).code.upper()}_SOCKET"


def socket_path(code: str) -> str:
    """連到轉接器橋接的本機 socket：環境變數 PANELROOM_<CODE>_SOCKET（絕對路徑）優先；
    否則 $XDG_RUNTIME_DIR/panelroom/<socket_name>，沒有 XDG_RUNTIME_DIR 時用 ~/.local/state/panelroom/run/。"""
    entry = get(code)
    name = socket_env(entry.code)
    value = os.environ.get(name)
    if value:
        if not Path(value).is_absolute():
            raise ValueError(f"{name} 必須是絕對路徑")
        return value
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and Path(runtime).is_absolute():
        return str(Path(runtime) / "panelroom" / entry.socket_name)
    return str(Path.home() / ".local" / "state" / "panelroom" / "run" / entry.socket_name)
