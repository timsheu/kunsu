---
name: kunsu-inbox
version: 0.1.0
description: |
  查詢跨 repo 協作信箱：列出軍師（規劃協調中心）中待接手的交接文件，或回報新抵達的回覆。
  觸發語：/kunsu-inbox、檢查信箱、有沒有待接手的交接、有沒有新的 handoff、
  查看 handoff 清單、檢查新回覆、inbox、收件匣、有沒有待處理的交接、
  查看交接狀態、kunsu inbox、kunsu-inbox。
  依當前 repo 在 ~/.claude/kunsu-registry.json 中的身分自動選擇模式：
  - 子 repo 模式：列出所屬軍師中 to: 為本角色的待接手與已回覆待確認交接文件
  - 軍師模式：回報 docs/handoffs/replies/ 新回覆與 docs/applications/ 新申請的
    未 commit 份數，並執行 tripwire 核對
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

## ⚠️ 授權邊界（必讀）

**以下三條限制不得例外：**

1. **只告知不開工** — `/kunsu-inbox` 只回報信箱狀態，不自動接手任何交接文件、不自動執行任何後續動作。一切動工須使用者明確指示。
2. **不主動輪詢** — 本 skill 僅在使用者觸發時執行一次，不設定任何定時執行或背景監聽。
3. **兩個信箱是唯讀邊界的唯一例外** — 軍師的 `docs/handoffs/replies/`（接手方建立新回覆檔案）與 `docs/applications/` 頂層（子專案以 `/kunsu-apply` 建立新申請檔案）是僅有的兩個授權寫入點。軍師其他任何目錄均屬唯讀。

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
  > 找不到 `~/.claude/kunsu-registry.json`。請先以 `/kunsu-init` 建立軍師並完成登記。

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
      "roles": ["<角色名稱>", "..."]
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
| 否 | 否 | 報錯並停止：`CURRENT_ROOT` 不在任何已知登記中。請以 `/kunsu-init` 建立軍師，或以 `/kunsu-init add-project` 子指令將此 repo 登記至現有軍師。|

**重要：不以目錄存在與否作為判斷依據。** 任何跑過 `/handoff reply` 的一般 repo 都有 `docs/handoffs/replies/`，以目錄判斷會造成誤判。

---

### 步驟 4a：子 repo 模式

對 `SUBREPO_ENTRIES` 中的每個條目，**依軍師分組**執行以下掃描。

**4a-1. 收集此軍師的全部已知角色：**

掃描整個 registry，找出所有 `entry.kunsu == kunsu_path` 的條目，將其 `roles` 陣列取聯集，得到 `ALL_KNOWN_ROLES`。這用於後續的「to: 不符清單」核對。

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
1. `Read` 每個回覆的 frontmatter，取 `in_reply_to` 與 `status`
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
   | 無符合的回覆（零筆） | **待接手** |
   | 最新回覆 `status: partial` | **待接手** |
   | 最新回覆 `status: blocked` | **待接手** |
   | 最新回覆 `status: submitted` | **已回覆待確認** |
   | 最新回覆 `status: done` | **略過，不列出** |

**4a-4. 「to: 不符清單」核對：**

若有任何 handoff 的 `to:` 值不在 `ALL_KNOWN_ROLES` 中，收集這些項目。

**4a-5. 輸出格式（每個軍師一組）：**

```
## 軍師：{kunsu_abs_path}

### ☐ 待接手（{N} 份）

| 交接文件 | 建立日期 | 方向 | 回覆狀態 |
|---|---|---|---|
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | 無回覆 |
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | 最新回覆 partial（{reply_date}）|

### ✓ 已回覆待確認（{N} 份）

| 交接文件 | 建立日期 | 方向 | 最新回覆日期 |
|---|---|---|---|
| {title} ({HANDOFF_FILENAME}) | {created} | {from} → {to} | {reply_date} |

---
### 回覆方式（Method 2 — 無需切換工作目錄）

在以下路徑直接建立回覆檔案，不依賴當前工作目錄：

  {kunsu_abs_path}/docs/handoffs/replies/{原交接檔名}-reply-YYYY-MM-DD.md

frontmatter 範本：
---
title: {交接標題} — 回覆
type: handoff-reply
from: {我的角色}
to: {交接文件的 from 值}
in_reply_to: {原交接檔名（含 .md 後綴）}
created: YYYY-MM-DD
status: submitted
---
```

**若有「to: 不符清單」時，附加：**

