# 來源紀錄（PROVENANCE）

本檔記錄所有從其他來源帶進本 repo 的檔案。本 repo 自己新寫的檔案不列在這裡。第三方素材與套件記在 `THIRD_PARTY_NOTICES.md`。

各小節記的是**匯入當時**的狀態：替換清單裡的新名稱與「匯入後 SHA-256」都是匯入那一刻的值。之後在本 repo 的修改不回頭改這些紀錄，以 Git 歷史為準。

匯入後的修改：
- 2026-11-12：產品定名為 Panelroom，所以把匯入時替換成的暫定名稱再改一次。
  - 環境變數前綴：`AIOFFICE_` → `PANELROOM_`
  - 狀態目錄名：`ai-office` → `panelroom`
  - 程式內部識別字裡的 `office` 一起改成 `panelroom`：
    - contextvar 名稱：`panelroom_worker_turn`、`panelroom_turn_timeout`、`panelroom_turn_processes`
    - 程序物件屬性名：`_panelroom_output_tails`
    - 測試的暫存目錄前綴與假持有者名稱
  - 影響的檔案共六個：`app/services/write_ownership.py`、`app/services/worker_turn.py`、`scripts/host_diagnostics.py`、`scripts/private_cli.py`、`tests/test_write_ownership.py`、`tests/test_host_diagnostics.py`。這六個檔案現在的 SHA-256 和各小節記的「匯入後 SHA-256」不同。
- 2026-11-12：實作 SPEC NFR-7 的轉接器登記處（新檔 `app/services/adapters.py`，本 repo 自寫，不列在本檔）。寫死的轉接器清單改成從登記處取得：
  - `app/services/turn_contract.py`：移除 `PROVIDERS`、`FIELD_KEYS`；`claude_code_api` 不再算獨立一家（API key 是 `claude_code` 的認證模式）。`turn_begin` 加上 `auth_mode`，`TURN_PROTOCOL` 升為 2，fields 依認證模式而定（`max_budget_usd` 改為 `claude_code` API key 模式的專屬欄位）。
  - `scripts/turn_host.py`：提供者檢查改查登記處；橋接的 `validate` 回呼多收 `auth_mode`。
  - `app/services/dispatch_context.py`：移除 `WORKERS`（`dispatch_context.py` 小節備註提到的寫死三家已處理）。
  - `app/services/dispatcher_guidance.py`：`WORKER_CAPABILITIES` 改成 `worker_capabilities()`；提示詞的工作者清單與模型等級由登記處產生。
  - `app/services/discussion_contract.py`：`SPEAKERS`、`ORDER`、`NAMES`、`MAX_CALLS`、`PACKET_HOSTS` 改成依登記處計算的函式；發言者與順序依本場參與名單計算（SPEC FR-3，2N+3 格），有選名單的場次封包帶 `participants`；`CLAUDE_HOST_FORMAT` 改名為 `PROMPT_HOST_FORMAT`；主持人預設順序改為登記順序，主持人設定可為有順序的代號清單，未登記代號一律拒絕。
  - `app/services/worker_turn.py`：`LABELS` 改成 `label()`；`socket_path()` 改由登記處決定（`worker_turn.py` 小節備註提到的橋接模組 import 已移除）；`run()` 多收 `auth_mode`。
  - `scripts/host_diagnostics.py`：錯誤分類改依登記的規則；未登記的代號不寫診斷檔。
  - `tests/test_discussion_contract.py`：預設順序改為 Codex、Grok、Claude Code，顯示名稱 Claude → Claude Code，主持人預設改為登記順序，`typo` 由退回預設改為拒絕。
- 2026-11-12：只改註解與說明文字，不影響行為。
  - `scripts/turn_host.py`：模組說明與 `EndedBeforeWork` 說明裡提到尚未匯入的 `_run_codex`／`_run_claude`／`_run_request`、`claude_host_bridge._no_work_done`，改成不指名這些橋接內部名稱。
  - `app/services/discussion_contract.py`：`_host_json` 說明改成依 `host_output="prompt"` 描述，不寫死 Claude。
