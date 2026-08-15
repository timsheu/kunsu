---
name: handoff
version: 0.16.0
description: |
  把一個需要交給「另一個 session／另一個角色（如後台、前端、DevOps）」研究或
  接手的議題，寫成一份獨立交接文件，落在當前專案的 docs/handoffs/。每份交接一個
  檔（YYYY-MM-DD-標題.md），含 Dataview 友善 frontmatter（from/to/status）。
  交接文件本體建立後即為定案快照，任何人（含發起方自己）都不再編輯（唯一例外：
  done 收尾時發起方更新本體 status 並歸檔）；接手方改以
  在 docs/handoffs/replies/ 新增獨立回覆檔案回報結論（回覆信箱模式），避免雙方
  共編同一檔案造成版本漂移。
  Use when asked to「寫一份交接文件」「交接給後台」「handoff 給另一個 session」
  「回覆交接文件」「回覆軍師」「回覆軍師的交接」「回覆交接」「回報軍師」
  「回報結果」「reply 給軍師」「產生交接文件」「新增 handoff」「list handoffs」
  「交接收尾」「這份交接可以收尾了」「這份交接做完了」「完成這份交接」
  「歸檔這份交接」「標記交接完成」「handoff done」「交接工作先暫停」
  「暫停這份交接」「交接先放著，先做別的需求」「交接工作先放到 branch，之後再回來」
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
docs/handoffs/          → 交接文件本體（定案快照，任何人不再編輯，含發起方自己；
                           唯一例外：done 收尾更新 status）
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
- 使用者要查詢交接現況（`/handoff list`）、標記完成／收尾歸檔（`/handoff done`，
  含口語「這份交接可以收尾了」「歸檔這份交接」）

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

## 確認 commit（協議步驟）

add／done／reply（本地語境）三個子指令的尾端，依 ADR 009 執行「確認一次 → commit」
的協議步驟。逐次確認即構成「使用者明確要求」，與全域「不主動 commit」規範相容；
此為軍師協議「未 commit 即未處理」狀態機的收斂動作，先例為 kunsu-init 步驟 ⑥。

1. **核對**：`git status --porcelain <本流程產出的路徑>` 確認確有待提交變更——
   輸出非空即視為有待提交變更（rename 呈現為 `XY src -> dst` 複合行，亦屬
   待提交變更）。無變更（使用者已自行 commit）→ 回報「相關檔案已提交，
   無需操作」，**不產生空 commit**。
2. **確認**：AskUserQuestion「是否 commit 本次產出？（訊息：`<固定格式訊息>`）」。
3. **確認後執行**：`git add <僅本流程產出的具體路徑>`（不用 `git add -A`、不整目錄
   打包）→ `git commit -m "<固定格式訊息>"`。**絕不 push**。
4. **取消時**：保留全部產出、不回退任何操作，回報可稍後手動執行的完整
   `git add`＋`git commit` 指令。

**非互動環境**：AskUserQuestion 不可用（headless／pipeline）時，一律視同取消
——不 commit，僅輸出可手動執行的指令提示，不得跳過確認逕行 commit。

固定訊息格式（「`docs:` 動詞＋對象檔名」結構，用語可微調）：

| 子指令 | 訊息 |
|--------|------|
| add | `docs: 建立交接 <檔名>`（更正交接補記指標時再附：`；補記更正指標 <原本體檔名>`） |
| done | `docs: 歸檔交接 <檔名>`（含 todo 一併收尾時：`docs: 歸檔交接 <檔名>；一併收尾 todo <slug>[、<slug>…]`；殘項清點有轉出時再附：`；轉出殘項 todo <slug>[、<slug>…]`） |
| reply（本地語境） | `docs: 回覆交接 <檔名>` |

**例外**：kunsu 語境的 reply（回覆檔落在另一 repo 的軍師回覆信箱）**不執行**本
步驟——未 commit 正是軍師信箱的「新回覆」訊號，見 reply 步驟 5。

## 執行步驟

### add

