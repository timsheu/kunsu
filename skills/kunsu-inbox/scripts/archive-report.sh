#!/usr/bin/env bash
# archive-report.sh — 上報歸檔四步驟（1）–（3）的腳本化執行：
#   status Edit（submitted→archived）→ untracked 前置 git add → git mv 至 archive/
#   → git add 歸檔目的地
#
# 用法：
#   archive-report.sh "<上報檔名、slug 片段或路徑>" [更多上報…]
#
# 行為：
#   1. 逐一解析參數為 docs/reports/ 頂層上報檔——支援完整檔名、絕對／相對路徑、
#      足以唯一比對的檔名片段；已在 archive/ 者略過（供中途失敗後重跑），找不到或
#      多重比對時報錯並列出候選
#   2. 對每份上報依序：frontmatter status 改 archived（python3，只動 frontmatter
#      區塊；已是 archived 的頂層殘留冪等重做、續行搬移）→ untracked 者先 git add
#      （untracked 檔直接 git mv 會失敗）→ git mv 至 archive/ → git add 歸檔後
#      目的地路徑（git mv 不會暫存 working tree 的內容修改，status Edit 靠這步帶入）
#   3. 所有 git add 僅限本流程產出的具體路徑，絕不 -A、不整目錄打包
#   4. 不 commit：stdout 印出一行帶兩形 pathspec 的待確認 git commit 指令
#      （ADR 009 經使用者確認後執行；ADR 018 宣告範圍契約——tracked rename 成對
#      列 src＋dst、untracked 來源（上報常態）僅列 dst）
#   5. 暫存區含 docs/reports/ 之外的路徑時警告——不在本次 commit 宣告範圍內
#      不會被帶入，列出供人工裁決是否另行處理（上報歸檔無 todo 聯動，排除清單
#      僅 docs/reports/ 單一前綴，不比照 archive-handoff.sh 放寬）
#   6. 中途失敗不回滾：已完成的搬移保留，git status 檢視現況後重跑即續
#
# 來源事故（2026-08-31 ebook 軍師）：上報歸檔的 git mv 先留 index 殘留，隨後
# 「建立交接」的無 pathspec commit 把殘留一併吞入，同一 session 重犯兩次——
# 上報歸檔是 v0.18.0 歸檔腳本化未覆蓋的流程，git 編排自此同樣該被計算而非被記憶。

set -euo pipefail

MUTATION_STARTED=0
on_err() {
  if [[ "$MUTATION_STARTED" -eq 1 ]]; then
    echo "✗ 歸檔中途失敗：已完成的搬移不回滾。請以 git status 檢視現況後重跑本腳本（已在 archive/ 的傳入項會自動略過）。" >&2
    echo "ℹ 完成前 /kunsu-inbox 對中間態會誤報：已 commit 上報 Edit 後的 \` M\` 觸發 tripwire、untracked 上報仍列為新上報——補跑收斂即回復，不是外部入侵。" >&2
  fi
}
trap on_err ERR

