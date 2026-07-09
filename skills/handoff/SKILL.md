---
name: handoff
version: 0.3.0
description: |
  把一個需要交給「另一個 session／另一個角色（如後台、前端、DevOps）」研究或
  接手的議題，寫成一份獨立交接文件，落在當前專案的 docs/handoffs/。每份交接一個
  檔（YYYY-MM-DD-標題.md），含 Dataview 友善 frontmatter（from/to/status）。
  交接文件本體建立後即為定案快照，任何人（含發起方自己）都不再編輯；接手方改以
  在 docs/handoffs/replies/ 新增獨立回覆檔案回報結論（回覆信箱模式），避免雙方
  共編同一檔案造成版本漂移。
  Use when asked to「寫一份交接文件」「交接給後台」「handoff 給另一個 session」
  「回覆交接文件」「回覆軍師」「回覆軍師的交接」「回覆交接」「回報軍師」
  「回報結果」「reply 給軍師」「產生交接文件」「新增 handoff」「list handoffs」
  「/handoff」.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# handoff — 跨 session／跨角色交接文件

把一個「這個 session 已研究到一個段落、需要另一個 session 或另一個角色接手」的
議題，寫成一份獨立 md 檔，放進當前專案的 `docs/handoffs/`。

典型場景：Android session 分析完前端改動、需要後台 session 研究對應的 API 契約；
或某議題需要 DevOps／DBA 接手評估。交接文件是「跨對話的工作記憶」，讓接手方不必
重讀整段對話就能理解背景、現況與待決問題。

```
docs/handoffs/          → 交接文件本體（定案快照，任何人不再編輯，含發起方自己）
docs/handoffs/replies/  → 接手方回覆信箱（append-only，接手方新增新檔案回覆，
                           不編輯交接文件本體，也不覆寫前次回覆）
                         →（發起方確認回覆後）status 改 done，交接文件與其回覆
                           一併 git mv 到 docs/handoffs/archive/
```

`docs/handoffs/` 屬參考層（非 CE plugin 管理），與 `docs/plans`、`docs/brainstorms`
等 plugin 原生路徑無關，不取代任何 CE 指令行為。若交接內容成形為正式規劃，仍走
既有 `/ce-brainstorm`／`/ce-plan` 流程，交接文件本身只作為輸入。

## 何時使用

- 使用者說「寫一份交接文件」「交接給後台」「handoff 給另一個 session」「/handoff ...」
- 目前 session 已把某議題研究到一個段落，需要**換一個上下文乾淨的 session**（不同
  程式碼庫、不同角色）接手，且不希望對方重讀整段對話
- 接手方已完成研究，要回報結論給發起方（`/handoff reply`；含子 repo 回覆所屬
  軍師的交接，如口語「回覆軍師」）
- 使用者要查詢交接現況（`/handoff list`）、標記完成（`/handoff done`）

不要用於：
- 純粹自己的待辦技術債 → 用 `/todo`
- 還沒成形的靈感速記 → 用 `/idea`
- 需要對話釐清需求後才規劃 → 用 `/ce-brainstorm`

## 指令格式

- `/handoff` 或 `/handoff list` — 列出所有交接文件（含回覆狀態）
- `/handoff add <標題> [from] [to] [tag1,tag2]` — 新增一份交接
- `/handoff reply <原交接檔案 slug 或路徑> [from]` — 針對某份交接新增一則回覆
- `/handoff done <slug>` — 標記為已完成並歸檔

`from`／`to` 範例：`app`、`backend`、`frontend`、`devops`、`dba`。
本專案最常見方向為 `app` → `backend`（預設值）。

> **kunsu 情境約定**：若此 repo 隸屬某軍師（規劃協調中心），`to:` 應使用該軍師登記的**角色代碼**（與 `~/.claude/kunsu-registry.json` 的 `roles` 及軍師 CLAUDE.md 關聯專案表代碼欄字面一致），`/kunsu-inbox` 據此精確比對待接手交接。子 repo 回覆軍師的交接時，依 reply 步驟 1 的 kunsu 語境分支自軍師 repo 定位原交接檔；回覆落點一律為軍師的 `docs/handoffs/replies/`（軍師 repo 其餘目錄唯讀）。`/handoff` 作為通用交接原語不強制此約定，僅在 kunsu 語境下成立。

## 執行步驟

### add

1. **取得內容**：這是交接文件的重點，內文必須讓「上下文乾淨的接手方」讀得懂。
   把目前 session 已釐清的事實整理進以下段落（腳本會產生骨架，再用 Edit 補實）：
   - **背景 / 目標**：為什麼需要這次交接，接手方要達成什麼
   - **現況分析（已知事實）**：本 session 已查證的程式碼位置、資料結構、行為；
     引用具體 `檔案:行號`，不要只給結論
   - **需要你研究／決策的問題**：明確列點，讓接手方知道要回答什麼
   - **期望交付**：希望接手方回什麼（API 契約、可行性評估、估算數字…）
   - **相關檔案 / 連結**：關鍵檔案路徑、相關 plan／brainstorm／solution 連結