1. **取得內容**：這是交接文件的重點，內文必須讓「上下文乾淨的接手方」讀得懂。
   下筆前先確保議題已想透——現況分析與待決問題要具體、不空泛；仍有隱含假設或
   未決分支時，先以 grilling／`/ce-brainstorm` 逐一逼出再交接（ce-brainstorm 已內建
   此「一問一答、達成共識前不動手」的硬化流程，不需另建機制）。
   把目前 session 已釐清的事實整理進以下段落（腳本會產生骨架，再用 Edit 補實）：
   - **背景 / 目標**：為什麼需要這次交接，接手方要達成什麼
   - **現況分析（已知事實）**：本 session 已查證的程式碼位置、資料結構、行為；
     引用具體 `檔案:行號`，不要只給結論。引用中介文件而未自行查證的內容，
     標明「依 X 記載」（見下方斷言層級紀律）
   - **需要你研究／決策的問題**：明確列點，讓接手方知道要回答什麼
   - **期望交付**：希望接手方回什麼（API 契約、可行性評估、估算數字…）
   - **相關檔案 / 連結**：關鍵檔案路徑、相關 plan／brainstorm／solution 連結。
     引用其他交接／回覆時必含**完整檔名**（含日期）——檔名是權威識別，路徑僅為
     當下位置提示；歸檔造成的路徑失效不構成錯誤，讀者以檔名搜尋定位（ADR 016）

   **投遞前 redact**：交接檔會 commit 進 repo（kunsu 語境下更落入軍師 repo、可能
   公開），內文與引用的日誌／設定片段務必移除敏感資訊——API key、密碼、token／
   憑證、個資（PII）；需要時以佔位符（如 `<REDACTED>`）代替，不要貼原值。

   **斷言層級紀律**：查閱他方系統的中介文件（規格、索引、對照表）所得＝
   **二手資訊**。對他方系統的事實斷言，凡來源為中介文件即標明來源層級——寫
   「依 X 記載」，不以「事實是」語氣轉述：接手方無從分辨幾手資訊、只能選擇
   信任，未標層級的錯誤斷言曾使推導正確的一方被說服改口，且轉述鏈上任何一環
   都無法定位上游失真。接手方會**據以實作**的斷言（判準：對方會不會據此寫
   程式或改設計）須一手——落原始碼／實際狀態查證（自查或派副官查證），並在
   內文註明查證方式與位置（`檔案:行號`），留下跨 session 可重建的文本痕跡；
   背景說明可停在中介文件、標明層級即可。

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
   「回覆方式」段落是腳本自動產生的定型文字，不需要也不應該手動修改。（此定型
   文字有兩份同文案副本——`scripts/new-handoff.sh` 的 printf 與本文件「檔案格式
   範例」段的說明；修訂此文案時兩處必須連動修改，保持字面一致。另外軍師範本
   `skills/kunsu-init/assets/templates/kunsu-claude.md` 的「回覆檔 `status` 值域」
   說明是同一值域的語意副本（非逐字），修訂值域或其限制語時一併核查該處與既有
   軍師的 CLAUDE.md。）

4. **回報**：附上建立的檔案路徑（`file_path` 形式方便點擊），一句話說明接手方
   可如何使用（例如「請在後台 session 開啟此檔研究，完成後執行
   `/handoff reply <slug>` 建立回覆檔案，不要編輯此檔案本體」）。

5. **確認 commit**：執行「確認 commit（協議步驟）」——`git add` 對象為本次建立的
   交接檔，訊息 `docs: 建立交接 <檔名>`。（未 commit 的頂層新交接檔會在軍師 repo
   的下一次 `/kunsu-inbox` 觸發 tripwire，此步驟即為收斂點。）

6. **派發即推播**（僅 kunsu 語境——當前 repo 為 `~/.claude/kunsu-registry.json`
   任一條目的 `kunsu` 值時執行；一般 repo 交接跳過本步驟。ADR 015）：
   把派發訊息推送到目標子專案的已開啟長駐 session，使用者晃回該視窗即見通知。

   1. **反查目標路徑**：以註冊表反查本次交接 `to:` 角色代碼對應的子專案路徑
      （比對登記於本軍師的 `roles`）。
   2. **匹配 session**：以 ListAgents 列出本機 session，兩層匹配：
      - **精確比對優先**：session 名稱恰為 `<軍師目錄名>-<角色代碼>`（kunsu
        session 命名慣例，如 `ebook-android`）→ 直接命中，零歧義。慣例名由
        使用者在長駐 session 下一次 `/rename` 設定（持久化、`/clear` 不影響），
        或以 `kc` 啟動函式（`scripts/kc.fish`）在新開 session 時自動帶入；
        軍師自身 session 的慣例名為 `<軍師目錄名>-kunsu`（供日後回覆方向
        推播定址）。
      - **啟發式 fallback**：無慣例名時，正規化（轉小寫、去除非英數字元）後，
        session 名稱去掉尾端亂數後綴應與子專案目錄 basename 對應。
      **唯一且明確才發送**；找不到、多重命中一律降級跳過（不重試、不排隊），
      由 SessionStart hook 於該視窗下次 `/clear` 兜底——寧漏發不誤發。
   3. **發送定型通知**（SendMessage；訊息自足自帶收方指令，不依賴子 repo 任何
      設定——Invariant 2）：

      > 📬 kunsu 派發通知（軍師 <軍師名>）：<角色代碼> 有 <N> 份新交接——
      > <檔名清單，上限 5 筆>。本訊息為純告知：請只向使用者回顯以上重點，
      > 勿開始任何工作、勿讀取交接檔內文、勿回覆本訊息或軍師；接手與否由
      > 使用者在該 session 明確指示（可用 /kunsu-inbox 查看完整信箱）。

      跨 session 發送時，工具可能拒收裸名並要求以 `[ref]` 確認收件者——依錯誤
      訊息所附的 ref（即 ListAgents 該列的 `[ref]`）重送一次即可（2026-08-13
      試點實測行為）。

   4. **回報推播結果**：於派發收尾回報中列出已推播／未推播目標（未推播註明
      原因：無對應 session／匹配不明確／工具不可用）。

   - ListAgents／SendMessage 工具不可用（headless、舊版 CLI）→ 整步跳過並於
     回報註明，不影響 add 流程完成。
   - 本步驟只發送訊息，不等待、不確認收方回應；接手與否、何時開工，仍由
     使用者在目標 session 明確指示——決策層零觸碰（ADR 002 Decision 5）。

