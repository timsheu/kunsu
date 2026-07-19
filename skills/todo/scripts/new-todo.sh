#!/usr/bin/env bash
# new-todo.sh — 在當前專案的 docs/todos/ 建立一個技術債 TODO 檔
#
# 用法：
#   echo "<內文>" | new-todo.sh "<標題>" [來源] [嚴重度]
#
# 行為：
#   1. 從當前目錄往上找最近的 CLAUDE.md/AGENTS.md 定位專案根（monorepo/submodule
#      場景下，實際專案常不等於 git 根目錄）；找不到才退回 git 根，最後退回當前目錄
#   2. 確保 docs/todos/ 存在
#   3. 檔名 = <slug>.md（不加日期前綴，比照 docs/solutions/ 慣例）；
#      同名視為衝突直接報錯，要求換更具體的標題
#   4. 寫入 Dataview 友善 frontmatter（status/date/source/severity）+ stdin 內文；
#      內文開頭若重複了與標題相同的 H1 會被去除，內文若已含「相關檔案」／
#      「待辦方向」段落標題則不再重複附加空白骨架
#   5. 印出最終檔案路徑（供呼叫端回報）

set -euo pipefail

TITLE="${1:-}"
SOURCE="${2:-manual}"
SEVERITY="${3:-low}"

if [[ -z "$TITLE" ]]; then
  echo "錯誤：缺少標題（第一個參數）" >&2
  echo "用法：new-todo.sh \"<標題>\" [來源] [嚴重度]" >&2
  exit 1
fi

case "$SEVERITY" in
  low|medium|high) ;;
  *)
    echo "錯誤：嚴重度須為 low / medium / high，收到：$SEVERITY" >&2
    exit 1
    ;;
esac

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

TODOS_DIR="$ROOT/docs/todos"
mkdir -p "$TODOS_DIR"

DATE="$(date +%F)"

# slug：保留中英數與既有連字號，空白與底線轉連字號，去除其餘標點，收斂連續連字號
# 既有連字號與底線先以控制字元 \001 佔位（[:punct:] 不含控制字元，不會被清除），
# 清完標點後再與空白一起轉回連字號——若先轉再清，[:punct:] 會把連字號一併清掉
slug="$(printf '%s' "$TITLE" \
  | tr -- '-_' '\001\001' \
  | sed -E 's/[[:punct:]]//g' \
  | tr ' \001' '--' \
  | sed -E 's/-+/-/g; s/^-+//; s/-+$//')"
[[ -z "$slug" ]] && slug="todo"

file="$TODOS_DIR/$slug.md"
if [[ -e "$file" ]]; then
  echo "錯誤：$file 已存在。TODO 檔名不加日期，請換一個更具體的標題避免撞名。" >&2
  exit 1
fi

# 讀取 stdin 內文（可為空）
BODY="$(cat || true)"

# 若呼叫端在內文開頭重複打了與標題相同的 H1，去除以免跟腳本自動產生的標題重複
first_line="${BODY%%$'\n'*}"
if [[ "$first_line" == "# $TITLE" ]]; then
  if [[ "$BODY" == *$'\n'* ]]; then
    BODY="${BODY#*$'\n'}"
    BODY="${BODY#$'\n'}"
  else
    BODY=""
  fi
fi

{
  printf -- '---\n'
  printf 'status: 未處理\n'
  printf 'date: %s\n' "$DATE"
  printf 'source: %s\n' "$SOURCE"
  printf 'severity: %s\n' "$SEVERITY"
  printf -- '---\n\n'
  printf '# %s\n\n' "$TITLE"
  if [[ -n "$BODY" ]]; then
    printf '%s\n' "$BODY"
  else
    printf '_（待補充）_\n'
  fi
  # 內文若已自帶這些段落標題，不再附加空白骨架造成重複
  if [[ "$BODY" != *"## 相關檔案"* ]]; then
    printf '\n## 相關檔案\n\n'
  fi
  if [[ "$BODY" != *"## 待辦方向"* ]]; then
    printf '\n## 待辦方向\n\n'
  fi
} > "$file"

echo "$file"
