---
date: 2026-08-14
topic: invariant5-lifecycle-metadata
---

# Invariant #5 生命週期 metadata 邊界與勘誤、引用兩慣例——需求文件

## Summary

以 ADR Candidate 把 Invariant #5 的例外邊界自「status 更新」重述為「內文不可變；frontmatter 生命週期 metadata 由發起方維護」，並據此落兩條慣例：勘誤以更正交接傳遞、原本體 frontmatter 補 `corrected_by:` 指標；交接引用以檔名為權威識別、路徑降為當下提示。範本 Invariant #5 修訂與三 live 軍師同步遷移。

---

## Problem Frame

兩個同源於 Invariant #5 的缺口，由 ebook 軍師研究文件記錄：

**勘誤落點**（事件五）：已歸檔交接被發現內容有誤（密碼欄位方向寫反），依不可變性錯誤原封留存 `archive/`，成為未來讀者的錯誤參考；回覆信箱是接手方單向管道、軍師無法寫入更正。現狀僅外部記錄，依賴記錄者當下恰好察覺，且已觀察到「重複察覺重複付出查證成本」——記錄本身缺乏可被下一次察覺者命中的索引路徑。

**引用腐化**：發新交接必然引用剛收到的回覆（發交接的依據），彙整完隨即收尾把該批回覆歸檔，引用路徑必然失效；順序不可調換，屬流程必然而非偶發。done 步驟 8 的連結修正 grep 會命中交接本體但依 Invariant #5 跳過——偵測到了、無法處置，修復可能性為零。現行低影響來自「歸檔只換一層目錄、檔名不變」的實作細節，對自動化解析與未來目錄調整都是硬失敗。

三項地貌變化使本次收斂成為可能：偵測側已由矛盾回報指引（handoff v0.13.0）與反向路由查核補完，缺口收窄為「錯誤確認後更正放哪、未來讀者如何找到」；「更正交接」已是 ebook 田野實務（實發兩份），缺的只是本體指回更正的指標；範本 Invariant #5 例外原文已自帶「作者自己對文件的生命週期標記……不改內文」的定性，本次是明文化既存原則而非開新例外。

---

## Key Decisions

- **例外邊界明文化，而非逐案開例外**：範本原文的「生命週期標記」定性已涵蓋 status 之外的同類欄位，把邊界說清楚（內文不可變；frontmatter 生命週期 metadata 由發起方維護）比每次需要新欄位就修一次例外健康。滑坡風險以擴張判準防堵（見 R2）。
- **勘誤載體採更正交接**：田野已驗證、零新機制。否決 corrections/ 目錄（掃描、沙盤、範本、歸檔形狀全要認識新目錄，且本體仍無指標）與本體追加勘誤節（內文可 append 即開始空洞化定案快照語意）。
- **`corrected_by` 於發更正交接當下補寫，含已歸檔本體**：archive 內檔案的 frontmatter 編輯在例外邊界內（發起方對自己文件的生命週期標記，位置無關）；archive 不在任何掃描面上，無 tripwire 疑慮。
- **引用慣例採「檔名權威＋路徑提示」而非純檔名**：保住可點擊性；路徑失效自「錯誤」重定義為「提示過期」，讀者以檔名為穩定識別鍵。既有 archive 數十份失效引用接受不回溯。
- **接受三 live 軍師遷移成本**：Invariant #5 是範本文字，修訂必須同步 ebook／ivm／px 的 CLAUDE.md，否則新舊軍師帶著不同版本的憲章（2026-07-13 憲章掃蕩教訓）。

---

## Requirements

**Invariant 邊界（ADR 層級）**

- R1. ADR Candidate 明訂 Invariant #5 例外邊界重述：內文不可變；frontmatter 生命週期 metadata 由發起方維護。
- R2. ADR 附欄位擴張判準：僅限發起方對自己文件的生命週期事實標記（狀態、指向後續文件的指標），不承載內容判斷、不進掃描／tripwire／分類等任何比對邏輯、僅 display 與追溯用途；新欄位需經 ADR 修訂納入。
- R3. 現行合規欄位窮舉列於 ADR：`status`（既有）、`corrected_by`（本次新增，選填）。

