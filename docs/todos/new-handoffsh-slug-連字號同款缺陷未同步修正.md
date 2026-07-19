---
status: 未處理
date: 2026-07-19
source: code-review
severity: low
---

# new-handoff.sh slug 連字號同款缺陷未同步修正

code review（2026-07-19 handoff done todo 閉環）發現：skills/handoff/scripts/new-handoff.sh 的 slug 產生 pipeline 與 new-todo.sh 修正前同款——先 tr 空白轉連字號、再 sed [[:punct:]] 清標點，標題內既有連字號與轉出的分隔符都會被清除（如 cache-key → cachekey）。new-todo.sh 已於 /todo 0.1.2 以  佔位法修正，new-handoff.sh 尚未同步，兩支腳本同類邏輯分叉。

## 相關檔案

- skills/handoff/scripts/new-handoff.sh（slug pipeline）
- skills/todo/scripts/new-todo.sh（已修正的參考做法）

## 待辦方向

- 比照 new-todo.sh 的佔位法同步修正，並以相同六案例驗證（英文多詞、詞內連字號、中文、底線、頭尾標點、撞名）
