---
title: "feat: 將 /handoff skill 併入 planner-toolkit 維護與散布"
type: feat
status: completed
date: 2026-07-06
---

# feat: 將 /handoff skill 併入 planner-toolkit 維護與散布

## Summary

把全域 `/handoff` skill（v0.2.1，現僅存在於部署目錄 `~/.claude/skills/handoff`，無開發母體）的原始碼收進本 repo 作為第三個散布 skill：`skills/handoff/` 入庫、`install.sh` 納入部署、消除 README「已知硬依賴」缺口，並以 ADR 記錄整合決策。**純搬家，不改任何行為。**

## Problem Frame

`/planner-inbox` 解析的是 `/handoff` 寫出的檔案格式（協議與消費者關係），兩者分開發版必然產生 drift；且 handoff 目前只活在部署目錄，違反本 repo「開發與部署分離」的 Invariant 3 精神，也讓 planner-toolkit 開源後外部使用者缺硬依賴。handoff 當初即為跨 repo 協作而生，與 planner-toolkit 同屬一個問題域——使用者已定案整合（2026-07-06 對話）。`/init-obsidian-vault` 為工具耦合（介面乾淨、已有優雅降級、通用性明確），維持外部引用不整合。

## Requirements

- R1. `skills/handoff/` 內容與部署目錄現行 v0.2.1 **逐字一致**（SKILL.md＋兩支腳本），此後本 repo 為 handoff 的開發母體、`~/.claude/skills/` 為部署目標。
- R2. `install.sh` 部署三個 skill（handoff、init-planner、planner-inbox）；重複安裝冪等，既有行為（覆寫提示、`--link`、同源防呆）對 handoff 同樣生效。
- R3. 文件同步：README 移除「已知硬依賴」中 handoff 部分並將其列為內建 skill；CLAUDE.md 與 docs/README.md 結構與狀態更新；`skills/planner-inbox/SKILL.md` 的依賴聲明由「外部全域 skill」改為「同 toolkit 兄弟 skill，共同發版」。
- R4. 新增 ADR 003 記錄決策：handoff 併入散布（協議耦合）、init-obsidian-vault 維持外部（工具耦合）、命名維持 `/handoff` 不加前綴、隨 repo 以 MIT 散布。
- R5. 零行為變更：版本維持 0.2.1、觸發語不變；部署後以 smoke 驗證（實跑 new-handoff.sh 與 new-handoff-reply.sh）確認與整合前行為一致。

## Key Technical Decisions

- **權威來源與匯入方向**：以 `~/.claude/skills/handoff` 現行內容為唯一真實來源做一次性逐字匯入（已確認無其他原始碼備份）；此後方向反轉——repo 開發、install.sh 部署，與另外兩個 skill 同模式。
- **逐字匯入、不加註記**：不在 SKILL.md 內加「維護於 planner-toolkit」之類註記，避免匯入即產生內容差異；維護地資訊放 README 與 CLAUDE.md。
- **版本維持 0.2.1**：無行為變更不 bump；未來任何 handoff 改動（含 ADR 002 Decision 6 的 registry 升版）一律在本 repo 內進行並 bump。
- **命名維持 `/handoff`**（使用者定案）：`planner-` 前綴保留給離開 planner 體系即無意義的 skill（如 planner-inbox）；handoff 是通用交接原語，無前綴正確反映通用性，且既有規劃中心文件、範本、慣例文件與使用習慣零破壞。
- **ADR 003 直接以 accepted 寫入**：candidate→審定流程的目的（供使用者審視）已於本次對話完成（整合、命名、MIT 三項皆使用者明示定案），ADR 內註明定案脈絡。
- **開源就緒已查核**：handoff 三檔無機器特定內容（無絕對路徑、無使用者名、無私人專案名），可隨 MIT repo 直接公開。

## Implementation Units

### U1. 匯入 handoff 原始碼

- **Goal:** `skills/handoff/` 與部署目錄逐字一致，repo 成為開發母體。
- **Requirements:** R1、R5
- **Dependencies:** 無
- **Files:** `skills/handoff/SKILL.md`、`skills/handoff/scripts/new-handoff.sh`、`skills/handoff/scripts/new-handoff-reply.sh`
- **Approach:** 自 `~/.claude/skills/handoff` 整目錄複製入 repo，保留執行權限位。不做任何內容修改。
- **Test scenarios:**
  - 匯入後 `diff -r` repo 目錄 vs 部署目錄：零差異。
  - 兩支腳本執行權限位保留（`test -x`）。
- **Verification:** diff 零差異且權限正確。

### U2. install.sh 納入 handoff 並重新部署驗證