**勘誤慣例**

- R4. 勘誤以更正交接傳遞：發現已定案交接內容有誤時，發起方發新交接更正記錄（指名被更正檔與錯誤點），不編輯原本體內文。
- R5. 發更正交接當下，發起方在原本體 frontmatter 補 `corrected_by: <更正交接檔名>`；原本體已歸檔時同樣適用。
- R6. `corrected_by` 為 display 與追溯用途，不進任何掃描、tripwire 或分類邏輯。

**引用慣例**

- R7. add 指引「相關檔案 / 連結」明訂：引用其他交接／回覆時必含完整檔名（含日期），路徑為當下位置提示、非權威識別；歸檔造成的路徑失效不構成錯誤，讀者以檔名搜尋定位。
- R8. 既有 archive 交接的失效引用不回溯修正；done 步驟 8 現行範圍（todos／plans 連結修正、跳過交接本體）零改動。

**遷移與同步**

- R9. 範本 Invariant #5 文字修訂（例外邊界重述＋`corrected_by`），ebook／ivm／px 三 live 軍師 CLAUDE.md 同步遷移。
- R10. handoff SKILL.md：add 指引補引用慣例、新增更正交接子指引（含 `corrected_by` 補寫動作），版號升 minor；CONCEPTS 相關詞條（交接文件、done 收尾）同步並新增「更正交接」。

---

## Acceptance Examples

- AE1. **Covers R4, R5.** 已歸檔交接被發現數字寫反 → 發起方發更正交接，並在 `archive/` 內原本體 frontmatter 補 `corrected_by` → 未來讀者開啟原檔即見指標，不再把錯誤內容當正確參考。
- AE2. **Covers R7, R8.** 新交接引用剛收到的回覆（完整檔名＋當下路徑），彙整後收尾將回覆歸檔 → 路徑失效但檔名可搜，不視為錯誤、無人需要修改任何檔案。
- AE3. **Covers R6.** 某本體帶有 `corrected_by` → `/kunsu-inbox`、掃描腳本、沙盤分類與 tripwire 行為零變化。

---

## Scope Boundaries

- corrections/ 目錄與本體勘誤節：方案評估時否決（見 Key Decisions）。
- archive 既有失效引用的回溯修正：不做，接受並記錄。
- 沙盤顯示 `corrected_by`（例如 archive 檢視時標示「此件已有更正」）：後續評估，本輪不做。
- 接手方端任何改動：偵測側已由矛盾回報（v0.13.0）與反向路由查核完備，本次僅處理更正的落點與指標。

---

## Outstanding Questions

**Deferred to Planning**

- `corrected_by` 多份更正時的值形（單值以最新為準，或 YAML 列表逐筆累加）。
- 更正交接的檔名慣例是否定型（田野已自發使用「更正」字樣開頭，是否明文建議）。
- 範本修訂後 `scripts/consistency-check.sh` 的 live 軍師抽查（H 檢查）是否需同步新增比對點。

---

## Sources

- 起源 idea：`docs/ideas/2026-08-13-交接本體錯誤的勘誤落點與不可變性張力.md`、`docs/ideas/2026-08-14-交接本體不可變但引用路徑隨歸檔腐化.md`
- 事件證據：ebook 軍師（`kunsu-project-root/ebook`）`docs/todos/交接本體不可變但其引用路徑會隨歸檔失效.md`（含 done 步驟 8「偵測到但無法處置」的實測與附帶誤差）、`docs/todos/軍師流程缺口回覆內容缺乏路由機制導致軍師自身行動項靜默漏接.md` 事件五
- 例外定性原文：`skills/kunsu-init/assets/templates/kunsu-claude.md` Invariant #5（「生命週期標記……不改內文」）
- 偵測側前置：`docs/brainstorms/2026-08-14-reply-contradiction-reporting-norm-requirements.md`（矛盾回報，已落地 v0.13.0）
- done 步驟 8 現行文字：`skills/handoff/SKILL.md`
