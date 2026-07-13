---
date: 2026-07-13
topic: handoff-done-closure
---

# handoff done 收尾閉環 — 需求

## Summary

把「`/handoff done` 收尾」補進協作鏈的四個斷點：handoff 觸發詞補收尾口語、軍師範本工作流程加第 7 步收尾、`/kunsu-inbox` 回報新回覆後附收尾提示句、範本 Invariant #5 明列 done 例外。並在軍師沙盤「已回覆待確認」分類為每筆附 verify 推導的白話「下一步」提示與停留天數。全部為文案層與 display 層改動。

---

## Problem Frame

實際使用中，軍師 session 查核完回覆後不會提示以 `/handoff done` 收尾，使用者也常忘記主動要求，導致 `status: submitted` 的交接長期積壓在 `docs/handoffs/` 頂層——持續被 `/kunsu-inbox` 與 `/handoff list` 掃描消耗 token，沙盤上也一直列在「已回覆待確認」。

歸檔機制本身完備（`/handoff done` 即「改 `status: done` ＋ `git mv` 至 `archive/`」，掃描面天然排除 `archive/`），缺的是讓這個動作在對的時機被想起。查證後定位四個斷點：

1. `skills/handoff/SKILL.md` 的 description 觸發詞完全沒有 done 口語——「收尾」「結案」「歸檔交接」都不命中，與 v0.3.0「回覆軍師」reply 路由補洞同類。
2. 軍師範本 `skills/kunsu-init/assets/templates/kunsu-claude.md` 的工作流程六步驟結束在「讀取新回覆、調整規劃」，沒有收尾步驟，軍師 session 的流程認知裡沒有下一個動作。
3. `/kunsu-inbox` 軍師模式回報新回覆後，沒有任何後續提示句。
4. 範本 Invariant #5「本體任何人都不再編輯（含本 session）」是無例外的字面禁令，但 `/handoff done` 的既定流程就是編輯本體 `status`——機制層（handoff SKILL.md done 流程、`scan-replies.sh` 授權歸檔豁免、ADR 009）已授權，憲章層沒跟上；守規矩的 session 可能因此迴避建議 done。

另有一個查證中發現的鄰近缺陷：`skills/handoff/SKILL.md` 內回覆檔 `status` 值域兩處說明不一致（「回覆方式」段落列 `submitted`／`partial`／`blocked`，「值域對照」段落列四值含 `done`），而掃描端（kunsu-inbox 4a、沙盤 `subrepo_status.py`）均認得回覆 `done` 值並據以略過。

---

## Key Decisions

- **Invariant #5 例外直接寫進第 5 條內文**——例外與禁令同條，session 讀到禁令當下即見例外，單點修改。例外語意為「發起方執行 `/handoff done` 時將本體 frontmatter `status` 改為 `done` 並歸檔，屬授權歸檔、不改內文」，是對既有事實的明文化，不是放寬原則：本體作者本來就是軍師自己，done 是作者對自己文件的生命週期標記，單一作者與防版本漂移的意圖不變。
- **一律只提示、不自動執行**——done 永遠由使用者觸發，`/kunsu-inbox` 的 Invariant 1「只告知不開工」零改動；提示句是告知的一部分，不是開工。
- **觸發詞一律帶交接語境**——收「交接收尾」「歸檔這份交接」「這份交接可以結案」等，不收裸詞「收尾」「結案」；handoff skill 部署於所有 repo，裸詞會在無關情境誤觸發。
- **停留天數自最新回覆日起算**——語意是「回覆已等待確認多久」，不是交接文件的年齡。
- **沙盤僅動 display 層**——五分類判斷邏輯（`subrepo_status.py`）零改動。

---

## Requirements

**handoff skill**

- R1. `skills/handoff/SKILL.md` description 觸發詞補 done 收尾口語，全部帶交接語境（如「交接收尾」「這份交接可以收尾了」「歸檔這份交接」「標記交接完成」「handoff done」），不收裸詞「收尾」「結案」。
- R2. SKILL.md 本文補行為指引：發起方語境下，使用者表達「查核完成、結論無誤」時，session 應主動建議執行 `/handoff done` 收尾。
- R3. 回覆檔 `status` 值域兩處說明一致化為四值（`submitted`／`partial`／`blocked`／`done`），並補一句 `done` 值在回覆檔的語意說明；掃描端既有的 done 略過行為不動。

**軍師範本與既有軍師遷移**

- R4. 範本工作流程新增第 7 步：軍師查核回覆、使用者確認結論無誤後，主動提示以 `/handoff done` 收尾歸檔；執行仍經使用者確認。
- R5. 範本 Invariant #5 第 5 條內文補唯一例外句，語意見 Key Decisions 第一條。
- R6. ivm／ebook 兩既有軍師的 CLAUDE.md 比照 R4、R5 live 遷移。

**kunsu-inbox**

- R7. 軍師模式回報新回覆的輸出尾端固定附一句收尾提示：確認回覆無誤後可用 `/handoff done` 歸檔；僅提示、不自動執行。

**軍師沙盤**

- R8. 「已回覆待確認」每筆依最新回覆的 `verify` 值附白話「下一步」提示；`verify` 缺省顯示通用提示（查核後執行 `/handoff done`），自由字串顯示通用提示、既有原樣 badge 行為不變。
- R9. 「已回覆待確認」每筆顯示停留天數，自最新回覆日期起算至瀏覽當下。
- R10. 沙盤改動限渲染層，`subrepo_status.py` 五分類邏輯零改動；pytest 測試同步增補。

---

## Acceptance Examples

- AE1. **Covers R8, R9.** 某交接最新回覆 `status: submitted`、`verify: needs-device`、回覆日三天前——沙盤該筆顯示實機測試類的下一步提示與「已等 3 天」。
- AE2. **Covers R8.** 最新回覆無 `verify`——顯示通用提示「查核後執行 /handoff done」類文案，不顯示 verify badge。
- AE3. **Covers R1.** 使用者在軍師 session 說「這份交接可以收尾了」——命中 handoff skill 的 done 子指令。
- AE4. **Covers R1.** 使用者在一般（非 kunsu）repo 說「幫這個功能收尾」——不觸發 handoff skill。
- AE5. **Covers R2, R4.** 軍師 session 查核完回覆、使用者說「沒問題」——session 主動提示可執行 `/handoff done`，不逕自執行。

---

## Scope Boundaries

- 交接本體與回覆檔的 `status` 值域、掃描邏輯、tripwire 判斷零改動。
- 「未接手」「部分完成」分類不加下一步提示——其下一步在接手方，不是使用者。
- 不自動執行 done、不加任何自動歸檔路徑。
- SessionStart hook 自動提醒維持 ADR 002 的既有延後決策，不因本題提前。

---

## Dependencies / Assumptions

- 機制層已完備：`/handoff done` 流程、`scan-replies.sh` 授權歸檔豁免、ADR 009 協議 commit——本次僅補文案層與顯示層，無新協議。
- `verify` 欄位（ADR 011）已落地，沙盤 badge 渲染與 `latest_reply_verify`／`latest_reply_date` 資料已存在，R8、R9 只消費既有資料。
- ivm／ebook live 遷移比照 ADR 007、ADR 009 先例（範本改動同步遷移既有軍師）。

---

## Outstanding Questions

**Deferred to Planning**

- 各 `verify` 值對應的下一步提示精確文案。
- R3 中回覆檔 `done` 值的語意說明措辭（何時由接手方自標 done）。
