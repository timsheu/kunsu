---
date: 2026-07-25
topic: handoff-pause-report
---

# handoff 暫離回報慣例——需求文件

## Summary

為 `/handoff` skill 建立「暫離回報」慣例:接手方要暫停交接工作、切去別的任務時,先投遞一則最小 `partial` 回覆(內文附 branch 名與現況),讓軍師端把該交接自「未接手」看成「部分完成」。指引落在 SKILL.md reply 段與 description 暫離語境口語,並在每份新交接檔自動附上的「回覆方式」定型文字加一行暫離提示。

---

## Problem Frame

實際案例:軍師派發的交接已做完,成果先 commit 進 git branch(未合併),接手方臨時插入緊急需求,尚未回覆軍師就切走。軍師端查交接時,`/kunsu-inbox` 與軍師沙盤把這筆交接判為「未接手」——與實際不符。

機制上這不是分類缺陷:協議的唯一狀態訊號源是回覆檔,零回覆即判未接手,是機制正確運作、訊號缺席。斷點在行為層——切換任務的當下沒有任何東西提醒接手方先投遞回覆。

事發當下使用者的原話是「把做好的部份先移到新的 branch,現在要先做新的需求,之後再回來整合」——整句沒有任何交接語彙(交接、軍師、回覆皆未出現),因此單靠 skill description 的觸發詞攔不住這種話。相對可行的攔截點是接手方 session 自己的語境:在 session 本輪對話已讀過交接檔「回覆方式」段落的前提下,指引已在其 context 內;若 session 未讀過交接檔(如使用者口語轉述任務),或讀取後歷經大量操作使指引不再顯著,此路徑同樣無法保證觸達。

---

## Key Decisions

- **暫離回報的 status 固定用 `partial`,不用 `submitted`** — `partial` 的既有語意「部分完成,後續會再回報」精確對應暫離情境:合併、上線這些剩餘步驟仍在接手方手上,回來後會再回報。用 `submitted` 會讓軍師端看起來「只差驗收」,可能提前進入 done 收尾流程(雖會被逐項驗收查核攔下,但多一輪往返)。
- **指引種進交接檔的「回覆方式」定型文字,不只靠觸發詞** — 事發語句沒有交接語彙,觸發詞路徑是機率性的。定型文字在接手方 session 讀交接檔時就進入其 context,之後使用者說「先移到 branch」時 session 自己就有規則可以主動提醒——涵蓋場景較觸發詞廣,但仍以 session 已讀交接檔為前提,並非無條件可靠。代價是定型文字有兩處同文案副本需連動修改,此同步紀律已是既有慣例。
- **branch 名的可見度以「點開內文可見」為準** — 沙盤摘要列維持顯示「部分完成」與 verify 標籤,branch 名寫在回覆內文、展開全文可見。不為此新增 frontmatter 欄位或動渲染層。

---

## Requirements

**指引內容(SKILL.md reply 段)**

- R1. reply 段新增「暫離回報」指引:交接工作已有階段性成果(如已 commit 至 branch)但需切換任務暫時離開時,切走前投遞最小回覆——`status: partial`,內文至少含 branch 名、一句現況、之後回來繼續的意向。
- R2. 指引明訂暫離回報固定用 `partial`,並簡述理由(剩餘步驟仍在接手方手上,避免發起方誤啟收尾)。
- R3. `verify` 依既有規則照常評估選填;branch 資訊寫在內文,不放進 `verify`(維持其純驗收語意),也不新增建議代碼。
- R4. 指引提醒:回來完成整合後照常投遞完成回覆(`status: submitted`),並引用既有的 verify 不跨回覆繼承規則,一句帶過即可。

**觸發詞(SKILL.md description)**

- R5. description 補暫離語境口語觸發詞(如「交接工作先放到 branch,之後再回來」「交接工作先暫停」「交接先放著,先做別的需求」),比照 v0.3.0 reply 路由補洞與 v0.6.0 done 收尾口語的先例;觸發詞須帶交接語境,避免過度泛化在無交接場景誤觸發。

**定型文字(交接檔「回覆方式」段落)**

- R6. `skills/handoff/scripts/new-handoff.sh` printf 的「回覆方式」定型文字加一行暫離提示:中途需切換任務時,先投遞暫離回報(`status: partial`、內文附 branch 名),之後回來再照常回覆。
- R7. SKILL.md「檔案格式範例」段的同文案副本連動修改,維持兩處字面一致(SKILL.md 步驟 3 已明文的同步紀律)。

**範圍與同步**

- R8. `status`/`verify` 值域、四份值域語意副本、沙盤分類邏輯(`skills/kunsu-dashboard/app/subrepo_status.py`)、軍師範本一律零改動;因此不需要 live 軍師遷移。
- R9. handoff 版號依慣例升版,`skills/kunsu-inbox/SKILL.md` 的依賴聲明版號同步。

---

## Acceptance Examples

- AE1. **Covers R1, R2, R6。** Given 接手方 session 正在執行軍師派發的交接工作,本輪對話已讀過含新暫離提示的交接檔(含「回覆方式」段),且成果已 commit 至新 branch;When 使用者說「把做好的部份先移到新的 branch,現在要先做新的需求,之後再回來整合」(無交接語彙);Then session 依交接檔「回覆方式」段的暫離提示主動建議投遞暫離回報,產出 `status: partial`、內文含 branch 名的回覆檔,軍師沙盤該交接自「未接手」變為「部分完成」。
- AE2. **Covers R4。** Given 先前已投遞暫離回報;When 接手方回來完成整合與驗證;Then 照常投遞完成回覆(`status: submitted`,需要時顯式帶 `verify`),沙盤變為「已回覆待確認」。
- AE3. **Covers R5。** Given 使用者在接手方 session 說「交接工作先暫停,先去做別的」(帶交接語彙);Then 命中 description 觸發詞,進入暫離回報指引。

---

## Scope Boundaries

- 軍師端自動偵測子專案 branch——branch 名與交接無結構性連結,猜測式對應不可靠,不做。
- 回覆檔新增 `branch:` frontmatter 欄位與沙盤摘要列渲染——點開內文可見已足夠。
- 存量交接檔不回填新定型文字;本次觸發此需求的個案由使用者手動補投一則 `partial` 回覆解決。
- `status`/`verify` 值域擴充——不擴充,既有四值與建議代碼一律不動,見 R8。

---

## Sources

- `skills/handoff/SKILL.md` — reply 段(指引落點)、步驟 3(定型文字兩處副本的同步紀律)、「檔案格式範例」段(副本之一)。
- `skills/handoff/scripts/new-handoff.sh` — 「回覆方式」定型文字的 printf 來源。
- `docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md` — verify 欄位語意、不跨回覆繼承規則、「部分完成」分類拆分。
