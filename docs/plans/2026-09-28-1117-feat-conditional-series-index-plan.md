---
title: 條件式線總表與產檔訊號 - Plan
type: feat
date: 2026-09-28
topic: conditional-series-index
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-brainstorm
execution: code
---

# 條件式線總表與產檔訊號 - Plan

## Goal Capsule

- **Objective**：軍師發交接時，能回答「這條工作線總共幾份、還缺哪幾份」；「該立總表了」的提醒落在發第三份交接的那一刻，由腳本計算給出，不再靠 session 記得工作流程第 3 步。
- **Means**：範本工作流程第 3 步改為條件式（KD1、KD4）；線總表為軍師自寫的 `docs/plans/` 輕量檔，frontmatter 帶 `series`（KD3）；`new-handoff.sh` 新增 `series` 參數，同 series 每份印計數、第三份起找不到對應總表即於 stderr 印出可貼上的總表骨架（KTD1、KTD4、KTD5）；三 live 軍師 CLAUDE.md 與 CONCEPTS 第十二波遷移（KTD7）。
- **Product authority**：本文件的 Product Contract；kunsu `CLAUDE.md` 四條 Invariants；ADR 009（確認 commit）、ADR 016（定案快照與生命週期 metadata 邊界）；全域 CLAUDE.md「CE 指令由使用者發起，session 不自行觸發」維持不動。
- **Execution profile**：單一 repo 六個單元依序落地，第十二波遷移觸及三 live 軍師 repo（各一筆確認 commit，走 ADR 009 阻塞式確認）；母體不主動 commit、絕不 push。
- **Stop conditions**：`scripts/consistency-check.sh` 任一項 FAIL 未收斂；沙盤或 kunsu-inbox pytest 出現回歸；三 live 遷移錨句 grep 非恰中一次；`series` 拒收規則使既有 dogfooding fixture 無法產檔。
- **Tail ownership**：ce-work 完成後接 ce-simplify-code 與 ce-code-review；commit 由使用者明確要求時執行；`install.sh` 重佈署與沙盤重啟由本 session 執行。
- **Open blockers**：無。
- **Product Contract preservation**：changed: R2、R3、R5、R6 — 依規劃期研究修訂：R2 補更正交接歸屬與早期份次人工補列；R3 改為對既有句附加而非取代（`docs/plans/` 同時容納使用者發起的深規劃）；R5 補 YAML 敏感字元拒收；R6 由「未達 3 份靜默」改為「給了 `series` 一律印計數行」並補提醒內容（骨架、grep 範式、多筆總表、近似值列出）。四項均於 2026-09-28 規劃綜整經使用者確認；同日 doc review 再修 R6／R7（總表路徑行不受計數閘、`docs/plans/` 不存在視為零總表），經使用者確認套用。

---

## Product Contract

### Summary

把範本工作流程第 3 步從「一律以 ce-plan 寫入 docs/plans」改為條件式，總表改由軍師自寫輕量檔並以 frontmatter `series` 與交接對齊；產檔腳本對帶 `series` 的交接印出同線計數，第三份起找不到總表時印出可貼上的總表骨架，有總表時印出路徑提醒更新份次狀態。

### Problem Frame

ebook 軍師的 18 份 plan 集中於 2026-07-03 至 08-07，之後約 140 份交接零新 plan；iOS 底層移植線八份交接的第四至八份範圍只存在於前幾份的交叉引用與排除項裡，回答「還剩什麼」必須翻遍所有交接、回覆與停車紀錄（見 ebook `docs/solutions/documentation-gaps/handoff-series-scope-needs-an-index-not-cross-references.md`）。同一缺口在 2026-08-13 的 todo 已記錄一次，一週後以同形態再發生。

2026-09-27 依 ebook 軍師 27 個 session 紀錄（2026-08-25 起，更早的已滾動清除）分析第 3 步為何被跳過，成因分三層，皆有證據：

1. **規則結構互鎖**：全域 CLAUDE.md「CE 指令由使用者發起，session 不自行觸發」逐字載入每個軍師 session，而本地第 3 步要求 session「以 ce-plan skill 寫入」。模型不能自己跑，使用者在軍師 repo 輸入 `/ce-plan` 的次數為 0（子專案 repo 有 3 次）。第 3 步從結構上是死信。
2. **使用者起手語直指第 5 步**：抽樣 10 例交接產出，8 例是「發交接給 android」「照 A 出兩份交接」「收一下上報」，0 例是「幫我規劃 X」。模型執行的是被點名的動作。
3. **議題從未被喚起，不是明知故犯**：139 次 `new-handoff.sh` 呼叫，assistant 文字沒有一句「不需要 plan，直接發交接」。與 2026-08-29 分析的「自然語言指示不觸發 skill 聯想」、2026-08-31 的「敘述性紀律靠記得，指令化步驟才兌現」同形。

第四個現象是 plan 層已被架空：兩次使用者問「iOS 進度到哪」，模型都掃 handoffs 與 replies 的 status 作答，完全沒讀 `docs/plans/`；8/21 事後補的總表之後也沒人讀。

只把第 3 步改成條件式，三個成因一個都沒碰——載體還是同一份文件、觸發點仍不在發交接那一刻、ce-plan 死結還在。修法必須解掉成因 1，並把訊號掛到成因 2、3 的實際觸發點：產檔腳本是手動路徑上唯一每次都被呼叫的載體（2026-08-29 分析：產檔腳本 14/14 被呼叫，skill 0/23）。純指路型的 stderr 行（「見 SKILL.md 某段」）在同一分析裡 14 次觸發 0 次兌現，印出實際資料的查重候選清單則被採用——提醒內容因此必須是可直接動手的材料，不是指路。

### Key Decisions

