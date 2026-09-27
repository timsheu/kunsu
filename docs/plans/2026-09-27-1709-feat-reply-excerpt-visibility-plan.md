---
title: 久懸交接帶最新回覆摘錄 - Plan
type: feat
date: 2026-09-27
topic: reply-excerpt-visibility
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# 久懸交接帶最新回覆摘錄 - Plan

## Goal Capsule

- **Objective**：使用者從沙盤卡片、接手方從自己的 session 啟動摘要，不必點開任何回覆檔就能看出一份久懸交接「內容物做到哪了」——使用者不再把「還沒收尾」讀成「還沒做」而要求軍師對已完成工作重複派發。軍師 session 自身的抵達通道不在本計畫，見 Scope Boundaries。
- **Means**：在子專案分類資料層一次讀取回覆時順手萃取最新回覆的首句，兩個既有計算載體（軍師沙盤卡片、SessionStart hook 子專案摘要）各自在自己的顯示格式裡附上（KTD1、KTD2）。
- **Authority hierarchy**：Product Contract 的 R-ID 決定產品行為；Planning Contract 的 KTD 決定實作機制；單元不得改寫兩者。
- **Stop conditions**：實作時若發現萃取必須第二次讀檔才能達成，停下回報（KTD1 前提失效）；若既有沙盤或 hook 測試因新增欄位而需要修改既有斷言的語意（非只補 body 參數），停下回報。
- **Execution profile**：單一 repo、純 python3 stdlib、無新依賴、無新狀態檔、無新環境變數；分類邏輯、handoff 協議、`status`／`verify` 值域、軍師範本、UserPromptSubmit hook 一律零改動，免三 live 軍師遷移。
- **Tail ownership**：install.sh 重佈署與 commit 由使用者明確要求時執行。
- **Open blockers**：無。

**Product Contract preservation**：本計畫由 idea 檔直接規劃（`docs/ideas/2026-09-01-久懸已回覆待確認件於沙盤與inbox摘要列帶回覆結論首句.md`），無上游 brainstorm。idea 原提「停留 ≥5 天才顯示」與「只做已回覆待確認」兩點經三 live 軍師實證後由使用者改為「一律顯示」與「已回覆待確認＋部分完成」，見 Key Decisions。

---

## Product Contract

### Summary

軍師沙盤「已回覆待確認」與「部分完成」每筆卡片，在 `<details>` 收合狀態下常態可見處多一行最新回覆的首句摘錄；SessionStart hook 子專案摘要的同兩分類每行尾端附同一句。摘錄是回覆原文的唯讀擷取，不做分類依據、不進任何比對邏輯。

### Problem Frame

2026-09-01 ebook 軍師差點對 iOS WebSocket 七事件重複派發「補消費端」交接：正確答案（實作全完成、僅三項驗收需真推播）在自家回覆信箱 2026-08-24 的回覆裡躺了 8 天。該交接因驗收外部阻塞久懸「已回覆待確認」，卡片只傳達「已等 8 天」，不傳達「內容物已完成」；session 遂以另一子專案回覆的隻字片語外推 iOS 現況。同軍師 2026-08-31 已真實發生重複派發（devicename 兩份重複交接）。

結構原因：長懸交接的內容資訊被容器的開閉狀態遮蔽。懸置愈久，回覆內文離 session 工作記憶愈遠，「還沒收尾」愈容易被讀成「還沒做」。系統後果是對已完成工作重複派發——子專案耗一輪回覆指出重複，或照做造成雙頭實作。

三 live 軍師 2026-09-27 實況：「已回覆待確認」22 筆中 21 筆停留 ≥5 天；同型「實作已完成、僅剩驗收」的回覆約半數落在接手方自標 `partial` 的「部分完成」分類（ebook 08-29 WebSocket 握手回覆即一例）。既有沙盤卡片只對「已回覆待確認」帶下一步提示與停留天數，「部分完成」卡片沒有任何常態可見資訊。

### Key Decisions

