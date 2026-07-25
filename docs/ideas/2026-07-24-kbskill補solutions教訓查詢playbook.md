---
title: kb skill 補 solutions 教訓查詢 playbook
type: idea
status: promoted
brainstorm: docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md
created: 2026-07-24
tags: [idea, kb, solutions]
---

# kb skill 補 solutions 教訓查詢 playbook

kb skill 現有 playbook 只有「找 repo」「搜代碼」兩類，補第三類「搜教訓」：docs/solutions/ 的 query 模板（`f:docs/solutions/`）、frontmatter 過濾技巧（problem_type／module／tags）、以及「本地熱區查無再翻 archive 冷區」的兩層檢索慣例。

## 背景 / 動機

kb skill 原始碼屬 tshehtu 專案（開發部署分離），落地應改 tshehtu repo 再 install，不直接改 ~/.claude/skills/kb。此為 zoekt 跨 repo 複利接線三點之一，讓任何 session 都知道「搜教訓」這條路存在。

## 落地研究（2026-07-24）

- 部署方式已確認：`~/.claude/skills/kb` 是 **symlink** → `/Users/kasingkhoo/Documents_local/Obsidian 專案/tshehtu/skill/kb`（開發模式）——改 tshehtu repo 內的 `skill/kb/SKILL.md` 即時生效，免 install 步驟。tshehtu 為獨立 git repo。
- 改動形狀：SKILL.md 查詢 playbook 新增「### 搜教訓（跨 repo solutions）」段——query 模板（`f:docs/solutions/ 關鍵字`、`problem_type:`／`tags:`／`module:` frontmatter 過濾）、兩層檢索慣例（預設查頂層熱區、需要時以 `f:docs/solutions/.*archive` 翻冷區）、回報時沿用既有「附索引新鮮度」慣例。純文件改動、零腳本。
- 順帶發現 tshehtu 兩個既有問題（本次不修，應於該 repo 記 todo）：
  1. `~/.tshehtu/project-dir` **不存在**——SKILL.md 故障排除段的 `$(cat ~/.tshehtu/project-dir)` 指令會失敗，手動重建索引指引實際不可用。
  2. `inventory.json`／`repos.txt` 停留在 2026-07-07，但索引 log 今天有跑——推測每小時排程只重建既有清單的索引，discovery（新 repo 發現）未入排程；7/7 之後新建的 repo 可能不在 inventory 與索引內。

## 下一步

- [x] 確認 tshehtu repo 位置與 kb SKILL.md 部署方式（symlink／copy）→ symlink 開發模式，見上方落地研究
- [ ] 於 tshehtu repo 記兩筆 todo（project-dir 缺失、discovery 未入排程）
- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
