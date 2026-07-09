---
name: kunsu-report
version: 0.1.0
description: |
  在子專案 session 向已登記的軍師（規劃協調中心）投遞「主動上報」：自動偵測子專案
  路徑，從全域反向註冊表 ~/.claude/kunsu-registry.json 取得本 repo 自身條目（限
  已登記 repo），選定目標軍師與角色代碼後，將情報上報至軍師 docs/reports/ 信箱。
  上報是情報傳遞，不是反向委派——不承諾軍師回覆或執行任何動作。投遞前內建反向
  重導：若目標軍師有待回覆（to: 本角色代碼且 status 非 done）的交接文件，先反
  問是否其實是回覆，確認是回覆時導向 /handoff reply 停止投遞。
  Use when asked to「上報軍師」「向軍師上報」「主動上報」「主動回報」「稟報軍師」
  「跟軍師報告」「知會軍師」「反映給軍師」.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---

# kunsu-report — 向軍師投遞主動上報

在已登記的子專案 session 一鍵投遞主動上報：能自動偵測就不問、能點選就不打字。
上報是情報，不是委派任務——軍師讀取後自行決定後續行動，不設回覆義務。

---

## ⚠️ 授權邊界（必讀）

**以下限制不得例外：**

1. **只在 `docs/reports/` 頂層新增新檔案** — 本次執行對軍師 repo 的寫入僅限「在 `docs/reports/` 頂層新增一個上報檔」，此為軍師上報信箱協議的例外授權範圍。不寫入 `archive/`、不覆寫任何既有上報（同日同名自動加 `-2`、`-3`）。
2. **不編輯任何既有檔案** — 不修改軍師的 CLAUDE.md、任何 handoff 檔案或任何其他既有內容。
3. **上報是情報，不是反向委派** — 本 skill 不承諾軍師回覆或執行任何動作；若子專案意圖「要軍師做某事」，由軍師讀取上報後自行開 plan 或發起 handoff 追蹤。
4. **僅服務已登記 repo** — 本 skill 不寫入全域註冊表，`~/.claude/kunsu-registry.json` 中查無當前 repo 條目時直接停止，導引使用 `/kunsu-apply` 申請加入。
5. **對子專案自身 repo 零寫入** — 自動偵測（路徑）僅以唯讀工具進行。

---

## 執行步驟

### 步驟 1：偵測子專案根目錄

```bash
git rev-parse --show-toplevel
```

結果記為 `SUB_ROOT`（絕對路徑）；非 git repo 則報錯停止，不繼續後續步驟。

### 步驟 2：讀取 registry，取本 repo 自身條目

以 `Read ~/.claude/kunsu-registry.json` 讀取全域反向註冊表，在 JSON 物件中以 `SUB_ROOT` 為鍵取值（格式為陣列，每項含 `kunsu` 路徑與 `roles` 陣列）。

- **降級路徑（三種情境同一處理）**：registry 不存在、JSON 格式損壞、或 `SUB_ROOT` 鍵不存在 → 視同無條目，進入步驟 3 硬停。
- **注意**：本步驟只取本 repo 自身條目（`registry[SUB_ROOT]`），**不取全域軍師聯集**——與 `/kunsu-apply` 步驟 2 的「取所有條目 kunsu 欄位聯集」不同，兩者為刻意差異（apply 服務未登記 repo，report 只服務已登記 repo）。

### 步驟 3：未登記硬停

若步驟 2 查無 `SUB_ROOT` 的條目，停止並回報：

> 此 repo（`<SUB_ROOT>`）尚未登記於任何軍師（`~/.claude/kunsu-registry.json` 中查無對應條目）。
> 請先以 `/kunsu-apply` 申請加入目標軍師，核准登記後再使用 `/kunsu-report` 上報。

不寫入任何檔案，不繼續後續步驟。

### 步驟 4：選定目標軍師

取 `registry[SUB_ROOT]` 陣列，列出所有 `kunsu` 值。

- **單一條目**：自動選定該軍師路徑（記為 `KUNSU_ROOT`），不詢問。
- **多個條目**：以 `AskUserQuestion` 列出所有軍師路徑（附上各自的 `roles` 欄位供辨識），請使用者選定，結果記為 `KUNSU_ROOT`。

### 步驟 5：角色代碼消歧

取選定條目的 `roles` 陣列。

- **唯一角色**：自動填入 `ROLE_CODE`，不詢問。
- **多筆角色**：以 `AskUserQuestion` 列出所有角色代碼，請使用者選定，結果記為 `ROLE_CODE`。

### 步驟 6：上報信箱守門

```bash
test -d "<KUNSU_ROOT>/docs/reports" && echo "ok" || echo "missing"
```

