---
title: 軍師派發交接前以 kb 掃相關 solutions 附進交接本體
type: idea
status: promoted
brainstorm: docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md
created: 2026-07-24
tags: [idea, kb, kunsu, handoff]
---

# 軍師派發交接前以 kb 掃相關 solutions 附進交接本體

軍師撰寫交接文件時，先用 /kb（zoekt）掃相關主題，把其他 repo 的相關 solution 連結附進交接本體的參考段。純讀取，軍師唯讀原則（Invariant 2）零改動；接手方一開工就帶著全機既有經驗。

## 背景 / 動機

zoekt 索引已涵蓋全機 docs/solutions/（2026-07-24 驗證 42 篇命中）。落點推測為 kunsu-init 軍師範本 CLAUDE.md 的工作流程段（新增派發前查 kb 步驟），以及 ebook／ivm 兩個 live 軍師的同步遷移。kb 為軟依賴（未安裝 tshehtu 時應可略過），需在範本措辭中處理。

## 落地研究（2026-07-24）

- 插入點已確認：範本 `skills/kunsu-init/assets/templates/kunsu-claude.md` 工作流程段——
  - 第 2 步「評估技術可行性」：查閱子專案文件時，順手以 kb 掃相關教訓（提早進入規劃視野）。
  - 第 5 步「拆解為交接文件」的「須包含」清單：加一項「相關既有教訓（選附）——kb 掃 `f:docs/solutions/` 相關主題，他 repo 的相關 solution 以 repo 名＋路徑列入參考段」。兩處擇一或並用，以第 5 步為最小改動。
- 軟依賴措辭比照既有先例：kunsu CLAUDE.md 相關資產表的 `init-obsidian-vault`「軟依賴，未安裝時略過」——kb 未安裝或 zoekt 服務未啟動（curl 健康檢查失敗）即略過此步，不阻斷派發流程。
- 範圍決策：**通用 `/handoff` skill 不動**（它服務非 kunsu 場景，不該綁 kb 依賴），改動限於軍師範本＝慣例層、零腳本。
- 連帶工作：ebook（`project/planner/ebook`）／ivm 兩個 live 軍師 CLAUDE.md 同步遷移（比照歷次 live 遷移慣例，各一筆確認 commit）；kunsu 母體 CLAUDE.md 開發狀態同步。

## 下一步

- [x] 確認範本工作流程段的插入位置與軟依賴措辭 → 見上方落地研究
- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/（三個接線點中唯一動 kunsu 範本者，建議走正規流程）
