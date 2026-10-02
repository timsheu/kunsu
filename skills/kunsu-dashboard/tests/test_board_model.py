"""
test_board_model.py — app/board_model.py（看板持球者與欄位歸屬）的單元測試

覆蓋看板化計畫（docs/plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md）
U2 的 test scenarios：AE1–AE3 歸欄、已回覆但依賴未滿足、孤立交接、未知 status、
未知收件角色、頂層已 done 未歸檔、回覆自標 done、信箱卡片、tripwire、軍師失聯、
泳道命名碰撞與順序、欄內排序、壞檔去重、等待項標題與無法解析依賴、空看板。

本模組為純函式：以資料類別直接組裝輸入，只有信箱卡片讀取申請／上報檔標題時
需要 tmp_path 實際檔案。
"""

from pathlib import Path

import pytest

from app.board_model import (
    ANOMALY_DEPENDENCY,
    ANOMALY_PARSE_ERROR,
    ANOMALY_REPLY_DONE,
    ANOMALY_SCRIPT_ERROR,
    ANOMALY_STALE,
    ANOMALY_TOP_DONE_UNARCHIVED,
    ANOMALY_TRIPWIRE,
    ANOMALY_UNKNOWN_TO,
    CARD_APPLICATION,
    CARD_HANDOFF,
    CARD_REPORT,
    COL_DOING,
    COL_REVIEW,
    COL_TODO,
    COL_WAITING,
    LANE_KUNSU,
    build_board,
)
from app.handoff_graph import (
    DERIVED_READY,
    DERIVED_WAITING,
    LOCATION_ARCHIVE,
    LOCATION_TOP,
    HandoffGraphResult,
    HandoffNode,
    UnresolvedEdge,
)
from app.handoff_graph import ErrorItem as GraphErrorItem
from app.kunsu_scan import KunsuScanResult
from app.subrepo_status import ErrorItem as SubErrorItem
from app.subrepo_status import HandoffInfo, SubrepoStatusResult, UnknownToItem
from app.todo_status import TodoInfo, TodoStatusResult

KUNSU = "/fake/ebook"
ROLES = {"android", "backend"}


# ── 輔助函式 ────────────────────────────────────────────────────────────────────

def _h(
    filename: str,
    to_role: str = "android",
    status: str | None = None,
    reply_date: str | None = None,
    verify: str | None = None,
    created: str = "2026-09-01",
    title: str | None = None,
    reply_filename: str | None = None,
) -> HandoffInfo:
    return HandoffInfo(
        filename=filename,
        title=title or f"標題-{filename}",
        from_role="kunsu",
        to_role=to_role,
        created=created,
        latest_reply_status=status,
        latest_reply_date=reply_date,
        latest_reply_verify=verify,
        latest_reply_filename=reply_filename,
    )


def _sub(not_picked=(), partial=(), awaiting=(), unknown=(), errors=()) -> SubrepoStatusResult:
    return SubrepoStatusResult(
        not_picked_up=list(not_picked),
        partial_done=list(partial),
        awaiting_confirm=list(awaiting),
        unknown_to=list(unknown),
        errors=list(errors),
    )


def _node(filename, to_role="android", status="open", location=LOCATION_TOP, title=None):
    return HandoffNode(
        filename=filename,
        title=title or f"標題-{filename}",
        to_role=to_role,
        status=status,
        location=location,
    )


def _graph(nodes=(), derived=None, waiting_on=None, unresolved=(), errors=()):
    return HandoffGraphResult(
        nodes={n.filename: n for n in nodes},
        derived=dict(derived or {}),
        waiting_on=dict(waiting_on or {}),
        unresolved=list(unresolved),
        errors=list(errors),
    )


def _build(sub=None, scan=None, graph=None, todo=None, stale=False, roles=ROLES):
    return build_board(
        kunsu_path=KUNSU,
        known_roles=set(roles),
        sub=sub if sub is not None else _sub(),
        scan=scan if scan is not None else KunsuScanResult(kunsu_path=KUNSU),
        graph=graph if graph is not None else _graph(),
        todo=todo if todo is not None else TodoStatusResult(),
        stale=stale,
    )


