"""
test_board_html.py — 看板頁 / 與 archive 頁 /archive 的路由與渲染測試

覆蓋看板化計畫（docs/plans/2026-10-02-1327-feat-dashboard-kanban-board-plan.md）
U4、U5 的 test scenarios：AE1、AE4、AE5、查詢參數白名單、registry 為空、
轉義、series、卡片全文連結、單格超量收合、掃描時間、循環匯入防護、
既有 class 字面相容、軍師失聯、archive 排序與全文連結，以及全文頁 /handoff
（Markdown 渲染、原始 HTML 轉義、連結協定、f 路徑守門、回覆序列、降級）。

測試策略：軍師目錄以 tmp_path 建立真實交接檔（subrepo_status、handoff_graph、
todo_status 實跑）；registry 讀取與信箱掃描腳本（需 git）以 monkeypatch 替換
app.main 命名空間中的函式引用，不讀取真實機器的註冊表。
"""

import re
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
    # 檔名只允許出現在全文連結的 href 屬性內，不出現在可見文字
    visible = re.sub(r'href="[^"]*"', "", html)
    assert "2026-09-01-android-crash-fix.md" not in visible


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


def test_card_links_to_handoff_page_without_embedding_body(client, monkeypatch, ebook):
    """卡片不再內嵌本體與回覆全文，改為指向 /handoff 的連結。"""
    _handoff(ebook, "2026-09-01-a.md", "部分完成交接")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "partial",
           body="摘錄首句。回覆的第二句不該出現在卡片。")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/?k=ebook").text
    assert 'href="/handoff?k=ebook&amp;f=docs/handoffs/2026-09-01-a.md"' in html
    assert "交接本體內文：部分完成交接" not in html
    assert "回覆摘錄：「摘錄首句。」" in html
    assert "回覆的第二句不該出現在卡片" not in html
    assert "展開全文" not in html


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


def test_card_shows_unknown_status_kind_tag_and_three_day_states(client, monkeypatch, ebook):
    """卡片三態：未知 status 原值、信箱類型標籤、停留天數（今天／N 天／不明）（PR #1 review）。"""
    from datetime import date, timedelta
    today = date.today().isoformat()
    old_day = (date.today() - timedelta(days=3)).isoformat()
    _handoff(ebook, "2026-09-01-u.md", "未知狀態交接")
    _reply(ebook, "2026-09-01-u-reply-2026-09-05.md", "2026-09-01-u.md", "weird-value")
    _handoff(ebook, "2026-09-02-t.md", "今天派發", created=today)
    _handoff(ebook, "2026-09-03-o.md", "三天前派發", created=old_day)
    _handoff(ebook, "2026-09-04-n.md", "日期不明派發", created="not-a-date")
    _write(ebook / "docs/applications/2026-09-01-apply.md",
           "---\ntitle: 申請加入\nstatus: submitted\ncreated: 2026-09-01\n---\n\n申請內文。\n")
    _write(ebook / "docs/reports/2026-09-01-report.md",
           "---\ntitle: 上報一件\nstatus: submitted\ncreated: 2026-09-01\n---\n\n上報內文。\n")
    _install(monkeypatch, {str(ebook): ["android"]}, scans={
        str(ebook): KunsuScanResult(
            kunsu_path=str(ebook),
            new_applications=["docs/applications/2026-09-01-apply.md"],
            new_reports=["docs/reports/2026-09-01-report.md"],
        ),
    })
    html = client.get("/?k=ebook").text
    assert "status: weird-value" in html
    assert 'class="kb-tag kb-tag-kind">申請</span>' in html
    assert 'class="kb-tag kb-tag-kind">上報</span>' in html
    assert "今天（" in html
    assert "已等 3 天（" in html
    assert "日期不明" in html


