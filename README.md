# kunsu

**kunsu**（軍師，台語 Tâi-lô *kun-su*，"the strategist"）——運籌帷幄而不上陣。為多 repo AI 協作建立「軍師」的 scaffolding 工具組：以純 skill＋markdown 範本快速建立唯讀的軍師 repo（規劃一切、不執行任何實作），並以全域反向註冊表自動化跨 session 傳令（軍師沙盤為唯一例外，詳見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)）。同一份 skill 原始碼雙部署至 [Claude Code](https://claude.com/claude-code) 與 [Codex CLI](https://developers.openai.com/codex)，兩者可並存，軍師端與子專案端都可由任一 agent 擔任（[ADR 019](docs/adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md)，目前為 proposed，詳見下方「多 agent 支援」）。

## 緣起

因為自己接手了很多案子都有前後端+客戶端的架構，雖然可以交給 AI 做，但總會遇到「這個問題要前後端+客戶端一起修改，但 AI session 跨 repo 很容易會出現幻覺」的問題，所以想要做一個「讓其中一個 session 主要負責規劃但不執行，其它 project 各自開 AI session 負責執行但不規劃」的工具，加上直到 2026/07/07 都可以用訂閱制跑 Claude Fable 5，所以跟 Fable 5 發想討論後寫了這個工具，期望是未來能有效率的使用 AI agent。

## 這是什麼

> **命名故事**：kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；handoff skill 是軍師與各營共用的公文格式。

當一個功能橫跨多個 git repo（例如後台 API、Android App、前端網站各自獨立），單一 AI session 難以同時掌握全局。**軍師**是一個獨立的第三方 repo——多 repo 協作的規劃協調中心，只放 markdown 文件：它對所有子專案唯讀、產出跨專案的定案規劃，並以「交接文件（handoff）＋回覆信箱（reply inbox）」與各營的 session 往返協作。

這套模式已在三個真實專案群跑完多輪完整功能週期。本工具組把它變成七個可安裝的 skill（Claude Code 與 Codex 共用同一份原始碼）、兩支選用的 hook、一個選用的本機沙盤頁面，以及一組選用的知悉層自動化配件（見下方「知悉層自動化」）：

| Skill（Claude Code `/<name>`、Codex `$<name>`；沙盤與 hook 除外） | 用途 |
|--------|------|
| `kunsu-init` | 訪談式 scaffolding 建軍師（CLAUDE.md 五條不變量＋三信箱協議、規劃前既有盤點與副官慣例、Obsidian vault、git、註冊表登記）；含 `add-project`（申請審核制登記）與 `remove-project`（整筆移除登記）子指令 |
| `kunsu-apply` | 子專案端投遞「申請加入軍師」到申請信箱，路徑與技術棧自動偵測；正式登記留給軍師端審核 |
| `kunsu-inbox` | 跨 session 傳令：子專案列出待接手交接，軍師回報新回覆／新申請／新上報並跑 tripwire 核對，回報附收尾與分流提示（行動項落 todo、答案回填）；另含歷史夾帶偵測（歸檔 commit 夾帶未讀回覆、非歸檔 commit 新增 archive 檔）與掃描統計（`~/.claude/kunsu-scan-stats.json`，供評估「未 commit 即未處理」訊號的脆弱度）、上報歸檔腳本 `archive-report.sh`；兩支 hook 隨本 skill 一併部署 |
| `kunsu-report` | 子專案端投遞「主動上報」到上報信箱；單向情報傳遞，不設軍師回覆義務 |
| `kunsu-list` | 唯讀列出全域註冊表全部登記，含 stale 偵測與當前位置標記 |
| `handoff` | 通用交接原語：`add`（斷言層級紀律——引用中介文件標「依 X 記載」、據以實作的斷言落原始碼並留查證痕跡；引用以完整檔名為權威識別；更正交接——已定案交接有誤時發更正交接並在原本體 frontmatter 補 `corrected_by` 指標）／`reply`（`verify:` 驗收方式、暫離回報、矛盾回報——發現交接與自身參照物不符時即使不影響實作也明列）／`list`／`done`（逐項驗收、沉澱訊號、反向路由、來源 todo 收尾與殘項清點、斷言自查等歸檔前查核；歸檔由 `archive-handoff.sh` 執行——status 更新、本體與回覆成對 `git mv`、僅暫存具體路徑，印出帶宣告範圍 pathspec 的待確認 commit 指令而不自動 commit）。`add` 產檔後印出近期同收件角色的交接候選與 zoekt 關鍵詞命中（advisory 查重）。單 repo 專案也能獨立使用；kunsu 語境下 `add`／`reply` 內建派發即推播／回覆即推播（[ADR 015](docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md)）；手動呼叫產檔腳本時 stderr 指路行提示回讀對應指引 |
| `todo` | CE 副作用技術債清單：一檔一項落在 `docs/todos/`，`add`／`list`／`done`（歸檔前先清點檔內未完成殘項）／`rm`；歸檔由 `archive-todo.sh` 執行，handoff `done` 收尾時一併找出並收尾來源 todo |
| 軍師沙盤 | 本機網頁：看板首頁依「球在誰手上」攤開每個軍師的未收尾交接與信箱新件，另有全文頁、已完成頁與完整彙整頁；可選登入自動啟動（非 skill，見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)、[ADR 020](docs/adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md)） |
| SessionStart hook | session 啟動（含 `/clear`）自動攤開 kunsu 信箱摘要；toolkit 升版後另提示一行「handoff skill 已更新至 vX」使長駐 session 得知指引有變。未登記 repo 靜默、fail-open 不阻斷 session（隨 kunsu-inbox skill 部署，於各 agent 的 hook 設定檔掛載後生效，見 [ADR 014](docs/adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md)） |
| PreToolUse git add 守門 | 在軍師 repo 內攔下 `git add -A`／`.`／涵蓋信箱路徑的整目錄 add，deny 訊息內嵌逐檔列名與歸檔腳本的正確做法；`KUNSU_ADD_GUARD_OFF=1` 前綴單次放行、deny 事件記入掃描統計。這是 kunsu 唯一的行為強制點，判準四要件：機械可判、規則已明文、可逆、零能力限縮（[ADR 017](docs/adr/2026-08-29-adr-candidate-017-pretooluse-git-add-guard.md)） |
| `kc` 啟動函式 | fish 函式：依註冊表以 kunsu session 命名慣例自動 `claude -n` 啟動，使推播匹配走精確比對；`--slot <後綴>` 區分同資料夾多 session（`scripts/kc.fish`；Claude Code 限定，Codex 無 session 命名與推播、不需此函式） |

