---
title: ADR Candidate 001 — 純 skill＋範本；不建編譯型工具；不注入子 repo
date: 2026-07-06
type: adr
status: accepted
---

# ADR 001：純 skill＋範本；不建編譯型工具；不注入子 repo

> 狀態：**Accepted**（2026-07-06 經兩輪 doc-review 後由使用者審定）。

> **更名註記（2026-07-06）**：本文所稱 `/inbox`／`/init-planner`／`planner-registry.json`，於 rebrand 後對應 `/kunsu-inbox`／`/kunsu-init`／`kunsu-registry.json`，決策本文維持歷史原貌。見 [ADR 004](2026-07-06-adr-004-rebrand-kunsu.md)。

## Context

建立規劃中心的全部工作是：訪談參數 → 產生一組 markdown（骨架＋參數注入）→ 複製 Obsidian vault 設定 → `git init`。純文字生成加檔案複製。

先前嘗試 ce-team（Rust CLI）以編譯型工具處理同類需求，其路徑耦合來自四個設計決策：注入子 repo 的 managed section、依賴未實作的 launcher 展開佔位符、walk-up discovery 的同 workspace 假設、機器路徑存於被 gitignore 的設定檔。詳見種子需求文件「先前嘗試的教訓」一節。

反例是 ebook 規劃中心：零程式碼、純慣例，實際跑完兩個功能週期的多輪協作。其關鍵是依賴方向反轉——子 repo 完全不知道規劃中心存在，所有路徑集中於中心 CLAUDE.md 的一張表。

## Decision（proposed）

1. 交付物限定為：markdown 範本、skill 指令文件（SKILL.md）、少量膠水腳本（shell，附於 skill 內）。不建立需要獨立建置、測試、發版的工具專案。
2. 工具產出的規劃中心對其子專案唯讀；本工具亦不在任何目標 repo 寫入任何檔案或設定區塊。
3. 機器路徑只允許存在兩處：各規劃中心 CLAUDE.md 的關聯專案表（該中心的單一事實來源）、全域註冊表 `~/.claude/planner-registry.json`（反向索引，見 ADR Candidate 002）。
4. 不做任何形式的自動 discovery（walk-up 或其他）；路徑一律顯式登記。

## Consequences

- **正面**：無工具鏈依賴（不需 cargo／pip）；skill 由 Claude 執行，可在 scaffold 過程中即時查證子專案路徑與 CLAUDE.md 內容（編譯工具做不到）；子 repo 零污染，repo 搬家只改中心的一張表與註冊表一處。
- **負面／限制**：範本渲染由模型執行，確定性低於程式渲染（緩解：範本檔案隨 skill 附帶，指令要求逐字複製固定段落）；無法服務不跑 Claude Code 的使用情境（接受——目前唯一使用者的工作流即 Claude Code）。
- **結構不變量**：scaffold 產出必須保留以下結構，供 `/inbox`（見 ADR Candidate 002）正常運作：(1) `docs/handoffs/` 目錄，交接文件含 `to:` frontmatter；(2) `docs/handoffs/replies/` 目錄（內含 `.gitkeep` 佔位檔——git 不追蹤空目錄，無佔位檔則 clone／換機後目錄不會重建），回覆文件含 `in_reply_to:` frontmatter；(3) 規劃中心根目錄為 git repo（供 git status tripwire 使用）。`/init-planner` 的驗收步驟應逐項核查上述三項，而非僅目測輸出正確。

## Alternatives considered

- **編譯型 CLI（ce-team 路線）**：已實證失敗，耦合來源正是工具要管理的注入與 discovery 機制。
- **MCP server**：解決傳輸層而非觸發層痛點，且增加常駐 process 與設定負擔。明確延後，啟用訊號見 ADR Candidate 002。
