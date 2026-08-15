---
date: 2026-08-15
topic: mechanism-reach-signpost
---

# 機制投放點與觸及率：指路牌、腳本 stdout 與 hook 版號提示——需求文件

## Summary

三件套修復「skill 內部指引在手動執行等效步驟時靜默失效」：範本層指路牌（kunsu-concepts 新增「done 收尾」詞條點名各查核＋工作流程兩句「手動等效執行不豁免」）、產檔腳本 stdout 尾端指路行（手動路徑上唯一倖存載體）、SessionStart hook 版號變動提示（機器層級狀態檔、事件驅動）。細節維持單一副本留 SKILL.md，指路牌只放名字與權威位置；三 live 軍師第四波遷移。

---

## Problem Frame

kunsu 流程改良有兩個投放點——skill 流程步驟只在 skill 被實際呼叫時生效，軍師 CLAUDE.md 每 session 自動載入。熟練軍師傾向手動執行等效步驟（產物完全相同、指引完全未觸及），skill 內部指引因此靜默失效且不留痕跡（ebook 審計第五份）：量化查核顯示十項機制中六項只在 skill 內、軍師 CLAUDE.md 零命中；ebook 2026-08-14 全日 8 建立＋6 收尾全手動，v0.10.0 起的三道 done 查核可能一次未跑——既有機制的有效性評估失去資料基礎，done 斷言自查（R10 判別機制）在整條 done 流程被繞過時連輸出機會都沒有。

結構定調：「掛載點須在必經路徑」教訓的一般化——**必經路徑是動態的**。熟練 session 的必經只剩三處：CLAUDE.md（自動載入）、腳本本身（reply 側生效不是指引寫得好，是腳本計算複雜度逼人走 skill）、仍會被呼叫的入口（kunsu-inbox、SessionStart hook）。觸及率由手動繞道成本決定，與指引品質無關。同時存在一個必須調和的張力：六項零命中是依單一副本教訓刻意為之——解法不能是把查核細節搬進 CLAUDE.md（副本漂移回歸＋載入成本），只能搬「名字與權威位置」。

---

## Key Decisions

- **指路牌只放名字＋權威位置，細節單一副本留 SKILL**：母體 CONCEPTS「done 收尾」詞條已是正確形狀（點名各查核＋「以 SKILL.md done 段為準」），但範本與三 live 軍師皆無此詞條——手動執行者連「有哪些查核、去哪讀」都不知道。補詞條＋工作流程兩句，使「不知道」變成「知道去哪讀」，單一副本教訓與觸及率同時兼顧。
- **腳本 stdout 是手動路徑上唯一倖存的載體**：手動執行仍必須跑產檔腳本（產物需要它），在其輸出尾端加一行指路是零摩擦的精準投放——只觸及手動執行者，經 skill 執行者本來就讀過指引。版本資訊如需展示，執行時動態讀同目錄 SKILL.md frontmatter，不建立版號副本。
- **hook 版號提示為事件驅動告知層**：session_hook.py 已存在（ADR 014，機器層級），比對部署版號與狀態檔、變動時一行提示，零輪詢零強制；狀態檔為 kunsu 首個 hook 持久化狀態，落機器層級不進任何 repo，僅承載「上次看到的版號」這一項告知性事實，fail-open。
- **三管齊下而非單點**：三載體各覆蓋一種繞過形態——CLAUDE.md 管「知道查核存在」、腳本管「手動產檔當下」、hook 管「版本更新的知悉」；任一失效仍有兜底。
- **否決**：提高手動摩擦（用摩擦換遵循反 harness 前提，且傷害正當手動情境）；查核細節全文搬 CLAUDE.md（副本漂移回歸）。

---

## Requirements

**指路牌（範本層）**

- R1. 範本 `kunsu-concepts.md` 新增「done 收尾」詞條：點名全部收尾查核（逐項驗收、沉澱訊號、反向路由、來源 todo 查核、殘項清點、斷言自查），細節以 handoff SKILL.md done 段為準，並含「手動等效執行不豁免」語句。
- R2. 範本工作流程第 5 步補一句：以 `/handoff` 產出交接——含手動呼叫產檔腳本時，撰寫指引（斷言層級紀律、引用檔名權威、更正交接）以 SKILL.md add 段為準。
- R3. 範本工作流程第 7 步補一句：收尾無論經 skill 或手動等效執行，查核清單以 SKILL.md done 段為準、不豁免。

