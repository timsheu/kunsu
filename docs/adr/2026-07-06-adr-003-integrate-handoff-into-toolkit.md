---
title: ADR 003 — /handoff skill 併入 planner-toolkit 維護與散布；/init-obsidian-vault 維持外部
date: 2026-07-06
type: adr
status: accepted
---

# ADR 003：/handoff skill 併入 planner-toolkit 維護與散布

> 狀態：**Accepted**（2026-07-06 由使用者於設計對話中定案：整合、命名維持、MIT 散布三項均為明示決定）。

> **更名註記（2026-07-06）**：本文所稱 `/inbox`／`/init-planner`／`planner-registry.json`，於 rebrand 後對應 `/kunsu-inbox`／`/kunsu-init`／`kunsu-registry.json`，決策本文維持歷史原貌。見 [ADR 004](2026-07-06-adr-004-rebrand-kunsu.md)。

## Context

planner-toolkit 完成首版實作後，README 標注了兩個外部依賴：全域 `/handoff` skill（硬依賴——`/planner-inbox` 解析其寫出的檔案格式）與全域 `/init-obsidian-vault` skill（軟依賴——未安裝時優雅降級）。兩個依賴的耦合性質不同：

- **`/handoff` 是協議耦合**：`/planner-inbox` 的狀態推導依賴 handoff 的回覆檔命名規則（`{原檔名}-reply-YYYY-MM-DD[-N].md`）、frontmatter 欄位（`in_reply_to` 含 `.md` 後綴）與 status 值域——協議與消費者分開發版必然產生 drift。且 handoff 當初即為跨 repo 協作而生，與 planner-toolkit 同屬一個問題域。
- **`/init-obsidian-vault` 是工具耦合**：介面乾淨（`init-vault.sh --target ...`）、已有優雅降級、且在非 planner 場景（一般專案 vault 初始化）有獨立用途。

另有兩個結構性問題：handoff 原始碼只存在於部署目錄 `~/.claude/skills/handoff`（無開發母體，違反本 repo「開發與部署分離」Invariant 3 的精神）；planner-toolkit 以 MIT 開源後，外部使用者將缺硬依賴。

## Decision

1. **`/handoff` 併入 planner-toolkit**：原始碼自部署目錄一次性逐字匯入 `skills/handoff/`（以現行 v0.2.1 為唯一真實來源），此後本 repo 為開發母體、`install.sh` 為部署途徑，與另外兩個 skill 同模式。與 `/planner-inbox` 共同發版，協議 drift 風險結構性消除。
2. **`/init-obsidian-vault` 維持外部引用**：不整合。`/init-planner` 保留「未安裝即略過」的降級行為。
3. **命名維持 `/handoff`，不加 `planner-` 前綴**：`planner-` 前綴保留給離開 planner 體系即無意義的 skill（如 `planner-inbox`）；handoff 是通用交接原語，單 repo 專案亦可用，無前綴正確反映通用性，且既有規劃中心文件、範本、慣例文件與使用習慣零破壞。
4. **隨 repo 以 MIT 散布**：handoff 三檔經隱私掃描無機器特定內容，可公開。
5. **版本延續 0.2.1，本次零行為變更**：純搬家；未來任何 handoff 改動（含 ADR 002 Decision 6 的註冊表升版）一律在本 repo 內進行並 bump 版號。

## Consequences

- **正面**：協議與消費者同源發版，drift 結構性消除；toolkit 自包含，開源後開箱即用；handoff 取得開發母體與版控歷史；ADR 002 Decision 6 的未來升版有了明確的施工地點。
- **負面／限制**：使用者若忘記「改 repo 再 install」而直接改部署目錄，drift 會重現（緩解：開發期用 `install.sh --link`；CLAUDE.md 明載維護地）；handoff 的通用用途（非 planner 專案）從此跟隨 planner-toolkit 的發版節奏。

## Alternatives considered

- **skills monorepo 全收**（把 init-obsidian-vault 等全域 skill 一併收進單一 repo，仿 `~/.claude/rules` 模式）：可行但屬過度重組——目前只有協議耦合的 handoff 有整合的結構性理由。留作未來選項。
- **vendor 複製**（planner-toolkit 內放 handoff 副本、全域另有一份原版）：兩份原始碼需人工同步，重蹈 ce-team「同步 N 份注入區塊」的耦合教訓。否決。
- **維持外部依賴**：開發與部署分離缺口、開源硬依賴缺口均不解，drift 風險常存。否決。
- **改名 `planner-handoff` 求前綴一致**：需同步改動範本、solutions 種子、planner-inbox 依賴聲明、ebook 中心既有文件與使用習慣，一致化收益純屬美觀。否決。
