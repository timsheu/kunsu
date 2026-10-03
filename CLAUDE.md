# kunsu

kunsu（軍師，台語 kun-su）——為多 repo AI 協作建立「軍師」（規劃協調中心）的 scaffolding 工具組：以純 skill＋範本快速建立唯讀的軍師 repo（軍師沙盤為唯一例外，見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)），並以全域反向註冊表自動化跨 session 傳令。本專案是工具母體——skill 原始碼在此開發與版控，部署目標為各 agent 的 skill 目錄（Claude Code `~/.claude/skills/`、Codex `~/.agents/skills/`，見 ADR 019）。

## 核心規範（Invariants）

1. **純 skill＋範本，不建編譯型工具** — 交付物是 markdown 範本、skill 指令文件與少量膠水腳本（shell），不建立 Rust／Go／Python 等需要獨立維護的工具專案。理由見 [docs/adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md](docs/adr/2026-07-06-adr-candidate-001-pure-skill-no-injection.md)。
2. **絕不注入子 repo** — 工具產出的軍師對其子專案唯讀；本工具本身也不在任何目標 repo 寫入 managed section 或設定。所有機器路徑的**常設登記**只存在於兩處：各軍師自己 CLAUDE.md 的關聯專案表，以及全域註冊表 `~/.claude/kunsu-registry.json`（申請信箱中待審申請的 `path` 欄位為暫態投遞內容，核准即轉入上述正式登記、歸檔後僅為歷史紀錄；上報信箱中上報檔的情報內容同屬暫態投遞，不構成機器路徑的常設登記，見 ADR 006、ADR 008）。
3. **開發與部署分離** — skill 原始碼在本 repo 版控，經 `install.sh` 部署（symlink 或 copy）至各 agent 的 skill 目錄（Claude Code `~/.claude/skills/`、Codex `~/.agents/skills/`，ADR 019），不直接在任何部署目錄內開發。與 `~/.claude/rules` 既有的 install.sh 模式一致。
4. **範本母本唯讀參考** — 抽象化來源為 ebook 專案群規劃中心（本機私有路徑，略），僅唯讀查閱，不回頭修改母本。

## 專案結構

