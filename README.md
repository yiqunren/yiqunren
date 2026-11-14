# Yiqunren（議群人）

讓多家 AI 在你自己的電腦上一起討論、互相審查，最後由你決定。

> **English:** Yiqunren is a local, self-hosted workspace where several AI agents (such as OpenAI Codex, xAI Grok and Anthropic Claude Code) answer the same question side by side, discuss it, and review each other's work. Their output is always a candidate; you make the final call. The project is in early development and is not yet usable by end users. Documentation is currently in Traditional Chinese.

名字由來：「議群人」念起來就是「一群人」，意思是一群 AI 坐下來議事。

## 目前狀態

**早期開發中，還不能給一般使用者使用。**

目前只有核心的協定、資料驗證與本機元件，以及對應的測試。還沒有網頁介面、沒有安裝包，實際呼叫各家 AI CLI 的橋接程式也還沒完成。

## 想做到什麼

1. **多家並列**：同一個問題同時問多家，比較不同觀點。
2. **互相制衡**：一家做、另一家審，降低單一模型的盲點。
3. **人做最後決定**：AI 的產出一律是候選，要由你確認才算數。
4. **出錯時不亂猜**：狀態不明時明確標示「未知」，交給你核對，不自動重試、不假裝成功。

## 規劃中的功能

| 階段 | 內容 |
|---|---|
| MVP（v0.1） | 成員設定、私聊、群聊討論 |
| v0.2 | 決策模式、派工、專案綁定與唯讀檢視、待處理收件匣 |
| 之後 | 實作加審查、顧問角色、無人值守排程、視覺化辦公室 |

MVP 先接 Codex 與 Grok；Claude Code 是第三家，先做 API key 模式。完整需求見 [`docs/SPEC.md`](docs/SPEC.md)。

## 目前已有的元件

- **轉接器登記處**：唯一列出「有哪些 AI」的地方。預設登記 Codex、Grok、Claude Code；新增或移除一家只改這裡。
- **回合協定**：送給一位成員的一次請求，涵蓋開始、查回、中斷與「未知」狀態。
- **群聊協定**：發言順序、發言上限（預設 2N+3 次，N 是參與成員數）與主持人選擇。
- **工作區寫入權**：同一範圍同時只允許一個成員寫入；無法確認程序是否停止時持續擋住，等你手動解除。
- **失敗診斷檔**：只存在本機，寫入前先遮罩可能的機密。
- **調度依據**：調度用的現況快照與各家能力描述。

## 開發者：跑測試與啟動後端

