"""uv_reexec.py 測試：缺 PyYAML 時以 uv 重跑一次，其餘情況不動。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import uv_reexec  # noqa: E402


@pytest.fixture
def execs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, list[str]]]:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(uv_reexec.os, "execv", lambda path, args: calls.append((path, args)))
    monkeypatch.delenv(uv_reexec.GUARD_ENV, raising=False)
    return calls


def _missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uv_reexec.importlib.util, "find_spec", lambda name: None)


def test_module_present_does_not_reexec(execs, monkeypatch):
    monkeypatch.setattr(uv_reexec.shutil, "which", lambda name: "/bin/uv")
    uv_reexec.reexec_with_uv_if_missing("s.py", ["a"])
    assert execs == []


def test_missing_module_reexecs_with_uv_script(execs, monkeypatch):
    _missing(monkeypatch)
    monkeypatch.setattr(uv_reexec.shutil, "which", lambda name: "/bin/uv")
    uv_reexec.reexec_with_uv_if_missing("s.py", ["kunsu", "--role", "android"])
    assert execs == [
        ("/bin/uv", ["/bin/uv", "run", "--quiet", "--script", "s.py", "kunsu", "--role", "android"])
    ]
    assert uv_reexec.os.environ[uv_reexec.GUARD_ENV] == "1"


def test_missing_module_without_uv_returns(execs, monkeypatch):
    _missing(monkeypatch)
    monkeypatch.setattr(uv_reexec.shutil, "which", lambda name: None)
    uv_reexec.reexec_with_uv_if_missing("s.py", [])
    assert execs == []


def test_guard_env_prevents_second_reexec(execs, monkeypatch):
    _missing(monkeypatch)
    monkeypatch.setattr(uv_reexec.shutil, "which", lambda name: "/bin/uv")
    monkeypatch.setenv(uv_reexec.GUARD_ENV, "1")
    uv_reexec.reexec_with_uv_if_missing("s.py", [])
    assert execs == []


def test_execv_failure_is_fail_open(monkeypatch, capsys):
    _missing(monkeypatch)
    monkeypatch.delenv(uv_reexec.GUARD_ENV, raising=False)
    monkeypatch.setattr(uv_reexec.shutil, "which", lambda name: "/bin/uv")

    def boom(path: str, args: list[str]) -> None:
        raise OSError("exec format error")

    monkeypatch.setattr(uv_reexec.os, "execv", boom)
    uv_reexec.reexec_with_uv_if_missing("s.py", [])
    assert "uv 重新執行失敗" in capsys.readouterr().err
