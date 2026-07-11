"""
test_kunsu_scan.py — KunsuScanResult 與 scan_kunsu 函式的測試

測試情境對應計畫 U2 的六個 test scenarios：
  1. happy path: 三支腳本 exit 0，各有 NEW_* 行 → 正確解析三個清單
  2. happy path: 三支腳本 exit 0，零筆結果 → 回傳空清單，不視為異常
  3. edge case: TRIPWIRE: rename 形式（src -> dst）→ 完整行字串保留雙側路徑
  4. error path: 任一腳本 exit 2 → 標記 tripwire，停止後續腳本不再呼叫
  5. error path: 任一腳本非預期 exit code → script_error 非 None，
                 tripwire_lines 為空；與 tripwire 明確可區分
  6. integration: 對真實 git repo fixture 呼叫真實三支腳本（不 mock），
                  驗證端到端解析結果與腳本實際輸出一致
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.kunsu_scan import KunsuScanResult, scan_kunsu


# ─── 輔助工具 ─────────────────────────────────────────────────────────────────


def _make_proc(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> MagicMock:
    """建立模擬 subprocess.CompletedProcess 的 MagicMock。"""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ─── Scenario 1: happy path，三支腳本各回傳若干 NEW_* 行 ──────────────────────


def test_all_scripts_exit0_results_parsed_correctly():
    """三支腳本皆 exit 0 且各回傳 NEW_* 行 → 正確解析至對應清單，無異常狀態。"""
    replies_out = (
        "NEW_REPLY:docs/handoffs/replies/2026-07-11-foo-reply.md\n"
        "NEW_REPLY:docs/handoffs/replies/2026-07-11-bar-reply.md\n"
    )
    apps_out = "NEW_APPLICATION:docs/applications/2026-07-11-baz-apply.md\n"
    reports_out = "NEW_REPORT:docs/reports/2026-07-11-qux-report.md\n"

    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_proc(0, replies_out),
            _make_proc(0, apps_out),
            _make_proc(0, reports_out),
        ]
        result = scan_kunsu("/fake/kunsu")

    assert result.new_replies == [
        "docs/handoffs/replies/2026-07-11-foo-reply.md",
        "docs/handoffs/replies/2026-07-11-bar-reply.md",
    ]
    assert result.new_applications == [
        "docs/applications/2026-07-11-baz-apply.md",
    ]
    assert result.new_reports == [
        "docs/reports/2026-07-11-qux-report.md",
    ]
    assert result.tripwire_lines == []
    assert result.script_error is None


# ─── Scenario 2: happy path，三支腳本 exit 0 但零筆結果 ──────────────────────


def test_all_scripts_exit0_empty_is_not_error():
    """三支腳本 exit 0 且無任何輸出 → 三清單皆空，tripwire_lines 空，script_error None。"""
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(0, "")
        result = scan_kunsu("/fake/kunsu")

    assert result.new_replies == []
    assert result.new_applications == []
    assert result.new_reports == []
    assert result.tripwire_lines == []
    assert result.script_error is None


# ─── Scenario 3: TRIPWIRE: rename 形式（src -> dst）──────────────────────────


def test_tripwire_rename_form_preserved_in_full():
    """scan-replies exit 2，TRIPWIRE 行為 rename 形式 → 完整行字串（含雙側路徑）保留。"""
    tripwire_out = (
        "TRIPWIRE:RM docs/handoffs/foo.md -> docs/wrong-place/foo.md\n"
    )
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(2, tripwire_out)
        result = scan_kunsu("/fake/kunsu")

    assert len(result.tripwire_lines) == 1
    line = result.tripwire_lines[0]
    # 完整字串需含雙側路徑，可在上層 UI 自行解析
    assert line.startswith("TRIPWIRE:")
    assert "docs/handoffs/foo.md" in line
    assert "docs/wrong-place/foo.md" in line
    assert "->" in line
    # 不是 script_error
    assert result.script_error is None


def test_tripwire_multiple_lines_all_collected():
    """exit 2 且 TRIPWIRE 行有多筆（含 rename 與單路徑混合）→ 全數收集。"""
    tripwire_out = (
        "TRIPWIRE:?? docs/handoffs/unexpected.md\n"
        "TRIPWIRE:RM docs/handoffs/replies/r.md -> docs/handoffs/unexpected/r.md\n"
    )
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(2, tripwire_out)
        result = scan_kunsu("/fake/kunsu")

    assert len(result.tripwire_lines) == 2
    assert result.tripwire_lines[0] == "TRIPWIRE:?? docs/handoffs/unexpected.md"
    assert "RM" in result.tripwire_lines[1]


# ─── Scenario 4: exit 2 → tripwire，停止後續腳本 ─────────────────────────────


def test_exit2_on_first_script_stops_subsequent_calls():
    """第一支腳本（scan-replies.sh）exit 2 → subprocess.run 只被呼叫一次，後兩支略過。"""
    tripwire_out = "TRIPWIRE:?? docs/handoffs/bad.md\n"
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(2, tripwire_out)
        result = scan_kunsu("/fake/kunsu")

    # 只呼叫一次（第一支即觸發 tripwire，立即回傳）
    assert mock_run.call_count == 1

    assert result.tripwire_lines == ["TRIPWIRE:?? docs/handoffs/bad.md"]
    assert result.new_replies == []
    assert result.new_applications == []
    assert result.new_reports == []
    assert result.script_error is None


def test_exit2_on_second_script_stops_third_preserves_prior_results():
    """第一支 exit 0 有結果、第二支 exit 2 → 第三支不被呼叫；第一支已收集的清單保留。"""
    replies_out = "NEW_REPLY:docs/handoffs/replies/2026-07-11-ok.md\n"
    tripwire_out = "TRIPWIRE:?? docs/applications/bad.txt\n"

    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_proc(0, replies_out),  # scan-replies.sh exit 0
            _make_proc(2, tripwire_out), # scan-applications.sh exit 2
            # scan-reports.sh → 不被呼叫
        ]
        result = scan_kunsu("/fake/kunsu")

    assert mock_run.call_count == 2  # 第三支未被呼叫
    assert result.tripwire_lines == ["TRIPWIRE:?? docs/applications/bad.txt"]
    assert result.new_replies == ["docs/handoffs/replies/2026-07-11-ok.md"]
    assert result.new_applications == []
    assert result.new_reports == []
    assert result.script_error is None


# ─── Scenario 5: 非預期 exit code → script_error，與 tripwire 明確可區分 ──────


def test_unexpected_exit_code_marks_script_error_not_tripwire():
    """第一支腳本 exit 3（非預期）→ script_error 非 None，tripwire_lines 為空清單。"""
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(3, "", "some internal failure")
        result = scan_kunsu("/fake/kunsu")

    # 明確可區分：tripwire 與 script_error 是不同欄位
    assert result.tripwire_lines == []          # 不是 tripwire
    assert result.script_error is not None      # 是腳本錯誤
    assert "scan-replies.sh" in result.script_error
    assert "3" in result.script_error
    assert "some internal failure" in result.script_error


def test_script_error_and_tripwire_are_distinguishable():
    """驗證 tripwire 與 script_error 為獨立欄位，可明確區分兩種異常類型。"""
    # 情境 A：tripwire → tripwire_lines 非空，script_error 為 None
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(2, "TRIPWIRE:?? docs/handoffs/x.md\n")
        tripwire_result = scan_kunsu("/fake/kunsu")

    assert tripwire_result.tripwire_lines != []
    assert tripwire_result.script_error is None

    # 情境 B：腳本錯誤 → tripwire_lines 為空，script_error 非 None
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(42, "", "fatal: not a repo")
        error_result = scan_kunsu("/fake/kunsu")

    assert error_result.tripwire_lines == []
    assert error_result.script_error is not None
    # 兩者互斥（在此測試的回傳值中）
    assert not (tripwire_result.script_error and tripwire_result.tripwire_lines == [])


def test_unexpected_exit_code_empty_stderr():
    """非預期 exit code 且無 stderr → script_error 仍記錄 exit code，無冒號尾端。"""
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(1, "", "")
        result = scan_kunsu("/fake/kunsu")

    assert result.script_error is not None
    assert "scan-replies.sh" in result.script_error
    assert "1" in result.script_error
    # 無 stderr 時不應有「: 」尾端的空字串
    assert not result.script_error.endswith(": ")


# ─── Scenario 6: integration test（真實腳本 × 真實 git repo fixture）─────────


@pytest.fixture()
def git_repo_with_inbox_files(tmp_path: Path) -> Path:
    """建立帶有已知未 commit 信箱檔案的暫存 git repo。

    建立的未 commit 檔案：
      docs/handoffs/replies/2026-07-11-test-reply.md  → 應被 scan-replies.sh 偵測
      docs/applications/2026-07-11-test-app.md        → 應被 scan-applications.sh 偵測
      docs/reports/2026-07-11-test-report.md          → 應被 scan-reports.sh 偵測
    """
    # git init + 基本 config（避免 "Please tell me who you are" 警告）
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@kunsu.test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "KunsuTest"],
        check=True,
        capture_output=True,
    )

    # 新回覆（untracked → scan-replies.sh 輸出 NEW_REPLY:）
    replies_dir = tmp_path / "docs" / "handoffs" / "replies"
    replies_dir.mkdir(parents=True)
    (replies_dir / "2026-07-11-test-reply.md").write_text("# 測試回覆\n")

    # 新申請（untracked → scan-applications.sh 輸出 NEW_APPLICATION:）
    apps_dir = tmp_path / "docs" / "applications"
    apps_dir.mkdir(parents=True)
    (apps_dir / "2026-07-11-test-app.md").write_text("# 測試申請\n")

    # 新上報（untracked → scan-reports.sh 輸出 NEW_REPORT:）
    reports_dir = tmp_path / "docs" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "2026-07-11-test-report.md").write_text("# 測試上報\n")

    return tmp_path


def test_integration_real_scripts_against_git_fixture(
    git_repo_with_inbox_files: Path,
):
    """對真實 git repo fixture 呼叫真實三支腳本（不 mock），驗證端到端解析一致。

    此測試直接執行 scan-replies.sh、scan-applications.sh、scan-reports.sh；
    確認：
    - 三支腳本皆 exit 0（無 tripwire、無腳本錯誤）
    - 解析結果的路徑字串與腳本輸出格式一致
    - 每種信箱各偵測到一筆已知檔案
    """
    kunsu_path = str(git_repo_with_inbox_files)
    result = scan_kunsu(kunsu_path)

    # 無 tripwire
    assert result.tripwire_lines == [], (
        f"Unexpected tripwire lines: {result.tripwire_lines}"
    )
    # 無腳本錯誤
    assert result.script_error is None, (
        f"Unexpected script error: {result.script_error}"
    )

    # 新回覆：應含測試回覆檔案路徑
    matched_replies = [
        r for r in result.new_replies
        if "2026-07-11-test-reply.md" in r
    ]
    assert len(matched_replies) == 1, (
        f"Expected exactly one test reply, got: {result.new_replies}"
    )
    # 路徑格式為相對路徑（腳本輸出格式）
    assert matched_replies[0].startswith("docs/handoffs/replies/")

    # 新申請：應含測試申請檔案路徑
    matched_apps = [
        a for a in result.new_applications
        if "2026-07-11-test-app.md" in a
    ]
    assert len(matched_apps) == 1, (
        f"Expected exactly one test application, got: {result.new_applications}"
    )
    assert matched_apps[0].startswith("docs/applications/")

    # 新上報：應含測試上報檔案路徑
    matched_reports = [
        r for r in result.new_reports
        if "2026-07-11-test-report.md" in r
    ]
    assert len(matched_reports) == 1, (
        f"Expected exactly one test report, got: {result.new_reports}"
    )
    assert matched_reports[0].startswith("docs/reports/")


# ─── Regression（code review C1）：subprocess 逾時／找不到執行檔不得穿透例外 ──


def test_timeout_expired_returns_script_error_not_exception():
    """腳本逾時（TimeoutExpired）→ 回傳 script_error，不得讓例外穿透至呼叫端。"""
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="scan-replies.sh", timeout=15)
        result = scan_kunsu("/fake/kunsu")

    assert result.script_error is not None
    assert "timed out" in result.script_error
    assert result.tripwire_lines == []


def test_bash_not_found_returns_script_error_not_exception():
    """bash 執行檔不存在（FileNotFoundError）→ 回傳 script_error，不得讓例外穿透。"""
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("bash: command not found")
        result = scan_kunsu("/fake/kunsu")

    assert result.script_error is not None
    assert "failed to run" in result.script_error


# ─── Regression（code review C3）：exit 2 但 stdout 無 TRIPWIRE: 行仍須標記 tripwire ──


def test_exit2_with_no_tripwire_prefix_lines_still_flags_tripwire():
    """exit code 2 但 stdout 沒有任何 TRIPWIRE: 前綴行（診斷輸出寫到 stderr 等情況）

    → tripwire_lines 仍必須非空，不得讓呼叫端誤判為「正常、無新訊息」。
    """
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_proc(2, stdout="", stderr="unexpected write outside mailbox"),
        ]
        result = scan_kunsu("/fake/kunsu")

    assert result.tripwire_lines != []
    assert result.script_error is None


# ─── Regression（code review C4）：前綴比對須侷限於該腳本自己的前綴 ──────────


def test_script_output_only_matched_against_its_own_prefix():
    """scan-replies.sh 的 stdout 若剛好含有其他前綴（NEW_APPLICATION:）開頭的行，

    不得被誤植到 new_applications——每支腳本的輸出只比對它自己被指派的前綴。
    """
    with patch("app.kunsu_scan.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_proc(0, stdout=(
                "NEW_REPLY:docs/handoffs/replies/real-reply.md\n"
                "NEW_APPLICATION:this-looks-like-an-application-but-came-from-scan-replies.sh\n"
            )),
            _make_proc(0, stdout=""),
            _make_proc(0, stdout=""),
        ]
        result = scan_kunsu("/fake/kunsu")

    assert result.new_replies == ["docs/handoffs/replies/real-reply.md"]
    assert result.new_applications == []