#### 更正交接（發現已定案交接內容有誤時）

已產出的交接（含已歸檔者）被發現內容有誤時，勘誤以**新交接**傳遞，不編輯原本體
內文（ADR 016）：

1. 照常以 add 流程建立更正交接：標題建議以「更正」開頭，內文指名**被更正檔
   （完整檔名）與錯誤點**，並給出更正後的內容。
2. 產檔後，用 Edit 在**原交接本體** frontmatter 補
   `corrected_by: <更正交接檔名>`（檔名不含路徑；已有 `corrected_by` 時改為
   YAML 列表累加，保留全部更正歷史）。原本體已歸檔（`archive/` 內）時同樣
   適用——這是發起方對自己文件的生命週期標記，位置無關。此欄位僅供 display
   與追溯，不進任何掃描、tripwire 或分類邏輯。
3. 確認 commit 的 `git add` 範圍**包括更正交接檔與原本體路徑**（含 archive 內
   路徑），訊息沿 add 格式加註記（見指令格式段表格）。
4. 原本體在**頂層**時，步驟 2 的 Edit 至確認 commit 之間不執行 `/kunsu-inbox`
   （中間態 ` M` 屬 catch-all tripwire 範圍，比照 done 步驟 4–7 連續執行約束）；
   archive 內本體無此疑慮。取消 commit 時保留變更並附可手動執行的指令，同時
   明示：頂層本體未 commit 的 ` M` 會使 `/kunsu-inbox` 觸發 tripwire，屬預期
   訊號、以補 commit 收斂，不是外部入侵。

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
      檔案進軍師 repo。若使用者意圖是**主動上報**（無對應交接的情報），請改用
      `/kunsu-report` 投遞（上報信箱管道），不要以孤兒回覆檔投遞。

2. **取得內容**：這是接手方要交付給發起方的結論，讓對方不必再往返確認就能知道
   結果。內文至少包含：目前狀態（進行中／完成）、對原問題清單的逐項回答、與原
   規劃的落差（如有）、其他備註。逐項回答處盡量附上可查核的證據（測試輸出、
   日誌摘要、commit hash 或 `檔案:行號`）——發起方 done 收尾時會逐項驗收，
   證據完整可省去一輪往返追問。附證據時務必 redact 敏感資訊——測試輸出／日誌
   摘要最易夾帶 API key、密碼、token／憑證、個資（PII），貼入前先移除或以佔位符
   代替（回覆檔會 commit，kunsu 語境下更落入軍師 repo）。

   逐項回答之外，也把交接內容本身當作可查核對象：你是唯一同時持有交接文件
   與自身參照物（原始碼、原始文件、實際狀態）的一方，發起方看不到你這端的
   事實。若發現交接內容與參照物不符、或交接內文自相矛盾（例如數字對不上、
   前後段互斥），即使判斷不影響自身實作，也在回覆中明列並附位置——未被
   指出的錯誤認知會留存於交接定案快照，並可能流傳進後續交接。矛盾寫在
   回覆內文即可，不要回頭修改交接本體；是否核對、核對到哪一層由你判斷，
   無矛盾時不需任何核對聲明。

   同時評估此次工作的**驗收狀態**，決定選填欄位 `verify` 的值——這個欄位讓
   發起方（與軍師沙盤）不必點開全文就知道「還缺哪種驗證」：
   - `needs-deploy`（需上線測試）／`testable-now`（馬上可測）／
     `needs-device`（需實機測試）三個建議代碼（一律**全小寫 kebab-case**），
     顯示端會轉為中文標籤；
   - 三者都不貼切時可填自由字串（原樣顯示）；
   - 無明確驗收需求（例如純研究結論）則省略此欄位；
   - **verify 不跨回覆繼承**（ADR 011）：顯示端只讀最新回覆——分階段回報時，
     驗收需求未改變也要在新回覆中**顯式複寫**相同的值，否則標籤靜默消失；
     驗收環境改變（如部署已完成）時，同樣以新回覆更新 verify 值，避免沙盤
     持續顯示過期標籤。

