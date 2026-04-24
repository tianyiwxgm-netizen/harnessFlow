"""TC-L104-L207 · stage_mapper · severity+verdict → target_stage · RouteDecision。

核心 TC（对齐 Dev-ζ rollback_pusher.py `_LEGAL_MAPPING`）：

| 常规映射                    |
|:----------------------------|
| FAIL_L1 → S3  (retry_s3)    |
| FAIL_L2 → S4  (retry_s4)    |
| FAIL_L3 → S5  (retry_s5)    |
| FAIL_L4 → UPGRADE_TO_L1_01  |

同级 >= 3 升级：任何 verdict → UPGRADE_TO_L1_01（override）。
"""
from __future__ import annotations

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    RollbackSeverity,
    RollbackVerdict,
    TargetStage,
)
from app.quality_loop.rollback_router.stage_mapper import StageMapper


def _mk_rv(verdict: FailVerdict, level_count: int = 1,
           severity: RollbackSeverity | None = None) -> RollbackVerdict:
    """Helper · 构造 RollbackVerdict."""
    from app.quality_loop.rollback_router.verdict_classifier import classify_verdict
    return RollbackVerdict(
        verdict=verdict,
        severity=severity or classify_verdict(verdict),
        wp_id="wp-1", project_id="p1", level_count=level_count,
    )


class TestStageMapperNormal:
    """常规路径 · 同级 < 3 · 按 4 级 verdict → 4 stage 双射。"""

    def test_fail_l1_routes_to_s3_retry_s3(self) -> None:
        """TC-L104-L207-mapper-01 · FAIL_L1 (WARN) · stage 内 retry → S3。"""
        mapper = StageMapper()
        dec = mapper.decide(rv=_mk_rv(FailVerdict.FAIL_L1), route_id="route-001")
        assert dec.target_stage == TargetStage.S3
        assert dec.new_wp_state == NewWpState.RETRY_S3
        assert dec.escalated is False
        assert dec.severity == RollbackSeverity.WARN

    def test_fail_l2_routes_to_s4_retry_s4(self) -> None:
        """TC-L104-L207-mapper-02 · FAIL_L2 (FAIL) · 回上一 stage → S4。"""
        mapper = StageMapper()
        dec = mapper.decide(rv=_mk_rv(FailVerdict.FAIL_L2), route_id="route-002")
        assert dec.target_stage == TargetStage.S4
        assert dec.new_wp_state == NewWpState.RETRY_S4
        assert dec.escalated is False

    def test_fail_l3_routes_to_s5_retry_s5(self) -> None:
        """TC-L104-L207-mapper-03 · FAIL_L3 (FAIL) · 回上一 stage → S5。"""
        mapper = StageMapper()
        dec = mapper.decide(rv=_mk_rv(FailVerdict.FAIL_L3), route_id="route-003")
        assert dec.target_stage == TargetStage.S5
        assert dec.new_wp_state == NewWpState.RETRY_S5

    def test_fail_l4_routes_to_upgrade(self) -> None:
        """TC-L104-L207-mapper-04 · FAIL_L4 (CRITICAL) · 深度回退 UPGRADE_TO_L1_01。"""
        mapper = StageMapper()
        dec = mapper.decide(rv=_mk_rv(FailVerdict.FAIL_L4), route_id="route-004")
        assert dec.target_stage == TargetStage.UPGRADE_TO_L1_01
        assert dec.new_wp_state == NewWpState.UPGRADED_TO_L1_01
        assert dec.severity == RollbackSeverity.CRITICAL
        # FAIL_L4 本身是升级语义 · 非 "同级 >= 3" · escalated=False
        assert dec.escalated is False


