"""
test_prompt_inbox_hook.py — UserPromptSubmit hook（prompt_inbox_hook.py）端到端測試

全部以 subprocess 實跑腳本（stdin JSON → stdout 純文字），registry 與狀態檔
一律以環境變數導向 tmp_path，不觸真實 ~/.claude/。涵蓋計畫
docs/plans/2026-09-27-1232-feat-kunsu-prompt-inbox-notice-plan.md 的 AE1–AE9 與 F4。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prompt_inbox_hook.py"
MAILBOXES = {
    "replies": "docs/handoffs/replies",
    "reports": "docs/reports",
    "applications": "docs/applications",
}


# ─── fixtures ────────────────────────────────────────────────────────────────


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture()
def kunsu_repo(tmp_path) -> Path:
    """帶三信箱（含 archive）的軍師 git repo，實體路徑（消 /tmp symlink 差）。"""
    repo = (tmp_path / "kunsu").resolve()
    for m in (
        "docs/handoffs/replies/archive",
        "docs/handoffs/archive/replies",
        "docs/reports/archive",
        "docs/applications/archive",
    ):
        (repo / m).mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("x", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


@pytest.fixture()
def hook_env(tmp_path, kunsu_repo) -> dict:
    """registry 登記 kunsu_repo 為軍師（sub 為另一 tmp 目錄）、狀態檔導向 tmp。"""
    sub = (tmp_path / "sub").resolve()
    sub.mkdir()
    _git(sub, "init", "-q")
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({str(sub): [{"kunsu": str(kunsu_repo), "roles": ["backend"]}]}),
        encoding="utf-8",
    )
    state = tmp_path / "hook-state.json"
    env = dict(os.environ)
    env["KUNSU_REGISTRY_FILE"] = str(registry)
    env["KUNSU_HOOK_STATE_FILE"] = str(state)
    return {"env": env, "state": state, "repo": kunsu_repo, "sub": sub, "registry": registry}


def _run(env: dict, cwd: str, prompt: str = "可以重啟了") -> str:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        input=json.dumps({"cwd": cwd, "prompt": prompt, "hook_event_name": "UserPromptSubmit"}),
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr  # fail-open 契約：一律 exit 0
    return proc.stdout


def _put(repo: Path, mailbox: str, name: str, body: str = "---\nstatus: submitted\n---\n") -> Path:
    p = repo / MAILBOXES[mailbox] / name
    p.write_text(body, encoding="utf-8")
    return p


def _state(env: dict) -> dict:
    return json.loads(Path(env["KUNSU_HOOK_STATE_FILE"]).read_text(encoding="utf-8"))


REPLY = "2026-09-23-今晚直接切正式-reply-2026-09-23.md"


# ─── AE1／AE2：首次列名、之後計數 ───────────────────────────────────────────


def test_first_prompt_names_file_second_prompt_counts_only(hook_env):
    """Covers AE1／AE2."""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    out1 = _run(env, str(repo))
    assert out1.count("\n") == 1  # 恰一行
    assert REPLY in out1 and "回覆 1 份" in out1
    assert "kunsu-inbox skill" in out1 and "不構成任何動工授權" in out1
    out2 = _run(env, str(repo))
    assert out2.count("\n") == 1
    assert "回覆 1 份" in out2 and REPLY not in out2
    assert _state(env)["prompt_inbox"][str(repo)]["replies"] == [REPLY]


# ─── AE3：三信箱、上限與輪替 ────────────────────────────────────────────────


def test_three_mailboxes_cap_and_rotation(hook_env):
    """Covers AE3. 16 份回覆＋1 份上報：點名 5／5／5／1，第五次起僅計數。"""
    env, repo = hook_env["env"], hook_env["repo"]
    names = [f"2026-09-{i:02d}-h-reply-2026-09-{i:02d}.md" for i in range(1, 17)]
    for n in names:
        _put(repo, "replies", n)
    _put(repo, "reports", "2026-09-20-x-report.md")

    def named_replies(out: str) -> list[str]:
        return [n for n in names if n in out]

    outs = [_run(env, str(repo)) for _ in range(5)]
    assert [len(named_replies(o)) for o in outs] == [5, 5, 5, 1, 0]
    assert named_replies(outs[0]) == names[:5]  # 字典序
    assert "另有 11 份未點名" in outs[0]
    assert "2026-09-20-x-report.md" in outs[0] and "2026-09-20-x-report.md" not in outs[1]
    for o in outs:
        assert "回覆 16 份" in o and "上報 1 份" in o and "申請" not in o
        assert o.count("\n") == 1
    assert "點名" not in outs[4]
    assert sorted(_state(env)["prompt_inbox"][str(repo)]["replies"]) == sorted(names)


# ─── AE4／AE9：歸檔或直接 commit 後靜默並自清 ──────────────────────────────


def test_archive_clears_output_and_state(hook_env):
    """Covers AE4."""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    _run(env, str(repo))
    _git(repo, "add", "--", f"docs/handoffs/replies/{REPLY}")
    _git(repo, "mv", f"docs/handoffs/replies/{REPLY}", f"docs/handoffs/archive/replies/{REPLY}")
    _git(repo, "commit", "-q", "-m", "docs: 歸檔交接")
    assert _run(env, str(repo)) == ""
    assert str(repo) not in _state(env).get("prompt_inbox", {})


def test_direct_commit_without_archive_goes_silent(hook_env):
    """Covers AE9（已知限制）。"""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    assert REPLY in _run(env, str(repo))
    _git(repo, "add", "--", f"docs/handoffs/replies/{REPLY}")
    _git(repo, "commit", "-q", "-m", "docs: 建立交接 x")
    assert _run(env, str(repo)) == ""
    assert str(repo) not in _state(env).get("prompt_inbox", {})


# ─── AE5／F4：身分與 fail-open ──────────────────────────────────────────────


def test_subrepo_and_unregistered_are_silent(hook_env, tmp_path):
    """Covers AE5／F4."""
    env = hook_env["env"]
    _put(hook_env["repo"], "replies", REPLY)
    assert _run(env, str(hook_env["sub"])) == ""
    other = (tmp_path / "other").resolve()
    other.mkdir()
    _git(other, "init", "-q")
    assert _run(env, str(other)) == ""
    assert not Path(env["KUNSU_HOOK_STATE_FILE"]).exists()


def test_corrupt_registry_is_silent(hook_env):
    """Covers AE5."""
    env = hook_env["env"]
    Path(env["KUNSU_REGISTRY_FILE"]).write_text("{not json", encoding="utf-8")
    _put(hook_env["repo"], "replies", REPLY)
    assert _run(env, str(hook_env["repo"])) == ""


def test_git_missing_is_silent(hook_env, tmp_path):
    """Covers AE5. PATH 清空找不到 git：零輸出 exit 0。"""
    env = dict(hook_env["env"])
    env["PATH"] = str(tmp_path / "empty-bin")
    _put(hook_env["repo"], "replies", REPLY)
    assert _run(env, str(hook_env["repo"])) == ""


def test_slash_prompt_is_silent_and_writes_no_state(hook_env):
    """Covers F4. 斜線指令提問靜默，狀態檔不被建立。"""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    assert _run(env, str(repo), prompt="/kunsu-inbox") == ""
    assert _run(env, str(repo), prompt="/clear") == ""
    assert not Path(env["KUNSU_HOOK_STATE_FILE"]).exists()


def test_non_kunsu_cwd_never_spawns_git(hook_env, tmp_path):
    """非軍師 repo 快退不啟動 git：假 git 哨兵寫 marker；軍師 cwd 為正向對照。"""
    env = dict(hook_env["env"])
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    marker = tmp_path / "git-called"
    (fakebin / "git").write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 0\n", encoding="utf-8")
    (fakebin / "git").chmod(0o755)
    env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
    other = (tmp_path / "other").resolve()
    other.mkdir()
    assert _run(env, str(other)) == ""
    assert not marker.exists()
    assert _run(env, str(hook_env["repo"])) == ""  # 假 git 回空 → root None → 靜默
    assert marker.exists()


# ─── AE6／AE7：tripwire 形狀不入此行 ────────────────────────────────────────


def test_modified_committed_reply_is_ignored(hook_env):
    """Covers AE6／AE7."""
    env, repo = hook_env["env"], hook_env["repo"]
    old = "2026-09-01-old-reply-2026-09-01.md"
    _put(repo, "replies", old)
    _git(repo, "add", "--", f"docs/handoffs/replies/{old}")
    _git(repo, "commit", "-q", "-m", "docs: x")
    (repo / MAILBOXES["replies"] / old).write_text("changed", encoding="utf-8")
    assert _run(env, str(repo)) == ""  # 純 tripwire 形狀：零輸出
    _put(repo, "replies", REPLY)
    out = _run(env, str(repo))
    assert REPLY in out and old not in out and "回覆 1 份" in out


# ─── 新件判定邊界 ──────────────────────────────────────────────────────────


def test_index_added_and_added_modified_count_as_new(hook_env):
    env, repo = hook_env["env"], hook_env["repo"]
    a = "2026-09-02-a-reply-2026-09-02.md"
    am = "2026-09-03-b-reply-2026-09-03.md"
    _put(repo, "replies", a)
    _put(repo, "replies", am)
    _git(repo, "add", "--", f"docs/handoffs/replies/{a}", f"docs/handoffs/replies/{am}")
    (repo / MAILBOXES["replies"] / am).write_text("more", encoding="utf-8")
    out = _run(env, str(repo))
    assert a in out and am in out and "回覆 2 份" in out


def test_archive_subdir_untracked_not_counted(hook_env):
    env, repo = hook_env["env"], hook_env["repo"]
    (repo / "docs/handoffs/replies/archive/x-reply-2026-01-01.md").write_text("x", encoding="utf-8")
    (repo / "docs/handoffs/archive/replies/y-reply-2026-01-01.md").write_text("y", encoding="utf-8")
    (repo / "docs/reports/archive/z-report.md").write_text("z", encoding="utf-8")
    assert _run(env, str(repo)) == ""


def test_chinese_filename_listed_verbatim(hook_env):
    env, repo = hook_env["env"], hook_env["repo"]
    name = "2026-09-23-書城web來源封面-reply-2026-09-23.md"
    _put(repo, "replies", name)
    out = _run(env, str(repo))
    assert name in out and "\\" not in out


def test_state_preserves_other_keys_and_corrupt_state_rebuilds(hook_env):
    env, repo = hook_env["env"], hook_env["repo"]
    Path(env["KUNSU_HOOK_STATE_FILE"]).write_text(
        json.dumps({"handoff_version": "0.23.0"}), encoding="utf-8"
    )
    _put(repo, "replies", REPLY)
    _run(env, str(repo))
    st = _state(env)
    assert st["handoff_version"] == "0.23.0"
    assert st["prompt_inbox"][str(repo)]["replies"] == [REPLY]
    Path(env["KUNSU_HOOK_STATE_FILE"]).write_text("{broken", encoding="utf-8")
    out = _run(env, str(repo))
    assert REPLY in out  # 視同首次：重列一次
    assert _state(env)["prompt_inbox"][str(repo)]["replies"] == [REPLY]


def test_nested_topology_takes_kunsu_branch(hook_env):
    """cwd 同時登記為子專案與軍師 → 走軍師分支輸出。"""
    env, repo = hook_env["env"], hook_env["repo"]
    reg = json.loads(Path(env["KUNSU_REGISTRY_FILE"]).read_text(encoding="utf-8"))
    reg[str(repo)] = [{"kunsu": str(hook_env["sub"]), "roles": ["nested"]}]
    Path(env["KUNSU_REGISTRY_FILE"]).write_text(json.dumps(reg), encoding="utf-8")
    _put(repo, "replies", REPLY)
    assert REPLY in _run(env, str(repo))


def test_subdirectory_cwd_inside_kunsu_repo(hook_env):
    """cwd 在軍師 repo 子目錄時仍判為軍師。"""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    assert REPLY in _run(env, str(repo / "docs"))


# ─── code review 補強（2026-09-27 review #2／#4／#5／#6／#7、testing gaps） ──────


def test_filename_with_spaces_is_counted_and_named(hook_env):
    """review #2：porcelain 對含空格路徑加引號，須以 -z 解析。"""
    env, repo = hook_env["env"], hook_env["repo"]
    name = "2026-09-23-store nginx 切換-reply-2026-09-23.md"
    _put(repo, "replies", name)
    out = _run(env, str(repo))
    assert name in out and "回覆 1 份" in out


