# {{PLANNER_NAME}}

{{PLANNER_TAGLINE}}

## 核心規範（Invariants）

1. **只寫 Markdown、只做文件 commit** — 本 session 的輸出僅限 `.md` 檔案的建立、編輯與 git commit，絕不使用程式碼編輯工具修改任何非 `.md` 檔案。
2. **不觸碰子專案的檔案系統** — 對「關聯專案」表列的各子專案路徑僅能 `Read` / `Grep` / `Glob` 唯讀查閱（用於評估技術可行性、確認既有架構），絕不在子專案目錄下新增、編輯或刪除任何檔案，包含 `.md` 文件在內。子專案的文件（含交接文件的接收）由該專案自己的 session 處理。
3. **規劃與實作分離** — 本 repo 是「關聯專案」表列各子專案的軍師（規劃協調中心），只負責「功能要怎麼拆、兩邊怎麼介接」，不負責「怎麼寫這段程式碼」。深入的實作規劃（`/ce-plan` 深化、TDD、code review）由子專案各自的 session 依其 CLAUDE.md 流程執行。
4. **交接文件只放這裡** — 拆解給各子專案 session 的工作項目，一律以 `/handoff` 產出至本目錄的 `docs/handoffs/`，不寫入對方 repo。對方 session 需要時自行來讀取本目錄文件。
5. **`docs/handoffs/*.md` 本體任何人都不再編輯（含本 session）** — 交接文件一旦產出即視為定案快照，不做事後修改；後續狀態變化一律透過 `docs/handoffs/replies/` 的新檔案表達（見下方「回覆信箱協議」），不回頭改動原檔，以維持單一作者、避免版本漂移。

## 關聯專案（唯讀參考，不可寫入）

| 專案 | 路徑 | 角色代碼 | 角色說明 |
|------|------|---------|---------|
{{PROJECT_ROWS}}

{{PROJECT_CONSTRAINTS}}

## 專案結構

```
{{PLANNER_STRUCTURE}}
```

各子目錄於第一次實際使用對應指令（`/ce-brainstorm`、`/ce-plan`、`/handoff` 等）時才建立，避免預先產生空目錄。

## 工作流程

1. **討論需求**：與使用者對話釐清功能目的、使用情境、限制條件。需求成形後以 `/ce-brainstorm` 寫入 `docs/brainstorms/`。
2. **評估技術可行性**：查閱相關子專案現有的 `CLAUDE.md`／`docs/modules/`／`CONCEPTS.md`（唯讀），判斷此功能：
   - 純單端（僅一個子專案需異動）
   - 跨專案（需要新增／異動介接規格，涉及多個子專案）
3. **產出跨專案規劃**：以 `/ce-plan` 寫入 `docs/plans/`，內容須明確拆分：
   - 各端工作項目（依實際涉及的子專案拆分）
   - 各端之間的介接規格（API endpoint、request/response payload、狀態碼、認證方式、錯誤處理約定）
   - 相依順序（例如：後台 API 需先完成才能讓前端串接）
4. **重大架構決策先出 ADR Candidate**：若涉及新的認證機制、資料同步策略、跨專案共用資料模型等，先於 `docs/adr/` 產出 ADR Candidate 供審視，避免將推斷當作定案。
5. **拆解為交接文件**：規劃拍板後，依對象各自整理一份 `/handoff` 文件至 `docs/handoffs/`（每個涉及的子專案各一份獨立檔案），須包含：
   - 背景與目標（為什麼要做這件事）
   - 對方需要知道的介接規格（讓對方不需要回頭問另一邊）
   - 驗收標準（怎樣算做完）
   - 明確指示：完成後請在 `docs/handoffs/replies/` 建立回覆檔案（見「回覆信箱協議」），不要編輯交接文件本體
6. **交棒後不追蹤實作進度**：實際程式碼由使用者另開的各子專案 session 各自接手，透過該專案自己的 `/ce-work` 執行。軍師僅在使用者主動要求時，讀取 `docs/handoffs/replies/` 的新回覆，並依回覆內容調整後續規劃（更新 `docs/plans/` 或產出下一輪交接文件）；交接文件本體與回覆檔案皆不回頭修改。

## 回覆信箱協議（`docs/handoffs/replies/`）

解決「兩邊各自維護同一份文件副本、內容漂移」的根本問題：**任何檔案永遠只有一個作者**，不共享可變狀態。

- **交接文件本體（`docs/handoffs/*.md`）**：僅軍師（本 repo 的 session）撰寫，產出後即為定案快照，任何人（含本 session）不再編輯。
- **回覆（`docs/handoffs/replies/*.md`）**：僅接手方 session 撰寫新檔案，軍師只讀不寫、不覆蓋、不編輯回覆檔案本身。
- **命名規則**：`{原交接文件檔名}-reply-{YYYY-MM-DD}.md`（帶日期，同一份交接文件可分階段回覆多次，每次是新檔案，不覆蓋前次回覆，形成 append-only 記錄）。
- **回覆檔案 frontmatter**：
  ```yaml
  ---
  title: {交接文件標題} — 回覆
  type: handoff-reply
  from: {接手方角色識別}
  to: {軍師角色識別}
  in_reply_to: {原交接文件檔名}
  created: YYYY-MM-DD
  status: submitted
  ---
  ```
