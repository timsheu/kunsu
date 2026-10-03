---
title: 推播匹配排除 offline session - Plan
type: fix
date: 2026-10-03
topic: push-match-exclude-offline
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# 推播匹配排除 offline session - Plan

## Goal Capsule

- **Objective**：軍師派發交接或子專案投遞回覆時，只要目標視窗有一個活的 session 開著，就能收到推播通知；過去關掉的同名 session 留下的殘影不再讓活 session 被誤判為「多重命中」而漏發。
- **Means**：handoff skill 兩方向推播的 session 匹配規則在兩層匹配之前先排除狀態為 offline 的列（KTD1）；規則副本（CONCEPTS、kc 啟動函式註解、ADR 015）同步對齊；handoff 版號 patch 升版並過一致性檢查。
- **Product authority**：本文件的 Product Contract；kunsu `CLAUDE.md` 四條 Invariants；ADR 015（派發即推播）與其「寧漏發不誤發」取捨；2026-08-21 定案「同慣例名 slot 變體並存即多重命中」維持不動。
- **Execution profile**：單一 repo、純文字規則修訂，三個單元依序落地；不新增腳本、不改掃描／分類／hook 邏輯；母體不主動 commit、絕不 push。
- **Stop conditions**：`scripts/consistency-check.sh` 任一項 FAIL 未收斂；兩處規則文字的定型用語不一致；修訂後需要改動任何 `.py`／`.sh` 的分類或掃描邏輯（代表範圍被撐開，應停下重審）。
- **Tail ownership**：ce-work 完成後接 ce-code-review；`install.sh` 重佈署由本 session 執行（SessionStart hook 的版號變動提示隨之觸發一次屬預期）；commit 由使用者明確要求時執行。
- **Open blockers**：無。

## Product Contract

### Summary

handoff skill 的派發即推播與回覆即推播在列出本機 session 後，先丟掉狀態為 offline 的列，再對剩餘的 online 候選套用既有的精確比對、slot 變體多重命中與啟發式 fallback；「唯一且明確才發送」的判斷只看 online 候選。同時在 ADR 015 補修訂註記、CONCEPTS 詞條與 kc 啟動函式註解對齊用語，並記錄 offline 殘影的成因、清除現況與 `remoteControlAtStartup` 設定建議。

### Problem Frame

2026-10-03 在本 repo session 以 ListAgents 實測：21 筆 peer session 中 19 筆為 `Remote Control · offline`，只有 2 筆是活的 `interactive`。同一慣例名的 offline 殘影最多疊到 4 筆（`ebook-kunsu`），`ebook-ios-app` 則是 2 筆 offline 加 1 筆活的。

殘影的來源有兩層。第一層是 `kc` 啟動函式每次都以 `claude -n <慣例名>` 開一個全新 session，名字只是標籤，不是 session 身分，所以同一資料夾每啟動一次就多一個同名 session。第二層是使用者機器 `~/.claude/settings.json` 的 `remoteControlAtStartup: true`，使每個新 session 啟動即註冊 Remote Control；process 結束後該登記不消失，只是狀態變成 offline，持續留在 ListAgents 清單。官方文件（https://code.claude.com/docs/en/remote-control.md）未載明 offline 條目的 CLI 清除指令與自動過期政策，只提到 claude.ai/code 可篩選已歸檔 session。

現行規則（`skills/handoff/SKILL.md` add 步驟 6-2、reply 步驟 6-1）寫的是「同一慣例名的 slot 變體開了兩個以上（或無後綴與有後綴並存）即屬多重命中、降級跳過」，沒有區分 session 狀態。後果是：活的 `ebook-ios-app` 被兩筆 offline 同名殘影拖成多重命中，推播永遠不會送達，只剩 SessionStart hook 兜底；回覆方向推播 `ebook-kunsu` 時四筆殘影同樣讓任何活的軍師 session 被誤判。殘影隨每次啟動單向累積，誤判率只會惡化，ADR 015 設計的「使用者晃回視窗即見通知」在這台機器上實際已失效。

### Key Decisions

- KD1. **以排除 offline 修正匹配規則，而非維持現規則、改靠人工清理殘影**（session-settled: user-approved — chosen over 不改規則只清殘影：殘影每次 `kc` 啟動就再生，且官方未提供 CLI 清除法，清理追不上累積）。Governs R1, R2。
- KD2. **`remoteControlAtStartup` 只做文件建議，不把設定變更列為實作單元**（session-settled: user-directed — chosen over 計畫內含「改 settings.json 為 false」單元：修訂規則本身已能擋住殘影誤判，使用者機器設定不屬 repo 交付物）。Governs R6。
- KD3. **「唯一且明確才發送」與 2026-08-21 的 slot 變體多重命中定案維持不動**：本次只改候選集，不改判斷。Governs R2。

