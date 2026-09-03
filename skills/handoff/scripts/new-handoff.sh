#!/usr/bin/env bash
# new-handoff.sh — 在當前專案的 docs/handoffs/ 建立一份跨 session／跨角色交接文件
#
# 用法：
#   echo "<內文>" | new-handoff.sh "<標題>" [from] [to] [tag1,tag2,...] [查重關鍵詞(空白分隔)]
#
# 行為：
#   1. 從當前目錄往上找最近的 CLAUDE.md/AGENTS.md 定位專案根（monorepo/submodule
#      場景下，實際專案常不等於 git 根目錄）；找不到才退回 git 根，最後退回當前目錄；往上找到家目錄即停，不把家目錄當專案根
#   2. 確保 docs/handoffs/ 存在
#   3. 檔名 = YYYY-MM-DD-<slug>.md；同日同名自動加 -2、-3...
#   4. 寫入 Dataview 友善 frontmatter（from/to/status）+ stdin 內文 +
#      「回覆方式」定型段落（指示接手方去 docs/handoffs/replies/ 建新檔回覆，
#      不要編輯本檔案）；內文開頭若重複了與標題相同的 H1 會被去除，內文若已含
#      背景／現況分析／問題／期望交付／相關檔案等段落標題則不再重複附加空白骨架
#   5. 印出最終檔案路徑（供呼叫端回報）
#   6. 產檔查重（advisory，全走 stderr）：本地層列出近 N 天發給同收件角色的既有
#      交接（含 archive/，回覆檔僅用於推導「已回覆」狀態）；tshehtu 層以關鍵詞
#      （第 5 參數，缺省時自標題去通用詞抽取）查 zoekt 跨 repo 索引。降級顯式、
#      零命中顯式，不改產出檔、不改 exit code、stdout 維持單行路徑。有效性為
#      條件式：時間窗外、索引盲區（未 commit、一小時內新 commit、未 discovery
#      的 repo）攔不住——查重把候選推到決策時點眼前，不是防重複的保證

set -euo pipefail

