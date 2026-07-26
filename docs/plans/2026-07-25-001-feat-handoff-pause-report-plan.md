---
title: "feat: handoff 暫離回報慣例"
type: feat
status: completed
date: 2026-07-25
origin: docs/brainstorms/2026-07-25-handoff-pause-report-requirements.md
---

# feat: handoff 暫離回報慣例

## Summary

為 `/handoff` skill 建立「暫離回報」慣例:接手方暫停交接工作、切換任務前,投遞最小 `status: partial` 回覆附 branch 名,使軍師端把交接自「未接手」看成「部分完成」。三個實作單元:SKILL.md 指引與觸發詞、「回覆方式」定型文字兩副本連動、版號與母體文件同步。handoff v0.8.1 → v0.9.0。

---

## Problem Frame

實證案例:交接工作已 commit 至 branch、未合併,接手方臨時插單切走且未回覆,軍師沙盤誤判「未接手」。協議唯一狀態訊號源是回覆檔,機制正確、訊號缺席;斷點在切換任務當下無任何提醒(見 origin: docs/brainstorms/2026-07-25-handoff-pause-report-requirements.md)。事發語句「把做好的部份先移到新的 branch,現在要先做新的需求,之後再回來整合」無任何交接語彙,單靠觸發詞攔不住,因此指引須同時種進接手方 session 必然讀到的交接檔定型文字。

---

## Requirements

沿用 origin 的 R1–R9(逐字定義見 origin 文件):

**指引內容(SKILL.md reply 段)**

- R1. reply 段新增「暫離回報」指引:切走前投遞最小回覆——`status: partial`,內文至少含 branch 名、一句現況、之後回來繼續的意向。
- R2. 明訂固定用 `partial` 並簡述理由(剩餘步驟仍在接手方手上,避免發起方誤啟收尾)。
- R3. `verify` 照常評估選填;branch 資訊寫內文、不放 `verify`,不新增建議代碼。
- R4. 提醒回歸後照常投遞完成回覆(`status: submitted`),引用 verify 不跨回覆繼承規則。

**觸發詞(SKILL.md description)**

- R5. 補暫離語境口語觸發詞,一律帶交接語境,避免無交接場景誤觸發。

**定型文字(交接檔「回覆方式」段落)**

- R6. `new-handoff.sh` printf 定型文字加一行暫離提示。
- R7. SKILL.md「檔案格式範例」段同文案副本連動修改,維持字面一致。

**範圍與同步**

- R8. `status`/`verify` 值域、四份值域語意副本、沙盤分類邏輯、軍師範本零改動;不需 live 軍師遷移。
- R9. handoff 版號升版,kunsu-inbox 依賴聲明版號同步。

---

## Key Technical Decisions

- **版號升 0.9.0(minor),依賴聲明一併收斂既有漂移** — 版號慣例:新增行為/觸發詞 → minor(先例:v0.6.0 done 收尾閉環、v0.7.0 逐項驗收查核)。`skills/kunsu-inbox/SKILL.md` 依賴聲明現記 v0.8.0、handoff 實際已 0.8.1(既存漂移),本次直接寫 0.9.0 收斂,不另開修正輪。
- **暫離回報以獨立子節附於 reply 段,不改既有五步驟編號** — reply 段現有步驟 1–5 被 kunsu-inbox 依賴聲明與既有慣例引用;暫離回報是 reply 的特化情境(最小內文、固定 partial),以「暫離回報」子節收尾 reply 段即可,零編號牽動。
- **觸發詞套用補詞三步驟** — 收集真實口語、帶語境拒裸詞、負向場景驗證(docs/solutions/workflow-issues/handoff-done-closure-gap.md 既有教訓;「暫離」「先放著」等裸詞會在無關情境誤觸,一律夾帶「交接」語彙)。
- **定型文字新行插於 status 值域說明之後,兩副本逐字一致;順手拉齊既有換行差異** — solutions 教訓明示最高風險是「只改範例、漏改產生器」;既有「建立回覆檔案」斷行差異(SKILL.md 範例段有換行、printf 輸出無)與本次編輯同一區塊,以 printf 實際輸出為準拉齊範例段,近零成本消除既有債。
- **範本與沙盤零改動(origin R8)** — `partial` 為既有值,ADR 011 值域約束零觸及;kunsu-init 範本的值域行是「值域語意副本」,本次未修訂值域故無連動義務;ADR 009 投遞端不 commit 邊界不受影響(暫離回報屬 kunsu 語境 reply,本就不 commit)。

---

## Implementation Units

### U1. SKILL.md 暫離回報指引與觸發詞

- **Goal**:reply 段新增「暫離回報」子節,description 補暫離語境口語。
- **Requirements**:R1、R2、R3、R4、R5(Covers AE3)。
- **Dependencies**:無。
- **Files**:`skills/handoff/SKILL.md`。
- **Approach**:
  - 子節置於 reply 段步驟 5 之後,標題含「暫離回報」字樣。內容涵蓋:適用情境(工作已有階段性成果但需切換任務暫離)、最小內文三要素(branch 名、一句現況、回來意向)、固定 `status: partial` 與理由、verify 照常選填且 branch 不入 verify、回歸後照常投遞 `submitted` 完成回覆並顯式複寫 verify(引用既有步驟 2 的不繼承說明,一句帶過)。
  - description 觸發詞插於「/handoff」. 終止符之前(比照 v0.3.0、v0.6.0 先例形狀),候選:「交接工作先暫停」「交接先放著,先做別的需求」「交接工作先放到 branch,之後再回來」「暫停這份交接」——每一個都含「交接」語彙,實作時逐一核對。
