# kunsu

kunsu（軍師，台語 kun-su）——為多 repo AI 協作建立「軍師」（規劃協調中心）的 scaffolding 工具組：以純 skill＋範本快速建立唯讀的軍師 repo（軍師沙盤為唯一例外，見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)），並以全域反向註冊表自動化跨 session 傳令。本專案是工具母體——skill 原始碼在此開發與版控，部署目標為 `~/.claude/skills/`。

## 核心規範（Invariants）

1. **純 skill＋範本，不建編譯型工具** — 交付物是 markdown 範本、skill 指令文件與少量膠水腳本（shell），不建立 Rust／Go／Python 等需要獨立維護的工具專案。理由見 [docs/adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md](docs/adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md)。
2. **絕不注入子 repo** — 工具產出的軍師對其子專案唯讀；本工具本身也不在任何目標 repo 寫入 managed section 或設定。所有機器路徑的**常設登記**只存在於兩處：各軍師自己 CLAUDE.md 的關聯專案表，以及全域註冊表 `~/.claude/kunsu-registry.json`（申請信箱中待審申請的 `path` 欄位為暫態投遞內容，核准即轉入上述正式登記、歸檔後僅為歷史紀錄；上報信箱中上報檔的情報內容同屬暫態投遞，不構成機器路徑的常設登記，見 ADR 006、ADR 008）。
3. **開發與部署分離** — skill 原始碼在本 repo 版控，經 `install.sh` 部署（symlink 或 copy）至 `~/.claude/skills/`，不直接在 `~/.claude` 內開發。與 `~/.claude/rules` 既有的 install.sh 模式一致。
4. **範本母本唯讀參考** — 抽象化來源為 ebook 專案群規劃中心（本機私有路徑，略），僅唯讀查閱，不回頭修改母本。

## 專案結構

```
CLAUDE.md
CONCEPTS.md            → 領域詞彙表（實體、具名流程、狀態概念；/ce-compound 維護）
docs/
  README.md            → 文件中心主索引
  brainstorms/         → 需求（種子：2026-07-06 需求彙整）
  plans/               → 實作計畫（/ce-plan 產出）
  adr/                 → ADR（001–015 全數 accepted）
  solutions/           → 可重用學習與解法（/ce-compound 產出，YAML frontmatter 依 module/tags/problem_type 可搜尋）
  playbooks/           → 操作教學（端到端工作流程、軍師沙盤導覽；手工維護，自 README 拆出的教學唯一落點）
skills/                → skill 原始碼
  handoff/             → 通用交接原語（v0.13.0，2026-07-06 自部署目錄併入，見 ADR 003）
    SKILL.md           → add／reply／list／done 子指令（reply 含 kunsu 語境分支、verify 驗收方式選填欄位、逐項回答附證據指引、矛盾回報指引與暫離回報最小 partial 回覆；done 含收尾口語觸發、發起方守門、歸檔前逐項驗收查核、沉澱訊號查核、反向路由查核與來源 todo 查核一併收尾（todo 收尾含殘項清點）；add／done／本地 reply 尾端確認 commit）
    scripts/           → new-handoff.sh、new-handoff-reply.sh
  todo/                → CE 副作用 TODO 清單管理原語（v0.2.0，2026-07-17 自部署目錄併入，見 ADR 013）
    SKILL.md           → add／list／done／rm 子指令，管理 docs/todos/ 一檔一項技術債（done 含殘項清點；done／rm 含 untracked 前置檢查）
    scripts/           → new-todo.sh
  kunsu-init/          → 軍師 scaffolding
    SKILL.md           → 訪談→查證→產檔→vault→git→註冊表主流程＋add-project（申請審核制）＋remove-project（整筆移除）子指令
    scripts/registry-merge.sh → 註冊表 read-merge-write（python3）
    scripts/registry-remove.sh → 註冊表 read-remove-write，獨立 exit code 區分冪等略過與成功移除（python3）
    assets/templates/  → 軍師範本（CLAUDE.md／CONCEPTS.md／README／HOME dataview 區塊＋PLACEHOLDERS.md）
    assets/solutions/  → 兩篇種子沉澱文件（自母本通用化）
  kunsu-inbox/         → 跨 session 傳令自動化
    SKILL.md           → 模式偵測（獨立雙判斷）＋子 repo／軍師雙模式（軍師模式含收尾與分流提示行）
    scripts/scan-replies.sh → 未 commit 回覆掃描＋tripwire（done 授權歸檔豁免、雙側核驗）
    scripts/scan-applications.sh → 申請信箱掃描＋tripwire（雙側核驗授權歸檔）
    scripts/scan-reports.sh → 上報信箱掃描＋tripwire（結構同 scan-applications.sh）
    scripts/session_hook.py → SessionStart hook：session 啟動（含 /clear）自動注入信箱摘要（ADR 014，複用沙盤分類模組）
    tests/             → pytest，session hook 單元測試
  kunsu-apply/         → 子專案端投遞申請加入
    SKILL.md           → 自動偵測＋registry 選軍師＋守門與冪等預檢
    scripts/new-application.sh → 申請檔產檔（frontmatter＋防撞）
  kunsu-report/        → 子專案端投遞主動上報
    SKILL.md           → 僅服務已登記 repo＋信箱守門＋反向重導（是否其實是回覆）
    scripts/new-report.sh → 上報檔產檔（stdin 內文＋frontmatter＋防撞）
  kunsu-list/          → 全域登記清單查詢
    SKILL.md           → 唯讀列出註冊表全部登記（無 git 身分前提，任何目錄可執行）
    scripts/registry-list.sh → 按軍師分組＋stale 偵測＋當前位置標記（python3）
  kunsu-dashboard/     → kunsu 訊息聚合本機網頁（非 Claude Code skill，見 ADR 010）
    SKILL.md           → 純安裝／啟動說明，不涉及觸發語
    requirements.txt   → fastapi／uvicorn[standard]／PyYAML（本專案首次 pip 依賴）
    app/               → registry.py／kunsu_scan.py／subrepo_status.py／todo_status.py／main.py
    tests/             → pytest，137 項測試
scripts/kc.fish        → kunsu claude 啟動函式（fish autoload；依 registry 自動以命名慣例 `-n` 啟動，部署至 ~/.config/fish/functions/）
scripts/consistency-check.sh → 跨檔案一致性機械檢查（版號鏈、值域副本、定型文字實跑比對、install 覆蓋、分類詞對映、live 軍師 WARN 級抽查；沉澱自 2026-08-12 邏輯連結稽核）
install.sh             → 部署至 ~/.claude/skills/（預設 copy、--link 開發模式）
```