### Requirements

**匹配規則**

- R1. 派發即推播（add 步驟 6-2）與回覆即推播（reply 步驟 6-1）在兩層匹配之前，先排除列出清單中狀態為 offline 的 session。
- R2. 排除之後，精確比對、slot 變體多重命中與啟發式 fallback 的規則文字與判斷維持現狀，只對剩餘的 online 候選運作；「唯一且明確才發送」只以 online 候選計數。
- R2a. 命中的 online 列連同其 `[ref]` 一併記下，發送一律以該 ref 定址；同慣例名的 offline 列並存時裸名必歧義，不得改取錯誤訊息中其他同名列的 ref（送進殘影卻回報「已推播」比降級跳過更糟，違反寧漏發不誤發）。
- R3. 列出清單不含狀態資訊時（舊版 CLI、其他 agent），不過濾、維持現行為，規則文字須明寫此降級；此類來源下 offline 殘影仍會計入候選，不在本次修復的保證範圍（見 Scope Boundaries）。

**副本對齊**

- R4. 兩處規則的新增文字使用同一組定型用語；CONCEPTS「派發即推播」詞條、`README.md`「session 命名慣例」條目、`scripts/kc.fish` 檔頭註解與 ADR 015 Decision 2、6 以修訂註記對齊，不留任何一份仍寫「並存即多重命中」而未提 offline 排除。
- R5. handoff skill 版號 patch 升版，`CLAUDE.md` 專案結構行與 kunsu-inbox SKILL.md 依賴聲明同步，`scripts/consistency-check.sh` A1 版號鏈與全部既有項目 PASS。

**文件記錄**

- R6. 以文件記錄 offline 殘影的成因（`-n` 新開 session 加 `remoteControlAtStartup: true`）、清除現況（官方文件未載明 CLI 清除法與過期政策）與建議（關閉自動啟用、改以 `/remote-control` 或 `/rc` 按需開啟），落點為 `scripts/kc.fish` 檔頭註解與開發日誌條目；不改任何使用者機器設定。成因二（Remote Control 登記留存為 offline）在未經「開一個 kc session 再關閉、重列清單多一筆同名 offline」實測前，一律以「推斷」標示，不寫成因果事實；建議句須附代價——需遠端接管的 session 都得手動 `/rc`，且此建議只為減少清單噪訊，非推播正確性所需。

**界線**

- R7. 不新增腳本，不改 `scan-*.sh`、`session_hook.py`、`prompt_inbox_hook.py`、沙盤分類與交接依賴圖的任何邏輯；推播定型通知文案（add 6-3、reply 6-2）的通知本文不動；6-3／reply 6-2 的「以 ref 重送」句可依 R2a 補定址規則。

### Scope Boundaries

- 不實作「自動清除 offline Remote Control 條目」：官方未提供 CLI，且屬使用者帳號層級資料，不是 repo 交付物。
- 不改 `kc` 的啟動行為（例如改為 `--resume` 續接舊 session）：`-n` 新開 session 是 `/park`／`/unpark` 停車格與 slot 設計的前提，改動屬另案。
- 不把 offline 過濾寫進任何腳本或 hook：推播匹配只存在於 SKILL.md 的規則文字，由 session 以 ListAgents 結果人工判斷，本就沒有程式化的匹配層。
- 不處理「兩個以上 online 同名 session 並存」的情境：維持 2026-08-21 定案降級。
- 不保證無狀態欄清單來源（舊版 CLI、其他 agent）的殘影誤判：R3 刻意退回現行為，該路徑的漏發照舊。

#### Deferred to Follow-Up Work

- 若日後 ListAgents 提供更細的狀態值（例如區分 busy／idle／offline 以外的新態），再評估是否要把 busy session 也納入「推播但排隊」的考量（既有「busy session 收訊排隊時機」觀察項）。

### Success Criteria

- 在本機現況（`ebook-ios-app` 1 筆 online 加 2 筆 offline）下，依修訂後規則人工走一遍 add 步驟 6-2，結論為「唯一命中、以 idle 列的 ref 發送」，而非「多重命中、降級」。
- 回覆方向對稱：`ebook-kunsu` 1 筆 online 加 4 筆 offline 時，reply 步驟 6-1 判唯一命中；`ebook-kunsu` 與 `ebook-kunsu.deploy` 皆 online 時仍判多重命中降級；無狀態欄清單時不過濾。
- 一致性檢查全綠，且新增的錨句檢查能在任一副本漏改時 FAIL。

