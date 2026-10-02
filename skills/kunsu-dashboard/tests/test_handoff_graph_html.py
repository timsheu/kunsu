"""
test_handoff_graph_html.py — 交接依賴圖沙盤渲染（app/handoff_graph_html.py）與 main.py 接線測試

覆蓋計畫 U3 test scenarios：
  - 兩交接 B 依賴 open 的 A → 頁面含 <svg、兩個錨點、B 摘要列含 dlabel-waiting、總覽含「等依賴 1」
  - Covers AE3. B 最新回覆 blocked 且等依賴 → 同時含 badge-blocked 與 dlabel-waiting
  - Covers AE6. 全部無 depends_on → 不含 dlabel-、區塊含「無依賴宣告」、既有斷言零回歸
  - 循環 → 含 <svg、環內兩節點同欄、循環提示與兩檔名；總覽含「依賴圖異常」
  - 無法解析 → 提示含目標檔名與原因；幽靈節點置第 0 欄
  - 九個有邊的活節點（另 30 孤立 open）→ 不含 <svg、含文字清單
  - corrected_by 節點 → dlabel-corrected；兩元素列表逐檔名列出
  - 同檔名跨兩軍師 → 錨點 id 不同
  - 錨點 id 掛在 <details> 隱藏區（<pre> 前）的 span，fragment 導向才會自動展開
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.handoff_graph import get_handoff_graph
from app.handoff_graph_html import (
    SVG_MAX_ACTIVE,
    anchor_id,
    dependency_labels,
    html_dependency_section,
    render_svg,
)
from app.main import app
from app.kunsu_scan import KunsuScanResult
from app.registry import RegistryResult
from app.subrepo_status import HandoffInfo, SubrepoStatusResult


# ── 輔助 ────────────────────────────────────────────────────────────────────────

def _mk(directory: Path, name: str, *, status: str = "open", depends_on: str | None = None,
        corrected_by: str | None = None, title: str | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"title: {title or name[:-3]}", "type: handoff", f"status: {status}",
             "from: kunsu", "to: dev", "created: 2026-09-01", "tags: [handoff]"]
    if depends_on is not None:
        lines.append(f"depends_on: {depends_on}")
    if corrected_by is not None:
        lines.append(f"corrected_by: {corrected_by}")
    lines += ["---", "", f"# {name[:-3]}", ""]
    (directory / name).write_text("\n".join(lines), encoding="utf-8")


def _kunsu(tmp_path: Path, name: str = "kunsu") -> tuple[Path, Path, Path]:
    k = tmp_path / name
    top = k / "docs" / "handoffs"
    (top / "archive").mkdir(parents=True)
    (top / "replies").mkdir()
    return k, top, top / "archive"


def _handoff(filename: str, status: str | None = None, date: str | None = None) -> HandoffInfo:
    return HandoffInfo(filename=filename, title=filename[:-3], from_role="kunsu", to_role="dev",
                       created="2026-09-01", latest_reply_status=status, latest_reply_date=date)


def _client_for(monkeypatch, kunsu: Path, subrepo_result: SubrepoStatusResult) -> TestClient:
    KUNSU = str(kunsu)
    SUB = "/fake/sub-dep"
    monkeypatch.setattr("app.main.load_registry", lambda _: RegistryResult(
        healthy=[KUNSU, SUB], stale=[], registry_error=None,
        raw={SUB: [{"kunsu": KUNSU, "roles": ["dev"]}]}))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: KunsuScanResult(
        kunsu_path=p, new_replies=[], new_applications=[], new_reports=[],
        tripwire_lines=[], script_error=None))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: subrepo_result)
    return TestClient(app)


A, B, C = "2026-09-01-a.md", "2026-09-02-b.md", "2026-09-03-c.md"


# ── 頁面接線 ────────────────────────────────────────────────────────────────────

def test_waiting_handoff_renders_svg_anchors_label_and_overview_chip(tmp_path, monkeypatch):
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A)
    _mk(top, B, depends_on=f"[{A}]")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(A), _handoff(B)], partial_done=[],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    assert "<svg" in html
    assert f'href="#{anchor_id(str(k), A)}"' in html and f'href="#{anchor_id(str(k), B)}"' in html
    assert f'</summary><span id="{anchor_id(str(k), B)}"></span><pre>' in html
    assert 'dlabel dlabel-waiting">等依賴</span><span class="dep-waiting-on">（等 2026-09-01-a.md）' in html
    assert 'dlabel dlabel-ready">可開工' in html  # A 有入邊、無依賴
    assert "⏳ 等依賴 1" in html
    assert 'class="chip chip-dep-issue"' not in html


def test_ae3_blocked_and_waiting_coexist(tmp_path, monkeypatch):
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A)
    _mk(top, B, depends_on=f"[{A}]")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(A)],
                              partial_done=[_handoff(B, "blocked", "2026-09-05")],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    # 定位到子專案卡片內 B 的摘要列（SVG 內也含檔名，故自「部分完成」標題起找）
    b_start = html.index(B, html.index("部分完成（1）"))
    seg = html[b_start: b_start + 600]
    assert "badge-blocked" in seg and "dlabel-waiting" in seg


def test_ae6_no_depends_on_has_no_labels_and_says_none(tmp_path, monkeypatch):
    k, top, archive = _kunsu(tmp_path)
    _mk(top, A)
    _mk(top, B)
    _mk(archive, C, status="done")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(A), _handoff(B)], partial_done=[],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    body = html[html.index("<body"):]
    assert 'class="dlabel' not in body
    assert "交接依賴圖：無依賴宣告" in body
    assert "<svg" not in html
    assert '<span class="badge' not in body
    assert "等依賴" not in body


def test_cycle_renders_svg_same_column_and_issue_list(tmp_path, monkeypatch):
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A, depends_on=f"[{B}]")
    _mk(top, B, depends_on=f"[{A}]")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(A), _handoff(B)], partial_done=[],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    assert "<svg" in html
    assert f"⟳ 循環：{A}、{B}" in html
    assert "⟳ 依賴圖異常 1" in html
    # 環內兩節點同欄：兩個 rect 的 x 相同
    import re
    xs = re.findall(r'<rect x="(\d+)" y="\d+" width="190"', html)
    assert len(xs) == 2 and xs[0] == xs[1]
    assert 'stroke="#c62828"' in html


def test_unresolved_edge_lists_reason_and_draws_ghost_in_first_column(tmp_path, monkeypatch):
    k, top, archive = _kunsu(tmp_path)
    _mk(archive, A, status="done")
    _mk(top, B, depends_on=f"[{A}, 2026-01-01-nope.md]")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(B)], partial_done=[],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    assert f"無法解析：{B} → 2026-01-01-nope.md（不存在）" in html
    assert 'stroke-dasharray="5,4"' in html
    assert "無法解析</text>" in html
    assert "⟳ 依賴圖異常 1" in html
    # 幽靈與 done 上游同在第 0 欄（x=16），B 在第 1 欄
    import re
    rects = re.findall(r'<rect x="(\d+)" y="(\d+)" width="190"', html)
    assert sorted(int(x) for x, _ in rects) == [16, 16, 276]


def test_more_than_max_active_degrades_to_text_list(tmp_path, monkeypatch):
    k, top, archive = _kunsu(tmp_path)
    _mk(archive, A, status="done")
    for i in range(SVG_MAX_ACTIVE + 1):
        _mk(top, f"2026-09-1{i}-n{i}.md", depends_on=f"[{A}]")
    for i in range(30):
        _mk(top, f"2026-08-{i + 1:02d}-iso{i}.md")
    sub = SubrepoStatusResult(not_picked_up=[], partial_done=[], awaiting_confirm=[],
                              unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    assert "<svg" not in html
    assert f"活節點 {SVG_MAX_ACTIVE + 1} 筆超過 {SVG_MAX_ACTIVE}，改列文字清單" in html
    assert '<ul class="dep-list">' in html


def test_corrected_by_label_lists_each_filename(tmp_path, monkeypatch):
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A)
    _mk(top, B, depends_on=f"[{A}]", corrected_by=f"\n  - {C}\n  - 2026-09-09-y.md")
    sub = SubrepoStatusResult(not_picked_up=[_handoff(B)], partial_done=[],
                              awaiting_confirm=[], unknown_to=[], errors=[])
    html = _client_for(monkeypatch, k, sub).get("/overview").text
    assert f'dlabel-corrected">已被更正：{C}、2026-09-09-y.md</span>' in html


def test_anchor_ids_differ_across_kunsus():
    assert anchor_id("/x/ebook", A) != anchor_id("/x/ivm", A)
    assert anchor_id("/x/ebook", A) == "ebook--2026-09-01-a"


# ── 純函式 ──────────────────────────────────────────────────────────────────────

def test_dependency_labels_none_graph_and_isolated_node(tmp_path):
    assert dependency_labels(None, A) == ""
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A)
    g = get_handoff_graph(str(k))
    assert dependency_labels(g, A) == ""


def test_render_svg_empty_graph_returns_empty_string(tmp_path):
    k, top, _ = _kunsu(tmp_path)
    _mk(top, A)
    assert render_svg(get_handoff_graph(str(k)), str(k)) == ""


def test_section_open_only_when_waiting_or_issues(tmp_path):
    k, top, archive = _kunsu(tmp_path)
    _mk(archive, A, status="done")
    _mk(top, B, depends_on=f"[{A}]")
    out = html_dependency_section(str(k), get_handoff_graph(str(k)))
    assert '<details class="dep-graph">' in out  # 全 ready、無異常 → 收合
    _mk(top, C, depends_on=f"[{B}]")
    out = html_dependency_section(str(k), get_handoff_graph(str(k)))
    assert '<details class="dep-graph" open>' in out
