---
name: kunsu-inbox
version: 0.14.0
description: |
  查詢跨 repo 協作信箱：列出軍師（規劃協調中心）中待接手的交接文件，或回報新抵達的回覆。
  觸發語：/kunsu-inbox、檢查信箱、有沒有待接手的交接、有沒有新的 handoff、
  查看 handoff 清單、檢查新回覆、inbox、收件匣、有沒有待處理的交接、
  信箱還有幾件、信箱幾件、還有哪些待收尾、待收尾有哪些、現在有幾件待處理、
  查看交接狀態、kunsu inbox、kunsu-inbox。
  （回報自身信箱狀態的具體數字一律以本 skill 的掃描結果為準，不憑對話記憶作答。）
  依當前 repo 在 ~/.claude/kunsu-registry.json 中的身分自動選擇模式：
  - 子 repo 模式：列出所屬軍師中 to: 為本角色的未接手／部分完成／已回覆待確認交接文件
  - 軍師模式：回報 docs/handoffs/replies/ 新回覆、docs/applications/ 新申請與
    docs/reports/ 新上報的未 commit 份數，並執行 tripwire 核對
  - 巢狀拓撲（兩者皆符合）：合併輸出兩種模式的結果
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# kunsu-inbox — 跨 repo 協作信箱

查詢全域反向註冊表（`~/.claude/kunsu-registry.json`），依當前 repo 身分列出跨 repo 的待處理交接訊息。

---

## Agent 對應表

本 skill 以能力名描述步驟；各 agent 的實際工具與慣例對應如下（七份 SKILL.md 共用同一張表，由 `scripts/consistency-check.sh` 比對逐字一致；新增 agent 只改此表，不改內文）。

| 能力 | Claude Code | Codex |
|------|-------------|-------|
| 阻塞式確認（流程中需使用者當下裁決的提問） | AskUserQuestion 工具 | 預設無阻塞式工具（`request_user_input` 僅 plan mode；開啟 `[features] default_mode_request_user_input` 後可用即用）：印出定型指令與訊息並結束回合，下一回合收到使用者明確同意文字才執行 |
| 跨 session 推播（向另一個長駐 session 發一次性通知） | ListAgents＋SendMessage 工具 | 無對應物：整步跳過，由 SessionStart hook 兜底 |
| skill 目錄（本 skill 部署後所在目錄，用於定位 scripts/ 與 assets/） | `$CLAUDE_SKILL_DIR`（harness 注入；未定義時以本 SKILL.md 所在目錄推算），部署於 `~/.claude/skills/<name>/` | 無注入變數：以本 SKILL.md 所在目錄推算，部署於 `~/.agents/skills/<name>/` |
| skill 呼叫形（使用者或指引點名某個 skill） | `/<name>` 斜線指令 | `$<name>` 顯式呼叫，或依 description 自動選用（斜線只保留給內建指令） |
| hook 設定檔（機器層級，不進 repo） | `~/.claude/settings.json` 的 `hooks` | `~/.codex/hooks.json`（或 config.toml `[hooks]`）；改動後須於 TUI 重新信任 |
| 子 agent（副官：派出新鮮 context 分擔查證與提取） | Agent 工具（subagent） | `spawn_agent`（custom agents 於 `~/.codex/agents/*.toml`） |

未列於本表的 agent 一律採 Codex 欄行為：文字回合確認、不逕行執行；跨 session 推播整步跳過。

## ⚠️ 授權邊界（必讀）

**以下三條限制不得例外：**

1. **只告知不開工** — 本 skill 只回報信箱狀態，不自動接手任何交接文件、不自動執行任何後續動作。一切動工須使用者明確指示。
2. **不主動輪詢** — 本 skill 僅在使用者觸發時執行一次，不設定任何定時執行或背景監聽。（SessionStart hook 為使用者自行於 hook 設定檔（見 Agent 對應表）掛載的**事件驅動**通道——session 啟動是使用者的動作，hook 隨之執行一次同邏輯的確定性掃描，無定時器、無背景監聽，不違反本條；見下方「SessionStart hook」節與 ADR 014。UserPromptSubmit hook 同理——使用者提問是使用者的動作，hook 隨之執行一次三信箱新件的確定性掃描，見下方「UserPromptSubmit hook」節與 ADR 014 修訂註記。）
3. **三個信箱是唯讀邊界的唯一例外** — 軍師的 `docs/handoffs/replies/`（接手方建立新回覆檔案）、`docs/applications/` 頂層（子專案以 kunsu-apply skill 建立新申請檔案）與 `docs/reports/` 頂層（子專案以 kunsu-report skill 建立新上報檔案）是僅有的三個授權寫入點。軍師其他任何目錄均屬唯讀。

---

## 執行步驟

### 步驟 1：取當前 repo 根路徑

執行以下指令，取得 git repo 根（**不使用 cwd**，避免從子目錄誤判）：

```bash
git rev-parse --show-toplevel
```

將結果記為 `CURRENT_ROOT`（絕對路徑）。若非 git repo 則報錯停止。

---

### 步驟 2：讀取與解析全域反向註冊表

嘗試以 `Read ~/.claude/kunsu-registry.json` 讀取檔案。

**可能的錯誤情境（獨立判斷，不混同）：**

- **檔案不存在** → 報錯並停止：
  > 找不到 `~/.claude/kunsu-registry.json`。請先執行 kunsu-init skill 建立軍師並完成登記。

- **檔案存在但 JSON 格式損壞**（無法解析為合法 JSON 物件）→ 報錯並停止：
  > `~/.claude/kunsu-registry.json` 格式損壞，請手動修復（應為合法 JSON 物件）。
  
  不得將「格式損壞」與「未登記」混同回報。

- **JSON 為合法空物件 `{}`** → 可正常解析，進入步驟 3（兩個判斷皆為否，走到未登記錯誤分支）。

