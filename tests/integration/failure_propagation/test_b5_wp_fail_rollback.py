"""B5 · L1-03 WP fail → L1-04 回退 (IC-02 → IC-14) · 4 TC.

链路:
    L1-03 WP execution status=FAILED → IC-02 expose 失败 →
    IC-14 push_rollback_route verdict=FAIL_L2 → L2-07 IC14Consumer 路由 →
    L1-02 state_transition (回退路由).
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


def _make_route_command(
    *,
    project_id: str,
    wp_id: str,
    verdict: FailVerdict,
    target_stage: TargetStage,
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
            verifier_report_id="vr-fail",
            decision_id="d-fail",
        ),
        ts=datetime.now(UTC).isoformat(),
    )


class TestB5WpFailRollback:
    """B5 · WP fail → L1-04 回退路径 · 4 TC."""

    async def test_b5_01_wp_fail_l2_routes_to_s4(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B5.1: FAIL_L2 (WP 中度失败) → S4 → retry_s4."""
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd = _make_route_command(
            project_id=project_id,
            wp_id="wp-fail-001",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S4
        # spy 收 retry_s4
        assert_state_transition_to(
            spy.calls, wp_id="wp-fail-001",
            new_wp_state="retry_s4",
            project_id=project_id,
        )

    async def test_b5_02_wp_fail_l3_routes_to_s5(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B5.2: FAIL_L3 (WP 严重失败) → S5 → retry_s5."""
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd = _make_route_command(
            project_id=project_id,
            wp_id="wp-fail-002",
            verdict=FailVerdict.FAIL_L3,
            target_stage=TargetStage.S5,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S5

    async def test_b5_03_idempotent_same_route_id(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B5.3: 同 route_id 重复 push · cache 直返 · spy 仅调一次.

        IC-14 §3.14.5 幂等 by route_id.
        """
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        cmd1 = _make_route_command(
            project_id=project_id,
            wp_id="wp-fail-003",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            route_id="route-dup-id",
        )
        cmd2 = _make_route_command(
            project_id=project_id,
            wp_id="wp-fail-003",  # 同 wp + 同 route_id
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            route_id="route-dup-id",
        )
        ack1 = await consumer.consume(cmd1)
        ack2 = await consumer.consume(cmd2)
        # 二次返 cached ack(同一 ts)
        assert ack1.route_id == ack2.route_id == "route-dup-id"
        # spy 只调一次
        assert len(spy.calls) == 1
        # is_processed 校
        assert consumer.is_processed("route-dup-id") is True

    async def test_b5_04_invalid_verdict_target_mapping_rejected(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B5.4: verdict 与 target_stage 非法组合 · 拒 · E_ROUTE_VERDICT_TARGET_MISMATCH.

        如 FAIL_L1 (轻度) 不允许直接 → S5 (深度回退) · 跨级映射违法.

        合法集 (rollback_pusher._LEGAL_MAPPING):
            FAIL_L1 → S3 / UPGRADE_TO_L1_01
            FAIL_L2 → S4 / UPGRADE_TO_L1_01
            FAIL_L3 → S5 / UPGRADE_TO_L1_01
            FAIL_L4 → UPGRADE_TO_L1_01
        所以 FAIL_L1 → S5 / S4 都非法.
        """
        spy = StateTransitionSpy()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=spy,
            event_bus=sup_event_bus,
        )
        # FAIL_L1 → S5 是跨级非法
        cmd = _make_route_command(
            project_id=project_id,
            wp_id="wp-fail-004",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S5,
        )
        with pytest.raises(ValueError, match="E_ROUTE_VERDICT_TARGET_MISMATCH"):
            await consumer.consume(cmd)
        # spy 未调
        assert spy.calls == []
