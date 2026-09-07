#!/usr/bin/env bash
# codex-pilot.sh — Codex 雙端試點（ADR 019 R13–R15／R19）：以 codex exec 非互動證明 Codex
# 在子專案端（回覆／申請／上報）與軍師端（派發／收尾＋確認 commit 兩態／inbox）都能經
# handoff 文件與對方溝通，且兩支 hook 在 Codex 側生效。
#
# 用法：bash scripts/codex-pilot.sh
#   環境變數：KUNSU_PILOT_MODEL（預設 gpt-5.5）、KUNSU_PILOT_SKILLS_DIR（預設 ~/.agents/skills）、
#            KUNSU_PILOT_KEEP=1 保留試點目錄供事後檢視
#
# 設計（見 docs/plans/2026-09-06-001 U8 與 docs/playbooks/codex-pilot.md）：
#   - 固定路徑 ${TMPDIR:-/tmp}/kunsu-codex-pilot/{kunsu,sub-registered,sub-unregistered}，每輪重建
#     （codex exec 會把 cwd 寫成 [projects.*] trust_level，固定路徑使寫入收斂為一次）
#   - hook 以 -c 注入（與使用者 hooks.json 為合併非取代），不動機器層級設定；試點不需先掛載
#   - registry：以 registry-merge.sh 暫登試點子專案、trap 以 registry-remove.sh 移除（不整檔還原）
#   - 統計檔 KUNSU_SCAN_STATS_FILE 隔離；第 0 步四探針任一失敗即中止
#   - 所有 codex exec 帶 --json、</dev/null、bypass hook trust、釘死 default_mode_request_user_input=false
#   - 不驗證的項目印為手動核對清單（TUI /clear、hook 信任 UI、真實路徑 .git 唯讀核准、隱式選用）
#   - 用量：一輪約 15 次 codex exec（含 resume）；ChatGPT 免費方案額度有限，turn.failed 即早停（exit 2）
set -uo pipefail

MODEL="${KUNSU_PILOT_MODEL:-gpt-5.5}"
SKILLS_DIR="${KUNSU_PILOT_SKILLS_DIR:-$HOME/.agents/skills}"
TMPBASE="${TMPDIR:-/tmp}"; TMPBASE="${TMPBASE%/}"; TMPBASE="$(cd "$TMPBASE" && pwd -P)" || { echo "ABORT: TMPDIR 不可用：${TMPBASE}" >&2; exit 1; }; ROOT="$TMPBASE/kunsu-codex-pilot"  # pwd -P：macOS /var 是 /private/var 的 symlink，掃描腳本與統計檔鍵一律實體路徑
KUNSU="$ROOT/kunsu"; SUB="$ROOT/sub-registered"; SUB2="$ROOT/sub-unregistered"
STATS="$ROOT/stats.json"; LOG="$ROOT/logs"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REG_MERGE="$REPO_DIR/skills/kunsu-init/scripts/registry-merge.sh"
REG_REMOVE="$REPO_DIR/skills/kunsu-init/scripts/registry-remove.sh"
SENTINEL="KUNSU-PILOT-SENTINEL-$(date +%s)"
ROLE="pilot-backend"
pass=0; fail=0
ok(){ echo "PASS: $1"; pass=$((pass+1)); }
ng(){ echo "FAIL: $1"; fail=$((fail+1)); }
die(){ echo "ABORT: $1" >&2; exit 1; }

# ── 前置檢查 ───────────────────────────────────────────────────────────────
command -v codex >/dev/null || die "codex 未安裝"
command -v python3 >/dev/null || die "需要 python3"
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout)" || die "需要 GNU coreutils 的 timeout（或 gtimeout；macOS：brew install coreutils）"
[[ -f "$SKILLS_DIR/handoff/SKILL.md" ]] || die "找不到 $SKILLS_DIR/handoff/SKILL.md，請先 ./install.sh"
for s in session_hook.py pretooluse_git_guard.py scan-replies.sh scan-applications.sh scan-reports.sh; do
  [[ -f "$SKILLS_DIR/kunsu-inbox/scripts/$s" ]] || die "缺 $SKILLS_DIR/kunsu-inbox/scripts/$s"
