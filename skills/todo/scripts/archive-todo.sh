#!/usr/bin/env bash
# archive-todo.sh — /todo done、/todo rm 與 /handoff done 步驟 4 的 todo 歸檔腳本化：
#   frontmatter status Edit → 選填依據回填 → untracked 前置 git add → git mv 至
#   docs/todos/archive/ → git add 歸檔目的地
#
# 用法：
#   archive-todo.sh --done [--basis "<解決依據>"] [--from-handoff] <slug|檔名|路徑> [更多…]
#   archive-todo.sh --rm   [--basis "<結案原因>"] [--from-handoff] <slug|檔名|路徑> [更多…]
#
# 行為：
#   1. 終態旗標必填且單一：--done（status 改「已解決」）或 --rm（改「已封存」）；
#      不可混用——混合收尾請分次呼叫
#   2. --basis 選填：--done 語境於標題下補「**解決依據**：<文字>」、--rm 語境補
#      「**結案原因**：<文字>」；多筆傳入時同一 basis 套用於每筆。basis 由本腳本
#      在 git add 歸檔目的地**之前**寫入——mv 後才 Edit 的內容不會入暫存，
#      pathspec commit 會帶入舊版且無任何掃描訊號
#   3. status 已是「已解決」／「已封存」的孤兒：跳過 Edit（不改終態、不補依據），
#      僅執行搬移補歸檔
#   4. --from-handoff：供 /handoff done 步驟 4 呼叫——抑制 stdout 的待確認 commit
#      指令（改由 archive-handoff.sh 掃 index 聚合進單一 commit），僅暫存
#   5. 所有 git add 僅限本流程產出的具體路徑，絕不 -A、不整目錄打包
#   6. 不 commit：獨立執行時 stdout 印一行帶兩形 pathspec 的待確認 git commit 指令
#      （ADR 009 經使用者確認後執行；ADR 018 宣告範圍契約——tracked rename 成對
#      列 src＋dst、untracked 來源僅列 dst）
#   7. 已在 archive/ 的傳入項自動略過（供中途失敗後重跑）；中途失敗不回滾
#
# 來源事故（2026-08-31 ebook 軍師 fc143a8）：手動 todo 歸檔 commit 把 tracked
# rename 的 pathspec 只列目的地，rename 拆半、來源刪除留在 index——todo 歸檔是
# v0.18.0 歸檔腳本化後唯一沒有計算載體的歸檔流程，本腳本補上此缺口。
#
# 殘項清點、三去向裁決與跨檔連結修正不在本腳本內（判斷型，留模型層）：
# 執行本腳本前先完成殘項清點與內文 Edit——mv 後的內文修改不會入暫存。

set -euo pipefail

MUTATION_STARTED=0
on_err() {
  if [[ "$MUTATION_STARTED" -eq 1 ]]; then
    echo "✗ 歸檔中途失敗：已完成的搬移不回滾。請以 git status 檢視現況後重跑本腳本（已在 archive/ 的傳入項會自動略過）。" >&2
  fi
}
trap on_err ERR

MODE=""
BASIS=""
FROM_HANDOFF=0
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --done)
      if [[ -n "$MODE" && "$MODE" != "done" ]]; then
        echo "錯誤：--done 與 --rm 不可混用（單次呼叫單一終態；混合收尾請分次執行）" >&2
        exit 2
      fi
      MODE="done"; shift ;;
    --rm)
      if [[ -n "$MODE" && "$MODE" != "rm" ]]; then
        echo "錯誤：--done 與 --rm 不可混用（單次呼叫單一終態；混合收尾請分次執行）" >&2
        exit 2
      fi
      MODE="rm"; shift ;;
    --basis)
      BASIS="${2:-}"
      if [[ -z "$BASIS" ]]; then
        echo "錯誤：--basis 需要一個文字參數" >&2
        exit 2
      fi
      shift 2 ;;
    --from-handoff)
      FROM_HANDOFF=1; shift ;;
    --*)
      echo "錯誤：未知旗標「$1」" >&2
      exit 2 ;;
    *)
      ARGS+=("$1"); shift ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo "錯誤：缺少終態旗標——--done（已解決）或 --rm（已封存）擇一必填" >&2
  echo "用法：archive-todo.sh --done|--rm [--basis \"<文字>\"] [--from-handoff] <slug|檔名|路徑> [更多…]" >&2
  exit 1