TITLE="${1:-}"
FROM="${2:-app}"
TO="${3:-backend}"
TAGS_RAW="${4:-}"
DEDUP_KEYWORDS="${5:-}"
# to 是否為呼叫端顯式指定——缺省採預設值時查重清單不過濾角色：手動呼叫最易漏傳
# to，此時以預設值過濾會漏列其他角色的重複交接、產出檔的 to: 本身也可能是錯的
TO_GIVEN=0
if [[ $# -ge 3 && -n "${3:-}" ]]; then TO_GIVEN=1; fi

if [[ -z "$TITLE" ]]; then
  echo "錯誤：缺少標題（第一個參數）" >&2
  echo "用法：new-handoff.sh \"<標題>\" [from] [to] [tag1,tag2,...]" >&2
  exit 1
fi

# 定位專案根：優先往上找最近的 CLAUDE.md/AGENTS.md，其次 git 根，最後當前目錄。
# 往上找到家目錄即停：家目錄可能放著全域規範檔（如 Codex 的 ~/AGENTS.md），專案
# 沒有標記檔時若不設界，會把家目錄誤認為專案根、檔案寫進 ~/docs/
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
  printf '%s\n' '' '投遞前有程式碼改動時，回覆請附主要修改檔案路徑清單（不論 `status`；暫離回報除外——branch 名即查證錨點），細節見 handoff SKILL reply 段。'
  printf '\n中途需切換任務時，請先投遞暫離回報——`status: partial`、內文附 branch 名與現況，之後回來再照常回覆。\n'
} > "$file"

echo "$file"

# ── 產檔查重（advisory，全走 stderr）────────────────────────────────
# 三不變條件：不改產出檔內容、不改 exit code、stdout 維持單行路徑——
# consistency-check C 項會在無 zoekt 的假 repo 實跑本腳本並丟棄 stderr，
# 守住三條件即零回歸。整段 fail-open：查重任何內部錯誤不阻斷產檔。
# 有效性為條件式：時間窗外、tshehtu 索引盲區（未 commit、一小時內新 commit、
# 未 discovery 的 repo）攔不住——查重把候選推到決策時點眼前，不是防重複的保證。
DEDUP_WINDOW_DAYS=14
DEDUP_LOCAL_MAX=8
DEDUP_KB_MAX=8
ZOEKT_URL="${KUNSU_ZOEKT_URL:-http://127.0.0.1:6070}"

dedup_check() {
  shopt -s nullglob
  local cutoff
  cutoff="$(date -v-"${DEDUP_WINDOW_DAYS}"d +%F 2>/dev/null || date -d "-${DEDUP_WINDOW_DAYS} days" +%F 2>/dev/null || echo "")"

  # 本地層：候選＝docs/handoffs/ 頂層＋archive/ 的交接本體（type: handoff）；
  # replies/、archive/replies/ 僅用於推導「已回覆」狀態——回覆檔 to: 是發起方，
  # 入候選過濾必致全滅
  local candidates=()
  local cand_count=0
  local f fhead fto fcreated ftitle fstatus fstem
  for f in "$HANDOFFS_DIR"/*.md "$HANDOFFS_DIR"/archive/*.md; do
    [[ "$f" == "$file" ]] && continue   # 剔除本次剛產出的檔案自身，否則必自我命中
    fstem="$(basename "$f" .md)"
    # 檔名日期前綴先濾（YYYY-MM-DD-<slug>.md 為本腳本自身命名慣例）：archive/
    # 單調成長，逐檔讀 frontmatter 的成本會隨歷史線性膨脹，窗外檔零成本跳過
    if [[ -n "$cutoff" && "${fstem:0:10}" < "$cutoff" ]]; then continue; fi
    fhead="$(sed -n '1,12p' "$f")"
    printf '%s\n' "$fhead" | grep -q '^type: handoff$' || continue
    fto="$(printf '%s\n' "$fhead" | sed -n 's/^to: //p' | head -1)"
    fcreated="$(printf '%s\n' "$fhead" | sed -n 's/^created: //p' | head -1)"
    ftitle="$(printf '%s\n' "$fhead" | sed -n 's/^title: //p' | head -1)"
    if [[ "$TO_GIVEN" -eq 1 && "$fto" != "$TO" ]]; then continue; fi
    if [[ -n "$cutoff" && -n "$fcreated" && "$fcreated" < "$cutoff" ]]; then continue; fi
    if [[ "$f" == */archive/* ]]; then
      fstatus="已歸檔"
    else
      local rhits=("$HANDOFFS_DIR/replies/${fstem}-reply-"*.md "$HANDOFFS_DIR/archive/replies/${fstem}-reply-"*.md)
      if [[ ${#rhits[@]} -gt 0 ]]; then fstatus="已回覆"; else fstatus="open"; fi
    fi
    if [[ "$TO_GIVEN" -eq 1 ]]; then
      candidates+=("${fcreated}｜${ftitle}｜[${fstatus}]")
    else
      candidates+=("${fcreated}｜${ftitle}｜[${fstatus}]｜to: ${fto}")
    fi
    cand_count=$((cand_count + 1))
  done

  if [[ "$cand_count" -gt 0 ]]; then
    if [[ "$TO_GIVEN" -eq 1 ]]; then
      echo "── 查重：近 ${DEDUP_WINDOW_DAYS} 天發給 ${TO} 的既有交接（${cand_count} 筆）──" >&2
    else
      echo "── 查重：近 ${DEDUP_WINDOW_DAYS} 天全部既有交接（${cand_count} 筆；to 未指定採預設 ${TO}，請確認收件角色）──" >&2
    fi
    local shown=0
    local line
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$shown" -lt "$DEDUP_LOCAL_MAX" ]]; then
        echo "  ${line}" >&2
      fi
      shown=$((shown + 1))
    done < <(printf '%s\n' "${candidates[@]}" | sort -r)
    if [[ "$cand_count" -gt "$DEDUP_LOCAL_MAX" ]]; then
      echo "  （另有 $((cand_count - DEDUP_LOCAL_MAX)) 筆未列出）" >&2
    fi
  elif [[ "$TO_GIVEN" -eq 0 ]]; then
    echo "ℹ to 未指定，採預設 ${TO}，請確認收件角色" >&2
  fi

  # tshehtu 層（zoekt 跨 repo 索引；軟依賴，降級一律顯式、不靜默）
  local kb_state="degrade"
  local kb_hits=0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ℹ 查重降級：python3 不可用，tshehtu 層略過（僅本地層生效）" >&2
  elif ! curl -s -m 2 "$ZOEKT_URL" >/dev/null 2>&1; then
    echo "ℹ 查重降級：tshehtu（${ZOEKT_URL}）未回應，跨 repo 層略過（僅本地層生效）" >&2
  else
    local kb_out
    kb_out="$(python3 - "$TITLE" "$DEDUP_KEYWORDS" "$ZOEKT_URL" "$DEDUP_KB_MAX" <<'PYEOF'
import json
import re
import sys
import urllib.request

title, kw_raw, base_url, maxn = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
STOP = {"查證", "更正", "裁示", "盤點", "確認", "建立", "交接", "回覆", "知會",
        "處理", "問題", "是否", "調查", "研究", "評估", "報告", "需求", "實作",
        "修正", "檢查", "清單", "項目"}
if kw_raw.strip():
    kws = [k for k in kw_raw.split() if k]
else:
    frags = re.split(r"[\s\-—_，。、：:／/()（）\[\]「」『』《》?？!！\"'·．.]+", title)
    kws = [f for f in frags if len(f) >= 2 and f not in STOP][:3]
if not kws:
    print("SKIP:標題抽不出有效關鍵詞")
    sys.exit(0)
query = "f:docs/ " + " ".join(kws)
try:
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/search",
        data=json.dumps({"Q": query}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=4) as resp:
        data = json.load(resp)
except Exception as e:
    print("DEGRADE:%s" % e.__class__.__name__)
    sys.exit(0)
if data.get("Error"):
    print("DEGRADE:zoekt query error")
    sys.exit(0)
files = (data.get("Result") or {}).get("Files") or []
print("QUERY:" + " ".join(kws))
print("COUNT:%d" % len(files))
for f in files[:maxn]:
    print("HIT:%s/%s" % (f.get("Repository", ""), f.get("FileName", "")))
PYEOF
)" || kb_out="DEGRADE:python 執行失敗"
    case "$kb_out" in
      SKIP:*)
        kb_state="skip"
        echo "ℹ tshehtu 層略過：${kb_out#SKIP:}（可以第 5 參數顯式給關鍵詞）" >&2
        ;;
      DEGRADE:*|"")
        kb_state="degrade"
        echo "ℹ 查重降級：tshehtu 查詢失敗（${kb_out#DEGRADE:}），跨 repo 層無結果" >&2
        ;;
      *)
        kb_state="ok"
        local kb_query kb_count
        kb_query="$(printf '%s\n' "$kb_out" | sed -n 's/^QUERY://p' | head -1)"
        kb_count="$(printf '%s\n' "$kb_out" | sed -n 's/^COUNT://p' | head -1)"
        kb_hits="${kb_count:-0}"
        if [[ "$kb_hits" -eq 0 ]]; then
          # 零命中也顯式——本地層有候選時整段沉默會使「跑了沒中」與「沒跑」同形
          echo "ℹ tshehtu：「${kb_query}」零命中" >&2
        fi
        if [[ "$kb_hits" -gt 0 ]]; then
          echo "── tshehtu：「${kb_query}」命中 ${kb_hits} 筆 ──" >&2
          printf '%s\n' "$kb_out" | sed -n 's/^HIT:/  /p' >&2
          if [[ "$kb_hits" -gt "$DEDUP_KB_MAX" ]]; then
            echo "  （另有 $((kb_hits - DEDUP_KB_MAX)) 筆未列出）" >&2
          fi
        fi
        ;;
    esac
  fi

  # 零命中顯式一行——區分「查重沒跑」與「跑了沒中」（訊號缺席不可與機制缺席同形）
  if [[ "$cand_count" -eq 0 && "$kb_hits" -eq 0 ]]; then
    if [[ "$kb_state" == "ok" ]]; then
      echo "ℹ 查重已執行：時間窗內無既有交接候選（兩層均零命中）" >&2
    else
      echo "ℹ 查重已執行：時間窗內無既有交接候選（tshehtu 層未生效，見上）" >&2
    fi
  else
    echo "⚠ 若上列既有交接／文件已涵蓋本次主題，請考慮撤回本檔（未 commit，rm 即可）並改讀既有結論" >&2
  fi
}
dedup_check || true

echo "ℹ 本腳本僅產檔；撰寫與查核指引（斷言層級紀律、引用檔名權威、更正交接）見 handoff SKILL.md add 段——未經 /handoff skill 執行時請回讀對應步驟" >&2
