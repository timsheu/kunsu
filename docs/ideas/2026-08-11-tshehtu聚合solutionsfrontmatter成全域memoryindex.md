---
title: tshehtu 聚合 solutions frontmatter 成全域 memory index
type: idea
status: closed
created: 2026-08-11
tags: [idea, memory, tshehtu, kb]
---

# tshehtu 聚合 solutions frontmatter 成全域 memory index

各 repo docs/solutions/ 本來就有 YAML frontmatter（module／tags／problem_type），tshehtu discovery 掃描時順手聚合成一份全域 memory index（純 JSON、標準庫可做），kb skill 即可回答「所有 repo 裡關於 X 類問題的教訓有哪些」——從 zoekt 字面搜尋升級成按經驗類型檢索，不引入 Vector DB。

## 背景 / 動機

「搜得到相關，搜不出因果」是 lexical 搜尋的天花板；metadata 檢索是零新依賴的升級路徑。落點在 tshehtu repo（本檔僅為發想登記，實作時於 tshehtu 開工）。

## 查證結論（2026-08-12，縮減落地）

實測查證後，原構想的聚合 JSON index 判定冗餘、縮減為 kb playbook 補充並已落地：

- **列舉與彙整能力 zoekt 已有**：一發查詢列舉全機 64 篇 solutions（12 repos）；欄位字面查詢＋客端解析即得 metadata 值分布與檔案清單。frontmatter schema 跨 repo 高度一致（63/64 有 `problem_type:`），queries 可通用。
- **聚合 JSON 的實際增量極小**：僅預計算與離線可用性（kb 已內建健康檢查／重啟），且同樣繼承「discovery 未入排程」的新鮮度限制，維護成本不對等。
- **真缺口是 playbook 沒教彙整模式**：已在 tshehtu `skill/kb/SKILL.md` 第 4 節補「彙整模式」query 範本（欄位字面查詢＋客端聚合，範本實跑驗證通過）與「彙整值域開放」慣例要點，symlink 部署即改即生效。此補充順帶實質推進 kunsu backlog「跨 repo solutions 檢索外環」，未動全域 CLAUDE.md。
