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
    && echo "一致性檢查內文" | bash "${OLDPWD}/skills/handoff/scripts/new-handoff.sh" "一致性檢查" >/dev/null 2>&1); then
  gen="$(ls "${tmp}"/docs/handoffs/*.md 2>/dev/null | head -1)"
  for sentence in '回覆檔 `status` 值：' '中途需切換任務時'; do
    a="$(grep -F "${sentence}" "${gen}" | head -1 | sed 's/^[[:space:]]*//')"
    b="$(grep -F "${sentence}" skills/handoff/SKILL.md | head -1 | sed 's/^[[:space:]]*//')"
    if [[ -n "${a}" && "${a}" == "${b}" ]]; then
      ok "C  定型文字兩副本逐字一致：「${sentence}…」"
    else
      ng "C  定型文字兩副本不一致或缺失：「${sentence}…」（產生器與 SKILL.md 範例段須連動修改）"
    fi
  done
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

# --- H. live 軍師同步抽查（WARN 級）---
REG="${HOME}/.claude/kunsu-registry.json"
if [[ -f "${REG}" ]] && command -v python3 >/dev/null; then
  while IFS= read -r kroot; do
    [[ -z "${kroot}" || ! -f "${kroot}/CLAUDE.md" ]] && continue
    if grep -q '規劃前既有盤點' "${kroot}/CLAUDE.md" && grep -q '勿自標' "${kroot}/CLAUDE.md"; then
      ok "H  live 軍師遷移標記齊全：${kroot}"
    else
      wn "H  live 軍師疑似漏遷移（缺 規劃前既有盤點 或 勿自標）：${kroot}"
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
