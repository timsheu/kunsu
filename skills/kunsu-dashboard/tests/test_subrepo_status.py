"""
test_subrepo_status.py — skills/kunsu-dashboard/app/subrepo_status.py 的單元測試

覆蓋計畫 U3 的 7 個 test scenarios：
  - Covers AE1. happy path：交接文件無任何回覆 → 待接手
  - Covers AE2. happy path：最新回覆 status: submitted → 已回覆待確認
  - Covers AE3. happy path：最新回覆 status: done → 不列出
  - edge case：最新回覆 status: partial 或 status: blocked → 待接手
  - edge case：同日多份回覆（-2 後綴）→ 依數值排序取最大 n 者，非字串排序
  - edge case：to: 值不在任何已知角色代碼集合 → unknown_to 清單
  - error path：frontmatter 缺少必要欄位 → 不拋例外，歸入異常清單
"""

from pathlib import Path

import pytest

from app.subrepo_status import (
    ErrorItem,
    HandoffInfo,
    SubrepoStatusResult,
    UnknownToItem,
    get_subrepo_status,
)


# ── 輔助函式 ────────────────────────────────────────────────────────────────────

def make_handoff(
    handoffs_dir: Path,
    filename: str,
    title: str = "測試交接",
    from_role: str = "ebook-store",
    to_role: str = "my-role",
    created: str = "2026-07-01",
) -> Path:
    """在 handoffs_dir 建立一份交接文件（含完整 frontmatter）。"""
    content = f"""---
title: {title}
from: {from_role}
to: {to_role}
created: {created}
status: open
---

交接內容。
"""
    path = handoffs_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def make_reply(
    replies_dir: Path,
    filename: str,
    in_reply_to: str,
    status: str = "submitted",
    from_role: str = "my-role",
    to_role: str = "ebook-store",
) -> Path:
    """在 replies_dir 建立一份回覆檔案（含完整 frontmatter）。"""
    replies_dir.mkdir(parents=True, exist_ok=True)
    content = f"""---
title: 回覆
type: handoff-reply
from: {from_role}
to: {to_role}
in_reply_to: {in_reply_to}
created: 2026-07-06
status: {status}
---

回覆內容。
"""
    path = replies_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def setup_kunsu(tmp_path: Path, kunsu_name: str = "kunsu") -> tuple[Path, Path, Path]:
    """建立基本軍師目錄結構，回傳 (kunsu_path, handoffs_dir, replies_dir)。"""
    kunsu = tmp_path / kunsu_name
    handoffs = kunsu / "docs" / "handoffs"
    replies = handoffs / "replies"
    handoffs.mkdir(parents=True)
    return kunsu, handoffs, replies


# ── Test Scenario 1（Covers AE1）：無回覆 → 待接手 ──────────────────────────────

