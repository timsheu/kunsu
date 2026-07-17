---
date: 2026-07-17
topic: dashboard-todo-list
---

# 軍師沙盤 todo 列表顯示 — 需求

## Summary

軍師沙盤新增第四類彙整——讀取各軍師自己 `docs/todos/` 裡未歸檔的技術債，唯讀展示、依 severity 排序、status 顯示比照 ADR 011 verify 欄位樣式，並在全域總覽與軍師分組摘要帶入未處理筆數與 archive 進度感。同一批工作把 `/todo` skill 併入 kunsu repo 版控（比照 ADR 003 handoff 先例）。

---

## Problem Frame

使用者想在跟 supervisor 討論時，一次性攤開所有軍師（ebook、ivm 等）目前累積的技術債，不用逐一開軍師 session 跑 `/todo list`。目前 ebook 軍師有 26 筆未歸檔、ivm 軍師有 15 筆未歸檔（其中混有標記「已解決」卻尚未 `git mv` 到 archive 的項目），這個查看需求與軍師沙盤既有彙整交接／申請／上報的動機（避免逐一切換 CLI 視窗手動查詢）同質，但沙盤目前完全沒有涵蓋 `docs/todos/`。

另外，`/todo` skill 本身是全域 skill（`~/.claude/skills/todo/`），不在 kunsu repo 版控內；kunsu-dashboard 若要長期依賴其檔案格式（frontmatter 的 status／date／source／severity），這個跨 repo 的隱性耦合需要一併處理，否則格式演進時兩邊會漂移。

---

## Key Decisions

- **先做唯讀展示，互動標記留待後續評估**——軍師沙盤是 ADR 010 訂下的唯讀工具（無背景輪詢、僅 text/html、啟停由人手動掌握）。把 todo 狀態改為「已解決」或「已封存」是寫入操作，會牽動 ADR 010 唯讀不變量的例外設計與 commit 歸屬（比照 ADR 009 精神，不能無聲自動 commit）。這次先解決「看得到」的需求，互動標記另外評估。
- **只掃軍師自己的 `docs/todos/`，不含子專案**——目前實際有 `docs/todos/` 的都是軍師自己 repo（ebook、ivm、kunsu 自己），子專案（MainServer_Code、eBookApp 等）都沒有，不預先設計用不到的路徑。
- **status 顯示沿用 ADR 011 verify 欄位的「建議代碼＋開放值域」模式**——SKILL.md 定義的已知值套樣式標籤，其餘自由字串原樣顯示、不做語意猜測；「已解決」「已封存」若出現在活躍（未歸檔）目錄，視為「疑似漏歸檔」的獨立訊號，不歸入未處理數，避免虛報進度。
- **未知 status 自由字串計入未處理總數**——除「已解決」「已封存」兩個明確關閉值外，其餘一律視為仍需留意（含未來可能出現的新值），比照既有 `subrepo_status.py` partial_done 分類「未知值保守列出不略過」的設計哲學，避免漏計真正待處理的項目。
- **`/todo` skill 併入 kunsu repo 版控**——比照 ADR 003 handoff 先例：dashboard 既然要長期解析其檔案格式，併入同一 repo 能讓格式異動與解析邏輯同步改動，不會漂移；也讓 `/todo` 隨 kunsu toolkit 共同開發、版控與 `install.sh` 部署，不再是純外部依賴。併入本身視為對 Invariant 3（開發與部署分離）範圍的實質擴張，比照 ADR 003 另開一份新 ADR candidate 正式記錄決策與理由。

---

## Requirements

**`/todo` skill 併入**

- R1. 將 `~/.claude/skills/todo/` 的 skill 原始碼併入本 repo `skills/todo/`（比照 ADR 003 handoff 先例），隨 kunsu toolkit 共同開發、版控，並經 `install.sh` 部署。
- R2. 母體文件（`CLAUDE.md` 專案結構）同步登記 `skills/todo/`。
- R3. 另開一份新 ADR candidate，記錄「`/todo` skill 併入 kunsu repo」的決策與理由（比照 ADR 003 先例、範圍界定為 Invariant 3 的實質擴張）。