核心設計（詳見 `docs/adr/`）：

- **純 skill＋範本，零編譯依賴**：交付物只有 markdown 與少量 shell 膠水腳本。
- **絕不注入子專案**：子 repo 完全不知道軍師存在；所有機器路徑的常設登記只存在於軍師 CLAUDE.md 的關聯專案表與全域註冊表 `~/.claude/kunsu-registry.json` 兩處。
- **例外授權三信箱**：子專案 session 對軍師 repo 的寫入僅限三個信箱各新增新檔案：回覆信箱（`docs/handoffs/replies/`）、申請信箱（`docs/applications/`）與上報信箱（`docs/reports/`）；tripwire 核對守住這條邊界。
- **上報是情報，不是委派**：kunsu-report skill 讓子專案主動告知軍師，但不設回覆義務，與 handoff／reply 的雙向協作明確區分。
- **傳令自動化、審核閘門不動**：kunsu-inbox skill、SessionStart hook 與雙向推播一律只告知不開工；推播為派發／回覆事件當下的一次性訊息，非輪詢、非常駐服務；方案核准與驗收照舊由使用者把關（ADR 014、015）。
- **內文不可變、生命週期 metadata 可維護**：交接本體是定案快照、內文永不回頭修改；frontmatter 生命週期欄位（`status`、`corrected_by`）由發起方維護——勘誤以更正交接傳遞、原本體留指標可尋，引用以檔名為權威識別、歸檔造成的路徑失效不構成錯誤（[ADR 016](docs/adr/2026-08-14-adr-candidate-016-lifecycle-metadata-boundary.md)）。
- **帶理由的規範，不做枷鎖**：查核與紀律以帶理由的指引掛在 session 必經路徑，不強制儀式；軍師可派副官（subagent）分擔原始碼查證與大量彙整的原文提取（原文回傳、判斷不外包），為能力提示非義務。手動執行等效步驟不豁免查核——範本指路牌、腳本 stderr 指路行與 hook 版號提示三路確保指引送達手動執行者。
- **會飄移的紀律改用計算載體**：live 軍師的事故調查證實文件層規範只在 skill 被呼叫時生效、熟練 session 手動繞道時靜默失效，而產檔腳本在手動路徑上從未失效。因此容易出錯的 git 編排交給腳本計算：三支歸檔腳本印出帶兩形 pathspec 的定型 commit 指令、不自動 commit，確認 commit 的契約自「提交 index」改為「提交宣告範圍」（[ADR 018](docs/adr/2026-08-31-adr-candidate-018-commit-declared-scope-contract.md)）；唯一跨過「提醒→阻止」線的是 git add 守門（[ADR 017](docs/adr/2026-08-29-adr-candidate-017-pretooluse-git-add-guard.md)），並以掃描統計累積資料決定是否再擴。
- **agent 中立，adapter 只在部署目標與字面**：skill 內文只用能力名（阻塞式確認、跨 session 推播、skill 目錄、呼叫形、hook 設定檔、子 agent），各 SKILL.md 首節一張逐字一致的「Agent 對應表」交代 Claude Code 與 Codex 的實際工具；新增 agent 只改表、不改內文，不寫任何 agent 專屬薄殼；未列入表的 agent 一律採 Codex 欄的保守行為（[ADR 019](docs/adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md)）。

