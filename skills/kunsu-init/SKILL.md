---
name: kunsu-init
version: 0.3.0
description: |
  為多 repo AI 協作場景 scaffold 一個「軍師」（規劃協調中心）：以訪談收集子專案清單，
  自動查證路徑並讀取技術棧，填入固定不變量（5 條 Invariants、回覆信箱協議與
  申請信箱協議全文、工作流程六步驟）與參數化內容，建立 Obsidian vault、git 初始化，
  並將各子專案登記至全域反向註冊表 ~/.claude/kunsu-registry.json。
  Use when asked to「建立軍師」「幫我建一個軍師」「立軍師」「新增軍師」
  「建立規劃中心」「init planner」「scaffold 規劃協調中心」
  「初始化規劃協調中心」「建立 planner 中心」「建立一個規劃協調中心」
  「幫我建一個規劃中心」「create planning center」「setup planner center」
  「新增規劃中心」「init planning center」.
  Use add-project sub-command when asked to「add-project」「加入子專案」
  「新增子專案到軍師」「把子專案加入軍師」「新增子專案到規劃中心」
  「新增子專案」「add project to planner」「把子專案加入規劃中心」.
  Use remove-project sub-command when asked to「remove-project」「移除子專案」
  「刪除子專案登記」「移除子專案登記」「把子專案從軍師移除」「remove project from planner」.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
---

# kunsu-init — 軍師（規劃協調中心）scaffolding

在一個全新目錄下建立多 repo AI 協作的「軍師」（規劃協調中心）：包含固定 5 條 Invariants、
回覆信箱協議、工作流程六步驟、CONCEPTS.md、solutions 種子文件、Obsidian vault，
並以 registry-merge.sh 登記各子專案至全域反向註冊表。

**本 skill 對子專案目錄完全唯讀（只使用 Read／Grep／Glob），絕不在任何子專案目錄下
新增、編輯或刪除任何檔案，包含 .md 文件在內。**

## 全部用正體中文輸出，對話套用簡潔模式。

---

## 步驟 ①：訪談

### ①-A 基本資訊

以單次 `AskUserQuestion` 取得以下三項：

1. **軍師名稱**（`{{PLANNER_NAME}}`）：建議 kebab-case，通常作為目標目錄的最後一段路徑名稱。例：`my-product-planner`。
2. **目標目錄絕對路徑**（`{{PLANNER_ROOT_PATH}}`）：軍師將建立於此路徑，必須是絕對路徑。例：`/Users/dev/projects/my-product-planner`。
3. **Tagline**（`{{PLANNER_TAGLINE}}`）：一行描述軍師定位，例：「跨前端、後台與行動 App 的功能規劃與協調中心」。

### ①-B 子專案清單

以單次 `AskUserQuestion` 收集所有子專案。要求使用者以如下格式逐行提供（每個子專案一行）：

```
顯示名稱 | 絕對路徑 | 角色代碼 | 角色說明 | 環境限制（可留空）| 能否自我驗證（y/n）
```

- **顯示名稱**：出現在關聯專案表的名稱，可含空格。
- **絕對路徑**：`{{PROJECT_ROWS}}` 的來源，SKILL 將以 `ls` 查證存在。
- **角色代碼**：短、kebab-case，即交接文件 `to:` 的唯一比對鍵（`{{PROJECT_ROWS}}` 第三欄）；宜 ≤ 20 字、不含軍師名前綴。**同一軍師內須唯一**——見下方唯一性檢查。
- **角色說明（選填）**：一行職責描述，display-only，只落關聯專案表說明欄、不進註冊表、不比對（`{{PROJECT_ROWS}}` 第四欄）；留空為「無」。
- **環境限制（選填）**：特殊限制或已知約束；填「無」即不產生限制小節（`{{PROJECT_CONSTRAINTS}}`）。
- **能否自我驗證**：`y` = 可在該 repo 執行測試驗收；`n` = 需人工或跨 repo。

**角色代碼唯一性檢查**：收集完成後，以本批子專案的角色代碼建累積集逐筆比對；若有兩個子專案填入相同代碼，以 `AskUserQuestion` 列出撞名者、要求改其一（同碼會使 `/kunsu-inbox` 對兩子專案雙向誤命中）。全部唯一後才續行。

儲存所有子專案資訊（含角色代碼與角色說明），供後續步驟使用。

---

## 步驟 ②：前置保護

**在目標路徑執行任何寫入前**，先以 `Bash` 檢查是否已有 CLAUDE.md：

```bash
test -f "<PLANNER_ROOT_PATH>/CLAUDE.md" && echo "exists" || echo "not_found"
```

- **已存在 → 停住**：以 `AskUserQuestion` 告知使用者「目標路徑 `<PLANNER_ROOT_PATH>` 已有 CLAUDE.md，繼續將覆寫既有軍師。確認繼續？（y/n）」若使用者回 n，終止並說明何者已存在、可手動備份。
- **不存在 → 繼續**：以 `Bash` 建立目標目錄：`mkdir -p "<PLANNER_ROOT_PATH>"`。

---

## 步驟 ③：查證子專案路徑與技術棧摘要

### ③-1 路徑查證

對每個子專案執行：

```bash
test -d "<sub-repo-abs-path>" && echo "ok" || echo "missing"
```

**彙整**所有查證失敗的子專案（不單筆中斷）。若有任何路徑不存在，以**單次** `AskUserQuestion` 列出所有錯誤，詢問：「以下子專案路徑不存在，請提供修正後的絕對路徑，或輸入 skip 略過該子專案：」。等待回覆後更新子專案清單，再繼續步驟 ③-2。

### ③-2 技術棧摘要（唯讀）

對每個通過路徑查證的子專案，嘗試以 `Read` 讀取 `<sub-repo-abs-path>/CLAUDE.md`：

- **有 CLAUDE.md** → 從「技術棧」或「技術選型」小節摘出關鍵詞（語言、框架）。
- **無 CLAUDE.md** → 記錄該子專案技術棧為「待補充」，**流程不中斷**，於步驟 ⑧ 回報。

---

## 步驟 ④：產生軍師檔案

> **範本固定段落（5 條 Invariants、回覆信箱協議與申請信箱協議全文、工作流程六步驟）逐字保留，絕不改寫；只替換 `{{...}}` 佔位符。**

### ④-1 產生 CLAUDE.md

1. 以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/kunsu-claude.md`（若 `$CLAUDE_SKILL_DIR` 未定義，改用此 SKILL.md 所在目錄的絕對路徑）。
2. 替換以下佔位符（見 `assets/templates/PLACEHOLDERS.md` 詳解）：
   - `{{PLANNER_NAME}}` → 步驟 ①-A 的軍師名稱
   - `{{PLANNER_TAGLINE}}` → 步驟 ①-A 的 tagline
   - `{{PLANNER_ROOT_PATH}}` → 步驟 ①-A 的目標絕對路徑
   - `{{PROJECT_ROWS}}` → 每個通過查證的子專案一行，格式：`| 顯示名稱 | 絕對路徑 | 角色代碼 | 角色說明 |`（角色說明留空時該欄留空字串，欄位結構仍在）
   - `{{PROJECT_CONSTRAINTS}}` → 針對環境限制非「無」的子專案，各產一個 `### {顯示名稱} 環境限制\n\n<限制說明>` 小節；全部為「無」時，以空字串取代整個佔位符（含前後空行）
   - `{{PLANNER_STRUCTURE}}` → **暫填空字串，步驟 ④-6 更新**
