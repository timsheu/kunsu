---
title: "feat: 軍師沙盤新增 todo 列表顯示，`/todo` skill 併入 toolkit"
type: feat
status: completed
date: 2026-07-17
origin: docs/brainstorms/2026-07-17-dashboard-todo-list-requirements.md
---

# feat: 軍師沙盤新增 todo 列表顯示，`/todo` skill 併入 toolkit

## Summary

軍師沙盤（`skills/kunsu-dashboard/`）新增第四類彙整——唯讀讀取各軍師自己 `docs/todos/` 裡未歸檔的技術債，依 severity 排序、status 顯示比照既有 verify 欄位樣式，並在全域總覽與軍師分組摘要帶入未處理筆數。同一批工作把全域 `/todo` skill（`~/.claude/skills/todo/`）併入本 repo 版控，比照 ADR 003 handoff 併入先例，並新開一份 ADR candidate 記錄決策。

## Problem Frame

使用者想在跟 supervisor 討論時，一次性攤開所有軍師目前累積的技術債，不用逐一開軍師 session 跑 `/todo list`（ebook 軍師 26 筆未歸檔、ivm 軍師 15 筆）。`/todo` skill 目前只活在部署目錄 `~/.claude/skills/todo/`，沙盤若要長期解析它的檔案格式，這個跨 repo 隱性耦合需要一併收斂，否則格式演進時兩邊會漂移（見 origin: docs/brainstorms/2026-07-17-dashboard-todo-list-requirements.md）。

## Requirements

**`/todo` skill 併入**（origin R1-R3）

- R1. 將 `~/.claude/skills/todo/` 的原始碼併入本 repo `skills/todo/`，隨 kunsu toolkit 共同開發、版控，並經 `install.sh` 部署。
- R2. 母體文件（`CLAUDE.md` 專案結構）同步登記 `skills/todo/`。
- R3. 另開一份新 ADR candidate，記錄「`/todo` skill 併入 kunsu repo」的決策與理由。

**軍師 `docs/todos/` 掃描**（origin R4-R7）

- R4. 新增讀取軍師自己 repo `docs/todos/` 頂層（不含 `archive/`）的模組，解析各檔 frontmatter（status／date／source／severity），唯讀、讀取失敗不中斷整體渲染。
- R5. status 顯示比照 ADR 011 verify 欄位模式：`未處理` 視為已知值並標示樣式；`已解決`／`已封存` 若出現在活躍（未歸檔）目錄，歸入獨立的「看似完成但未歸檔」分類，不計入未處理總數；其餘自由字串（如 `open`、`已回覆待實機驗證`）原樣顯示一般標籤，計入未處理總數。
- R6. severity（high／medium／low）驅動排序，high 優先排前並以醒目樣式標示。
- R7. 讀取 `docs/todos/archive/` 的檔案數量（不展開內容），顯示於未處理清單旁作進度感。

**軍師沙盤渲染**（origin R8-R9）

- R8. 軍師卡片新增第四個分類區塊「待辦技術債」，比照既有新回覆／新申請／新上報的展開式清單樣式（`<details>`/`<summary>`、標題列帶最新修改時間）。
- R9. 全域總覽 chips 與軍師分組摘要列的 pending 計數，一併帶入未處理 todo 筆數。

---

## Key Technical Decisions

