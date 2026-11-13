# 技術選型比較報告（SPEC 第 7 節第 5 項）

- 日期：2026-11-13
- 性質：調研報告，供擁有者決定用。**這是建議，不是決定**；決定後要寫回 `docs/SPEC.md` 第 7 節第 5 項，才算定案。
- 範圍：後端語言與框架、資料庫、前端框架；順帶處理兩個連帶問題：Python 最低版本、瀏覽器即時更新方式。
- 方法：需求只取自 `docs/SPEC.md` 與本 repo 現有程式碼。版本、授權、Python／Node 下限以 2026-11-13 直接查詢 PyPI 與 npm 官方 registry 的結果為準；功能與政策以各專案官方文件為主，少數只找到第三方來源的會標明。
- 沒做的事：初版調研時沒有安裝任何套件。之後擁有者同意安裝 FastAPI、Uvicorn、Vite，在暫存目錄做了最小原型；之後又同意用 uv 下載 Python 3.12 重跑測試，以及在 `/mnt/d` 的暫存目錄測 SQLite WAL。第 7 節 6 項都有實測結果，各項的限制也列在那裡。

## 0. 一頁結論

推薦組合：

| 項目 | 推薦 | 主要替代 |
|---|---|---|
| 後端語言 | Python | （不建議換語言） |
| Python 最低版本 | 3.12 | 3.11 |
| 後端框架 | FastAPI（跑在 Uvicorn 上），明確關閉內建遙測 | Litestar；或只用 Starlette |
| 資料庫 | SQLite，用標準庫 `sqlite3`，WAL 模式 | SQLite＋SQLAlchemy／Alembic |
| 前端 | React＋TypeScript＋Vite，打包成靜態檔由後端提供 | Svelte＋Vite |
| 即時更新 | SSE（伺服器推送事件）＋一般 HTTP 請求 | WebSocket |

一句話理由：現有程式碼已經是 Python asyncio＋Unix socket＋SQLite，照這條路走不必重寫；資料庫與後端都是單機、單一擁有者，不需要資料庫伺服器；前端的群聊、計時、中斷與之後的 2D 場景都是狀態多的互動畫面，用元件式框架比較好維護，而且打包後使用者不需要裝 Node。

需要擁有者決定的事（照順序）：

1. 後端維持 Python？（建議：是）
2. Python 最低版本定在 3.12？（建議：是；3.10 已在 2026-10 停止支援）
3. 後端框架選 FastAPI、Litestar 還是只用 Starlette？（建議：FastAPI）
4. 資料庫用 SQLite＋標準庫？（建議：是）
5. 前端選 React 還是 Svelte？（建議：React）

## 1. 前提：選型必須滿足的條件

以下條件來自 SPEC 與現有程式碼，後面各節都用這些編號比較。

- **C1 沿用現有程式碼**：現在約 4,400 行 Python（含測試），只用標準庫加 pytest（README「開發者：跑測試」一節）。App 端透過 asyncio 的 Unix socket 和各家橋接程序往來（`app/services/cli_socket.py:29`），回合是「begin → 查回 → 中斷 → ack」的非同步協定（`app/services/worker_turn.py`、`scripts/turn_host.py`），寫入權登記已經用 SQLite（`app/services/write_ownership.py:9`、`:83`）。後端最好能直接 import 這些模組。
- **C2 長時間回合與即時狀態**：回合預設可跑 15 分鐘、最長 60 分鐘（FR-1）；介面要顯示「執行中」與經過時間、可以中斷（FR-2）；重新整理或伺服器重啟後要能查回狀態（FR-2）；群聊要同時追蹤多位成員（FR-3）。
- **C3 冪等與唯一執行權**：每個請求帶唯一 ID，重送回原結果；呼叫模型前先寫進資料庫並取得唯一執行權（NFR-1）。工作區寫入權同一時間只給一個成員（NFR-2）。
- **C4 本機安全**：預設只聽 127.0.0.1；首次配對碼、之後用 Cookie；改變狀態的請求要防 CSRF、限制大小與頻率；AI 回覆一律當純文字顯示，不當 HTML 渲染（NFR-3）。
- **C5 不送遙測、不經手憑證**：預設不送任何遙測（NFR-4）；憑證不寫進資料庫、log 或錯誤訊息（NFR-4、NFR-6）。
- **C6 好安裝**：一般使用者照 README 能在全新的 Linux 或 WSL 上裝起來（NFR-5）。
- **C7 授權**：所有依賴都要允許商用與再散布，並記進 `THIRD_PARTY_NOTICES.md`（`CLAUDE.md` 隔離規則）。
- **C8 可擴充**：轉接器、顧問角色、排程任務、介面面板之後要能由另外安裝的擴充提供（NFR-7）；之後可能有 2D 場景（FR-11）。
- **C9 單一擁有者、單機**：不做多使用者或雲端代管（SPEC 第 6 節）。

