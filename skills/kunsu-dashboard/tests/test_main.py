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

import re
from html import escape

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
    raw: dict | None = None,
) -> RegistryResult:
    """建立 RegistryResult 測試用實例。

    raw 對應 registry.py load_registry() 回傳的原始 JSON 結構，main.py
    的身分判斷（軍師 vs 子專案）直接讀這個欄位，不再重新開檔讀取
    （code review 修正：消除雙重讀取的競態，見 registry.py raw 欄位說明）。
    """
    return RegistryResult(
        healthy=healthy or [],
        stale=stale or [],
        registry_error=error,
        raw=raw or {},
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
    not_picked_up: list[HandoffInfo] | None = None,
    partial_done: list[HandoffInfo] | None = None,
    awaiting: list[HandoffInfo] | None = None,
    unknown: list[UnknownToItem] | None = None,
    errors: list[ErrorItem] | None = None,
) -> SubrepoStatusResult:
    """建立 SubrepoStatusResult 測試用實例。"""
    return SubrepoStatusResult(
        not_picked_up=not_picked_up or [],
        partial_done=partial_done or [],
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
    latest_reply_verify: str | None = None,
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
        latest_reply_verify=latest_reply_verify,
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
        raw={
            SUBREPO: [
                {"kunsu": KUNSU_A, "roles": ["worker"]},
                {"kunsu": KUNSU_B, "roles": ["writer"]},
            ]
        },
    ))
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
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(
        p, new_replies=[" docs/handoffs/reply.md"]
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        not_picked_up=[_handoff(filename="work.md", title="Pending Task")]
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "軍師" in html
    assert "子專案" in html
    assert KUNSU in html
    assert SUBREPO in html
    assert "未接手" in html
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
        raw=registry_data,
    ))
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
        # raw 預設 {}：KUNSU 沒有子 repo，也不是任何條目的 kunsu 值
        # → 不觸發 scan_kunsu 或 get_subrepo_status
    ))

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


# ── Test 6b: 子專案所屬軍師為 stale（code review 修正的迴歸測試）────────────

def test_subrepo_with_stale_kunsu_shows_unreachable_not_empty(monkeypatch, client):
    """子專案所屬軍師本身 stale → 顯示「軍師不可達」，不得誤報「無待處理交接文件」。

    Regression: code review 發現先前版本會對 stale 軍師仍呼叫
    get_subrepo_status，該函式對不存在的路徑靜默回傳空結果，
    使頁面誤顯示「無待處理交接文件」，讓使用者誤以為真的沒有待辦事項。
    """
    SUBREPO = "/fake/subrepo"
    STALE_KUNSU = "/fake/stale-kunsu"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[SUBREPO],
        stale=[STALE_KUNSU],
        raw={SUBREPO: [{"kunsu": STALE_KUNSU, "roles": ["dev"]}]},
    ))

    def _fail_if_called(*a, **k):
        raise AssertionError(
            "get_subrepo_status 不應在所屬軍師 stale 時被呼叫"
        )
    monkeypatch.setattr("app.main.get_subrepo_status", _fail_if_called)

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "軍師不可達" in html
    assert STALE_KUNSU in html
    assert "無待處理交接文件" not in html


# ── Test 7: to: 不符清單 ──────────────────────────────────────────────────────

def test_unknown_to_shown_as_separate_warning_list(monkeypatch, client):
    """子專案的交接文件屬「to: 不符清單」→ 以獨立警示列呈現，不落入待接手。"""
    KUNSU = "/fake/kunsu"
    SUBREPO = "/fake/subrepo"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
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
    # 未被歸入未接手／部分完成
    assert "未接手" not in html
    assert "部分完成" not in html


# ── Test 8: XSS 轉義 ─────────────────────────────────────────────────────────