- **計數兩桶、顯示三層，兩者不可互相取代**（origin）：計數僅分兩桶——status ∈ {`已解決`,`已封存`} → 看似完成但未歸檔（`orphaned_done`），不計入未處理；其餘一切值（含未知自由字串）→ 未處理（`pending`）。但 `pending` 桶內部的顯示樣式仍分兩層：`未處理` 是已知值，套用獨立標示樣式；其餘自由字串（`open`、`已回覆待實機驗證` 等）原樣顯示為一般標籤，不做語意判斷。判斷只看 `已解決`／`已封存` 這兩個明確關閉值，不對其餘字串做語意猜測。
- **版本延續 0.1.1，零行為變更**（比照 ADR 003 handoff 併入慣例，見 docs/plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md）：純搬家，不改 `/todo` skill 任何觸發詞或子指令行為；未來若改動 skill 本身才在本 repo bump 版號。
- **標題解析改讀內文首個 H1**：`/todo` 產出的 frontmatter 刻意不含 `title` 欄位（避免與 Dataview `File` 欄位重複），與 handoff 的 `fm["title"]` 解析路徑不同。新模組讀取 frontmatter 結束後內文第一個以 `# ` 開頭的行作為標題；找不到 H1 時以檔名（去除 `.md`、連字號還原為空白）作為 fallback 標題。
- **新 CSS class 命名空間，不沿用 `badge`／`chip`**：既有測試以 `'<span class="badge' not in html` 斷言 verify 缺省時無標籤（`test_missing_verify_shows_no_badge`），全域總覽刻意用 `chip` 與 `badge` 區隔。待辦技術債的 severity／狀態標籤需採用第三個獨立 class 前綴，兩邊既有斷言都不能因此連帶失敗。
- **status／date 欄位一律 `str()` 轉型**：PyYAML `safe_load()` 會把未加引號的 `YYYY-MM-DD` 解析為 `datetime.date`、`已解決` 等中文字串不受影響但仍统一轉型以防禦性一致；沿用 `subrepo_status.py` 既有慣例。
- **todo pending 筆數與子專案 pending 聚合分開計算，但一律經建構子帶入**：`PendingAggregate`／`_aggregate_pending` 現有邏輯彙整的是「同一軍師底下所有子專案」的交接分類，粒度是子專案清單；todo pending 的粒度是「軍師自身一份」，兩者不可混進同一個彙整函式產生語意混淆——但 `PendingAggregate` 是 `@dataclass(frozen=True)`，建構後不可對其實例做屬性賦值（會拋出 `FrozenInstanceError`）。因此 `_aggregate_pending` 簽章加一個 `todo_pending: int` 參數，於函式內部連同其餘欄位一併傳入 `PendingAggregate(...)` 建構子，不在建構後才賦值。
- **每個軍師只呼叫一次 `get_todo_status`**：U6（渲染待辦技術債區塊）與 U7（計數彙整）共用同一次呼叫結果——`index()` 在軍師層迴圈對每個非 stale 軍師呼叫一次 `get_todo_status(kunsu_path)`，結果同時傳給 U6 的渲染函式與 U7 的 `_aggregate_pending(..., todo_pending=len(結果.pending))`，避免重複讀取 `docs/todos/` 造成的雙倍 I/O 與潛在資料不一致（比照既有 `scan = scan_kunsu(kunsu_path)` 單次呼叫後多處引用的既定寫法）。

---

## Implementation Units

### U1. 匯入 `/todo` skill 原始碼

- **Goal:** `skills/todo/` 與部署目錄 `~/.claude/skills/todo/` 現行 v0.1.1 逐字一致，本 repo 成為開發母體。
- **Requirements:** R1
- **Dependencies:** 無
- **Files:** `skills/todo/SKILL.md`、`skills/todo/scripts/new-todo.sh`
- **Approach:** 自 `~/.claude/skills/todo/` 整目錄複製入 repo，保留執行權限位，不做任何內容修改（比照 U1 handoff 匯入模式）。
- **Test scenarios:**
  - 匯入後 `diff -r` repo 目錄 vs 部署目錄：零差異。
  - `new-todo.sh` 執行權限位保留（`test -x`）。
- **Verification:** diff 零差異且權限正確。

### U2. install.sh 納入 todo 並重新部署驗證

- **Goal:** 新增 skill 隨既有一鍵部署機制生效，行為冪等。
- **Requirements:** R1
- **Dependencies:** U1
- **Files:** `install.sh`
- **Approach:** `SKILLS` 陣列（目前為手動硬編碼清單，不會自動偵測新目錄）加入 `todo`；末行 echo 訊息補上 `/todo`。既有覆寫提示、`--link`、同源防呆邏輯自動涵蓋。重新部署後對 `/todo` 做 smoke 驗證。
- **Test scenarios:**
  - 部署後 `~/.claude/skills/todo` 與 repo 版 diff 零差異。
  - install.sh 末行 echo 含 `/todo`。
  - `--target` 隔離目錄測試：`todo` 目錄部署成功。
  - Smoke：於暫存 git repo（含 `docs/todos/`）以部署後的 `new-todo.sh` 建一筆待辦，frontmatter 與檔名慣例與 v0.1.1 既有行為一致。
- **Verification:** smoke 全過，與整合前行為無差異。

### U3. ADR candidate 記錄 `/todo` skill 併入決策