3. **建立回覆檔案**（內文走 stdin）：

   ```bash
   echo "<回覆內文>" | bash ~/.claude/skills/handoff/scripts/new-handoff-reply.sh "<原交接檔案 slug 或路徑>" "<from>" "<verify>"
   ```

   - 腳本會自動定位原交接文件（可用完整檔名、相對／絕對路徑，或足以唯一比對的
     檔名片段），讀出其 `title`／`from`，推算回覆的 `to`（= 原交接文件的 `from`）；
     `from` 參數可省略，預設取原交接文件的 `to`。
   - `verify` 參數選填（步驟 2 評估的值）：非空時寫入 frontmatter `verify:` 欄位；
     不需要時省略。只帶 `verify` 不覆寫 `from` 時，`from` 傳空字串 `""` 佔位。
   - 找不到、或找到多筆符合的原交接文件時，腳本會報錯並列出候選，需給更精確的
     片段或完整路徑重新執行。
   - 回覆一律落在**原交接檔所在 repo** 的 `docs/handoffs/replies/`：腳本從原檔
     位置推算 replies 目錄，與當前工作目錄無關。跨 repo 回覆（子 repo 回覆軍師）
     時傳軍師交接檔的**絕對路徑**即可，落點保證在軍師的回覆信箱。
   - 輸出檔名固定為 `{原交接檔所在 handoffs 目錄}/replies/{原交接檔名}-reply-{today}.md`；
     同日已存在同名回覆會自動加 `-2`、`-3`…（append-only，不覆寫前次回覆）。

4. **回報**：附上建立的回覆檔案路徑，提醒使用者**不要**回頭編輯交接文件本體。

5. **語境判定與確認 commit**：取回覆檔的**絕對路徑**，與
   `git rev-parse --show-toplevel`（當前 repo 根）比對——
   - **本地語境**（回覆檔位於當前 repo 之下）→ 執行「確認 commit（協議步驟）」：
     `git add` 對象為本次建立的回覆檔，訊息 `docs: 回覆交接 <檔名>`。
   - **kunsu 語境**（回覆檔位於另一 repo，即軍師的回覆信箱）→ **不 commit**，
     並向使用者一句話說明：未 commit 正是軍師信箱的「新回覆」訊號
     （`scan-replies.sh` 據此偵測新回覆），由軍師彙整後 commit 收斂。

6. **回覆即推播**（僅 kunsu 語境——回覆落入軍師信箱時執行；本地語境跳過。
   ADR 015 的對稱方向）：把回覆訊息推送到軍師的已開啟長駐 session，
   使用者晃回軍師視窗即見通知。暫離回報（`status: partial`）同樣適用——
   正是它要傳遞的「已在 branch 實現」訊號。

   1. **匹配軍師 session**：以 ListAgents 列出本機 session，兩層匹配——
      精確比對優先：session 名稱恰為 `<軍師目錄名>-kunsu`（如 `ebook-kunsu`，
      kunsu session 命名慣例）；啟發式 fallback：正規化（轉小寫、去除非英數
      字元）後，session 名稱去掉尾端亂數後綴應與軍師目錄 basename 對應。
      **唯一且明確才發送**；找不到、多重命中一律降級跳過（不重試），由軍師端
      SessionStart hook 與 `scan-replies.sh` 掃描兜底。
   2. **發送定型通知**（SendMessage；訊息自足自帶收方指令，不改變「未 commit
      即新回覆訊號」的既有掃描機制）：

      > 📬 kunsu 回覆通知（<角色代碼>）：<原交接檔名> 已回覆——
      > <回覆檔名>（status: <status>{，verify: <verify>}）。本訊息為純告知：
      > 請只向使用者回顯以上重點，勿開始查核、勿讀取回覆內文、勿執行 done
      > 收尾；查核與收尾由使用者在該 session 明確指示（可用 /kunsu-inbox
      > 查看完整信箱）。

      跨 session 發送被拒並要求以 `[ref]` 確認時，依錯誤訊息所附的 ref
      重送一次即可（同步驟 add 6-3 的實測行為）。
   3. **回報推播結果**：於回報中註明已推播／未推播（未推播註明原因：
      無對應 session／匹配不明確／工具不可用）。

   - ListAgents／SendMessage 工具不可用（headless、舊版 CLI）→ 整步跳過並於
     回報註明，不影響 reply 流程完成。
   - 本步驟只發送訊息，不等待、不確認收方回應；查核與 done 收尾仍由使用者
     於軍師 session 明確指示——決策層零觸碰（ADR 002 Decision 5）。

