---
date: 2026-07-11
topic: kunsu-dashboard
---

# kunsu 訊息聚合儀表板

## Summary

一個獨立的本機 FastAPI 網頁，彙整全域註冊表 `~/.claude/kunsu-registry.json` 中所有軍師與子專案的 kunsu 訊息狀態（交接待接手／已回覆、新申請、新上報）。啟動一次伺服器後，每次刷新瀏覽器頁面即即時重新掃描，取代目前得逐一切換 CLI 視窗手動執行 `/kunsu-inbox` 的做法。

## Problem Frame

使用者目前同時維運多個 kunsu 網路（現況 1 軍師＋2 子專案，可能擴充到 2 軍師＋6 子專案），每個都是獨立的 Claude Code CLI 視窗。`/kunsu-inbox` 是手動觸發的 skill，若要知道有沒有新交接、新申請或新上報，得逐一切換到每個視窗手動下指令查詢。

這造成的實際代價不是「別人卡住等你」——上報與交接本身就不承諾即時回應——而是使用者自己的注意力被切割：等真正回頭處理某個視窗時，得重新確認脈絡才能接續。

研究確認 Claude Code 原生 Agent View（`claude agents`）與第三方 claude-view 都只感知 session 執行狀態（工作中／等待輸入／完成），不知道 kunsu 信箱裡的檔案內容；本專案自己的 [ADR 002](../adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) 也已評估並駁回 MCP 路線（信箱已是檔案，不缺傳輸層，缺的是觸發層）。這個缺口目前沒有現成工具能填。

## Key Decisions

- **獨立 FastAPI 本機服務，不掛 Claude Code skill** — 使用者要的是「不開 AI session 就能看」，skill 觸發模式（每次刷新都要跑一次 session）做不到這件事。
- **刷新頁面才即時掃描，不跑背景 worker** — 核心代價是使用者自己脈絡斷掉（不是別人卡住等待），不需要即時推播；手動刷新已足夠，同時避免違反 `/kunsu-inbox` 既有「不主動輪詢」設計原則與本專案 CLAUDE.md Invariant 1（不建置需要獨立維護的服務型架構）。
- **掃描範圍為全域註冊表全部登記，不限於當前開啟的視窗** — 比照既有 `/kunsu-list` 的作法，善用註冊表已知道全部路徑這件事，一次涵蓋所有軍師與子專案，不管當下有沒有開對應的終端機視窗。
- **軍師模式重用既有三支掃描腳本，子專案模式另寫 Python 版本** — 軍師模式（新回覆／新申請／新上報＋ tripwire）直接呼叫既有 `scan-replies.sh`／`scan-applications.sh`／`scan-reports.sh`；子專案模式（交接文件「待接手」／「已回覆待確認」判斷）目前只以 LLM 步驟說明存在於 `/kunsu-inbox` 的 SKILL.md 步驟 4a，需另寫 Python 版本複製同一套邏輯（frontmatter 讀取、回覆比對、日期／n 排序取最新回覆），行為與既有規則保持一致，不重新設計判斷規則本身。

## Requirements

**資料聚合**

- R1. Dashboard 於每次觸發掃描時讀取全域反向註冊表 `~/.claude/kunsu-registry.json`，取得全部登記的軍師與子專案路徑。
- R2. 對每個軍師路徑，重用既有 `scan-replies.sh`／`scan-applications.sh`／`scan-reports.sh` 三支腳本，取得新回覆／新申請／新上報清單與 tripwire 狀態。
- R3. 對每個子專案路徑，以 Python 重新實作 `/kunsu-inbox` 步驟 4a 的判斷邏輯（讀交接文件 frontmatter、比對回覆、取最新回覆狀態），分類為「待接手」／「已回覆待確認」／略過（`status: done`）。

**呈現與刷新**

- R4. 掃描結果彙整為單一網頁，本機瀏覽器開啟後可看到所有軍師與子專案的訊息狀態。
- R5. 資料新鮮度由使用者刷新瀏覽器頁面觸發——每次刷新即同步重新執行 R1–R3 的完整掃描，不使用背景計時器或背景執行緒。
- R6. 伺服器需使用者手動啟動（如終端機下一個指令），不隨開機或既有 Claude Code session 自動啟動。

