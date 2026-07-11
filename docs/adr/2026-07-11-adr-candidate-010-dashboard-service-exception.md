---
title: ADR Candidate 010 — kunsu 訊息聚合 Dashboard 對 Invariant 1 的例外
date: 2026-07-11
type: adr
status: accepted
---

# ADR 010：kunsu 訊息聚合 Dashboard 對 Invariant 1 的例外

> 狀態：**Accepted**（2026-07-11 經一輪 doc-review 後由使用者審定）。

## Context

CLAUDE.md Invariant 1 明定「純 skill＋範本，不建編譯型工具」——交付物限定為 markdown 範本、SKILL.md、少量膠水腳本（shell），不建立需要獨立建置、測試、發版的工具專案。[ADR 001](2026-07-06-adr-candidate-001-pure-skill-no-injection.md) 訂定此原則時，在 Alternatives considered 將 MCP server 路線**明確延後**（非否決），理由是「解決傳輸層而非觸發層痛點，且增加常駐 process 與設定負擔」；[ADR 002](2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) 進一步訂出重啟評估 MCP 的訊號（跨機器協作，或需讓無法執行 Claude hooks／skills 的 agent 型別化存取信箱），同樣未當作永久否決處理。

[docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md](../plans/2026-07-11-001-feat-kunsu-dashboard-plan.md)（origin：[docs/brainstorms/2026-07-11-kunsu-dashboard-requirements.md](../brainstorms/2026-07-11-kunsu-dashboard-requirements.md)）提出一個獨立本機 FastAPI 服務，彙整全域反向註冊表裡所有軍師與子專案的 kunsu 訊息狀態，取代逐一切換 CLI 視窗手動執行 `/kunsu-inbox` 的做法。這個工具：

- 引入本專案第一個 pip 依賴（`fastapi`、`uvicorn[standard]`、`PyYAML`）
- 引入本專案第一個常駐 process（使用者手動啟動的本機 HTTP 伺服器）

字面上直接牴觸 Invariant 1，且與 MCP 路線表面相似（兩者都是常駐 process）。本 ADR 評估是否、以及在什麼條件下，允許這個例外——條件必須是可由程式碼直接檢查的技術約束，不能只是意圖聲明，否則無法擋下未來表面相似但實質不同的提案。

## Decision（proposed）

**允許此例外**，條件如下：

1. **例外範圍界定**（缺一則不適用此例外，須回到 Invariant 1 字面規則評估）：
   1. 唯讀查詢工具——不寫入任何被彙整的軍師或子專案 repo；亦不在 `skills/kunsu-dashboard/` 自身目錄以外的任何路徑產生持久性資料（含快取、已讀標記、日誌）。若日後想加入這類寫入或持久化功能（例如「標記已讀」「快取上次掃描結果」），視為新功能提案，須另立 ADR 重新評估，不能直接沿用本例外。
   2. 資料新鮮度由使用者刷新瀏覽器頁面觸發，伺服器本身不跑背景計時器或背景執行緒做定期掃描。
   3. **啟動與停止必須由使用者手動掌握**——不得有 `launchd`、`cron`、或任何其他 skill／排程觸發的自主重啟路徑。
   4. 綁定 `127.0.0.1`，不對外部網路開放，不服務多使用者。
   5. **所有端點僅回傳 `text/html`；不得提供任何 JSON、XML 或其他機器可解析結構化格式的端點，也不建立可供程式化呼叫的 API contract。** 這條把「只服務人類使用者、不是給其他程式呼叫的機器對機器介面」從意圖聲明變成可由程式碼直接檢查的技術條件——不依賴「連線的是瀏覽器還是腳本」這種無法技術性驗證的區分。

   條件 3、5 具備可證偽性：任何提案若需要背景排程／開機自動啟動（違反 3），或提供結構化資料端點（違反 5），即不適用本例外，須回頭走完整的 Invariant 1 例外評估，不能直接援引本 ADR。

