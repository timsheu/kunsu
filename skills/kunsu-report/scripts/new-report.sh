#!/usr/bin/env bash
# new-report.sh — 在目標軍師的 docs/reports/ 建立一份主動上報檔
#
# 用法：
#   echo "<內文>" | new-report.sh <kunsu-root-abs-path> <標題> <角色代碼> [附加標籤（逗號分隔）]
#
# 位置參數：
#   $1  KUNSU_ROOT   目標軍師的絕對路徑
#   $2  TITLE        上報標題
#   $3  ROLE         角色代碼（from: 欄位，與 registry roles 字面一致）
#   $4  TAGS_RAW     附加標籤（逗號分隔，選填；預設僅含 report）
#
# 行為：
#   1. 驗證目標軍師的 docs/reports/ 存在（不存在即報錯退出，不建立目錄——
#      信箱由軍師端 scaffold 或遷移建立，子端不越權補建）
#   2. 檔名 = YYYY-MM-DD-<slug>-report.md；同日同名自動加 -2、-3...
#      （永遠新增新檔案，絕不覆寫既有上報——上報為 append-only 情報，同主題多次投遞合法）
#   3. 從 stdin 讀取內文，寫入 frontmatter（title/type/from/created/status/tags）與正文
#   4. stdout 最後一行印出上報檔完整路徑（供呼叫端回報）
#
# 授權範圍：本腳本只在 docs/reports/ 頂層新增一個檔案，不寫入任何其他位置。

set -euo pipefail

KUNSU_ROOT="${1:-}"
TITLE="${2:-}"
ROLE="${3:-}"          # 角色代碼（from:），與 registry roles 字面一致
TAGS_RAW="${4:-}"      # 附加標籤（逗號分隔，選填；空字串代表無附加標籤）

if [[ -z "$KUNSU_ROOT" || -z "$TITLE" || -z "$ROLE" ]]; then
  echo "錯誤：缺少必要參數" >&2
  echo "用法：new-report.sh <kunsu-root> <標題> <角色代碼> [附加標籤]" >&2
  exit 1
fi

REPORTS_DIR="$KUNSU_ROOT/docs/reports"
if [[ ! -d "$REPORTS_DIR" ]]; then
  echo "錯誤：目標軍師尚無上報信箱（$REPORTS_DIR 不存在）。" >&2
  echo "請先在軍師目錄的 session 執行 /kunsu-init add-project 完成遷移（補建上報信箱），再重新投遞。" >&2
  exit 1
fi

DATE="$(date +%F)"

# slug：保留中英數，空白與底線轉連字號，去除其餘標點，收斂連續連字號
slug="$(printf '%s' "$TITLE" \
  | tr ' _' '--' \
  | sed -E 's/[[:punct:]]//g; s/-+/-/g; s/^-+//; s/-+$//')"
[[ -z "$slug" ]] && slug="report"

# 防撞檔名迴圈：同日同名自動加 -2、-3（永遠新增，不覆寫）
base="$DATE-$slug-report"
file="$REPORTS_DIR/$base.md"
n=2
while [[ -e "$file" ]]; do
  file="$REPORTS_DIR/$base-$n.md"
  n=$((n + 1))
done

# tags 陣列：預設含 report，選填附加主題標籤
if [[ -n "$TAGS_RAW" ]]; then
  tags_yaml="[report, $(printf '%s' "$TAGS_RAW" | sed 's/,/, /g')]"
else
  tags_yaml="[report]"
fi

# 讀取 stdin 內文（可為空；set -e 下 cat 不會因 EOF 失敗）
BODY="$(cat || true)"

# 寫入上報檔：frontmatter 欄位順序為 title/type/from/created/status/tags
{
  printf -- '---\n'
  printf 'title: %s\n' "$TITLE"
  printf 'type: report\n'
  printf 'from: %s\n' "$ROLE"
  printf 'created: %s\n' "$DATE"
  printf 'status: submitted\n'
  printf 'tags: %s\n' "$tags_yaml"
  printf -- '---\n\n'
  printf '# %s\n\n' "$TITLE"
  if [[ -n "$BODY" ]]; then
    printf '%s\n' "$BODY"
  else
    printf '_（待補充）_\n'
  fi
} > "$file"

# stdout 最後一行為上報檔完整路徑（供呼叫端 SKILL.md 回報）
echo "$file"