## 2. 後端語言與框架

### 2.1 語言：建議維持 Python

| 候選 | C1 沿用 | C6 安裝 | 評語 |
|---|---|---|---|
| Python | 直接沿用 | 要有 Python 3.12＋（見第 3 節） | 推薦 |
| TypeScript（Node） | 要重寫約 4,400 行與全部測試 | 要有 Node | 前後端同一語言是優點，但重寫成本與風險都高，沒有對應的 SPEC 需求撐得起 |
| Go／Rust | 要重寫 | 可以出單一執行檔，安裝最簡單 | 只有 C6 占優；重寫成本最高 |

結論：沒有任何 SPEC 需求是 Python 做不到、而其他語言才做得到的；換語言只會把已經過測試的協定與生命週期程式重寫一遍。

### 2.2 框架：三個 Python 候選

三者都是 ASGI 框架，都能直接在同一個 asyncio 事件迴圈裡呼叫現有的 `cli_socket.request(...)`，滿足 C1。差別在下表。

| 項目 | FastAPI | Litestar | Django |
|---|---|---|---|
| 最新版（2026-11-13 PyPI） | 0.162.5 | 2.25.0 | 6.1.3 |
| Python 下限 | ≥3.10（但它依賴的 Starlette 最新版要 ≥3.11） | ≥3.8 | ≥3.12 |
| 授權 | MIT | MIT | BSD-3-Clause |
| SSE（C2） | 內建，0.135.0 起有 `EventSourceResponse`，會自動送保活訊號 | 內建 SSE 回應，可設保活間隔 | 可用非同步串流回應自己組；官方追蹤系統有串流相關未解問題（見下方說明） |
| CSRF（C4） | 沒有內建，要自己寫中介層或用第三方套件 | 內建 CSRF 中介層 | 內建 |
| 請求驗證（C3） | Pydantic，內建 | 內建（msgspec／Pydantic 皆可） | 表單／序列化器，偏同步 ORM 思維 |
| 遙測（C5） | 內建 OpenTelemetry，預設不外送，可在程式裡明確關閉（見下方說明） | 未發現內建遙測 | 未發現內建遙測 |
| 社群與資料量 | 最大 | 小很多 | 很大，但非同步串流的資料較少 |
| 版本風險 | 版本號仍在 0.x，常有小改動 | 3.0 規劃中（依賴注入大改），2.x 之後可能要遷移 | 穩定 |

**FastAPI 的遙測細節（C5，已讀官方文件原文）**：FastAPI 現在預設會為 HTTP 請求產生 trace、metrics、logs，並把 `opentelemetry-api` 列為必要依賴。但只有同時符合兩個條件才會外送：設定 `FASTAPI_OTEL_AUTO_CONFIGURE=true`（或程式裡 `auto_configure=True`），而且設了 OTLP 端點環境變數；外送用的套件在 `fastapi[standard]` 額外選項裡。單裝 `opentelemetry-api`、沒有 SDK 時，OpenTelemetry 規格要求它是不做事的空實作。為了讓 NFR-4 不受使用者環境變數影響，採用 FastAPI 時應該：
- 只裝 `fastapi`，不裝 `fastapi[standard]`（另外單獨裝 `uvicorn`）。
- 建立 app 時明確傳 `telemetry={"auto_configure": False, "tracing": False, "metrics": False, "logs": False}`。官方文件寫明程式裡的 `auto_configure` 值會蓋過環境變數。
- 加一條測試：設了上述環境變數時，仍然沒有任何 exporter 被建立。

