"""
test_main.py — skills/kunsu-dashboard/app/main.py 的單元測試

覆蓋計畫 U4 的 9 個 test scenarios（含 Covers AE4），以及 Verification
要求的兩項額外驗證：
  - 回應 Content-Type 為 text/html
  - app 內未定義任何回傳 JSON 的路由（ADR 010 Decision 1.5）

測試策略：
  - 透過 monkeypatch.setattr 替換 app.main 命名空間中的函式引用，
    確保測試不讀取真實機器上的 ~/.claude/kunsu-registry.json。
  - 每個測試僅 patch 實際會被呼叫的函式，保持測試焦點明確。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.registry import RegistryResult
from app.kunsu_scan import KunsuScanResult
from app.subrepo_status import (
    HandoffInfo,
    SubrepoStatusResult,
    UnknownToItem,
    ErrorItem,
)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """FastAPI TestClient，供所有測試共用。"""
    return TestClient(app)


# ── 輔助建構函式 ──────────────────────────────────────────────────────────────

def _reg(
    healthy: list[str] | None = None,
    stale: list[str] | None = None,
    error: str | None = None,
) -> RegistryResult:
    """建立 RegistryResult 測試用實例。"""
    return RegistryResult(
        healthy=healthy or [],
        stale=stale or [],
        registry_error=error,
    )


def _scan(
    kunsu_path: str,
    new_replies: list[str] | None = None,
    new_applications: list[str] | None = None,
    new_reports: list[str] | None = None,
    tripwire_lines: list[str] | None = None,
    script_error: str | None = None,
) -> KunsuScanResult:
    """建立 KunsuScanResult 測試用實例。"""
    return KunsuScanResult(
        kunsu_path=kunsu_path,
        new_replies=new_replies or [],
        new_applications=new_applications or [],
        new_reports=new_reports or [],
        tripwire_lines=tripwire_lines or [],
        script_error=script_error,
    )


def _subrepo(
    pending: list[HandoffInfo] | None = None,
    awaiting: list[HandoffInfo] | None = None,
    unknown: list[UnknownToItem] | None = None,
    errors: list[ErrorItem] | None = None,
) -> SubrepoStatusResult:
    """建立 SubrepoStatusResult 測試用實例。"""
    return SubrepoStatusResult(
        pending=pending or [],
        awaiting_confirm=awaiting or [],
        unknown_to=unknown or [],
        errors=errors or [],
    )


def _handoff(
    filename: str = "task.md",
    title: str = "Task Title",
    from_role: str = "boss",
    to_role: str = "worker",
    created: str = "2026-07-01",
    latest_reply_status: str | None = None,
    latest_reply_date: str | None = None,
) -> HandoffInfo:
    """建立 HandoffInfo 測試用實例。"""
    return HandoffInfo(
        filename=filename,
        title=title,
        from_role=from_role,
        to_role=to_role,
        created=created,
        latest_reply_status=latest_reply_status,
        latest_reply_date=latest_reply_date,
    )


# ── Test 1: Covers AE4 — tripwire + 其餘正常 ─────────────────────────────────

def test_tripwire_kunsu_shown_other_sections_normal(monkeypatch, client):
    """Covers AE4: 一個軍師 tripwire，其餘軍師與子專案正常 → 各區塊正確渲染。

    tripwire 區塊顯示異常標示（⛔、lbl-tripwire），
    其餘軍師正常渲染（card-normal），子專案區塊也正常出現。
    """
    KUNSU_A = "/fake/kunsu-tripwire"
    KUNSU_B = "/fake/kunsu-normal"
    SUBREPO = "/fake/subrepo"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU_A, KUNSU_B, SUBREPO],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: {
        SUBREPO: [
            {"kunsu": KUNSU_A, "roles": ["worker"]},
            {"kunsu": KUNSU_B, "roles": ["writer"]},
        ]
    })
    monkeypatch.setattr("app.main.scan_kunsu", lambda path: (
        _scan(path, tripwire_lines=["TRIPWIRE:RM docs/handoffs/old.md"])
        if path == KUNSU_A
        else _scan(path, new_replies=[" docs/handoffs/new-reply.md"])
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # tripwire 軍師區塊的異常標示
    assert "lbl-tripwire" in html
    assert "⛔" in html
    assert "TRIPWIRE:RM docs/handoffs/old.md" in html

    # 正常軍師區塊（KUNSU_B）正常渲染
    assert KUNSU_B in html
    assert "card-normal" in html

    # 子專案分組出現
    assert "子專案" in html


# ── Test 2: Happy path — 軍師與子專案皆有正常結果 ────────────────────────────

def test_happy_path_kunsu_and_subrepo_both_rendered(monkeypatch, client):
    """至少一軍師、一子專案皆有正常掃描結果 → 兩分組皆正確渲染。"""
    KUNSU = "/fake/kunsu"
    SUBREPO = "/fake/subrepo"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: {
        SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]
    })
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(
        p, new_replies=[" docs/handoffs/reply.md"]
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        pending=[_handoff(filename="work.md", title="Pending Task")]
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "軍師" in html
    assert "子專案" in html
    assert KUNSU in html
    assert SUBREPO in html
    assert "待接手" in html
    assert "Pending Task" in html
    assert "新回覆" in html


# ── Test 3: 空 registry ───────────────────────────────────────────────────────

def test_empty_registry_shows_empty_message(monkeypatch, client):
    """registry 為空物件 {} → 顯示「無登記」訊息，非錯誤樣式。"""
    monkeypatch.setattr("app.main.load_registry", lambda _: _reg())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "沒有任何已登記的軍師或子專案" in html
    # 錯誤狀態的標題文字不應出現（CSS class 定義出現在每頁的 <style>，不能用來反向斷言）
    assert "Registry 讀取錯誤" not in html


# ── Test 4a: Registry 不存在 → HTTP 200 ─────────────────────────────────────

def test_registry_not_found_returns_200_with_error_message(monkeypatch, client):
    """registry 檔案不存在 → HTTP 200，顯示對應錯誤訊息，不是 HTTP 500。"""
    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        error="Registry file not found: /no/such/registry.json"
    ))

    resp = client.get("/")
    assert resp.status_code == 200  # 非 500，避免瀏覽器顯示通用錯誤頁
    html = resp.text

    assert "Registry 讀取錯誤" in html
    assert "/no/such/registry.json" in html
    assert "not found" in html


# ── Test 4b: Registry JSON 損壞 → HTTP 200，訊息與 not found 不同 ───────────

def test_malformed_registry_returns_200_with_distinct_error(monkeypatch, client):
    """registry JSON 格式損壞 → HTTP 200，錯誤訊息與「not found」不同。"""
    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        error="Registry JSON is malformed (/bad/registry.json): "
              "Expecting value: line 1 column 1"
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "malformed" in html
    assert "Registry 讀取錯誤" in html


# ── Test 5: 巢狀拓撲 ─────────────────────────────────────────────────────────

def test_nested_topology_appears_in_both_sections(monkeypatch, client):
    """同一路徑同時符合軍師與子專案身分（巢狀）→ 在軍師分組與子專案分組各出現一次。"""
    NESTED = "/fake/nested"          # 同時是軍師（有子 repo 登記到它）和子 repo（登記到 PARENT）
    PARENT = "/fake/parent-kunsu"    # 純軍師
    CHILD = "/fake/child-subrepo"    # NESTED 底下的子 repo

    registry_data = {
        # NESTED 作為子 repo 登記到 PARENT
        NESTED: [{"kunsu": PARENT, "roles": ["mid-layer"]}],
        # CHILD 登記到 NESTED（使 NESTED 具備軍師身分）
        CHILD: [{"kunsu": NESTED, "roles": ["worker"]}],
    }

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[PARENT, NESTED, CHILD],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: registry_data)
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # NESTED 路徑應在軍師分組（card-normal）和子專案分組（card-subrepo）各出現一次
    # 計算出現次數（每個分組各含 <code>NESTED</code>）
    count = html.count(NESTED)
    assert count >= 2, (
        f"Nested path {NESTED} expected in both kunsu and subrepo sections, "
        f"but appeared {count} time(s)"
    )

    # 確認兩個分組標題都存在
    assert "軍師" in html
    assert "子專案" in html


# ── Test 6: Stale 路徑 ────────────────────────────────────────────────────────

def test_stale_path_shows_stale_card(monkeypatch, client):
    """某路徑被標記 stale → 顯示 stale 樣式卡片，與 tripwire 視覺可區分。"""
    STALE = "/fake/stale-repo"
    KUNSU = "/fake/kunsu"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU],
        stale=[STALE],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: {
        # KUNSU 沒有子 repo，也不是任何條目的 kunsu 值
        # → 不觸發 scan_kunsu 或 get_subrepo_status
    })
    # KUNSU 在 kunsu_paths / subrepo_paths 皆為空（raw data {}），不需要 mock scan

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Stale 路徑出現在頁面
    assert STALE in html
    assert "stale" in html.lower()
    # Stale 使用 card-stale class，與 card-tripwire 不同
    assert "card-stale" in html
    # tripwire 顯示文字（實際卡片內容）不應出現，CSS class 名稱不可用於反向斷言
    assert "tripwire 異常" not in html
    assert "⛔" not in html


# ── Test 7: to: 不符清單 ──────────────────────────────────────────────────────

def test_unknown_to_shown_as_separate_warning_list(monkeypatch, client):
    """子專案的交接文件屬「to: 不符清單」→ 以獨立警示列呈現，不落入待接手。"""
    KUNSU = "/fake/kunsu"
    SUBREPO = "/fake/subrepo"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: {
        SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]
    })
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        unknown=[UnknownToItem(filename="mystery.md", to_value="ghost-role")]
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 不符清單項目出現在頁面
    assert "mystery.md" in html
    assert "ghost-role" in html
    # 「to: 不符清單」標題出現
    assert "不符清單" in html
    # 不符清單以警示樣式（lbl-warn）呈現
    assert "lbl-warn" in html
    # 未被歸入待接手
    assert "待接手" not in html


# ── Test 8: XSS 轉義 ─────────────────────────────────────────────────────────

def test_xss_in_handoff_title_is_escaped(monkeypatch, client):
    """frontmatter title 含 <script> 標籤 → 渲染後字元已轉義，不構成可執行標籤。"""
    KUNSU = "/fake/kunsu"
    SUBREPO = "/fake/subrepo"
    XSS_TITLE = "<script>alert(1)</script>"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: {
        SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]
    })
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        pending=[_handoff(filename="task.md", title=XSS_TITLE)]
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 未轉義的 script 標籤不得出現（XSS 防護）
    assert "<script>alert(1)</script>" not in html
    # 轉義後的版本應存在
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ── Test 9: Integration — 全狀態組合 fixture ─────────────────────────────────

def test_integration_all_status_types_rendered(monkeypatch, client):
    """含多種狀態組合的完整 fixture → 單頁 HTML 同時正確呈現全部類別。

    覆蓋：healthy 軍師（tripwire）、healthy 軍師（正常）、stale 路徑、
    待接手子專案、已回覆待確認子專案、to 不符清單子專案。
    """
    KUNSU_TRIPWIRE = "/fake/kunsu-tw"
    KUNSU_NORMAL = "/fake/kunsu-ok"
    SUBREPO_PENDING = "/fake/sub-pending"
    SUBREPO_AWAITING = "/fake/sub-awaiting"
    SUBREPO_UNKNOWN = "/fake/sub-unknown"
    STALE = "/fake/stale"

    registry_data = {
        SUBREPO_PENDING: [{"kunsu": KUNSU_TRIPWIRE, "roles": ["alpha"]}],
        SUBREPO_AWAITING: [{"kunsu": KUNSU_NORMAL, "roles": ["beta"]}],
        SUBREPO_UNKNOWN: [{"kunsu": KUNSU_NORMAL, "roles": ["gamma"]}],
    }

    def mock_scan(path: str) -> KunsuScanResult:
        if path == KUNSU_TRIPWIRE:
            return _scan(path, tripwire_lines=["TRIPWIRE:RM docs/handoffs/stale.md"])
        return _scan(path, new_reports=[" docs/reports/latest.md"])

    def mock_subrepo(
        subrepo_path: str, our_roles, all_known_roles, kunsu_path: str
    ) -> SubrepoStatusResult:
        if subrepo_path == SUBREPO_PENDING:
            return _subrepo(
                pending=[_handoff("p.md", "Pending Job", "boss", "alpha")]
            )
        if subrepo_path == SUBREPO_AWAITING:
            return _subrepo(
                awaiting=[_handoff(
                    "a.md", "Awaiting Job", "boss", "beta",
                    latest_reply_status="submitted",
                    latest_reply_date="2026-07-10",
                )]
            )
        # SUBREPO_UNKNOWN
        return _subrepo(unknown=[UnknownToItem("u.md", "phantom-role")])

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU_TRIPWIRE, KUNSU_NORMAL, SUBREPO_PENDING, SUBREPO_AWAITING, SUBREPO_UNKNOWN],
        stale=[STALE],
    ))
    monkeypatch.setattr("app.main._load_raw_registry", lambda _: registry_data)
    monkeypatch.setattr("app.main.scan_kunsu", mock_scan)
    monkeypatch.setattr("app.main.get_subrepo_status", mock_subrepo)

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Tripwire 軍師
    assert "⛔" in html
    assert "TRIPWIRE:RM docs/handoffs/stale.md" in html

    # 正常軍師（有新上報）
    assert KUNSU_NORMAL in html
    assert "新上報" in html

    # Stale 路徑
    assert STALE in html
    assert "card-stale" in html

    # 待接手子專案
    assert "待接手" in html
    assert "Pending Job" in html

    # 已回覆待確認子專案
    assert "已回覆待確認" in html
    assert "Awaiting Job" in html

    # to: 不符清單
    assert "不符清單" in html
    assert "phantom-role" in html


# ── Verification: Content-Type ────────────────────────────────────────────────

def test_response_content_type_is_text_html(monkeypatch, client):
    """回應 Content-Type 為 text/html（ADR 010 Decision 1.5 可驗證條件）。"""
    monkeypatch.setattr("app.main.load_registry", lambda _: _reg())

    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ── Verification: No JSON routes (ADR 010 Decision 1.5) ──────────────────────

def test_no_json_routes_in_app(client):
    """app 內未定義任何回傳 JSON 的路由（ADR 010 Decision 1.5）。

    驗證兩點：
    1. app.routes 中所有 APIRoute 的 response_class 均非 JSONResponse。
    2. /openapi.json 端點已停用（openapi_url=None），回傳 404。
    """
    from fastapi.responses import JSONResponse
    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            assert route.response_class is not JSONResponse, (
                f"Route '{route.path}' uses JSONResponse, "
                "violates ADR 010 Decision 1.5 (text/html-only constraint)"
            )

    # OpenAPI JSON 端點已停用
    resp = client.get("/openapi.json")
    assert resp.status_code == 404, (
        "/openapi.json should be disabled (openapi_url=None)"
    )
