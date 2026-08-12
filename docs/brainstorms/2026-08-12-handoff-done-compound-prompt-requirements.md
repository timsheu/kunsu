---
date: 2026-08-12
topic: handoff-done-compound-prompt
---

# handoff done 收尾沉澱訊號查核——需求文件

## Summary

handoff done 收尾流程新增第三個回頭查核「沉澱訊號查核」：session 在逐項驗收查核時通讀全部回覆（多份回覆時屬新增讀檔範圍），順手判斷本次交接往返有無值得沉澱的教訓訊號；有訊號則在收尾回報附一句候選教訓摘要並建議 `/ce-compound`，無訊號則靜默。純資訊性提示，不自動執行、不新增互動、不改變 done 流程分支。

---

## Problem Frame

教訓沉澱目前完全依賴使用者事後想起 `/ce-compound`。實際發生過的失效形態：規劃或執行時使用者得親自指示「這個問題以前已發生過」——教訓存在使用者腦中，不在系統可檢索的位置（`docs/solutions/`），既有的規劃前既有盤點與 ce-plan learnings researcher 因此撈不到。

Live 軍師實證顯示沉澱極不均勻：ebook 軍師 84 筆已歸檔交接對 11 篇非種子 solutions（約 13%）、ivm 41 筆對 2 篇（5%）、px 16 筆對 0 篇。比例本身不證明流失（多數交接為例行工作），但 px 全零說明沉澱與否完全取決於使用者當下是否記得。

既有教訓 `docs/solutions/workflow-issues/handoff-intercept-point-selection.md` 指出：觸發詞攔截有覆蓋上限，指引應種在 session 必經路徑上。done 流程本身就是必經路徑——交接的完整往返證據（問題清單、逐項回答、翻案軌跡、落差說明）在此時點全數在 session 手上，是結構上最可靠、資訊最完整的沉澱掛載點。

---

## Key Decisions

- **有訊號才提示，而非每次固定一行**：無條件提示會產生提示疲勞，最終被當背景雜訊忽略。訊號判斷交給 session，掛在逐項驗收查核的讀檔動作上（多份回覆需通讀全部回覆，屬新增讀檔範圍），無訊號時零輸出成本。代價是可能漏報，以「訊號字面存在即提示」的傾向緩解（見 R3）。
- **僅 done 端，不動 reply 端**：接手方的技術教訓會隨回覆證據流到發起方，done 逐項驗收查核時全部可見；live 軍師實證顯示使用者將軍師 repo 作為專案群的共享記憶中心（ebook 軍師 solutions 含大量子專案技術教訓），落點單一。reply 端對稱提示等實痛出現再評估。
- **純資訊性提示，不新增互動**：done 尾端已有確認 commit 互動，且 `/ce-compound` 產出的 solutions 檔不在 done 的 commit 範圍內；提示只出現在收尾回報中，使用者若要沉澱，於 done 完成後自行發起，維持「CE 指令由使用者發起」的既有政策。

---

## Requirements

**查核行為**

- R1. done 流程在逐項驗收查核時一併判斷本次往返有無沉澱訊號，多份回覆時通讀全部回覆以判斷往返軌跡（現行流程僅讀最新一份，通讀屬新增讀檔行為）；訊號限於當次交接往返可見的證據，候選訊號：往返翻案（後續回覆推翻先前說法）、blocked 軌跡（曾有 `blocked` 回覆）、與原規劃的落差（回覆的落差段非空）、多輪往返（回覆數明顯多於常態）、驗收查核發現且使用者接受的缺口。
- R2. 有訊號時，於收尾回報中附一句候選教訓摘要（點名訊號與可能的教訓方向），並建議使用者以 `/ce-compound` 沉澱；`/ce-compound` 為軟依賴，措辭附「或手動沉澱至 `docs/solutions/`」的替代路徑。
- R3. 訊號判斷的邊界傾向：訊號字面存在即提示（漏報正是本功能要修的痛），以摘要收斂為一句控制雜訊；無訊號時靜默，不輸出任何提示。

**流程邊界**

- R4. 提示為純資訊性：不自動執行 `/ce-compound`、不新增 AskUserQuestion 互動、不改變 done 流程的任何分支與既有步驟順序。
- R5. 提示僅在收尾完成的回報中出現；使用者因驗收缺口暫緩收尾時不提示（缺口本身已在逐項驗收查核中顯式呈現）。

**落點與同步**

- R6. 改動落點僅 `skills/handoff/SKILL.md` 的 done 流程；軍師範本（`skills/kunsu-init/assets/templates/`）零改動，免 live 軍師遷移——done 流程全文在 skill 內，軍師 session 執行時必經。
- R7. handoff 版號升版，`skills/kunsu-inbox/SKILL.md` 依賴聲明同步；CONCEPTS.md「done 收尾」詞條同步補述本查核。

---

## Acceptance Examples

- AE1. **Covers R1, R2.** 某交接有三份回覆：第一份 `blocked`（等後台開權限）、第二份推翻第一份的方案改走另一條路、第三份 `submitted` 完成。done 收尾回報在逐項驗收結果之後附一句：「本次往返含 blocked 軌跡與方案翻案，可能值得沉澱（如：權限依賴應在交接前確認），可用 `/ce-compound` 或手動沉澱至 `docs/solutions/`」。
- AE2. **Covers R3.** 某交接一份 `submitted` 回覆、逐項全數命中、無落差段。收尾回報不含任何沉澱相關文字。
- AE3. **Covers R5.** 逐項驗收查核發現 `needs-deploy` 尚未實際上線驗證，使用者選擇暫緩收尾。流程停止，不出現沉澱提示。

---

## Scope Boundaries

- reply 端（接手方）對稱提示：不做，等實痛出現再評估（記錄於 `docs/ideas/2026-08-11-接手端對稱既有盤點.md` 同族觀察）。
- 跨交接「同型問題重現」偵測：不做——需掃描 `docs/handoffs/archive/`，成本與本次「當次往返可見證據」的定位不成比例。
- 每次 done 無條件提示、自動執行 compound、以 AskUserQuestion 確認沉澱：均不採，理由見 Key Decisions。

---

## Dependencies / Assumptions

- 假設：軍師 session 執行 done 時 `/ce-compound`（CE plugin）通常可用；不可用時 R2 的手動替代路徑仍成立。
- 假設：使用者曾遭遇的「得親自指示以前已發生過」案例屬沉澱缺失（write 側）而非檢索缺失（read 側）；案例多發生於規劃前既有盤點（2026-07-25）落地之前，無法逐案回溯確認，故本功能定位為 write 側補強，與既有 read 側機制互補而非替代。

---

## Sources / Research

- `docs/solutions/workflow-issues/handoff-intercept-point-selection.md` — 攔截點選擇教訓：觸發詞覆蓋有上限，指引種在必經路徑；本需求的掛載點選擇直接援引其結論。
- `skills/handoff/SKILL.md` done 流程（v0.9.0）——九步驟、既有兩個回頭查核（逐項驗收查核、來源 todo 查核），本查核為第三個，插點與呈現形狀比照既有查核慣例。
- Live 軍師沉澱統計（2026-08-12 實測）：ebook 84 筆歸檔交接／11 篇非種子 solutions、ivm 41／2、px 16／0。
- 發想源頭：`docs/ideas/2026-08-11-handoffdone收尾加教訓沉澱提示.md`，上游脈絡為 Agent Memory 系列文章對「記憶形成時機」的檢驗清單（誰寫入、何時更新、讀完是否改變行動）。