原型已實測（見第 7 節第 3 項）：只裝 `fastapi`、沒有明確關閉遙測、又設了上述環境變數時，app 照常啟動，只在啟動時記一行「FastAPI automatic telemetry configuration failed」錯誤，不外送。

**Django 的串流問題**：Django 官方 ticket 曾記錄串流回應沒有處理 ASGI 的 `http.disconnect`、非同步產生器的收尾延遲等問題（見來源）。這些 ticket 現在是否已修好，本次沒有逐一核對。SSE 是本產品的核心路徑（C2），所以 Django 在這點上風險最高；再加上它的強項（ORM、管理後台、多使用者帳號）本產品大多用不到（C9），不建議。

**FastAPI 與 Litestar 的取捨**：
- Litestar 的優點是 CSRF、SSE、session 都內建，C4 少寫一些程式。缺點是社群小很多，而且 3.0 會大改依賴注入，現在開始用 2.x，之後大概要遷移一次。
- FastAPI 的 CSRF 要自己寫，但本產品是同源的單頁應用，只聽 127.0.0.1，可以用「SameSite=Strict Cookie＋檢查 `Origin`／`Sec-Fetch-Site` 標頭＋改狀態的請求要帶自訂標頭或 token」組合，大約幾十行，而且好寫測試。頻率與大小限制兩個框架都得自己處理。
- 本專案主要靠 AI 協作寫程式；FastAPI 的官方文件、範例與各家模型的熟悉度都明顯較多，這點對維護成本是實際的差距（推論，沒有量化）。

**只用 Starlette 的選項**：FastAPI 本身就建在 Starlette 上。只用 Starlette（BSD-3-Clause，1.10.0，Python ≥3.11）依賴最少，也沒有內建遙測；代價是請求驗證要自己寫。現有程式碼本來就是手寫驗證（例如 `discussion_contract.validate_begin`），所以這條路也合理。如果擁有者很在意依賴數量，這是比 FastAPI 更精簡的選擇。

**建議：FastAPI**，並照上面的方式關閉遙測。若擁有者偏好依賴最少，改選只用 Starlette；若想少寫安全相關程式、能接受之後遷移一次，選 Litestar。

## 3. Python 最低版本：建議 3.12

- 本機 `.venv` 與 README 現在是 Python 3.10。依 python.org，**3.10 已在 2026-10 停止支援**（3.10.22 是最後一版），之後沒有安全更新。
- 套件端已經在往上移：Starlette 最新版要 ≥3.11、SQLAlchemy 2.1 要 ≥3.11、Django 6.1 要 ≥3.12（2026-11-13 PyPI）。
- 停止支援時間（PEP 664／693／719）：3.11 是 2027-10，3.12 是 2028-10，3.13 是 2029-10。
- Ubuntu 的預設版本：22.04 是 3.10（套件庫另有 3.11），24.04 是 3.12。

| 選項 | 優點 | 缺點 |
|---|---|---|
| 3.11 | Ubuntu 22.04 用套件庫就能裝 | 只剩不到一年支援 |
| **3.12** | Ubuntu 24.04 內建；支援到 2028-10 | Ubuntu 22.04 使用者要另外裝（例如用 uv 下載 Python） |
| 3.13 | 支援最久 | 兩個 LTS 都不是內建版本，每個使用者都要另外裝 |

建議 3.12。安裝說明可以寫成兩條路：Ubuntu 24.04 直接用系統 Python；其他環境用 uv（`uv python install 3.12`，uv 使用 python-build-standalone 的建置，不是 python.org 官方二進位檔）。改下限時要同步改 README，並在 3.12 上重跑全部測試；這屬於實作工作，不在本報告範圍。

## 4. 資料庫

