"""三個 CLI 橋接共用的 Unix socket 單行請求／回覆。

橋接協定是「一行 JSON 請求 → 一行 JSON 回覆」。asyncio StreamReader 預設只允許 64 KiB 的一行，
而主機端允許回覆正文到 100,000 bytes，所以連線時必須把 limit 放大到 MAX_RESPONSE，
否則超過 64 KiB 的回覆會以 ValueError 失敗、回覆與續接 ID 一起遺失。

進度行：用戶端在請求帶 `progress: true` 時，橋接可在最終回覆前送出多行 `{"progress": {...}}`；
每行交給 on_progress，不計入回覆。沒有要求時仍容忍並忽略這種行。
"""
from __future__ import annotations

import asyncio
import json
import os

MAX_RESPONSE = 120_000
CONNECT_TIMEOUT = 3
MAX_PROGRESS_LINES = 5_000


async def request(socket_path: str, payload: dict, *, timeout: float, label: str, on_progress=None) -> dict:
    """送出 payload 並回傳 ok 為真的回覆；所有失敗都以 RuntimeError 呈現固定訊息。

    timeout 是整個往返的牆鐘上限，進度行不延長它；逾時以 asyncio.TimeoutError 呈現（與舊版相同）。
    """
    invalid = RuntimeError(f"Invalid response from {label} bridge")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(socket_path, limit=MAX_RESPONSE + 1), timeout=CONNECT_TIMEOUT
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise RuntimeError(f"WSL {label} bridge is not running") from exc
    try:
        writer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        await writer.drain()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        progress_lines = 0
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=remaining)
            except ValueError as exc:
                # 超過 limit 的行：資料已不可恢復，當成無效回覆。
                raise invalid from exc
            if not line or len(line) > MAX_RESPONSE:
                raise invalid
            try:
                response = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise invalid from exc
            if isinstance(response, dict) and "ok" not in response and "progress" in response:
                progress_lines += 1
                if progress_lines > MAX_PROGRESS_LINES:
                    raise invalid
                if on_progress is not None and isinstance(response["progress"], dict):
                    try:
                        on_progress(response["progress"])
                    except Exception:
                        pass
                continue
            if not isinstance(response, dict) or not response.get("ok"):
                error = response.get("error") if isinstance(response, dict) else None
                raise RuntimeError(error if isinstance(error, str) and error else f"{label} bridge failed")
            return response
    finally:
        writer.close()
        await writer.wait_closed()