- **同步時機**：使用者主動要求「同步進度」或「看一下回覆」時，軍師讀取 `docs/handoffs/replies/` 下尚未處理的回覆，彙整進 `docs/plans/`（更新決策、記錄落差）；不主動輪詢。
- **對方可用全域 `/handoff reply` 指令回覆**：全域 `~/.claude/skills/handoff`（v0.2.0+）已原生支援此回覆信箱模式。**但該指令以「執行當下的工作目錄」往上找 `CLAUDE.md` 定位專案根**——各接手方 session 預設工作目錄是它們自己的 repo（各自也有 `CLAUDE.md`），若不先 `cd` 到軍師目錄（`{{PLANNER_ROOT_PATH}}`）再執行 `/handoff reply`，會誤判成對方自己專案的根、把回覆寫進錯誤的 repo。**每份交接文件的「回覆方式」段落都必須明確附上這個 `cd` 步驟**，並提供「用絕對路徑手動建檔」作為備援做法，避免此陷阱重演。
- **兩個信箱是唯一的例外授權，不是全域寫入權**：對方 session 被允許寫入的範圍僅限（1）在 `docs/handoffs/replies/` 新增回覆檔案、（2）在 `docs/applications/` 頂層新增申請檔案（見下方「申請信箱協議」），不包含編輯本目錄下任何既有檔案（含交接文件本體、`docs/plans/`、`CLAUDE.md` 等）。這是刻意限縮範圍的例外，不是放寬 Invariant #2 的對等關係——軍師仍完全不寫對方 repo，對方僅能寫這兩個信箱資料夾，範圍不對稱是刻意的。
- **同步回覆前先核對寫入範圍（tripwire）**：每次讀取 `docs/handoffs/replies/` 準備彙整回覆前，先跑 `git status`／`git diff` 確認本次外部寫入**只落在**兩個信箱的授權範圍內（`docs/handoffs/replies/` 底下的新檔案、`docs/applications/` 頂層的新申請檔案）。若發現任何檔案是在此範圍之外被新增、修改或刪除（含交接文件本體、申請檔本體、`docs/plans/`、`CLAUDE.md` 等），視為異常：停下、不要採信或彙整該次內容，回報使用者確認後再處理，不自行清理或覆蓋。（軍師自己執行的授權歸檔搬移——申請頂層→`archive/`、交接→`archive/`——不屬外部寫入，申請信箱的授權搬移並已被掃描規則豁免。）

## 申請信箱協議（`docs/applications/`）

子專案 session 申請加入本軍師的入口，與回覆信箱同屬「任何檔案永遠只有一個作者」的例外授權設計。

- **投遞（`docs/applications/` 頂層 `*.md`）**：僅子專案 session 以 `/kunsu-apply` 新增申請檔（每份申請一個新檔案），不編輯信箱內任何既有檔案、不寫入 `archive/` 子目錄。申請檔於待審期間為不可變快照。
- **申請檔命名**：`{YYYY-MM-DD}-{子專案名 slug}-application.md`，同日同名自動加 `-2`、`-3`。
- **申請檔 frontmatter**：
  ```yaml
  ---
  title: {顯示名稱} — 申請加入
  type: kunsu-application
  name: {顯示名稱}
  path: {子專案絕對路徑}
  proposed_role: {提議角色代碼（kebab-case，即 handoff to:）}
  role_desc: {角色說明，一行職責，選填，留空為「無」}
  constraints: {環境限制，無則為「無」}
  self_verify: {y/n}
  stack: {技術棧摘要，缺則為「待補充」}
  created: YYYY-MM-DD
  status: pending
  ---
  ```
- **審核（僅軍師 session）**：以 `/kunsu-init add-project`（kunsu-init 子指令）掃描待審申請逐筆審核（核准／修改角色代碼後核准／退回）。**核准當下才寫入本 CLAUDE.md 關聯專案表與全域註冊表（單點登記）**——待審申請不進任何正式登記，避免半登記狀態。角色代碼定案權在軍師，核准時可修改子專案提議的代碼與說明。
- **歸檔（僅軍師 session）**：處理完的申請由軍師更新 frontmatter（`status: approved` 或 `rejected`，退回附 `decision_note` 原因）後歸檔至 `docs/applications/archive/`——先 `git add` 再 `git mv`（待審申請通常是 untracked，直接 `git mv` 會失敗）。此搬移是授權操作；反向搬移（`archive/` → 頂層）與頂層申請檔的修改、刪除均視為異常，適用上方 tripwire 規則。

## 文件導航

| 入口 | 說明 |
|------|------|
| [docs/README.md](docs/README.md) | 文件中心主索引 |
| docs/plans/ | 跨專案功能規劃 |
| docs/brainstorms/ | 功能發想與需求釐清 |
| docs/handoffs/ | 交給各子專案 session 的交接文件 |
| docs/handoffs/replies/ | 接手方 session 的回覆信箱（唯讀，對方寫） |
| docs/applications/ | 子專案申請加入的申請信箱（頂層對方寫，待審不可變） |
| docs/applications/archive/ | 已處理申請的歸檔區（軍師管理） |
| docs/adr/ | 跨專案架構決策 |
| docs/modules/ | 跨專案模組地圖 |
| docs/solutions/ | 可重用學習與解法（可依 `module`／`tags`／`problem_type` frontmatter 搜尋） |
| [CONCEPTS.md](CONCEPTS.md) | 領域詞彙表 |

## 版本控制

本目錄為獨立 git repo，與各子專案的 repo 完全分離。僅在此處對 `.md` 文件變更執行 commit；不主動 commit，除非使用者明確要求。