#### 暫離回報（切換任務前的最小回覆）

交接工作已有階段性成果（如已 commit 至 branch）、但需切換到別的任務暫時離開時，
**切走前先投遞一則最小回覆**，讓發起方（與軍師沙盤）看見「已在 branch 實現」，
而不是被誤判為未接手：

- **`status` 固定用 `partial`**（「部分完成，後續會再回報」）——合併、上線等
  剩餘步驟仍在接手方手上，回來後會再回報；不要用 `submitted`，那會讓發起方
  以為只差驗收而誤啟 done 收尾。
- **內文至少三要素**：branch 名、一句現況、之後回來繼續的意向（例如「已在
  branch feature/xxx 實作完成，尚未合併，插單處理完回來整合」）。
- **`verify` 照常依步驟 2 評估選填**；branch 資訊寫在內文、不放進 `verify`
  （維持其純驗收語意），也不需要新的建議代碼。
- **回來完成整合後**，照常投遞完成回覆（`status: submitted`）；verify 不跨
  回覆繼承（見步驟 2），驗收需求未變也要顯式複寫。

建立方式與一般回覆相同（步驟 3 的腳本），差別只在內文最小化與 `status: partial`。

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

> **時機與守門**：發起方查核完最新回覆、使用者表達「結論無誤」「可以收尾」等確認
> 語意時，應**主動建議**執行 `/handoff done` 收尾歸檔（僅建議，執行前仍經使用者
> 確認，絕不逕自執行）。反面守門：若當前 repo 的 `docs/handoffs/` 頂層沒有與議題
> 相符的交接本體（代表本 repo 是接手方、不是發起方），不進入 done 流程——done 只
> 由發起方在交接本體所在 repo 執行，請提示使用者至發起方 repo（kunsu 語境即軍師
> repo）處理，避免誤歸檔本 repo 自己對外發出的其他交接。

