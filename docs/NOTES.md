# 交接筆記（2026-11-12 起草，2026-11-13 第三次更新）

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
  - 範圍 B（`5ae11fa`）：`POST /api/turns` 送出回合（帶 NFR-1 請求 ID；同 ID 同內容回傳原結果、不同內容 409；同一段對話同時只有一個進行中回合，否則 409）、`GET /api/turns/{id}`、SSE `GET /api/turns/{id}/events`（一律從資料庫讀事件：不帶 `Last-Event-ID` 從頭重送，帶了只補送之後的）。伺服器重啟時怎麼處理殘留的「執行中」回合，見下方「轉接器介面」那一條（原本是一律標為「未知」，`d0a6ee8` 起改為先接回）。
  - 保存與刪除（`483804c` SPEC、`19c3a6c` 實作）：訊息全文與回覆存在本機狀態資料庫，保留到擁有者刪除；`GET /api/conversations/{id}` 列整段對話，`DELETE /api/conversations/{id}` 刪除整段（進行中回合時 409）。每個連線都開 `secure_delete`，刪除後清空 WAL；請求登記只留雜湊並標為 `deleted`，刪除後用同一個請求 ID 重送回 410。
  - 中斷與逾時（`ae3e16a` 第一版，`d0a6ee8` 改成對齊 `worker_turn`）：`POST /api/turns/{id}/interrupt`；單回合逾時目前固定 15 分鐘（`TIMEOUT_DEFAULT`）。
  - 轉接器介面（`d0a6ee8`，寫在 `app/web/runner.py`）：轉接器繼承 `Runner`，實作 `run(turn, hooks)`、`resume(turn_id, record, hooks)`（可選）、`stop(turn_id)`。
    - 三個回呼：`hooks.began(record)` 在橋接接受回合後把回合身分存進資料庫（`turns.bridge_record`，資料庫第 4 版，不含訊息或回覆）；`hooks.progress(item)` 記進度；`hooks.save(reply)` 存回覆並把回合標為完成。轉接器要在 `save` 成功之後才通知橋接丟掉回覆（`worker_turn` 的 ack）；`save` 在回合已不在進行中時丟例外，所以不會誤 ack。
    - 結果用例外表示：`Interrupted`（已中斷，確認程序已停止）、`Unknown(reason)`（未知）、`Failed(kind)`（失敗；分類不在固定清單就記為 `internal_error`）。其他例外、或返回卻沒呼叫 `save`，也都是 `internal_error`，只存固定分類，不存原始錯誤訊息。
    - 中斷：服務層呼叫 `runner.stop(turn_id)`（真轉接器送 `turn_stop`），不再取消 asyncio 工作。送達後 SSE 先送一個 `stopping`（中斷中）事件，之後才是結束事件；送不到轉接器時回 502，回合不變。
    - 逾時：由轉接器或它的橋接執行，秒數放在 `TurnInput.timeout`；服務層不再自己計時。
    - 伺服器關閉（asyncio 取消）時不停止遠端的回合。重啟後 `TurnService.recover()` 對有 `bridge_record` 的進行中回合呼叫 `resume` 接回；沒有身分、身分讀不出來、轉接器不支援接回（`NotImplementedError`）或沒有轉接器的，標為「未知」。
  - 真轉接器 `app/web/worker_runner.py`（`WorkerTurnRunner(provider, auth_mode=, fields=)`）：包住 `app/services/worker_turn.py`，沒有改 `worker_turn.py`、`turn_contract.py`、`turn_host.py`。`tests/test_worker_runner.py` 用同程序裡的真 `TurnHost`（經 Unix socket、testbot 轉接器）驗證完成後 ack、存失敗不 ack、中斷（確認與未確認）、中斷比 `turn_begin` 先到、橋接重啟後接回得到「未知」，以及 HTTP 到橋接的接回與中斷。它還沒接進設定，目前只能在建立 app 時用 `create_app(runner=…)` 注入。
  - `YIQUNREN_FAKE_TURNS=1` 啟用假轉接器（`app/web/fake_runner.py`，不呼叫任何 AI，不支援接回，所有轉接器的成員共用）；沒有轉接器時送出回合回 503。