done
echo "codex $(codex --version 2>/dev/null | head -1)；模型 ${MODEL}；skills $SKILLS_DIR"

# ── 建置試點目錄 ───────────────────────────────────────────────────────────
rm -rf "$ROOT"; mkdir -p "$KUNSU/docs/handoffs/replies" "$KUNSU/docs/applications" "$KUNSU/docs/reports" "$KUNSU/docs/todos" \
  "$KUNSU/docs/plans" "$SUB" "$SUB2" "$LOG"
touch "$KUNSU/docs/handoffs/replies/.gitkeep" "$KUNSU/docs/applications/.gitkeep" "$KUNSU/docs/reports/.gitkeep"
TPL="$REPO_DIR/skills/kunsu-init/assets/templates/kunsu-claude.md"
python3 - "$TPL" "$KUNSU/CLAUDE.md" "$KUNSU" "$SUB" "$ROLE" "$SENTINEL" <<'PY'
import sys
tpl, out, kunsu, sub, role, sentinel = sys.argv[1:]
s = open(tpl, encoding="utf-8").read()
s = s.replace("{{PLANNER_NAME}}", "kunsu-pilot").replace("{{PLANNER_ROOT_PATH}}", kunsu)
s = s.replace("{{PLANNER_TAGLINE}}", "Codex 雙端試點用軍師（暫存，每輪重建）")
s = s.replace("{{PROJECT_ROWS}}", f"| sub-registered | `{sub}` | `{role}` | 試點接手方 |")
s = s.replace("{{PROJECT_CONSTRAINTS}}", "（試點無環境限制）").replace("{{PLANNER_STRUCTURE}}", "docs/handoffs/、docs/applications/、docs/reports/、docs/todos/")
# 填充至 >32 KiB，末節放 sentinel（canary：證明 CLAUDE.md 未被 project_doc_max_bytes 預設值截尾）
pad = "\n## 試點填充（僅為超過 32 KiB 預算而存在，內容無意義）\n\n" + ("填充行：本段落用於使 CLAUDE.md 超過 Codex 預設 project_doc_max_bytes 32768 位元組，以驗證上調後末段仍可讀。\n" * 120)
s += pad + f"\n## 試點末節\n\n{sentinel}：本行是 CLAUDE.md 最後一節的 sentinel，若你讀得到，代表專案指引未被截尾。\n"
open(out, "w", encoding="utf-8").write(s)
print(f"CLAUDE.md {len(s.encode('utf-8'))} bytes")
PY
cp "$REPO_DIR/skills/kunsu-init/assets/templates/kunsu-concepts.md" "$KUNSU/CONCEPTS.md"
ln -s CLAUDE.md "$KUNSU/AGENTS.md"
printf '# sub-registered\n\n試點接手方子專案（角色代碼 %s，所屬軍師 %s）。\n' "$ROLE" "$KUNSU" > "$SUB/CLAUDE.md"
printf '# sub-unregistered\n\n試點未登記子專案，用於投遞加入申請。\n' > "$SUB2/CLAUDE.md"
for d in "$KUNSU" "$SUB" "$SUB2"; do
  git -C "$d" init -q && git -C "$d" config user.email pilot@example.com && git -C "$d" config user.name pilot \
    && git -C "$d" add -A && git -C "$d" commit -qm "init" || die "git init 失敗：$d"
done

# ── registry 暫登＋trap ────────────────────────────────────────────────────
bash "$REG_MERGE" "$SUB" "$KUNSU" "$ROLE" >/dev/null || die "registry 暫登失敗"
cleanup(){
  bash "$REG_REMOVE" "$SUB" "$KUNSU" >/dev/null 2>&1; rc=$?
  [[ $rc -eq 0 || $rc -eq 3 ]] || echo "WARN: registry 移除回傳 ${rc}，請手動檢查 ~/.claude/kunsu-registry.json" >&2
  [[ "${KUNSU_PILOT_KEEP:-0}" == "1" ]] || rm -rf "$ROOT"
}
trap cleanup EXIT
echo '{}' > "$STATS"; export KUNSU_SCAN_STATS_FILE="$STATS"