2. **與 MCP 路線的機制層級區隔**：MCP 與本工具都引入常駐 process，兩者的差異不能只停留在「使用情境不同」這種立場層級的說法，必須是機制層級、且可驗證的區別：

   | | MCP server（ADR 001／002 明確延後） | 本 dashboard（本 ADR 允許） |
   |---|---|---|
   | 輸出格式 | 結構化資料（JSON-RPC 等），供程式解析 | 僅 `text/html`，供人類閱讀；由 Decision 第 1 項第 5 條強制，非僅意圖聲明 |
   | API contract | 有——MCP 協定本身即定義可程式化呼叫的介面規格 | 無——沒有機器可解析的回應格式，不構成可程式化呼叫的介面 |
   | ADR 002 定義的「觸發層」問題 | 未解決——session 不會自主呼叫 MCP 工具，通知問題依舊；MCP 解決的是傳輸層（信箱已是檔案，不缺存取方式），不是這個問題 | **同樣未解決**——使用者仍須主動開瀏覽器並刷新，沒有任何自主觸發路徑；本工具解決的是另一個問題（人工操作整合：一次刷新涵蓋全部已登記軍師與子專案，取代逐視窗手動查詢），不宣稱解決 ADR 002 所稱的 AI session 自主觸發問題 |

   簡言之：MCP 引入常駐 process 是為了**建立新的機器對機器存取介面**；本 dashboard 引入常駐 process 只是**把既有的人工觸發流程（`/kunsu-inbox`）換一個呈現介面**，且第 1 項第 5 條的 `text/html`-only 約束讓這個區別可由程式碼檢查，不是單憑消費者身分或協定名稱來區分。

3. **未來比照此例外的判斷條件**：其他工具若想援引本 ADR 作為先例，須同時滿足第 1 項的全部五個範圍界定（尤其是第 5 條的 `text/html`-only 技術約束），且第 2 項的機制層級區隔須能同樣清楚地寫出（不是為了新增機器對機器介面，而是既有人工觸發流程的呈現方式改變）。不滿足者一律回到 Invariant 1 字面規則，另立新 ADR 評估，不得直接套用本例外。

## Consequences

- **正面**：使用者不必逐一切換 CLI 視窗手動執行 `/kunsu-inbox`，可用瀏覽器一次看到所有已登記軍師與子專案的訊息狀態；不新增機器對機器的存取介面（由第 1 項第 5 條技術性保證），維持「kunsu 網路只服務使用者本人」的既有姿態。
- **負面／限制**：本專案 skill 目錄下首次出現需要 `pip install` 才能運作的工具，`install.sh` 的 copy／symlink 部署不涵蓋依賴安裝，安裝步驟改為 `SKILL.md` 內的手動指引；此工具的正確性驗證方式（自動化測試）與其餘六個 skill（僅靠 SKILL.md 步驟說明＋人工驗收）不同，多一種需要維護的機制類型；`skills/kunsu-inbox/SKILL.md` 步驟 4a 與 `skills/kunsu-dashboard/app/subrepo_status.py` 兩處各自維護判斷邏輯，若靜默偏差，dashboard 顯示的狀態可能與 `/kunsu-inbox` 不一致且無錯誤訊號提示（緩解：兩處皆有測試覆蓋，SKILL.md 步驟 4a 已加維護提示，但提示是建議性質，不是強制機制）。
- **結構不變量**：本例外僅適用於 `skills/kunsu-dashboard/` 這一個工具，且僅限於第 1 項五條範圍內的行為；不代表 Invariant 1 對「純 skill＋範本」的字面規則整體鬆綁。任何後續工具若要比照，須逐一核對 Decision 第 1、2、3 項全部條件，不得以「先前已經有 kunsu-dashboard 這個先例」作為唯一理由。

## Alternatives considered

- **維持 Invariant 1 字面規則，不做例外，改用純 skill 方案**：已在 [docs/brainstorms/2026-07-11-kunsu-dashboard-requirements.md](../brainstorms/2026-07-11-kunsu-dashboard-requirements.md) 的方案探索階段評估——新增 `/kunsu-dashboard` skill 在 Claude Code session 內產生 HTML，但每次刷新都要開一次 session，違背使用者要「不啟動 AI session 就能看」的核心目標，僅把「六個視窗各查一次」壓縮成「一個視窗查全部」，未真正解決問題。
- **一次性腳本產生靜態 HTML，手動重跑指令＋開啟瀏覽器（無常駐 process、無 pip 依賴）**：brainstorm 對話中曾是第一版方案（方案 A：靜態 HTML＋手動重產指令），完全不牴觸 Invariant 1。使用者其後選擇「常駐網頁、刷新分頁才觸發掃描」，取捨在於：靜態 HTML 版每次要記得回到終端機重新執行指令才能看到新資料；常駐版只需開一次伺服器，之後單純按瀏覽器的刷新鍵即可，操作成本更低、更貼近「隨時瞄一眼」的使用情境。此取捨已於 brainstorm 階段定案，非本 ADR 重新開放。
- **背景排程自動更新（launchd／cron）**：brainstorm 階段使用者選擇先做手動版、將背景自動化留待之後評估（延後決策，非當場否決）。若日後真的採用背景排程，會使本 ADR 第 1 項第 3 條「啟動停止使用者手動掌握」不成立，屆時須另立新 ADR 重新評估，不在本次允許範圍內。