- **兩個計算載體同步：軍師沙盤卡片與 SessionStart hook 子專案摘要** (session-settled: user-approved — chosen over 只做沙盤、以及再加 kunsu-inbox SKILL 4a-5 手動輸出表格: 兩者都是既有計算載體，成本是資料層已算好的欄位各印一次；沙盤的讀者是使用者、hook 子專案摘要的讀者是接手方 session，兩者都不是會重複派發的軍師 session——軍師側通道另案；4a-5 表格由模型手工渲染、非計算載體，加欄位只增副本不增觸及率). Governs R1, R2, R3.
- **「已回覆待確認」與「部分完成」兩分類都附摘錄** (session-settled: user-directed — chosen over 只做已回覆待確認（idea 原範圍）: 三 live 軍師實證動機同型案例約半數在部分完成；資料層欄位對兩分類免費可得，只差渲染). Governs R2, R3.
- **一律顯示，不設停留天數門檻** (session-settled: user-directed — chosen over 停留 ≥5 天才顯示（idea 暫定）: 實證 22 筆中 21 筆已 ≥5 天，門檻實質不過濾，卻要在 hook 端新增日期邏輯並與沙盤共用天數函式；「已等 N 天」既有標籤照舊，久懸由使用者自判). Governs R2, R3.
- **不在 UserPromptSubmit hook 加內容** (session-settled: user-approved — chosen over 三載體一起加: 該 hook 每句提問執行、只掃未 commit 新件，與「久懸件內容可見」是不同時點與不同資料來源). Governs R7.
- **摘錄是回覆原文擷取，不是軍師斷言**。顯示文案與文件一律稱「回覆摘錄」，不稱「結論」；依斷言層級紀律，這句話的層級是「依 X 記載」而非「已查證」。Governs R4。

### Requirements

**資料層**

- R1. 子專案分類結果的每筆交接帶一個選填欄位：最新回覆檔（依既有 `(日期, 序號)` 數值排序取最新）的首句摘錄；無回覆、回覆內文無可用文字段時為空值；回覆檔讀取失敗時依 R6 自索引消失，摘錄與 status、日期同源改取其餘可讀回覆中最新的一份，且無其餘可讀回覆時才為空值。
- R4. 摘錄為回覆原文的唯讀擷取：跳過 frontmatter、任何層級標題行、空行、程式碼圍欄內容、表格列與 HTML 標籤行；連續非空行先併為一段再取首段；去除清單標記、反引號、連結語法（保留連結文字）；粗體與斜體只去除成對且緊貼文字兩端、外側不緊鄰英數字的標記（`**x**`、`*x*`、`_x_`），識別字內的單一底線（如 `client_ref`、`_lang=zh-TW`）原樣保留；以第一個「。」「！」「？」截斷，超過 60 字元（以字元計，非 byte）截斷並加「…」。
- R5. 摘錄不參與任何分類、排序、tripwire 或比對邏輯；分類分支與既有欄位語意零改動。

**軍師沙盤**

- R2. 「已回覆待確認」與「部分完成」每筆卡片在 `<details>` 之外常態可見處顯示摘錄；摘錄為空值時該行不渲染；「未接手」卡片不顯示。摘錄經 HTML escape。

**SessionStart hook**

- R3. 子專案模式「已回覆待確認」與「部分完成」每行尾端附摘錄；摘錄為空值時零後綴（不留空括號或分隔符）；「未接手」行不變；既有每分類 5 筆上限與「另有 N 筆」不變。

**邊界**

- R6. 回覆檔讀取失敗（`OSError`／`UnicodeDecodeError`）維持既有行為：該回覆自索引消失、交接分類依其餘回覆推導；不新增第二種降級分支。
- R7. UserPromptSubmit hook（`prompt_inbox_hook.py`）、kunsu-inbox SKILL 4a-5 手動輸出表格、軍師範本、handoff 協議零改動。

### Acceptance Examples

- AE1. **已回覆待確認卡片帶摘錄**
  - **Covers:** R1, R2, R4
  - **Given** 一份交接的最新回覆 `status: submitted`，內文為範本回顯 H1「# 標題 — 回覆」、空行、「## 狀態」、空行、「七個端點全部實作並接線完成，`xcodebuild test` 全套通過（單元測試 141/141）。」硬換行接「已 commit。」
  - **When** 沙盤渲染該子專案
  - **Then** 卡片 `</details>` 之後出現摘錄行，內容為「七個端點全部實作並接線完成，xcodebuild test 全套通過（單元測試 141/141）。」；既有下一步提示與「已等 N 天」照舊。