## 安裝

需求：Claude Code 或 Codex CLI（兩者可並存，同一份原始碼雙部署，見 ADR 019）、macOS 或類 Unix 環境、`python3`（registry 腳本與 hook 使用，可經 Homebrew 或 Xcode Command Line Tools 取得）。

```bash
git clone <this-repo>
cd kunsu
./install.sh          # 複製部署至 ~/.claude/skills/；偵測到 ~/.codex/ 時一併部署至 ~/.agents/skills/（Codex）
./install.sh --link   # 開發者模式：目錄 symlink 部署，改原始碼即時生效（repo 搬家後需重跑）
./install.sh --adopt  # 既有舊版 copy 部署（無 .kunsu-origin 標記）首次升級時採納覆寫：列出候選、互動確認後才覆寫（非互動環境須另設 KUNSU_INSTALL_YES=1）
```

覆寫保護：目的路徑已存在時，只有指向本 repo 的 symlink（含 repo 搬家後的懸空 symlink）或帶 `.kunsu-origin` 標記的目錄會被覆寫；其他同名目錄（例如第三方也叫 `todo` 的 skill）一律整批中止、零目錄改動。

新開 agent session 即可使用 handoff、todo、kunsu-init、kunsu-inbox、kunsu-apply、kunsu-report 與 kunsu-list 七個 skill——Claude Code 以 `/<name>` 呼叫，Codex 以 `$<name>` 呼叫或依 description 自動選用；各 SKILL.md 首節「Agent 對應表」列出阻塞式確認、跨 session 推播、skill 目錄等能力在各 agent 的對應。

選用配件（皆為機器層級設定，解除即完全停用）：

- **SessionStart hook 與 PreToolUse git add 守門**：已隨 kunsu-inbox skill 一併部署，於各 agent 的 hook 設定檔掛載後生效（Claude Code `~/.claude/settings.json`；Codex `~/.codex/hooks.json`，掛後須於 TUI 信任）——掛載範例、Codex 的 `project_doc_*` config 設定與解除方式見 `skills/kunsu-inbox/SKILL.md` 的「SessionStart hook」「PreToolUse git add 守門」與「Codex config 設定」三節。
- **`kc` 啟動函式**（fish shell 限定）：`cp scripts/kc.fish ~/.config/fish/functions/`——之後以 `kc` 取代 `claude` 啟動，依註冊表自動命名 session；未登記目錄、自帶 `-n`／`--name` 與 `--resume` 一律透傳、行為同 `claude`。同一資料夾要開多個 session 分頭做不同工作時，改用 `kc --slot <後綴>` 啟動，session 名會變成 `<慣例名>.<後綴>`（例如 `ebook-android.auth`；後綴限英數、`-`、`_`），`/park`／`/unpark` 就能各持一份停車格。