## 文件導航

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md) | 操作教學：端到端工作流程（README 只留門面摘要） |
| [docs/playbooks/dashboard.md](docs/playbooks/dashboard.md) | 操作教學：軍師沙盤安裝與頁面導覽 |
| [docs/brainstorms/2026-07-06-planner-toolkit-requirements.md](docs/brainstorms/2026-07-06-planner-toolkit-requirements.md) | 種子需求：問題定義、ce-team 教訓、母本解剖、方案設計 |
| [docs/adr/](docs/adr/) | ADR（001–004 於 2026-07-06、005 於 2026-07-07 審定為 accepted；006 申請信箱與 008 上報信箱於 2026-07-09 accepted；007 角色代碼／說明分離於 2026-07-08 accepted；010 kunsu-dashboard 對 Invariant 1 的例外於 2026-07-11 accepted；011 回覆 verify 欄位與分類拆分、012 remove-project 子指令於 2026-07-12 accepted；013 `/todo` skill 併入 toolkit 於 2026-07-17 accepted；014 SessionStart hook 第二階段啟用與 015 派發即推播於 2026-08-13 accepted——全數 accepted） |
| [docs/brainstorms/2026-07-17-dashboard-todo-list-requirements.md](docs/brainstorms/2026-07-17-dashboard-todo-list-requirements.md) | 軍師沙盤 todo 列表顯示需求 |
| [docs/plans/2026-07-17-001-feat-dashboard-todo-list-plan.md](docs/plans/2026-07-17-001-feat-dashboard-todo-list-plan.md) | 軍師沙盤 todo 列表顯示與 `/todo` skill 併入實作計畫（R1–R9、七個實作單元，已執行完畢） |
| [docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md) | 實作計畫（12 條 requirements、7 個實作單元，已執行完畢） |
| [docs/plans/2026-07-07-001-feat-application-inbox-plan.md](docs/plans/2026-07-07-001-feat-application-inbox-plan.md) | 申請信箱實作計畫（R1–R20、六個實作單元） |
| [docs/plans/2026-07-08-001-refactor-role-code-description-separation-plan.md](docs/plans/2026-07-08-001-refactor-role-code-description-separation-plan.md) | 角色代碼／說明分離實作計畫（R1–R22、九個實作單元） |
| [docs/plans/2026-07-08-002-feat-report-inbox-plan.md](docs/plans/2026-07-08-002-feat-report-inbox-plan.md) | 上報信箱實作計畫（R1–R25、八個實作單元，已執行完畢） |
| [docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md](docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md) | 軍師沙盤（kunsu dashboard）實作計畫（R1–R10、六個實作單元，已執行完畢） |
| [docs/plans/2026-07-12-001-feat-reply-verify-field-plan.md](docs/plans/2026-07-12-001-feat-reply-verify-field-plan.md) | 回覆驗收方式欄位（verify）與沙盤「部分完成」子分類實作計畫（U0–U7，已執行完畢） |
| [docs/plans/2026-07-12-002-feat-remove-project-subcommand-plan.md](docs/plans/2026-07-12-002-feat-remove-project-subcommand-plan.md) | remove-project 子指令實作計畫（R1–R16、六個實作單元） |
| [docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md](docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md) | 軍師規劃前既有盤點與 kb 檢索接線需求 |
| [docs/plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md](docs/plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md) | 規劃前既有盤點實作計畫（核心＋kb playbook、六個實作單元，已執行完畢） |
| [docs/brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md](docs/brainstorms/2026-08-12-handoff-done-compound-prompt-requirements.md) | handoff done 收尾沉澱訊號查核需求（R1–R7、AE 三例） |
| [docs/plans/2026-08-12-001-feat-handoff-done-compound-prompt-plan.md](docs/plans/2026-08-12-001-feat-handoff-done-compound-prompt-plan.md) | 沉澱訊號查核實作計畫（三個實作單元，已執行完畢） |
| [docs/brainstorms/2026-08-12-awareness-automation-requirements.md](docs/brainstorms/2026-08-12-awareness-automation-requirements.md) | 知悉層自動化需求（Phase A SessionStart hook＋Phase B 派發即推播，Open Questions 已定案） |

## 開發狀態

### 已完成
- 種子需求文件與兩份 ADR Candidate（2026-07-06，由 ebook 規劃中心 session 的設計討論彙整而來）。
- 兩份 ADR 經兩輪 `/ce-doc-review`（5 persona、14 項修正）審定為 accepted（2026-07-06）。
- 實作計畫（[docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md)）與全部三件交付物：`/kunsu-init` skill（含範本抽取、`add-project` 子指令、`registry-merge.sh`）、`/kunsu-inbox` skill（含 `scan-replies.sh`）、`install.sh`（2026-07-06）。
- 端到端 dogfooding 驗證 19 場景全數通過（暫存目錄實跑 scaffold＋handoff 往返＋inbox 雙模式＋add-project；發現並修復同日多份回覆的檔名排序缺陷）。
- `/handoff` skill（v0.2.1）自部署目錄逐字併入 `skills/handoff/`，隨 toolkit 共同維護與散布；本 repo 為其開發母體，改動一律「改 repo 再 install」（ADR 003，2026-07-06）。
- 詞彙統一遷移（「規劃中心」→「軍師」）：README、兩份 SKILL.md 文案、腳本訊息、範本內容與檔名（`planner-*.md` → `kunsu-*.md`）、solutions 種子文件、註冊表欄位 `planner` → `kunsu` 全面改稱；歷史快照（ADR 001–003、plans、brainstorms）與母本指稱維持原貌（[ADR 005](docs/adr/2026-07-07-adr-candidate-005-unify-kunsu-terminology.md)，2026-07-07）。
- 申請信箱功能：例外授權擴為雙信箱（scaffold 內建 `docs/applications/`），新增 `/kunsu-apply` 子專案端投遞 skill 與 `scan-applications.sh`，`add-project` 改為掃描審核制（核准當下單點登記、內建舊軍師遷移），`/kunsu-inbox` 軍師模式一併回報新申請（[ADR 006 candidate](docs/adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md)，2026-07-07）。
- 上報信箱落地（[ADR 008](docs/adr/2026-07-08-adr-candidate-008-report-inbox-triple-mailbox.md) 實作，2026-07-09）：例外授權擴為三信箱——新增 `/kunsu-report` 子專案端投遞 skill（僅服務已登記 repo、信箱守門、反向重導）與 `scan-reports.sh`（以 `scan-applications.sh` 為基底，三陷阱內建）、`/kunsu-inbox` 軍師模式第三段、scaffold 與 add-project 三信箱化（②-a／②-b 拆分延後跳轉）、母體文件與 CONCEPTS 同步（中文定名「上報」）、ivm／ebook 兩軍師 live 遷移與 ivm 孤兒上報歸位。依 [實作計畫](docs/plans/2026-07-08-002-feat-report-inbox-plan.md)（經 headless doc review）以 maker（sonnet）／verifier 分離執行八單元，暫存目錄 dogfooding 全數通過（scaffold 驗收 11 項、掃描十場景、投遞歸檔全鏈路）。
- `/handoff` reply 路由補洞（v0.3.0，2026-07-08）：子專案口語「回覆軍師」未命中任何 skill 觸發詞，回覆錯投軍師 `docs/handoffs/` 頂層（`scan-replies.sh` tripwire 如設計攔截）。修補三處——description 觸發詞補「回覆軍師」等口語、reply 新增 kunsu 語境分支（未給 slug 時查註冊表定位軍師與 `to:` 為本角色的待回交接、零筆時明確禁止即興落檔）、`new-handoff-reply.sh` 的 `replies/` 落點改從**原交接檔位置**推算（跨 repo 回覆保證落在軍師回覆信箱，含 archive 上層歸位與非 handoffs 路徑防呆），暫存目錄五場景實測通過。
- 角色識別正規化（[ADR 007](docs/adr/2026-07-08-adr-candidate-007-role-code-description-separation.md)，2026-07-08）：「角色」拆為**角色代碼**（短、kebab-case，registry／handoff `to:`／CLAUDE.md 代碼欄三處字面一致的唯一比對鍵）與**角色說明**（整句職責，display-only、不進註冊表、不比對）。範本關聯專案表改雙欄、申請 frontmatter 新增 `role_desc`、CONCEPTS 詞彙拆分、四支 SKILL 與 `registry-merge.sh`（軟警告）、`add-project` 唯一性權威強制點同步；並遷移 ivm／ebook 兩軍師 live registry 與 CLAUDE.md（**修復 ivm `/kunsu-inbox` false-negative**，兩軍師 handoff `to:` 全數命中）。經兩輪 `/ce-doc-review`（15 項修正，含兩處失實：ebook-nginx、ebook 軍師 CLAUDE.md）。

