# kc.fish — kunsu claude 啟動函式（fish autoload function）
#
# 依 cwd 在 ~/.claude/kunsu-registry.json 的登記，自動以 kunsu session 命名
# 慣例啟動 claude（`claude -n <慣例名>`），使派發即推播（handoff add 步驟 6，
# ADR 015）的 session 匹配走精確比對、零歧義：
#   子專案 → <軍師目錄名>-<角色代碼>（如 ebook-android；多重登記取第一筆，
#            需要其他名稱時以 /rename 覆蓋）
#   軍師   → <軍師目錄名>-kunsu（如 ebook-kunsu，供日後回覆方向推播定址）
#
# 同一資料夾要開多個 session 分頭處理不同工作時，加 `--slot <後綴>` 區分：
#   kc --slot auth   → ebook-android.auth
# 分隔符固定為 `.`（角色代碼為 kebab-case 不含 `.`，解析唯一）；後綴限
# 英數、`-`、`_`。不同名稱使 /park 與 /unpark 各持一份停車格（slot 取
# session 名稱）。推播匹配會把帶後綴的 session 一併列入候選，但仍維持
# 「唯一命中才發送」——同慣例名前綴的 online session 開了兩個以上時降級跳過，
# 由 SessionStart hook 或手動 /kunsu-inbox 兜底。
#
# 每次 kc 都是 `claude -n` 新開一個 session（名字只是標籤，不是 session 身分，
# 續接舊 session 要走 --resume）；session 關掉後，清單裡可能留下一筆同名、
# 狀態為 offline 的殘影（推斷：Claude Code settings.json 的
# remoteControlAtStartup 為 true 時，每個 session 啟動即註冊 Remote Control，
# process 結束後該登記留存為 offline；本機 2026-10-03 實測 21 筆 peer 有 19 筆
# 是 Remote Control · offline，但未做過「開關一次 session 再重列」的對照）。
# 推播匹配已於匹配前排除狀態為 offline 的列（handoff add 6-2／reply 6-1，
# 2026-10-03 定案），殘影不再使活 session 被判多重命中。若想減少清單噪訊，可把
# remoteControlAtStartup 設為 false、需要遠端接管時在 session 內以 /remote-control
# （/rc）按需開啟；代價是每個要遠端接管的 session 都得手動開，且此設定只影響
# 清單長度，不影響推播正確性。
#
# 未登記、非 git 目錄、自帶 -n／--name、或帶 --resume／-r 時不命名，行為同
# 直接執行 claude（--slot 此時一併忽略並提示）。
#
# 安裝（機器層級，開發部署分離——原始碼在 kunsu repo 版控）：
#   cp <kunsu repo>/scripts/kc.fish ~/.config/fish/functions/kc.fish
# 解除：刪除 ~/.config/fish/functions/kc.fish 即可。

function kc --description "啟動 claude 並依 kunsu 登記自動命名 session（--slot <後綴> 區分同資料夾多 session）"
    # 先抽出 --slot <後綴>，其餘參數原樣透傳給 claude
    set -l slot ""
    set -l passthru
    set -l i 1
    while test $i -le (count $argv)
        set -l a $argv[$i]
        if test "$a" = "--slot"
            set i (math $i + 1)
            if test $i -gt (count $argv)
                echo "kc: --slot 需要一個後綴值（英數、-、_）" >&2
                return 2
            end
            set slot $argv[$i]
        else if string match -q -- "--slot=*" $a
            set slot (string replace -- "--slot=" "" $a)
        else
            set -a passthru $a
        end
        set i (math $i + 1)
    end

    if test -n "$slot"; and not string match -qr -- '^[A-Za-z0-9_-]+$' $slot
        echo "kc: --slot 後綴僅限英數、-、_（收到：$slot）" >&2
        return 2
    end

    # --resume／-r 與 -n 並用會衝突；使用者自帶 -n／--name 則尊重其命名。
    # 兩種情況皆直接透傳，不套慣例名。
    # 注意：用 contains 而非 test——參數值本身為 -n／-r 時，test 會把它當成
    # 一元運算子而解析失敗。
    for a in $passthru
        if contains -- "$a" --resume -r -n --name
            if test -n "$slot"
                echo "kc: 偵測到 $a，略過自動命名（--slot 一併忽略）" >&2
            end
            claude $passthru
            return
        end
    end

    set -l root (git rev-parse --show-toplevel 2>/dev/null)
    if test -z "$root"
        if test -n "$slot"
            echo "kc: 非 git 目錄，略過自動命名（--slot 一併忽略）" >&2
        end
        claude $passthru
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
        if test -n "$slot"
            set name "$name.$slot"
        end
        claude -n "$name" $passthru
    else
        if test -n "$slot"
            echo "kc: 本目錄未登記於 kunsu 註冊表，略過自動命名（--slot 一併忽略）" >&2
        end
        claude $passthru
    end
end
