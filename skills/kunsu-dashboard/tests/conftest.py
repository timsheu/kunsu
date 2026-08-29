"""
conftest.py — 沙盤測試共用 fixture

統計檔隔離：test_kunsu_scan.py 的整合情境會實跑 scan-replies.sh，
該腳本自 v0.9.0（kunsu-inbox）起會把掃描統計寫入
~/.claude/kunsu-scan-stats.json。不隔離的話，測試會把 fixture 暫存路徑
寫進使用者的真實統計檔（比照 session hook 測試隔離狀態檔的既有教訓——
2026-08-15 doc review 抓出既有測試直寫真實狀態檔）。
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_scan_stats(tmp_path, monkeypatch) -> None:
    """所有測試一律把掃描統計導向暫存檔，不觸碰真實 ~/.claude/。"""
    monkeypatch.setenv("KUNSU_SCAN_STATS_FILE", str(tmp_path / "kunsu-scan-stats.json"))
