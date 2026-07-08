---
title: planner-toolkit 種子需求 — 規劃中心 scaffolding 與跨 session 傳令自動化
date: 2026-07-06
topic: planner-toolkit
type: brainstorm
status: draft
---

# planner-toolkit 種子需求

> 本文件由 ebook 規劃協調中心 session（2026-07-06）的設計討論彙整而成，是本專案的起點脈絡。依 CE 規範，觀察（observation）、推斷（hypothesis）、建議（recommendation）與疑問（questions）分層陳述。

## 背景與動機

ebook 專案群規劃中心（唯讀規劃中心模式，本機私有路徑，略）已跑完兩個完整功能週期（書籤筆記 bulk 同步、書城登入功能），包含多輪 handoff 往返、回覆信箱彙整與第三方實作查核，驗證了這套協作模式的實用性。使用者提出兩個需求：

1. **Scaffolding**：把「建立規劃中心」工具化，未來其他由數個子專案組成的專案群，能快速架起同款規劃中心（含 CLAUDE.md 規範、docs 結構、Obsidian vault、git repo）。
2. **傳令自動化**：改善目前的人工傳達痛點——使用者要手動提示子 repo session「去看哪份 handoff」、手動通知規劃中心「對方已回覆」。

## 觸點拆解（observation）

現行人工介入混合了兩種性質不同的工作：

| 觸點 | 性質 | 判斷 |
|---|---|---|
| 「子 repo session 去看某份 handoff」 | 傳令——純轉送路徑，零判斷 | 可自動化 |
| 「跟規劃中心說對方回覆了」 | 傳令——純通知事件，零判斷 | 可自動化 |
| 核准方案、產品取捨（AskUserQuestion）、驗收查核結果 | 審核——需要判斷力 | 必須保留 |
| 決定「何時」開子 repo session 動工 | 調度——涉及優先序 | 建議保留 |

改良方向：**把傳令自動化，審核與調度閘門原封不動。**

## 先前嘗試的教訓：ce-team

路徑：（本機私有路徑，略）（Rust CLI，Phase 1 完成，Phase 2 launcher 未實作）。

- **使用者親述（事實）**：路徑耦合程度很高，實務上不實用。
- **設計觀察（讀其 README 與文件所得）**：
  1. `add-repo` 在每個子 repo 的 CLAUDE.md／AGENTS.md 注入 managed section——協調層的存在滲入 N 個 repo，每個 repo 都對協調層產生依賴。
  2. 為避免絕對路徑洩漏，注入區塊採 `{coord-root}` 佔位符，需靠 Phase 2 launcher 在執行期展開；launcher 從未做出來，注入區塊因此是死文字。
  3. Walk-up discovery 假設各 repo 位於同一 workspace 根之下；實際 repo 散落於 `~/PhpstormProjects`、`~/AndroidStudioProjects`、`~/Documents_local` 三處，假設不成立。
  4. `ce-team.yaml` 存放機器路徑且被 gitignore，工具核心狀態不可備份、不可跨機。
  5. `docs/troubleshooting/dogfooding-log.md` 完全空白——工具先於痛點驗證而建。
- **推斷（hypothesis）**：耦合養出工具（同步 N 個注入區塊需要程式碼維護），工具又需要持續維護；把耦合從架構上消除（子 repo 零寫入、路徑集中單點），工具本身就失去存在必要。ebook 規劃中心以純慣例達成實際多輪協作，是此推斷的正面例證。

## 範本母本解剖（observation）

ebook 規劃中心的組成，依可範本化程度分類：

**通用骨架（直接進範本）**：
- CLAUDE.md 的 5 條 Invariants（只寫 md、子專案唯讀、規劃實作分離、交接文件只放中心、handoff 本體不可變）。
- 回覆信箱協議全文（命名規則、frontmatter 格式、tripwire 檢查、不對稱授權說明、cd 工作目錄陷阱警告）。
- 工作流程六步驟、文件導航表。
- CONCEPTS.md「跨專案協調」段落的 5 個概念：規劃協調中心、子專案、交接文件、回覆信箱、定案規劃。
- docs/README.md 與 docs/HOME.md（Obsidian 著陸頁，Dataview 動態清單）骨架。
- 母本 `docs/solutions/` 的兩篇模式沉澱文件（唯讀規劃中心模式、回覆信箱慣例），可作為新中心的種子知識。
- Obsidian vault 設定（Dataview＋Minimal 主題、`.obsidian/.gitignore` 排除 workspace 狀態）——既有全域 `/init-obsidian-vault` skill 已涵蓋。

**參數化內容**：
- 中心名稱與 tagline。
- 關聯專案表：各子專案的名稱、絕對路徑、角色。
- 各子專案的環境限制與驗證能力（例如 Lumen「PHP 7.2、無 runtime、驗收以程式碼審閱與靜態檢查為主」vs 書城「可實跑驗證」）——直接影響規劃時的驗收方式設計，範本需保留此段落結構供填空。
- CONCEPTS.md 領域段落、README「目前狀態」（留空起始）。

**注意**：母本目前為三方協調（Lumen＋Android＋書城），且已知未來會加入 iOS。範本應直接設計為 N 方，不要複製母本早期「兩方」的痕跡（如 plan 文件固定拆「Android 端／Lumen 端」兩節的寫法）。