**Registry schema（供解析參考）：**
```json
{
  "<子 repo 絕對路徑>": [
    {
      "kunsu": "<軍師絕對路徑>",
      "roles": ["<角色代碼>", "..."]
    }
  ]
}
```

每個子 repo 鍵對應一個條目陣列（可隸屬多個軍師），每個條目有 `kunsu`（字串）和 `roles`（字串陣列）。

---

### 步驟 3：模式偵測（雙重獨立判斷）

以 `CURRENT_ROOT` 對已解析的 registry JSON 進行**兩個獨立判斷**，結果可同時為真（巢狀拓撲）：

**判斷 ①（子 repo 身分）：**
`CURRENT_ROOT` 是否為 registry 的鍵（key）？
- 若是：取 `registry[CURRENT_ROOT]` = 條目陣列（`[{kunsu, roles}, ...]`），記為 `SUBREPO_ENTRIES`。

**判斷 ②（軍師身分）：**
`CURRENT_ROOT` 是否出現在任一條目的 `kunsu` 欄位？
- 掃描 registry 所有鍵、所有條目，若有 `entry.kunsu == CURRENT_ROOT`，則標記為軍師。

**四種結果的處理：**

| 判斷 ① | 判斷 ② | 執行 |
|--------|--------|------|
| 是 | 否 | 僅執行步驟 4a（子 repo 模式）|
| 否 | 是 | 僅執行步驟 4b（軍師模式）|
| 是 | 是 | 步驟 4a 與 4b 合併執行（巢狀拓撲）|
| 否 | 否 | 報錯並停止：`CURRENT_ROOT` 不在任何已知登記中。請執行 kunsu-init skill 建立軍師，或執行 kunsu-init skill 的 add-project 子指令將此 repo 登記至現有軍師。|

**重要：不以目錄存在與否作為判斷依據。** 任何跑過 handoff skill reply 子指令的一般 repo 都有 `docs/handoffs/replies/`，以目錄判斷會造成誤判。

---

### 步驟 4a：子 repo 模式

對 `SUBREPO_ENTRIES` 中的每個條目，**依軍師分組**執行以下掃描。

**4a-1. 收集此軍師的全部已知角色代碼：**

掃描整個 registry，找出所有 `entry.kunsu == kunsu_path` 的條目，將其 `roles` 陣列（角色代碼集合）取聯集，得到 `ALL_KNOWN_ROLES`。這用於後續的「to: 不符清單」核對——handoff `to:` 值即角色代碼，精確比對此集合。

**4a-2. 掃描軍師的交接文件：**

```
Glob("{kunsu_path}/docs/handoffs/*.md")
```

此 Glob 僅取頂層 `.md` 檔案。若結果路徑中含 `/replies/` 或 `/archive/` 子目錄，略過（正常情況不應出現，因 `*.md` 不遞迴）。

對每個掃描到的 handoff 檔案：
1. `Read` 其 frontmatter（至少讀取 `title`、`from`、`to`、`created`）
2. 取得 handoff 的**檔名**（basename，含 `.md` 後綴），記為 `HANDOFF_FILENAME`
3. 判斷 `to:` 值：
   - 若 `to` ∈ `our_roles`（本 repo 在此軍師的角色集合）→ **納入主處理流程**（步驟 4a-3）
   - 若 `to` ∉ `ALL_KNOWN_ROLES` → **加入「to: 不符清單」**（步驟 4a-4）
   - 若 `to` ∈ `ALL_KNOWN_ROLES` 但 ∉ `our_roles` → 屬於其他子 repo，靜默略過

**4a-3. 狀態推導（針對 `to` ∈ `our_roles` 的 handoff）：**

掃描軍師的回覆目錄，找出此 handoff 的最新回覆：

```
Glob("{kunsu_path}/docs/handoffs/replies/*.md")
```

從結果中：
1. `Read` 每個回覆的 frontmatter，取 `in_reply_to`、`status` 與 `verify`（選填
   欄位，驗收方式；缺省視為無，純空白字串視同缺省）
2. 篩選 `in_reply_to == HANDOFF_FILENAME`（精確字串比對，`in_reply_to` 應含 `.md` 後綴）
3. 若有多份符合，依以下規則取「最新回覆」：
   - 從每個回覆檔名中解析 `{date}` 與可選的 `{n}`（無 `-2`、`-3`… 後綴時 n=1）
   - 排序鍵為 `(date, n)`，均降序（先比日期，日期相同再比 n）
   - 取排序後第一筆（date 最新、同日 n 最大）為「最新回覆」

   > **注意**：勿直接對檔名做字串降序排列（lexicographic）——因 ASCII 中 `-` (45) < `.` (46)，同日多份時「無後綴的基礎回覆」`.md` 字串排名反而高於有 `-2` 後綴者，會誤取較舊的一份。必須提取數值後綴做數值比較。
   >
   > 範例：`...-reply-2026-07-06-2.md` (n=2) 比 `...-reply-2026-07-06.md` (n=1) 新。

4. 依最新回覆狀態分類：

   | 情況 | 分類 |
   |------|------|
   | 無符合的回覆（零筆） | **未接手** |
   | 最新回覆 `status: partial` | **部分完成** |
   | 最新回覆 `status: blocked` | **部分完成**（另標 ⛔ 卡關） |
   | 最新回覆 status 為未知值 | **部分完成**（原樣顯示該 status，保守不略過） |
   | 最新回覆 `status: submitted` | **已回覆待確認** |
   | 最新回覆 `status: done` | **略過，不列出** |

   分類判準是「有無回覆」：有回覆就不是未接手。「部分完成」與「已回覆待確認」
   的項目一併呈現最新回覆的 `verify` 值（**驗收欄**）——建議代碼轉中文標籤
   （`needs-deploy`→需上線測試、`testable-now`→馬上可測、`needs-device`→
   需實機測試；比對前正規化為小寫），其他字串原樣顯示，缺省顯示 `—`。
   verify **只讀最新回覆、不跨回覆繼承**：最新回覆未填即顯示 `—`，不沿用
   前輪值（ADR 011）。

