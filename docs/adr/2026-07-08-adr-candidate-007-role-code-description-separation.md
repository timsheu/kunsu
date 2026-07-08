---
title: ADR Candidate 007 — 角色識別正規化：角色代碼（比對鍵）與角色說明（描述）分離
date: 2026-07-08
type: adr
status: accepted
---

# ADR 007：角色識別正規化——角色代碼（比對鍵）與角色說明（描述）分離

> 狀態：**Accepted**（2026-07-08 由實際使用回報觸發、經兩輪 `/ce-doc-review` 審定；使用者已就「保留角色說明欄」「一併
> 遷移現存 live 資料」「兩筆無 handoff 依據的代碼即席定案」「唯一性檢查與軟警告提升為
> Decision」逐一確認）。經**兩輪** `/ce-doc-review`（coherence／feasibility／product-lens／
> adversarial 四 persona）審查：第一輪 8 finding＋2 FYI，含修正原稿「ebook 全側免動」失實
> （`ebook-store-nginx` 亦為整句）；第二輪 7 項完備化，含**再修一處失實**（ebook 軍師
> CLAUDE.md 亦停舊單欄、須雙欄遷移）與 Decision 7 唯一性的實作強制點錨定。上游觸發脈絡見
> 本文 Observations。

## Context

### Observations（現況盤點）

- CONCEPTS.md 的「角色字串」定義將**兩個相互衝突的職責**綁在單一概念上：既是「子專案在
  某軍師中的**職責描述字串**」，又是「交接文件 `to:` 欄位的**唯一比對鍵**」，並要求在軍師
  關聯專案表、註冊表與交接文件三處字面一致。
- 範本自身的命名早已分裂，佐證這概念從未真正是一件事：回覆信箱協議的 frontmatter 寫
  `from: {接手方角色識別}`／`to: {軍師角色識別}`（識別），但 kunsu-init／add-project／
  kunsu-apply 的訪談與關聯專案表卻叫「角色描述」，`registry` schema 欄位名為 `roles`。
- `/handoff` 指令說明給的 `to:`／`from` 範例本就是短碼（`app`、`backend`、`frontend`、
  `devops`、`dba`）；不存在把整句職責描述打進 `to:` 的自然用法。
- **資料級不一致實證**（同一套工具產出兩種不相容資料）：

  | 軍師 | registry `roles` | 與 handoff `to:` 短碼慣例 | `/kunsu-inbox` 比對 |
  |------|------------------|--------------------------|---------------------|
  | ebook | `backend`／`android`／`store`（短碼） | 吻合 | 正常 |
  | ivm | 「機台端 Electron/Vue2 前端…」（整句） | 衝突 | false-negative |

- 實跑回報：ivm 軍師的交接文件 `to:` 用短碼（`shun-tien`、`backend`），但註冊表登記的是
  完整角色描述，`/kunsu-inbox` 步驟 4a-3 的 `to ∈ our_roles` 精確比對命中不到，只能依交接
  文件內文人工核實方向。附註當時建議「add-project 登記時一併記錄短碼別名」。

### Hypothesis（推斷，非事實）

- 使用者在 add-project／kunsu-apply 被問「角色**描述**」時，自然填整句；在 `/handoff` 被問
  `to:` 時，自然填短碼。**同一概念在兩個入口的提示語不同**，誘導出不相容資料——這是介面
  用語問題，非使用者疏失。ebook 那次剛好填了短碼所以能動，屬巧合而非工具保證。

## Decision（proposed）

1. **概念拆分為兩個獨立欄位**：
   - **角色代碼**（identity／比對鍵）：短、kebab-case、穩定。「三處字面一致」的對象自「角色
     字串」改為**角色代碼**——registry `roles`、handoff `to:`／回覆 `in_reply_to` 對應角色、
     CLAUDE.md 關聯專案表代碼欄。
   - **角色說明**（description／display-only，選填）：整句職責描述。**永久落地於**軍師 CLAUDE.md
     關聯專案表的說明欄；申請流程中以 `role_desc` **暫存於申請 frontmatter（暫態中繼）**，核准
     後由 add-project 寫入關聯專案表說明欄。**不進 registry、不參與任何比對**。
