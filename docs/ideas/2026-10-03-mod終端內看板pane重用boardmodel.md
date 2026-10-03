---
title: mod：終端內看板 pane 重用 board_model
type: idea
status: inbox
created: 2026-10-03
tags: [idea, kunsu, mod, claude-code]
---

# mod：終端內看板 pane 重用 board_model

## 背景 / 動機

沙盤看板要切瀏覽器；mod 的 Pane 可在 Claude Code 終端內開側邊面板。

## 做法

`$.command.register` 註冊 `/kunsu-board`，`ui.render` 的 `Pane` 以 `$.process.run` 呼叫沙盤 `app/board_model.py`（純函式）取卡片歸屬，畫持球者 × 狀態欄；重新整理才掃描，沙盤程式碼零改動。寬度不足（<144 欄）時 pane 等待不畫，需評估終端寬度實況。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
