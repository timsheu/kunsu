---
title: "feat: handoff done 收尾沉澱訊號查核"
type: feat
status: completed
date: 2026-08-12
origin: docs/brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md
---

# feat: handoff done 收尾沉澱訊號查核

## Summary

handoff done 收尾流程新增「沉澱訊號查核」：逐項驗收查核通讀回覆時順手判斷有無值得沉澱的教訓訊號，有訊號則在收尾回報附一句候選教訓摘要並建議 `/ce-compound`，無訊號靜默。純資訊性提示，不自動執行、不新增互動、不改變流程分支。handoff v0.9.0 → v0.10.0。

## Problem Frame

教訓沉澱依賴使用者事後想起 `/ce-compound`，實際發生過「規劃時得由使用者親自指示以前已發生過」的失效；live 軍師沉澱率極不均（ebook 84 筆歸檔交接對 11 篇非種子 solutions、px 16 筆對 0 篇）。done 流程是 session 必經路徑且往返證據最完整，是結構上最可靠的沉澱掛載點（攔截點教訓見 `docs/solutions/workflow-issues/handoff-intercept-point-selection.md`：觸發詞覆蓋有上限、指引種在必經路徑）。完整脈絡見 origin 需求文件。

---

## Requirements

沿用 origin R-IDs（見 origin: docs/brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md）：

- R1. 逐項驗收查核時一併判斷沉澱訊號；多份回覆時通讀全部回覆以判斷往返軌跡——現行步驟 2 僅讀最新一份，此為本次明文新增的讀檔行為。訊號限當次往返可見：往返翻案、blocked 軌跡、與原規劃落差、多輪往返、使用者接受的驗收缺口。
- R2. 有訊號時收尾回報附一句候選教訓摘要＋建議 `/ce-compound`，措辭附「或手動沉澱至 `docs/solutions/`」替代路徑（軟依賴）。
- R3. 訊號字面存在即提示、摘要收斂一句；無訊號靜默零輸出。
- R4. 純資訊性：不自動執行、不新增 AskUserQuestion、不改變 done 既有步驟與分支。
- R5. 提示僅在收尾完成的回報出現；暫緩收尾不提示。
- R6. 落點僅 `skills/handoff/SKILL.md`；軍師範本零改動、免 live 遷移。
- R7. 版號升版；`skills/kunsu-inbox/SKILL.md` 依賴聲明與 `CONCEPTS.md`「done 收尾」詞條同步。

---

## Key Technical Decisions

- **判斷與呈現分離、不重排步驟編號**：訊號判斷寫成 done 步驟 2「逐項驗收查核」內的子項，提示呈現寫進步驟 9 回報內容。讀檔範圍：單份回覆零額外讀檔；多份回覆時為判斷往返軌跡而通讀全部回覆——現行步驟 2 僅 Read 最新一份，通讀屬本次新增的讀檔行為，結論確認仍以最新一份為準。不新增獨立步驟——done 步驟 3–9 間有多處互相引用（連續執行約束、`git add` 範圍），重排編號的修訂成本與出錯面遠大於子項寫法；R5「暫緩不提示」亦自然成立（流程停在步驟 2 時步驟 9 未達成）。
- **單一語意副本**：新查核文字只存在 SKILL.md done 段一處，不入軍師範本、不入任何腳本 printf。依 `docs/solutions/workflow-issues/handoff-done-closure-gap.md` 的多副本同步教訓，不新增需要連動維護的副本（R6 的零範本改動同時是零副本增生）。
- **版號 minor 升 0.10.0、依賴聲明僅版本同步**：新查核不涉掃描慣例、不新增檔案搬移形狀，`kunsu-inbox` 依賴聲明比照 v0.8.0 先例僅同步版號並註明不在掃描範圍，不新增依賴項目。
- **不新增觸發詞**：查核在既有 done 流程內部執行，無獨立入口，description 零改動——不適用補詞三步驟（無新口語需攔截）。

---

## Implementation Units

### U1. handoff SKILL.md done 流程加入沉澱訊號查核

- **Goal**：done 步驟 2 增加訊號判斷子項、步驟 9 回報增加條件提示行，版號升 0.10.0。
- **Requirements**：R1–R6。
- **Dependencies**：無。
- **Files**：`skills/handoff/SKILL.md`。
- **Approach**：
  - frontmatter `version: 0.9.0` → `0.10.0`。
  - 步驟 2「逐項驗收查核」子項之後新增「沉澱訊號查核」子項：明訂讀檔範圍——多份回覆時通讀全部回覆（至少各回覆 frontmatter `status` 與內文要點），結論確認仍以最新一份為準、單份回覆維持現行；通讀時一併判斷 R1 五類訊號（列舉具名訊號）；明文「訊號字面存在即記下、不確定時傾向記下」（R3）與「本查核不阻擋流程、不改變任何分支」（R4）。
  - 步驟 9 回報內容新增一句條件行：有訊號時附「本次往返含〈訊號〉，可能值得沉澱（一句候選教訓方向），可用 `/ce-compound` 或手動沉澱至 `docs/solutions/`」；無訊號時不輸出任何沉澱相關文字（R2、R3、R5）。
  - 描寫為指引語氣、比照步驟 2 逐項驗收查核與步驟 3 來源 todo 查核的既有行文密度，不展開成獨立長段。
