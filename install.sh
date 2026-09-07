#!/usr/bin/env bash
# install.sh — 部署 kunsu 的 skills 至各 agent 的 skill 目錄
#
# 部署目標（Invariant 3，ADR 019）：
#   Claude Code  ~/.claude/skills/   恆部署
#   Codex        ~/.agents/skills/   偵測到 ~/.codex/ 才部署（Codex 官方 user 位置；~/.codex/skills 已 deprecated 不用）
#
# 用法：
#   ./install.sh              # 預設：整目錄複製（cp -R，不加 /* 攤平），並於目的目錄寫入 .kunsu-origin 標記
#   ./install.sh --link       # 開發模式：以目錄 symlink 部署，本 repo 修改即時生效（Codex 追蹤目錄 symlink，勿改成檔案層）
#   ./install.sh --adopt      # 採納既有無標記的實體目錄（舊版 copy 部署）：列出候選並互動確認後覆寫並寫入 .kunsu-origin；
#                               非互動環境須另設 KUNSU_INSTALL_YES=1 才會覆寫；預設（無 --adopt）對此類目錄整批中止
#   懸空 symlink（--link 部署後 repo 搬家）視為安全覆寫，不需 --adopt
#   ./install.sh --target <dir>  # 覆寫為單一部署目標（供測試用；此時不偵測 Codex）
#
# 覆寫保護：目的路徑已存在時，只有「指向本 repo 的 symlink」或「含 .kunsu-origin 的目錄」會被覆寫；
#   其他一律整批中止、零目錄改動（pre-flight 先掃全部目標×skill，再進部署迴圈）。
# 注意：--link 模式依賴本 repo 保持在原路徑，repo 搬家後 symlink 失效，需重新執行 install.sh。
# 測試隔離：KUNSU_INSTALL_HOME 覆寫家目錄（預設 $HOME），用於在暫存目錄模擬 ~/.codex 存在與否。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=(handoff todo kunsu-init kunsu-inbox kunsu-apply kunsu-report kunsu-list kunsu-dashboard)
INSTALL_HOME="${KUNSU_INSTALL_HOME:-$HOME}"
MODE="copy"
ADOPT="no"
SINGLE_TARGET=""
MARKER=".kunsu-origin"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link)
      MODE="link"
      shift
      ;;
    --adopt)
      ADOPT="yes"
      shift
      ;;
    --target)
      [[ $# -ge 2 ]] || { echo "錯誤：--target 需要目錄參數" >&2; exit 2; }
      [[ -n "$2" ]] || { echo "錯誤：--target 不可為空字串" >&2; exit 2; }
      SINGLE_TARGET="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "錯誤：未知參數 $1（支援 --link、--adopt、--target <dir>、--help）" >&2
      exit 2
      ;;
  esac
done

for name in "${SKILLS[@]}"; do
  src="${SCRIPT_DIR}/skills/${name}"
  [[ -d "$src" ]] || { echo "錯誤：來源不存在 ${src}" >&2; exit 1; }
done

# 部署目標清單：--target 單一覆寫；否則 Claude Code 恆在、Codex 依 ~/.codex/ 存在與否
TARGETS=()
TARGET_LABELS=()
if [[ -n "$SINGLE_TARGET" ]]; then
  TARGETS+=("$SINGLE_TARGET")
  TARGET_LABELS+=("custom")
else
  TARGETS+=("${INSTALL_HOME}/.claude/skills")
  TARGET_LABELS+=("Claude Code")
  if [[ -d "${INSTALL_HOME}/.codex" ]]; then
    TARGETS+=("${INSTALL_HOME}/.agents/skills")
    TARGET_LABELS+=("Codex")
  else
    echo "略過 Codex 目標：未偵測到 ${INSTALL_HOME}/.codex/（Codex 未安裝）。"
  fi
fi

# 判定 dest 是否為本 repo 的部署產物：指向本 repo 的 symlink，或含標記檔的目錄
is_kunsu_deploy() {
  local dest="$1" src="$2"
  if [[ -L "$dest" ]]; then
    # 懸空 symlink（目標已不存在，典型為 --link 部署後 repo 搬家）：內容已不存在，覆寫零資料風險
    [[ -e "$dest" ]] || return 0
    local link_target
    link_target="$(cd "$dest" 2>/dev/null && pwd -P)" || return 1
    [[ "$link_target" == "$(cd "$src" && pwd -P)" ]]
    return
  fi
  [[ -d "$dest" && -f "${dest}/${MARKER}" ]]
}

# pre-flight：掃全部目標×skill，任一衝突整批中止、零目錄改動
conflicts=()
adoptable=()
for target in "${TARGETS[@]}"; do
  for name in "${SKILLS[@]}"; do
    src="${SCRIPT_DIR}/skills/${name}"
    dest="${target}/${name}"
    [[ -e "$dest" || -L "$dest" ]] || continue
    # 防呆：目標為實體目錄且與來源為同一路徑（如 --target 誤指向本 repo 的 skills/）時，
    # rm -rf 會摧毀待部署的原始碼——直接報錯退出。
    if [[ ! -L "$dest" && -d "$dest" ]]; then
      dest_canon="$(cd "$dest" && pwd -P)"
      src_canon="$(cd "$src" && pwd -P)"
      if [[ "$dest_canon" == "$src_canon" ]]; then
        echo "錯誤：部署目標與來源為同一目錄（${dest_canon}），中止以免刪除原始碼。" >&2
        exit 1
      fi
    fi
    if is_kunsu_deploy "$dest" "$src"; then
      continue
    fi
    if [[ "$ADOPT" == "yes" && ! -L "$dest" && -d "$dest" ]]; then
      adoptable+=("$dest")
      continue
    fi
    conflicts+=("$dest")
  done
done

if [[ ${#conflicts[@]} -gt 0 ]]; then
  echo "錯誤：下列目的路徑已存在且不是本 repo 的部署產物（無 ${MARKER} 標記、亦非指向本 repo 或已懸空的 symlink），整批中止、未改動任何目錄：" >&2
  for c in "${conflicts[@]}"; do echo "  ${c}" >&2; done
  echo "若這些是舊版 kunsu copy 部署，請以 ./install.sh --adopt 採納（列出候選、確認後覆寫並寫入標記）；若是第三方 skill，請先改名或移除。" >&2
  exit 1
fi

# --adopt 採納前確認：候選目錄無任何 kunsu 特徵可機械辨識（第三方 skill 也可能叫 todo／handoff），
# 覆寫等於 rm -rf 使用者資料，必經人工確認；非互動環境（無 tty）須另設 KUNSU_INSTALL_YES=1
if [[ ${#adoptable[@]} -gt 0 ]]; then
  echo "--adopt 候選（將 rm -rf 後以本 repo 內容覆寫並寫入 ${MARKER}）："
  for a in "${adoptable[@]}"; do
    desc="$(grep -m1 '^description:' "${a}/SKILL.md" 2>/dev/null | cut -c1-80 || true)"
    echo "  ${a}  ${desc:+（SKILL.md：${desc}）}"
  done
  if [[ "${KUNSU_INSTALL_YES:-0}" != "1" ]]; then
    if [[ -t 0 ]]; then
      printf '確認採納並覆寫以上 %d 個目錄？[y/N] ' "${#adoptable[@]}"
      read -r ans
      [[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "已取消，未改動任何目錄。" >&2; exit 1; }
    else
      echo "錯誤：非互動環境無法確認 --adopt；請改於終端執行，或確認候選皆為舊版 kunsu 部署後以 KUNSU_INSTALL_YES=1 重跑。" >&2
      exit 1
    fi
  fi
fi

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
done

if [[ "$MODE" == "link" ]]; then
  echo "⚠ symlink 模式：依賴本 repo 保持在 ${SCRIPT_DIR}，搬家後需重新執行 install.sh。"
fi

deployed=()
for target in "${TARGETS[@]}"; do
  for name in "${SKILLS[@]}"; do
    src="${SCRIPT_DIR}/skills/${name}"
    dest="${target}/${name}"
    if [[ -e "$dest" || -L "$dest" ]]; then
      echo "已存在：${dest}，將覆寫舊版。"
      rm -rf "$dest"
    fi
    if [[ "$MODE" == "link" ]]; then
      ln -sfn "$src" "$dest"
    else
      cp -R "$src" "$dest"
      printf '%s\n' "$SCRIPT_DIR" > "${dest}/${MARKER}"
    fi
    deployed+=("$dest")
  done
done

echo ""
echo "部署完成（模式：${MODE}）："
i=0
for target in "${TARGETS[@]}"; do
  echo "  [${TARGET_LABELS[$i]}] ${target}/"
  i=$((i+1))
done
if [[ ${#deployed[@]} -gt 0 ]]; then
  for d in "${deployed[@]}"; do
    if [[ -L "$d" ]]; then
      echo "    ${d} -> $(readlink "$d")"
    else
      echo "    ${d}"
    fi
  done
fi
echo ""
echo "新開 agent session 即可使用 handoff、todo、kunsu-init、kunsu-inbox、kunsu-apply、kunsu-report 與 kunsu-list skill"
echo "（Claude Code 以 /<name> 呼叫；Codex 以 \$<name> 呼叫或依 description 自動選用）。"
echo "hook 與 config 為機器層級設定，須手動掛載：見 kunsu-inbox/SKILL.md 的「SessionStart hook」「PreToolUse git add 守門」與「Codex config 設定」三節。"
echo ""
echo "kunsu-dashboard 不是可觸發的 skill（frontmatter 已以兩 agent 原生旗標停用選用）——"
echo "見 <部署目錄>/kunsu-dashboard/SKILL.md 的安裝說明（pip install -r requirements.txt）；"
echo "裝好依賴後執行 <部署目錄>/kunsu-dashboard/start.sh 一鍵啟動。"