def test_xss_in_handoff_title_is_escaped(monkeypatch, client):
    """frontmatter title 含 <script> 標籤 → 渲染後字元已轉義，不構成可執行標籤。"""
    KUNSU = "/fake/kunsu"
    SUBREPO = "/fake/subrepo"
    XSS_TITLE = "<script>alert(1)</script>"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        not_picked_up=[_handoff(filename="task.md", title=XSS_TITLE)]
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
                not_picked_up=[_handoff("p.md", "Pending Job", "boss", "alpha")]
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
        raw=registry_data,
    ))
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

    # 未接手子專案
    assert "未接手" in html
    assert "Pending Job" in html

    # 已回覆待確認子專案
    assert "已回覆待確認" in html
    assert "Awaiting Job" in html

    # to: 不符清單
    assert "不符清單" in html
    assert "phantom-role" in html


# ── Test 10: 子專案巢狀呈現於所屬軍師分組內 ──────────────────────────────────

def test_subrepo_rendered_nested_within_its_kunsu_group(monkeypatch, client):
    """子專案卡片應巢狀呈現於所屬軍師的分組容器內，而非獨立的頂層分組。

    版面調整核心驗證：軍師與其子專案改為擺在一起，而非各自成一個區塊。
    """
    KUNSU = "/fake/kunsu-group-test"
    SUBREPO = "/fake/subrepo-group-test"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    group_start = html.index('<details class="kunsu-group"')
    group_end = html.index("</details>", group_start)
    assert group_start < html.index(KUNSU) < html.index(SUBREPO) < group_end


# ── Test 11: Stale 子專案巢狀呈現於健康軍師分組內 ────────────────────────────

def test_stale_subrepo_nested_under_healthy_kunsu(monkeypatch, client):
    """子專案本身 stale、但所屬軍師健康 → 以 stale 樣式巢狀呈現於軍師分組內，

    不呼叫 get_subrepo_status（路徑不存在，呼叫該函式無意義）。
    """
    KUNSU = "/fake/kunsu-healthy-group"
    STALE_SUBREPO = "/fake/subrepo-stale-nested"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU],
        stale=[STALE_SUBREPO],
        raw={STALE_SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))

    def _fail_if_called(*a, **k):
        raise AssertionError("get_subrepo_status 不應在子專案自身 stale 時被呼叫")
    monkeypatch.setattr("app.main.get_subrepo_status", _fail_if_called)

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    group_start = html.index('<details class="kunsu-group"')
    group_end = html.index("</details>", group_start)
    assert group_start < html.index(KUNSU) < html.index(STALE_SUBREPO) < group_end
    assert "card-subrepo card-stale" in html


# ── Test 12: 展開式預覽 — 子專案待接手交接文件顯示 raw_content 與 mtime ──────