- KD1. **解死結並掛觸發點，而非只改範本字面**（session-settled: user-directed — chosen over 只改第 3 步字面為條件式：字面改動不改變載體與觸發點，同一失效形狀已在 ebook 發生兩次）。Governs R1, R5, R6。
- KD2. **同一線以交接 frontmatter 新欄 `series` 判定**（session-settled: user-directed — chosen over depends_on 鏈長度與標題前綴比對：三 live 軍師 `depends_on` 合計僅 4 檔、平行分梯次的線多半無邊，覆蓋率近零；標題前綴誤判雙向）。Governs R5, R7。
- KD3. **線總表落 `docs/plans/` 輕量檔，frontmatter `series` 與交接對齊**（session-settled: user-directed — chosen over `docs/handoffs/` 內的 series 檔：後者要逐一豁免信箱掃描、依賴圖建圖、歸檔形狀與 git 守門四套機制；前者 kb 索引、範本目錄表與盤點優先序零改動）。Governs R2, R3, R6。
- KD4. **總表由軍師自寫，不經 ce-plan**：解成因 1；ce-plan 仍由使用者主動發起用於深規劃。Governs R1, R3。
- KD5. **有總表時腳本也印一行總表路徑**（session-settled: user-approved — chosen over 有總表即靜默：發完每份後更新份次狀態是總表活著的前提，路徑提示是最便宜的讀寫接點）。Governs R6。
- KD6. **單份或兩份交接的跨端介接規格只靠交接本體承載**（session-settled: user-approved — chosen over 保留 plan 作為 API 契約落點：第 5 步既已要求交接本體含介接規格，雙落點只會重演 plan 被架空）。Governs R1。
- KD7. **訊號只提醒不阻擋**：沿用 harness 不做枷鎖、信息補全優於行為強制的設計前提；`series` 缺省零訊號，與 `depends_on` 同型。Governs R5, R6。
- KD8. **不回填既有交接與 ebook 8/21 總表的 `series`**（session-settled: user-approved — chosen over 遷移波次一併回填：訊號屬 advisory，回填只增遷移面不增觸及率）。Governs R9。
- KD9. **給了 `series` 就一律印一行計數，只有未給 `series` 才靜默**（session-settled: user-approved — chosen over 未達 3 份靜默：「正常無需提醒」「偵測失敗放棄」「根本沒給參數」三種靜默同形，agent 無從分辨訊號缺席與機制缺席）。Governs R6。
- KD10. **更正交接可帶原線 `series`；計數是「同線本體數」不是份次編號**（session-settled: user-approved — chosen over 更正交接不帶 `series`：`series` 是歸屬標記，grep 一次要能撈齊整線；份次編號由總表人工維護）。Governs R2, R6。

### Requirements

**範本工作流程（kunsu-init）**

- R1. 範本工作流程第 3 步改為條件式：單份或兩份交接可解的需求不立 plan，介接規格寫進交接本體（第 5 步既有要求）；同一工作線預計拆三份以上交接時，發第一份前先立線總表。ce-plan 由使用者主動發起時仍可用於深規劃，第 3 步不再要求 session 以 ce-plan 寫入。
- R2. 線總表最小內容只回答四問：份次清單（含暫定份次，暫定者標為推論；標記 `series` 之前已發出的份次由軍師人工補列）、每份範圍摘要、相依順序（可與 `depends_on` 互相指涉）、各份狀態（未發／已發／已驗收）。總表不是 spec，不寫介接規格細節。份次編號帶線別（如「iOS 底層移植第六份」）。更正交接屬同線歸屬、不占份次編號，總表以註記標示其更正對象。
- R3. 線總表落於 `docs/plans/`，frontmatter 含 `series: <線別名>`，值與該線交接本體的 `series` 精確一致；範本第 6 步與回覆信箱協議的「更新 docs/plans」「彙整進 docs/plans」兩句各附加「（線總表則更新份次狀態）」而非取代，並補一句「回答線進度以線總表為起點、以交接與回覆狀態核對；以 `grep -rlF 'series: <線別名>' docs/plans/` 定位總表」。
- R4. 範本 kunsu-concepts「定案規劃」詞條補條件式與線總表語意；母體 CONCEPTS「線總表」詞條已於需求定案時新增，規劃期只核對與落地字面一致。

**產檔腳本訊號（handoff）**

- R5. `new-handoff.sh` 新增選填第 7 參數 `series`，寫入本體 frontmatter `series: <線別名>`；缺省不產生欄位。值先 trim；trim 後含 YAML flow／註解敏感字元（`:`、`#`、`,`、`"`、`'`、`[`、`]`、`{`、`}`、`|`、`>`、`&`、`*`、`!`、`%`、`@`、反引號）或為空時，腳本於寫檔前以 exit 1 拒收並於 stderr 說明可用字元。比對一律 trim 後精確比對，不做大小寫或模糊正規化。
- R6. 產檔後，腳本對帶 `series` 的交接計算同 `series` 交接本體數（`docs/handoffs/` 頂層與 `archive/`，含本次產出檔；`replies/` 不計），並於 stderr 印一行「線別「X」：同線已有 N 份交接本體」。給了 `series` 就掃 `docs/plans/` 找 frontmatter `series` 相同的檔案，不受計數閘：恰一檔時印總表路徑並提醒更新該份狀態；多於一檔時全部列出並標 ⚠；零檔且計數達 3 時印立線總表提醒——建議路徑（`docs/plans/` 不存在時前附 `mkdir -p docs/plans` 一行，腳本不代建）、可貼上的 frontmatter 骨架（含 `series`）、四問空白清單、定位用的 `grep -rlF` 範式，`docs/plans/` 存在其他 `series` 值時另列出既有值供辨識手誤；零檔且計數未達 3 時只印計數行。提醒為無狀態判定，每次產檔重新計算、不因「已提醒過」消音。未給 `series` 時整段靜默。
- R7. 訊號維持產檔腳本三不變條件：stdout 仍為單行路徑、產出檔內容除新增 `series` 欄外不變、exit code 不變（R5 拒收發生在寫檔前，屬輸入驗證、不在此列）；`docs/plans/` 不存在視為零總表（走 R6 分支），偵測階段的讀檔錯誤才 fail-open，並印一行「線總表偵測略過：<原因>」使其與正常靜默可辨。
- R8. handoff SKILL 的 add 用法列、產檔參數說明段（呼叫範例改為七參數全列並註明佔位）、回覆信箱協議「本體選填欄位」段補 `series` 說明（含可用字元規則與手動 Write 交接時同樣適用），與 `depends_on` 既有段落相鄰；kunsu-inbox 依賴聲明版號同步。

