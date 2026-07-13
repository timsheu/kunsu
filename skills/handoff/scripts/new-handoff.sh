#!/usr/bin/env bash
# new-handoff.sh — 在當前專案的 docs/handoffs/ 建立一份跨 session／跨角色交接文件
#
# 用法：
#   echo "<內文>" | new-handoff.sh "<標題>" [from] [to] [tag1,tag2,...]
#
# 行為：
#   1. 從當前目錄往上找最近的 CLAUDE.md/AGENTS.md 定位專案根（monorepo/submodule
#      場景下，實際專案常不等於 git 根目錄）；找不到才退回 git 根，最後退回當前目錄
#   2. 確保 docs/handoffs/ 存在
#   3. 檔名 = YYYY-MM-DD-<slug>.md；同日同名自動加 -2、-3...
#   4. 寫入 Dataview 友善 frontmatter（from/to/status）+ stdin 內文 +
#      「回覆方式」定型段落（指示接手方去 docs/handoffs/replies/ 建新檔回覆，
#      不要編輯本檔案）；內文開頭若重複了與標題相同的 H1 會被去除，內文若已含
#      背景／現況分析／問題／期望交付／相關檔案等段落標題則不再重複附加空白骨架
#   5. 印出最終檔案路徑（供呼叫端回報）

set -euo pipefail

TITLE="${1:-}"
FROM="${2:-app}"
TO="${3:-backend}"
TAGS_RAW="${4:-}"

if [[ -z "$TITLE" ]]; then
  echo "錯誤：缺少標題（第一個參數）" >&2
  echo "用法：new-handoff.sh \"<標題>\" [from] [to] [tag1,tag2,...]" >&2
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
mkdir -p "$HANDOFFS_DIR"

DATE="$(date +%F)"

# slug：保留中英數，空白與底線轉連字號，去除其餘標點，收斂連續連字號
slug="$(printf '%s' "$TITLE" \
  | tr ' _' '--' \
  | sed -E 's/[[:punct:]]//g; s/-+/-/g; s/^-+//; s/-+$//')"
[[ -z "$slug" ]] && slug="handoff"

base="$DATE-$slug"
file="$HANDOFFS_DIR/$base.md"
n=2
while [[ -e "$file" ]]; do
  file="$HANDOFFS_DIR/$base-$n.md"
  n=$((n + 1))
done
final_base="$(basename "$file" .md)"

# tags 陣列：預設含 handoff
if [[ -n "$TAGS_RAW" ]]; then
  tags_yaml="[handoff, $(printf '%s' "$TAGS_RAW" | sed 's/,/, /g')]"
else
  tags_yaml="[handoff]"
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
  printf 'title: %s\n' "$TITLE"
  printf 'type: handoff\n'
  printf 'status: open\n'
  printf 'from: %s\n' "$FROM"
  printf 'to: %s\n' "$TO"
  printf 'created: %s\n' "$DATE"
  printf 'tags: %s\n' "$tags_yaml"
  printf -- '---\n\n'
  printf '# %s\n\n' "$TITLE"
  if [[ -n "$BODY" ]]; then
    printf '%s\n' "$BODY"
  else
    printf '_（待補充）_\n'
  fi
  # 內文若已自帶這些段落標題，不再附加空白骨架造成重複
  if [[ "$BODY" != *"## 背景 / 目標"* ]]; then
    printf '\n## 背景 / 目標\n\n'
  fi
  if [[ "$BODY" != *"## 現況分析"* ]]; then
    printf '\n## 現況分析（已知事實）\n\n'
  fi
  if [[ "$BODY" != *"## 需要你研究"* ]]; then
    printf '\n## 需要你研究／決策的問題\n\n'
  fi
  if [[ "$BODY" != *"## 期望交付"* ]]; then
    printf '\n## 期望交付\n\n'
  fi
  if [[ "$BODY" != *"## 相關檔案 / 連結"* ]]; then
    printf '\n## 相關檔案 / 連結\n\n'
  fi
  printf -- '\n---\n\n'
  printf '## 回覆方式（請讀，不要編輯本檔案）\n\n'
  printf '本檔案是定案快照，完成後**請勿在此檔案內回填任何內容**。請執行以下指令建立回覆檔案：\n\n'
  printf '    /handoff reply %s\n\n' "$final_base"
  printf '或直接於下列路徑新增檔案（`{YYYY-MM-DD}` 為回覆當天日期；分階段回報多次時每次建立新檔案，不要覆寫前一份回覆）：\n\n'
  printf '    docs/handoffs/replies/%s-reply-{YYYY-MM-DD}.md\n\n' "$final_base"
  printf '新檔案請以下列 frontmatter 開頭：\n\n'
  printf -- '```yaml\n'
  printf -- '---\n'
  printf 'title: %s — 回覆\n' "$TITLE"
  printf 'type: handoff-reply\n'
  printf 'from: %s\n' "$TO"
  printf 'to: %s\n' "$FROM"
  printf 'in_reply_to: %s.md\n' "$final_base"
  printf 'created: YYYY-MM-DD\n'
  printf 'status: submitted\n'
  printf -- '---\n'
  printf -- '```\n'
  printf '\n回覆檔 `status` 值：`submitted`（預設，已完成待發起方確認）／`partial`（部分完成，後續會再回報）／`blocked`（卡關）／`done`（已結案——**由發起方經 `/handoff done` 對交接本體執行，接手方回覆請勿自標**；自標會使此交接從 `/kunsu-inbox` 與軍師沙盤消失，本體卻仍留在頂層未歸檔）。另可加選填欄位 `verify:` 標注驗收方式——`needs-deploy`（需上線測試）／`testable-now`（馬上可測）／`needs-device`（需實機測試）或自由字串，無明確驗收需求則省略。\n'
} > "$file"

echo "$file"