> 外部軟依賴：kunsu-init 的 Obsidian vault 步驟會呼叫全域 init-obsidian-vault skill，未安裝時自動略過；軍師的「規劃前既有盤點」使用 kb skill（zoekt 本機索引），未安裝時降級為手動查閱。兩者缺席都不影響其餘功能。交接慣例所需的 handoff skill 已內建（見 ADR 003）。以下以 skill 名指稱指令；呼叫形依 agent：Claude Code `/<name>`、Codex `$<name>`（或依 description 自動選用），細節見各 SKILL.md 首節「Agent 對應表」。

## 快速開始

1. **建立軍師**：在任意工作目錄對 agent 說「幫我建一個軍師」（或執行 kunsu-init skill：Claude Code `/kunsu-init`、Codex `$kunsu-init`），訪談時給齊軍師名稱、目標路徑與子專案清單，當下即完成登記。
2. **發交接**：軍師 session 規劃拍板後以 handoff skill 對各相關子專案產交接——Claude Code 派發完成當下自動推播通知目標子專案的長駐 session（Codex 無跨 session 推播，整步跳過）；子專案 session 也可開新對話（Claude Code `/clear`，hook 攤開信箱）或執行 kunsu-inbox skill 看到待接手清單。完成後口語「回覆軍師」回報（可標注 `verify:` 驗收方式），回覆投遞當下同樣自動推播通知軍師 session（Claude Code 側）。
3. **收件與收尾**：軍師 session 收到回覆通知（或開新對話由 hook 攤開信箱、執行 kunsu-inbox skill）後，彙整確認並以 handoff skill 的 done 子指令逐項驗收、歸檔收尾；確認 commit 在 Claude Code 走阻塞式提問、在 Codex 走「印出定型指令後結束回合、下一回合同意才執行」。

完整教學（前提、申請審核與移除、主動上報、暫離回報、技術債管理、tripwire 說明）見 **[docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md)**。

## 軍師沙盤（選用）

獨立的本機 FastAPI 服務，把所有軍師與子專案的訊息狀態攤在同一個瀏覽器分頁，取代逐一切換 CLI 視窗手動執行 `kunsu-inbox`。四個頁面：

- **看板（首頁 `/`）**：每個軍師一張，縱向泳道是持球者（軍師置頂，其下為各子專案角色），橫向依等待中／待辦／進行中／待驗收分欄。尚無回覆的交接掛在收件角色底下（依賴未滿足者進等待中並標所等的前置交接）、`partial` 進收件角色進行中、`blocked` 進軍師進行中並標 ⛔ 卡關、`submitted` 進軍師待驗收並標驗收方式，未 commit 的新申請／新上報進軍師待辦。卡片顯示標題、驗收方式、停留天數、線別與最新回覆摘錄；有異常（軍師路徑失聯、tripwire、已標 done 未歸檔、回覆自標 done 等）時頂端出現一行警示並連到完整彙整頁，異常件不上看板。
- **全文頁（`/handoff`）**：卡片與已完成列表的「全文」連結開啟獨立頁面，frontmatter 鍵值表＋交接本體的 Markdown 伺服器端渲染（markdown-it-py，缺席時降級純文字），另列依賴區塊與同串回覆舊→新。路徑參數只接受四個信箱目錄下的單層 `.md`，HTML 一律轉義。
- **已完成（`/archive`）**：依日期由新到舊列出已歸檔交接，每筆標題即全文頁連結。
- **完整彙整頁（`/overview`）**：原首頁，保留軍師分組與子專案巢狀明細、三信箱新訊息、依賴圖、交接三分類（未接手／部分完成／已回覆待確認依 `verify:` 子分組）與待辦技術債卡片。

頁首有四組配色主題（墨與朱、沙盤、青瓷、夜戰）可點選切換，選擇存在瀏覽器 localStorage，伺服器不持有狀態。設計邊界不變：唯讀、重新整理頁面才掃描（看板不跑 `scan-replies.sh`，避免推進歷史夾帶偵測基線）、無背景輪詢；啟停由使用者掌握——前景手動啟動，或親手安裝只含 `RunAtLoad` 的 macOS LaunchAgent 於登入時啟動一次（範本與安裝步驟見 SKILL.md，[ADR 020](docs/adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md)）。安裝啟動與頁面導覽見 **[docs/playbooks/dashboard.md](docs/playbooks/dashboard.md)**。

