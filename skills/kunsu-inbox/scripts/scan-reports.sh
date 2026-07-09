#!/usr/bin/env bash
# scan-reports.sh — 掃描軍師 docs/reports/ 中未 commit 的新上報檔案
# 同時執行 tripwire 核對：上報信箱內是否有授權範圍之外的意外變更
#
# 用法：scan-reports.sh <kunsu-root-abs-path>
#
# 輸出（stdout，每行一筆）：
#   NEW_REPORT:<相對路徑>        新上報（頂層 .md 檔案，untracked 或 index 新增）
#   TRIPWIRE:<XY> <相對路徑>     意外變更（授權範圍之外的任何狀態變更）
#   TRIPWIRE:<XY> <src> -> <dst> 意外搬移（rename 形式，路徑欄為雙側複合字串）
#
# exit code：
#   0 — 正常完成（含零上報、零 tripwire；docs/reports/ 不存在時同零筆處理）
#   1 — 參數錯誤或非 git repo 根
#   2 — tripwire 觸發（上報信箱有授權範圍外的未 commit 變更）
#
# 分類規則（if/elif 順序即授權邊界，不可調換）：
#   1. docs/reports/archive/* 一律靜默略過 —— 歸檔區由軍師 session 管理，
#      含授權歸檔產生的新增檔案。此分支必須最先評估：bash [[ ]] 的
#      docs/reports/*.md pattern 中 `*` 可跨 `/`，會同時匹配 archive/ 內
#      檔案（與 scan-replies.sh 的單層 replies/ 結構不同，不可直接類比替換）。
#   2. docs/reports/.gitkeep 靜默略過 —— 遷移補建後未 commit 的佔位檔。
#   3. 頂層 <名稱>.md（名稱不含 /）：?? 或 index A ＝新上報；其餘狀態
#      （修改、刪除等）＝tripwire。
#   4. docs/reports/ 下的其他路徑（非預期巢狀、非 .md）＝tripwire。
#   rename（XY 含 R/C，格式 old -> new）：僅「src 為頂層 .md 且 dst 位於
#   archive/」視為授權歸檔（可攜帶內容修改），靜默略過；其餘涉及
#   docs/reports/ 任一側的搬移（含 archive/→頂層反向搬移）＝tripwire。
#
# 路徑處理：
#   porcelain 輸出含空格或特殊字元時 git 以雙引號括住路徑，腳本會自動去除引號

set -euo pipefail

KUNSU_ROOT="${1:-}"

if [[ -z "$KUNSU_ROOT" ]]; then
  echo "錯誤：缺少軍師根路徑（第一個參數）" >&2
  echo "用法：scan-reports.sh <kunsu-root-abs-path>" >&2
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

# 去除 git 引號（路徑含空格或特殊字元時 git 以雙引號括起）
strip_quotes() {
  local p="$1"
  if [[ "${p:0:1}" == '"' && "${p: -1}" == '"' ]]; then
    printf '%s' "${p:1:${#p}-2}"
  else
    printf '%s' "$p"
  fi
}

# 解析 git status --porcelain 輸出
# 格式：XY <path>  或  XY <old> -> <new>（rename/copy）
# X = index 狀態欄（第一字元）；Y = work tree 狀態欄（第二字元）
while IFS= read -r line; do
  [[ -z "$line" ]] && continue

  XY="${line:0:2}"
  X="${line:0:1}"
  path_raw="${line:3}"

  # rename/copy 格式：XY old -> new（如 git mv 產生的 R 狀態）
  if [[ "$path_raw" == *" -> "* ]]; then
    src_raw="${path_raw%% -> *}"
    dst_raw="${path_raw#* -> }"
    src="$(strip_quotes "$src_raw")"
    dst="$(strip_quotes "$dst_raw")"

    # 與 docs/reports/ 無關的搬移：略過
    if [[ "$src" != docs/reports/* && "$dst" != docs/reports/* ]]; then
      continue
    fi

    # 授權歸檔豁免：雙側核驗，src 為頂層 .md 且 dst 位於 archive/，
    # 兩條件缺一即走 tripwire（含 archive/→頂層的反向搬移）。
    src_rel="${src#docs/reports/}"
    if [[ "$src" == docs/reports/*.md && "$src_rel" != */* \
          && "$dst" == docs/reports/archive/* ]]; then
      continue
    fi

    HAS_TRIPWIRE=1
    echo "TRIPWIRE:$XY $src -> $dst"
    continue
  fi

  path_part="$(strip_quotes "$path_raw")"

  # 分類判斷：archive/ 分支必須最先評估（見檔頭分類規則說明）
  if [[ "$path_part" == docs/reports/archive/* ]]; then
    # 歸檔區：軍師 session 管理範圍，靜默略過
    continue
  elif [[ "$path_part" == "docs/reports/.gitkeep" ]]; then
    # 遷移補建的佔位檔：靜默略過
    continue
  elif [[ "$path_part" == docs/reports/*.md \
          && "${path_part#docs/reports/}" != */* ]]; then
    # 頂層上報檔：untracked (??) 或 index 新增（X 為 A，涵蓋 A  與 AM）＝新上報
    if [[ "$XY" == "??" ]] || [[ "$X" == "A" ]]; then
      echo "NEW_REPORT:$path_part"
    else
      # 頂層既有檔案的修改、刪除等＝授權範圍外變更
      HAS_TRIPWIRE=1
      echo "TRIPWIRE:$XY $path_part"
    fi
  elif [[ "$path_part" == docs/reports/* ]]; then
    # 非預期巢狀目錄或非 .md 檔案＝授權範圍外變更
    HAS_TRIPWIRE=1
    echo "TRIPWIRE:$XY $path_part"
  fi

done < <(git -C "$KUNSU_ROOT" -c core.quotepath=false status --porcelain -uall 2>/dev/null)
# -uall：強制逐檔列出 untracked（預設會把整個未追蹤目錄收合為 "dir/" 一行，
# 導致 reports/ 目錄本身未被追蹤時新上報無法逐檔偵測）

if [[ "$HAS_TRIPWIRE" -eq 1 ]]; then
  exit 2
fi

exit 0