| 項目 | SQLite＋標準庫 `sqlite3` | SQLite＋SQLAlchemy 2.1＋Alembic | PostgreSQL |
|---|---|---|---|
| 額外依賴 | 無 | 兩個套件（皆 MIT；SQLAlchemy 2.1.8 要 Python ≥3.11） | 要裝資料庫伺服器或 Docker |
| C1 沿用 | 現有 `write_ownership.py` 就是這樣寫 | 要和現有寫法並存或改寫 | 要改寫 |
| C3 唯一執行權 | 用 `BEGIN IMMEDIATE` 交易＋唯一索引即可 | 同左，多一層包裝 | 可以，但殺雞用牛刀 |
| C6 安裝 | 什麼都不用裝 | pip 會一起裝 | 使用者要多管一個服務 |
| 資料表變更（migration） | 自己寫，用 `PRAGMA user_version` 記版本 | Alembic 自動產生與管理 | 要另選工具 |

SQLite 的已知限制與對策：

- WAL 模式下讀者和寫者不互相阻擋，但同一時間只有一個寫者（SQLite 官方 WAL 文件）。本產品只有一位擁有者，寫入量很小，夠用。
- WAL **不能放在網路檔案系統上**（同一份官方文件）。WSL 下的 `/mnt/c`、`/mnt/d` 是透過 Windows 檔案系統橋接的，初版調研時沒有驗證 WAL 在上面能不能正常運作；之後實測，只從 WSL 內部存取時可以運作，但約慢一倍；Windows 端的程式同時開檔時是否遵守 SQLite 的鎖沒有測，推論是不會（見第 7 節第 5 項）。保險做法是把資料庫放在 Linux 檔案系統的狀態目錄（例如 `~/.local/state/yiqunren/`，可用 `YIQUNREN_` 開頭的環境變數覆寫），不要放在 repo 目錄底下。現在 `write_ownership.py:15` 的預設位置在 repo 的 `data/` 底下，如果使用者把 repo clone 到 `/mnt/d`，資料庫就會落在 Windows 磁碟上；這點要在實作時一起調整。
- 標準庫 `sqlite3` 是同步呼叫。交易都很短，可以直接在事件迴圈裡呼叫，或包一層 `asyncio.to_thread`；不必為此加 `aiosqlite`。

**小實驗（2026-11-13，只用標準庫，在暫存目錄執行，沒有放進 repo）**：做法是 WAL 模式，加上「`BEGIN IMMEDIATE` → 查 ID → 沒有就寫入並取得執行權」的寫法。結果如下：

- 同 ID、同內容重送，會回傳原紀錄。
- 同 ID、不同內容會被拒絕。
- 16 個程序同時搶同一個 ID，只有 1 個取得執行權。
- 16 個程序帶兩種不同內容搶同一個 ID，只有 1 個取得執行權；另一種內容一律被拒絕。
- 有交易正在寫入時，讀取不會被擋住，而且看不到還沒提交的資料；第二個寫者會拿到 `locked`。

以上在 Python 3.10（SQLite 3.37.2）重跑 6 次、Python 3.11（SQLite 3.53.1）跑 1 次，全部通過。這證實 NFR-1 的冪等與唯一執行權用標準庫就做得到。

另做了一個實驗：讓持有寫入交易的程序被 `SIGKILL` 強制結束。結果是鎖在 1 ms 內就能重新取得，還沒提交的資料也消失了，其他程序能正常取得執行權。這在兩個 Python 版本上都通過，代表程序當掉不會讓資料庫卡住。

資料庫放在 `/mnt/*` 底下的情況，之後另外驗證過，見第 7 節第 5 項。

**建議：SQLite＋標準庫**。等資料表多到手寫 migration 開始出錯（經驗值：十幾張表、或每個版本都要改表），再考慮加 SQLAlchemy／Alembic。PostgreSQL 不建議：它解決的是多使用者、多機器的問題，本產品沒有（C9），而且會讓安裝變難（C6）。

## 5. 前端框架

共同前提：不論選哪個，都打包成靜態檔，放進 Python 套件由後端提供，**使用者不需要裝 Node**，只有開發者打包時需要（C6）。Vite 8 要 Node 20.19＋或 22.12＋；目前 Node 的 Active LTS 是 26（2026-11-10 發布 26.13.1），24 是維護期 LTS。

