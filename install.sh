#!/usr/bin/env bash
# install.sh — 部署 kunsu 的 skills 至 ~/.claude/skills/
#
# 用法：
#   ./install.sh              # 預設：整目錄複製（cp -R，不加 /* 攤平）
#   ./install.sh --link       # 開發模式：以 symlink 部署，本 repo 修改即時生效
#   ./install.sh --target <dir>  # 覆寫部署目標（預設 ~/.claude/skills，供測試用）
#
# 注意：--link 模式依賴本 repo 保持在原路徑，repo 搬家後 symlink 失效，需重新執行 install.sh。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=(handoff kunsu-init kunsu-inbox kunsu-apply kunsu-report)
TARGET_DIR="${HOME}/.claude/skills"
MODE="copy"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link)
      MODE="link"
      shift
      ;;
    --target)
      [[ $# -ge 2 ]] || { echo "錯誤：--target 需要目錄參數" >&2; exit 2; }
      [[ -n "$2" ]] || { echo "錯誤：--target 不可為空字串" >&2; exit 2; }
      TARGET_DIR="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "錯誤：未知參數 $1（支援 --link、--target <dir>、--help）" >&2
      exit 2
      ;;
  esac
done

for name in "${SKILLS[@]}"; do
  src="${SCRIPT_DIR}/skills/${name}"
  [[ -d "$src" ]] || { echo "錯誤：來源不存在 ${src}" >&2; exit 1; }
done

mkdir -p "$TARGET_DIR"

if [[ "$MODE" == "link" ]]; then
  echo "⚠ symlink 模式：依賴本 repo 保持在 ${SCRIPT_DIR}，搬家後需重新執行 install.sh。"
fi

deployed=()
for name in "${SKILLS[@]}"; do
  src="${SCRIPT_DIR}/skills/${name}"
  dest="${TARGET_DIR}/${name}"

  if [[ -e "$dest" || -L "$dest" ]]; then
    # 防呆：目標為實體目錄且與來源為同一路徑（如 --target 誤指向本 repo 的 skills/）時，
    # rm -rf 會摧毀待部署的原始碼——直接報錯退出。
    # 目標為 symlink 時不需比對：rm 只刪 symlink 本身，不跟隨目標。
    if [[ ! -L "$dest" && -d "$dest" ]]; then
      dest_canon="$(cd "$dest" && pwd)"
      src_canon="$(cd "$src" && pwd)"
      if [[ "$dest_canon" == "$src_canon" ]]; then
        echo "錯誤：部署目標與來源為同一目錄（${dest_canon}），中止以免刪除原始碼。" >&2
        exit 1
      fi
    fi
    echo "已存在：${dest}，將覆寫舊版。"
    rm -rf "$dest"
  fi

  if [[ "$MODE" == "link" ]]; then
    ln -sfn "$src" "$dest"
  else
    cp -R "$src" "$dest"
  fi
  deployed+=("$dest")
done

echo ""
echo "部署完成（模式：${MODE}）："
for d in "${deployed[@]}"; do
  if [[ -L "$d" ]]; then
    echo "  ${d} -> $(readlink "$d")"
  else
    echo "  ${d}"
  fi
done
echo ""
echo "新開 Claude Code session 即可使用 /handoff、/kunsu-init、/kunsu-inbox、/kunsu-apply 與 /kunsu-report。"