3. 以 `Write` 寫至 `<PLANNER_ROOT_PATH>/CLAUDE.md`。

### ④-2 複製 CONCEPTS.md（無佔位符，逐字複製）

以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/kunsu-concepts.md`，以 `Write` 逐字寫至 `<PLANNER_ROOT_PATH>/CONCEPTS.md`，不做任何修改。

### ④-3 產生 docs/README.md

以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/kunsu-docs-readme.md`，替換 `{{PLANNER_NAME}}` 後以 `Write` 寫至 `<PLANNER_ROOT_PATH>/docs/README.md`。

### ④-4 建立目錄結構與 .gitkeep

```bash
mkdir -p "<PLANNER_ROOT_PATH>/docs/handoffs/replies"
touch "<PLANNER_ROOT_PATH>/docs/handoffs/replies/.gitkeep"
mkdir -p "<PLANNER_ROOT_PATH>/docs/applications/archive"
touch "<PLANNER_ROOT_PATH>/docs/applications/.gitkeep"
touch "<PLANNER_ROOT_PATH>/docs/applications/archive/.gitkeep"
mkdir -p "<PLANNER_ROOT_PATH>/docs/reports/archive"
touch "<PLANNER_ROOT_PATH>/docs/reports/.gitkeep"
touch "<PLANNER_ROOT_PATH>/docs/reports/archive/.gitkeep"
mkdir -p "<PLANNER_ROOT_PATH>/docs/solutions/architecture-patterns"
mkdir -p "<PLANNER_ROOT_PATH>/docs/solutions/conventions"
```

> `docs/applications/` 是申請信箱（`/kunsu-apply` 投遞、`add-project` 審核），與 `docs/handoffs/replies/` 同屬例外授權信箱。`.gitkeep` 佔位確保 clone 後目錄存在，否則掃描腳本在首份申請抵達前無從核對。`docs/reports/` 是上報信箱（子專案以 `/kunsu-report` 主動上報、軍師審閱歸檔）。`.gitkeep` 佔位確保 clone 後目錄存在，否則掃描腳本在首份上報抵達前無從核對。

### ④-5 複製 solutions 種子文件

以 `Read` 讀取以下兩份種子文件，以 `Write` 原樣寫至目標路徑：

- `$CLAUDE_SKILL_DIR/assets/solutions/architecture-patterns/cross-repo-coordination-planner-pattern.md`
  → `<PLANNER_ROOT_PATH>/docs/solutions/architecture-patterns/cross-repo-coordination-planner-pattern.md`
- `$CLAUDE_SKILL_DIR/assets/solutions/conventions/cross-repo-handoff-reply-inbox-convention.md`
  → `<PLANNER_ROOT_PATH>/docs/solutions/conventions/cross-repo-handoff-reply-inbox-convention.md`

### ④-6 生成 `{{PLANNER_STRUCTURE}}` 並更新 CLAUDE.md

執行：

```bash
find "<PLANNER_ROOT_PATH>" -not -path "*/.git/*" -not -path "*/.obsidian/*" \
  -maxdepth 4 | sort
```

依實際目錄結構產生三層 ASCII tree（格式：路徑末段名稱加 `→ 說明`），至少包含：

```
CLAUDE.md              → 主入口（規範、關聯專案、工作流程）
CONCEPTS.md            → 領域詞彙表
docs/
  README.md            → 文件中心主索引
  handoffs/            → 交接文件（/handoff 產出）
    replies/           → 回覆信箱（對方 session 寫入）
  applications/        → 申請信箱（/kunsu-apply 投遞、add-project 審核）
    archive/           → 已處理申請歸檔
  reports/             → 上報信箱（/kunsu-report 投遞，軍師審閱歸檔）
    archive/           → 已處理上報歸檔
  solutions/           → 可重用學習與解法（/ce-compound 產出）
    architecture-patterns/
    conventions/
```

若步驟 ⑤ 已建立 Obsidian vault，則在結構末加 `docs/HOME.md → Obsidian 著陸頁`。

以 `Edit` 將 CLAUDE.md 中的 `{{PLANNER_STRUCTURE}}` 取代為生成的 ASCII tree。完成後以 `Grep` 確認 CLAUDE.md 內不含任何 `{{` 字串（無殘留佔位符）。

---

## 步驟 ⑤：建立 Obsidian Vault

### ⑤-1 檢查 init-vault.sh 是否存在

```bash
test -f "$HOME/.claude/skills/init-obsidian-vault/scripts/init-vault.sh" \
  && echo "found" || echo "not_found"
```

- **不存在** → 告知使用者：「init-obsidian-vault skill 未安裝，略過 Obsidian vault 步驟。可稍後手動執行 `/init-obsidian-vault`。」記錄此項於步驟 ⑧ 回報清單中。**繼續後續步驟，不中斷。**
- **存在** → 執行 ⑤-2。

### ⑤-2 執行 init-vault.sh

對軍師而言，`--ignore` 通常為空（純文件 repo 無需隱藏程式碼目錄）；若目標目錄已有非文件目錄（如 `skills/`），以逗號加入 `--ignore`。

```bash
bash "$HOME/.claude/skills/init-obsidian-vault/scripts/init-vault.sh" \
  --target "<PLANNER_ROOT_PATH>" \
  --home "docs/HOME.md"
```

### ⑤-3 產生 docs/HOME.md

1. 以 `Read` 讀取 `$HOME/.claude/skills/init-obsidian-vault/assets/home-template.md`。
2. 替換以下佔位符：
   - `{{PROJECT_NAME}}` → 軍師名稱（PLANNER_NAME）
   - `{{PROJECT_TAGLINE}}` → tagline
   - `{{ENTRY_LINKS}}` → 列實際存在的入口：`[[CLAUDE]]`、`[[CONCEPTS]]`、`[[docs/README|📁 文件中心索引]]`
   - `{{NAV_LINKS}}` → 列實際存在的 docs/ 子目錄：`docs/handoffs/`、`docs/solutions/` 等
3. 將 **Dataview 區塊移除**：軍師初始只有 solutions 有 frontmatter，其餘空目錄無 frontmatter 可查。只保留 HOME.md 基礎入口區塊。
4. 以 `Write` 寫至 `<PLANNER_ROOT_PATH>/docs/HOME.md`。
5. 以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/home-dataview-handoffs.md`，以**追加**方式（另起新行 `\n\n` 後）附加至 `docs/HOME.md`：以 `Edit` 在 HOME.md 末尾附加整個 dataview 區塊。
6. 以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/home-dataview-reports.md`，以**追加**方式（另起新行 `\n\n` 後）附加至 `docs/HOME.md`：以 `Edit` 在 HOME.md 末尾附加整個上報 dataview 區塊。

---

## 步驟 ⑥：Git 初始化（需使用者確認）

### ⑥-1 列出已建立的檔案

```bash
find "<PLANNER_ROOT_PATH>" -not -path "*/.git/*" -not -name ".DS_Store" | sort
```

以清單形式回報給使用者，詢問確認：

> AskUserQuestion：「以上 N 個檔案已建立於 <PLANNER_ROOT_PATH>。確認後將執行 git init 並建立初始 commit。繼續？（y/n）」

### ⑥-2 執行 git 初始化（使用者確認後）