- 2026-11-12：產品名稱由 Panelroom 改為 Yiqunren（SPEC 第 1 節），所以再改一次名稱。
  - 環境變數前綴：`PANELROOM_` → `YIQUNREN_`
  - 狀態目錄名：`panelroom` → `yiqunren`
  - 程式內部識別字裡的 `panelroom` 一起改成 `yiqunren`：
    - contextvar 名稱：`yiqunren_worker_turn`、`yiqunren_turn_timeout`、`yiqunren_turn_processes`
    - 程序物件屬性名：`_yiqunren_output_tails`
    - 測試的暫存目錄前綴與假持有者名稱
  - 影響的匯入檔案同上一次改名的六個：`app/services/write_ownership.py`、`app/services/worker_turn.py`、`scripts/host_diagnostics.py`、`scripts/private_cli.py`、`tests/test_write_ownership.py`、`tests/test_host_diagnostics.py`。
- 2026-11-14：寫入權登記庫的預設位置，從 repo 底下的 `data/write-ownership/registry.sqlite3` 改到狀態目錄的 `write-ownership.sqlite3`（和後端資料庫同一個目錄；技術選型報告第 4 節）。`YIQUNREN_WRITE_REGISTRY` 仍可覆寫。
  - `app/services/write_ownership.py`：`DEFAULT_REGISTRY` 常數改成 `default_registry()`，狀態目錄由 `app/web/config.py` 的 `resolve_state_dir()` 決定，找不到時丟 `OwnershipError`；`configured_registry()` 可傳入環境變數，`YIQUNREN_WRITE_REGISTRY` 設成空字串視同沒設；`WriteRegistry` 的路徑改為必填。
  - `scripts/turn_host.py`：模組說明裡的登記位置跟著改，不影響行為。
- 2026-11-15：預設登記加入第四家 Claude（API）（SPEC NFR-7），群聊名單與格位數會跟著登記處變。
  - `tests/test_discussion_contract.py`：加上自動套用的 fixture，用測試專用的登記資料（Codex、Grok、Claude Code 三家）跑本檔全部測試；發言者參數化改用同一份三家清單。斷言都沒有改（SPEC NFR-7 驗收條件允許測試改用自己的登記資料）。

## 第一批共同事項（2026-11-12）

- 來源：舊專案（私人），commit `10b047d9bdb05115272bcedaaa27d54264d3e94d`。匯入時該檔案與 commit 內容相同（沒有未 commit 的改動）。
- 「新增」檢查方法：上游基準 `8d20ff5` 用 `git cat-file -e 8d20ff5:<舊路徑>` 查無此檔；基準之後的 283 個 commit 都由擁有者提交，沒有 merge，也沒有偵測到改名或複製（`git diff -M50% -C50% --diff-filter=RC`）。
- 「獨立」檢查方法：解析 import 並遞迴追查，確認沒有直接或間接 import 上游基準裡的任何檔案；與上游基準全部程式檔做行重疊比對（去除空白後長度 30 字元以上、排除 import 與註解行）。另外人工逐檔閱讀，確認沒有透過傳入物件依賴上游資料模型。
- 補充（2026-11-12）：第一次審查只看了模組開頭的 import，漏掉函式裡的延遲 import。之後用 AST 掃描全部層級的 import，本批只有兩個檔案依賴尚未匯入的模組：`app/services/worker_turn.py`（各家橋接）與 `app/services/discussion_contract.py`（`dispatcher_guidance`），兩者都已在各自小節記錄。
- 「乾淨」檢查方法：掃描個人路徑、帳號、私人專案名稱、外接磁碟路徑、舊產品名與舊環境變數前綴。掃描範圍是匯入後的檔案。
- 匯入後驗證：11 個檔案以 Python `compile()` 檢查語法都通過；`scripts.turn_host`、`app.services.worker_turn`、`scripts.write_ownership`、`scripts.host_diagnostics` 可以 import；寫入權命令列在暫存登記庫實測，申請、衝突拒絕、釋放三種情況都符合預期。
- 擁有者同意：2026-11-12