- FR-1 成員設定的後端（2026-11-14，`b52577f` SPEC、`86b8d94` 實作）：
  - SPEC FR-1 補了：轉接器新增後不能改；停用＝設定保留、不能送新回合、已在跑的回合不受影響；刪除＝拿掉設定、保留對話（回合記著當時的成員名稱），有進行中回合時不能刪；模型清單檢查的分期；成員狀態的推算方式；私聊依成員設定執行。
  - API（`app/web/members.py`、`app/storage/members.py`）：`POST /api/members`（NFR-1 請求 ID，也是成員 ID；刪除後重送回 410）、`GET /api/members`、`GET /api/members/{id}`、`PATCH /api/members/{id}`（含 `enabled` 停用／啟用；`effort` 送 null 清除）、`DELETE /api/members/{id}`。轉接器、認證模式、模型、推理強度能不能設一律查轉接器登記處；逾時 1～60 分鐘整數，預設 15；訂閱 CLI 模式回傳 `terms_notice`；狀態 `running`／`needs_review`（最近一個回合未知）／`idle`。
  - 相容性變更：`POST /api/turns` 的 `member` 從任意文字改成必須是成員 ID（UUID）。成員不存在 422、已停用 409、該轉接器沒有執行者 503，三種都不留紀錄；成員檢查與寫入回合在同一個交易。回合帶入成員的轉接器、模型、推理強度、認證模式與逾時（`TurnInput` 多了 `adapter`、`model`、`effort`、`auth_mode`）。
  - 執行者可以是單一個（所有轉接器共用）或 `{轉接器代號: 執行者}`；`create_app(turn_timeout=)` 只剩測試縮短逾時用，`None` 表示用成員設定。`WorkerTurnRunner` 的認證模式改取自回合，拿掉建構參數。
  - 資料庫第 5 版：新增 `members` 表（不存憑證；`timeout` 存秒數）；`turns` 加 `member_name`、`adapter` 兩欄（第 5 版之前的回合這兩欄是空的）與 `turns_member` 索引。
  - 沒做：前端；列出轉接器與其支援項目的 API（做畫面時需要）；依各家模型清單檢查模型名稱（SPEC 分期，等轉接器能提供清單）；FR-10 的「已核對」確認動作。
- 範圍 C（NFR-3 本機安全，2026-11-14，`a697e45` SPEC、`6535e39` 實作）：
  - SPEC NFR-3 補了配對碼、Cookie、CSRF、Host、大小與頻率限制的細節與已知限制；所有檢查固定開啟，沒有關閉的開關。
  - 實作：`app/web/security.py`（ASGI 中介層 `Guard`＋配對路由）、`app/storage/pairing.py`（配對碼與已配對瀏覽器，只存 SHA-256 雜湊）。檢查順序：Host → CSRF（GET、HEAD 以外）→ 配對 → 請求大小 → 頻率。
  - 配對：`python -m app.web pair` 在本機終端印出一次性配對碼（伺服器有沒有在跑都可以；伺服器輸出與 log 不出現配對碼）；8 個字元、10 分鐘內有效、只能用一次，錯 5 次或再產生新碼就作廢。`POST /api/pair` 換 Cookie（HttpOnly、SameSite=Strict，名稱 `yiqunren_session_<埠>`，連續 30 天沒使用才失效，使用時續期）；`GET /api/session` 查配對狀態；`DELETE /api/session` 只登出這個瀏覽器；`python -m app.web unpair` 撤銷全部。
  - 不必配對的端點只有 `GET /api/health`、`POST /api/pair`、`GET /api/session`、`DELETE /api/session`；其他請求（含讀取與 SSE）沒有有效 Cookie 一律回 401。
  - CSRF：GET、HEAD 以外要帶 `X-Yiqunren-CSRF: 1`；有帶 `Origin` 必須等於 `http://<Host 標頭>`，有帶 `Sec-Fetch-Site` 必須是 `same-origin`，否則 403。Host 只接受 IP 位址或 `localhost` 加上設定的埠，否則 400。請求本體上限 512 KiB（超過 413，含沒有 Content-Length 的分段傳送）。改變狀態的請求合計每分鐘 60 次、其中送出回合每分鐘 20 次，超過回 429 並帶 `Retry-After`。
  - 相容性變更：既有的 API 呼叫方式都要改。要先配對、帶 CSRF 標頭，並用 `127.0.0.1` 或 `localhost`（加正確埠）連線，用其他主機名稱回 400。`create_app` 多了 `clock` 參數，只供測試控制期限與頻率視窗。
  - 資料庫第 6 版：新增 `pairing_code`（同時只有一組）與 `browser_sessions` 兩張表。
  - 測試：`tests/test_web_security.py`（14 個）；`tests/web_client.py` 的 `PairedClient` 先配對再呼叫，其他 HTTP 測試檔都改用它，原有斷言沒有放寬。
  - 已知限制：
    - 頻率計數只在伺服器行程的記憶體裡，重啟就重新計算。
    - Cookie 不分埠，本機其他埠的網頁伺服器也收得到（瀏覽器規則）；Cookie 名稱帶埠號只避免兩個實例互相蓋掉。開放到其他網路時走 HTTP，同網路的人可能看到 Cookie，要另外處理 HTTPS，不在 MVP 範圍（SPEC 已寫）。
    - 啟動時「還沒有配對任何瀏覽器」的提示只在實機確認過（8420、假轉接器），沒有自動測試。
    - 推論，尚未驗證：前端開發若用 Vite 開發伺服器（不同埠），請求的 `Origin` 會和 `Host` 不同而被擋；做前端時要決定怎麼處理，同時要確保 `fetch` 帶 CSRF 標頭（SSE 的 GET 不需要）。
  - 沒做：前端的配對畫面；HTTPS。
