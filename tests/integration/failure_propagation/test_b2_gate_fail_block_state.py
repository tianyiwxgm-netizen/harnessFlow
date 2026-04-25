"""B2 · L1-04 Gate FAIL → L1-02 拒推进 (IC-14) · 3 TC.

链路:
    L1-04 Gate verdict=FAIL_L1/L2/L3/L4 → IC-14 push_rollback_route →
    L1-02 state_transition NewWpState (RETRY_S3 等) · 拒原推进路径.

注: 真实测 IC14Consumer 端到端 (PM-14 守卫 + executor + state_transition spy).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from app.supervisor.common.event_bus_stub import EventBusStub
from tests.shared.ic_assertions import assert_state_transition_to
from tests.shared.stubs import StateTransitionSpy


def _make_command(
    *,
    project_id: str,
    verdict: FailVerdict = FailVerdict.FAIL_L1,
    target_stage: TargetStage = TargetStage.S3,
    wp_id: str = "wp-001",
    route_id: str = "route-aaa",
    level_count: int = 1,
) -> PushRollbackRouteCommand:
    return PushRollbackRouteCommand(
        route_id=route_id,
        project_id=project_id,
        wp_id=wp_id,
        verdict=verdict,
        target_stage=target_stage,
        level_count=level_count,
        evidence=RouteEvidence(
            verifier_report_id="vr-1", decision_id="d-1",
        ),
        ts=datetime.now(UTC).isoformat(),
    )


class TestB2GateFailBlockState:
    """B2 · L1-04 verdict FAIL → L1-02 reject 推进 · 3 TC."""

    async def test_b2_01_fail_l1_routes_to_retry_s3(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B2.1: FAIL_L1 → S3 → new_wp_state=retry_s3 · L1-02 接 state_transition."""
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd = _make_command(
            project_id=project_id,
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S3
        # spy 校
        assert_state_transition_to(
            spy.calls, wp_id="wp-001",
            new_wp_state="retry_s3",
            project_id=project_id,
        )

    async def test_b2_02_fail_l4_escalates_to_l1_01(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B2.2: FAIL_L4 → UPGRADE_TO_L1_01 · escalated=True."""
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd = _make_command(
            project_id=project_id,
            verdict=FailVerdict.FAIL_L4,
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            level_count=3,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.UPGRADED_TO_L1_01
        assert ack.escalated is True
        # spy 校 escalated=true
        calls = spy.calls
        assert len(calls) == 1
        assert calls[0]["escalated"] is True

    async def test_b2_03_cross_pid_route_rejected(
        self,
        project_id: str,
        other_project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B2.3: 跨 pid IC-14 command · IC14Consumer 守卫 · ValueError E_ROUTE_CROSS_PROJECT.

        PM-14 §1: consumer.session_pid 锁 · 跨 pid 拒.
        """
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd = _make_command(
            project_id=other_project_id,  # 跨 pid
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
        )
        with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
            await consumer.consume(cmd)
        # spy 不应被调
        assert spy.calls == []
