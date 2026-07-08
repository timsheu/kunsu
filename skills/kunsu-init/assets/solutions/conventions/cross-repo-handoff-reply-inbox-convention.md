---
title: 跨專案 Handoff 回覆信箱模式：單一作者取代共編回覆區
date: 2026-07-03
category: docs/solutions/conventions
module: 跨專案 handoff 協調
problem_type: convention
component: development_workflow
severity: high
applies_when:
  - 多個 repo 或獨立 session 需要協商同一份規格或 API 契約
  - 使用 handoff 文件協調跨 session 工作，且接手方需要回覆結論
  - 需要保留交接紀錄不可篡改，並支援分階段多次回覆
  - 接手方的工作目錄與軍師 repo 不同，存在 cd 路徑限制
tags: [handoff, cross-repo, reply-inbox, single-writer, append-only, collaboration, convention]
source: 抽取自 ebook 規劃協調中心（母本）沉澱文件，日期 2026-07-03；路徑與專案特定名稱已通用化。
---

# 跨專案 Handoff 回覆信箱模式：單一作者取代共編回覆區

## Context

軍師（規劃協調中心——純文件 git repo，角色是協調多個獨立 repo 之間的跨專案功能規劃）在實際執行一份 API 契約協商時，暴露了原始 `/handoff` 慣例的根本缺陷：交接文件（`docs/handoffs/*.md`）被設計成「接手方在同一份檔案的回覆區直接補填結論」，也就是**多方共享一個可變狀態**。

> **來源案例（ebook 書籍購買系統協調中心）**：Android 與後台兩個 session 各自在自己的 repo 下維護了「同名」的交接文件副本，只有其中一份被持續更新到含完整後台回覆，另一份停留在舊快照。兩邊各說各話，直到第三方（軍師）重新比對才發現落差。

根本原因不是任何一方沒有遵守流程紀律，而是**結構設計讓版本漂移成為必然**：只要同一份可變檔案有多個潛在寫入方，且位於不同 working directory、不同 git repo，就一定會有快照不一致的時刻，而且這個不一致不會主動報錯。

## Guidance

核心原則：**任何檔案永遠只有一個作者；不共享可變狀態。**

檔案結構：

```
docs/handoffs/            → 交接文件本體（由發起方撰寫，建立後即為定案快照，任何人不再編輯）
docs/handoffs/replies/    → 回覆信箱（append-only，接手方每次回覆新增一個新檔案，絕不覆蓋）
```

規則清單：

1. **交接文件本體只讀**：`docs/handoffs/*.md` 由發起方起草，`git commit` 後視為定案快照。任何人（含發起方自己）都不再編輯這份檔案。若有修訂需求，發起方建立新交接文件，舊檔案保持原樣。

2. **回覆一律是新檔案**：接手方完成後在 `docs/handoffs/replies/` 底下**新增**一個獨立檔案，命名規則：
   ```
   {原交接文件檔名}-reply-{YYYY-MM-DD}.md
   ```
   同一份交接文件可分階段回覆多次，每次是獨立新檔案，不覆蓋前次回覆（append-only）。

3. **回覆檔案 frontmatter 格式**：
   ```yaml
   ---
   type: handoff-reply
   from: {接手方角色識別}     # 回覆方識別
   to: {軍師角色識別}     # 交接文件原始發起方
   in_reply_to: {原交接文件檔名}.md
   created: YYYY-MM-DD
   status: done                 # 或 partial / blocked
   ---
   ```

4. **軍師只讀信箱，不寫入**：第三方（軍師）讀取 `docs/handoffs/replies/` 取得回覆，但永遠不編輯回覆檔案本身。讀取時機：使用者主動要求「同步進度」，不主動輪詢。

5. **彙整前先跑 tripwire 檢查**：每次彙整外部回覆前，先執行 `git status`／`git diff`，核對這次外部寫入**只落在** `docs/handoffs/replies/` 底下的新檔案。若發現任何檔案在此範圍之外被新增、修改或刪除，視為異常，停下回報使用者，不自行採信或清理。信箱範圍是唯一的例外授權，不是全域寫入權。

6. **交接文件必須附備援路徑**：每份交接文件的「回覆方式」段落除了教 `/handoff reply <slug>` 指令外，必須同時附上以絕對路徑手動建立回覆檔案的備援做法（見 Examples）。

此模式已推廣進全域 `~/.claude/skills/handoff/SKILL.md`，成為所有專案 `/handoff` 指令的預設行為（新增 `/handoff reply` 子指令；`done` 步驟改為檢查信箱裡的回覆，而非同檔案回覆區）。

## Why This Matters