```bash
cd "<PLANNER_ROOT_PATH>" && git init
git -C "<PLANNER_ROOT_PATH>" add .
git -C "<PLANNER_ROOT_PATH>" commit -m "feat: 初始化軍師（規劃協調中心）<PLANNER_NAME>"
```

> 說明：此 commit 是新建立的軍師 repo 的初始 commit，屬於允許的操作。

### ⑥-3 取消時的處理

若使用者回 n，提示：「可手動刪除整個目錄（`rm -rf <PLANNER_ROOT_PATH>`）還原。registry 尚未寫入，無需額外清理。」**不自動執行 rollback。**

---

## 步驟 ⑦：登記至 kunsu-registry.json

對每個子專案，呼叫 `registry-merge.sh`（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑）：

```bash
bash "$CLAUDE_SKILL_DIR/scripts/registry-merge.sh" \
  "<sub-repo-abs-path>" \
  "<PLANNER_ROOT_PATH>" \
  "<角色代碼>"
```

> 傳入 registry 的是**角色代碼**（非角色說明）；角色說明只落在 CLAUDE.md 關聯專案表說明欄，不進註冊表。

逐一執行，回報每次的 stdout（新增 / 已登記 / 更新角色）。若 registry-merge 對某代碼輸出 WARN（含空白或過長，疑為誤填整句描述），停下向使用者確認該欄是否填成說明。若任一呼叫以非零退出（JSON 損壞或 python3 缺失），停下報告錯誤，不繼續後續子專案的登記。

---

## 步驟 ⑧：驗收核查

逐項核對以下十一項，以表格或清單形式回報「通過 / 未通過 + 說明」：

| 項目 | 查核方式 | 不變量編號 |
|------|----------|-----------|
| `docs/handoffs/` 目錄存在 | `test -d "<PLANNER_ROOT_PATH>/docs/handoffs"` | ADR 001 結構不變量 |
| `docs/handoffs/replies/.gitkeep` 存在 | `test -f "<PLANNER_ROOT_PATH>/docs/handoffs/replies/.gitkeep"` | ADR 001 結構不變量 |
| `docs/applications/.gitkeep` 存在 | `test -f "<PLANNER_ROOT_PATH>/docs/applications/.gitkeep"` | ADR 006 申請信箱結構 |
| `docs/applications/archive/.gitkeep` 存在 | `test -f "<PLANNER_ROOT_PATH>/docs/applications/archive/.gitkeep"` | ADR 006 申請信箱結構 |
| CLAUDE.md 含申請信箱協議 | `grep -c 'docs/applications/' "<PLANNER_ROOT_PATH>/CLAUDE.md"` 應大於 0 | ADR 006 申請信箱結構 |
| `docs/reports/.gitkeep` 存在 | `test -f "<PLANNER_ROOT_PATH>/docs/reports/.gitkeep"` | ADR 008 上報信箱結構 |
| `docs/reports/archive/.gitkeep` 存在 | `test -f "<PLANNER_ROOT_PATH>/docs/reports/archive/.gitkeep"` | ADR 008 上報信箱結構 |
| CLAUDE.md 含上報信箱協議 | `grep -c 'docs/reports/' "<PLANNER_ROOT_PATH>/CLAUDE.md"` 應大於 0 | ADR 008 上報信箱結構 |
| 軍師根目錄為 git repo | `test -d "<PLANNER_ROOT_PATH>/.git"` | ADR 001 結構不變量 |
| CLAUDE.md 無殘留 `{{...}}` 佔位符 | `grep -c '{{' "<PLANNER_ROOT_PATH>/CLAUDE.md"` 應為 0 | 範本渲染完整 |
| docs/README.md 無殘留 `{{...}}` 佔位符 | `grep -c '{{' "<PLANNER_ROOT_PATH>/docs/README.md"` 應為 0 | 範本渲染完整 |

最後附加回報：
- 技術棧降級為「待補充」的子專案（若有）
- init-obsidian-vault 是否略過（若略過，提示安裝方式）
- registry 登記摘要（各子專案登記結果）

---

## 設計備註

- **`$CLAUDE_SKILL_DIR` 定位**：由 Claude Code harness 注入，指向此 skill 目錄（例如部署後為 `~/.claude/skills/kunsu-init/`）；若未注入，以 `Read` 查閱此 SKILL.md 所在路徑後推算。
- **範本固定段落來源**：抽取自 ebook 專案群規劃中心母本（本機私有路徑，略），含 5 條 Invariants、回覆信箱協議全文（含 cd 陷阱說明、Method 2 備援、tripwire、不對稱授權）、工作流程六步驟。各軍師自持一份，消除對母本路徑的依賴。
- **`registry-merge.sh` 的 python3 依賴**：macOS 系統自帶 python3（Xcode CLT），腳本已在缺失時給出安裝提示。不引入 jq 或其他外部依賴。
- **為何 git commit 允許**：步驟 ⑥ 的 commit 是新建軍師 repo 的初始 commit，不是對既有 repo 的未授權提交，且需使用者明確確認後才執行。add-project 步驟 ⑩ 的確認 commit 同理——依 ADR 009，逐次確認即為使用者明確要求，允許理由擴為「協議流程尾端對自身產出的收斂 commit」。
- **Obsidian vault 呼叫既有 skill 的腳本**：直接呼叫 `init-vault.sh` 的固定部分（建立 .obsidian/），HOME.md 由本 skill 產生（含 handoffs dataview 附加），不重複執行 init-obsidian-vault 的完整流程。

---

## add-project 子指令

在既有軍師（已由 `/kunsu-init` 建立）中新增一個子專案，或更新已登記子專案的角色代碼或角色說明。主要路徑是**審核申請信箱**：掃描 `docs/applications/` 的待審申請（由子專案以 `/kunsu-apply` 投遞）、逐筆審核，核准當下才同步更新軍師 CLAUDE.md 關聯專案表與環境限制小節、登記至全域反向註冊表（單點登記），並將申請歸檔。無待審申請時退回分題訪談路徑；偵測到舊版軍師缺申請信箱時內建遷移。

**必須在軍師根目錄下的 session 執行此子指令。**

**本子指令對子專案目錄完全唯讀（只使用 Read 與唯讀 git 查詢）。**

---

### ①：身分驗證

以 `Bash` 取得當前 repo 根路徑，設為 `<CURRENT_REPO_ROOT>`：

```bash
git rev-parse --show-toplevel
```

接著以 `Bash` 讀取並驗證 registry（以 python3 行內執行，傳入 `<CURRENT_REPO_ROOT>` 作為參數）：

```bash
python3 - "<CURRENT_REPO_ROOT>" <<'PYEOF'
import json, os, sys
reg = os.path.expanduser("~/.claude/kunsu-registry.json")
if not os.path.exists(reg):
    print("not_found"); sys.exit(0)
try:
    data = json.load(open(reg))
except Exception:
    print("json_error"); sys.exit(0)
kunsu_paths = {e["kunsu"] for entries in data.values() for e in entries}
print("ok" if sys.argv[1] in kunsu_paths else "not_kunsu")
PYEOF
```

根據輸出：

