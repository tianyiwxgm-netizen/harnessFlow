"""Scenario 03 · T1-T2 · WP fail → IC-02/IC-14 BLOCK 链路.

T1: WP4 test 红 · L1-04 verifier emit IC-02 status_change → FAIL_L*
T2: IC-14 verdict=BLOCK · L1-04 IC14Consumer 收到 → 推进 rollback
"""
from __future__ import annotations

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import FailVerdict, TargetStage
from tests.acceptance.scenario_03_wp_fail_rollback.conftest import StateTransitionSpy
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


async def test_t1_wp_fail_emits_ic02_status_change_fail(
    project_id: str,
    real_event_bus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    state_spy: StateTransitionSpy,
    make_route_cmd,
    gwt: GWT,
) -> None:
    """T1 · WP fail · IC-02 status_change FAIL_L1 → IC-14 入消费."""
    async with gwt("T1 · WP4 test 红 → IC-02 FAIL_L1 → IC-14 路由"):
        gwt.given("WP4 测试失败 · verifier 出 FAIL_L1 verdict")
        cmd = make_route_cmd(
            route_id="route-t1-wp4-fail",
            wp_id="wp-4",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
        )

        gwt.when("L2-07 IC14Consumer.consume(FAIL_L1, target=S3) · 端到端")
        ack = await ic14_consumer.consume(cmd)

        gwt.then("ack.applied=True · new_wp_state=retry_s3 · 不升级")
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s3"
        assert ack.escalated is False

        gwt.then("IC-01 state_transition 被调 · wp_id=wp-4")
        assert len(state_spy.calls) == 1
        assert state_spy.calls[0]["wp_id"] == "wp-4"
        assert state_spy.calls[0]["new_wp_state"] == "retry_s3"


async def test_t2_ic14_verdict_block_emits_audit(
    project_id: str,
    real_event_bus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    make_route_cmd,
    gwt: GWT,
) -> None:
    """T2 · IC-14 BLOCK verdict · L1-04:rollback_executed audit 落盘."""
    async with gwt("T2 · IC-14 verdict=FAIL_L2 → audit BLOCK 落盘"):
        gwt.given("FAIL_L2 中度回退 · target=S4")
        cmd = make_route_cmd(
            route_id="route-t2-block",
            wp_id="wp-4",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
            level_count=1,
        )

        gwt.when("IC14Consumer 消费 · audit 必落 L1-04:rollback_executed")
        ack = await ic14_consumer.consume(cmd)

        gwt.then("ack.applied=True · new_wp_state=retry_s4")
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s4"

        gwt.then("IC-09 rollback_executed 落盘 · payload 含 severity=FAIL")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            payload_contains={
                "wp_id": "wp-4",
                "severity": "FAIL",
                "target_stage": "S4",
            },
        )
        assert len(events) == 1