## Planning Contract

### Key Technical Decisions

- KTD1. **以狀態欄 offline 排除，不以 kind 為 Remote Control 排除**：連線中的 Remote Control session 是真實收件目標（狀態會是 idle／busy），以 kind 過濾會把它誤丟；以狀態過濾才對應「活不活」這個真正要判斷的事。
- KTD2. **排除動作前置為獨立一句，既有兩層匹配文字零改寫**：在「兩層匹配」之前插入「先排除狀態為 offline 的列」一句，再把「唯一且明確才發送」的計數對象改寫為「剩餘 online 候選」；最小 diff，且兩處（add／reply）插入位置與句式一致，便於日後 grep 核對。
- KTD3. **無狀態欄時不過濾**：ListAgents 的輸出格式由 CLI 決定，舊版或其他 agent 可能不印狀態；規則文字明寫「清單未提供狀態資訊時視同全部 online、不過濾」，行為退回現行、不多擋也不少擋。
- KTD4. **ADR 015 以修訂註記補記，不開新 ADR**：沿用 ADR 010／014／016 既有的「> 修訂註記（日期）」慣例，在 Decision 2 與 Decision 6 各補一段，Context 不動；本次是對既定決策的候選集修正，不是新決策。
- KTD5. **版號為 patch（0.24.0 → 0.24.1）**：規則文字修正、無新子指令、無新參數，依全域 CLAUDE.md 版號規則屬 Bug fix。
- KTD6. **新增一致性檢查錨句項（T 項）**：以固定錨句「排除狀態為 offline」在 `skills/handoff/SKILL.md` 計數恰為 2（add、reply 各一）、`CONCEPTS.md`、`README.md` 與 `scripts/kc.fish` 各至少 1、ADR 015 至少 2（Decision 2、6 各一段修訂註記），防止日後單側改動漂移；沿用 Q 項的 `grep -cF` 形。錨句須整句置於同一行、每處只出現一次（括註與降級句的措辭避開該短語），因 `grep -cF` 以行計數。
- KTD7. **`remoteControlAtStartup` 建議的落點為 kc.fish 檔頭與開發日誌**（承 KD2）：kc.fish 是殘影第一層成因的所在，註解就地說明最容易被看到；playbook 目前沒有 session 啟動章節，不為此新開一節。

### Assumptions

- ListAgents 的列格式持續以「狀態」欄呈現 `offline`／`idle`／`busy` 等字樣；若未來改為其他字樣，規則文字中的「狀態為 offline」需一併更新（KTD3 的降級句保證不會因此誤擋）。

## Implementation Units

### U1. handoff SKILL.md 兩處規則修訂與版號鏈

- **Goal**：add 步驟 6-2 與 reply 步驟 6-1 加入 offline 排除句與降級句，版號升至 0.24.1 並同步兩處版號鏈。
- **Requirements**：R1、R2、R3、R5
- **Dependencies**：無
- **Files**：
  - `skills/handoff/SKILL.md`（frontmatter `version`、add 步驟 6-2、reply 步驟 6-1）
  - `CLAUDE.md`（專案結構 `handoff/` 行的版號）
  - `skills/kunsu-inbox/SKILL.md`（依賴聲明的 handoff 版號）
- **Approach**：
  1. add 6-2：在「列出本機 session，兩層匹配」之前插入一句「先排除狀態為 offline 的列（清單未提供狀態資訊時視同全部 online、不過濾）」，並把「同一慣例名的 slot 變體開了兩個以上……即屬多重命中」的主詞改為「online 候選中」；其餘文字不動（KTD1、KTD3）。句末補「（2026-10-03 定案：offline 列為已關閉 session 的殘影，不是收件目標）」括註。
  2. reply 6-1：前置句插在「列出本機 session，兩層匹配——」之前，「**唯一且明確才發送**」改為「**online 候選中唯一且明確才發送**」，括號內「含同一慣例名的多個 slot 變體並存」維持原文，同樣補 2026-10-03 括註。
  3. add 6-3 與 reply 6-2 的「以 ref 重送」句後補 R2a 定址規則一句：命中列的 `[ref]` 於匹配時記下，發送一律以該 ref 定址，不改取錯誤訊息中其他同名列的 ref。
  4. 版號三處同步（KTD5）。