1. Read 指定的 `docs/handoffs/<slug>.md`（或使用者給的關鍵字，Glob 找出對應檔案）。
2. Glob `docs/handoffs/replies/*.md`，篩選 frontmatter `in_reply_to` 等於此交接
   文件檔名者；若有多份，依檔名的 `(日期, 序號)` **數值排序**取最新一份 Read
   確認結論（同日多份以 `-2`、`-3`… 序號消歧；與 `/kunsu-inbox` 4a 的排序慣例
   一致，勿以 frontmatter `created` 或整段檔名字串排序——`created` 同日無法
   消歧、字串排序會把 `-10` 排在 `-2` 前）。
   - 若完全沒有回覆檔案，提醒使用者尚無接手方回覆，確認是否仍要標記完成（例如
     發起方自行確認已完成）。
   - **逐項驗收查核**（歸檔前守門，顯式化缺口、不強制擋下）：把交接本體的
     「需要你研究／決策的問題」與「期望交付」逐項對照最新回覆，回報每項的
     覆蓋狀態（已回答／部分回答／未回答）。最新回覆帶 `verify:` 欄位時，一併
     向使用者確認該驗收方式是否已實際執行（例如 `needs-deploy` 是否已上線
     驗證、`testable-now` 是否已實測）；查核以可驗證的證據（日誌、測試輸出、
     部署紀錄）為準，不以回覆的文字宣稱代替驗證。存在未回答項或未執行的
     驗收時明確列出，由使用者決定仍要收尾或暫緩——本步驟的責任是讓缺口
     可見，不是替使用者做決定。
   - **沉澱訊號查核**（純資訊性，不阻擋流程、不改變任何分支）：存在多份回覆
     時，除上述取最新一份確認結論外，一併 Read 先前各回覆（至少 frontmatter
     `status` 與內文要點）以掌握往返軌跡——通讀屬本查核新增的讀檔範圍，結論
     確認與逐項驗收仍以最新回覆為準、單份回覆維持現行。通讀時順手判斷本次
     往返有無值得沉澱的教訓訊號：往返翻案（後續回覆推翻先前說法）、blocked
     軌跡（曾有 `blocked` 回覆）、與原規劃的落差（回覆落差段非空）、多輪往返
     （回覆數明顯多於常態）、驗收缺口經使用者接受收尾。訊號字面存在即記下、
     不確定時傾向記下，留待步驟 9 回報時提示；無訊號則全程零輸出。
   - **反向路由查核**（純資訊性，不阻擋流程；命中即於本步驟當下回報，與沉澱
     訊號查核「留待步驟 9」的呈現時點刻意不同——行動項不可隨暫緩收尾而
     消失）：附掛於上述讀檔動作（多份回覆的通讀、單份回覆的最新一份），一併
     判斷回覆中的兩類反向內容：
     - **指向發起方或第三方的行動項**：回覆要求發起方協調、安排、處理某事，
       或建議讓第三方知悉，且不屬接手方自身的後續工作。偵測範圍為全部回覆
       的聯集；被後期回覆明示撤回或已完成者照列並標註該狀態，不靜默剔除。
     - **已解答的既有疑問**：回覆內容回答了查核範圍內登記過的疑問或承諾。
       查核範圍依優先序設上限——`docs/todos/` 頂層全讀、本交接本體內文引用
       的文件、`docs/plans/` 僅標題與目標段掃描；`archive/` 不入範圍，範圍外
       漏報顯式接受（成本上限，非疏漏）。
     有命中時逐筆隨逐項驗收結果一併回報並提示落點：行動項→落 todo 或轉新
     交接；答案→回填至該疑問所在的 todo／plan 並附回覆路徑。**疑問所在為
     交接本體（含已歸檔者）時不提示編輯本體**——本體是定案快照，改提示落
     todo／plan 註記並附回覆路徑。提示前可 grep `docs/todos/` 頂層，疑似已有
     落點者改標「似已落點於〈檔名〉」；與 inbox 分流提示、來源 todo 查核的
     重複提示屬可接受誤報。本查核不自動建檔、不自動編輯任何文件，是否當場
     處理由使用者決定；無命中則零輸出。查核無狀態——暫緩收尾後重跑 done
     必然重新提示，此即反向內容的遺失防線。
3. **來源 todo 查核**：掃描本 repo `docs/todos/` 頂層 `*.md`（排除 `archive/`；
   目錄不存在或無檔案時本步驟靜默跳過），以具體檔名做雙向比對——(a) 各 todo 檔
   內文是否提及本交接檔名 `<slug>.md`；(b) 交接本體內文是否提及某 todo 檔名。
   任一方向命中即列為候選。
   - 有候選 → AskUserQuestion 讓使用者確認哪些 todo 一併收尾：候選 ≤4 筆用
     multiSelect 一次呈現（label 為 todo 標題，description 註明現況 status 與
     命中方向；若步驟 2 反向路由查核命中的行動項指向該候選 todo，description
     一併註明「本輪回覆含指向此 todo 的未完成行動項」且該筆不建議收尾——
     避免未完成行動項隨檔歸檔蒸發），>4 筆改在對話中列數字清單請使用者以
     文字指定。候選 status 已是
     「已解決」或「已封存」（漏歸檔孤兒）者，文案標明「已標記為<status>但尚未
     歸檔，確認一併補歸檔？」，與未處理件的收尾文案區分。
   - 使用者取消、零選、或非互動環境 AskUserQuestion 不可用 → 一律不執行任何
     todo 操作，逕行後續交接收尾（比照「確認 commit」不可用視同取消的規則，
     本查核不阻擋 done 完成）。
   - 無候選但頂層仍有未歸檔 todo → 僅顯示一行提示「`docs/todos/` 尚有 N 筆
     未歸檔 todo，若此交接源自其中一筆可一併收尾」，不阻擋流程。

   > **連續執行約束**：步驟 4 至步驟 7 必須連續執行，中間不得執行
   > `/kunsu-inbox`——todo 檔與交接本體在 Edit 後、`git mv` 前的中間態不在
   > 掃描豁免範圍內，靠流程原子性避免 tripwire 與沙盤誤報。