- `/kunsu-list` skill（2026-07-09）：獨立薄殼 skill 唯讀列出全域註冊表登記——按軍師分組、多角色併列、路徑存活檢查（⚠ stale entry 只報不修）、當前 repo「← 你在這」標記；刻意無 git 身分前提，任何目錄（含多 repo 父層 workspace）皆可執行。獨立成 skill（而非 kunsu-init 子指令）是為取得 `/kunsu-list` 斜線指令入口；`registry-list.sh` 自持於本 skill，與 `registry-merge.sh` 一讀一寫分工。暫存目錄 dogfooding 六場景通過（真實註冊表三 cwd、註冊表不存在、JSON 損壞、stale＋多角色 fixture）。
- 協議 commit 逐次確認制與 handoffs 授權歸檔豁免（[ADR 009](docs/adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md)，2026-07-10）：軍師側／發起側流程尾端 commit 升格為「AskUserQuestion 確認一次 → 執行」的協議步驟——handoff v0.4.0（add／done／本地語境 reply；done 補 untracked 前置 git add、步驟連續執行約束、確認 commit 的 git add 必含歸檔目的地路徑以帶入 `status: done`）、kunsu-init v0.2.0（add-project 審核歸檔自提醒模式升格、registry 明示不入 commit）、範本上報歸檔四步驟化；固定 `docs:` 訊息格式、僅 add 本流程產出、防空 commit、絕不 push，全域「不主動 commit」規範零改動。投遞端（kunsu-apply／kunsu-report／kunsu 語境 reply）維持不 commit——未 commit 即信箱新件訊號的不對稱設計。`scan-replies.sh` 以 scan-applications.sh 為基底重構雙側核驗，豁免 done 授權歸檔三形狀（頂層→archive、replies→archive/replies、archive/ 內靜默；kunsu-inbox v0.3.0 訊息同步）；實測修正「git mv 會暫存工作樹修改」誤解（porcelain 實為 `RM`、staged 為舊版）。fixture 十四場景＋端到端 dogfooding 九場景全數通過，ivm／ebook 兩軍師 live 遷移各以一筆確認 commit 收斂（新協議首次實跑）。
- **軍師沙盤**（kunsu dashboard；[ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)，2026-07-11）：新增 `skills/kunsu-dashboard/`，獨立本機 FastAPI 服務彙整全域註冊表裡所有軍師與子專案的訊息狀態，取代逐一切換 CLI 視窗手動執行 `/kunsu-inbox` 的做法；重新整理瀏覽器頁面才即時重新掃描，不跑背景 worker，啟動停止由使用者手動掌握。**本專案首次引入 pip 依賴（fastapi／uvicorn／PyYAML）與常駐服務**，字面上牴觸 Invariant 1，ADR 010 明訂例外範圍界定（唯讀、無背景輪詢、text/html-only 硬性技術條件、不得有自主重啟路徑）與未來比照此例外的判斷條件；`SKILL.md` 僅作安裝／啟動說明，刻意不使用觸發語慣例格式。依 [實作計畫](docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md)（R1–R10、六單元，U6 ADR 先於程式碼動工完成一輪 doc-review）執行，Tier 2 code review（xhigh，10 finder angles）發現並修正 9 個經驗證的正確性缺陷（含 registry 雙重讀取 TOCTOU 競態、tripwire 於無明細行時靜默遺失、stale 軍師誤報「無待處理交接文件」等），58 項 pytest 測試通過，並以真實啟動伺服器＋curl 驗證端到端行為。
- 軍師沙盤（kunsu dashboard）易用性迭代與更名（2026-07-11，試用回饋同日多輪）：依軍師分組、子專案巢狀顯示於所屬軍師底下（取代軍師／子專案兩個獨立區塊）；每筆交接／新訊息以原生 `<details>`（零 JS）展開看完整 md 內容與最後修改時間，軍師的新回覆／新申請／新上報三個分類標題列各顯示「最新」時間；軍師分組本身亦可折疊，有進度（新訊息／tripwire／stale）者預設展開、健康且無新訊息者預設折疊，避免軍師一多列表過長；新增 `start.sh` 一鍵啟動腳本（仍為手動觸發，符合 ADR 010 Decision 1.3）；修復 `eBookApp` 子專案登記路徑非 git root 導致誤報 stale 且 `/kunsu-report`／`/kunsu-apply` 實際已失聯的問題（改登記其真正 git root，兩處同步）；README.md 補齊六個 skill 完整清單與軍師沙盤說明；「Dashboard」正式更名為 **軍師沙盤（kunsu dashboard）**（如統帥推演戰局的沙盤，貼合軍師文化意象，中文置前、英文技術名括號註記），沿用既有 skill 目錄名 `kunsu-dashboard` 不變。66 項 pytest 測試通過（自 58 項增至 66）。

- 回覆驗收方式欄位（verify）與交接三分類（[ADR 011](docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md)，2026-07-12 accepted）：源自沙盤試用回饋「看不出 partial 的原因是哪種測試需求」。回覆檔 frontmatter 新增選填 display-only 欄位 `verify:`（建議代碼 `needs-deploy`／`testable-now`／`needs-device`，全小寫 kebab-case＋開放值域，缺省不顯示，零遷移；不跨回覆繼承——只讀最新回覆，需求未變仍需顯式複寫），「待接手」拆分為「未接手（無回覆）」與「部分完成（partial／blocked／未知 status，blocked 另標 ⛔ 卡關）」；handoff v0.5.0（`new-handoff-reply.sh` 第三參數、`new-handoff.sh` 回覆方式段落補值域說明）、kunsu-inbox 4a 分類表與依賴聲明、`subrepo_status.py`（`pending` 拆 `not_picked_up`／`partial_done`）與沙盤標籤渲染（標籤置於摘要列、blocked 與 verify 並列不互抑、查找前小寫正規化、分類內 verify 聚合排序）、scaffold 範本同步。`status` 既有值域與所有精確比對邏輯（tripwire、done 歸檔豁免）零改動。同日 5-persona `/ce-doc-review` 審定 accepted（9 項修正全數套用，含繼承語意、過期語意、未接手限制之明文化）。88 項 pytest 通過（自 74 項增至 88）。

