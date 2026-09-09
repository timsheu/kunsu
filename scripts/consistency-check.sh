#!/usr/bin/env bash
# consistency-check.sh — kunsu 母體跨檔案一致性機械檢查
#
# 沉澱自 2026-08-12 跨功能邏輯連結稽核的機械層（詳見 CLAUDE.md 開發狀態同日條目）。
# 檢查「來源之間是否一致」而非寫死期望值，升版不需回頭改本腳本。
#
# 用法：bash scripts/consistency-check.sh
# exit code：0 = 全數 PASS（WARN 不影響）；1 = 任一 FAIL
#
# 檢查項目：
#   A. 版號鏈——skill frontmatter version 與依賴聲明、CLAUDE.md 專案結構行一致
#   B. 回覆檔 status 值域副本——三檔各含四值值域行與「勿自標」限制語
#   C. 定型文字實跑比對——mktemp 假 repo 實跑 new-handoff.sh，產出檔的值域長句
#      與暫離提示行須與 SKILL.md 範例段逐字一致（兩副本同步紀律）
#   D. install.sh 覆蓋全部 skills/ 目錄
#   E. 沙盤分類 = kunsu-inbox 4a 詞彙對映
#   F. 範本 dataview 交接區塊使用 created 欄位（handoff frontmatter 無 date 欄）
#   G. 已修正漂移的防回歸——kunsu-init 不得再現「六步驟」
#   H. live 軍師同步抽查（WARN 級，經 ~/.claude/kunsu-registry.json 動態發現，
#      registry 不存在時靜默略過）——各軍師 CLAUDE.md 含最近一波遷移標記
#   I. 確認 commit 宣告範圍定型（ADR 018）——四載體（handoff SKILL、範本、兩支
#      歸檔腳本 echo）的定型指令均為 -m 在 -- 之前的 pathspec 形，防回退錯序
#   J. 產檔查重與 todo 歸檔腳本錨點——查重零命中定型行、archive-todo 旗標與範本指路句
#   K. reply 腳本 stderr 條款行實跑比對——在 C 項 fixture 內實跑 new-handoff-reply.sh，
#      stderr 須含產出檔的修改檔案清單定型行（實跑比對而非比原始碼字面：echo 雙引號
#      會把反引號當指令替換、輸出已壞而字面 grep 仍命中）
#   L. 字面中性化（ADR 019）——七份 SKILL.md 與範本兩檔，去 frontmatter、Agent 對應表區塊
#      與 fenced code block 後，Claude Code 專屬字面（AskUserQuestion／ListAgents／SendMessage／
#      $CLAUDE_SKILL_DIR／~/.claude/settings.json／~/.claude/skills／錨定樣式的斜線呼叫形）裸出現即 FAIL
#   M. Agent 對應表七份逐字一致——以 handoff SKILL 的區塊為基準兩兩比對
#   N. Codex hook 信任索引漂移（WARN 級，~/.codex 不存在時靜默略過）——hooks.json 內 kunsu 條目的
#      群組索引須與 config.toml hooks.state 鍵一致，否則 hook 靜默略過
#   O. install.sh 實跑六場景（KUNSU_INSTALL_HOME 隔離）——無 ~/.codex 只部署 Claude 樹、有 ~/.codex 建兩樹、
#      同名非 kunsu 目錄整批中止零改動、懸空 symlink 安全覆寫、--adopt（KUNSU_INSTALL_YES=1）採納寫標記、重跑冪等
#      另 H 項對 live 軍師 CLAUDE.md 大小達 project_doc_max_bytes（65536）80% 即 WARN（Codex 靜默截尾）

set -u
cd "$(dirname "$0")/.." || exit 1

pass=0; fail=0; warn=0
ok(){ echo "PASS: $1"; pass=$((pass+1)); }
ng(){ echo "FAIL: $1"; fail=$((fail+1)); }
wn(){ echo "WARN: $1"; warn=$((warn+1)); }

# --- A. 版號鏈 ---
hv="$(grep -m1 '^version:' skills/handoff/SKILL.md | awk '{print $2}')"
iv="$(grep -o 'handoff` skill（v[0-9.]*' skills/kunsu-inbox/SKILL.md | head -1 | grep -o '[0-9.]*$')"
cv="$(grep -o '通用交接原語（v[0-9.]*' CLAUDE.md | head -1 | grep -o '[0-9.]*$')"
if [[ "${hv}" == "${iv}" && "${hv}" == "${cv}" ]]; then
  ok "A1 handoff 版號鏈一致（${hv}）"
