---
title: "feat: reply 步驟 2 新增接手方矛盾回報指引"
type: feat
status: completed
date: 2026-08-14
origin: docs/brainstorms/2026-08-14-reply-contradiction-reporting-norm-requirements.md
---

# feat: reply 步驟 2 新增接手方矛盾回報指引

## Summary

在 `skills/handoff/SKILL.md` reply 步驟 2 插入一段帶理由的矛盾回報指引（handoff v0.13.0），同步版號鏈三檔與 CONCEPTS 詞條。單一語意副本、零觸發詞、零腳本零範本改動，以 `scripts/consistency-check.sh` 實跑驗證後經 `install.sh` 部署。

## Problem Frame

接手方發現交接內容與原始來源矛盾時，現行 reply 協議沒有回報義務，錯誤認知可留存於定案快照並跨交接流傳（origin 文件記錄的 ebook 事件五與 2026-08-14 田野命中）。詳見 origin：`docs/brainstorms/2026-08-14-reply-contradiction-reporting-norm-requirements.md`。

---

## Requirements

承 origin R1–R5，計畫層面不增減：

- R1. reply 步驟 2 新增矛盾回報指引，涵蓋「與接手方所持參照物不符」與「交接內文自相矛盾」兩類情形。
- R2. 指引明訂「即使判斷不影響自身實作也在回覆中明列」，並自帶理由（唯一同時持有交接與參照物的一方；未被指出的錯誤認知跨交接流傳）。
- R3. 命中才報：不要求每份回覆附核對聲明、不新增回覆格式欄位、不強制核對範圍與深度。
- R4. 兩種語境通用，不設語境分支；暫離回報最小三要素不受影響。
- R5. 零改動邊界：回覆檔格式、`new-handoff-reply.sh`、定型文字、軍師範本、掃描與 tripwire、done 流程皆不動；handoff 版號升 minor，kunsu-inbox 依賴聲明同步。

---

## Key Technical Decisions

- **插入點：redact 提醒段之後、verify 評估段之前**（`skills/handoff/SKILL.md` 步驟 2 主段與 verify 段的交界）。矛盾回報屬「內文該寫什麼」的指引，與既有「逐項回答附可查核證據」同群；插在 verify 段之後會切斷「評估 verify → 步驟 3 帶參數」的既有銜接。
- **指引文字不得包含定型文字句首字串**：`consistency-check.sh` 的 C 檢查以 `grep -F … | head -1` 對「回覆檔 `status` 值：」與「中途需切換任務時」兩句做逐字比對——新段若含這兩個句首，`head -1` 會先命中新文字造成假失敗。新段也不複述任何值域句或「回覆方式」定型句，避免製造新的語意副本（多副本同步教訓，見 `docs/solutions/workflow-issues/handoff-done-closure-gap.md`）。
- **明示「矛盾寫在回覆內文，不回頭修改交接本體」**：與 Invariant #5（定案快照、單一作者）及 v0.12.0「本體不可回填」語意對齊，消除新指引與既有「不編輯本體」禁令的表面張力。
- **效果採條件式陳述**：指引生效前提是 reply 流程被觸發，計畫與文件不宣稱「可靠攔截」（攔截點教訓，見 `docs/solutions/workflow-issues/handoff-intercept-point-selection.md`；同教訓支持本次零觸發詞——攔截點遷移優先於堆詞，v0.10.0／v0.12.0 先例）。
- **版號鏈三檔連動、kunsu-inbox 自身版號不動**：`skills/handoff/SKILL.md` frontmatter、`skills/kunsu-inbox/SKILL.md` 依賴聲明首個版號、`CLAUDE.md` 專案結構行三處全等才過 A1 檢查；依賴聲明括號內逐版列舉續列一句（不涉掃描慣例、無豁免需求）。kunsu-inbox 自身 frontmatter 不升版，沿 v0.10.0／v0.11.0 兩次同步先例。

---

## Implementation Units

> U1 與 U2 須同一次 commit 落地，否則版號鏈 A1 檢查在中間狀態必然失敗。

### U1. reply 步驟 2 插入矛盾回報指引段並升版