- **Patterns to follow**：既有 add 6-3 的「（2026-08-13 試點實測行為）」日期括註寫法，本次於 add 6-2／reply 6-1 補「（2026-10-03 定案）」括註說明 offline 排除緣由一句。
- **Test scenarios**：
  - 以 `grep -cF '排除狀態為 offline' skills/handoff/SKILL.md` 計數恰為 2。
  - `scripts/consistency-check.sh` A1 版號鏈 PASS（三處皆 0.24.1）。
  - 人工情境：清單為 `ebook-ios-app` 1 筆 idle 加 2 筆 offline → 依修訂文字判為唯一命中，以 idle 列的 `[ref]` 發送。
  - 人工情境（reply）：清單為 `ebook-kunsu` 1 筆 idle 加 4 筆 offline → reply 6-1 判唯一命中。
  - 人工情境：清單為 `ebook-kunsu` 1 筆 idle、`ebook-kunsu.deploy` 1 筆 idle、其餘 offline → 仍判多重命中降級（KD3 不動）。
  - 人工情境：清單無狀態欄 → 不過濾，行為同修訂前。
- **Verification**：兩處文字對照一致；一致性檢查 A1 PASS。

### U2. 副本對齊：CONCEPTS、kc.fish、ADR 015 與一致性檢查錨句

- **Goal**：三份規則副本加上 offline 排除的用語，kc.fish 檔頭補殘影成因與設定建議，一致性檢查新增 T 項守住錨句。
- **Requirements**：R4、R6、R5
- **Dependencies**：U1（定型用語以 U1 落定者為準）
- **Files**：
  - `CONCEPTS.md`（「派發即推播」詞條）
  - `README.md`（「session 命名慣例」條目）
  - `scripts/kc.fish`（檔頭註解）
  - `docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md`（Decision 2、6 修訂註記）
  - `scripts/consistency-check.sh`（新增 T 項）
- **Approach**：
  1. CONCEPTS 詞條與 README「session 命名慣例」條目在「唯一才發送」前補「先排除狀態為 offline 的 session」短語。
  2. kc.fish 檔頭「推播匹配會把帶後綴的 session 一併列入候選」段補兩點：每次 `kc` 都是新 session、關掉後若啟用 Remote Control 會留 offline 殘影，匹配已排除之；成因二依 R6 以「推斷」標示；建議 `remoteControlAtStartup` 設 false、需要時以 `/remote-control`（`/rc`）按需開啟，並附代價句（KTD7、R6）。
  3. ADR 015 Decision 2 與 Decision 6 各補「> 修訂註記（2026-10-03）」一段：候選集先排除 offline，理由與本機實測數據一句，並帶一句「兩層匹配與 slot 變體規則見 SKILL.md add 6-2（2026-08-21 定案）」補 ADR 本文未載的中間演進（KTD4）。
  4. consistency-check 新增 T 項（KTD6），置於 S 項之後。
- **Patterns to follow**：ADR 010 第 29–47 行的修訂註記格式；consistency-check Q 項的 `grep -cF` 錨句檢查形。
- **Test scenarios**：
  - T 項正向：三檔錨句齊全 → PASS。
  - T 項負向：對 CONCEPTS、README、kc.fish、ADR 015 各暫時刪除一處錨句 → FAIL 並點名檔案，還原後 PASS（每檔實跑一次負向案例後還原，沿用 R 項落地時的做法）。
  - ADR 015 frontmatter `status: accepted` 不變，修訂註記兩段皆含「2026-10-03」。
- **Verification**：`scripts/consistency-check.sh` 全 PASS，T 項出現在輸出中。

### U3. 開發日誌條目與部署

- **Goal**：在開發日誌追加本次條目（含殘影成因、官方文件查證結論、取捨），重佈署 skill。
- **Requirements**：R6
- **Dependencies**：U1、U2
- **Files**：
  - `docs/history/development-log.md`
- **Approach**：
  1. 依既有條目格式追加「推播匹配排除 offline session（2026-10-03，handoff v0.24.1）」一條：來源（本機 ListAgents 實測 19/21 offline）、成因兩層、官方文件查證（無 CLI 清除法、無過期政策、`/rc` 按需開啟）、決策（KD1–KD3）、驗證結果。
  2. 執行 `install.sh` 重佈署；SessionStart hook 下次啟動印版號變動提示屬預期。
  3. `cp scripts/kc.fish ~/.config/fish/functions/kc.fish`（依 kc.fish 檔頭既有安裝說明；`install.sh` 不處理頂層 `scripts/`）。
  4. 成因二實測（可選，需使用者於終端操作）：以 `kc` 開一個 session 後關閉，重列清單確認多一筆同名 `Remote Control · offline` 列；完成即把日誌與 kc.fish 中的「推斷」改為實證，未做則維持「推斷」標示。
