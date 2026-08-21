# kunsu

**kunsu**（軍師，台語 Tâi-lô *kun-su*，"the strategist"）——運籌帷幄而不上陣。為多 repo AI 協作建立「軍師」的 scaffolding 工具組：以純 skill＋markdown 範本，為 [Claude Code](https://claude.com/claude-code) 快速建立唯讀的軍師 repo（規劃一切、不執行任何實作），並以全域反向註冊表自動化跨 session 傳令（軍師沙盤為唯一例外，詳見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)）。

## 緣起

因為自己接手了很多案子都有前後端+客戶端的架構，雖然可以交給 AI 做，但總會遇到「這個問題要前後端+客戶端一起修改，但 AI session 跨 repo 很容易會出現幻覺」的問題，所以想要做一個「讓其中一個 session 主要負責規劃但不執行，其它 project 各自開 AI session 負責執行但不規劃」的工具，加上直到 2026/07/07 都可以用訂閱制跑 Claude Fable 5，所以跟 Fable 5 發想討論後寫了這個工具，期望是未來能有效率的使用 AI agent。

## 這是什麼

> **命名故事**：kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；`/handoff` 是軍師與各營共用的公文格式。

當一個功能橫跨多個 git repo（例如後台 API、Android App、前端網站各自獨立），單一 AI session 難以同時掌握全局。**軍師**是一個獨立的第三方 repo——多 repo 協作的規劃協調中心，只放 markdown 文件：它對所有子專案唯讀、產出跨專案的定案規劃，並以「交接文件（handoff）＋回覆信箱（reply inbox）」與各營的 session 往返協作。

這套模式已在三個真實專案群跑完多輪完整功能週期。本工具組把它變成七個可安裝的 skill、一個選用的本機沙盤頁面，以及一組選用的知悉層自動化配件（見下方「知悉層自動化」）：

| 交付物 | 用途 |
|--------|------|
| `/kunsu-init` | 訪談式 scaffolding 建軍師（CLAUDE.md 五條不變量＋三信箱協議、規劃前既有盤點與副官慣例、Obsidian vault、git、註冊表登記）；含 `add-project`（申請審核制登記）與 `remove-project`（整筆移除登記）子指令 |
| `/kunsu-apply` | 子專案端投遞「申請加入軍師」到申請信箱，路徑與技術棧自動偵測；正式登記留給軍師端審核 |
| `/kunsu-inbox` | 跨 session 傳令：子專案列出待接手交接，軍師回報新回覆／新申請／新上報並跑 tripwire 核對，回報附收尾與分流提示（行動項落 todo、答案回填） |
| `/kunsu-report` | 子專案端投遞「主動上報」到上報信箱；單向情報傳遞，不設軍師回覆義務 |
| `/kunsu-list` | 唯讀列出全域註冊表全部登記，含 stale 偵測與當前位置標記 |
| `/handoff` | 通用交接原語：`add`（斷言層級紀律——引用中介文件標「依 X 記載」、據以實作的斷言落原始碼並留查證痕跡；引用以完整檔名為權威識別；更正交接——已定案交接有誤時發更正交接並在原本體 frontmatter 補 `corrected_by` 指標）／`reply`（`verify:` 驗收方式、暫離回報、矛盾回報——發現交接與自身參照物不符時即使不影響實作也明列）／`list`／`done`（逐項驗收、沉澱訊號、反向路由、來源 todo 收尾與殘項清點、斷言自查等歸檔前查核）。單 repo 專案也能獨立使用；kunsu 語境下 `add`／`reply` 內建派發即推播／回覆即推播（[ADR 015](docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md)）；手動呼叫產檔腳本時 stderr 指路行提示回讀對應指引 |
| `/todo` | CE 副作用技術債清單：一檔一項落在 `docs/todos/`，`add`／`list`／`done`（歸檔前先清點檔內未完成殘項）／`rm` |
| 軍師沙盤 | 本機網頁一頁彙整所有軍師與子專案的訊息狀態與待辦技術債（非 skill，見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)） |
| SessionStart hook | session 啟動（含 `/clear`）自動攤開 kunsu 信箱摘要；toolkit 升版後另提示一行「handoff skill 已更新至 vX」使長駐 session 得知指引有變。未登記 repo 靜默、fail-open 不阻斷 session（隨 `/kunsu-inbox` 部署，掛載後生效，見 [ADR 014](docs/adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md)） |
| `kc` 啟動函式 | fish 函式：依註冊表以 kunsu session 命名慣例自動 `claude -n` 啟動，使推播匹配走精確比對；`--slot <後綴>` 區分同資料夾多 session（`scripts/kc.fish`） |