fi
if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "錯誤：缺少 todo 檔參數" >&2
  echo "用法：archive-todo.sh --done|--rm [--basis \"<文字>\"] [--from-handoff] <slug|檔名|路徑> [更多…]" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "錯誤：需要 python3（frontmatter status 編輯）；不可用時請依 todo SKILL done／rm 步驟手動執行" >&2
  exit 1
}

if [[ "$MODE" == "done" ]]; then
  NEW_STATUS="已解決"
  BASIS_LABEL="解決依據"
else
  NEW_STATUS="已封存"
  BASIS_LABEL="結案原因"
fi

# 定位專案根：與 new-todo.sh 同一套——優先往上找最近的 CLAUDE.md/AGENTS.md
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

T_DIR=""          # 全部 todo 檔必須同屬一個 docs/todos/（單一 commit 訊息）
FILES=()          # 解析成功、待歸檔的絕對路徑
SKIPPED=()        # 已在 archive/ 的略過項（檔名）

# 解析單一參數 → 絕對路徑存入 resolved（頂層檔）或 resolved_archived（已歸檔）
resolve_arg() {
  local arg="$1"
  resolved=""
  resolved_archived=""

  if [[ "$arg" == */* ]]; then
    local abs
    abs="$(cd "$(dirname "$arg")" 2>/dev/null && pwd -P)/$(basename "$arg")" || true
    if [[ -z "$abs" || ! -f "$abs" ]]; then
      echo "錯誤：找不到檔案「${arg}」" >&2
      return 1
    fi
    if [[ "$abs" == */docs/todos/archive/* ]]; then
      resolved_archived="$abs"
      return 0
    fi
    local rel="${abs##*/docs/todos/}"
    if [[ "$abs" != */docs/todos/*.md || "$rel" == */* ]]; then
      echo "錯誤：「${arg}」不是 docs/todos/ 頂層 todo 檔" >&2
      return 1
    fi
    resolved="$abs"
    return 0
  fi

  local td="$ROOT/docs/todos"
  if [[ ! -d "$td" ]]; then
    echo "錯誤：$td 不存在（請於含 docs/todos/ 的專案內執行，或改傳 todo 檔路徑）" >&2
    return 1
  fi
  local name="${arg%.md}"
  if [[ -f "$td/$name.md" ]]; then
    resolved="$td/$name.md"
    return 0
  fi
  local hits=()
  local f
  for f in "$td"/*"$name"*.md; do
    hits+=("$f")
  done
  if [[ ${#hits[@]} -eq 1 ]]; then
    resolved="${hits[0]}"
    return 0
  elif [[ ${#hits[@]} -gt 1 ]]; then
    echo "錯誤：「${arg}」比對到多筆 todo，請給更精確的片段或完整檔名：" >&2
    for f in "${hits[@]}"; do echo "  - $(basename "$f")" >&2; done
    return 1
  fi
  # 頂層零命中 → 查 archive/（重跑場景：前次已搬移成功）
  for f in "$td/archive/"*"$name"*.md; do
    resolved_archived="$f"
    return 0
  done
  echo "錯誤：docs/todos/ 頂層與 archive/ 均找不到「${arg}」" >&2
  return 1
}

for arg in "${ARGS[@]}"; do
  resolve_arg "$arg"
  if [[ -n "$resolved_archived" ]]; then
    SKIPPED+=("$(basename "$resolved_archived")")
    continue
  fi
  fdir="$(dirname "$resolved")"
  if [[ -z "$T_DIR" ]]; then
    T_DIR="$fdir"
  elif [[ "$T_DIR" != "$fdir" ]]; then
    echo "錯誤：todo 檔分屬不同 docs/todos/（${T_DIR} 與 ${fdir}），請分批執行" >&2
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

GITROOT="$(git -C "$T_DIR" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "錯誤：$T_DIR 不在 git 儲存庫內" >&2
  exit 1
}

ARCHIVE_DIR="$T_DIR/archive"
mkdir -p "$ARCHIVE_DIR"

names=()
PATHSPECS=()
MUTATION_STARTED=1
for f in "${FILES[@]}"; do
  base="$(basename "$f")"

  # frontmatter status → 終態；basis 補於 H1 標題下方。孤兒（已是終態）整筆跳過
  # Edit——不改終態、不補依據，僅搬移（python 印 EDITED／ORPHAN 供回報）
  edit_result="$(python3 - "$f" "$NEW_STATUS" "$BASIS_LABEL" "$BASIS" <<'PYEOF'
import re
import sys

path, new_status, basis_label, basis = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path, encoding="utf-8") as fh:
    text = fh.read()
m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
if not m:
    sys.exit(f"frontmatter 缺失或格式異常：{path}")
fm = m.group(1)
sm = re.search(r"(?m)^status:\s*(.*)$", fm)
if sm is None:
    sys.exit(f"frontmatter 無 status 欄位：{path}")
current = sm.group(1).strip()
if current in ("已解決", "已封存"):
    print("ORPHAN:" + current)
    sys.exit(0)
fm2 = re.sub(r"(?m)^status:.*$", "status: " + new_status, fm, count=1)
body = text[m.end(1):]
if basis:
    line = "\n**" + basis_label + "**：" + basis + "\n"
    h1 = re.search(r"(?m)^# .*$", body)
    if h1:
        body = body[: h1.end()] + "\n" + line + body[h1.end():]
    else:
        body = body + line
with open(path, "w", encoding="utf-8") as fh:
    fh.write(text[: m.start(1)] + fm2 + body)
print("EDITED")
PYEOF
)"
  case "$edit_result" in
    ORPHAN:*)
      echo "ℹ ${base} status 已是「${edit_result#ORPHAN:}」（孤兒），僅補歸檔、不改終態不補依據" >&2
      ;;
  esac

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
  # status／basis Edit 靠這一步帶入暫存
  git -C "$GITROOT" add -- "$ARCHIVE_DIR/$base"
  if [[ "$body_tracked" -eq 1 ]]; then
    PATHSPECS+=("$f")
  fi
  PATHSPECS+=("$ARCHIVE_DIR/$base")

  echo "✓ 歸檔 todo ${base}（status: ${NEW_STATUS}）" >&2
  names+=("$(basename "$f" .md)")
done

if [[ "$FROM_HANDOFF" -eq 1 ]]; then
  # 聚合握手 marker（.git/ 內，不入版控不被掃描）：archive-handoff.sh 只聚合
  # 列名於此的收尾筆——防前流程殘留的無關 todo 暫存被冒名收進交接 commit
  MARKER="$GITROOT/.git/kunsu-todo-aggregate"
  for n in "${names[@]}"; do echo "${n}.md" >> "$MARKER"; done
  echo "ℹ 已暫存 todo 歸檔路徑（--from-handoff）；待確認 commit 指令由 archive-handoff.sh 掃 index 聚合印出，本腳本不另印" >&2
else
  msg="docs: 歸檔 todo $(IFS=、; echo "${names[*]}")"
  quoted=""
  for p in "${PATHSPECS[@]}"; do quoted+=" \"$p\""; done
  echo "git commit -m \"$msg\" --$quoted"
  staged_count="$(git -C "$GITROOT" diff --cached --name-only | wc -l | tr -d ' ')"
  echo "ℹ index 現含 ${staged_count} 筆暫存路徑；上列指令僅收斂 pathspec 宣告範圍（兩形：tracked rename 成對、untracked 僅目的地，ADR 018），範圍外暫存不受影響" >&2
  echo "ℹ 已暫存本流程全部路徑（僅具體路徑，未用 -A）；尚未 commit——請經使用者確認後執行上列指令（ADR 009；/todo 單獨收尾同樣不主動 commit）" >&2
fi
echo "ℹ 殘項清點、三去向裁決與跨檔連結修正不隨腳本豁免：清點與內文 Edit 須在本腳本執行前完成——見 todo SKILL.md done／rm 段" >&2
