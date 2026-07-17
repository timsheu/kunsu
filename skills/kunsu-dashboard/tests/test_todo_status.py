"""
test_todo_status.py — skills/kunsu-dashboard/app/todo_status.py 的單元測試

覆蓋計畫 U5 的 test scenarios：
  - happy path：severity 排序、自由字串 status 歸入 pending
  - Covers AE1. status: 已解決 且未歸檔 → orphaned_done，不進 pending
  - Covers AE2. status: open 原樣顯示、計入 pending
  - edge case：無 docs/todos/ 目錄、空目錄、frontmatter 缺 status、
    內文無 H1、date 欄位 YAML 型別轉換、中文檔名、archive 計數
  - error path：讀取失敗不中斷其餘檔案處理
"""

import os
from pathlib import Path

import pytest

from app.todo_status import ErrorItem, TodoInfo, TodoStatusResult, get_todo_status


# ── 輔助函式 ────────────────────────────────────────────────────────────────────

def make_todo(
    todos_dir: Path,
    filename: str,
    status: str = "未處理",
    date: str = "2026-07-01",
    source: str = "manual",
    severity: str = "low",
    body: str | None = None,
) -> Path:
    """在 todos_dir 建立一份待辦檔案（含完整 frontmatter）。"""
    todos_dir.mkdir(parents=True, exist_ok=True)
    if body is None:
        body = f"# {filename.removesuffix('.md')}\n\n測試內文。\n"
    content = (
        "---\n"
        f"status: {status}\n"
        f"date: {date}\n"
        f"source: {source}\n"
        f"severity: {severity}\n"
        "---\n\n"
        f"{body}"
    )
    path = todos_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def make_todo_no_frontmatter_field(todos_dir: Path, filename: str, fields: dict) -> Path:
    """建立一份 frontmatter 欄位可自訂（可缺欄位）的待辦檔案，供缺欄位測試使用。"""
    todos_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {filename.removesuffix('.md')}")
    content = "\n".join(lines) + "\n"
    path = todos_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


class TestHappyPath:
    def test_severity_sort_order(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "low.md", severity="low")
        make_todo(todos_dir, "high.md", severity="high")
        make_todo(todos_dir, "medium.md", severity="medium")

        result = get_todo_status(str(tmp_path))

        assert [t.filename for t in result.pending] == ["high.md", "medium.md", "low.md"]

    def test_free_string_status_goes_to_pending(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "open.md", status="open")

        result = get_todo_status(str(tmp_path))

        assert len(result.pending) == 1
        assert result.pending[0].status == "open"
        assert result.orphaned_done == []


class TestEdgeCases:
    def test_covers_ae1_resolved_but_not_archived_goes_to_orphaned(self, tmp_path):
        """Covers AE1：status: 已解決 且檔案仍在頂層（未歸檔）——歸入 orphaned_done。"""
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "resolved.md", status="已解決")

        result = get_todo_status(str(tmp_path))

        assert result.pending == []
        assert len(result.orphaned_done) == 1
        assert result.orphaned_done[0].status == "已解決"

    def test_covers_ae2_open_status_displayed_and_counted(self, tmp_path):
        """Covers AE2：status: open 原樣顯示、計入 pending（分類與顯示值皆正確）。"""
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "open.md", status="open")

        result = get_todo_status(str(tmp_path))

        assert len(result.pending) == 1
        assert result.pending[0].status == "open"

    def test_no_todos_directory_returns_empty_result(self, tmp_path):
        result = get_todo_status(str(tmp_path))

        assert result == TodoStatusResult()

    def test_empty_todos_directory(self, tmp_path):
        (tmp_path / "docs" / "todos").mkdir(parents=True)

        result = get_todo_status(str(tmp_path))

        assert result.pending == []
        assert result.orphaned_done == []
        assert result.archive_count == 0

    def test_missing_status_field_recorded_as_error(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo_no_frontmatter_field(
            todos_dir, "no-status.md", {"date": "2026-07-01", "source": "manual", "severity": "low"}
        )

        result = get_todo_status(str(tmp_path))

        assert result.pending == []
        assert result.orphaned_done == []
        assert len(result.errors) == 1
        assert result.errors[0].filename == "no-status.md"
        assert "status" in result.errors[0].error

    def test_missing_h1_falls_back_to_filename(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "no-h1-title.md", body="沒有標題的內文。\n")

        result = get_todo_status(str(tmp_path))

        assert result.pending[0].title == "no h1 title"

    def test_unquoted_date_yaml_type_converted_to_str(self, tmp_path):
        """PyYAML safe_load 會把未加引號的 YYYY-MM-DD 解析為 datetime.date；驗證 str() 轉型。"""
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "date-test.md", date="2026-07-01")

        result = get_todo_status(str(tmp_path))

        assert result.pending[0].date == "2026-07-01"
        assert isinstance(result.pending[0].date, str)

    def test_non_ascii_filename_and_title(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(
            todos_dir,
            "書城帳號動線批次工作項.md",
            body="# 書城帳號動線批次工作項\n\n中文內文測試。\n",
        )

        result = get_todo_status(str(tmp_path))

        assert len(result.pending) == 1
        assert result.pending[0].filename == "書城帳號動線批次工作項.md"
        assert result.pending[0].title == "書城帳號動線批次工作項"

    def test_archive_count_without_reading_content(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        todos_dir.mkdir(parents=True)
        archive_dir = todos_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "a.md").write_text("---\nstatus: 已解決\n---\n", encoding="utf-8")
        (archive_dir / "b.md").write_text("not even valid frontmatter", encoding="utf-8")

        result = get_todo_status(str(tmp_path))

        assert result.archive_count == 2
        # archive/ 內容不應出現在 pending／orphaned_done（非遞迴 glob 天然排除）
        assert result.pending == []
        assert result.orphaned_done == []


class TestErrorPaths:
    def test_unreadable_file_recorded_as_error_others_continue(self, tmp_path):
        todos_dir = tmp_path / "docs" / "todos"
        make_todo(todos_dir, "good.md", severity="high")
        bad_path = make_todo(todos_dir, "bad.md", severity="low")
        os.chmod(bad_path, 0o000)

        try:
            result = get_todo_status(str(tmp_path))
        finally:
            os.chmod(bad_path, 0o644)

        assert len(result.pending) == 1
        assert result.pending[0].filename == "good.md"
        assert len(result.errors) == 1
        assert result.errors[0].filename == "bad.md"
