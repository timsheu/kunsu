# 佔位符對照表

本文件列出 `skills/kunsu-init/assets/templates/` 中所有使用的 `{{...}}` 佔位符、語意說明、出現位置，以及 `/kunsu-init` SKILL.md 應在哪一個訪談問題中取得填充值。

供 U2（SKILL.md 撰寫）使用：每個佔位符皆需對應 SKILL.md 訪談流程的某一題，保證無孤兒佔位符。

---

## 佔位符清單

| 佔位符 | 語意 | 出現的範本檔案 | 由訪談哪一題填入 |
|--------|------|----------------|-----------------|
| `{{PLANNER_NAME}}` | 軍師名稱（用於 CLAUDE.md 標題與 docs/README.md 描述首行） | `kunsu-claude.md`（第 1 行標題）、`kunsu-docs-readme.md`（第 3 行描述） | Q1：軍師名稱（如 `my-product-planner`）——建議使用 kebab-case，作為目標目錄的最後一段路徑名稱 |
| `{{PLANNER_TAGLINE}}` | 一行描述：說明本軍師協調的是哪些子專案、定位是什麼（通常為「跨 X、Y 與 Z 的功能規劃與協調中心」形式） | `kunsu-claude.md`（第 3 行 tagline） | Q2：軍師 tagline（一句話描述軍師定位與涵蓋的子專案群） |
| `{{PROJECT_ROWS}}` | 關聯專案表的資料行，每行格式為 `\| 專案顯示名稱 \| /絕對路徑 \| 角色代碼 \| 角色說明 \|`，一個子專案一行；表頭已固定不含在此佔位符中 | `kunsu-claude.md`（「關聯專案」表的 tbody） | Q3（重複）：子專案清單——每個子專案依序詢問：(a) 顯示名稱、(b) 絕對路徑（SKILL.md 應以 `ls` 查證路徑存在）、(c) 角色代碼（短、kebab-case，即 handoff `to:`）、(d) 角色說明（一行職責，選填） |
| `{{PROJECT_CONSTRAINTS}}` | 各子專案的環境限制小節——每個有限制的子專案產出一個 `### {子專案名稱}環境限制` 小節；若某子專案無特殊限制可省略。整段置於關聯專案表之後、專案結構之前 | `kunsu-claude.md`（「關聯專案」表與「專案結構」之間的區塊） | Q4（選填，針對每個子專案）：環境或技術限制——例如「無可用 runtime，無法實跑測試」「PHP 7.2 語法上限」「需 VPN 才能連接 staging」等；無限制可填「無」，SKILL.md 應對填「無」的子專案省略該小節，對 CLAUDE.md 有的子專案嘗試讀取其技術棧摘要 |
| `{{PLANNER_STRUCTURE}}` | 軍師的目錄結構樹（ASCII tree），只列到三層，末端項目附一行說明；固定包含 `CLAUDE.md`、`CONCEPTS.md`、`docs/` 下各已建立子目錄（至少 `handoffs/`、`handoffs/replies/`） | `kunsu-claude.md`（「專案結構」code block 內容） | 自動產生：SKILL.md 在建立完所有目錄後，依實際落地的目錄結構生成此樹狀圖，不需使用者回答；但需在最終 CLAUDE.md 寫入時填入 |
| `{{PLANNER_ROOT_PATH}}` | 軍師目錄的絕對路徑，用於「回覆信箱協議」中 cd 步驟的路徑提示（讓接手方 session 知道要 cd 到哪裡才能使用 `/handoff reply`） | `kunsu-claude.md`（「回覆信箱協議」章節的 cd 說明段落） | Q1 的延伸：由目標目錄路徑直接推導（使用者在 Q1b 提供目標絕對路徑，即為此值）；SKILL.md 應以此路徑確認目錄不含既有 CLAUDE.md（前置保護） |

---

## 佔位符與訪談問題對照（SKILL.md 設計參考）

U2 撰寫 SKILL.md 訪談流程時，應確保以下問題涵蓋所有佔位符：

| 訪談問題 | 對應佔位符 |
|----------|-----------|
| Q1a：軍師名稱（kebab-case）| `{{PLANNER_NAME}}` |
| Q1b：目標目錄絕對路徑 | `{{PLANNER_ROOT_PATH}}` |
| Q2：tagline（一行描述） | `{{PLANNER_TAGLINE}}` |
| Q3（每個子專案）：顯示名稱、絕對路徑、角色代碼、角色說明 | `{{PROJECT_ROWS}}` |
| Q4（每個子專案，選填）：環境限制 | `{{PROJECT_CONSTRAINTS}}` |
| 自動產生（建檔後推導） | `{{PLANNER_STRUCTURE}}` |

---

## 無佔位符的範本（逐字使用）

以下範本不含 `{{...}}` 佔位符，scaffold 時直接複製無需替換：

| 範本檔案 | 說明 |
|----------|------|
| `kunsu-concepts.md` | 5 個跨專案協調核心概念的定義逐字保留；複製後即可使用 |
| `home-dataview-handoffs.md` | 附加至 HOME.md 的「交接文件狀態」dataview 區塊；路徑 `"docs/handoffs"` 為通用路徑，直接使用 |

---

## 範本代入範例

代入 `{{PLANNER_NAME}} = my-saas-planner`、`{{PLANNER_TAGLINE}} = 跨前端、後台與行動 App 的功能規劃與協調中心`、`{{PLANNER_ROOT_PATH}} = /Users/developer/projects/my-saas-planner` 後，`kunsu-claude.md` 的頭三行與信箱協議說明應呈現為：

```
# my-saas-planner

跨前端、後台與行動 App 的功能規劃與協調中心
```

…以及：

```
若不先 `cd` 到軍師目錄（`/Users/developer/projects/my-saas-planner`）再執行 `/handoff reply`
```

範本代入後若以上文字完整出現且無殘留 `{{...}}` 字串，視為代入完成。
