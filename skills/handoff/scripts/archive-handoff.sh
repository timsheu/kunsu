#!/usr/bin/env bash
# archive-handoff.sh — /handoff done 步驟 5–7 的腳本化執行：
#   status Edit → untracked 前置 git add → 本體與回覆成對 git mv → git add 歸檔目的地
#
# 用法：
#   archive-handoff.sh "<交接檔名、slug 片段或路徑>" [更多交接…]
#   archive-handoff.sh --precheck "<交接檔名…>" [更多交接…]
#     → done 步驟 3 的來源 todo 查核：對每份交接印雙向檔名比對候選
#       （todo 內文含交接檔名／交接本體含 todo 檔名），零搬移零暫存後結束
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
#   4. 不 commit：stdout 印出一行帶兩形 pathspec 的待確認 git commit 指令
#      （ADR 009 經使用者確認後執行；ADR 018 宣告範圍契約——tracked rename 成對
#      列 src＋dst、untracked 來源僅列 dst）。todo 一併收尾／轉出由本腳本掃
#      index 的 docs/todos/ 三形（R＝tracked 收尾、archive/ 下 A＝untracked 來源
#      收尾、頂層 A＝轉出殘項）自動聚合進訊息與 pathspec——步驟 4 以
#      archive-todo.sh --from-handoff 暫存後，宣告收斂於本段單一 commit，
#      雙指令並存會重演 index 半截殘留（fc143a8 形狀）
#   4b. 歸檔執行尾端印引用連結偵測（done 步驟 8 候選）：grep 各交接舊路徑形
#       `docs/handoffs/<檔名>` 的命中檔清單——修不修與白名單判斷留模型層
#   5. 暫存區含 docs/handoffs/、docs/todos/ 之外的路徑時警告——不在本次 commit
#      宣告範圍內不會被帶入，列出供人工裁決是否另行處理
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

PRECHECK=0
if [[ "${1:-}" == "--precheck" ]]; then
  PRECHECK=1
  shift
fi