- **Goal:** 決策依據可追溯，比照 ADR 003 先例。
- **Requirements:** R3
- **Dependencies:** 無（可與 U1 平行）
- **Files:** `docs/adr/2026-07-17-adr-candidate-013-integrate-todo-into-toolkit.md`
- **Approach:** 記錄 Context（`/todo` 目前只活在部署目錄、沙盤將長期解析其檔案格式產生的耦合缺口、對 Invariant 3 開發部署分離範圍的擴張）、Decision（併入 `skills/todo/`；命名維持 `todo` 不加前綴，比照 handoff 通用原語命名判斷；版本延續 0.1.1）、Consequences（格式異動可同 repo 同步修改、`/todo` 不再是純外部依賴）、Alternatives（維持外部依賴、僅在沙盤端加註解說明耦合——兩者皆無法根治 drift 風險，予以否決）。
- **Test scenarios:** Test expectation: none — 純文件。
- **Verification:** ADR 涵蓋決策與否決理由，格式比照既有 `docs/adr/2026-07-06-adr-003-integrate-handoff-into-toolkit.md`。

### U4. 母體文件同步

- **Goal:** `CLAUDE.md` 專案結構反映新併入的 skill。
- **Requirements:** R2
- **Dependencies:** U1、U2
- **Files:** `CLAUDE.md`
- **Approach:** 專案結構樹加入 `skills/todo/` 條目（含 `SKILL.md`、`scripts/new-todo.sh` 說明），比照既有 `skills/handoff/` 條目的寫法。
- **Test scenarios:** Test expectation: none — 純文件同步。
- **Verification:** grep 確認 `skills/todo/` 出現在專案結構樹。

### U5. 新增 `app/todo_status.py` 掃描與分類模組

- **Goal:** 唯讀解析軍師 `docs/todos/` 頂層 frontmatter，分類未處理／看似完成未歸檔，依 severity 排序，計數 archive。
- **Requirements:** R4、R5、R6、R7
- **Dependencies:** 無（不依賴 U1-U4，可平行進行；資料來源是軍師 repo 既有的 `docs/todos/`，與 `/todo` skill 併入與否無關）
- **Files:** `skills/kunsu-dashboard/app/todo_status.py`、`skills/kunsu-dashboard/tests/test_todo_status.py`
- **Approach:** 比照 `skills/kunsu-dashboard/app/subrepo_status.py` 的結構與既定慣例（`_parse_frontmatter` 的 YAML 安全解析寫法、`@dataclass(frozen=True)`、讀取失敗不拋例外）：
  - `TodoInfo` dataclass：`filename`、`title`、`status`、`date`、`source`、`severity`、`mtime`、`raw_content`。
  - `TodoStatusResult` dataclass：`pending: list[TodoInfo]`、`orphaned_done: list[TodoInfo]`、`archive_count: int = 0`、`errors: list[ErrorItem]`（沿用或仿造 `subrepo_status.ErrorItem` 形狀）。
  - `get_todo_status(kunsu_path) -> TodoStatusResult`：`docs/todos/` 不存在時回傳空結果，不報錯（比照 `handoffs_dir` 不存在的既有處理）；`Path.glob("*.md")` 讀頂層（非遞迴，天然排除 `archive/`）；`status` 欄位缺失記入 `errors` 並跳過分類，`date`／`source`／`severity` 缺失不視為錯誤；標題解析見 Key Technical Decisions；`archive_count` 為 `docs/todos/archive/*.md` 的檔案數，不讀取其內容。
  - 排序鍵：severity（high=0、medium=1、low=2、缺省或未知值=3）升冪，同 severity 依 mtime 降冪。
- **Test scenarios:**
  - Happy path：建立 high／medium／low 三筆 `status: 未處理`，驗證 `pending` 依 severity 排序。
  - Happy path：`status: open`（自由字串）——歸入 `pending`。
  - **Covers AE1.** `status: 已解決` 且檔案在頂層未歸檔——歸入 `orphaned_done`，不進 `pending`。
  - **Covers AE2.** `status: open` 原樣顯示、計入 `pending`（驗證分類與顯示值兩者皆正確）。
  - Edge：無 `docs/todos/` 目錄——回傳空結果。
  - Edge：`docs/todos/` 存在但為空目錄——`pending`／`orphaned_done` 皆空，`archive_count` 為 0。
  - Edge：frontmatter 缺 `status` 欄位——記入 `errors`，不進 `pending`／`orphaned_done`。
  - Edge：內文無 H1——`title` fallback 為檔名還原字串。
  - Edge：`date` 欄位未加引號（YAML 解析為 `datetime.date`）——`str()` 轉型後為字串。
  - Edge：中文（非 ASCII）檔名與標題——Python `pathlib.glob` 正常讀取。
  - Error path：讀取中途失敗（`OSError`/`UnicodeDecodeError`）——記入 `errors`，不中斷其餘檔案處理。
  - `archive_count`：`docs/todos/archive/` 內 2 筆 `.md`——`archive_count == 2`，不展開讀取其內容。