| 項目 | React＋Vite | Svelte＋Vite | Vue＋Vite | htmx＋伺服器模板 |
|---|---|---|---|---|
| 最新版（2026-11-13 npm） | react 19.3.1 | svelte 5.57.3 | vue 3.5.45 | htmx.org 2.0.11 |
| 授權 | MIT | MIT | MIT | 0BSD |
| 要不要打包 | 要 | 要 | 要 | 不用，連 Node 都不用 |
| 複雜狀態（C2：多成員、計時、中斷、重連） | 適合 | 適合 | 適合 | 吃力，狀態分散在伺服器片段與 DOM |
| AI 回覆當純文字（C4） | JSX 預設轉義文字 | 模板預設轉義 | 模板預設轉義 | 由伺服器模板負責轉義（Jinja2 要開 autoescape） |
| 擴充面板（C8，NFR-7） | 生態最大，動態載入元件的做法最多 | 可以，資料較少 | 可以 | 擴充要提供伺服器端片段，較難隔離 |
| 2D 場景（C8，FR-11） | 可搭 PixiJS（MIT）等，任何框架都能用 | 同左 | 同左 | 同左，但和其他畫面的狀態整合較難 |
| 版本風險 | 穩定 | 穩定 | 穩定 | htmx 4 開發中，SSE 寫法和 2.x 不同 |

說明：

- 本產品的核心畫面是「好幾位成員同時在跑、各自有狀態與計時、可以中斷、重新整理要能接回」，這是狀態很多的互動畫面。htmx 擅長的是表單與局部更新為主的頁面，用在這裡會越寫越吃力；它最大的優點（不用 Node）在「打包成靜態檔」的做法下已經沒有差別。
- React、Svelte、Vue 在功能上都夠用。React 的優勢是生態與資料量最大、AI 協作最熟悉，擴充面板與 2D 場景也最容易找到現成做法。Svelte 的優勢是程式碼較少、打包較小、上手較簡單。Vue 介於兩者之間，沒有特別突出的理由選它。
- 兩個注意事項：(1) AI 回覆如果之後要顯示成 Markdown，必須用「不允許原始 HTML」的轉換方式並做淨化，否則違反 NFR-3；這和框架無關，要在 SPEC 或實作時決定。(2) React 的 `dangerouslySetInnerHTML`（或其他框架的同等功能）在專案裡應該禁止使用，可以用 lint 規則擋。

**建議：React＋TypeScript＋Vite**（打包成單頁應用，不用伺服器端渲染）。如果擁有者偏好程式碼少、上手快，改選 Svelte＋Vite；兩者對後端的要求完全相同，換選不影響第 2～4 節。

## 6. 即時更新方式：建議 SSE

| 方式 | 適合度 |
|---|---|
| **SSE** | 伺服器單向推送狀態、進度與經過時間，正好是 C2 要的。網路中斷時，瀏覽器的 `EventSource` 會自動重連並帶上 `Last-Event-ID`，伺服器從那之後補送即可。但**重新整理頁面會建立新的 `EventSource`，不會帶 `Last-Event-ID`**（原型已證實，見第 7 節），所以「重新整理後接回」（FR-2）要靠伺服器從資料庫重送完整狀態，不能只靠這個標頭。同源請求會帶 Cookie，不必另外處理認證。FastAPI、Litestar 都內建。 |
| WebSocket | 雙向，但本產品的「送出、中斷」都是單次動作，用一般 POST 就好，而且 POST 能直接套 CSRF 與冪等規則（NFR-1、NFR-3）。WebSocket 要另外處理這兩件事。MVP 不需要。 |
| 定時輪詢 | 最簡單，但經過時間與進度的更新會一頓一頓；可以當 SSE 斷線時的退路。 |

做法：狀態變化寫進資料庫 → 透過 SSE 推給瀏覽器；送出、中斷、確認等動作走一般 POST，帶 NFR-1 的請求 ID。

## 7. 推薦組合的風險與要先驗證的事