## 知悉層自動化（選用）

把「發現有信」自動化、把「決定接不接」留給人（[ADR 014](docs/adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md)、[ADR 015](docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md)；需求脈絡見 [docs/brainstorms/2026-08-12-awareness-automation-requirements.md](docs/brainstorms/2026-08-12-awareness-automation-requirements.md)）：

- **SessionStart hook**：session 啟動（含 `/clear`）時以確定性腳本掃描信箱、把摘要注入開場 context——長駐視窗按 `/clear` 即攤開待接手清單。零 token、未登記 repo 靜默、fail-open 絕不阻斷 session 啟動。Claude Code 與 Codex 皆可掛載（Codex 掛於 `~/.codex/hooks.json`、須於 TUI 信任）。
- **派發即推播／回覆即推播**：軍師派發完成、子專案回覆投遞（含暫離回報）的當下，向對方的已開啟長駐 session 發送一次性告知訊息——事件驅動、零輪詢、零常駐服務，訊息自帶「僅回顯、勿開工」收方指令，子專案 repo 零注入。Claude Code 限定：Codex 沒有跨 session 傳訊的對應物，這一步整個跳過，由 SessionStart hook 與掃描兜底。
- **session 命名慣例**：子專案 `<軍師目錄名>-<角色代碼>`（如 `ebook-android`）、軍師 `<軍師目錄名>-kunsu`，以及兩者再接上 `.` 與後綴的 slot 變體（如 `ebook-android.auth`，`kc --slot` 產生）——以 Claude Code 的 `/rename` 一次設定（持久化）或以 `kc` 啟動函式自動帶入，使推播匹配走精確比對；無慣例名時退回名稱啟發式，兩層皆唯一命中才發送、寧漏發不誤發（同一慣例名的多個 slot 變體並存即多重命中、一律降級），未推播由 hook 與掃描兜底。

三者皆屬知悉層：接手、開工、查核、done 收尾的決策閘門一律留在使用者手上。

## 多 agent 支援（Codex）

同一份 skill 原始碼、同一套文件協議，`install.sh` 偵測到 `~/.codex/` 就一併部署至 Codex 的 skill 目錄 `~/.agents/skills/`（Codex 官方 user 位置；舊的 `~/.codex/skills` 已 deprecated，不再使用）。軍師端與子專案端都可由任一 agent 擔任，兩邊經 handoff 文件溝通，不需要同一種 agent。差異只在各 agent 提供的工具，整理成每份 SKILL.md 首節的「Agent 對應表」（七份逐字一致，由 `scripts/consistency-check.sh` 比對），摘要如下：

| 能力 | Claude Code | Codex |
|------|-------------|-------|
| skill 呼叫形 | `/<name>` 斜線指令 | `$<name>` 顯式呼叫，或依 description 自動選用 |
| 阻塞式確認（確認 commit 等） | AskUserQuestion 提問後執行 | 預設無阻塞式工具：印出定型指令與狀態宣告後結束回合，下一回合收到明確同意文字才執行；同意只對緊接的下一回合有效 |
| 跨 session 推播 | ListAgents＋SendMessage | 無對應物，整步跳過 |
| hook 設定檔 | `~/.claude/settings.json` | `~/.codex/hooks.json`，改動後須於 TUI 重新信任 |
| 子 agent（副官） | Agent 工具 | `spawn_agent` |

使用 Codex 時另有三件機器層級設定，掛載步驟與 toml 片段見 `skills/kunsu-inbox/SKILL.md` 的「Codex config 設定」節：

- **軍師憲章的讀取**：kunsu-init 建出的軍師 repo 內建 `AGENTS.md → CLAUDE.md` symlink，Codex 讀到的是同一份憲章；既有軍師升級時補一個 symlink 即可。
- **`project_doc_max_bytes = 65536`**：Codex 對專案指引檔預設只讀 32 KiB 合計預算、超出部分靜默截尾，實際運作中的軍師 CLAUDE.md 已超過此值，不設定會讓憲章尾段（含副官慣例與工作流程）默默消失；`consistency-check.sh` 對接近上限的軍師發 WARN。
- **hook 信任**：Codex 的 hook 掛進 `~/.codex/hooks.json` 後要在 TUI 信任一次；未信任或信任索引漂移時 hook 靜默略過而非報錯，`consistency-check.sh` 的 N 項會檢查此狀態。

