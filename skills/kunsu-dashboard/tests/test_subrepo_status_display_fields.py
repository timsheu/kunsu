"""
test_subrepo_status_display_fields.py — HandoffInfo 看板顯示用欄位的單元測試

覆蓋看板化計畫（docs/plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md）
U1 的 test scenarios：
  - series 線別欄位：一般字串、YAML 型別轉換值（yes／123）、缺省與空值
  - latest_reply_filename：多份回覆取檔名排序最後一份、無回覆為 None
  - 既有三分類結果不因新增欄位而改變

兩個欄位皆為 display-only（KTD7），不參與分類。測試檔獨立於
test_subrepo_status.py，避免後者跨過 1000 行（沿用回覆摘錄測試的拆分先例）。
"""

from pathlib import Path

from app.subrepo_status import get_subrepo_status
from tests.test_subrepo_status import make_handoff, make_reply, setup_kunsu


ROLE = "my-role"


def _write_handoff_with_series(handoffs: Path, filename: str, series_line: str) -> None:
    """建立帶任意 series 行的交接文件（series_line 為整行原文，可為空字串）。"""
    content = (
        "---\n"
        "title: 線別測試\n"
        "from: ebook-store\n"
        f"to: {ROLE}\n"
        "created: 2026-09-01\n"
        "status: open\n"
        f"{series_line}\n"
        "---\n\n交接內容。\n"
    )
    (handoffs / filename).write_text(content, encoding="utf-8")


def _status(tmp_path: Path, kunsu: Path):
    return get_subrepo_status(
        subrepo_path=str(tmp_path / "subrepo"),
        our_roles={ROLE},
        all_known_roles={ROLE},
        kunsu_path=str(kunsu),
    )


class TestSeriesField:
    def test_plain_series_value(self, tmp_path):
        kunsu, handoffs, _ = setup_kunsu(tmp_path)
        _write_handoff_with_series(handoffs, "2026-09-01-a.md", "series: 線A")
        info = _status(tmp_path, kunsu).not_picked_up[0]
        assert info.series == "線A"

    def test_yaml_coerced_values_become_strings(self, tmp_path):
        kunsu, handoffs, _ = setup_kunsu(tmp_path)
        _write_handoff_with_series(handoffs, "2026-09-01-a.md", "series: yes")
        _write_handoff_with_series(handoffs, "2026-09-01-b.md", "series: 123")
        infos = {h.filename: h for h in _status(tmp_path, kunsu).not_picked_up}
        assert isinstance(infos["2026-09-01-a.md"].series, str)
        assert infos["2026-09-01-a.md"].series == str(True)
        assert infos["2026-09-01-b.md"].series == "123"

    def test_missing_or_empty_series_is_none(self, tmp_path):
        kunsu, handoffs, _ = setup_kunsu(tmp_path)
        _write_handoff_with_series(handoffs, "2026-09-01-a.md", "")
        _write_handoff_with_series(handoffs, "2026-09-01-b.md", "series:")
        _write_handoff_with_series(handoffs, "2026-09-01-c.md", 'series: "   "')
        infos = _status(tmp_path, kunsu).not_picked_up
        assert len(infos) == 3
        assert all(h.series is None for h in infos)


class TestLatestReplyFilename:
    def test_takes_last_reply_by_date_and_sequence(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-09-01-x.md", to_role=ROLE)
        make_reply(replies, "2026-09-01-x-reply-2026-09-02.md", "2026-09-01-x.md", status="partial")
        make_reply(replies, "2026-09-01-x-reply-2026-09-02-2.md", "2026-09-01-x.md", status="submitted")
        info = _status(tmp_path, kunsu).awaiting_confirm[0]
        assert info.latest_reply_filename == "2026-09-01-x-reply-2026-09-02-2.md"

    def test_no_reply_is_none(self, tmp_path):
        kunsu, handoffs, _ = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-09-01-x.md", to_role=ROLE)
        info = _status(tmp_path, kunsu).not_picked_up[0]
        assert info.latest_reply_filename is None


def test_classification_unchanged_by_display_fields(tmp_path):
    kunsu, handoffs, replies = setup_kunsu(tmp_path)
    make_handoff(handoffs, "2026-09-01-a.md", to_role=ROLE)
    make_handoff(handoffs, "2026-09-01-b.md", to_role=ROLE)
    make_handoff(handoffs, "2026-09-01-c.md", to_role=ROLE)
    make_reply(replies, "2026-09-01-b-reply-2026-09-02.md", "2026-09-01-b.md", status="partial")
    make_reply(replies, "2026-09-01-c-reply-2026-09-02.md", "2026-09-01-c.md", status="submitted")
    result = _status(tmp_path, kunsu)
    assert [h.filename for h in result.not_picked_up] == ["2026-09-01-a.md"]
    assert [h.filename for h in result.partial_done] == ["2026-09-01-b.md"]
    assert [h.filename for h in result.awaiting_confirm] == ["2026-09-01-c.md"]
