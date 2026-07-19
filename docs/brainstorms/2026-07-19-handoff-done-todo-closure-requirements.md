---
date: 2026-07-19
topic: handoff-done-todo-closure
---

# handoff done 來源 todo 一併收尾——需求文件

## Summary

`/handoff done` 收尾流程新增「來源 todo 查核」步驟：以雙向文字提及比對找出與本交接相關的 todo，命中經使用者確認後一併執行 todo 收尾歸檔，並納入同一個協議確認 commit。同批修正 `/todo` skill 的兩個併入前既有缺陷（untracked `git mv` 歸檔失敗、slug 連字號被清除），升版 0.1.2。

---

## Problem Frame

todo 升級成交接文件處理完畢後，todo 檔常停留在「未處理」沒被一併收尾。根因是協議層缺口：todo 與 handoff 之間沒有任何結構性連結，`/handoff done` 的七個步驟也沒有任何一步會回頭檢查來源 todo——收尾與否完全取決於當下 session 或使用者是否記得那筆 todo 存在。

副作用是軍師沙盤的待辦計數失真：實際已完成的工作持續被算進「待辦 N」，與真實技術債狀態脫節。

---

## Key Decisions

- **文字提及比對，不加結構欄位**——原本考慮在 todo frontmatter 加選填 `handoff:` 欄位（升級時寫入、done 時精確比對），使用者評估後撤回：升級時點零改動、零遷移、零新慣例，代價是 todo 內文沒寫交接連結時只能靠提示行兜底。
- **確認後代為執行，而非僅建議**——遺忘問題的根源是「多一次手動步驟就會被跳過」，僅顯示建議訊息無法閉環；改為確認後在 done 流程內直接執行收尾，一次確認完成交接與 todo 兩件歸檔。
- **一併修 `/todo` 既有缺陷**——done 內執行 todo 歸檔會踩到同一個 untracked `git mv` 地雷，修復邏輯反正要寫；順手把 `/todo` 自身 done／rm 的前置檢查與 `new-todo.sh` 的 slug 順序一併修掉，不留同邏輯兩處實作的尾巴。此決策撤銷 ADR 013 併入時的「零行為變更」限制。
- **收尾狀態一律「已解決」**——done 語境代表交接已完成並通過查核，不提供「已封存」分支；確認不需處理的封存路徑仍走使用者自行 `/todo rm`。

---

## Requirements

**來源 todo 查核（`/handoff done` 新步驟）**

- R1. `/handoff done` 於逐項驗收查核之後、歸檔動作之前，執行來源 todo 查核，範圍為本 repo `docs/todos/` 頂層的未歸檔檔案。
- R2. 比對為雙向文字提及：todo 檔內文提及本交接檔名，或交接本體內文提及某 todo 檔名，任一方向命中即列為候選。
- R3. 有候選時以 AskUserQuestion 讓使用者確認哪些 todo 一併收尾；多筆候選支援複選，也可全部略過。
- R4. 無候選但 `docs/todos/` 頂層仍有未歸檔檔案時，僅顯示一行提示（含筆數）；`docs/todos/` 不存在或頂層無檔案時完全靜默。
- R5. 查核與提示不阻擋 done 流程——使用者略過或無命中時，交接歸檔照常完成。

**todo 收尾執行**

- R6. 經確認的 todo 依既有 `/todo done` 語意收尾：frontmatter `status` 改「已解決」、標題下方補一行解決依據、`git mv` 至 `docs/todos/archive/`。
- R7. 解決依據自動填入本交接的歸檔路徑，不另外詢問使用者。
- R8. todo 檔為 untracked 時先 `git add` 再 `git mv`，比照 done 既有步驟 4 的前置檢查做法。
- R9. todo 收尾的全部改動納入 done 流程既有的協議確認 commit，不新增第二個確認點或第二個 commit。

**`/todo` skill 既有缺陷修正（0.1.2）**

- R10. `/todo done` 與 `/todo rm` 補 untracked 前置檢查：`git mv` 前以 `git status --porcelain` 核對，untracked 檔先 `git add`。
- R11. `new-todo.sh` 的 slug 產生保留連字號：調整標點清除與分隔符轉換的執行順序，英文詞間分隔不再喪失。

**相容與同步**

- R12. `/todo` 檔案格式與 frontmatter 欄位零改動，不新增任何欄位。
- R13. 版號同步：handoff skill v0.7.0 → v0.8.0、todo skill 0.1.1 → 0.1.2，kunsu-inbox 對 handoff 的依賴聲明版號一併更新。
- R14. 軍師沙盤（`todo_status.py` 桶邏輯、`main.py` 渲染）與軍師範本零改動。

