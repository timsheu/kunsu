---
status: 已解決
date: 2026-09-28
source: 2026-09-27 前段遺留
severity: medium
---

# Codex 側 UserPromptSubmit hook 實測與 ADR 019 試點單輪全綠

**解決依據**：2026-10-03：(2) codex-pilot.sh 單輪 25/25 全綠、ADR 019 同日審定 accepted（docs/adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md）；(1) 三支 hook 已附加至 ~/.codex/hooks.json，UserPromptSubmit 以 codex exec -c 注入於 ebook 軍師 repo 實收純文字注入成功（codex-cli 0.154.0）；殘項（TUI 信任與壞條目清理）轉出 docs/todos/Codex-TUI-信任三支-kunsu-hook-並清理-hooksjson-壞條目.md


兩件前段遺留：（1）Codex 側 UserPromptSubmit hook 實測——~/.codex/hooks.json 現無任何 kunsu 條目，須先掛既有兩支（SessionStart、PreToolUse）再加 prompt_inbox_hook.py，以 codex exec 實收確認純文字注入（kunsu-inbox v0.14.0 的 Codex 假設尚未本機驗證）；（2）ADR 019 試點補跑——跑 scripts/codex-pilot.sh 取單輪全綠（額度 9/27 已恢復），據以請使用者審定 ADR 019 status（現仍 proposed）。

## 相關檔案


## 待辦方向