- **`not_found`**：報錯「`~/.claude/kunsu-registry.json` 不存在，請先以 `/kunsu-init` 建立軍師並完成登記。」終止。
- **`json_error`**：報錯「kunsu-registry.json 格式損壞，請手動修復後再執行 add-project。」終止。
- **`not_kunsu`**：報錯「請於軍師根目錄執行 add-project（當前路徑 `<CURRENT_REPO_ROOT>` 未登記為任何軍師）。」終止。
- **`ok`**：繼續步驟 ②。

---

### ②-a：申請信箱遷移偵測

```bash
test -d "<CURRENT_REPO_ROOT>/docs/applications" && echo "ok" || echo "missing"
```

- **ok** → 記錄 `APP_MIGRATION=ok`，繼續執行 ②-b。
- **missing**（舊版 scaffold 的軍師）→ 以 `AskUserQuestion` 提議遷移：「本軍師尚無申請信箱（`docs/applications/`）。是否補建並在 CLAUDE.md 補入申請信箱協議？補建後子專案才能以 `/kunsu-apply` 投遞申請。（y/n）」
  - **y → 執行遷移三步：**
    1. **補建目錄**：
       ```bash
       mkdir -p "<CURRENT_REPO_ROOT>/docs/applications/archive"
       touch "<CURRENT_REPO_ROOT>/docs/applications/.gitkeep"
       touch "<CURRENT_REPO_ROOT>/docs/applications/archive/.gitkeep"
       ```
    2. **補協議文字**：以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/kunsu-claude.md`（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑），取出「申請信箱協議」整個章節與雙信箱版的兩條 bullet，以 `Edit` 更新軍師 CLAUDE.md：
       - 在 `## 文件導航` 標題之前插入「## 申請信箱協議」整段（與範本逐字相同），並在文件導航表補 `docs/applications/` 兩列。
       - 將回覆信箱協議中「**信箱範圍是唯一的例外授權**」bullet 改寫為範本現行的雙信箱表述；tripwire bullet 的核對範圍同步擴及 `docs/applications/` 頂層。
       - 任一插入錨點不存在（CLAUDE.md 經手改）→ 略過該處，留待核查回報。
    3. **完成核查（兩條，防半更新）**：
       - `grep -c 'docs/applications/' "<CURRENT_REPO_ROOT>/CLAUDE.md"` 應大於 0（申請信箱協議已插入）。
       - `grep -c '信箱範圍是唯一的例外授權' "<CURRENT_REPO_ROOT>/CLAUDE.md"` 應為 0（舊單信箱 bullet 已改寫；非零表示協議停在自相矛盾的半更新狀態）。pattern 須用舊 bullet 專屬前綴「信箱範圍是唯一的例外授權」（與上方步驟 2「改寫舊 bullet」所指涉的字串一致）；**勿改回較短的「唯一的例外授權」——範本現行雙信箱 bullet 本身即「兩個信箱是唯一的例外授權…」，含該短子字串，會被命中而把正確遷移誤判成半更新**。
       任一條核查失敗 → 明確回報失敗項目：「目錄已補建，但 CLAUDE.md 協議文字補入不完整（申請信箱章節缺失／舊『唯一例外授權』bullet 未改寫）。請對照範本 `kunsu-claude.md` 手動補正。」**不回滾已建目錄**，記錄 `APP_MIGRATION=migrated`（目錄已建），繼續執行 ②-b。
    → 三步執行完畢：記錄 `APP_MIGRATION=migrated`，繼續執行 ②-b。
  - **n → 拒絕遷移**：記錄 `APP_MIGRATION=skipped`，繼續執行 ②-b。

---

### ②-b：上報信箱遷移偵測

> **兩段偵測各自獨立、依序執行、單段失敗回報後，後段照常執行。**

```bash
test -d "<CURRENT_REPO_ROOT>/docs/reports" && echo "ok" || echo "missing"
```

- **ok** → 記錄 `REPORT_MIGRATION=ok`，繼續（見下方統一跳轉）。
- **missing**（尚未補建上報信箱的軍師）→ 以 `AskUserQuestion` 提議遷移：「本軍師尚無上報信箱（`docs/reports/`）。是否補建並在 CLAUDE.md 補入上報信箱協議？補建後子專案才能以 `/kunsu-report` 投遞上報。（y/n）」
  - **y → 執行遷移三步：**
    1. **補建目錄**：
       ```bash
       mkdir -p "<CURRENT_REPO_ROOT>/docs/reports/archive"
       touch "<CURRENT_REPO_ROOT>/docs/reports/.gitkeep"
       touch "<CURRENT_REPO_ROOT>/docs/reports/archive/.gitkeep"
       ```
    2. **補協議文字**：以 `Read` 讀取 `$CLAUDE_SKILL_DIR/assets/templates/kunsu-claude.md`（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑），取出「上報信箱協議」整個章節，以 `Edit` 更新軍師 CLAUDE.md：
       - 在 `## 文件導航` 標題之前插入「## 上報信箱協議」整段（置於「申請信箱協議」章節之後，與範本逐字相同），並在文件導航表補 `docs/reports/` 與 `docs/reports/archive/` 兩列。
       - 將回覆信箱協議中「**兩個信箱是唯一的例外授權**」bullet 改寫為範本現行的三信箱表述（「三個信箱是唯一的例外授權…」）；tripwire bullet 的核對範圍同步擴及 `docs/reports/` 頂層，並更新授權歸檔括號說明列入上報信箱。
       - 任一插入錨點不存在（CLAUDE.md 經手改）→ 略過該處，留待核查回報。
    3. **完成核查（兩條，防半更新）**：
       - `grep -c 'docs/reports/' "<CURRENT_REPO_ROOT>/CLAUDE.md"` 應大於 0（上報信箱協議已插入）。
       - `grep -c '兩個信箱是唯一的例外授權' "<CURRENT_REPO_ROOT>/CLAUDE.md"` 應為 0（雙信箱 bullet 已改寫為三信箱表述；此為軍師 CLAUDE.md 雙信箱版 bullet 的專屬前綴，三信箱改寫後不復存在）。**勿縮短核查字串為「唯一的例外授權」——三信箱新 bullet 本身即「三個信箱是唯一的例外授權…」，含該短子串，會把正確遷移誤判成半更新**；並注意此處核查的是軍師 CLAUDE.md 的 bullet 文字，與 kunsu-inbox SKILL.md 的「兩個信箱是唯讀邊界的唯一例外」措辭不同，請勿混用。
       任一條核查失敗 → 明確回報失敗項目：「目錄已補建，但 CLAUDE.md 協議文字補入不完整（上報信箱章節缺失／雙信箱 bullet 未改寫為三信箱表述）。請對照範本 `kunsu-claude.md` 手動補正。」**不回滾已建目錄**，記錄 `REPORT_MIGRATION=migrated`（目錄已建），繼續（見下方統一跳轉）。
    → 三步執行完畢：記錄 `REPORT_MIGRATION=migrated`，繼續（見下方統一跳轉）。
  - **n → 拒絕遷移**：記錄 `REPORT_MIGRATION=skipped`，繼續（見下方統一跳轉）。

**②-b 完成後統一跳轉**：
- `APP_MIGRATION=skipped` → 記錄「軍師未遷移，本次跳過申請掃描」，跳至步驟 ⑤（訪談路徑）。
- `APP_MIGRATION=ok` 或 `APP_MIGRATION=migrated` → 繼續步驟 ③。

（`REPORT_MIGRATION` 結果不影響此跳轉——上報信箱缺失僅擋 `/kunsu-report` 投遞，不擋申請審核流程。）