if [[ $# -lt 1 ]]; then
  echo "錯誤：缺少交接檔參數" >&2
  echo "用法：archive-handoff.sh [--precheck] \"<交接檔名、slug 片段或路徑>\" [更多交接…]" >&2
  exit 1
fi

if [[ "$PRECHECK" -eq 0 ]]; then
  command -v python3 >/dev/null 2>&1 || {
    echo "錯誤：需要 python3（frontmatter status 編輯）；不可用時請依 SKILL done 步驟 5–7 手動執行" >&2
    exit 1
  }
fi

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
# 實體路徑正規化：symlink 佈局（如 macOS /tmp）下，邏輯路徑與 git 根的實體
# 路徑不一致會使相對前綴剝除失效——tracked 檔被誤判 untracked、pathspec 拆半
ROOT="$(cd "$ROOT" && pwd -P)"

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
    abs="$(cd "$(dirname "$arg")" 2>/dev/null && pwd -P)/$(basename "$arg")" || true
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

ARCHIVED_FILES=()   # 已在 archive/ 的絕對路徑——precheck 仍需掃描（失敗重跑場景：
                    # 本體已歸檔、todo 收尾失敗筆待重列候選，SKILL done 步驟 4 承諾）
for arg in "$@"; do
  resolve_arg "$arg"
  if [[ -n "$resolved_archived" ]]; then
    SKIPPED+=("$(basename "$resolved_archived")")
    ARCHIVED_FILES+=("$resolved_archived")
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

# ── --precheck：done 步驟 3 來源 todo 查核（零搬移零暫存）──────────────
# 已歸檔本體一併掃描：todo 收尾失敗筆＋本體已進 archive/ 是協議可達狀態
#（SKILL done 步驟 4「任一筆失敗續行交接收尾」），重跑 done 的步驟 3 必須仍列候選
if [[ "$PRECHECK" -eq 1 ]]; then
  ALL_PRECHECK=()
  if [[ ${#FILES[@]} -gt 0 ]]; then ALL_PRECHECK+=("${FILES[@]}"); fi
  if [[ ${#ARCHIVED_FILES[@]} -gt 0 ]]; then ALL_PRECHECK+=("${ARCHIVED_FILES[@]}"); fi
  if [[ ${#ALL_PRECHECK[@]} -eq 0 ]]; then
    echo "ℹ precheck：無可查核之交接" >&2
    exit 0
  fi
  total_todos=-1
  any_hit=0
  for f in "${ALL_PRECHECK[@]}"; do
    hdir="$(dirname "$f")"
    if [[ "$(basename "$hdir")" == "archive" ]]; then hdir="$(dirname "$hdir")"; fi
    TODO_DIR="$(dirname "$hdir")/todos"
    if [[ "$total_todos" -lt 0 ]]; then
      total_todos=0
      if [[ -d "$TODO_DIR" ]]; then
        for t in "$TODO_DIR"/*.md; do
          [[ "$(basename "$t")" == "README.md" ]] && continue
          total_todos=$((total_todos + 1))
        done
      fi
    fi
    base="$(basename "$f")"
    hit_lines=()
    if [[ -d "$TODO_DIR" ]]; then
      for t in "$TODO_DIR"/*.md; do
        tbase="$(basename "$t")"
        [[ "$tbase" == "README.md" ]] && continue
        dir_t2h=0
        dir_h2t=0
        grep -qF -- "$base" "$t" && dir_t2h=1
        grep -qF -- "$tbase" "$f" && dir_h2t=1
        if [[ "$dir_t2h" -eq 1 || "$dir_h2t" -eq 1 ]]; then
          if [[ "$dir_t2h" -eq 1 && "$dir_h2t" -eq 1 ]]; then
            hitdir="雙向"
          elif [[ "$dir_t2h" -eq 1 ]]; then
            hitdir="todo→交接"
          else
            hitdir="交接→todo"
          fi
          tstatus="$(sed -n 's/^status:[[:space:]]*//p' "$t" | head -1)"
          hit_lines+=("  - ${tbase}（${hitdir}；status: ${tstatus:-?}）")
        fi
      done
    fi
    if [[ ${#hit_lines[@]} -gt 0 ]]; then
      any_hit=1
      echo "── 來源 todo 查核：${base} ──" >&2
      for l in "${hit_lines[@]}"; do echo "$l" >&2; done
    fi
  done
  if [[ "$any_hit" -eq 0 ]]; then
    if [[ "$total_todos" -gt 0 ]]; then
      echo "ℹ 來源 todo 查核零命中；docs/todos/ 尚有 ${total_todos} 筆未歸檔 todo，若本交接源自其中一筆可一併收尾" >&2
    else
      echo "ℹ 來源 todo 查核零命中（docs/todos/ 無未歸檔 todo）" >&2
    fi
  fi
  echo "ℹ precheck 僅查核、未搬移未暫存；裁決後以 archive-todo.sh --from-handoff 收尾 todo，再執行本腳本正式歸檔" >&2
  exit 0
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
PATHSPECS=()
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
  # tracked 與否以 HEAD 存在性判定——已 add 未 commit（porcelain `A `）的來源
  # 同樣不在 HEAD，成對列入 pathspec 會以不匹配失敗，須與 `??` 一樣僅列目的地
  rel="${f#"$GITROOT"/}"
  body_tracked=0
  if git -C "$GITROOT" cat-file -e "HEAD:$rel" 2>/dev/null; then
    body_tracked=1
  fi

  git -C "$GITROOT" mv "$f" "$ARCHIVE_DIR/$base"
  # git mv 不會暫存 working tree 的內容修改（porcelain 呈現 RM、staged 為舊版），
  # status Edit 靠這一步帶入暫存
  git -C "$GITROOT" add -- "$ARCHIVE_DIR/$base"
  # commit pathspec 兩形（ADR 018）：tracked rename 成對列 src＋dst（只列單邊會把
  # rename 拆半）；untracked 來源（A 形狀）僅列 dst——src 從未入 git，成對必敗
  if [[ "$body_tracked" -eq 1 ]]; then
    PATHSPECS+=("$f")
  fi
  PATHSPECS+=("$ARCHIVE_DIR/$base")

  rcount=0
  for r in "$H_DIR/replies/$stem-reply-"*.md; do
    rst="$(git -C "$GITROOT" status --porcelain -- "$r" | head -1)"
    if [[ "${rst:0:2}" == "??" ]]; then
      git -C "$GITROOT" add -- "$r"
    fi
    rrel="${r#"$GITROOT"/}"
    reply_tracked=0
    if git -C "$GITROOT" cat-file -e "HEAD:$rrel" 2>/dev/null; then
      reply_tracked=1
    fi
    git -C "$GITROOT" mv "$r" "$ARCHIVE_DIR/replies/$(basename "$r")"
    if [[ "$reply_tracked" -eq 1 ]]; then
      PATHSPECS+=("$r")
    fi
    PATHSPECS+=("$ARCHIVE_DIR/replies/$(basename "$r")")
    rcount=$((rcount + 1))
  done

  echo "✓ 歸檔 ${base}（回覆 ${rcount} 份）" >&2
  names+=("$base")
done

# ── todo 聚合：掃 index 中 docs/todos/ 三形，併入 pathspec 與訊息 ─────────
# 步驟 4 的 archive-todo.sh --from-handoff 僅暫存不印指令，commit 宣告收斂於
# 本段單一指令——雙指令並存時執行任一條，另一半 rename 留在 index（fc143a8
# 半截殘留形狀）。三形（子目錄分支先評估＋去前綴不含 / 二次驗證，[[ ]] 的 *
# 會跨 / 誤匹配）：
#   R  old→new，new 在 archive/ 下＝tracked todo 收尾（成對列 src＋dst）
#   A  path 在 archive/ 下＝untracked 來源收尾（僅列目的地）
#   A  path 在頂層＝轉出殘項（僅列新檔）
h_rel="${H_DIR#"$GITROOT"/}"
todo_rel="$(dirname "$H_DIR")/todos"
todo_rel="${todo_rel#"$GITROOT"/}"
TODO_CLOSED=()
TODO_SPUN=()
CLOSED_BASES=()   # archive 下 A 形的 basename——供頂層 D 回配（退化 rename 的另半邊）
D_TOP=()          # 頂層 D 形候選：小檔改動比例過大時 -M 相似度不足，R 退化為 A＋D
UNMARKED_SKIP=()  # index 有收尾形狀但不在握手 marker 內——前流程殘留，不冒名聚合
# 聚合握手 marker：只有本流程 archive-todo.sh --from-handoff 列名的收尾筆才聚合，
# 前流程殘留的無關 todo 暫存（如 /todo done 印出指令後尚未 commit 的 R 形）不收
#（轉出殘項為 session 手動 add、無 marker 來源，維持 index 即真相＋訊息帶 slug
# 由確認 commit 人工把關）
MARKER="$GITROOT/.git/kunsu-todo-aggregate"
MARKED=()
if [[ -f "$MARKER" ]]; then
  while IFS= read -r mline; do
    [[ -n "$mline" ]] && MARKED+=("$mline")
  done < "$MARKER"
fi
is_marked() {
  local b="$1" m
  if [[ ${#MARKED[@]} -gt 0 ]]; then
    for m in "${MARKED[@]}"; do
      [[ "$m" == "$b" ]] && return 0
    done
  fi
  return 1
}
while IFS=$'\t' read -r tstat p1 p2; do
  [[ -z "$tstat" ]] && continue
  # 保險剝除殘留引號（掃描已帶 -c core.quotepath=false，中文路徑為原始字元）
  p1="${p1%\"}"; p1="${p1#\"}"
  p2="${p2%\"}"; p2="${p2#\"}"
  case "$tstat" in
    R*)
      if [[ "$p2" == "$todo_rel"/archive/* ]]; then
        sub="${p2#"$todo_rel"/archive/}"
        if [[ "$sub" != */* && "$sub" == *.md ]]; then
          if is_marked "$(basename "$p2")"; then
            PATHSPECS+=("$GITROOT/$p1" "$GITROOT/$p2")
            TODO_CLOSED+=("$(basename "$p2" .md)")
          else
            UNMARKED_SKIP+=("$p2")
          fi
        fi
      fi
      ;;
    A)
      if [[ "$p1" == "$todo_rel"/archive/* ]]; then
        sub="${p1#"$todo_rel"/archive/}"
        if [[ "$sub" != */* && "$sub" == *.md ]]; then
          if is_marked "$(basename "$p1")"; then
            PATHSPECS+=("$GITROOT/$p1")
            TODO_CLOSED+=("$(basename "$p1" .md)")
            CLOSED_BASES+=("$(basename "$p1")")
          else
            UNMARKED_SKIP+=("$p1")
          fi
        fi
      elif [[ "$p1" == "$todo_rel"/* ]]; then
        sub="${p1#"$todo_rel"/}"
        if [[ "$sub" != */* && "$sub" == *.md ]]; then
          PATHSPECS+=("$GITROOT/$p1")
          TODO_SPUN+=("$(basename "$p1" .md)")
        fi
      fi
      ;;
    D)
      if [[ "$p1" == "$todo_rel"/* && "$p1" != "$todo_rel"/archive/* ]]; then
        sub="${p1#"$todo_rel"/}"
        if [[ "$sub" != */* && "$sub" == *.md ]]; then
          D_TOP+=("$p1")
        fi
      fi
      ;;
  esac
done < <(git -c core.quotepath=false -C "$GITROOT" diff --cached -M --name-status)
# 退化 rename 回配：頂層 D 的 basename 與 archive 下 A 相同者＝同一次收尾被 -M
# 拆成兩半（tracked 來源刪除＋目的地新增），來源補入宣告範圍——僅回配 basename
# 精確相符者，孤懸的 D（前流程殘留）不撿
if [[ ${#D_TOP[@]} -gt 0 && ${#CLOSED_BASES[@]} -gt 0 ]]; then
  for d in "${D_TOP[@]}"; do
    db="$(basename "$d")"
    for cb in "${CLOSED_BASES[@]}"; do
      if [[ "$db" == "$cb" ]]; then
        PATHSPECS+=("$GITROOT/$d")
        break
      fi
    done
  done
fi
if [[ ${#TODO_CLOSED[@]} -gt 0 ]]; then
  echo "ℹ 聚合 todo 收尾 ${#TODO_CLOSED[@]} 筆：$(IFS=、; echo "${TODO_CLOSED[*]}")" >&2
fi
if [[ ${#TODO_SPUN[@]} -gt 0 ]]; then
  echo "ℹ 聚合轉出殘項 todo ${#TODO_SPUN[@]} 筆：$(IFS=、; echo "${TODO_SPUN[*]}")" >&2
fi
if [[ ${#UNMARKED_SKIP[@]} -gt 0 ]]; then
  echo "⚠ index 含非本流程的 todo 歸檔暫存——不聚合、不入本 commit 宣告範圍，請依其原印出的指令另行 commit：" >&2
  for p in "${UNMARKED_SKIP[@]}"; do echo "  - $p" >&2; done
fi
rm -f "$MARKER"

# 暫存區範圍核對：pathspec commit 只收斂宣告範圍，範圍外暫存不會被帶入——
# 仍列出供人工裁決是否另行處理，不擅自 unstage（前綴以 H_DIR 相對 GITROOT 計算，
# 專案根深於 git 根的 monorepo 佈局下才不會把自己剛暫存的歸檔檔誤報為外部路徑）
outside="$(git -c core.quotepath=false -C "$GITROOT" diff --cached --name-only | grep -v "^${h_rel}/" | grep -v "^${todo_rel}/" || true)"
if [[ -n "$outside" ]]; then
  echo "⚠ 暫存區含本流程（${h_rel}/、${todo_rel}/）之外的已暫存路徑——不在本次 commit 宣告範圍內、不會被帶入，請確認是否需另行處理：" >&2
  while IFS= read -r p; do echo "  - $p" >&2; done <<< "$outside"
fi

msg="docs: 歸檔交接 $(IFS=、; echo "${names[*]}")"
if [[ ${#TODO_CLOSED[@]} -gt 0 ]]; then
  msg="${msg}；一併收尾 todo $(IFS=、; echo "${TODO_CLOSED[*]}")"
fi
if [[ ${#TODO_SPUN[@]} -gt 0 ]]; then
  msg="${msg}；轉出殘項 todo $(IFS=、; echo "${TODO_SPUN[*]}")"
fi
quoted=""
for p in "${PATHSPECS[@]}"; do quoted+=" \"$p\""; done
echo "git commit -m \"$msg\" --$quoted"
staged_count="$(git -C "$GITROOT" diff --cached --name-only | wc -l | tr -d ' ')"
echo "ℹ index 現含 ${staged_count} 筆暫存路徑；上列指令僅收斂 pathspec 宣告範圍（兩形：tracked rename 成對、untracked 僅目的地，ADR 018），範圍外暫存不受影響" >&2
echo "ℹ 已暫存本流程全部路徑（僅具體路徑，未用 -A）；尚未 commit——請經使用者確認後執行上列指令（ADR 009）。todo 一併收尾／轉出已由本腳本掃 index 聚合進訊息與 pathspec（步驟 4 先以 archive-todo.sh --from-handoff 暫存）" >&2

# ── 引用連結偵測（done 步驟 8 候選）：grep 舊路徑形，僅列出——修不修、
# 白名單（todo／plan 可修、交接本體含 archive 內僅回報不修）判斷留模型層
REF_MAX=8
for name in "${names[@]}"; do
  ref_hits="$(grep -rlF -- "docs/handoffs/${name}" "$ROOT/docs" 2>/dev/null || true)"
  if [[ -n "$ref_hits" ]]; then
    ref_count="$(printf '%s\n' "$ref_hits" | wc -l | tr -d ' ')"
    echo "── 引用偵測：docs/handoffs/${name}（${ref_count} 檔命中）──" >&2
    printf '%s\n' "$ref_hits" | head -n "$REF_MAX" | while IFS= read -r p; do
      echo "  - ${p#"$ROOT"/}" >&2
    done
    if [[ "$ref_count" -gt "$REF_MAX" ]]; then
      echo "  （另有 $((ref_count - REF_MAX)) 檔未列出）" >&2
    fi
  fi
done

echo "ℹ done 收尾查核不隨腳本豁免：逐項驗收、沉澱訊號、反向路由、來源 todo（--precheck 印候選）、殘項清點、斷言自查——見 handoff SKILL.md done 段" >&2
