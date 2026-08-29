"""
test_git_guard.py — pretooluse_git_guard 的測試（ADR 017）

純函式層測 find_offending 的凍結三形狀判定與信箱涵蓋邏輯；
端到端層以 subprocess 實跑 hook（stdin JSON → stdout deny JSON），
registry 與統計檔一律以環境變數導向 tmp_path，不觸真實 ~/.claude/。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import pretooluse_git_guard as guard

_GUARD_PATH = Path(guard.__file__).resolve()


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def kunsu_repo(tmp_path) -> Path:
    """一個帶三信箱目錄的軍師 git repo（實體路徑，避免 /tmp symlink 誤差）。"""
    repo = (tmp_path / "kunsu").resolve()
    for m in ("docs/handoffs/replies", "docs/applications", "docs/reports", "skills"):
        (repo / m).mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "docs/handoffs/2026-01-01-x.md").write_text("x", encoding="utf-8")
    return repo


@pytest.fixture()
def hook_env(tmp_path, kunsu_repo, monkeypatch) -> dict:
    """端到端環境：registry 登記 kunsu_repo 為軍師、統計檔導向 tmp。"""
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({str(tmp_path / "sub"): [{"kunsu": str(kunsu_repo), "roles": ["r"]}]}),
        encoding="utf-8",
    )
    stats = tmp_path / "stats.json"
    import os

    env = dict(os.environ)
    env["KUNSU_REGISTRY_FILE"] = str(registry)
    env["KUNSU_SCAN_STATS_FILE"] = str(stats)
    env.pop("KUNSU_ADD_GUARD_OFF", None)
    return {"env": env, "stats": stats, "repo": kunsu_repo}


def _run_hook(env: dict, payload: dict) -> str:
    proc = subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 0  # fail-open 契約：一律 exit 0
    return proc.stdout


def _bash_payload(command: str, cwd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


# ─── 純函式：find_offending ──────────────────────────────────────────────────


def test_dash_a_and_all_offend(kunsu_repo):
    root = str(kunsu_repo)
    assert guard.find_offending("git add -A", root, root)
    assert guard.find_offending("git add --all", root, root)


def test_dot_and_root_pathspec_offend(kunsu_repo):
    root = str(kunsu_repo)
    assert guard.find_offending("git add .", root, root)
    assert guard.find_offending("git add :/", root, root)


def test_mailbox_dir_and_ancestor_offend(kunsu_repo):
    root = str(kunsu_repo)
    assert guard.find_offending("git add docs/handoffs", root, root)
    assert guard.find_offending("git add docs/handoffs/", root, root)
    assert guard.find_offending("git add docs/handoffs/replies", root, root)
    assert guard.find_offending("git add docs", root, root)  # 信箱祖先目錄


def test_specific_files_allowed(kunsu_repo):
    root = str(kunsu_repo)
    cmd = "git add docs/handoffs/2026-01-01-x.md docs/handoffs/archive/y.md"
    assert guard.find_offending(cmd, root, root) == []


def test_non_mailbox_dir_allowed(kunsu_repo):
    # ADR 017 範圍：整目錄僅攔「涵蓋信箱路徑」者，其他目錄放行
    root = str(kunsu_repo)
    assert guard.find_offending("git add skills", root, root) == []


def test_non_add_git_commands_allowed(kunsu_repo):
    root = str(kunsu_repo)
    assert guard.find_offending('git commit -m "docs: 歸檔交接 x.md"', root, root) == []
    assert guard.find_offending("git status", root, root) == []


def test_compound_command_segment_detected(kunsu_repo):
    root = str(kunsu_repo)
    assert guard.find_offending("python3 x.py && git add -A", root, root)


def test_git_c_segment_uses_c_path_as_base(kunsu_repo, tmp_path):
    # 從外部 cwd 以 git -C 指向軍師 repo 的相對目錄仍判定
    outside = str(tmp_path)
    cmd = f"git -C {kunsu_repo} add docs/handoffs"
    assert guard.find_offending(cmd, str(kunsu_repo), outside)


# ─── 端到端：main()（subprocess，stdin JSON） ────────────────────────────────


def test_e2e_deny_dash_a_in_kunsu_repo(hook_env):
    out = _run_hook(hook_env["env"], _bash_payload("git add -A", str(hook_env["repo"])))
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "僅限具體檔案路徑" in decision["permissionDecisionReason"]
    assert "archive-handoff.sh" in decision["permissionDecisionReason"]


def test_e2e_deny_logged_to_stats(hook_env):
    _run_hook(hook_env["env"], _bash_payload("git add -A", str(hook_env["repo"])))
    stats = json.loads(hook_env["stats"].read_text(encoding="utf-8"))
    ent = stats["kunsu"][str(hook_env["repo"])]
    assert ent["guard_denies"] == 1
    assert ent["events"][-1]["type"] == "GUARD_DENY"


def test_e2e_allow_specific_paths(hook_env):
    out = _run_hook(
        hook_env["env"],
        _bash_payload("git add docs/handoffs/2026-01-01-x.md", str(hook_env["repo"])),
    )
    assert out == ""


def test_e2e_allow_outside_kunsu_repo(hook_env, tmp_path):
    other = (tmp_path / "other").resolve()
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    out = _run_hook(hook_env["env"], _bash_payload("git add -A", str(other)))
    assert out == ""


def test_e2e_escape_hatch_prefix(hook_env):
    out = _run_hook(
        hook_env["env"],
        _bash_payload("KUNSU_ADD_GUARD_OFF=1 git add -A", str(hook_env["repo"])),
    )
    assert out == ""


def test_e2e_deny_via_git_c_from_outside(hook_env, tmp_path):
    outside = (tmp_path / "elsewhere").resolve()
    outside.mkdir()
    out = _run_hook(
        hook_env["env"],
        _bash_payload(f"git -C {hook_env['repo']} add -A", str(outside)),
    )
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_e2e_non_bash_tool_allowed(hook_env):
    out = _run_hook(
        hook_env["env"],
        {"tool_name": "Edit", "tool_input": {"command": "git add -A"}, "cwd": str(hook_env["repo"])},
    )
    assert out == ""


def test_e2e_corrupted_registry_fail_open(hook_env):
    Path(hook_env["env"]["KUNSU_REGISTRY_FILE"]).write_text("{broken", encoding="utf-8")
    out = _run_hook(hook_env["env"], _bash_payload("git add -A", str(hook_env["repo"])))
    assert out == ""