## 方案設計（recommendation）

### 1. `/init-planner` skill（scaffolding）

1. **訪談**：中心名稱、子專案清單（名稱／絕對路徑／角色／環境限制／能否自我驗證）。
2. **自動查證**：驗證各子專案路徑存在；讀取其 CLAUDE.md 自動摘要角色與技術棧，減少手填。
3. **產生檔案**：CLAUDE.md（通用骨架＋參數注入）、CONCEPTS.md（種入 5 個協調概念）、docs/README.md、複製兩篇 solutions 種子文件。docs 子目錄維持「首次使用對應指令才建立」慣例，不預建空目錄。
4. **建 Obsidian vault**：沿用或內嵌 `/init-obsidian-vault`。
5. **git init＋初始 commit**（經使用者確認後執行）。
6. **維護全域註冊表**（見下）。
7. **`add-project` 子指令**：往既有中心新增子專案——更新中心 CLAUDE.md 關聯專案表與註冊表。已知 ebook 中心未來加入 iOS 時即是第一個真實案例。

### 2. 全域反向註冊表 `~/.claude/planner-registry.json`

現有架構的缺口是反向索引：規劃中心知道所有子 repo 路徑，但子 repo session 不知道「哪些規劃中心管到我」。註冊表補上這塊：

```json
{
  "/path/to/backend-repo": [
    { "planner": "/path/to/my-product-planner", "role": "backend" }
  ]
}
```

機器特定路徑本來就不應進 git，放全域設定檔恰當。由 `/init-planner` 與 `add-project` 維護。副作用：可根治 `/handoff reply` 的 cd 工作目錄陷阱（查註冊表定位規劃中心，不再靠工作目錄往上找 CLAUDE.md）。

### 3. `/inbox` skill（傳令按鈕化）

- **在子 repo session 執行**：查註冊表 → 掃描對應規劃中心 `docs/handoffs/` 中 `to:` 為我的角色、且最新回覆狀態非 `done` 的交接文件 → 列出待接手清單。口頭傳令從「去看這個長路徑」降為打一次 `/inbox`。
- **在規劃中心 session 執行**：以 `git status` 找 `docs/handoffs/replies/` 下的 untracked 新檔案（外部回覆天然未 commit，**git 本身就是「未處理」標記**，同時順便完成 tripwire 範圍核對）→ 回報「收到 N 份新回覆」，彙整仍由使用者下令。
- **狀態推導規則**：handoff 本體不可變，其 frontmatter `status` 不會更新；「待接手／已完成」由 `replies/` 中 `in_reply_to` 對應的最新回覆檔 `status`（submitted／partial／blocked／done）推導。以小型 shell 腳本實作，附於 skill 內——屬設定層膠水，非獨立維護的工具專案。

### 4. 第二階段：SessionStart hook

全域 hook 於 session 啟動時執行同一支檢查腳本，自動注入「有 N 份待接手 handoff」到開場 context，傳令降到零。取捨：同 repo 的無關 session 也會看到提示。建議先以 `/inbox` 按需觸發，實際使用一段時間後再決定是否升級。

### 5. 明確延後：MCP server

MCP 解決的是「session 怎麼讀寫信箱」，但信箱本來就是檔案，傳輸層已存在；真正的痛點在觸發層（session 不知道有事找它），MCP 無法解決（session 不會自己呼叫工具）。留待兩個訊號出現再評估：
1. 需要跨機器協作。
2. 需要讓無法執行 Claude hooks／skills 的 agent 以型別化工具存取信箱。

### 保留的人工閘門

- 交棒時機：`/inbox` 只告知，不自動開工。
- 彙整時機：規劃中心只報「有新回覆」，彙整由使用者下令（維持「不主動輪詢」精神）。
- 所有產品取捨與查核驗收：照舊走 AskUserQuestion。

## 開放問題（questions）

1. 全域 `/handoff` skill（v0.2.0+）是否升版改用註冊表解 cd 陷阱？涉及全域資產異動，需評估對非規劃中心專案的相容性。
2. scaffold 隨附的兩篇 solutions 種子文件，採複製（各中心自持一份）還是引用母本路徑（單一來源但跨 repo 依賴）？初步傾向複製——solutions 本來就是「沉澱後各自帶走」的性質。
3. 註冊表格式與粒度：JSON 單檔是否足夠？一個 repo 隸屬多個規劃中心、或在同一中心擔任多角色的情境是否要支援？
4. `/inbox` 在子 repo session 的角色識別：以 repo 路徑對應註冊表的 `role` 欄位即可，還是需要更細的比對？
5. Obsidian vault 步驟：呼叫既有 `/init-obsidian-vault` skill，還是把邏輯內嵌進 `/init-planner`（避免跨 skill 依賴）？
6. skill 與指令命名定案（`/init-planner`？`/planner init`？`/inbox` 是否與其他慣用指令衝突？）。

## 下一步

在本 repo 開新 session：先審視兩份 ADR Candidate（`docs/adr/`），拍板後以 `/ce-plan` 將本文件推進為實作計畫。