else
  ng "A1 handoff 版號鏈不一致（SKILL=${hv} 依賴聲明=${iv} CLAUDE.md=${cv}）"
fi

tv="$(grep -m1 '^version:' skills/todo/SKILL.md | awk '{print $2}')"
tc="$(grep -o 'TODO 清單管理原語（v[0-9.]*' CLAUDE.md | head -1 | grep -o '[0-9.]*$')"
if [[ "${tv}" == "${tc}" ]]; then
  ok "A2 todo 版號鏈一致（${tv}）"
else
  ng "A2 todo 版號鏈不一致（SKILL=${tv} CLAUDE.md=${tc}）"
fi

# --- B. status 值域副本（含種子沉澱文件——2026-08-13 發現的第五份副本，見開發狀態）---
for f in "skills/handoff/SKILL.md" \
         "skills/handoff/scripts/new-handoff.sh" \
         "skills/kunsu-init/assets/templates/kunsu-claude.md" \
         "skills/kunsu-init/assets/solutions/conventions/cross-repo-handoff-reply-inbox-convention.md"; do
  v="$(grep -c 'submitted.*partial.*blocked' "${f}" || true)"
  z="$(grep -c '勿自標\|請勿自標\|不自標' "${f}" || true)"
  if [[ "${v}" -ge 1 && "${z}" -ge 1 ]]; then
    ok "B  值域副本齊全：${f}（值域行 ${v}、勿自標 ${z}）"
  else
    ng "B  值域副本缺漏：${f}（值域行 ${v}、勿自標 ${z}）"
  fi
done

# --- C. 定型文字實跑比對 ---
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
if (cd "${tmp}" && git init -q . \
    && echo "一致性檢查內文" | KUNSU_ZOEKT_URL="http://127.0.0.1:1" bash "${OLDPWD}/skills/handoff/scripts/new-handoff.sh" "一致性檢查" >/dev/null 2>&1); then
  gen="$(ls "${tmp}"/docs/handoffs/*.md 2>/dev/null | head -1)"
  for sentence in '回覆檔 `status` 值：' '中途需切換任務時' '投遞前有程式碼改動時，回覆請附'; do
    a="$(grep -F "${sentence}" "${gen}" | head -1 | sed 's/^[[:space:]]*//')"
    b="$(grep -F "${sentence}" skills/handoff/SKILL.md | head -1 | sed 's/^[[:space:]]*//')"
    if [[ -n "${a}" && "${a}" == "${b}" ]]; then
      ok "C  定型文字兩副本逐字一致：「${sentence}…」"
    else
      ng "C  定型文字兩副本不一致或缺失：「${sentence}…」（產生器與 SKILL.md 範例段須連動修改）"
    fi
  done
  # --- C2. depends_on 第 6 參數實跑（2026-09-08）：欄位存在且位於 tags: 之後、flow 形 ---
  if (cd "${tmp}" && echo "x" | KUNSU_ZOEKT_URL="http://127.0.0.1:1" bash "${OLDPWD}/skills/handoff/scripts/new-handoff.sh" "依賴檢查" "" "" "" "" "a.md, b.md,a.md" >/dev/null 2>&1); then
    gen2="$(ls "${tmp}"/docs/handoffs/*依賴檢查*.md 2>/dev/null | head -1)"
    tl="$(grep -n '^tags:' "${gen2}" | cut -d: -f1)"
    dl="$(grep -n '^depends_on: \[a.md, b.md\]$' "${gen2}" | cut -d: -f1)"
    if [[ -n "${tl}" && -n "${dl}" && "${dl}" -eq $((tl + 1)) ]]; then
      ok "C2 depends_on 第 6 參數寫入 flow 形、去重、緊接 tags: 之後"
    else
      ng "C2 depends_on 欄位缺失、未去重或位置不在 tags: 之後（查重 12 行窗口會漏檔）"
    fi
  else
    ng "C2 new-handoff.sh 帶第 6 參數實跑失敗"
  fi
  # --- K. reply 腳本 stderr 條款行實跑比對（2026-09-01）---
  a="$(grep -F '投遞前有程式碼改動時，回覆請附' "${gen}" | head -1 | sed 's/^[[:space:]]*//')"
  if [[ -n "${a}" ]] \
      && (cd "${tmp}" && echo "一致性檢查回覆" | bash "${OLDPWD}/skills/handoff/scripts/new-handoff-reply.sh" "${gen}" >/dev/null 2>"${tmp}/reply.err") \
      && grep -qF "${a}" "${tmp}/reply.err"; then
    ok "K  reply 腳本 stderr 條款行與產出檔定型行逐字一致（實跑比對，對引號語意免疫）"
  else
    ng "K  reply 腳本 stderr 條款行缺失或與定型行不一致（須以單引號 printf 輸出；雙引號 echo 會吞反引號，靜態字面比對看不見）"
  fi
