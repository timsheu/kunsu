"""
board_model.py — 軍師沙盤看板：持球者泳道 × 狀態欄的卡片歸屬與異常彙整

純函式模組：把單一軍師的既有掃描結果（subrepo_status 三分類、kunsu_scan 信箱
新件、handoff_graph 依賴推導、todo_status 技術債）轉成看板模型，不讀 registry、
不渲染 HTML。唯一的檔案讀取是信箱卡片取申請／上報檔的 frontmatter 標題與日期。

分類規則零改動（看板化計畫 KTD2）：本模組只讀 subrepo_status 的分類結果，
歸欄依「最新回覆狀態＋依賴推導」決定：
  - 未接手（無回覆）：依賴推導為等依賴 → 收件角色・等待中；否則 → 收件角色・待辦
  - 最新回覆 partial 或未知值 → 收件角色・進行中
  - 最新回覆 blocked → 軍師・進行中（卡關旗標）
  - 最新回覆 submitted → 軍師・待驗收
  - 新申請、新上報 → 軍師・待辦
「等待中」只在尚無回覆且 derived 為等依賴時成立；不在 derived 的孤立或 done 節點
走一般規則（derived 不是全集）。

異常（看板化計畫 KTD11、KTD12）不上看板、只計入警示列：軍師路徑失聯、tripwire、
掃描腳本錯誤、未知收件角色、交接解析錯誤（兩來源以檔名去重）、依賴圖異常、
頂層已標 done 未歸檔、回覆自標 done。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from app.handoff_graph import DERIVED_WAITING, LOCATION_TOP, HandoffGraphResult
from app.kunsu_scan import KunsuScanResult
from app.subrepo_status import (
    HandoffInfo,
    SubrepoStatusResult,
    parse_frontmatter,
)
from app.todo_status import TodoStatusResult


# ── 常數 ────────────────────────────────────────────────────────────────────────

# 軍師泳道的保留鍵：含 NUL 字元，不可能與任何角色代碼（kebab-case）同名（KTD3）
LANE_KUNSU = "\x00kunsu"
LANE_KUNSU_LABEL = "軍師"

COL_WAITING = "waiting"
COL_TODO = "todo"
COL_DOING = "doing"
COL_REVIEW = "review"
COLUMNS: tuple[str, ...] = (COL_WAITING, COL_TODO, COL_DOING, COL_REVIEW)
COLUMN_LABELS: dict[str, str] = {
    COL_WAITING: "等待中",
    COL_TODO: "待辦",
    COL_DOING: "進行中",
    COL_REVIEW: "待驗收",
}

CARD_HANDOFF = "handoff"
CARD_APPLICATION = "application"
CARD_REPORT = "report"

# 停留天數基準名稱（KTD8）
BASE_DISPATCHED = "自派發"
BASE_REPLIED = "自最新回覆"
BASE_SUBMITTED = "自投遞"

ANOMALY_STALE = "stale"
ANOMALY_TRIPWIRE = "tripwire"
ANOMALY_SCRIPT_ERROR = "script_error"
ANOMALY_UNKNOWN_TO = "unknown_to"
ANOMALY_PARSE_ERROR = "parse_error"
ANOMALY_DEPENDENCY = "dependency"
ANOMALY_TOP_DONE_UNARCHIVED = "top_done_unarchived"
ANOMALY_REPLY_DONE = "reply_done"

ANOMALY_LABELS: dict[str, str] = {
    ANOMALY_STALE: "軍師路徑失聯",
    ANOMALY_TRIPWIRE: "tripwire",
    ANOMALY_SCRIPT_ERROR: "掃描腳本錯誤",
    ANOMALY_UNKNOWN_TO: "未知收件角色",
    ANOMALY_PARSE_ERROR: "交接解析錯誤",
    ANOMALY_DEPENDENCY: "依賴圖異常",
    ANOMALY_TOP_DONE_UNARCHIVED: "已標 done 未歸檔",
    ANOMALY_REPLY_DONE: "回覆自標 done",
}

_STATUS_PARTIAL = "partial"
_STATUS_BLOCKED = "blocked"
_STATUS_SUBMITTED = "submitted"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


# ── 資料類別 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Card:
    """看板上的一張卡片（交接、新申請或新上報）。"""

    kind: str                              # CARD_*
    filename: str
    title: str
    lane: str                              # LANE_KUNSU 或角色代碼
    column: str                            # COL_*
    base_date: Optional[str]               # 停留天數基準日原值；None 表示不明
    base_label: str                        # BASE_*
    body_rel_path: str                     # 相對軍師根目錄的本文路徑
    to_role: Optional[str] = None          # 交接的收件角色；信箱卡片為 None
    series: Optional[str] = None
    verify: Optional[str] = None
    blocked: bool = False
    unknown_status: Optional[str] = None   # 最新回覆為未知 status 時的原值
    excerpt: Optional[str] = None          # 最新回覆首句摘錄（display-only）
    reply_rel_path: Optional[str] = None   # 最新回覆相對路徑；無回覆為 None
    body: Optional[str] = None             # 掃描時已讀到的本文；None 表示渲染時再讀檔
    waiting_titles: tuple[str, ...] = ()   # 所等待交接的標題
    unresolved_waiting: tuple[str, ...] = ()  # 無法解析的依賴目標（檔名，只供展開區）


@dataclass(frozen=True)
class AnomalySummary:
    """一類異常的彙整。"""

    kind: str
    count: int

    @property
    def label(self) -> str:
        return ANOMALY_LABELS.get(self.kind, self.kind)


@dataclass(frozen=True)
class Board:
    """單一軍師的看板模型。"""

    lanes: tuple[tuple[str, str], ...]                     # (lane_key, 顯示名稱)
    cells: dict[tuple[str, str], tuple[Card, ...]] = field(default_factory=dict)
    anomalies: tuple[AnomalySummary, ...] = ()
    todo_count: int = 0
    mailbox_incomplete: bool = False
    stale: bool = False

    @property
    def card_count(self) -> int:
        return sum(len(cards) for cards in self.cells.values())


# ── 內部輔助 ────────────────────────────────────────────────────────────────────

def _valid_date(value: Optional[str]) -> Optional[str]:
    """回傳有效的 YYYY-MM-DD 日期字串；格式不符或日期不存在（如 2026-13-01）為 None。

    與顯示端 html_common.days_since 採同一判準（fromisoformat），避免排序視為
    有效、顯示卻是「日期不明」；未來日期仍視為有效，依日期排序。
    """
    if not value or not _DATE_RE.match(value):
        return None
    try:
        date.fromisoformat(value[:10])
    except ValueError:
        return None
    return value[:10]


def _sort_key(card: Card) -> tuple[int, str, str]:
    """欄內排序：基準日升冪（陳年件浮頂），日期不明排最後。"""
    date = _valid_date(card.base_date)
    return (0 if date else 1, date or "", card.title)


def _waiting_items(
    filename: str, graph: HandoffGraphResult
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """回傳（所等待交接的標題, 無法解析的依賴檔名）。"""
    titles: list[str] = []
    unresolved: list[str] = []
    for target in graph.waiting_on.get(filename, []):
        node = graph.nodes.get(target)
        if node is None:
            unresolved.append(target)
        else:
            titles.append(node.title or target)
    return tuple(titles), tuple(unresolved)


def _handoff_card(
    h: HandoffInfo, lane: str, column: str, graph: HandoffGraphResult
) -> Card:
    has_reply = h.latest_reply_status is not None
    status = h.latest_reply_status
    titles, unresolved = _waiting_items(h.filename, graph)
    unknown = (
        status
        if has_reply and status not in (_STATUS_PARTIAL, _STATUS_BLOCKED, _STATUS_SUBMITTED)
        else None
    )
    return Card(
        kind=CARD_HANDOFF,
        filename=h.filename,
        title=h.title,
        lane=lane,
        column=column,
        base_date=h.latest_reply_date if has_reply else h.created,
        base_label=BASE_REPLIED if has_reply else BASE_DISPATCHED,
        body_rel_path=f"docs/handoffs/{h.filename}",
        to_role=h.to_role,
        series=h.series,
        verify=h.latest_reply_verify,
        blocked=status == _STATUS_BLOCKED,
        unknown_status=unknown,
        excerpt=h.latest_reply_excerpt,
        body=h.raw_content or None,
        reply_rel_path=(
            f"docs/handoffs/replies/{h.latest_reply_filename}"
            if h.latest_reply_filename
            else None
        ),
        waiting_titles=titles,
        unresolved_waiting=unresolved,
    )


def _mailbox_card(kunsu_path: str, rel_path: str, kind: str) -> Card:
    """讀申請／上報檔 frontmatter 的 title 與 created；失敗時退回檔名、日期不明。"""
    rel = rel_path.strip()
    path = Path(kunsu_path) / rel
    try:
        content: Optional[str] = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        content = None
    fm = parse_frontmatter(content) if content is not None else {}
    title_raw = fm.get("title")
    created_raw = fm.get("created")
    title = str(title_raw).strip() if title_raw is not None else ""
    return Card(
        kind=kind,
        filename=path.name,
        title=title or path.stem,
        lane=LANE_KUNSU,
        column=COL_TODO,
        base_date=str(created_raw) if created_raw is not None else None,
        base_label=BASE_SUBMITTED,
        body_rel_path=rel,
        body=content,
    )


def _summaries(counts: Iterable[tuple[str, int]]) -> tuple[AnomalySummary, ...]:
    return tuple(AnomalySummary(kind, n) for kind, n in counts if n > 0)


# ── 主函式 ──────────────────────────────────────────────────────────────────────

def build_board(
    *,
    kunsu_path: str,
    known_roles: set[str],
    sub: SubrepoStatusResult,
    scan: KunsuScanResult,
    graph: HandoffGraphResult,
    todo: TodoStatusResult,
    stale: bool,
) -> Board:
    """把單一軍師的掃描結果轉成看板模型。

    Args:
        kunsu_path:  軍師絕對路徑（信箱卡片讀檔用）。
        known_roles: 該軍師已登記的全部角色代碼。
        sub:         以全部已知角色呼叫一次 get_subrepo_status 的結果（KTD1）。
        scan:        scan_kunsu 結果。
        graph:       get_handoff_graph 結果。
        todo:        get_todo_status 結果。
        stale:       軍師路徑是否失聯；失聯時不產生任何卡片（KTD13）。
    """
    lanes = ((LANE_KUNSU, LANE_KUNSU_LABEL),) + tuple(
        (role, role) for role in sorted(known_roles)
    )

    if stale:
        return Board(lanes=lanes, anomalies=_summaries([(ANOMALY_STALE, 1)]), stale=True)

    buckets: dict[tuple[str, str], list[Card]] = {}

    def add(card: Card) -> None:
        buckets.setdefault((card.lane, card.column), []).append(card)

    # 頂層本體已標 done 但未歸檔 → 不上看板（KTD12）
    top_done = {
        name
        for name, node in graph.nodes.items()
        if node.location == LOCATION_TOP and node.is_done
    }

    for h in sub.not_picked_up:
        if h.filename in top_done:
            continue
        waiting = graph.derived.get(h.filename) == DERIVED_WAITING
        add(_handoff_card(h, h.to_role, COL_WAITING if waiting else COL_TODO, graph))

    for h in sub.partial_done:
        if h.filename in top_done:
            continue
        if h.latest_reply_status == _STATUS_BLOCKED:
            add(_handoff_card(h, LANE_KUNSU, COL_DOING, graph))
        else:
            add(_handoff_card(h, h.to_role, COL_DOING, graph))

    for h in sub.awaiting_confirm:
        if h.filename in top_done:
            continue
        add(_handoff_card(h, LANE_KUNSU, COL_REVIEW, graph))

    for rel in scan.new_applications:
        add(_mailbox_card(kunsu_path, rel, CARD_APPLICATION))
    for rel in scan.new_reports:
        add(_mailbox_card(kunsu_path, rel, CARD_REPORT))

    # 回覆自標 done：現有分類整筆略過，以依賴圖頂層節點補判（KTD11）
    classified = {
        h.filename
        for h in (*sub.not_picked_up, *sub.partial_done, *sub.awaiting_confirm)
    }
    unknown_files = {u.filename for u in sub.unknown_to}
    sub_error_files = {e.filename for e in sub.errors}
    reply_done = [
        name
        for name, node in graph.nodes.items()
        if node.location == LOCATION_TOP
        and not node.is_done
        and node.to_role in known_roles
        and name not in classified
        and name not in unknown_files
        and name not in sub_error_files
    ]

    parse_error_files = sub_error_files | {e.filename for e in graph.errors}
    dependency_issues = len(graph.unresolved) + len(graph.anomalies) + len(graph.cycles)

    anomalies = _summaries(
        [
            (ANOMALY_TRIPWIRE, len(scan.tripwire_lines)),
            (ANOMALY_SCRIPT_ERROR, 1 if scan.script_error else 0),
            (ANOMALY_UNKNOWN_TO, len(sub.unknown_to)),
            (ANOMALY_PARSE_ERROR, len(parse_error_files)),
            (ANOMALY_DEPENDENCY, dependency_issues),
            (ANOMALY_TOP_DONE_UNARCHIVED, len(top_done)),
            (ANOMALY_REPLY_DONE, len(reply_done)),
        ]
    )

    cells = {key: tuple(sorted(cards, key=_sort_key)) for key, cards in buckets.items()}
    return Board(
        lanes=lanes,
        cells=cells,
        anomalies=anomalies,
        todo_count=len(todo.pending),
        mailbox_incomplete=bool(scan.tripwire_lines) or bool(scan.script_error),
        stale=False,
    )
