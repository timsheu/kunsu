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

# --- H. live 軍師同步抽查（WARN 級）---
REG="${HOME}/.claude/kunsu-registry.json"
if [[ -f "${REG}" ]] && command -v python3 >/dev/null; then
  while IFS= read -r kroot; do
    [[ -z "${kroot}" || ! -f "${kroot}/CLAUDE.md" ]] && continue
    if grep -q '規劃前既有盤點' "${kroot}/CLAUDE.md" && grep -q '勿自標' "${kroot}/CLAUDE.md" && grep -q 'corrected_by' "${kroot}/CLAUDE.md" && grep -q '副官' "${kroot}/CLAUDE.md" && grep -q '不豁免' "${kroot}/CLAUDE.md" && grep -q '宣告範圍' "${kroot}/CLAUDE.md" && grep -q '以原始碼為準' "${kroot}/CLAUDE.md" && grep -q '不豁免' "${kroot}/CONCEPTS.md" 2>/dev/null && grep -q 'archive-handoff' "${kroot}/CONCEPTS.md" 2>/dev/null && grep -q 'archive-todo' "${kroot}/CONCEPTS.md" 2>/dev/null; then
      ok "H  live 軍師遷移標記齊全：${kroot}"
    else
      wn "H  live 軍師疑似漏遷移（缺 規劃前既有盤點／勿自標／corrected_by／副官／不豁免（CLAUDE 與 CONCEPTS 各自）／宣告範圍／以原始碼為準（CLAUDE）／archive-handoff／archive-todo（CONCEPTS） 之一）：${kroot}"
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