class TestStageMapperEscalation:
    """同级连续 ≥ 3 升级 · 任何 verdict override → UPGRADE_TO_L1_01。"""

    def test_fail_l1_escalates_at_level_count_3(self) -> None:
        """TC-L104-L207-mapper-esc-01 · FAIL_L1 连 3 次 → UPGRADE · escalated=True。"""
        mapper = StageMapper()
        dec = mapper.decide(
            rv=_mk_rv(FailVerdict.FAIL_L1, level_count=3),
            route_id="route-esc-1",
        )
        assert dec.target_stage == TargetStage.UPGRADE_TO_L1_01
        assert dec.new_wp_state == NewWpState.UPGRADED_TO_L1_01
        assert dec.escalated is True

    def test_fail_l2_escalates_at_level_count_5(self) -> None:
        """TC-L104-L207-mapper-esc-02 · FAIL_L2 连 5 次 → UPGRADE · escalated=True。"""
        mapper = StageMapper()
        dec = mapper.decide(
            rv=_mk_rv(FailVerdict.FAIL_L2, level_count=5),
            route_id="route-esc-2",
        )
        assert dec.target_stage == TargetStage.UPGRADE_TO_L1_01
        assert dec.escalated is True

    def test_fail_l3_escalates_at_level_count_3(self) -> None:
        """TC-L104-L207-mapper-esc-03 · FAIL_L3 连 3 次 → UPGRADE。"""
        mapper = StageMapper()
        dec = mapper.decide(
            rv=_mk_rv(FailVerdict.FAIL_L3, level_count=3),
            route_id="route-esc-3",
        )
        assert dec.target_stage == TargetStage.UPGRADE_TO_L1_01
        assert dec.escalated is True

    def test_level_count_2_not_escalated(self) -> None:
        """TC-L104-L207-mapper-esc-04 · 连 2 次 · 未到阈值 · 不升级。"""
        mapper = StageMapper()
        dec = mapper.decide(
            rv=_mk_rv(FailVerdict.FAIL_L1, level_count=2),
            route_id="route-no-esc",
        )
        assert dec.escalated is False
        assert dec.target_stage == TargetStage.S3


class TestStageMapperLegalityVsDevZeta:
    """对齐 Dev-ζ `rollback_pusher._LEGAL_MAPPING` · 任何 decide 产出必然在合法集合内。"""

    def test_all_four_verdicts_legal_normal(self) -> None:
        from app.supervisor.event_sender.rollback_pusher import _LEGAL_MAPPING
        mapper = StageMapper()
        for verdict in (FailVerdict.FAIL_L1, FailVerdict.FAIL_L2,
                        FailVerdict.FAIL_L3, FailVerdict.FAIL_L4):
            dec = mapper.decide(rv=_mk_rv(verdict), route_id="r-x")
            assert (verdict, dec.target_stage) in _LEGAL_MAPPING, (
                f"({verdict}, {dec.target_stage}) 不在 Dev-ζ 合法映射中"
            )

    def test_all_escalation_legal(self) -> None:
        from app.supervisor.event_sender.rollback_pusher import _LEGAL_MAPPING
        mapper = StageMapper()
        for verdict in (FailVerdict.FAIL_L1, FailVerdict.FAIL_L2,
                        FailVerdict.FAIL_L3, FailVerdict.FAIL_L4):
            dec = mapper.decide(rv=_mk_rv(verdict, level_count=3), route_id="r-x")
            # mapper 产出的 (verdict, target_stage) 必须在 Dev-ζ 合法集中
            assert (verdict, dec.target_stage) in _LEGAL_MAPPING
            # 升级路径必须是 UPGRADE_TO_L1_01
            assert dec.target_stage == TargetStage.UPGRADE_TO_L1_01


class TestStageMapperPMRules:
    """PM-14 · project_id / wp_id 保留在 decision 上。"""

    def test_route_decision_carries_pid_wp(self) -> None:
        mapper = StageMapper()
        rv = RollbackVerdict(
            verdict=FailVerdict.FAIL_L1, severity=RollbackSeverity.WARN,
            wp_id="wp-777", project_id="proj-777", level_count=1,
        )
        dec = mapper.decide(rv=rv, route_id="route-pm")
        assert dec.project_id == "proj-777"
        assert dec.wp_id == "wp-777"
        assert dec.route_id == "route-pm"
