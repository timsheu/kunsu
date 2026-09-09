"""
test_handoff_graph_cli.py — scripts/handoff-graph.py CLI 測試（計畫 U5）

  - 暫存軍師含依賴 → DEP:B\twaiting\tA
  - --role 過濾只列 to: 該角色
  - 無依賴 → DEP_NONE
  - 目錄不存在 → DEP_NONE、exit 0
  - 沙盤模組匯入失敗（腳本複製到暫存目錄執行，路徑推算落空）→ DEP_ERROR、exit 0
  - 循環／無法解析／異常行
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "handoff-graph.py"


def _run(*args: str, script: Path = SCRIPT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)


def _mk(directory: Path, name: str, *, status: str = "open", depends_on: str | None = None, to: str = "backend") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    dep = f"depends_on: {depends_on}\n" if depends_on else ""
    (directory / name).write_text(
        f"---\ntitle: {name[:-3]}\ntype: handoff\nstatus: {status}\nfrom: kunsu\nto: {to}\n"
        f"created: 2026-09-01\n{dep}---\n\n# x\n", encoding="utf-8")


A, B, C = "2026-09-01-a.md", "2026-09-02-b.md", "2026-09-03-c.md"


def test_waiting_line(tmp_path):
    top = tmp_path / "docs" / "handoffs"
    _mk(top, A, to="ios-app")
    _mk(top, B, depends_on=f"[{A}]")
    r = _run(str(tmp_path))
    assert r.returncode == 0
    assert f"DEP:{B}\twaiting\t{A}" in r.stdout.splitlines()
    assert f"DEP:{A}\tready\t" in r.stdout.splitlines()


def test_role_filter(tmp_path):
    top = tmp_path / "docs" / "handoffs"
    _mk(top, A, to="ios-app")
    _mk(top, B, depends_on=f"[{A}]", to="backend")
    r = _run(str(tmp_path), "--role", "backend")
    lines = r.stdout.splitlines()
    assert lines == [f"DEP:{B}\twaiting\t{A}"]


def test_no_dependency_prints_none(tmp_path):
    _mk(tmp_path / "docs" / "handoffs", A)
    r = _run(str(tmp_path))
    assert r.returncode == 0 and r.stdout.strip() == "DEP_NONE"


def test_missing_directory_prints_none():
    r = _run("/nonexistent/kunsu-xyz")
    assert r.returncode == 0 and r.stdout.strip() == "DEP_NONE"


def test_missing_argument_prints_error():
    r = _run()
    assert r.returncode == 0 and r.stdout.startswith("DEP_ERROR:")


def test_import_failure_prints_error_exit_zero(tmp_path):
    """腳本複製到暫存目錄執行，parents[2]/kunsu-dashboard 不存在 → 匯入失敗 → DEP_ERROR。"""
    copy = tmp_path / "x" / "y" / "handoff-graph.py"
    copy.parent.mkdir(parents=True)
    shutil.copy(SCRIPT, copy)
    r = _run(str(tmp_path), script=copy)
    assert r.returncode == 0
    assert r.stdout.startswith("DEP_ERROR:")


def test_issue_lines(tmp_path):
    top = tmp_path / "docs" / "handoffs"
    archive = top / "archive"
    _mk(top, A, depends_on=f"[{B}]")
    _mk(top, B, depends_on=f"[{A}, nope.md]")
    _mk(archive, C, status="open")
    r = _run(str(tmp_path))
    lines = r.stdout.splitlines()
    assert f"DEP_CYCLE:{A},{B}" in lines
    assert f"DEP_UNRESOLVED:{B}\tnope.md\tnot_found" in lines
    assert f"DEP_ANOMALY:{C}\tarchived_not_done" in lines
