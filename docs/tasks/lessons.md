# 教訓紀錄

## 2026-10-05 ADR 是執行護欄，不是不可違反的憲法

- **情境**：盤點哪些 CLAUDE.md／skill 規則適合改成 Claude Code mod 時，把 ADR 019（Codex 對等）、ADR 018（提醒不跨阻止線）、Invariant 1（純 skill）直接當成「不改」的理由。
- **糾正**：ADR 的目的是讓 AI 執行時不偏離既定方向；遇到新能力（如 mod）時，應先評估「防住什麼事故 × 發生頻率」對「維護成本／覆蓋落差／API 漂移」的效益，再決定是遵循還是提修訂。拿 ADR 當結論等於放棄評估。
- **規則**：凡以「ADR／Invariant 規定」作為否決理由，必須同時寫出效益評估；若效益明顯高於成本，結論改為「提 ADR 修訂候選」，不是「不改」。

## 2026-10-05 找規則落點時漏查 git 全域 hooksPath

- **情境**：使用者說「push main/master 會要求加參數」，前一個 session 查了 `~/.claude/settings*.json`、hooks、rules、git alias 與 repo 的 `.git/hooks/pre-push` 都沒找到，回報「本機找不到」並提議用 mod 重做。
- **糾正**：規則在 `git config --global core.hooksPath` 指向的 `~/.config/git/hooks/pre-push`。全域 hooksPath 會整個取代 repo 的 `.git/hooks`，查 repo 內 hooks 看不到它。
- **規則**：查 git 行為的落點時，第一步先跑 `git config --show-origin --get-all core.hooksPath` 與 `git config --show-origin -l | grep -i hook`，再看 repo 內 `.git/hooks`；確認找不到之前不提「重做一份」。
