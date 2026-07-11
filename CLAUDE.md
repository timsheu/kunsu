# kunsu

kunsu（軍師，台語 kun-su）——為多 repo AI 協作建立「軍師」（規劃協調中心）的 scaffolding 工具組：以純 skill＋範本快速建立唯讀的軍師 repo，並以全域反向註冊表自動化跨 session 傳令。本專案是工具母體——skill 原始碼在此開發與版控，部署目標為 `~/.claude/skills/`。

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
  adr/                 → ADR（001–009 全數 accepted）
  solutions/           → 可重用學習與解法（/ce-compound 產出，YAML frontmatter 依 module/tags/problem_type 可搜尋）
skills/                → skill 原始碼
  handoff/             → 通用交接原語（v0.4.0，2026-07-06 自部署目錄併入，見 ADR 003）
    SKILL.md           → add／reply／list／done 子指令（reply 含 kunsu 語境分支；add／done／本地 reply 尾端確認 commit）
    scripts/           → new-handoff.sh、new-handoff-reply.sh
  kunsu-init/          → 軍師 scaffolding
    SKILL.md           → 訪談→查證→產檔→vault→git→註冊表主流程＋add-project 子指令（申請審核制）
    scripts/registry-merge.sh → 註冊表 read-merge-write（python3）
    assets/templates/  → 軍師範本（CLAUDE.md／CONCEPTS.md／README／HOME dataview 區塊＋PLACEHOLDERS.md）
    assets/solutions/  → 兩篇種子沉澱文件（自母本通用化）
  kunsu-inbox/         → 跨 session 傳令自動化
    SKILL.md           → 模式偵測（獨立雙判斷）＋子 repo／軍師雙模式
    scripts/scan-replies.sh → 未 commit 回覆掃描＋tripwire（done 授權歸檔豁免、雙側核驗）
    scripts/scan-applications.sh → 申請信箱掃描＋tripwire（雙側核驗授權歸檔）
    scripts/scan-reports.sh → 上報信箱掃描＋tripwire（結構同 scan-applications.sh）
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
    app/               → registry.py／kunsu_scan.py／subrepo_status.py／main.py
    tests/             → pytest，58 項測試
install.sh             → 部署至 ~/.claude/skills/（預設 copy、--link 開發模式）
```

## 文件導航

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/brainstorms/2026-07-06-planner-toolkit-requirements.md](docs/brainstorms/2026-07-06-planner-toolkit-requirements.md) | 種子需求：問題定義、ce-team 教訓、母本解剖、方案設計 |
| [docs/adr/](docs/adr/) | ADR（001–004 於 2026-07-06、005 於 2026-07-07 審定為 accepted；006 申請信箱與 008 上報信箱於 2026-07-09 accepted；007 角色代碼／說明分離於 2026-07-08 accepted；010 kunsu-dashboard 對 Invariant 1 的例外於 2026-07-11 accepted——全數 accepted） |
| [docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md](docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan.md) | 實作計畫（12 條 requirements、7 個實作單元，已執行完畢） |
| [docs/plans/2026-07-07-001-feat-application-inbox-plan.md](docs/plans/2026-07-07-001-feat-application-inbox-plan.md) | 申請信箱實作計畫（R1–R20、六個實作單元） |
| [docs/plans/2026-07-08-001-refactor-role-code-description-separation-plan.md](docs/plans/2026-07-08-001-refactor-role-code-description-separation-plan.md) | 角色代碼／說明分離實作計畫（R1–R22、九個實作單元） |
| [docs/plans/2026-07-08-002-feat-report-inbox-plan.md](docs/plans/2026-07-08-002-feat-report-inbox-plan.md) | 上報信箱實作計畫（R1–R25、八個實作單元，已執行完畢） |
| [docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md](docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md) | kunsu 訊息聚合本機 Dashboard 實作計畫（R1–R10、六個實作單元，已執行完畢） |

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
- **kunsu 訊息聚合本機 Dashboard**（[ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)，2026-07-11）：新增 `skills/kunsu-dashboard/`，獨立本機 FastAPI 服務彙整全域註冊表裡所有軍師與子專案的訊息狀態，取代逐一切換 CLI 視窗手動執行 `/kunsu-inbox` 的做法；刷新瀏覽器頁面才即時重新掃描，不跑背景 worker，啟動停止由使用者手動掌握。**本專案首次引入 pip 依賴（fastapi／uvicorn／PyYAML）與常駐服務**，字面上牴觸 Invariant 1，ADR 010 明訂例外範圍界定（唯讀、無背景輪詢、text/html-only 硬性技術條件、不得有自主重啟路徑）與未來比照此例外的判斷條件；`SKILL.md` 僅作安裝／啟動說明，刻意不使用觸發語慣例格式。依 [實作計畫](docs/plans/2026-07-11-001-feat-kunsu-dashboard-plan.md)（R1–R10、六單元，U6 ADR 先於程式碼動工完成一輪 doc-review）執行，Tier 2 code review（xhigh，10 finder angles）發現並修正 9 個經驗證的正確性缺陷（含 registry 雙重讀取 TOCTOU 競態、tripwire 於無明細行時靜默遺失、stale 軍師誤報「無待處理交接文件」等），58 項 pytest 測試通過，並以真實啟動伺服器＋curl 驗證端到端行為。

### 尚未實作／後續評估
- ADR 008 open questions 留待用量評估——歸檔 `status` 值域升級（現為單一 `archived`）、「軍師已讀」輕量標記、上報量成長後的整理慣例。
- applications 的 HOME dataview 補齊、add-project reports 遷移不含 HOME dataview 附加（已知落差，見實作計畫 Scope Boundaries）。
- SessionStart hook（第二階段，待 `/kunsu-inbox` 用出實際手感後再評估，ADR 002 Decision 3）。
- `/handoff` skill 升版改查註冊表（現已內建於本 repo，施工地點明確；仍為獨立延後決策，ADR 002 Decision 6）。
- 角色改名的追溯修復工具化（ADR 002 Deferred／[ADR 007](docs/adr/2026-07-08-adr-candidate-007-role-code-description-separation.md) Open Questions；代碼穩定＋Decision 7 唯一性可減少非必要改名，但自動批次修復仍缺，現行為 add-project 警告掃描）。
- add-project 內建「整句 `roles` → 代碼」自動遷移偵測（ADR 007 Open Questions；本次已手動遷 ivm 三筆＋ebook-store-nginx，工具內建供其他既有軍師升級待評估）。
- 角色說明欄留空時關聯專案表的呈現規格（ADR 007 Open Questions；顯示「無說明」佔位 vs 留空欄，待範本落地時定）。

### 相關資產（唯讀參考）

| 資產 | 路徑 | 用途 |
|------|------|------|
| ebook 專案群規劃中心 | （本機私有路徑，略） | 範本母本；其 `docs/solutions/` 有兩篇模式沉澱文件 |
| 全域 /init-obsidian-vault skill | `~/.claude/skills/init-obsidian-vault` | scaffold 的 Obsidian vault 步驟直接呼叫（軟依賴，未安裝時略過） |
| ce-team（先前嘗試） | （本機私有路徑，略） | 失敗教訓來源，不沿用其程式碼 |

## 版本控制

本目錄為獨立 git repo。不主動 commit，除非使用者明確要求。