- `kunsu-init` 新增 `remove-project` 子指令（[ADR 012](docs/adr/2026-07-12-adr-candidate-012-remove-project-subcommand.md)，2026-07-12 accepted）：源自使用者發現子專案可能因檔案結構合併或拆分而需要刪除，但只有 `add-project` 沒有對應移除路徑。對稱 `add-project`（v0.2.0 → v0.3.0），僅能軍師端發起，整筆移除該子專案在本軍師的所有角色代碼登記（不支援部分角色保留）；清單呈現比照 `kunsu-list` 的失效感知選取（stale 標記排前，候選清單為 registry 與 CLAUDE.md 關聯專案表兩來源聯集，避免只認 registry 而漏掉單側殘留登記）；移除前掃描軍師自身 `docs/handoffs/` 未完成交接並警告（角色代碼取 registry／CLAUDE.md 聯集，非擇一 fallback）；不可逆最終確認與未完成交接警告為兩個獨立確認點，語意不可合併。新增 `skills/kunsu-init/scripts/registry-remove.sh`（對稱 `registry-merge.sh`，以獨立 exit code 3 區分「冪等略過」與「成功移除」，避免不可逆操作把路徑打錯誤判為已完成）。雙側寫入順序固定為先 CLAUDE.md（受版控、未 commit 前可 `git checkout` 復原）、後 registry（不可逆），CLAUDE.md 編輯後加 Grep 核查關卡才進入 registry 移除。經 `/ce-brainstorm` → `/ce-plan` 完整流程定案，4-persona `/ce-doc-review`（coherence／feasibility／scope-guardian／adversarial）發現 8 項、直接修正 6 項（含一個 P1：registry exit code 靜默誤判風險；一個 P2 邏輯錯：取消 commit 後若先 `git checkout CLAUDE.md` 再跑 `add-project` 會使 registry 與 CLAUDE.md 重新漂移，已修正復原指引）。

- **handoff done 收尾閉環**（2026-07-13）：源自實際使用回饋——軍師 session 查核完回覆後不會提示以 `/handoff done` 收尾，使用者也常忘記要求，`submitted` 交接積壓頂層持續被掃描耗 token。四斷點修補：handoff（v0.6.0）description 補七個帶交接語境的收尾口語（「交接收尾」「這份交接可以收尾了」等，與 v0.3.0 reply 路由補洞同類），done 章節補正反行為指引（發起方語境使用者表達確認即主動建議 done；接手方 repo 無相符本體時不觸發，防誤歸檔子專案對外交接）；軍師範本工作流程新增第 7 步「確認回覆後以 done 收尾歸檔」，並於 Invariant #5 內文、第 6 步、回覆信箱協議三處明列 done 唯一例外——機制層（done 流程、scan-replies 豁免、ADR 009）早已授權，憲章層字面禁令未跟上，守規 session 因此迴避建議 done 的補正；`/kunsu-inbox`（v0.4.0）軍師模式新回覆段補「→ 收尾提示行」（對稱申請／上報段既有格式，僅提示不自動執行，Invariant 1 零改動）。回覆檔 `status` 值域說明一致化為四值並加「接手方勿自標 `done`」限制語（自標會使交接從掃描面靜默消失、本體卻未歸檔），四份語意副本全數同步（handoff SKILL.md 兩處、`new-handoff.sh` printf、軍師範本值域行——後兩者分別由 doc review P1 與 Tier 1 review 抓出）。沙盤「已回覆待確認」每筆新增 verify 推導的白話下一步提示與停留天數（自最新回覆日起算、0 天顯示「今天回覆」、無效／未來日期防守降級，提示置於 `<details>` 外常態可見；附帶修正 verify 純空白字串正規化）。ivm／ebook 兩軍師 live 遷移（各二筆確認 commit）。經 5-persona `/ce-doc-review` headless（計畫期修正：憲章例外 1→3 處、done 限制語、fixture YAML 引號假綠燈）與 8-angle Tier 1 code review（雙 dict 鍵集合一致性測試等 5 筆修正）。98 項 pytest 通過（自 88 項增至 98）。

- 沙盤「已回覆待確認」verify 子分組與未接手顯眼化（2026-07-17）：源自 ebook 軍師試用回饋——14 筆已回覆待確認混雜不同驗收方式看不出「哪幾筆現在就能收尾」，未接手件又不顯眼。「已回覆待確認」由平面清單改為依 verify 顯式子分組（⚡ 馬上可測 → 📱 需實機測試 → 🚀 需上線測試 → 自由字串各 distinct 值一組 → 未標示驗收方式；順序＝可動性優先，組內改依最新回覆日期升冪讓陳年件浮頂；未接手／部分完成維持既有 `_verify_sort_key` 排序）。未接手顯眼化三件套：分類標題改 ⚠ 橘紅醒目樣式；軍師分組摘要列上浮子專案待處理計數（未接手／部分完成／待確認／異常，僅列非零項），且有未接手或異常件時強制預設展開——修正「未接手藏在『無新訊息』收合分組裡」的結構性盲點（收合判斷原本只看軍師自身新訊息掃描）；頁首新增全域總覽列（⚠ 未接手・⛔ 卡關・⚡ 馬上可測・其餘待確認・📨 新訊息，另含 tripwire／腳本錯誤軍師計數，全零不渲染；chips 與 verify badge 刻意分離 CSS class，避免破壞既有「頁面不含 badge」測試斷言）。分類邏輯（`subrepo_status.py`＝kunsu-inbox SKILL.md 4a）、handoff 協議與 verify 值域零改動，純 `main.py` 渲染層；沿用現有三個建議代碼拆分為使用者定案（「無需驗收可直接 done」的新代碼暫不引入）。以真實啟動伺服器＋curl 對照 ebook／ivm 兩軍師實況驗證（含 ivm 複合式自由字串 verify 各自成組的開放值域行為）。111 項 pytest 通過（自 98 項增至 111）。

- handoff done 歸檔前逐項驗收查核（handoff v0.7.0，2026-07-17）：源自使用者某 session 執行 insights 後獲得的建議「建立獨立 `handoff-done` skill（依日誌逐一驗證每項驗收條件、封存交接文件、草擬給協調者的回覆、以分開的 commit 提交）」，經 kunsu 化評估**不另建 skill**——「handoff done」觸發詞已屬既有 done 收尾閉環（雙 skill 撞路由）、建議步驟混合發起方（封存）與接手方（草擬回覆）兩個 kunsu 刻意分離的角色、「分開 commit」牴觸 ADR 009 不對稱 commit 設計、`.claude/skills/` 直建違反 Invariant 3 開發部署分離。僅吸收真缺口「逐項驗證驗收條件」：done 步驟 2 新增「逐項驗收查核」子步驟（交接本體問題清單與期望交付逐項對照最新回覆並回報覆蓋狀態；`verify:` 欄位存在時確認該驗收方式已實際執行，以日誌／測試輸出等證據為準、不以回覆文字宣稱代替驗證；缺口顯式列出、由使用者決定收尾或暫緩），reply 步驟 2 對稱補「逐項回答附可查核證據」指引。掃描慣例、`status`／`verify` 值域、tripwire 與歸檔形狀零改動；kunsu-inbox 依賴聲明版號同步 v0.7.0。

