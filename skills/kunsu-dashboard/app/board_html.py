"""
board_html.py — 軍師沙盤看板頁（/）與 archive 頁（/archive）的 HTML 渲染

輸入為 board_model.Board 與 handoff_graph 結果，輸出完整 HTML 頁面字串；
不讀 registry、不呼叫掃描。零 JS：卡片全文以原生 <details> 展開。

CSS class 一律用 `kb-` 前綴，避開原彙整頁負向測試針對的 badge／chip／tlabel／
dlabel／reply-excerpt 字面（看板化計畫 KTD5）。本模組不得匯入 app.main，
共用輔助一律取自 app.html_common（避免循環匯入）。
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import quote

from app.board_model import (
    CARD_APPLICATION,
    CARD_HANDOFF,
    CARD_REPORT,
    COLUMN_LABELS,
    COLUMNS,
    LANE_KUNSU,
    Board,
    Card,
)
from app.handoff_graph import LOCATION_ARCHIVE, HandoffGraphResult
from app.html_common import (
    VERIFY_LABELS,
    days_since,
    nav_anchor_id,
    page_shell,
    read_related_file,
)

# 單一格子常態顯示的卡片上限，其餘收進「另有 N 筆」（KTD6）
CELL_VISIBLE_LIMIT = 8
# archive 頁內嵌可展開全文的筆數上限（KTD10）
ARCHIVE_EMBED_LIMIT = 50

# HTML 屬性用的軍師泳道識別：@ 不屬於角色代碼字元集，不與任何角色同名
_KUNSU_ATTR = "@kunsu"

_KIND_TAGS = {CARD_APPLICATION: "申請", CARD_REPORT: "上報"}

_VERIFY_CSS = {
    "needs-deploy": "kb-tag-deploy",
    "testable-now": "kb-tag-now",
    "needs-device": "kb-tag-device",
}

BOARD_CSS = (
    "body{font-family:system-ui,sans-serif;max-width:1400px;"
    "margin:1.5em auto;padding:0 1em;line-height:1.45}"
    "h1{border-bottom:2px solid #333;padding-bottom:.3em;font-size:1.5em}"
    "a{color:#1565c0}"
    "pre{white-space:pre-wrap;word-break:break-all;background:#f8f8f8;"
    "padding:.5em;border-radius:3px;font-size:.82em;margin:.3em 0;"
    "max-height:24em;overflow:auto}"
    "details{margin:.25em 0}"
    "summary{cursor:pointer;color:#1565c0;font-size:.85em}"
    ".kb-nav{display:flex;flex-wrap:wrap;gap:.4em 1em;align-items:center;"
    "margin:.5em 0 1em;font-size:.92em}"
    ".kb-switch a,.kb-switch span{margin-right:.7em}"
    ".kb-switch-current{font-weight:700;color:#222;border-bottom:2px solid #1565c0}"
    ".kb-scan-time{color:#999;font-size:.85em}"
    ".kb-notice{background:#fff8e1;border:1px solid #ffcc80;padding:.4em .8em;"
    "border-radius:4px;margin:.5em 0}"
    ".kb-alert{background:#ffebee;border:1px solid #e57373;padding:.4em .8em;"
    "border-radius:4px;margin:.5em 0;color:#b71c1c}"
    ".kb-alert a{color:#b71c1c;margin-right:.8em}"
    ".kb-empty{color:#888;font-style:italic;margin:1.5em 0}"
    ".kb-grid{display:grid;grid-template-columns:7.5em repeat(4,minmax(0,1fr));"
    "gap:.4em;align-items:start}"
    ".kb-colhead{font-weight:700;background:#eceff1;padding:.3em .5em;"
    "border-radius:4px;text-align:center}"
    ".kb-lane{font-weight:700;padding:.4em .3em;border-top:2px solid #cfd8dc;"
    "word-break:break-all}"
    ".kb-lane-kunsu{color:#4527a0}"
    ".kb-cell{border-top:2px solid #cfd8dc;padding-top:.3em;min-height:2em}"
    ".kb-cell-empty{background:repeating-linear-gradient(45deg,#fafafa,#fafafa 6px,"
    "#f4f4f4 6px,#f4f4f4 12px)}"
    ".kb-card{border:1px solid #cfd8dc;border-left:4px solid #90a4ae;"
    "border-radius:5px;padding:.35em .5em;margin:0 0 .4em;background:#fff}"
    ".kb-card-blocked{border-left-color:#e53935;background:#fff5f5}"
    ".kb-card-mail{border-left-color:#1e88e5}"
    ".kb-title{font-weight:600;font-size:.92em;display:-webkit-box;"
    "-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}"
    ".kb-meta{font-size:.78em;color:#555;margin-top:.2em;display:flex;"
    "flex-wrap:wrap;gap:.1em .5em}"
    ".kb-tag{display:inline-block;padding:0 .4em;border-radius:8px;"
    "background:#f0f0f0;color:#555;white-space:nowrap}"
    ".kb-tag-kind{background:#e3f2fd;color:#1565c0}"
    ".kb-tag-blocked{background:#ffebee;color:#b71c1c;font-weight:700}"
    ".kb-tag-deploy{background:#fff3e0;color:#e65100}"
    ".kb-tag-now{background:#e8f5e9;color:#2e7d32}"
    ".kb-tag-device{background:#ede7f6;color:#4527a0}"
    ".kb-tag-status{background:#f3e5f5;color:#7b1fa2}"
    ".kb-days{color:#e65100}"
    ".kb-wait{font-size:.78em;color:#6d4c41;margin-top:.15em}"
    ".kb-excerpt{font-size:.78em;color:#555;margin-top:.15em}"
    ".kb-fulltitle{font-weight:600;font-size:.85em;margin:.3em 0}"
    ".kb-section{font-size:.78em;color:#777;margin-top:.4em}"
    ".kb-more>summary{color:#555}"
    ".kb-archive li{margin:.35em 0}"
    ".kb-archive-meta{font-size:.82em;color:#666}"
    ".kb-path{font-size:.8em;color:#888}"
)


# ── 共用片段 ────────────────────────────────────────────────────────────────────

def kunsu_label(kunsu_path: str) -> str:
    """軍師顯示名稱＝目錄名（亦為查詢參數 k 的值）。"""
    return Path(kunsu_path).name or kunsu_path


def _lane_attr(lane: str) -> str:
    return _KUNSU_ATTR if lane == LANE_KUNSU else lane


def _days_text(card: Card) -> str:
    days = days_since(card.base_date)
    if days is None:
        return "日期不明"
    if days == 0:
        return f"今天（{card.base_label}）"
    return f"已等 {days} 天（{card.base_label}）"


def _verify_tag(verify: Optional[str]) -> str:
    if not verify:
        return ""
    key = verify.lower()
    known = VERIFY_LABELS.get(key)
    if known:
        return f'<span class="kb-tag {_VERIFY_CSS[key]}">{known[0]}</span>'
    return f'<span class="kb-tag">{escape(verify)}</span>'


def _nav(
    kunsus: Sequence[str],
    selected: Optional[str],
    page: str,
    todo_count: Optional[int] = None,
) -> str:
    """頁首：軍師切換、技術債、archive、原彙整頁連結與掃描時間（KTD9）。"""
    links: list[str] = []
    for kp in kunsus:
        name = kunsu_label(kp)
        href = f"{page}?k={quote(name)}"
        if kp == selected:
            links.append(f'<span class="kb-switch-current">{escape(name)}</span>')
        else:
            links.append(f'<a href="{escape(href)}">{escape(name)}</a>')
    parts = [f'<span class="kb-switch">{"".join(links)}</span>']
    if selected is not None:
        k = quote(kunsu_label(selected))
        anchor = nav_anchor_id(selected)
        if page == "/":
            parts.append(f'<a href="/archive?k={escape(k)}">已完成（archive）</a>')
        else:
            parts.append(f'<a href="/?k={escape(k)}">← 看板</a>')
        if todo_count is not None:
            parts.append(
                f'<a href="/overview#{escape(anchor)}">技術債 {todo_count} 筆</a>'
            )
    parts.append('<a href="/overview">完整彙整頁</a>')
    parts.append(
        f'<span class="kb-scan-time">掃描時間 {datetime.now().strftime("%H:%M:%S")}</span>'
    )
    return f'<nav class="kb-nav">{"".join(parts)}</nav>'


def _notice(not_found: Optional[str]) -> str:
    if not_found is None:
        return ""
    return f'<p class="kb-notice">找不到軍師「{escape(not_found)}」，改顯示第一個軍師。</p>'


# ── 看板頁 ──────────────────────────────────────────────────────────────────────

def _alert(board: Board, kunsu_path: str) -> str:
    """異常警示列：有異常才出現，逐類連到原彙整頁該軍師錨點（KTD11）。"""
    if not board.anomalies:
        return ""
    href = f"/overview#{nav_anchor_id(kunsu_path)}"
    items = "".join(
        f'<a href="{escape(href)}">{escape(a.label)} {a.count}</a>' for a in board.anomalies
    )
    extra = (
        "（新申請／新上報清單可能不完整）" if board.mailbox_incomplete else ""
    )
    return f'<div class="kb-alert">⚠ 異常：{items}{extra}</div>'


def _card_html(card: Card, kunsu_path: str) -> str:
    classes = ["kb-card"]
    if card.blocked:
        classes.append("kb-card-blocked")
    if card.kind != CARD_HANDOFF:
        classes.append("kb-card-mail")

    meta: list[str] = []
    if card.kind in _KIND_TAGS:
        meta.append(f'<span class="kb-tag kb-tag-kind">{_KIND_TAGS[card.kind]}</span>')
    if card.blocked:
        meta.append('<span class="kb-tag kb-tag-blocked">⛔ 卡關</span>')
    if card.unknown_status:
        meta.append(
            f'<span class="kb-tag kb-tag-status">status: {escape(card.unknown_status)}</span>'
        )
    meta.append(_verify_tag(card.verify))
    if card.to_role and card.lane == LANE_KUNSU:
        meta.append(f"<span>收件：{escape(card.to_role)}</span>")
    meta.append(f'<span class="kb-days">{escape(_days_text(card))}</span>')
    if card.series:
        meta.append(f"<span>線：{escape(card.series)}</span>")

    wait = ""
    if card.waiting_titles or card.unresolved_waiting:
        items = [escape(t) for t in card.waiting_titles]
        if card.unresolved_waiting:
            items.append("無法解析的依賴")
        wait = f'<div class="kb-wait">等：{"、".join(items)}</div>'

    excerpt = (
        f'<div class="kb-excerpt">回覆摘錄：「{escape(card.excerpt)}」</div>'
        if card.excerpt
        else ""
    )

    body, _ = read_related_file(kunsu_path, card.body_rel_path)
    expand = [f'<div class="kb-fulltitle">{escape(card.title)}</div>']
    if card.unresolved_waiting:
        expand.append(
            '<div class="kb-section">無法解析的依賴：'
            f'{escape("、".join(card.unresolved_waiting))}</div>'
        )
    expand.append(
        '<div class="kb-section">'
        f'{"交接本體" if card.kind == CARD_HANDOFF else "全文"}</div>'
        f"<pre>{escape(body)}</pre>"
    )
    if card.reply_rel_path:
        reply, _ = read_related_file(kunsu_path, card.reply_rel_path)
        expand.append(f'<div class="kb-section">最新回覆</div><pre>{escape(reply)}</pre>')

    return (
        f'<div class="{" ".join(classes)}">'
        f'<div class="kb-title">{escape(card.title)}</div>'
        f'<div class="kb-meta">{"".join(meta)}</div>'
        f"{wait}{excerpt}"
        f'<details><summary>展開全文</summary>{"".join(expand)}</details>'
        "</div>"
    )


def _cell_html(lane: str, column: str, cards: Sequence[Card], kunsu_path: str) -> str:
    cls = "kb-cell" if cards else "kb-cell kb-cell-empty"
    visible = "".join(_card_html(c, kunsu_path) for c in cards[:CELL_VISIBLE_LIMIT])
    rest = cards[CELL_VISIBLE_LIMIT:]
    more = (
        f'<details class="kb-more"><summary>另有 {len(rest)} 筆</summary>'
        f'{"".join(_card_html(c, kunsu_path) for c in rest)}</details>'
        if rest
        else ""
    )
    return (
        f'<div class="{cls}" data-cell="{escape(_lane_attr(lane))}|{column}">'
        f"{visible}{more}</div><!--cell-->"
    )


def _grid(board: Board, kunsu_path: str) -> str:
    head = ['<div></div>']
    for col in COLUMNS:
        n = sum(len(board.cells.get((lane, col), ())) for lane, _ in board.lanes)
        head.append(f'<div class="kb-colhead">{COLUMN_LABELS[col]}（{n}）</div>')
    rows: list[str] = []
    for lane, label in board.lanes:
        lane_cls = "kb-lane kb-lane-kunsu" if lane == LANE_KUNSU else "kb-lane"
        rows.append(
            f'<div class="{lane_cls}" data-lane="{escape(_lane_attr(lane))}">'
            f"{escape(label)}</div>"
        )
        for col in COLUMNS:
            rows.append(_cell_html(lane, col, board.cells.get((lane, col), ()), kunsu_path))
    return f'<div class="kb-grid">{"".join(head)}{"".join(rows)}</div>'


def render_board_page(
    *,
    kunsus: Sequence[str],
    selected: str,
    board: Board,
    not_found: Optional[str] = None,
) -> str:
    """看板頁完整 HTML。"""
    parts = [_nav(kunsus, selected, "/", board.todo_count), _notice(not_found)]
    if board.stale:
        parts.append(
            '<div class="kb-alert">⚠ 軍師路徑失聯：'
            f"<code>{escape(selected)}</code>（路徑不存在或非有效 git repo）。"
            '<a href="/overview">到完整彙整頁查看</a></div>'
        )
        return page_shell("".join(parts), BOARD_CSS)
    parts.append(_alert(board, selected))
    if board.card_count == 0:
        parts.append('<p class="kb-empty">目前沒有待處理的項目。</p>')
    else:
        parts.append(_grid(board, selected))
    return page_shell("".join(parts), BOARD_CSS)


def render_no_kunsu_page() -> str:
    """registry 無任何軍師時的頁面。"""
    body = (
        _nav((), None, "/")
        + '<p class="kb-empty">尚無已登記的軍師。請先以 kunsu-init 建立軍師，'
        "或以 kunsu-list 確認註冊表。</p>"
    )
    return page_shell(body, BOARD_CSS)


def render_error_page(message: str) -> str:
    """registry 讀取錯誤頁（仍回 HTTP 200）。"""
    body = (
        _nav((), None, "/")
        + f'<div class="kb-alert">Registry 讀取錯誤</div><pre>{escape(message)}</pre>'
    )
    return page_shell(body, BOARD_CSS)


# ── archive 頁 ──────────────────────────────────────────────────────────────────

def render_archive_page(
    *,
    kunsus: Sequence[str],
    selected: str,
    graph: HandoffGraphResult,
    not_found: Optional[str] = None,
) -> str:
    """archive 頁：依檔名日期新到舊列出已歸檔交接，最近 N 份內嵌全文（KTD10）。"""
    nodes = sorted(
        (n for n in graph.nodes.values() if n.location == LOCATION_ARCHIVE),
        key=lambda n: n.filename,
        reverse=True,
    )
    parts = [_nav(kunsus, selected, "/archive"), _notice(not_found)]
    parts.append(f"<h2>已完成（archive）：{escape(kunsu_label(selected))}</h2>")
    if not nodes:
        parts.append('<p class="kb-empty">沒有已歸檔的交接。</p>')
        return page_shell("".join(parts), BOARD_CSS)

    items: list[str] = []
    for i, node in enumerate(nodes):
        rel = f"docs/handoffs/archive/{node.filename}"
        meta = [f"收件：{escape(node.to_role or '（未知）')}"]
        if not node.is_done:
            meta.append('<span class="kb-tag kb-tag-status">已歸檔未標 done</span>')
        if node.corrected_by:
            meta.append(f"已由 {escape('、'.join(node.corrected_by))} 更正")
        head = (
            f"<strong>{escape(node.title or node.filename)}</strong> "
            f'<span class="kb-archive-meta">{" ・ ".join(meta)}</span>'
        )
        if i < ARCHIVE_EMBED_LIMIT:
            body, _ = read_related_file(selected, rel)
            items.append(
                f"<li>{head}<details><summary>展開全文</summary>"
                f"<pre>{escape(body)}</pre></details></li>"
            )
        else:
            items.append(f'<li>{head} <span class="kb-path">{escape(rel)}</span></li>')
    parts.append(
        f'<p class="kb-archive-meta">共 {len(nodes)} 份；最近 {ARCHIVE_EMBED_LIMIT} '
        "份可展開全文，其餘僅列標題與路徑。</p>"
    )
    parts.append(f'<ul class="kb-archive">{"".join(items)}</ul>')
    return page_shell("".join(parts), BOARD_CSS)