4. **todo 收尾執行**（僅步驟 3 有經確認的 todo 時執行；語意比照 `/todo done`，
   該 skill 步驟更新時同步核查本段）：先 `mkdir -p docs/todos/archive/`（目錄
   不存在時 `git mv` 會失敗），再對每筆依序——
   - **殘項清點**（每筆先於 Edit 執行）：Read 該 todo 檔，掃描「下一步」「待辦」
     等段落中未註記完成的子項；無可辨識的子項段落時靜默通過。有殘項時逐項
     回報，由使用者決定各殘項去向（互動沿用步驟 3 慣例：≤4 筆 multiSelect、
     >4 筆數字清單）——**一併視為已解決**（隨檔歸檔）／**轉出為新 todo**
     （使用者裁決即授權，由 session 代建：新檔內文首行註明
     `轉出自 docs/todos/archive/<原slug>.md`——填歸檔後路徑，比照解決依據
     的預期路徑慣例；`source` 填 `manual`）／**保留不歸檔**（該筆整筆退出
     收尾：不 Edit、不 `git add`、不 `git mv`，並自步驟 9 commit 訊息的
     「一併收尾」清單剔除）。status 已是終態的孤兒同樣清點——提示語意改為
     「已標〈status〉但仍有未註記完成子項，歸檔前確認是否轉出」，不改動其
     終態 status。
   - status 非終態者：Edit frontmatter `status` 改「已解決」，標題下方補一行
     `**解決依據**：交接 docs/handoffs/archive/<交接slug>.md 收尾歸檔`（填預期
     歸檔路徑，此時交接本體尚未搬移）；status 已是「已解決」／「已封存」者
     僅跳過本項 Edit（不改 status、不補依據），後續兩項照常執行。
   - `git status --porcelain` 核對該 todo 檔，`??`（untracked）者先 `git add`
     （untracked 檔直接 `git mv` 會以 `not under version control` 失敗）。
   - `git mv docs/todos/<todo-slug>.md docs/todos/archive/<todo-slug>.md`。
   - 任一筆失敗 → 中止剩餘 todo 操作（已完成筆不回滾），記下失敗筆於步驟 9
     回報，續行交接收尾（交接本體仍未動，整段可重跑；已 Edit 未搬移的失敗筆
     會在重跑的步驟 3 以孤兒身分再次列為候選，補歸檔即收斂）。

5. 用 Edit 把交接文件本體 frontmatter `status` 改為 `done`（這是發起方對自己文件
   的生命週期狀態更新，不是接手方回填內容，不違反「本體不編輯」的規則）。

6. **untracked 前置檢查**：`git status --porcelain` 核對交接本體與步驟 2 找到的
   各回覆檔，狀態為 `??`（untracked）者一律先 `git add`（untracked 檔直接
   `git mv` 會以 `not under version control` 失敗；比照 add-project 審核歸檔的
   既有做法）。

7. `git mv docs/handoffs/<slug>.md docs/handoffs/archive/<slug>.md`；若該交接文件
   在 `docs/handoffs/replies/` 有對應回覆檔案，一併 `git mv` 到
   `docs/handoffs/archive/replies/`，讓交接文件與其回覆的歸檔位置保持成對；沒有
   回覆檔案則略過。

8. 檢查是否有其他文件連結指向舊路徑（`grep -Frl "docs/handoffs/<slug>.md" docs/`，
   `-F` 固定字串比對避免 `.` 誤中），逐一修正為 `docs/handoffs/archive/<slug>.md`——
   但 grep 命中**交接文件本體**（含 `archive/` 內）時不修正、僅回報供追溯
   （Invariant #5 本體內文不可變；讀者依檔名為權威識別自行定位，ADR 016）；
   步驟 4 有**成功歸檔**的 todo 時，對每筆同樣檢查
   （`grep -Frl "docs/todos/<todo-slug>.md" docs/`）並逐一修正為
   `docs/todos/archive/<todo-slug>.md`（失敗筆不改連結——其檔案仍在頂層）。