- **軍師沙盤新增 todo 列表顯示，`/todo` skill 併入 toolkit**（[ADR 013](docs/adr/2026-07-17-adr-candidate-013-integrate-todo-into-toolkit.md)，2026-07-17 accepted）：源自使用者想在跟 supervisor 討論時一次性攤開所有軍師累積的技術債（ebook 軍師 26 筆未歸檔、ivm 軍師 15 筆），不用逐一開軍師 session 跑 `/todo list`。同一批工作把全域 `/todo` skill（v0.1.1，原僅存在部署目錄）逐字併入 `skills/todo/`，比照 ADR 003 handoff 併入先例，`install.sh` 與 CLAUDE.md 專案結構同步。軍師沙盤新增 `app/todo_status.py` 唯讀掃描軍師自己 `docs/todos/` 頂層，兩桶計數（`orphaned_done`：status 為 已解決／已封存 但未歸檔；`pending`：其餘所有值，含未知自由字串）、三層顯示樣式（未處理已知值標籤／自由字串一般標籤／看似完成未歸檔獨立子區塊，比照 ADR 011 verify 欄位模式）、severity 排序＋archive 筆數計數；`main.py` 新增「待辦技術債」卡片區塊（新 CSS class 前綴 `tlabel`，避開既有 `badge`/`chip` 字面）；`PendingAggregate` 新增 `todo_pending` 欄位（經 `_aggregate_pending` 建構子參數帶入，因該 dataclass 為 frozen 不可於建構後指派值），全域總覽與軍師分組摘要非零才顯示「待辦 N」。經 `/ce-brainstorm` → `/ce-plan` 完整流程定案（5 個 AskUserQuestion 釐清互動範圍、todo skill 耦合處理、status 計數/顯示分離、未歸檔孤兒判定），計畫期 3-persona `/ce-doc-review`（coherence／feasibility／scope-guardian）發現並修正 R5 顯示樣式弄丟三層區分、`PendingAggregate` frozen dataclass 直接指派值會拋 `FrozenInstanceError` 兩項正確性缺陷；`ce-simplify-code` 三面向審查合併重複 CSS 宣告、修正 `_html_todo_section` 對解析錯誤靜默略過（原本全數解析失敗會誤顯示「無待辦」）；8-agent Tier 2 code review（correctness／testing／maintainability／project-standards／performance／adversarial／agent-native／learnings）發現並修正 `status` 欄位 YAML falsy 值（`false`/`0`）誤判為缺欄位的邊界案例，另發現 `/todo` skill 原有的 `git mv` 前缺 `git add`（untracked 檔案歸檔會失敗，很可能正是 ivm 軍師真實資料裡「已解決但未歸檔」異常的成因）與 `new-todo.sh` slug 產生順序（連字號先轉又被標點清除）兩個**併入前既有**的 skill 本身缺陷，因本次明訂零行為變更未在此 PR 修正，列入下方後續評估。137 項 pytest 測試通過（自 111 項增至 137）。

- **handoff done 來源 todo 查核與一併收尾，`/todo` 0.1.2 既有缺陷修正**（2026-07-19）：源自實際使用回饋——todo 升級成交接、交接完成且驗收後，常忘記把 todo 一併收尾，todo 停留「未處理」使沙盤待辦計數失真；根因是 todo 與 handoff 間無結構性連結、done 步驟無一回頭檢查來源 todo。經 `/ce-brainstorm`（中途自「frontmatter 加 handoff 欄位」的結構性方案自我修正為「done 時雙向發現」，todo 檔案格式零改動、零遷移）→ `/ce-plan` 定案：handoff（v0.8.0）done 於逐項驗收查核後新增步驟 3「來源 todo 查核」——掃描本 repo `docs/todos/` 頂層、以具體檔名雙向比對（todo 內文含交接檔名或交接本體含 todo 檔名）、AskUserQuestion 複選確認（>4 筆退化為對話數字清單；取消／零選／非互動一律不動 todo 續行收尾；無命中僅一行提示含筆數、無檔案靜默）——與步驟 4「todo 收尾執行」——非終態者 Edit status 改「已解決」＋解決依據自動填交接預期歸檔路徑，已解決／已封存孤兒僅補歸檔保留終態語意，untracked 先 `git add`，單筆失敗中止剩餘不還原；原步驟 3–7 順移為 5–9，連續執行約束改涵蓋步驟 4–7，步驟 8 連結修正與步驟 9 協議 commit 的 `git add` 範圍擴及 todo 歸檔路徑（`git mv` 不暫存 Edit 內容的陷阱四防護），commit 訊息含 todo 時附「；一併收尾 todo <slug>」註記（ADR 009 `docs:` 前綴與主體不變）。`/todo`（0.1.2）同批修正兩個併入前既有缺陷：done／rm 補 untracked 前置檢查（很可能是 ivm「已解決但未歸檔」異常成因）、`new-todo.sh` slug 以 `\001` 佔位保護連字號與底線再清標點（原順序 `[:punct:]` 會把分隔符一併清除；順帶修正底線分隔喪失）。kunsu-inbox 依賴聲明同步 v0.8.0（todo 歸檔不在其掃描範圍、無豁免需求）；CONCEPTS「done 收尾」詞條同步。計畫經 3-persona headless doc review（coherence 抓出 R6 與終態保護矛盾、feasibility 抓出「僅調換順序仍會清掉既有連字號」的 U3 正確性缺陷）。暫存目錄 dogfooding 20 項斷言全過（含 porcelain `RM`／`A` 兩種前置狀態形狀、孤兒零 diff、中文檔名 quotepath 陷阱）＋ slug 六案例；137 項 pytest 通過（沙盤零改動）。

