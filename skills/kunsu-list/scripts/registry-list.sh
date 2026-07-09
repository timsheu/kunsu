#!/usr/bin/env bash
# registry-list.sh — 列出 kunsu-registry.json 的全部登記（按軍師分組，純唯讀）
#
# 用法：
#   registry-list.sh [--registry <path>] [<current-root-abs-path>]
#
# 選用位置參數：
#   <current-root-abs-path>  當前 session 所在 git repo 根的絕對路徑（可空字串）；
#                            命中登記條目時該列標示「← 你在這」。
#
# 選用旗標：
#   --registry <path>  覆寫預設的 ~/.claude/kunsu-registry.json（供測試與 dogfooding 用）
#
# 行為：
#   - 純唯讀，不寫入任何檔案。
#   - 登記路徑（子專案與軍師）不存在於檔案系統時標示 ⚠，作為 stale entry 偵測。
#   - 註冊表不存在 → 友善訊息、exit 0（無登記不是錯誤）。
#   - 註冊表 JSON 損壞 → stderr 報錯、exit 1（與 registry-merge.sh 一致）。

set -euo pipefail

# ── 守衛：需要 python3 ─────────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  echo "錯誤：需要 python3，請先安裝（brew install python3 或安裝 Xcode CLT）" >&2
  exit 1
fi

# ── 預設 registry 路徑 ─────────────────────────────────────────────────────────
REGISTRY="${HOME}/.claude/kunsu-registry.json"

# ── 解析參數 ───────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry)
      if [[ $# -lt 2 ]]; then
        echo "錯誤：--registry 需要路徑參數" >&2
        exit 2
      fi
      REGISTRY="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "未知旗標：$1" >&2
      echo "用法：registry-list.sh [--registry <path>] [<current-root-abs-path>]" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

CURRENT_ROOT="${1:-}"

# ── Python3 讀取與排版 ─────────────────────────────────────────────────────────
python3 - "$REGISTRY" "$CURRENT_ROOT" <<'PYEOF'
import json
import os
import sys

registry_path, current_root_raw = sys.argv[1], sys.argv[2]
current_root = os.path.realpath(current_root_raw) if current_root_raw else None
home = os.path.expanduser("~")


def tilde(path):
    """以 ~ 縮寫 HOME 前綴，提升可讀性。"""
    if path == home or path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


if not os.path.exists(registry_path):
    print(f"註冊表不存在（{tilde(registry_path)}）：尚未登記任何子專案。")
    print("可以 /kunsu-init 建立軍師，或在子專案以 /kunsu-apply 投遞申請。")
    sys.exit(0)

try:
    with open(registry_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    data = json.loads(content) if content else {}
    if not isinstance(data, dict):
        raise ValueError(
            "頂層結構應為 JSON 物件（object），實際為：" + type(data).__name__
        )
except (json.JSONDecodeError, ValueError) as e:
    print(f"錯誤：註冊表格式損壞，請手動修復（{registry_path}）：{e}", file=sys.stderr)
    sys.exit(1)

if not data:
    print(f"註冊表為空（{tilde(registry_path)}）：尚未登記任何子專案。")
    sys.exit(0)

# 反轉為「軍師 → [(roles, sub_repo)]」分組
groups = {}
for sub_repo, entries in data.items():
    if not isinstance(entries, list):
        continue
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kunsu = entry.get("kunsu", "")
        roles = entry.get("roles", [])
        if not kunsu:
            continue
        groups.setdefault(kunsu, []).append((roles, sub_repo))

print(f"kunsu 子專案登記清單（{tilde(registry_path)}）")

stale = []
total_entries = 0

for kunsu in sorted(groups):
    rows = sorted(groups[kunsu], key=lambda r: (", ".join(r[0]), r[1]))
    kunsu_warn = "" if os.path.isdir(kunsu) else "　⚠ 軍師路徑不存在"
    if kunsu_warn:
        stale.append(f"軍師 {tilde(kunsu)}")
    print()
    print(f"■ {os.path.basename(kunsu)}（{tilde(kunsu)}）{kunsu_warn}")

    role_width = max(len(", ".join(roles)) for roles, _ in rows)
    for roles, sub_repo in rows:
        total_entries += 1
        role_str = ", ".join(roles)
        markers = ""
        if not os.path.isdir(sub_repo):
            markers += "　⚠ 路徑不存在"
            stale.append(f"{role_str}（{tilde(sub_repo)}）")
        if current_root and os.path.realpath(sub_repo) == current_root:
            markers += "　← 你在這"
        print(f"  {role_str:<{role_width}}  {tilde(sub_repo)}{markers}")

print()
print(f"共 {len(groups)} 個軍師、{total_entries} 筆登記。")
if stale:
    print()
    print("⚠ 以下登記路徑已不存在（stale entry，建議檢查是否搬家或移除）：")
    for s in stale:
        print(f"  - {s}")
PYEOF