**遷移與檢查**

- R9. ebook／ivm／px 三 live 軍師 CLAUDE.md 第 3 步、第 6 步與回覆信箱協議句，以及 CONCEPTS「定案規劃」詞條同波遷移（第十二波），錨句 grep 恰中一次才動；既有交接本體與 ebook 8/21 總表不回填 `series`。
- R10. `scripts/consistency-check.sh` 涵蓋新字面：產檔腳本 `series` 參數實跑（欄位位置與值）、stderr 提醒與計數行以實跑擷取比對錨句、範本與三 live 第 3 步條件式錨句、CONCEPTS 詞條雙檔比對；每個新增錨句於實作時各做一次「改壞字面應 FAIL」的負向驗證；全項照常通過。

### Key Flows

- F1. 發同線第一、二份
  - **Trigger:** 軍師以 `new-handoff.sh` 產檔並給 `series`。
  - **Steps:** 腳本驗證 `series` 字元；寫入 `series` 欄；計數 1 或 2；stderr 印計數行；已有總表則另印路徑行，無總表不印骨架提醒。
  - **Covered by:** R5, R6
- F2. 發同線第三份，尚無總表
  - **Trigger:** 同 series 本體計數達 3，`docs/plans/` 無對應 `series`。
  - **Steps:** stderr 印計數行、建議路徑、frontmatter 骨架、四問清單、grep 範式；軍師依骨架自寫線總表（R2、R3）；產檔不受影響。
  - **Covered by:** R2, R3, R6, R7
- F3. 總表已立，續發後續份次
  - **Trigger:** `docs/plans/` 有對應 `series`（不限計數）。
  - **Steps:** stderr 印計數行與總表路徑一行；軍師更新該份狀態。
  - **Covered by:** R3, R6
- F4. 使用者問「這條線還剩什麼」
  - **Trigger:** 對話中的進度提問。
  - **Steps:** 軍師依範本指路句以 `grep -rlF` 定位線總表，再以交接與回覆狀態核對。
  - **Covered by:** R3

### Acceptance Examples

- AE1. **Covers R5, R6.** Given 暫存軍師 repo 無任何 `series`，When 以 `series=線A` 連發兩份，Then 兩份 frontmatter 含 `series: 線A`，stderr 各有一行計數（1、2），無立總表提醒。
- AE2. **Covers R6.** Given 線A 已有兩份，When 發第三份，Then stderr 出現計數行「3」與立總表提醒（含建議路徑、`series: 線A` 骨架、四問清單、`grep -rlF 'series: 線A' docs/plans/`），stdout 仍為單行路徑，exit 0。
- AE3. **Covers R3, R6.** Given `docs/plans/` 有一檔 frontmatter `series: 線A`，When 發線A 第四份，Then stderr 印該總表路徑一行，無立總表提醒。
- AE4. **Covers R5, R7.** Given 未給 `series`，When 產檔，Then 本體無 `series` 欄，stderr 無任何線總表相關輸出（與既有行為一致）。
- AE5. **Covers R6.** Given 線A 兩份已歸檔至 `archive/`、頂層零份，When 發第三份，Then 計數為 3，觸發提醒。
- AE6. **Covers R6.** Given `docs/handoffs/replies/` 有含 `series: 線A` 的回覆檔，When 計數，Then 回覆檔不計入。
- AE7. **Covers R6, R7.** Given `docs/plans/` 不存在，When 發第三份，Then 產檔照常、stdout 單行、exit 0，stderr 印立總表提醒且建議路徑前附 `mkdir -p docs/plans`，腳本不建立該目錄。
- AE15. **Covers R6.** Given `docs/plans/` 已有 `series: 線A` 的總表而線A 尚無交接，When 發第一份，Then stderr 印計數 1 與總表路徑行。
- AE16. **Covers R7.** Given `docs/plans/` 存在但其中一檔不可讀，When 發第三份，Then 產檔照常、exit 0，stderr 印「線總表偵測略過：<原因>」。
- AE8. **Covers R9, R10.** Given 三 live 軍師遷移完成，When 執行 `scripts/consistency-check.sh`，Then 全項 PASS，範本與三 live 第 3 步條件式字面逐字一致。
- AE9. **Covers R5.** Given `series` 值前後帶空白或大小寫不同，When 比對，Then 只 trim、不做大小寫正規化，大小寫不同視為不同線。
- AE10. **Covers R6.** Given 第三份已印過立總表提醒但軍師未建總表，When 發第四、五份，Then 每次都再印同一提醒。
- AE11. **Covers R5.** Given `series` 值為「後端: API」或「線 #3」，When 產檔，Then 不寫任何檔案、exit 1、stderr 說明可用字元；`docs/handoffs/` 無新檔。
- AE12. **Covers R6.** Given `docs/plans/` 兩檔 frontmatter 皆為 `series: 線A`，When 發線A 第四份，Then 兩條路徑全列並標 ⚠ 同 series 總表多於一檔。
- AE13. **Covers R6.** Given `docs/plans/` 只有 `series: 線a`（小寫）而交接為 `線A`，When 發第三份，Then 印立總表提醒，並列出既有 `series` 值「線a」供辨識手誤。
- AE14. **Covers R2, R6.** Given 線A 已三份，When 發更正交接並帶 `series: 線A`，Then 計數為 4（本體數），提醒文字不宣稱份次編號。

### Scope Boundaries