2. **角色代碼規格**：短、kebab-case；定案權在軍師（沿用既有原則）。「短」給軟性錨點供實作
   參照——**宜 ≤ 20 字元、不含軍師名稱前綴**（避免 `{軍師名}-{子專案名}` 複合碼稀釋「短」目標）；
   此為建議非硬擋（Decision 8 軟警告的長度閾值另設 30 字元為誤填整句的偵測線）。「**穩定**」是
   設計目標而非系統強制——代碼仍可能演變，改名成本見 Consequences。registry schema **不變**
   （`roles` 仍為 `string[]`），僅語意收斂為「代碼」；**不引入 `aliases` 欄**（否決附註別名案，
   理由見 Alternatives）。
3. **關聯專案表欄位**自單欄「角色」改為雙欄「**角色代碼｜角色說明**」。`{{PROJECT_ROWS}}` 產列
   格式對應調整。
4. **申請 frontmatter**：`proposed_role` 語意改為「提議角色**代碼**」，新增 `role_desc`（角色說明，
   選填，**暫態中繼**，見 Decision 1）。`new-application.sh` 參數與 kunsu-apply 訪談對應調整。
5. **訪談用語統一**：kunsu-init／add-project／kunsu-apply 一律改問「角色代碼（kebab-case，即
   handoff `to:`）」與「角色說明（選填）」兩題，取代舊「角色描述」單題。三處「此字串即 handoff
   `to:` 唯一來源」提示改為指向**角色代碼**。
6. **現存 live 資料遷移（本次一併執行，非日後）**，定案代碼對照：

   | 軍師 | registry 子專案 | 舊 `roles`（整句摘要） | 新代碼 | 代碼來源 |
   |------|-----------------|------------------------|--------|----------|
   | ivm | ivm-backend-go | IVM 後端 API（Go/Gin…） | `backend` | 既有 handoff `to:` |
   | ivm | ivm-shun-tien-frontend | 機台端 Electron/Vue2… | `shun-tien` | 既有 handoff `to:` |
   | ivm | ivm-website | 後端管理網頁（Admin）… | `ivm-website` | 使用者即席定案（無既有 handoff） |
   | ebook | ebook-store-nginx | HTTPS 前門代理與 TLS… | `store-nginx` | 使用者即席定案（無既有 handoff） |

   - `backend`／`shun-tien` 取自 ivm 既有交接文件實際 `to:` 值；`ivm-website`／`store-nginx`
     **無既有 handoff 可推導**，由使用者即席定案（已確認），不臆填。ebook 其餘三筆
     （`backend`／`android`／`store`）已是代碼、免動——**原稿「ebook 全側免動」失實已修正**：
     `ebook-store-nginx` 亦為整句、須遷移。
   - **`ivm-website` 屬一次性例外**：因無既有 handoff 依據、以 repo 全名即席定案，含軍師名前綴、
     不符 Decision 2 的「短、不含軍師名前綴」建議；此例外**不代表** `{軍師名}-{子專案名}` 複合碼
     為可接受範式，後續代碼仍循 Decision 2 軟性錨點。
   - **registry 遷移機制（關鍵）**：以 **python3 原子寫入**編修 `~/.claude/kunsu-registry.json`
     （`json.load` → 替換對應 entry `roles` 陣列 → `tempfile` 寫入後 `os.replace`，與
     `registry-merge.sh` 同一原子模式），**不得以文字編輯器直接存檔**（中斷會截斷 JSON，觸發全套
     工具的「格式損壞」硬停分支）；操作前先 `cp` 一份備份。**不呼叫 `registry-merge.sh`**：其為
     union-merge（`sorted(existing | new_set)`），只會聯集新增、留下舊整句，收斂不掉。
   - **CLAUDE.md 遷移範圍＝兩軍師**：ivm **與 ebook** 兩軍師 CLAUDE.md 關聯專案表均改雙欄。ivm
     四筆整句降說明欄、補代碼欄；ebook 四筆（`backend`／`android`／`store`／`store-nginx`）代碼欄
     取 registry 現值、現有「角色」欄描述降為說明欄——ebook registry 雖已是代碼，但其 CLAUDE.md
     仍停舊單欄，不遷則 Decision 1「CLAUDE.md 代碼欄」在 ebook 側不存在、三處一致破功。
   - **遷移後核查（雙軌，不單靠 `/kunsu-inbox`）**：(a) 於 ivm／ebook 子專案 session 各跑一次
     `/kunsu-inbox` 子 repo 模式，確認 false-negative 消除、無「to: 不符」孤兒；(b) 因無 handoff
     的子專案（`ivm-website`／`ebook-store-nginx`）`/kunsu-inbox` 掃不到 `to:` 比對、無法佐證，
     另以 python3 讀 registry 印出兩軍師所有子 repo 的 `roles`，逐條確認皆為短碼格式（無空白、
     長度低於 30 字元閾值）。
