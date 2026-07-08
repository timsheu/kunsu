---
name: kunsu-apply
version: 0.1.0
description: |
  在子專案 session 向軍師（規劃協調中心）投遞「申請加入」：自動偵測子專案路徑、
  顯示名稱與技術棧，從全域反向註冊表 ~/.claude/kunsu-registry.json 撈出軍師清單
  供點選，使用者只需填角色描述與環境限制，寫成申請檔投遞至目標軍師的
  docs/applications/ 申請信箱。審核與正式登記由軍師端的 add-project 執行。
  Use when asked to「申請加入軍師」「投遞申請」「加入軍師」「向軍師申請」
  「把這個專案申請加入軍師」「kunsu apply」「apply to kunsu」.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---

# kunsu-apply — 向軍師投遞申請加入

在子專案 session 一鍵投遞「申請加入軍師」：能自動偵測就不問、能點選就不打字，
使用者只需手填角色描述與環境限制。

---

## ⚠️ 授權邊界（必讀）

**以下限制不得例外：**

1. **只投遞不登記** — 本 skill 絕不寫入全域註冊表、絕不修改軍師的 CLAUDE.md 或任何既有檔案。正式登記只在軍師端 `add-project` 核准當下發生（單點登記）。
2. **寫入僅限一個新檔案** — 本次執行對軍師 repo 的寫入僅限「在 `docs/applications/` 頂層新增一個申請檔」，此為軍師申請信箱協議的例外授權範圍。不寫入 `archive/`、不覆寫任何既有申請（含本子專案先前投遞的版本）。
3. **對子專案自身 repo 零寫入** — 自動偵測（路徑、名稱、技術棧）僅以唯讀工具進行。

> 軍師本身也可以作為子專案執行本 skill 向另一個軍師申請加入（巢狀拓撲），流程無任何特殊分支。

---

## 執行步驟

### 步驟 1：自動偵測子專案資訊

```bash
git rev-parse --show-toplevel
```

- 結果記為 `SUB_ROOT`（絕對路徑）；非 git repo 則報錯停止。
- **顯示名稱預設值** = `SUB_ROOT` 的目錄名（basename）。
- **技術棧摘要**：以 `Read` 讀取 `SUB_ROOT/CLAUDE.md`，從「技術棧」或「技術選型」小節摘出關鍵詞（語言、框架）；無 CLAUDE.md 或無該小節 → 記為「待補充」，流程不中斷。

### 步驟 2：選擇目標軍師

嘗試以 `Read ~/.claude/kunsu-registry.json` 讀取註冊表，掃描所有條目的 `kunsu` 欄位取聯集（去重）得到軍師清單。

- **正常（清單非空）**：以 `AskUserQuestion` 列出軍師路徑供點選（軍師數量超過選項上限時，依 registry 出現順序列前幾個，其餘由使用者以 Other 輸入路徑）。
- **降級路徑（三種情境同一處理）**：registry 不存在、JSON 格式損壞、或清單為空 → 以 `AskUserQuestion` 直接詢問目標軍師的絕對路徑。本 skill 不因 registry 缺失而終止——申請者本來就可能是尚未登記的 repo。使用者也可在正常路徑選 Other 手動輸入不在清單中的軍師路徑。

> 注意：`SUB_ROOT` **不需要**已存在於 registry——首次加入的子專案正是尚未登記的狀態。

### 步驟 3：申請信箱守門

```bash
test -d "<KUNSU_ROOT>/docs/applications" && echo "ok" || echo "missing"
```

- **missing** → 報錯終止，不寫入任何檔案：
  > 目標軍師 `<KUNSU_ROOT>` 尚無申請信箱（`docs/applications/` 不存在）。請先於該軍師目錄的 session 執行 `add-project`，依提示完成遷移（補建申請信箱與協議文字），再重新投遞。
- **ok** → 繼續步驟 4。

### 步驟 4：重複投遞預檢

以 `Glob "<KUNSU_ROOT>/docs/applications/*.md"` 取頂層申請檔（不含 `archive/`），先以 `Grep` 篩 `path: <SUB_ROOT>` 縮小範圍，再 `Read` 命中者確認 `status: pending`（積壓多份時避免逐檔全讀）。

- **無待審申請** → 繼續步驟 5。
- **已有待審申請** → 以 `AskUserQuestion` 告知並詢問：
  - **另投新版**：繼續步驟 5，產生新申請檔（絕不覆寫舊檔——子端無權修改既有檔案；軍師端 `add-project` 審核時會依「同路徑取最新」自動將舊版歸檔）。
  - **取消**：終止，不寫入任何檔案。

### 步驟 5：訪談（僅剩人工欄位）

以單次 `AskUserQuestion` 收集：

1. **顯示名稱**：預設值為步驟 1 的目錄名，可修改。
2. **角色描述**：一行說明協作職責；此字串為**提議值**，軍師核准時可修改後定案（角色字串定案權在軍師）。
3. **環境限制（選填）**：特殊限制或已知約束；留空即「無」。
4. **能否自我驗證**：`y` = 可在該 repo 執行測試驗收；`n` = 需人工或跨 repo。

### 步驟 6：產生申請檔

呼叫產檔腳本（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑）：

```bash
bash "$CLAUDE_SKILL_DIR/scripts/new-application.sh" \
  "<KUNSU_ROOT>" \
  "<顯示名稱>" \
  "<SUB_ROOT>" \
  "<角色描述>" \
  "<環境限制或「無」>" \
  "<y/n>" \
  "<技術棧摘要或「待補充」>"
```

腳本 stdout 最後一行為申請檔完整路徑。非零退出時停下報告錯誤（含步驟 3 之後信箱被移除的競態情境）。

### 步驟 7：完成回報

以正體中文回報：

```
✅ 申請已投遞

申請檔：<完整路徑>
目標軍師：<KUNSU_ROOT>
提議角色：<角色描述>

本次寫入僅此一個新檔案（申請信箱協議授權範圍內），未觸碰軍師其他任何檔案，
未寫入全域註冊表。

下一步：到軍師目錄的 session 執行 add-project 審核此申請；
核准當下才會寫入軍師 CLAUDE.md 關聯專案表與 ~/.claude/kunsu-registry.json。
```

若技術棧為「待補充」，一併提醒可於子專案補齊 CLAUDE.md 技術棧小節後再投遞，或由軍師核准後自行補註。

---

## 依賴聲明

| 項目 | 慣例 |
|------|------|
| 申請檔命名 | `{YYYY-MM-DD}-{顯示名稱 slug}-application.md`；同日同名加 `-2`、`-3`… |
| frontmatter | `type: kunsu-application`、`name`、`path`、`proposed_role`、`constraints`、`self_verify`、`stack`、`created`、`status: pending` |
| `path` 欄位 | 子專案絕對路徑；軍師端以此作為分組與重複登記判斷的鍵 |
| 信箱目錄 | `docs/applications/`（一律在軍師 repo 內，頂層投遞、`archive/` 歸檔） |
| 審核端 | 軍師 session 的 `add-project`（`/kunsu-init` 子指令）；掃描端另有 `/kunsu-inbox` 軍師模式回報新申請 |