## app/services/write_ownership.py

- 來源：舊專案 `app/services/write_ownership.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：替換
- 替換清單：
  - L23，舊產品名（環境變數前綴）→ `AIOFFICE_WRITE_REGISTRY`
- 原檔 SHA-256：`d5dbb9cfcd7240a11d519070ec826fc23e4f4aaf59866abee0bf91bd4d8408c7`
- 匯入後 SHA-256：`8d3e49b2b9a56b206cc792515ae7e41fcd58e2788c5a13e9e0f81cbd4673741e`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：替換後掃描無命中
- 擁有者同意：2026-11-12

## scripts/write_ownership.py

- 來源：舊專案 `scripts/write_ownership.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：整檔複製
- 替換清單：無
- 原檔 SHA-256：`aae9d5b088d799079c247980942173d1dd93bbc5e38000c12ad5087bc2325a41`
- 匯入後 SHA-256：`aae9d5b088d799079c247980942173d1dd93bbc5e38000c12ad5087bc2325a41`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 標準庫與本批的 `app/services/write_ownership.py`；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12

## scripts/workspace_fingerprint.py

- 來源：舊專案 `scripts/workspace_fingerprint.py`，首次加入於 `2e8e2f6`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：模組說明第 6 行末尾一句指向舊專案內部設計文件的參照
- 替換清單：無
- 原檔 SHA-256：`f211848d6171ee60f596fb1a25f91aad2c95dc9f61443f1b25fd56e17f55484d`
- 匯入後 SHA-256：`a91ad1e06704ada09459af08bbe3f1aa41b8617f7556a68f38b1bf2045ced367`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12

## app/services/turn_contract.py

- 來源：舊專案 `app/services/turn_contract.py`，首次加入於 `9478fb4`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：模組說明第 4 行末尾一句指向舊專案文件的參照
- 替換清單：無
- 原檔 SHA-256：`7280ea1ea096378cb17cae0e22e5bcd0b7399b2f462e5ab012014602ae230803`
- 匯入後 SHA-256：`3565b89186ba11564bb4047f4996b52c7108c4ddf81be271e33c32c77ea60d4e`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：提供者名稱與欄位寫死在 `PROVIDERS`／`FIELD_KEYS`，之後要另開一筆改動，改成可設定

## scripts/turn_host.py

- 來源：舊專案 `scripts/turn_host.py`，首次加入於 `9478fb4`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：模組說明第 13 行末尾一句指向舊專案文件的參照
- 替換清單：無
- 原檔 SHA-256：`9470f51acb3cd9ca48e2eb108b206cc1d3c99f50df5878e80e0002a2bed19b99`
- 匯入後 SHA-256：`dd3ea83da8734649fcaf1b382aac129c6258952565b4aaeebd44df9add4a1fd0`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 標準庫與本批檔案；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：說明文字仍提到 `claude_host_bridge`、`project_build` 等尚未匯入的模組名稱，只是說明，不影響執行

## scripts/private_cli.py

- 來源：舊專案 `scripts/private_cli.py`，首次加入於 `ddc597b`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：舊同步路徑用的 `env_path()`、`TIMEOUT_MIN`／`TIMEOUT_MAX`（30～840 秒）與 `env_seconds()`（原第 53～76 行）；本批其他檔案沒有引用
- 替換清單：無
- 原檔 SHA-256：`a53db5c2c76b8bcad1cd6195c79175df175077eb5d6cbc8bf032644363dd1ef4`
- 匯入後 SHA-256：`044622a545dbe9c59af501cadbfa586785266e116a04697dc99290c37fd50fe9`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 標準庫與本批的 `scripts/discussion_host.py`、`scripts/host_diagnostics.py`；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：程序身分核對依賴 Linux 的 `/proc`，只能在 Linux 或 WSL 上執行