- 沙盤、SessionStart hook、kunsu-inbox 依 `series` 聚合顯示「已發幾份、各份狀態、還缺哪幾份」——留給「還缺什麼」視圖（idea `docs/ideas/2026-09-27-還缺什麼視圖軍師欠辦行動項與工作線剩餘範圍的可見性.md`），本計畫只確保資料層（`series` 欄與總表）存在。
- 不對「立總表」加任何阻擋式關卡；不修改全域 CLAUDE.md。
- `new-report.sh`、`new-handoff-reply.sh` 不加 `series`；`depends_on` 語意零改動；`app/handoff_graph.py` 不讀 `series`。
- 總表份次狀態由軍師人工更新，不做自動推導，不偵測總表過期。
- 既有交接與總表不回溯補 `series`（KD8）；標記前已發的份次只靠總表人工補列（R2）。
- `kc --slot` 多 session 同時發同線時計數可能各自少算一份，屬 advisory 訊號已接受的限制。
- 手動 Write 交接繞過 R5 驗證，只靠 SKILL 協議段字面約束（R8），與既有腳本護欄同型。

#### Deferred to Follow-Up Work

- ebook CONCEPTS「定案規劃」詞條首句仍寫「規劃協調中心」（ADR 005 前用語），與範本首句不同；第十二波只以尾句為錨插入，首句漂移另記 todo。
- 查重 12 行窗口在同時有 `depends_on` 與 `series` 時只剩 1 行餘裕；再加第三個選填欄位時須連動放寬窗口常數。

### Dependencies / Assumptions

- 產檔腳本是手動路徑上每次都被呼叫的載體（2026-08-29 ebook 分析：14/14），訊號掛在此才有觸及率；此假設若因 session 改以 Write 直接落檔而失效，訊號同樣缺席（與 `depends_on`、產檔查重同型）。
- 產檔查重只讀交接 frontmatter 前 12 行，`series` 欄置於 `depends_on` 之後、閉合 `---` 之前，兩欄同時存在時 frontmatter 為 11 行，仍在窗口內。
- ADR 016 四要件：`series` 為派發時寫入的定案快照內容，非生命週期 metadata，事後不編輯本體；線別變更走更正交接。
- 沙盤 `app/handoff_graph.py` 以 `yaml.safe_load` 解析整塊 frontmatter：`series` 值只要不含 YAML 敏感字元即為純量字串，不影響既有 `depends_on` 推導（R5 拒收規則的依據）。

### Outstanding Questions

**Deferred to Planning**

- 無（規劃期已定：`series` 位置與 12 行窗口、總表骨架附於 stderr 與 SKILL 協議段、提醒定型行納入 consistency-check 實跑錨句）。

### Sources / Research

- idea：`docs/ideas/2026-09-27-範本工作流程第3步plan降為條件式一線拆三份以上交接才立輕量總表.md`、`docs/ideas/2026-09-03-交接前置規劃深度的張力UncleBob反SDD論點對照跨repo介接規格前置.md`
- ebook 軍師：`docs/solutions/documentation-gaps/handoff-series-scope-needs-an-index-not-cross-references.md`、`docs/2026-08-29-軍師機制失效分析-手動執行等效步驟使skill指引靜默失效.md`、`docs/2026-08-31-沉澱機制失效調查報告-需要比沉澱更好的方式.md`、`docs/plans/2026-08-21-iOS底層移植八份交接梯次規劃.md`（事後補的總表，frontmatter 為 `title/date/topic/status/type/tags`，無 `series`）
- 既有機制：`skills/handoff/scripts/new-handoff.sh`（第 6 參數 `depends_on` 為 `series` 參數的先例；`dedup_check || true` 為 fail-open 先例；`sed -n '1,12p'` 查重窗口）、`skills/handoff/SKILL.md` add 段（用法列、參數說明段、協議段「本體選填欄位 `depends_on:`」）、`skills/kunsu-init/assets/templates/kunsu-claude.md` 第 3 步（與三 live 逐字一致）、`scripts/consistency-check.sh` C2（第 6 參數實跑）、K（stderr 實跑擷取）、H 鏈（live 軍師雙檔錨句）
- 本 repo 教訓：`docs/solutions/workflow-issues/handoff-intercept-point-selection.md`（訊號效力寫條件式）、`docs/solutions/workflow-issues/handoff-done-closure-gap.md`（副本清單窮舉、遷移恰中一次）、`docs/solutions/workflow-issues/assertion-level-discipline-coverage-gap.md`（shell 產生文字須實跑比對、靜默單義化）、`docs/solutions/workflow-issues/literal-replacement-residue-and-review-triage.md`（範本瑕疵是廣播、pathspec 精確）
- 相關 ADR：ADR 014（事件驅動掛載點）、ADR 016（定案快照與生命週期 metadata 邊界）

---

## Planning Contract

### Key Technical Decisions

