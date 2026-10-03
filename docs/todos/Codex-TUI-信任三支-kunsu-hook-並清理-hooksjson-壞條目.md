---
status: 未處理
date: 2026-10-03
source: 2026-10-03 todo 收尾殘項轉出
severity: medium
---

# Codex TUI 信任三支 kunsu hook 並清理 hooks.json 壞條目

轉出自 docs/todos/archive/Codex-側-UserPromptSubmit-hook-實測與-ADR-019-試點單輪全綠.md 的殘項：三支 kunsu hook 已於 2026-10-03 附加至 ~/.codex/hooks.json 尾端（SessionStart／UserPromptSubmit／PreToolUse），但 Codex 信任鍵（config.toml hooks.state）須在 TUI 內以 /hooks 由使用者親手信任，未信任前三支靜默略過、consistency-check N 項持續 WARN。另 ~/.codex/hooks.json 內有兩條指向已移除 everything-claude-code plugin 的壞條目（PreToolUse 群組 0、PostToolUse 群組 0），清理會使其後群組索引漂移、須重新信任，故與信任步驟一併處理。

## 待辦方向

1. 使用者於 Codex TUI 執行 /hooks，信任三支 kunsu 條目（或先刪兩條壞條目再信任全部）。
2. 信任後跑 `bash scripts/consistency-check.sh`，N 項應 PASS。
3. 真實路徑軍師 repo 開一次 Codex TUI session，確認 SessionStart 摘要出現（playbook 手動核對清單第 1、2 項）。

## 相關檔案

