"""单元测试 · requirement_parser + coverage_planner + dod_adapter · 覆盖细节纯函数。

这些是 WP02 的 "coverage booster"，目标 ≥ 85%。
"""

from __future__ import annotations

import pytest

from app.quality_loop.tdd_blueprint import schemas as S
from app.quality_loop.tdd_blueprint.coverage_planner import (
    _kind_weight,
    _shrink_to_cap,
    assemble_test_env,
    build_coverage_target,
    build_matrix,
    compute_coverage,
    derive_pyramid,
    priority_annotation_complete,
)
from app.quality_loop.tdd_blueprint.dod_adapter import MockDoDAdapter
from app.quality_loop.tdd_blueprint.requirement_parser import (
    ac_clauses_hash,
    parse_ac_clauses,
    split_ac_candidates,
    synth_clauses_for_count,
)


class TestRequirementParser:
    def test_split_empty(self) -> None:
        assert split_ac_candidates("") == []
        assert split_ac_candidates("   \n\n   ") == []

    def test_split_numbered(self) -> None:
        txt = "1. 必须 A\n2. 禁止 B\n\n- 第三条"
        items = split_ac_candidates(txt)
        assert items == ["必须 A", "禁止 B", "第三条"]

    def test_parse_gherkin(self) -> None:
        r = parse_ac_clauses(["Given x When y Then z"])
        assert r.ok
        assert r.parsed[0].structured["template"] == "gherkin"
        assert r.parsed[0].parse_tier == 1

    def test_parse_must_forbid(self) -> None:
        r = parse_ac_clauses(["必须 保存数据", "禁止 跨越边界"])
        tmpls = [p.structured["template"] for p in r.parsed]
        assert "must" in tmpls
        assert "forbid" in tmpls

    def test_parse_unstructured_fallback(self) -> None:
        r = parse_ac_clauses(["普通陈述句没有关键词"], allow_unstructured_fallback=True)
        assert r.ok
        assert r.parsed[0].structured["template"] == "fallback_raw"
        assert r.parsed[0].confidence == 0.3

    def test_parse_strict_rejects_unstructured(self) -> None:
        r = parse_ac_clauses(
            ["无关键字陈述"], allow_unstructured_fallback=False
        )
        assert not r.ok
        assert r.failed_ac_ids == ["AC-001"]

    def test_parse_empty_string_fails(self) -> None:
        r = parse_ac_clauses(["", "   "], allow_unstructured_fallback=True)
        # 两个空串都 failed（空/空白字符直接拒）
        assert r.failed_ac_ids == ["AC-001", "AC-002"]

    def test_synth_stable(self) -> None:
        a = synth_clauses_for_count(4)
        b = synth_clauses_for_count(4)
        assert a == b
        assert synth_clauses_for_count(0) == []

    def test_ac_clauses_hash_stable(self) -> None:
        h1 = ac_clauses_hash(["a", "b"])
        h2 = ac_clauses_hash(["a", "b"])
        assert h1 == h2
        assert h1.startswith("sha256:")
        assert ac_clauses_hash(["a", "b"]) != ac_clauses_hash(["a", "c"])


