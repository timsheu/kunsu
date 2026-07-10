---
title: 撰寫 git porcelain 掃描腳本的四個陷阱
date: "2026-07-07"
category: best-practices
module: kunsu-toolkit-scripts
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - "撰寫以 git status --porcelain 為基礎的 shell 掃描或分類腳本"
  - "腳本處理的檔名可能含非 ASCII 字元（中文 slug 等）"
  - "以 bash [[ ]] glob 對多層目錄結構分類路徑"
  - "需要以 git mv 搬移可能尚未 commit 的檔案"
tags: [git-porcelain, shell-script, core-quotepath, git-mv, untracked-files, glob-pattern, macos, kunsu-inbox]
---

# 撰寫 git porcelain 掃描腳本的四個陷阱

## Context

申請信箱功能（ADR 006）需要一支掃描腳本 `scan-applications.sh`：以 `git status --porcelain` 識別頂層新申請、靜默豁免歸檔區（`archive/`）的授權變更、對其他意外變更觸發 tripwire 硬停。開發過程中，端到端 dogfooding 與 code review 實測共暴露三個 shell/git 陷阱，均已修復並以自動化場景驗證。

三個失敗路徑（What Didn't Work）：

- **直接 `git mv` 搬移待審申請**：申請依「未 commit 即未處理」慣例是 untracked，`git mv` 直接以 `fatal: not under version control` 失敗，歸檔流程中斷。
- **直接類比既有單層腳本的路徑 pattern**：`scan-replies.sh` 監看的 `docs/handoffs/replies/` 沒有子目錄；`docs/applications/` 有 `archive/`，照搬 `*.md` glob 會把歸檔區檔案誤判為新申請。
- **假設 porcelain 輸出的路徑永遠可直接使用**：中文檔名在 macOS 預設設定下輸出為 octal escape，以該字串讀檔必然失敗，且錯誤靜默流走。

## Guidance

### 陷阱一：`git mv` 對 untracked 檔案失敗

**錯誤寫法**

```bash
# untracked 檔案直接搬移 → fatal: not under version control
git -C "$ROOT" mv "docs/applications/foo.md" "docs/applications/archive/foo.md"
```

**正確寫法**

```bash
# 先 add 使 git 追蹤，再 mv（untracked 與已 commit 兩種前置狀態都安全）
git -C "$ROOT" add "docs/applications/foo.md"
git -C "$ROOT" mv "docs/applications/foo.md" "docs/applications/archive/foo.md"
```

兩種前置狀態的 porcelain 結果不同，但可預期、可被掃描規則正確分類：

- 前置為 **untracked** → add 後 mv：目的地顯示 `A  docs/applications/archive/foo.md`
- 前置為 **已 commit** → 顯示 rename `R  docs/applications/foo.md -> docs/applications/archive/foo.md`

### 陷阱二：macOS `core.quotepath=true` 把非 ASCII 檔名輸出成 octal escape

macOS 的 git 預設 `core.quotepath=true`，中文等非 ASCII 檔名在 porcelain 輸出成 `"\351\273\236..."` 形式；去除外層引號後仍是 octal 字串，拿去讀檔必然找不到。

**錯誤寫法**

```bash
git -C "$ROOT" status --porcelain -uall
# 輸出：?? "docs/applications/2026-07-07-\351\273\236...-application.md"
```

**正確寫法**

```bash
git -C "$ROOT" -c core.quotepath=false status --porcelain -uall
# 輸出：?? docs/applications/2026-07-07-電子書-application.md
```

以 `-c` 行內覆寫而非改使用者全域設定，腳本自帶正確行為、不依賴環境。

### 陷阱三：bash `[[ ]]` 的 glob `*` 可跨 `/`

bash `[[ string == pattern ]]` 中的 `*` **預設可匹配 `/`**（與檔名展開的 glob 不同），`docs/applications/*.md` 會同時匹配 `docs/applications/archive/foo.md`。

**錯誤寫法**

```bash
# archive/ 內的歸檔檔案也符合此 pattern，誤走頂層申請分支
if [[ "$path_part" == docs/applications/*.md ]]; then
  echo "NEW_APPLICATION:$path_part"
fi
```

**正確寫法**（雙重防護）

```bash
# 1. 子目錄分支必須最先評估（if/elif 順序即分類邊界）
if [[ "$path_part" == docs/applications/archive/* ]]; then
  continue
# 2. 頂層判斷以「去前綴後不含 /」二次驗證
elif [[ "$path_part" == docs/applications/*.md \
        && "${path_part#docs/applications/}" != */* ]]; then
  echo "NEW_APPLICATION:$path_part"
# 3. 其餘信箱內路徑 → tripwire（catch-all 是安全閥，照搬範例時勿省略）
elif [[ "$path_part" == docs/applications/* ]]; then
  echo "TRIPWIRE:$XY $path_part"
fi
```

