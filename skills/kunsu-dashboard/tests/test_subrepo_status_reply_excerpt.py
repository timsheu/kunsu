"""
test_subrepo_status_reply_excerpt.py — 最新回覆首句摘錄（display-only）

自 test_subrepo_status.py 拆出（該檔因本功能跨過 1000 行，比照
test_handoff_graph／test_handoff_graph_html 兩檔並存慣例）；fixture helper
（make_handoff／make_reply／setup_kunsu）自原檔匯入共用，不另抄一份。
"""

from __future__ import annotations

from app.subrepo_status import _extract_reply_excerpt, get_subrepo_status
from test_subrepo_status import make_handoff, make_reply, setup_kunsu


# ── 最新回覆首句摘錄（display-only，R4 萃取規則）────────────────────────────────

class TestReplyExcerptExtraction:
    """純函式 _extract_reply_excerpt：輸入 frontmatter 之後的本文，輸出首句摘錄。"""

    def test_template_echo_h1_and_status_heading_then_hardwrap(self):
        """Covers AE1／AE4：範本回顯 H1 與「## 狀態」小標跳過；硬換行先併段再切句。"""
        body = (
            "# 標題 — 回覆\n\n## 狀態\n\n"
            "七個端點全部實作並接線完成，`xcodebuild test` 全套通過（單元測試 141/141）。\n"
            "已 commit。\n"
        )
        assert _extract_reply_excerpt(body) == (
            "七個端點全部實作並接線完成，xcodebuild test 全套通過（單元測試 141/141）。"
        )

    def test_hardwrap_without_period_on_first_line_is_joined(self):
        """Covers AE4：首行硬換行未以句號收尾，兩行併成一句。"""
        body = "承接同日的第一份回覆（-reply-2026-08-24.md），本份回報依\n裁示完成的三項修正。\n"
        assert _extract_reply_excerpt(body) == (
            "承接同日的第一份回覆（-reply-2026-08-24.md），本份回報依裁示完成的三項修正。"
        )

    def test_h1_that_reads_like_conclusion_is_still_skipped(self):
        """Covers AE5：H1 本身像結論仍取其後首段；反引號去除。"""
        body = (
            "# 回覆（第三階段）：正式切換完成，複驗全數通過\n\n"
            "`endlesslights.link` 已完成正式環境切換：前門連正式後台。\n"
        )
        assert _extract_reply_excerpt(body) == "endlesslights.link 已完成正式環境切換：前門連正式後台。"

    def test_truncates_at_60_chars_with_ellipsis(self):
        """Covers AE8：超過 60 字元且無句號 → 60 字元加「…」，CJK 以字元計。"""
        body = "甲" * 40 + "abcdefghij" * 3 + "\n"
        out = _extract_reply_excerpt(body)
        assert out == "甲" * 40 + "abcdefghij" * 2 + "…"
        assert len(out) == 61

    def test_sentence_shorter_than_60_is_not_truncated(self):
        body = "狀態：完成。後面還有第二句不應出現。\n"
        assert _extract_reply_excerpt(body) == "狀態：完成。"

    def test_long_sentence_with_period_is_cut_then_truncated(self):
        """先以句號切句、再套 60 字元上限（兩段式依序）。"""
        body = "乙" * 70 + "。第二句。\n"
        assert _extract_reply_excerpt(body) == "乙" * 60 + "…"

    def test_placeholder_body_is_kept_verbatim(self):
        """Covers AE9：範本預設「_（待補充）_」→「（待補充）」，不視為空值。"""
        assert _extract_reply_excerpt("_（待補充）_\n") == "（待補充）"

    def test_list_marker_is_stripped(self):
        body = "- install-logrotate.sh：/etc/logrotate.d/ 已就位。\n- 第二項。\n"
        assert _extract_reply_excerpt(body) == "install-logrotate.sh：/etc/logrotate.d/ 已就位。"

    def test_numbered_list_marker_is_stripped(self):
        body = "1. 前端部署完成。\n2. 後端待補。\n"
        assert _extract_reply_excerpt(body) == "前端部署完成。"

    def test_fence_and_table_rows_are_skipped(self):
        body = (
            "```bash\nmake deploy ENV=prod\n```\n\n"
            "| 欄位 | 值 |\n|---|---|\n| a | b |\n\n"
            "表格之後才是第一段。\n"
        )
        assert _extract_reply_excerpt(body) == "表格之後才是第一段。"

    def test_html_tag_lines_are_skipped(self):
        body = "<details>\n<summary>展開</summary>\n\n真正內文。\n"
        assert _extract_reply_excerpt(body) == "真正內文。"

    def test_link_keeps_text_and_bold_markers_are_removed(self):
        body = "**commit**：`5e49184`（已 push 到 [origin/master](https://example/x)）。\n"
        assert _extract_reply_excerpt(body) == "commit：5e49184（已 push 到 origin/master）。"

    def test_identifier_underscores_are_preserved(self):
        """R4：識別字內的單一底線原樣保留；成對斜體標記才去除。"""
        body = "已改 `client_ref` 與 `_lang=zh-TW`，_重要_ 欄位 purchased_at 未動。\n"
        assert _extract_reply_excerpt(body) == (
            "已改 client_ref 與 _lang=zh-TW，重要 欄位 purchased_at 未動。"
        )

    def test_only_headings_and_blank_lines_yields_none(self):
        assert _extract_reply_excerpt("# 只有標題\n\n## 小標\n\n") is None

    def test_empty_body_yields_none(self):
        assert _extract_reply_excerpt("") is None
        assert _extract_reply_excerpt("\n\n") is None


    def test_cjk_adjacent_bold_is_removed(self):
        """review #6：漢字緊貼粗體（lookaround 不得把 CJK 當 \\w）。"""
        body = "但**尚未能鎖定最終根因**，故 status: partial。\n"
        assert _extract_reply_excerpt(body) == "但尚未能鎖定最終根因，故 status: partial。"

    def test_list_items_are_separate_paragraphs(self):
        """review #7：清單第二項為段落邊界，只取第一項，不黏連。"""
        assert _extract_reply_excerpt("1. 部署完成\n2. 測試通過\n") == "部署完成"
        assert _extract_reply_excerpt("- 前端 OK\n- 後端待補\n") == "前端 OK"

    def test_latin_hardwrap_gets_a_space(self):
        """review #5：英數字硬換行併段時插入空白；CJK 併段不插。"""
        assert _extract_reply_excerpt("Deployment is\nready\n") == "Deployment is ready"
        assert _extract_reply_excerpt("已部署\n完成\n") == "已部署完成"

    def test_ascii_sentence_terminator_only_at_boundary(self):
        """ASCII 句號僅在後接空白或行尾時視為句尾；版本號小數點不切。"""
        assert _extract_reply_excerpt("Deployed v1.30.7 to staging. Next: QA.\n") == "Deployed v1.30.7 to staging."

    def test_leading_horizontal_rule_is_skipped(self):
        """review #2：首行水平線 --- 不成為摘錄。"""
        assert _extract_reply_excerpt("---\n\n真正內文。\n") == "真正內文。"

    def test_setext_heading_is_skipped(self):
        """review #2：Setext 標題（文字＋=== 或 --- 底線）視為標題跳過。"""
        assert _extract_reply_excerpt("狀態說明\n===\n\n實作完成。\n") == "實作完成。"
        assert _extract_reply_excerpt("狀態說明\n---\n\n實作完成。\n") == "實作完成。"

    def test_mixed_fence_markers_do_not_close_each_other(self):
        """review #3：``` 圍欄內出現 ~~~ 不提前關閉。"""
        body = "```bash\nmake deploy\n~~~\necho still code\n```\n\n內文。\n"
        assert _extract_reply_excerpt(body) == "內文。"


