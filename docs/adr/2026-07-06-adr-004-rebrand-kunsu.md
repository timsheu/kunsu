---
title: ADR 004 — Rebrand 為 kunsu（軍師）：repo 改名、體系專屬 skill 改 kunsu- 前綴、/handoff 不變
date: 2026-07-06
type: adr
status: accepted
---

# ADR 004：Rebrand 為 kunsu（軍師）

> 狀態：**Accepted**（2026-07-06 由使用者定案：名稱 kunsu、混合前綴制均為明示決定）。

> **補充註記（2026-07-07）**：本 ADR 的命名故事原將「軍師」指向工具組本體，scaffold 產物仍沿稱「規劃中心」（「`/kunsu-init` 建中心」）。2026-07-07 使用者指示名稱統一以避免誤解：scaffold 產物本身亦正式改稱「軍師」，README 與 `/kunsu-init` 觸發語已先行完成，全面遷移提案見 [ADR Candidate 005](2026-07-07-adr-candidate-005-unify-kunsu-terminology.md)。決策本文維持歷史原貌。

## Context

原名 planner-toolkit 過於通用——搜尋辨識度低、無品牌記憶點，開源後難以識別。使用者提出台語羅馬字 **kunsu**（軍師，Tâi-lô *kun-su*）：「運籌帷幄而不上陣」與本工具「唯讀規劃、絕不執行」的世界觀精準對應。GitHub 撞名檢查乾淨（無成型專案使用此名）。

repo 改名後浮現前綴一致性問題：skill 名（`init-planner`、`planner-inbox`、`handoff`）與品牌斷層，且部署進扁平的 `~/.claude/skills/` 時，通用名有命名空間碰撞風險。

## Decision

1. **repo 改名 `kunsu`**；README 標題保留台語出處：kunsu（軍師 / kun-su, "the strategist"）。
2. **體系專屬 skill 改 `kunsu-` 前綴**：`/init-planner` → `/kunsu-init`、`/planner-inbox` → `/kunsu-inbox`。前綴回答「這指令屬於哪個工具」、提供命名空間安全，且 `/kunsu-inbox` 比原名更短。
3. **`/handoff` 維持不變**：通用交接原語的定位不因 rebrand 而變（ADR 003 Decision 3 的理由持續有效）；ebook 中心既有引用零破壞。
4. **全域註冊表改名 `~/.claude/kunsu-registry.json`**：趁檔案尚不存在（dogfooding 後已清理、無真實部署）零成本改名。
5. **歷史文件不改寫**：ADR 001–003 決策本文維持原貌、各加更名註記指向本 ADR；docs/plans 與 docs/brainstorms 為歷史快照不動（含檔名）。

命名故事：**kunsu（軍師）是本體；`/kunsu-init` 建中心、`/kunsu-inbox` 傳令；`/handoff` 是軍師與各營共用的公文格式。**

## Consequences

- **正面**：品牌識別度與命名空間安全同時解決；skill 名自帶所屬工具資訊；改名時點在開源前、零 commit 遠端、零外部使用者，成本最低。
- **負面／限制**：非中文使用者無法望文生義（緩解：README 首行一句出處說明；先例：Kubernetes、kanban 等非英語名）；本機既有部署的舊目錄（`init-planner`、`planner-inbox`）需清除後重新部署，避免新舊 skill 並存造成重複觸發。

## Alternatives considered

- **planner-hq／planrelay 等英語名**：辨識度可，但隱喻契合度均不及「軍師」，且缺乏在地敘事的差異化。否決。
- **全部加前綴（含 `/kunsu-handoff`）**：破壞 /handoff 通用性與 ebook 中心既有引用，ADR 003 已否決過一次。否決。
- **全部不改（kunsu 僅作 repo 名）**：可行（如 ripgrep → rg 慣例），但放棄命名空間安全與品牌一致性，而此刻改名成本趨近零。否決。