def test_registry_error_renders_200_with_message_on_board_and_archive(client, monkeypatch):
    """registry 讀取失敗：/ 與 /archive 皆 HTTP 200 並顯示錯誤訊息（PR #1 review）。"""
    reg = RegistryResult(healthy=[], stale=[], registry_error="JSON 損壞：模擬", raw={})
    monkeypatch.setattr("app.main.load_registry", lambda _p: reg)
    for path in ("/", "/archive", "/handoff?k=x&f=docs/handoffs/a.md"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert "Registry 讀取錯誤" in resp.text and "JSON 損壞：模擬" in resp.text


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


def test_archive_links_every_entry_without_embedding(client, monkeypatch, ebook):
    for i in range(55):
        day = f"2026-{(i // 28) + 7:02d}-{(i % 28) + 1:02d}"
        _handoff(ebook, f"{day}-h{i}.md", f"歸檔{i}", created=day, status="done", archive=True)
    _install(monkeypatch, {str(ebook): ["android"]})
    html = client.get("/archive?k=ebook").text
    assert "交接本體內文：" not in html
    assert html.count('href="/handoff?k=ebook&amp;f=docs/handoffs/archive/') == 55
    assert "共 55 份" in html


def test_archive_empty_and_invalid_k(client, monkeypatch, ebook):
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = client.get("/archive", params={"k": "../etc"})
    assert resp.status_code == 200
    assert "找不到軍師" in resp.text
    assert "沒有已歸檔的交接" in resp.text


def test_archive_stale_kunsu_shows_notice_not_empty(client, monkeypatch, ebook):
    """軍師失聯時 archive 頁不得誤報「沒有已歸檔的交接」（code review #2）。"""
    _install(monkeypatch, {str(ebook): ["android"]}, stale=(str(ebook),))
    monkeypatch.setattr(
        "app.main.get_handoff_graph",
        lambda _kp: pytest.fail("失聯軍師不應讀取依賴圖"),
    )
    html = client.get("/archive?k=ebook").text
    assert "路徑失聯" in html
    assert "沒有已歸檔的交接" not in html


# ── 全文頁 /handoff ─────────────────────────────────────────────────────────────

def _detail(client, f: str, k: str = "ebook"):
    return client.get("/handoff", params={"k": k, "f": f})


def test_handoff_page_renders_markdown_and_frontmatter(client, monkeypatch, ebook):
    _write(
        ebook / "docs/handoffs/2026-09-01-a.md",
        "---\ntitle: 渲染測試\nfrom: kunsu\nto: android\ncreated: 2026-09-01\n"
        "status: open\ntags:\n  - alpha\n  - beta\n---\n\n## 問題清單\n\n"
        "- 第一項\n\n| 欄 | 值 |\n|---|---|\n| a | b |\n",
    )
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = _detail(client, "docs/handoffs/2026-09-01-a.md")
    assert resp.status_code == 200
    html = resp.text
    assert "<h2>問題清單</h2>" in html
    assert "<li>第一項</li>" in html
    assert "<td>b</td>" in html
    assert 'class="kb-fm"' in html and "alpha、beta" in html
    assert "<title>" in html and "渲染測試" in html
    assert "尚無回覆" in html


def test_handoff_page_escapes_raw_html_and_blocks_javascript_links(client, monkeypatch, ebook):
    _write(
        ebook / "docs/handoffs/2026-09-01-x.md",
        "---\ntitle: <img src=x onerror=alert(1)>\nto: android\nstatus: open\n---\n\n"
        "<script>alert(1)</script>\n\n[點我](javascript:alert(1))\n\n"
        "[正常](https://example.com/a)\n",
    )
    _install(monkeypatch, {str(ebook): ["android"]})
    html = _detail(client, "docs/handoffs/2026-09-01-x.md").text
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img" not in html
    assert 'href="javascript:' not in html
    assert 'href="https://example.com/a"' in html


@pytest.mark.parametrize("bad", [
    "../../etc/passwd",
    "docs/handoffs/../../CLAUDE.md",
    "docs/handoffs/sub/2026-09-01-a.md",
    "docs/plans/2026-09-01-a.md",
    "docs/handoffs/2026-09-01-a.txt",
    "docs/handoffs/missing.md",
    "docs/handoffs\\2026-09-01-a.md",
    "",
])
def test_handoff_page_rejects_bad_paths_with_404(client, monkeypatch, ebook, bad):
    _handoff(ebook, "2026-09-01-a.md", "存在的交接")
    _write(ebook / "CLAUDE.md", "# 不可被讀到\n")
    _write(ebook / "docs/plans/2026-09-01-a.md", "---\ntitle: plan\n---\n不可被讀到\n")
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = _detail(client, bad)
    assert resp.status_code == 404
    assert "不可被讀到" not in resp.text
    assert "找不到這份文件" in resp.text


def test_handoff_page_symlink_escape_is_rejected(client, monkeypatch, ebook, tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("---\ntitle: s\n---\n外部機密\n", encoding="utf-8")
    (ebook / "docs/handoffs/2026-09-01-link.md").symlink_to(secret)
    _install(monkeypatch, {str(ebook): ["android"]})
    resp = _detail(client, "docs/handoffs/2026-09-01-link.md")
    assert resp.status_code == 404
    assert "外部機密" not in resp.text


def test_handoff_page_unknown_kunsu_is_404_not_fallback(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "存在的交接")
    _install(monkeypatch, {str(ebook): ["android"]})
    assert _detail(client, "docs/handoffs/2026-09-01-a.md", k="nope").status_code == 404
    assert client.get("/handoff", params={"f": "docs/handoffs/2026-09-01-a.md"}).status_code == 404


def test_handoff_page_lists_replies_oldest_first_with_status_and_verify(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "多回覆交接")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05.md", "2026-09-01-a.md", "partial",
           body="第一份回覆。")
    _reply(ebook, "2026-09-01-a-reply-2026-09-05-2.md", "2026-09-01-a.md", "submitted",
           verify="testable-now", body="第二份回覆。")
    _reply(ebook, "2026-09-01-other-reply-2026-09-06.md", "2026-09-01-other.md", "submitted",
           body="別串的回覆。")
    _install(monkeypatch, {str(ebook): ["android"]})
    html = _detail(client, "docs/handoffs/2026-09-01-a.md").text
    assert "回覆（2 份，舊→新）" in html
    assert html.index("第一份回覆。") < html.index("第二份回覆。")
    assert "別串的回覆。" not in html
    assert "status: submitted" in html and "馬上可測" in html


def test_handoff_page_opens_archived_handoff_with_archive_replies(client, monkeypatch, ebook):
    _handoff(ebook, "2026-08-01-old.md", "已歸檔交接", status="done", archive=True,
             extra="depends_on:\n  - 2026-07-01-base.md\n")
    _handoff(ebook, "2026-07-01-base.md", "前置交接", status="done", archive=True)
    _write(
        ebook / "docs/handoffs/archive/replies/2026-08-01-old-reply-2026-08-02.md",
        "---\nin_reply_to: 2026-08-01-old.md\nstatus: submitted\n---\n\n歸檔的回覆。\n",
    )
    _install(monkeypatch, {str(ebook): ["android"]})
    html = _detail(client, "docs/handoffs/archive/2026-08-01-old.md").text
    assert "已歸檔交接" in html and "歸檔的回覆。" in html
    assert "已歸檔" in html and 'href="/archive?k=ebook"' in html
    assert "前置交接（已完成）" in html


def test_handoff_page_opens_application_and_report(client, monkeypatch, ebook):
    _write(ebook / "docs/applications/2026-09-01-apply.md",
           "---\ntitle: 申請加入\nstatus: submitted\n---\n\n申請內文。\n")
    _write(ebook / "docs/reports/2026-09-01-report.md",
           "---\ntitle: 上報一件\nstatus: submitted\n---\n\n上報內文。\n")
    _install(monkeypatch, {str(ebook): ["android"]})
    a = _detail(client, "docs/applications/2026-09-01-apply.md").text
    r = _detail(client, "docs/reports/2026-09-01-report.md").text
    assert "申請內文。" in a and "尚無回覆" not in a
    assert "上報內文。" in r


def test_handoff_page_stale_kunsu_shows_notice(client, monkeypatch, ebook):
    _install(monkeypatch, {str(ebook): ["android"]}, stale=(str(ebook),))
    resp = _detail(client, "docs/handoffs/2026-09-01-a.md")
    assert resp.status_code == 200
    assert "路徑失聯" in resp.text


def test_handoff_page_never_runs_mailbox_scan(client, monkeypatch, ebook):
    _handoff(ebook, "2026-09-01-a.md", "存在的交接")
    _install(monkeypatch, {str(ebook): ["android"]})
    monkeypatch.setattr("app.main.scan_kunsu", lambda kp: pytest.fail("全文頁不得呼叫掃描"))
    assert _detail(client, "docs/handoffs/2026-09-01-a.md").status_code == 200


def test_handoff_page_degrades_to_pre_when_markdown_unavailable(client, monkeypatch, ebook):
    import app.markdown_render as mr
    _write(ebook / "docs/handoffs/2026-09-01-a.md",
           "---\ntitle: 降級\nto: android\nstatus: open\n---\n\n## 標題 <b>x</b>\n")
    _install(monkeypatch, {str(ebook): ["android"]})
    monkeypatch.setattr(mr, "_MarkdownIt", None)
    monkeypatch.setattr(mr, "_md", None)
    html = _detail(client, "docs/handoffs/2026-09-01-a.md").text
    assert mr.MARKDOWN_UNAVAILABLE_NOTICE in html
    assert "<pre>" in html and "## 標題 &lt;b&gt;x&lt;/b&gt;" in html
    assert "<h2>標題" not in html


def test_handoff_page_does_not_repeat_title_from_frontmatter_or_leading_h1(client, monkeypatch, ebook):
    _write(
        ebook / "docs/handoffs/2026-09-01-t.md",
        "---\ntitle: 不重複的標題\nto: android\nstatus: open\n---\n\n# 不重複的標題\n\n"
        "## 第一節\n\n內文。\n",
    )
    _install(monkeypatch, {str(ebook): ["android"]})
    html = _detail(client, "docs/handoffs/2026-09-01-t.md").text
    doc = html.split('<div class="kb-doc">')[1]
    assert doc.count("不重複的標題") == 1
    assert "<h1>" not in doc
    assert "<h2>第一節</h2>" in doc
    assert "<th>title</th>" not in doc