- KTD1. **`series` 於寫檔前驗證，敏感字元拒收 exit 1，不加引號跳脫**（session-settled: user-approved — chosen over 以雙引號跳脫寫入：跳脫後每個讀端（腳本比對、總表手寫、`grep -rlF`）都要處理引號，且沙盤 `yaml.safe_load` 對壞值會使整份交接連 `depends_on` 一起變「無法解析」，拒收是唯一零讀端成本的做法）。Governs R5。實作：以 R5 列舉的敏感字元黑名單拒收，用 bash glob `*[...]*` 比對、不依賴 locale 字元類別（macOS bash 3.2 在 `LC_ALL=C` 下 `[[:alpha:]]` 不含中文，白名單會把所有中文線別擋掉），trim 後為空亦拒收；驗證位於現有「缺少標題」檢查之後、任何寫檔之前。
- KTD2. **`series` 欄位置緊接 `depends_on` 之後（無 `depends_on` 則緊接 `tags:`）、非空才印**。理由：與 `depends_on` 同型、查重 12 行窗口兩欄並存仍餘 1 行；consistency-check 以行號相對位置斷言。Governs R5。
- KTD3. **`docs/plans/` 掃描以純 bash 讀至閉合 `---`，`series:` 行 trim 後精確比對**。理由：既有 `dedup_check` 同型純 bash，不引入 python3；`docs/plans/` 兩種 frontmatter schema 並存（舊 `title/type/status/date` 與 ce-unified-plan），固定 12 行不可靠；以第 1 行等於 `---` 為起點，無 frontmatter 的檔（ivm 有兩份）直接跳過，避免有水平線而無 frontmatter 的檔被讀進內文。同線計數以單次 `grep -lxF -- "series: $SERIES"` 掃頂層與 `archive/*.md` 取候選再驗 `type: handoff`（ebook 304 份本體逐檔 sed 實測 1.8 秒，單次 grep 0.02 秒），比對一律 `-F`。Governs R6。
- KTD4. **線總表偵測獨立函式，整段 `|| true` fail-open，stderr 三態文案**：計數行（一律）、提醒或總表路徑（條件）、偵測略過（失敗）；未給 `series` 整段不呼叫。定型行只在腳本一處，consistency-check 以實跑擷取 stderr 比對錨句（K 項方法），SKILL.md 只描述不複製。Governs R6, R7, R10。
- KTD5. **提醒內容為可貼上材料**：建議路徑 `docs/plans/<今日>-<series 去空白>-線總表.md`、frontmatter 骨架（`title`、`type: plan`、`date`、`series`）、四問空白表頭、`grep -rlF 'series: <線別名>' docs/plans/`。理由：2026-08-29 分析純指路行 14/0 兌現、印實際資料的查重候選被採用。Governs R6。
- KTD6. **版號**：handoff 0.23.0 → 0.24.0（新參數）、kunsu-init 0.9.1 → 0.10.0（範本工作流程語意變更）、kunsu-inbox 0.15.0 → 0.15.1（依賴聲明句追加 v0.24.0 註記，掃描慣例零改動）。母體 CLAUDE.md 結構樹 handoff 行版號同步。
- KTD7. **第十二波遷移**：三 live CLAUDE.md 三處錨句（第 3 步四行整段、第 6 步「更新 `docs/plans/` 或產出下一輪交接文件」、同步時機「彙整進 `docs/plans/`（更新決策、記錄落差）」）與 CONCEPTS「定案規劃」尾句「不留在只有單一 session 知道的地方」為錨；`grep -cF` 舊句恰中一次才替換，遷移後新句命中、舊句歸零、`git diff --stat` 僅 CLAUDE.md 與 CONCEPTS.md；每軍師一筆確認 commit 帶精確 pathspec（ADR 009 阻塞式確認）。Governs R9。
- KTD8. **SKILL 呼叫範例改為七參數全列**（`"<標題>" "<from>" "<to>" "<tags>" "<查重關鍵詞>" "<depends_on>" "<series>"`，並註明空字串佔位）。理由：`depends_on` 第 6 參數三 live 合計 4 檔，位置靠後的選填參數若範例不帶滿會被系統性漏填。Governs R8。

### High-Level Technical Design

產檔腳本尾端新增的線總表偵測（directional，非實作規格）：

```mermaid
flowchart TB
  A[產檔完成 stdout 印路徑] --> B{有給 series?}
  B -->|否| Z[整段靜默]
  B -->|是| C[計數同 series 本體<br/>頂層 + archive/，replies 不計]
  C --> D[stderr：線別 X 同線已有 N 份]
  D --> F[掃 docs/plans/*.md frontmatter 至閉合 ---<br/>目錄不存在視為零檔]
  F --> G{series 相同的檔數}
  G -->|1| I[印總表路徑，提醒更新該份狀態]
  G -->|>=2| J[全列並標 ⚠]
  G -->|0| E{N >= 3?}
  E -->|否| Z2[結束]
  E -->|是| H[印立總表提醒：路徑（目錄缺則附 mkdir -p）、骨架、四問、grep 範式<br/>另列既有 series 值]
  C -.讀檔錯誤.-> K[印「線總表偵測略過：原因」，|| true]
  F -.讀檔錯誤.-> K
```

`series` 驗證（KTD1）發生在流程圖之前、寫檔之前，與「缺少標題」同層。

### Assumptions

- 三 live 軍師 CLAUDE.md 第 3 步四行、第 6 步句、同步時機句與範本逐字一致（claim verifier 2026-09-27 確認：ebook 110／123／167、ivm 86／99／134、px 104／117／152）。
- ebook CONCEPTS「定案規劃」尾句與範本一致、首句不一致（已實測），錨定尾句可安全插入。
- `consistency-check.sh` 現行 34 項全 PASS，新增檢查以 `ok`／`ng`／`wn` 慣例累計。

### Sequencing

U1 → U2 → U3 → U4 → U5 → U6。U4 依賴 U1（實跑腳本）與 U3（範本錨句）；U5 依賴 U3 定稿字面與 U4（H 鏈可驗）；U6 收尾。

---

## Implementation Units

### U1. 產檔腳本 `series` 參數、驗證與線總表偵測

- **Goal**：`new-handoff.sh` 接受第 7 參數 `series`，寫入 frontmatter，產檔後依 KTD3–KTD5 印出計數、提醒或總表路徑。
- **Requirements**：R5, R6, R7；KTD1–KTD5；AE1–AE7、AE9–AE16。
- **Dependencies**：無。
- **Files**：`skills/handoff/scripts/new-handoff.sh`。
- **Approach**：
  1. 檔頭用法註解加第 7 參數與第 8 點行為說明（比照第 7 點 `depends_on` 段落）。
  2. 讀 `SERIES_RAW="${7:-}"`，trim；非空時以白名單驗證（KTD1），不合即 stderr 說明並 `exit 1`，位置在「缺少標題」檢查之後、`mkdir -p` 之前。
  3. frontmatter 寫入區在 `depends_on` 行之後加 `if [[ -n "$SERIES" ]]; then printf 'series: %s\n' "$SERIES"; fi`（KTD2）。
  4. 新增 `series_index_check()` 函式置於 `dedup_check || true` 之後、指路行之前：計數依 KTD3（單次 `grep -lxF` 取候選、再驗 `type: handoff`；頂層與 `archive/*.md`，排除 `replies/`）；`docs/plans/*.md` 以第 1 行為 `---` 起算、awk 讀到第二個 `---` 為止比對 `series:`，目錄不存在視為零檔；三態文案走 stderr；整段 `series_index_check || true`；未給 `series` 時不呼叫。
  5. 提醒定型行固定字面（供 U4 錨句）：計數行「ℹ 線別「X」：同線已有 N 份交接本體」；提醒首行「⚠ 本線已達 3 份仍無線總表，請先立總表再續發：」；總表行「ℹ 本線總表：<path>（發完請更新該份狀態）」；略過行「ℹ 線總表偵測略過：<原因>」。
  6. 陣列展開沿用 `"${arr[@]+"${arr[@]}"}"` 防呆；不用 `date -v` 以外的新平台相依。