```
CLAUDE.md
CONCEPTS.md            → 領域詞彙表（實體、具名流程、狀態概念；/ce-compound 維護）
docs/
  README.md            → 文件中心主索引
  brainstorms/         → 需求（種子：2026-07-06 需求彙整）
  plans/               → 實作計畫（/ce-plan 產出）
  adr/                 → ADR（001–015、017–020 accepted；016 proposed）
  solutions/           → 可重用學習與解法（/ce-compound 產出，YAML frontmatter 依 module/tags/problem_type 可搜尋）
  playbooks/           → 操作教學（端到端工作流程、軍師沙盤導覽；手工維護，自 README 拆出的教學唯一落點）
  history/             → 開發日誌（已完成條目自 CLAUDE.md 遷出，新條目追加於此）
skills/                → skill 原始碼
  handoff/             → 通用交接原語（v0.24.1，見 ADR 003）
    SKILL.md           → add／reply／list／done 子指令（add 含引用檔名權威慣例、斷言層級紀律與更正交接子節（corrected_by 補記）；done 回報含斷言自查兩態附句；reply 含 kunsu 語境分支、verify 驗收方式選填欄位、逐項回答附證據指引、矛盾回報指引與暫離回報最小 partial 回覆；done 含收尾口語觸發、發起方守門、歸檔前逐項驗收查核、沉澱訊號查核、反向路由查核與來源 todo 查核一併收尾（todo 收尾含殘項清點）；done 步驟 5–7 歸檔執行腳本化（archive-handoff.sh）；add 產檔查重（時間窗清單＋tshehtu 關鍵詞層，advisory）、done 步驟 3 以 `--precheck` 印候選、步驟 4 以 archive-todo.sh 執行；add／done／本地 reply 尾端確認 commit——宣告範圍契約：帶兩形 pathspec、`&&` 串接與排序規則，ADR 018）
    scripts/           → new-handoff.sh（產檔＋查重＋第 6 參數 `depends_on` 依賴宣告——flow 形置 tags 後、stderr 印宣告筆數或未宣告提醒；本地時間窗清單＋tshehtu zoekt 關鍵詞層，stderr advisory、降級與零命中顯式；第 7 參數 `series` 線別——YAML 敏感字元寫檔前拒收、frontmatter 純量欄，產檔後 stderr 印同線本體計數與線總表訊號：有總表印路徑、同線 ≥3 份無總表印可貼上的骨架、多檔標 ⚠、讀檔錯誤顯式略過）、new-handoff-reply.sh、archive-handoff.sh（done 歸檔執行：status Edit→成對 git mv→僅具體路徑暫存，掃 index 聚合 todo 三形進訊息與 pathspec、尾端印引用偵測，印出帶兩形 pathspec 的待確認 commit 指令、不 commit；`--precheck` 印來源 todo 雙向比對候選）
  todo/                → CE 副作用 TODO 清單管理原語（v0.4.0，見 ADR 013）
    SKILL.md           → add／list／done／rm 子指令，管理 docs/todos/ 一檔一項技術債（done 含殘項清點；done／rm 歸檔經 archive-todo.sh 腳本化，印待確認 commit 指令、不主動 commit）
    scripts/           → new-todo.sh、archive-todo.sh（todo 歸檔執行：status Edit＋依據回填→untracked 前置 add→git mv→add 目的地；`--done`／`--rm` 單一終態、`--from-handoff` 抑制指令輸出交由 archive-handoff.sh 聚合）
  kunsu-init/          → 軍師 scaffolding
    SKILL.md           → 訪談→查證→產檔→vault→git→註冊表主流程＋add-project（申請審核制）＋remove-project（整筆移除）子指令
    scripts/registry-merge.sh → 註冊表 read-merge-write（python3）
    scripts/registry-remove.sh → 註冊表 read-remove-write，獨立 exit code 區分冪等略過與成功移除（python3）
    assets/templates/  → 軍師範本（CLAUDE.md／CONCEPTS.md／README／HOME dataview 區塊＋PLACEHOLDERS.md；工作流程第 3 步為條件式線總表——單／兩份交接不立 plan、同線 ≥3 份才由軍師自寫 `docs/plans/` 輕量總表、frontmatter `series` 與交接對齊）
    assets/solutions/  → 兩篇種子沉澱文件（自母本通用化）
  kunsu-inbox/         → 跨 session 傳令自動化
    SKILL.md           → 模式偵測（獨立雙判斷）＋子 repo／軍師雙模式（軍師模式含收尾與分流提示行）
    scripts/scan-replies.sh → 未 commit 回覆掃描＋tripwire（done 授權歸檔豁免、雙側核驗）＋歷史夾帶偵測與掃描統計（advisory；狀態檔 ~/.claude/kunsu-scan-stats.json；含 MISDECLARED_ARCHIVE_ADD 非白名單訊息夾帶 archive 新增偵測與 TRUNCATED 截斷聲明，ADR 018）
    scripts/scan-applications.sh → 申請信箱掃描＋tripwire（雙側核驗授權歸檔）
    scripts/scan-reports.sh → 上報信箱掃描＋tripwire（結構同 scan-applications.sh）
    scripts/archive-report.sh → 上報歸檔執行（status Edit→untracked 前置 add→git mv→add 目的地，印出帶兩形 pathspec 的待確認 commit 指令、不 commit）
    scripts/session_hook.py → SessionStart hook：session 啟動（含 /clear）自動注入信箱摘要（ADR 014，複用沙盤分類模組；含 handoff skill 版號變動提示——狀態檔 ~/.claude/kunsu-hook-state.json；子專案行尾附交接依賴圖推導態與最新回覆首句摘錄（「｜摘錄「…」」、空值零後綴）、軍師模式加依賴圖異常一行，建圖失敗只降級該行）
    scripts/handoff-graph.py → 交接依賴圖 CLI（匯入沙盤 handoff_graph 模組，印 DEP:／DEP_CYCLE:／DEP_UNRESOLVED:／DEP_ANOMALY:／DEP_NONE 固定前綴行供 4a／4b 讀取，`--role` 過濾，一律 exit 0）
    scripts/pretooluse_git_guard.py → PreToolUse hook：軍師 repo 攔寬範圍 git add（ADR 017，凍結三形狀＋逃生門＋deny 入統計，fail-open）
    scripts/prompt_inbox_hook.py → UserPromptSubmit hook：軍師 repo 每句提問掃三信箱未 commit 新件，一行注入（首次列名、之後計數、輪替每份恰點名一次；自跑 git status 不呼叫 scan 腳本；狀態共用 kunsu-hook-state.json 的 prompt_inbox 鍵、差集自清；斜線指令與非軍師 repo 快退不啟動 git；fail-open，ADR 014 修訂註記）
    tests/             → pytest，session hook、UserPromptSubmit hook、git guard 與 handoff-graph CLI 測試
  kunsu-apply/         → 子專案端投遞申請加入
    SKILL.md           → 自動偵測＋registry 選軍師＋守門與冪等預檢
    scripts/new-application.sh → 申請檔產檔（frontmatter＋防撞）
  kunsu-report/        → 子專案端投遞主動上報
    SKILL.md           → 僅服務已登記 repo＋信箱守門＋反向重導（是否其實是回覆）
    scripts/new-report.sh → 上報檔產檔（stdin 內文＋frontmatter＋防撞）
  kunsu-list/          → 全域登記清單查詢
    SKILL.md           → 唯讀列出註冊表全部登記（無 git 身分前提，任何目錄可執行）
    scripts/registry-list.sh → 按軍師分組＋stale 偵測＋當前位置標記（python3）
  kunsu-dashboard/     → kunsu 訊息聚合本機網頁（非可觸發的 skill，frontmatter 以兩 agent 原生旗標停用選用，見 ADR 010／019；登入自動啟動選用路徑見 ADR 020）
    launchd/           → kunsu-dashboard.plist.template（使用者親手安裝的 LaunchAgent 範本，只含 RunAtLoad 等五個白名單鍵，consistency-check R 項檢查）
    SKILL.md           → 純安裝／啟動說明，不涉及觸發語
    requirements.txt   → fastapi／uvicorn[standard]／PyYAML／markdown-it-py（唯一 pip 依賴；markdown-it-py 為全文頁渲染，缺席降級）
    app/               → registry.py／kunsu_scan.py／subrepo_status.py（含最新回覆首句摘錄唯讀擷取，display-only）／todo_status.py／handoff_graph.py（交接依賴圖：頂層＋archive 建圖、直接邊推導可開工／等依賴、Tarjan 循環、無法解析與異常顯式回報——三消費端單一來源）／handoff_graph_html.py（inline SVG 分層排版、dlabel 標籤、錨點、活節點 >8 降級文字清單）／board_model.py（看板模型：持球者泳道 × 狀態欄的卡片歸屬與異常彙整，純函式、分類零改動）／board_html.py（看板頁 `/` 與 archive 頁 `/archive` 渲染，`kb-` class 前綴，不匯入 main）／html_common.py（各頁共用輔助：頁面骨架、讀檔、錨點、verify 標籤、停留天數）／markdown_render.py（全文頁 Markdown 伺服器端渲染：markdown-it-py `html=False` 轉義原始 HTML、預設 validateLink 擋 `javascript:`，frontmatter 鍵值表逐值 escape；匯入失敗降級 `<pre>`）／handoff_detail.py（全文頁資料模型：`f` 路徑守門——四允許目錄＋單層 `.md`＋resolve 核對擋 symlink、同串回覆依 `in_reply_to` 舊→新；純讀檔不呼叫掃描）／board_html.py 另含四組配色主題（墨與朱預設／沙盤／青瓷／夜戰，`html[data-kb-theme]` 覆寫 `:root` 色票，欄首與格子底色綁狀態）與主題切換鈕，html_common.THEME_SCRIPT 為頁面唯一 JS（localStorage 持久、伺服器零狀態）／board_routes.py（APIRouter：`/` 看板、`/archive`、`/handoff` 全文頁（`k` 不命中與 `f` 不合法皆 404），看板以 `MAILBOX_ONLY_SCRIPTS` 呼叫 scan_kunsu 跳過 scan-replies.sh；不匯入 main）／registry.py（load_registry 與 registry 路徑、角色輔助，供兩路由模組共用）／main.py（`/overview` 原彙整頁與 include_router；原彙整頁含頁首快速導覽：每軍師一行目錄名連結跳至分組與子專案卡片，錨點 `nav-<軍師>--<子專案>-<雜湊>` 掛 `<details>` 內容區使收合分組自動展開）
    tests/             → pytest（回覆首句摘錄測試自 test_subrepo_status.py 拆至 test_subrepo_status_reply_excerpt.py）
scripts/kc.fish        → kunsu claude 啟動函式（fish autoload；依 registry 自動以命名慣例 `-n` 啟動，`--slot <後綴>` 產生 `<慣例名>.<後綴>` 區分同資料夾多 session，部署至 ~/.config/fish/functions/）
scripts/consistency-check.sh → 跨檔案一致性機械檢查（版號鏈、值域副本、定型文字實跑比對、install 覆蓋、分類詞對映、live 軍師 WARN 級抽查）
install.sh             → 部署至 ~/.claude/skills/ 與 ~/.agents/skills/（Codex，偵測 ~/.codex/ 才啟用；預設 copy 並寫 .kunsu-origin 標記、--link 開發模式、--adopt 採納舊版無標記部署；pre-flight 對非 kunsu 產物整批中止）
```