- **Patterns to follow**:v0.3.0(commit 4265817)與 v0.6.0(commit 020edba)的 description 補詞 diff 形狀;done 章節「時機與守門」的正反行為指引寫法。
- **Test scenarios**(文件層核查):
  - Covers AE3. 「交接工作先暫停,先去做別的」語意可命中新增觸發詞。
  - 負向場景:「先暫離辦公室」「這個功能先放著之後再回來」(無交接語彙)不在觸發詞字面覆蓋內。
  - 指引含最小內文三要素、固定 partial 理由、verify 規則引用、回歸完成回覆提醒(對照 R1–R4 逐項)。
  - reply 段步驟 1–5 編號與內容未被牽動(diff 核查)。
- **Verification**:Read 全段確認結構;grep 新增觸發詞與「暫離回報」字樣命中。

### U2. 「回覆方式」定型文字兩副本連動

- **Goal**:每份新交接檔的「回覆方式」段落帶暫離提示行,兩副本字面一致。
- **Requirements**:R6、R7(Covers AE1 的定型文字存在性前提)。
- **Dependencies**:U1(「暫離回報」一詞與指引先落地,定型文字引用同一詞彙)。
- **Files**:`skills/handoff/scripts/new-handoff.sh`、`skills/handoff/SKILL.md`(「檔案格式範例」段)。
- **Approach**:
  - 新行接在 status 值域說明段之後,方向性文案:「中途需切換任務時,請先投遞暫離回報——`status: partial`、內文附 branch 名與現況,之後回來再照常回覆。」(實作時定稿,兩處逐字一致。)
  - printf 與範例段同步修改;順手把範例段「請執行以下指令建立\n回覆檔案:」的既有斷行拉齊為與 printf 輸出一致的單行。
- **Patterns to follow**:`new-handoff.sh` 既有 printf 區塊的跳脫寫法(反引號、`--` 前綴防連字號誤判)。
- **Test scenarios**:
  - Covers AE1(前提層). 暫存目錄實跑 `new-handoff.sh` 產檔,輸出的「回覆方式」段含暫離提示行,且 frontmatter 與既有段落結構不變。
  - grep「暫離回報」於 `new-handoff.sh` 與 SKILL.md 範例段皆命中,該行字面一致。
  - 兩副本 status 值域段維持逐字相同(diff 核對)。
  - AE1 的模型行為端(session 讀過交接檔後主動建議暫離回報)屬模型層,無法自動化;以定型文字存在性為驗收基準,實際 session 試誤列選作。
- **Verification**:暫存目錄產檔輸出目視+grep 比對兩副本。

### U3. 版號與母體文件同步

- **Goal**:版號 0.9.0 落地、依賴聲明收斂、零改動範圍核查、母體文件同步。
- **Requirements**:R8、R9。
- **Dependencies**:U1、U2(版號描述需反映最終改動內容)。
- **Files**:`skills/handoff/SKILL.md`(frontmatter version)、`skills/kunsu-inbox/SKILL.md`(依賴聲明版號)、`CLAUDE.md`(專案結構 handoff 行、開發狀態新條目)。
- **Approach**:
  - frontmatter `version: 0.8.1` → `0.9.0`;kunsu-inbox 依賴聲明「v0.8.0」→「v0.9.0」(依賴聲明表格內容不需改——本次未動回覆檔命名、值域、信箱目錄、done 歸檔形狀)。
  - CLAUDE.md 專案結構的 handoff 行版號與描述更新;開發狀態補本輪條目。
  - R8 核查:`git status`/`git diff` 確認未觸及 `skills/kunsu-dashboard/`、`skills/kunsu-init/assets/templates/`、status/verify 值域文字。
- **Test scenarios**:Test expectation: none — 純版號字串與母體文件同步,以 grep 與 diff 核查取代測試。
- **Verification**:grep `0.9.0` 於 handoff frontmatter 與 kunsu-inbox 依賴聲明皆命中;`git diff --stat` 僅含本計畫預期檔案。

---

## Scope Boundaries

沿用 origin 四項(軍師端自動偵測 branch 不做、回覆檔 `branch:` 欄位不加、存量交接檔不回填、值域不擴充)。

### Deferred to Follow-Up Work

- 明訂「接手方開始執行交接前須先 Read 交接檔本體」為協議步驟(doc review 延後問題;會擴張 handoff 協議本體,另案評估)。
- 定型文字升級為主動查核句(「每次切換任務前先確認是否需暫離回報」);本次採單行被動提示,實測攔截率不足再升級。

---

## Documentation / Operational Notes

- 部署:repo 改完需重新執行 `./install.sh` 才在 `~/.claude/skills/` 生效(copy 模式預設;`--link` 模式即時生效)。驗證前確認部署模式。
- CONCEPTS.md「暫離回報」詞條已於 brainstorm 階段寫入,本輪無需再動。
- 不主動 commit;完成後由使用者決定(全域規範)。

---

## Sources / Research

- `skills/handoff/SKILL.md` — frontmatter 版號、description 觸發詞清單、reply 段步驟結構、「檔案格式範例」段定型文字(範例副本)。
- `skills/handoff/scripts/new-handoff.sh` — 「回覆方式」printf 區塊(產生器副本,top-level 線性腳本)。
- `skills/kunsu-inbox/SKILL.md` — 依賴聲明段(現記 v0.8.0,既存漂移)。
- `docs/solutions/workflow-issues/handoff-done-closure-gap.md` — 補詞三步驟、「範例 vs 產生器」副本同步教訓(severity: high)。
- `docs/adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md`、`docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md` — 邊界核查:本計畫全落在既有協議邊界內,零牴觸。
- git 先例:commit 4265817(v0.3.0 reply 路由補洞)、020edba(v0.6.0 done 收尾口語)— description 補詞 diff 形狀。