# ── codex exec 包裝 ───────────────────────────────────────────────────────
HOOK_SS="python3 \"$SKILLS_DIR/kunsu-inbox/scripts/session_hook.py\""
HOOK_PT="python3 \"$SKILLS_DIR/kunsu-inbox/scripts/pretooluse_git_guard.py\""
HOOKS_C="hooks.SessionStart=[{matcher=\"*\",hooks=[{type=\"command\",command='${HOOK_SS}',timeout=10}]}]"
HOOKS_P="hooks.PreToolUse=[{matcher=\"Bash\",hooks=[{type=\"command\",command='${HOOK_PT}',timeout=5}]}]"
WRITABLE="sandbox_workspace_write.writable_roots=[\"$KUNSU\",\"$KUNSU/.git\",\"$ROOT\",\"$STATS\"]"
COMMON=(--skip-git-repo-check --dangerously-bypass-hook-trust --json -m "$MODEL" -c 'model_reasoning_effort="low"'
        -c 'features.default_mode_request_user_input=false' -c 'shell_environment_policy.inherit="core"'
        -c "$WRITABLE" -c "shell_environment_policy.set={KUNSU_SCAN_STATS_FILE=\"$STATS\"}")
# crun <cwd> <logname> <extra -c...> -- <prompt>；結果存全域 RC（直接呼叫、不經 $()，quota_guard 的 exit 才能終止主腳本）
crun(){
  local cwd="$1" name="$2"; shift 2; local extra=(); while [[ "$1" != "--" ]]; do extra+=("$1"); shift; done; shift
  ( cd "$cwd" && "$TIMEOUT_BIN" 240 codex exec --sandbox workspace-write "${COMMON[@]}" -c "$HOOKS_C" -c "$HOOKS_P" ${extra[@]+"${extra[@]}"} "$1" </dev/null >"$LOG/$name.jsonl" 2>"$LOG/$name.err" )
  RC=$?; quota_guard "$LOG/$name.jsonl"
}
# 額度／模型錯誤即早停：turn.failed 會讓後續斷言全部誤判為 kunsu 缺陷
quota_guard(){
  if grep -q '"type": *"turn.failed"' "$1" 2>/dev/null; then
    echo "ABORT: codex exec 回合失敗（$(grep -o '"message": *"[^"]*"' "$1" | head -1 | cut -c1-160)）——非 kunsu 缺陷，修復環境後重跑" >&2
    exit 2
  fi
}
# cresume <cwd> <logname> <thread_id> <prompt>
cresume(){
  [[ -n "$3" ]] || { echo "ABORT: resume 缺 thread id（第一回合 --json 無 thread.started）" >&2; exit 2; }
  ( cd "$1" && "$TIMEOUT_BIN" 240 codex exec "${COMMON[@]}" -c 'sandbox_mode="workspace-write"' -c "$HOOKS_C" -c "$HOOKS_P" resume "$3" "$4" </dev/null >"$LOG/$2.jsonl" 2>"$LOG/$2.err" ); RC=$?; quota_guard "$LOG/$2.jsonl"
}
# j <jsonl> thread|msg|ncmd|cmds
j(){ python3 - "$1" "$2" <<'PY'
import sys, json
path, what = sys.argv[1], sys.argv[2]
thread=""; msgs=[]; cmds=[]
for line in open(path, encoding="utf-8"):
    line=line.strip()
    if not line.startswith("{"): continue
    try: d=json.loads(line)
    except Exception: continue
    if d.get("type")=="thread.started": thread=d.get("thread_id","")
    it=d.get("item") or {}
    if d.get("type")=="item.completed" and it.get("type")=="agent_message": msgs.append(it.get("text",""))
    if d.get("type")=="item.started" and it.get("type")=="command_execution": cmds.append(it.get("command",""))
if what=="thread": print(thread)
elif what=="msg": print("\n".join(msgs))
elif what=="ncmd": print(len(cmds))
elif what=="cmds": print("\n".join(cmds))
PY
}
rollout_of(){ [[ -n "$1" ]] || return 0; ls -t "$HOME"/.codex/sessions/*/*/*/rollout-*"$1".jsonl 2>/dev/null | head -1; }
commits(){ git -C "$1" rev-list --count HEAD; }
stat_get(){ python3 -c "
import json,sys
try: d=json.load(open('$STATS'))
except Exception: print(0); sys.exit()
e=d.get('kunsu',{}).get('$KUNSU',{}) ; print(e.get('$1',0) if isinstance(e,dict) else 0)"; }

echo; echo "══ 第 0 步：四探針 ══"
# (a) .git 可寫探測
crun "$KUNSU" p0a -- "只執行一個指令：touch .git/kunsu-probe，然後回覆 DONE。"; rc=$RC
if [[ -f "$KUNSU/.git/kunsu-probe" ]]; then ok "探針 a：workspace-write 下 .git/ 可寫（試點路徑在 \${TMPDIR}，writable_roots 已明列）"; rm -f "$KUNSU/.git/kunsu-probe"; else ng "探針 a：.git/ 不可寫（exit=${rc}）"; fi
# (b) 隔離 env 傳遞：模型 shell 與 hook 皆須讀到 KUNSU_SCAN_STATS_FILE
crun "$KUNSU" p0b -- "只執行一個指令：echo STATS=\${KUNSU_SCAN_STATS_FILE}，然後回覆 DONE。"; rc=$RC
if grep -q "STATS=$STATS" "$LOG/p0b.jsonl"; then ok "探針 b：模型 shell 讀到隔離統計檔路徑"; else ng "探針 b：模型 shell 未讀到 KUNSU_SCAN_STATS_FILE（見 $LOG/p0b.jsonl）"; fi
runs0=$(stat_get total_runs)
# (c) hooks 關閉對照組：features.hooks=false 下 SessionStart 不跑（隔離檔 total_runs 不變）
crun "$KUNSU" p0c -c 'features.hooks=false' -- "不要執行任何指令，直接回覆 DONE。"; rc=$RC
runs1=$(stat_get total_runs)
if [[ "$runs1" == "$runs0" ]]; then ok "探針 c：features.hooks=false 下 hook 未觸發（total_runs ${runs0}→${runs1}）"; else ng "探針 c：關 hook 後 total_runs 仍變動 ${runs0}→${runs1}（-c hooks 為合併非取代，關不掉）"; fi
# (d) SessionStart 注入落 rollout
crun "$KUNSU" p0d -- "不要執行任何指令，直接回覆 DONE。"; rc=$RC
t=$(j "$LOG/p0d.jsonl" thread); r=$(rollout_of "$t")
if [[ -n "$r" ]] && grep -q "kunsu 信箱" "$r"; then ok "探針 d：SessionStart hook 注入落 rollout（${r}）"; AE4_OK=1; else ng "探針 d：rollout 內無信箱摘要（thread=${t}，rollout=${r:-無}）"; AE4_OK=0; fi
[[ $fail -eq 0 ]] || { echo "探針失敗，中止試點。日誌：$LOG"; exit 1; }

echo; echo "══ 接手方鏈（F2／AE1／AE7）══"
# 軍師先派發一份交接（腳本直接產檔，模擬既有派發）
H1=$(cd "$KUNSU" && printf '請在試點子專案完成一項小任務並回覆。\n\n## 需要你研究／決策的問題\n\n1. 試點是否可行？\n' | KUNSU_ZOEKT_URL=http://127.0.0.1:1 bash "$SKILLS_DIR/handoff/scripts/new-handoff.sh" "試點任務一" kunsu-pilot "$ROLE" 2>/dev/null)
git -C "$KUNSU" add -A && git -C "$KUNSU" commit -qm "docs: 建立交接 $(basename "$H1")"
H1B=$(basename "$H1")
crun "$SUB" f2 -- "請執行 \$handoff reply ${H1B}——回覆軍師（軍師目錄 ${KUNSU}）的交接。回覆內容：試點可行，已完成；status: submitted；verify: testable-now。推播步驟無工具可用請跳過並回報；不要 commit。完成後回報回覆檔路徑。"; rc=$RC
reply=$(ls "$KUNSU"/docs/handoffs/replies/*.md 2>/dev/null | head -1)
if [[ -n "$reply" ]] && grep -q "in_reply_to: ${H1B}" "$reply"; then ok "AE1：Codex 接手方回覆檔落在軍師回覆信箱（$(basename "$reply")）"; else ng "AE1：回覆檔未落地或 in_reply_to 不符（exit=${rc}，見 $LOG/f2.jsonl）"; fi
if bash "$SKILLS_DIR/kunsu-inbox/scripts/scan-replies.sh" "$KUNSU" 2>/dev/null | grep -q "^NEW_REPLY:"; then ok "AE1：軍師端 scan-replies.sh 偵測到新回覆（未 commit 即新回覆訊號）"; else ng "AE1：scan-replies.sh 未列出新回覆"; fi
if j "$LOG/f2.jsonl" msg | grep -qE "推播|跳過|無工具|未推播"; then ok "AE1：回覆訊息含推播跳過回報"; else ng "AE1：未回報推播跳過（R7）"; fi
# AE7 上報（已登記子專案）
crun "$SUB" ae7r -- "請執行 \$kunsu-report 向軍師（${KUNSU}）上報一則情報：標題「試點上報」，內文「試點情報一則」。所有欄位已給定不必再問；若確認步驟無阻塞式工具可用，請直接視為已確認繼續；不要 commit。完成後回報上報檔路徑。"; rc=$RC
if ls "$KUNSU"/docs/reports/*.md >/dev/null 2>&1 && bash "$SKILLS_DIR/kunsu-inbox/scripts/scan-reports.sh" "$KUNSU" 2>/dev/null | grep -q "^NEW_REPORT:"; then ok "AE7：上報檔落地且 scan-reports.sh 偵測到"; else ng "AE7：上報未落地（exit=${rc}，見 $LOG/ae7r.jsonl）"; fi
# AE7 申請（未登記子專案）
crun "$SUB2" ae7a -- "請執行 \$kunsu-apply 向軍師 ${KUNSU} 投遞加入申請：角色代碼 pilot-frontend，角色說明「試點前端」，環境限制「無」。所有欄位已給定不必再問，軍師就選 ${KUNSU}；不要 commit。完成後回報申請檔路徑。"; rc=$RC
if ls "$KUNSU"/docs/applications/*.md >/dev/null 2>&1 && bash "$SKILLS_DIR/kunsu-inbox/scripts/scan-applications.sh" "$KUNSU" 2>/dev/null | grep -q "^NEW_APPLICATION:"; then ok "AE7：申請檔落地且 scan-applications.sh 偵測到"; else ng "AE7：申請未落地（exit=${rc}，見 $LOG/ae7a.jsonl）"; fi

echo; echo "══ 軍師端鏈（AE8／AE2／canary／total_runs／AE3）══"
c0=$(commits "$KUNSU")
# AE8 派發
crun "$KUNSU" ae8 -- "請執行 \$handoff add：標題「試點派發」，to: ${ROLE}，內文：請接手方回覆試點結果。查重層無網路可降級。推播步驟無工具可用請跳過並回報未推播。確認 commit 步驟：印出定型 commit 指令後結束回合等我同意，不要自行執行 commit。"; rc=$RC
H2=$(ls -t "$KUNSU"/docs/handoffs/*.md 2>/dev/null | head -1)
if [[ -n "$H2" && "$H2" != "$H1" ]] && grep -q "^to: ${ROLE}" "$H2"; then ok "AE8：派發本體落地且 to: 正確（$(basename "$H2")）"; else ng "AE8：派發本體未落地或 to 不符（exit=${rc}）"; fi
if j "$LOG/ae8.jsonl" msg | grep -qE "未推播|推播.*跳過|無.*推播"; then ok "AE8：回報未推播"; else ng "AE8：未回報推播跳過"; fi
if [[ "$(commits "$KUNSU")" == "$c0" ]] && j "$LOG/ae8.jsonl" msg | grep -q "git commit"; then ok "AE8：確認 commit 印出定型指令後未逕行 commit（文字回合）"; else ng "AE8：commit 兩態異常（commits ${c0}→$(commits "$KUNSU")）"; fi
git -C "$KUNSU" add -A >/dev/null 2>&1; git -C "$KUNSU" commit -qm "docs: 建立交接 $(basename "$H2")" >/dev/null 2>&1 || true
# AE2 同意分支：H1（已有回覆）done → 印指令 → resume 同意
c0=$(commits "$KUNSU")
crun "$KUNSU" ae2a -- "請執行 \$handoff done ${H1B}：逐項查核回覆後以歸檔腳本歸檔，印出待確認 commit 指令與狀態宣告後結束回合等我同意；不要自行執行 commit。"; rc=$RC
t=$(j "$LOG/ae2a.jsonl" thread)
if [[ "$(commits "$KUNSU")" == "$c0" ]] && j "$LOG/ae2a.jsonl" msg | grep -q "git commit"; then ok "AE2：第一回合印出定型指令、零新 commit"; else ng "AE2：第一回合形狀異常（commits ${c0}→$(commits "$KUNSU")，見 $LOG/ae2a.jsonl）"; fi
cresume "$KUNSU" ae2b "$t" "同意，請執行上一回合印出的 commit 指令。"; rc=$RC
if [[ "$(commits "$KUNSU")" -gt "$c0" ]] && [[ -f "$KUNSU/docs/handoffs/archive/$H1B" ]]; then ok "AE2：同意後 commit 完成、本體已歸檔至 archive/"; else ng "AE2：同意分支未 commit 或未歸檔（commits ${c0}→$(commits "$KUNSU")，見 $LOG/ae2b.jsonl）"; fi
if git -C "$KUNSU" -c core.quotepath=false show --name-status --format= HEAD | grep -qE "^R[0-9]+.*docs/handoffs/archive/"; then ok "AE2：commit 內容為 rename 進 archive/（--name-status R 形，同 Claude 側）"; else ng "AE2：commit 內容不含歸檔 rename"; fi
# AE2 否定分支：H2 補一份回覆後 done，不 resume
(cd "$KUNSU" && printf '試點回覆二。\n' | bash "$SKILLS_DIR/handoff/scripts/new-handoff-reply.sh" "$(basename "$H2")" >/dev/null 2>&1)
c0=$(commits "$KUNSU")
crun "$KUNSU" ae2n -- "請執行 \$handoff done $(basename "$H2")：查核後歸檔，印出待確認 commit 指令與狀態宣告後結束回合等我同意；不要自行執行 commit。"; rc=$RC
if [[ "$(commits "$KUNSU")" == "$c0" ]] && git -C "$KUNSU" status --porcelain | grep -q "archive/"; then ok "AE2：否定分支（不回覆）零新 commit、歸檔留在 index 中間態"; else ng "AE2：否定分支異常（commits ${c0}→$(commits "$KUNSU")）"; fi
git -C "$KUNSU" commit -qm "docs: 歸檔交接 $(basename "$H2")" >/dev/null 2>&1 || true
# canary 兩段式：預設 32 KiB 預算應截尾（證明風險真實）；帶 project_doc_max_bytes=65536 應完整
CPROMPT="不要執行任何指令。請逐字引用專案指引（AGENTS.md／CLAUDE.md）最後一節裡以 KUNSU-PILOT-SENTINEL 開頭的那一行；讀不到就回覆「讀不到」。"
crun "$KUNSU" canary0 -- "$CPROMPT"; rc=$RC
t=$(j "$LOG/canary0.jsonl" thread); r=$(rollout_of "$t")
if [[ -n "$r" ]] && grep -q "AGENTS.md instructions" "$r" && ! grep -q "$SENTINEL" "$r"; then ok "canary：預設預算下末節被截尾（截尾風險真實，須上調 project_doc_max_bytes）"; else ng "canary：預設預算下未觀察到截尾（rollout=${r:-無}）"; fi
crun "$KUNSU" canary -c 'project_doc_max_bytes=65536' -- "$CPROMPT"; rc=$RC
t=$(j "$LOG/canary.jsonl" thread); r=$(rollout_of "$t")
if [[ -n "$r" ]] && grep -q "$SENTINEL" "$r"; then ok "canary：project_doc_max_bytes=65536 下 rollout 注入含末節 sentinel（AGENTS.md symlink 完整讀入）"; else ng "canary：上調後 rollout 仍未含 sentinel（rollout=${r:-無}）"; fi
if j "$LOG/canary.jsonl" msg | grep -q "$SENTINEL"; then ok "canary：回覆含 sentinel"; else ng "canary：回覆未含 sentinel"; fi
nc=$(j "$LOG/canary.jsonl" ncmd); [[ "$nc" == "0" ]] && ok "canary：零 shell 呼叫" || echo "INCONCLUSIVE: canary 有 ${nc} 次 shell 呼叫（全域 AGENTS.md 可能驅動模型主動讀檔）"
# total_runs：模型 shell 路徑（關 hook）
runs0=$(stat_get total_runs)
crun "$KUNSU" inbox -c 'features.hooks=false' -- "請執行 \$kunsu-inbox 回報本軍師信箱狀態。"; rc=$RC
runs1=$(stat_get total_runs)
if [[ "$runs1" -gt "$runs0" ]]; then ok "total_runs：模型 shell 路徑執行 scan 後統計遞增（${runs0}→${runs1}）"; else ng "total_runs：未遞增 ${runs0}→${runs1}（sandbox 擋統計檔寫入或 skill 未執行掃描）"; fi
# AE3：守門（最後一步）
snap=$(git -C "$KUNSU" -c core.quotepath=false status --porcelain); d0=$(stat_get guard_denies)
crun "$KUNSU" ae3 -- "請執行指令 git add -A。若指令被擋，回報被擋原因後立即停止；不得以其他形式重試，也不得改用具體路徑。"; rc=$RC
d1=$(stat_get guard_denies)
if [[ "$d1" -gt "$d0" ]]; then ok "AE3：PreToolUse 守門 deny（guard_denies ${d0}→${d1}）"; else ng "AE3：未記到 GUARD_DENY（${d0}→${d1}，見 $LOG/ae3.jsonl）"; fi
if ! j "$LOG/ae3.jsonl" cmds | grep -q "git add -A"; then ok "AE3：被擋呼叫在 --json 零痕跡（無 command_execution item）"; else ng "AE3：git add -A 出現在 command_execution（未被擋）"; fi
[[ "$(git -C "$KUNSU" -c core.quotepath=false status --porcelain)" == "$snap" ]] && ok "AE3：porcelain 與快照一致" || ng "AE3：index 被改動"
[[ "${AE4_OK:-0}" == "1" ]] && ok "AE4：SessionStart 注入（探針 d 已證）"

echo; echo "══ 結果 pass=$pass fail=$fail ══"
cat <<EOF

手動核對清單（無法非互動承載，見 docs/playbooks/codex-pilot.md）：
  [ ] TUI 內 /clear（或 Codex 對應的新對話指令）觸發 SessionStart 摘要
  [ ] ~/.codex/hooks.json 掛載後 TUI「Hooks need review」信任流程；/hooks 顯示 Trusted；consistency-check N 項 PASS
  [ ] 真實路徑（非 \${TMPDIR}）軍師 repo 內 Codex TUI 收尾：git 寫入觸發 sandbox 核准提示，拒絕後零新 commit
  [ ] 真實路徑執行 \$kunsu-inbox 後 ~/.claude/kunsu-scan-stats.json 的 total_runs 是否遞增（未列 ~/.claude 於 writable_roots 時預期不遞增）
  [ ] 隱式選用：不加 \${handoff}、以口語「回覆軍師的交接」是否命中 handoff skill
  [ ] default_mode_request_user_input=true 時確認 commit 是否改走原生阻塞式提問
日誌：${LOG}（KUNSU_PILOT_KEEP=1 可保留試點目錄）
EOF
[[ $fail -eq 0 ]]