- **Test expectation**：none -- 純文件條目與部署；以下列 Verification 為證。
- **Verification**：日誌條目含成因兩層、官方文件查證結論（無 CLI 清除法、無過期政策）、`remoteControlAtStartup` 建議與 `/rc` 按需開啟、代價句；部署副本 `~/.claude/skills/handoff/SKILL.md` 版號 0.24.1 且錨句恰為 2、兩處含降級句與「online 候選中」字樣；`diff -q scripts/kc.fish ~/.config/fish/functions/kc.fish` 無輸出。

## Verification Contract

| 檢查 | 指令／方式 | 適用單元 | 通過訊號 |
|------|-----------|---------|---------|
| 跨檔一致性 | `bash scripts/consistency-check.sh` | U1、U2 | `fail=0`，A1 顯示 0.24.1，T 項 PASS |
| 錨句計數 | `grep -cF '排除狀態為 offline' skills/handoff/SKILL.md` | U1 | 輸出 `2` |
| T 項負向 | 暫刪一處錨句後實跑，再還原 | U2 | FAIL 點名該檔；還原後 PASS |
| 人工情境 | 以本機 ListAgents 當前清單對照修訂文字走一遍 add 6-2 與 reply 6-1 | U1 | `ebook-ios-app` 判唯一命中並取 idle 列 ref；`ebook-kunsu` 情境同 Success Criteria |
| 端到端實發（可選） | 經使用者同意後，依修訂規則向本機活的 `ebook-ios-app` 實發一則定型通知 | U1 | 收方視窗回顯重點、發送端回報已推播；結果寫入 U3 日誌 |
| 部署 | `./install.sh` 後讀部署副本 | U3 | `version: 0.24.1`，錨句恰為 2，兩處含降級句 |
| kc.fish 部署 | `diff -q scripts/kc.fish ~/.config/fish/functions/kc.fish` | U3 | 無輸出 |

既有 pytest（沙盤、kunsu-inbox）不受影響，不需重跑；若實作過程誤觸 `.py`，即為 Stop condition。

## Definition of Done

- 全域：三單元完成、一致性檢查全綠、部署副本版號一致、無 `.py`／`.sh` 邏輯改動（consistency-check.sh 新增檢查項除外）。
- U1：兩處規則文字含同一組定型用語與降級句；版號鏈三處同步。
- U2：CONCEPTS、README、kc.fish、ADR 015 四副本對齊；T 項正負向皆驗過。
- U3：開發日誌條目含 R6 全部內容；skill 已重佈署且部署副本錨句核過；kc.fish 部署副本與 repo 一致。
- 清理：無暫時性負向測試殘留（刪掉的錨句已還原）。

## Appendix

### offline 殘影：成因、清除現況與設定建議（2026-10-03 查證）

- **成因一（repo 內）**：`scripts/kc.fish` 以 `claude -n <慣例名>` 啟動，每次都是新 session ID，名字只是顯示標籤；續接舊 session 要靠 `claude --resume`，kc 刻意不走這條路（避免與 `-n` 衝突）。
- **成因二（使用者機器，推斷）**：`~/.claude/settings.json` 的 `remoteControlAtStartup: true`——官方文件語意為「每個 session 啟動時自動連接 Remote Control」；設 `false` 關閉自動連接，`default` 依組織或預設值。「process 結束後該 session 的 Remote Control 登記留存為 offline」為依清單形態（19 筆 offline 皆為 Remote Control kind）所作的推斷，未經開關一次 session 的對照實測。
- **清除現況**：官方文件未載明 offline 條目的 CLI 刪除指令（`claude remote-control` 子指令與 `claude rm` 皆無對應），未載明自動過期政策；僅提到 session 可被歸檔、claude.ai/code 可篩選已歸檔 session，無具體網頁操作步驟。
- **按需開啟**：session 內 `/remote-control` 或 `/rc`，或以 `claude --remote-control` 啟動，皆不需預先設定。
- **來源**：https://code.claude.com/docs/en/remote-control.md（`remoteControlAtStartup` 設定、`/remote-control` 指令、archived session 描述與篩選說明）。
- **本機實測（2026-10-03）**：ListAgents 21 筆 peer，19 筆 `Remote Control · offline`；同名 offline 最多 4 筆（`ebook-kunsu`）；活的 2 筆為 `kunsu-60`、`ebook-ios-app`，皆 `interactive · idle`。