def test_added_then_deleted_in_worktree_is_not_new(hook_env):
    """review #5：AD（index 已 add、工作樹已刪）不算新件。"""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    _git(repo, "add", "--", f"docs/handoffs/replies/{REPLY}")
    (repo / MAILBOXES["replies"] / REPLY).unlink()
    assert _run(env, str(repo)) == ""


def test_git_failure_keeps_state_untouched(hook_env, tmp_path):
    """review #4：git status 失敗時零輸出且狀態不變（不做差集回收）。"""
    env, repo = hook_env["env"], hook_env["repo"]
    _put(repo, "replies", REPLY)
    _run(env, str(repo))
    before = _state(env)
    fakebin = tmp_path / "failbin"
    fakebin.mkdir()
    (fakebin / "git").write_text("#!/bin/sh\nexit 128\n", encoding="utf-8")
    (fakebin / "git").chmod(0o755)
    env2 = dict(env)
    env2["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
    assert _run(env2, str(repo)) == ""
    assert _state(env) == before
    assert REPLY not in _run(env, str(repo))  # 恢復後不重複點名


def test_nested_non_kunsu_repo_inside_kunsu_path_never_spawns_git(hook_env, tmp_path):
    """review #6：已登記路徑之下的巢狀獨立 git repo 不啟動 git。"""
    env, repo = hook_env["env"], hook_env["repo"]
    nested = repo / "vendor" / "inner"
    nested.mkdir(parents=True)
    _git(nested, "init", "-q")
    fakebin = tmp_path / "fakebin2"
    fakebin.mkdir()
    marker = tmp_path / "git-called-2"
    (fakebin / "git").write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 0\n", encoding="utf-8")
    (fakebin / "git").chmod(0o755)
    env2 = dict(env)
    env2["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
    assert _run(env2, str(nested)) == ""
    assert not marker.exists()


def test_partial_archive_recycles_only_gone_files(hook_env):
    """testing gap：同信箱部分已點名件歸檔，其餘保留於已點名清單。"""
    env, repo = hook_env["env"], hook_env["repo"]
    names = [f"2026-09-0{i}-p-reply-2026-09-0{i}.md" for i in (1, 2, 3)]
    for n in names:
        _put(repo, "replies", n)
    _run(env, str(repo))
    _git(repo, "add", "--", f"docs/handoffs/replies/{names[0]}")
    _git(repo, "mv", f"docs/handoffs/replies/{names[0]}", f"docs/handoffs/archive/replies/{names[0]}")
    _git(repo, "commit", "-q", "-m", "docs: 歸檔交接")
    out = _run(env, str(repo))
    assert "回覆 2 份" in out and "點名" not in out
    assert _state(env)["prompt_inbox"][str(repo)]["replies"] == names[1:]


def test_missing_helper_module_is_fail_open(hook_env, tmp_path):
    """residual：部署不完整（session_hook.py 缺失）仍 exit 0 零輸出。"""
    lone = tmp_path / "lone"
    lone.mkdir()
    import shutil
    shutil.copy(_SCRIPT, lone / "prompt_inbox_hook.py")
    proc = subprocess.run(
        [sys.executable, str(lone / "prompt_inbox_hook.py")],
        input=json.dumps({"cwd": str(hook_env["repo"]), "prompt": "hi"}),
        capture_output=True, text=True, env=hook_env["env"], timeout=20,
    )
    assert proc.returncode == 0 and proc.stdout == "" and proc.stderr == ""