2. **建立檔案**（內文走 stdin）：

   ```bash
   echo "<整理後的內文>" | bash ~/.claude/skills/handoff/scripts/new-handoff.sh "<標題>" "<from>" "<to>" "<tag1,tag2>"
   ```

   - `from`／`to`／tags 皆可省略，預設 `app`／`backend`／`[handoff]`。
   - 腳本會自動定位專案根、建立 `docs/handoffs/`、以 `YYYY-MM-DD-<slug>.md` 命名
     （同日同名自動加 `-2`、`-3`…），並自動附上「回覆方式」段落（見下方範例），
     印出最終檔案路徑。

3. **補強內容**：現況分析與問題清單通常較長且有結構（清單、程式碼、表格），
   務必在建檔後用 Edit 補進實質內容，不要留空泛骨架——交接文件的價值全在細節。
   「回覆方式」段落是腳本自動產生的定型文字，不需要也不應該手動修改。

4. **回報**：附上建立的檔案路徑（`file_path` 形式方便點擊），一句話說明接手方
   可如何使用（例如「請在後台 session 開啟此檔研究，完成後執行
   `/handoff reply <slug>` 建立回覆檔案，不要編輯此檔案本體」）。
   **不要**主動 commit。

### reply

1. **定位原交接檔**：使用者已給 slug 或路徑就直接採用。若**未給**、或口語指向
   軍師（如「回覆軍師」「reply 給軍師」），走 **kunsu 語境分支**定位：

   1. 以 `git rev-parse --show-toplevel` 取當前 repo 根，作為鍵 Read
      `~/.claude/kunsu-registry.json`，查出本 repo 所屬軍師（條目的 `kunsu`
      欄位，絕對路徑）與本專案的**角色代碼**（`roles` 欄位）。未登記於任何
      軍師時，回報此事並請使用者直接提供原交接檔路徑，不要猜測。
   2. Glob `{軍師路徑}/docs/handoffs/*.md`（僅頂層，排除 `replies/`、
      `archive/`、`README.md`），逐一 Read frontmatter，篩出 `to:` 與本角色
      代碼**字面一致**且 `status` 非 `done` 的交接文件。
   3. 唯一命中 → 以該檔**絕對路徑**進入後續步驟；多筆命中 → 列出標題、建立
      日期讓使用者選（若均非使用者所指，依零筆分支的主動上報判斷處理）；
      零筆 → 回報「軍師中沒有待你回覆的交接」並停止——**不要**即興寫任何
      檔案進軍師 repo。若使用者意圖是**主動上報**（無對應交接的情報），屬
      `/kunsu-report` 上報管道的範疇；該 skill 尚未提供時，如實告知目前無
      正式上報管道，同樣不落檔、勿以孤兒回覆檔投遞。

2. **取得內容**：這是接手方要交付給發起方的結論，讓對方不必再往返確認就能知道
   結果。內文至少包含：目前狀態（進行中／完成）、對原問題清單的逐項回答、與原
   規劃的落差（如有）、其他備註。

3. **建立回覆檔案**（內文走 stdin）：

   ```bash
   echo "<回覆內文>" | bash ~/.claude/skills/handoff/scripts/new-handoff-reply.sh "<原交接檔案 slug 或路徑>" "<from>"
   ```

   - 腳本會自動定位原交接文件（可用完整檔名、相對／絕對路徑，或足以唯一比對的
     檔名片段），讀出其 `title`／`from`，推算回覆的 `to`（= 原交接文件的 `from`）；
     `from` 參數可省略，預設取原交接文件的 `to`。
   - 找不到、或找到多筆符合的原交接文件時，腳本會報錯並列出候選，需給更精確的
     片段或完整路徑重新執行。
   - 回覆一律落在**原交接檔所在 repo** 的 `docs/handoffs/replies/`：腳本從原檔
     位置推算 replies 目錄，與當前工作目錄無關。跨 repo 回覆（子 repo 回覆軍師）
     時傳軍師交接檔的**絕對路徑**即可，落點保證在軍師的回覆信箱。
   - 輸出檔名固定為 `{原交接檔所在 handoffs 目錄}/replies/{原交接檔名}-reply-{today}.md`；
     同日已存在同名回覆會自動加 `-2`、`-3`…（append-only，不覆寫前次回覆）。

4. **回報**：附上建立的回覆檔案路徑，提醒使用者**不要**回頭編輯交接文件本體。
   **不要**主動 commit。

### list

1. Glob `docs/handoffs/*.md`（排除 `docs/handoffs/replies/**`、
   `docs/handoffs/archive/**`、`README.md`），逐一 Read frontmatter
   （`status`/`from`/`to`/`created`）。
2. Glob `docs/handoffs/replies/*.md`，逐一 Read frontmatter（`in_reply_to`/
   `created`），依 `in_reply_to` 分組，統計每份交接文件的回覆數與最新回覆日期。
