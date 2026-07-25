---
title: 跨 repo solutions 檢索慣例——本地查無時改查 kb
type: idea
status: promoted
brainstorm: docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md
created: 2026-07-24
tags: [idea, kb, ce, solutions]
---

# 跨 repo solutions 檢索慣例——本地查無時改查 kb

ce-learnings-researcher（CE plugin）目前只搜本 repo 的 docs/solutions/。補一條檢索慣例：本地查無時，改用 /kb（zoekt）跨 repo 再查一次（query 形如 `f:docs/solutions/ 關鍵字`），讓 A repo 踩過的坑能被 B repo 的 session 找到。

## 背景 / 動機

2026-07-24 驗證：本機 zoekt 索引已涵蓋全部 152 個 repo 的已 commit 內容，一條 `problem_type: f:docs/solutions/` 查詢命中 42 篇跨 repo solutions。跨 repo 複利引擎不需搬運檔案（虛擬 hub）：solutions 留在原 repo，zoekt 提供檢索層。此為三個接線點之一。

## 落地研究（2026-07-24）

- `ce-learnings-researcher` 定義位於 `~/.claude/plugins/cache/compound-engineering-plugin/compound-engineering/3.11.2/agents/ce-learnings-researcher.md`——**版本化快取目錄，直接修改會在 plugin 升級時被覆蓋，fork 方案否決**。
- 零 fork 擴充點有二：
  1. 該 agent `tools` 含 `Bash`，可直接執行 zoekt curl 查詢；且 subagent context 同樣載入全域 CLAUDE.md——把慣例寫進**全域層**（`~/.claude/CLAUDE.md` 一小段，或 rules 來源 repo 新增規則檔後 install）即可被主 session 與所有 subagent 讀到。
  2. 使用者自有的 `ce-orchestrate` skill（可直接改）：研究 fan-out 階段加一步 kb 跨 repo 查詢，作為雙保險。
- 慣例內容要件：觸發條件（本地 `docs/solutions/` 查無或命中 <3 時）、健康檢查（`curl -s -m 2 http://127.0.0.1:6070` 失敗即靜默略過，軟依賴）、query 模板（`f:docs/solutions/ 關鍵字`）、引用格式（附 repo 名＋路徑，標明是他 repo 情境、需自行判斷適用性）。
- 已知限制：CLAUDE.md 對 subagent 是背景指引非硬性強制，命中率非 100%；主 session 派發 researcher 時可在 work-context 內顯式提示，補強命中率。

## 下一步

- [x] 研究 CE plugin 的擴充點（避免直接改 plugin 內檔案被升級覆蓋）→ 見上方落地研究
- [ ] 決定慣例落點：全域 CLAUDE.md 直加 vs rules 來源 repo 新增規則檔
- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
