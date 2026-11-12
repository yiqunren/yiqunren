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

## 開發者：跑測試

需要 Python 3.10 以上。目前只在 Linux（WSL）上測試過。

```bash
git clone https://github.com/yiqunren/yiqunren.git
cd yiqunren
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest
```

除了 pytest，目前沒有其他第三方依賴。

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