def _cell(board, lane, col):
    return board.cells.get((lane, col), ())


def _kinds(board):
    return {a.kind for a in board.anomalies}


# ── 歸欄規則 ────────────────────────────────────────────────────────────────────

def test_not_picked_up_goes_to_role_todo():
    """Covers AE1（前半）。"""
    h = _h("a.md")
    board = _build(sub=_sub(not_picked=[h]), graph=_graph([_node("a.md")]))
    cards = _cell(board, "android", COL_TODO)
    assert [c.filename for c in cards] == ["a.md"]
    assert cards[0].kind == CARD_HANDOFF
    assert cards[0].base_date == "2026-09-01"


def test_submitted_goes_to_kunsu_review_with_verify():
    """Covers AE1（後半）。"""
    h = _h("a.md", status="submitted", reply_date="2026-09-05", verify="needs-device")
    board = _build(sub=_sub(awaiting=[h]), graph=_graph([_node("a.md")]))
    cards = _cell(board, LANE_KUNSU, COL_REVIEW)
    assert [c.filename for c in cards] == ["a.md"]
    assert cards[0].verify == "needs-device"
    assert cards[0].base_date == "2026-09-05"
    assert _cell(board, "android", COL_TODO) == ()


def test_blocked_goes_to_kunsu_doing_with_blocked_flag():
    """Covers AE2。"""
    h = _h("a.md", status="blocked", reply_date="2026-09-05")
    board = _build(sub=_sub(partial=[h]), graph=_graph([_node("a.md")]))
    cards = _cell(board, LANE_KUNSU, COL_DOING)
    assert [c.filename for c in cards] == ["a.md"]
    assert cards[0].blocked is True
    for col in (COL_WAITING, COL_TODO, COL_DOING, COL_REVIEW):
        assert _cell(board, "android", col) == ()


def test_waiting_without_reply_goes_to_role_waiting():
    """Covers AE3（前半）。"""
    h = _h("a.md")
    graph = _graph(
        [_node("a.md"), _node("dep.md", title="前置交接")],
        derived={"a.md": DERIVED_WAITING},
        waiting_on={"a.md": ["dep.md"]},
    )
    board = _build(sub=_sub(not_picked=[h]), graph=graph)
    cards = _cell(board, "android", COL_WAITING)
    assert [c.filename for c in cards] == ["a.md"]
    assert cards[0].waiting_titles == ("前置交接",)
    assert cards[0].unresolved_waiting == ()


def test_ready_without_reply_goes_to_role_todo():
    """Covers AE3（後半）。"""
    h = _h("a.md")
    graph = _graph([_node("a.md")], derived={"a.md": DERIVED_READY})
    board = _build(sub=_sub(not_picked=[h]), graph=graph)
    assert [c.filename for c in _cell(board, "android", COL_TODO)] == ["a.md"]


def test_partial_with_unmet_dependency_stays_doing_and_lists_wait():
    h = _h("a.md", status="partial", reply_date="2026-09-05")
    graph = _graph(
        [_node("a.md"), _node("dep.md", title="前置交接")],
        derived={"a.md": DERIVED_WAITING},
        waiting_on={"a.md": ["dep.md"]},
    )
    board = _build(sub=_sub(partial=[h]), graph=graph)
    cards = _cell(board, "android", COL_DOING)
    assert [c.filename for c in cards] == ["a.md"]
    assert cards[0].waiting_titles == ("前置交接",)
    assert _cell(board, "android", COL_WAITING) == ()


def test_isolated_handoff_not_in_derived_goes_todo():
    h = _h("a.md")
    board = _build(sub=_sub(not_picked=[h]), graph=_graph([_node("a.md")]))
    assert [c.filename for c in _cell(board, "android", COL_TODO)] == ["a.md"]


