---
status: 未處理
date: 2026-09-28
source: 2026-09-27 前段遺留
severity: medium
---

# Codex 側 UserPromptSubmit hook 實測與 ADR 019 試點單輪全綠

兩件前段遺留：（1）Codex 側 UserPromptSubmit hook 實測——~/.codex/hooks.json 現無任何 kunsu 條目，須先掛既有兩支（SessionStart、PreToolUse）再加 prompt_inbox_hook.py，以 codex exec 實收確認純文字注入（kunsu-inbox v0.14.0 的 Codex 假設尚未本機驗證）；（2）ADR 019 試點補跑——跑 scripts/codex-pilot.sh 取單輪全綠（額度 9/27 已恢復），據以請使用者審定 ADR 019 status（現仍 proposed）。

## 相關檔案


## 待辦方向

