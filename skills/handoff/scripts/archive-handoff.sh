#!/usr/bin/env bash
# archive-handoff.sh — /handoff done 步驟 5–7 的腳本化執行：
#   status Edit → untracked 前置 git add → 本體與回覆成對 git mv → git add 歸檔目的地
#
# 用法：
#   archive-handoff.sh "<交接檔名、slug 片段或路徑>" [更多交接…]
#
# 行為：
#   1. 逐一解析參數為 docs/handoffs/ 頂層交接檔——支援完整檔名、絕對／相對路徑、
#      足以唯一比對的檔名片段；已在 archive/ 者略過（供中途失敗後重跑），找不到或
#      多重比對時報錯並列出候選
#   2. 對每份交接依序：frontmatter status 改 done（python3，只動 frontmatter 區塊）
#      → untracked 者先 git add（untracked 檔直接 git mv 會失敗）→ git mv 本體至
#      archive/、對應回覆（<stem>-reply-*.md）至 archive/replies/ → git add 歸檔後
#      本體路徑（git mv 不會暫存 working tree 的內容修改，status Edit 靠這步帶入）
#   3. 所有 git add 僅限本流程產出的具體路徑，絕不 -A、不整目錄打包
#   4. 不 commit：stdout 印出一行待確認的 git commit 指令（ADR 009 經使用者確認後
#      執行；todo 一併收尾／轉出時依 SKILL done 步驟 9 擴充訊息與 add 範圍）
#   5. 暫存區含 docs/handoffs/、docs/todos/ 之外的路徑時警告——該路徑會被無
#      pathspec 的 commit 一併帶入，正是本腳本要杜絕的「commit 多了東西」風險
#   6. 中途失敗不回滾：已完成的搬移保留，git status 檢視現況後重跑即續
#
# 來源事故（2026-08-29 ebook 軍師）：手動歸檔以 git add -A 夾帶 16 份未讀回覆，
# 靜默清除「未 commit 即未處理」狀態訊號。歸檔的 git 編排細節（pathspec rename
# 兩側、add 範圍）是該被計算而非被記憶的約束，故收進腳本。

set -euo pipefail

MUTATION_STARTED=0
on_err() {
  if [[ "$MUTATION_STARTED" -eq 1 ]]; then
    echo "✗ 歸檔中途失敗：已完成的搬移不回滾。請以 git status 檢視現況後重跑本腳本（已在 archive/ 的傳入項會自動略過）。" >&2
  fi
}
trap on_err ERR