- AE2. **部分完成卡片帶摘錄**
  - **Covers:** R2
  - **Given** 最新回覆 `status: partial`，首段「程式改動已完成、Debug 建置與測試套件皆通過。」
  - **When** 沙盤渲染
  - **Then** 該卡片 `</details>` 之後出現摘錄行；不出現下一步提示與停留天數（既有分工不變）。
- AE3. **未接手卡片與無回覆件不顯示**
  - **Covers:** R2, R3
  - **Given** 一份交接無任何回覆
  - **Then** 沙盤卡片與 hook 行皆無摘錄元素；hook 行字面與現行完全相同。
- AE4. **硬換行先併段再切句**
  - **Covers:** R4
  - **Given** 首段第一行「承接同日的第一份回覆（-reply-2026-08-24.md），本份回報依」硬換行接「裁示完成的三項修正。」
  - **Then** 摘錄為「承接同日的第一份回覆（-reply-2026-08-24.md），本份回報依裁示完成的三項修正。」，不是半句。
- AE5. **H1 即結論時仍取內文首段**
  - **Covers:** R4
  - **Given** H1「# 回覆（第三階段）：正式切換完成，複驗全數通過」，其後首段「`endlesslights.link` 已完成正式環境切換：前門連正式後台。」
  - **Then** 摘錄取內文首段（去反引號），不取 H1。
- AE6. **hook 行格式**
  - **Covers:** R3
  - **Given** 已回覆待確認一筆，摘錄「狀態：完成。」
  - **Then** 該行為既有格式（檔名、括號內 status 與日期與 verify、依賴後綴）之後接摘錄；既有子字串斷言「`<檔名>（submitted <日期>）`」仍命中。
- AE7. **HTML 注入**
  - **Covers:** R2
  - **Given** 回覆首段含「<b>完成</b> & 通過」
  - **Then** 沙盤輸出含 `&lt;b&gt;` 與 `&amp;`，不含原始標籤。
- AE8. **60 字元截斷**
  - **Covers:** R4
  - **Given** 首句超過 60 個字元且無句號
  - **Then** 摘錄為前 60 字元加「…」，CJK 以字元計。
- AE9. **空殼回覆**
  - **Covers:** R4
  - **Given** 內文僅範本預設「_（待補充）_」
  - **Then** 摘錄為「（待補充）」（誠實反映回覆是空殼），不視為空值。
- AE10. **最新回覆為補件時取補件首句**
  - **Covers:** R1
  - **Given** 同一交接兩份回覆，最新一份首段「更正前一份回覆第 2 點：…」
  - **Then** 摘錄取最新一份的首句，不回退前一份。
- AE11. **最新回覆讀取失敗、較舊回覆可讀**
  - **Covers:** R1, R6
  - **Given** 同一交接兩份回覆，最新一份 `UnicodeDecodeError`，較舊一份 `status: submitted` 首段「狀態：完成。」
  - **Then** 分類、status、日期、verify 與摘錄全部來自較舊那份（既有降級行為），摘錄為「狀態：完成。」；不出現空摘錄。

### Success Criteria

- 對三 live 軍師啟動沙盤，「已回覆待確認」與「部分完成」每筆卡片在收合狀態下可讀到一句回覆原文；以 2026-09-01 iOS WebSocket 案例（若尚在頂層）或同型 partial 件對照，摘錄提供「實作做到哪」的判斷線索，降低使用者要求軍師對已完成工作重複派發的機率；摘錄是原文擷取，補件型、粗體鍵值型與被截斷的首句不保證足以判定完成（見 Deferred to Follow-Up Work）。
- 沙盤 166 項與 kunsu-inbox 78 項既有 pytest 除補 fixture 參數外零語意改動照常通過；consistency-check 34 項 PASS。

### Scope Boundaries