```
⚠️ to: 不符清單（{N} 份）
以下交接文件的 to: 值不屬於此軍師已登記的任何角色，可能是拼寫錯誤或尚未以 add-project 登記：
- {HANDOFF_FILENAME}: to: {unknown_value}
請核查拼寫，或以 add-project 在此軍師補登記對應角色。
```

**若「待接手」與「已回覆待確認」皆為空（本角色無任何待處理交接）：**

```
## 軍師：{kunsu_abs_path}

本 repo 角色（{roles}）目前無待接手或待確認的交接文件。
```

---

### 步驟 4b：軍師模式

**4b-1. 呼叫掃描腳本（兩支）：**

```bash
bash ~/.claude/skills/kunsu-inbox/scripts/scan-replies.sh "{CURRENT_ROOT}"
bash ~/.claude/skills/kunsu-inbox/scripts/scan-applications.sh "{CURRENT_ROOT}"
```

各自記錄 stdout 輸出與 exit code。`scan-applications.sh` 對無 `docs/applications/` 的舊版軍師輸出零筆、exit 0（向後相容，不報錯）。任一腳本以非 0 且非 2 的 exit code 結束（如 1：參數錯誤或非 git 根）→ 停下回報該腳本的 stderr，不繼續彙整。

**4b-2. 解析腳本輸出：**

- 每行 `NEW_REPLY:<路徑>` → 新回覆路徑清單（路徑為相對於軍師根的路徑）
- 每行 `NEW_APPLICATION:<路徑>` → 新申請路徑清單
- 每行 `TRIPWIRE:<XY> <路徑>` → 意外變更清單

**4b-3. tripwire 判斷（任一腳本 exit code 2）：**

若任一腳本 exit code 為 2（有 tripwire 行）：
- **立即停止**，不繼續彙整
- 回報（依觸發來源列出對應範圍）：

```
⚠️ 疑似意外寫入偵測到，已停止彙整

信箱授權範圍外有未 commit 的變更：
{每行列出：  {XY} {路徑}}

請確認這些變更是否預期。若為正常操作（如手動建立新交接、/handoff done 的歸檔搬移
尚未 commit），確認並 commit 後再執行 /kunsu-inbox。（申請信箱的授權歸檔搬移已被
掃描規則豁免，正常情況不會出現在此清單。）
```

**4b-4. 正常輸出（兩支腳本皆 exit code 0）：**

```
## 軍師信箱

收到 {N} 份新回覆（未 commit，等待彙整）：
{每行列出：  - {路徑}}

收到 {M} 份新申請（未 commit，等待審核）：
{每行列出：  - {路徑}}
→ 以 /kunsu-init add-project 逐筆審核（核准當下才正式登記）。

（各段為零時改列：目前沒有未 commit 的新回覆。／目前沒有待審申請。）
```

> **「未 commit 即未處理」** 的前提：軍師的慣例是彙整回覆後才 commit，因此 uncommitted 回覆視為尚未處理的標記。若提前 commit，已彙整者在此不再顯示。

---

### 步驟 5：合併輸出（巢狀拓撲時）

若步驟 3 同時滿足判斷 ① 和 ②，依序輸出：
1. 步驟 4a 的子 repo 模式結果（各軍師分組）
2. 步驟 4b 的軍師模式結果

兩段之間加分隔線。

---

## 依賴聲明

本 skill 依賴同 toolkit 內建的 `/handoff` skill（v0.2.1，原始碼位於本 repo `skills/handoff/`）所定義的下列慣例。兩者共同發版、慣例定義以本 repo 為準；更新 handoff 的以下行為時需同步核查本 skill：

| 項目 | 慣例 |
|------|------|
| 回覆檔命名 | `{原交接檔名}-reply-YYYY-MM-DD.md`；同日多份加 `-2`、`-3`… |
| `in_reply_to` 值 | 原交接檔名，**含 `.md` 後綴** |
| `status` 可能值 | `submitted`（預設）/ `partial` / `blocked` / `done` |
| 信箱目錄 | `docs/handoffs/replies/`（一律在軍師 repo 內）|
| `in_reply_to` 比對方式 | 精確字串比對，含後綴 |

另依賴同 toolkit 內建的 `/kunsu-apply` skill 所定義的申請信箱目錄慣例
（`docs/applications/` 頂層投遞、`archive/` 歸檔——本 skill 的掃描只看 git 狀態
與路徑前綴，不解析申請 frontmatter；欄位規格見 kunsu-apply 依賴聲明與軍師範本）；
掃描端 `scan-applications.sh` 與審核端 add-project 共享同一套 tripwire 分類規則。
