# kunsu

**kunsu**（軍師，台語 Tâi-lô *kun-su*，"the strategist"）——運籌帷幄而不上陣。為多 repo AI 協作建立「軍師」的 scaffolding 工具組：以純 skill＋markdown 範本，為 [Claude Code](https://claude.com/claude-code) 快速建立唯讀的軍師 repo（規劃一切、不執行任何實作），並以全域反向註冊表自動化跨 session 傳令（軍師沙盤為唯一例外，詳見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)）。

## 緣起

因為自己接手了很多案子都有前後端+客戶端的架構，雖然可以交給 AI 做，但總會遇到「這個問題要前後端+客戶端一起修改，但 AI session 跨 repo 很容易會出現幻覺」的問題，所以想要做一個「讓其中一個 session 主要負責規劃但不執行，其它 project 各自開 AI session 負責執行但不規劃」的工具，加上直到 2026/07/07 都可以用訂閱制跑 Claude Fable 5，所以跟 Fable 5 發想討論後寫了這個工具，期望是未來能有效率的使用 AI agent。

## 這是什麼

> **命名故事**：kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；`/handoff` 是軍師與各營共用的公文格式。

當一個功能橫跨多個 git repo（例如後台 API、Android App、前端網站各自獨立），單一 AI session 難以同時掌握全局。**軍師**是一個獨立的第三方 repo——多 repo 協作的規劃協調中心，只放 markdown 文件：它對所有子專案唯讀、產出跨專案的定案規劃，並以「交接文件（handoff）＋回覆信箱（reply inbox）」與各營的 session 往返協作。

這套模式已在三個真實專案群跑完多輪完整功能週期。本工具組把它變成七個可安裝的 skill 與一個選用的本機沙盤頁面：

| 交付物 | 用途 |
|--------|------|
| `/kunsu-init` | 訪談式 scaffolding 建軍師（CLAUDE.md 五條不變量＋三信箱協議、Obsidian vault、git、註冊表登記）；含 `add-project`（申請審核制登記）與 `remove-project`（整筆移除登記）子指令 |
| `/kunsu-apply` | 子專案端投遞「申請加入軍師」到申請信箱，路徑與技術棧自動偵測；正式登記留給軍師端審核 |
| `/kunsu-inbox` | 跨 session 傳令：子專案列出待接手交接，軍師回報新回覆／新申請／新上報並跑 tripwire 核對 |
| `/kunsu-report` | 子專案端投遞「主動上報」到上報信箱；單向情報傳遞，不設軍師回覆義務 |
| `/kunsu-list` | 唯讀列出全域註冊表全部登記，含 stale 偵測與當前位置標記 |
| `/handoff` | 通用交接原語：`add`／`reply`（含 `verify:` 驗收方式與暫離回報）／`list`／`done`（逐項驗收查核＋來源 todo 一併收尾）。單 repo 專案也能獨立使用 |
| `/todo` | CE 副作用技術債清單：一檔一項落在 `docs/todos/`，`add`／`list`／`done`／`rm` |
| 軍師沙盤 | 本機網頁一頁彙整所有軍師與子專案的訊息狀態與待辦技術債（非 skill，見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)） |

核心設計（詳見 `docs/adr/`）：

- **純 skill＋範本，零編譯依賴**：交付物只有 markdown 與少量 shell 膠水腳本。
- **絕不注入子專案**：子 repo 完全不知道軍師存在；所有機器路徑的常設登記只存在於軍師 CLAUDE.md 的關聯專案表與全域註冊表 `~/.claude/kunsu-registry.json` 兩處。
- **例外授權三信箱**：子專案 session 對軍師 repo 的寫入僅限三個信箱各新增新檔案：回覆信箱（`docs/handoffs/replies/`）、申請信箱（`docs/applications/`）與上報信箱（`docs/reports/`）；tripwire 核對守住這條邊界。
- **上報是情報，不是委派**：`/kunsu-report` 讓子專案主動告知軍師，但不設回覆義務，與 handoff／reply 的雙向協作明確區分。
- **傳令自動化、審核閘門不動**：`/kunsu-inbox` 只告知不開工、不主動輪詢；方案核准與驗收照舊由使用者把關。

## 安裝

需求：Claude Code、macOS 或類 Unix 環境、`python3`（registry 腳本使用，可經 Homebrew 或 Xcode Command Line Tools 取得）。

```bash
git clone <this-repo>
cd kunsu
./install.sh          # 複製部署至 ~/.claude/skills/
./install.sh --link   # 開發者模式：symlink 部署，改原始碼即時生效（repo 搬家後需重跑）
```

新開 Claude Code session 即可使用 `/handoff`、`/todo`、`/kunsu-init`、`/kunsu-inbox`、`/kunsu-apply`、`/kunsu-report` 與 `/kunsu-list`。

> 外部軟依賴：`/kunsu-init` 的 Obsidian vault 步驟會呼叫全域 `/init-obsidian-vault` skill，未安裝時自動略過；軍師的「規劃前既有盤點」使用 `/kb`（zoekt 本機索引），未安裝時降級為手動查閱。兩者缺席都不影響其餘功能。交接慣例所需的 `/handoff` 已內建（見 ADR 003）。

## 快速開始

1. **建立軍師**：在任意工作目錄對 Claude 說「幫我建一個軍師」（或 `/kunsu-init`），訪談時給齊軍師名稱、目標路徑與子專案清單，當下即完成登記。
2. **發交接**：軍師 session 規劃拍板後以 `/handoff` 對各相關子專案產交接；子專案 session 執行 `/kunsu-inbox` 看到待接手清單，完成後口語「回覆軍師」回報（可標注 `verify:` 驗收方式）。
3. **收件與收尾**：軍師 session 執行 `/kunsu-inbox` 看到新回覆，彙整確認後以 `/handoff done` 逐項驗收並歸檔收尾。

完整教學（前提、申請審核與移除、主動上報、暫離回報、技術債管理、tripwire 說明）見 **[docs/playbooks/end-to-end-workflow.md](docs/playbooks/end-to-end-workflow.md)**。

## 軍師沙盤（選用）

獨立的本機 FastAPI 服務，一頁彙整所有軍師與子專案的未接手／部分完成／已回覆待確認交接、三信箱新訊息與待辦技術債；「已回覆待確認」依驗收方式子分組排序，一眼可辨哪幾筆現在就能收尾。重新整理頁面才掃描、無背景常駐、純手動啟停。安裝啟動與頁面導覽見 **[docs/playbooks/dashboard.md](docs/playbooks/dashboard.md)**。

## 專案結構

```
skills/
  handoff/             → 通用交接 skill（SKILL.md＋new-handoff.sh／new-handoff-reply.sh）
  todo/                → 技術債清單 skill（SKILL.md＋new-todo.sh）
  kunsu-init/          → scaffolding skill（SKILL.md＋registry-merge.sh／registry-remove.sh＋範本與種子文件）
  kunsu-inbox/         → 傳令 skill（SKILL.md＋scan-replies.sh／scan-applications.sh／scan-reports.sh）
  kunsu-apply/         → 申請投遞 skill（SKILL.md＋new-application.sh）
  kunsu-report/        → 上報投遞 skill（SKILL.md＋new-report.sh）
  kunsu-list/          → 全域登記清單查詢 skill（SKILL.md＋registry-list.sh）
  kunsu-dashboard/     → 軍師沙盤（kunsu dashboard），本機訊息聚合頁面（非 Claude Code skill，見 ADR 010）
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