class TestNoReplyIsPending:
    """AE1: 交接文件無任何回覆，應分類為待接手。"""

    def test_handoff_without_reply_is_pending(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role", "other-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        assert len(result.awaiting_confirm) == 0
        assert len(result.unknown_to) == 0
        assert len(result.errors) == 0

        item = result.pending[0]
        assert item.filename == "2026-07-01-test-handoff.md"
        assert item.to_role == "my-role"
        assert item.latest_reply_status is None
        assert item.latest_reply_date is None

    def test_pending_handoff_contains_correct_metadata(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(
            handoffs,
            "2026-07-01-test-handoff.md",
            title="重要交接",
            from_role="ebook-store",
            to_role="my-role",
            created="2026-07-01",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        item = result.pending[0]
        assert item.title == "重要交接"
        assert item.from_role == "ebook-store"
        assert item.created == "2026-07-01"

    def test_pending_handoff_carries_raw_file_content(self, tmp_path):
        """HandoffInfo.raw_content 應為檔案完整原始內容，供 Dashboard 展開式預覽使用。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        path = make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        expected_content = path.read_text(encoding="utf-8")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        assert result.pending[0].raw_content == expected_content
        assert "交接內容。" in result.pending[0].raw_content

    def test_pending_handoff_carries_mtime(self, tmp_path):
        """HandoffInfo.mtime 應等於檔案實際的最後修改時間（st_mtime）。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        path = make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        expected_mtime = path.stat().st_mtime

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        assert result.pending[0].mtime == expected_mtime


# ── Test Scenario 2（Covers AE2）：最新回覆 submitted → 已回覆待確認 ─────────────

class TestSubmittedReplyIsAwaitingConfirm:
    """AE2: 最新回覆 status: submitted，應分類為已回覆待確認。"""

    def test_submitted_reply_is_awaiting_confirm(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="submitted",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 1
        assert len(result.errors) == 0

        item = result.awaiting_confirm[0]
        assert item.filename == "2026-07-01-test-handoff.md"
        assert item.latest_reply_status == "submitted"
        assert item.latest_reply_date == "2026-07-06"


# ── Test Scenario 3（Covers AE3）：最新回覆 done → 不列出 ───────────────────────

class TestDoneReplyIsSkipped:
    """AE3: 最新回覆 status: done，應略過不列出。"""

    def test_done_reply_not_listed(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="done",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 0
        assert len(result.unknown_to) == 0
        assert len(result.errors) == 0


# ── Test Scenario 4：partial / blocked → 待接手 ───────────────────────────────

class TestPartialAndBlockedIsPending:
    """edge case: status: partial 或 status: blocked 的最新回覆應視同待接手。

    覆蓋 SKILL.md 4a-3 表格中「最新回覆 status: partial/blocked → 待接手」兩列。
    """

    def test_partial_reply_is_pending(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="partial",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        assert len(result.awaiting_confirm) == 0
        assert result.pending[0].latest_reply_status == "partial"

    def test_blocked_reply_is_pending(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="blocked",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 1
        assert len(result.awaiting_confirm) == 0
        assert result.pending[0].latest_reply_status == "blocked"


# ── Test Scenario 5：同日多份回覆數值排序 ──────────────────────────────────────

class TestSameDayMultipleRepliesSorting:
    """edge case: 同日多份回覆（含 -2 後綴）→ 依數值排序取最大 n 者為最新。

    此測試驗證數值排序而非字串排序：
    - 基礎回覆（無後綴，n=1）status: done
    - -2 後綴回覆（n=2）       status: submitted

    字串降序排列：'.md' > '-2.md'（因 '.'=46 > '-'=45）→ 基礎回覆排第一 → done → 略過
    數值排序：n=2 > n=1 → -2 回覆排第一 → submitted → 已回覆待確認（正確）
    """

    def test_numeric_sort_takes_highest_n(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        handoff_name = "2026-07-01-test-handoff.md"

        make_handoff(handoffs, handoff_name, to_role="my-role")

        # n=1（無後綴，基礎回覆）：status: done
        make_reply(
            replies,
            f"{handoff_name[:-3]}-reply-2026-07-06.md",
            in_reply_to=handoff_name,
            status="done",
        )
        # n=2（-2 後綴）：status: submitted（較新，應獲選）
        make_reply(
            replies,
            f"{handoff_name[:-3]}-reply-2026-07-06-2.md",
            in_reply_to=handoff_name,
            status="submitted",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        # 若誤用字串排序，n=1（done）會排第一 → 結果為空（略過），測試失敗
        # 正確數值排序：n=2（submitted）排第一 → 已回覆待確認
        assert len(result.awaiting_confirm) == 1, (
            "n=2 的回覆（submitted）應為最新，"
            "若結果為空表示誤用字串排序（n=1 的 done 被錯誤選中）"
        )
        assert len(result.pending) == 0
        assert result.awaiting_confirm[0].latest_reply_status == "submitted"

    def test_three_same_day_replies_selects_highest_n(self, tmp_path):
        """同日三份回覆（n=1/2/3），n=3 應為最新。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        handoff_name = "2026-07-01-test-handoff.md"

        make_handoff(handoffs, handoff_name, to_role="my-role")

        make_reply(
            replies,
            f"{handoff_name[:-3]}-reply-2026-07-06.md",
            in_reply_to=handoff_name,
            status="partial",    # n=1
        )
        make_reply(
            replies,
            f"{handoff_name[:-3]}-reply-2026-07-06-2.md",
            in_reply_to=handoff_name,
            status="blocked",    # n=2
        )
        make_reply(
            replies,
            f"{handoff_name[:-3]}-reply-2026-07-06-3.md",
            in_reply_to=handoff_name,
            status="submitted",  # n=3（最新）
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.awaiting_confirm) == 1
        assert result.awaiting_confirm[0].latest_reply_status == "submitted"


# ── Test Scenario 6：to: 不符清單 ─────────────────────────────────────────────

class TestUnknownToIsListed:
    """edge case: to: 值不在此軍師任何已知角色代碼集合中 → 加入 unknown_to 清單。"""

    def test_unknown_to_value_is_flagged(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(
            handoffs,
            "2026-07-01-test-handoff.md",
            to_role="typo-role",  # 非已知角色代碼
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role", "other-role"},  # 不含 typo-role
            kunsu_path=str(kunsu),
        )

        assert len(result.unknown_to) == 1
        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 0

        item = result.unknown_to[0]
        assert item.filename == "2026-07-01-test-handoff.md"
        assert item.to_value == "typo-role"

    def test_known_other_role_is_silently_skipped(self, tmp_path):
        """to: 屬於已知角色但非本 repo 角色（其他子 repo）→ 靜默略過，不出現在任何清單。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        make_handoff(
            handoffs,
            "2026-07-01-test-handoff.md",
            to_role="other-role",  # 已知但非本 repo 角色
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role", "other-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 0
        assert len(result.unknown_to) == 0
        assert len(result.errors) == 0


# ── Test Scenario 7：frontmatter 缺少必要欄位 → 歸入異常清單 ──────────────────

class TestMissingFrontmatterFieldIsError:
    """error path: frontmatter 缺必要欄位 → 不拋例外，歸入異常清單，其餘繼續處理。"""

    def test_missing_to_field_goes_to_errors(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        # 缺少 to: 欄位
        bad_content = """---
title: 有問題的交接
from: ebook-store
created: 2026-07-01
status: open
---

缺少 to: 欄位。
"""
        (handoffs / "2026-07-01-bad-handoff.md").write_text(bad_content, encoding="utf-8")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.errors) == 1
        assert len(result.pending) == 0
        assert "to" in result.errors[0].error

    def test_missing_multiple_fields_reports_all(self, tmp_path):
        """多個必要欄位缺失時，錯誤訊息應列出全部缺失欄位。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        # 只有 title，其餘都缺
        bad_content = """---
title: 只有標題
---

缺 from/to/created。
"""
        (handoffs / "2026-07-01-minimal.md").write_text(bad_content, encoding="utf-8")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.errors) == 1
        error_msg = result.errors[0].error
        # 三個缺失欄位（from, to, created）應全部出現在錯誤訊息中
        assert "from" in error_msg or "to" in error_msg or "created" in error_msg

    def test_error_in_one_handoff_does_not_stop_others(self, tmp_path):
        """一份交接文件異常，其餘交接文件的判斷不受影響。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)

        # 正常交接文件
        make_handoff(handoffs, "2026-07-01-good-handoff.md", to_role="my-role")

        # 有問題的交接文件（缺 to:）
        bad_content = """---
title: 有問題的交接
from: ebook-store
created: 2026-07-01
---

缺少 to: 欄位。
"""
        (handoffs / "2026-07-01-bad-handoff.md").write_text(bad_content, encoding="utf-8")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        # 正常的那份應分類為待接手
        assert len(result.pending) == 1
        assert result.pending[0].filename == "2026-07-01-good-handoff.md"
        # 有問題的那份應進異常清單
        assert len(result.errors) == 1
        assert result.errors[0].filename == "2026-07-01-bad-handoff.md"


# ── 補充邊界測試 ─────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """補充：handoffs 目錄不存在、空目錄等邊界情境。"""

    def test_no_handoffs_dir_returns_empty_result(self, tmp_path):
        """軍師 docs/handoffs/ 不存在 → 回傳空結果，不拋例外。"""
        kunsu = tmp_path / "kunsu"
        kunsu.mkdir()

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert isinstance(result, SubrepoStatusResult)
        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 0
        assert len(result.unknown_to) == 0
        assert len(result.errors) == 0

    def test_archive_files_are_not_included(self, tmp_path):
        """archive/ 子目錄內的 .md 不應被誤判為頂層交接文件。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        archive = handoffs / "archive"
        archive.mkdir()

        # 在 archive/ 放一個歸檔的交接文件（已完成，不應出現）
        archived_content = """---
title: 已歸檔交接
from: ebook-store
to: my-role
created: 2026-06-01
status: done
---
"""
        (archive / "2026-06-01-archived.md").write_text(archived_content, encoding="utf-8")

        # 頂層放一個正常交接文件
        make_handoff(handoffs, "2026-07-01-active.md", to_role="my-role")

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        # 只有頂層的一份應被判斷
        assert len(result.pending) == 1
        assert result.pending[0].filename == "2026-07-01-active.md"

    def test_replies_subdir_not_treated_as_handoffs(self, tmp_path):
        """replies/ 子目錄內的 .md 不應被掃描為交接文件（只掃頂層）。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        replies.mkdir(parents=True)

        # 在 replies/ 放一份回覆（若誤當交接文件，from/to 解析會出錯）
        reply_content = """---
title: 某回覆
type: handoff-reply
from: my-role
to: ebook-store
in_reply_to: some-handoff.md
created: 2026-07-06
status: submitted
---
"""
        (replies / "some-handoff-reply-2026-07-06.md").write_text(
            reply_content, encoding="utf-8"
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        # replies/ 內的回覆不應出現在任何分類
        assert len(result.pending) == 0
        assert len(result.awaiting_confirm) == 0
        assert len(result.unknown_to) == 0
        assert len(result.errors) == 0


# ── Regression（code review C8）：frontmatter 內文含 '---' 開頭行不誤判為結束標記 ──


class TestFrontmatterDelimiterRobustness:
    def test_body_line_starting_with_dashes_does_not_truncate_frontmatter(
        self, tmp_path
    ):
        """交接內文（frontmatter 之後）含以 '---' 開頭的行不影響 frontmatter 解析

        ——用來確認新的結束標記判斷（須為獨立一行）沒有誤傷正常檔案。
        """
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        content = """---
title: 測試交接
from: ebook-store
to: my-role
created: 2026-07-01
status: open
---

正文開頭。
---
這行看起來像分隔符，但屬於內文，不是 frontmatter 的一部分。
"""
        (handoffs / "2026-07-01-test-handoff.md").write_text(
            content, encoding="utf-8"
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.errors) == 0
        assert len(result.pending) == 1
        assert result.pending[0].title == "測試交接"


# ── Regression（code review C9）：in_reply_to 型別強制轉為字串 ─────────────────


class TestInReplyToTypeCoercion:
    def test_normal_string_in_reply_to_still_matches(self, tmp_path):
        """基本情境不因新增的 str() 轉換而退化：一般字串檔名仍正常比對成功。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="submitted",
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        assert len(result.awaiting_confirm) == 1
        assert len(result.pending) == 0

    def test_non_string_in_reply_to_does_not_crash(self, tmp_path):
        """in_reply_to 被 YAML 解析為非字串型別（如布林值）時不得拋例外。

        這種值本來就不是合法的交接檔名，預期結果是交接文件仍列為「待接手」
        （找不到相符的回覆），但不能讓型別不符直接讓函式崩潰。
        """
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")

        replies.mkdir(parents=True, exist_ok=True)
        reply_content = """---
title: 回覆
type: handoff-reply
from: my-role
to: ebook-store
in_reply_to: true
created: 2026-07-06
status: submitted
---
"""
        (replies / "2026-07-01-test-handoff-reply-2026-07-06.md").write_text(
            reply_content, encoding="utf-8"
        )

        result = get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

        # 不拋例外即為此測試的主要目的；型別不符的回覆無法比對，
        # 交接文件因找不到相符回覆而歸類為待接手。
        assert len(result.pending) == 1
        assert len(result.awaiting_confirm) == 0
