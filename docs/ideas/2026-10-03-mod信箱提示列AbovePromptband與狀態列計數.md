---
title: mod：信箱提示列 AbovePrompt band 與狀態列計數
type: idea
status: inbox
created: 2026-10-03
tags: [idea, kunsu, mod, claude-code]
---

# mod：信箱提示列 AbovePrompt band 與狀態列計數

## 背景 / 動機

Claude Code mods（plugin of function hooks，`ui.render` 的 `AbovePrompt` 元件與 `$.ui.status`）可以把訊號畫給「人」看，不經模型 context。現有 UserPromptSubmit hook 是把信箱新件注入模型 context，人只有在模型轉述時才看到；2026-09-23 事故的 77 分鐘空窗正是人沒看到。

## 做法

`prompt.submit` 時跑一次 `git status --porcelain -z` 掃三信箱頂層未 commit 新件，畫一行「📨 回覆 N｜上報 N｜申請 N｜最新：檔名」在提示框上方、狀態列常駐計數。零輪詢、事件驅動，與現行 hook 互補（hook 餵模型、band 餵人）。非軍師 repo 零輸出。

## 邊界

mod 是純 Claude Code adapter（ADR 019 第三類配件，與 kc.fish 同級），Codex 零對應；TSX 熱重載無建置步驟但已是程式，Invariant 1 要比照 ADR 010 寫例外範圍；API 標 this build，漂移風險高於 hook。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