- 分類邏輯（`subrepo_status.py` 4a-3 分支＝kunsu-inbox SKILL 4a）、`status`／`verify` 值域、handoff 協議、軍師範本、三 live 軍師：零改動。
- kunsu-inbox SKILL 4a-5 手動輸出表格不加摘錄欄（比照 ADR 011 對「新回覆」清單不加 verify 標籤的排除寫法）；SKILL 4a-3 僅補一句「摘錄為沙盤與 hook 顯示專用、非分類依據」以保鏡射宣告完整。
- UserPromptSubmit hook 不加內容。
- 軍師模式（hook 與 kunsu-inbox 4b）不列「已回覆待確認」，本計畫不新增該列表。因此會重複派發的軍師 session 本身收不到摘錄——它的抵達通道（軍師模式 hook 加「久懸已回覆件」段，或產檔查重候選行附摘錄）列入 Deferred to Follow-Up Work。

#### Deferred to Follow-Up Work

- 最新回覆為補件／更正型時摘錄為後設語（「更正前一份回覆…」），不回退取前一份：維持「只讀最新」與零額外讀檔。若實用上常見，另案評估在摘錄前標「補件」。
- 首段為粗體鍵值（「**commit**：hash」，三 live 約 4%）時摘錄為元資料非結論：本輪接受，不加「狀態／結論」小標優先啟發式。
- 軍師 session 自身的抵達通道：軍師模式 hook 與 kunsu-inbox 4b 現以「未 commit 即新件」為判準，加「久懸已回覆件」段等於引入第二種列表語意；產檔查重候選行只看近 14 天，久懸件（實證 21/22 ≥5 天、最久 35 天）落在窗外。兩條路皆需另案定判準後才動；本計畫資料層欄位即為其資料來源。
- 「軍師欠辦行動項」與「工作線剩餘範圍」兩子題（idea B，見 `docs/ideas/2026-09-27-還缺什麼視圖軍師欠辦行動項與工作線剩餘範圍的可見性.md`）另案；前者涉狀態載體屬 ADR 層級。

---

## Planning Contract

### Key Technical Decisions

- KTD1. **萃取在回覆索引迴圈內一次完成，索引多帶已萃取字串而非檔案路徑**。`subrepo_status.py` 索引迴圈已把每份回覆 `read_text` 進記憶體只拆 frontmatter；在同一處萃取，每份回覆仍只讀一次，讀檔失敗維持既有 `continue`（R6 零新分支）。帶路徑再於渲染層讀檔會引入「索引成功、萃取時失敗」的第二種降級路徑，且 hook 每次啟動重跑。
- KTD2. **新欄位以預設值 `None` 接在 `HandoffInfo` 既有欄位之後，經建構子帶入**。`HandoffInfo` 為 frozen dataclass，建構後指派值會拋 `FrozenInstanceError`（2026-07-17 沙盤 todo 計畫已踩過）；預設值必須存在——`test_main.py` 的 `_handoff` helper 與 `test_handoff_graph_html.py` 皆以 kwargs 建構，缺預設全數斷。比照 `latest_reply_verify` 的加法模式。
- KTD3. **萃取函式自成一份放在 `subrepo_status.py`，規則由 R4 單一擁有**。全 repo 無既有「取首段首句」工具可重用；`_parse_frontmatter` 已在三個模組各自一份（既有被接受的複製體慣例），本計畫不順手抽共用模組。函式為純函式（字串進、`Optional[str]` 出），供單元測試直接覆蓋十形狀。
- KTD4. **沙盤新增獨立 CSS class，不沿用 `hint-next-step`／`days-waiting`，不含 `badge`／`chip`／`tlabel` 字面**。既有測試以 `'class="badge …"' not in html` 等精確 class 值做負向斷言，且「未接手／部分完成不含 hint-next-step 與 days-waiting」是既有測試明文契約；摘錄行用自己的 class（建議 `reply-excerpt`）即不觸動任何既有斷言。部分完成卡片新增一個專屬包裝（比照 `_html_awaiting_confirm_item` 對 `_html_handoff_detail` 的包裝方式），只附摘錄、不附提示與天數。
- KTD5. **hook 的 `_reply_annotated` 加選填參數帶摘錄，接在依賴後綴之後，空值零後綴**。該函式為部分完成與已回覆待確認兩分類共用；接在整個括號與依賴後綴之後，既有子字串斷言（`（submitted 日期）`）與 partial 行的精確行斷言在 fixture 內文僅「# 回覆」（萃取為 `None`）時全數維持。分隔符與引號形式由實作定，須保證單行、不換行。
- KTD6. **kunsu-inbox 版號 0.14.0 → 0.15.0；沙盤無 skill 版號**。`session_hook.py` 與其依賴的 `subrepo_status.py` 改動依歷次慣例 bump kunsu-inbox；`kunsu-dashboard/SKILL.md` 無 `version` 欄位，純渲染改動歷來只記 CLAUDE.md 開發狀態。
- KTD7. **CONCEPTS.md 不動**。「交接三分類」「驗收方式」詞條歷來不收純顯示強化（停留天數、verify 子分組皆未入詞條）；摘錄同屬顯示層。

