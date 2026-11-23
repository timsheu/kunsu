# 端到端工作流程（end-to-end workflow）

從建立軍師、加入子專案，到「規劃 → 交接 → 接手 → 回覆 → 收尾」完整走過一輪的操作步驟。

本文是操作教學的唯一落點：[README](../../README.md) 只保留門面摘要；各 skill 的行為權威定義在對應的 `skills/*/SKILL.md`；軍師沙盤的完整功能說明另見 [dashboard.md](dashboard.md)。

## 前提

- Claude Code 與 Codex CLI 皆可，軍師端與子專案端可由任一 agent 擔任（同一份原始碼雙部署，ADR 019 已於 2026-10-03 審定為 accepted；Codex 側的機器層級設定與已知邊界見 README「多 agent 支援」）。
- 本文以 skill 名指稱各指令，不綁定任一 agent 的呼叫形：Claude Code 以 `/<name>` 呼叫、Codex 以 `$<name>` 呼叫或依 description 自動選用；阻塞式確認（確認 commit 等）在 Claude Code 為提問工具、在 Codex 為印出定型指令後結束回合、下一回合同意才執行；跨 session 推播為 Claude Code 限定，Codex 側由 SessionStart hook 兜底。完整對應見各 SKILL.md 首節「Agent 對應表」與 README「多 agent 支援」。
- 預設搭配 every.to 出品的 Compound Engineering（CE）plugin 與 Obsidian 使用：需求成形後落 `docs/brainstorms/`（使用者發起 `/ce-brainstorm` 時由其產出，否則軍師自寫）；規劃採條件式線總表——單份或兩份交接可解的需求不立 plan，同一工作線預計拆三份以上交接時，才由軍師在 `docs/plans/` 自寫輕量的線總表，`/ce-plan` 仍可由使用者主動發起用於深規劃。文件以 Obsidian vault（Dataview）瀏覽。
- 安裝方式見 [README「安裝」一節](../../README.md#安裝)。

## 一、建立軍師

執行 kunsu-init skill，依訪談回答軍師名稱與目標路徑，agent 會自己建好軍師資料夾與結構（CLAUDE.md 五條不變量與三信箱協議、CONCEPTS.md、docs 結構、Obsidian vault、git repo），並將子專案登記至全域反向註冊表 `~/.claude/kunsu-registry.json`。

訪談時就把子專案清單一併給齊的話，當下直接完成登記，可跳過下一步的申請流程。

## 二、加入或移除子專案

- **加入**：到子專案資料夾中執行 kunsu-apply skill，agent 會詢問要把這個子專案申請加入哪個軍師。申請送出後是待審狀態，得切回軍師 session 執行 kunsu-init skill 的 add-project 子指令逐筆審核，核准當下才正式登記；在那之前 kunsu-inbox skill、kunsu-report skill 與沙盤都還不認得這個子專案。
- **移除**：子專案因檔案結構合併或拆分不再由本軍師管轄時，在軍師 session 執行 kunsu-init skill 的 remove-project 子指令，整筆移除該子專案在本軍師的所有角色代碼登記。移除前會掃描未完成交接並警告，且未完成交接警告與不可逆最終確認是兩道獨立確認，不會合併帶過。
- **補上範本新增的規則**：軍師是用舊版範本建立的話，在軍師 session 執行 kunsu-init skill 的 sync-rules 子指令。它檢查軍師的 CLAUDE.md 是否已有「環境版本以正本為起點」規則，沒有就在你同意後補上；接著列出環境限制段裡含版本號的行（分成「精確版本號」與「可能是上限的主次版本」兩類），並告訴你環境版本正本（`docs/modules/各環境版本現況.md`）是否已存在。它只改 CLAUDE.md，不改寫環境限制段的內容，也不動既有的環境版本正本——列出的行由你和軍師逐條決定怎麼改。可以重複執行，已補上的不會再插一次。

## 三、查看整體狀態（軍師沙盤）

想一眼看出每份交接卡在誰手上時，手動啟動軍師沙盤，打開 `http://127.0.0.1:8000/` 的看板；要看所有軍師與子專案的完整訊息狀態則開 `/overview`。沙盤不會自動偵測更新，重新整理頁面才會重新掃描並顯示最新狀態。安裝、啟動與各區塊的完整說明見 [dashboard.md](dashboard.md)。

## 四、規劃與發交接（軍師 session）

1. 從軍師 session 直接要求軍師研究並規劃新功能或問題。討論需求時軍師會問一次「**目標背後的目標**」——這件事做完後你真正想要發生什麼（「修這個當機」背後是「App 不當機」）；同一類問題近期已出現第二次時，軍師會提出改以這個更上層的目標一次收口的選項，避免逐點修補卻答不出「還剩哪些沒做」。
2. 軍師動手規劃前會先做**規劃前既有盤點**——以 `/kb`（zoekt 本機索引；軟依賴，未安裝或服務未回應時自動降級為手動查閱、不阻斷）依「自家 handoffs（含 replies／archive）→ 自家 plans → 子專案文件 → 子專案原始碼」的優先序檢索既有能力與既有結論，避免漏查自家歷史而過度規劃。子專案文件屬中介層、原始碼才是一手：接手方會據以實作的事實斷言須落到原始碼層查證。
3. 方向確定後，下筆交接前先確認議題已想透——隱含假設或未決分支可用 grilling／`/ce-brainstorm` 逐一逼出。
4. 軍師用 handoff skill 對每個有關聯的子專案各產生一份交接文件。兩個選填宣告會影響後續的狀態顯示：
   - **`depends_on`**（上游依賴）：這份交接須等其他交接完成才能開工時，宣告被依賴交接的完整檔名；沙盤、kunsu-inbox skill 與 SessionStart hook 據此推導「可開工」或「等依賴」。
   - **`series`**（線別）：同一工作線的交接填同一個線別名。同線第三份起若還沒有線總表，產檔腳本會印出可貼上的骨架提醒；已有線總表則印出路徑，提醒更新份次狀態。
5. 文件產生完成後會問一次「是否 commit」，記得答應——交接檔未 commit 的話，軍師下次 kunsu-inbox skill 會產生 tripwire 誤報。Claude Code 派發完成當下會自動推播通知目標子專案已開啟的長駐 session（Codex 沒有跨 session 推播，這一步整個跳過）。

> **tripwire** 是絆馬索：一個避免流程出錯的核對提示，觸發時讓 agent 與使用者知道目前有意外狀況需要人工處理排除。

## 五、子專案接手

自己到子專案打開新 session，口語要求查看信箱、或直接執行 kunsu-inbox skill，agent 會列出「未接手」「部分完成」「已回覆待確認」的交接清單與檔案路徑。inbox 的設計是「只告知不開工」——接著讀規格、開工由使用者下令。

已掛載 SessionStart hook 時不必手動查：session 啟動（含 Claude Code 的 `/clear`）當下，信箱摘要會自動注入對話；子專案 session 若在軍師派發時已開著，Claude Code 還會收到派發即推播的一次性告知。推播要精準送達，session 名稱須符合命名慣例（子專案 `<軍師目錄名>-<角色代碼>`、軍師 `<軍師目錄名>-kunsu`）——以 `kc` 啟動函式取代 `claude` 啟動即自動帶入，同一資料夾開多個 session 時用 `kc --slot <後綴>` 區分。hook 與 `kc` 的安裝方式見 [README「安裝」一節](../../README.md#安裝)。

## 六、回覆與收尾

1. **回覆**：子專案完成（或部分完成、卡關）後，口語「回覆軍師」或 handoff skill 的 reply 子指令建立回覆檔，逐項回答並附可查核證據；可用選填欄位 `verify:` 標注驗收方式（`needs-deploy` 需上線測試／`testable-now` 馬上可測／`needs-device` 需實機測試，或自由字串），沙盤會顯示成對應標籤。回覆刻意不 commit——未 commit 正是軍師端的「新回覆」訊號。
2. **暫離回報**：交接做到一半要臨時切去別的需求時，說「交接工作先暫停」「先放到 branch，之後再回來」等，會投遞一份最小 partial 回覆（branch 名、一句現況、回來意向），讓軍師沙盤顯示「部分完成」而不是誤判「未接手」；回歸完成後照常投遞 `submitted` 完成回覆。
3. **軍師收件**：回到軍師 session 執行 kunsu-inbox skill 看到新回覆，下令彙整。已掛載 hook 時不必手動查——SessionStart hook 在 session 啟動時注入信箱摘要；UserPromptSubmit hook 在軍師 session 進行中、你每送出一句提問時掃描三信箱，有未 commit 新件就以一行告知；子專案經 handoff skill 投遞回覆時，Claude Code 另有回覆即推播。
4. **done 收尾**：確認完成後以 handoff skill 的 done 子指令歸檔——done 會先把原交接的問題清單、期望交付與 `verify:` 驗收方式逐項對照最新回覆，缺口顯式列出後由你決定收尾或暫緩；接著掃描本 repo `docs/todos/` 頂層，若這份交接源自某筆 todo（以檔名雙向比對），經確認後把該 todo 一併標記已解決並歸檔，避免交接收尾了、todo 卻停留「未處理」使沙盤計數失真；todo 收尾前會做**殘項清點**——讀該 todo 檔裡尚未完成的「下一步」「待辦」，有殘項就先轉出成新的 todo，不讓未做完的事隨歸檔一起消失。歸檔動作由腳本暫存具體路徑後，再問一次「是否 commit」（確認 commit）：同意才提交，且只提交這次收尾宣告的檔案範圍，不會夾帶工作區裡其他未提交的修改。commit 完成，這一輪交接才算真正走完。

## 七、主動上報

子專案 session 發現與手上交接無關的新情報、或發現更好的方向時，用 kunsu-report skill 或口語「稟報軍師」向軍師提案。若其實是手上交接要調整方向，那屬於回覆而不是上報——投錯也沒關係，kunsu-report skill 偵測到有待回覆的交接會先反問並導回 handoff skill 的 reply 子指令。

回到軍師 session 執行 kunsu-inbox skill 看到新上報，軍師讀文件與研究後，跟使用者討論定向，再重複第四步以後的流程。上報是情報傳遞，不是反向委派——不承諾軍師回覆或執行任何動作。

## 八、技術債與待辦（/todo）

規劃或實作過程中發現、但明確排除於當前範圍外的殘留問題，用 todo skill 的 add 子指令記成一檔一項的技術債（落在該 repo 的 `docs/todos/`，含 status／severity 等 Dataview 友善 frontmatter）；todo skill 的 list 子指令列出、todo skill 的 done 子指令標記解決並歸檔、todo skill 的 rm 子指令直接封存。

軍師自己的 todo 會被沙盤彙整成「待辦技術債」計數與卡片——跟 supervisor 討論時可以一次攤開所有軍師累積的技術債，不用逐一開軍師 session 執行 todo skill 的 list 子指令。

## 延伸操作

- **kunsu-list skill**：快速回顧目前有哪些子專案登記在哪個軍師底下。純唯讀、不需 git 身分，任何目錄（含多 repo 父層 workspace）皆可執行，含 stale entry 偵測與當前位置標記。