def test_unknown_reply_status_goes_doing_and_keeps_raw_value():
    h = _h("a.md", status="archived", reply_date="2026-09-05")
    board = _build(sub=_sub(partial=[h]), graph=_graph([_node("a.md")]))
    cards = _cell(board, "android", COL_DOING)
    assert cards[0].unknown_status == "archived"
    assert cards[0].blocked is False


def test_partial_has_no_unknown_status():
    h = _h("a.md", status="partial", reply_date="2026-09-05")
    board = _build(sub=_sub(partial=[h]), graph=_graph([_node("a.md")]))
    assert _cell(board, "android", COL_DOING)[0].unknown_status is None


# ── 異常 ────────────────────────────────────────────────────────────────────────

def test_unknown_role_is_anomaly_not_card():
    board = _build(sub=_sub(unknown=[UnknownToItem("x.md", "ghost")]))
    assert board.card_count == 0
    assert ANOMALY_UNKNOWN_TO in _kinds(board)


def test_top_level_done_unarchived_is_anomaly_not_card():
    h = _h("a.md")
    board = _build(sub=_sub(not_picked=[h]), graph=_graph([_node("a.md", status="done")]))
    assert board.card_count == 0
    assert ANOMALY_TOP_DONE_UNARCHIVED in _kinds(board)


@pytest.mark.parametrize("bucket,status", [
    ("partial", "partial"),
    ("partial", "blocked"),
    ("awaiting", "submitted"),
])
def test_top_level_done_skip_covers_partial_and_awaiting(bucket, status):
    """頂層本體已 done 但未歸檔：partial_done／awaiting_confirm 同樣不出卡片（PR #1 review）。"""
    h = _h("a.md", status=status, reply_date="2026-09-05")
    sub = _sub(partial=[h]) if bucket == "partial" else _sub(awaiting=[h])
    board = _build(sub=sub, graph=_graph([_node("a.md", status="done")]))
    assert board.card_count == 0
    assert ANOMALY_TOP_DONE_UNARCHIVED in _kinds(board)


def test_reply_self_marked_done_is_anomaly():
    # 最新回覆 status: done → 現有分類整筆略過，不在任何清單
    board = _build(sub=_sub(), graph=_graph([_node("a.md", status="open")]))
    assert board.card_count == 0
    assert ANOMALY_REPLY_DONE in _kinds(board)


def test_unknown_role_node_is_not_reported_as_reply_done():
    board = _build(
        sub=_sub(unknown=[UnknownToItem("a.md", "ghost")]),
        graph=_graph([_node("a.md", to_role="ghost")]),
    )
    assert ANOMALY_REPLY_DONE not in _kinds(board)


def test_archived_node_is_not_reported_as_reply_done():
    board = _build(graph=_graph([_node("a.md", location=LOCATION_ARCHIVE, status="done")]))
    assert _kinds(board) == set()


def test_tripwire_marks_mailbox_incomplete():
    scan = KunsuScanResult(kunsu_path=KUNSU, tripwire_lines=["TRIPWIRE:M x"])
    board = _build(scan=scan)
    assert ANOMALY_TRIPWIRE in _kinds(board)
    assert board.mailbox_incomplete is True


def test_script_error_marks_mailbox_incomplete():
    scan = KunsuScanResult(kunsu_path=KUNSU, script_error="scan-replies.sh exited with code 1: x")
    board = _build(scan=scan)
    assert ANOMALY_SCRIPT_ERROR in _kinds(board)
    assert board.mailbox_incomplete is True


def test_stale_kunsu_has_no_cards():
    h = _h("a.md")
    board = _build(sub=_sub(not_picked=[h]), stale=True)
    assert board.card_count == 0
    assert board.stale is True
    assert ANOMALY_STALE in _kinds(board)


def test_parse_errors_deduplicated_across_sources():
    board = _build(
        sub=_sub(errors=[SubErrorItem("bad.md", "missing created")]),
        graph=_graph(errors=[GraphErrorItem("bad.md", "yaml error")]),
    )
    parse = [a for a in board.anomalies if a.kind == ANOMALY_PARSE_ERROR]
    assert len(parse) == 1
    assert parse[0].count == 1