def test_pending_handoff_shows_expandable_raw_content(monkeypatch, client):
    """待接手交接文件以 <details> 展開式呈現 raw_content 與最後修改時間，

    內容須經 escape()。
    """
    from datetime import datetime

    KUNSU = "/fake/kunsu-detail"
    SUBREPO = "/fake/subrepo-detail"
    RAW = "---\ntitle: 任務\n---\n\n內文含 <b>標籤</b>。"
    MTIME = 1_752_000_000.0  # 固定 epoch，避免測試因執行當下時間而浮動
    expected_mtime_str = datetime.fromtimestamp(MTIME).strftime("%Y-%m-%d %H:%M")

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    # _handoff 輔助函式預設 raw_content=""／mtime=None，改用實際物件驗證需直接建構
    from app.subrepo_status import HandoffInfo
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo(
        not_picked_up=[HandoffInfo(
            filename="task.md", title="Pending Task",
            from_role="boss", to_role="worker", created="2026-07-01",
            latest_reply_status=None, latest_reply_date=None,
            raw_content=RAW, mtime=MTIME,
        )]
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "<details>" in html and "<summary>" in html
    assert "Pending Task" in html
    assert 'class="mtime"' in html and expected_mtime_str in html
    # 原始內容經 escape() 後出現，未轉義版本不得出現（XSS 防護延伸至新功能）
    assert "&lt;b&gt;標籤&lt;/b&gt;" in html
    assert "<b>標籤</b>" not in html
    # 摘要列版面：時間在前、<br> 換行、縮排（class="detail-name"）接檔名
    mtime_pos = html.index('class="mtime"')
    br_pos = html.index("<br>", mtime_pos)
    name_pos = html.index('class="detail-name"', br_pos)
    assert mtime_pos < br_pos < name_pos


# ── Test 13: 展開式預覽 — 軍師新回覆讀取實際檔案內容與最後修改時間 ────────────

def test_kunsu_new_reply_reads_actual_file_content(monkeypatch, client, tmp_path):
    """軍師分組的新回覆項目應讀取 kunsu_path 底下對應相對路徑的實際檔案內容，

    並顯示該檔案的實際最後修改時間（st_mtime）。
    """
    from datetime import datetime

    kunsu_dir = tmp_path / "kunsu"
    reply_rel = "docs/handoffs/replies/2026-07-11-foo-reply.md"
    reply_path = kunsu_dir / reply_rel
    reply_path.parent.mkdir(parents=True)
    reply_path.write_text("---\ntitle: 回覆\n---\n\n實際回覆內容。", encoding="utf-8")
    expected_mtime_str = datetime.fromtimestamp(
        reply_path.stat().st_mtime
    ).strftime("%Y-%m-%d %H:%M")

    KUNSU = str(kunsu_dir)
    SUBREPO = "/fake/subrepo-for-content-test"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(
        p, new_replies=[reply_rel]
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert reply_rel in html
    assert "實際回覆內容。" in html
    assert 'class="mtime"' in html and expected_mtime_str in html


# ── Test 13b: 分類標題列顯示多筆項目中最新的修改時間 ──────────────────────────

def test_kunsu_category_heading_shows_latest_mtime_among_multiple_items(
    monkeypatch, client, tmp_path
):
    """新回覆分類標題列應顯示該分類全部項目中「最新」的修改時間，非任意一筆。"""
    import os
    from datetime import datetime, timedelta

    kunsu_dir = tmp_path / "kunsu"
    replies_dir = kunsu_dir / "docs" / "handoffs" / "replies"
    replies_dir.mkdir(parents=True)

    older_rel = "docs/handoffs/replies/2026-07-01-older-reply.md"
    newer_rel = "docs/handoffs/replies/2026-07-11-newer-reply.md"
    older_path = kunsu_dir / older_rel
    newer_path = kunsu_dir / newer_rel
    older_path.write_text("較舊回覆", encoding="utf-8")
    newer_path.write_text("較新回覆", encoding="utf-8")

    # 明確拉開兩者的 mtime 差距，避免同一秒寫入導致排序無法驗證
    now = newer_path.stat().st_mtime
    older_mtime = now - 3600
    os.utime(older_path, (older_mtime, older_mtime))

    expected_latest_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M")
    expected_older_str = datetime.fromtimestamp(older_mtime).strftime("%Y-%m-%d %H:%M")

    KUNSU = str(kunsu_dir)
    SUBREPO = "/fake/subrepo-for-latest-badge-test"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(
        p, new_replies=[older_rel, newer_rel]
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    heading_end = html.index("</h4>")
    heading = html[: heading_end + len("</h4>")]

    assert "最新" in heading
    assert expected_latest_str in heading
    # 較舊項目的時間不應出現在標題列（只會出現在其自己的展開項目摘要裡）
    if expected_older_str != expected_latest_str:
        assert expected_older_str not in heading


# ── Test 14: 軍師分組展開／折疊狀態反映有無進度 ──────────────────────────────

def test_kunsu_group_open_state_reflects_activity(monkeypatch, client):
    """有進度（新訊息／tripwire）或 stale 的軍師分組預設展開；

    健康且無新訊息的軍師分組預設折疊，避免軍師一多列表就過長。
    """
    KUNSU_EMPTY = "/fake/kunsu-a-empty"
    KUNSU_ACTIVE = "/fake/kunsu-b-active"
    KUNSU_TRIPWIRE = "/fake/kunsu-c-tripwire"
    STALE_KUNSU = "/fake/kunsu-d-stale"
    SUBREPO_EMPTY = "/fake/subrepo-for-empty-kunsu"
    SUBREPO_ACTIVE = "/fake/subrepo-for-active-kunsu"
    SUBREPO_TRIPWIRE = "/fake/subrepo-for-tripwire-kunsu"
    SUBREPO_FOR_STALE = "/fake/subrepo-for-stale-kunsu"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[
            KUNSU_EMPTY, KUNSU_ACTIVE, KUNSU_TRIPWIRE,
            SUBREPO_EMPTY, SUBREPO_ACTIVE, SUBREPO_TRIPWIRE,
        ],
        stale=[STALE_KUNSU],
        # 每個軍師都必須至少有一筆子專案 entry 指向它，才會被 _build_kunsu_paths
        # 判定為「軍師」身分——單純列在 healthy 清單不足以觸發軍師分組渲染。
        raw={
            SUBREPO_EMPTY: [{"kunsu": KUNSU_EMPTY, "roles": ["dev"]}],
            SUBREPO_ACTIVE: [{"kunsu": KUNSU_ACTIVE, "roles": ["dev"]}],
            SUBREPO_TRIPWIRE: [{"kunsu": KUNSU_TRIPWIRE, "roles": ["dev"]}],
            SUBREPO_FOR_STALE: [{"kunsu": STALE_KUNSU, "roles": ["dev"]}],
        },
    ))

    def mock_scan(p):
        if p == KUNSU_ACTIVE:
            return _scan(p, new_replies=["docs/handoffs/replies/x.md"])
        if p == KUNSU_TRIPWIRE:
            return _scan(p, tripwire_lines=["TRIPWIRE:RM x.md"])
        return _scan(p)  # KUNSU_EMPTY：無新訊息

    monkeypatch.setattr("app.main.scan_kunsu", mock_scan)
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # sorted(kunsu_paths) 順序：a-empty, b-active, c-tripwire, d-stale
    tags = re.findall(r'<details class="kunsu-group"( open)?>', html)
    assert len(tags) == 4
    assert tags[0] == ""       # KUNSU_EMPTY：無新訊息 → 折疊
    assert tags[1] == " open"  # KUNSU_ACTIVE：有新回覆 → 展開
    assert tags[2] == " open"  # KUNSU_TRIPWIRE：tripwire → 展開
    assert tags[3] == " open"  # STALE_KUNSU：stale → 展開


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


# ── _annotate_tripwire_line：漏 commit 提示 ───────────────────────────────────

def test_annotate_tripwire_line_hints_untracked_handoff():
    """未 commit 的頂層交接檔（?? 狀態）→ 附加白話漏 commit 提示。"""
    from app.main import _annotate_tripwire_line

    line = "TRIPWIRE:?? docs/handoffs/2026-07-11-vmcapi-restart.md"
    html = _annotate_tripwire_line(line)

    assert escape(line) in html
    assert "hint-uncommitted" in html
    assert "尚未 commit" in html


def test_annotate_tripwire_line_hints_staged_handoff():
    """已 git add 但未 commit 的頂層交接檔（A  狀態）→ 同樣附加提示。"""
    from app.main import _annotate_tripwire_line

    line = "TRIPWIRE:A  docs/handoffs/2026-07-11-vmcapi-restart.md"
    html = _annotate_tripwire_line(line)

    assert "hint-uncommitted" in html


@pytest.mark.parametrize(
    "line",
    [
        "TRIPWIRE:RM docs/handoffs/old.md",  # 修改既有交接檔
        "TRIPWIRE: D docs/handoffs/removed.md",  # 刪除
        "TRIPWIRE:?? docs/handoffs/nested/oops.md",  # 非預期巢狀路徑
        "TRIPWIRE:?? docs/handoffs/not-markdown.txt",  # 非 .md
        "TRIPWIRE:R  docs/handoffs/a.md -> docs/handoffs/replies/a.md",  # 越界搬移
    ],
)
def test_annotate_tripwire_line_no_hint_for_other_shapes(line):
    """非「剛建立未 commit」的其餘 tripwire 形狀 → 不附加提示，原樣顯示。"""
    from app.main import _annotate_tripwire_line

    html = _annotate_tripwire_line(line)

    assert html == escape(line)
    assert "hint-uncommitted" not in html


def test_uncommitted_handoff_hint_rendered_in_tripwire_card(monkeypatch, client):
    """整頁渲染：未 commit 的頂層交接檔 tripwire → 卡片內附白話提示，方便使用者一眼判讀成因。"""
    KUNSU_A = "/fake/kunsu-uncommitted-handoff"
    SUBREPO = "/fake/subrepo-for-uncommitted-handoff"

    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU_A, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU_A, "roles": ["worker"]}]},
    ))
    monkeypatch.setattr("app.main.get_subrepo_status", lambda *a, **k: _subrepo())
    monkeypatch.setattr("app.main.scan_kunsu", lambda path: _scan(
        path,
        tripwire_lines=["TRIPWIRE:?? docs/handoffs/2026-07-11-vmcapi-restart.md"],
    ))

    resp = client.get("/")
    html = resp.text

    assert "hint-uncommitted" in html
    assert "漏做 /handoff add 尾端確認 commit" in html


