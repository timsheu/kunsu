# 文件中心索引

kunsu 專案的文件集合。專案定位與核心規範見上層 [CLAUDE.md](../CLAUDE.md)。

## 子目錄說明

| 目錄 | 內容 | 產出指令 |
|------|------|----------|
| `brainstorms/` | 需求與構想 | `/ce-brainstorm`（種子文件為手工彙整） |
| `plans/` | 實作計畫 | `/ce-plan` |
| `adr/` | 架構決策紀錄與候選 | 先產出 Candidate，審定後正式化 |
| `solutions/` | 可重用學習與解法 | `/ce-compound` |
| `playbooks/` | 操作教學（端到端工作流程、軍師沙盤導覽） | 手工維護 |

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
- **remove-project 子指令（2026-07-12）**：`kunsu-init` 新增 `remove-project` 子指令（v0.2.0 → v0.3.0），對稱 `add-project`，整筆移除子專案在本軍師的登記；新增 `registry-remove.sh`（獨立 exit code 區分冪等略過與成功移除）、清單失效感知選取、移除前未完成交接警告、雙階段不可逆確認、CLAUDE.md 先於 registry 的寫入順序設計。經 `/ce-brainstorm` → `/ce-plan`（4-persona doc-review）完整流程定案（ADR 012 accepted，[實作計畫](plans/2026-07-12-002-feat-remove-project-subcommand-plan.md)）。
- **軍師沙盤新增 todo 列表顯示，`/todo` skill 併入 toolkit（2026-07-17）**：全域 `/todo` skill（v0.1.1）逐字併入 `skills/todo/`（比照 ADR 003 handoff 先例），`install.sh` 與 CLAUDE.md 同步；軍師沙盤新增 `app/todo_status.py` 唯讀彙整軍師自己 `docs/todos/` 未歸檔技術債（兩桶計數＋三層顯示樣式，比照 ADR 011 verify 欄位模式，severity 排序＋archive 計數），`main.py` 新增「待辦技術債」卡片與全域總覽整合。經 `/ce-brainstorm` → `/ce-plan` 完整流程定案（ADR 013 accepted），計畫期 doc-review 與 `ce-simplify-code` 各修正正確性缺陷，8-agent Tier 2 code review 修正 status 欄位 falsy 值誤判，並發現 `/todo` skill 併入前既有的 `git mv` 缺 `git add`、slug 產生順序兩個缺陷（零行為變更決策下留待後續版號修正）。137 項 pytest 通過（自 111 項增至 137）。
- **軍師規劃前既有盤點與 kb 檢索接線（2026-07-25）**：軍師範本工作流程步驟 2 新增「規劃前既有盤點」子步驟（以 `/kb`／zoekt 依 handoffs→plans→子專案文件優先序檢索既有能力與結論，kb 軟依賴降級不阻斷）、步驟 5 加「相關既有教訓（選附）」；ebook／ivm／px 三 live 軍師同步遷移，tshehtu kb skill 補「搜教訓／搜歷史」playbook 並記兩筆既有缺陷 todo；dogfooding AE1／AE2 通過（[實作計畫](plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md)）。
- **軍師沙盤與收尾強化系列（2026-07-11 – 2026-07-19）**：軍師沙盤上線（ADR 010，本機 FastAPI 訊息聚合頁）與多輪易用性迭代；回覆 `verify:` 驗收方式欄位與交接三分類（ADR 011）；done 收尾口語觸發與憲章例外明文化、歸檔前逐項驗收查核、來源 todo 查核與一併收尾。
- **暫離回報（2026-07-26，handoff v0.9.0）**：接手方切換任務前投遞最小 `partial` 回覆（branch 名＋一句現況＋回來意向），消除「工作已在 branch 卻顯示未接手」的訊號缺席。
- **done 收尾沉澱訊號查核（2026-08-12，handoff v0.10.0）**：收尾時通讀全部回覆判斷五類沉澱訊號，回報附候選教訓與 `/ce-compound` 建議——僅提示不自動執行。
- **跨功能邏輯連結稽核（2026-08-12）**：四軸唯讀稽核收斂 15 筆漂移；機械層檢查沉澱為 `scripts/consistency-check.sh`，可隨時重跑。
- **知悉層自動化（2026-08-13，ADR 014／015 accepted）**：SessionStart hook 於 session 啟動（含 `/clear`）攤開信箱摘要；派發即推播／回覆即推播與 kunsu session 命名慣例（`kc` 啟動函式）。
- **回覆內容路由與收尾殘項清點（2026-08-13，handoff v0.12.0）**：反向路由查核（回覆中指向發起方的行動項與已解答疑問不再靜默蒸發）、todo 殘項清點、inbox 分流提示行。
- **接手方矛盾回報（2026-08-14，handoff v0.13.0）**：reply 步驟 2 帶理由規範——發現交接內容與自身參照物不符或內文自相矛盾時，即使不影響自身實作也在回覆中明列；讀方由既有反向路由查核承接。
- **Invariant #5 生命週期 metadata 邊界（2026-08-14，ADR 016 candidate、handoff v0.14.0）**：本體內文不可變、frontmatter 生命週期欄位（`status`、`corrected_by`）由發起方維護；勘誤採更正交接＋原本體補指標、引用以完整檔名為權威識別，歸檔路徑失效不構成錯誤。
- **軍師端斷言層級紀律與副官慣例（2026-08-14，handoff v0.15.0）**：查閱中介文件所得＝二手，據以實作的斷言須落原始碼並留查證痕跡；副官（subagent）慣例——原文回傳與完備性契約、判斷不外包；done 斷言自查兩態回報；kunsu-inbox 自身狀態觸發詞。
- **kc `--slot` 後綴（2026-08-21，handoff v0.17.0）**：同資料夾多 session 以 `kc --slot <後綴>` 取得 `<慣例名>.<後綴>` 名稱，`/park`／`/unpark` 停車格不互撞；推播精確比對納入 slot 變體，多重命中仍降級。
- **產檔腳本家目錄止步與 init-docs 標記檔必建（2026-08-21，handoff v0.17.1／todo v0.2.1）**：四支產檔腳本往上找專案根時走到 `$HOME` 即停，不再因 `~/AGENTS.md` 把家目錄誤認為專案根；全域 `/init-docs` 改為無條件先建最小 `CLAUDE.md` 作標記檔並於尾端驗證解析結果。
- **機制觸及率三件套（2026-08-15，handoff v0.16.0）**：修復「skill 內部指引在手動執行等效步驟時靜默失效」——範本指路牌（done 收尾詞條點名六查核＋手動不豁免句）、產檔腳本 stderr 指路行、SessionStart hook 版號變動提示。
- **下一步**：ADR 016 candidate 待審定；done 斷言自查與觸及率三件套的實績觀察（判準錯位／規則不被查閱兩假說判別）；ebook 軍師側五份審計研究 todo 依對應機制收尾。

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
| [adr/2026-07-12-adr-candidate-012-remove-project-subcommand.md](adr/2026-07-12-adr-candidate-012-remove-project-subcommand.md) | ADR 012（accepted）：軍師端 remove-project 子指令——整筆移除、失效感知選取、雙階段不可逆確認、CLAUDE.md 先於 registry 的寫入順序 |
| [adr/2026-07-17-adr-candidate-013-integrate-todo-into-toolkit.md](adr/2026-07-17-adr-candidate-013-integrate-todo-into-toolkit.md) | ADR 013（accepted）：`/todo` skill 併入 toolkit 維護與散布，比照 ADR 003 handoff 先例 |
| [brainstorms/2026-07-07-application-inbox-requirements.md](brainstorms/2026-07-07-application-inbox-requirements.md) | 需求：申請信箱與 add-project 對話式改造（R1–R15、驗收例） |
| [plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md) | 實作計畫：kunsu-init 與 kunsu-inbox skill 工具組（已執行完畢） |
| [plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md](plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md) | 實作計畫：/handoff 併入 toolkit（已執行完畢） |
| [plans/2026-07-07-001-feat-application-inbox-plan.md](plans/2026-07-07-001-feat-application-inbox-plan.md) | 實作計畫：申請信箱（R1–R20、六個實作單元） |
| [plans/2026-07-08-001-refactor-role-code-description-separation-plan.md](plans/2026-07-08-001-refactor-role-code-description-separation-plan.md) | 實作計畫：角色代碼／說明分離（R1–R22、九個實作單元，已執行完畢） |
| [plans/2026-07-08-002-feat-report-inbox-plan.md](plans/2026-07-08-002-feat-report-inbox-plan.md) | 實作計畫：上報信箱（R1–R25、八個實作單元，已執行完畢） |
| [plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md](plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md) | 實作計畫：協議 commit 逐次確認制與 handoffs 授權歸檔豁免（R1–R20、八個實作單元） |
| [brainstorms/2026-07-12-remove-project-requirements.md](brainstorms/2026-07-12-remove-project-requirements.md) | 需求：軍師端 remove-project 子指令（整筆移除、失效感知選取、未完成交接警告、不可逆確認） |
| [plans/2026-07-12-002-feat-remove-project-subcommand-plan.md](plans/2026-07-12-002-feat-remove-project-subcommand-plan.md) | 實作計畫：remove-project 子指令與 registry-remove.sh（R1–R16、六個實作單元） |
| [brainstorms/2026-07-17-dashboard-todo-list-requirements.md](brainstorms/2026-07-17-dashboard-todo-list-requirements.md) | 需求：軍師沙盤 todo 列表顯示與 `/todo` skill 併入 |
| [plans/2026-07-17-001-feat-dashboard-todo-list-plan.md](plans/2026-07-17-001-feat-dashboard-todo-list-plan.md) | 實作計畫：軍師沙盤 todo 列表顯示與 `/todo` skill 併入（R1–R9、七個實作單元，已執行完畢） |
| [brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md](brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md) | 需求：軍師規劃前既有盤點與 kb 檢索接線（主從反轉、檢索優先序、軟依賴降級） |
| [plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md](plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md) | 實作計畫：規劃前既有盤點（核心＋kb playbook、六個實作單元，已執行完畢） |
| [adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md](adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md) | ADR 010（accepted）：軍師沙盤對 Invariant 1 的例外範圍界定（唯讀、無背景輪詢、不得自主重啟） |
| [adr/2026-07-12-adr-candidate-011-reply-verify-field.md](adr/2026-07-12-adr-candidate-011-reply-verify-field.md) | ADR 011（accepted）：回覆 `verify:` 驗收方式欄位（display-only 開放值域）與交接三分類 |
| [adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md](adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md) | ADR 014（accepted）：SessionStart hook 第二階段啟用——事件驅動信箱摘要注入 |
| [adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md](adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md) | ADR 015（accepted）：派發即推播／回覆即推播——對 ADR 002 推播否決的翻案（限縮於 daemon 輪詢形態） |
| [adr/2026-08-14-adr-candidate-016-lifecycle-metadata-boundary.md](adr/2026-08-14-adr-candidate-016-lifecycle-metadata-boundary.md) | ADR 016（candidate，待審定）：Invariant #5 例外邊界重述——內文不可變、frontmatter 生命週期 metadata 由發起方維護 |
| [plans/2026-07-11-001-feat-kunsu-dashboard-plan.md](plans/2026-07-11-001-feat-kunsu-dashboard-plan.md) | 實作計畫：軍師沙盤（R1–R10、六個實作單元，已執行完畢） |
| [plans/2026-07-12-001-feat-reply-verify-field-plan.md](plans/2026-07-12-001-feat-reply-verify-field-plan.md) | 實作計畫：回覆 verify 欄位與沙盤「部分完成」子分類（U0–U7，已執行完畢） |
| [brainstorms/2026-07-25-handoff-pause-report-requirements.md](brainstorms/2026-07-25-handoff-pause-report-requirements.md) | 需求：handoff 暫離回報慣例 |
| [brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md](brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md) | 需求：done 收尾沉澱訊號查核（R1–R7、AE 三例） |
| [plans/2026-08-12-001-feat-handoff-done-compound-prompt-plan.md](plans/2026-08-12-001-feat-handoff-done-compound-prompt-plan.md) | 實作計畫：沉澱訊號查核（三個實作單元，已執行完畢） |
| [brainstorms/2026-08-12-awareness-automation-requirements.md](brainstorms/2026-08-12-awareness-automation-requirements.md) | 需求：知悉層自動化（Phase A SessionStart hook＋Phase B 派發即推播） |
| [brainstorms/2026-08-13-reply-routing-and-residual-check-requirements.md](brainstorms/2026-08-13-reply-routing-and-residual-check-requirements.md) | 需求：回覆內容路由與收尾殘項清點（反向路由查核、殘項清點、分流提示） |
| [plans/2026-08-13-001-feat-reply-routing-closure-checks-plan.md](plans/2026-08-13-001-feat-reply-routing-closure-checks-plan.md) | 實作計畫：收尾查核三件套（已執行完畢） |
| [brainstorms/2026-08-14-reply-contradiction-reporting-norm-requirements.md](brainstorms/2026-08-14-reply-contradiction-reporting-norm-requirements.md) | 需求：接手方矛盾回報規範（帶理由 norm、命中才報、兩語境通用） |
| [plans/2026-08-14-001-feat-reply-contradiction-reporting-norm-plan.md](plans/2026-08-14-001-feat-reply-contradiction-reporting-norm-plan.md) | 實作計畫：矛盾回報指引（三個實作單元，已執行完畢） |
| [brainstorms/2026-08-14-invariant5-lifecycle-metadata-requirements.md](brainstorms/2026-08-14-invariant5-lifecycle-metadata-requirements.md) | 需求：Invariant #5 生命週期 metadata 邊界與勘誤、引用兩慣例 |
| [plans/2026-08-14-002-feat-invariant5-lifecycle-metadata-plan.md](plans/2026-08-14-002-feat-invariant5-lifecycle-metadata-plan.md) | 實作計畫：ADR 016、更正交接與引用檔名權威（五個實作單元，已執行完畢） |
| [brainstorms/2026-08-14-adjutant-source-level-requirements.md](brainstorms/2026-08-14-adjutant-source-level-requirements.md) | 需求：軍師端斷言層級紀律與副官慣例（經 3-persona × 2 輪 doc review 收斂） |
| [plans/2026-08-14-003-feat-adjutant-source-level-plan.md](plans/2026-08-14-003-feat-adjutant-source-level-plan.md) | 實作計畫：斷言層級紀律、done 斷言自查、觸發詞與副官小節（五個實作單元，已執行完畢） |
| [brainstorms/2026-08-15-mechanism-reach-signpost-requirements.md](brainstorms/2026-08-15-mechanism-reach-signpost-requirements.md) | 需求：機制投放點與觸及率——指路牌、腳本 stdout 指路與 hook 版號提示 |
| [plans/2026-08-15-001-feat-mechanism-reach-signpost-plan.md](plans/2026-08-15-001-feat-mechanism-reach-signpost-plan.md) | 實作計畫：觸及率三件套（五個實作單元，已執行完畢） |
| [playbooks/end-to-end-workflow.md](playbooks/end-to-end-workflow.md) | 操作教學：從建立軍師到一輪交接完成收尾的完整工作流程（自 README 拆出，操作教學唯一落點） |
| [playbooks/dashboard.md](playbooks/dashboard.md) | 操作教學：軍師沙盤安裝、啟動與頁面導覽（自 README 拆出） |