- **軍師規劃前既有盤點與 kb 檢索接線**（2026-07-25）：源自實證案例——ebook 軍師處理「已購書籍排序」時漏查自家歷史（既有快取能力記錄於過往 plan／handoff），過度規劃至使用者人工介入才收斂；經 `/idea` 三點子 → `/ce-brainstorm`（框架反轉：主軸自「跨 repo solutions 檢索」重定位為「軍師漏查自家歷史」，handoff 回覆為最可靠的「做了沒＋結果」一手紀錄）→ `/ce-plan` 定案首發範圍為核心＋kb playbook。軍師範本工作流程步驟 2 新增「規劃前既有盤點」子步驟——以 `/kb`（zoekt）依「自家 handoffs（含 replies／archive）→ plans → 子專案文件」優先序檢索既有能力與結論，plans 命中以對應 handoff 回覆核對有效性、索引僅含已 commit 內容提醒、kb 軟依賴（服務未回應降級手動查閱不阻斷）、命中須為方案基礎或述明不採用理由；步驟 5 須包含清單加「相關既有教訓（選附，repo 名＋路徑）」。ebook／ivm／px 三 live 軍師同步遷移（ebook 客製子分類逐句保留，grep 恰中一次正反核查，各一筆確認 commit）；tshehtu kb skill 新增「搜教訓／搜歷史」playbook 段（query 範本逐條實跑命中、archive 冷區兩層檢索、引用格式，symlink 部署即時生效），並於該 repo 記兩筆既有缺陷 todo（`~/.tshehtu/project-dir` 缺失、discovery 未入排程——後者正是三軍師搬家至 `kunsu-project-root/` 後索引殘留舊路徑的成因，本輪手動重跑 discovery＋rebuild 收斂，三軍師 handoffs／plans 全數入索引）。headless doc review（coherence＋feasibility）3 筆修正全數套用；dogfooding AE1（「已購 快取」一查命中過度規劃→收斂全鏈歷史紀錄）＋AE2（bootout 服務後降級手動查閱不中斷、bootstrap 復原）通過。跨 repo solutions 檢索外環依計畫延後（[實作計畫](docs/plans/2026-07-24-001-feat-kunsu-pre-planning-inventory-plan.md)）。

- **handoff 暫離回報慣例**（handoff v0.9.0，2026-07-26）：源自實際使用回饋——交接工作已做完、成果先 commit 進 git branch（未合併），接手方臨時插入緊急需求切走且尚未回覆軍師，軍師沙盤將該交接誤判為「未接手」；機制正確、訊號缺席（協議唯一狀態源是回覆檔），且事發語句「把做好的部份先移到新的 branch」無任何交接語彙，單靠觸發詞攔不住。經 `/ce-brainstorm`（status 定調固定 `partial`——合併上線等剩餘步驟仍在接手方手上，避免發起方誤啟收尾；branch 名以點開回覆內文可見為準，不加 frontmatter 欄位）→ `/ce-plan` 三單元執行：reply 段新增「暫離回報」子節（最小內文三要素——branch 名、一句現況、回來意向；verify 照常選填且 branch 不入 verify；回歸後照常投遞 `submitted` 完成回覆並顯式複寫 verify）、description 補四個帶交接語境觸發詞（「交接工作先暫停」「暫停這份交接」等，套用 solutions 補詞三步驟教訓——帶語境拒裸詞、負向場景核查）、「回覆方式」定型文字兩副本各加一行暫離提示（產生器 printf 與 SKILL.md 範例段字面一致，順手拉齊兩處既有斷行差異）。`status`／`verify` 值域、四份值域語意副本、沙盤分類邏輯、軍師範本一律零改動，免 live 軍師遷移；kunsu-inbox 依賴聲明同步 v0.9.0（一併收斂 0.8.1 patch 未同步的既有漂移）。需求經 4-persona doc review（4 筆修正全數套用，含「可靠攔截」過度承諾降為條件式陳述、AE1 補「session 已讀交接檔」前置條件），計畫經 3-persona headless review；暫存目錄實跑產檔驗證兩副本逐字一致。CONCEPTS「暫離回報」詞條同步。

- **handoff done 收尾沉澱訊號查核**（handoff v0.10.0，2026-08-12）：源自 Agent Memory 文章（AILogora）五條發想之一（記憶 write 側補強）——教訓沉澱全靠使用者事後想起 `/ce-compound`，實際發生過「規劃時得由使用者親自指示以前已發生過」；live 軍師沉澱率實測極不均（ebook 84 筆歸檔交接對 11 篇非種子 solutions、ivm 41/2、px 16/0）。done 步驟 2 新增「沉澱訊號查核」子項——多份回覆時通讀全部回覆判斷往返軌跡（**新增讀檔範圍**，結論確認仍以最新一份為準；此前提為 doc review feasibility persona 抓出的 P1 修正：原計畫誤稱步驟 2 本來就通讀，實則僅讀最新一份，照字面實作訊號場景必然失敗）、判斷五類訊號（往返翻案、blocked 軌跡、與原規劃落差、多輪往返、經接受的驗收缺口）、字面存在即記下不確定傾向記下；步驟 9 回報附一句候選教訓摘要與 `/ce-compound` 建議（含手動沉澱至 `docs/solutions/` 的 fallback），僅提示不自動執行、無訊號靜默、暫緩收尾不提示——「CE 指令由使用者發起」原則零改動。落點僅 handoff SKILL.md 單一語意副本（依 done 收尾閉環的多副本教訓），軍師範本零改動免三軍師遷移、不新增觸發詞（掛載點依攔截點教訓選在 session 必經路徑，不吃觸發詞覆蓋上限）；kunsu-inbox 依賴聲明同步 v0.10.0（不涉掃描慣例、無豁免需求）、CONCEPTS「done 收尾」詞條同步。經 `/ce-brainstorm`（live 軍師沉澱統計實測查證）→ `/ce-plan` → 2-persona 兩輪 doc review（headless＋互動 walkthrough，共 2 筆修正）；暫存目錄 dogfooding 22 項斷言全過（訊號場景證明先前回覆確實被讀取——摘要含僅存在於第一、二份回覆的內容；乾淨場景零沉澱文字；暫緩場景不提示；無回覆邊界；歸檔全鏈 porcelain `RM` 形狀無回歸）。同批發想的 idea 2（solutions 失效欄位）查證判定不適用（`/ce-compound`／`/ce-compound-refresh` 原生已覆蓋且哲學相反，見 `docs/ideas/`），idea 3（tshehtu memory index）縮減為 kb playbook「彙整模式」補充並已於 tshehtu repo 落地。

- **跨功能邏輯連結稽核與 15 筆漂移收斂**（2026-08-12）：源自使用者提問「加了諸多功能後，彼此邏輯是否仍完整連結」。四個唯讀 subagent 各查一軸——ADR 001–013 逐條 vs 實作、CONCEPTS 21 詞條 vs 行為權威來源、三條訊息生命週期全交界（申請／上報／交接鏈）、範本 vs 三 live 軍師 vs skill 三方——主幹全數通過（registry schema 六消費者一致、歸檔形狀與掃描豁免形狀精確對合、三信箱協議與七步驟三方同版），15 筆確認漂移全數修正、1 筆假警報經 grep 實證駁回（兩 agent 同稱 CLAUDE.md 停在 v0.9.0——多 agent 同錯佐證逐筆抽驗必要）。**行為級**：handoff done 取最新回覆改依檔名 `(日期, 序號)` 數值排序（v0.10.1——原依 frontmatter `created` 同日多份無法消歧，為全體系唯一未採該慣例的消費端）；`scan-replies.sh` 對修改／刪除已 commit 回覆由靜默忽略改判 tripwire（kunsu-inbox v0.4.1，憲章與機制對齊，七場景 fixture 迴歸通過）。**協議矛盾級**：範本 kunsu-concepts「交接文件」詞條補 done 唯一例外（2026-07-13 憲章掃蕩漏掉的副本，新軍師不再帶矛盾出生）；ivm 軍師申請信箱協議補 ADR 007 遷移（`proposed_role` 代碼化＋`role_desc` 欄＋語彙，live 間唯一實質分歧收斂）；HOME dataview 交接區塊 `date`→`created`（範本＋三 live，原日期欄恆空）。**文字追述級十筆**：CONCEPTS 四詞條（角色代碼誤納 `in_reply_to`、盤點外環超前、上報四步驟、確認 commit 窮舉補 remove-project）、kunsu-init 四處「六步驟」→七步驟與三信箱列舉（v0.3.1）、ADR 011 排序規格修訂註記（實作已依 2026-07-17 定案演化）、kunsu-apply「自動歸檔」改確認制措辭、範本目錄預建句（＋三 live 同句）、ebook 回覆範例枚舉去寫死、kunsu-inbox schema 註解「角色名稱」正名代碼。機械層檢查同批沉澱為 `scripts/consistency-check.sh`（21 項：版號鏈、值域副本、定型文字 mktemp 實跑逐字比對、install 覆蓋、分類詞對映、dataview 欄位、六步驟防回歸、live 軍師經 registry 動態發現的 WARN 級同步抽查），可隨時重跑。

