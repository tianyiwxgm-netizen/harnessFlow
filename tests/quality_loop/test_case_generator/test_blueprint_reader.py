"""main-1 WP03 · L2-03 blueprint_reader · TDD unit tests。

对齐 3-2 §2 正向 TC-L104-L203-001/004/012 + §3 负向 TC-L104-L203-102/103/116。
WP03 scope 裁：blueprint_reader 只做"读 WP02 blueprint → 展开 CaseSlot 序列",
不做 IC 订阅/并发/状态机(留 generator)。
"""

from __future__ import annotations

import pytest

from app.quality_loop.test_case_generator.blueprint_reader import BlueprintReader
from app.quality_loop.test_case_generator.schemas import (
    AC_COVERAGE_NOT_100,
    AC_MATRIX_INVALID,
    CaseSlot,
    TestCaseGeneratorError,
)
from app.quality_loop.tdd_blueprint.schemas import (
    ACItem,
    ACMatrix,
    ACMatrixRow,
    BlueprintState,
    CoverageTarget,
    SourceRefs,
    TDDBlueprint,
    TestEnvBlueprint,
    TestPyramid,
)


class TestBlueprintReaderPositive:
    """§2 正向 · reader 能读出合法蓝图的 slot 矩阵。"""

    def test_TC_L104_L203_001_reads_published_blueprint_emits_slots(self, tiny_blueprint: TDDBlueprint) -> None:
        """TC-L104-L203-001 · blueprint PUBLISHED + 3 AC × unit=1 → 至少 3 slot。"""
        reader = BlueprintReader()
        slots = reader.read(tiny_blueprint)
        assert len(slots) >= 3
        assert all(isinstance(s, CaseSlot) for s in slots)

    def test_TC_L104_L203_004_slot_count_matches_ac_matrix_row_sum(self, make_blueprint) -> None:
        """TC-L104-L203-004 · slot 数 == sum(unit+integration+e2e slots)。"""
        bp = make_blueprint(
            ac_rows=[
                ("AC-001", 2, 1, 0, "P1", "unit"),
                ("AC-002", 1, 1, 1, "P0", "unit"),
            ]
        )
        reader = BlueprintReader()
        slots = reader.read(bp)
        # 2+1+0 + 1+1+1 = 6
        assert len(slots) == 6

    def test_TC_L104_L203_004b_each_slot_has_ac_layer_seq(self, tiny_blueprint: TDDBlueprint) -> None:
        """TC-L104-L203-004b · 每个 slot 含 ac_id + layer + seq · slot_id 稳定去重。"""
        reader = BlueprintReader()
        slots = reader.read(tiny_blueprint)
        slot_ids = {s.slot_id for s in slots}
        assert len(slot_ids) == len(slots), "slot_id 必须唯一"
        for s in slots:
            assert s.ac_id.startswith("AC-")
            assert s.layer in ("unit", "integration", "e2e")
            assert s.seq >= 1

    def test_TC_L104_L203_012_slots_carry_priority_from_ac_matrix(self, make_blueprint) -> None:
        """TC-L104-L203-012 · slot.priority 来自 ACMatrixRow.priority。"""
        bp = make_blueprint(
            ac_rows=[
                ("AC-001", 1, 0, 0, "P0", "unit"),
                ("AC-002", 1, 0, 0, "P2", "unit"),
            ]
        )
        reader = BlueprintReader()
        slots = reader.read(bp)
        by_ac = {s.ac_id: s for s in slots}
        assert by_ac["AC-001"].priority == "P0"
        assert by_ac["AC-002"].priority == "P2"

    def test_TC_L104_L203_012b_unit_integration_e2e_layers_all_expanded(
        self,
        make_blueprint,
    ) -> None:
        """TC-L104-L203-012b · 3 层在同一 AC 下都展开成独立 slot。"""
        bp = make_blueprint(ac_rows=[("AC-001", 1, 1, 1, "P0", "unit")])
        reader = BlueprintReader()
        slots = reader.read(bp)
        layers = sorted(s.layer for s in slots)
        assert layers == ["e2e", "integration", "unit"]


class TestBlueprintReaderNegative:
    """§3 负向 · 错误码硬映射。"""

    def test_TC_L104_L203_102_none_blueprint_raises_ac_matrix_invalid(self) -> None:
        """TC-L104-L203-102 · bp 为 None → AC_MATRIX_INVALID。"""
        reader = BlueprintReader()
        with pytest.raises(TestCaseGeneratorError) as ei:
            reader.read(None)  # type: ignore[arg-type]
        assert ei.value.code == AC_MATRIX_INVALID

    def test_TC_L104_L203_102b_empty_ac_matrix_raises_ac_matrix_invalid(
        self,
        make_blueprint,
    ) -> None:
        """TC-L104-L203-102b · ACMatrix.rows 空 → AC_MATRIX_INVALID。"""
        empty_bp = TDDBlueprint(
            blueprint_id="bp-empty",
            project_id="pid-wp03",
            version=1,
            state=BlueprintState.PUBLISHED,
            test_pyramid=TestPyramid(0.7, 0.2, 0.1),
            ac_matrix=ACMatrix(rows={}),
            coverage_target=CoverageTarget(),
            test_env=TestEnvBlueprint(),
            source_refs=SourceRefs(
                four_pieces_hash="sha256:" + "0" * 64,
                wbs_version=1,
                ac_clauses_hash="sha256:" + "0" * 64,
            ),
            ac_items=[],
            created_at="2026-04-23T00:00:00Z",
        )
        reader = BlueprintReader()
        with pytest.raises(TestCaseGeneratorError) as ei:
            reader.read(empty_bp)
        assert ei.value.code == AC_MATRIX_INVALID

    def test_TC_L104_L203_103_ac_with_zero_slots_raises_coverage_not_100(
        self,
        make_blueprint,
    ) -> None:
        """TC-L104-L203-103 · 某 AC 三层 slot 都 0 → AC_COVERAGE_NOT_100 · CRITICAL。"""
        bp = make_blueprint(
            ac_rows=[
                ("AC-001", 1, 0, 0, "P1", "unit"),
                ("AC-999", 0, 0, 0, "P2", "unit"),  # 0 slot
            ]
        )
        reader = BlueprintReader()
        with pytest.raises(TestCaseGeneratorError) as ei:
            reader.read(bp)
        assert ei.value.code == AC_COVERAGE_NOT_100
        assert "AC-999" in str(ei.value) or "AC-999" in repr(ei.value.context)
