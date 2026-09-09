"""
handoff_graph_html.py — 交接依賴圖的沙盤渲染（inline SVG、推導態標籤、錨點）

純渲染層：輸入 handoff_graph.get_handoff_graph 的結果，輸出 HTML 片段字串。
零 JS、零新依賴，回應仍為 text/html（ADR 010 條件 5 內）。

CSS class 一律以 `dlabel`／`dep-` 前綴，刻意避開既有 `badge`／`chip`／`tlabel`——
既有測試以「頁面不含 <span class="badge」斷言 verify 標籤缺席（2026-07-17 教訓）。

排版：以 Tarjan SCC 縮點後的 DAG 做 longest-path 分欄（上游在左、下游在右），
同一 SCC 的節點置同一欄、SCC 內的邊不參與層級計算（只畫、標紅）。活節點超過
SVG_MAX_ACTIVE 時降級為文字清單。
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from app.handoff_graph import (
    ANOMALY_ARCHIVED_NOT_DONE,
    ANOMALY_DUPLICATE,
    DERIVED_READY,
    DERIVED_WAITING,
    UNRESOLVED_BAD_TYPE,
    UNRESOLVED_NOT_FOUND,
    UNRESOLVED_REPLY_FILE,
    HandoffGraphResult,
)

SVG_MAX_ACTIVE = 8  # 活節點超過此數即降級為文字清單（需求 R25）

_NODE_W = 190
_NODE_H = 46
_COL_GAP = 70
_ROW_GAP = 18
_PAD = 16
_TITLE_MAX = 16

_UNRESOLVED_LABEL = {
    UNRESOLVED_NOT_FOUND: "不存在",
    UNRESOLVED_REPLY_FILE: "指向回覆檔（應指向交接本體）",
    UNRESOLVED_BAD_TYPE: "元素型別錯誤",
}
_ANOMALY_LABEL = {
    ANOMALY_ARCHIVED_NOT_DONE: "已歸檔未標 done",
    ANOMALY_DUPLICATE: "頂層與 archive 同名並存（取頂層）",
}

CSS = (
    ".dlabel{display:inline-block;padding:0 .45em;border-radius:9px;"
    "font-size:.8em;font-weight:600;margin-left:.35em;white-space:nowrap}"
    ".dlabel-ready{background:#e8f5e9;color:#1b5e20;border:1px solid #81c784}"
    ".dlabel-waiting{background:#fff3e0;color:#e65100;border:1px solid #ffb74d}"
    ".dlabel-corrected{background:#eceff1;color:#546e7a}"
    ".dlabel-anomaly{background:#fce4ec;color:#880e4f}"
    ".dep-graph{margin:.4em 0}"
    ".dep-graph>summary{font-weight:600}"
    ".dep-svg{max-width:100%;height:auto;display:block;margin:.4em 0}"
    ".dep-list li{margin:.15em 0}"
    ".dep-waiting-on{color:#e65100;font-size:.85em}"
    ".chip-dep-wait{background:#fff3e0;color:#e65100}"
    ".chip-dep-issue{background:#fce4ec;color:#880e4f}"
)


# ── 標籤與錨點 ──────────────────────────────────────────────────────────────────

def anchor_id(kunsu_path: str, filename: str) -> str:
    """交接卡片錨點 id：`<軍師目錄名>--<檔名去 .md>`，跨軍師同檔名不撞。"""
    stem = filename[:-3] if filename.endswith(".md") else filename
    return f"{Path(kunsu_path).name}--{stem}"


def dependency_labels(graph: HandoffGraphResult | None, filename: str) -> str:
    """交接摘要列的推導態標籤：可開工／等依賴（附在等哪些）＋已被更正／異常註記。

    孤立節點（不在 derived）不加標籤；與 ⛔ 卡關等既有 badge 並列不互抑。
    """
    if graph is None:
        return ""
    parts: list[str] = []
    derived = graph.derived.get(filename)
    if derived == DERIVED_READY:
        parts.append('<span class="dlabel dlabel-ready">可開工</span>')
    elif derived == DERIVED_WAITING:
        waiting = graph.waiting_on.get(filename, [])
        names = "、".join(escape(w) for w in waiting)
        parts.append(
            f'<span class="dlabel dlabel-waiting">等依賴</span>'
            f'<span class="dep-waiting-on">（等 {names}）</span>'
        )
    node = graph.nodes.get(filename)
    if node is not None and node.corrected_by:
        names = "、".join(escape(c) for c in node.corrected_by)
        parts.append(f'<span class="dlabel dlabel-corrected">已被更正：{names}</span>')
    kinds = [a.kind for a in graph.anomalies if a.filename == filename]
    for kind in kinds:
        parts.append(
            f'<span class="dlabel dlabel-anomaly">{escape(_ANOMALY_LABEL.get(kind, kind))}</span>'
        )
    return "".join(parts)


# ── 排版 ────────────────────────────────────────────────────────────────────────

def _drawn_nodes(graph: HandoffGraphResult) -> list[str]:
    """活節點 ∪ 其直接 done 上游（灰色），排序穩定。"""
    drawn = set(graph.active_nodes)
    for src, dst in graph.edges:
        if src in graph.active_nodes and graph.nodes[dst].is_done:
            drawn.add(dst)
    return sorted(drawn)


def _layers(graph: HandoffGraphResult, drawn: list[str], ghosts: list[str]) -> dict[str, int]:
    """longest-path 分層：依賴（上游）在低層。SCC 縮點，環內邊不計。

    幽靈節點（無法解析的目標）視為第 0 層的上游，一併參與層級計算，
    使依賴幽靈的節點及其下游都正確右移。
    """
    drawn_set = set(drawn)
    comp_of: dict[str, str] = {n: n for n in drawn}
    for g in ghosts:
        comp_of[g] = g
    for cyc in graph.cycles:
        members = [m for m in cyc if m in drawn_set]
        if len(members) >= 2:
            rep = members[0]
            for m in members:
                comp_of[m] = rep
    # 縮點後的鄰接：dependent → upstream
    deps: dict[str, set[str]] = {comp_of[n]: set() for n in list(drawn) + list(ghosts)}
    for src, dst in graph.edges:
        if src in drawn_set and dst in drawn_set and comp_of[src] != comp_of[dst]:
            deps[comp_of[src]].add(comp_of[dst])
    ghost_set = set(ghosts)
    for u in graph.unresolved:
        if u.source in drawn_set and u.target in ghost_set:
            deps[comp_of[u.source]].add(u.target)

    memo: dict[str, int] = {}

    def layer(c: str) -> int:
        if c in memo:
            return memo[c]
        memo[c] = 0  # 防禦：縮點後理論上無環
        value = 0 if not deps[c] else 1 + max(layer(d) for d in deps[c])
        memo[c] = value
        return value

    return {n: layer(comp_of[n]) for n in list(drawn) + list(ghosts)}


def _short(title: str) -> str:
    return title if len(title) <= _TITLE_MAX else title[: _TITLE_MAX - 1] + "…"


def _node_style(graph: HandoffGraphResult, name: str, in_cycle: set[str]) -> tuple[str, str, str]:
    """回傳 (fill, stroke, 狀態文字)。"""
    node = graph.nodes[name]
    if node.is_done:
        return "#eeeeee", "#9e9e9e", "done"
    if name in in_cycle:
        return "#ffebee", "#c62828", "⟳ 循環"
    derived = graph.derived.get(name)
    if derived == DERIVED_READY:
        return "#e8f5e9", "#2e7d32", "可開工"
    if derived == DERIVED_WAITING:
        return "#fff3e0", "#e65100", "等依賴"
    return "#f3e5f5", "#7b1fa2", node.status or "?"


def render_svg(graph: HandoffGraphResult, kunsu_path: str) -> str:
    """畫活節點與其直接 done 上游；無法解析目標畫成虛線幽靈節點。"""
    drawn = _drawn_nodes(graph)
    if not drawn:
        return ""
    in_cycle = {m for cyc in graph.cycles if len(cyc) >= 2 for m in cyc}
    # 幽靈節點（無法解析的目標）：只畫活節點宣告的那些
    ghosts = sorted({u.target for u in graph.unresolved if u.source in graph.active_nodes})
    layers = _layers(graph, drawn, ghosts)
    columns: dict[int, list[str]] = {}
    for n in ghosts + drawn:
        columns.setdefault(layers[n], []).append(n)

    pos: dict[str, tuple[int, int]] = {}
    max_rows = 0
    for col, names in sorted(columns.items()):
        max_rows = max(max_rows, len(names))
        for row, name in enumerate(names):
            x = _PAD + col * (_NODE_W + _COL_GAP)
            y = _PAD + row * (_NODE_H + _ROW_GAP)
            pos[name] = (x, y)
    width = _PAD * 2 + (max(columns) + 1) * _NODE_W + max(columns) * _COL_GAP
    height = _PAD * 2 + max_rows * _NODE_H + (max_rows - 1) * _ROW_GAP

    marker_id = f"dep-arrow-{escape(Path(kunsu_path).name)}"
    parts: list[str] = [
        f'<svg class="dep-svg" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="交接依賴圖">',
        f'<defs><marker id="{marker_id}" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#616161"/></marker></defs>',
    ]
    # 邊：上游（target）右緣 → 下游（source）左緣
    for src, dst in graph.edges:
        if src not in pos or dst not in pos:
            continue
        sx, sy = pos[src]
        dx, dy = pos[dst]
        x1, y1 = dx + _NODE_W, dy + _NODE_H // 2
        x2, y2 = sx, sy + _NODE_H // 2
        stroke = "#c62828" if (src in in_cycle and dst in in_cycle) else "#616161"
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="1.5" marker-end="url(#{marker_id})"/>'
        )
    for u in graph.unresolved:
        if u.source not in pos or u.target not in pos:
            continue
        sx, sy = pos[u.source]
        gx, gy = pos[u.target]
        parts.append(
            f'<line x1="{gx + _NODE_W}" y1="{gy + _NODE_H // 2}" x2="{sx}" '
            f'y2="{sy + _NODE_H // 2}" stroke="#880e4f" stroke-width="1.5" '
            f'stroke-dasharray="5,4" marker-end="url(#{marker_id})"/>'
        )
    # 節點
    for name, (x, y) in pos.items():
        if name in graph.nodes:
            fill, stroke, state = _node_style(graph, name, in_cycle)
            title = _short(graph.nodes[name].title)
            href = f"#{escape(anchor_id(kunsu_path, name))}"
            parts.append(
                f'<a href="{href}"><g>'
                f'<rect x="{x}" y="{y}" width="{_NODE_W}" height="{_NODE_H}" rx="6" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
                f'<title>{escape(name)}</title>'
                f'<text x="{x + 8}" y="{y + 19}" font-size="12" fill="#212121">{escape(title)}</text>'
                f'<text x="{x + 8}" y="{y + 36}" font-size="10" fill="{stroke}">{escape(state)}</text>'
                '</g></a>'
            )
        else:  # 幽靈
            parts.append(
                f'<g><rect x="{x}" y="{y}" width="{_NODE_W}" height="{_NODE_H}" rx="6" '
                'fill="#fafafa" stroke="#880e4f" stroke-width="1.5" stroke-dasharray="5,4"/>'
                f'<title>{escape(name)}</title>'
                f'<text x="{x + 8}" y="{y + 19}" font-size="12" fill="#880e4f">{escape(_short(name))}</text>'
                f'<text x="{x + 8}" y="{y + 36}" font-size="10" fill="#880e4f">無法解析</text></g>'
            )
    parts.append("</svg>")
    return "".join(parts)


# ── 區塊 ────────────────────────────────────────────────────────────────────────

def _text_list(graph: HandoffGraphResult, kunsu_path: str) -> str:
    items: list[str] = []
    for name in sorted(graph.active_nodes):
        node = graph.nodes[name]
        derived = graph.derived.get(name, "")
        state = "可開工" if derived == DERIVED_READY else "等依賴"
        deps = "、".join(escape(d) for d in node.depends_on) or "（無宣告，僅被依賴）"
        href = f"#{escape(anchor_id(kunsu_path, name))}"
        items.append(
            f'<li><a href="{href}">{escape(node.title)}</a> '
            f'<span class="filename">({escape(name)})</span> → {deps}'
            f'{dependency_labels(graph, name)}</li>'
        )
    return f'<ul class="dep-list">{"".join(items)}</ul>'


def _issues_html(graph: HandoffGraphResult) -> str:
    items: list[str] = []
    for cyc in graph.cycles:
        label = "自迴圈" if len(cyc) == 1 else "循環"
        items.append(f'<li class="lbl-error">⟳ {label}：{"、".join(escape(c) for c in cyc)}</li>')
    for u in graph.unresolved:
        items.append(
            f'<li class="lbl-warn">無法解析：{escape(u.source)} → {escape(u.target)}'
            f'（{escape(_UNRESOLVED_LABEL.get(u.reason, u.reason))}）</li>'
        )
    for a in graph.anomalies:
        items.append(
            f'<li class="lbl-warn">{escape(_ANOMALY_LABEL.get(a.kind, a.kind))}：{escape(a.filename)}</li>'
        )
    for e in graph.errors:
        items.append(f'<li class="lbl-error">frontmatter 異常：{escape(e.filename)}（{escape(e.error)}）</li>')
    if not items:
        return ""
    return f'<h5>依賴圖異常（{len(items)}）</h5><ul>{"".join(items)}</ul>'


def html_dependency_section(kunsu_path: str, graph: HandoffGraphResult) -> str:
    """軍師分組內的依賴圖區塊；無任何邊時仍印一行「無依賴宣告」（靜默單義化）。"""
    n_active = len(graph.active_nodes)
    n_wait = sum(1 for v in graph.derived.values() if v == DERIVED_WAITING)
    is_open = n_wait > 0 or graph.has_issues
    open_attr = " open" if is_open else ""
    summary = f"交接依賴圖（活節點 {n_active}・等依賴 {n_wait}）"
    if not graph.has_edges and not graph.has_issues:
        # 無邊亦無異常：不用折疊容器，一行即可（既有頁面結構零變化）
        return (
            '<div class="card card-normal"><p class="empty dep-none">'
            "交接依賴圖：無依賴宣告</p></div>"
        )
    if n_active > SVG_MAX_ACTIVE:
        body = (
            f'<p class="empty">活節點 {n_active} 筆超過 {SVG_MAX_ACTIVE}，改列文字清單</p>'
            f"{_text_list(graph, kunsu_path)}"
        )
    else:
        body = render_svg(graph, kunsu_path) or '<p class="empty">無可畫節點</p>'
    return (
        f'<div class="card card-normal"><details class="dep-graph"{open_attr}>'
        f"<summary>{escape(summary)}</summary>{body}{_issues_html(graph)}</details></div>"
    )