- **Execution note**：先在暫存 repo 以 AE2、AE11 的輸入手動實跑確認 stderr 形狀，再回填 U4 的錨句。
- **Patterns to follow**：`depends_on` 第 6 參數的正規化與寫入（`new-handoff.sh` 第 91–109、134–136 行）；`dedup_check` 的 stderr-only 與 `|| true`（第 203–353 行）；`sed -n '1,12p'` 讀 frontmatter 與 `grep -q '^type: handoff$'` 過濾。
- **Test scenarios**（暫存 repo 實跑，無 pytest）：
  - Covers AE1. 連發兩份 `series=線A` → 兩檔第 9 行（無 depends_on）為 `series: 線A`，stderr 含計數 1、2，無提醒。
  - Covers AE2. 第三份 → stderr 含「同線已有 3 份」與提醒首行、`series: 線A` 骨架、`grep -rlF 'series: 線A' docs/plans/`；stdout 恰一行；exit 0。
  - Covers AE3. `docs/plans/x.md` 含 `series: 線A` → 第四份 stderr 含總表路徑行，無提醒首行。
  - Covers AE4. 不給第 7 參數 → 本體無 `series:` 行，stderr 無「線別」「線總表」字樣。
  - Covers AE5. 兩份移至 `archive/` 後發第三份 → 計數 3。
  - Covers AE6. `replies/` 放入含 `series: 線A` 的檔 → 計數不變。
  - Covers AE7. 刪除 `docs/plans/` 後發第三份 → stderr 含提醒首行與 `mkdir -p docs/plans`，exit 0，檔案已產，`docs/plans/` 仍不存在。
  - Covers AE15. 先建 `docs/plans/x.md` 含 `series: 線A` 再發線A 第一份 → stderr 含計數 1 與總表路徑行。
  - Covers AE16. `docs/plans/` 內放一個不可讀檔（`chmod 000`）後發第三份 → stderr 含「線總表偵測略過」，exit 0。
  - `LC_ALL=C` 環境下 `series=線A` → 照常產檔並寫入 `series: 線A`（黑名單不依賴 locale）。
  - Covers AE9. `series=" 線A "` → 寫入 `series: 線A`；`series=線a` 與 `線A` 各自計數。
  - Covers AE10. 第四、五份仍無總表 → 每次都印提醒首行。
  - Covers AE11. `series="後端: API"`、`"線 #3"`、`"a,b"` → exit 1、`docs/handoffs/` 無新檔、stderr 含可用字元說明。
  - Covers AE12. `docs/plans/` 兩檔同 `series` → 兩路徑全列且含 ⚠。
  - Covers AE13. 只有 `series: 線a` 總表、交接 `線A` → 提醒含「既有 series 值：線a」。
  - Covers AE14. 更正交接帶 `series: 線A` → 計數含之。
  - 同時給 `depends_on` 與 `series` → frontmatter 共 11 行，`series` 行緊接 `depends_on` 行之後。
  - `docs/plans/` 含 ce-unified-plan schema 檔（10 行 frontmatter）且 `series` 在第 9 行 → 仍命中。
- **Verification**：上列情境全部符合；既有 consistency-check C／C2／J 項照常 PASS（stdout 單行、exit code、定型文字兩副本不變）。

### U2. handoff SKILL 字面與版號

- **Goal**：SKILL.md 說明第 7 參數、可用字元、提醒行為與手動 Write 同樣適用；版號升 0.24.0；kunsu-inbox 依賴聲明與母體 CLAUDE.md 結構樹同步。
- **Requirements**：R8；KTD6、KTD8。
- **Dependencies**：U1（定型行字面）。
- **Files**：`skills/handoff/SKILL.md`、`skills/kunsu-inbox/SKILL.md`、`CLAUDE.md`（結構樹 handoff 行）。
- **Approach**：
  1. 用法列（第 85 行）加 `[series]`。
  2. add 段「上游依賴」項之後加「線別」項：何時給（同一線預計 ≥3 份或已達 3 份）、值即總表 `series`、可用字元、更正交接可帶原線 `series`。
  3. 建檔指令範例（第 175–177 行）改七參數全列並註明空字串佔位；參數說明段（第 181–187 行）補第 7 參數與 stderr 三態行為描述（描述不複製定型行）。
  4. 協議段「本體選填欄位 `depends_on:`」之後加「本體選填欄位 `series:`」：歸屬標記、位置、可用字元、手動 Write 亦須遵守、消費端為產檔腳本（沙盤與 hook 不讀）。
  5. frontmatter `version: 0.24.0`；kunsu-inbox 依賴聲明句尾追加「、v0.24.0 的 `series` 線別欄與線總表提醒為 add 產檔內部訊號」並改版號 0.15.1；母體 CLAUDE.md 結構樹 handoff 行 `v0.23.0` → `v0.24.0`。
- **Patterns to follow**：`depends_on` 在同三處的既有寫法（第 85、155–158、181–187、721–722 行）。
- **Test scenarios**：Test expectation: none -- 純文件；由 U4 的 consistency-check 版號鏈（A 項）與 M 項 Agent 對應表逐字一致驗證。
- **Verification**：`consistency-check.sh` 版號鏈 PASS；SKILL 內三處 `series` 說明可被 `grep -c` 各命中。

### U3. 範本第 3 步條件式與 kunsu-concepts 詞條

