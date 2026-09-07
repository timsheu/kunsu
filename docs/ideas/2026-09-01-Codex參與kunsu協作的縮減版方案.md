---
title: Codex 參與 kunsu 協作的縮減版方案
type: idea
status: promoted
brainstorm: docs/brainstorms/2026-09-06-codex-agent-neutral-deployment-requirements.md
created: 2026-09-01
tags: [idea, codex, agent-neutral, protocol]
---

# Codex 參與 kunsu 協作的縮減版方案

讓 Codex 能參與 kunsu 協作，但不走「Kunsu 通用 Agent 架構重構」原計畫的 Core／Adapter 程式化重構——以文件與現有腳本達成，零 Invariant 翻案。

## 背景 / 動機

源自外部計畫文件《Kunsu 通用 Agent 架構重構》（~/Downloads，2026-09-01 評估）。評估結論：方向有價值但照原文執行屬過度設計——計畫假設 kunsu 是有 module／import／dependency direction 的程式，實際上 kunsu 本體是 markdown 協議＋檔案系統慣例＋膠水腳本（Invariant 1）。落實原計畫的 Agent Runtime interface（start/attach/status/stop）與 registry live state store，需要建真正的 orchestrator 程式或 daemon，違反 Invariant 1、推翻 ADR 002／010／015 的手動掌控設計。

同時，大半「agent-neutral」目標其實已成立：
- 資料層（handoff／reply／report／todo 為 YAML frontmatter＋markdown、registry 純 JSON、「未 commit 即新訊息」訊號是 git）任何能讀寫檔案跑 git 的 agent 今天就能參與。
- 腳本層幾乎零 Claude 耦合：產檔／歸檔腳本的 claude 引用僅兩類——專案根標記已同時認 CLAUDE.md 與 AGENTS.md（Codex 慣例）、registry 等狀態檔路徑在 ~/.claude/ 底下。
- 角色代碼（ADR 007）是 role 不是 agent type；事件分類已是任務語彙，推播只是其中一種 delivery 且自帶降級。

真正的 Claude 耦合面很窄：SKILL.md 格式與觸發詞、兩支 hook（SessionStart／PreToolUse）、ListAgents/SendMessage 推播、~/.claude/ 路徑、kc.fish、install.sh 部署目標——這就是「Claude adapter」的全部，已天然隔離在指令載體層。

## 縮減版內容（四項）

1. **協議規格抽成 agent-neutral spec**：檔案格式、生命週期、commit 宣告範圍契約、目錄佈局寫成單一權威規格文件；內容大多已存在於 SKILL.md，抽取時守單一權威副本教訓，其餘處指路（指路牌模式）。
2. **Codex 側 AGENTS.md 式指引**作為第二個「adapter」：沿用同一批 shell 腳本——腳本已 agent 無關，且載體光譜實證（文件層機制全失效過、腳本 14/14 從未失效）Codex 側更該把紀律放腳本。
3. **狀態檔路徑中性化（可選）**：registry 與統計檔是否搬離 ~/.claude/ 屬 cosmetic，動它要付六個消費端同步成本，另議。
4. **Codex 防線真空顯式決策**：Codex 無 PreToolUse 等價攔截點，ADR 017（git add 守門）／ADR 018 防線在 Codex 側退回「提醒」層（掃描層事後偵測仍在）。git add -A 夾帶、commit 邊界失誤這些有實證事故紀錄的失效形狀會在無守門環境重開——須顯式決定接受風險或限縮 Codex 角色（例如只當接手方、不碰軍師信箱歸檔）。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/（先定 Codex 角色邊界與防線真空的裁決，再定 spec 抽取範圍）
