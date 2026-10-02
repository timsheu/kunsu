"""
board_html.py — 軍師沙盤看板頁（/）與 archive 頁（/archive）的 HTML 渲染

輸入為 board_model.Board 與 handoff_graph 結果，輸出完整 HTML 頁面字串；
不讀 registry、不呼叫掃描。零 JS：卡片與 archive 列表只放連結，全文由
獨立全文頁（/handoff）伺服器端渲染 Markdown 呈現。

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
from app.handoff_detail import KIND_LABELS, HandoffDetail
from app.handoff_graph import LOCATION_ARCHIVE, HandoffGraphResult
from app.html_common import (
    VERIFY_LABELS,
    days_since,
    nav_anchor_id,
    page_shell,
)
from app.markdown_render import render_document

# 單一格子常態顯示的卡片上限，其餘收進「另有 N 筆」（KTD6）
CELL_VISIBLE_LIMIT = 8
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
    ".kb-more>summary{color:#555}"
    ".kb-archive li{margin:.35em 0}"
    ".kb-archive-meta{font-size:.82em;color:#666}"
    ".kb-path{font-size:.8em;color:#888}"
    ".kb-open{font-size:.8em;white-space:nowrap}"
    ".kb-doc{max-width:900px}"
    ".kb-doc h2{font-size:1.3em;margin:.6em 0 .3em}"
    ".kb-doc-meta{font-size:.85em;color:#666;margin:.2em 0 .8em}"
    ".kb-fm{border-collapse:collapse;font-size:.82em;margin:.5em 0 1em}"
    ".kb-fm th{text-align:left;color:#555;font-weight:600;padding:.15em .8em .15em 0;"
    "vertical-align:top;white-space:nowrap}"
    ".kb-fm td{padding:.15em 0;word-break:break-all}"
    ".kb-md{font-size:.95em}"
    ".kb-md h1{font-size:1.25em;border:0;padding:0;margin:1em 0 .4em}"
    ".kb-md h2{font-size:1.12em;margin:1em 0 .4em}"
    ".kb-md h3{font-size:1em;margin:.9em 0 .3em}"
    ".kb-md table{border-collapse:collapse;margin:.5em 0;font-size:.9em}"
    ".kb-md th,.kb-md td{border:1px solid #cfd8dc;padding:.2em .5em;vertical-align:top}"
    ".kb-md th{background:#eceff1}"
    ".kb-md blockquote{border-left:3px solid #cfd8dc;margin:.5em 0;padding:.1em .8em;"
    "color:#555}"
    ".kb-md code{background:#f3f3f3;padding:0 .25em;border-radius:3px;font-size:.9em}"
    ".kb-md pre{max-height:none}"
    ".kb-md pre code{background:none;padding:0}"
    ".kb-md-notice{background:#fff8e1;border:1px solid #ffcc80;padding:.3em .6em;"
    "border-radius:4px;font-size:.85em}"
    ".kb-reply{border-top:1px solid #cfd8dc;margin-top:1.2em;padding-top:.6em}"
    ".kb-reply-head{font-size:.85em;color:#555;margin-bottom:.4em;display:flex;"
    "flex-wrap:wrap;gap:.1em .6em;align-items:center}"
    ".kb-doc-section{font-weight:700;margin:1.2em 0 .3em;color:#37474f}"
    ".kb-deps li{margin:.15em 0}"
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
        return f'<span class="kb-tag {_VERIFY_CSS.get(key, "")}">{known[0]}</span>'
    return f'<span class="kb-tag">{escape(verify)}</span>'


def handoff_href(kunsu_path: str, rel_path: str) -> str:
    """全文頁連結：`/handoff?k=<軍師目錄名>&f=<相對路徑>`（兩值皆 URL 編碼）。"""
    return f"/handoff?k={quote(kunsu_label(kunsu_path))}&f={quote(rel_path)}"


def _open_link(kunsu_path: str, rel_path: str, text: str = "全文") -> str:
    return f'<a class="kb-open" href="{escape(handoff_href(kunsu_path, rel_path))}">{text}</a>'


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

    meta.append(_open_link(kunsu_path, card.body_rel_path))

    return (
        f'<div class="{" ".join(classes)}">'
        f'<div class="kb-title">{escape(card.title)}</div>'
        f'<div class="kb-meta">{"".join(meta)}</div>'
        f"{wait}{excerpt}"
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
    stale: bool = False,
) -> str:
    """archive 頁：依檔名日期新到舊列出已歸檔交接，每筆連結至全文頁。

    軍師路徑失聯時無法讀取 archive，顯示失聯說明而非「沒有已歸檔的交接」，
    避免把無法判定的狀態誤呈現為歷史資料不存在。
    """
    nodes = sorted(
        (n for n in graph.nodes.values() if n.location == LOCATION_ARCHIVE),
        key=lambda n: n.filename,
        reverse=True,
    )
    parts = [_nav(kunsus, selected, "/archive"), _notice(not_found)]
    parts.append(f"<h2>已完成（archive）：{escape(kunsu_label(selected))}</h2>")
    if stale:
        parts.append(
            '<div class="kb-alert">⚠ 軍師路徑失聯：'
            f"<code>{escape(selected)}</code>（路徑不存在或非有效 git repo），"
            '無法讀取已歸檔的交接。<a href="/overview">到完整彙整頁查看</a></div>'
        )
        return page_shell("".join(parts), BOARD_CSS)
    if not nodes:
        parts.append('<p class="kb-empty">沒有已歸檔的交接。</p>')
        return page_shell("".join(parts), BOARD_CSS)

    items: list[str] = []
    for node in nodes:
        rel = f"docs/handoffs/archive/{node.filename}"
        meta = [f"收件：{escape(node.to_role or '（未知）')}"]
        if not node.is_done:
            meta.append('<span class="kb-tag kb-tag-status">已歸檔未標 done</span>')
        if node.corrected_by:
            meta.append(f"已由 {escape('、'.join(node.corrected_by))} 更正")
        title_link = (
            f'<a href="{escape(handoff_href(selected, rel))}">'
            f"<strong>{escape(node.title or node.filename)}</strong></a>"
        )
        items.append(
            f'<li>{title_link} <span class="kb-archive-meta">{" ・ ".join(meta)}</span></li>'
        )
    parts.append(f'<p class="kb-archive-meta">共 {len(nodes)} 份，點標題開啟全文。</p>')
    parts.append(f'<ul class="kb-archive">{"".join(items)}</ul>')
    return page_shell("".join(parts), BOARD_CSS)


# ── 全文頁 ──────────────────────────────────────────────────────────────────────

def _back_links(kunsu_path: str, detail: HandoffDetail) -> str:
    k = quote(kunsu_label(kunsu_path))
    links = [f'<a href="/?k={escape(k)}">← 看板</a>']
    if detail.location == LOCATION_ARCHIVE:
        links.append(f'<a href="/archive?k={escape(k)}">已完成（archive）</a>')
    links.append('<a href="/overview">完整彙整頁</a>')
    return f'<nav class="kb-nav">{"".join(links)}</nav>'


def _deps_section(detail: HandoffDetail, graph: Optional[HandoffGraphResult]) -> str:
    """依賴區塊：宣告的 depends_on、尚未滿足者與 corrected_by；全無則不渲染。"""
    if graph is None or detail.kind != "handoff":
        return ""
    node = graph.nodes.get(detail.filename)
    if node is None:
        return ""
    waiting = set(graph.waiting_on.get(detail.filename, ()))
    items: list[str] = []
    for dep in node.depends_on:
        target = graph.nodes.get(dep)
        if target is None:
            items.append(f"<li>{escape(dep)}（無法解析）</li>")
            continue
        state = "等待中" if dep in waiting else ("已完成" if target.is_done else "未完成")
        items.append(
            f"<li>{escape(target.title or dep)}（{state}）"
            f' <span class="kb-path">{escape(dep)}</span></li>'
        )
    if node.corrected_by:
        items.append(f"<li>已由 {escape('、'.join(node.corrected_by))} 更正</li>")
    if not items:
        return ""
    return f'<div class="kb-doc-section">依賴</div><ul class="kb-deps">{"".join(items)}</ul>'


def render_handoff_page(
    *,
    kunsu_path: str,
    detail: HandoffDetail,
    graph: Optional[HandoffGraphResult] = None,
) -> str:
    """全文頁：frontmatter 鍵值表、本體 Markdown、同串回覆（舊→新）。

    Markdown 渲染與 frontmatter 表由 markdown_render 負責（html=False，
    原文 HTML 一律轉義）；graph 可省略，省略時不渲染依賴區塊。
    """
    kind_label = KIND_LABELS.get(detail.kind, detail.kind)
    parts = [_back_links(kunsu_path, detail), '<div class="kb-doc">']
    parts.append(f"<h2>{escape(detail.title)}</h2>")
    meta = [kind_label, escape(kunsu_label(kunsu_path))]
    if detail.location == LOCATION_ARCHIVE:
        meta.append("已歸檔")
    meta.append(f'<span class="kb-path">{escape(detail.rel_path)}</span>')
    parts.append(f'<div class="kb-doc-meta">{" ・ ".join(meta)}</div>')
    if detail.read_error:
        parts.append(f'<div class="kb-alert">{escape(detail.read_error)}</div>')
    else:
        _, html = render_document(detail.content)
        parts.append(html)
    parts.append(_deps_section(detail, graph))

    if detail.kind == "handoff":
        if detail.replies:
            parts.append(f'<div class="kb-doc-section">回覆（{len(detail.replies)} 份，舊→新）</div>')
        else:
            parts.append('<div class="kb-doc-section">尚無回覆</div>')
        for i, reply in enumerate(detail.replies, start=1):
            head = [f"<strong>第 {i} 份</strong>"]
            if reply.status:
                head.append(
                    f'<span class="kb-tag kb-tag-status">status: {escape(reply.status)}</span>'
                )
            head.append(_verify_tag(reply.verify))
            if reply.created:
                head.append(f"<span>{escape(reply.created)}</span>")
            head.append(f'<span class="kb-path">{escape(reply.filename)}</span>')
            _, reply_html = render_document(reply.content)
            parts.append(
                f'<div class="kb-reply" id="reply-{i}">'
                f'<div class="kb-reply-head">{"".join(head)}</div>{reply_html}</div>'
            )
    parts.append("</div>")
    return page_shell("".join(parts), BOARD_CSS)


def render_handoff_stale_page(kunsu_path: str) -> str:
    """全文頁：軍師路徑失聯時的說明頁（HTTP 200，比照看板與 archive 頁）。"""
    k = quote(kunsu_label(kunsu_path))
    body = (
        f'<nav class="kb-nav"><a href="/?k={escape(k)}">← 看板</a></nav>'
        '<div class="kb-alert">⚠ 軍師路徑失聯：'
        f"<code>{escape(kunsu_path)}</code>（路徑不存在或非有效 git repo），"
        '無法讀取文件。<a href="/overview">到完整彙整頁查看</a></div>'
    )
    return page_shell(body, BOARD_CSS)


def render_handoff_not_found_page(kunsu_path: Optional[str], f: Optional[str]) -> str:
    """全文頁 404：不回顯原始 f 以外的任何路徑資訊（f 經轉義）。"""
    k = quote(kunsu_label(kunsu_path)) if kunsu_path else ""
    back = f'<a href="/?k={escape(k)}">← 看板</a>' if kunsu_path else '<a href="/">← 看板</a>'
    body = (
        f'<nav class="kb-nav">{back}</nav>'
        '<div class="kb-alert">找不到這份文件。</div>'
        f'<p class="kb-path">f={escape(f or "")}</p>'
    )
    return page_shell(body, BOARD_CSS)