## app/services/cli_socket.py

- 來源：舊專案 `app/services/cli_socket.py`，首次加入於 `7bc7ea9`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：舊相容開關 `progress_requests_enabled()`、舊同步逾時 `TURN_TIMEOUT_*` 與 `turn_timeout()`，以及從 `discussion_contract` 轉出的 `public_usage`（原第 21～45 行）；本批其他檔案沒有引用
- 替換清單：無（被刪的段落裡原本有舊環境變數前綴，刪除後已不存在）
- 原檔 SHA-256：`4888d04b6a335d2c8e47e0c03fbf7abb3c26d4e2a4741217ea8a5964201a2305`
- 匯入後 SHA-256：`69cd126b16166edcc876710005fd56b300729a69b29a33e20ccdbc65759c7248`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12

## app/services/worker_turn.py

- 來源：舊專案 `app/services/worker_turn.py`，首次加入於 `9478fb4`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：模組說明第 3 行（舊同步路徑的相容說明）與第 4 行末尾的文件參照；舊相容開關 `enabled()`（原第 39～41 行）
- 替換清單：無（被刪的段落裡原本有舊環境變數前綴，刪除後已不存在）
- 原檔 SHA-256：`506556354678562ec83fd6eb3ae41707ad59a3596531bd197c9676b102afb4e3`
- 匯入後 SHA-256：`96fe21bf77c860c68601dbeeb19e9974f8c41cd32348bd7976c819bfb7073f94`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：模組層級只 import 標準庫與本批檔案；行重疊 1 行，是 Python 慣用的 `logger = logging.getLogger(__name__)`
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：`socket_path()` 呼叫時會 import 尚未匯入的各家橋接模組（`codex_bridge` 等），目前呼叫會失敗；之後要另開一筆改動，改成從設定讀 socket 位置

## scripts/discussion_host.py

- 來源：舊專案 `scripts/discussion_host.py`，首次加入於 `fbbd415`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：`DiscussionHost` 類別與其後全部內容（原第 92～383 行），只保留程序身分核對相關函式（`process_stat`、`birth_receipt`、`validate_receipt`、`group_ended`、`signal_owned`）和模組常數。做法是取原檔前 91 行。
- 替換清單：無
- 原檔 SHA-256：`f354bf67771f67dcd918c85b1f3106114d0e305a0c69df3419179930292653ba`
- 匯入後 SHA-256：`1479f00cf1fecdeeeaa10b614723258306f804bf78ee8523cecc9d2dcbc21a40`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 標準庫與本批的 `app/services/discussion_contract.py`、`scripts/host_diagnostics.py`；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：import 行仍列出 `DiscussionHost` 用過的名稱（`MAX_REPLY` 等），刪減後未使用，不影響執行。群聊主持類別留到之後的批次另行審查。

## app/services/discussion_contract.py