- **missing** → 報錯終止，不寫入任何檔案：
  > 目標軍師 `<KUNSU_ROOT>` 尚無上報信箱（`docs/reports/` 不存在）。請先在軍師目錄的 session 執行 `/kunsu-init add-project`，依提示完成遷移（補建上報信箱與協議文字），再重新投遞。
- **ok** → 繼續步驟 7。

### 步驟 7：反向重導——確認是否其實是回覆

以 `Glob "<KUNSU_ROOT>/docs/handoffs/*.md"` 取頂層交接文件（此 glob 模式不進入子目錄，天然排除 `replies/`、`archive/` 下的檔案）。

對每個命中檔案以 `Read` 讀取 frontmatter，篩選條件：
- `to:` 欄位值等於 `ROLE_CODE`（精確字串比對）
- `status:` 欄位值**不是** `done`（包含 `open`、`in-progress` 等非完成狀態）

跳過 `README.md`（若存在）。

**若有命中**：

1. 以 `AskUserQuestion` 列出所有命中的交接文件（標題、檔名），反問：
   > 目前目標軍師有以下交接文件的 `to:` 指向本角色（`<ROLE_CODE>`），且尚未完成：
   > 1. 《交接標題》（`<檔名>`）
   > 2. …
   >
   > 請問這次是否其實是在回覆其中某份交接（而不是新的主動上報）？

2. **使用者確認「是回覆」**：詢問要回覆哪份交接（若命中多份），然後提示：
   > 請執行 `/handoff reply <交接檔名>` 以建立正式回覆。本次 `/kunsu-report` 停止，不產生上報檔。

   立即結束，不繼續步驟 8。

3. **使用者確認「不是回覆，是新情報上報」**：繼續步驟 8。

**若無命中**：直接繼續步驟 8。

### 步驟 8：收集上報標題與 tags

以 `AskUserQuestion` 收集：

1. **上報標題**（必填）：簡短說明本次上報的主題。
2. **附加標籤（tags）**（選填）：以逗號分隔的主題標籤（Obsidian 分類用），不含 `report`（腳本自動加入）；留空即只有 `[report]`。

### 步驟 9：收集並整理上報內文

請使用者提供上報正文（可直接貼上已整理的內容，或口述後由 model 協助整理為結構化段落），將最終內文記為 `BODY`。

### 步驟 10：產生上報檔

呼叫產檔腳本（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑）：

```bash
printf '%s' "$BODY" | bash "$CLAUDE_SKILL_DIR/scripts/new-report.sh" \
  "<KUNSU_ROOT>" \
  "<上報標題>" \
  "<ROLE_CODE>" \
  "<附加標籤或空字串>"
```

腳本 stdout 最後一行為上報檔完整路徑。非零退出時停下報告錯誤（含步驟 6 之後信箱被移除的競態情境）。

### 步驟 11：完成回報

以正體中文回報：

```
✅ 上報已投遞

上報檔：<完整路徑>
目標軍師：<KUNSU_ROOT>
上報角色：<ROLE_CODE>

本次寫入僅此一個新檔案（上報信箱協議授權範圍內），未觸碰軍師其他任何檔案，
未寫入全域註冊表。

上報是情報傳遞，不承諾軍師回覆或執行。軍師讀取後，若需後續行動，將自行開 plan
或發起新交接。
```

不主動 commit 任何變更。

---

## 依賴聲明

| 項目 | 慣例 |
|------|------|
| 上報檔命名 | `{YYYY-MM-DD}-{標題 slug}-report.md`；同日同名加 `-2`、`-3`… |
| frontmatter 欄位順序 | `title`、`type: report`、`from`（角色代碼）、`created`、`status: submitted`、`tags` |
| `from:` 欄位 | 角色代碼，自 registry 自動填入，與 `~/.claude/kunsu-registry.json` 的 `roles` 字面一致 |
| `tags` 預設值 | `[report]`；有附加主題標籤時 `[report, 標籤…]`；掃描腳本不解析此欄 |
| 信箱目錄 | `docs/reports/`（一律在軍師 repo 內，頂層投遞、`archive/` 歸檔） |
| 軟依賴 | `~/.claude/kunsu-registry.json`（缺失時硬停於步驟 3）；目標軍師已遷移的 `docs/reports/`（缺失時硬停於步驟 6） |
| 掃描端 | 軍師 session 的 `/kunsu-inbox`（軍師模式）；`scan-reports.sh` 回報新上報份數 |
| 歸檔 | 由軍師 session 手動執行三步驟：Edit `status` → `git add` → `git mv` 至 `archive/`（untracked 檔案須先 `git add` 才能 `git mv`，順序不可顛倒） |
