# kunsu

**kunsu**（軍師，台語 Tâi-lô *kun-su*，"the strategist"）——運籌帷幄而不上陣。為多 repo AI 協作建立「軍師」的 scaffolding 工具組：以純 skill＋markdown 範本，為 [Claude Code](https://claude.com/claude-code) 快速建立唯讀的軍師 repo（規劃一切、不執行任何實作），並以全域反向註冊表自動化跨 session 傳令。

## 緣起

因為自己接手了很多案子都有前後端+客戶端的架構，雖然可以交給 AI 做，但總會遇到「這個問題要前後端+客戶端一起修改，但 AI session 跨 repo 很容易會出現幻覺」的問題，所以想要做一個「讓其中一個 session 主要負責規劃但不執行，其它 project 各自開 AI session 負責執行但不規劃」的工具，加上直到 2026/07/07 都可以用訂閱制跑 Claude Fable 5，所以跟 Fable 5 發想討論後寫了這個工具，期望是未來能有效率的使用 AI agent。

## 這是什麼

> **命名故事**：kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；`/handoff` 是軍師與各營共用的公文格式。

當一個功能橫跨多個 git repo（例如後台 API、Android App、前端網站各自獨立），單一 AI session 難以同時掌握全局。**軍師**是一個獨立的第三方 repo——多 repo 協作的規劃協調中心，只放 markdown 文件：它對所有子專案唯讀、產出跨專案的定案規劃，並以「交接文件（handoff）＋回覆信箱（reply inbox）」與各營的 session 往返協作。

這套模式已在真實專案群跑完多個完整功能週期。本工具組把它變成四個可安裝的 skill：

| Skill | 用途 |
|-------|------|
| `/kunsu-init` | 訪談式 scaffolding：一次建好軍師的 CLAUDE.md（含五條不變量、回覆信箱與申請信箱協議）、CONCEPTS.md、docs 結構、Obsidian vault、git repo，並登記全域註冊表。含 `add-project` 子指令：掃描申請信箱逐筆審核（核准當下才正式登記），無申請時退回分題訪談，並內建舊軍師的申請信箱遷移。 |
| `/kunsu-apply` | 子專案端投遞「申請加入軍師」：自動偵測路徑、名稱與技術棧，軍師清單從註冊表點選，只需手填角色描述與環境限制；寫一份申請檔到目標軍師的申請信箱，正式登記留給軍師端審核。 |
| `/kunsu-inbox` | 跨 session 傳令：在子專案 repo 執行，列出「哪些交接文件在等我」；在軍師 repo 執行，回報「收到幾份新回覆、幾份新申請」並核對寫入範圍（tripwire）。傳令成本從口述長路徑降為打一次指令。 |
| `/handoff` | 通用交接原語（協議基礎）：在任何專案建立交接文件（`add`）、以回覆信箱模式回報（`reply`）、列出狀態（`list`）、歸檔（`done`）。單 repo 專案也能獨立使用；`/kunsu-inbox` 解析的正是它寫出的檔案格式。 |

核心設計（詳見 `docs/adr/`）：

- **純 skill＋範本，零編譯依賴**——交付物只有 markdown 與少量 shell 膠水腳本。
- **絕不注入子專案**——子 repo 完全不知道軍師存在；所有機器路徑的常設登記只存在於軍師 CLAUDE.md 的關聯專案表與全域註冊表 `~/.claude/kunsu-registry.json` 兩處。
- **例外授權雙信箱**——子專案 session 對軍師 repo 的寫入僅限兩個信箱各新增新檔案：回覆信箱（`docs/handoffs/replies/`）與申請信箱（`docs/applications/`）；tripwire 核對守住這條邊界。
- **傳令自動化、審核閘門不動**——`/kunsu-inbox` 只告知不開工、不主動輪詢；方案核准與驗收照舊由使用者把關。

## 安裝

需求：Claude Code、macOS 或類 Unix 環境、`python3`（registry 腳本使用，可經 Homebrew 或 Xcode Command Line Tools 取得）。

```bash
git clone <this-repo>
cd kunsu
./install.sh          # 複製部署至 ~/.claude/skills/
./install.sh --link   # 開發者模式：symlink 部署，改原始碼即時生效（repo 搬家後需重跑）
```

新開 Claude Code session 即可使用 `/handoff`、`/kunsu-init`、`/kunsu-inbox` 與 `/kunsu-apply`。

> 唯一的外部軟依賴：`/kunsu-init` 的 Obsidian vault 步驟會呼叫全域 `/init-obsidian-vault` skill，未安裝時自動略過該步驟，其餘功能不受影響。交接慣例所需的 `/handoff` 已內建（見 ADR 003）。

## 快速開始

1. **建立軍師**——在任意工作目錄對 Claude 說「幫我建一個軍師」（或 `/kunsu-init`），依訪談回答軍師名稱、目標路徑與子專案清單（名稱／絕對路徑／角色），其餘自動完成。
2. **發交接**——在軍師 repo 以 `/handoff` skill 建立交接文件，`to:` 填子專案的角色字串。
3. **子專案接手**——在子專案 repo 的 session 打 `/kunsu-inbox`，看到待接手清單與回覆路徑，完成後以回覆檔回報。
4. **軍師收件**——回到軍師 repo 的 session 打 `/kunsu-inbox`，看到「收到 N 份新回覆」，下令彙整。
5. **加入新子專案**——在子專案 repo 的 session 說「申請加入軍師」（`/kunsu-apply`），路徑與技術棧自動偵測、只填角色描述；回到軍師 repo 說「add-project」逐筆審核，核准當下才正式登記，三處角色字串（軍師的關聯專案表、註冊表、handoff `to:`）自動保持一致。也可直接在軍師 repo 說「add-project」走訪談路徑。

## 專案結構

```
skills/
  handoff/             → 通用交接 skill（SKILL.md＋new-handoff.sh／new-handoff-reply.sh）
  kunsu-init/          → scaffolding skill（SKILL.md＋registry-merge.sh＋範本與種子文件）
  kunsu-inbox/         → 傳令 skill（SKILL.md＋scan-replies.sh／scan-applications.sh）
  kunsu-apply/         → 申請投遞 skill（SKILL.md＋new-application.sh）
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