def test_unresolved_dependency_shown_as_marker_not_filename_title():
    h = _h("a.md")
    graph = _graph(
        [_node("a.md")],
        derived={"a.md": DERIVED_WAITING},
        waiting_on={"a.md": ["ghost.md"]},
        unresolved=[UnresolvedEdge("a.md", "ghost.md", "not_found")],
    )
    board = _build(sub=_sub(not_picked=[h]), graph=graph)
    card = _cell(board, "android", COL_WAITING)[0]
    assert card.waiting_titles == ()
    assert card.unresolved_waiting == ("ghost.md",)
    assert ANOMALY_DEPENDENCY in _kinds(board)


# ── 信箱卡片 ────────────────────────────────────────────────────────────────────

def test_mailbox_cards_in_kunsu_todo(tmp_path: Path):
    kunsu = tmp_path / "ebook"
    (kunsu / "docs/applications").mkdir(parents=True)
    (kunsu / "docs/reports").mkdir(parents=True)
    (kunsu / "docs/applications/app1.md").write_text(
        "---\ntitle: 申請加入 android\ncreated: 2026-09-03\n---\n本文\n", encoding="utf-8"
    )
    (kunsu / "docs/reports/rep1.md").write_text("沒有 frontmatter\n", encoding="utf-8")
    scan = KunsuScanResult(
        kunsu_path=str(kunsu),
        new_applications=["docs/applications/app1.md"],
        new_reports=["docs/reports/rep1.md"],
    )
    board = build_board(
        kunsu_path=str(kunsu),
        known_roles=set(ROLES),
        sub=_sub(),
        scan=scan,
        graph=_graph(),
        todo=TodoStatusResult(),
        stale=False,
    )
    cards = _cell(board, LANE_KUNSU, COL_TODO)
    by_kind = {c.kind: c for c in cards}
    assert by_kind[CARD_APPLICATION].title == "申請加入 android"
    assert by_kind[CARD_APPLICATION].base_date == "2026-09-03"
    assert by_kind[CARD_REPORT].title == "rep1"
    assert by_kind[CARD_REPORT].base_date is None


# ── 泳道與排序 ──────────────────────────────────────────────────────────────────

def test_lane_order_kunsu_first_then_alphabetical():
    board = _build(roles={"store", "android", "backend"})
    assert [key for key, _ in board.lanes] == [LANE_KUNSU, "android", "backend", "store"]
    assert board.lanes[0][1] == "軍師"


def test_role_named_like_kunsu_lane_stays_separate():
    h = _h("a.md", to_role="kunsu")
    board = _build(sub=_sub(not_picked=[h]), graph=_graph([_node("a.md", to_role="kunsu")]), roles={"kunsu"})
    keys = [key for key, _ in board.lanes]
    assert keys == [LANE_KUNSU, "kunsu"]
    assert [c.filename for c in _cell(board, "kunsu", COL_TODO)] == ["a.md"]
    assert _cell(board, LANE_KUNSU, COL_TODO) == ()


def test_cell_sorted_oldest_first_invalid_dates_last():
    hs = [
        _h("new.md", created="2026-09-20"),
        _h("bad.md", created="not-a-date"),
        _h("impossible.md", created="2026-13-01"),
        _h("old.md", created="2026-09-01"),
    ]
    board = _build(sub=_sub(not_picked=hs), graph=_graph([_node(h.filename) for h in hs]))
    assert [c.filename for c in _cell(board, "android", COL_TODO)] [:2] == ["old.md", "new.md"]


def test_empty_board():
    board = _build()
    assert board.card_count == 0
    assert board.anomalies == ()


def test_todo_count_from_pending():
    todo = TodoStatusResult(pending=[TodoInfo(filename="t.md", title="t", status="未處理")])
    board = _build(todo=todo)
    assert board.todo_count == 1
