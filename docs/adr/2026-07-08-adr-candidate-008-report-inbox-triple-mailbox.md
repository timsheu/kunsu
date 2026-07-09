---
title: ADR Candidate 008 — 上報信箱：例外授權自雙信箱擴為三信箱（子專案主動上報）
date: 2026-07-08
type: adr
status: proposed
---

# ADR 008：上報信箱——例外授權自雙信箱擴為三信箱（子專案主動上報）

> 狀態：**Proposed**（2026-07-08 起草，尚未實作；源自既有軍師 repo 的「孤兒回覆」
> 事件與使用者裁示「支持主動回報並加入軍師的記錄」。待審定後另立實作計畫。）

## Context

### Observations（現況盤點）

- 一座既有軍師的 `docs/handoffs/replies/` 中出現一份**無對應原交接文件的孤兒回覆**
  （子專案就 UI/UX 發現主動上報，軍師未曾就該議題發起交接）。其落點位於授權信箱內
  （位置合規），但缺乏可配對的 `in_reply_to` 對象。
- 現行協議（ADR 002、ADR 006）只定義兩種子專案→軍師的訊息類型：**回覆**（需既有
  交接文件）與**申請**（請求加入登記）。「子專案主動上報／軍師未發起議題」沒有正式
  管道。
- `replies/` 的所有消費端均假設「回覆與交接一對一配對」：`/handoff list` 依
  `in_reply_to` 分組；`/handoff done` 將交接與其回覆成對歸檔；`/kunsu-inbox` 子
  repo 模式的狀態機（待接手／已回覆待確認）以交接文件為鍵。孤兒回覆掛不進任何
  生命週期，永遠不會被歸檔收斂。
- 同日另有一起「子專案口語『回覆軍師』未命中任何 skill、回覆錯投軍師
  `docs/handoffs/` 頂層」事件（已由 handoff skill v0.3.0 的觸發詞與 kunsu 語境
  分支修補，並由 `scan-replies.sh` tripwire 如設計般攔截）。兩起事件同根因：
  **子專案有話要對軍師說、卻無結構化管道時，session 即興落檔**。
- ADR 006 已有同型前例：「子端發起的訊息類型」以獨立信箱＋獨立掃描＋獨立
  frontmatter schema 處理；其替代方案審議中曾以「語意錯置、掃描誤計」否決
  「借用 `docs/handoffs/replies/` 偽裝」的做法。

### Hypothesis（推斷，非事實）

- 子專案開發過程中產出的跨專案情報（UI/UX 發現、環境限制變動、影響規劃的技術
  現況）對軍師的規劃記憶有留存價值；推斷此類上報會隨協作深化持續出現，而非一次性
  事件。

## Decision（proposed）

1. **例外授權自雙信箱擴為三信箱**：在回覆信箱、申請信箱之外，新增**上報信箱**
   `docs/reports/`（scaffold 內建，含 `archive/` 與兩層 `.gitkeep`）。授權形式
   不變——子專案 session 僅能在信箱內**新增新檔案**（上報限頂層），不得編輯任何
   既有檔案。ADR 006 的「僅有的兩個」語義由本 ADR 修訂為「僅有的三個」；ADR 006
   主文維持原貌（循 ADR 005 歷史快照前例）。
2. **語意界線與唯一判準——上報是情報，不是反向委派**：三種訊息的區分以**結構
   判準**定義，不依動詞語感——回覆與上報的唯一分界是**有無對應的原交接文件**：
   **回覆（reply）**＝軍師發起之交接的下游回應，必有 `in_reply_to` 配對（含
   `status: partial` 分階段進度）；**上報（report）**＝子專案發起、無對應交接的
   情報，**不承諾軍師回覆或執行**。若子專案的實際意圖是「要軍師做某事」，由軍師
   讀取上報後自行開 plan 或發起 handoff 追蹤；`docs/reports/` 不作為反向任務
   佇列，不設回覆機制。與既有兩種訊息的區分：**handoff**＝軍師發起的委派、期待
   回覆；**application**＝子端發起的登記請求、期待審核；**report**＝子端發起的
   情報、無回覆義務。
   **中文定名「上報」的理由**：正體中文口語中「回報」偏向 reply（回報交辦結果、
   回報進度），「報」系動詞普遍雙關（「跟軍師報告進度」若指交辦事項即為 partial
   回覆），故概念詞取方向明確、必然主動的「上報」；英文與機器識別字維持
   report（`docs/reports/`、`type: report`、`/kunsu-report`）不變。
3. **frontmatter schema**：`type: report`、`from:`（角色代碼，與
   `~/.claude/kunsu-registry.json` 的 `roles` 字面一致）、`title`、`created`、
   `status: submitted`、`tags`。不設 `to:` 欄（收件方即信箱所在軍師，無需比對）。
