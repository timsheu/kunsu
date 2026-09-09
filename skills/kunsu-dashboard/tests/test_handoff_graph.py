"""
test_handoff_graph.py — skills/kunsu-dashboard/app/handoff_graph.py 的單元測試

覆蓋計畫 U2 的 test scenarios（docs/plans/2026-09-08-001-feat-handoff-dependency-dag-plan.md）：
  - Covers AE1. B 依賴 archive 內 done 的 A → B ready
  - Covers AE2. B 依賴頂層 open 的 A → B waiting，waiting_on[B] == [A]
  - 中間態：頂層 A 已 Edit 為 done 未 mv → B ready
  - archive 內 A 為 open → B waiting，anomalies 含 archived_not_done
  - Covers AE4. A↔B 循環 → cycles 含兩檔名；A、B 皆 waiting；環外 C 仍 ready
  - Covers AE5. B 依賴不存在檔名 → unresolved not_found，B waiting，其餘依賴照常
  - 指向回覆檔名 → reason reply_file
  - 自迴圈 → 邊不入推導，cycles 含單元素
  - 重複去重、純量容錯、非字串元素 bad_type
  - Covers AE6. 全部節點無 depends_on → derived／edges 為空
  - 33 份孤立 open 本體＋一條邊 → active_nodes 僅含邊兩端
  - 頂層與 archive 同名 → 取頂層，anomalies 含 duplicate
  - frontmatter 縮排寫壞 → errors 一筆，其餘照常；B 依賴壞檔 → B waiting、unresolved 不含
  - docs/handoffs/ 不存在 → 空結果
  - Covers AE7. 更正交接 Y 帶 depends_on: [C]、B 帶 corrected_by: Y → B 的邊不變
  - corrected_by 兩元素 block 列表 → tuple 兩元素、無錯誤
"""

from pathlib import Path

from app.handoff_graph import (
    ANOMALY_ARCHIVED_NOT_DONE,
    ANOMALY_DUPLICATE,
    DERIVED_READY,
    DERIVED_WAITING,
    STATUS_UNKNOWN,
    UNRESOLVED_BAD_TYPE,
    UNRESOLVED_NOT_FOUND,
    UNRESOLVED_REPLY_FILE,
    get_handoff_graph,
)


# ── 輔助 ────────────────────────────────────────────────────────────────────────

def setup_kunsu(tmp_path: Path) -> tuple[Path, Path, Path]:
    kunsu = tmp_path / "kunsu"
    handoffs = kunsu / "docs" / "handoffs"
    archive = handoffs / "archive"
    archive.mkdir(parents=True)
    (handoffs / "replies").mkdir()
    return kunsu, handoffs, archive


def make_handoff(
    directory: Path,
    filename: str,
    *,
    status: str = "open",
    depends_on: str | None = None,
    corrected_by: str | None = None,
    to_role: str = "backend",
) -> Path:
    """depends_on／corrected_by 以原始 YAML 片段傳入（含 flow／block 兩形）。"""
    lines = [
        "---",
        f"title: {Path(filename).stem}",
        "type: handoff",
        f"status: {status}",
        "from: kunsu",
        f"to: {to_role}",
        "created: 2026-09-01",
        "tags: [handoff]",
    ]
    if depends_on is not None:
        lines.append(f"depends_on: {depends_on}")
    if corrected_by is not None:
        lines.append(f"corrected_by: {corrected_by}")
    lines += ["---", "", f"# {Path(filename).stem}", "", "內文。", ""]
    path = directory / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


A, B, C, Y = "2026-09-01-a.md", "2026-09-02-b.md", "2026-09-03-c.md", "2026-09-04-y.md"


# ── 推導 ────────────────────────────────────────────────────────────────────────