- **Verification:** `pytest skills/kunsu-dashboard/tests/test_todo_status.py` 全數通過。

### U6. `main.py` 渲染「待辦技術債」區塊

- **Goal:** 軍師卡片新增第四個分類區塊，比照既有三個信箱分類的展開式清單樣式。
- **Requirements:** R8
- **Dependencies:** U5
- **Files:** `skills/kunsu-dashboard/app/main.py`、`skills/kunsu-dashboard/tests/test_main.py`
- **Approach:** 新增 `_html_todo_section(kunsu_path, result: TodoStatusResult) -> str`，接受呼叫端已取得的 `TodoStatusResult`（不自行呼叫 `get_todo_status`，見 Key Technical Decisions 的單次呼叫共用設計）；`index()` 路由在非 stale 軍師的迴圈內呼叫一次 `get_todo_status(kunsu_path)`，結果同時傳給本函式與 U7 的計數邏輯。`is_stale` 軍師比照 `_html_subrepo_kunsu_unreachable` 的既有防呆模式，不呼叫 `get_todo_status`。展開式清單沿用 `_html_detail`/`_html_summary_line` 既有寫法；`pending` 桶內 `未處理`（已知值）套用獨立標示樣式、其餘自由字串套用一般標籤樣式，兩者與 `orphaned_done`（看似完成但未歸檔）三層視覺區分，一律使用新 CSS class 前綴（見 Key Technical Decisions，不得用 `badge`/`chip` 字面）；`archive_count` 以純文字附註呈現、不展開；`pending`/`orphaned_done` 皆空時顯示既有 `<p class="empty">` 風格的「無待辦」提示。
- **Test scenarios:**
  - Happy path：傳入含 `pending` 與 `orphaned_done` 的 `TodoStatusResult`，驗證 HTML 含「待辦技術債」標題與正確筆數。
  - **Covers R5.** 顯示樣式三層區分：`status: 未處理` 與 `status: open` 兩筆分別渲染時，兩者的 class 不同（前者為已知值樣式、後者為一般標籤），且皆與 `orphaned_done` 筆目的 class 不同。
  - Edge：空結果——顯示「無待辦」，不報錯。
  - **Covers AE3.** severity 排序與標色：high 筆目排最前並帶有醒目樣式 class。
  - **Covers AE4.** 軍師 repo 沒有 `docs/todos/` 目錄（`get_todo_status` 回傳空結果）——顯示空狀態，不中斷整頁渲染。
  - Class 衝突防護：明確斷言新標籤的 class 名稱不是 `badge` 或 `chip`（維持既有 `test_missing_verify_shows_no_badge` 與總覽列斷言不受影響）。
  - Stale 軍師：`is_stale` 時不呼叫 `get_todo_status`（`monkeypatch.setattr("app.main.get_todo_status", _fail_if_called)` 風格驗證，比照既有 `get_subrepo_status` 防呆測試）。
- **Verification:** `pytest skills/kunsu-dashboard/tests/test_main.py` 全數通過；既有測試（含 `badge` 負面斷言）維持綠燈。

### U7. 全域總覽與軍師分組摘要整合 todo 未處理數

- **Goal:** 未處理 todo 筆數一併反映在頁首全域總覽與各軍師分組摘要列。
- **Requirements:** R9
- **Dependencies:** U5、U6
- **Files:** `skills/kunsu-dashboard/app/main.py`、`skills/kunsu-dashboard/tests/test_main.py`
- **Approach:** `PendingAggregate` 新增欄位 `todo_pending: int = 0`；`_aggregate_pending` 簽章加一個 `todo_pending: int` 參數，於函式內部連同其餘欄位一併傳入 `PendingAggregate(...)` 建構子（見 Key Technical Decisions，frozen dataclass 不可建構後賦值）。`index()` 路由在軍師層迴圈（U6 已呼叫的 `get_todo_status(kunsu_path)` 結果，見 U6 Approach）以 `_aggregate_pending(sub_results, todo_pending=len(todo_result.pending))` 取得該軍師的 `pending`。`_pending_suffix` 補一項「待辦 N」（非零才顯示）。全域總覽以獨立變數在軍師迴圈中累加各軍師 `todo_result.pending` 筆數，傳入 `_html_overview` 新增引數，比照既有全零不渲染規則。
- **Test scenarios:**
  - 軍師分組摘要列含「待辦 N」（N 為該軍師未處理 todo 筆數，非零才出現）。
  - 全域總覽 chips 新增「待辦 N」，N 為所有軍師加總；全零時不出現此 chip。
  - 多軍師加總：兩軍師分別 3 筆與 5 筆未處理 todo，全域總覽顯示 8。
  - 零 todo：待辦 chip 不出現，不影響既有其他 chips 渲染。