---

### ③：掃描待審申請

呼叫部署於 kunsu-inbox 的掃描腳本（兩 skill 由同一 `install.sh` 散布，不在 kunsu-init 內複製副本以免雙份漂移）：

```bash
bash ~/.claude/skills/kunsu-inbox/scripts/scan-applications.sh "<CURRENT_REPO_ROOT>"
```

- **腳本不存在** → 報錯「找不到 `scan-applications.sh`，請重跑 kunsu toolkit 的 `install.sh` 更新部署後再執行。」終止。
- **exit 2（tripwire）** → **立即停止**，比照 `/kunsu-inbox` 軍師模式的 tripwire 格式回報意外變更清單（每行 `TRIPWIRE:<XY> <路徑>`），請使用者確認處置並 commit 後再執行，不繼續審核。
- **其他非零 exit（如 1：參數錯誤或非 git 根）** → 停下回報腳本的 stderr 內容，不繼續。
- **exit 0** → 解析每行 `NEW_APPLICATION:<相對路徑>` 得待審申請清單。**另補一道已 commit 漏網檢查**：以 `Glob` 掃 `<CURRENT_REPO_ROOT>/docs/applications/*.md`（頂層），`Read` frontmatter 篩 `status: pending` 者——已被 commit 的待審申請不會出現在 git 狀態掃描中（例如使用者習慣性 commit 了整個工作樹），但仍是待審。待審清單 = 兩者聯集（去重）：
  - **零筆** → 跳至步驟 ⑤（訪談路徑）。
  - **一筆以上** → 繼續步驟 ④。

---

### ④：審核待審申請

**④-1 解析與分組：**

逐一以 `Read` 讀取申請檔 frontmatter（`name`／`path`／`proposed_role`（提議角色代碼）／`role_desc`（角色說明，選填）／`constraints`／`self_verify`／`stack`／`created`／`status`），並**一次** `Read` 軍師 CLAUDE.md 供整批申請的關聯專案表比對（避免每筆重讀）。

- **frontmatter 解析失敗**（截斷、缺 `path` 或 `proposed_role` 等必要欄位）→ 呈現為「格式異常申請」，僅提供「退回歸檔」選項（走 ④-5，`decision_note: frontmatter 格式異常`）。
- **`status` 非 `pending`**（前次處置在 frontmatter 更新後、歸檔搬移前中斷的殘留）→ 不進入審核，以 `AskUserQuestion` 詢問是否補完歸檔（依 ④-4 第 2 點的 add＋mv 搬移收檔）。
- 依 `path` 分組。**同路徑有多份待審** → 以 `AskUserQuestion` 列出各份（檔名、`created`），詢問：「同一子專案有多份待審申請。以最新一份繼續審核、其餘自動退回（原因：被較新申請取代）？或取消本次處理？」使用者確認後才執行，不靜默退回。**「最新」的排序規則**：從檔名解析日期與可選數值後綴（無 `-2`、`-3` 後綴時 n=1），以 `(date, n)` 降序取第一筆——勿直接對檔名做字串排序（ASCII 中 `-` < `.`，同日時無後綴的基礎檔名反而排在有後綴者之後，會誤取較舊的一份；同 `/kunsu-inbox` 步驟 4a-3 的注意事項）。

**④-2 路徑有效性驗證（每份進入審核的申請）：**

```bash
git -C "<path>" rev-parse --show-toplevel 2>/dev/null || echo "invalid"
```

- **invalid**（路徑不存在或非 git repo）→ 以 `AskUserQuestion` 警告，選項：「修正路徑（輸入正確絕對路徑後重驗）／強制登記（自負風險）／退回此申請」。不靜默通過——`path` 是關聯專案表、registry 與後續 handoff 協作的鍵，登記錯誤路徑會讓下游全部失效。

**④-3 逐筆審核：**

每份申請以 `AskUserQuestion` 呈現摘要（顯示名稱、路徑、提議角色代碼、角色說明、環境限制、自我驗證、技術棧），選項：

- **核准（採用提議角色代碼）**
- **修改角色代碼後核准**：追問定案角色代碼（代碼定案權在軍師）。追問時提醒：**此代碼即 handoff `to:` 的唯一來源，務必精確且為短、kebab-case（宜 ≤ 20 字、不含軍師名前綴）**——與既有交接文件的 `to:` 不一致會使 `/kunsu-inbox` 篩選失效。（角色說明可一併調整，只寫入 CLAUDE.md 說明欄、不影響比對。）
- **退回**：追問退回原因。

**④-3.5 角色代碼唯一性強制（權威強制點）：**

核准（或改碼核准）定案後、執行 ④-4 寫入前，強制核對代碼唯一性——**這是全體系唯一性的權威強制點**（kunsu-apply 的早期檢查非權威、看不到在途申請）：

1. 以 python3 讀 registry，取本軍師（`entry.kunsu == <CURRENT_REPO_ROOT>`）所有已登記代碼聯集，**排除**當前申請子專案路徑自身的既有代碼（改碼更新場景不與自己相撞）。
2. 再聯集**本批次已核准代碼的 session 級暫存集**（本次 add-project 已處理、尚在同一 session 的核准代碼）——**每筆均重新比對此暫存集，不可沿用 ④-1 的批次快照**（否則同批兩份填同碼會漏偵測）。
3. 定案代碼命中上述聯集 → 以 `AskUserQuestion` 阻擋，**列出該軍師已登記代碼集合**，要求改碼後重驗；不命中才續 ④-4，並把此代碼加入 session 暫存集。

**④-4 核准處置：**

1. 以 `Read` 讀取軍師 CLAUDE.md 關聯專案表，判斷申請 `path` 是否已出現：
   - **已出現（重複申請）** → 走步驟 ⑧（重複登記處理，詢問是否更新角色代碼或說明，含步驟 ⑨ 改名警告分支）。
   - **未出現（首次登記）** → 若定案角色代碼異於 `proposed_role`，**先以 `proposed_role` 為「舊角色代碼」執行步驟 ⑨ 掃描**（軍師可能在正式登記前已用提議代碼建立過交接文件，改名會使其 `to:` 對應失效）；之後執行步驟 ⑥（更新關聯專案表與環境限制小節）與步驟 ⑦（registry-merge）。
2. **處置落檔**：以 `Edit` 更新申請檔 frontmatter `status: pending` → `approved`，再以授權歸檔搬移收檔：

   ```bash
   git -C "<CURRENT_REPO_ROOT>" add "docs/applications/<檔名>"
   git -C "<CURRENT_REPO_ROOT>" mv "docs/applications/<檔名>" "docs/applications/archive/<檔名>"
   ```

   > 先 `git add` 再 `git mv`：待審申請通常是 untracked（未 commit 即未處理慣例），`git mv` 對 untracked 檔案會以 `not under version control` 失敗；add 之後兩種狀態（untracked／已 commit）都能安全搬移，且掃描結果分別為 archive/ 內新增與授權歸檔 rename，均不誤觸 tripwire。

**④-5 退回處置：**

以 `Edit` 更新申請檔 frontmatter：`status: pending` → `rejected`，並於 `status` 下一行加入 `decision_note: <退回原因>`；同樣以 ④-4 的「先 `git add` 再 `git mv`」順序歸檔至 `archive/`。CLAUDE.md 與 registry 均不異動。

