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
- **/handoff reply 路由補洞（2026-07-08，v0.3.0）**：子專案口語「回覆軍師」未命中任何 skill、回覆錯投軍師 `docs/handoffs/` 頂層（tripwire 如設計攔截）。修補三處：description 觸發詞補口語、reply 新增 kunsu 語境分支（未給 slug 時查 registry 定位軍師與待回交接）、`new-handoff-reply.sh` 落點改從原交接檔位置推算（跨 repo 回覆保證落在軍師 `replies/`，含 archive 與非 handoffs 路徑防呆），五場景實測通過。
- **上報信箱提案（2026-07-08）**：孤兒回覆事件暴露「子專案主動上報」無正式管道，起草 ADR 008 candidate——例外授權擴為三信箱（`docs/reports/`）、以「有無對應交接」結構判準分界 reply／report、中文定名「上報」（口語「回報」偏 reply 故歸 reply 觸發，「稟報軍師」列 report 觸發別名）、雙向重導兜底灰帶、`/kunsu-report` 投遞 skill，待審定後另立實作計畫。
- **上報信箱落地（2026-07-09）**：ADR 008 全量實作——`/kunsu-report`、`scan-reports.sh`、`/kunsu-inbox` 第三段、scaffold 與 add-project 三信箱化、母體同步、ivm／ebook live 遷移與 ivm 孤兒上報歸位；八單元 maker（sonnet）／verifier 分離執行、dogfooding 全過（[實作計畫](plans/2026-07-08-002-feat-report-inbox-plan.md)）。
- **協議 commit 逐次確認制（2026-07-10）**：ADR 009 落地——流程尾端 commit 升格為 AskUserQuestion 確認制（handoff v0.4.0、kunsu-init v0.2.0、kunsu-inbox v0.3.0），投遞端不對稱維持；`scan-replies.sh` 補 done 授權歸檔豁免（雙側核驗三形狀、RM 陷阱實測修正）；範本與 ivm／ebook 兩軍師 live 遷移；fixture 十四場景＋e2e dogfooding 九場景全過（[實作計畫](plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md)）。
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
| [adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md](adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md) | ADR 006（accepted）：申請信箱——例外授權擴為雙信箱，投遞與審核分離、單點登記（「僅有的兩個」語義後由 ADR 008 修訂為三） |
| [adr/2026-07-08-adr-candidate-007-role-code-description-separation.md](adr/2026-07-08-adr-candidate-007-role-code-description-separation.md) | ADR 007（accepted）：角色識別正規化——角色代碼（比對鍵）與角色說明（描述）分離 |
| [adr/2026-07-08-adr-candidate-008-report-inbox-triple-mailbox.md](adr/2026-07-08-adr-candidate-008-report-inbox-triple-mailbox.md) | ADR 008（accepted）：上報信箱——例外授權擴為三信箱，子專案主動上報入軍師記錄 |
| [adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md](adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md) | ADR 009（accepted）：協議 commit 逐次確認制——確認 commit 升格協議步驟、投遞端不對稱維持、handoffs 授權歸檔豁免 |
| [brainstorms/2026-07-07-application-inbox-requirements.md](brainstorms/2026-07-07-application-inbox-requirements.md) | 需求：申請信箱與 add-project 對話式改造（R1–R15、驗收例） |
| [plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md) | 實作計畫：kunsu-init 與 kunsu-inbox skill 工具組（已執行完畢） |
| [plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md](plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md) | 實作計畫：/handoff 併入 toolkit（已執行完畢） |
| [plans/2026-07-07-001-feat-application-inbox-plan.md](plans/2026-07-07-001-feat-application-inbox-plan.md) | 實作計畫：申請信箱（R1–R20、六個實作單元） |
| [plans/2026-07-08-001-refactor-role-code-description-separation-plan.md](plans/2026-07-08-001-refactor-role-code-description-separation-plan.md) | 實作計畫：角色代碼／說明分離（R1–R22、九個實作單元，已執行完畢） |
| [plans/2026-07-08-002-feat-report-inbox-plan.md](plans/2026-07-08-002-feat-report-inbox-plan.md) | 實作計畫：上報信箱（R1–R25、八個實作單元，已執行完畢） |
| [plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md](plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md) | 實作計畫：協議 commit 逐次確認制與 handoffs 授權歸檔豁免（R1–R20、八個實作單元） |