# ── verify 標籤與三分類渲染（ADR 011） ────────────────────────────────────────


def _client_with_subrepo(monkeypatch, subrepo_result):
    """組出「一軍師＋一子專案」的最小 registry mock，回傳指定子專案分類結果。"""
    KUNSU = "/fake/kunsu-verify"
    SUBREPO = "/fake/subrepo-verify"
    monkeypatch.setattr("app.main.load_registry", lambda _: _reg(
        healthy=[KUNSU, SUBREPO],
        raw={SUBREPO: [{"kunsu": KUNSU, "roles": ["dev"]}]},
    ))
    monkeypatch.setattr("app.main.scan_kunsu", lambda p: _scan(p))
    monkeypatch.setattr(
        "app.main.get_subrepo_status", lambda *a, **k: subrepo_result
    )


def test_three_categories_rendered_with_verify_badges(monkeypatch, client):
    """未接手／部分完成／已回覆待確認三分類標題同時出現，
    三個建議代碼各自渲染為對應中文彩色標籤。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        not_picked_up=[_handoff("n.md", "New Job")],
        partial_done=[
            _handoff(
                "p.md", "Deploy Job",
                latest_reply_status="partial",
                latest_reply_date="2026-07-10",
                latest_reply_verify="needs-deploy",
            ),
            _handoff(
                "d.md", "Device Job",
                latest_reply_status="partial",
                latest_reply_date="2026-07-10",
                latest_reply_verify="needs-device",
            ),
        ],
        awaiting=[_handoff(
            "a.md", "Now Job",
            latest_reply_status="submitted",
            latest_reply_date="2026-07-11",
            latest_reply_verify="testable-now",
        )],
    ))

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "未接手（1）" in html
    assert "部分完成（2）" in html
    assert "已回覆待確認（1）" in html
    assert "需上線測試 🚀" in html and "badge-deploy" in html
    assert "需實機測試 📱" in html and "badge-device" in html
    assert "馬上可測 ⚡" in html and "badge-now" in html


def test_free_text_verify_rendered_as_plain_badge_and_escaped(monkeypatch, client):
    """自由字串 verify 原樣顯示為一般標籤（badge-other），且經 escape()。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        partial_done=[_handoff(
            "p.md", "Custom Job",
            latest_reply_status="partial",
            latest_reply_verify="等 <b>DBA</b> 開權限",
        )],
    ))

    resp = client.get("/")
    html = resp.text

    assert "badge-other" in html
    assert "等 &lt;b&gt;DBA&lt;/b&gt; 開權限" in html
    assert "<b>DBA</b>" not in html


