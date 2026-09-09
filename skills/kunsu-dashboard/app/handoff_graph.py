"""
handoff_graph.py — 交接依賴圖（depends_on）建圖與推導態計算

唯讀解析軍師 repo docs/handoffs/ 頂層與 archive/ 的全部交接本體，以檔名為節點、
frontmatter `depends_on`（被依賴交接的完整檔名列表）為邊，推導每個節點的「可開工」
（ready）／「等依賴」（waiting）狀態，並回報循環、無法解析的邊與異常。

單一推導來源：軍師沙盤（main.py）、SessionStart hook（kunsu-inbox/scripts/
session_hook.py）與 kunsu-inbox CLI（kunsu-inbox/scripts/handoff-graph.py）三個
消費端皆呼叫本模組，不各自重寫圖邏輯。

與 subrepo_status.py／todo_status.py 同為獨立資料來源，各自持一份 frontmatter
解析（既定慣例）；本模組的解析**失敗顯式回報**而非回空 dict——寫壞的
`depends_on` 若被當成「無依賴」，等依賴會靜默變成可開工。

推導規則（需求 R22／R23／R25，見 docs/brainstorms/2026-09-08-handoff-dependency-dag-requirements.md）：
  - 依賴滿足判準＝被依賴本體 `status: done`，位置無關（頂層已 Edit 為 done 尚未
    git mv 的中間態算滿足；archive/ 內非 done 為異常、不算滿足）。
  - 只看直接邊，不算傳遞閉包：全部直接依賴滿足 → ready；任一未滿足或無法解析
    → waiting。循環為 advisory 標記，不另立狀態，環上節點自然互等。
  - 孤立節點（無出邊、無入邊）不入 derived——既有交接零 depends_on 時輸出零變化。
  - 活節點（active_nodes）＝本體非 done 且至少有一條邊（含無法解析邊）的節點；
    沙盤只畫活節點與其直接 done 上游。
  - `depends_on` 指向：不存在→unresolved(not_found)；命中回覆檔名→unresolved(reply_file)；
    自己→忽略不入推導、列入 cycles；重複→去重；純量→單元素列表；非字串元素
    →unresolved(bad_type)；指向解析失敗的本體→已解析但未滿足（不入 unresolved）。
  - `corrected_by` 只作 display 註記，不進推導（ADR 016）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml  # PyYAML — 列於 requirements.txt


# ── 常數 ────────────────────────────────────────────────────────────────────────

DERIVED_READY = "ready"      # 可開工：全部直接依賴的本體 status: done
DERIVED_WAITING = "waiting"  # 等依賴：任一直接依賴未滿足或無法解析

STATUS_DONE = "done"
STATUS_UNKNOWN = "unknown"   # frontmatter 解析失敗或缺欄位的本體

LOCATION_TOP = "top"
LOCATION_ARCHIVE = "archive"

# 無法解析邊的原因
UNRESOLVED_NOT_FOUND = "not_found"
UNRESOLVED_REPLY_FILE = "reply_file"
UNRESOLVED_BAD_TYPE = "bad_type"

# 異常種類
ANOMALY_ARCHIVED_NOT_DONE = "archived_not_done"
ANOMALY_DUPLICATE = "duplicate"

# 與 subrepo_status.py `_REPLY_SUFFIX_RE` 同型（各持一份，互不匯入）
_REPLY_SUFFIX_RE = re.compile(r"-reply-(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$")


# ── 資料類別 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HandoffNode:
    """一份交接本體在圖上的節點。"""

    filename: str                      # basename，含 .md
    title: str
    to_role: str
    status: str                        # 本體 status 原值（str()）；解析失敗為 STATUS_UNKNOWN
    location: str                      # LOCATION_TOP／LOCATION_ARCHIVE
    depends_on: tuple[str, ...] = ()   # 正規化後（去重、去空、str()）的宣告；含無法解析者
    corrected_by: tuple[str, ...] = () # display-only（ADR 016）；純量容錯為單元素

    @property
    def is_done(self) -> bool:
        return self.status == STATUS_DONE


@dataclass(frozen=True)
class UnresolvedEdge:
    """無法解析的依賴邊。"""

    source: str    # 宣告 depends_on 的交接檔名
    target: str    # 宣告的目標（原字串；bad_type 時為 repr）
    reason: str    # UNRESOLVED_*


@dataclass(frozen=True)
class Anomaly:
    """不阻斷推導但需顯式回報的資料異常。"""

    filename: str
    kind: str      # ANOMALY_*


@dataclass(frozen=True)
class ErrorItem:
    """frontmatter 解析失敗、缺必要欄位或 depends_on 型別錯誤的本體。"""

    filename: str
    error: str


@dataclass(frozen=True)
class HandoffGraphResult:
    """建圖與推導結果。

    Attributes:
        nodes:        filename → HandoffNode（頂層＋archive 全部本體）。
        edges:        (source, target) 已解析的依賴邊（含指向解析失敗本體者）。
        active_nodes: 本體非 done 且至少有一條邊（含無法解析邊）的檔名集合。
        derived:      filename → DERIVED_READY／DERIVED_WAITING；孤立節點與 done 節點不入表。
        waiting_on:   filename → 未滿足的直接依賴檔名列表（含無法解析目標），僅 waiting 節點。
        unresolved:   無法解析的邊。
        cycles:       每個循環涉及的檔名列表（含自迴圈的單元素列表）。
        anomalies:    已歸檔未標 done、頂層與 archive 同名並存等。
        errors:       解析失敗的本體。
    """

    nodes: dict[str, HandoffNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    active_nodes: frozenset[str] = frozenset()
    derived: dict[str, str] = field(default_factory=dict)
    waiting_on: dict[str, list[str]] = field(default_factory=dict)
    unresolved: list[UnresolvedEdge] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    errors: list[ErrorItem] = field(default_factory=list)

    @property
    def has_edges(self) -> bool:
        return bool(self.edges) or bool(self.unresolved)

    @property
    def has_issues(self) -> bool:
        """三消費端「顯式呈現」的觸發條件：循環、無法解析或異常任一非空。"""
        return bool(self.cycles) or bool(self.unresolved) or bool(self.anomalies)


# ── frontmatter 解析 ────────────────────────────────────────────────────────────

class _FrontmatterError(Exception):
    """解析失敗（與「無 frontmatter」區分，兩者皆歸 errors 但訊息不同）。"""


def _parse_frontmatter(content: str) -> dict:
    """比照 subrepo_status.py 的分隔符偵測；差異在失敗**拋例外**而非回空 dict。"""
    if not (content.startswith("---\n") or content == "---"):
        raise _FrontmatterError("無 frontmatter")

    search_from = 3
    end = -1
    while True:
        candidate = content.find("\n---", search_from)
        if candidate == -1:
            break
        after = candidate + len("\n---")
        if after == len(content) or content[after] == "\n":
            end = candidate
            break
        search_from = after
    if end == -1:
        raise _FrontmatterError("frontmatter 未閉合")

    try:
        result = yaml.safe_load(content[3:end])
    except yaml.YAMLError as e:  # 縮排寫壞等
        raise _FrontmatterError(f"YAML 解析失敗：{type(e).__name__}") from e
    if not isinstance(result, dict):
        raise _FrontmatterError("frontmatter 非對映")
    return result


def _normalize_str_list(value) -> tuple[tuple[str, ...], list[str]]:
    """把 depends_on／corrected_by 正規化為字串 tuple。

    純量容錯為單元素；list 逐元素 str()；非字串／非數值元素（dict、list、None）
    記入 bad 供呼叫端歸 unresolved(bad_type) 或 errors。去重、去空白。
    """
    if value is None:
        return (), []
    items = value if isinstance(value, list) else [value]
    out: list[str] = []
    bad: list[str] = []
    for item in items:
        if isinstance(item, (dict, list, tuple, set)) or item is None or isinstance(item, bool):
            bad.append(repr(item))
            continue
        s = str(item).strip()
        if not s or s in out:
            continue
        out.append(s)
    return tuple(out), bad


# ── 讀檔建節點 ──────────────────────────────────────────────────────────────────

def _read_node(path: Path, location: str, errors: list[ErrorItem]) -> tuple[HandoffNode, list[str]]:
    """讀一份本體成節點；解析失敗仍建節點（status unknown）並記 errors。

    Returns:
        (node, bad_depends_elements)
    """
    filename = path.name
    try:
        content = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(content)
    except (OSError, UnicodeDecodeError, _FrontmatterError) as e:
        errors.append(ErrorItem(filename, str(e) if isinstance(e, _FrontmatterError) else f"讀取失敗：{type(e).__name__}"))
        return HandoffNode(filename, path.stem, "", STATUS_UNKNOWN, location), []

    missing = [k for k in ("title", "from", "to") if fm.get(k) is None]
    if missing:
        errors.append(ErrorItem(filename, f"缺少必要欄位：{', '.join(missing)}"))
        status = STATUS_UNKNOWN
    else:
        status = str(fm.get("status")).strip() if fm.get("status") is not None else ""

    depends, bad_dep = _normalize_str_list(fm.get("depends_on"))
    corrected, bad_corr = _normalize_str_list(fm.get("corrected_by"))
    if bad_corr:
        errors.append(ErrorItem(filename, f"corrected_by 含非字串元素：{', '.join(bad_corr)}"))

    node = HandoffNode(
        filename=filename,
        title=str(fm.get("title")) if fm.get("title") is not None else path.stem,
        to_role=str(fm.get("to")) if fm.get("to") is not None else "",
        status=status,
        location=location,
        depends_on=depends,
        corrected_by=corrected,
    )
    return node, bad_dep


# ── 循環偵測（Tarjan SCC） ──────────────────────────────────────────────────────

def _find_cycles(adj: dict[str, list[str]], self_loops: set[str]) -> list[list[str]]:
    """回傳所有大小 ≥2 的強連通分量，加上自迴圈的單元素分量。迭代式避免遞迴深度。"""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[list[str]] = []
    counter = 0

    for root in sorted(adj):
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            v, i = work[-1]
            neighbours = adj.get(v, [])
            if i < len(neighbours):
                work[-1] = (v, i + 1)
                w = neighbours[i]
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, 0))
                elif w in on_stack:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[v])
                if low[v] == index[v]:
                    comp: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    if len(comp) >= 2:
                        result.append(sorted(comp))
    for s in sorted(self_loops):
        result.append([s])
    return result


# ── 主函式 ──────────────────────────────────────────────────────────────────────

def get_handoff_graph(kunsu_path: str) -> HandoffGraphResult:
    """對軍師 repo 的 docs/handoffs/ 頂層＋archive/ 建圖並推導。

    目錄不存在時回傳空結果（既有測試以假路徑實跑 main.py，不得拋例外）。
    """
    handoffs_dir = Path(kunsu_path) / "docs" / "handoffs"
    if not handoffs_dir.is_dir():
        return HandoffGraphResult()

    errors: list[ErrorItem] = []
    anomalies: list[Anomaly] = []
    nodes: dict[str, HandoffNode] = {}
    bad_deps: dict[str, list[str]] = {}

    # archive 先讀、頂層後讀：同名並存時頂層覆蓋（取頂層）並記異常
    archive_dir = handoffs_dir / "archive"
    for location, directory in ((LOCATION_ARCHIVE, archive_dir), (LOCATION_TOP, handoffs_dir)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if _REPLY_SUFFIX_RE.search(path.name):
                continue  # 誤置於本體目錄的回覆檔不成節點
            node, bad = _read_node(path, location, errors)
            if node.filename in nodes:
                anomalies.append(Anomaly(node.filename, ANOMALY_DUPLICATE))
            nodes[node.filename] = node
            if bad:
                bad_deps[node.filename] = bad
            if location == LOCATION_ARCHIVE and node.status != STATUS_DONE:
                anomalies.append(Anomaly(node.filename, ANOMALY_ARCHIVED_NOT_DONE))

    edges: list[tuple[str, str]] = []
    unresolved: list[UnresolvedEdge] = []
    adj: dict[str, list[str]] = {}
    incoming: dict[str, int] = {}
    self_loops: set[str] = set()

    for filename in sorted(nodes):
        node = nodes[filename]
        for target in node.depends_on:
            if target == filename:
                self_loops.add(filename)
                continue
            if target in nodes:
                edges.append((filename, target))
                adj.setdefault(filename, []).append(target)
                incoming[target] = incoming.get(target, 0) + 1
            elif _REPLY_SUFFIX_RE.search(target):
                unresolved.append(UnresolvedEdge(filename, target, UNRESOLVED_REPLY_FILE))
            else:
                unresolved.append(UnresolvedEdge(filename, target, UNRESOLVED_NOT_FOUND))
        for bad in bad_deps.get(filename, []):
            unresolved.append(UnresolvedEdge(filename, bad, UNRESOLVED_BAD_TYPE))

    unresolved_sources = {u.source for u in unresolved}
    unresolved_by_source: dict[str, list[str]] = {}
    for u in unresolved:
        unresolved_by_source.setdefault(u.source, []).append(u.target)

    derived: dict[str, str] = {}
    waiting_on: dict[str, list[str]] = {}
    active: set[str] = set()

    for filename in sorted(nodes):
        node = nodes[filename]
        if node.is_done:
            continue
        outgoing = adj.get(filename, [])
        has_edge = bool(outgoing) or incoming.get(filename, 0) > 0 or filename in unresolved_sources
        if not has_edge:
            continue  # 孤立節點：不入 derived、不入 active
        active.add(filename)
        pending = [t for t in outgoing if not nodes[t].is_done]
        pending += unresolved_by_source.get(filename, [])
        if pending:
            derived[filename] = DERIVED_WAITING
            waiting_on[filename] = pending
        else:
            derived[filename] = DERIVED_READY

    cycles = _find_cycles(
        {k: [t for t in v if not nodes[t].is_done] for k, v in adj.items() if not nodes[k].is_done},
        self_loops,
    )

    return HandoffGraphResult(
        nodes=nodes,
        edges=edges,
        active_nodes=frozenset(active),
        derived=derived,
        waiting_on=waiting_on,
        unresolved=unresolved,
        cycles=cycles,
        anomalies=anomalies,
        errors=errors,
    )