- **Goal:** 三個 skill 一鍵部署，行為冪等。
- **Requirements:** R2、R5
- **Dependencies:** U1
- **Files:** `install.sh`
- **Approach:** `SKILLS` 陣列加入 `handoff`；既有覆寫提示、`--link`、同源防呆邏輯自動涵蓋。另需更新 install.sh 末行 echo 訊息——原文硬編碼「/init-planner 與 /planner-inbox」，需將 `/handoff` 加入。重新部署後對 handoff 做 smoke 驗證。
- **Test scenarios:**
  - 部署後 `~/.claude/skills/handoff` 與 repo 版 diff 零差異（覆寫既有版本，內容相同故冪等）。
  - install.sh 末行 echo 明確列出三個 skill（/handoff、/init-planner、/planner-inbox）。
  - `--target` 隔離目錄測試：三個目錄皆部署。
  - Smoke：於暫存 git repo（含 CLAUDE.md）以部署後的 `new-handoff.sh` 建一份交接、`new-handoff-reply.sh` 建一份回覆，檔名與 frontmatter 符合 v0.2.1 既有慣例；planner-inbox 的狀態推導對其正常運作。
- **Verification:** smoke 全過，與整合前行為無差異。

### U3. 文件同步

- **Goal:** 依賴描述全面改為「內建兄弟 skill」，散布故事完整。
- **Requirements:** R3
- **Dependencies:** U1、U2
- **Files:** `README.md`、`CLAUDE.md`、`docs/README.md`、`skills/planner-inbox/SKILL.md`
- **Approach:** README——skill 對照表加 `/handoff` 列、安裝節「已知依賴」註記改寫（handoff 移除、僅剩 init-obsidian-vault 可降級說明）、專案結構樹加 `skills/handoff/`、快速開始第 2 步「以全域 `/handoff` skill」移除「全域」修飾詞；CLAUDE.md——結構樹與開發狀態，並刪除「相關資產（唯讀參考）」表格中的 handoff 列（維護地資訊由結構樹與開發狀態承載，該表回歸真正外部資產）；docs/README.md——目前狀態補記，並在文件清單加入 ADR 003 條目（與 U4 產出同步）；planner-inbox SKILL.md——依賴聲明段改為「同 toolkit 內建 `/handoff`（v0.2.1），共同發版，慣例定義以本 repo 為準」。`skills/init-planner/assets/templates/planner-claude.md` 對 `/handoff` 的引用不需改（部署位置與指令名皆不變）。
- **Test scenarios:** Test expectation: none — 純文件同步；以連結與路徑正確性人工核對代替。
- **Verification:** 全 repo grep「已知依賴」「外部全域 skill」與「全域.*handoff」對 handoff 的過時描述無殘留。

### U4. ADR 003 整合決策紀錄

- **Goal:** 決策依據可追溯。
- **Requirements:** R4
- **Dependencies:** 無（可與 U1 平行）
- **Files:** `docs/adr/2026-07-06-adr-003-integrate-handoff-into-toolkit.md`
- **Approach:** 記錄：Context（協議耦合 vs 工具耦合的分析、開發與部署分離缺口、開源依賴缺口）、Decision（handoff 併入；init-obsidian-vault 維持外部；命名維持 `/handoff`；MIT 散布；版本延續 0.2.1）、Consequences（drift 風險結構性消除；handoff 改動走 repo 流程；toolkit 自包含）、Alternatives（skills monorepo 全收——過度重組；vendor 複製——重蹈同步耦合；維持外部——開源缺口不解）。狀態 accepted，註明 2026-07-06 對話定案。docs/README.md 文件清單同步（併入 U3 的編輯）。
- **Test scenarios:** Test expectation: none — 純文件。
- **Verification:** ADR 涵蓋四項定案與否決理由。

## Scope Boundaries

### Deferred to Follow-Up Work

- handoff 升版改查註冊表（根治 cd 陷阱）——維持 ADR 002 Decision 6 的獨立延後決策；本次整合為其未來執行掃清了維護地問題，但不觸發它。
- `/init-obsidian-vault` 的獨立化或散布安排——維持外部引用（本計畫 ADR 003 記錄理由）。

### Outside this product's identity

- 對 handoff 的任何行為修改（觸發語、frontmatter 欄位、命名規則、status 值域）——本次為純搬家。

## Risks & Dependencies

- **部署目錄與 repo 的雙寫風險**：整合後若忘記「改 repo 再 install」而直接改部署目錄，drift 重現。緩解：CLAUDE.md 開發狀態註明維護地；開發期可用 `install.sh --link`。
- **既有規劃中心（ebook）引用不受影響**：指令名與部署位置皆不變，零遷移動作——此為維持命名決策的直接收益。

## Sources & Research

- 部署目錄盤點（2026-07-06）：`~/.claude/skills/handoff` 共 3 檔 498 行（SKILL.md 241、new-handoff.sh 138、new-handoff-reply.sh 119）；隱私掃描僅一處通用「Android session」示例，無機器特定內容。
- 本 session 稍早的 handoff 深度研究：v0.2.1 frontmatter 結構、腳本行為、回覆命名與 status 慣例（見 docs/plans/2026-07-06-001 的 Sources 節）。
- 協議耦合 vs 工具耦合的分析與使用者定案：2026-07-06 對話。
