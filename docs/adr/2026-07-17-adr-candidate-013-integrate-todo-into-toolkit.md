---
title: ADR 013 — `/todo` skill 併入 kunsu toolkit 維護與散布
date: 2026-07-17
type: adr
status: accepted
---

# ADR 013：`/todo` skill 併入 kunsu toolkit 維護與散布

> 狀態：**Accepted**（2026-07-17 於軍師沙盤 todo 列表顯示需求 brainstorm 對話中定案，比照 ADR 003 handoff 併入先例）。

## Context

軍師沙盤（kunsu-dashboard）要新增讀取各軍師自己 `docs/todos/` 技術債清單的功能，需要長期解析全域 `/todo` skill（現僅存在於部署目錄 `~/.claude/skills/todo/`，無開發母體）產出的檔案格式（frontmatter 的 status／date／source／severity）。這與 ADR 003 當初併入 `/handoff` 的處境相同：

- **功能耦合**：沙盤的 `docs/todos/` 解析邏輯依賴 `/todo` 的 frontmatter 契約與 `done`／`rm` 的 `git mv` 歸檔慣例，格式與消費者分開發版必然產生 drift。
- **開發與部署分離缺口**：`/todo` 原始碼只存在於部署目錄，違反本 repo Invariant 3「開發與部署分離」的精神。
- **開源硬依賴缺口**：kunsu 以 MIT 開源後，外部使用者若未另外安裝 `/todo`，軍師沙盤的待辦技術債功能將無法運作。

## Decision

1. **`/todo` 併入 kunsu toolkit**：原始碼自部署目錄一次性逐字匯入 `skills/todo/`（以現行 v0.1.1 為唯一真實來源），此後本 repo 為開發母體、`install.sh` 為部署途徑，與既有六個 skill 同模式。
2. **命名維持 `todo`，不加 `kunsu-` 前綴**：`kunsu-` 前綴保留給離開 kunsu 體系即無意義的 skill（如 `kunsu-init`、`kunsu-inbox`）；`todo` 是通用技術債管理原語，單一 repo 專案亦可獨立使用，無前綴正確反映通用性，比照 `handoff` 的命名判斷（ADR 003 Decision 3）。
3. **隨 repo 以 MIT 散布**：`todo` 兩檔（`SKILL.md`、`scripts/new-todo.sh`）經隱私掃描無機器特定內容，可公開。
4. **版本延續 0.1.1，本次零行為變更**：純搬家，不改任何觸發詞或子指令行為；未來若改動 `/todo` 本身才在本 repo 內進行並 bump 版號。

## Consequences

- **正面**：格式與消費者（軍師沙盤的 `todo_status.py`）同源發版，drift 結構性消除；toolkit 自包含，開源後開箱即用；`/todo` 取得開發母體與版控歷史。
- **負面／限制**：使用者若忘記「改 repo 再 install」而直接改部署目錄，drift 會重現（緩解：開發期用 `install.sh --link`；`CLAUDE.md` 明載維護地）；`/todo` 的通用用途（非 kunsu 專案的技術債記錄）從此跟隨 kunsu toolkit 的發版節奏。

## Alternatives considered

- **維持外部依賴，僅在沙盤端加註解說明耦合**：開發與部署分離缺口、開源硬依賴缺口均不解，drift 風險常存。否決。
- **vendor 複製**（kunsu 內放 `/todo` 副本、全域另有一份原版）：兩份原始碼需人工同步，重蹈已知的多份注入區塊同步耦合教訓（比照 ADR 003 否決理由）。否決。
- **改名 `kunsu-todo` 求前綴一致**：需同步改動觸發詞、既有使用習慣，一致化收益純屬美觀，且與 `handoff` 已建立的「通用原語不加前綴」慣例矛盾。否決。