- 來源：舊專案 `app/services/discussion_contract.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：整檔複製
- 替換清單：無
- 原檔 SHA-256：`89d0c1b4c76b8de8eab0c3b84b6ae6b70cdda6d7cf4d598477d3872ca8fd7885`
- 匯入後 SHA-256：`89d0c1b4c76b8de8eab0c3b84b6ae6b70cdda6d7cf4d598477d3872ca8fd7885`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：沒有直接或間接 import 上游基準的檔案；行重疊 0。更正（2026-11-12）：原本寫「只用標準庫」是錯的。模組開頭確實只 import 標準庫，但第 343 行在主持人封包的組裝函式裡，會延遲 import `app.services.dispatcher_guidance`。這個模組上游基準沒有，但也還沒匯入本 repo；它本身又 import `app.services.consultants.profiles` 與 `app.services.dispatch_context`。
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：本批只需要其中的 `receipt_shape`，因為 `group_ended` 會用到；其餘是群聊協定，之後做群聊時再詳細審查內容。在 `dispatcher_guidance` 匯入以前，組裝主持人封包會失敗；對應測試有 35 個因此失敗（2026-11-12 實測）。第二批匯入這三個檔案後重跑，對應測試全部通過（見第二批共同事項）。

## scripts/host_diagnostics.py

- 來源：舊專案 `scripts/host_diagnostics.py`，首次加入於 `f34aeb9`
- 匯入日期：2026-11-12
- 匯入方式：刪減、替換
- 刪減內容：模組說明第 3 行裡指向舊專案內部審查報告的括號註記
- 替換清單：
  - L6，舊產品名（環境變數前綴）→ `AIOFFICE_DIAG_DIR`
  - L6，舊產品名（狀態目錄名）→ `ai-office`
  - L7，舊產品名（狀態目錄名）→ `ai-office`
  - L26，舊產品名（環境變數前綴）→ `AIOFFICE_DIAG_DIR`
  - L65，舊產品名（狀態目錄名）→ `ai-office`
- 原檔 SHA-256：`8fda293ba3c7d6483186c2e92a956e896871bdab51474ece85019b1a291145c6`
- 匯入後 SHA-256：`2be590fc76ce999d9c8a8aff89bd9dddbe447a7cc48124e04a24f2a73d2af01c`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：替換後掃描無命中
- 擁有者同意：2026-11-12

## 第二批共同事項（2026-11-12）

- 目的：補上 `app/services/discussion_contract.py` 第 343 行延遲 import 的依賴鏈：`dispatcher_guidance` → `consultants/profiles`、`dispatch_context`（後者也 import `profiles`）。
- 來源、「新增」與「獨立」的檢查方法和第一批相同，來源 commit 也一樣（`10b047d9bdb05115272bcedaaa27d54264d3e94d`）。這次用 AST 檢查全部層級的 import：三個檔案在本 repo 內只互相依賴，其餘只用標準庫。
- 「乾淨」檢查：方法同第一批，另外加掃上游前端與資料模型的欄位名（`phaser`、`room_id`）。
- 匯入後驗證：
  - `dispatcher_guidance`、`consultants.profiles` 可以 import，`PROFILES` 共 13 位顧問。
  - 刪減的名稱在三個檔案裡已無殘留。
  - 5 個對應測試檔在 scratchpad 的副本（尚未匯入本 repo）重跑 185 個，全部通過，pytest 結束碼 0。
- 套件說明：`app/services/consultants/` 沿用第一批的 namespace package 做法，不帶舊專案的 `__init__.py`（只有一行模組說明）。
- 擁有者同意：2026-11-12

## app/services/dispatcher_guidance.py

- 來源：舊專案 `app/services/dispatcher_guidance.py`，首次加入於 `ddc597b`
- 匯入日期：2026-11-12
- 匯入方式：整檔複製
- 替換清單：無
- 原檔 SHA-256：`4b91521e9ada973c28b84d95b154065712c790cddc35970ec6d244e5bb30f4d8`
- 匯入後 SHA-256：`4b91521e9ada973c28b84d95b154065712c790cddc35970ec6d244e5bb30f4d8`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 本批的 `consultants.profiles`、`dispatch_context` 與標準庫；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：第 156～158 行把模型等級對應寫死了：Codex 對應 Luna／Sol／Astra，Claude 對應 Sonnet／Opus。這是舊專案的設定，之後應改成可設定，和 `turn_contract` 的 PROVIDERS 一起處理。

## app/services/consultants/profiles.py

- 來源：舊專案 `app/services/consultants/profiles.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：
  - 原第 10～11 行：`DEFAULT_MODEL`、`DEFAULT_EFFORT`，只有 `templates()` 用到。
  - 原第 157～165 行：`templates()`，含後面兩行空行。它產生的是舊專案代理名冊的種子資料，帶有上游前端與資料模型的欄位（`phaser_agent_id`、`room_id`、`department`），舊專案裡只有沿用上游的 store 會呼叫它。