if [[ $# -lt 1 ]]; then
  echo "錯誤：缺少交接檔參數" >&2
  echo "用法：archive-handoff.sh \"<交接檔名、slug 片段或路徑>\" [更多交接…]" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "錯誤：需要 python3（frontmatter status 編輯）；不可用時請依 SKILL done 步驟 5–7 手動執行" >&2
  exit 1
}

# 定位專案根：與 new-handoff.sh 同一套——優先往上找最近的 CLAUDE.md/AGENTS.md
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

shopt -s nullglob

H_DIR=""          # 全部交接檔必須同屬一個 docs/handoffs/（單一 commit 訊息）
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
    abs="$(cd "$(dirname "$arg")" 2>/dev/null && pwd)/$(basename "$arg")" || true
    if [[ -z "$abs" || ! -f "$abs" ]]; then
      echo "錯誤：找不到檔案「${arg}」" >&2
      return 1
    fi
    if [[ "$abs" == */docs/handoffs/archive/* ]]; then
      resolved_archived="$abs"
      return 0
    fi
    local rel="${abs##*/docs/handoffs/}"
    if [[ "$abs" != */docs/handoffs/*.md || "$rel" == */* ]]; then
      echo "錯誤：「${arg}」不是 docs/handoffs/ 頂層交接檔" >&2
      return 1
    fi
    resolved="$abs"
    return 0
  fi

  # 檔名／片段形式：在專案根的 docs/handoffs/ 頂層搜尋
  local hd="$ROOT/docs/handoffs"
  if [[ ! -d "$hd" ]]; then
    echo "錯誤：$hd 不存在（請於軍師／發起方 repo 內執行，或改傳交接檔路徑）" >&2
    return 1
  fi
  local name="${arg%.md}"
  if [[ -f "$hd/$name.md" ]]; then
    resolved="$hd/$name.md"
    return 0
  fi
  local hits=()
  local f
  for f in "$hd"/*"$name"*.md; do
    hits+=("$f")
  done
  if [[ ${#hits[@]} -eq 1 ]]; then
    resolved="${hits[0]}"
    return 0
  elif [[ ${#hits[@]} -gt 1 ]]; then
    echo "錯誤：「${arg}」比對到多份交接，請給更精確的片段或完整檔名：" >&2
    for f in "${hits[@]}"; do echo "  - $(basename "$f")" >&2; done
    return 1
  fi
  # 頂層零命中 → 查 archive/（重跑場景：前次已搬移成功）
  for f in "$hd/archive/"*"$name"*.md; do
    resolved_archived="$f"
    return 0
  done
  echo "錯誤：docs/handoffs/ 頂層與 archive/ 均找不到「${arg}」" >&2
  return 1
}

for arg in "$@"; do
  resolve_arg "$arg"
  if [[ -n "$resolved_archived" ]]; then
    SKIPPED+=("$(basename "$resolved_archived")")
    continue
  fi
  fdir="$(dirname "$resolved")"
  if [[ -z "$H_DIR" ]]; then
    H_DIR="$fdir"
  elif [[ "$H_DIR" != "$fdir" ]]; then
    echo "錯誤：交接檔分屬不同 docs/handoffs/（${H_DIR} 與 ${fdir}），請分批執行" >&2
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

GITROOT="$(git -C "$H_DIR" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "錯誤：$H_DIR 不在 git 儲存庫內" >&2
  exit 1
}

ARCHIVE_DIR="$H_DIR/archive"
mkdir -p "$ARCHIVE_DIR/replies"

names=()
MUTATION_STARTED=1
for f in "${FILES[@]}"; do
  base="$(basename "$f")"
  stem="$(basename "$f" .md)"

  # frontmatter status → done（只動 frontmatter 區塊，內文一字不碰——Invariant #5）
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
fm2 = re.sub(r"(?m)^status:.*$", "status: done", fm, count=1)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(text[: m.start(1)] + fm2 + text[m.end(1) :])
PYEOF

  # untracked 前置：?? 狀態直接 git mv 會以 not under version control 失敗
  st="$(git -C "$GITROOT" status --porcelain -- "$f" | head -1)"
  if [[ "${st:0:2}" == "??" ]]; then
    git -C "$GITROOT" add -- "$f"
  fi

  git -C "$GITROOT" mv "$f" "$ARCHIVE_DIR/$base"
  # git mv 不會暫存 working tree 的內容修改（porcelain 呈現 RM、staged 為舊版），
  # status Edit 靠這一步帶入暫存
  git -C "$GITROOT" add -- "$ARCHIVE_DIR/$base"

  rcount=0
  for r in "$H_DIR/replies/$stem-reply-"*.md; do
    rst="$(git -C "$GITROOT" status --porcelain -- "$r" | head -1)"
    if [[ "${rst:0:2}" == "??" ]]; then
      git -C "$GITROOT" add -- "$r"
    fi
    git -C "$GITROOT" mv "$r" "$ARCHIVE_DIR/replies/$(basename "$r")"
    rcount=$((rcount + 1))
  done

  echo "✓ 歸檔 ${base}（回覆 ${rcount} 份）" >&2
  names+=("$base")
done

# 暫存區範圍核對：本流程與 todo 收尾之外的已暫存路徑會被無 pathspec 的 commit
# 一併帶入——列出供人工裁決，不擅自 unstage
outside="$(git -C "$GITROOT" diff --cached --name-only | grep -v '^docs/handoffs/' | grep -v '^docs/todos/' || true)"
if [[ -n "$outside" ]]; then
  echo "⚠ 暫存區含本流程（docs/handoffs/、docs/todos/）之外的路徑，commit 前請先處理或確認確屬本次收尾：" >&2
  while IFS= read -r p; do echo "  - $p" >&2; done <<< "$outside"
fi

msg="docs: 歸檔交接 $(IFS=、; echo "${names[*]}")"
echo "git commit -m \"$msg\""
echo "ℹ 已暫存本流程全部路徑（僅具體路徑，未用 -A）；尚未 commit——請經使用者確認後執行上列指令（ADR 009），todo 一併收尾／轉出時依 SKILL done 步驟 9 擴充訊息與 git add 範圍" >&2
echo "ℹ done 收尾查核不隨腳本豁免：逐項驗收、沉澱訊號、反向路由、來源 todo、殘項清點、斷言自查——見 handoff SKILL.md done 段" >&2