9. 回報歸檔結果（含步驟 4 的 todo 收尾與失敗筆）；步驟 2 沉澱訊號查核有記下
   訊號時，回報中附一句候選教訓提示——「本次往返含〈具名訊號〉，可能值得沉澱
   （一句候選教訓方向），可用 `/ce-compound` 或手動沉澱至 `docs/solutions/`」
   （僅提示、不自動執行，是否沉澱由使用者決定）；無訊號時不輸出任何沉澱相關
   文字。另附**斷言自查**一句（錨定步驟 1–2 已讀文本、不憑印象回想）：逐筆
   點數本輪交接本體與回覆中的他方系統事實斷言——據以實作級區分「已一手查證」
   與「僅標明層級」兩態，後者顯式列為缺口（比照逐項驗收查核的缺口回報慣例，
   由使用者決定收尾或暫緩）；全輪零筆時顯式回報一行「本輪無他方系統斷言」，
   使靜默只剩「查核未執行」一種含義（步驟 2 無回覆的收尾分支照常輸出）。
   僅回報、不強制查證深度。並執行「確認 commit（協議
   步驟）」——`git add` 對象為**歸檔目的地路徑**（`docs/handoffs/archive/<slug>.md`
   與各回覆的 `archive/replies/` 路徑，加上各**成功歸檔** todo 的
   `docs/todos/archive/<todo-slug>.md` 與殘項清點**轉出**的新 todo 頂層路徑
   `docs/todos/<新slug>.md`——失敗筆的 archive 路徑不存在，列入
   `git add` 會以 pathspec 錯誤中斷；`git mv` 不會暫存 working tree 的內容
   修改，porcelain 呈現 `RM`，步驟 5 的 `status: done` 與步驟 4 的 todo Edit
   修改靠這一步 add 帶入 commit）**加上步驟 8 修改的所有檔案路徑**；訊息
   `docs: 歸檔交接 <檔名>`，含 todo 一併收尾時改用
   `docs: 歸檔交接 <檔名>；一併收尾 todo <slug>[、<slug>…]`，殘項清點有
   轉出時再附 `；轉出殘項 todo <slug>[、<slug>…]`（保留不歸檔的筆已自
   「一併收尾」清單剔除，不出現在訊息中）。

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

本檔案是定案快照，完成後**請勿在此檔案內回填任何內容**。請執行以下指令建立回覆檔案：

    /handoff reply 2026-07-02-書籤筆記-bulk-同步-api-契約

或直接於下列路徑新增檔案（`{YYYY-MM-DD}` 為回覆當天日期；分階段回報多次時每次建立新檔案，不要覆寫前一份回覆）：

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

回覆檔 `status` 值：`submitted`（預設，已完成待發起方確認）／`partial`（部分完成，後續會再回報）／`blocked`（卡關）／`done`（已結案——**由發起方經 `/handoff done` 對交接本體執行，接手方回覆請勿自標**；自標會使此交接從 `/kunsu-inbox` 與軍師沙盤消失，本體卻仍留在頂層未歸檔）。另可加選填欄位 `verify:` 標注驗收方式——`needs-deploy`（需上線測試）／`testable-now`（馬上可測）／`needs-device`（需實機測試）或自由字串，無明確驗收需求則省略。

中途需切換任務時，請先投遞暫離回報——`status: partial`、內文附 branch 名與現況，之後回來再照常回覆。
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
verify: needs-deploy
---

# 書籤筆記 bulk 同步 API 契約 — 回覆

狀態：完成。API 已實作並通過本機測試，需部署上線後以正式環境驗證。契約與驗收標準如下……
```

## 注意

- **交接文件與回覆檔案皆為 append-only、永遠只有單一作者，兩者互不編輯**：
  交接文件本體只有發起方寫（建立後除 `done` 步驟更新 `status` 外不再改動），
  回覆檔案只有接手方寫（每次回覆是新檔案，不覆寫前次回覆）。這是避免多方共編
  同一檔案造成版本漂移的關鍵，不是形式而已。
- 日期一律以 `date +%F` 取系統實際日期，不要臆測。
- 交接文件**本體**的 `status` 值：`open`（待接手，預設）／`in-progress`（接手方
  研究中）／`done`（已完成）。**回覆檔**的 `status` 值域不同：`submitted`（預設）
  ／`partial`／`blocked`／`done`，兩者不可混用。回覆檔的 `done` 一般不由接手方
  自標（限制說明見「檔案格式範例」段）——結案動作是發起方對**本體**執行
  `/handoff done`。
- 回覆檔選填欄位 `verify:`（驗收方式）：建議代碼 `needs-deploy`（需上線測試）／
  `testable-now`（馬上可測）／`needs-device`（需實機測試），開放值域（其他自由
  字串原樣顯示），缺省不顯示。display-only——不參與任何比對邏輯，`/kunsu-inbox`
  與軍師沙盤據此顯示標籤。
- `from`／`to` 是交接文件的靈魂，務必填正確方向，Dataview 才能依角色過濾。
- 現況分析要引用具體 `檔案:行號` 與資料結構，接手方在**不同程式碼庫**時尤其重要。
- 內文不要再重複打 `# 標題`（腳本已自動產生一次）；若內文本身已包含「背景 /
  目標」等段落標題與內容，腳本不會再重複附加空白骨架。
- 多個議題請逐一建檔，不要把不同交接塞進同一個檔。
- `done` 是「搬到 archive + 改 status」，不是刪檔案。
