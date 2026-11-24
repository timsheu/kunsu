# 文件中心索引

kunsu 專案的文件集合。專案定位與核心規範見上層 [CLAUDE.md](../CLAUDE.md)。

## 子目錄說明

| 目錄 | 內容 | 產出指令 |
|------|------|----------|
| `brainstorms/` | 需求與構想 | `/ce-brainstorm`（種子文件為手工彙整） |
| `plans/` | 實作計畫 | `/ce-plan` |
| `adr/` | 架構決策紀錄與候選 | 先產出 Candidate，審定後正式化 |
| `solutions/` | 可重用學習與解法 | `/ce-compound` |
| `playbooks/` | 操作教學（端到端工作流程、軍師沙盤導覽、Codex 雙端試點） | 手工維護 |
| `history/` | 開發日誌（已完成條目自 CLAUDE.md 遷出，新條目追加於此） | 手工維護 |

## 目前狀態

- 已完成的功能落地紀錄（2026-07-06 起）統一記於 [history/development-log.md](history/development-log.md)，每條含來源回饋、決策取捨、審查與 dogfooding 結果；新完成的工作一律追加至該檔，本節不再逐條列出。
- 尚未實作與後續評估的項目見上層 [CLAUDE.md](../CLAUDE.md) 的「尚未實作／後續評估」。
- ADR 的狀態以各檔 frontmatter 為準（現僅 ADR 016 為 proposed，其餘 accepted）。

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
| [adr/2026-08-29-adr-candidate-017-pretooluse-git-add-guard.md](adr/2026-08-29-adr-candidate-017-pretooluse-git-add-guard.md) | ADR 017（accepted）：軍師 repo `git add` 寬範圍守門——kunsu 首個行為強制點，四要件判準、環境變數逃生門、deny 入統計 |
| [adr/2026-08-31-adr-candidate-018-commit-declared-scope-contract.md](adr/2026-08-31-adr-candidate-018-commit-declared-scope-contract.md) | ADR 018（accepted）：確認 commit 自「提交 index」改為「提交宣告範圍」——pathspec 兩形契約、上報歸檔腳本化、`MISDECLARED_ARCHIVE_ADD` 偵測 |
| [adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md](adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md) | ADR 019（accepted，2026-10-03 審定）：kunsu 通用化——adapter＝部署目標＋字面對應、Invariant 3 擴為各 agent skill 目錄、ADR 009 第二種確認形態、ADR 001 Consequences 翻案 |
| [adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md](adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md) | ADR 020（accepted）：軍師沙盤登入自動啟動——修訂 ADR 010 Decision 第 1 項第 3 條，允許使用者親手安裝只含 `RunAtLoad` 的 LaunchAgent |
| [brainstorms/2026-09-06-codex-agent-neutral-deployment-requirements.md](brainstorms/2026-09-06-codex-agent-neutral-deployment-requirements.md) | 需求：kunsu 通用化雙部署（R1–R19、AE1–AE8；5-persona review 13 筆） |
| [plans/2026-09-06-001-feat-codex-agent-neutral-deployment-plan.md](plans/2026-09-06-001-feat-codex-agent-neutral-deployment-plan.md) | 實作計畫：雙部署（U1–U9；4-persona review 14 筆；U8 試點 2026-10-03 單輪全綠、ADR 019 accepted） |
| [playbooks/codex-pilot.md](playbooks/codex-pilot.md) | 操作教學：Codex 雙端試點腳本用法、可觀測面與手動核對清單 |
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
| [brainstorms/2026-07-11-kunsu-dashboard-requirements.md](brainstorms/2026-07-11-kunsu-dashboard-requirements.md) | 需求：kunsu 訊息聚合儀表板（軍師沙盤） |
| [brainstorms/2026-07-13-handoff-done-closure-requirements.md](brainstorms/2026-07-13-handoff-done-closure-requirements.md) | 需求：handoff done 收尾閉環 |
| [plans/2026-07-13-001-feat-handoff-done-closure-plan.md](plans/2026-07-13-001-feat-handoff-done-closure-plan.md) | 實作計畫：handoff done 收尾閉環（已執行完畢） |
| [brainstorms/2026-07-19-handoff-done-todo-closure-requirements.md](brainstorms/2026-07-19-handoff-done-todo-closure-requirements.md) | 需求：handoff done 來源 todo 一併收尾 |
| [plans/2026-07-19-001-feat-handoff-done-todo-closure-plan.md](plans/2026-07-19-001-feat-handoff-done-todo-closure-plan.md) | 實作計畫：handoff done 來源 todo 查核與 /todo 0.1.2 缺陷修正（已執行完畢） |
| [brainstorms/2026-07-24-committed-orphan-detection-requirements.md](brainstorms/2026-07-24-committed-orphan-detection-requirements.md) | 需求：投遞檔已 commit 漏收偵測（遺漏提醒） |
| [plans/2026-07-24-002-feat-committed-orphan-detection-plan.md](plans/2026-07-24-002-feat-committed-orphan-detection-plan.md) | 實作計畫：投遞檔已 commit 漏收偵測（frontmatter 為 `status: active`） |
| [brainstorms/2026-07-24-handoff-redact-grill-prompts-requirements.md](brainstorms/2026-07-24-handoff-redact-grill-prompts-requirements.md) | 需求：handoff redact 與 grill 議題硬化提示 |
| [plans/2026-07-25-001-feat-handoff-pause-report-plan.md](plans/2026-07-25-001-feat-handoff-pause-report-plan.md) | 實作計畫：handoff 暫離回報慣例（已執行完畢） |
| [brainstorms/2026-08-31-commit-declared-scope-requirements.md](brainstorms/2026-08-31-commit-declared-scope-requirements.md) | 需求：確認 commit 宣告範圍契約——pathspec 定型化、上報歸檔腳本與夾帶偵測 |
| [plans/2026-08-31-001-feat-commit-declared-scope-plan.md](plans/2026-08-31-001-feat-commit-declared-scope-plan.md) | 實作計畫：確認 commit 宣告範圍契約（已執行完畢） |
| [brainstorms/2026-08-31-dedup-and-todo-archive-scripts-requirements.md](brainstorms/2026-08-31-dedup-and-todo-archive-scripts-requirements.md) | 需求：產檔查重與 todo 歸檔腳本化——會飄移的紀律改用腳本 |
| [plans/2026-08-31-002-feat-dedup-and-todo-archive-scripts-plan.md](plans/2026-08-31-002-feat-dedup-and-todo-archive-scripts-plan.md) | 實作計畫：產檔查重與 todo 歸檔腳本化（已執行完畢） |
| [brainstorms/2026-09-01-current-state-assertion-dual-side-requirements.md](brainstorms/2026-09-01-current-state-assertion-dual-side-requirements.md) | 需求：實作現況斷言的讀寫雙側補強 |
| [plans/2026-09-01-001-feat-current-state-assertion-dual-side-plan.md](plans/2026-09-01-001-feat-current-state-assertion-dual-side-plan.md) | 實作計畫：實作現況斷言的讀寫雙側補強（已執行完畢） |
| [brainstorms/2026-09-08-handoff-dependency-dag-requirements.md](brainstorms/2026-09-08-handoff-dependency-dag-requirements.md) | 需求：交接依賴圖——以 `depends_on` 邊推導 DAG 式依賴追蹤 |
| [plans/2026-09-08-001-feat-handoff-dependency-dag-plan.md](plans/2026-09-08-001-feat-handoff-dependency-dag-plan.md) | 實作計畫：交接依賴圖——`depends_on` 邊、推導態與沙盤 inline SVG（已執行完畢） |
| [plans/2026-09-27-1232-feat-kunsu-prompt-inbox-notice-plan.md](plans/2026-09-27-1232-feat-kunsu-prompt-inbox-notice-plan.md) | 實作計畫：軍師提問時三信箱新件提示（UserPromptSubmit hook） |
| [plans/2026-09-27-1709-feat-reply-excerpt-visibility-plan.md](plans/2026-09-27-1709-feat-reply-excerpt-visibility-plan.md) | 實作計畫：久懸交接帶最新回覆摘錄 |
| [plans/2026-09-28-1117-feat-conditional-series-index-plan.md](plans/2026-09-28-1117-feat-conditional-series-index-plan.md) | 實作計畫：條件式線總表與產檔訊號 |
| [plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md](plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md) | 實作計畫：軍師沙盤看板化 |
| [plans/2026-10-03-1034-fix-push-match-exclude-offline-plan.md](plans/2026-10-03-1034-fix-push-match-exclude-offline-plan.md) | 實作計畫：推播匹配排除 offline session |
| [plans/2026-11-22-1651-feat-env-version-record-template-plan.md](plans/2026-11-22-1651-feat-env-version-record-template-plan.md) | 實作計畫：環境版本正本進軍師範本 |
| [solutions/best-practices/git-porcelain-scan-script-pitfalls.md](solutions/best-practices/git-porcelain-scan-script-pitfalls.md) | 學習：撰寫 git porcelain 掃描腳本的四個陷阱 |
| [solutions/workflow-issues/handoff-done-closure-gap.md](solutions/workflow-issues/handoff-done-closure-gap.md) | 學習：handoff done 收尾閉環四斷點——觸發詞、流程步驟、輸出提示與憲章同步 |
| [solutions/workflow-issues/handoff-intercept-point-selection.md](solutions/workflow-issues/handoff-intercept-point-selection.md) | 學習：handoff 暫離回報與攔截點選擇——切任務無回報導致交接狀態失真 |
| [solutions/workflow-issues/assertion-level-discipline-coverage-gap.md](solutions/workflow-issues/assertion-level-discipline-coverage-gap.md) | 學習：斷言層級紀律兩輪演進——掛載點覆蓋缺口、時效陷阱與讀寫雙態措辭 |
| [solutions/workflow-issues/literal-replacement-residue-and-review-triage.md](solutions/workflow-issues/literal-replacement-residue-and-review-triage.md) | 學習：大範圍字面替換的正確性後檢查與語言審查工具的分流判準 |
| [history/development-log.md](history/development-log.md) | 開發日誌：2026-07-06 起的功能落地紀錄（來源回饋、決策取捨、審查與 dogfooding 結果） |
