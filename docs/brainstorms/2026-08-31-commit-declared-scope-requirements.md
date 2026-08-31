---
title: 確認 commit 宣告範圍契約——pathspec 定型化、上報歸檔腳本與夾帶偵測
date: 2026-08-31
topic: commit-declared-scope
---

# 確認 commit 宣告範圍契約——pathspec 定型化、上報歸檔腳本與夾帶偵測

## Summary

把協議「確認 commit」的契約自「提交 index」改為「提交宣告範圍」：所有協議 commit 的定型指令改帶成對 pathspec；新增上報歸檔腳本補齊 v0.18.0 的計算載體覆蓋缺口；掃描端新增「非歸檔訊息 commit 夾帶 archive/ 新增」的 advisory 偵測入統計，作為日後是否啟動強制守門的數據基礎。

---

## Problem Frame

2026-08-31 ebook 軍師調查報告（`ebook/docs/2026-08-31-commit邊界失誤調查報告.md`，本 session 已逐筆獨立核對屬實）記錄同一 session 內兩次「commit 內容超出訊息宣告範圍」：上報歸檔的 `git mv` 先在 index 留下內容，隨後「建立交接」的 `git commit -m` 不帶 pathspec，把歸檔內容一併吞入。第一次修正後 session 自建的檢查對策在 20 個 commit 內有效，隔日仍重犯——對策只存在於短期注意力，沒有機制載體。

成因不是單一疏失，是三個條件疊加：（一）commit 編排（pathspec、排序、串接方式）無定型，各 session 自由發揮；（二）ADR 009「先暫存、隔著確認、後 commit」使 index 殘留跨 Bash 呼叫存在是協議常態；（三）三處權威文本（handoff SKILL 確認 commit 協議、範本上報歸檔第（4）步、`archive-handoff.sh` 印出的待確認指令）教的正是不帶 pathspec 的寫法，全部隱含假設 index 是空的。

系統層級後果：若被夾帶的是未讀回覆而非已處理上報，「未 commit 即未處理」訊號被靜默清除——與 2026-08-29 `git add -A` 事故同一條後果路徑，只是入口從 add 換成 commit。現有防護對此形狀全盲：PreToolUse 守門只攔 `git add` 三形狀，掃描統計檔 ebook 條目 7 次掃描 0 事件。

兩起事故都發生在上報歸檔——正是 v0.18.0 歸檔腳本化未覆蓋的流程；夾帶當下 git 其實有非零 exit code（空 index commit 為 1、對已搬走路徑 add 為 128），但被 `;`／換行串接吃掉，只有串尾指令的結果被看見。

---

## Key Decisions

- **commit 收斂宣告範圍，不收斂 index。** 確認 commit 的定型指令一律帶 pathspec，且與 `git add` 為同一組具體路徑；與 index 殘留徹底脫鉤後，殘留自地雷降級為無害狀態。已於暫存目錄實測：index 有歸檔殘留時 pathspec commit 只提交指名檔案，殘留原封不動。
- **pathspec 化涵蓋所有協議 commit，不限歸檔類。** 兩起事故的吞噬者都是「建立交接」commit——只改歸檔類擋不住這個形狀。涵蓋範圍：建立交接、回覆、done 歸檔、todo 收尾，以及 ebook 免確認白名單流程的 commit。
- **rename 必須成對列出 pathspec。** 歸檔 rename 只給目的地路徑會把 rename 拆半、來源刪除殘留 index；成對（來源＋目的地）已實測乾淨收斂。
- **只腳本化上報歸檔，申請歸檔延後。** 兩起事故實證都在上報；申請量少且歸檔內嵌於 add-project 審核流程，本次僅動其定型文字，等量成長再評估——與 ADR 008 open question 的觀察節奏一致。
- **範本四步驟全文保留，加腳本指路句。** 協議文字維持自足（腳本未部署時仍可手動執行），比照 kunsu-concepts done 收尾指路句先例（kunsu-init v0.6.1）；不採指路句化縮減，避免軍師協議文字依賴 toolkit 部署狀態。
- **advisory 偵測先行，強制守門觀察後另案。** ADR 017 擴 `git commit` 守門是唯一跨「提醒→阻止」線的選項，其必要性取決於本案落地後還會不會再犯；以新偵測的統計數據為啟動依據，本案不實作。
- **開一篇 ADR candidate 記錄原則。** 本案改協議定型文字且為歷史事故的機制性回應，依 kunsu 慣例留 ADR 血統；ADR 017 擴充列為其開放問題。

---

## Requirements

**甲、定型文字 pathspec 化**

- R1. handoff SKILL「確認 commit 協議」步驟 3 的定型指令改為 `git add <具體路徑> && git commit <同一組路徑> -m "<訊息>"`，add 與 commit 的路徑集合一致。
- R2. 歸檔類 commit 的 pathspec 成對列出 rename 的來源與目的地路徑（含 done 歸檔、todo 一併收尾與轉出路徑）。
- R3. 協議補排序規則一句：index 已有前一流程的暫存內容時，先收斂該 commit 再開始新流程的 add。
- R4. 協議多指令串接一律 `&&`（任一步失敗即中斷並可見），不使用 `;` 或裸換行串接。
- R5. 範本 `kunsu-claude.md` 上報歸檔第（4）步與申請歸檔句、`home-dataview-reports.md` 歸檔說明、kunsu-init SKILL add-project 審核歸檔的 commit 定型指令同步 pathspec 化。
- R6. `scripts/consistency-check.sh` 的定型文字比對項涵蓋新寫法，防副本漂移。
- R7. ebook／ivm／px 三 live 軍師合批遷移；ebook 另同步一句「免確認白名單流程的 commit 適用同一 pathspec 慣例」。

