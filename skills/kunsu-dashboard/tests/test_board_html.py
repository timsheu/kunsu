"""
test_board_html.py — 看板頁 / 與 archive 頁 /archive 的路由與渲染測試

覆蓋看板化計畫（docs/plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md）
U4、U5 的 test scenarios：AE1、AE4、AE5、查詢參數白名單、registry 為空、
轉義、series、展開全文與讀檔降級、單格超量收合、掃描時間、循環匯入防護、
既有 class 字面相容、軍師失聯、archive 排序與全文內嵌上限。

測試策略：軍師目錄以 tmp_path 建立真實交接檔（subrepo_status、handoff_graph、
todo_status 實跑）；registry 讀取與信箱掃描腳本（需 git）以 monkeypatch 替換
app.main 命名空間中的函式引用，不讀取真實機器的註冊表。
"""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.kunsu_scan import KunsuScanResult
from app.main import app
from app.registry import RegistryResult


# ── Fixture 與輔助 ──────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _handoff(kunsu: Path, filename: str, title: str, to_role: str = "android",
             created: str = "2026-09-01", extra: str = "", status: str = "open",
             archive: bool = False) -> None:
    sub = "docs/handoffs/archive" if archive else "docs/handoffs"
    _write(
        kunsu / sub / filename,
        f"---\ntitle: {title}\nfrom: kunsu\nto: {to_role}\ncreated: {created}\n"
        f"status: {status}\n{extra}---\n\n交接本體內文：{title}\n",
    )


def _reply(kunsu: Path, filename: str, in_reply_to: str, status: str,
           verify: str | None = None, body: str = "回覆內文第一句。") -> None:
    verify_line = f"verify: {verify}\n" if verify else ""
    _write(
        kunsu / "docs/handoffs/replies" / filename,
        f"---\ntitle: 回覆\nin_reply_to: {in_reply_to}\nstatus: {status}\n"
        f"{verify_line}created: 2026-09-05\n---\n\n{body}\n",
    )


def _install(monkeypatch, kunsus: dict[str, list[str]], stale: tuple[str, ...] = (),
             scans: dict[str, KunsuScanResult] | None = None) -> None:
    """以 {軍師路徑: [角色代碼]} 建立假註冊表並替換信箱掃描。"""
    raw: dict = {}
    healthy: list[str] = []
    for i, (kunsu_path, roles) in enumerate(kunsus.items()):
        sub = f"/fake/sub{i}"
        raw[sub] = [{"kunsu": kunsu_path, "roles": roles}]
        healthy.append(sub)
        if kunsu_path not in stale:
            healthy.append(kunsu_path)
    reg = RegistryResult(healthy=healthy, stale=list(stale), registry_error=None, raw=raw)
    monkeypatch.setattr("app.main.load_registry", lambda _p: reg)
    scans = scans or {}
    monkeypatch.setattr(
        "app.main.scan_kunsu",
        lambda kp: scans.get(kp, KunsuScanResult(kunsu_path=kp)),
    )


@pytest.fixture
def ebook(tmp_path: Path) -> Path:
    kunsu = tmp_path / "ebook"
    (kunsu / "docs/handoffs").mkdir(parents=True)
    return kunsu


# ── 看板頁 ──────────────────────────────────────────────────────────────────────

def test_board_shows_title_in_role_todo_lane_without_filename(client, monkeypatch, ebook):
    """Covers AE1。"""
    _handoff(ebook, "2026-09-01-android-crash-fix.md", "修正閃退")
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = client.get("/?k=ebook")
    assert resp.status_code == 200
    html = resp.text
    assert "修正閃退" in html
    assert 'data-lane="android"' in html
    lane_todo = html.split('data-cell="android|todo"')[1].split("</div><!--cell-->")[0]
    assert "修正閃退" in lane_todo
    # 常態區不出現檔名（展開區可含路徑以外的檔名提示，故只檢查卡片標題區）
    assert "2026-09-01-android-crash-fix.md" not in html.split('<details')[0]


def test_submitted_moves_to_kunsu_review_lane(client, monkeypatch, ebook):
    """Covers AE1（後半）。"""
    _handoff(ebook, "2026-09-01-a.md", "待驗收的交接")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "submitted",
           verify="needs-device")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    review = html.split('data-cell="@kunsu|review"')[1].split("</div><!--cell-->")[0]
    assert "待驗收的交接" in review
    assert "需實機測試" in review


def test_empty_board_shows_empty_state_without_grid(client, monkeypatch, ebook):
    """Covers AE4（看板留白）。"""
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert "目前沒有待處理的項目" in html
    assert 'class="kb-grid"' not in html
    assert 'class="kb-alert"' not in html


def test_tripwire_shows_alert_with_overview_link(client, monkeypatch, ebook):
    """Covers AE5。"""
    scan = KunsuScanResult(kunsu_path=str(ebook), tripwire_lines=["TRIPWIRE:M x.md"])
    _install(monkeypatch, {str(ebook): ["android"]}, scans={str(ebook): scan})
    html = client.get("/?k=ebook").text
    assert 'class="kb-alert"' in html
    assert 'href="/overview#nav-ebook-' in html
    assert "可能不完整" in html