7. **同軍師代碼唯一性（本次納入）**：短代碼比整句更易撞名，是本次拆分**新引入**的正確性風險
   （同碼會使 `/kunsu-inbox` 對兩子專案雙方誤命中），故一併約束、不留待事後。三處核對**強度
   不同、不可視為對等**：
   - **add-project 為最終權威強制點**：在逐筆審核核准後、呼叫 `registry-merge` 之前，取本軍師
     registry 已登記代碼聯集（排除當前申請子 repo）**再聯集本批次已核准代碼的 session 級暫存
     集**——**同批每筆均重新比對暫存集，不可沿用批次開始時的 CLAUDE.md 快照**（否則同批兩份填
     同碼會漏偵測）；定案代碼命中即阻擋此筆、要求改碼。kunsu-init 首建多子專案時同樣以累積集
     逐筆比對。
   - **kunsu-apply 為早期最佳努力訊號（非權威）**：其可讀資料源僅 registry（只含**已核准**代碼），
     看不到在途待審申請，故同日兩份申請填同碼可能雙雙放行；真正的收斂由 add-project 承擔。ADR
     不誇大 kunsu-apply 的保證強度。
   - **阻擋訊息須列出該軍師已登記代碼集合**，讓使用者於同一輪互動選定替代碼，免中斷去查
     registry。
8. **`registry-merge.sh` 軟警告（本次納入）**：`roles` 條目含空白字元或超過長度閾值（如 30
   字元）時輸出 **WARN**（不強制擋、不阻斷寫入），讓「整句誤填」在登記當下曝光，而非等到
   `/kunsu-inbox` 比對失效才人工發現。維持「不加**強制**驗證」原則（避免擋合法例外）——**此
   原則的作用域限於 `registry-merge.sh` 的格式校驗層**，與 Decision 7 不衝突：Decision 7 的
   撞名硬擋作用於 skill 互動層的**語意正確性**（唯一性），Decision 8 的軟警告作用於腳本層的
   **格式合理性**（是否像代碼），兩者分屬不同層次、各自為政，不可因並列而把 Decision 7 降格為
   警告。

## Consequences

- CONCEPTS.md 將「角色字串」拆為「角色代碼」與「角色說明」兩詞；並在「角色代碼」詞條註明
  「角色識別」為其在回覆信箱 frontmatter 佔位符（`from`／`to`）的別稱，收束 Observations 指出的
  第三段命名（避免使用者查詞彙表時「角色識別」懸空無定義）。範本回覆信箱協議 frontmatter 的
  **佔位符文字「角色識別」本身不變**（其值本就是角色代碼），僅由 CONCEPTS.md 釐清語意，**不改**
  `new-handoff-reply.sh` 產出格式，該腳本不列入影響檔案。
- `/kunsu-inbox` 比對邏輯**不需改動**（本就對 `roles` 做精確比對）；`roles` 語意為代碼後自然
  正確。「to: 不符清單」文案微調為「不在此軍師已登記的任何角色**代碼**集合」。
