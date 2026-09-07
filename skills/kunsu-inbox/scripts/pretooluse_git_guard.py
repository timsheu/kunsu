#!/usr/bin/env python3
"""
pretooluse_git_guard.py — PreToolUse hook：軍師 repo 的 git add 範圍守門（ADR 017）

攔截 Bash 工具中對軍師 repo 執行的寬範圍 git add——`-A`／`--all`、`.`／`:/`、
以及涵蓋信箱路徑（docs/handoffs、docs/applications、docs/reports）的整目錄
add——並以 deny 回應，訊息內嵌正確做法。這是 kunsu 首個行為強制機制：判準是
機械可判、規則早已字面明文（SKILL done 段與軍師 CLAUDE.md 的「僅限具體路徑」）、
deny 後逐檔列名重做即可、零能力限縮。來源事故：2026-08-29 ebook 軍師手動歸檔
以 `git add -A` 夾帶 16 份未讀回覆，靜默清除「未 commit 即未處理」訊號。

範圍刻意最小（ADR 017 治理決議：規則凍結，不隨新變體增長；變體後果面由
scan-replies.sh 歷史夾帶偵測兜底）：
  - 僅軍師 repo（raw registry ＋ git root 快速比對，比照 session_hook.py）
  - 僅 git add 的三種寬範圍形狀；具體檔案路徑、非信箱目錄一律放行
  - 逃生門：指令前綴 `KUNSU_ADD_GUARD_OFF=1`（或程序環境同名變數）放行——
    打字成本即摩擦，且指令史留痕可稽
  - deny 事件記入掃描統計檔（同 scan-replies.sh 的 kunsu-scan-stats.json，
    type: GUARD_DENY），誤擋率與命中率有數據可查

已知限制（威脅模型是無意誤用、非惡意繞過，均屬接受）：
  - 指令切段為樸素字串分割（&&、;、|、換行），引號內含這些符號時可能誤切
  - `cd <他處> && git add` 的目標 repo 判定依 hook 收到的 cwd 與 `git -C`，
    不模擬 shell 狀態

失敗策略 fail-open：任何錯誤一律放行（exit 0 無輸出），絕不阻斷正常工作。
掛載與解除（機器層級設定，見 SKILL.md「PreToolUse git add 守門」節）：
  Claude Code ~/.claude/settings.json → hooks.PreToolUse matcher "Bash"；Codex ~/.codex/hooks.json 同形
  （各指向自己部署位置的本腳本，附加於陣列尾端並於 TUI 信任，ADR 019）。

環境變數（測試隔離用）：KUNSU_REGISTRY_FILE 覆寫註冊表路徑、
KUNSU_SCAN_STATS_FILE 覆寫統計檔路徑。
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

MAILBOXES = ("docs/handoffs", "docs/applications", "docs/reports")

# 歸檔腳本路徑以本檔所在部署位置推算（parents[2] = 部署目錄，如 ~/.claude/skills 或 ~/.agents/skills），
# 各 agent 的部署位置自足，不寫死任何一方的目錄（ADR 019）。用 absolute() 不用 resolve()：--link 部署下
# resolve 會追 symlink 回開發 repo，deny 訊息應指向 agent 自己的部署位置。任何失敗退回相對檔名（fail-open）。
try:
    _ARCHIVE_SCRIPT = Path(__file__).absolute().parents[2] / "handoff" / "scripts" / "archive-handoff.sh"
except Exception:  # 部署層級異常（parents 不足）不得阻斷守門
    _ARCHIVE_SCRIPT = Path("archive-handoff.sh")

DENY_MESSAGE = (
    "✋ 軍師 repo 內 git add 僅限具體檔案路徑（不用 -A、不整目錄打包）——"
    "整目錄 add 會夾帶未讀信箱檔案、靜默清除「未 commit 即未處理」訊號"
    "（ADR 017；2026-08-29 曾因此夾帶 16 份未讀回覆）。"
    f"歸檔請改用 bash {_ARCHIVE_SCRIPT}"
    "（自動處理 rename 兩側與暫存範圍）；其他情境請逐檔列名後重新執行。"
    "緊急需整目錄 add 時，指令前綴 KUNSU_ADD_GUARD_OFF=1 可單次放行（留痕可稽）。"
)


def _registry_path() -> str:
    return os.environ.get("KUNSU_REGISTRY_FILE") or os.path.expanduser(
        "~/.claude/kunsu-registry.json"
    )


def _stats_path() -> str:
    return os.environ.get("KUNSU_SCAN_STATS_FILE") or os.path.expanduser(
        "~/.claude/kunsu-scan-stats.json"
    )


def _load_kunsu_paths() -> set[str]:
    """raw registry 中全部軍師路徑集合；任何錯誤回傳空集合（→ 一律放行）。"""
    try:
        with open(_registry_path(), encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return set()
        paths: set[str] = set()
        for entries in raw.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("kunsu"):
                    paths.add(str(entry["kunsu"]))
        return paths
    except Exception:
        return set()


def _git_root(cwd: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _split_segments(command: str) -> list[str]:
    """樸素切段：&&、||、;、|、換行。引號內含符號時可能誤切（接受，見檔頭）。"""
    return [s for s in re.split(r"&&|\|\||;|\||\n", command) if s.strip()]


def _covers_mailbox(dir_path: str, repo_root: str) -> bool:
    """目錄是否涵蓋任一信箱路徑（等於、其祖先、或其子目錄）。"""
    d = os.path.normpath(dir_path)
    for m in MAILBOXES:
        mabs = os.path.normpath(os.path.join(repo_root, m))
        if d == mabs or mabs.startswith(d + os.sep) or d.startswith(mabs + os.sep):
            return True
    return False


def _extract_c_paths(command: str) -> list[str]:
    """git 呼叫全域旗標 `-C <path>` 的 path 清單（供軍師 repo 判定）。

    只認 git 段的 -C：其他程式的 -C（make -C、tar -C…）不收——否則在
    非軍師 repo 內執行「make -C <軍師路徑> … && git add -A」這類合法指令
    會被誤擋，且誤擋與真命中同記 GUARD_DENY，污染 ADR 017 觀察期統計。
    """
    paths: list[str] = []
    for seg in _split_segments(command):
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            continue
        idx = 0
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", tokens[idx]):
            idx += 1
        if idx >= len(tokens) or os.path.basename(tokens[idx]) != "git":
            continue
        idx += 1
        while idx < len(tokens) and tokens[idx].startswith("-"):
            if tokens[idx] in ("-C", "-c") and idx + 1 < len(tokens):
                if tokens[idx] == "-C":
                    paths.append(tokens[idx + 1])
                idx += 2
            else:
                idx += 1
    return paths


def _has_guard_off_prefix(command: str) -> bool:
    """任一指令段的**前導環境變數指定**含 KUNSU_ADD_GUARD_OFF=1 才算逃生門。

    子字串比對會被 heredoc 內文／echo 訊息誤觸——守門相關文件（ADR 017、
    SKILL.md、本檔 docstring）正文都含該字串，撰寫這些文件的指令會整條
    靜默放行且零留痕；ADR 017 裁決的形式是「指令前綴」，以 token 級判定對齊。
    """
    for seg in _split_segments(command):
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            continue
        idx = 0
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", tokens[idx]):
            if tokens[idx] == "KUNSU_ADD_GUARD_OFF=1":
                return True
            idx += 1
    return False


def find_offending(command: str, repo_root: str, base_dir: str) -> list[str]:
    """回傳寬範圍 add 的違規描述清單；空清單＝放行。

    repo_root：軍師 repo 根（信箱涵蓋判斷基準）。
    base_dir：相對路徑解析基準（hook cwd；`git -C` 段改以其 -C 路徑為基準）。
    """
    offending: list[str] = []
    for seg in _split_segments(command):
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            continue

        # 跳過前導環境變數指定，找出 git 呼叫
        idx = 0
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", tokens[idx]):
            idx += 1
        if idx >= len(tokens) or os.path.basename(tokens[idx]) != "git":
            continue
        idx += 1

        # git 全域旗標：-C／-c 帶值，其餘 -* 單獨跳過，直到子指令
        seg_base = base_dir
        while idx < len(tokens) and tokens[idx].startswith("-"):
            if tokens[idx] in ("-C", "-c") and idx + 1 < len(tokens):
                if tokens[idx] == "-C":
                    seg_base = tokens[idx + 1]
                idx += 2
            else:
                idx += 1
        if idx >= len(tokens) or tokens[idx] != "add":
            continue
        idx += 1

        for arg in tokens[idx:]:
            if arg == "--":
                continue
            if arg in ("-A", "--all"):
                offending.append(f"{arg}（整 repo 掃入）")
                continue
            if arg.startswith("-"):
                continue  # 其他旗標不在凍結範圍
            if arg in (".", ":/"):
                offending.append(f"{arg}（整 repo／整目錄掃入）")
                continue
            abs_arg = (
                arg if os.path.isabs(arg) else os.path.normpath(os.path.join(seg_base, arg))
            )
            if os.path.isdir(abs_arg) and _covers_mailbox(abs_arg, repo_root):
                offending.append(f"{arg}（涵蓋信箱路徑的整目錄）")
    return offending


def _log_deny(kunsu_root: str, command: str) -> None:
    """deny 事件記入掃描統計檔（fail-open，結構同 scan-replies.sh）。"""
    try:
        path = _stats_path()
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or not isinstance(data.get("kunsu"), dict):
                data = {"version": 1, "kunsu": {}}
        except Exception:
            data = {"version": 1, "kunsu": {}}
        ent = data["kunsu"].setdefault(kunsu_root, {})
        events = ent.setdefault("events", [])
        if not isinstance(events, list):
            events = ent["events"] = []
        ent["guard_denies"] = int(ent.get("guard_denies", 0) or 0) + 1
        events.append(
            {
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "type": "GUARD_DENY",
                "detail": command[:500],
            }
        )
        ent["events"] = events[-500:]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except Exception:
        pass


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return 0
        tool_input = data.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or "git" not in command or "add" not in command:
            return 0

        # 逃生門：指令段前導環境變數指定（token 級，非子字串）或程序環境變數
        if _has_guard_off_prefix(command) or (
            os.environ.get("KUNSU_ADD_GUARD_OFF") == "1"
        ):
            return 0

        kunsu_paths = _load_kunsu_paths()
        if not kunsu_paths:
            return 0

        cwd = data.get("cwd")
        cwd = cwd if isinstance(cwd, str) and cwd else os.getcwd()

        # 候選 repo：hook cwd 與指令中的 git -C 路徑，取其 git root 比對軍師集合
        kunsu_root: str | None = None
        for candidate in [cwd, *_extract_c_paths(command)]:
            root = _git_root(candidate)
            if root and root in kunsu_paths:
                kunsu_root = root
                break
        if kunsu_root is None:
            return 0

        offending = find_offending(command, kunsu_root, cwd)
        if not offending:
            return 0

        _log_deny(kunsu_root, command)
        _deny(DENY_MESSAGE + " 本次攔截參數：" + "、".join(offending))
        return 0
    except Exception:
        return 0  # fail-open：守門自身出錯不得阻斷任何工作


if __name__ == "__main__":
    sys.exit(main())
