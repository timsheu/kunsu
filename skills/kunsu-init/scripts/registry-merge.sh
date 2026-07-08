#!/usr/bin/env bash
# registry-merge.sh — 將子 repo 登記至 kunsu-registry.json（read-merge-write）
#
# 用法：
#   registry-merge.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path> <roles-comma-separated>
#
# 必填位置參數（置於選用旗標之後）：
#   <sub-repo-abs-path>      子 repo 的絕對路徑
#   <kunsu-abs-path>         軍師根目錄的絕對路徑
#   <roles-comma-separated>  以逗號分隔的角色字串（至少一個；例如 "前端 UI 實作" 或 "後端,DevOps"）
#
# 選用旗標：
#   --registry <path>  覆寫預設的 ~/.claude/kunsu-registry.json（供測試與 dogfooding 用）
#
# Schema：
#   {
#     "<sub-repo 絕對路徑>": [
#       { "kunsu": "<軍師絕對路徑>", "roles": ["<角色>", ...] }
#     ]
#   }
#   一個 sub-repo 可隸屬多個軍師（陣列）；roles 為字串陣列。
#
# 路徑正規化：寫入前對 sub-repo 與 kunsu 兩條路徑執行 os.path.realpath，
# 避免 symlink 差異造成重複條目。

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
      echo "用法：registry-merge.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path> <roles-comma-separated>" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 3 ]]; then
  echo "用法：registry-merge.sh [--registry <path>] <sub-repo-abs-path> <kunsu-abs-path> <roles-comma-separated>" >&2
  exit 2
fi

SUB_REPO="$1"
KUNSU="$2"
ROLES="$3"

# ── Python3 read-merge-write ────────────────────────────────────────────────────
python3 - "$SUB_REPO" "$KUNSU" "$REGISTRY" "$ROLES" <<'PYEOF'
import sys
import json
import os

sub_repo_raw, kunsu_raw, registry_path, roles_csv = (
    sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
)

# 路徑正規化（避免 symlink 造成重複條目）
sub_repo = os.path.realpath(sub_repo_raw)
kunsu  = os.path.realpath(kunsu_raw)

# 解析角色清單（逗號分隔，過濾空白項）
roles = [r.strip() for r in roles_csv.split(',') if r.strip()]
if not roles:
    print(
        "錯誤：角色清單不可空白（<roles-comma-separated> 至少需提供一個角色）",
        file=sys.stderr
    )
    sys.exit(2)

# 讀取現有 registry（或建新空物件）
if os.path.exists(registry_path):
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
else:
    data = {}

# 確保父目錄存在（首次建立 registry 時自動建立 ~/.claude/）
parent = os.path.dirname(registry_path)
if parent:
    os.makedirs(parent, exist_ok=True)

# 尋找或建立條目
if sub_repo not in data:
    # 全新登記
    data[sub_repo] = [{"kunsu": kunsu, "roles": roles}]
    print(f"已新增登記：{sub_repo}")
    print(f"  → 軍師：{kunsu}")
    print(f"  → 角色：{', '.join(roles)}")
else:
    entries = data[sub_repo]

    # 尋找同一 kunsu 的條目（正規化比對）
    matching = None
    for entry in entries:
        if os.path.realpath(entry.get("kunsu", "")) == kunsu:
            matching = entry
            break

    if matching is None:
        # 不同軍師 → append 新條目
        data[sub_repo].append({"kunsu": kunsu, "roles": roles})
        print(f"已新增條目（新軍師）：{sub_repo}")
        print(f"  → 軍師：{kunsu}")
        print(f"  → 角色：{', '.join(roles)}")
    else:
        # 同軍師 → 角色聯集合併
        existing  = set(matching["roles"])
        new_set   = set(roles)
        added     = sorted(new_set - existing)
        if not added:
            print(f"已登記，略過：{sub_repo}")
            print(f"  → 軍師：{kunsu}")
            print(
                f"  → 角色已全部涵蓋，無新角色（現有：{', '.join(sorted(existing))}）"
            )
            sys.exit(0)
        else:
            matching["roles"] = sorted(existing | new_set)
            print(f"已更新角色：{sub_repo}")
            print(f"  → 軍師：{kunsu}")
            print(
                f"  → 新增角色：{', '.join(added)}"
                f"（完整角色：{', '.join(matching['roles'])}）"
            )

# 寫回 registry（原子替換：先寫同目錄暫存檔再 os.replace，避免中斷造成截斷損壞）
# 已知限制：多個行程「同時」寫入仍可能後寫覆蓋前寫（last-writer-wins）；
# 本 skill 的使用情境為單一 session 序列呼叫，此風險可接受。
import tempfile
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