### Sources

- 資料層現況：`skills/kunsu-dashboard/app/subrepo_status.py` 回覆索引迴圈（4a-3 前置區塊）與 `HandoffInfo` 定義；`raw_content` 存的是交接本體、非回覆內文。
- 沙盤卡片前例：`skills/kunsu-dashboard/app/main.py` 的 `_NEXT_STEP_HINTS`、`_days_waiting_label`、`_html_awaiting_confirm_item`、`_html_handoff_detail`；CSS 於同檔 `.hint-next-step`／`.days-waiting` 宣告處。
- hook 現況：`skills/kunsu-inbox/scripts/session_hook.py` 的 `_reply_annotated`、`_sub_mode_lines`、`_capped`。
- 測試 helper：`skills/kunsu-dashboard/tests/test_subrepo_status.py` 的 `make_reply`（body 寫死「回覆內容。」）、`skills/kunsu-dashboard/tests/test_main.py` 的 `_handoff`（無 `raw_content` 參數，需真實內文的測試直接建構 `HandoffInfo`）、`skills/kunsu-inbox/tests/test_session_hook.py` 的 `_write_reply`（body 寫死「# 回覆」）。
- 回覆產檔範本：`skills/handoff/scripts/new-handoff-reply.sh` printf 區塊（H1 為「<title> — 回覆」、空內文預設「_（待補充）_」）。
- 三 live 軍師 428 份回覆首段形狀統計（2026-09-27 規劃期實測）：硬換行且首行未以句號收尾 26%、粗體鍵值起頭 4.4%、清單起頭 2.8%、「狀態」起頭 8.2%、表格起頭 0、空內文 0；H1 之後全部有可用文字段。
- 前例決策：`docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md`（display-only 欄位邊界與顯示面刻意排除寫法）、`docs/plans/2026-07-17-001-feat-dashboard-todo-list-plan.md` Key Technical Decisions（frozen dataclass、CSS class 避讓）。

---

## Implementation Units

### U1. 資料層：回覆首句萃取與 HandoffInfo 新欄位

- **Goal**：分類結果每筆交接帶最新回覆的首句摘錄，其餘行為零改動。
- **Requirements**：R1, R4, R5, R6；KTD1, KTD2, KTD3。
- **Dependencies**：無。
- **Files**：`skills/kunsu-dashboard/app/subrepo_status.py`、`skills/kunsu-dashboard/tests/test_subrepo_status.py`。
- **Approach**：
  1. 新增純函式：輸入回覆檔全文，輸出 `Optional[str]`，規則依 R4。
  2. 回覆索引迴圈於拆 frontmatter 後呼叫該函式，索引元組多帶摘錄；讀檔失敗分支不動。
  3. 取最新回覆處同時取出摘錄，`HandoffInfo` 新欄位 `latest_reply_excerpt: Optional[str] = None` 接在既有欄位之後。
  4. 檔頭「鏡射 SKILL.md 4a」註解補一句：摘錄為顯示專用、非分類依據。
