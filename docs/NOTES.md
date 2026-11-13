# 交接筆記（2026-11-12 起草，2026-11-13 第二次更新）

這份筆記記的是還沒寫進其他文件的待辦，讓換 session 後可以接得上。正式的決策與需求以 `docs/SPEC.md` 為準，匯入紀錄在 `PROVENANCE.md`，隔離與 Git 規則在 `CLAUDE.md`。

## 主線狀態

- 決策與需求：`docs/SPEC.md`（第 1 節名稱、授權與收費方式，FR-1、FR-3、FR-9、NFR-7，第 7 節待決事項）。
- 轉接器登記處（NFR-7）已實作並 commit（`b8012aa`）。
- 技術選型已定案（2026-11-13，SPEC 第 7 節第 5 項，`6555448`）：Python 3.12＋FastAPI／Uvicorn、SQLite（標準庫）、React＋TypeScript＋Vite、SSE。比較與原型驗證見 `docs/research/2026-11-13-tech-stack-options.md`，第 7 節 6 項風險都有實測結果與限制。
- 最小後端骨架已完成（2026-11-13，`acd7372`、`27dd2ee`）：
  - 依賴與鎖檔：`pyproject.toml`、`uv.lock`，用 `uv sync` 建立 `.venv`（Python 3.12）。
  - `app/web/`：設定（預設只聽 `127.0.0.1:8420`，可用 `YIQUNREN_HOST`／`YIQUNREN_PORT`／`YIQUNREN_STATE_DIR` 覆寫）、FastAPI app（內建遙測明確關閉、API 文件頁關閉）、健康檢查 `GET /api/health`、`python -m app.web` 啟動。
  - `app/storage/`：狀態資料庫（WAL、`PRAGMA user_version` 版本管理、目錄 0700／檔案 0600）、NFR-1 請求登記（同 ID 同內容回傳原紀錄、不同內容拒絕、多程序只有一個取得執行權）。
- FR-2 私聊的後端已用假轉接器做到可以完整跑通（2026-11-13）：
  - 範圍 B（`5ae11fa`）：`POST /api/turns` 送出回合（帶 NFR-1 請求 ID；同 ID 同內容回傳原結果、不同內容 409；同一段對話同時只有一個進行中回合，否則 409）、`GET /api/turns/{id}`、SSE `GET /api/turns/{id}/events`（一律從資料庫讀事件：不帶 `Last-Event-ID` 從頭重送，帶了只補送之後的）、伺服器啟動時把殘留的「執行中」回合標為「未知」。
  - 保存與刪除（`483804c` SPEC、`19c3a6c` 實作）：訊息全文與回覆存在本機狀態資料庫，保留到擁有者刪除；`GET /api/conversations/{id}` 列整段對話，`DELETE /api/conversations/{id}` 刪除整段（進行中回合時 409）。每個連線都開 `secure_delete`，刪除後清空 WAL；請求登記只留雜湊並標為 `deleted`，刪除後用同一個請求 ID 重送回 410。
  - 中斷與逾時（`ae3e16a`）：`POST /api/turns/{id}/interrupt`；單回合逾時目前固定 15 分鐘（`TIMEOUT_DEFAULT`）。
  - 轉接器介面寫在 `app/web/runner.py`：轉接器是 `async (member, text, emit) -> 回覆文字`。系統要停止回合（中斷、逾時、伺服器關閉）時取消執行它的 asyncio 工作；轉接器確認程序已停止就讓 `CancelledError` 往外傳（回合標為已中斷；逾時則是「失敗（逾時）」），無法確認就丟 `StopUnconfirmed`（回合標為未知）。其他例外一律是失敗，只存固定分類 `internal_error`，不存原始錯誤訊息。
  - `YIQUNREN_FAKE_TURNS=1` 啟用假轉接器（`app/web/fake_runner.py`，不呼叫任何 AI）；沒有轉接器時送出回合回 503。
- 截至 2026-11-13：`main` 已推到 `origin/main`（含 `ae3e16a` 與這份筆記的更新）；`pytest` 結果 303 passed。還沒有網頁介面、成員設定與實際呼叫各家 CLI 的轉接器。
- 建議的下一步（建議，不是決定）：
  1. FR-2 回覆長度上限（預設 100 KB，超過明確告知、不默默截斷）。
  2. 接 Codex 的真實轉接器：照 `app/web/runner.py` 的介面，經由現有的轉接器登記處與回合協定（`app/services/turn_contract.py`、`cli_socket.py`）；要先確認停止（`turn_stop`）能怎麼確認程序已結束。
  3. FR-1 成員設定（讓逾時、模型、認證模式可以依成員設定）。
  4. 範圍 C（NFR-3）：配對、Cookie、CSRF、大小與頻率限制；目前所有改變狀態的請求（送出、中斷、刪除對話）都還沒有防護，所以後端只適合在本機單人環境用。
  5. 前端（React＋TypeScript＋Vite），再接 Grok，最後做 FR-3 群聊。