class TestReplyExcerptInResult:
    """摘錄經索引迴圈帶進 HandoffInfo.latest_reply_excerpt；分類與既有欄位零改動。"""

    def _run(self, tmp_path, kunsu):
        return get_subrepo_status(
            subrepo_path=str(tmp_path / "subrepo"),
            our_roles={"my-role"},
            all_known_roles={"my-role"},
            kunsu_path=str(kunsu),
        )

    def test_awaiting_confirm_carries_excerpt(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            body="# 標題 — 回覆\n\n狀態：完成。\n",
        )
        result = self._run(tmp_path, kunsu)
        assert len(result.awaiting_confirm) == 1
        assert result.awaiting_confirm[0].latest_reply_excerpt == "狀態：完成。"

    def test_partial_carries_excerpt(self, tmp_path):
        """Covers AE2（資料層）：partial 件同樣帶摘錄。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="partial",
            body="程式改動已完成、Debug 建置與測試套件皆通過。\n",
        )
        result = self._run(tmp_path, kunsu)
        assert result.partial_done[0].latest_reply_excerpt == "程式改動已完成、Debug 建置與測試套件皆通過。"

    def test_no_reply_has_none_excerpt(self, tmp_path):
        """Covers AE3（資料層）：未接手件摘錄為 None。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        result = self._run(tmp_path, kunsu)
        assert result.not_picked_up[0].latest_reply_excerpt is None

    def test_reply_with_only_heading_has_none_excerpt(self, tmp_path):
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            body="# 回覆\n",
        )
        result = self._run(tmp_path, kunsu)
        assert result.awaiting_confirm[0].latest_reply_excerpt is None

    def test_latest_reply_wins_over_older(self, tmp_path):
        """Covers AE10：兩份回覆取最新一份的摘錄（依 (date, n) 數值排序）。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            body="第一份：實作完成。\n",
        )
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06-2.md",
            in_reply_to="2026-07-01-test-handoff.md",
            body="更正前一份回覆第 2 點：Circuit.vu 版本應為 3。\n",
        )
        result = self._run(tmp_path, kunsu)
        assert result.awaiting_confirm[0].latest_reply_excerpt == (
            "更正前一份回覆第 2 點：Circuit.vu 版本應為 3。"
        )

    def test_latest_unreadable_falls_back_to_older_with_its_excerpt(self, tmp_path):
        """Covers AE11：最新回覆讀取失敗（非 UTF-8）自索引消失，摘錄與 status、日期同取較舊份。"""
        kunsu, handoffs, replies = setup_kunsu(tmp_path)
        make_handoff(handoffs, "2026-07-01-test-handoff.md", to_role="my-role")
        make_reply(
            replies,
            "2026-07-01-test-handoff-reply-2026-07-06.md",
            in_reply_to="2026-07-01-test-handoff.md",
            status="submitted",
            body="狀態：完成。\n",
        )
        (replies / "2026-07-01-test-handoff-reply-2026-07-08.md").write_bytes(
            b"---\nin_reply_to: 2026-07-01-test-handoff.md\nstatus: partial\n---\n\n\xff\xfe\n"
        )
        result = self._run(tmp_path, kunsu)
        assert len(result.awaiting_confirm) == 1
        info = result.awaiting_confirm[0]
        assert info.latest_reply_date == "2026-07-06"
        assert info.latest_reply_status == "submitted"
        assert info.latest_reply_excerpt == "狀態：完成。"

    def test_excerpt_change_does_not_affect_classification_or_fields(self, tmp_path):
        """R5 差分：兩組 fixture 只差回覆正文，分類與既有 latest_reply_* 欄位逐項相等。"""
        results = []
        for idx, body in enumerate(("狀態：完成。\n", "還在等後端部署。\n")):
            kunsu, handoffs, replies = setup_kunsu(tmp_path, kunsu_name=f"kunsu{idx}")
            for n, (name, status) in enumerate((
                ("2026-07-01-a.md", "submitted"),
                ("2026-07-02-b.md", "partial"),
                ("2026-07-03-c.md", "blocked"),
            )):
                make_handoff(handoffs, name, to_role="my-role")
                make_reply(
                    replies,
                    f"{name[:-3]}-reply-2026-07-0{5 + n}.md",
                    in_reply_to=name,
                    status=status,
                    verify="needs-deploy" if status == "partial" else None,
                    body=body,
                )
            make_handoff(handoffs, "2026-07-04-d.md", to_role="my-role")
            results.append(self._run(tmp_path, kunsu))

        first, second = results
        for bucket in ("not_picked_up", "partial_done", "awaiting_confirm"):
            a = [h for h in getattr(first, bucket)]
            b = [h for h in getattr(second, bucket)]
            assert [h.filename for h in a] == [h.filename for h in b]
            for x, y in zip(a, b):
                assert (x.latest_reply_status, x.latest_reply_date, x.latest_reply_verify) == (
                    y.latest_reply_status, y.latest_reply_date, y.latest_reply_verify
                )
        assert [h.latest_reply_excerpt for h in first.awaiting_confirm] == ["狀態：完成。"]
        assert [h.latest_reply_excerpt for h in second.awaiting_confirm] == ["還在等後端部署。"]