- `/handoff` SKILL 補一句：kunsu 情境下 `to:` = 軍師登記的角色代碼。`/handoff` 作為通用交接原語
  不強制此約定，僅在 kunsu 語境下成立（handoff 可獨立於 kunsu 使用）。
- `registry-merge.sh`：提示訊息補「代碼宜為 kebab-case」，並新增軟警告（Decision 8）；仍**不加
  強制驗證**（避免擋住合法非 ASCII 或既有例外）；schema 不變，無破壞性。
- **改名成本（新機器鍵的代價）**：代碼成為 handoff `to:` 的機器鍵後，改一次代碼會使所有歷史
  交接文件的 `to:` 失效、需逐一追溯修復；現行僅 add-project 的改名警告掃描（只提示、不自動
  修復）。故 Decision 2 明訂「穩定」為設計目標而非強制——實務改名成本隨交接文件數線性增長，
  追溯修復工具化列 Open questions。
- **根因措辭校正**：本 ADR 降低角色字串三處漂移的**機率**（代碼短、穩定、登記時軟警告曝光），
  但「三處字面一致」的維護要求本身**不變**——改善的是值的穩定性與可見性，不是消除三處依賴的
  拓撲。勿將本 ADR 讀為「根因徹底消除」而放鬆三處對齊的警覺。
- **說明欄選填之限**：說明欄留空時，關聯專案表「一眼可見職責脈絡」的效益由使用者紀律而非工具
  保證；訪談跳過說明時提示一次「留空將導致關聯專案表缺職責脈絡」。留空的呈現規格見 Open
  questions。
- 影響檔案：CONCEPTS.md、範本 `kunsu-claude.md`（關聯專案表雙欄＋申請 frontmatter 範例）、
  kunsu-init SKILL、kunsu-apply SKILL＋`new-application.sh`、add-project 子指令（審核收代碼、
  定案代碼、寫雙欄、改名警告掃 `to:` == 舊代碼）、`/kunsu-inbox` SKILL（文案）、`/handoff` SKILL
  （一句約定）、`registry-merge.sh`（軟警告）、kunsu-init／add-project／kunsu-apply 的代碼唯一性
  交叉核對（add-project 為權威強制點）。加上 live 資料遷移：ivm registry 三筆＋`ebook-store-nginx`
  一筆（以 python3 原子寫入）、**ivm 與 ebook 兩軍師** CLAUDE.md 關聯專案表改雙欄。

## Alternatives considered

- **整句為 canonical＋代碼別名（附註原案）**：把描述當身分、代碼當別名，需維護對照表與模糊
  比對（`to:` 先查別名表再命中 canonical），兩份要同步、比對語意變複雜，且未真正 unify——問題
  的病灶「一個欄位兩個職責」原封不動，只是再疊一層。否決。
- **只留代碼、砍掉整句描述**：最精簡、零額外欄位，但軍師關聯專案表會失去一眼可見的職責脈絡
  （跨 repo 規劃拆解時有用）。使用者裁定保留說明欄。否決。
- **維持現狀、僅在文件警告「要填短碼」**：不改結構、零遷移，但用語誘導仍在（訪談問「描述」
  卻要短碼），false-negative 會復發，且已污染的 ivm 資料仍壞。否決。

## Open questions

- add-project 是否內建「整句 `roles` → 代碼」自動遷移偵測（比照 ADR 006 申請信箱缺目錄的遷移
  機制），供其他既有軍師升級——本次先手動遷 ivm 三筆＋`ebook-store-nginx`，工具內建列為後續
  評估。
- 角色改名的**追溯修復工具化**（掃描所有 handoff `to:` 並批次替換舊代碼）——改名成本已於
  Consequences 點明、Decision 7 唯一性可減少非必要改名，但自動修復機制仍缺（ADR 002 Deferred／
  Open Questions 延續）。現行仍為 add-project 的改名警告掃描（只提示不修復）。
- 角色說明欄留空時在關聯專案表的**呈現規格**（顯示「無說明」佔位 vs 留空欄）——本 ADR 未規格化，
  待範本落地時定；行為不一致會讓軍師協調者難辨是填寫疏漏或刻意留空。