核心設計（詳見 `docs/adr/`）：

- **純 skill＋範本，零編譯依賴**：交付物只有 markdown 與少量 shell 膠水腳本。
- **絕不注入子專案**：子 repo 完全不知道軍師存在；所有機器路徑的常設登記只存在於軍師 CLAUDE.md 的關聯專案表與全域註冊表 `~/.claude/kunsu-registry.json` 兩處。
- **例外授權三信箱**：子專案 session 對軍師 repo 的寫入僅限三個信箱各新增新檔案：回覆信箱（`docs/handoffs/replies/`）、申請信箱（`docs/applications/`）與上報信箱（`docs/reports/`）；tripwire 核對守住這條邊界。
- **上報是情報，不是委派**：`/kunsu-report` 讓子專案主動告知軍師，但不設回覆義務，與 handoff／reply 的雙向協作明確區分。
- **傳令自動化、審核閘門不動**：`/kunsu-inbox`、SessionStart hook 與雙向推播一律只告知不開工；推播為派發／回覆事件當下的一次性訊息，非輪詢、非常駐服務；方案核准與驗收照舊由使用者把關（ADR 014、015）。
- **內文不可變、生命週期 metadata 可維護**：交接本體是定案快照、內文永不回頭修改；frontmatter 生命週期欄位（`status`、`corrected_by`）由發起方維護——勘誤以更正交接傳遞、原本體留指標可尋，引用以檔名為權威識別、歸檔造成的路徑失效不構成錯誤（[ADR 016](docs/adr/2026-08-14-adr-candidate-016-lifecycle-metadata-boundary.md)）。
- **帶理由的規範，不做枷鎖**：查核與紀律以帶理由的指引掛在 session 必經路徑，不強制儀式；軍師可派副官（subagent）分擔原始碼查證與大量彙整的原文提取（原文回傳、判斷不外包），為能力提示非義務。手動執行等效步驟不豁免查核——範本指路牌、腳本 stderr 指路行與 hook 版號提示三路確保指引送達手動執行者。

## 安裝

需求：Claude Code、macOS 或類 Unix 環境、`python3`（registry 腳本使用，可經 Homebrew 或 Xcode Command Line Tools 取得）。

```bash
git clone <this-repo>
cd kunsu
./install.sh          # 複製部署至 ~/.claude/skills/
./install.sh --link   # 開發者模式：symlink 部署，改原始碼即時生效（repo 搬家後需重跑）
```

新開 Claude Code session 即可使用 `/handoff`、`/todo`、`/kunsu-init`、`/kunsu-inbox`、`/kunsu-apply`、`/kunsu-report` 與 `/kunsu-list`。

選用配件（皆為機器層級設定，解除即完全停用）：

- **SessionStart hook**：已隨 `/kunsu-inbox` 一併部署，於 `~/.claude/settings.json` 掛載後生效——掛載範例與解除方式見 `skills/kunsu-inbox/SKILL.md` 的「SessionStart hook」節。
- **`kc` 啟動函式**（fish shell 限定）：`cp scripts/kc.fish ~/.config/fish/functions/`——之後以 `kc` 取代 `claude` 啟動，依註冊表自動命名 session；未登記目錄、自帶 `-n`／`--name` 與 `--resume` 一律透傳、行為同 `claude`。同一資料夾要開多個 session 分頭處理不同工作時，加 `kc --slot <後綴>`（後綴限英數、`-`、`_`）取得 `<慣例名>.<後綴>`（如 `ebook-android.auth`），讓 `/park`／`/unpark` 各持一份停車格（slot 取 session 名稱）。

> 外部軟依賴：`/kunsu-init` 的 Obsidian vault 步驟會呼叫全域 `/init-obsidian-vault` skill，未安裝時自動略過；軍師的「規劃前既有盤點」使用 `/kb`（zoekt 本機索引），未安裝時降級為手動查閱。兩者缺席都不影響其餘功能。交接慣例所需的 `/handoff` 已內建（見 ADR 003）。

## 快速開始

1. **建立軍師**：在任意工作目錄對 Claude 說「幫我建一個軍師」（或 `/kunsu-init`），訪談時給齊軍師名稱、目標路徑與子專案清單，當下即完成登記。
2. **發交接**：軍師 session 規劃拍板後以 `/handoff` 對各相關子專案產交接——派發完成當下自動推播通知目標子專案的長駐 session；子專案 session 也可按 `/clear`（hook 攤開信箱）或執行 `/kunsu-inbox` 看到待接手清單。完成後口語「回覆軍師」回報（可標注 `verify:` 驗收方式），回覆投遞當下同樣自動推播通知軍師 session。
3. **收件與收尾**：軍師 session 收到回覆通知（或 `/clear`／`/kunsu-inbox`）後，彙整確認並以 `/handoff done` 逐項驗收、歸檔收尾。