def test_blocked_reply_shows_blocked_badge(monkeypatch, client):
    """blocked 回覆在部分完成分類中另標 ⛔ 卡關標籤。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        partial_done=[_handoff(
            "b.md", "Blocked Job",
            latest_reply_status="blocked",
            latest_reply_verify="needs-deploy",
        )],
    ))

    resp = client.get("/")
    html = resp.text

    assert "部分完成（1）" in html
    assert "badge-blocked" in html and "⛔ 卡關" in html
    # verify 標籤與卡關標籤並存
    assert "badge-deploy" in html


def test_unknown_status_shows_raw_status_badge(monkeypatch, client):
    """未知 status 值歸部分完成，摘要列原樣顯示該 status 標籤（經 escape）。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        partial_done=[_handoff(
            "w.md", "WIP Job",
            latest_reply_status="wip<x>",
        )],
    ))

    resp = client.get("/")
    html = resp.text

    assert "部分完成（1）" in html
    assert "badge-status-unknown" in html
    assert "status: wip&lt;x&gt;" in html
    assert "wip<x>" not in html


def test_missing_verify_shows_no_badge(monkeypatch, client):
    """verify 缺省（既有回覆檔零遷移）→ 不出現任何 verify 標籤 class。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        awaiting=[_handoff(
            "a.md", "Plain Job",
            latest_reply_status="submitted",
        )],
    ))

    resp = client.get("/")
    html = resp.text

    assert "已回覆待確認（1）" in html
    # CSS class 定義出現在每頁的 <style>，不能用 class 名稱反向斷言；
    # 改斷言「實際渲染出的 badge span」不存在
    assert '<span class="badge' not in html


def test_verify_suggested_code_lookup_is_case_insensitive(monkeypatch, client):
    """建議代碼大小寫變體（Needs-Deploy）仍命中彩色標籤，不靜默降格為一般標籤
    （ADR 011 doc review 修正：查找前正規化為小寫）。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        partial_done=[_handoff(
            "p.md", "Case Job",
            latest_reply_status="partial",
            latest_reply_verify="Needs-Deploy",
        )],
    ))

    resp = client.get("/")
    html = resp.text

    assert "需上線測試 🚀" in html and "badge-deploy" in html
    assert '<span class="badge badge-other">' not in html