全部申請處理完 → 跳至步驟 ⑩（完成回報）。

---

### ⑤：訪談（fallback——無待審申請或未遷移時）

以單次 `AskUserQuestion` **分題**收集新子專案資訊（分題取代舊版一行式輸入，避免長字串在終端機輸入的顯示問題）：

1. **顯示名稱**：出現在關聯專案表的名稱，可含空格。
2. **絕對路徑**：子 repo 的絕對路徑（隨後查證存在）。
3. **角色代碼**：短、kebab-case，**即 handoff `to:` 的唯一比對鍵，務必精確**（宜 ≤ 20 字、不含軍師名前綴）；同軍師內須唯一（進 ④-3.5 唯一性強制）。
4. **角色說明（選填）**：一行職責描述，display-only，只落 CLAUDE.md 說明欄、不進註冊表、不比對；留空為「無」。
5. **環境限制（選填）**：特殊限制或已知約束；留空即「無」，不新增限制小節。
6. **能否自我驗證**：`y` = 可在該 repo 執行測試驗收；`n` = 需人工或跨 repo。

**查證與分支判斷：**

- **路徑存在性**：
  ```bash
  test -d "<sub-repo-abs-path>" && echo "ok" || echo "missing"
  ```
  路徑不存在 → 以 `AskUserQuestion` 告知，請使用者提供修正路徑或輸入 `skip` 略過；等待回覆後更新路徑並重新查證。
- **技術棧摘要（唯讀）**：以 `Read` 嘗試讀取 `<sub-repo-abs-path>/CLAUDE.md`：有 CLAUDE.md → 摘出「技術棧」或「技術選型」小節關鍵詞（語言、框架）；無 → 記錄「待補充」，流程不中斷，於步驟 ⑩ 回報。
- **重複登記預檢**：以 `Read` 讀取 `<CURRENT_REPO_ROOT>/CLAUDE.md`，確認子專案絕對路徑是否已出現在關聯專案表：
  - **未出現（新增路徑）** → 先執行 **④-3.5 角色代碼唯一性強制**（撞名即列既有代碼、要求改碼），通過後執行步驟 ⑥ 與步驟 ⑦，之後跳至步驟 ⑩。
  - **已出現（重複路徑）** → 跳至步驟 ⑧。

---

### ⑥：更新軍師 CLAUDE.md

以 `Edit` 精準插入，**不重排既有內容**。

**關聯專案表 append**（新增分支）：在表格最後一個 `| … |` 列的末尾換行後插入新列（雙欄：角色代碼＋角色說明，說明留空時該欄留空）：

```
| <顯示名稱> | <絕對路徑> | <角色代碼> | <角色說明或空> |
```

**環境限制小節 append**（僅限環境限制非「無」時）：在現有環境限制段落末尾後附加：

```markdown
### <顯示名稱> 環境限制

<限制說明>
```

全部環境限制為「無」時略過此步驟。

> 從步驟 ⑧ 進入更新路徑時：以 `Edit` 精確替換現有列的角色代碼欄與（如有調整）角色說明欄文字，不異動其他列。

---

### ⑦：登記至 kunsu-registry.json

呼叫 `registry-merge.sh`（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑）：

```bash
bash "$CLAUDE_SKILL_DIR/scripts/registry-merge.sh" \
  "<sub-repo-abs-path>" \
  "<CURRENT_REPO_ROOT>" \
  "<角色代碼>"
```

> 傳入 registry 的是**角色代碼**（非角色說明）。角色說明只在步驟 ⑥ 寫入 CLAUDE.md 說明欄。

回報 stdout（新增 / 已登記 / 更新角色）。若 registry-merge 對定案代碼輸出 WARN（含空白或過長，疑為誤填整句），停下向使用者確認。若呼叫以非零退出（JSON 損壞或 python3 缺失），停下報告錯誤，不繼續後續步驟。

---

### ⑧：重複登記處理

（從步驟 ④-4「已出現（重複申請）」或步驟 ⑤「已出現（重複路徑）」分支進入）

以 `AskUserQuestion` 告知：「`<顯示名稱>`（`<絕對路徑>`）已登記於本軍師，是否更新角色代碼或角色說明？（y/n）」

- **n**：略過步驟 ⑥、⑦，回報「登記已存在，無異動。」（申請路徑進入時仍執行 ④-4 第 2 點的處置落檔：`status: approved`，並加 `decision_note: 角色未變更（沿用既有登記）`。）
- **y**：以 `AskUserQuestion` 請使用者提供**新角色代碼**（與可選的新角色說明；申請路徑進入時，代碼預設值為申請的 `proposed_role`、說明預設為 `role_desc`）；記錄舊角色代碼後，**先執行 ④-3.5 角色代碼唯一性強制**（排除本子專案自身舊碼），再**跳至步驟 ⑨** 進行角色改名警告；警告確認後執行步驟 ⑥（更新現有列的代碼欄與說明欄）與步驟 ⑦。（申請路徑進入時，⑥⑦ 完成後同樣執行 ④-4 第 2 點的處置落檔，避免申請檔以 pending 狀態留在頂層成為幽靈申請。）

---

### ⑨：角色改名警告

（多入口：從步驟 ⑧ y 分支進入時，「舊角色代碼」為既有登記的角色；從步驟 ④-4 首次核准改名進入時，「舊角色代碼」為申請的 `proposed_role`。兩種入口的掃描邏輯相同。）

1. 以 `Glob` 掃描 `<CURRENT_REPO_ROOT>/docs/handoffs/*.md`（**只取頂層**，不含 `replies/`、`archive/` 子目錄內的檔案）。
2. 逐一以 `Read` 讀取每份 handoff 的 frontmatter，篩選 `to:` 字面等於**舊角色代碼**的文件。
3. 對每筆符合者判斷「是否未完成」：
   - 以 `Glob` 掃描 `<CURRENT_REPO_ROOT>/docs/handoffs/replies/*.md`，篩選 frontmatter `in_reply_to` 對應原交接檔名（含 `.md` 後綴）的回覆。
   - **無任何對應回覆** → 未完成。
   - **有對應回覆** → 取最新一份（依日期與數值後綴排序，非字串排序），以 `Read` 讀其 `status`：`done` = 完成；`partial`／`blocked`／`submitted` = 未完成。
4. **有未完成 handoff 持有舊角色代碼**：
   - 列出警告清單（交接文件標題、建立日期、`to:` 欄位值、最新 status 或「無回覆」）。
   - 以 `AskUserQuestion` 提示：「以下 N 份未完成交接文件的 `to:` 仍為舊角色代碼「<舊角色代碼>」，改名後 /kunsu-inbox 將無法自動篩選到這些交接。請確認處置方式（手動更新 `to:` 欄位 / 保留舊角色代碼不動 / 取消改名）：」
   - **僅提示，不自動修復 `to:`**；等待使用者確認。若使用者選擇取消改名：申請路徑進入時退回步驟 ④-3 重新選擇動作；訪談路徑（自步驟 ⑧）進入時終止本筆，**不執行步驟 ⑥、⑦**。
5. **無未完成 handoff 持有舊角色代碼** → 不出警告，直接繼續原流程。

---

### ⑩：完成回報

以正體中文摘要變更：