**安全邊界延續**

- R7. 任一軍師的 tripwire 偵測（沿用既有 scan-*.sh 的 exit code 2 判斷）觸發時，該軍師的區塊須清楚標示異常，不得靜默略過或當作零筆新訊息呈現。

## Acceptance Examples

- AE1. **Covers R3.** 子專案 A 收到一份交接文件，尚無任何回覆 → 網頁在子專案 A 區塊顯示「待接手」。
- AE2. **Covers R3.** 子專案 A 的交接文件最新回覆 `status: submitted` → 網頁顯示「已回覆待確認」。
- AE3. **Covers R3.** 子專案 A 的交接文件最新回覆 `status: done` → 網頁不列出，比照現行 `/kunsu-inbox` 略過規則。
- AE4. **Covers R7.** 軍師 B 的信箱授權範圍外偵測到未預期的未 commit 變更（tripwire）→ 網頁在軍師 B 區塊顯示異常警示，其餘軍師／子專案區塊仍正常顯示。

## Scope Boundaries

**Deferred for later**
- 背景／排程自動刷新（如 launchd／cron）——留待手動版用出實際手感後再評估。

**Outside this product's identity**
- Session 執行狀態總覽（誰在等你、類似 Agent View／FleetView／claude-view）——這是另一個獨立問題，本次研究已明確排除在範圍外，此 dashboard 只處理 kunsu 訊息內容，不處理 Claude Code session 本身的執行狀態。
- MCP-based 方案——本專案 [ADR 002](../adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) 已評估並駁回，不重新開放。

## Dependencies / Assumptions

- 依賴既有 `scan-replies.sh`／`scan-applications.sh`／`scan-reports.sh` 三支腳本的輸出格式（`NEW_REPLY:`／`NEW_APPLICATION:`／`NEW_REPORT:`／`TRIPWIRE:` 前綴行與 exit code 語意）維持不變。
- 依賴全域反向註冊表 `~/.claude/kunsu-registry.json` 存在且為合法 JSON；若檔案不存在或損壞的處理方式比照 `/kunsu-inbox` 既有錯誤訊息設計。
- 假設單一使用者、單機本地執行，僅綁定 localhost，不需要多機器存取或身分驗證。
- 新增 FastAPI／ASGI server 為 pip 依賴，本專案既有腳本已用 python3（`registry-merge.sh`／`registry-list.sh`），但尚未有 pip 套件依賴，此為本專案首次引入。

## Outstanding Questions

**Resolve Before Planning**
- 無。

**Deferred to Planning**
- 子專案模式的 4a 判斷邏輯要不要抽成 SKILL.md 與 Python 腳本共用的單一來源，還是接受兩處各自維護並以測試確保一致——使用者已示意方向未定，留待規劃階段討論。
- Tripwire 異常時的呈現粒度：整頁掃描失敗，還是僅該軍師區塊顯示異常、其餘正常呈現（AE4 假設後者，但對話中未明確定案）。
- 本專案 CLAUDE.md Invariant 1（純 skill＋範本，不建編譯型工具）與這次新增的常駐服務型工具如何共存——是否需要新增或修訂 ADR，正式承認此例外並記錄理由。

## Sources / Research

- [Claude Code Agent View 官方文件](https://code.claude.com/docs/en/agent-view) — `claude agents` 指令，2026-05-11 以 research preview 上線。
- [claude-view](https://claudeview.ai/) — 第三方多 session 儀表板，本地免費、跨機器需訂閱。
- [docs/adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md](../adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) — MCP 路線駁回理由（解決傳輸層而非觸發層）；SessionStart hook 列為延後評估的第二階段。
- `skills/kunsu-inbox/SKILL.md` 步驟 4a — 現行子專案模式判斷邏輯，將作為 Python 版本的來源規格。
- `skills/kunsu-inbox/scripts/scan-replies.sh`、`scan-applications.sh`、`scan-reports.sh` — 軍師模式將直接重用，不重寫掃描本體。