- 截至 2026-11-14：`6535e39` 是最新的功能 commit；`pytest` 結果 357 passed（`-W error`）。推送現況以 `git status` 為準，筆記更新不一定已推送。還沒有網頁介面、橋接程式（見下方建議第 2 項）。
- 建議的下一步（建議，不是決定）：
  1. （已完成，`95e69a8` SPEC、`d34468c` 實作）FR-2 回覆長度上限：UTF-8 超過 100,000 位元組時回合失敗，分類 `reply_too_long`，回覆不存、不截斷；檢查在服務層 `save`。限制：橋接每次回覆是一行，單行上限 120,000 位元組（`cli_socket.MAX_RESPONSE`），橋接若回傳更大的一行，`worker_turn` 會當成連線失敗，回合變成「未知」而不是「回覆過長」；要明確告知得由橋接端自己先檢查 100,000 位元組並回報，做橋接與協定第 3 版時一起處理。
  2. 接 Codex 的真實轉接器。包住 `worker_turn` 的 `WorkerTurnRunner` 已經有了，剩下的是：
     - 橋接程式從哪來（決定 3，2026-11-14 定案：先請規格側審查匯入舊專案的 `codex_host_bridge`，審查不過或依賴太多再改成本 repo 自己寫；審查結果還沒回來，見「仍待決定」）：repo 裡目前只有 `scripts/turn_host.py`（橋接共用的回合管理）與 `scripts/private_cli.py`，沒有可以啟動、監聽 socket 的橋接程式。
     - 把它接進設定與 `create_app`（成員、認證模式、`fields` 怎麼組：Codex 的欄位是 message、thread_id、workspace、model、effort）。
     - 橋接協定第 3 版加上結構化的錯誤分類（`error_kind`），才分得出 `timeout` 與 `internal_error`；目前橋接逾時回報為一般失敗，只能記成 `internal_error`。決定 1：等做橋接時一起加。
  3. （後端已完成，`86b8d94`，見上方）FR-1 成員設定。剩下的見上方「沒做」。
  4. （已完成，`a697e45` SPEC、`6535e39` 實作，見上方）範圍 C（NFR-3）：配對、Cookie、CSRF、Host、大小與頻率限制。剩下的見上方「已知限制」與「沒做」。
  5. 前端（React＋TypeScript＋Vite），再接 Grok，最後做 FR-3 群聊。

## 尚未寫進其他文件的待辦

