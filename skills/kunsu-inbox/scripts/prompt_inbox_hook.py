#!/usr/bin/env python3
"""
prompt_inbox_hook.py — UserPromptSubmit hook：軍師 session 每次提問時提示三信箱新件

軍師 repo 內每一句使用者提問觸發一次確定性掃描：回覆／上報／申請三信箱頂層
的未 commit 新件（porcelain `??`、`A`、`AM`），首次出現的新件列檔名（每信箱
最多 MAX_ITEMS_PER_CATEGORY 筆、未點名者於後續提問輪替），之後只計數，固定
一行純文字注入 context。補的是 2026-09-23 事故缺的「派發之後、動手之前」
抵達訊號：回覆方不走 handoff skill、回覆即推播沒觸發時，軍師仍能在下一句
提問看到新件（計畫 docs/plans/2026-09-27-1232-feat-kunsu-prompt-inbox-notice-plan.md）。

不呼叫三支 scan 腳本（它們會寫統計檔並推進歷史夾帶基線）；整支腳本只跑一次
git（`status --porcelain -z`，timeout 3 秒 < 掛載 5 秒）。tripwire 與歷史夾帶警示
不在本 hook 輸出範圍。只告知不開工、事件驅動非輪詢、全程唯讀、不呼叫 LLM
（ADR 014 修訂註記）。

快退順序（非軍師 repo 零子程序）：
  stdin cwd／prompt → prompt 以 / 開頭靜默 → registry → cwd 位於任一軍師路徑下
  → 自 cwd 向上找最近的 .git 標記（純檔案系統，不跑 git）等於該軍師路徑（巢狀
  獨立 repo 會先命中內層 .git 而靜默）→ 掃描。git 失敗時零輸出且狀態不動。

狀態（機器層級，不進任何 repo）：與 session_hook.py 共用 kunsu-hook-state.json，
本腳本只動頂層鍵 prompt_inbox：{<軍師實體路徑>: {replies|reports|applications: [已點名檔名]}}；
每次掃描以現存候選集合做差集回收（歸檔、刪除、直接 commit 皆自清），tmp＋os.replace 原子寫回。
路徑覆寫：KUNSU_REGISTRY_FILE、KUNSU_HOOK_STATE_FILE（供 subprocess 測試隔離）。

掛載與解除（機器層級設定，見 SKILL.md「UserPromptSubmit hook」節）。
失敗策略 fail-open：任何錯誤零輸出、exit 0。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import session_hook  # 共用函式庫（見該檔開頭「共用函式庫註記」）
except Exception:  # 部署不完整亦 fail-open：零輸出 exit 0
    session_hook = None  # type: ignore[assignment]

STATE_KEY = "prompt_inbox"
GIT_TIMEOUT = 3  # 唯一一次 git 呼叫；小於掛載 timeout 5，使腳本自身 fail-open 恆先於 harness 逾時
MAX_NAMED = 5  # = session_hook.MAX_ITEMS_PER_CATEGORY（import 可能失敗，故在此以常數持有）
NEW_STATUS = {"??", "A ", "AM"}  # 明確集合：AD／AA／AU 等不算新件

# (狀態鍵, 信箱相對路徑, 顯示名)——順序即輸出順序
MAILBOXES = (
    ("replies", "docs/handoffs/replies", "回覆"),
    ("reports", "docs/reports", "上報"),
    ("applications", "docs/applications", "申請"),
)


def _registry_path() -> Path:
    return session_hook._env_path("KUNSU_REGISTRY_FILE", session_hook.REGISTRY_PATH)


def _read_stdin() -> tuple[str, str]:
    """取 stdin JSON 的 cwd（缺欄退回程序目錄）與 prompt（缺欄為空字串）。"""
    data = session_hook._read_stdin_json()
    cwd = data.get("cwd")
    prompt = data.get("prompt")
    return (
        cwd if isinstance(cwd, str) and cwd else os.getcwd(),
        prompt if isinstance(prompt, str) else "",
    )


def _fs_git_root(real_cwd: str) -> str | None:
    """自 cwd 向上找最近含 .git（目錄或檔案）的祖先；純檔案系統，不啟動 git。"""
    d = real_cwd
    while True:
        if os.path.lexists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _kunsu_root_for(cwd: str, kunsu_paths: set[str]) -> str | None:
    """cwd 位於某軍師路徑之下、且最近的 git root 就是該軍師路徑時回傳之（實體路徑比對）。"""
    real_cwd = os.path.realpath(cwd)
    candidates: set[str] = set()
    for k in kunsu_paths:
        real_k = os.path.realpath(k)
        if real_cwd == real_k or real_cwd.startswith(real_k + os.sep):
            candidates.add(real_k)
    if not candidates:
        return None
    root = _fs_git_root(real_cwd)
    return root if root in candidates else None


def _scan(root: str) -> dict[str, list[str]] | None:
    """三信箱頂層未 commit 新件（porcelain -z，NEW_STATUS 狀態碼的 .md）；git 失敗回傳 None。"""
    out = session_hook._run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain", "-z", "-uall", "--",
         *(rel for _, rel, _ in MAILBOXES)],
        root,
        GIT_TIMEOUT,
    )
    if out is None:
        return None
    found: dict[str, list[str]] = {key: [] for key, _, _ in MAILBOXES}
    tokens = out.split("\0")
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in "RC":
            i += 1  # rename／copy 有第二欄（原路徑），跳過
            continue
        if xy not in NEW_STATUS or not path.endswith(".md"):
            continue
        parent, name = os.path.split(path)
        for key, rel, _ in MAILBOXES:
            if parent == rel:
                found[key].append(name)
                break
    for key in found:
        found[key].sort()
    return found


def _compose(counts: dict[str, int], named: dict[str, list[str]], extra: dict[str, int]) -> str:
    count_part = "、".join(
        f"{label} {counts[key]} 份" for key, _, label in MAILBOXES if counts[key]
    )
    named_parts = []
    for key, _, label in MAILBOXES:
        if not named[key]:
            continue
        seg = f"{label} {', '.join(named[key])}"
        if extra[key] > 0:
            seg += f"（另有 {extra[key]} 份未點名）"
        named_parts.append(seg)
    line = f"📨 kunsu 信箱新件：{count_part}"
    if named_parts:
        line += "｜本次點名：" + "；".join(named_parts)
    line += "｜查看完整清單請執行 kunsu-inbox skill；本提示僅告知，不構成任何動工授權"
    return line


def main() -> int:
    try:
        if session_hook is None:
            return 0
        cwd, prompt = _read_stdin()
        if prompt.startswith("/"):
            return 0  # 斜線指令：交給 SessionStart 摘要與 skill 自身輸出
        raw = session_hook._load_raw_registry(_registry_path())
        if not raw:
            return 0
        root = _kunsu_root_for(cwd, session_hook._kunsu_paths_of(raw))
        if root is None:
            return 0

        current = _scan(root)
        if current is None:
            return 0  # git 失敗：零輸出且狀態不動，不做差集回收
        state_path = session_hook._state_path()
        state = session_hook._load_raw_registry(state_path)  # 缺檔或損壞：視同首次（重列一次）
        all_repos = state.get(STATE_KEY)
        if not isinstance(all_repos, dict):
            all_repos = {}
        repo_state = all_repos.get(root)
        if not isinstance(repo_state, dict):
            repo_state = {}

        counts: dict[str, int] = {}
        named: dict[str, list[str]] = {}
        extra: dict[str, int] = {}
        new_repo_state: dict[str, list[str]] = {}
        for key, _, _ in MAILBOXES:
            files = current[key]
            present = set(files)
            prior = repo_state.get(key)
            notified = [f for f in prior if f in present] if isinstance(prior, list) else []
            already = set(notified)
            pending = [f for f in files if f not in already]
            named[key] = pending[:MAX_NAMED]
            extra[key] = len(pending) - len(named[key])
            counts[key] = len(files)
            if notified or named[key]:
                new_repo_state[key] = notified + named[key]

        if new_repo_state != repo_state:
            if new_repo_state:
                all_repos[root] = new_repo_state
            else:
                all_repos.pop(root, None)
            state[STATE_KEY] = all_repos
            session_hook._atomic_write_json(state_path, state)

        if not any(counts.values()):
            return 0
        print(_compose(counts, named, extra))
        return 0
    except Exception:
        return 0  # fail-open：提示屬告知層，任何失敗靜默、絕不阻斷提問


if __name__ == "__main__":
    sys.exit(main())