3. 再 Glob `docs/handoffs/archive/*.md` 與 `docs/handoffs/archive/replies/*.md`，
   同樣處理（已歸檔的交接與回覆）。
4. 以正體中文彙整成兩個表格：「進行中」與「已完成」，各欄位：標題（H1 或檔名）／
   狀態／方向（from → to）／建立日期／回覆狀態（例如「2 則回覆（最新
   2026-07-05）」／「待回覆」）。

### done

1. Read 指定的 `docs/handoffs/<slug>.md`（或使用者給的關鍵字，Glob 找出對應檔案）。
2. Glob `docs/handoffs/replies/*.md`，篩選 frontmatter `in_reply_to` 等於此交接
   文件檔名者；若有多份，依 `created` 取最新一份 Read 確認結論。
   - 若完全沒有回覆檔案，提醒使用者尚無接手方回覆，確認是否仍要標記完成（例如
     發起方自行確認已完成）。
3. 用 Edit 把交接文件本體 frontmatter `status` 改為 `done`（這是發起方對自己文件
   的生命週期狀態更新，不是接手方回填內容，不違反「本體不編輯」的規則）。
4. `git mv docs/handoffs/<slug>.md docs/handoffs/archive/<slug>.md`。
5. 若該交接文件在 `docs/handoffs/replies/` 有對應回覆檔案，一併 `git mv` 到
   `docs/handoffs/archive/replies/`，讓交接文件與其回覆的歸檔位置保持成對；沒有
   回覆檔案則略過此步。
6. 檢查是否有其他文件連結指向舊路徑（`grep -rl "docs/handoffs/<slug>.md" docs/`），
   逐一修正為 `docs/handoffs/archive/<slug>.md`。
7. 回報歸檔結果，**不要**主動 commit。

## 檔案格式範例

交接文件本體（`docs/handoffs/2026-07-02-書籤筆記-bulk-同步-api-契約.md`）：

````markdown
---
title: 書籤筆記 bulk 同步 API 契約
type: handoff
status: open
from: app
to: backend
created: 2026-07-02
tags: [handoff, sync, api]
---

# 書籤筆記 bulk 同步 API 契約

App 端目前逐本書呼叫同步 API，需後台提供 bulk 端點。請研究契約設計與傳輸量。

## 背景 / 目標

## 現況分析（已知事實）

## 需要你研究／決策的問題

## 期望交付

## 相關檔案 / 連結

---

## 回覆方式（請讀，不要編輯本檔案）

本檔案是定案快照，完成後**請勿在此檔案內回填任何內容**。請執行以下指令建立
回覆檔案：

    /handoff reply 2026-07-02-書籤筆記-bulk-同步-api-契約

或直接於下列路徑新增檔案（`{YYYY-MM-DD}` 為回覆當天日期；分階段回報多次時每次
建立新檔案，不要覆寫前一份回覆）：

    docs/handoffs/replies/2026-07-02-書籤筆記-bulk-同步-api-契約-reply-{YYYY-MM-DD}.md

新檔案請以下列 frontmatter 開頭：

```yaml
---
title: 書籤筆記 bulk 同步 API 契約 — 回覆
type: handoff-reply
from: backend
to: app
in_reply_to: 2026-07-02-書籤筆記-bulk-同步-api-契約.md
created: YYYY-MM-DD
status: submitted
---
```
````

對應的回覆檔案（`docs/handoffs/replies/2026-07-02-書籤筆記-bulk-同步-api-契約-reply-2026-07-05.md`）：

```markdown
---
title: 書籤筆記 bulk 同步 API 契約 — 回覆
type: handoff-reply
from: backend
to: app
in_reply_to: 2026-07-02-書籤筆記-bulk-同步-api-契約.md
created: 2026-07-05
status: submitted
---

# 書籤筆記 bulk 同步 API 契約 — 回覆

狀態：完成。API 契約與驗收標準如下……
```

## 注意

- **交接文件與回覆檔案皆為 append-only、永遠只有單一作者，兩者互不編輯**：
  交接文件本體只有發起方寫（建立後除 `done` 步驟更新 `status` 外不再改動），
  回覆檔案只有接手方寫（每次回覆是新檔案，不覆寫前次回覆）。這是避免多方共編
  同一檔案造成版本漂移的關鍵，不是形式而已。
- 日期一律以 `date +%F` 取系統實際日期，不要臆測。
- `status` 值：`open`（待接手，預設）／`in-progress`（接手方研究中）／`done`（已完成）。
- `from`／`to` 是交接文件的靈魂，務必填正確方向，Dataview 才能依角色過濾。
- 現況分析要引用具體 `檔案:行號` 與資料結構，接手方在**不同程式碼庫**時尤其重要。
- 內文不要再重複打 `# 標題`（腳本已自動產生一次）；若內文本身已包含「背景 /
  目標」等段落標題與內容，腳本不會再重複附加空白骨架。
- 多個議題請逐一建檔，不要把不同交接塞進同一個檔。
- `done` 是「搬到 archive + 改 status」，不是刪檔案。