## 尚未寫進其他文件的待辦

1. 產品名稱 Yiqunren（議群人）已初步自查（2026-11-12）：USPTO 的 `yiqunren` 全類別無紀錄；智慧局 009／042 類無相同或近似；GitHub、PyPI、npm 名稱無人使用。商用或申請註冊前，仍需請商標代理人正式檢索，並考慮註冊。
2. GitHub 組織 `yiqunren` 已建立（2026-11-12），repo 現在位於 `yiqunren/yiqunren`（`origin` 已指向它）。常見網域是否可用還沒查。
3. 舊專案的公開候選資料夾裡，有 Codex 生成的 SVG 素材與 `scripts/build_public_assets.py`，列為之後的候選。這要由規格側 session 照 `CLAUDE.md` 的匯入規則審查；在本 repo 工作的實作側 session 不可自己去讀舊專案。
4. 各家 AI 服務 API 的支援地區還沒查。
5. repo 公開與機密掃描現況（2026-11-13 查）：
   - repo 目前是 PUBLIC。`CLAUDE.md` 規定先 private、做完機密掃描再公開；它是何時、怎麼變成 public 的沒有查到。
   - GitHub 端的 secret scanning、push protection、Dependabot 全部是 disabled，所以 GitHub 沒有掃描紀錄。是否開啟尚未決定（開啟會改外部設定，需擁有者同意）。
   - 本機 gitleaks 8.30.0：掃 Git 歷史（16 個 commit）沒有發現機密；2026-11-13 推送 `27dd2ee` 前再掃一次（23 個 commit），仍沒有發現。掃工作目錄會在 `tests/__pycache__/*.pyc` 報 4 筆，是 `tests/test_host_diagnostics.py` 那 3 筆假值的編譯副本；`__pycache__/` 已被 `.gitignore` 排除，不會進 Git。
   - 歷史與 commit message 沒有舊專案的私人目錄名稱；所有 commit 的作者與提交者都是 noreply 地址；歷史裡的 `/home/` 都是佔位或測試用假路徑。
   - 沒涵蓋：只比對了 `.claude/settings.local.json` 列到的目錄名稱，舊專案若有其他私人名稱（例如舊產品名）沒有清單可比對。
   - `CLAUDE.md` 隔離規則提到上游專案名稱 AgentsOffice、AgentFleet，已隨 repo 公開；要不要保留由擁有者決定。
6. 狀態目錄的權限檢查要求 0700，所以 `YIQUNREN_STATE_DIR` 設在 WSL 的 `/mnt/*`（drvfs 預設權限通常是 0777）會被拒絕。這比技術選型報告第 7 節第 5 項「不必把 `/mnt/*` 擋掉」更嚴；要不要放寬尚未決定。
7. `app/services/write_ownership.py:15` 的寫入權登記庫預設還在 repo 的 `data/` 底下，應改到狀態目錄（技術選型報告第 4 節）；尚未處理。
8. 回合進行中，從按下「中斷」到轉接器確認停止之間，SSE 沒有「中斷中」的事件，介面要等結束事件才知道結果；假轉接器幾乎立即停止，真的轉接器可能要等幾秒，接上真轉接器時可能要補。
9. 刪除對話時若有其他連線正在讀（例如還開著的 SSE），WAL 可能無法立刻清空，舊內容要等之後的檢查點才會清掉（伺服器會記一行警告）；這個情況沒有寫測試。
10. 開發環境：`uv sync` 建立 `.venv`（Python 3.12）。2026-11-13 為了驗證另外下載的 uv 管理 Python 在 `~/.local/share/uv/python/`，可用 `uv python uninstall` 移除。

## 全域設定變更

- 擁有者的 `~/.gitconfig` 加了 gh 的 credential helper（`github.com`、`gist.github.com`），讓 https 推送走 gh 登入。
- 撤銷指令：
  ```
  git config --global --unset-all credential.https://github.com.helper
  git config --global --unset-all credential.https://gist.github.com.helper
  ```

## 仍待決定

- 下一步的順序是否照「主線狀態」的建議。
- 狀態目錄 0700 檢查要不要對 `/mnt/*` 放寬（見上方待辦第 6 項）。
- `docs/SPEC.md` 第 7 節第 6 項：美術素材來源（只有做 FR-11 才需要）。
- 開始收費前要向原廠確認的事項：見 `docs/SPEC.md` 第 7 節第 4 項。
- 是否開啟 GitHub 的 secret scanning 與 push protection（見上方待辦第 5 項）。
- 是否補更多舊專案私人名稱來比對 Git 歷史（見上方待辦第 5 項）。
- `CLAUDE.md` 提到上游專案名稱那一句要不要保留（見上方待辦第 5 項）。