if [[ $# -lt 1 ]]; then
  echo "錯誤：缺少上報檔參數" >&2
  echo "用法：archive-report.sh \"<上報檔名、slug 片段或路徑>\" [更多上報…]" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "錯誤：需要 python3（frontmatter status 編輯）；不可用時請依軍師 CLAUDE.md 上報信箱協議四步驟手動執行" >&2
  exit 1
}

# 定位專案根：與 archive-handoff.sh 同一套——優先往上找最近的 CLAUDE.md/AGENTS.md
#（走到家目錄即停，不把家目錄當專案根），其次 git 根，最後當前目錄
ROOT=""
dir="$(pwd)"
while [[ "$dir" != "/" && "$dir" != "${HOME:-}" ]]; do
  if [[ -f "$dir/CLAUDE.md" || -f "$dir/AGENTS.md" ]]; then
    ROOT="$dir"
    break
  fi
  dir="$(dirname "$dir")"
done
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
# 實體路徑正規化：symlink 佈局（如 macOS /tmp）下，邏輯路徑與 git 根的實體
# 路徑不一致會使相對前綴剝除失效——tracked 檔被誤判 untracked、pathspec 拆半
ROOT="$(cd "$ROOT" && pwd -P)"

shopt -s nullglob

R_DIR=""          # 全部上報檔必須同屬一個 docs/reports/（單一 commit 訊息）
FILES=()          # 解析成功、待歸檔的絕對路徑
SKIPPED=()        # 已在 archive/ 的略過項（檔名）

# 解析單一參數 → 絕對路徑存入 resolved（頂層檔）或 resolved_archived（已歸檔）
resolve_arg() {
  local arg="$1"
  resolved=""
  resolved_archived=""

  if [[ "$arg" == */* ]]; then
    # 路徑形式：直接解析為絕對路徑
    local abs
    abs="$(cd "$(dirname "$arg")" 2>/dev/null && pwd -P)/$(basename "$arg")" || true
    if [[ -z "$abs" || ! -f "$abs" ]]; then
      echo "錯誤：找不到檔案「${arg}」" >&2
      return 1
    fi
    if [[ "$abs" == */docs/reports/archive/* ]]; then
      resolved_archived="$abs"
      return 0
    fi
    local rel="${abs##*/docs/reports/}"
    if [[ "$abs" != */docs/reports/*.md || "$rel" == */* ]]; then
      echo "錯誤：「${arg}」不是 docs/reports/ 頂層上報檔" >&2
      return 1
    fi
    resolved="$abs"
    return 0
  fi

  # 檔名／片段形式：在專案根的 docs/reports/ 頂層搜尋
  local rd="$ROOT/docs/reports"
  if [[ ! -d "$rd" ]]; then
    echo "錯誤：$rd 不存在（請於軍師 repo 內執行，或改傳上報檔路徑）" >&2
    return 1
  fi
  local name="${arg%.md}"
  if [[ -f "$rd/$name.md" ]]; then
    resolved="$rd/$name.md"
    return 0
  fi
  local hits=()
  local f
  for f in "$rd"/*"$name"*.md; do
    hits+=("$f")
  done
  if [[ ${#hits[@]} -eq 1 ]]; then
    resolved="${hits[0]}"
    return 0
  elif [[ ${#hits[@]} -gt 1 ]]; then
    echo "錯誤：「${arg}」比對到多份上報，請給更精確的片段或完整檔名：" >&2
    for f in "${hits[@]}"; do echo "  - $(basename "$f")" >&2; done
    return 1
  fi
  # 頂層零命中 → 查 archive/（重跑場景：前次已搬移成功）
  for f in "$rd/archive/"*"$name"*.md; do
    resolved_archived="$f"
    return 0
  done
  echo "錯誤：docs/reports/ 頂層與 archive/ 均找不到「${arg}」" >&2
  return 1
}

for arg in "$@"; do
  resolve_arg "$arg"
  if [[ -n "$resolved_archived" ]]; then
    SKIPPED+=("$(basename "$resolved_archived")")
    continue
  fi
  fdir="$(dirname "$resolved")"
  if [[ -z "$R_DIR" ]]; then
    R_DIR="$fdir"
  elif [[ "$R_DIR" != "$fdir" ]]; then
    echo "錯誤：上報檔分屬不同 docs/reports/（${R_DIR} 與 ${fdir}），請分批執行" >&2
    exit 1
  fi
  FILES+=("$resolved")
done

if [[ ${#SKIPPED[@]} -gt 0 ]]; then
  for name in "${SKIPPED[@]}"; do
    echo "ℹ 已在 archive/，略過：${name}" >&2
  done
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "ℹ 無待歸檔項（傳入項均已在 archive/），未執行任何操作" >&2
  exit 0
fi

GITROOT="$(git -C "$R_DIR" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "錯誤：$R_DIR 不在 git 儲存庫內" >&2
  exit 1
}

ARCHIVE_DIR="$R_DIR/archive"
mkdir -p "$ARCHIVE_DIR"

names=()
PATHSPECS=()
MUTATION_STARTED=1
for f in "${FILES[@]}"; do
  base="$(basename "$f")"

  # frontmatter status → archived（只動 frontmatter 區塊；已是 archived 的頂層
  # 殘留冪等重做、續行搬移——與 add-project 對申請殘留的互動補完是刻意差異：
  # 腳本情境使用者已下達歸檔意圖）
  python3 - "$f" <<'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    text = fh.read()
m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
if not m:
    sys.exit(f"frontmatter 缺失或格式異常：{path}")
fm = m.group(1)
if re.search(r"(?m)^status:", fm) is None:
    sys.exit(f"frontmatter 無 status 欄位：{path}")
fm2 = re.sub(r"(?m)^status:.*$", "status: archived", fm, count=1)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(text[: m.start(1)] + fm2 + text[m.end(1) :])
PYEOF

  # untracked 前置：?? 狀態直接 git mv 會以 not under version control 失敗
  st="$(git -C "$GITROOT" status --porcelain -- "$f" | head -1)"
  if [[ "${st:0:2}" == "??" ]]; then
    git -C "$GITROOT" add -- "$f"
  fi
  # tracked 與否以 HEAD 存在性判定——已 add 未 commit（porcelain `A `）的來源
  # 同樣不在 HEAD，成對列入 pathspec 會以不匹配失敗，須與 `??` 一樣僅列目的地
  rel="${f#"$GITROOT"/}"
  body_tracked=0
  if git -C "$GITROOT" cat-file -e "HEAD:$rel" 2>/dev/null; then
    body_tracked=1
  fi

  git -C "$GITROOT" mv "$f" "$ARCHIVE_DIR/$base"
  # git mv 不會暫存 working tree 的內容修改（porcelain 呈現 RM、staged 為舊版），
  # status Edit 靠這一步帶入暫存
  git -C "$GITROOT" add -- "$ARCHIVE_DIR/$base"
  # commit pathspec 兩形（ADR 018）：tracked rename 成對列 src＋dst（只列單邊會把
  # rename 拆半）；untracked 來源（上報常態、A 形狀）僅列 dst——src 從未入 git
  if [[ "$body_tracked" -eq 1 ]]; then
    PATHSPECS+=("$f")
  fi
  PATHSPECS+=("$ARCHIVE_DIR/$base")

  echo "✓ 歸檔 ${base}" >&2
  names+=("$base")
done

# 暫存區範圍核對：pathspec commit 只收斂宣告範圍，範圍外暫存不會被帶入——
# 仍列出供人工裁決是否另行處理，不擅自 unstage（前綴以 R_DIR 相對 GITROOT 計算，
# 專案根深於 git 根的 monorepo 佈局下才不會把自己剛暫存的歸檔檔誤報為外部路徑）
mail_rel="${R_DIR#"$GITROOT"/}"
outside="$(git -C "$GITROOT" diff --cached --name-only | grep -v "^${mail_rel}/" || true)"
if [[ -n "$outside" ]]; then
  echo "⚠ 暫存區含本流程（${mail_rel}/）之外的已暫存路徑——不在本次 commit 宣告範圍內、不會被帶入，請確認是否需另行處理：" >&2
  while IFS= read -r p; do echo "  - $p" >&2; done <<< "$outside"
fi

msg="docs: 歸檔上報 $(IFS=、; echo "${names[*]}")"
quoted=""
for p in "${PATHSPECS[@]}"; do quoted+=" \"$p\""; done
echo "git commit -m \"$msg\" --$quoted"
staged_count="$(git -C "$GITROOT" diff --cached --name-only | wc -l | tr -d ' ')"
echo "ℹ index 現含 ${staged_count} 筆暫存路徑；上列指令僅收斂 pathspec 宣告範圍（兩形：tracked rename 成對、untracked 僅目的地，ADR 018），範圍外暫存不受影響" >&2
echo "ℹ 尚未 commit——請經 AskUserQuestion 確認後執行上列指令（ADR 009 上報歸檔第（4）步）；本腳本僅完成步驟（1）–（3）與目的地暫存，審閱與分流義務不因腳本而豁免" >&2