| 位置 | 異動內容 |
|------|---------|
| 申請處理摘要 | 核准 N 份（列出各定案角色代碼）、退回 M 份（列出退回原因）、格式異常 K 份（若走申請路徑）|
| 軍師 CLAUDE.md 關聯專案表 | 新增列 or 更新角色代碼欄／角色說明欄（列出具體角色代碼）|
| 環境限制小節 | 新增段落（若有）/ 略過（無環境限制）|
| kunsu-registry.json | registry-merge.sh 回報結果（新增 / 已登記更新 / 略過），登記值為**角色代碼** |
| 申請歸檔 | 各申請檔 → `docs/applications/archive/`（status 已更新）|

最後加上角色代碼三處一致確認：

> **角色代碼三處一致提醒**：角色代碼「<角色代碼>」已同步至軍師 CLAUDE.md 關聯專案表代碼欄與 kunsu-registry.json roles 欄位；角色說明（若有）僅寫入 CLAUDE.md 說明欄、不進註冊表。此代碼即 handoff `to:` 的唯一來源——後續建立交接請使用字面完全相同的角色代碼，/kunsu-inbox 以此篩選待接手交接文件。

若有技術棧降級為「待補充」的子專案，一併回報。

**確認 commit（協議步驟，走申請路徑時必執行）**：

依 ADR 009，本次審核產出以「確認一次 → commit」收斂，維持「未 commit 即未處理」慣例的清晰度：

1. **核對**：`git status --porcelain` 確認本次審核產出的具體路徑（軍師 `CLAUDE.md`、`docs/applications/archive/<各歸檔檔名>`）確有待提交變更。無變更（使用者已自行 commit）→ 回報「相關檔案已提交，無需操作」，**不產生空 commit**。
2. **確認**：AskUserQuestion「是否 commit 本次審核產出？（訊息：`docs: 審核申請 <子專案顯示名>（核准）`，多筆審核時併列於同一訊息）」。
3. **確認後執行**：`git add` 上述具體路徑（**不含** `~/.claude/kunsu-registry.json`——registry 為 repo 外全域檔案，不屬任何 repo 的版控範圍；亦不用 `git add -A`）→ `git commit`。**絕不 push**。
4. **取消時**：登記與歸檔結果保留、不回退任何操作，回報可稍後手動執行的完整 `git add`＋`git commit` 指令。（歸檔搬移已被掃描規則豁免，未 commit 期間不會誤觸 tripwire。）

---

## remove-project 子指令

在既有軍師（已由 `/kunsu-init` 建立）中移除一個子專案在本軍師的登記——對稱於 `add-project`。子專案可能因檔案結構合併或拆分使原本登記的路徑或角色代碼失效；本子指令**整筆移除**該子專案在本軍師的所有角色代碼登記（不支援只移除其中一個角色代碼），同步更新軍師 CLAUDE.md 關聯專案表與全域反向註冊表 `~/.claude/kunsu-registry.json`。移除前掃描未完成交接文件並警告、需經不可逆確認。

**必須在軍師根目錄下的 session 執行此子指令。**

**本子指令對子專案目錄完全唯讀（只使用 Read 與唯讀 git 查詢）；全部寫入僅發生在軍師自己的 CLAUDE.md 與軍師 repo 外的全域 registry，不寫入任何子專案目錄——不構成「軍師對子專案唯讀」（Invariant 2）的例外。**

---

### ①：身分驗證

與 `add-project` 步驟①完全相同：

```bash
git rev-parse --show-toplevel
```

```bash
python3 - "<CURRENT_REPO_ROOT>" <<'PYEOF'
import json, os, sys
reg = os.path.expanduser("~/.claude/kunsu-registry.json")
if not os.path.exists(reg):
    print("not_found"); sys.exit(0)
try:
    data = json.load(open(reg))
except Exception:
    print("json_error"); sys.exit(0)
kunsu_paths = {e["kunsu"] for entries in data.values() for e in entries}
print("ok" if sys.argv[1] in kunsu_paths else "not_kunsu")
PYEOF
```

- **`not_found`**：報錯「`~/.claude/kunsu-registry.json` 不存在，請先以 `/kunsu-init` 建立軍師並完成登記。」終止。
- **`json_error`**：報錯「kunsu-registry.json 格式損壞，請手動修復後再執行 remove-project。」終止。
- **`not_kunsu`**：報錯「請於軍師根目錄執行 remove-project（當前路徑 `<CURRENT_REPO_ROOT>` 未登記為任何軍師）。」終止。
- **`ok`**：繼續步驟②。

---

### ②：清單建立與呈現

以 python3 行內執行，讀 registry 取本軍師（`entry.kunsu` 正規化後與 `<CURRENT_REPO_ROOT>` 相符）的所有子專案（路徑＋`roles`），並以 `Read` 讀取軍師 CLAUDE.md 關聯專案表逐列解析（顯示名稱、路徑、角色代碼；表格 header 為 `| 專案 | 路徑 | 角色代碼 | 角色說明 |`，逐列以 `|` 切分並去除空白，略過 header 列與 `---` 分隔列）。

**兩來源聯集，不是只認 registry**：對兩側路徑均執行 `os.path.realpath()` 正規化後以路徑為鍵聯集去重——

- 僅 registry 有的項目 → 顯示名稱 fallback 為「（無 CLAUDE.md 對應列，路徑：`<path>`）」。
- 僅 CLAUDE.md 有的項目 → 正常列出（此類項目移除時，registry 側呼叫 `registry-remove.sh` 會走冪等略過，見步驟⑤）。

之所以聯集兩來源而非只以 registry 為權威候選清單：registry 與 CLAUDE.md 可能因手動編輯而不同步，若清單只認 registry，僅存在於 CLAUDE.md 的殘留列將永遠無法被本子指令選中清除，形同留下一條沒有出口的孤兒資料。

對聯集後的每筆執行 `os.path.isdir()` 路徑存在性查核，路徑不存在者標記 ⚠ 並排列在清單前段（stale 優先，其餘依原順序）。

**清單為零筆** → 提示「本軍師目前沒有已登記子專案。」並終止，不進入後續步驟。

**清單非空** → 以 `AskUserQuestion` 呈現含序號的清單（顯示名稱、路徑、角色代碼，stale 者加 ⚠），選項明確包含「取消」：

- **選「取消」** → 回報「操作取消，未執行任何移除。」終止，不寫入任何檔案。
- **選定一筆** → 繼續步驟③。

---

### ③：未完成交接警告

取得選定子專案在本軍師登記的完整角色代碼集合——registry 該子專案本軍師 entry 的 `roles` 陣列與 CLAUDE.md 該列代碼欄兩者的**聯集**（不是擇一 fallback；擇一會讓另一側才有的角色代碼被漏掃，使該代碼底下的未完成交接悄悄跳過警告）。兩側代碼不一致時，額外回報「發現 registry 與 CLAUDE.md 角色代碼不一致（registry: `<...>`，CLAUDE.md: `<...>`），掃描已取聯集」。