- **Patterns to follow**：`latest_reply_verify` 的落地路徑（索引元組→排序取最新→`HandoffInfo` 預設值欄位）；verify 對純空白正規化為 `None` 的寫法。
- **Test scenarios**：
  - `make_reply` 加選填 `body` 參數（預設維持「回覆內容。」），既有測試零改動通過。
  - Covers AE1. 範本回顯 H1＋「## 狀態」＋硬換行段 → 摘錄為完整首句。
  - Covers AE4. 硬換行兩行併段後以句號切句。
  - Covers AE5. H1 本身像結論，仍取其後首段；反引號去除。
  - Covers AE8. 超過 60 字元無句號 → 60 字元加「…」（含 CJK 混合）。
  - Covers AE9. 內文僅「_（待補充）_」→「（待補充）」。
  - Covers AE10. 兩份回覆取最新一份的摘錄，不取舊份。
  - 清單起頭「- install-logrotate.sh：…」→ 去標記後的文字。
  - 首段前有程式碼圍欄與表格列 → 皆跳過，取其後段落。
  - 連結語法「[文字](路徑)」→ 保留「文字」。
  - 內文全為標題與空行 → `None`；無回覆 → `None`。
  - 回覆檔 `UnicodeDecodeError` → 該回覆自索引消失、分類依其餘回覆（既有行為迴歸）。
  - 分類結果三分類筆數與既有 `latest_reply_*` 欄位對既有 fixture 全部不變。
  - 差分案例：同一交接兩組 fixture 只差回覆正文（摘錄不同），分類、排序鍵、`latest_reply_status`／`latest_reply_date`／`latest_reply_verify` 逐項相等（R5 顯示專用不變式）。
  - 首句含 `client_ref`、`_lang=zh-TW` → 底線原樣保留；AE9 仍為「（待補充）」。
  - Covers AE11. 最新回覆讀取失敗、較舊回覆可讀 → 摘錄與 status、日期同取較舊份。
- **Verification**：`test_subrepo_status.py` 全數通過；沙盤其餘測試模組零改動通過。

### U2. 軍師沙盤：兩分類卡片摘錄行

- **Goal**：「已回覆待確認」與「部分完成」卡片在收合狀態下可見摘錄。
- **Requirements**：R2；KTD4。
- **Dependencies**：U1。
- **Files**：`skills/kunsu-dashboard/app/main.py`、`skills/kunsu-dashboard/tests/test_main.py`。
- **Approach**：
  1. 新增摘錄行渲染函式：摘錄非空時輸出獨立 class 的 `div`，內容經 `escape()`，帶「回覆摘錄」語意的前綴（不用「結論」）。
  2. `_html_awaiting_confirm_item` 在既有提示行之後接摘錄行。
  3. 部分完成分類改用新包裝函式：`_html_handoff_detail` 之後只接摘錄行；「未接手」維持直接呼叫 `_html_handoff_detail`。
  4. CSS 於既有 `.hint-next-step` 宣告旁新增一條。
- **Patterns to follow**：`_html_awaiting_confirm_item` 的「提示置於 `</details>` 之外」組合方式與對應位置測試（`html.index` 比較）；`escape()` 一律於渲染端。
- **Test scenarios**：
  - Covers AE1. 已回覆待確認卡片含摘錄 class 與文字；`</details>` 位置在摘錄之前；既有 `hint-next-step` 與 `days-waiting` 照舊出現。
  - Covers AE2. 部分完成卡片含摘錄；不含 `hint-next-step` 與 `days-waiting`（既有負向斷言維持）。
  - Covers AE3. 未接手卡片不含摘錄 class；摘錄為 `None` 的已回覆待確認卡片不渲染摘錄行。
  - Covers AE7. 摘錄含 `<b>` 與 `&` → 輸出 escape 後字面，不含原始標籤。
  - 既有「頁面不含 badge」類負向斷言在有摘錄的頁面下仍成立。
  - 全域總覽列與軍師分組摘要列計數不受影響（摘錄不進 `PendingAggregate`）。
- **Verification**：`test_main.py` 全數通過；以 fixture 軍師啟動伺服器對照頁面，兩分類卡片收合時可見摘錄。

### U3. SessionStart hook：子專案摘要行附摘錄與 SKILL 同步

- **Goal**：hook 子專案模式兩分類每行尾端附摘錄；kunsu-inbox 版號與 4a 鏡射宣告同步。
- **Requirements**：R3, R7；KTD5, KTD6。
- **Dependencies**：U1。
- **Files**：`skills/kunsu-inbox/scripts/session_hook.py`、`skills/kunsu-inbox/tests/test_session_hook.py`、`skills/kunsu-inbox/SKILL.md`。
- **Approach**：
  1. `_reply_annotated` 加選填摘錄參數，接在依賴後綴之後；`None` 零後綴；保證單行（摘錄本身由 R4 保證無換行）。
  2. `_sub_mode_lines` 的部分完成與已回覆待確認兩處呼叫傳入 `latest_reply_excerpt`；未接手行不動。
  3. SKILL.md frontmatter `version: 0.15.0`；4a-3 補一句摘錄為顯示專用、非分類依據；SessionStart hook 節「只告知不開工」項補一句子專案摘要附最新回覆摘錄。