else
  ng "C  new-handoff.sh 實跑產檔失敗，無法比對定型文字"
fi

# --- D. install.sh 覆蓋 ---
for d in skills/*/; do
  n="$(basename "${d}")"
  if grep -q "${n}" install.sh; then
    ok "D  install.sh 覆蓋 ${n}"
  else
    ng "D  install.sh 未覆蓋 ${n}"
  fi
done
if grep -q '\.claude/skills' install.sh && grep -q '\.agents/skills' install.sh; then
  ok "D  install.sh 含兩個部署目標（~/.claude/skills 與 ~/.agents/skills，ADR 019）"
else
  ng "D  install.sh 缺部署目標字面（須同時含 .claude/skills 與 .agents/skills）"
fi

# --- E. 沙盤分類 = kunsu-inbox 4a ---
e1="$(grep -c 'not_picked_up\|partial_done' skills/kunsu-dashboard/app/subrepo_status.py || true)"
e2="$(grep -c '未接手\|部分完成' skills/kunsu-inbox/SKILL.md || true)"
if [[ "${e1}" -ge 2 && "${e2}" -ge 1 ]]; then
  ok "E  沙盤分類與 kunsu-inbox 4a 詞彙對映存在（py ${e1}、SKILL ${e2}）"
else
  ng "E  沙盤分類與 kunsu-inbox 4a 詞彙對映缺失（py ${e1}、SKILL ${e2}）"
fi

# --- F. 範本 dataview 欄位 ---
if grep -q 'SORT created DESC' skills/kunsu-init/assets/templates/home-dataview-handoffs.md \
   && ! grep -q 'SORT date DESC' skills/kunsu-init/assets/templates/home-dataview-handoffs.md; then
  ok "F  範本交接 dataview 使用 created 欄位"
else
  ng "F  範本交接 dataview 欄位錯誤（handoff frontmatter 無 date 欄，須用 created）"
fi

# --- G. 已修正漂移防回歸 ---
g1="$(grep -c '六步驟' skills/kunsu-init/SKILL.md || true)"
if [[ "${g1}" -eq 0 ]]; then
  ok "G  kunsu-init 無「六步驟」殘留（步驟數以範本為準，引用處已去計數化）"
else
  ng "G  kunsu-init 出現「六步驟」${g1} 處（2026-08-12 稽核已去計數化，疑似回歸）"
fi

# --- I. 確認 commit 宣告範圍定型（ADR 018）---
i1="$(grep -cF 'git commit -m "<固定格式訊息>" -- ' skills/handoff/SKILL.md || true)"
i2="$(grep -cF 'git commit -m "docs: 歸檔上報 <檔名>" -- ' skills/kunsu-init/assets/templates/kunsu-claude.md || true)"
i3="$(grep -cF 'git commit -m \"$msg\" --' skills/handoff/scripts/archive-handoff.sh || true)"
i4="$(grep -cF 'git commit -m \"$msg\" --' skills/kunsu-inbox/scripts/archive-report.sh || true)"
if [[ "${i1}" -ge 1 && "${i2}" -ge 1 && "${i3}" -ge 1 && "${i4}" -ge 1 ]]; then
  ok "I  確認 commit 定型四載體均為 pathspec 形（-m 在 -- 之前）"
else
  ng "I  確認 commit 定型載體缺 pathspec 形（SKILL=${i1} 範本=${i2} archive-handoff=${i3} archive-report=${i4}；-- 之後一切都被解析為 pathspec，-m 誤置其後必以 pathspec 錯誤失敗）"
fi

# --- J. 產檔查重與 todo 歸檔腳本錨點（2026-09-01）---
j1="$(grep -cF '查重已執行' skills/handoff/scripts/new-handoff.sh || true)"
j2="$(grep -cF -- '--from-handoff' skills/todo/scripts/archive-todo.sh || true)"
j3="$(grep -cF -- '--precheck' skills/handoff/scripts/archive-handoff.sh || true)"
j4="$(grep -cF '一併收尾 todo' skills/handoff/scripts/archive-handoff.sh || true)"
j5="$(grep -cF 'archive-todo' skills/kunsu-init/assets/templates/kunsu-concepts.md || true)"
if [[ "${j1}" -ge 1 && "${j2}" -ge 1 && "${j3}" -ge 1 && "${j4}" -ge 1 && "${j5}" -ge 1 ]]; then
  ok "J  查重零命中定型行、todo 歸檔／聚合與範本指路句錨點齊備"
else
  ng "J  查重／todo 歸檔錨點缺失（查重已執行=${j1} from-handoff=${j2} precheck=${j3} 聚合註記=${j4} 範本指路=${j5}；缺失代表文件教的與腳本印的已分岔）"
fi

# --- L. 字面中性化（ADR 019）：SKILL.md 與範本內文不得裸寫 Claude Code 專屬字面 ---
# 排除：frontmatter（description 觸發詞、allowed-tools）、「## Agent 對應表」區塊、fenced code block。
# 斜線呼叫形以錨定樣式比對（前導行首／空白／全形括號引號，後接 skill 名，再接空白／全形標點／行尾），
# 避免誤中 docs/handoffs/、skills/handoff 等路徑；增列 skill 名時同步改下方 SLASH 樣式。
if command -v python3 >/dev/null; then
  l_out="$(python3 - <<'PYL'
import re
files = ["skills/handoff/SKILL.md","skills/todo/SKILL.md","skills/kunsu-init/SKILL.md","skills/kunsu-inbox/SKILL.md",
         "skills/kunsu-apply/SKILL.md","skills/kunsu-report/SKILL.md","skills/kunsu-list/SKILL.md",
         "skills/kunsu-init/assets/templates/kunsu-claude.md","skills/kunsu-init/assets/templates/kunsu-concepts.md"]
LITERALS = ["AskUserQuestion","ListAgents","SendMessage","$CLAUDE_SKILL_DIR","~/.claude/settings.json","~/.claude/skills"]
SLASH = re.compile(r'(?:^|[\s（「：(])/(?:handoff|todo|kunsu-(?:init|inbox|apply|report|list)|kb|ce-[a-z-]+)(?:[\s）」、。)]|$)', re.M)
bad = []
for f in files:
    try:
        s = open(f, encoding="utf-8").read()
    except Exception as e:
        bad.append(f"{f}: 無法讀取（{e}）"); continue
    if s.startswith("---"):
        parts = s.split("\n---\n", 1); s = parts[1] if len(parts) == 2 else s
    s = re.sub(r'^## Agent 對應表.*?(?=^## )', '', s, flags=re.S | re.M)
    s = re.sub(r'^```.*?^```[ \t]*$', '', s, flags=re.S | re.M)
    hits = [lit for lit in LITERALS if lit in s]
    n_slash = len(SLASH.findall(s))
    if hits or n_slash:
        bad.append(f"{f}: {','.join(hits)}{' slash=' + str(n_slash) if n_slash else ''}")
print("\n".join(bad))
PYL
)"
  if [[ -z "${l_out}" ]]; then
    ok "L  字面中性化：九檔內文（去 frontmatter／對應表／code block）無 Claude Code 專屬字面與裸斜線形"
  else
    ng "L  字面殘留（須改為能力名或移入 Agent 對應表／code block）：$(echo "${l_out}" | tr '\n' '；')"
  fi
  # --- M. Agent 對應表七份逐字一致 ---
  m_out="$(python3 - <<'PYM'
import re
files = ["skills/handoff/SKILL.md","skills/todo/SKILL.md","skills/kunsu-init/SKILL.md","skills/kunsu-inbox/SKILL.md",
         "skills/kunsu-apply/SKILL.md","skills/kunsu-report/SKILL.md","skills/kunsu-list/SKILL.md"]
def block(f):
    try:
        s = open(f, encoding="utf-8").read()
    except Exception:
        return None
    m = re.search(r'^## Agent 對應表.*?(?=^## )', s, flags=re.S | re.M)
    return m.group(0).strip() if m else None
base = block(files[0]); bad = []
if base is None: bad.append(f"{files[0]}: 無對應表區塊")
for f in files[1:]:
    b = block(f)
    if b is None: bad.append(f"{f}: 無對應表區塊")
    elif b != base: bad.append(f"{f}: 與 handoff 不一致")
print("\n".join(bad))
PYM
)"
  if [[ -z "${m_out}" ]]; then
    ok "M  Agent 對應表七份逐字一致（以 handoff SKILL 為基準）"
  else
    ng "M  Agent 對應表不一致或缺失：$(echo "${m_out}" | tr '\n' '；')"
  fi
else
  wn "L/M 需要 python3，略過"
fi

# --- N. Codex hook 信任索引漂移（WARN 級，ADR 019）---
CODEX_HOOKS="${HOME}/.codex/hooks.json"; CODEX_CFG="${HOME}/.codex/config.toml"
if [[ -f "${CODEX_HOOKS}" ]] && command -v python3 >/dev/null; then
  n_out="$(python3 - "${CODEX_HOOKS}" "${CODEX_CFG}" <<'PYN'
import json, re, sys
hooks_path, cfg_path = sys.argv[1], sys.argv[2]
try:
    hooks = json.load(open(hooks_path, encoding="utf-8")).get("hooks", {})
except Exception as e:
    print(f"hooks.json 無法解析：{e}"); sys.exit(0)
try:
    cfg = open(cfg_path, encoding="utf-8").read()
except Exception:
    cfg = ""
def snake(ev):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', ev).lower()
issues = []
found = False
for ev, groups in hooks.items():
    for gi, g in enumerate(groups or []):
        cmds = " ".join(h.get("command", "") for h in g.get("hooks", []))
        if "kunsu-inbox/scripts/" not in cmds:
            continue
        found = True
        key = f"{hooks_path}:{snake(ev)}:{gi}:0"
        if key not in cfg:
            issues.append(f"{ev} 群組 {gi} 無對應 hooks.state 信任鍵（未信任或索引漂移）")
        elif re.search(re.escape(key) + r'"\]\s*\n(?:[^\[]*\n)*?enabled\s*=\s*false', cfg):
            issues.append(f"{ev} 群組 {gi} 已被 enabled=false 關閉")
if not found:
    print("hooks.json 內無 kunsu 條目")
else:
    print("\n".join(issues))
PYN
)"
  if [[ -z "${n_out}" ]]; then
    ok "N  Codex hooks.json 內 kunsu 條目信任鍵齊全（索引未漂移）"
  else
    wn "N  Codex hook 狀態：$(echo "${n_out}" | tr '\n' '；')（未信任或索引漂移時 hook 靜默略過，請於 TUI /hooks 重新信任）"
  fi
fi

# --- O. install.sh 覆寫保護與雙目標實跑（2026-09-07 code review 補；比照 C／K 實跑而非比字面）---
oh="$(mktemp -d)"; o_fail=""
run_install(){ KUNSU_INSTALL_HOME="$1" bash ./install.sh "${@:2}" >/dev/null 2>&1; }
mkdir -p "${oh}/h1"; run_install "${oh}/h1" && [[ -d "${oh}/h1/.claude/skills/handoff" && ! -e "${oh}/h1/.agents" ]] || o_fail+="無~/.codex只部署Claude樹；"
mkdir -p "${oh}/h2/.codex"; run_install "${oh}/h2" && [[ -f "${oh}/h2/.agents/skills/handoff/.kunsu-origin" && -f "${oh}/h2/.claude/skills/todo/.kunsu-origin" ]] || o_fail+="有~/.codex建兩樹；"
mkdir -p "${oh}/h3/.codex/" "${oh}/h3/.agents/skills/todo"; echo third > "${oh}/h3/.agents/skills/todo/SKILL.md"
if run_install "${oh}/h3" || [[ -e "${oh}/h3/.claude/skills/handoff" ]] || [[ "$(cat "${oh}/h3/.agents/skills/todo/SKILL.md")" != "third" ]]; then o_fail+="同名非kunsu目錄未整批中止；"; fi
mkdir -p "${oh}/h4/.claude/skills"; ln -s "/nonexistent-kunsu-src/handoff" "${oh}/h4/.claude/skills/handoff"
run_install "${oh}/h4" && [[ -f "${oh}/h4/.claude/skills/handoff/.kunsu-origin" ]] || o_fail+="懸空symlink未安全覆寫；"
mkdir -p "${oh}/h5/.claude/skills/handoff"; touch "${oh}/h5/.claude/skills/handoff/SKILL.md"
if run_install "${oh}/h5"; then o_fail+="無標記實體目錄應中止卻通過；"; fi
KUNSU_INSTALL_YES=1 run_install "${oh}/h5" --adopt && [[ -f "${oh}/h5/.claude/skills/handoff/.kunsu-origin" ]] || o_fail+="--adopt未採納；"
run_install "${oh}/h2" && [[ -f "${oh}/h2/.agents/skills/handoff/.kunsu-origin" ]] || o_fail+="重跑不冪等；"
rm -rf "${oh}"
if [[ -z "${o_fail}" ]]; then ok "O  install.sh 六場景實跑全過（雙目標、整批中止零改動、懸空 symlink、--adopt、冪等）"; else ng "O  install.sh 場景失敗：${o_fail}"; fi

# --- H. live 軍師同步抽查（WARN 級）---
REG="${HOME}/.claude/kunsu-registry.json"
if [[ -f "${REG}" ]] && command -v python3 >/dev/null; then
  while IFS= read -r kroot; do
    [[ -z "${kroot}" || ! -f "${kroot}/CLAUDE.md" ]] && continue
    csz="$(wc -c < "${kroot}/CLAUDE.md" | tr -d ' ')"
    if [[ "${csz}" -ge 52428 ]]; then
      wn "H  live 軍師 CLAUDE.md 達 ${csz} bytes（project_doc_max_bytes 65536 的 80% 以上，Codex 超限靜默截尾）：${kroot}"
    fi
    if grep -q '規劃前既有盤點' "${kroot}/CLAUDE.md" && grep -q '勿自標' "${kroot}/CLAUDE.md" && grep -q 'corrected_by' "${kroot}/CLAUDE.md" && grep -q '副官' "${kroot}/CLAUDE.md" && grep -q '不豁免' "${kroot}/CLAUDE.md" && grep -q '宣告範圍' "${kroot}/CLAUDE.md" && grep -q '以原始碼為準' "${kroot}/CLAUDE.md" && grep -q 'Agent 對應表' "${kroot}/CLAUDE.md" && [[ -L "${kroot}/AGENTS.md" ]] && grep -q '不豁免' "${kroot}/CONCEPTS.md" 2>/dev/null && grep -q 'archive-handoff' "${kroot}/CONCEPTS.md" 2>/dev/null && grep -q 'archive-todo' "${kroot}/CONCEPTS.md" 2>/dev/null && grep -q 'depends_on' "${kroot}/CLAUDE.md" && grep -q 'depends_on' "${kroot}/CONCEPTS.md" 2>/dev/null; then
      ok "H  live 軍師遷移標記齊全：${kroot}"
    else
      wn "H  live 軍師疑似漏遷移（缺 規劃前既有盤點／勿自標／corrected_by／副官／不豁免（CLAUDE 與 CONCEPTS 各自）／宣告範圍／以原始碼為準／Agent 對應表（CLAUDE）／AGENTS.md symlink／archive-handoff／archive-todo（CONCEPTS）／depends_on（CLAUDE 與 CONCEPTS 各自） 之一）：${kroot}"
    fi
  done < <(python3 -c "
import json
try:
    reg = json.load(open('${REG}'))
    seen = set()
    for entries in reg.values():
        for e in entries:
            k = e.get('kunsu')
            if k and k not in seen:
                seen.add(k); print(k)
except Exception:
    pass
")
fi

echo "---"
echo "pass=${pass} fail=${fail} warn=${warn}"
[[ "${fail}" -eq 0 ]] || exit 1
exit 0
