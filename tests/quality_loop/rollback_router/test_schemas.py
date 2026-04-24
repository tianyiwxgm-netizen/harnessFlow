"""TC-L104-L207-601 系 · IC-14 schema 对齐核查 · L2-07 消费端 schema 单元测。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RollbackSeverity,
    RollbackVerdict,
    RouteDecision,
    RouteEvidence,
    TargetStage,
)


class TestSchemaReExportMatchesDevZeta:
    """TC-L104-L207-601 · 严格对齐 `app/supervisor/event_sender/schemas.py`。"""

    def test_fail_verdict_enum_is_reexported_from_dev_zeta(self) -> None:
        """生产端 FailVerdict 与消费端同一对象 · 值严格一致。"""
        from app.supervisor.event_sender.schemas import FailVerdict as ProdFV
        assert FailVerdict is ProdFV
        assert {v.value for v in FailVerdict} == {
            "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"
        }

    def test_target_stage_enum_is_reexported_from_dev_zeta(self) -> None:
        from app.supervisor.event_sender.schemas import TargetStage as ProdTS
        assert TargetStage is ProdTS
        assert {v.value for v in TargetStage} == {
            "S3", "S4", "S5", "UPGRADE_TO_L1-01"
        }

    def test_new_wp_state_enum_is_reexported_from_dev_zeta(self) -> None:
        from app.supervisor.event_sender.schemas import NewWpState as ProdNS
        assert NewWpState is ProdNS
        assert {v.value for v in NewWpState} == {
            "retry_s3", "retry_s4", "retry_s5", "upgraded_to_l1_01"
        }

    def test_push_rollback_route_command_reexported(self) -> None:
        from app.supervisor.event_sender.schemas import PushRollbackRouteCommand as ProdCmd
        assert PushRollbackRouteCommand is ProdCmd

    def test_push_rollback_route_ack_reexported(self) -> None:
        from app.supervisor.event_sender.schemas import PushRollbackRouteAck as ProdAck
        assert PushRollbackRouteAck is ProdAck


class TestRollbackSeverity:
    """4 级 severity 枚举定义。"""

    def test_four_levels_defined(self) -> None:
        assert {s.value for s in RollbackSeverity} == {
            "INFO_SUGG", "WARN", "FAIL", "CRITICAL"
        }


class TestRollbackVerdict:
    """内部 verdict · classifier 的输出 schema。"""

    def test_construct_with_required_fields(self) -> None:
        v = RollbackVerdict(
            verdict=FailVerdict.FAIL_L1,
            severity=RollbackSeverity.WARN,
            wp_id="wp-alpha",
            project_id="proj-X",
            level_count=1,
        )
        assert v.verdict == FailVerdict.FAIL_L1
        assert v.severity == RollbackSeverity.WARN
        assert v.level_count == 1

    def test_frozen_immutable(self) -> None:
        v = RollbackVerdict(
            verdict=FailVerdict.FAIL_L2,
            severity=RollbackSeverity.FAIL,
            wp_id="wp-1", project_id="p1", level_count=1,
        )
        with pytest.raises(ValidationError):
            v.level_count = 5  # type: ignore[misc]

    def test_level_count_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            RollbackVerdict(
                verdict=FailVerdict.FAIL_L1, severity=RollbackSeverity.WARN,
                wp_id="wp-1", project_id="p1", level_count=0,
            )


class TestRouteDecision:
    """stage_mapper 的决策输出 schema。"""

    def test_construct_minimal(self) -> None:
        d = RouteDecision(
            target_stage=TargetStage.S3,
            new_wp_state=NewWpState.RETRY_S3,
            severity=RollbackSeverity.WARN,
            escalated=False,
            route_id="route-abc123",
            wp_id="wp-1", project_id="p1", level_count=1,
        )
        assert d.escalated is False
        assert d.target_stage == TargetStage.S3

    def test_cross_project_empty_pid_rejected(self) -> None:
        """PM-14 · 空 pid 拒绝（对齐 Dev-ζ 错误码 E_ROUTE_NO_PROJECT_ID）。"""
        with pytest.raises(ValidationError) as exc:
            RouteDecision(
                target_stage=TargetStage.S3,
                new_wp_state=NewWpState.RETRY_S3,
                severity=RollbackSeverity.WARN,
                route_id="route-1", wp_id="wp-1", project_id="   ",
                level_count=1,
            )
        assert "E_ROUTE_NO_PROJECT_ID" in str(exc.value)

    def test_frozen(self) -> None:
        d = RouteDecision(
            target_stage=TargetStage.S3, new_wp_state=NewWpState.RETRY_S3,
            severity=RollbackSeverity.WARN,
            route_id="route-1", wp_id="wp-1", project_id="p1", level_count=1,
        )
        with pytest.raises(ValidationError):
            d.escalated = True  # type: ignore[misc]


class TestPushRollbackRouteCommandProducerContract:
    """IC-14 producer command 的入口契约 · L2-07 从 Dev-ζ 接到的是这份。"""

    def test_valid_command_accepted(self) -> None:
        cmd = PushRollbackRouteCommand(
            route_id="route-abc123",
            project_id="proj-X",
            wp_id="wp-alpha",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-1"),
            ts="2026-04-23T10:00:00Z",
        )
        assert cmd.verdict == FailVerdict.FAIL_L1
        assert cmd.target_stage == TargetStage.S3

    def test_missing_project_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PushRollbackRouteCommand(
                route_id="route-abc123",
                project_id="",
                wp_id="wp-alpha",
                verdict=FailVerdict.FAIL_L1,
                target_stage=TargetStage.S3,
                level_count=1,
                evidence=RouteEvidence(verifier_report_id="vr-1"),
                ts="2026-04-23T10:00:00Z",
            )
