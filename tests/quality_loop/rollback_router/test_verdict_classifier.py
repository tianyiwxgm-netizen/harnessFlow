"""TC-L104-L207 · verdict_classifier · verdict → 4 级 severity 映射。

核心 TC：
- 4 级分级正确映射 verdict（FAIL_L1→WARN · FAIL_L2/L3→FAIL · FAIL_L4→CRITICAL）
- INFO_SUGG 级由外部注入（不走 IC-14）· classifier 不在此产
"""
from __future__ import annotations

import pytest

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    RollbackSeverity,
    RollbackVerdict,
)
from app.quality_loop.rollback_router.verdict_classifier import (
    VerdictClassifier,
    classify_verdict,
)


class TestClassifyVerdict:
    """纯函数 · classifier 主映射表。"""

    def test_fail_l1_maps_to_warn(self) -> None:
        """TC-L104-L207-classifier-01 · FAIL_L1 (L2 WARN)  · stage 内 retry。"""
        assert classify_verdict(FailVerdict.FAIL_L1) == RollbackSeverity.WARN

    def test_fail_l2_maps_to_fail(self) -> None:
        """TC-L104-L207-classifier-02 · FAIL_L2 (L3 FAIL) · 回上一 stage。"""
        assert classify_verdict(FailVerdict.FAIL_L2) == RollbackSeverity.FAIL

    def test_fail_l3_maps_to_fail(self) -> None:
        """TC-L104-L207-classifier-03 · FAIL_L3 (L3 FAIL) · 回上一 stage。"""
        assert classify_verdict(FailVerdict.FAIL_L3) == RollbackSeverity.FAIL

    def test_fail_l4_maps_to_critical(self) -> None:
        """TC-L104-L207-classifier-04 · FAIL_L4 (L4 CRITICAL) · 深度回退 UPGRADE。"""
        assert classify_verdict(FailVerdict.FAIL_L4) == RollbackSeverity.CRITICAL


class TestVerdictClassifier:
    """类版本 · 可注入 + 带 project_id/wp_id 包装 RollbackVerdict 输出。"""

    def test_classifier_wraps_into_rollback_verdict(self) -> None:
        c = VerdictClassifier()
        rv = c.classify(
            verdict=FailVerdict.FAIL_L2,
            wp_id="wp-1",
            project_id="p1",
            level_count=2,
        )
        assert isinstance(rv, RollbackVerdict)
        assert rv.severity == RollbackSeverity.FAIL
        assert rv.verdict == FailVerdict.FAIL_L2
        assert rv.level_count == 2

    def test_classifier_empty_wp_id_rejected(self) -> None:
        """wp_id 为空字符串 · Pydantic 层拒绝。"""
        c = VerdictClassifier()
        with pytest.raises(Exception):  # ValidationError
            c.classify(
                verdict=FailVerdict.FAIL_L1, wp_id="", project_id="p1", level_count=1,
            )

    def test_classifier_all_four_levels_round_trip(self) -> None:
        """4 级均能产出合法 RollbackVerdict。"""
        c = VerdictClassifier()
        expected = {
            FailVerdict.FAIL_L1: RollbackSeverity.WARN,
            FailVerdict.FAIL_L2: RollbackSeverity.FAIL,
            FailVerdict.FAIL_L3: RollbackSeverity.FAIL,
            FailVerdict.FAIL_L4: RollbackSeverity.CRITICAL,
        }
        for verdict, sev in expected.items():
            rv = c.classify(
                verdict=verdict, wp_id="wp-x", project_id="p-x", level_count=1,
            )
            assert rv.severity == sev, f"{verdict} → {sev} 映射错"