class TestDerivation:
    def test_ae1_dependency_done_in_archive_is_ready(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="done")
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.derived[B] == DERIVED_READY
        assert r.edges == [(B, A)]
        assert B not in r.waiting_on
        assert r.active_nodes == frozenset({B})

    def test_ae2_dependency_open_on_top_is_waiting(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, A)
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.derived[B] == DERIVED_WAITING
        assert r.waiting_on[B] == [A]
        assert A in r.active_nodes and B in r.active_nodes
        # A 有入邊、無出邊 → ready（可開工）
        assert r.derived[A] == DERIVED_READY

    def test_top_level_done_intermediate_state_is_satisfied(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, A, status="done")
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.derived[B] == DERIVED_READY
        assert A not in r.derived and A not in r.active_nodes
        assert r.anomalies == []

    def test_archived_but_open_is_anomaly_and_not_satisfied(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="open")
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.derived[B] == DERIVED_WAITING
        assert any(a.filename == A and a.kind == ANOMALY_ARCHIVED_NOT_DONE for a in r.anomalies)

    def test_ae4_cycle_marks_both_waiting_and_leaves_outside_node_ready(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(top, A, depends_on=f"[{B}]")
        make_handoff(top, B, depends_on=f"[{A}]")
        make_handoff(archive, "2026-08-01-done.md", status="done")
        make_handoff(top, C, depends_on="[2026-08-01-done.md]")
        r = get_handoff_graph(str(kunsu))
        assert r.cycles == [[A, B]]
        assert r.derived[A] == DERIVED_WAITING and r.derived[B] == DERIVED_WAITING
        assert r.derived[C] == DERIVED_READY

    def test_ae5_missing_target_is_unresolved_and_others_still_count(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="done")
        make_handoff(top, B, depends_on=f"[{A}, 2026-01-01-nope.md]")
        r = get_handoff_graph(str(kunsu))
        assert r.unresolved == [type(r.unresolved[0])(B, "2026-01-01-nope.md", UNRESOLVED_NOT_FOUND)]
        assert r.derived[B] == DERIVED_WAITING
        assert r.waiting_on[B] == ["2026-01-01-nope.md"]
        assert (B, A) in r.edges

    def test_reply_filename_target_has_specific_reason(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, B, depends_on=f"[{A[:-3]}-reply-2026-09-02.md]")
        r = get_handoff_graph(str(kunsu))
        assert r.unresolved[0].reason == UNRESOLVED_REPLY_FILE
        assert r.derived[B] == DERIVED_WAITING

    def test_self_loop_ignored_in_derivation_but_reported_as_cycle(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, A, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.edges == []
        assert r.cycles == [[A]]
        assert A not in r.derived  # 無其他邊 → 孤立，不入推導

    def test_duplicates_scalars_and_bad_types(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="done")
        make_handoff(top, B, depends_on=f"[{A}, {A}]")
        make_handoff(top, C, depends_on=A)  # 純量
        make_handoff(top, Y, depends_on=f"[{A}, 42, {{x: 1}}]")
        r = get_handoff_graph(str(kunsu))
        assert r.edges.count((B, A)) == 1
        assert r.nodes[C].depends_on == (A,)
        assert r.derived[C] == DERIVED_READY
        bad = [u for u in r.unresolved if u.source == Y and u.reason == UNRESOLVED_BAD_TYPE]
        assert len(bad) == 1 and bad[0].target == "{'x': 1}"
        assert r.nodes[Y].depends_on == (A, "42")  # 數值元素 str() 後成無法解析的 not_found
        assert any(u.source == Y and u.target == "42" and u.reason == UNRESOLVED_NOT_FOUND for u in r.unresolved)


# ── 邊界 ────────────────────────────────────────────────────────────────────────

class TestBoundaries:
    def test_ae6_no_depends_on_anywhere_yields_empty_graph(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        for i in range(5):
            make_handoff(top, f"2026-09-0{i + 1}-x{i}.md")
        make_handoff(archive, A, status="done")
        r = get_handoff_graph(str(kunsu))
        assert r.derived == {} and r.edges == [] and r.active_nodes == frozenset()
        assert not r.has_edges and not r.has_issues
        assert len(r.nodes) == 6

    def test_isolated_open_bodies_do_not_count_as_active(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        for i in range(33):
            make_handoff(top, f"2026-08-{i + 1:02d}-iso{i}.md")
        make_handoff(top, A)
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.active_nodes == frozenset({A, B})
        assert set(r.derived) == {A, B}

    def test_duplicate_top_and_archive_takes_top(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="done")
        make_handoff(top, A, status="open")
        make_handoff(top, B, depends_on=f"[{A}]")
        r = get_handoff_graph(str(kunsu))
        assert r.nodes[A].location == "top"
        assert any(a.filename == A and a.kind == ANOMALY_DUPLICATE for a in r.anomalies)
        assert r.derived[B] == DERIVED_WAITING

    def test_broken_frontmatter_is_error_and_dependents_wait(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        (top / A).write_text("---\ntitle: a\n  bad: [\n---\n# a\n", encoding="utf-8")
        make_handoff(archive, C, status="done")
        make_handoff(top, B, depends_on=f"[{A}, {C}]")
        r = get_handoff_graph(str(kunsu))
        assert [e.filename for e in r.errors] == [A]
        assert r.nodes[A].status == STATUS_UNKNOWN
        assert r.derived[B] == DERIVED_WAITING
        assert r.waiting_on[B] == [A]
        assert r.unresolved == []

    def test_missing_required_field_is_error(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        (top / A).write_text("---\ntitle: a\nstatus: open\n---\n# a\n", encoding="utf-8")
        r = get_handoff_graph(str(kunsu))
        assert r.errors and "from" in r.errors[0].error and "to" in r.errors[0].error

    def test_missing_directory_returns_empty(self, tmp_path):
        r = get_handoff_graph(str(tmp_path / "nowhere"))
        assert r.nodes == {} and r.errors == []

    def test_reply_file_misplaced_in_top_is_not_a_node(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, A)
        (top / f"{A[:-3]}-reply-2026-09-02.md").write_text("---\nin_reply_to: x\n---\n", encoding="utf-8")
        r = get_handoff_graph(str(kunsu))
        assert set(r.nodes) == {A}


# ── 更正交接與 corrected_by ────────────────────────────────────────────────────

class TestCorrection:
    def test_ae7_correction_is_plain_node_and_original_edges_unchanged(self, tmp_path):
        kunsu, top, archive = setup_kunsu(tmp_path)
        make_handoff(archive, A, status="done")
        make_handoff(top, C)
        make_handoff(top, B, depends_on=f"[{A}]", corrected_by=Y)
        make_handoff(top, Y, depends_on=f"[{C}]")
        r = get_handoff_graph(str(kunsu))
        assert r.nodes[B].depends_on == (A,)
        assert r.nodes[B].corrected_by == (Y,)
        assert r.derived[B] == DERIVED_READY   # B 的邊不受 Y 影響
        assert r.derived[Y] == DERIVED_WAITING

    def test_corrected_by_block_list_two_elements(self, tmp_path):
        kunsu, top, _ = setup_kunsu(tmp_path)
        make_handoff(top, A)
        make_handoff(top, B, depends_on=f"[{A}]", corrected_by=f"\n  - {Y}\n  - {C}")
        r = get_handoff_graph(str(kunsu))
        assert r.nodes[B].corrected_by == (Y, C)
        assert r.errors == []
