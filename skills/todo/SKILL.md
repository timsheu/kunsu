---
name: todo
version: 0.2.0
description: |
  管理專案的 CE 副作用 TODO 清單：一檔一項技術債，存放於當前專案的 docs/todos/，
  含 Dataview 友善 frontmatter（status/date/source/severity）。用於記錄
  ce-work/ce-plan/code-review/LeakCanary 等過程中發現、但明確排除於當前
  範圍之外的殘留問題，供未來評估或修復。
  Use when asked to「記一個 todo」「新增待辦」「列出待辦」「標記待辦完成」
  「封存這個待辦」「add todo」「list todos」「/todo」.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# todo — CE 副作用 TODO 管理

把 ce-work/ce-plan/code-review 等過程中發現、但明確排除於當前範圍之外的技術債，
記成一個獨立 md 檔，放進當前專案的 `docs/todos/`。

```
docs/todos/  →（解決後）status 改 已解決，git mv 到 docs/todos/archive/
```

`docs/todos/` 屬參考層（非 CE plugin 管理），與 `docs/plans`、`docs/brainstorms`
等 plugin 原生路徑無關，不取代任何 CE 指令行為。

## 何時使用

- 使用者說「記一個 todo」「新增待辦」「/todo add ...」
- ce-work/ce-plan/code-review 過程中發現一個明確不在本次範圍內、但值得記錄的問題
- 使用者要查詢待辦現況（`/todo list`）、標記完成（`/todo done`）或封存不處理（`/todo rm`）

不要用於：已經要立刻處理的問題 → 直接修，不需要先記 todo 再處理。

## 指令格式

- `/todo` 或 `/todo list` — 列出所有待辦
- `/todo add <標題> [來源] [嚴重度]` — 新增一筆待辦
- `/todo done <slug>` — 標記為已解決並歸檔
- `/todo rm <slug>` — 標記為已封存（不處理／非 bug）並歸檔，**不刪除檔案**

來源範例：`manual`（預設）、`ce-work`、`ce-plan`、`ce-compound`、`code-review`
嚴重度：`low`（預設）／`medium`／`high`

## 執行步驟

### add

1. **取得內容**：標題取一句精煉的正體中文描述（不含標點符號結尾）；若使用者當下
   已提供現象/根因/相關檔案（常見於 code review、LeakCanary 報告等場景），整理成
   內文一併帶入。完全沒有內容時用 AskUserQuestion 或直接詢問後再繼續。

2. **建立檔案**（內文走 stdin）：

   ```bash
   echo "<整理後的內文>" | bash ~/.claude/skills/todo/scripts/new-todo.sh "<標題>" "<來源>" "<嚴重度>"
   ```

   來源、嚴重度可省略，預設 `manual`／`low`。腳本會自動定位專案根、建立
   `docs/todos/`、以標題轉 slug 決定檔名（**不加日期前綴**，撞名會直接報錯，
   請換更具體的標題），並印出最終檔案路徑。

3. **補強內容**：若現象/根因/相關檔案的細節較長或有結構，用 Edit 補進檔案的
   「相關檔案」「待辦方向」段落，不要留空泛骨架。

4. **回報**：附上建立的檔案路徑，一句話帶出可用 `/todo list` 查看現況。**不要**
   主動 commit。

### list

1. Glob `docs/todos/*.md`（排除 `docs/todos/archive/**`、`README.md`），逐一 Read
   frontmatter（`status`/`date`/`source`/`severity`）。
2. 再 Glob `docs/todos/archive/*.md`，同樣讀取 frontmatter。
3. 以正體中文彙整成兩個表格輸出：「未執行」與「已完成／已封存」，各欄位：
   標題（H1 或檔名）／狀態／日期／來源／嚴重度。

### done

