---
title: ADR Candidate 002 — 傳令自動化：全域反向註冊表＋/inbox；SessionStart hook 第二階段；MCP 延後
date: 2026-07-06
type: adr
status: accepted
---

# ADR 002：傳令自動化採全域反向註冊表＋/inbox

> 狀態：**Accepted**（2026-07-06 經兩輪 doc-review 後由使用者審定）。

> **更名註記（2026-07-06）**：本文所稱 `/inbox`／`/init-planner`／`planner-registry.json`，於 rebrand 後對應 `/kunsu-inbox`／`/kunsu-init`／`kunsu-registry.json`，決策本文維持歷史原貌。見 [ADR 004](2026-07-06-adr-004-rebrand-kunsu.md)。

## Context

規劃中心模式的現行人工介入，拆解後分為可自動化的「傳令」（轉送 handoff 路徑、通知回覆抵達）與必須保留的「審核／調度」（核准方案、驗收查核、決定動工時機）。架構上的缺口是反向索引：中心知道所有子 repo 路徑，子 repo session 不知道哪些中心管到它。

已知的既有陷阱：全域 `/handoff reply` 以工作目錄往上找 CLAUDE.md 定位專案根，子 repo session 未先 `cd` 到中心目錄就會把回覆寫進錯誤的 repo，且不報錯（見 ebook 中心 `docs/solutions/conventions/cross-repo-handoff-reply-inbox-convention.md`）。

## Decision（proposed）

1. **全域反向註冊表** `~/.claude/planner-registry.json`：以子 repo 絕對路徑為鍵，值為其隸屬的規劃中心與角色清單。由 `/init-planner` 與 `add-project` 維護，機器特定、不進任何 git repo。角色字串以規劃中心 CLAUDE.md 關聯專案表為唯一來源——註冊表 `role` 欄位與所有 handoff `to:` 值必須與其字面一致；`/init-planner` scaffold 時初始填入，`add-project` 更新時同步核對。
2. **`/inbox` skill**（按需觸發，第一階段）：
   - 子 repo session：查註冊表 → 掃描中心 `docs/handoffs/` 中 `to:` 為本角色且未完成的交接文件 → 列出待接手清單，並一併顯示規劃中心絕對路徑，提示接手方以該路徑直接建立回覆檔案（消除絕對路徑備案中「路徑靠人工傳達」的限制）。掃描時若發現任何 `to:` 值不屬於註冊表中本 repo 已知角色字串集合，附加回報「N 份交接文件的 `to:` 值與註冊表角色不符」並列出清單，提示核查拼寫或以 `add-project` 同步更新——避免拼寫不一致造成待接手項目靜默漏列。
   - 規劃中心 session：以 `git status --porcelain` 掃描 `docs/handoffs/replies/` 中尚未 commit 的新檔案——行首兩字元為 `??`（untracked），或 XY 狀態碼的 X（index 欄）為 `A`（同時涵蓋 `A ` 已暫存與 `AM` 暫存後再修改）——回報「收到 N 份新回覆」；git 的「尚未 commit」狀態即「未處理」標記（已暫存者同樣視為未處理），同時完成 tripwire 範圍核對。
   - 完成狀態由回覆檔推導（`in_reply_to` 對應之最新回覆的 `status`），不修改不可變的 handoff 本體。
   - 執行模式偵測：以「當前 repo 根路徑」為唯一比對基準，獨立評估兩種身分——①根路徑存在於註冊表鍵集合→具子 repo 身分；②根路徑為註冊表值中任一規劃中心路徑→具規劃中心身分。兩者皆符合（巢狀拓撲：本身是規劃中心、又是上層中心的子 repo）→合併執行兩種模式的輸出；僅符合其一→執行對應模式；皆不符合→報錯，提示以 `/init-planner` 或 `add-project` 完成登記。不以目錄存在與否（如 `docs/handoffs/replies/`）作為判斷依據——任何執行過 `/handoff reply` 的一般 repo 都有該目錄，會造成誤判。
3. **SessionStart hook 為第二階段**：同一支檢查腳本改為 session 啟動時自動注入提示。是否採用，待 `/inbox` 實際使用後再決定。
4. **MCP 明確延後**：僅當出現「跨機器協作」或「需讓無法執行 Claude hooks／skills 的 agent 型別化存取信箱」兩訊號之一才重啟評估。
5. **人工閘門不動**：`/inbox` 只告知不開工；彙整由使用者下令；產品取捨與驗收照舊 AskUserQuestion。
6. **全域 `/handoff` skill 升版另行決策**：`/handoff reply` 是否改為查詢註冊表定位規劃中心（以根治 cd 陷阱），涉及全域資產異動與對非規劃中心專案的相容性（含註冊表查無路徑時的 fallback 設計），列為獨立決策點，延後至本工具完成首輪實際使用後再評估。在此之前，cd 陷阱沿用既有緩解（見 Alternatives 的絕對路徑備案）。

## Consequences

- **正面**：傳令成本從「口述長路徑」降為一次 `/inbox`（第二階段可降為零）；註冊表為根治 `/handoff reply` cd 陷阱提供前提條件——一旦全域 `/handoff` skill 升版改查註冊表定位中心，即不再依賴工作目錄推導，惟該升版為獨立延後決策（見 Decision 第 6 項），不在本次交付範圍；不引入常駐 process；「不主動輪詢」的協議精神不變。
- **負面／限制**：註冊表是新的全域狀態，repo 搬家需同步更新（緩解：`/init-planner` 寫入初始條目、`add-project` 維護後續更新（含路徑搬遷），且 `/inbox` 查無路徑時應報錯提示修復）；uncommitted-as-unprocessed 依賴「規劃中心彙整時才 commit 回覆」的既有慣例，若使用者提前 commit 會失去標記（已暫存未 commit 者仍可偵測；緩解：skill 文件明載此前提）。

## Alternatives considered

- **MCP server**：解決傳輸層（信箱已是檔案，不缺）而非觸發層；session 不會自主呼叫工具，通知問題依舊。延後。
- **fswatch／daemon 輪詢推播**：違反協議「不主動輪詢」設計，且 session 非常駐，推播無處落地。否決。
- **在子 repo CLAUDE.md 加提示區塊**：重蹈 ce-team 注入耦合。否決（違反 ADR Candidate 001）。
- **絕對路徑備案（既有 Method 2）**：接手方以規劃中心的完整絕對路徑直接建立回覆檔案，完全不依賴工作目錄推導；已在 ebook 慣例文件落地、目前可用。限制：每份 handoff 需預埋絕對路徑，且路徑仍靠人工傳達。不否決——在全域 `/handoff` skill 升版決策（Decision 第 6 項）落定前，持續作為 cd 陷阱的現行緩解；註冊表方案為其升級替代。

## Deferred / Open Questions

### From 2026-07-06 review

- **角色改名的追溯修復機制**：規劃中心 CLAUDE.md 關聯專案表改名角色後，`add-project` 可同步更新註冊表 `role` 欄位，但已落地 handoff 的 `to:` 值不會被追溯修正——舊角色名的未完成交接將因精確字串比對而從 `/inbox` 靜默消失。候選方向：改名時批次修復既有 handoff、僅掃描警告（Decision 第 2 項的不符回報可部分緩解）、或約定角色名不可變。屬多解判斷，待實作或首輪實際使用時決定。（adversarial reviewer，Round 2）