def test_items_within_category_sorted_by_verify_grouping(monkeypatch, client):
    """同分類內依 verify 聚合排序：已知代碼在前、自由字串次之、缺省最後，
    同 verify 值相鄰（ADR 011 Decision 2 排序規則）。"""
    _client_with_subrepo(monkeypatch, _subrepo(
        partial_done=[
            _handoff("z-none.md", "NoVerify Job",
                     latest_reply_status="partial"),
            _handoff("a-free.md", "FreeText Job",
                     latest_reply_status="partial",
                     latest_reply_verify="等 DBA 開權限"),
            _handoff("m-dev2.md", "Device Job Two",
                     latest_reply_status="partial",
                     latest_reply_verify="needs-device"),
            _handoff("b-deploy.md", "Deploy Job",
                     latest_reply_status="partial",
                     latest_reply_verify="needs-deploy"),
            _handoff("k-dev1.md", "Device Job One",
                     latest_reply_status="partial",
                     latest_reply_verify="needs-device"),
        ],
    ))

    resp = client.get("/")
    html = resp.text

    # 已知代碼（needs-deploy < needs-device，值相同者相鄰）→ 自由字串 → 缺省
    pos_deploy = html.index("Deploy Job")
    pos_dev1 = html.index("Device Job One")
    pos_dev2 = html.index("Device Job Two")
    pos_free = html.index("FreeText Job")
    pos_none = html.index("NoVerify Job")

    assert pos_deploy < min(pos_dev1, pos_dev2)
    assert max(pos_dev1, pos_dev2) < pos_free < pos_none