class TestCoveragePlanner:
    def _items(self, n: int = 10) -> list[S.ACItem]:
        kinds = ["data", "collab", "ui", "mixed"]
        return [
            S.ACItem(id=f"AC-{i+1:03d}", raw_text=f"raw{i}", kind=kinds[i % 4])
            for i in range(n)
        ]

    def test_derive_pyramid_defaults(self) -> None:
        items = [S.ACItem(id="AC-001", raw_text="x", kind="mixed")]
        p = derive_pyramid(items)
        assert abs(p.unit_ratio + p.integration_ratio + p.e2e_ratio - 1.0) < 0.01

    def test_derive_pyramid_skewed_by_kind(self) -> None:
        ui_only = [S.ACItem(id=f"AC-{i:03d}", raw_text="x", kind="ui") for i in range(20)]
        p = derive_pyramid(ui_only)
        # UI 主导 · e2e_ratio 应比默认 0.1 更高
        data_only = [S.ACItem(id=f"AC-{i:03d}", raw_text="x", kind="data") for i in range(20)]
        p2 = derive_pyramid(data_only)
        assert p.e2e_ratio > p2.e2e_ratio

    def test_build_matrix_unit_ge_1(self) -> None:
        items = self._items(5)
        p = derive_pyramid(items)
        matrix, meta = build_matrix(items, p)
        assert all(r.unit_slots >= 1 for r in matrix.rows.values())
        assert meta["total_slots"] > 0

    def test_build_matrix_forced_unmapped(self) -> None:
        items = self._items(3)
        p = derive_pyramid(items)
        matrix, meta = build_matrix(items, p, forced_unmapped_ac_ids=["AC-001"])
        assert matrix.rows["AC-001"].total_slots() == 0
        assert matrix.rows["AC-002"].total_slots() > 0

    def test_build_matrix_case_explosion_warns(self) -> None:
        items = self._items(5)
        p = derive_pyramid(items)
        matrix, meta = build_matrix(items, p, case_explosion_ac_index=0)
        codes = [w["code"] for w in meta["warnings"]]
        assert "E_L204_L201_AC_CASE_EXPLOSION" in codes

    def test_build_matrix_total_cap_clamps(self) -> None:
        items = self._items(50)
        p = derive_pyramid(items)
        matrix, meta = build_matrix(items, p, total_cap=30)
        # total_cap=30 触发后 · 剩余 AC 降到 (1,0,0) · 每个 AC 至少 1 unit slot 保底
        assert matrix.total_slots() >= 50  # 每 AC ≥ 1 unit
        # 大部分 AC 被截到 unit-only
        unit_only = sum(
            1 for r in matrix.rows.values()
            if r.unit_slots == 1 and r.integration_slots == 0 and r.e2e_slots == 0
        )
        assert unit_only >= 10

    def test_shrink_to_cap(self) -> None:
        assert _shrink_to_cap(3, 3, 3, cap=5) == (1, 3, 1) or _shrink_to_cap(3, 3, 3, cap=5)[0] >= 1
        u, i, e = _shrink_to_cap(10, 10, 10, cap=3)
        assert u + i + e <= 3 and u >= 1

    def test_kind_weight(self) -> None:
        assert _kind_weight("data", "unit") > _kind_weight("data", "e2e")
        assert _kind_weight("ui", "e2e") > _kind_weight("ui", "unit")
        assert _kind_weight("mixed", "unit") == 1.0
        assert _kind_weight("unknown", "unit") == 1.0

    def test_compute_coverage_full(self) -> None:
        items = self._items(4)
        p = derive_pyramid(items)
        matrix, _ = build_matrix(items, p)
        cov = compute_coverage(matrix, items)
        assert cov.ac_coverage == 1.0
        assert cov.missing_ac_ids == []

    def test_compute_coverage_missing(self) -> None:
        items = self._items(4)
        p = derive_pyramid(items)
        matrix, _ = build_matrix(items, p, forced_unmapped_ac_ids=["AC-001"])
        cov = compute_coverage(matrix, items)
        assert cov.ac_coverage < 1.0
        assert "AC-001" in cov.missing_ac_ids

    def test_compute_coverage_empty(self) -> None:
        cov = compute_coverage(S.ACMatrix(rows={}), [])
        assert cov.ac_coverage == 0.0

    def test_build_coverage_target_defaults(self) -> None:
        t = build_coverage_target()
        assert t.ac == 1.0
        assert 0.60 <= t.line <= 1.0
        assert 0.60 <= t.branch <= 1.0

    def test_build_coverage_target_overrides(self) -> None:
        t = build_coverage_target({"line_coverage": 0.85, "branch_coverage": 0.75})
        assert t.line == 0.85
        assert t.branch == 0.75
        # ac 无论如何都锁死
        t2 = build_coverage_target({"ac_coverage": 0.5})
        assert t2.ac == 1.0

    def test_coverage_target_out_of_range_raises(self) -> None:
        with pytest.raises(S.TDDBlueprintError) as ei:
            S.CoverageTarget(line=0.5, branch=0.7, ac=1.0)
        assert ei.value.code == "E_L204_L201_COVERAGE_OUT_OF_RANGE"

    def test_assemble_test_env(self) -> None:
        items = self._items(4)
        p = derive_pyramid(items)
        matrix, _ = build_matrix(items, p)
        env = assemble_test_env(items, matrix, project_id="pid-t")
        assert env.isolation_prefix == "proj-pid-t"
        assert env.mock_profiles
        assert "normal" in env.fixtures

    def test_priority_annotation_complete(self) -> None:
        items = self._items(3)
        p = derive_pyramid(items)
        matrix, _ = build_matrix(items, p)
        assert priority_annotation_complete(matrix) is True