- 替換清單：無
- 原檔 SHA-256：`1d555b656cbaac08787907f4257eb21517fdc39c7a98b146a2557ca47c8cbc4b`
- 匯入後 SHA-256：`960371fb6ec2e86b02ea74621e90f176b68e7f0610303e2f30289849bf723736`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只用標準庫；行重疊 0
  - 乾淨：刪減後掃描無命中（刪減前只有第 162 行命中上游欄位名）
- 擁有者同意：2026-11-12
- 備註：13 位顧問的專業規格是內容資產，會出現在提示詞裡；規格雜湊（`digest`）和舊專案的值相同。

## app/services/dispatch_context.py

- 來源：舊專案 `app/services/dispatch_context.py`，首次加入於 `4097b30`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：模組說明第 4 行末尾那句「組裝在 App 端的 dispatch_context_builder。」。它指向的舊專案模組沒有匯入。
- 替換清單：無
- 原檔 SHA-256：`70dce498a1053d756e4006968c563fca57a8ad857618328b757929fd96b7db4d`
- 匯入後 SHA-256：`b941afb697c77a0830a6081916cac6cd1b293f73c3b5b2437a6079a2102165d2`
- 三項檢查：
  - 新增：上游基準沒有此檔
  - 獨立：只 import 本批的 `consultants.profiles` 與標準庫；行重疊 0
  - 乾淨：掃描無命中
- 擁有者同意：2026-11-12
- 備註：`WORKERS` 寫死了三家（codex、claude_code、grok），第 17 行的註解提到舊專案群聊的部署門檻；之後和 providers 可設定化一起處理。

## 第三批共同事項：測試檔（2026-11-12）

- 目的：涵蓋第一、二批模組的對應測試。來源 commit 與「新增」「獨立」的檢查方法同第一批；五個檔案在上游基準 `8d20ff5` 都不存在，歷次提交都由擁有者完成。
- 獨立：只 import 本 repo 已匯入的 `app.services.*`、`scripts.*`、標準庫與 pytest。舊專案的 `tests/conftest.py` 沒有帶進來，因為裡面有 FastAPI 路由工具和舊環境變數的 fixture，留下來的測試也用不到。
- 乾淨：掃描只有兩處命中，都不是問題：
  - `test_discussion_contract.py` 第 161 行替換後的假路徑 `/home/user`
  - `test_write_ownership.py` 第 42 行的測試資料 `docs/a.md`
- 隔離驗證：不設任何 `AIOFFICE_*` 環境變數、把 HOME 指到空的暫存目錄跑全部測試，185 個通過，暫存 HOME 裡沒有產生任何檔案；`~/.local/state/ai-office` 在真實環境跑之前、跑之後都不存在。
- 匯入後驗證：在 repo 根目錄直接執行 `.venv/bin/pytest`，用自寫的 `pytest.ini`（`pythonpath = .`、`testpaths = tests`），結果 185 passed，結束碼 0。
- 擁有者同意：2026-11-12

## tests/test_workspace_fingerprint.py

- 來源：舊專案 `tests/test_workspace_fingerprint.py`，首次加入於 `2e8e2f6`
- 匯入日期：2026-11-12
- 匯入方式：整檔複製
- 替換清單：無
- 原檔 SHA-256：`a4c24110fbf90a1d5458764b09f0015b734692edeac2f72f4eca725a250a2d29`
- 匯入後 SHA-256：`a4c24110fbf90a1d5458764b09f0015b734692edeac2f72f4eca725a250a2d29`
- 三項檢查：新增：上游基準沒有此檔；獨立：見第三批共同事項；乾淨：掃描無命中
- 擁有者同意：2026-11-12

## tests/test_write_ownership.py