2026-11-13 擁有者同意安裝 FastAPI、Uvicorn、Vite 後，在暫存目錄做了最小原型（沒有放進 repo）：FastAPI 0.162.5、Starlette 1.10.0、Uvicorn 0.54.0，跑在 Python 3.11.15；前端是 Vite 8.3.8 打包的原生 JS（未授權 React，所以沒用）。後端用一個模擬回合代替真的 AI 呼叫，依序送出進度事件與完成事件，SSE 端點支援 `Last-Event-ID` 補送。測試客戶端是 Node 22 內建的 `EventSource` 與 curl，**不是真的瀏覽器**。

1. **長連線與重連——已驗證，但有一點和原本的假設不同。**
   - 60 分鐘：單一 SSE 連線持續 3661 秒，8 個事件依序收齊、0 個錯誤；期間收到 237 個保活訊號（FastAPI 每 15 秒送一次），任兩行輸出最長間隔 16 秒，連線沒有被切斷。
   - 網路中斷：伺服器每送 3 個事件就主動斷線，客戶端自動重連 6 次，每次都帶上 `Last-Event-ID`（3、6、9…18），21 個事件依序收齊，沒有重複也沒有遺漏。
   - 重新整理：新建的 `EventSource` **不會**帶 `Last-Event-ID`，伺服器只能從頭重送。所以原本「重新整理後能依 `Last-Event-ID` 接回」的寫法不成立，第 6 節已更正：FR-2 的重新整理接回要靠伺服器從資料庫重送完整狀態。
2. **斷線偵測——已驗證。** 客戶端正常關閉、或被 `kill -9` 強制結束時，後端約 0.02 秒就察覺並結束該條 SSE；回合本身照常跑完（21 個事件、狀態為完成），不受瀏覽器連線影響。限制：沒有模擬「網路線被拔掉、但 TCP 沒有收到關閉」的半開連線，這種情況要靠保活訊號寫入失敗才會發現。
3. **遙測——已驗證。** 四組都設了 `FASTAPI_OTEL_AUTO_CONFIGURE=true` 與指向本機假收集器的 OTLP 端點：
   - 對照組（`fastapi[standard]`、遙測維持預設）：收集器收到 2 次 trace 與 5 次 metrics，證明這個測試抓得到外送。
   - `fastapi[standard]`＋照第 2.2 節明確關閉：0 次。
   - 只裝 `fastapi`＋明確關閉：0 次。
   - 只裝 `fastapi`、沒有明確關閉：app 照常啟動，只記一行設定失敗的錯誤，0 次。
4. **Python 3.12——已驗證。** 擁有者另外同意後，用 uv 下載 Python 3.12.15，在暫存目錄建虛擬環境，只裝 README 列的唯一依賴 pytest（9.2.0，和現有 3.10 環境同版本），在 repo 目錄跑全部測試：249 個通過、10 個子測試通過，exit 0；把 `DeprecationWarning`／`PendingDeprecationWarning` 當成錯誤再跑一次，結果相同。對照組（現有 3.10 環境）也是 249 個通過。跑測試時關掉了 pytest 快取與 `.pyc` 寫入，repo 沒有多出檔案。這只證明現有程式碼在 3.12 上能跑；README 的版本下限要不要改，仍等擁有者決定第 0 節第 2 項。
5. **`/mnt/*` 上的 WAL——在 WSL 內部使用時可以運作，但較慢，仍建議放在 Linux 檔案系統。** 擁有者另外同意後，在 `/mnt/d`（WSL2 的 drvfs，檔案系統類型 `v9fs`）底下建一個暫存目錄，跑三個只用標準庫的實驗：第 4 節的冪等／唯一執行權實驗、`SIGKILL` 實驗，以及新加的壓力實驗（6 個程序各用 `BEGIN IMMEDIATE` 寫 150 筆，檢查筆數、每筆交易看到的筆數不重複、`PRAGMA integrity_check`）。同時在 Linux 檔案系統跑同一組當對照組。Python 3.10（SQLite 3.37.2）與 3.12（SQLite 3.53.1）各跑一遍，共跑 3 輪：`/mnt/d` 與對照組 36 組全部通過，`journal_mode` 都確實是 `wal`；暫存目錄跑完已刪除。壓力實驗在 `/mnt/d` 花 3.13 秒，Linux 檔案系統 1.49 秒，約慢一倍。限制與判斷：
   - 這只證明「所有存取都來自同一個 WSL 裡的程序」時鎖與共享記憶體正常。SQLite 在 Linux 上用的是 POSIX 檔案鎖；Windows 端的程式（備份、同步、防毒軟體或 Windows 版的 SQLite 工具）同時開這個檔時，推論不會遵守這些鎖。這是推論，沒有測，也不打算靠測試保證。
   - 只測了 `/mnt/d`，`/mnt/c` 是同一種掛載方式，沒有另外測；也沒有測真的網路磁碟。
   - 結論：不必把 `/mnt/*` 當成錯誤擋掉，但預設位置維持第 4 節的 Linux 狀態目錄；使用者自己把路徑設到 `/mnt/*` 時，可以印一行提醒（較慢、不要讓 Windows 端程式同時開這個檔）。
