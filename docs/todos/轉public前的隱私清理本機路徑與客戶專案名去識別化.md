---
status: 未處理
date: 2026-07-08
source: manual
severity: high
---

# 轉 public 前的隱私清理：本機路徑與客戶專案名去識別化

repo 目前為 GitHub private，轉 public 前需完成隱私清理。已 commit 檔案含本機絕對路徑（/Users/<使用者名稱>/...）、使用者名稱與客戶專案名（已去識別化）、ebook 母本路徑，且同樣存在於歷史 commit 中。

## 相關檔案

- `CLAUDE.md`（相關資產表：ebook 母本、ce-team vault 絕對路徑；核心規範 4 母本路徑）
- `docs/brainstorms/2026-07-06-planner-toolkit-requirements.md`（母本解剖與 ce-team 教訓段的絕對路徑）
- `docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md`（來源引用的絕對路徑）
- `skills/kunsu-init/SKILL.md`（設計備註：範本固定段落來源的母本絕對路徑）
- git 歷史全部 commit（上述內容自初始 commit 起即存在）

## 待辦方向

- 決策一：歷史處理——改寫歷史（git filter-repo／新開孤兒分支重建）或接受歷史留存、只清理現行檔案
- 決策二：現行檔案清理——絕對路徑改為相對描述或佔位符（如「母本規劃中心（本機路徑，略）」），客戶專案名去識別化
- 檢查遺漏：轉 public 前再跑一次 grep -r '/Users/' 與使用者名稱全 repo 掃描（含 .obsidian 設定）
- 順帶確認：docs/solutions/ 與 CONCEPTS.md 已確認無敏感內容，無需處理
