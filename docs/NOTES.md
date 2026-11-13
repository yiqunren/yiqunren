# 交接筆記（2026-11-12，規格側 session 收尾）

這份筆記記的是還沒寫進其他文件的待辦，讓換 session 後可以接得上。正式的決策與需求以 `docs/SPEC.md` 為準，匯入紀錄在 `PROVENANCE.md`，隔離與 Git 規則在 `CLAUDE.md`。

## 主線狀態

- 決策與需求：`docs/SPEC.md`（第 1 節名稱、授權與收費方式，FR-1、FR-3、FR-9、NFR-7，第 7 節待決事項）。
- 轉接器登記處（NFR-7）已實作並 commit（`b8012aa`）。
- 截至 2026-11-13：`main` 與 `origin/main` 同步、工作區乾淨，`pytest` 結果 249 passed。目前只有協定與本機元件，還沒有網頁介面、資料庫與實際呼叫各家 CLI 的橋接程式。
- 建議的下一步：先定 SPEC 第 7 節第 5 項（技術選型），再做一條最小的端到端路徑（FR-2 私聊，先只接 Codex），之後接 Grok，最後做 FR-3 群聊。這是建議，不是決定。

## 尚未寫進其他文件的待辦

1. 產品名稱 Yiqunren（議群人）已初步自查（2026-11-12）：USPTO 的 `yiqunren` 全類別無紀錄；智慧局 009／042 類無相同或近似；GitHub、PyPI、npm 名稱無人使用。商用或申請註冊前，仍需請商標代理人正式檢索，並考慮註冊。
2. GitHub 組織 `yiqunren` 已建立（2026-11-12），repo 現在位於 `yiqunren/yiqunren`（`origin` 已指向它）。常見網域是否可用還沒查。
3. 舊專案的公開候選資料夾裡，有 Codex 生成的 SVG 素材與 `scripts/build_public_assets.py`，列為之後的候選。這要由規格側 session 照 `CLAUDE.md` 的匯入規則審查；在本 repo 工作的實作側 session 不可自己去讀舊專案。
4. 各家 AI 服務 API 的支援地區還沒查。
5. repo 公開與機密掃描現況（2026-11-13 查）：
   - repo 目前是 PUBLIC。`CLAUDE.md` 規定先 private、做完機密掃描再公開；它是何時、怎麼變成 public 的沒有查到。
   - GitHub 端的 secret scanning、push protection、Dependabot 全部是 disabled，所以 GitHub 沒有掃描紀錄。是否開啟尚未決定（開啟會改外部設定，需擁有者同意）。
   - 本機 gitleaks 8.30.0：掃 Git 歷史（16 個 commit）沒有發現機密。掃工作目錄會在 `tests/__pycache__/*.pyc` 報 4 筆，是 `tests/test_host_diagnostics.py` 那 3 筆假值的編譯副本；`__pycache__/` 已被 `.gitignore` 排除，不會進 Git。
   - 歷史與 commit message 沒有舊專案的私人目錄名稱；所有 commit 的作者與提交者都是 noreply 地址；歷史裡的 `/home/` 都是佔位或測試用假路徑。
   - 沒涵蓋：只比對了 `.claude/settings.local.json` 列到的目錄名稱，舊專案若有其他私人名稱（例如舊產品名）沒有清單可比對。
   - `CLAUDE.md` 隔離規則提到上游專案名稱 AgentsOffice、AgentFleet，已隨 repo 公開；要不要保留由擁有者決定。

## 全域設定變更

- 擁有者的 `~/.gitconfig` 加了 gh 的 credential helper（`github.com`、`gist.github.com`），讓 https 推送走 gh 登入。
- 撤銷指令：
  ```
  git config --global --unset-all credential.https://github.com.helper
  git config --global --unset-all credential.https://gist.github.com.helper
  ```

## 仍待決定

- `docs/SPEC.md` 第 7 節第 5 項：技術選型（後端語言、資料庫、前端框架）。
- `docs/SPEC.md` 第 7 節第 6 項：美術素材來源（只有做 FR-11 才需要）。
- 開始收費前要向原廠確認的事項：見 `docs/SPEC.md` 第 7 節第 4 項。
- 是否開啟 GitHub 的 secret scanning 與 push protection（見上方待辦第 5 項）。
- 是否補更多舊專案私人名稱來比對 Git 歷史（見上方待辦第 5 項）。
- `CLAUDE.md` 提到上游專案名稱那一句要不要保留（見上方待辦第 5 項）。