沙盒方面，Codex 預設的 workspace-write 模式下 `.git/` 為唯讀，軍師 session 執行 `done` 歸檔的 git 寫入會觸發核准提示——這是 kunsu 邊界之外的一道附帶關卡，把 `.git` 列入 `writable_roots` 會失去它。確認 commit 在 Codex 側改走文字回合，是規範層而非結構關卡：同意缺席時事後無法從產物觀測，實害邊界由「絕不 push」界定為本地可逆。

驗證狀態：`scripts/codex-pilot.sh`（用法與手動核對清單見 [docs/playbooks/codex-pilot.md](docs/playbooks/codex-pilot.md)）以 `codex exec` 非互動跑完接手方鏈與軍師端鏈共八個驗收例，機制面全部成立過，但 Codex 免費方案額度於第五輪用盡、尚無單輪全綠，ADR 019 因此仍為 proposed，正式生效綁定試點單輪通過。已知邊界：done 收尾的六道查核、斷言層級紀律等多步驟流程在 Codex 上的保真度尚未量測；軍師沙盤讀的是檔案、與 agent 無關，`kc` 啟動函式則為 Claude Code 側配件。

## 專案結構

```
skills/
  handoff/             → 通用交接 skill（SKILL.md＋new-handoff.sh／new-handoff-reply.sh／archive-handoff.sh）
  todo/                → 技術債清單 skill（SKILL.md＋new-todo.sh／archive-todo.sh）
  kunsu-init/          → scaffolding skill（SKILL.md＋registry-merge.sh／registry-remove.sh＋範本與種子文件）
  kunsu-inbox/         → 傳令 skill（SKILL.md＋scan-replies.sh／scan-applications.sh／scan-reports.sh／archive-report.sh＋session_hook.py／pretooluse_git_guard.py 兩支 hook＋tests）
  kunsu-apply/         → 申請投遞 skill（SKILL.md＋new-application.sh）
  kunsu-report/        → 上報投遞 skill（SKILL.md＋new-report.sh）
  kunsu-list/          → 全域登記清單查詢 skill（SKILL.md＋registry-list.sh）
  kunsu-dashboard/     → 軍師沙盤（kunsu dashboard）：看板／全文頁／已完成頁／完整彙整頁的本機 FastAPI 服務，含 launchd/ 登入自啟 plist 範本（非可觸發的 skill，frontmatter 以兩 agent 原生旗標停用選用，見 ADR 010／019／020）
scripts/               → kc.fish（session 自動命名啟動函式，`--slot` 後綴）、consistency-check.sh（跨檔案一致性機械檢查，43 項）、codex-pilot.sh（Codex 雙端試點）
install.sh             → 部署腳本（Claude Code `~/.claude/skills/`；偵測到 `~/.codex/` 時一併部署 Codex `~/.agents/skills/`）
docs/                  → 本工具組自身的需求、ADR、實作計畫、操作教學與可重用學習
```

## 文件

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md) | 端到端工作流程完整教學 |
| [docs/playbooks/dashboard.md](docs/playbooks/dashboard.md) | 軍師沙盤安裝與頁面導覽 |
| [docs/playbooks/codex-pilot.md](docs/playbooks/codex-pilot.md) | Codex 雙端試點腳本用法與手動核對清單 |
| [docs/adr/](docs/adr/) | 架構決策紀錄（為什麼是純 skill、為什麼是反向註冊表、為什麼是同一份原始碼雙部署） |
| [docs/brainstorms/](docs/brainstorms/) | 種子需求與模式背景 |
| [CLAUDE.md](CLAUDE.md) | 開發本工具組時的專案規範 |

## 授權

[MIT](LICENSE)。

`.obsidian/plugins/dataview/` 內附的 [Dataview](https://github.com/blacksmithgu/obsidian-dataview) 外掛為第三方作品（MIT License, © Michael Brenan），一併散布以利 vault 開箱即用。