6. **靜態檔——已驗證。** 前端用 Vite 打包後放進 Python 套件，做成 wheel，離線裝進全新的虛擬環境；在 PATH 只有一個空目錄（確認找不到 `node`）、工作目錄是 `/` 的條件下啟動。套件確實從 `site-packages` 載入；首頁與 JS 檔都回 200，內容和打包結果逐位元組相同（JS 的 Content-Type 是 `text/javascript`）；透過安裝後的套件也能收到 SSE 事件。限制：(1) 打包用的是系統上舊版 setuptools 59.6 的 `setup.py` 寫法，正式專案應改用 `pyproject.toml`；(2) 只測了 `pip`／`uv pip install`，沒測 `uv tool install`；(3) 沒有用真的瀏覽器開頁面。

## 8. 什麼情況該重新考慮

- **改選 Litestar**：如果原型發現自己寫的 CSRF、session、頻率限制程式量明顯變大，或安全審查要求用框架內建的實作。
- **改選只用 Starlette**：如果 FastAPI 再加入其他預設啟用、和 NFR-4 有關的功能，或依賴數量成為問題。
- **加 SQLAlchemy／Alembic**：資料表多到手寫 migration 開始出錯。
- **改用 PostgreSQL**：只有 SPEC 第 6 節改成要做多使用者或雲端版本時。
- **改用 WebSocket**：出現真正需要雙向即時的功能（例如擁有者在回合進行中持續送輸入）。
- **改選 Svelte**：React 的打包大小或複雜度在實作中造成實際困擾。
- **換語言**：只有出現 Python 做不到、而且 SPEC 明確要求的需求（例如規定要單一執行檔發行）。

## 9. 若採用推薦組合，SPEC 第 7 節第 5 項可以這樣寫（草稿，擁有者確認後才寫入）

> 5. （已決定，YYYY-MM-DD）技術選型：
>    - 後端：Python 3.12 以上；Web 框架用 FastAPI，跑在 Uvicorn 上。只安裝 `fastapi`，不安裝 `fastapi[standard]`，並在程式中明確關閉 FastAPI 內建的 OpenTelemetry（NFR-4）。
>    - 資料庫：SQLite（標準庫 `sqlite3`，WAL 模式），資料庫檔放在 Linux 檔案系統上的狀態目錄，可由環境變數覆寫；資料表版本用 `PRAGMA user_version` 管理。
>    - 前端：React＋TypeScript＋Vite，打包成靜態檔由後端提供；一般使用者不需要安裝 Node。
>    - 瀏覽器即時更新用 SSE；改變狀態的動作用一般 HTTP 請求，套用 NFR-1 與 NFR-3。

## 10. 授權彙整（2026-11-13 registry 查詢結果）

全部允許商用與再散布。實際採用時，要把**會隨產品散布的**套件逐一記進 `THIRD_PARTY_NOTICES.md`，並核對當時版本的 LICENSE 檔。