1. 以 `Glob` 掃描 `<CURRENT_REPO_ROOT>/docs/handoffs/*.md`（**只取頂層**，不含 `replies/`、`archive/`）。
2. 逐一以 `Read` 讀取每份 frontmatter，篩選 `to:` 屬於上述角色代碼集合的文件。
3. 對每筆符合者判斷「是否未完成」：
   - 先以 `Glob` 列出 `<CURRENT_REPO_ROOT>/docs/handoffs/replies/*.md` 全部實體檔案（不依賴 git status，含 untracked），逐一以 `Read` 讀取 frontmatter，篩選 `in_reply_to` 字面等於該交接檔名（含 `.md` 後綴）者為其回覆。
   - **無任何對應回覆** → 未完成。
   - **有對應回覆** → 取最新一份（依檔名 `(date, n)` 降序，不可用字串排序——同日多份回覆時，無數值後綴視為 `n=1`，字串排序會把無後綴的基礎檔名誤判為排在有後綴版本之後而誤取（即誤取較舊的一份），同 `add-project` 步驟⑨的提醒）讀其 `status`：`done` = 完成；`partial`／`blocked`／`submitted`／其他未知值 = 未完成。

**有未完成交接** → 以 `AskUserQuestion` 列出警告清單（每筆顯示：標題、建立日期、觸發的角色代碼、最新 status 或「無回覆」），並提示：「移除後，上述交接文件在軍師沙盤將被歸類為『to: 不符清單』，需手動歸檔。」選項「繼續」／「取消」：

- **選「取消」** → 終止，不寫入任何檔案。
- **選「繼續」** → 進入步驟④。

**無未完成交接** → 不出警告，直接進入步驟④。

---

### ④：不可逆最終確認

以 `AskUserQuestion` 呈現即將移除的摘要：

> 即將移除「`<顯示名稱>`」（`<絕對路徑>`）在本軍師的登記，角色代碼：`<角色代碼清單>`。
>
> **此操作不可逆**：全域反向註冊表（`~/.claude/kunsu-registry.json`）不受任何 repo 版控，移除後無法用 git 復原。
>
> 若此子專案同時登記其他軍師，其他軍師的登記不受影響。
>
> 確認移除？

選項「確認移除」／「取消」：

- **選「取消」** → 終止，不寫入任何檔案。
- **選「確認移除」** → 進入步驟⑤。

---

### ⑤：雙側移除

**寫入順序固定為先 CLAUDE.md、後 registry**——CLAUDE.md 受 git 版控、未 commit 前可用 `git checkout` 復原；registry 不受版控、寫入即不可逆。把可復原的操作放前面、不可逆操作放最後，任何中斷後的殘留狀態都停在「CLAUDE.md 已編輯未 commit（可復原）＋registry 未動」，而非相反。

**⑤-a：CLAUDE.md（若有對應列）**

以 `Read` 確認軍師 CLAUDE.md 關聯專案表是否仍有該子專案的列（可能已被手動刪除）：

- **有對應列**：
  1. 若該子專案有環境限制小節（`### <顯示名稱> 環境限制`），先以 `Grep` 確認此標題在 CLAUDE.md 中只出現一次。**出現多次** → 停下回報「「`<顯示名稱>` 環境限制」標題在 CLAUDE.md 中出現多次，無法安全定位，需人工確認後手動刪除，不自動刪除。」**終止整個 remove-project 流程，不繼續執行本步驟其餘部分，不進入⑤-b，也不進入步驟⑥**（此時尚未對 CLAUDE.md 做任何 Edit，無殘留狀態需要收拾）。
  2. 以 `Edit` 刪除關聯專案表對應列（以絕對路徑欄位為唯一定位鍵，精準匹配整行）；若環境限制小節唯一或不存在，一併刪除整個小節（標題行至下一個 `##`／`###` 標題前的全部內容，含前後空行）。
  3. 以 `Grep` 核查：表列中已無該子專案路徑字串、環境限制小節標題（若原本存在）也已消失。**核查失敗** → 停下回報「CLAUDE.md 可能已手動修改導致定位失敗，請人工確認後重新執行 remove-project。」**終止整個 remove-project 流程，不繼續執行⑤-b，也不進入步驟⑥**——CLAUDE.md 此時處於未確認的中間狀態，不得詢問是否 commit；registry 維持原狀。使用者需先人工確認 CLAUDE.md 的實際內容（`git diff` 檢視這次 Edit 的結果），修正無誤後才重新執行 remove-project。
  4. 核查通過 → 繼續⑤-b。
- **無對應列**（可能已手動刪除）→ 回報「CLAUDE.md 已無此子專案登記（可能已手動刪除），略過此步驟。」直接繼續⑤-b。

**⑤-b：registry**

呼叫 `registry-remove.sh`（`$CLAUDE_SKILL_DIR` 若未定義，改用此 SKILL.md 所在目錄的絕對路徑）：

```bash
bash "$CLAUDE_SKILL_DIR/scripts/registry-remove.sh" \
  "<sub-repo-abs-path>" \
  "<CURRENT_REPO_ROOT>"
```

回報 stdout 與 exit code：

- **exit 0**（成功移除）→ 回報「registry 登記已移除。」
- **exit 3**（找不到對應登記）→ 明確回報「registry 中未找到此子專案在本軍師的登記，請確認路徑是否正確；若此子專案原本僅登記於 CLAUDE.md，這是預期行為。」**不得**與 exit 0 混為一談、不得回報成「已成功移除」。
- **exit 1**（JSON 損壞或 python3 缺失）或其他非零 → 停下回報錯誤，不視為完成。

---

### ⑥：完成回報與確認 commit

以正體中文摘要變更：

| 位置 | 異動內容 |
|------|---------|
| 軍師 CLAUDE.md 關聯專案表 | 刪除列（或略過，若 CLAUDE.md 原本已無對應列）|
| 環境限制小節 | 刪除段落（若有）/ 略過（無環境限制）|
| kunsu-registry.json | `registry-remove.sh` 回報結果（已移除 / 找不到對應登記，略過）|

**確認 commit（協議步驟，比照 ADR 009）**：

1. **核對**：`git status --porcelain` 確認 `<CURRENT_REPO_ROOT>/CLAUDE.md` 確有待提交變更。**無變更**（如⑤-a 判定「無對應列」而略過編輯，CLAUDE.md 本就無異動）→ 回報「CLAUDE.md 無異動，無需 commit」，**不產生空 commit**。
2. **確認**：`AskUserQuestion`「是否 commit 本次移除產出？（訊息：`docs: 移除子專案登記 <顯示名稱>`）」。
3. **確認後執行**：`git add <CURRENT_REPO_ROOT>/CLAUDE.md`（**不含** `~/.claude/kunsu-registry.json`）→ `git commit`。**絕不 push**。
4. **取消時**：保留產出（CLAUDE.md 變更留在 working tree 未 commit；registry 已完成移除，不可逆），回報可稍後手動執行的 `git add`＋`git commit` 指令。

   **若使用者想完全放棄本次移除，明確提醒：不可先執行 `git checkout CLAUDE.md` 再重跑 `add-project`**——CLAUDE.md 還原後，`add-project` 的重複登記預檢會判定該子專案「已登記」，若使用者在該分支回答角色代碼不需異動，`add-project` 不會呼叫 `registry-merge.sh`，導致 registry 停留在已移除狀態、與還原後的 CLAUDE.md 重新產生漂移。正確作法二擇一：
   - **(a)** 保持 CLAUDE.md 目前未 commit 的刪除狀態，直接執行 `add-project` 走「首次登記」分支，同步補回 CLAUDE.md 列與 registry 登記；或
   - **(b)** 若已誤先 `git checkout CLAUDE.md`，改直接呼叫 `registry-merge.sh <sub-repo-abs-path> <kunsu-abs-path> <角色代碼>` 補回 registry，不透過 `add-project`。