**4a-3b. 交接依賴圖推導態（handoff v0.23.0 起，advisory）：**

不手算依賴——執行同 toolkit 的 CLI 取推導態（單一推導來源為沙盤 `app/handoff_graph.py`，兩 agent 呼叫形相同）：

```bash
python3 "<skill 目錄>/scripts/handoff-graph.py" "{kunsu_abs_path}" --role "{我的角色代碼}"
```

- 每行 `DEP:<檔名>\t<ready|waiting>\t<在等的檔名逗號分隔>` → 該交接的推導態：`ready`＝**可開工**（全部直接依賴的本體 `status: done`）、`waiting`＝**等依賴**（附在等哪些）；未列出的交接為孤立節點（無依賴宣告亦無人依賴），不標推導態
- `DEP_CYCLE:`／`DEP_UNRESOLVED:`／`DEP_ANOMALY:`／`DEP_ERROR:` → 顯式列於輸出尾端「依賴圖異常」段（不靜默略過；`DEP_ERROR` 表示建圖失敗，只降級此段）
- `DEP_NONE` → 無任何依賴宣告，輸出不加「依賴」欄

推導態與回覆分類正交：「未接手＋可開工」＝營該動了、「未接手＋等依賴」＝正當空等；「部分完成」或「已回覆待確認」仍可能等依賴（並列顯示，不互抑）。

**4a-4. 「to: 不符清單」核對：**

若有任何 handoff 的 `to:` 值不在 `ALL_KNOWN_ROLES` 中，收集這些項目。

**4a-5. 輸出格式（每個軍師一組）：**

```
## 軍師：{kunsu_abs_path}

### ☐ 未接手（{N} 份）

| 交接文件 | 建立日期 | 方向 | 依賴 |
|---|---|---|---|
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | 可開工 |
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | 等依賴：{上游檔名} |

### ◐ 部分完成（{N} 份）

| 交接文件 | 建立日期 | 方向 | 回覆狀態 | 驗收 | 依賴 |
|---|---|---|---|---|---|
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | partial（{reply_date}）| 需上線測試 | — |
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | ⛔ blocked（{reply_date}）| — | 等依賴：{上游檔名} |

### ✓ 已回覆待確認（{N} 份）

| 交接文件 | 建立日期 | 方向 | 最新回覆日期 | 驗收 | 依賴 |
|---|---|---|---|---|---|
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | {reply_date} | 馬上可測 | — |

（「依賴」欄：4a-3b 的推導態；孤立節點顯示 `—`；`DEP_NONE` 時整欄省略。）

### ⟳ 依賴圖異常（{N} 筆）——僅 4a-3b 有 DEP_CYCLE／DEP_UNRESOLVED／DEP_ANOMALY／DEP_ERROR 時附加

- 循環：{檔名,檔名}
- 無法解析：{檔名} → {目標}（{原因：not_found／reply_file／bad_type}）
- 異常：{檔名}（{archived_not_done／duplicate}）

---
### 回覆方式（Method 2 — 無需切換工作目錄）

在以下路徑直接建立回覆檔案，不依賴當前工作目錄：

  {kunsu_abs_path}/docs/handoffs/replies/{原交接檔名}-reply-YYYY-MM-DD.md

frontmatter 範本：
---
title: {交接標題} — 回覆
type: handoff-reply
from: {我的角色代碼}
to: {交接文件的 from 值}
in_reply_to: {原交接檔名（含 .md 後綴）}
created: YYYY-MM-DD
status: submitted
---

（選填欄位 verify: 可標注驗收方式——needs-deploy／testable-now／needs-device
或自由字串，無明確驗收需求則省略。）
```

**若有「to: 不符清單」時，附加：**

```
⚠️ to: 不符清單（{N} 份）
以下交接文件的 to: 值不在此軍師已登記的任何角色代碼集合中，可能是拼寫錯誤或尚未以 add-project 登記：
- {HANDOFF_FILENAME}: to: {unknown_value}
請核查拼寫，或以 add-project 在此軍師補登記對應角色代碼。
```

**若「未接手」「部分完成」「已回覆待確認」三分類皆為空（本角色無任何待處理交接）：**

```
## 軍師：{kunsu_abs_path}

本 repo 角色（{roles}）目前無任何待處理的交接文件。
```

---

### 步驟 4b：軍師模式

**4b-1. 呼叫掃描腳本（三支）：**

```bash
bash "<skill 目錄>/scripts/scan-replies.sh" "{CURRENT_ROOT}"
bash "<skill 目錄>/scripts/scan-applications.sh" "{CURRENT_ROOT}"
bash "<skill 目錄>/scripts/scan-reports.sh" "{CURRENT_ROOT}"
```

`<skill 目錄>` 為本 skill 部署後所在目錄（定位見 Agent 對應表：以本 SKILL.md 所在目錄推算）。依序執行，各自記錄 stdout 輸出與 exit code。`scan-applications.sh` 對無 `docs/applications/` 的舊版軍師輸出零筆、exit 0（向後相容，不報錯）；`scan-reports.sh` 對無 `docs/reports/` 的舊版軍師同樣輸出零筆、exit 0（向後相容設計）。任一腳本以非 0 且非 2 的 exit code 結束（如 1：參數錯誤或非 git 根）→ 停下回報該腳本的 stderr，不繼續彙整。

**4b-1b. 交接依賴圖摘要（handoff v0.23.0 起，advisory，獨立於 tripwire 之外）：**