4. **生命週期與掃描**：沿用「未 commit 即未處理」慣例。軍師彙整入規劃記錄後，
   更新上報檔 `status`（值域見 Open questions）並 `git mv` 至 `archive/`——比照
   ADR 006 Decision 4 的論證：歸檔時點僅剩軍師單一寫入方，版本漂移條件不成立。
   上報歸檔為**純手動操作**，不另建 skill 子指令：軍師 session 依序以 Edit 更新
   `status` → `git add` → `git mv` 至 `archive/`（與 `add-project` 歸檔申請同
   順序，原因相同：untracked 檔案直接 `git mv` 會失敗）；此三步驟逐字記入軍師
   CLAUDE.md 範本「上報信箱協議」章節。
   掃描實作為 `scan-reports.sh`，分類規則比照 `scan-applications.sh`：
   `docs/reports/.gitkeep` 靜默略過（遷移補建後未 commit 的佔位檔，比照
   `scan-applications.sh` 既有豁免分支）；頂層 `*.md` 新增＝新上報；「頂層→
   `archive/`」搬移（可攜帶 frontmatter 更新）＝授權歸檔（雙側核驗）；`archive/`
   內新增＝合法；反向搬移、頂層修改與刪除、外部搬入＝異常硬停。置於 kunsu-inbox
   （信箱掃描域）。`/kunsu-inbox` 軍師模式增列第三段上報份數；授權邊界聲明
   「兩個信箱」同步改「三個信箱」。
5. **投遞端為獨立 `/kunsu-report` skill**（`kunsu-` 前綴循 ADR 004）：復用
   `/kunsu-apply` 的管線模式（自動偵測當前 repo → registry 選軍師與角色代碼 →
   防撞產檔，新增 `new-report.sh`）。採獨立 skill 而非 `kunsu-apply` 子指令的
   理由：**觸發詞路由清晰**——本輪兩起事件的根因正是口語觸發縫隙；且申請與
   上報的下游流程完全不同（申請→審核登記，上報→彙整歸檔）。管線復用發生在
   腳本與流程模式層，不共用 skill 入口。
   **前置條件——僅服務已登記 repo**：registry 查無當前 repo 條目（尚未登記於
   任何軍師）時，停止並回報「此 repo 尚未登記，請先以 `/kunsu-apply` 申請加入
   後再使用 `/kunsu-report`」，不寫入任何檔案。此為與 `/kunsu-apply` 管線的
   **刻意差異**：apply 服務首次接觸的未登記 repo、不需角色代碼；report 只服務
   已登記 repo，`from:` 必須自 registry 自動填入（Decision 6 的反向快查同以
   已知角色代碼為前提）。
   **觸發詞分配（口語→歸屬）**：
   - **reply**（`/handoff` reply，已隨 v0.3.0 落地）：「回覆軍師」「回覆軍師的
     交接」「回覆交接」「**回報軍師**」「回報結果／回報進度」——「回報」口語
     偏向報告交辦結果，歸 reply。
   - **report**（`/kunsu-report`）：「上報軍師」「向軍師上報」「主動上報」
     「主動回報」「**稟報軍師**」（稟報必為下對上、必為主動，與軍師隱喻相契）。
   - **灰帶傾向 report**：「跟軍師報告」「知會軍師」「反映給軍師」——由
     Decision 6 行為層兜底，分類錯誤僅多一次重導。
6. **雙向重導——狀態為最終消歧者**：動詞觸發的灰帶由**狀態核對**兜底，兩側
   皆內建重導。reply 側（`/handoff` reply 的 kunsu 語境分支）查無 `to:` 本角色
   的待回交接時，提示使用者意圖可能是主動上報並指向 `/kunsu-report`（該 skill
   落地前如實告知暫無正式管道，不落檔）；report 側（`/kunsu-report`）投遞前
   反向快查待回交接，若存在 `to:` 本角色的 open 交接，反問「是否其實是回覆
   某份交接」並列出候選供重導。任一側路由錯誤僅多一次重導，不產生錯投檔案。
7. **範本與既有軍師遷移**：scaffold 範本內建 `docs/reports/` 結構與「上報信箱
   協議」章節；既有軍師比照 ADR 006 Decision 5 模式，由 `add-project` 遷移邏輯
   擴充（偵測缺 `docs/reports/` 時提議補建、Grep 核查），子端 `/kunsu-report`
   投遞前檢查目標軍師已有信箱，未遷移即導引不投遞。