需要 Python 3.12 以上與 [uv](https://docs.astral.sh/uv/)。目前只在 Linux（WSL）上測試過。

依賴寫在 `pyproject.toml`，版本鎖在 `uv.lock`。`uv sync` 會照鎖檔建立 `.venv`；系統沒有 Python 3.12 時（例如 Ubuntu 22.04 內建的是 3.10），uv 會自動下載。

```bash
git clone https://github.com/yiqunren/yiqunren.git
cd yiqunren
uv sync
.venv/bin/pytest
```

啟動後端（還沒有網頁介面，也還沒接上真的 AI）：

```bash
.venv/bin/python -m app.web
```

第一次使用要先配對：另開一個終端執行下面的指令取得一次性配對碼，再用 `POST /api/pair` 送出，換到 Cookie。配對碼 10 分鐘內有效、只能用一次。伺服器有沒有在跑都可以產生配對碼，伺服器自己的輸出也不會出現配對碼。

```bash
.venv/bin/python -m app.web pair     # 產生配對碼；再產生一組，舊的就作廢
.venv/bin/python -m app.web unpair   # 撤銷所有已配對的瀏覽器
```

還沒有網頁介面，可以先用 curl 試（`-c`、`-b` 讀寫 Cookie 檔；這個檔等於登入憑證，用完要刪掉）：

```bash
curl -c cookies.txt -H 'X-Yiqunren-CSRF: 1' -H 'Content-Type: application/json' \
     -d '{"code": "ABCD-EFGH"}' http://127.0.0.1:8420/api/pair
curl -b cookies.txt http://127.0.0.1:8420/api/members
```

所有請求都要通過以下安全檢查：

- 只接受用 IP 位址或 `localhost` 加上設定的埠連線；用其他主機名稱連線回 400。
- 除了 `GET /api/health`、`POST /api/pair`、`GET /api/session`、`DELETE /api/session`，都要先配對，讀取與 SSE 也一樣，否則回 401。Cookie 連續 30 天沒使用就失效。
- GET、HEAD 以外的請求要帶 `X-Yiqunren-CSRF: 1` 標頭；帶了 `Origin` 或 `Sec-Fetch-Site` 時必須是同源，否則回 403。
- 請求本體上限 512 KiB，超過回 413。
- 改變狀態的請求合計每分鐘最多 60 次，其中送出回合每分鐘最多 20 次；超過回 429，`Retry-After` 標頭告知幾秒後可以再試。

目前的 API：

- `GET /api/health`：健康檢查。
- `POST /api/pair`：用配對碼換 Cookie，內容是 JSON：`code`（大小寫、連字號都可以）。配對碼不對或已失效回 403；輸錯 5 次就作廢，要重新產生。
- `GET /api/session`：查這個瀏覽器是否已配對，回傳 `{"paired": true}` 或 `false`。
- `DELETE /api/session`：登出這個瀏覽器，只撤銷它自己，其他已配對的瀏覽器不受影響。
- `GET /api/adapters`：列出新增成員時可選的轉接器，依登記順序：`code`、`name`、`auth_modes`（支援的認證模式）、`supports_model`、`supports_effort`（能不能指定模型、推理強度），以及 `available`（伺服器目前有沒有這家的執行者；沒有時送出回合會回 503，但有也不代表該家 CLI 已安裝或已登入）。`terms_notice` 是選訂閱 CLI 模式時要顯示的提示。
- `POST /api/members`：新增一位成員（你設定的一位 AI 參與者），內容是 JSON：`request_id`（前端產生的 UUID，也是之後的成員 ID）、`adapter`（轉接器代號，例如 `codex`）、`name`、`auth_mode`（`api_key` 或 `subscription_cli`，要是該轉接器支援的），可選 `model`（空白表示用該家預設）、`effort`（推理強度，該轉接器支援時才能設）、`timeout_minutes`（單回合逾時，1～60 分鐘，預設 15）。同一個 `request_id` 重送回傳原本的成員。選訂閱 CLI 模式時，回傳的 `terms_notice` 會帶服務條款提示。模型目前只存文字，還不比對各家的模型清單。
- `GET /api/members`、`GET /api/members/{id}`：列出成員或查一位，含狀態 `status`：`running`（有進行中回合）、`needs_review`（最近一個回合是「未知」，需要你核對）、`idle`。
- `PATCH /api/members/{id}`：只送要改的欄位：`name`、`model`、`effort`（送 `null` 清除）、`auth_mode`、`timeout_minutes`、`enabled`（`false` 是停用：設定保留、不能送新回合，已經在跑的回合不受影響）。轉接器不能改，要換就新增另一位成員。
- `DELETE /api/members/{id}`：刪除成員設定；過去的對話照樣保留，回合上記著當時的成員名稱。還有進行中回合時回 409。
- `POST /api/turns`：送出一個私聊回合，內容是 JSON：`request_id`、`conversation_id`（都是前端產生的 UUID）、`member`（成員 ID）、`text`。成員不存在回 422、已停用回 409；回合使用該成員的轉接器、模型、推理強度、認證模式與逾時。同一個 `request_id` 重送會回傳原本的回合，不會重複執行；同一段對話同時只能有一個進行中的回合。
- `POST /api/turns/{id}/interrupt`：把中斷要求交給轉接器，送達後回 202，SSE 會先送一個 `stopping`（中斷中）事件。結果由 SSE 的結束事件告知：轉接器確認程序已停止才是「已中斷」，無法確認時是「未知」。回合已結束時回 409；要求沒有送達轉接器時回 502，回合可能仍在執行。
- `GET /api/turns/{id}`：查回合狀態（執行中、完成、失敗、已中斷、未知），含送出的訊息與回覆。單回合逾時依成員設定，由轉接器或它的橋接執行：逾時且確認程序停止是「失敗（逾時）」，無法確認時是「未知」。回覆以 UTF-8 編碼超過 100,000 位元組時是「失敗（回覆過長）」，回覆不存、也不截斷。
- `GET /api/conversations/{conversation_id}`：依時間順序列出一段對話的所有回合（訊息與回覆）。
- `DELETE /api/conversations/{conversation_id}`：刪除一整段對話的訊息、回覆與事件；還有進行中回合時回 409。刪除後用同一個 `request_id` 重送會回 410，不會重新執行。
- `GET /api/turns/{id}/events`：用 SSE 接收進度、中斷中與結束事件。不帶 `Last-Event-ID` 時從頭重送，帶了就只補送之後的事件。

伺服器關閉時不會停止還在執行的回合。重新啟動後，轉接器已經存下身分的回合會接回來繼續等結果；接不回來的（例如沒有身分紀錄，或橋接也重啟過）標為「未知」。

還沒接上轉接器之前，送出回合會回 503（成員的轉接器沒有接上時也是）。開發時可設 `YIQUNREN_FAKE_TURNS=1`，改用假轉接器：所有轉接器的成員都由它回覆，它不呼叫任何 AI，送出幾個進度後回覆一段固定文字。

預設只聽 `127.0.0.1:8420`，狀態資料庫放在 `~/.local/state/yiqunren/`（有設 `XDG_STATE_HOME` 時改放在它底下）。可用環境變數覆寫：

| 環境變數 | 用途 | 預設 |
|---|---|---|
| `YIQUNREN_HOST` | 監聽的 IP 位址；改成其他位址就會開放給其他網路 | `127.0.0.1` |
| `YIQUNREN_PORT` | 監聽的埠 | `8420` |
| `YIQUNREN_STATE_DIR` | 狀態資料庫目錄（絕對路徑，權限必須是 0700） | `~/.local/state/yiqunren` |
| `YIQUNREN_FAKE_TURNS` | 設成 `1` 時，私聊回合改由假轉接器回覆（只供開發） | `0` |
| `YIQUNREN_WRITE_REGISTRY` | 寫入權登記庫的檔案路徑（絕對路徑，不能經符號連結，所在目錄權限必須是 0700）；空字串視同沒設 | 狀態目錄裡的 `write-ownership.sqlite3` |

寫入權登記庫記錄哪個成員正在寫哪個專案範圍（同一範圍同時只允許一個成員寫入，見 `docs/SPEC.md` 的 NFR-2），預設和狀態資料庫放在同一個目錄，不放在 repo 底下。目前只有橋接的回合管理（`scripts/turn_host.py`）和命令列工具 `scripts/write_ownership.py` 會用到，後端還沒有接上。找不到狀態目錄（例如沒有家目錄、也沒設 `YIQUNREN_STATE_DIR`）時，寫入權工具會回報錯誤並禁止開始寫入。

資料庫與登記庫建議放在 Linux 檔案系統上；放在 WSL 的 `/mnt/*` 底下會變慢，也不要讓 Windows 端的程式同時開這些檔。

## 憑證與費用

- 本專案不提供、也不內建任何人的 API key 或帳號；憑證由你自己在本機設定。
- 規劃中每家都支援兩種用法：用你自己的 API key，或呼叫你自己安裝、自己登入的官方 CLI。使用時須遵守各家的服務條款，費用由你向各家支付。
- 設計上預設不送出任何遙測資料。

## 文件

- [`docs/SPEC.md`](docs/SPEC.md)：功能規格，本專案唯一的需求來源。
- [`PROVENANCE.md`](PROVENANCE.md)：從其他來源帶進本 repo 的檔案紀錄。
- [`LICENSE`](LICENSE)、[`NOTICE`](NOTICE)：授權條款與版權聲明。

## 授權

以 [Apache License 2.0](LICENSE) 授權。「Yiqunren」與「議群人」的名稱與商標不隨 Apache-2.0 授權給他人。

Codex、Grok、Claude Code 分別是 OpenAI、xAI、Anthropic 的產品名稱或商標。本專案與這些公司沒有關聯，也沒有獲得它們的背書。