- **Verification:** `pytest skills/kunsu-dashboard/tests/test_main.py` 全數通過；`_html_overview`/`_pending_suffix` 既有測試維持綠燈。

---

## Scope Boundaries

### Deferred to Follow-Up Work

- 把既有沙盤陷阱（registry 雙重讀取 TOCTOU 競態、tripwire 於無明細行時靜默遺失、stale 軍師誤報「無待處理交接文件」，三者皆已修復但只記在 CLAUDE.md 開發狀態）沉澱為 `docs/solutions/` 學習文件——與本次工作無關的既有技術債，不在本次範圍。
- `/todo` skill 觸發詞若未來需要調整，依既有 handoff done 收尾閉環學習的「帶語境觸發詞」原則處理——本次併入是零行為變更的純搬家，未發現觸發詞缺陷，不觸發此工作。

### Outside this product's identity

- 網頁互動標記 todo 為完成／封存——沙盤維持唯讀（origin Key Decision）。
- 子專案自己 repo 的 `docs/todos/`——目前無實例，不掃描。
- kunsu 自己（工具母體）的 `docs/todos/`——不在任何 registry 條目的軍師欄位中，沙盤現有架構掃不到。
- `/todo` skill 既有慣例（status 三值定義、`done`／`rm` 流程本身）的行為改動——併入是搬遷版控位置，不重新設計 skill 行為。

---

## Risks & Dependencies

- **install.sh `SKILLS` 陣列為手動硬編碼清單**：遺漏加入 `todo` 則 skill 不會部署，且不會有任何錯誤提示——U2 的部署驗證測試直接覆蓋此風險。
- **標題解析是新設計面**：`/todo` frontmatter 無 `title` 欄位，與現有 handoff 解析路徑不同，H1 缺失的 fallback 邏輯需要獨立測試覆蓋（U5 已列）。
- **CSS class 與既有 pytest 斷言衝突**：新增的 severity／狀態標籤若誤用 `badge` 或 `chip` 字面，會讓 `test_missing_verify_shows_no_badge` 等既有斷言失敗——U6 明確列為獨立測試項。
- **`PendingAggregate` 語意混淆風險**：todo pending（軍師粒度）與子專案 pending（跨子專案聚合）若共用同一計算路徑會產生錯誤加總——U7 的 Approach 已明訂分開計算、經 `_aggregate_pending` 建構子參數一併帶入（`PendingAggregate` 為 frozen dataclass，不可建構後賦值）。

---

## Sources & Research

- `skills/kunsu-dashboard/app/subrepo_status.py`、`app/kunsu_scan.py`、`app/main.py`、`app/registry.py` 及對應測試檔——frontmatter 解析、`@dataclass(frozen=True)`、HTML 渲染函式命名（`_html_*`/`_render_*`）、CSS class 命名慣例、測試 fixture 寫法（`conftest.py` 僅供 `sys.path` 設定；`tmp_path`／`monkeypatch.setattr("app.main.xxx", ...)` 既定模式）。
- `docs/adr/2026-07-06-adr-003-integrate-handoff-into-toolkit.md` 與 `docs/plans/2026-07-06-002-feat-integrate-handoff-skill-plan.md`——`/todo` skill 併入的直接先例範本（U1-U4 結構比照此計畫的 U1-U4）。
- `docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md`——status 顯示樣式（建議代碼＋開放值域＋標籤樣式）的直接先例。
- `~/.claude/skills/todo/SKILL.md`、`~/.claude/skills/todo/scripts/new-todo.sh`——`/todo` frontmatter 契約（status／date／source／severity，無 `title` 欄位）、slug 產生規則、`done`/`rm` 的 `git mv` 搬移邏輯。
- `install.sh`——`SKILLS` 陣列為手動硬編碼清單，非萬用字元自動偵測。
- `docs/solutions/best-practices/git-porcelain-scan-script-pitfalls.md`——shell 腳本掃描陷阱；本次以純 Python `pathlib.glob` 讀取不直接適用，但 `archive/` 子目錄的非遞迴排除邏輯沿用既有 `handoffs_dir.glob("*.md")` 慣例。
- `docs/solutions/workflow-issues/handoff-done-closure-gap.md`——定型文字多副本同步紀律；`/todo` 併入若未來調整觸發詞時應比照套用。