### 陷阱四：`git mv` 不暫存 working tree 的內容修改（porcelain 呈現 `RM`）

對「已 commit 且 working tree 有未暫存修改」的檔案執行 `git mv`，只有 rename 進入
index，**內容修改仍留在 working tree**——porcelain 呈現 `RM old -> new`（rename
已 stage、修改未 stage），且 **staged 內容是舊版**。ADR 009 落地時實測發現：
`/handoff done` 的「Edit `status: done` → `git mv` 至 archive」序列若在 commit 前
不補 `git add`，commit 進 archive 的檔案仍是 `status: open` 的舊版，且因檔案已在
歸檔區、掃描豁免範圍內，此錯誤**不會自我暴露**。

**錯誤假設**

```bash
# 誤以為 git mv 會把當前內容一併 stage
sed -i '' 's/status: open/status: done/' docs/handoffs/foo.md   # Edit（未 stage）
git mv docs/handoffs/foo.md docs/handoffs/archive/foo.md
git commit -m "docs: 歸檔交接 foo.md"
git show HEAD:docs/handoffs/archive/foo.md   # → 仍是 status: open！
```

**正確寫法**

```bash
# commit 前對「搬移目的地路徑」git add，把內容修改帶入
git mv docs/handoffs/foo.md docs/handoffs/archive/foo.md
git add docs/handoffs/archive/foo.md
git commit -m "docs: 歸檔交接 foo.md"
```

掃描端配套：rename 豁免規則只驗路徑形狀、不看 XY 狀態碼，`RM` 行與 `R ` 行同樣
豁免（`scan-replies.sh` rename 分支的設計前提）。

## Why This Matters

| 陷阱 | 失敗模式 |
|------|---------|
| untracked `git mv` 失敗 | 歸檔指令非零退出、流程中斷，申請卡在頂層維持 `pending`，形成需人工介入的卡死狀態 |
| `core.quotepath` octal escape | 含中文檔名的申請被**靜默忽略**——路徑不符任何分類分支、整筆流走，tripwire 也不觸發，申請無聲消失 |
| glob 跨 `/` 誤匹配 | 已歸檔的檔案被再次報為新申請、重複進入審核；分類邊界（授權豁免 vs 異常）整體失效 |
| `git mv` 不暫存內容修改（`RM`） | 歸檔 commit 帶入的是舊版內容（如 `status` 未更新），檔案已入豁免範圍、錯誤永不自我暴露，狀態機語意靜默失效 |

四者的共同性質是**靜默或半靜默失敗**：不修不會立刻噴錯到使用者面前，而是讓資料流在某處無聲斷掉。

## When to Apply

- 任何以腳本解析 porcelain 輸出並以路徑讀寫檔案的情境，一律加 `-c core.quotepath=false`。
- 以 bash `[[ ]]` glob 對含子目錄的樹狀結構分類時：子目錄分支排在頂層分支之前，並以 `${path#prefix}` 是否含 `/` 二次驗證「頂層」。
- 需要 `git mv` 的檔案可能尚未 commit 時：一律先 `git add` 再 `git mv`，同時讓 porcelain 結果可預期（`A` 或 `R`）。
- 類比既有腳本前，先確認目錄深度假設一致——單層結構的 pattern 不可直接套用到有子目錄的結構。
- 「Edit 後 `git mv` 再 commit」的流程：commit 前一律對搬移目的地路徑 `git add`，勿假設 `git mv` 已暫存內容修改。

## Examples

最終實作落點（本 repo）：

- `skills/kunsu-inbox/scripts/scan-applications.sh` — 檔頭「分類規則」說明 glob 跨層陷阱與 if/elif 順序約束；掃描迴圈尾端的 `git -c core.quotepath=false status --porcelain -uall` 為陷阱二修法（`scan-replies.sh` 同日同修）。
- `skills/kunsu-init/SKILL.md` add-project 步驟④-4 — 「先 `git add` 再 `git mv`」的歸檔指令塊與原因註解（軍師範本 `kunsu-claude.md` 申請信箱協議同步載明）。
- 驗證：掃描腳本 14 個單元場景（含反向搬移、含空格與中文檔名）、端到端 11 場景全數通過。

## Related

- [ADR 006 — 申請信箱：例外授權自單一信箱擴為雙信箱](../../adr/2026-07-07-adr-candidate-006-application-inbox-dual-mailbox.md)：tripwire 分類規則的決策背景（本文不重述決策，只記實作陷阱）。
- [申請信箱實作計畫](../../plans/2026-07-07-001-feat-application-inbox-plan.md)：三個注意點的規劃脈絡（U1 Approach 與 KTD「tripwire 分類規則」）。