- **Goal**：範本工作流程第 3 步改條件式，第 6 步與同步時機句附加線總表語意，kunsu-concepts「定案規劃」詞條補條件式與線總表；kunsu-init 版號 0.10.0。
- **Requirements**：R1, R2, R3, R4；KD1、KD4、KD6。
- **Dependencies**：無（與 U1 平行可行，但 U5 依賴其定稿）。
- **Files**：`skills/kunsu-init/assets/templates/kunsu-claude.md`、`skills/kunsu-init/assets/templates/kunsu-concepts.md`、`skills/kunsu-init/SKILL.md`（版號）、`CONCEPTS.md`（核對「線總表」詞條與落地字面一致）。
- **Approach**：
  1. 第 3 步四行改寫為：「3. **線總表（條件式）**：單份或兩份交接可解的需求不立 plan，介接規格寫進交接本體（第 5 步）；同一工作線預計拆三份以上交接時，發第一份前先在 `docs/plans/` 立線總表——軍師自寫的輕量檔，frontmatter `series: <線別名>` 與該線交接的 `series` 一致，只答四問（總共幾份含暫定、每份範圍、誰依賴誰、各份狀態），不寫介接規格；產檔腳本第 7 參數給同一線別，第三份起無總表會在 stderr 印骨架提醒。ce-plan 仍可由使用者主動發起用於深規劃。」保留原四行中「各端工作項目／介接規格／相依順序」語意，改列入第 5 步交接本體要求或總表欄位，不留孤句。
  2. 第 6 步句「（更新 `docs/plans/` 或產出下一輪交接文件）」改「（更新 `docs/plans/`——線總表則更新份次狀態——或產出下一輪交接文件）」；同步時機句「彙整進 `docs/plans/`（更新決策、記錄落差）」改「彙整進 `docs/plans/`（更新決策、記錄落差；線總表則更新份次狀態）」。
  3. 副官慣例區「子專案實作現況以原始碼為準」句之後加一句：「回答線進度以線總表為起點（`grep -rlF 'series: <線別名>' docs/plans/`），再以交接與回覆狀態核對」。
  4. kunsu-concepts「定案規劃」詞條尾句「不留在只有單一 session 知道的地方」之後加一句：「一條線拆三份以上交接時，定案規劃的最小形式是線總表（frontmatter `series` 與交接對齊，只答四問），由軍師自寫、不經 ce-plan」。
  5. kunsu-init `version: 0.10.0`。
  6. 母體 `CONCEPTS.md`「線總表」詞條與上述字面核對（定型字面以範本為準，詞條只需語意一致）。
- **Patterns to follow**：範本第 2 步「規劃前既有盤點」子項的寫法（機制名＋指路句＋降級）；第 5 步「上游依賴」項對 `depends_on` 的指路句。
- **Test scenarios**：Test expectation: none -- 純文件；由 U4 錨句與 U5 遷移對照驗證；改寫段落由實作者以散文通讀一遍（大範圍改寫教訓）。
- **Verification**：新第 3 步含「線總表」「series」「三份以上」三字串；舊句「以 ce-plan skill 寫入 `docs/plans/`，內容須明確拆分」在範本歸零。

### U4. consistency-check 擴充

- **Goal**：新字面與新行為進機械檢查：`series` 參數實跑、stderr 定型行實跑擷取、範本與 live 錨句、CONCEPTS 雙檔。
- **Requirements**：R10；KTD4、KTD7。
- **Dependencies**：U1、U3。
- **Files**：`scripts/consistency-check.sh`。
- **Approach**：
  1. C 項 fixture 內新增 C3：帶第 7 參數 `"線A"` 實跑（第 6 參數給 `"a.md"`），斷言 `series: 線A` 行號＝`depends_on` 行號＋1；再不帶第 6 參數實跑，斷言 `series:` 行號＝`tags:` 行號＋1。
  2. C4：同 fixture 連發三份 `series=線A`，第三次擷取 stderr（`2>&1 >/dev/null`），`grep -cF` 提醒首行與 `grep -rlF 'series: 線A' docs/plans/` 範式各恰中一次；建立 `docs/plans/x.md` 含 `series: 線A` 後發第四份，斷言總表行命中、提醒首行歸零；帶 `"後端: API"` 實跑斷言 exit 1 且無新檔。
  3. 範本錨句：kunsu-claude.md 含「線總表（條件式）」與 `series:` 各恰中一次、舊句「以 ce-plan skill 寫入」歸零；kunsu-concepts.md「定案規劃」段含「線總表」。
  4. H 鏈追加 `grep -q '線總表' "${kroot}/CLAUDE.md"` 與 `grep -q '線總表' "${kroot}/CONCEPTS.md"`，WARN 訊息列舉補「線總表（CLAUDE 與 CONCEPTS 各自）」。
  5. 版號鏈（A 項）與依賴聲明比對隨 U2 新版號自然涵蓋；確認無硬編碼舊版號。
- **Patterns to follow**：C2（第 99–111 行）行號相對斷言；K 項實跑 reply 腳本擷取 stderr；J 項 `grep -cF` 計數斷言；H 鏈 `&&` 疊加。
- **Test scenarios**：
  - 正向：`bash scripts/consistency-check.sh` 全 PASS（34 → 約 38 項），live 軍師 H 鏈於 U5 完成前為 WARN、完成後 ok。
  - 負向（實作時各跑一次，不留在檢查裡）：把腳本提醒首行改一個字 → C4 FAIL；把範本「線總表（條件式）」改字 → 範本錨句 FAIL；把 `series` 行印在 `tags` 之前 → C3 FAIL；改回後全 PASS。
- **Verification**：正向全 PASS；三個負向各實跑觀察到 FAIL 後還原（以反向 sed 還原，未 commit 前不用 `git checkout` 整檔）。

### U5. 第十二波遷移（ebook／ivm／px）

