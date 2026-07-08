# 文件中心索引

kunsu 專案的文件集合。專案定位與核心規範見上層 [CLAUDE.md](../CLAUDE.md)。

## 子目錄說明

| 目錄 | 內容 | 產出指令 |
|------|------|----------|
| `brainstorms/` | 需求與構想 | `/ce-brainstorm`（種子文件為手工彙整） |
| `plans/` | 實作計畫 | `/ce-plan` |
| `adr/` | 架構決策紀錄與候選 | 先產出 Candidate，審定後正式化 |

## 目前狀態

- **種子階段（2026-07-06）**：需求文件與兩份 ADR 已就位，皆源自 ebook 規劃中心 session 的設計討論。
- **ADR 已審定（2026-07-06）**：兩份 ADR 經兩輪 `/ce-doc-review`（5 persona）修訂後拍板為 accepted；剩餘規格細節記於 ADR 002 的 Deferred / Open Questions 與審查報告。
- **實作完成（2026-07-06）**：`/kunsu-init`（含 add-project）、`/kunsu-inbox`、`install.sh` 三件交付物完成並通過 19 場景端到端 dogfooding 驗證，已部署至 `~/.claude/skills/`。
- **handoff 併入（2026-07-06）**：`/handoff` skill（v0.2.1）自部署目錄逐字併入 `skills/handoff/` 隨 toolkit 共同維護與散布，硬依賴缺口消除（ADR 003）。
- **詞彙統一（2026-07-07）**：scaffold 產物正式改稱「軍師」；SKILL.md 文案、腳本訊息、範本（檔名 `planner-*` → `kunsu-*`）、solutions、註冊表欄位 `planner` → `kunsu` 全面遷移（ADR 005）。
- **申請信箱（2026-07-07）**：例外授權擴為雙信箱——scaffold 內建 `docs/applications/`，新增 `/kunsu-apply` 子專案端投遞 skill，`add-project` 改為掃描審核制（核准當下單點登記），`/kunsu-inbox` 軍師模式一併回報新申請（ADR 006 candidate）。
- **角色識別正規化（2026-07-08）**：「角色」拆為**角色代碼**（比對鍵）與**角色說明**（display-only）；範本雙欄、CONCEPTS 拆詞、四支 SKILL＋`registry-merge.sh` 軟警告＋`add-project` 唯一性權威強制點，並遷移 ivm／ebook 兩軍師 live registry 與 CLAUDE.md（**修復 ivm `/kunsu-inbox` false-negative**）。經兩輪 `/ce-doc-review`（15 項修正）審定（ADR 007 accepted）。
- **下一步**：於真實專案群首輪使用 `/kunsu-init` 建立軍師（如 ebook 中心加入 iOS 時的 add-project 案例），累積手感後評估 SessionStart hook（ADR 002 第二階段）。

## 文件清單

| 文件 | 說明 |
|------|------|
| [brainstorms/2026-07-06-planner-toolkit-requirements.md](brainstorms/2026-07-06-planner-toolkit-requirements.md) | 種子需求：問題定義、觸點拆解、ce-team 教訓、ebook 母本解剖、方案設計、開放問題 |
| [adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md](adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md) | ADR 001（accepted）：純 skill＋範本，不建編譯工具、不注入子 repo |
| [adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md](adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) | ADR 002（accepted）：傳令自動化採反向註冊表＋/inbox，hook 第二階段，MCP 延後 |
| [adr/2026-07-06-adr-003-integrate-handoff-into-toolkit.md](adr/2026-07-06-adr-003-integrate-handoff-into-toolkit.md) | ADR 003（accepted）：/handoff 併入 toolkit 維護與散布；/init-obsidian-vault 維持外部 |
| [adr/2026-07-06-adr-004-rebrand-kunsu.md](adr/2026-07-06-adr-004-rebrand-kunsu.md) | ADR 004（accepted）：rebrand 為 kunsu（軍師），體系 skill 改 kunsu- 前綴，/handoff 不變 |
| [adr/2026-07-07-adr-candidate-005-unify-kunsu-terminology.md](adr/2026-07-07-adr-candidate-005-unify-kunsu-terminology.md) | ADR 005（accepted）：詞彙統一，scaffold 產物正式稱「軍師」，機器識別字趁零部署窗口一併改 |
| [adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md](adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md) | ADR 006（proposed）：申請信箱——例外授權擴為雙信箱，投遞與審核分離、單點登記 |
| [adr/2026-07-08-adr-candidate-007-role-code-description-separation.md](adr/2026-07-08-adr-candidate-007-role-code-description-separation.md) | ADR 007（accepted）：角色識別正規化——角色代碼（比對鍵）與角色說明（描述）分離 |
| [brainstorms/2026-07-07-application-inbox-requirements.md](brainstorms/2026-07-07-application-inbox-requirements.md) | 需求：申請信箱與 add-project 對話式改造（R1–R15、驗收例） |
| [plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md) | 實作計畫：kunsu-init 與 kunsu-inbox skill 工具組（已執行完畢） |
| [plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md](plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md) | 實作計畫：/handoff 併入 toolkit（已執行完畢） |
| [plans/2026-07-07-001-feat-application-inbox-plan.md](plans/2026-07-07-001-feat-application-inbox-plan.md) | 實作計畫：申請信箱（R1–R20、六個實作單元） |
| [plans/2026-07-08-001-refactor-role-code-description-separation-plan.md](plans/2026-07-08-001-refactor-role-code-description-separation-plan.md) | 實作計畫：角色代碼／說明分離（R1–R22、九個實作單元，已執行完畢） |
