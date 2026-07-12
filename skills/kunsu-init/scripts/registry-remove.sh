#!/usr/bin/env bash
# registry-remove.sh — 從 kunsu-registry.json 移除子 repo 在某軍師的整筆登記（read-remove-write）
#
# 用法：
#   registry-remove.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path>
#
# 必填位置參數（置於選用旗標之後）：
#   <sub-repo-abs-path>      子 repo 的絕對路徑
#   <kunsu-abs-path>         軍師根目錄的絕對路徑
#
# 選用旗標：
#   --registry <path>  覆寫預設的 ~/.claude/kunsu-registry.json（供測試與 dogfooding 用）
#
# 移除邏輯（對稱 registry-merge.sh 的合併邏輯，但方向相反）：
#   從 data[sub_repo] 這個 list 中，篩掉 kunsu（正規化後）相符的 entry：
#     - 篩後為空 → 整個 data[sub_repo] key 一併刪除，不留空陣列
#     - 篩後仍有其他軍師的 entry → 只更新該 list，保留其他軍師登記
#   一次只移除一筆（子專案在本軍師的整筆登記，含其全部 roles），不支援只移除部分角色。
#
# exit code 慣例（與 registry-merge.sh 刻意不同：移除操作沒有「找不到就順便建立」的語意，
# 「找不到可移除的登記」與「找到並成功移除」用不同 exit code 區分，避免呼叫端把路徑打錯
# 誤判為「已成功移除」——這是不可逆操作，冪等與成功必須可被明確區分）：
#   0 = 找到並成功移除
#   3 = 找不到對應登記（registry 檔案不存在／sub_repo key 不存在／本軍師 entry 不存在），
#       視為冪等已達成，非錯誤，但與「成功移除」分開回報
#   1 = registry 格式損壞，或執行環境缺少 python3
#   2 = 參數錯誤
#
# 路徑正規化：比對前對 sub-repo 與 kunsu 兩條路徑執行 os.path.realpath，
# 避免 symlink 差異造成漏比對。

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
      echo "用法：registry-remove.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path>" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 2 ]]; then
  echo "用法：registry-remove.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path>" >&2
  exit 2
fi

SUB_REPO="$1"
KUNSU="$2"

# ── Python3 read-remove-write ────────────────────────────────────────────────────
python3 - "$SUB_REPO" "$KUNSU" "$REGISTRY" <<'PYEOF'
import sys
import json
import os
import tempfile

sub_repo_raw, kunsu_raw, registry_path = sys.argv[1], sys.argv[2], sys.argv[3]

# 路徑正規化（避免 symlink 造成漏比對）
sub_repo = os.path.realpath(sub_repo_raw)
kunsu = os.path.realpath(kunsu_raw)

# registry 檔案不存在 → 無可移除，冪等略過（不建立新檔案——移除操作沒有「順便建立」的語意）
if not os.path.exists(registry_path):
    print(f"無此登記，略過：{sub_repo}")
    print("  → registry 檔案不存在")
    sys.exit(3)

try:
    with open(registry_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        data = {}
    else:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError(
                "頂層結構應為 JSON 物件（object），實際為：" + type(data).__name__
            )
except (json.JSONDecodeError, ValueError) as e:
    print(
        f"錯誤：註冊表格式損壞，請手動修復（{registry_path}）：{e}",
        file=sys.stderr
    )
    sys.exit(1)

# sub_repo key 不存在 → 無可移除，冪等略過
if sub_repo not in data:
    print(f"無此登記，略過：{sub_repo}")
    print("  → registry 中無此子專案的任何登記")
    sys.exit(3)

entries = data[sub_repo]

# 篩掉本軍師（正規化後比對）的 entry
remaining = [
    e for e in entries
    if os.path.realpath(e.get("kunsu", "")) != kunsu
]

# 本軍師 entry 不存在（子專案僅登記其他軍師）→ 無可移除，冪等略過，其他軍師 entry 不動
if len(remaining) == len(entries):
    print(f"本軍師無此登記，略過：{sub_repo}")
    print(f"  → 軍師：{kunsu}")
    if entries:
        other_kunsu = ', '.join(sorted({e.get("kunsu", "") for e in entries}))
        print(f"  → 此子專案登記於其他軍師（不動）：{other_kunsu}")
    sys.exit(3)

# 找到本軍師 entry，執行移除
if not remaining:
    del data[sub_repo]
    print(f"已移除登記（本軍師為唯一登記，整筆刪除）：{sub_repo}")
    print(f"  → 軍師：{kunsu}")
else:
    data[sub_repo] = remaining
    print(f"已移除登記（保留其他軍師登記）：{sub_repo}")
    print(f"  → 軍師：{kunsu}")
    other_kunsu = ', '.join(sorted({e.get("kunsu", "") for e in remaining}))
    print(f"  → 其他軍師登記保留：{other_kunsu}")

# 原子寫入（同 registry-merge.sh：先寫同目錄暫存檔再 os.replace，避免中斷造成截斷損壞）
parent = os.path.dirname(registry_path) or '.'
fd, tmp_path = tempfile.mkstemp(dir=parent, suffix='.tmp')
try:
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp_path, registry_path)
except Exception:
    os.unlink(tmp_path)
    raise

PYEOF