```bash
python3 "<skill 目錄>/scripts/handoff-graph.py" "{CURRENT_ROOT}"
```

圖只讀檔不讀 git，4b-3 tripwire 停止彙整時本段仍照印。彙整為一行：可開工 N／等依賴 M，另有 `DEP_CYCLE`／`DEP_UNRESOLVED`／`DEP_ANOMALY`／`DEP_ERROR` 時逐筆列出（不靜默略過）；`DEP_NONE` 則省略本段。

**4b-2. 解析腳本輸出：**

- 每行 `NEW_REPLY:<路徑>` → 新回覆路徑清單（路徑為相對於軍師根的路徑）
- 每行 `NEW_APPLICATION:<路徑>` → 新申請路徑清單
- 每行 `NEW_REPORT:<路徑>` → 新上報路徑清單
- 每行 `TRIPWIRE:<XY> <路徑>`（或 rename 形式 `TRIPWIRE:<XY> <src> -> <dst>`，路徑欄為雙側複合字串）→ 意外變更清單
- 每行 `HISTORY_WARN:<類型> <內容>`（僅 `scan-replies.sh` 產生）→ 歷史夾帶警示清單（advisory，呈現方式見 4b-5）

**4b-3. tripwire 判斷（任一腳本 exit code 2）：**

若任一腳本 exit code 為 2（有 tripwire 行）：
- **立即停止**，不繼續彙整
- 回報（依觸發來源列出對應範圍）：

```
⚠️ 疑似意外寫入偵測到，已停止彙整

信箱授權範圍外有未 commit 的變更：
{每行列出：  {XY} {路徑}}

請確認這些變更是否預期。若為正常操作（如手動建立新交接、或剛執行 handoff skill 的 add 子指令
尚未確認 commit），確認並 commit 後再執行 kunsu-inbox skill。（三個信箱的授權歸檔搬移
——交接與其回覆、申請、上報——均已被掃描規則豁免；handoff skill 的 done 子指令若中斷於
Edit 與 git mv 之間，頂層 ` M` 中間態亦會觸發，續行完成歸檔並 commit 即收斂。）
```

**4b-4. 正常輸出（三支腳本皆 exit code 0）：**

```
## 軍師信箱

收到 {N} 份新回覆（未 commit，等待彙整）：
{每行列出：  - {路徑}}
→ 彙整查核後若確認完成，執行 handoff skill 的 done 子指令收尾歸檔（僅提示，不自動執行）。
→ 彙整時分流：回覆中指向軍師的行動項落 todo 或轉新交接；解答既有疑問者回填至該疑問所在的 todo／plan（僅提示，不自動執行）。

收到 {M} 份新申請（未 commit，等待審核）：
{每行列出：  - {路徑}}
→ 執行 kunsu-init skill 的 add-project 子指令逐筆審核（核准當下才正式登記）。

收到 {K} 份新上報（未 commit，等待審閱）：
{每行列出：  - {路徑}}
→ 開檔審閱後依上報信箱協議四步驟歸檔（Edit status → git add → git mv → 確認 commit；步驟（1）–（3）可用 `archive-report.sh` 一次完成並印出帶 pathspec 的待確認 commit 指令）。
→ 審閱時分流：上報中指向軍師的行動項落 todo 或轉新交接（僅提示，不自動執行）。

（各段為零時改列：目前沒有未 commit 的新回覆。／目前沒有待審申請。／目前沒有待閱上報。）

交接依賴圖：可開工 {N}／等依賴 {M}（4b-1b；`DEP_NONE` 時省略本段）
{有異常時逐筆：  ⟳ 循環：…／無法解析：… → …（原因）／異常：…（種類）}
```

> **「未 commit 即未處理」** 的前提：軍師的慣例是彙整回覆後才 commit，因此 uncommitted 回覆視為尚未處理的標記。若提前 commit，已彙整者在此不再顯示。

**4b-5. 歷史夾帶警示（`HISTORY_WARN:`，advisory）：**

`scan-replies.sh` 除掃描工作樹外，會逐 commit 檢視上次掃描後的新 commit（基線記
於掃描統計檔，見下節），偵測已 commit 歷史中破壞「未 commit 即未處理」訊號的形
狀。輸出含 `HISTORY_WARN:` 行時（tripwire 與否皆可能出現），於彙整結果末尾附加：

```
⚠ 歷史夾帶警示（{J} 筆，advisory——不中止彙整、不影響 exit code）：
{每行原樣列出}
```

- `SMUGGLED_REPLY`：某「docs: 歸檔」開頭的 commit **新增**了 `replies/` 頂層回覆
  檔。歸檔 commit 只該搬移（rename 至 `archive/`）、不該新增——頂層新增即把未讀
  回覆靜默轉為已處理，該批回覆自此從掃描視野消失且雙方皆無錯誤訊號。請逐份確認
  列出的回覆是否確實已閱讀分流；未處理者以 `git reset` 還原為未 commit 重新入列，
  或當場補閱讀處理。
- `BATCH_REPLY_ADD`：任意單一 commit 新增 ≥6 份頂層回覆（啟發式）。批次處理合
  法，但請確認非 `git add -A` 之類的整批掃入。
- `MISDECLARED_ARCHIVE_ADD`：訊息不以白名單前綴（`docs: 歸檔交接`、`docs: 歸檔上報`、`docs: 審核申請`——2026-09-01 ADR 018 修訂自寬前綴 `docs: 歸檔` 收窄，防 `docs: 歸檔 todo` 繼承信箱豁免）
  開頭的 commit **新增**了任一信箱 `archive/`（handoffs／reports／applications）
  檔案——commit 內容疑似超出訊息宣告範圍（ADR 018 的事故形狀：無 pathspec 的
  commit 把前一流程的歸檔暫存一併吞入）。請核對該 commit 是否夾帶：確屬夾帶時以
  `git reset --soft` 拆分重 commit（帶 pathspec），確屬正當時忽略即可（advisory
  不阻斷；新增正當歸檔訊息形狀時白名單須經 ADR 018 修訂擴列）。
