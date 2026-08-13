# kc.fish — kunsu claude 啟動函式（fish autoload function）
#
# 依 cwd 在 ~/.claude/kunsu-registry.json 的登記，自動以 kunsu session 命名
# 慣例啟動 claude（`claude -n <慣例名>`），使派發即推播（handoff add 步驟 6，
# ADR 015）的 session 匹配走精確比對、零歧義：
#   子專案 → <軍師目錄名>-<角色代碼>（如 ebook-android；多重登記取第一筆，
#            需要其他名稱時以 /rename 覆蓋）
#   軍師   → <軍師目錄名>-kunsu（如 ebook-kunsu，供日後回覆方向推播定址）
# 未登記、非 git 目錄、或帶 --resume／-r 時不命名，行為同直接執行 claude。
#
# 安裝（機器層級，開發部署分離——原始碼在 kunsu repo 版控）：
#   cp <kunsu repo>/scripts/kc.fish ~/.config/fish/functions/kc.fish
# 解除：刪除 ~/.config/fish/functions/kc.fish 即可。

function kc --description "啟動 claude 並依 kunsu 登記自動命名 session"
    # --resume／-r 與 -n 並用會衝突，偵測到即直接透傳
    for a in $argv
        if test "$a" = "--resume" -o "$a" = "-r"
            claude $argv
            return
        end
    end

    set -l root (git rev-parse --show-toplevel 2>/dev/null)
    if test -z "$root"
        claude $argv
        return
    end

    set -l name (python3 -c "
import json, sys
from pathlib import Path

root = sys.argv[1]
try:
    raw = json.load(open(Path.home() / '.claude' / 'kunsu-registry.json'))
except Exception:
    sys.exit(0)
if not isinstance(raw, dict):
    sys.exit(0)

# 子專案身分：登記鍵即 git root，取第一筆有效條目
for entry in raw.get(root) or []:
    if not isinstance(entry, dict):
        continue
    kunsu = str(entry.get('kunsu') or '')
    roles = [str(r) for r in (entry.get('roles') or []) if str(r)]
    if kunsu and roles:
        print(f'{Path(kunsu).name}-{roles[0]}')
        sys.exit(0)

# 軍師身分：root 出現在任一條目的 kunsu 值
kunsu_paths = {
    str(e.get('kunsu') or '')
    for v in raw.values() if isinstance(v, list)
    for e in v if isinstance(e, dict)
}
if root in kunsu_paths:
    print(f'{Path(root).name}-kunsu')
" $root)

    if test -n "$name"
        claude -n "$name" $argv
    else
        claude $argv
    end
end