| 套件 | 版本 | 授權 | 備註 |
|---|---|---|---|
| fastapi | 0.162.5 | MIT | 依賴 starlette、pydantic、anyio、opentelemetry-api 等 |
| starlette | 1.10.0 | BSD-3-Clause | Python ≥3.11 |
| uvicorn | 0.54.0 | BSD-3-Clause | |
| pydantic | 2.14.3 | MIT | |
| litestar | 2.25.0 | MIT | 替代方案 |
| Django | 6.1.3 | BSD-3-Clause | 不建議 |
| SQLAlchemy | 2.1.8 | MIT | 選用 |
| alembic | 1.20.1 | MIT | 選用 |
| react／react-dom | 19.3.1 | MIT | |
| vite | 8.3.8 | MIT | 只在開發打包時使用，不隨產品散布 |
| typescript | 7.0.2 | Apache-2.0 | 只在開發時使用 |
| svelte | 5.57.3 | MIT | 替代方案 |
| vue | 3.5.45 | MIT | |
| htmx.org | 2.0.11 | 0BSD | |
| pixi.js | 8.23.0 | MIT | 只有做 FR-11 才需要 |

FastAPI 的依賴 `opentelemetry-api` 等間接依賴的授權，本次沒有逐一查，採用時要一併核對。

## 11. 來源

官方 registry（2026-11-13 直接查詢）：

- PyPI JSON API：`https://pypi.org/pypi/<套件名>/json`（fastapi、starlette、uvicorn、pydantic、litestar、django、sqlalchemy、alembic、jinja2、aiosqlite）
- npm registry：`https://registry.npmjs.org/<套件名>/latest`（react、react-dom、vite、svelte、vue、htmx.org、typescript、@sveltejs/kit、pixi.js）
- Node.js 發布清單：<https://nodejs.org/dist/index.json>

官方文件：

- Python 3.10.22（最後一版）：<https://www.python.org/downloads/release/python-31022/>
- Python 版本狀態：<https://devguide.python.org/versions/>
- Ubuntu 各版本的 Python：<https://ubuntu.com/developers/docs/reference/availability/python/>
- uv 安裝 Python：<https://docs.astral.sh/uv/guides/install-python/>、<https://docs.astral.sh/uv/concepts/python-versions/>
- FastAPI SSE：<https://fastapi.tiangolo.com/tutorial/server-sent-events/>、<https://fastapi.tiangolo.com/reference/sse/>
- FastAPI OpenTelemetry：<https://fastapi.tiangolo.com/advanced/opentelemetry/>
- OpenTelemetry 空實作規格：<https://opentelemetry.io/docs/specs/otel/metrics/noop/>
- Litestar 內建中介層（含 CSRF）：<https://docs.litestar.dev/2/usage/middleware/builtin-middleware.html>
- Litestar SSE：<https://docs.litestar.dev/2/reference/response/sse.html>
- Litestar 3.0 規劃：<https://litestar.dev/blog/v3-announcement>
- SQLite WAL：<https://www.sqlite.org/wal.html>（本次讀到的是官方文件原始碼的鏡像：<https://www.sqlite.org/docsrc/artifact/c89f81aeeef8bda1>）
- SQLAlchemy 下載與授權：<https://www.sqlalchemy.org/download.html>
- Vite 指南（Node 需求）：<https://vite.dev/guide/>
- Node.js 發布時程：<https://nodejs.org/about/releases/>
- React 19.3 發布：<https://react.dev/blog/2026/09/09/react-19-3>
- SvelteKit 單頁應用模式：<https://svelte.dev/docs/kit/single-page-apps>
- htmx 2 SSE 擴充：<https://v2.htmx.org/extensions/sse>；htmx 4 SSE（寫法不同）：<https://four.htmx.org/docs/extensions/sse>

第三方或追蹤系統（只作旁證）：

- Django 串流相關 ticket：<https://code.djangoproject.com/ticket/34752>、<https://groups.google.com/g/django-updates/c/KdTnG9mFrnM/m/-FCo9wlcCAAJ>
- FastAPI 沒有內建 CSRF 的佐證（第三方套件與舊 issue）：<https://pypi.org/project/starlette-csrf>、<https://lightrun.com/answers/tiangolo-fastapi-built-in-csrf-protect>
- FastAPI 加入 OpenTelemetry 的時間（2026-09 底）：<https://releasebot.io/updates/tiangolo>