8. **現存孤兒回覆的處置**：本 ADR 落地後，該檔 `git mv` 至 `docs/reports/`
   並補正 frontmatter（`type: report`、移除 `in_reply_to`），作為首份上報樣本；
   已入版控的歷史 commit 不改寫。落地前維持原地（已留存、不刪除）。

## Consequences

- `install.sh` SKILLS 陣列新增 `kunsu-report`。
- 軍師 CLAUDE.md 範本：例外授權與 tripwire 兩條 bullet 改三信箱表述，新增
  「上報信箱協議」章節（須含 Decision 4 的歸檔三步驟說明）；`/kunsu-inbox`
  授權邊界聲明與軍師模式輸出同步。
- kunsu-init SKILL.md 步驟 ④-4：新增 `docs/reports/` 與 `archive/` 目錄建立
  及兩層 `.gitkeep`（比照 `docs/applications/` 模式）；步驟 ④-6 產生的軍師
  結構 ASCII tree 同步補入 `docs/reports/` 兩層。
- kunsu-init `add-project` 步驟 ②：於申請信箱遷移偵測之後加入 `docs/reports/`
  遷移偵測——缺目錄時提議補建目錄與 `.gitkeep`、補入「上報信箱協議」章節、
  Grep 核查，任一核查失敗明確回報不回滾。
- reply 側重導文案已隨 handoff skill v0.3.0 預埋（零筆分支指向 `/kunsu-report`，
  該 skill 落地前如實告知暫無正式管道）。
- scaffold 驗收清單延伸 reports 結構項；結構不變量同 ADR 006（`docs/reports/`
  與 `archive/` 需含 `.gitkeep`，clone 後目錄需存在，否則掃描在首份上報前無從
  核對）。
- 重複投遞不覆寫：子端永遠只新增檔案（同日同名自動 `-2`、`-3`），與申請信箱
  一致。
- `CONCEPTS.md` 新增「上報（report）」詞條，與「交接（handoff）」「申請
  （application）」並列為三種跨 repo 訊息類型（`/ce-compound` 維護）；「例外
  授權信箱」詞條計數自「目前有兩個——回覆信箱與申請信箱」改為三個，並新增
  「上報信箱」詞條與「回覆信箱」「申請信箱」並列；「回覆信箱」詞條補
  「有無對應交接為回覆與上報的唯一分界」判準。
- 母體 repo CLAUDE.md Invariant 2 與 README.md「例外授權雙信箱」bullet 的信箱
  例外表述同步為三信箱。

## Alternatives considered

- **(a) 孤兒回覆留在 `replies/` 當 append-only 留存**：位置合規但語意破格——
  `replies/` 全部消費端（list 分組、done 成對歸檔、inbox 狀態機）依 `in_reply_to`
  配對，孤兒檔永不收斂；ADR 006 曾以同理否決「借用 replies/ 偽裝申請」。否決。
- **(b) 上報留在子專案自身 repo、自軍師移除**：軍師須以 pull 模型逐 repo 撈取
  情報，與整套 push 式信箱架構（registry 讓子端知道往哪投遞）相悖；跨專案情報
  不進軍師版控與 Obsidian 檢視。否決。
- **放在 `docs/handoffs/inbound/`（handoffs 樹下）**：`scan-replies.sh` tripwire
  的邊界簡單性（handoffs 下非 replies/ 即異常）被破壞，需讀 frontmatter 才能
  分類，porcelain 級偵測失效。否決。
- **反向 handoff（子端寫軍師 `docs/handoffs/` 頂層）**：破壞「交接文件單一作者
  ＝軍師」原則與 tripwire 錯投偵測——本次錯投事件正是靠此邊界攔截。否決。
- **擴充 `/kunsu-apply` 為通用投遞 skill（apply＋report 雙子指令）**：管線可
  復用，但觸發詞混流（申請語彙與上報語彙互相污染路由）、下游流程迥異。否決
  （復用降至腳本與流程模式層）。
- **概念詞沿用「回報」**：與事件描述直覺一致，但正體中文口語「回報」偏 reply
  （回報交辦結果），與 reply 觸發詞正面相撞——本輪根因即口語路由縫隙，概念詞
  自身製造歧義不可接受。否決，改採「上報」。

## Open questions

- 歸檔時的 `status` 值域：`incorporated`（已納入規劃記錄）／`noted`（已閱、
  無需動作）兩檔，或單一 `archived`——待實際用量與 Obsidian 檢視需求再定。
- 「未 commit 即未處理」對上報是否足夠，或需要輕量「軍師已讀」標記——待用出
  手感再評估。
- 上報量成長後的整理慣例（同 ADR 006 open question）。
- 既有軍師僅兩座，`add-project` 之外是否需要獨立遷移入口——傾向不需要，手動
  成本低。