class TestSchemas:
    def test_test_pyramid_sum_invalid(self) -> None:
        with pytest.raises(S.TDDBlueprintError) as ei:
            S.TestPyramid(0.1, 0.1, 0.1)
        assert ei.value.code == "E_L204_L201_PYRAMID_RATIO_SUM_INVALID"

    def test_coverage_target_ac_not_locked(self) -> None:
        with pytest.raises(S.TDDBlueprintError) as ei:
            S.CoverageTarget(line=0.8, branch=0.7, ac=0.99)
        assert ei.value.code == "E_L204_L201_COVERAGE_AC_NOT_LOCKED"

    def test_ac_matrix_missing(self) -> None:
        rows = {
            "AC-001": S.ACMatrixRow(ac_id="AC-001", unit_slots=0),
            "AC-002": S.ACMatrixRow(ac_id="AC-002", unit_slots=1),
        }
        m = S.ACMatrix(rows=rows)
        assert m.missing_ac_ids() == ["AC-001"]
        assert m.total_slots() == 1

    def test_ac_matrix_row_slot_ids(self) -> None:
        row = S.ACMatrixRow(
            ac_id="AC-001", unit_slots=2, integration_slots=1, e2e_slots=1
        )
        ids = row.slot_ids()
        assert ids == [
            "slot-AC-001-u1", "slot-AC-001-u2",
            "slot-AC-001-i1", "slot-AC-001-e1",
        ]

    def test_source_refs_hash_stable(self) -> None:
        h1 = S._compute_source_refs_hash(
            four_pieces_hash="fh", wbs_version=1,
            ac_clauses_hash="ah", clause_count=5,
            config_overrides=None,
        )
        h2 = S._compute_source_refs_hash(
            four_pieces_hash="fh", wbs_version=1,
            ac_clauses_hash="ah", clause_count=5,
            config_overrides=None,
        )
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_blueprint_assert_invariants_project_id(self) -> None:
        items = [S.ACItem(id="AC-001", raw_text="x", kind="mixed")]
        matrix = S.ACMatrix(
            rows={"AC-001": S.ACMatrixRow(ac_id="AC-001", unit_slots=1)}
        )
        bp = S.TDDBlueprint(
            blueprint_id="bp-1", project_id="",
            version=1, state=S.BlueprintState.DRAFT,
            test_pyramid=S.TestPyramid(0.7, 0.2, 0.1),
            ac_matrix=matrix,
            coverage_target=S.CoverageTarget(),
            test_env=S.TestEnvBlueprint(),
            source_refs=S.SourceRefs("fh", 1, "ah"),
            ac_items=items,
            created_at="2026-04-22T00:00:00Z",
        )
        with pytest.raises(S.TDDBlueprintError) as ei:
            bp.assert_invariants()
        assert ei.value.code == "E_L204_L201_BLUEPRINT_NO_PROJECT_ID"


class TestMockDoDAdapter:
    def test_compile_idempotent(self) -> None:
        a = MockDoDAdapter()
        c1 = a.compile_expression("project_exists and state_audited")
        c2 = a.compile_expression("project_exists and state_audited")
        assert c1.ast_hash == c2.ast_hash
        assert a.compute_dod_hash(c1) == c1.ast_hash

    def test_whitelist_rejects_exec(self) -> None:
        a = MockDoDAdapter()
        c = a.compile_expression("exec('boom')")
        assert c.whitelisted is False

    def test_whitelist_rejects_import(self) -> None:
        a = MockDoDAdapter()
        c = a.compile_expression("import os")
        assert c.whitelisted is False

    def test_whitelist_rejects_dunder(self) -> None:
        a = MockDoDAdapter()
        c = a.compile_expression("obj.__class__")
        assert c.whitelisted is False

    def test_whitelist_accepts_normal(self) -> None:
        a = MockDoDAdapter()
        c = a.compile_expression("hard_pass_rate >= 0.95")
        assert c.whitelisted is True