- 每筆警示只在事發後的**第一次掃描**出現一次（基線 commit 前進即不重報）；回顧
  歷史警示請查掃描統計檔的事件明細。

---

### 掃描統計（狀態訊號脆弱度觀測）

`scan-replies.sh` 每次執行時把觀測寫入 `~/.claude/kunsu-scan-stats.json`（機器層
級、不進任何 repo；環境變數 `KUNSU_SCAN_STATS_FILE` 可覆寫路徑，供測試隔離）：
各軍師的掃描次數（`total_runs`）、tripwire 次數（`runs_with_tripwire`）、歷史夾
帶警示次數（`runs_with_history_warn`）、歷史檢視基線（`last_checked_commit`）與
事件明細（`events`，含時間戳，每軍師保留最近 500 筆；型別含 `SMUGGLED_REPLY`／
`BATCH_REPLY_ADD`／`MISDECLARED_ARCHIVE_ADD`／`TRUNCATED`——rev-list 滿 200 筆
時聲明該輪數據不完整——／`TRIPWIRE`／`BASELINE_RESET`／`GUARD_DENY`；登記路徑
已不存在的軍師條目於寫入時自動清除）。`MISDECLARED_ARCHIVE_ADD` 的事件計數同時是
ADR 018 開放問題（ADR 017 擴 `git commit` 守門）的啟動依據——僅計上線後、經
人工核對排除誤報的事件（活習慣複合訊息實測約一成誤報，detail 帶完整訊息供
辨識），警示呈現以統計檔為準（一次性 stdout 警示可能被 hook／沙盤消耗）。

用途：給「未 commit 即未處理」狀態訊號的**脆弱度累積數據**——警示頻率高到不可
接受時，才有依據啟動狀態載體重設計（連同回覆檔「單一作者」原則重評，屬 ADR 層
級）的討論；頻率趨零則證明現行輕量防護已足。統計寫入任何失敗一律 fail-open
（單行 stderr 降級），不影響掃描結果與 exit code；python3 不可用時整段靜默跳過。

---

### 步驟 5：合併輸出（巢狀拓撲時）

若步驟 3 同時滿足判斷 ① 和 ②，依序輸出：
1. 步驟 4a 的子 repo 模式結果（各軍師分組）
2. 步驟 4b 的軍師模式結果

兩段之間加分隔線。

---

## SessionStart hook（第二階段傳令，選用）

ADR 002 Decision 3 預留的「第二階段」（ADR 014 啟用）：`scripts/session_hook.py`
於 session 啟動事件（startup／resume／`/clear`／compact／fork）自動執行一次與本
skill 同邏輯的**確定性腳本掃描**（不經 LLM、零 token），把信箱摘要注入開場
context——長駐 session 按 `/clear` 即攤開信箱，不必再手動觸發本 skill。

- **分類邏輯單一來源**：子專案模式匯入軍師沙盤 `app/subrepo_status.py`（＝本
  skill 步驟 4a 的 Python 實作），軍師模式匯入 `app/kunsu_scan.py`（＝三支
  `scan-*.sh` 的包裝）；hook 不自帶任何判斷規則。修改步驟 4a 或掃描腳本時，
  hook 自然跟隨，無需另行同步。
- **只告知不開工**：輸出僅含分類摘要（每分類上限 5 筆＋「另有 N 筆」）與提示
  行，授權邊界三條全數適用。
- **靜默與降級**：未登記 repo 零輸出；任何錯誤一律 exit 0 不阻斷 session
  啟動——身分確認前（如註冊表毀損）靜默，身分確認後（如沙盤模組／PyYAML
  缺失）輸出單行降級提示。
- **依賴**：軍師沙盤已部署（`install.sh` 一併部署）且其 PyYAML 依賴已安裝
  （見 kunsu-dashboard SKILL.md）。
- **skill 版號變動提示**（機制觸及率三件套之一）：身分確認後比對部署
  handoff SKILL.md 版號與狀態檔 `~/.claude/kunsu-hook-state.json`（機器層級，
  不進任何 repo），版號變動時於信箱摘要前輸出一行「handoff skill 已更新至
  vX（自 vY）……」並更新狀態檔；首次執行靜默建檔不提示、相同零輸出、任何
  失敗 fail-open 跳過。動機：熟練 session 手動執行等效步驟時 skill 指引靜默
  失效，更新提示使其在下個 session 得知指引有變。

**掛載**（機器層級設定，不進任何 git repo；hook 設定檔位置見 Agent 對應表）。Claude Code——`hooks` 設定檔（位置見 Agent 對應表）：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/skills/kunsu-inbox/scripts/session_hook.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Codex——完整 hooks 設定檔（位置見 Agent 對應表；頂層只能有 `hooks` 一鍵，多任何鍵整檔解析失敗；handler 只認 `type: command`，欄位限 `type`／`command`／`timeout`（秒）／`matcher`；command 指向 Codex 自己的部署位置，各部署位置自足）：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.agents/skills/kunsu-inbox/scripts/session_hook.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Codex 側掛載固定順序（信任鍵含群組**位置索引**，前面條目改動會使後面條目全變 Untrusted 而靜默略過）：（1）先清理設定檔內指向不存在腳本的壞條目 →（2）再把 kunsu 群組**附加於對應陣列尾端**、不前插 →（3）首次啟動 TUI 於「Hooks need review」提示信任（狀態記於 config.toml 的 `hooks.state`）。設定檔任何改動（含腳本路徑）須重新信任；腳本內容改動不用。掛後自檢：TUI `/hooks` 確認 Trusted；`scripts/consistency-check.sh` 的 N 項會持續比對 `hooks.state` 鍵的群組索引與設定檔內 kunsu 條目實際索引，漂移即 WARN。

