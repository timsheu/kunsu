#!/usr/bin/env bash
# scan-replies.sh — 掃描軍師 docs/handoffs/replies/ 中未 commit 的新回覆檔案
# 同時執行 tripwire 核對：docs/handoffs/ 下是否有授權範圍之外的意外變更
#
# 用法：scan-replies.sh <kunsu-root-abs-path>
#
# 輸出（stdout，每行一筆）：
#   NEW_REPLY:<相對路徑>          新回覆（replies/ 頂層 .md 檔案，untracked 或 index 新增）
#   TRIPWIRE:<XY> <相對路徑>      意外變更（授權範圍之外的任何狀態變更）
#   TRIPWIRE:<XY> <src> -> <dst>  意外搬移（rename 形式，路徑欄為雙側複合字串）
#
# exit code：
#   0 — 正常完成（含零回覆、零 tripwire）
#   1 — 參數錯誤或非 git repo 根
#   2 — tripwire 觸發（docs/handoffs/ 下有授權範圍外的未 commit 變更）
#
# 分類規則（if/elif 順序即授權邊界，不可調換）：
#   1. docs/handoffs/archive/* 一律靜默略過 —— 歸檔區由軍師 session 管理
#      （/handoff done 的授權歸檔），不做狀態欄篩選，與 scan-applications.sh
#      對 archive/ 的取捨一致：untracked 檔先 git add 再 git mv 後在 porcelain
#      呈現為 archive/ 下的 A 新增而非 rename，亦涵蓋在此分支。此分支必須
#      最先評估：bash [[ ]] 的 docs/handoffs/replies/*.md pattern 中 `*` 可跨
#      `/`，會同時匹配 archive/replies/ 內檔案。
#   2. replies/ 頂層 <名稱>.md（名稱不含 /）：?? 或 index A ＝新回覆；其餘
#      狀態（修改已 commit 的回覆等）＝靜默忽略（不計新回覆、不觸發 tripwire，
#      沿舊版行為）。
#   3. docs/handoffs/ 下的其他路徑（頂層交接檔的新增／修改／刪除、非預期
#      巢狀、非 .md）＝tripwire。
#   rename（XY 含 R/C，格式 old -> new）：雙側核驗，僅以下兩形狀視為
#   /handoff done 的授權歸檔（可攜帶內容修改，如 status: done 的 Edit——
#   git mv 對含未暫存修改的檔案呈現 RM，本豁免僅驗路徑形狀、不看 XY）：
#     a. src 為 docs/handoffs/ 頂層 .md 且 dst 位於 docs/handoffs/archive/
#     b. src 為 docs/handoffs/replies/ 頂層 .md 且 dst 位於
#        docs/handoffs/archive/replies/
#   其餘涉及 docs/handoffs/ 任一側的搬移（含 archive/→頂層、replies/→頂層
#   等反向或越界搬移）＝tripwire。不驗 src/dst basename 同名（/handoff done
#   的 git mv 天然同名，與 scan-applications.sh／scan-reports.sh 一致）。
#
# 授權邊界的威脅模型（為何 archive/ 靜默豁免是可接受取捨）：
#   投遞腳本（new-handoff-reply.sh）只往 replies/ 頂層寫；會寫 archive/ 的
#   只有軍師 session 自己執行的 /handoff done 歸檔。豁免 archive/ 等於信任
#   軍師自身的合法寫入，與 scan-applications.sh 已接受並記錄的取捨等價。
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

    # 與 docs/handoffs/ 無關的搬移：略過
    if [[ "$src" != docs/handoffs/* && "$dst" != docs/handoffs/* ]]; then
      continue
    fi

    # 授權歸檔豁免形狀 a：src 為頂層交接檔 .md 且 dst 位於 archive/，
    # 兩條件缺一即走 tripwire（含 archive/→頂層的反向搬移）。
    src_rel="${src#docs/handoffs/}"
    if [[ "$src" == docs/handoffs/*.md && "$src_rel" != */* \
          && "$dst" == docs/handoffs/archive/* ]]; then
      continue
    fi

    # 授權歸檔豁免形狀 b：src 為 replies/ 頂層回覆檔 .md 且 dst 位於
    # archive/replies/（/handoff done 將交接與其回覆成對歸檔）。
    src_rel_replies="${src#docs/handoffs/replies/}"
    if [[ "$src" == docs/handoffs/replies/*.md && "$src_rel_replies" != */* \
          && "$dst" == docs/handoffs/archive/replies/* ]]; then
      continue
    fi

    HAS_TRIPWIRE=1
    echo "TRIPWIRE:$XY $src -> $dst"
    continue
  fi

  path_part="$(strip_quotes "$path_raw")"

  # 分類判斷：archive/ 分支必須最先評估（見檔頭分類規則說明）
  if [[ "$path_part" == docs/handoffs/archive/* ]]; then
    # 歸檔區：軍師 session 管理範圍（含 git add 後搬移產生的 A 新增），靜默略過
    continue
  elif [[ "$path_part" == docs/handoffs/replies/*.md \
          && "${path_part#docs/handoffs/replies/}" != */* ]]; then
    # replies/ 頂層回覆檔：untracked (??) 或 index 新增（X 為 A，涵蓋 A  與 AM）＝新回覆
    if [[ "$XY" == "??" ]] || [[ "$X" == "A" ]]; then
      echo "NEW_REPLY:$path_part"
    fi
    # 其他狀態（如修改已 commit 的回覆）— 靜默忽略，不計為新回覆也不觸發 tripwire
  elif [[ "$path_part" == docs/handoffs/* ]]; then
    # tripwire：頂層交接檔的新增／修改／刪除、非預期巢狀或非 .md 路徑
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