**乙、上報歸檔腳本**

- R8. 新增上報歸檔腳本，行為對稱 `archive-handoff.sh`：frontmatter status Edit（`submitted` → `archived`）→ untracked 前置 `git add` → `git mv` 至 `archive/` → `git add` 目的地路徑；多份並列傳入、已在 `archive/` 者略過供重跑、`git add` 僅限具體路徑。
- R9. 腳本 stdout 印出帶成對 pathspec 的待確認 commit 指令，不自動 commit（ADR 009 零改動）。
- R10. 腳本輸出含 index 狀態提示：暫存區含本流程外路徑時警告，並提醒 index 現含筆數、後續 commit 須帶 pathspec。
- R11. 範本上報歸檔四步驟全文保留，於協議段加一句腳本指路。

**丙、advisory 夾帶偵測**

- R12. `scan-replies.sh` 逐 commit 檢視新增形狀：訊息不含「歸檔」的 commit 新增（diff-filter A）任一信箱 `archive/`（handoffs／reports／applications）路徑檔案，輸出 `HISTORY_WARN` 新型別。
- R13. 新型別沿既有 advisory 性質：不改 exit code、基線前進不重報、事件與計數入統計檔 `~/.claude/kunsu-scan-stats.json`。
- R14. `kunsu_scan.py` 與 session hook 對新型別安全靜默（沿既有未知前綴略過行為），沙盤顯示不在本案範圍。

**丁、ADR 與同步**

- R15. 新增 ADR candidate：記錄「確認 commit 收斂宣告範圍、不收斂 index」原則、成對 pathspec 慣例與 advisory 偵測；ADR 017 擴 `git commit` 守門列為開放問題，附啟動條件（統計檔出現本形狀再犯事件）。
- R16. kunsu-inbox 依賴聲明版號與 CONCEPTS 相關詞條同步（版號於實作計畫定）。

---

## Acceptance Examples

- AE1. **Covers R1.** Given index 含上報歸檔的暫存內容，When 依定型指令以 pathspec commit 新建的交接檔，Then commit 僅含交接檔，歸檔暫存原封保留於 index。
- AE2. **Covers R2、R9.** Given 上報歸檔腳本已完成搬移，When 執行其印出的成對 pathspec commit 指令，Then commit 含目的地新增與來源刪除兩筆、工作樹與 index 乾淨。
- AE3. **Covers R12、R13.** Given 重演事故形狀（訊息「docs: 建立交接 …」的 commit 新增 `docs/reports/archive/` 檔案），When 執行掃描，Then 輸出 `HISTORY_WARN` 新型別且統計檔記入事件；基線前進後重跑不重報。
- AE4. **Covers R12.** Given 正當歸檔 commit（訊息含「歸檔」、新增 `archive/` 檔案），When 執行掃描，Then 不觸發警示。

---

## Scope Boundaries

- 申請歸檔腳本化——延後至申請量成長或出現實證事故。
- ADR 017 擴 `git commit` 守門——觀察後另案；啟動條件為統計檔累積到本形狀的再犯事件。
- 報告方向 B 全版（解析中文訊息的宣告範圍比對）——機械判準不可行，不做。
- 報告方向 C（歸檔腳本不留 index）——牴觸 ADR 009 暫存等確認設計，動掃描豁免形狀的回歸風險大於收益，不做。
- 沙盤與 SessionStart hook 對新 `HISTORY_WARN` 型別的顯示——沿既有「後續評估」項，不在本案。

---

## Dependencies / Assumptions

- rename 成對 pathspec 的行為已於暫存目錄實測三場景（殘留隔離、成對收斂、順序防呆），實作計畫的 dogfooding 以歸檔全鏈重驗即可。
- ebook 免確認白名單回流案（todo 記於 ebook 軍師）與本案改動同一段確認 commit 協議文字——本案先行，回流案後續整合時以本案定型文字為基底。
- 「歸檔」關鍵詞豁免依賴協議定型訊息格式（`docs: 歸檔交接／歸檔上報／…`）持續成立；訊息格式本身本案零改動。

---

## Outstanding Questions

**Deferred to Planning**

- `HISTORY_WARN` 新型別命名，與「訊息不含『歸檔』」判準的精確形狀（任意位置含詞即豁免，或限定 `docs: 歸檔` 前綴）。
- R3 排序規則與 R4 串接規則的落點措辭（協議正文、腳本 stderr 提示，或兩者）。
- 上報歸檔腳本的檔名與參數介面（比照 `archive-handoff.sh` 的片段比對與多份並列慣例）。

---

## Sources

- `ebook/docs/2026-08-31-commit邊界失誤調查報告.md` — 事故快照；本 session 已獨立核對（reflog 物件、30 commit 檔數逐筆、守門範圍、統計檔）。
- `skills/kunsu-inbox/scripts/scan-replies.sh` — 既有 `HISTORY_WARN` 兩型別（SMUGGLED_REPLY／BATCH_REPLY_ADD）與統計檔寫入結構，R12–R13 的掛載點。
- `skills/handoff/scripts/archive-handoff.sh` — 乙組腳本的對稱母本；其暫存區警告（流程外路徑）為 R10 的既有先例。
- `docs/adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md` — 確認 commit 協議憲章，本案不動其決策本體。
- `docs/adr/2026-08-29-adr-candidate-017-pretooluse-git-add-guard.md` — git add 守門判準四要件，R15 開放問題的把關基準。
