"""
board_routes.py — 看板 /、archive 頁 /archive 與全文頁 /handoff 的路由

自 main.py 拆出（PR #1 review：main.py 逾 1000 行）。main.py 以 include_router
掛載；本模組不匯入 app.main（循環匯入），registry 路徑與角色輔助自 app.registry
取得。測試以 monkeypatch 替換本模組命名空間的 load_registry／scan_kunsu／
get_handoff_graph 等引用。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.board_html import (
    kunsu_label,
    render_archive_page,
    render_board_page,
    render_error_page,
    render_handoff_not_found_page,
    render_handoff_page,
    render_handoff_stale_page,
    render_no_kunsu_page,
)
from app.board_model import build_board
from app.handoff_detail import load_handoff_detail
from app.handoff_graph import HandoffGraphResult, get_handoff_graph
from app.kunsu_scan import MAILBOX_ONLY_SCRIPTS, KunsuScanResult, scan_kunsu
from app.registry import (
    RegistryResult,
    build_kunsu_paths,
    get_all_known_roles,
    get_registry_path,
    load_registry,
)
from app.subrepo_status import SubrepoStatusResult, get_subrepo_status
from app.todo_status import TodoStatusResult, get_todo_status

router = APIRouter()


# ── 路由：看板 / 與 archive 頁 /archive ───────────────────────────────────────

def _kunsu_list(reg: RegistryResult) -> list[str]:
    """registry 中健康或失聯的軍師路徑，依路徑排序（看板切換列順序）。"""
    known = set(reg.healthy) | set(reg.stale)
    return sorted(p for p in build_kunsu_paths(reg.raw) if p in known)


def _select_kunsu(kunsus: list[str], k: Optional[str]) -> tuple[str, Optional[str]]:
    """依查詢參數 k（軍師目錄名）以白名單選軍師（KTD4）。

    k 只與 registry 中的軍師目錄名比對，絕不當作路徑使用；不命中時退回第一個
    軍師並回傳原值供提示列顯示。目錄名重複時取排序在前者。
    """
    by_name: dict[str, str] = {}
    for kp in kunsus:
        by_name.setdefault(kunsu_label(kp), kp)
    if k and k in by_name:
        return by_name[k], None
    return kunsus[0], (k or None)


@router.get("/", response_class=HTMLResponse)
def board(k: Optional[str] = None) -> HTMLResponse:
    """看板：所選軍師的持球者泳道 × 狀態欄（看板化計畫 U4）。

    只掃描所選軍師，不計算其他軍師的卡片數（每次刷新掃描全部軍師會推進
    掃描統計，見計畫 U4）。registry 讀取失敗仍回 HTTP 200。
    """
    reg = load_registry(get_registry_path())
    if reg.registry_error:
        return HTMLResponse(content=render_error_page(reg.registry_error))
    kunsus = _kunsu_list(reg)
    if not kunsus:
        return HTMLResponse(content=render_no_kunsu_page())
    selected, not_found = _select_kunsu(kunsus, k)
    known_roles = get_all_known_roles(reg.raw, selected)
    if selected in set(reg.stale):
        model = build_board(
            kunsu_path=selected,
            known_roles=known_roles,
            sub=SubrepoStatusResult(),
            scan=KunsuScanResult(kunsu_path=selected),
            graph=HandoffGraphResult(),
            todo=TodoStatusResult(),
            stale=True,
        )
    else:
        model = build_board(
            kunsu_path=selected,
            known_roles=known_roles,
            # 以全部已知角色呼叫一次，取得該軍師全部交接（KTD1）
            sub=get_subrepo_status(selected, known_roles, known_roles, selected),
            scan=scan_kunsu(selected, MAILBOX_ONLY_SCRIPTS),
            graph=get_handoff_graph(selected),
            todo=get_todo_status(selected),
            stale=False,
        )
    return HTMLResponse(
        content=render_board_page(
            kunsus=kunsus, selected=selected, board=model, not_found=not_found
        )
    )


@router.get("/archive", response_class=HTMLResponse)
def archive(k: Optional[str] = None) -> HTMLResponse:
    """archive 頁：所選軍師已歸檔的交接（看板化計畫 U5）。"""
    reg = load_registry(get_registry_path())
    if reg.registry_error:
        return HTMLResponse(content=render_error_page(reg.registry_error))
    kunsus = _kunsu_list(reg)
    if not kunsus:
        return HTMLResponse(content=render_no_kunsu_page())
    selected, not_found = _select_kunsu(kunsus, k)
    stale = selected in set(reg.stale)
    graph = HandoffGraphResult() if stale else get_handoff_graph(selected)
    return HTMLResponse(
        content=render_archive_page(
            kunsus=kunsus, selected=selected, graph=graph, not_found=not_found, stale=stale
        )
    )


@router.get("/handoff", response_class=HTMLResponse)
def handoff_detail(k: Optional[str] = None, f: Optional[str] = None) -> HTMLResponse:
    """全文頁：單份交接／申請／上報的 Markdown 渲染與同串回覆。

    k 走與看板相同的白名單選軍師（不命中回 404，不退回第一個軍師——全文頁
    的 f 是相對該軍師的路徑，退回別的軍師會開到不相干的檔案）；f 由
    handoff_detail.resolve_rel_path 守門。純讀檔，絕不呼叫 scan_kunsu（掃描
    腳本會推進歷史夾帶基線並寫統計檔）。
    """
    reg = load_registry(get_registry_path())
    if reg.registry_error:
        return HTMLResponse(content=render_error_page(reg.registry_error))
    kunsus = _kunsu_list(reg)
    if not kunsus:
        return HTMLResponse(content=render_no_kunsu_page())
    selected, not_found = _select_kunsu(kunsus, k)
    if not_found is not None or not k:
        return HTMLResponse(content=render_handoff_not_found_page(None, f), status_code=404)
    if selected in set(reg.stale):
        return HTMLResponse(content=render_handoff_stale_page(selected))
    detail = load_handoff_detail(selected, f)
    if detail is None:
        return HTMLResponse(content=render_handoff_not_found_page(selected, f), status_code=404)
    graph = get_handoff_graph(selected) if detail.kind == "handoff" else None
    return HTMLResponse(
        content=render_handoff_page(kunsu_path=selected, detail=detail, graph=graph)
    )