def test_invalid_k_falls_back_to_first_kunsu_with_notice(client, monkeypatch, tmp_path, ebook):
    other = tmp_path / "ivm"
    (other / "docs/handoffs").mkdir(parents=True)
    _handoff(ebook, "2026-09-01-a.md", "電子書交接")
    _install(monkeypatch, {str(ebook): ["android"], str(other): ["backend"]})
    for bad in ("../x", "nope", ""):
        resp = client.get("/", params={"k": bad})
        assert resp.status_code == 200
        if bad:
            assert "找不到軍師" in resp.text
        assert "電子書交接" in resp.text  # sorted 後 ebook 在 ivm 之前


def test_no_k_selects_first_sorted_kunsu(client, monkeypatch, tmp_path, ebook):
    other = tmp_path / "ivm"
    (other / "docs/handoffs").mkdir(parents=True)
    _handoff(other, "2026-09-01-b.md", "智販機交接", to_role="backend")
    _install(monkeypatch, {str(other): ["backend"], str(ebook): ["android"]})
    html = client.get("/").text
    assert "智販機交接" not in html
    assert 'class="kb-switch-current"' in html


def test_empty_registry(client, monkeypatch):
    reg = RegistryResult(healthy=[], stale=[], registry_error=None, raw={})
    monkeypatch.setattr("app.main.load_registry", lambda _p: reg)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "尚無已登記的軍師" in resp.text


def test_title_is_escaped(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "'<script>alert(1)</script>'")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_series_shown_only_when_declared(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "有線別", extra="series: iOS移植\n")
    _handoff(ebook, "2026-09-02-b.md", "無線別")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert "線：iOS移植" in html
    assert html.count("線：") == 1


def test_expand_shows_body_and_reply_and_degrades_on_missing_reply(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "部分完成交接")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "partial",
           body="這是最新回覆的全文。")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert "交接本體內文：部分完成交接" in html
    assert "這是最新回覆的全文。" in html
    # 回覆檔於掃描後消失：降級提示而非 500
    (ebook / "docs/handoffs/replies/2026-09-01-a-reply-2026-09-05.md").unlink()
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "partial")
    monkeypatch.setattr(
        "app.board_html.read_related_file",
        lambda base, rel: ("（無法讀取檔案內容：模擬）", None),
    )
    resp = client.get("/?k=ebook")
    assert resp.status_code == 200
    assert "無法讀取檔案內容" in resp.text


def test_cell_overflow_collapses_after_eight(client, monkeypatch, ebook):
    for i in range(12):
        _handoff(ebook, f"2026-09-{i + 1:02d}-t{i}.md", f"交接{i}", created=f"2026-09-{i + 1:02d}")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert "另有 4 筆" in html


def test_page_shows_scan_time(client, monkeypatch, ebook):
    _install(monkeypatch, {str(ebook): ["android"]})
    assert "掃描時間" in client.get("/?k=ebook").text


def test_board_html_does_not_import_main():
    """在獨立子程序驗證：匯入 app.board_html 不會連帶匯入 app.main（KTD5）。

    不在本程序操作 sys.modules——移除並重新匯入 app.main 會讓其他測試的
    monkeypatch 打到新模組，而既有 TestClient 仍持有舊 app。
    """
    root = Path(__file__).resolve().parent.parent
    code = (
        "import sys; import app.board_html; "
        "sys.exit(1 if 'app.main' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_board_avoids_existing_class_literals(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "卡關交接")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "blocked",
           verify="needs-deploy")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    body = html.split("</style>")[1]
    for literal in ('class="badge', 'class="chip', 'class="tlabel', 'class="dlabel',
                    'class="reply-excerpt'):
        assert literal not in body
    assert "⛔" in body


def test_stale_kunsu_shows_notice_without_grid(client, monkeypatch, ebook):
    _install(monkeypatch, {str(ebook): ["android"]}, stale=(str(ebook),))
    html = client.get("/?k=ebook").text
    assert "路徑失聯" in html
    assert 'class="kb-grid"' not in html
    assert 'href="/overview' in html


# ── archive 頁 ──────────────────────────────────────────────────────────────────

def test_archive_lists_newest_first_with_titles(client, monkeypatch, ebook):
    """Covers AE4（archive 頁）。"""
    _handoff(ebook, "2026-08-01-old.md", "舊的交接", status="done", archive=True)
    _handoff(ebook, "2026-09-01-new.md", "新的交接", status="done", archive=True)
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/archive?k=ebook").text
    assert html.index("新的交接") < html.index("舊的交接")


def test_archive_marks_not_done_and_corrected_by(client, monkeypatch, ebook):
    _handoff(ebook, "2026-08-01-a.md", "未標 done", status="open", archive=True,
             extra="corrected_by:\n  - 2026-08-02-fix1.md\n  - 2026-08-03-fix2.md\n")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/archive?k=ebook").text
    assert "已歸檔未標 done" in html
    assert "2026-08-02-fix1.md" in html and "2026-08-03-fix2.md" in html


def test_archive_embeds_full_text_only_for_newest_fifty(client, monkeypatch, ebook):
    for i in range(55):
        day = f"2026-{(i // 28) + 7:02d}-{(i % 28) + 1:02d}"
        _handoff(ebook, f"{day}-h{i}.md", f"歸檔{i}", created=day, status="done", archive=True)
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/archive?k=ebook").text
    assert html.count("交接本體內文：") == 50
    assert html.count("docs/handoffs/archive/") >= 5


def test_archive_empty_and_invalid_k(client, monkeypatch, ebook):
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = client.get("/archive", params={"k": "../etc"})
    assert resp.status_code == 200
    assert "找不到軍師" in resp.text
    assert "沒有已歸檔的交接" in resp.text