1. 產品名稱 Yiqunren（議群人）已初步自查（2026-11-12）：USPTO 的 `yiqunren` 全類別無紀錄；智慧局 009／042 類無相同或近似；GitHub、PyPI、npm 名稱無人使用。商用或申請註冊前，仍需請商標代理人正式檢索，並考慮註冊。
2. GitHub 組織 `yiqunren` 已建立（2026-11-12），repo 現在位於 `yiqunren/yiqunren`（`origin` 已指向它）。常見網域是否可用還沒查。
3. 舊專案的公開候選資料夾裡，有 Codex 生成的 SVG 素材與 `scripts/build_public_assets.py`，列為之後的候選。這要由規格側 session 照 `CLAUDE.md` 的匯入規則審查；在本 repo 工作的實作側 session 不可自己去讀舊專案。
4. 各家 AI 服務 API 的支援地區還沒查。
5. repo 公開與機密掃描現況（2026-11-13 查）：
   - repo 目前是 PUBLIC。`CLAUDE.md` 規定先 private、做完機密掃描再公開；它是何時、怎麼變成 public 的沒有查到。
   - GitHub 端的 secret scanning、push protection、Dependabot 全部是 disabled，所以 GitHub 沒有掃描紀錄。是否開啟尚未決定（開啟會改外部設定，需擁有者同意）。
   - 本機 gitleaks 8.30.0：掃 Git 歷史（16 個 commit）沒有發現機密；2026-11-13 推送 `27dd2ee` 前再掃一次（23 個 commit），推送 `ecc0a8b` 前又掃一次（31 個 commit，輸出已遮罩），都沒有發現。掃工作目錄會在 `tests/__pycache__/*.pyc` 報 4 筆，是 `tests/test_host_diagnostics.py` 那 3 筆假值的編譯副本；`__pycache__/` 已被 `.gitignore` 排除，不會進 Git。
   - 歷史與 commit message 沒有舊專案的私人目錄名稱；所有 commit 的作者與提交者都是 noreply 地址；歷史裡的 `/home/` 都是佔位或測試用假路徑。
   - 沒涵蓋：只比對了 `.claude/settings.local.json` 列到的目錄名稱，舊專案若有其他私人名稱（例如舊產品名）沒有清單可比對。
   - `CLAUDE.md` 隔離規則提到上游專案名稱 AgentsOffice、AgentFleet，已隨 repo 公開；要不要保留由擁有者決定。
6. 狀態目錄的權限檢查要求 0700，所以 `YIQUNREN_STATE_DIR` 設在 WSL 的 `/mnt/*`（drvfs 預設權限通常是 0777）會被拒絕。這比技術選型報告第 7 節第 5 項「不必把 `/mnt/*` 擋掉」更嚴；要不要放寬尚未決定。
7. `app/services/write_ownership.py:15` 的寫入權登記庫預設還在 repo 的 `data/` 底下，應改到狀態目錄（技術選型報告第 4 節）；尚未處理。
8. `d0a6ee8` 之後轉接器介面的已知限制（沒有處理，也沒有 SPEC 要求）：
   - 接回（`resume`）時進度從頭查回，重啟前已經記過的進度項可能再記一次（只影響進度顯示；要避免得改 `worker_turn`）。
   - 中斷比 `turn_begin` 的回覆先到時，轉接器會在拿到橋接身分後補送 `turn_stop`；補送失敗只記一行警告，回合會照常跑完或逾時。
   - 中斷在回合工作開始前就送到時，轉接器的 `run` 仍會被呼叫，但一開始就照辦、不做任何工作（假轉接器與 `WorkerTurnRunner` 都是）。
   - `tests/test_worker_runner.py` 從 `tests/test_web_turns.py` 匯入讀 SSE 的小函式，兩個測試檔因此綁在一起。
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
- 決定 3（橋接程式從哪來）已定案（擁有者 2026-11-14）：先由規格側 session 依 `CLAUDE.md` 的匯入規則審查舊專案的 `codex_host_bridge`（含它在所有層級依賴、本 repo 還沒有的模組，以及匯入 `tests/test_host_diagnostics.py`、`tests/test_private_cli_lifecycle.py` 時刪掉的 codex 相關測試）；審查先只回報、不複製，匯入要擁有者當輪另外同意。三項檢查有任一核心檔案不過，或依賴鏈超過 3 個尚未匯入的模組，就改成本 repo 自己寫（先查 Codex CLI 現行參數與 JSON 事件格式，橋接端 100,000 位元組檢查與協定第 3 版 `error_kind` 一起設計）。審查結果還沒回來；在這之前真轉接器只能用測試裡的假橋接驗證，實作側不自己去讀舊專案。
- 狀態目錄 0700 檢查要不要對 `/mnt/*` 放寬（見上方待辦第 6 項）。
- `docs/SPEC.md` 第 7 節第 6 項：美術素材來源（只有做 FR-11 才需要）。
- 開始收費前要向原廠確認的事項：見 `docs/SPEC.md` 第 7 節第 4 項。
- 是否開啟 GitHub 的 secret scanning 與 push protection（見上方待辦第 5 項）。
- 是否補更多舊專案私人名稱來比對 Git 歷史（見上方待辦第 5 項）。
- `CLAUDE.md` 提到上游專案名稱那一句要不要保留（見上方待辦第 5 項）。
