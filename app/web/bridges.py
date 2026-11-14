"""後端要接哪些轉接器（設定 YIQUNREN_BRIDGES），以及各家 turn_begin 的欄位怎麼組（SPEC NFR-7）。

橋接是另外啟動的本機程序；這裡只決定後端用哪個執行者連過去。有實作欄位組法的轉接器才能接。
例外是 IN_PROCESS 裡的轉接器（Claude（API））：後端直接呼叫該家 API，不需要橋接。
"""
from __future__ import annotations

from pathlib import Path

from app.services import adapters
from app.storage import workspaces
from app.web import claude_api
from app.web.config import ConfigError
from app.web.runner import TurnInput
from app.web.worker_runner import WorkerTurnRunner


def claude_code_fields(state_dir: Path):
    """Claude Code：工作目錄在第一次送出回合時建立；模型空白表示用該家預設；續接用上一個完成回合的 session。"""
    root = workspaces.root(state_dir)

    def fields(turn: TurnInput) -> dict:
        workspace = workspaces.ensure(turn.workspace, root)
        values = {'message': turn.message, 'session_id': turn.session, 'workspace': str(workspace),
                  'model': turn.model or None, 'effort': turn.effort, 'max_budget_usd': turn.budget}
        wanted = adapters.get('claude_code').fields_for(turn.auth_mode)
        return {key: value for key, value in values.items() if key in wanted}

    return fields


BUILDERS = {'claude_code': claude_code_fields}
# 後端直接呼叫 API 的轉接器：代號 → 建立執行者的函式（缺少必要設定時丟 ConfigError）。
IN_PROCESS = {claude_api.CODE: claude_api.build}


def runners(codes, state_dir: Path) -> dict:
    """{轉接器代號: 執行者}；沒有實作的代號一律拒絕。"""
    found = {}
    for code in codes:
        if code in IN_PROCESS:
            found[code] = IN_PROCESS[code]()
            continue
        builder = BUILDERS.get(code)
        if builder is None:
            raise ConfigError('轉接器 %s 還沒有橋接實作，不能放進 YIQUNREN_BRIDGES' % code)
        found[code] = WorkerTurnRunner(code, fields=builder(Path(state_dir)))
    return found