- **SessionStart hook 第二階段啟用（知悉層自動化 Phase A）**（[ADR 014 candidate](docs/adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md)，2026-08-13）：源自使用者實況回饋（[需求文件](docs/brainstorms/2026-08-12-awareness-automation-requirements.md)）——一次派發同時涵蓋 3～4 個子專案、各 session 長駐不關以 `/clear` 清理，逐視窗手動 `/kunsu-inbox` 的輪詢成本全落在使用者身上；官方文件查證 `/clear` 觸發 SessionStart（matcher source 五值）且 stdout 注入清空後 context，hook 與既有習慣直接咬合。新增 `skills/kunsu-inbox/scripts/session_hook.py`（kunsu-inbox v0.5.0）：身分獨立雙判斷（ADR 002 Decision 2，raw registry＋git root 快速比對，不跑全路徑健康檢查以保未登記快退）、子專案模式匯入沙盤 `subrepo_status.py`、軍師模式匯入 `kunsu_scan.py`（分類邏輯零重寫、單一來源）、每分類上限 5 筆＋「另有 N 筆」、created／最新回覆日期升冪陳年件浮頂、stale 軍師路徑失聯警示、fail-open（身分確認前靜默、確認後單行降級，一律 exit 0 不阻斷 session）。SKILL.md 授權邊界第 2 條補「事件驅動非輪詢」明文化（機制先行、憲章同步的既有教訓），新增「SessionStart hook」節含 settings.json 掛載範例與解除說明；掛載為機器層級設定不進 repo。launchd 通知哨兵原案於需求審視階段廢棄（單人拓撲推播只轉述自己觸發的事件＋通知時刻與遺忘時刻錯位）。12 項 pytest（149 全過）、consistency-check 21 項通過。Phase B（派發即推播——軍師 session 派發完成當下向目標子專案長駐 session 發送純告知訊息，落地點以本機 session 網格實測確認存在）待 ADR Candidate 015 對 ADR 002 推播否決翻案後另行動工。

- **派發即推播（知悉層自動化 Phase B）**（[ADR 015 candidate](docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md)，2026-08-13）：對 ADR 002「daemon 輪詢推播」否決的翻案——翻案基礎為事實前提變更（使用者 session 長駐實況＋本機 session 網格實測可定址）與機制變更（非 daemon 輪詢，而是軍師 session 於派發完成當下發送的一次性事件驅動訊息，零輪詢零常駐零狀態檔，Invariant 1 字面合規、無需比照 ADR 010 開例外）。handoff add 新增步驟 6（v0.11.0，僅 kunsu 語境）：registry 反查 `to:` 角色對應子專案 → ListAgents 名稱啟發式匹配（唯一且明確才發送，寧漏發不誤發，降級不重試由 SessionStart hook 兜底）→ SendMessage 定型通知（訊息自足自帶收方指令——僅回顯勿開工勿讀檔，Invariant 2 零觸碰）→ 回報已推播／未推播清單；ListAgents／SendMessage 不可用整步跳過。CONCEPTS「派發即推播」詞條、kunsu-inbox 依賴聲明同步 v0.11.0（不涉掃描慣例）。R13 試點（2026-08-13）：向 eBookApp 長駐 session 實發真實待接手通知成功，實測發現跨 session 裸名發送需依錯誤訊息附 `[ref]` 重送（已補進步驟 6-3）；試點於同日通過（使用者確認軍師 session 實發至 ios-app session 觸發成功、收方僅回顯——推斷一、三同時驗證），**回覆方向同日對稱納入**（ADR 015 Decision 6 修訂）：handoff reply 新增步驟 6「回覆即推播」——kunsu 語境回覆（含暫離回報）落入軍師信箱後，以同一套兩層匹配通知軍師 session（慣例名 `<軍師目錄名>-kunsu`），降級由軍師端 hook 與 `scan-replies.sh` 兜底，「未 commit 即新回覆」訊號零改動。同批確立 **kunsu session 命名慣例**（查證 settings.json 無命名 key；`/rename`／`claude -n` 為官方機制且該名稱即 SendMessage 定址名）：子專案 `<軍師目錄名>-<角色代碼>`、軍師 `<軍師目錄名>-kunsu`，步驟 6-2 升為兩層匹配（慣例名精確比對優先、啟發式 fallback）；新增 `scripts/kc.fish` 啟動函式（fish autoload，依 registry 自動 `-n` 命名，未登記／`--resume` 透傳，五路徑解析實測正確，已部署 ~/.config/fish/functions/）。