**軍師 `docs/todos/` 掃描**

- R4. 新增讀取軍師自己 repo `docs/todos/` 頂層（不含 `archive/`）的模組，解析各檔 frontmatter（status／date／source／severity），比照既有 `kunsu_scan.py`／`subrepo_status.py` 的唯讀、讀取失敗不中斷整體渲染的設計。
- R5. status 顯示比照 ADR 011 verify 欄位模式：「未處理」視為已知值並標示樣式；「已解決」「已封存」若出現在活躍（未歸檔）目錄，歸入獨立的「看似完成但未歸檔」分類，不計入未處理總數；其餘自由字串（如 `open`、`已回覆待實機驗證`）原樣顯示一般標籤、不做語意判斷，但計入未處理總數（保守列出不略過）。
- R6. severity（high／medium／low）驅動排序，high 優先排前並以醒目樣式標示。
- R7. 讀取 `docs/todos/archive/` 的檔案數量（不展開內容），顯示於未處理清單旁作進度感。

**軍師沙盤渲染**

- R8. 軍師卡片新增第四個分類區塊「待辦技術債」，比照既有新回覆／新申請／新上報的展開式清單樣式（`<details>`/`<summary>`、標題列帶最新修改時間）。
- R9. 全域總覽 chips 與軍師分組摘要列的 pending 計數，一併帶入未處理 todo 筆數（依 R5 定義的未處理總數，含未知自由字串）。

---

## Acceptance Examples

- AE1. **Covers R5.** 某軍師 `docs/todos/` 內一筆 `status: 已解決` 但仍在頂層未歸檔——沙盤將其列入「看似完成但未歸檔」，不計入未處理數與總覽 chip。
- AE2. **Covers R5, R9.** 某筆 `status: open`——視為未知值，原樣顯示 `status: open` 一般標籤，同時計入未處理總數與全域總覽 chip。
- AE3. **Covers R6, R8.** 某軍師有多筆 high／medium／low 的未歸檔 todo——「待辦技術債」區塊內 high 排最前並標紅。
- AE4. **Covers R4.** 軍師 repo 沒有 `docs/todos/` 目錄——「待辦技術債」區塊顯示空狀態（無待辦），不報錯、不中斷整頁渲染。

---

## Scope Boundaries

- 網頁互動標記 todo 為完成／封存——沙盤維持唯讀，未來如需要另外評估（牽涉 ADR 010 例外設計）。
- 子專案自己 repo 的 `docs/todos/`——目前無實例，不掃描。
- kunsu 自己（工具母體）的 `docs/todos/`——不在任何 registry 條目的軍師欄位中，沙盤現有架構掃不到，本次不特別處理。
- `/todo` skill 既有慣例（status 三值定義、`done`／`rm` 流程本身）不因本次改動——併入 repo 是搬遷版控位置，不是重新設計 skill 行為。

---

## Dependencies / Assumptions

- `/todo` skill（併入前版本 0.1.1）的 frontmatter 契約：status／date／source／severity，此為既有事實，不因搬遷而變。
- 既有 `kunsu_scan.py`／`subrepo_status.py` 的唯讀解析模式（frontmatter 解析、mtime 讀取、錯誤不中斷）為本次新模組沿用的既定慣例。
- ADR 011 verify 欄位的「建議代碼＋開放值域＋標籤樣式」設計為 status 顯示的直接先例。
- ADR 003（handoff skill 併入 kunsu repo）為 `/todo` skill 併入的直接先例。

---

## Outstanding Questions

**Deferred to Planning**

- 「待辦技術債」區塊在軍師卡片內的確切排列位置與樣式命名（沿用既有樣式語言，細節留給實作）。
- archive 筆數呈現的確切文案與位置。
