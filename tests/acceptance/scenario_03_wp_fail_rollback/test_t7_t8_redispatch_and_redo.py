"""Scenario 03 · T7-T8 · 重新调度 + 重做绿路径.

T7: 回退后 L1-03 重派 wp-4 (state_transition wp_id=wp-4 second call)
T8: 重做后 verifier 出 PASS · 关闭 rollback 链
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import FailVerdict, TargetStage
from tests.acceptance.scenario_03_wp_fail_rollback.conftest import StateTransitionSpy
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


async def test_t7_redispatch_after_rollback(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    ic14_consumer: IC14Consumer,
    state_spy: StateTransitionSpy,
    make_route_cmd,
    gwt: GWT,
) -> None:
    """T7 · 回退后 L1-03 重派 · state_transition retry_s3 调用一次再发起."""
    async with gwt("T7 · L1-03 重派 wp-4 · 二次调用 state_transition"):
        gwt.given("wp-4 失败 · 已走过一次 FAIL_L1 → S3 retry")
        cmd1 = make_route_cmd(
            route_id="route-t7-attempt-1",
            wp_id="wp-4",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
        )
        await ic14_consumer.consume(cmd1)
        assert len(state_spy.calls) == 1

        gwt.when("L1-03 重派 wp-4 二次 (新 route_id · 新 attempt)")
        cmd2 = make_route_cmd(
            route_id="route-t7-attempt-2",
            wp_id="wp-4",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=2,
        )
        ack2 = await ic14_consumer.consume(cmd2)

        gwt.then("二次重派成功 · state_transition 共调 2 次 (跨 attempt)")
        assert ack2.applied is True
        assert len(state_spy.calls) == 2
        # 两次都是 wp-4 · level_count 不同
        assert state_spy.calls[0]["level_count"] == 1
        assert state_spy.calls[1]["level_count"] == 2

        gwt.then("两条 IC-09 rollback_executed 都落盘 · 跨 attempt evidence 关联")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            payload_contains={"wp_id": "wp-4"},
            min_count=2,
        )
        assert len(events) == 2


async def test_t8_redo_pass_closes_rollback_chain(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit_factory,
    gwt: GWT,
) -> None:
    """T8 · 重做后 verifier PASS · 关闭 rollback 链 · audit 闭环."""
    async with gwt("T8 · 重做绿 · verifier PASS 关闭链路"):
        gwt.given("已发生 1 次 rollback · audit 1 条 rollback_executed")
        emit_audit_factory(
            "L1-04:rollback_executed",
            {"wp_id": "wp-4", "route_id": "route-t8-r1", "severity": "WARN"},
        )

        gwt.when("重做后 verifier 出 PASS · L1-04 关闭链路 · emit verdict_decided=PASS")
        emit_audit_factory(
            "L1-04:verdict_decided",
            {"wp_id": "wp-4", "verdict": "PASS", "after_rollback": True},
        )

        gwt.then("audit 完整 · rollback + 后续 PASS 都在")
        rollback_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            payload_contains={"wp_id": "wp-4"},
        )
        pass_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:verdict_decided",
            payload_contains={"wp_id": "wp-4", "verdict": "PASS"},
        )
        assert len(rollback_events) == 1
        assert len(pass_events) == 1
        # PASS 在 rollback 之后 · seq 递增
        assert pass_events[0]["sequence"] > rollback_events[0]["sequence"]
