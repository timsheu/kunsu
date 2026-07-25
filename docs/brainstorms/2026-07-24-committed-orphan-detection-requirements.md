---
date: 2026-07-24
topic: committed-orphan-detection
---

# 投遞檔已 commit 漏收偵測（遺漏提醒）— 需求

## Summary

新增一支三信箱共用的獨立偵測腳本，找出「已被 commit、卻仍留在頂層未歸檔」的投遞檔——即 auto-commit 摧毀「未 commit 即新件」訊號後的靜默漏收——當成**自成一類的遺漏提醒**，在 `/kunsu-inbox` 軍師模式與軍師沙盤兩處**續行列出**，不比照 tripwire 硬停。現有三支 `scan-*.sh` 零改動。

---

## Problem Frame

kunsu 三信箱以「未 commit 即新件」為狀態訊號（見 [ADR 009](../adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md)）。若使用者環境有 auto-commit（PostToolUse／Stop hook，或全域規範主動 commit）把投遞檔誤 commit，這個訊號會被摧毀。

三支掃描腳本 `skills/kunsu-inbox/scripts/scan-replies.sh`、`scan-applications.sh`、`scan-reports.sh` 結構完全同構，全部基於 `git status --porcelain -uall`——已 commit 且無修改的檔案不出現在 porcelain 輸出，對三支一律隱形。軍師沙盤的軍師視角 `skills/kunsu-dashboard/app/kunsu_scan.py` 直接呼叫這三支腳本，故同樣漏。結果是軍師**靜默漏收**：不報錯，只是掃不到。

目前唯一不受影響的是沙盤子專案視角 `skills/kunsu-dashboard/app/subrepo_status.py`——它以檔案系統 glob 讀檔，reply 被 commit 也照樣顯示到 done。但它只覆蓋交接回覆（replies），applications 與 reports 無任何安全網，被 commit 即從所有視角消失。

本需求為**預防性**：目前開發者環境無 auto-commit、未實際發生漏收，面向未來公開給其他使用者的情境。

---

## Key Decisions

- **定位為 MVP 落地、保留升級路。** 先做最小可用的偵測告警，但設計不堵死日後長成「穩健訊號機制」（讓「新件」判斷本身不依賴 commit 狀態，比照 `subrepo_status.py` 的檔案系統基準）。

- **三信箱對稱做齊，不 replies-first。** 三支腳本同構、偵測邏輯可參數化共用，邊際成本低；且 applications／reports 比 replies 更裸（無子專案視角安全網），一併補上才無盲點。

- **語意是遺漏提醒，不是安全告警。** 「已 commit 漏收」偵測到的是**內容合法**的投遞檔（只是被誤 commit），與 tripwire（未 commit 的越界寫入）恰為鏡像。因此續行列出、不套用 tripwire 的 exit 2 硬停，且自成一類、不混入一般新件。

- **偵測落點為獨立腳本、三信箱參數化共用。** 現有三支 `scan-*.sh` 零改動，porcelain「新件」與 tripwire 邏輯完全不變，風險隔離。獨立腳本天然滿足「自成類別、獨立 exit 0」，且引入的「檔案系統存在性偵測」能力為未來升級路預留。

- **偵測範圍不對稱（正確性約束）。** replies 偵測 `docs/handoffs/replies/` 子目錄的回覆檔；applications／reports 偵測各自頂層 `.md`。**交接本體不偵測**——`docs/handoffs/` 頂層交接文件是軍師自建、`/handoff add` 後 commit 屬正常，若當漏收偵測必然誤報。

- **孤兒 reply 歸同一桶、不細分。** 對應交接已 done 歸檔、回覆卻遺留 `replies/` 頂層且已 commit 的孤兒 reply，與一般漏收件一併列入遺漏提醒，MVP 不細分為獨立的「歸檔未清」類別。

---

## Requirements

**偵測核心**

- R1. 新增一支獨立偵測腳本，接受信箱目錄參數，找出該信箱「已被 git 追蹤／已 commit 且無 porcelain 變更」、卻仍留在頂層未歸檔的投遞 `.md` 檔，以自成一類的前綴輸出遺漏提醒清單。
- R2. 腳本以正常結束碼（exit 0）回傳，**不**觸發現有 tripwire 的 exit 2 語意；偵測結果與 tripwire、一般新件三者在輸出上可清楚區分。
- R3. 三信箱（replies／applications／reports）共用同一支腳本，以參數化目錄達成，不為每個信箱各寫一份。
- R4. 現有三支 `scan-*.sh` 零改動——porcelain 的「新件」偵測與 tripwire 判定行為不變。

**偵測範圍與豁免**

