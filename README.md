# kunsu

**kunsu**（軍師，台語 Tâi-lô *kun-su*，"the strategist"）——運籌帷幄而不上陣。為多 repo AI 協作建立「軍師」的 scaffolding 工具組：以純 skill＋markdown 範本，為 [Claude Code](https://claude.com/claude-code) 快速建立唯讀的軍師 repo（規劃一切、不執行任何實作），並以全域反向註冊表自動化跨 session 傳令（軍師沙盤為唯一例外，詳見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)）。

## 緣起

因為自己接手了很多案子都有前後端+客戶端的架構，雖然可以交給 AI 做，但總會遇到「這個問題要前後端+客戶端一起修改，但 AI session 跨 repo 很容易會出現幻覺」的問題，所以想要做一個「讓其中一個 session 主要負責規劃但不執行，其它 project 各自開 AI session 負責執行但不規劃」的工具，加上直到 2026/07/07 都可以用訂閱制跑 Claude Fable 5，所以跟 Fable 5 發想討論後寫了這個工具，期望是未來能有效率的使用 AI agent。

## WorkFlow

0. 前提：目前只用在 Claude，其它 agent 我還沒有試過。此外預設還會搭配 every.to 出品的 CE 以及 Obsidian 來使用。
1. 首先執行 `/kunsu-init`，依訪談回答軍師名稱與目標路徑，agent 會自己建好軍師資料夾與結構。訪談時就把子專案清單一併給齊的話，當下直接完成登記，可跳過步驟 2。
2. 之後要加入新的子專案時，到子專案資料夾中執行 `/kunsu-apply`，agent 會詢問要把這個子專案申請加入哪個軍師。
	- 申請送出後會是待審狀態，得切回到軍師 session 執行「`/kunsu-init add-project`」逐筆審核，審核通過後才算是正式加入軍師。在那之前 `/kunsu-inbox`、`/kunsu-report` 與沙盤都還不認得這個子專案。
3. 想看專案整體狀態時，先手動啟動軍師沙盤（`cd skills/kunsu-dashboard && ./start.sh`，首次使用要先 `pip install -r requirements.txt`），再打開 `http://127.0.0.1:8000/` 就能看到所有軍師跟子專案的狀態。沙盤不會自動偵測更新，要重新整理頁面才會掃描最新狀態並顯示在畫面上。
4. 接著如果要新增功能或是解決問題，就可以從軍師的 session 直接要求軍師研究並規畫，方向確定之後，軍師會用 `/handoff` 對每個有關聯性的子專案各產生一份交接文件。文件產生完成後會問一次「是否 commit」，記得答應，因為交接檔未 commit 的話，軍師下次 `/kunsu-inbox` 會產生 tripwire 的誤報。
	- 註：tripwire 是絆馬索，在這裡指的是一個避免流程出錯的提示，觸發時可以讓 agent 跟使用者知道目前有意外的狀況需要人工處理排除。
5. 承 4，這時候要自己到子專案打開新 session，然後可以口語要求查看信箱，或是直接輸入 `/kunsu-inbox`，agent 會列出「未接手」、「部分完成」、或是「已回覆待確認」的交接清單與檔案路徑。inbox 的設計是「只告知不開工」，接著讀規格、開工由使用者下令。
6. 子專案完成（或部分完成、卡關）後，口語「回覆軍師」或 `/handoff reply` 建立回覆檔，可用選填欄位 `verify:` 標注驗收方式（需上線測試／馬上可測／需實機測試或自由字串），沙盤會顯示成對應標籤。回覆刻意不 commit——未 commit 正是軍師端的「新回覆」訊號。回到軍師 session 執行 `/kunsu-inbox` 看到新回覆，下令彙整；確認完成後 `/handoff done` 歸檔，這一輪交接才算閉環。
7. 在另一個情境下，如果子專案的 session 發現與手上交接無關的新情報，或是發現有更好的方向，則子專案可以用 `/kunsu-report` 或是口語化的「稟報軍師」來向軍師提案；若其實是手上交接要調整方向，那屬於回覆而不是上報（投錯也沒關係，`/kunsu-report` 偵測到有待回覆的交接會先反問並導回 `/handoff reply`）。回到軍師 session 再執行 `/kunsu-inbox` 看到新上報，軍師看文件跟研究，然後跟使用者討論決定方向之後再重複上面的流程。

## 這是什麼

> **命名故事**：kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；`/handoff` 是軍師與各營共用的公文格式。

當一個功能橫跨多個 git repo（例如後台 API、Android App、前端網站各自獨立），單一 AI session 難以同時掌握全局。**軍師**是一個獨立的第三方 repo——多 repo 協作的規劃協調中心，只放 markdown 文件：它對所有子專案唯讀、產出跨專案的定案規劃，並以「交接文件（handoff）＋回覆信箱（reply inbox）」與各營的 session 往返協作。

這套模式已在真實專案群跑完多個完整功能週期。本工具組把它變成六個可安裝的 skill：

| Skill | 用途 |
|-------|------|
| `/kunsu-init` | 訪談式 scaffolding：一次建好軍師的 CLAUDE.md（含五條不變量、回覆信箱與申請信箱協議）、CONCEPTS.md、docs 結構、Obsidian vault、git repo，並登記全域註冊表。含 `add-project` 子指令：掃描申請信箱逐筆審核（核准當下才正式登記），無申請時退回分題訪談，並內建舊軍師的申請信箱遷移。 |
| `/kunsu-apply` | 子專案端投遞「申請加入軍師」：自動偵測路徑、名稱與技術棧，軍師清單從註冊表點選，只需手填角色描述與環境限制；寫一份申請檔到目標軍師的申請信箱，正式登記留給軍師端審核。 |
| `/kunsu-inbox` | 跨 session 傳令：在子專案 repo 執行，列出「哪些交接文件在等我」；在軍師 repo 執行，回報「收到幾份新回覆、幾份新申請、幾份新上報」並核對寫入範圍（tripwire）。傳令成本從口述長路徑降為打一次指令。 |
| `/kunsu-report` | 子專案端投遞「主動上報」：自動偵測路徑，從註冊表取得已登記軍師與角色代碼，把情報寫入軍師的上報信箱（`docs/reports/`）。上報是情報傳遞，不是委派任務，不承諾軍師回覆；若偵測到其實是待回覆的交接，會先反問並導向 `/handoff reply`。 |
| `/kunsu-list` | 唯讀列出全域註冊表的全部登記：按軍師分組呈現角色代碼與子專案路徑，含 stale entry 偵測與當前所在位置標記。不需 git 身分，任何目錄（含多 repo 父層 workspace）皆可執行。 |
| `/handoff` | 通用交接原語（協議基礎）：在任何專案建立交接文件（`add`）、以回覆信箱模式回報（`reply`）、列出狀態（`list`）、歸檔（`done`）。單 repo 專案也能獨立使用；`/kunsu-inbox` 解析的正是它寫出的檔案格式。 |

核心設計（詳見 `docs/adr/`）：

- **純 skill＋範本，零編譯依賴**——交付物只有 markdown 與少量 shell 膠水腳本。
- **絕不注入子專案**——子 repo 完全不知道軍師存在；所有機器路徑的常設登記只存在於軍師 CLAUDE.md 的關聯專案表與全域註冊表 `~/.claude/kunsu-registry.json` 兩處。
- **例外授權三信箱**——子專案 session 對軍師 repo 的寫入僅限三個信箱各新增新檔案：回覆信箱（`docs/handoffs/replies/`）、申請信箱（`docs/applications/`）與上報信箱（`docs/reports/`）；tripwire 核對守住這條邊界。
- **上報是情報，不是委派**——`/kunsu-report` 讓子專案主動告知軍師，但不設回覆義務，與 handoff／reply 的雙向協作明確區分。
- **傳令自動化、審核閘門不動**——`/kunsu-inbox` 只告知不開工、不主動輪詢；方案核准與驗收照舊由使用者把關。

## 安裝

需求：Claude Code、macOS 或類 Unix 環境、`python3`（registry 腳本使用，可經 Homebrew 或 Xcode Command Line Tools 取得）。

```bash
git clone <this-repo>
cd kunsu
./install.sh          # 複製部署至 ~/.claude/skills/
./install.sh --link   # 開發者模式：symlink 部署，改原始碼即時生效（repo 搬家後需重跑）
```

新開 Claude Code session 即可使用 `/handoff`、`/kunsu-init`、`/kunsu-inbox`、`/kunsu-apply`、`/kunsu-report` 與 `/kunsu-list`。

> 唯一的外部軟依賴：`/kunsu-init` 的 Obsidian vault 步驟會呼叫全域 `/init-obsidian-vault` skill，未安裝時自動略過該步驟，其餘功能不受影響。交接慣例所需的 `/handoff` 已內建（見 ADR 003）。

## 快速開始

1. **建立軍師**——在任意工作目錄對 Claude 說「幫我建一個軍師」（或 `/kunsu-init`），依訪談回答軍師名稱、目標路徑與子專案清單（名稱／絕對路徑／角色），其餘自動完成。
2. **發交接**——在軍師 repo 以 `/handoff` skill 建立交接文件，`to:` 填子專案的角色字串。
3. **子專案接手**——在子專案 repo 的 session 打 `/kunsu-inbox`，看到未接手／部分完成／已回覆待確認清單與回覆路徑，完成後以回覆檔回報（回覆可用選填欄位 `verify:` 標注驗收方式——需上線測試／馬上可測／需實機測試或自由字串）。
4. **軍師收件**——回到軍師 repo 的 session 打 `/kunsu-inbox`，看到「收到 N 份新回覆」，下令彙整。
5. **加入新子專案**——在子專案 repo 的 session 說「申請加入軍師」（`/kunsu-apply`），路徑與技術棧自動偵測、只填角色描述；回到軍師 repo 說「add-project」逐筆審核，核准當下才正式登記，三處角色字串（軍師的關聯專案表、註冊表、handoff `to:`）自動保持一致。也可直接在軍師 repo 說「add-project」走訪談路徑。

延伸操作：子專案有非 handoff 觸發的情報要讓軍師知道，用 `/kunsu-report`「主動上報」；想快速回顧目前有哪些子專案登記在哪個軍師底下，用 `/kunsu-list`。

## 軍師沙盤（kunsu dashboard，選用）

同時開多個軍師／子專案視窗時，`/kunsu-inbox` 得逐一切換視窗手動執行才知道有沒有新訊息，視窗一多容易顧此失彼。`skills/kunsu-dashboard/` 是一個獨立的本機 FastAPI 服務——**軍師沙盤（kunsu dashboard）**，如統帥推演戰局的沙盤，把全域註冊表裡所有軍師與子專案的訊息狀態（未接手／部分完成／已回覆待確認交接、新回覆、新申請、新上報）彙整成一頁總覽：

- **頁首全域總覽列**先給出跨軍師的整體態勢（⚠ 未接手・⛔ 卡關・⚡ 馬上可測・其餘待確認・📨 新訊息，全零時不顯示）。
- 依軍師分組、子專案巢狀顯示在所屬軍師底下；分組收合列帶出子專案待處理計數，有進度或有未接手／異常件的軍師預設展開、其餘折疊，未接手件絕不會藏在收合分組裡。
- 每筆交接／訊息可展開看完整 md 內容與最後修改時間，並依回覆的 `verify` 欄位顯示驗收標籤（需上線測試 🚀／馬上可測 ⚡／需實機測試 📱／自由字串），blocked 回覆另標 ⛔ 卡關，未接手分類以 ⚠ 醒目標題呈現。
- **「已回覆待確認」依驗收方式拆成子分組**：馬上可測 → 需實機測試 → 需上線測試 → 自由字串 → 未標示，愈接近「能以 `/handoff done` 收尾」的排愈前，組內等最久的陳年件排最前，一眼可辨哪幾筆現在就能收尾。

刷新瀏覽器頁面即觸發全新掃描，不跑背景服務。

```bash
cd skills/kunsu-dashboard          # 或 ~/.claude/skills/kunsu-dashboard（install.sh 部署後）
pip install -r requirements.txt    # 首次安裝，需 Python 3.10+
./start.sh                         # 預設 http://127.0.0.1:8000/
```

**這不是 Claude Code skill**，不透過任何觸發語啟動，純手動啟停（無背景常駐、無開機自動啟動）——這是本工具組唯一的例外，詳見 [ADR 010](docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)。

## 專案結構

```
skills/
  handoff/             → 通用交接 skill（SKILL.md＋new-handoff.sh／new-handoff-reply.sh）
  kunsu-init/          → scaffolding skill（SKILL.md＋registry-merge.sh＋範本與種子文件）
  kunsu-inbox/         → 傳令 skill（SKILL.md＋scan-replies.sh／scan-applications.sh／scan-reports.sh）
  kunsu-apply/         → 申請投遞 skill（SKILL.md＋new-application.sh）
  kunsu-report/        → 上報投遞 skill（SKILL.md＋new-report.sh）
  kunsu-list/          → 全域登記清單查詢 skill（SKILL.md＋registry-list.sh）
  kunsu-dashboard/     → 軍師沙盤（kunsu dashboard），本機訊息聚合頁面（非 Claude Code skill，見 ADR 010）
install.sh             → 部署腳本
docs/                  → 本工具組自身的需求、ADR、實作計畫與可重用學習
```

## 文件

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| [docs/adr/](docs/adr/) | 架構決策紀錄（為什麼是純 skill、為什麼是反向註冊表） |
| [docs/brainstorms/](docs/brainstorms/) | 種子需求與模式背景 |
| [CLAUDE.md](CLAUDE.md) | 開發本工具組時的專案規範 |

## 授權

[MIT](LICENSE)。

`.obsidian/plugins/dataview/` 內附的 [Dataview](https://github.com/blacksmithgu/obsidian-dataview) 外掛為第三方作品（MIT License, © Michael Brenan），一併散布以利 vault 開箱即用。
