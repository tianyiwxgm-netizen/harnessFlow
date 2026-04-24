"""IC-14 RollbackPusher · L1-07 → L1-04 · 幂等 · 同 (wp_id, route_id) 返原 ack。

关键 TC（按 ic-contracts §3.14）：
- push_rollback_route 正常 · applied=true · new_wp_state 正确（verdict→target_stage 映射）
- 幂等 by route_id · 同 route_id 重复推返同 ack
- FAIL_L1 + level_count=3 → escalated=true（同级 ≥3 升级）
- project_id 跨 project 拒绝 → E_ROUTE_CROSS_PROJECT
- wp_id 不在拓扑 → E_ROUTE_WP_NOT_FOUND
- verdict=FAIL_L1 但 target_stage=S5（非法映射）→ E_ROUTE_VERDICT_TARGET_MISMATCH
- wp 已 done → E_ROUTE_WP_ALREADY_DONE
- IC-09 审计事件 emit
"""
from __future__ import annotations

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)


pytestmark = pytest.mark.asyncio


def _cmd(
    route_id: str = "route-abcdef01",
    pid: str = "proj-a",
    wp_id: str = "wp-abcdef01",
    verdict: FailVerdict = FailVerdict.FAIL_L2,
    target: TargetStage = TargetStage.S4,
    level_count: int = 1,
    verifier_report_id: str = "rep-1",
) -> PushRollbackRouteCommand:
    return PushRollbackRouteCommand(
        route_id=route_id,
        project_id=pid,
        wp_id=wp_id,
        verdict=verdict,
        target_stage=target,
        level_count=level_count,
        evidence=RouteEvidence(verifier_report_id=verifier_report_id),
        ts="t",
    )


@pytest.fixture
def target() -> MockRollbackRouteTarget:
    return MockRollbackRouteTarget(known_wps={"wp-abcdef01"})


@pytest.fixture
def bus() -> EventBusStub:
    return EventBusStub()


async def test_push_valid_returns_applied(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    ack = await p.push_rollback_route(_cmd())
    assert ack.applied is True
    assert ack.new_wp_state.value == "retry_s4"


async def test_push_idempotent_same_route_id(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    """§3.14.5 · Idempotent by (wp_id, route_id)。"""
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    ack1 = await p.push_rollback_route(_cmd(route_id="route-same00001"))
    ack2 = await p.push_rollback_route(_cmd(route_id="route-same00001"))
    assert ack1.route_id == ack2.route_id
    assert ack1.applied == ack2.applied
    # target 只应 apply 一次
    assert target.apply_call_count == 1


async def test_push_fail_l2_level_3_escalates(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    """level_count=3 触发 BF-E-10 升级 · escalated=true。"""
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    ack = await p.push_rollback_route(
        _cmd(verdict=FailVerdict.FAIL_L2, target=TargetStage.UPGRADE_TO_L1_01, level_count=3)
    )
    assert ack.escalated is True
    assert ack.new_wp_state.value == "upgraded_to_l1_01"


async def test_push_cross_project_rejected(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
        await p.push_rollback_route(_cmd(pid="proj-other"))


async def test_push_unknown_wp_rejected(bus: EventBusStub) -> None:
    target = MockRollbackRouteTarget(known_wps=set())
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    with pytest.raises(ValueError, match="E_ROUTE_WP_NOT_FOUND"):
        await p.push_rollback_route(_cmd())


async def test_push_verdict_target_mismatch_rejected(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    """FAIL_L1 只能 → S3（S4/S5 都是 mismatch）。"""
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    with pytest.raises(ValueError, match="E_ROUTE_VERDICT_TARGET_MISMATCH"):
        await p.push_rollback_route(
            _cmd(verdict=FailVerdict.FAIL_L1, target=TargetStage.S5)
        )


async def test_push_wp_already_done_rejected(bus: EventBusStub) -> None:
    target = MockRollbackRouteTarget(
        known_wps={"wp-abcdef01"}, done_wps={"wp-abcdef01"}
    )
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    with pytest.raises(ValueError, match="E_ROUTE_WP_ALREADY_DONE"):
        await p.push_rollback_route(_cmd())


async def test_push_emits_ic09_audit_event(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    await p.push_rollback_route(_cmd())
    evs = await bus.read_event_stream(
        project_id="proj-a", types=["L1-07:rollback_route_pushed"]
    )
    assert len(evs) == 1
    assert evs[0].payload["route_id"].startswith("route-")


async def test_push_emits_escalated_event_when_escalated(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    """escalated 时 emit L1-04:rollback_escalated（§3.14.6 时序）。"""
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    await p.push_rollback_route(
        _cmd(verdict=FailVerdict.FAIL_L2, target=TargetStage.UPGRADE_TO_L1_01, level_count=3)
    )
    evs = await bus.read_event_stream(
        project_id="proj-a", types=["L1-04:rollback_escalated"]
    )
    assert len(evs) == 1


async def test_push_idempotent_returns_original_state(
    target: MockRollbackRouteTarget, bus: EventBusStub
) -> None:
    """幂等场景 · 第二次 push 返回第一次记录的 new_wp_state（即使 level_count 不同）。"""
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    first = await p.push_rollback_route(
        _cmd(route_id="route-idem00001", verdict=FailVerdict.FAIL_L2, target=TargetStage.S4)
    )
    # 第二次传 level_count=3 · 但 route_id 相同 · 应返回第一次的 ack
    second = await p.push_rollback_route(
        _cmd(route_id="route-idem00001", verdict=FailVerdict.FAIL_L2, target=TargetStage.S4, level_count=3)
    )
    assert second.new_wp_state == first.new_wp_state
    assert second.escalated == first.escalated


async def test_push_verdict_to_target_mapping() -> None:
    """FAIL_L1→S3 / FAIL_L2→S4 / FAIL_L3→S5 · 合法映射全覆盖。"""
    target = MockRollbackRouteTarget(known_wps={"wp-abcdef01"})
    bus = EventBusStub()
    p = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)

    cases = [
        (FailVerdict.FAIL_L1, TargetStage.S3, "retry_s3"),
        (FailVerdict.FAIL_L2, TargetStage.S4, "retry_s4"),
        (FailVerdict.FAIL_L3, TargetStage.S5, "retry_s5"),
    ]
    for i, (verd, tgt, expected) in enumerate(cases):
        ack = await p.push_rollback_route(
            _cmd(route_id=f"route-case0000{i}", verdict=verd, target=tgt)
        )
        assert ack.new_wp_state.value == expected