- **Patterns to follow**：done 步驟 2「逐項驗收查核」子項（v0.7.0 加入）與步驟 3「來源 todo 查核」的行文形狀；kunsu-inbox「→ 收尾提示行」的僅提示不執行語氣。
- **Test scenarios**：Test expectation: none——純 SKILL.md 指引文字，行為驗證由 U3 dogfooding 承擔。
- **Verification**：Read 全文核對——步驟編號零重排、既有互相引用（連續執行約束、`git add` 範圍）字面不變；grep `0.9.0` 於本檔零殘留。

### U2. 依賴聲明、CONCEPTS 與母體文件同步

- **Goal**：版號與詞條同步，母體文件反映新查核。
- **Requirements**：R7。
- **Dependencies**：U1。
- **Files**：`skills/kunsu-inbox/SKILL.md`、`CONCEPTS.md`、`CLAUDE.md`。
- **Approach**：
  - `skills/kunsu-inbox/SKILL.md` 依賴聲明段：`v0.9.0` → `v0.10.0`，比照 v0.8.0 先例附一句「沉澱訊號查核為 done 流程內部指引，不在掃描慣例範圍、無豁免需求」。
  - `CONCEPTS.md`「done 收尾」詞條補一句：v0.10.0 起收尾流程內建沉澱訊號查核（有訊號時回報附候選教訓摘要與 `/ce-compound` 建議，僅提示不自動執行）。
  - `CLAUDE.md`：專案結構 `skills/handoff/` 行的功能描述補「沉澱訊號查核」、括號版號 `v0.9.0` → `v0.10.0`；開發狀態新增本次條目（含 idea 源頭與 brainstorm／plan 連結）。
- **Test scenarios**：Test expectation: none——文件同步。
- **Verification**：grep `v0.9.0` 於 `skills/kunsu-inbox/SKILL.md` 零殘留；核對 CLAUDE.md 專案結構 `handoff/` 行版號已更新（不對 CLAUDE.md 全檔 grep 零殘留——開發狀態歷史條目合法保留 v0.9.0 字樣）；CONCEPTS 詞條與 SKILL.md 行為描述一致（僅提示、不自動執行、無訊號靜默）。

### U3. 暫存目錄 dogfooding 驗證

- **Goal**：以 origin 三個 Acceptance Examples 實跑驗證新查核的行為。
- **Requirements**：R1–R5；Covers AE1、AE2、AE3。
- **Dependencies**：U1。
- **Files**：暫存目錄 fixture（不入 repo）；部署經 `install.sh`。
- **Approach**：暫存目錄建假 repo（`git init`＋`docs/handoffs/` fixture），部署更新後 skill，依 done 流程實跑三場景，核對回報輸出。
- **Test scenarios**：
  - Covers AE1. 交接含三份回覆（`blocked` → 翻案 → `submitted`）：done 收尾回報含一句候選教訓摘要、點名訊號、含 `/ce-compound` 與手動 fallback 措辭。
  - Covers AE2. 交接一份 `submitted` 回覆、逐項全中、無落差：收尾回報零沉澱相關文字。
  - Covers AE3. 最新回覆 `verify: needs-deploy` 且未實際上線驗證、使用者選暫緩：流程停止、無沉澱提示。
  - 邊界：交接無任何回覆（發起方自行確認完成的既有分支）——無訊號可判，回報零沉澱文字，既有「尚無回覆」提醒不受影響。
- **Verification**：三場景＋一邊界輸出符合預期；AE1 場景確認先前回覆（blocked 與翻案）確實被讀取並點名於摘要；fixture 中既有 done 步驟（逐項驗收、todo 查核、歸檔、確認 commit）行為與 v0.9.0 一致無回歸。

---

## Scope Boundaries

- reply 端（接手方）對稱提示：不做，等實痛（origin Scope Boundaries）。
- 跨交接「同型問題重現」偵測：不做——訊號限當次往返可見證據。
- 每次 done 無條件提示、自動執行 compound、AskUserQuestion 確認沉澱：不採（origin Key Decisions）。
- 軍師範本與 live 軍師：零改動、零遷移（R6）。

---

## Sources / Research

- `skills/handoff/SKILL.md` done 段（v0.9.0，九步驟、兩個既有回頭查核）——插點與行文範本。
- `docs/solutions/workflow-issues/handoff-intercept-point-selection.md` ——掛載點選擇依據（必經路徑優於觸發詞）。
- `docs/solutions/workflow-issues/handoff-done-closure-gap.md` ——多副本同步教訓（本計畫以單一副本規避）與觸發詞補洞三步驟（本計畫不適用之判定依據）。
- Live 軍師沉澱統計（2026-08-12 實測）：ebook 84/11、ivm 41/2、px 16/0。