## 文件導航

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md) | 操作教學：端到端工作流程（README 只留門面摘要） |
| [docs/playbooks/dashboard.md](docs/playbooks/dashboard.md) | 操作教學：軍師沙盤安裝與頁面導覽 |
| [docs/adr/](docs/adr/) | ADR 001–020；status 以各檔 frontmatter 為準（現僅 016 為 proposed，其餘 accepted） |

## 開發狀態

### 已完成
- 已完成條目（2026-07-06 起的功能落地紀錄）已遷至 [docs/history/development-log.md](docs/history/development-log.md)；每條含來源回饋、決策取捨、審查與 dogfooding 結果，規劃前既有盤點請以該檔與 `docs/solutions/` 為起點。
- 新完成的工作一律追加至該檔，本區只保留此指標。

### 尚未實作／後續評估
- ADR 008 open questions 留待用量評估——歸檔 `status` 值域升級（現為單一 `archived`）、「軍師已讀」輕量標記、上報量成長後的整理慣例。
- applications 的 HOME dataview 補齊、add-project reports 遷移不含 HOME dataview 附加（已知落差，見實作計畫 Scope Boundaries）。
- busy session 收訊排隊時機（派發即推播推斷二）留待實際使用觀察。
- `/handoff` 升版全面改查註冊表（reply 的 kunsu 語境分支已於 v0.3.0 實作查表定位軍師；其餘子指令未查表，維持獨立延後決策，ADR 002 Decision 6）。
- 角色改名的追溯修復工具化（ADR 002 Deferred／[ADR 007](docs/adr/2026-07-08-adr-candidate-007-role-code-description-separation.md) Open Questions；代碼穩定＋Decision 7 唯一性可減少非必要改名，但自動批次修復仍缺，現行為 add-project 警告掃描）。
- add-project 內建「整句 `roles` → 代碼」自動遷移偵測（ADR 007 Open Questions；本次已手動遷 ivm 三筆＋ebook-store-nginx，工具內建供其他既有軍師升級待評估）。
- 角色說明欄留空時關聯專案表的呈現規格（ADR 007 Open Questions；顯示「無說明」佔位 vs 留空欄，待範本落地時定）。
- 跨 repo solutions 檢索外環（全域 CLAUDE.md 慣例薄段＋ce-learnings-researcher 間接觸及）——等跨 repo 檢索實痛出現再做，落點建議全域 CLAUDE.md 直加（2026-07-24 計畫 Scope Boundaries）。
- 沙盤與 SessionStart hook 對 `HISTORY_WARN:` 的顯示（現僅 `/kunsu-inbox` CLI 呈現；`kunsu_scan.py` 對未知前綴靜默略過，無誤動作風險；`MISDECLARED_ARCHIVE_ADD` 的一次性警示可能被 hook／沙盤消耗——警示以統計檔為準，ADR 018 威脅模型明文）。
- git add 守門的誤擋率觀察期（ADR 017 開放問題 3）：以統計檔 `guard_denies`／`GUARD_DENY` 事件累積數據，據以定版或撤除。
- ADR 018 開放問題觀察期：以統計檔 `MISDECLARED_ARCHIVE_ADD` 事件（僅計上線後、經人工核對排除誤報——活習慣複合訊息經兩 live 軍師全歷史回放實測約 9.6% 誤報，detail 帶完整訊息供辨識；不含 2026-08-31 已知一次再犯）累積數據——出現真再犯才啟動「ADR 017 擴 `git commit` 守門」的修訂討論，零再犯不跨「提醒→阻止」線。
- 申請歸檔腳本化——延後至申請量成長或出現實證事故（2026-08-31 計畫 Scope Boundaries）。
- 掃描統計檔的並發防護（2026-08-31 code review 發現）：多寫入端（scan／沙盤／hook／guard）無鎖且共用固定同名 .tmp，併寫可致半截 JSON 靜默重建、基線歸零且不記事件——候選修法 mkstemp＋flock＋重建時記 STATS_RESET 事件；advisory 體系實害低，另案評估。
- `HISTORY_WARN` 一次性與 tripwire 同輪的呈現降級（2026-08-31 code review 發現）：同輪出現時 4b-3「立即停止」使警示被略過且基線照樣前進、警示不再現，僅剩統計檔可查（ADR 018 已明文「以統計檔為準」）；候選修法為未消費 warns 時基線不前進或 pending 重報，與沙盤／hook 顯示項合場評估。
- 歸檔腳本與統計 IO 的複製體收斂（2026-08-31 code review cleanup 級發現；2026-09-01 archive-todo.sh 成為第三份同構複製體，債加深）：archive-report.sh、archive-handoff.sh 與 archive-todo.sh 約 200 行同構（含 frontmatter python heredoc、專案根定位、resolve_arg），pretooluse_git_guard.py 的 `_log_deny` 重抄 scan-replies.sh 統計寫入且漏 stale 自清——契約再修訂時單側改動會靜默漂移；候選修法為抽參數化共用入口與 `scan_stats.py`，屬重構級另案評估。
- 產檔查重的觀察項（2026-09-01）：時間窗天數／筆數上限現為腳本頂部常數（14 天／8 筆），依實際使用噪訊比再調；上報查重（new-report.sh）與 reply 側維持不查重的界線照舊。

### 相關資產（唯讀參考）

| 資產 | 路徑 | 用途 |
|------|------|------|
| ebook 專案群規劃中心 | （本機私有路徑，略） | 範本母本；其 `docs/solutions/` 有兩篇模式沉澱文件 |
| 全域 /init-obsidian-vault skill | `~/.claude/skills/init-obsidian-vault` | scaffold 的 Obsidian vault 步驟直接呼叫（軟依賴，未安裝時略過） |
| ce-team（先前嘗試） | （本機私有路徑，略） | 失敗教訓來源，不沿用其程式碼 |

## 版本控制

本目錄為獨立 git repo。不主動 commit，除非使用者明確要求。

里程碑以 **git tag** 標記（annotated tag，repo 層級 semver，自 v1.0.0 起）——與各 skill 的 SKILL.md frontmatter 版號**互相獨立**：skill 版號隨個別 skill 演進照舊記錄於 frontmatter 與 commit 訊息，tag 則標記整個工具組的發布里程碑；打 tag 與 push 均由使用者明確要求時執行。