**解除**：自各 agent 的 hook 設定檔移除上述 `SessionStart` 條目即完全停用，無其他殘留（Codex 刪除任一位置在前的群組後，其餘條目須重新信任）。

---

## UserPromptSubmit hook（提問時信箱新件提示，選用）

`scripts/prompt_inbox_hook.py`：軍師 repo 內**每一句使用者提問**觸發一次確定性
掃描，把回覆／上報／申請三信箱頂層的未 commit 新件以**一行**注入 context——補
的是「派發之後、動手之前」這個時點的抵達訊號。2026-09-23 書城正式切換事故：
回覆方以 Write 直接落檔（未走 handoff skill、回覆即推播沒觸發），關鍵回覆在信箱
躺了 77 分鐘，軍師在「可以重啟了」那句提問時若已看到檔名，502 可免。SessionStart
hook 只在 session 啟動時跑、回覆即推播依賴回覆方走 skill，兩者都不落在這個時點。

- **輸出形狀**：`📨 kunsu 信箱新件：回覆 N 份、上報 N 份、申請 N 份｜本次點名：<檔名…>（另有 N 份未點名）｜查看完整清單請執行 kunsu-inbox skill；本提示僅告知，不構成任何動工授權`。
  零新件的信箱不列；三信箱皆零則零輸出。新件**首次出現列檔名**（每信箱最多
  5 筆，未點名者於後續提問輪替，每份新件恰被點名一次），之後只計數——「未
  commit」不等於「未讀」，回覆檔從投遞到歸檔都維持未 commit，每句列全名會成雜訊。
- **掃描形狀**：自跑一次 `git status --porcelain -z`（NUL 分隔，含空格或特殊字元的
  檔名不受引號包裹影響），新件＝三信箱頂層狀態碼恰為 `??`／`A `／`AM` 的 `.md`；
  archive/ 與其他狀態碼（含 `AD`、衝突態）一律忽略；git 失敗時零輸出且狀態不動。**不呼叫三支 `scan-*.sh`**（它們
  會寫統計檔並推進歷史夾帶基線）。tripwire 與歷史夾帶警示不在本 hook 輸出範圍，
  仍由本 skill 與 SessionStart hook 呈現。
- **快退**：斜線指令提問（`/` 開頭）靜默；非軍師 repo 只做 registry 路徑前綴比對，
  git root 以純檔案系統向上尋找 `.git` 標記判定——整支腳本只在確認為軍師 repo 後
  跑一次 `git status`（hook 為全域掛載，每個 repo 每句提問都會執行）；已登記路徑
  之下的巢狀獨立 git repo 會先命中內層 `.git` 而靜默；巢狀拓撲只走軍師分支。
- **狀態**：與 SessionStart hook 共用 `~/.claude/kunsu-hook-state.json`（機器層級，
  不進任何 repo），本 hook 只動頂層鍵 `prompt_inbox`；新件歸檔、刪除或直接
  commit 後自狀態中清除；狀態檔損壞視同首次（重列一次）。`KUNSU_HOOK_STATE_FILE`
  ／`KUNSU_REGISTRY_FILE` 可覆寫路徑供測試隔離。
- **fail-open**：任何錯誤（含部署不完整、共用函式庫載入失敗）零輸出、exit 0；唯一一次
  git 子程序 timeout 3 秒（小於掛載 timeout 5，腳本自身逾時恆先於 harness）。
- **已知限制**：同一軍師資料夾多 session（`kc --slot`）並行時，先提問的視窗看到檔名、
  其餘只看到計數（多 session 分頭作業以本 skill 查完整清單）；新件被直接 `git commit`
  而未歸檔時從掃描面消失——這是「未 commit 即未處理」訊號模型的共同限制，由
  `scan-replies.sh` 的歷史夾帶偵測兜底；Codex 以 `$` 形觸發 skill 時不受斜線靜默。

**掛載**（機器層級設定，不進任何 git repo；hook 設定檔位置見 Agent 對應表）。Claude Code——`hooks` 設定檔（位置見 Agent 對應表）的 `UserPromptSubmit` 陣列加一組（與同事件其他 hook 並存，各自一組）：

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$HOME/.claude/skills/kunsu-inbox/scripts/prompt_inbox_hook.py\"",
      "timeout": 5
    }
  ]
}
```

Codex——其 hook 設定檔的 `hooks.UserPromptSubmit` 陣列**尾端**加一組（純文字 stdout 加入 context，與 Claude Code 一致；stdin 是否同時帶 `cwd` 與 `prompt` 以本機版本實跑為準——缺 `prompt` 時斜線靜默不生效但無其他影響）：

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$HOME/.agents/skills/kunsu-inbox/scripts/prompt_inbox_hook.py\"",
      "timeout": 5
    }
  ]
}
```

掛載順序與信任步驟同 SessionStart 節；掛後自檢：在軍師 repo 以合成 stdin 餵腳本——`echo '{"cwd":"<軍師路徑>","prompt":"hi"}' | python3 <部署目錄>/kunsu-inbox/scripts/prompt_inbox_hook.py`——有未歸檔新件應得一行、`"prompt":"/x"` 應零輸出。

> **先部署後掛載**：腳本檔不存在時 `python3 <不存在的檔案>` exit 2 且 stderr 非空——
> Claude Code 對 UserPromptSubmit hook 的 exit 2 是**阻擋該句提問**（stderr 回顯給
> 使用者），與 PreToolUse 節的 fail-closed 同形；先跑 `install.sh` 再掛載即無此事。

**解除**：自各 agent 的 hook 設定檔移除上述 `UserPromptSubmit` 條目即完全停用；狀態檔 `prompt_inbox` 鍵殘留無害，可手動刪除。