**腳本 stdout 指路**

- R4. `new-handoff.sh` 產檔輸出尾端加一行指路：本腳本僅產檔，撰寫與查核指引見 SKILL.md add 段，未經 `/handoff` skill 執行時請回讀對應步驟。
- R5. `new-handoff-reply.sh` 同型一行（指向 reply 段）。
- R6. 指路行不改變任何產物檔案內容，且不含 consistency-check C 檢查的兩句定型句首字串（避免 `head -1` 比對假失敗）。

**hook 版號提示**

- R7. `session_hook.py` 比對部署 handoff SKILL.md 版號與狀態檔所記「上次看到的版號」：不同時記錄新值並輸出一行「handoff skill 已更新至 vX（自 vY），流程指引有變——本輪 add／done 建議經 skill 執行或回讀 SKILL.md」；相同時零輸出。
- R8. 狀態檔落 `~/.claude/` 下（機器層級，不進任何 repo）；讀寫失敗 fail-open 不阻斷 hook 既有輸出；軍師與子專案兩模式皆適用。

**遷移與同步**

- R9. 範本改動同步三 live 軍師（第四波，各一筆確認 commit）；涉及的 skill 依慣例升版（腳本輸出屬行為面）、kunsu-inbox 依賴聲明同步，版號序列計畫期定。

---

## Acceptance Examples

- AE1. **Covers R4.** 軍師手動 `cat 內文 | bash new-handoff.sh …` 產檔 → 輸出尾端見指路行 → 回讀 add 段後於交接補「依 X 記載」標注。
- AE2. **Covers R7.** handoff 自 v0.15.0 升版後，任一 session 首次啟動（含 `/clear`）→ hook 摘要多一行更新提示；下一個 session 不再提示。
- AE3. **Covers R1, R3.** 軍師手動收尾 → 因 CONCEPTS 詞條與工作流程句知道有六項查核、回讀 SKILL done 段執行（文字覆蓋檢核：詞條點名全部查核名）。
- AE4. **Covers R6.** 指路行上線後 `consistency-check.sh` C 檢查兩句逐字比對照常 PASS。

---

## Scope Boundaries

- 提高手動繞道摩擦、查核細節全文搬 CLAUDE.md：否決（見 Key Decisions）。
- 產物層強制查核記錄（commit 訊息須含查核結果）：留待 R10 斷言自查實績評估後再議，防儀式化。
- 審計系列自指問題（第五份 Q5：審計文件自身成為中介層）：另議。
- 觸及保證：指路牌仍依賴 session 讀取 CLAUDE.md——長駐後段注意力衰減的殘餘風險顯式接受（與前場相同），本設計提高的是「可知性」不是「必然執行」。

---

## Outstanding Questions

**Deferred to Planning**

- 狀態檔的確切檔名與格式（單一版號字串或多 skill 對照表）。
- hook 提示首發是否僅涵蓋 handoff（最高頻），todo／kunsu-init 等其他 skill 版號留待評估。
- 指路行是否附動態讀取的版號展示（成本一行 grep，價值待定）。

---

## Sources

- 起源 idea：`docs/ideas/2026-08-15-機制投放點與觸及率指路牌腳本stdout與hook版號提示三件套.md`
- 事件證據：ebook 軍師（`kunsu-project-root/ebook`）`docs/todos/機制的投放點決定觸及率skill內部指引在手動執行時靜默失效.md`（觀察三量化查核、觀察四 reply 側結構性差異）與 `docs/todos/比對關卡上線後的實測只攔得住下游有理由查證的斷言.md`（觀察五）
- 指路牌的既有正確形狀：母體 `CONCEPTS.md`「done 收尾」詞條
- 載體現況：`skills/handoff/scripts/new-handoff.sh`（stdout 定型輸出）、`skills/kunsu-inbox/scripts/session_hook.py`（ADR 014，現無持久化狀態）
