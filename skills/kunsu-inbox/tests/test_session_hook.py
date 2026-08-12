"""
test_session_hook.py — SessionStart hook 單元測試

涵蓋需求（docs/brainstorms/2026-08-12-awareness-automation-requirements.md）：
R1 身分偵測與未登記靜默、R2 子專案三分類輸出、R3 軍師模式輸出（格式層，
scan_kunsu 以替身注入）、R4 巢狀合併、R5 分類上限、R7 fail-open。
真實軍師端到端行為由部署後實跑驗證（驗收構想），不在本檔範圍。
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

import session_hook


# ── 共用 fixture 與輔助 ────────────────────────────────────────────────────────

def _make_git_repo(path: Path) -> str:
    """建立空 git repo，回傳 session_hook 視角的根路徑（消除 symlink 差異）。"""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", str(path)], check=True, capture_output=True
    )
    root = session_hook._git_root(str(path))
    assert root is not None
    return root


def _write_handoff(
    kunsu_dir: Path,
    filename: str,
    to_role: str,
    created: str = "2026-08-01",
) -> None:
    handoffs = kunsu_dir / "docs" / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    (handoffs / filename).write_text(
        f"---\ntitle: {filename}\ntype: handoff\nstatus: open\n"
        f"from: planner\nto: {to_role}\ncreated: {created}\n---\n\n# 本文\n",
        encoding="utf-8",
    )


def _write_reply(
    kunsu_dir: Path,
    handoff_filename: str,
    date: str,
    status: str,
    verify: str | None = None,
) -> None:
    replies = kunsu_dir / "docs" / "handoffs" / "replies"
    replies.mkdir(parents=True, exist_ok=True)
    stem = handoff_filename[:-3]  # 去 .md
    verify_line = f"verify: {verify}\n" if verify else ""
    (replies / f"{stem}-reply-{date}.md").write_text(
        f"---\ntitle: {stem} — 回覆\ntype: handoff-reply\nfrom: backend\n"
        f"to: planner\nin_reply_to: {handoff_filename}\ncreated: {date}\n"
        f"status: {status}\n{verify_line}---\n\n# 回覆\n",
        encoding="utf-8",
    )


@pytest.fixture
def registry_path(tmp_path: Path, monkeypatch) -> Path:
    reg = tmp_path / "kunsu-registry.json"
    monkeypatch.setattr(session_hook, "REGISTRY_PATH", reg)
    return reg


def _run_main(monkeypatch, cwd: str) -> int:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"cwd": cwd, "source": "startup"})),
    )
    return session_hook.main()


# ── R1：身分偵測與靜默快退 ─────────────────────────────────────────────────────

def test_unregistered_repo_silent(tmp_path, registry_path, monkeypatch, capsys):
    repo = _make_git_repo(tmp_path / "some-repo")
    registry_path.write_text(
        json.dumps({"/nonexistent/other": [{"kunsu": "/nonexistent/k", "roles": ["x"]}]}),
        encoding="utf-8",
    )
    assert _run_main(monkeypatch, repo) == 0
    assert capsys.readouterr().out == ""


def test_non_git_dir_silent(tmp_path, registry_path, monkeypatch, capsys):
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    registry_path.write_text(
        json.dumps({"/nonexistent/other": [{"kunsu": "/nonexistent/k", "roles": ["x"]}]}),
        encoding="utf-8",
    )
    assert _run_main(monkeypatch, str(plain)) == 0
    assert capsys.readouterr().out == ""


def test_empty_or_malformed_registry_silent(tmp_path, registry_path, monkeypatch, capsys):
    repo = _make_git_repo(tmp_path / "repo")

    # 註冊表不存在
    assert _run_main(monkeypatch, repo) == 0
    assert capsys.readouterr().out == ""

    # 註冊表毀損
    registry_path.write_text("{ not json", encoding="utf-8")
    assert _run_main(monkeypatch, repo) == 0
    assert capsys.readouterr().out == ""


# ── R2：子專案模式三分類 ───────────────────────────────────────────────────────

@pytest.fixture
def sub_topology(tmp_path, registry_path, monkeypatch):
    """一軍師二子專案：本 repo 角色 backend，鄰居角色 ios-app。"""
    kunsu_root = _make_git_repo(tmp_path / "kunsu-ebook")
    sub_root = _make_git_repo(tmp_path / "sub-backend")
    other_root = _make_git_repo(tmp_path / "sub-ios")
    registry_path.write_text(
        json.dumps({
            sub_root: [{"kunsu": kunsu_root, "roles": ["backend"]}],
            other_root: [{"kunsu": kunsu_root, "roles": ["ios-app"]}],
        }),
        encoding="utf-8",
    )
    return Path(kunsu_root), sub_root


def test_subrepo_categories(sub_topology, monkeypatch, capsys):
    kunsu_dir, sub_root = sub_topology
    _write_handoff(kunsu_dir, "2026-08-01-a.md", "backend", created="2026-08-01")
    _write_handoff(kunsu_dir, "2026-08-02-b.md", "backend", created="2026-08-02")
    _write_reply(kunsu_dir, "2026-08-02-b.md", "2026-08-03", "partial", verify="needs-deploy")
    _write_handoff(kunsu_dir, "2026-08-04-c.md", "backend", created="2026-08-04")
    _write_reply(kunsu_dir, "2026-08-04-c.md", "2026-08-05", "submitted")
    _write_handoff(kunsu_dir, "2026-08-06-d.md", "ios-app")     # 鄰居的件，靜默略過
    _write_handoff(kunsu_dir, "2026-08-07-e.md", "ghost-role")  # to: 不符

    assert _run_main(monkeypatch, sub_root) == 0
    out = capsys.readouterr().out

    assert "📬 kunsu 信箱" in out
    assert "[backend @ 軍師 kunsu-ebook]" in out
    assert "⚠ 未接手 1：" in out
    assert "2026-08-01-a.md（created 2026-08-01）" in out
    assert "部分完成 1：" in out
    assert "2026-08-02-b.md（partial 2026-08-03，verify: needs-deploy）" in out
    assert "已回覆待確認 1：" in out
    assert "2026-08-04-c.md（submitted 2026-08-05）" in out
    assert "⚠ to: 不符清單 1 筆" in out
    assert "2026-08-06-d.md" not in out          # 鄰居的件不得出現
    assert "不構成任何動工授權" in out            # 人工閘門提示


def test_done_handoff_excluded(sub_topology, monkeypatch, capsys):
    kunsu_dir, sub_root = sub_topology
    _write_handoff(kunsu_dir, "2026-08-01-x.md", "backend")
    _write_reply(kunsu_dir, "2026-08-01-x.md", "2026-08-02", "done")

    assert _run_main(monkeypatch, sub_root) == 0
    out = capsys.readouterr().out
    assert "📬 kunsu 信箱：無待辦" in out
    assert "2026-08-01-x.md" not in out


def test_empty_inbox_one_liner(sub_topology, monkeypatch, capsys):
    _, sub_root = sub_topology
    assert _run_main(monkeypatch, sub_root) == 0
    assert "📬 kunsu 信箱：無待辦" in capsys.readouterr().out


def test_stale_kunsu_path_warns(tmp_path, registry_path, monkeypatch, capsys):
    sub_root = _make_git_repo(tmp_path / "sub")
    registry_path.write_text(
        json.dumps({sub_root: [{"kunsu": str(tmp_path / "gone-kunsu"), "roles": ["backend"]}]}),
        encoding="utf-8",
    )
    assert _run_main(monkeypatch, sub_root) == 0
    assert "路徑失聯" in capsys.readouterr().out


# ── R5：分類上限 ───────────────────────────────────────────────────────────────

def test_category_cap_with_overflow(sub_topology, monkeypatch, capsys):
    kunsu_dir, sub_root = sub_topology
    for i in range(7):
        _write_handoff(kunsu_dir, f"2026-08-0{i + 1}-n{i}.md", "backend",
                       created=f"2026-08-0{i + 1}")

    assert _run_main(monkeypatch, sub_root) == 0
    out = capsys.readouterr().out
    assert "⚠ 未接手 7：" in out
    assert out.count("• 2026-08-") == 5
    assert "…另有 2 筆" in out
    # created 升冪：最舊的先列，溢出的是最新兩筆
    assert "2026-08-01-n0.md" in out
    assert "2026-08-07-n6.md" not in out


# ── R3／R4：軍師模式與巢狀合併（scan_kunsu 以替身注入，格式層驗證） ─────────────

def _fake_scan_result(kunsu_path: str):
    from app.kunsu_scan import KunsuScanResult

    return KunsuScanResult(
        kunsu_path=kunsu_path,
        new_replies=["docs/handoffs/replies/r1.md", "docs/handoffs/replies/r2.md"],
        new_applications=[],
        new_reports=["docs/reports/p1.md"],
    )


def test_kunsu_mode_formatting(tmp_path, registry_path, monkeypatch, capsys):
    kunsu_root = _make_git_repo(tmp_path / "kunsu-x")
    sub_root = _make_git_repo(tmp_path / "sub-x")
    registry_path.write_text(
        json.dumps({sub_root: [{"kunsu": kunsu_root, "roles": ["backend"]}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.kunsu_scan.scan_kunsu", _fake_scan_result)

    assert _run_main(monkeypatch, kunsu_root) == 0
    out = capsys.readouterr().out
    assert "[軍師模式 @ kunsu-x]" in out
    assert "新回覆 2：" in out
    assert "• docs/handoffs/replies/r1.md" in out
    assert "新上報 1：" in out
    assert "新申請" not in out  # 零分類省略


def test_nested_topology_merges_both_modes(tmp_path, registry_path, monkeypatch, capsys):
    """巢狀拓撲：同一 repo 既是子專案（上層軍師管它）也是軍師。"""
    upper_kunsu = _make_git_repo(tmp_path / "upper")
    nested_root = _make_git_repo(tmp_path / "nested")
    registry_path.write_text(
        json.dumps({
            nested_root: [{"kunsu": upper_kunsu, "roles": ["sub-planner"]}],
            str(tmp_path / "leaf"): [{"kunsu": nested_root, "roles": ["leaf-role"]}],
        }),
        encoding="utf-8",
    )
    _write_handoff(Path(upper_kunsu), "2026-08-01-up.md", "sub-planner")
    monkeypatch.setattr("app.kunsu_scan.scan_kunsu", _fake_scan_result)

    assert _run_main(monkeypatch, nested_root) == 0
    out = capsys.readouterr().out
    assert "[sub-planner @ 軍師 upper]" in out   # 子專案模式段
    assert "2026-08-01-up.md" in out
    assert "[軍師模式 @ nested]" in out          # 軍師模式段


# ── R7：fail-open ─────────────────────────────────────────────────────────────

def test_fail_open_after_identity(sub_topology, monkeypatch, capsys):
    _, sub_root = sub_topology

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(session_hook, "_sub_mode_lines", _boom)
    assert _run_main(monkeypatch, sub_root) == 0
    out = capsys.readouterr().out
    assert "降級" in out
    assert "RuntimeError" in out


def test_fail_open_before_identity_is_silent(tmp_path, registry_path, monkeypatch, capsys):
    repo = _make_git_repo(tmp_path / "repo")
    registry_path.write_text(
        json.dumps({"/other": [{"kunsu": "/k", "roles": ["x"]}]}), encoding="utf-8"
    )

    def _boom(cwd):
        raise RuntimeError("boom")

    monkeypatch.setattr(session_hook, "_git_root", _boom)
    assert _run_main(monkeypatch, repo) == 0
    assert capsys.readouterr().out == ""