---

## PreToolUse git add 守門（ADR 017，選用）

`scripts/pretooluse_git_guard.py`：軍師 repo 內攔截寬範圍 `git add` 的 PreToolUse
hook——kunsu 首個行為強制機制（ADR 017 accepted，2026-08-29）。攔截判準凍結為
三形狀（增列須 ADR 修訂）：`-A`／`--all`、`.`／`:/`、涵蓋信箱路徑
（`docs/handoffs`、`docs/applications`、`docs/reports`——含其祖先與子目錄）的
整目錄參數。deny 訊息內嵌正確做法（逐檔列名、歸檔改用 `archive-handoff.sh`）；
具體檔案路徑、非信箱目錄、非軍師 repo 一律放行。

- **身分判定**：raw registry＋git root 快速比對（含指令中 `git -C <path>` 的
  路徑），比照 SessionStart hook；registry 不可讀時放行。
- **逃生門**：指令前綴 `KUNSU_ADD_GUARD_OFF=1`（或程序環境同名變數）單次
  放行——打字成本即摩擦，指令史留痕可稽。
- **觀測**：deny 事件記入掃描統計檔（`GUARD_DENY` 事件＋`guard_denies` 計數，
  見「掃描統計」節），誤擋率與命中率有數據可查。
- **fail-open**：hook 自身任何錯誤一律放行，絕不阻斷正常工作。已知限制（威脅
  模型是無意誤用非惡意繞過）：指令切段為樸素字串分割、不模擬 `cd` 後的 shell
  狀態。

**掛載**（機器層級設定，不進任何 git repo；hook 設定檔位置見 Agent 對應表）。Claude Code——`hooks` 設定檔（位置見 Agent 對應表）的 `PreToolUse` 陣列加一組：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$HOME/.claude/skills/kunsu-inbox/scripts/pretooluse_git_guard.py\"",
      "timeout": 5
    }
  ]
}
```

Codex——其 hook 設定檔的 `hooks.PreToolUse` 陣列**尾端**加一組（payload 契約與 Claude Code 一致：`tool_name: "Bash"`、`tool_input.command`；放行時腳本 exit 0 無輸出，deny 以 JSON `permissionDecision`）：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$HOME/.agents/skills/kunsu-inbox/scripts/pretooluse_git_guard.py\"",
      "timeout": 5
    }
  ]
}
```

掛載順序與信任步驟同 SessionStart 節；掛後自檢：以合成 payload 餵腳本應得 deny JSON——`echo '{"tool_name":"Bash","tool_input":{"command":"git add -A"},"cwd":"<軍師路徑>"}' | python3 <部署目錄>/kunsu-inbox/scripts/pretooluse_git_guard.py`。

**解除**：自各 agent 的 hook 設定檔移除上述 `PreToolUse` 條目即完全停用。

> **掛載順序**：先 `install.sh` 部署、後掛載。順序顛倒時腳本檔不存在，hook 以
> 錯誤結束（`python3 <不存在的檔案>` exit 2 且 stderr 非空）——Claude Code 對
> PreToolUse hook 錯誤是 fail-closed，**所有 Bash 指令**都會被擋（2026-08-29 實測）；
> Codex 對 exit 2＋stderr 非空同樣視為 Blocked（原始碼查證，試點實測為準），兩
> agent 在此形狀一致。與腳本內部的 fail-open 是兩回事；此時以非 Bash 途徑補上
> 腳本檔即解。Codex 另有一形 Claude Code 沒有：條目**未信任或位置索引漂移**時
> hook 靜默略過、零訊號——守門與信箱摘要同時消失，統計檔零事件不可讀為健康。

---

## Codex config 設定（ADR 019，選用）

機器層級設定，寫於 `~/.codex/config.toml`，不進任何 git repo：

```toml
# ~/.codex/config.toml
# 必要：軍師 CLAUDE.md 常超過預設 32 KiB 專案文件預算（ebook 軍師 34,581 bytes），超限只在 log 留 warn、靜默截尾末段
project_doc_max_bytes = 65536

# 選用：軍師 repo 由 kunsu-init scaffold 內建 AGENTS.md → CLAUDE.md symlink，Codex 原生讀到憲章；
# 未建 symlink 的舊軍師才需要此 fallback（全域設定，會使 Codex 在所有 repo 於 AGENTS.md 缺席時也讀 CLAUDE.md）
# project_doc_fallback_filenames = ["CLAUDE.md"]

# 選用：sandbox 可寫根。基線不設——workspace-write 被擋時 Codex TUI 跳核准提示改在 sandbox 外重跑；
# 常設登記軍師路徑會成為機器路徑第三處登記（Invariant 2 張力，ADR 019 Decision 5 不開例外、由使用者自決），
# 且列入 <軍師>/.git 後每次 git 寫入的核准提示（Codex 側唯一附帶的結構性關卡）隨之消失；
# ~/.claude 不列則 Codex 模型 shell 路徑對統計檔的寫入靜默失敗、ADR 017／018 觀察期在 Codex 側缺漏
# [sandbox_workspace_write]
# writable_roots = ["/path/to/軍師", "/Users/<you>/.claude"]

# 選用：在 default mode 啟用阻塞式提問（0.142.5 under development、預設關）；開啟後 Agent 對應表「阻塞式確認」列的 Codex 欄自動改為可用即用
# [features]
# default_mode_request_user_input = true
```

預算為專案鏈合計（`AGENTS.override.md`→`AGENTS.md`→fallback 逐目錄取首個命中），全域 `~/.codex/AGENTS.md` 不計；`project_doc_max_bytes` 須高於現存最大軍師 CLAUDE.md 並留成長餘裕（consistency-check H 項對 live 軍師 CLAUDE.md 大小達上限 80% 即 WARN）。

