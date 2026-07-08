#!/usr/bin/env bash
# scan-replies.sh — 掃描軍師 docs/handoffs/replies/ 中未 commit 的新回覆檔案
# 同時執行 tripwire 核對：docs/handoffs/（排除 replies/）下是否有意外變更
#
# 用法：scan-replies.sh <kunsu-root-abs-path>
#
# 輸出（stdout，每行一筆）：
#   NEW_REPLY:<相對路徑>         新回覆（.md 檔案，untracked 或 index 新增）
#   TRIPWIRE:<XY> <相對路徑>     意外變更（docs/handoffs/ 下非 replies/ 的任何狀態變更）
#
# exit code：
#   0 — 正常完成（含零回覆、零 tripwire）
#   1 — 參數錯誤或非 git repo 根
#   2 — tripwire 觸發（docs/handoffs/ 下有意外未 commit 變更）
#
# 偵測條件：
#   新回覆  = 路徑在 docs/handoffs/replies/*.md，且
#             行首兩字元為 ?? (untracked)，或 index 欄 X 為 A（A  已暫存、AM 暫存後再修改）
#   tripwire = 路徑在 docs/handoffs/ 下、不在 docs/handoffs/replies/ 下、任何狀態變更；
#              或 rename/copy（old -> new）涉及 docs/handoffs/ 任一側（如回覆被移出 replies/）
#
# 路徑處理：
#   porcelain 輸出含空格或特殊字元時 git 以雙引號括住路徑，腳本會自動去除引號

set -euo pipefail

KUNSU_ROOT="${1:-}"

if [[ -z "$KUNSU_ROOT" ]]; then
  echo "錯誤：缺少軍師根路徑（第一個參數）" >&2
  echo "用法：scan-replies.sh <kunsu-root-abs-path>" >&2
  exit 1
fi

# 驗證是 git 儲存庫
if ! git -C "$KUNSU_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "錯誤：\"$KUNSU_ROOT\" 不是 git 儲存庫" >&2
  exit 1
fi

# 驗證是 git 儲存庫根（而非子目錄）
GIT_ROOT="$(git -C "$KUNSU_ROOT" rev-parse --show-toplevel)"
if [[ "$GIT_ROOT" != "$KUNSU_ROOT" ]]; then
  echo "錯誤：\"$KUNSU_ROOT\" 不是 git 儲存庫根（根為 \"$GIT_ROOT\"）" >&2
  exit 1
fi

HAS_TRIPWIRE=0

# 解析 git status --porcelain 輸出
# 格式：XY <path>  或  XY "<quoted path>"（路徑含空格或特殊字元時 git 加雙引號）
# X = index 狀態欄（第一字元）；Y = work tree 狀態欄（第二字元）
# ??  = untracked；A  = 已暫存新增；AM = 已暫存新增後又修改
while IFS= read -r line; do
  [[ -z "$line" ]] && continue

  XY="${line:0:2}"
  X="${line:0:1}"
  path_raw="${line:3}"

  # 去除 git 引號（路徑含空格或特殊字元時 git 以雙引號括起）
  if [[ "${path_raw:0:1}" == '"' && "${path_raw: -1}" == '"' ]]; then
    path_part="${path_raw:1:${#path_raw}-2}"
  else
    path_part="$path_raw"
  fi

  # rename/copy 格式：XY old -> new（如 git mv 產生的 R 狀態）。
  # 檔案在 handoffs 範圍內被移動（例如回覆被移出 replies/）屬意外變更，
  # 保守處理：涉及 docs/handoffs/ 任一側即觸發 tripwire，不做新回覆判斷。
  if [[ "$path_part" == *" -> "* ]]; then
    if [[ "$path_part" == *docs/handoffs/* ]]; then
      HAS_TRIPWIRE=1
      echo "TRIPWIRE:$XY $path_part"
    fi
    continue
  fi

  # 分類判斷（if/elif 確保 replies/ 路徑不會落入 tripwire 分支）
  if [[ "$path_part" == docs/handoffs/replies/*.md ]]; then
    # 新回覆：untracked (??) 或 index 新增（X 為 A，涵蓋 A  與 AM）
    if [[ "$XY" == "??" ]] || [[ "$X" == "A" ]]; then
      echo "NEW_REPLY:$path_part"
    fi
    # 其他狀態（如修改已提交的回覆）— 靜默忽略，不計為新回覆也不觸發 tripwire
  elif [[ "$path_part" == docs/handoffs/* ]]; then
    # tripwire：docs/handoffs/ 下（非 replies/）任何狀態變更
    # 包含：修改（M）、刪除（D）、新增/untracked（A/?）等
    HAS_TRIPWIRE=1
    echo "TRIPWIRE:$XY $path_part"
  fi

done < <(git -C "$KUNSU_ROOT" -c core.quotepath=false status --porcelain -uall 2>/dev/null)
# -uall：強制逐檔列出 untracked（預設會把整個未追蹤目錄收合為 "dir/" 一行，
# 導致 replies/ 目錄本身未被追蹤時新回覆無法逐檔偵測）

if [[ "$HAS_TRIPWIRE" -eq 1 ]]; then
  exit 2
fi

exit 0