完整教學（前提、申請審核與移除、主動上報、暫離回報、技術債管理、tripwire 說明）見 **[docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md)**。

## 軍師沙盤（選用）

獨立的本機 FastAPI 服務，一頁彙整所有軍師與子專案的未接手／部分完成／已回覆待確認交接、三信箱新訊息與待辦技術債；「已回覆待確認」依驗收方式子分組排序，一眼可辨哪幾筆現在就能收尾。重新整理頁面才掃描、無背景常駐、純手動啟停。安裝啟動與頁面導覽見 **[docs/playbooks/dashboard.md](docs/playbooks/dashboard.md)**。

## 知悉層自動化（選用）

把「發現有信」自動化、把「決定接不接」留給人（[ADR 014](docs/adr/2026-08-13-adr-candidate-014-sessionstart-hook-activation.md)、[ADR 015](docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md)；需求脈絡見 [docs/brainstorms/2026-08-12-awareness-automation-requirements.md](docs/brainstorms/2026-08-12-awareness-automation-requirements.md)）：

- **SessionStart hook**：session 啟動（含 `/clear`）時以確定性腳本掃描信箱、把摘要注入開場 context——長駐視窗按 `/clear` 即攤開待接手清單。零 token、未登記 repo 靜默、fail-open 絕不阻斷 session 啟動。
- **派發即推播／回覆即推播**：軍師派發完成、子專案回覆投遞（含暫離回報）的當下，向對方的已開啟長駐 session 發送一次性告知訊息——事件驅動、零輪詢、零常駐服務，訊息自帶「僅回顯、勿開工」收方指令，子專案 repo 零注入。
- **session 命名慣例**：子專案 `<軍師目錄名>-<角色代碼>`（如 `ebook-android`）、軍師 `<軍師目錄名>-kunsu`，以及兩者後接 `.` 與後綴的 slot 變體（如 `ebook-android.auth`，`kc --slot` 產生）——以 `/rename` 一次設定（持久化）或以 `kc` 啟動函式自動帶入，使推播匹配走精確比對；無慣例名時退回名稱啟發式，兩層皆唯一命中才發送、寧漏發不誤發（同一慣例名的多個 slot 變體並存即多重命中、一律降級），未推播由 hook 與掃描兜底。

三者皆屬知悉層：接手、開工、查核、done 收尾的決策閘門一律留在使用者手上。

## 專案結構

```
skills/
  handoff/             → 通用交接 skill（SKILL.md＋new-handoff.sh／new-handoff-reply.sh）
  todo/                → 技術債清單 skill（SKILL.md＋new-todo.sh）
  kunsu-init/          → scaffolding skill（SKILL.md＋registry-merge.sh／registry-remove.sh＋範本與種子文件）
  kunsu-inbox/         → 傳令 skill（SKILL.md＋scan-replies.sh／scan-applications.sh／scan-reports.sh／session_hook.py＋tests）
  kunsu-apply/         → 申請投遞 skill（SKILL.md＋new-application.sh）
  kunsu-report/        → 上報投遞 skill（SKILL.md＋new-report.sh）
  kunsu-list/          → 全域登記清單查詢 skill（SKILL.md＋registry-list.sh）
  kunsu-dashboard/     → 軍師沙盤（kunsu dashboard），本機訊息聚合頁面（非 Claude Code skill，見 ADR 010）
scripts/               → kc.fish（session 自動命名啟動函式，`--slot` 後綴）、consistency-check.sh（跨檔案一致性機械檢查）
install.sh             → 部署腳本
docs/                  → 本工具組自身的需求、ADR、實作計畫、操作教學與可重用學習
```

## 文件

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md) | 端到端工作流程完整教學 |
| [docs/playbooks/dashboard.md](docs/playbooks/dashboard.md) | 軍師沙盤安裝與頁面導覽 |
| [docs/adr/](docs/adr/) | 架構決策紀錄（為什麼是純 skill、為什麼是反向註冊表） |
| [docs/brainstorms/](docs/brainstorms/) | 種子需求與模式背景 |
| [CLAUDE.md](CLAUDE.md) | 開發本工具組時的專案規範 |

## 授權

[MIT](LICENSE)。

`.obsidian/plugins/dataview/` 內附的 [Dataview](https://github.com/blacksmithgu/obsidian-dataview) 外掛為第三方作品（MIT License, © Michael Brenan），一併散布以利 vault 開箱即用。