---

## 依賴聲明

本 skill 依賴同 toolkit 內建的 `handoff` skill（v0.23.0，原始碼位於本 repo `skills/handoff/`）所定義的下列慣例。兩者共同發版、慣例定義以本 repo 為準；更新 handoff 的以下行為時需同步核查本 skill（v0.10.0 的沉澱訊號查核為 done 流程內部指引、v0.11.0 的派發即推播／回覆即推播為 add／reply 流程收尾通知、v0.12.0 的反向路由查核與 todo 殘項清點為 done 流程內部指引、v0.13.0 的矛盾回報指引為 reply 流程內部指引、v0.14.0 的更正交接與 `corrected_by` 為 add 流程內部慣例（corrected_by 為 display-only frontmatter 欄位；其 Edit 中間態頂層屬既有 catch-all tripwire、archive 內屬既有靜默略過分支，皆無新豁免）、v0.15.0 的斷言層級紀律與 done 斷言自查為 add／done 流程內部指引、v0.16.0 的產檔腳本 stderr 指路行不改變產出檔內容與 stdout 路徑契約、v0.17.0 的 session 命名慣例 slot 變體（`kc --slot`，推播精確比對納入 `<慣例名>.<後綴>`、多重命中仍降級）為 add／reply 推播匹配規則、v0.17.1 的產檔腳本專案根定位「往上找到家目錄即停」為腳本內部防呆（不改變產出檔內容與 stdout 路徑契約）、v0.18.0 的歸檔腳本 `archive-handoff.sh` 為 done 步驟 5–7 的腳本化執行（其 rename 產物即本 skill 掃描豁免的既有兩形狀，`git add` 僅限具體路徑與確認 commit 協議零改動，無新豁免需求）、v0.19.0 的確認 commit 宣告範圍契約（ADR 018——定型指令改帶兩形 pathspec、add 與 commit 路徑集合一致，不改變掃描豁免形狀與「未 commit 即未處理」訊號，無新豁免需求）、v0.20.0 的產檔查重（stderr advisory，不改產出檔內容、exit code 與 stdout 路徑契約）與 done 查核腳本附掛（archive-handoff.sh `--precheck` 印來源 todo 候選、歸檔執行掃 index 聚合 todo 三形進 commit 宣告、尾端印引用偵測——todo 歸檔路徑不在本 skill 掃描範圍，無新豁免需求）、v0.21.0 的回覆修改檔案清單條款（reply 流程內部指引；回覆方式定型文字多一行、new-handoff-reply.sh 多一行 stderr——**確實改變交接本體產出內容**，但 frontmatter、stdout 路徑契約、掃描慣例與豁免形狀不變，無新豁免需求）、v0.22.0 的 SKILL 字面 agent 中性化與 Agent 對應表（ADR 019——阻塞式確認改依 agent 身分判定、跨 session 推播工具不可用時整步跳過；回覆方式定型文字的 reply 呼叫形改為 Claude Code／Codex 兩形並列——**確實改變交接本體產出內容**，但 frontmatter、stdout 路徑契約、掃描慣例與豁免形狀不變，無新豁免需求）、v0.23.0 的交接依賴圖 `depends_on`（產檔腳本第 6 參數——**確實改變交接本體產出內容**（僅給參數時 frontmatter 多一個選填欄位），stdout 路徑契約、掃描慣例與豁免形狀不變，無新豁免需求；推導由沙盤 `app/handoff_graph.py` 單一模組提供，本 skill 4a／4b 經 `scripts/handoff-graph.py` 呼叫）——皆不涉掃描慣例；回覆即推播不改變「未 commit 即新回覆」訊號）：

| 項目 | 慣例 |
|------|------|
| 回覆檔命名 | `{原交接檔名}-reply-YYYY-MM-DD.md`；同日多份加 `-2`、`-3`… |
| `in_reply_to` 值 | 原交接檔名，**含 `.md` 後綴** |
| `status` 可能值 | `submitted`（預設）/ `partial` / `blocked` / `done` |
| `verify` 欄位 | 選填，驗收方式（ADR 011）。建議代碼 `needs-deploy`／`testable-now`／`needs-device`（全小寫 kebab-case，顯示端查找前正規化為小寫），開放值域（其他字串原樣顯示）、缺省不顯示（純空白字串視同缺省）；不跨回覆繼承（只讀最新回覆）；display-only，不參與任何比對邏輯與 tripwire |
| 信箱目錄 | `docs/handoffs/replies/`（一律在軍師 repo 內）|
| `in_reply_to` 比對方式 | 精確字串比對，含後綴 |
| done 歸檔搬移 | 頂層交接→`archive/`、其回覆→`archive/replies/` 成對搬移，即 `scan-replies.sh` 授權豁免的兩個 rename 形狀（可攜帶 `status: done` 修改，porcelain 呈現 `RM`）；v0.8.0 起 done 亦可能一併搬移來源 todo（`docs/todos/`→`docs/todos/archive/`，不在本 skill 掃描範圍，無豁免需求）|
| 流程尾端確認 commit | add／done／reply（本地語境）經阻塞式確認後 commit（ADR 009；Codex 以文字回合確認，ADR 019）；commit 帶與 add 同一組 pathspec（宣告範圍契約，ADR 018）；kunsu 語境 reply 不 commit——未 commit 即本 skill 的新回覆偵測訊號 |

另依賴同 toolkit 內建的 `kunsu-apply` skill 所定義的申請信箱目錄慣例
（`docs/applications/` 頂層投遞、`archive/` 歸檔——本 skill 的掃描只看 git 狀態
與路徑前綴，不解析申請 frontmatter；欄位規格見 kunsu-apply 依賴聲明與軍師範本）；
掃描端 `scan-applications.sh` 與審核端 add-project 共享同一套 tripwire 分類規則。