「共編同一份檔案」的失敗不是流程紀律問題，而是結構性失敗：

- **版本漂移是結構性必然，不是偶發事故。** 只要同一份可變檔案有多個潛在寫入方，且分處不同 working directory 或不同 git repo，就不存在任何機制能保證雙方看到同一個版本。沒有共同的 lock、沒有自動 sync，唯一的防護是「人記得去更新」——而人最終一定會忘記。
- **靜默失敗比報錯更危險。** 檔案版本漂移不會拋出任何錯誤，兩方都在「正確地」閱讀自己看到的那份文件，內容卻不同。這個問題只有在第三方主動比對時才可能被發現，而且發現時通常已經有依賴舊版本做出的決策或實作。
- **「單一作者」在結構上排除了漂移，不只是紀律要求。** 回覆信箱模式讓每個檔案在建立時就確定唯一作者，此後任何人都不能編輯它。軍師收到的永遠是接手方的原始快照，不存在「哪個版本才是最新」的問題——每個檔案的版本就是它建立時的那個，且只有這一個。兩個 session 的寫入範圍不重疊，所以不存在衝突。
- **額外好處：完整的審計軌跡。** 每次回覆都是帶日期後綴的新檔案，整個溝通歷程自動形成不可篡改的時間序列，不需要靠 git log 重建對話，也不會有「這行是誰在什麼時候加的」的歧義。

## When to Apply

適用情境（需同時符合）：

- 溝通是雙向的（發起方送出、接手方需要回覆）
- 兩邊不共享同一個 working directory 或 git repo
- 協調需要留下可查核的紀錄（不能只靠口頭或即時通訊）
- 有第三方角色負責彙整或核查（例如軍師）

不適用：同一個 session、同一個 repo 內部的任務追蹤（那種情境用 TodoWrite 或單一 `tasks/todo.md` 即可，不需要信箱機制）。

## Examples

**Before（舊模式：共編同一份交接文件）**

交接文件末尾有一段：

```markdown
## 回覆區（由接手方 session 填入）

<!-- 接手方請在此填寫實作結論 -->
```

接手方 session 編輯這份檔案填入結論。若接手方在自己的 repo 下維護的是這份文件的一個副本，軍師看到的版本和接手方實際填寫的版本是兩個不同檔案，軍師沒有任何提示說明自己看的版本已經過期。

**After（新模式：回覆信箱）**

交接文件的「回覆方式」段落：

```markdown
## 回覆方式

**方法一：使用 /handoff reply 指令**（需先 cd 到軍師目錄）

    cd /path/to/your-planner-center
    /handoff reply {原交接文件 slug}

**方法二：用絕對路徑直接建立回覆檔案**（沙盒限制無法 cd 時的備援）

用 Write 工具建立：
`/path/to/your-planner-center/docs/handoffs/replies/{原交接文件檔名}-reply-{今日日期}.md`
```

接手方 session 的回覆落在 `docs/handoffs/replies/{原交接文件檔名}-reply-YYYY-MM-DD.md`，作者永遠是接手方 session，建立後不被任何人編輯。

**工作目錄陷阱（具體反例）**

接手方 session 的預設工作目錄是自己的 repo（該 repo 也有自己的 `CLAUDE.md`）。若不先 `cd` 到軍師目錄就直接執行 `/handoff reply`，腳本會以「執行當下的工作目錄」往上找最近的 `CLAUDE.md` 定位「專案根」——找到的是接手方自己的 `CLAUDE.md`，信箱路徑因此被解析到接手方自己的 repo 下。**這不會報任何錯誤**，接手方看起來執行成功，但回覆根本到不了軍師的信箱。

緩解：交接文件的「方法一」必須明確要求先 `cd`；若沙盒限制讓 `cd` 無法執行（工作目錄白名單限制），退而使用「方法二」——以完整絕對路徑建立回覆檔案，完全不依賴工作目錄推導。軍師彙整前的 tripwire（`git status`）也是一種偵測：若軍師什麼都沒收到，應主動詢問接手方是否遇到工作目錄問題，而不是默默等待。

## Related

- 本模式落地依據：軍師 `CLAUDE.md`「回覆信箱協議（`docs/handoffs/replies/`）」章節
- 全域 skill：`~/.claude/skills/handoff/SKILL.md`（v0.2.0+，`/handoff reply` 子指令）
- [`docs/solutions/architecture-patterns/cross-repo-coordination-planner-pattern.md`](../architecture-patterns/cross-repo-coordination-planner-pattern.md)：本機制所屬的更大架構模式（唯讀軍師角色），本文件是其中 handoff 回覆的細節規則