- **Goal**：新增指引段文字，frontmatter `version` 0.12.0 → 0.13.0。
- **Requirements**：R1–R4。
- **Files**：`skills/handoff/SKILL.md`。
- **Approach**：於步驟 2 主段（證據 redact 提醒結尾）與 verify 評估段之間插入獨立段落。方向性草稿（措辭可於實作時微調，約束見 KTD）：

  > 同時把交接內容本身當作可查核對象：你是唯一同時持有交接文件與自身參照物（原始碼、原始文件、實際狀態）的一方，發起方看不到你這端的事實。若發現交接內容與參照物不符、或交接內文自相矛盾（例如數字對不上、前後段互斥），即使判斷不影響自身實作，也在回覆中明列並附位置——未被指出的錯誤認知會留存於交接定案快照，並可能流傳進後續交接。矛盾寫在回覆內文即可，不要回頭修改交接本體；是否核對、核對到哪一層由你判斷，無矛盾時不需任何核對聲明。
- **Patterns to follow**：同步驟 2 既有「逐項回答附可查核證據」指引的行文密度與縮排；v0.10.0 沉澱訊號查核的單一副本掛載先例。
- **Test scenarios**（文件改動，以檢核代測試）：
  - 新段位於 redact 提醒與 verify 評估之間，Read 確認未打斷既有段落。
  - Covers AE1／AE2／AE3（origin）：逐句對照新段文字，三場景（命中即使不影響也報、無矛盾零聲明、本地語境同樣適用）皆被指引字面涵蓋——AE 為指引生效後的下游 session 行為預期，本 repo 無法實測，以文字覆蓋檢核代替。
  - `grep -c` 確認「回覆檔 \`status\` 值：」與「中途需切換任務時」兩字串全檔計數各維持 1（僅 add 範例段既有出現，證明新段未引入）。
- **Verification**：上述檢核全過；`version: 0.13.0` 就位。

### U2. 版號鏈與母體文件同步

- **Goal**：依賴聲明、CLAUDE.md、CONCEPTS.md 與新版號及新指引一致。
- **Requirements**：R5。
- **Dependencies**：U1。
- **Files**：`skills/kunsu-inbox/SKILL.md`（依賴聲明首個版號改 v0.13.0，逐版列舉續列一句）、`CLAUDE.md`（專案結構樹版號行、SKILL.md 說明行的 reply 內容列舉補「矛盾回報指引」、開發狀態新增一條目——歷史條目維持原貌）、`CONCEPTS.md`（新增「矛盾回報」詞條，行文比照「暫離回報」詞條）。
- **Test scenarios**：
  - `grep` 三檔版號字串全為 0.13.0。
  - CLAUDE.md 歷史開發狀態條目零 diff（僅新增不修改）。
- **Verification**：A1 版號鏈三源全等。

### U3. 驗證與部署

- **Goal**：機械檢查全過，部署目錄生效。
- **Requirements**：R5（零改動邊界的迴歸確認）。
- **Dependencies**：U1、U2。
- **Files**：無新改動；執行 `scripts/consistency-check.sh` 與 `install.sh`。
- **Test scenarios**：
  - `scripts/consistency-check.sh` 全項 PASS（含 A1 版號鏈、C 定型文字實跑逐字比對——後者同時證明定型文字與 `new-handoff.sh` 零 diff）。
  - `git diff --stat` 確認改動僅及 U1／U2 列出的四檔。
- **Verification**：檢查輸出全 PASS；`install.sh` 重跑後 `~/.claude/skills/handoff/SKILL.md` 為 0.13.0（部署為 copy 模式，須重跑才生效）。

---

## Scope Boundaries

承 origin：軍師端防線（副官、來源層級標注）與矛盾承接（勘誤落點，ADR 層級）不在本計畫；被回報矛盾的收尾處置沿用既有反向路由查核。R5 零改動清單為硬邊界。

---

## Sources & Research

- origin 需求文件與上游 idea：`docs/ideas/2026-08-13-接手方察覺交接與原始來源矛盾時無回報義務.md`
- 教訓：`docs/solutions/workflow-issues/handoff-intercept-point-selection.md`（零觸發詞、條件式可靠）、`docs/solutions/workflow-issues/handoff-done-closure-gap.md`（多副本同步、指引自帶理由的必要性）
- 機械檢查邏輯：`scripts/consistency-check.sh`（A1 版號鏈三源、C 定型文字 mktemp 實跑比對）