1. Read 指定的 `docs/todos/<slug>.md`（或使用者給的檔名關鍵字，Glob 找出對應檔案）。
2. **殘項清點後再 Edit**：先掃描檔內「下一步」「待辦」等段落中未註記完成的
   子項（無可辨識的子項段落時靜默通過）；有殘項時逐項回報，由使用者決定——
   一併視為已解決（續行收尾）／轉出為新 todo（使用者裁決即授權、由 session
   代建，新檔內文首行註明 `轉出自 docs/todos/archive/<原slug>.md`，填歸檔後
   路徑）／保留（中止本次 done，維持原 status 不動）。續行時用 Edit 只改
   frontmatter 的 `status: 未處理` → `status: 已解決`（不動內文其他部分）。
3. 詢問或從對話取得解決依據（commit hash、solution 文件連結），用 Edit 補一行
   在標題下方，例如：`**解決依據**：commit \`abc1234\`，見 docs/solutions/xxx.md`。
4. **歸檔前置檢查**：先 `mkdir -p docs/todos/archive/`（目錄不存在時 `git mv`
   會失敗）；`git status --porcelain docs/todos/<slug>.md` 狀態為
   `??`（untracked）者先 `git add`（untracked 檔直接 `git mv` 會以
   `not under version control` 失敗），再
   `git mv docs/todos/<slug>.md docs/todos/archive/<slug>.md`。
5. 檢查是否有其他文件連結指向舊路徑（`grep -Frl "docs/todos/<slug>.md" docs/`，
   `-F` 固定字串比對避免 `.` 誤中），逐一修正為 `docs/todos/archive/<slug>.md`。
6. 回報歸檔結果，**不要**主動 commit。

### rm

語意是「確認不需處理／非 bug，封存但不刪除」，不是刪檔案。rm **不執行**殘項
清點——封存語意為整檔判定不處理，檔內殘項一併封存：

1. Read 指定檔案，用 Edit 把 frontmatter `status` 改成 `已封存`，並在內文補一行
   結案原因（例如「三項假設皆不成立，logcat 實測排除」）。
2. 同 done 步驟 4 先做歸檔前置檢查（`mkdir -p`＋untracked），再 `git mv` 到
   `docs/todos/archive/`，並同 done 步驟 5 修正跨檔連結。
3. 回報結果。若使用者明確要求刪除誤建立的檔案（不是要封存），才用一般 Bash
   `rm` 處理，並在動手前跟使用者確認一次。

## 檔案格式範例

```markdown
---
status: 未處理
date: 2026-07-01
source: code-review
severity: medium
---

# 書城快取／網路競態

在 fix/xxx 的 code review 中發現，與本次修復範圍無關的殘留競態。

## 相關檔案

- `app/src/main/java/.../MallFragment.java`

## 待辦方向

- 加入 generation counter 或訂閱互斥
```

## 注意

- 日期一律以 `date +%F` 取系統實際日期，不要臆測。
- frontmatter 刻意不加 `title` 欄位——名稱交給檔名 slug ＋ 內文 H1，Dataview 用
  內建的 `File` 欄位顯示即可；避免製造第二個標題語意欄位造成重複（教訓見
  `docs/brainstorms/README.md` 記錄的 `title`/`topic` 混用事故）。
- 內文不要再重複打 `# 標題`（腳本已自動產生一次）；若內文本身已包含「相關檔案」
  ／「待辦方向」段落標題與內容，腳本不會再重複附加空白骨架，避免產生重複標題
  或多餘空段落。
- 多筆待辦請逐一建檔，不要塞進同一個檔。
- 若某筆 todo 已升級為交接文件處理，`/handoff done`（v0.8.0 起）收尾時會以雙向
  檔名比對找出它，經使用者確認後代執行本 skill 的 done 收尾（status、解決依據、
  歸檔，v0.12.0 起含殘項清點），不需事後再跑 `/todo done`；於該查核中略過或
  取消的 todo 不在此列，仍由本 skill 自行收尾。
- `done`／`rm` 都是「搬到 archive + 改 status」，不是刪檔案；只有使用者明確要求
  刪除誤建檔案時才用一般 `rm`。