- 來源：舊專案 `tests/test_write_ownership.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：替換
- 替換清單：
  - L128，舊產品名（環境變數前綴）→ `AIOFFICE_WRITE_REGISTRY`
- 原檔 SHA-256：`e37b75041403220f92b3d2b41a26a99004d4821ba12b46e3d2b1164a17df145e`
- 匯入後 SHA-256：`caa0954d73c8b0e5b34335675cd8c2c80f049d307cb8604b72f042ef4ff1a798`
- 三項檢查：新增：上游基準沒有此檔；獨立：見第三批共同事項；乾淨：替換後只命中測試資料 `docs/a.md`
- 擁有者同意：2026-11-12

## tests/test_discussion_contract.py

- 來源：舊專案 `tests/test_discussion_contract.py`，首次加入於 `3202f83`
- 匯入日期：2026-11-12
- 匯入方式：替換
- 替換清單：
  - L161，個人家目錄路徑（測試用的不合法 cwd 值）→ `/home/user`
- 原檔 SHA-256：`543d1994e12e553e87c6f9d80a1dc892b87699ab76e1a0e04e5bc4272e4472cc`
- 匯入後 SHA-256：`bed31e08ea6a16a5710b17bba5e2f21906c579f38802591f13dfcf63a4db2f51`
- 三項檢查：新增：上游基準沒有此檔；獨立：見第三批共同事項；乾淨：替換後掃描無命中
- 擁有者同意：2026-11-12

## tests/test_host_diagnostics.py

- 來源：舊專案 `tests/test_host_diagnostics.py`，首次加入於 `f34aeb9`
- 匯入日期：2026-11-12
- 匯入方式：刪減、替換
- 刪減內容：
  - 模組說明第 1 行：去掉指向舊專案內部審查報告的括號註記，以及「三個橋接的失敗路徑」。
  - 模組說明第 3 行：去掉「conftest 已把舊環境變數指到暫存目錄」那句。
  - 第 18 行：從 import 清單移除三支主機橋接（`claude_host_bridge`、`codex_host_bridge`、`grok_host_bridge`）。
  - 原第 277～364 行：刪掉三支橋接失敗路徑的測試和它們的輔助函式，共 5 個測試：`write_cli`、`diag_files`、`codex_cli` fixture，以及 codex 非零結束、codex 逾時、codex 成功不寫檔、claude 解析失敗、grok 非零結束。這些測試要等橋接匯入後才能跑。
- 替換清單：
  - L243、L245、L248，舊產品名（環境變數前綴）→ `AIOFFICE_DIAG_DIR`
  - L247、L250，舊產品名（狀態目錄名）→ `ai-office`
- 原檔 SHA-256：`f717d0b87405c264a6e11efc20d2a07f1859fdb3fb87d453e0a5ac87a336dfc2`
- 匯入後 SHA-256：`8ad0c49ba8bea77acc22191d05caba1ed13dbb1f2da81155f74146e9361f6ef7`
- 三項檢查：新增：上游基準沒有此檔；獨立：見第三批共同事項；乾淨：刪減與替換後掃描無命中
- 擁有者同意：2026-11-12

## tests/test_private_cli_lifecycle.py

- 來源：舊專案 `tests/test_private_cli_lifecycle.py`，首次加入於 `ddc597b`
- 匯入日期：2026-11-12
- 匯入方式：刪減
- 刪減內容：
  - 原第 14 行：三支橋接與 `codex_project_turn` 的 import。
  - 原第 17～117 行：`test_cancelled_private_call_reaps_its_process`，按 4 個 provider × 2 種情況參數化。它依賴橋接和專案回合模組，要等之後的批次。
- 替換清單：無
- 原檔 SHA-256：`6419b4b5385de2b55adedcb41c56ed76d2f9682d60afc66053c08f88ba2b5d3c`
- 匯入後 SHA-256：`b3d5f329763a001437bba0e554f12093524fbb9bb51c5d1cbda26d4467c5cbbf`
- 三項檢查：新增：上游基準沒有此檔；獨立：見第三批共同事項；乾淨：刪減後掃描無命中
- 擁有者同意：2026-11-12
