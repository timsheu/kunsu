#!/usr/bin/env bash
# new-application.sh — 在目標軍師的 docs/applications/ 建立一份申請加入的申請檔
#
# 用法：
#   new-application.sh <kunsu-root-abs-path> <顯示名稱> <子專案絕對路徑> \
#                      <提議角色代碼> [角色說明] [環境限制] [self_verify(y/n)] [技術棧摘要]
#
# 行為：
#   1. 驗證目標軍師的 docs/applications/ 存在（不存在即報錯退出，不建立目錄——
#      信箱由軍師端 scaffold 或遷移建立，子端不越權補建）
#   2. 檔名 = YYYY-MM-DD-<slug>-application.md；同日同名自動加 -2、-3...
#      （永遠新增新檔案，絕不覆寫既有申請——含子端自己先前投遞的版本）
#   3. 寫入 Dataview 友善 frontmatter（type: kunsu-application、status: pending）
#   4. 印出最終檔案路徑（供呼叫端回報）
#
# 授權範圍：本腳本只在 docs/applications/ 頂層新增一個檔案，不寫入任何其他位置。

set -euo pipefail

KUNSU_ROOT="${1:-}"
NAME="${2:-}"
SUB_PATH="${3:-}"
ROLE="${4:-}"            # 提議角色代碼（短、kebab-case，即 handoff to:）
ROLE_DESC="${5:-無}"     # 角色說明（選填，整句職責，display-only）
CONSTRAINTS="${6:-無}"
SELF_VERIFY="${7:-n}"
STACK="${8:-待補充}"

if [[ -z "$KUNSU_ROOT" || -z "$NAME" || -z "$SUB_PATH" || -z "$ROLE" ]]; then
  echo "錯誤：缺少必要參數" >&2
  echo "用法：new-application.sh <kunsu-root> <顯示名稱> <子專案路徑> <提議角色代碼> [角色說明] [環境限制] [y/n] [技術棧]" >&2
  exit 1
fi

APPS_DIR="$KUNSU_ROOT/docs/applications"
if [[ ! -d "$APPS_DIR" ]]; then
  echo "錯誤：目標軍師尚無申請信箱（$APPS_DIR 不存在）。" >&2
  echo "請先於軍師目錄的 session 執行 /kunsu-init add-project 完成遷移（補建申請信箱），再重新投遞。" >&2
  exit 1
fi

DATE="$(date +%F)"

# slug：保留中英數，空白與底線轉連字號，去除其餘標點，收斂連續連字號
slug="$(printf '%s' "$NAME" \
  | tr ' _' '--' \
  | sed -E 's/[[:punct:]]//g; s/-+/-/g; s/^-+//; s/-+$//')"
[[ -z "$slug" ]] && slug="project"

base="$DATE-$slug-application"
file="$APPS_DIR/$base.md"
n=2
while [[ -e "$file" ]]; do
  file="$APPS_DIR/$base-$n.md"
  n=$((n + 1))
done

{
  printf -- '---\n'
  printf 'title: %s — 申請加入\n' "$NAME"
  printf 'type: kunsu-application\n'
  printf 'name: %s\n' "$NAME"
  printf 'path: %s\n' "$SUB_PATH"
  printf 'proposed_role: %s\n' "$ROLE"
  printf 'role_desc: %s\n' "$ROLE_DESC"
  printf 'constraints: %s\n' "$CONSTRAINTS"
  printf 'self_verify: %s\n' "$SELF_VERIFY"
  printf 'stack: %s\n' "$STACK"
  printf 'created: %s\n' "$DATE"
  printf 'status: pending\n'
  printf -- '---\n\n'
  printf '# %s — 申請加入\n\n' "$NAME"
  printf '| 欄位 | 內容 |\n'
  printf '|------|------|\n'
  printf '| 子專案路徑 | `%s` |\n' "$SUB_PATH"
  printf '| 提議角色代碼 | %s |\n' "$ROLE"
  printf '| 角色說明 | %s |\n' "$ROLE_DESC"
  printf '| 環境限制 | %s |\n' "$CONSTRAINTS"
  printf '| 能否自我驗證 | %s |\n' "$SELF_VERIFY"
  printf '| 技術棧 | %s |\n' "$STACK"
  printf '\n> 本檔案為定案快照，待審期間任何人不得編輯。審核由軍師 session 以 `/kunsu-init add-project` 執行；\n'
  printf '> 核准當下才寫入軍師 CLAUDE.md 關聯專案表與全域註冊表，處理完由軍師歸檔至 `archive/`。\n'
} > "$file"

echo "$file"
