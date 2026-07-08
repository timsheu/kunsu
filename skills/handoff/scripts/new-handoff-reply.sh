#!/usr/bin/env bash
# new-handoff-reply.sh — 針對一份既有交接文件，在 docs/handoffs/replies/ 建立一則
# 獨立回覆檔案（回覆信箱模式：交接文件本體永遠不被編輯，回覆一律是新檔案）
#
# 用法：
#   echo "<回覆內文>" | new-handoff-reply.sh "<原交接檔案 slug 或路徑>" [from]
#
# 行為：
#   1. 從當前目錄往上找最近的 CLAUDE.md/AGENTS.md 定位專案根；找不到才退回
#      git 根，最後退回當前目錄（與 new-handoff.sh 一致）
#   2. 定位原交接文件：可傳完整路徑，或 docs/handoffs/（含 archive）底下
#      足以唯一比對的檔名片段；找不到或有多筆符合會報錯並列出候選
#   3. 讀出原交接文件 frontmatter 的 title／from，推算回覆的
#      from（預設 = 原文件的 to，可用第二參數覆寫）／to（= 原文件的 from）
#   4. 確保 docs/handoffs/replies/ 存在
#   5. 檔名 = {原交接檔名}-reply-YYYY-MM-DD.md；同日同名自動加 -2、-3...
#      （append-only，不覆寫前次回覆）
#   6. 寫入 Dataview 友善 frontmatter（from/to/in_reply_to/status）+ stdin 內文
#   7. 印出最終檔案路徑（供呼叫端回報）

set -euo pipefail

ORIG_REF="${1:-}"
FROM_OVERRIDE="${2:-}"

if [[ -z "$ORIG_REF" ]]; then
  echo "錯誤：缺少原交接檔案 slug 或路徑（第一個參數）" >&2
  echo "用法：new-handoff-reply.sh \"<原交接檔案 slug 或路徑>\" [from]" >&2
  exit 1
fi

# 定位專案根：優先往上找最近的 CLAUDE.md/AGENTS.md，其次 git 根，最後當前目錄
ROOT=""
dir="$(pwd)"
while [[ "$dir" != "/" ]]; do
  if [[ -f "$dir/CLAUDE.md" || -f "$dir/AGENTS.md" ]]; then
    ROOT="$dir"
    break
  fi
  dir="$(dirname "$dir")"
done
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

HANDOFFS_DIR="$ROOT/docs/handoffs"
REPLIES_DIR="$HANDOFFS_DIR/replies"

# 定位原交接文件
ORIG_FILE=""
if [[ -f "$ORIG_REF" ]]; then
  ORIG_FILE="$ORIG_REF"
else
  matches=()
  while IFS= read -r -d '' f; do
    matches+=("$f")
  done < <(find "$HANDOFFS_DIR" "$HANDOFFS_DIR/archive" -maxdepth 1 -type f -name "*${ORIG_REF}*.md" -print0 2>/dev/null)

  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "錯誤：找不到符合 \"$ORIG_REF\" 的交接文件（已搜尋 docs/handoffs/ 與 docs/handoffs/archive/）" >&2
    exit 1
  elif [[ ${#matches[@]} -gt 1 ]]; then
    echo "錯誤：找到多筆符合 \"$ORIG_REF\" 的交接文件，請給更精確的片段或完整路徑：" >&2
    printf '  - %s\n' "${matches[@]}" >&2
    exit 1
  fi
  ORIG_FILE="${matches[0]}"
fi

ORIG_BASENAME="$(basename "$ORIG_FILE")"

# 讀取原交接文件 frontmatter（title/from/to）
ORIG_TITLE="$(sed -n 's/^title: *//p' "$ORIG_FILE" | head -1)"
ORIG_FROM="$(sed -n 's/^from: *//p' "$ORIG_FILE" | head -1)"
ORIG_TO="$(sed -n 's/^to: *//p' "$ORIG_FILE" | head -1)"

if [[ -z "$ORIG_TITLE" || -z "$ORIG_FROM" || -z "$ORIG_TO" ]]; then
  echo "錯誤：無法從 $ORIG_FILE 讀出完整的 title/from/to frontmatter" >&2
  exit 1
fi

REPLY_FROM="${FROM_OVERRIDE:-$ORIG_TO}"
REPLY_TO="$ORIG_FROM"

mkdir -p "$REPLIES_DIR"

DATE="$(date +%F)"
ORIG_BASE="${ORIG_BASENAME%.md}"

base="$ORIG_BASE-reply-$DATE"
file="$REPLIES_DIR/$base.md"
n=2
while [[ -e "$file" ]]; do
  file="$REPLIES_DIR/$base-$n.md"
  n=$((n + 1))
done

# 讀取 stdin 內文（可為空）
BODY="$(cat || true)"

{
  printf -- '---\n'
  printf 'title: %s — 回覆\n' "$ORIG_TITLE"
  printf 'type: handoff-reply\n'
  printf 'from: %s\n' "$REPLY_FROM"
  printf 'to: %s\n' "$REPLY_TO"
  printf 'in_reply_to: %s\n' "$ORIG_BASENAME"
  printf 'created: %s\n' "$DATE"
  printf 'status: submitted\n'
  printf -- '---\n\n'
  printf '# %s — 回覆\n\n' "$ORIG_TITLE"
  if [[ -n "$BODY" ]]; then
    printf '%s\n' "$BODY"
  else
    printf '_（待補充）_\n'
  fi
} > "$file"

echo "$file"