- **回覆內容路由與收尾殘項清點**（handoff v0.12.0／todo v0.2.0／kunsu-inbox v0.6.0，2026-08-13）：源自 ebook 軍師檢討「回覆讀完後內容各自去哪」的流程缺口（事件三、四、六——指向軍師的行動項與已解答疑問無落點，只靠當次 session 記憶承載；事件四時間線證明含行動項回覆在 done 收尾當下已被讀取、僅查核面未涵蓋）。三軍師實例查證確認屬系統層面：ivm 51 份回覆 19 筆行動項僅 1 筆漏接、且為「行動項曾入 todo、整檔標已解決歸檔時殘項蒸發」的容器蒸發型；px 33 份逾 20 筆全路由、靠 kunsu 未規定的自建紀律補位。三道輕量查核全掛既有收尾／彙整必經路徑（比照沉澱訊號查核掛載模式，零觸發詞、僅提示不自動執行）：done 步驟 2 新增**反向路由查核**（附掛沉澱訊號查核通讀動作、零新增回覆讀檔，偵測指向發起方／第三方的行動項與已解答既有疑問——全回覆聯集、撤回者標註不剔除；命中於步驟 2 當下回報、查核無狀態暫緩重跑必再提示，與沉澱訊號「留待步驟 9」刻意相反；回填白名單限 todo／plan，交接本體為定案快照不可回填、改提示附回覆路徑；疑問查核範圍設優先序上限——todos 頂層全讀→本體引用文件→plans 標題段，archive 不入範圍、範圍外漏報顯式接受）；done 步驟 4 與 `/todo` done 新增**殘項清點**（todo 標已解決前掃描「下一步」等段未完成子項，三去向：一併已解決／轉出新 todo（裁決即授權代建，內文註明轉出自原檔歸檔後路徑）／保留退出收尾並自 commit 訊息剔除；孤兒同樣清點、不改終態；步驟 9 `git add` 擴及轉出 todo、訊息加註「；轉出殘項 todo <slug>」含訊息表格第二副本同步；rm 明文不清點）；kunsu-inbox 軍師模式新回覆／新上報段各加**分流提示行**（比照 v0.4.0 收尾提示行的 inbox 提示／handoff 執行分工）；步驟 3 候選 todo 同時被反向查核命中時 description 註明衝突且不建議收尾（防堵容器蒸發重演）。零腳本零範本改動免三軍師遷移；SessionStart hook 摘要不加提示行（hook 導引 `/kunsu-inbox`，避免第二文案副本）；上報顯式接受單層保障（歸檔四步驟人工審閱為等效攔截點）。事件五拆出兩筆 idea 另行發想（接手方矛盾回報義務、交接本體勘誤落點——後者涉 Invariant #5 屬 ADR 層級）。經 `/ce-brainstorm`（三軍師查證定範圍）→ 三路研究（repo 結構／learnings／flow 分析 2 Critical＋8 Important＋8 Minor 全數收攏為計畫 R9–R16）→ `/ce-plan` → 3-persona doc review（3 筆 P2 全套用，含 commit 訊息第二副本漏列）；dogfooding 23 項斷言全過（歸檔全鏈 porcelain `RM`／`A` 無回歸、轉出 todo add 範圍與新訊息格式、不可觸碰定型行零 diff、步驟編號引用零漂移）、consistency-check 22 項全 PASS、149 項 pytest 零改動照常通過。

- **接手方矛盾回報指引**（handoff v0.13.0，2026-08-14）：源自 ebook 軍師三份流程缺口研究文件——事件五記錄軍師交接把密碼欄位方向寫反（憑常識推論填補回覆未載明的細節），接手方依封包原文做對了卻未回報「與交接所述不符」，軍師靠彙整比對兩份表格才察覺；ebook 自行在交接期望交付加「發現不符請指出」項的田野機制四次實施全數被執行，2026-08-14 首次實質命中（接手方指出數字不一致、判斷不影響結論仍回報，順查揭出中介文件實質錯誤，命中價值遠大於命中點）。經 `/ce-brainstorm` 定案——期間使用者定調「harness 不做高能力模型的枷鎖」設計前提（機制優先信息補全與帶理由的規範，不採行為強制），落地形態自「一律回報核對結果」收斂為**帶理由的 norm、命中才報**：reply 步驟 2 於證據 redact 提醒與 verify 評估之間新增矛盾回報指引，涵蓋「與所持參照物不符」與「內文自相矛盾」兩類，明訂「即使判斷不影響自身實作也在回覆中明列並附位置」，指引自帶理由（接手方是唯一同時持有交接與參照物的一方、未被指出的錯誤認知會留存於定案快照並跨交接流傳）；不強制每份回覆附核對聲明、兩種語境通用不設分支、明示矛盾寫回覆內文不回頭改交接本體（Invariant #5 零改動）。單一語意副本、零觸發詞（攔截點教訓）、零腳本零範本改動免三軍師遷移；讀方承接沿用 v0.12.0 反向路由查核（矛盾指摘屬指向發起方的行動項），並界定 2026-08-13「寫方標記不做」的理由僅適用行動項／答案類、不涵蓋矛盾類。kunsu-inbox 依賴聲明同步 v0.13.0（reply 流程內部指引，不涉掃描慣例）、CONCEPTS「矛盾回報」詞條新增。經 `/ce-plan` → 2-persona headless doc review（coherence 零 findings；feasibility 六項事實查證全屬實、1 筆 FYI 檢核句期望計數已採納）；consistency-check 全項 PASS。同批自 ebook 研究文件記錄三筆 idea 待後續發想：軍師副官機制（過載假設——新鮮 context 分擔查證與覆核）、軍師事實斷言來源層級標注（前兩者同屬軍師端宜合場）、交接引用路徑隨歸檔腐化（與勘誤落點合場，涉 Invariant #5 屬 ADR 層級）。

### 尚未實作／後續評估
- ADR 008 open questions 留待用量評估——歸檔 `status` 值域升級（現為單一 `archived`）、「軍師已讀」輕量標記、上報量成長後的整理慣例。
- applications 的 HOME dataview 補齊、add-project reports 遷移不含 HOME dataview 附加（已知落差，見實作計畫 Scope Boundaries）。
- busy session 收訊排隊時機（派發即推播推斷二）留待實際使用觀察。
- `/handoff` 升版全面改查註冊表（reply 的 kunsu 語境分支已於 v0.3.0 實作查表定位軍師；其餘子指令未查表，維持獨立延後決策，ADR 002 Decision 6）。
- 角色改名的追溯修復工具化（ADR 002 Deferred／[ADR 007](docs/adr/2026-07-08-adr-candidate-007-role-code-description-separation.md) Open Questions；代碼穩定＋Decision 7 唯一性可減少非必要改名，但自動批次修復仍缺，現行為 add-project 警告掃描）。
- add-project 內建「整句 `roles` → 代碼」自動遷移偵測（ADR 007 Open Questions；本次已手動遷 ivm 三筆＋ebook-store-nginx，工具內建供其他既有軍師升級待評估）。
- 角色說明欄留空時關聯專案表的呈現規格（ADR 007 Open Questions；顯示「無說明」佔位 vs 留空欄，待範本落地時定）。
- 跨 repo solutions 檢索外環（全域 CLAUDE.md 慣例薄段＋ce-learnings-researcher 間接觸及）——等跨 repo 檢索實痛出現再做，落點建議全域 CLAUDE.md 直加（2026-07-24 計畫 Scope Boundaries）。

### 相關資產（唯讀參考）

| 資產 | 路徑 | 用途 |
|------|------|------|
| ebook 專案群規劃中心 | （本機私有路徑，略） | 範本母本；其 `docs/solutions/` 有兩篇模式沉澱文件 |
| 全域 /init-obsidian-vault skill | `~/.claude/skills/init-obsidian-vault` | scaffold 的 Obsidian vault 步驟直接呼叫（軟依賴，未安裝時略過） |
| ce-team（先前嘗試） | （本機私有路徑，略） | 失敗教訓來源，不沿用其程式碼 |

## 版本控制

本目錄為獨立 git repo。不主動 commit，除非使用者明確要求。

里程碑以 **git tag** 標記（annotated tag，repo 層級 semver，自 v1.0.0 起；2026-08-13 立約）——與各 skill 的 SKILL.md frontmatter 版號**互相獨立**：skill 版號隨個別 skill 演進照舊記錄於 frontmatter 與 commit 訊息，tag 則標記整個工具組的發布里程碑；打 tag 與 push 均由使用者明確要求時執行。