- **Patterns to follow**：`dep_suffix` 接在括號之後的位置慣例；`_write_reply` 加參數比照 `verify` 選填寫法。
- **Test scenarios**：
  - `_write_reply` 加選填 `body` 參數（預設維持「# 回覆」），既有測試（含 partial 行精確行斷言）零改動通過。
  - Covers AE6. 已回覆待確認行尾端含摘錄；既有子字串「`（submitted 日期）`」仍命中。
  - 部分完成行尾端含摘錄。
  - Covers AE3. 未接手行字面與現行完全相同；摘錄為 `None` 的已回覆待確認行無任何後綴。
  - 依賴後綴與摘錄並存時順序為括號、依賴後綴、摘錄。
  - 超過 5 筆時「另有 N 筆」行不變。
- **Verification**：`test_session_hook.py` 全數通過；`test_prompt_inbox_hook.py` 零改動通過（R7）。

### U4. 文件與一致性檢查

- **Goal**：母體文件反映本功能；一致性檢查照常通過。
- **Requirements**：R7；KTD6, KTD7。
- **Dependencies**：U1, U2, U3。
- **Files**：`CLAUDE.md`、`docs/ideas/2026-09-01-久懸已回覆待確認件於沙盤與inbox摘要列帶回覆結論首句.md`。
- **Approach**：
  1. CLAUDE.md 專案結構樹：`session_hook.py` 行補「子專案模式兩分類附最新回覆摘錄」；`app/` 行的 `subrepo_status.py` 補「含回覆首句萃取」。
  2. CLAUDE.md 開發狀態新增一條，依既有格式：動機（2026-09-01 案例、三 live 實證數字）、落地（資料層一次讀取萃取、兩載體、兩分類、去門檻決策與理由）、測試數字。
  3. idea 檔 frontmatter `status: promoted`，補一行 `plan:` 指向本計畫路徑（無 brainstorm，直接規劃）。
  4. 執行 consistency-check 確認 34 項 PASS；E 項對 `subrepo_status.py` 的關鍵詞計數不受影響。
- **Test expectation**：none — 純文件與檢查執行；以 consistency-check 結果為驗證。
- **Verification**：consistency-check 全 PASS；CLAUDE.md 結構樹與開發狀態各恰新增一處；idea 檔 frontmatter 含 `status: promoted` 與指向本計畫的 `plan:` 行。

---

## Verification Contract

| 檢查 | 指令 | 適用單元 | 通過訊號 |
|---|---|---|---|
| 沙盤測試 | `python3 -m pytest skills/kunsu-dashboard/tests/ -q` | U1, U2 | 全數通過，總數自 166 增加 |
| kunsu-inbox 測試 | `python3 -m pytest skills/kunsu-inbox/tests/ -q` | U3 | 全數通過，總數自 78 增加；`test_prompt_inbox_hook.py` 零改動 |
| 跨檔一致性 | `bash scripts/consistency-check.sh` | U3, U4 | 34 項全 PASS |
| 沙盤實況 | 以 fixture 或 live 軍師啟動 `start.sh` 後瀏覽 | U2 | 兩分類卡片收合時可見摘錄，未接手不見 |
| hook 實跑 | 對子專案 repo 以 stdin 餵 cwd 執行 `session_hook.py` | U3 | 兩分類行尾端有摘錄，未接手行不變 |

---

## Definition of Done

- U1–U4 全部完成；上表五項檢查全數通過。
- AE1–AE11 各有至少一條對應的自動化測試通過（U1–U3 測試情境中標 Covers 者）。
- 既有測試除補 fixture 選填參數外零語意改動。
- 分類分支、`status`／`verify` 值域、handoff 協議、範本、`prompt_inbox_hook.py` 零 diff。
- 無實驗性或廢棄程式碼殘留；新增 CSS class 不含 `badge`／`chip`／`tlabel` 字面。
- CLAUDE.md 開發狀態條目與結構樹已更新；idea 檔標記 promoted。
- commit 與 install.sh 重佈署由使用者明確要求時執行。