- R5. replies 偵測範圍為 `docs/handoffs/replies/` 頂層回覆檔，**排除** `docs/handoffs/` 頂層交接本體（軍師自建、commit 為正常狀態）。
- R6. applications 偵測 `docs/applications/` 頂層 `.md`、reports 偵測 `docs/reports/` 頂層 `.md`。
- R7. 三信箱一律排除 `archive/` 子目錄與 `.gitkeep`（比照現有 `scan-*.sh` 的既有豁免）。
- R8. 孤兒 reply（對應交接已 done）與一般漏收件歸入同一遺漏提醒清單，不做「是否已 done」的交叉分類。

**呈現**

- R9. `/kunsu-inbox` 軍師模式輸出遺漏提醒，與新回覆／新申請／新上報並列但自成一類；掃描續行、不硬停。
- R10. 軍師沙盤呈現遺漏提醒，續行、自成一類的視覺樣式（不混入既有新件或 tripwire 樣式）；沙盤軍師視角掃描（`kunsu_scan.py`）納入此偵測結果。

---

## Scope Boundaries

- **穩健訊號機制重構（延後）** — 讓軍師視角的「新件」判斷本身改用檔案系統存在性、不依賴 commit（brainstorm 中的「方案 3」）。本輪只做偵測告警，但獨立腳本刻意不堵死這條路。
- **孤兒 reply 細分（延後）** — 另立「歸檔未清」類別、與「漏收待處理」區分呈現。
- **安裝 gate 與 pre-commit 硬阻斷（不在本輪）** — 對話早期評估過的「手段 A」（`install.sh` 掃環境 auto-commit 風險）與「手段 B」（軍師 repo pre-commit hook 硬擋），本輪只做偵測告警一途。
- **修復自動化（不做）** — 偵測只提示，不自動撿回或代為歸檔，維持 kunsu「偵測不強制、閘門留給人」的一貫哲學。

---

## Dependencies / Assumptions

- **假設：正常流程下頂層投遞檔恆為未 commit。** 投遞方不 commit、軍師彙整不 commit，要到授權歸檔（`git mv` 至 `archive/`）＋確認 commit 才一起發生。故「已 commit ＋仍在頂層未歸檔」在正常流程下不存在，必為異常——判定乾淨。此前提已由三支 `scan-*.sh` 的設計與投遞檔生命週期佐證。
- **依賴：偵測需要 git 追蹤狀態維度。** 判定「已 tracked／已 commit」需 `git ls-files` 或等價手段，與現有純 porcelain 掃描是不同維度。
- **假設：預防性需求。** 目前無實際漏收案例；觸發風險的是「主動 auto-commit 軍師 repo 工作樹」的環境，Claude Code harness 預設本不主動 commit。

---

## Success Criteria

- 三信箱任一存在「已 commit ＋頂層未歸檔」投遞檔時，`/kunsu-inbox` 與軍師沙盤皆以自成一類的遺漏提醒列出，且不硬停、不將交接本體誤報為漏收。
- 現有掃描行為（一般新件、tripwire）零回歸——既有 pytest 全數維持通過。
- 新增偵測有對應 pytest 覆蓋：三信箱各一、`archive/`／`.gitkeep` 豁免、孤兒 reply 納入、交接本體不誤報。

---

## Outstanding Questions

**Deferred to Planning**

- 是否為此變更出 ADR。kunsu 慣例每個狀態機語意改動皆出 ADR（本次新增「遺漏提醒」這一類掃描面概念），傾向出一份 ADR candidate，實際於 `/ce-plan` 定案。
- 獨立腳本命名、輸出前綴字串、沙盤樣式的 CSS class 前綴、`KunsuScanResult` 新欄位、`/kunsu-inbox` SKILL.md 呈現段落措辭——實作細節，交 `/ce-plan`／`/ce-work` 決定。
- 遺漏提醒是否納入沙盤頁首全域總覽列與軍師分組摘要計數（比照未接手／tripwire 計數），或僅在軍師分組內呈現。

---

## Sources / Research

- `skills/kunsu-inbox/scripts/scan-replies.sh`、`scan-applications.sh`、`scan-reports.sh` — 三支同構、porcelain-based，已 commit 檔隱形的根因。
- `skills/kunsu-dashboard/app/kunsu_scan.py` — 軍師視角，直接呼叫三支腳本，故同樣漏收。
- `skills/kunsu-dashboard/app/subrepo_status.py` — 子專案視角，檔案系統 glob，既有部分安全網（僅覆蓋 replies）。
- [ADR 009](../adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md) — 「未 commit 即未處理」狀態機與確認 commit 的投遞端不對稱。
- `CONCEPTS.md` — Tripwire、未 commit 即未處理、授權歸檔的權威定義。