---

## Key Flows

- F1. 命中並一併收尾
  - **Trigger:** 發起方執行 `/handoff done`，逐項驗收查核完成。
  - **Steps:** 雙向 grep 找出候選 todo → AskUserQuestion 確認要收尾的筆數 → 各 todo 依序 Edit `status`、補解決依據、untracked 者先 `git add`、`git mv` 至 archive → 交接本體照既有步驟歸檔 → 協議確認 commit 的 `git add` 範圍涵蓋 todo 歸檔路徑。
  - **Outcome:** 交接與來源 todo 在同一個 commit 內完成收尾，沙盤待辦計數同步下降。
  - **Covers:** R1、R2、R3、R6、R7、R8、R9。
- F2. 未命中路徑
  - **Trigger:** 同 F1，但雙向 grep 無任何候選。
  - **Steps:** 檢查 `docs/todos/` 頂層未歸檔筆數 → 有則顯示一行提示，無則靜默 → done 既有流程照常執行。
  - **Outcome:** 使用者知道尚有未處理 todo 可自行判斷，收尾不受阻擋。
  - **Covers:** R4、R5。

---

## Acceptance Examples

- AE1. **Covers R2、R3、R6、R9。** Given 某 todo 內文含本交接檔名，When 執行 `/handoff done` 並於確認時選取該筆，Then 該 todo `status` 改「已解決」、解決依據為交接歸檔路徑、與交接同一個 commit 歸檔。
- AE2. **Covers R4、R5。** Given 無任何文字提及命中、`docs/todos/` 頂層有 3 筆未歸檔，When 執行 done，Then 顯示一行含筆數的提示，交接歸檔照常完成。
- AE3. **Covers R4。** Given 本 repo 沒有 `docs/todos/` 目錄，When 執行 done，Then 不顯示任何 todo 相關訊息。
- AE4. **Covers R8。** Given 命中的 todo 檔為 untracked，When 確認收尾，Then 先 `git add` 再 `git mv`，歸檔成功不報 `not under version control`。
- AE5. **Covers R3、R5。** Given 有候選但使用者於確認時全部略過，When done 繼續，Then 所有 todo 檔原封不動，交接照常歸檔。
- AE6. **Covers R11。** Given 以含英文連字號詞（如 `cache-key`）的標題執行 `/todo add`，Then 產生的檔名 slug 保留連字號。

---

## Scope Boundaries

- 升級時點零改動：不加 frontmatter 欄位、不加 `/todo escalate` 子指令，todo 轉交接的動作維持現行口語觸發 `/handoff add`。
- 歷史積壓不批次清理：既有的「已解決未歸檔」孤兒（如 ivm 軍師現況）不在本次範圍，本功能只作用於未來的 done 收尾。
- 沙盤不顯示 todo 與交接的關聯，也不新增任何顯示層改動。
- 不做跨 repo 比對：done 只由發起方在交接本體所在 repo 執行，todo 掃描限於同 repo 的 `docs/todos/`。

---

## Dependencies / Assumptions

- 假設 todo 與其升級成的交接同存於發起方（軍師）repo——此假設由 done 的發起方守門既有規則保證，故 R1 限於本 repo 掃描即足夠。
- done 步驟 3–5 的連續執行約束延伸涵蓋 todo 收尾改動：Edit 後、`git mv` 前的中間態同樣以流程原子性避免掃描面誤判。
- ADR 009 協議 commit 慣例不變，本次僅擴大該 commit 的 `git add` 範圍。
- CLAUDE.md 開發狀態所記「`/todo` 缺陷留待後續版號、本次零行為變更」的先前決策，由本需求明確接手（0.1.2 於本批執行）。

---

## Outstanding Questions

**Deferred to Planning**

- 協議 commit 訊息是否在 `docs: 歸檔交接 <檔名>` 之外註記 todo 收尾，或維持原訊息不變。
- grep 比對鍵的精確形狀（純檔名、含 `docs/todos/` 路徑字串、或兩者皆試）與大小寫處理。

---

## Sources

- `skills/handoff/SKILL.md` done 章節——既有七步驟、逐項驗收查核、連續執行約束、untracked 前置檢查，本功能的插入點與比照對象。
- `skills/todo/SKILL.md` done／rm 步驟——收尾語意（status 改值、解決依據、`git mv` 歸檔）的既有定義。
- CLAUDE.md 開發狀態（2026-07-17 ADR 013 段落）——兩個併入前既有缺陷的發現紀錄與「零行為變更」原決策脈絡。