- **Goal**：三 live 軍師 CLAUDE.md 第 3 步、第 6 步、同步時機句、副官慣例指路句，與 CONCEPTS「定案規劃」詞條同步範本定稿字面。
- **Requirements**：R9；KTD7；AE8。
- **Dependencies**：U3（定稿字面）、U4（H 鏈可驗）。
- **Files**：`kunsu-project-root/ebook/CLAUDE.md`、`kunsu-project-root/ebook/CONCEPTS.md`、`kunsu-project-root/ivm/CLAUDE.md`、`kunsu-project-root/ivm/CONCEPTS.md`、`kunsu-project-root/px/CLAUDE.md`、`kunsu-project-root/px/CONCEPTS.md`（各 repo 相對路徑即 `CLAUDE.md`、`CONCEPTS.md`）。
- **Approach**：
  1. 遷移前對每個檔案以 `grep -cF` 舊句（第 3 步首行「3. **產出跨專案規劃**：以 ce-plan skill 寫入」、第 6 步括號句、同步時機括號句、副官慣例錨句「子專案實作現況以原始碼為準」、CONCEPTS 尾句「不留在只有單一 session 知道的地方」）確認恰中一次；ebook 用語「本規劃中心」不在錨句內，不受影響。
  2. python3 批次替換（前置唯一性斷言，任一檔非恰中一次即中止不寫）：第 3 步四行整段替換、兩句附加、指路句插入、CONCEPTS 尾句後插入。
  3. 遷移後反向核查：新句各恰中一次、舊句歸零、`git diff --stat` 僅 CLAUDE.md 與 CONCEPTS.md。
  4. 每軍師一筆確認 commit：`git add -- CLAUDE.md CONCEPTS.md && git commit -m "docs: 第十二波遷移——工作流程第 3 步條件式線總表與 CONCEPTS「定案規劃」詞條" -- CLAUDE.md CONCEPTS.md`，執行前經阻塞式確認（ADR 009）；live 工作區的未 commit 信箱檔一律不入。
- **Execution note**：三 repo 逐一執行，每個 repo 遷移後先跑 `bash scripts/consistency-check.sh`（母體）觀察該 repo H 鏈由 WARN 轉 ok 再 commit。
- **Patterns to follow**：第十一波遷移 commit（ebook `94aa62e`）與 CONCEPTS「遷移波次」詞條；`literal-replacement-residue-and-review-triage.md` 的散文通讀。
- **Test scenarios**：
  - Covers AE8. 三 repo 遷移後 `consistency-check.sh` H 鏈三筆 ok，全項 PASS。
  - 任一 repo 舊句計數 ≠1 時腳本中止、零寫入（以暫存副本先驗證中止路徑）。
  - `git status --porcelain` 於 commit 後只少了 CLAUDE.md／CONCEPTS.md 的 M，信箱未 commit 檔數不變。
- **Verification**：三 repo 新句命中、舊句歸零、各一筆 commit、母體 H 鏈 ok。

### U6. 母體文件、部署與 dogfooding 收尾

- **Goal**：CLAUDE.md 開發狀態新條目與結構樹同步、idea 檔標記 promoted、`install.sh` 重佈署、暫存 repo 走完 AE1–AE14、pytest 零回歸確認。
- **Requirements**：R10；KTD6。
- **Dependencies**：U1–U5。
- **Files**：`CLAUDE.md`、`docs/ideas/2026-09-27-範本工作流程第3步plan降為條件式一線拆三份以上交接才立輕量總表.md`（frontmatter `status: promoted`、`plan:` 指本計畫）、`CONCEPTS.md`（核對）。
- **Approach**：
  1. CLAUDE.md 開發狀態加「條件式線總表與產檔訊號」條目：動機（根因三層）、落地、審查修正、residual、數字（consistency-check 項數、pytest 沙盤 200／inbox 82 零改動）。
  2. 結構樹：handoff `scripts/` 行補「第 7 參數 `series`＋線總表提醒」、kunsu-init 範本行補「第 3 步條件式線總表」。
  3. `./install.sh` 重佈署兩樹（`~/.claude/skills`、`~/.agents/skills`）；沙盤程式零改動，不需重啟。
  4. 暫存 repo dogfooding 腳本走 AE1–AE16，輸出斷言計數。
  5. `python3 -m pytest skills/kunsu-dashboard/tests skills/kunsu-inbox/tests -q` 確認零回歸。
- **Test scenarios**：Test expectation: none -- 文件與部署；dogfooding 斷言與 pytest 為驗證手段。
- **Verification**：dogfooding 全過、pytest 282 項通過、consistency-check 全 PASS、部署樹 `new-handoff.sh` 含 `series`。

---

## Verification Contract

| 檢查 | 指令／方式 | 適用單元 | 通過訊號 |
|---|---|---|---|
| 跨檔一致性 | `bash scripts/consistency-check.sh` | U1–U5 | 全項 PASS（含新增 C3、C4、範本錨句、H 鏈線總表） |
| 負向假綠燈 | 三個新錨句各改壞一次再跑 | U4 | 各觀察到對應 FAIL，還原後全 PASS |
| 產檔腳本行為 | 暫存 repo 依 AE1–AE16 實跑（含 `LC_ALL=C`） | U1、U6 | 每條 AE 斷言成立；stdout 單行、exit code 依 R5／R7 |
| 沙盤與 inbox 回歸 | `python3 -m pytest skills/kunsu-dashboard/tests skills/kunsu-inbox/tests -q` | U6 | 282 項通過，零改動 |
| live 遷移 | 三 repo `grep -cF` 新舊句、`git diff --stat` | U5 | 新句恰中一次、舊句歸零、diff 僅兩檔 |
| 部署 | `./install.sh`；`grep -c series ~/.claude/skills/handoff/scripts/new-handoff.sh` | U6 | 兩樹更新、計數 >0 |

---

## Definition of Done

- U1–U6 全部完成，`consistency-check.sh` 全 PASS，三個負向驗證各實跑過一次。
- AE1–AE16 各有對應的實跑斷言且通過。
- 三 live 軍師各一筆確認 commit，母體變更未 commit（等使用者要求）、絕不 push。
- handoff 0.24.0、kunsu-init 0.10.0、kunsu-inbox 0.15.1 三版號與依賴聲明、CLAUDE.md 結構樹一致。
- 母體 CLAUDE.md 開發狀態條目與 CONCEPTS「線總表」詞條與落地字面一致；idea 檔標記 promoted。
- 無殘留實驗性程式碼或暫存 fixture 進入 repo。
