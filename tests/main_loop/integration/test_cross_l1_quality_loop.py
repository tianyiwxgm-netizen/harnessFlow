"""WP07 · 跨 L1 e2e · L1-01 → L1-04 quality loop (Gate 裁决 + rollback)。

集成点:
- main-1 merged L1-04 L2-07 rollback_router (quality_loop.rollback_router.IC14Consumer)
- main-2 WP06 SupervisorReceiver 转发 IC-14 到 quality_loop

覆盖 (≥ 2 TC · 主要测 IC-14 路径):
- TC-24 IC-14 完整 quality loop: rollback_router 真 consume · state_transition 真调
- TC-25 IC-14 幂等: 同 route_id 重发 · idempotent_hit · state_transition 只调一次
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import RollbackInbox
from app.main_loop.tick_scheduler import TickScheduler
from app.quality_loop.rollback_router.ic_14_consumer import (
    IC14Consumer as QualityLoopIC14Consumer,
)
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _MockStateTransition:
    """IC-01 state_transition mock · 记录调用次数."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def state_transition(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {"transitioned": True, "project_id": kwargs.get("project_id")}


# ============================================================
# TC-24 · 完整 quality loop · IC-14 → state_transition
# ============================================================


async def test_TC_WP07_CROSS_QL_01_full_quality_loop_ic14() -> None:
    """main-1 merged QualityLoopIC14Consumer · main-2 WP06 转发 · state_transition 真调。"""
    pid = "pid-wp07xq01"
    bus = EventBusStub()
    state_ep = _MockStateTransition()
    ic14 = QualityLoopIC14Consumer(
        session_pid=pid,
        state_transition=state_ep,
        event_bus=bus,
    )
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=ic14,
    )

    # 构造 IC-14 路由指令 · FAIL_L2 → S4 retry
    cmd = PushRollbackRouteCommand(
        route_id="route-xq01",
        project_id=pid,
        wp_id="wp-xq01-1",
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.S4,
        level_count=1,
        evidence=RouteEvidence(verifier_report_id="vr-xq01"),
        ts=_iso_now(),
    )
    inbox = RollbackInbox.from_command(cmd, received_at_ms=0)
    ack = await receiver.consume_rollback(inbox)

    assert ack.forwarded is True
    assert ack.route_id == cmd.route_id
    # state_transition 被调一次
    assert len(state_ep.calls) == 1
    call = state_ep.calls[0]
    assert call["project_id"] == pid
    assert call["wp_id"] == "wp-xq01-1"
    assert call["escalated"] is False  # level_count=1 · 未触发 UPGRADE


# ============================================================
# TC-25 · 幂等 · 同 route_id 重发 · state_transition 仅 1 次
# ============================================================


async def test_TC_WP07_CROSS_QL_02_idempotent_same_route_id() -> None:
    """同 route_id 重发 IC-14 · state_transition 仅 1 次 · ack 标 idempotent_hit。"""
    pid = "pid-wp07xq02"
    bus = EventBusStub()
    state_ep = _MockStateTransition()
    ic14 = QualityLoopIC14Consumer(
        session_pid=pid,
        state_transition=state_ep,
        event_bus=bus,
    )
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=ic14,
    )

    cmd = PushRollbackRouteCommand(
        route_id="route-xq02-same",
        project_id=pid,
        wp_id="wp-xq02",
        verdict=FailVerdict.FAIL_L1,
        target_stage=TargetStage.S3,
        level_count=1,
        evidence=RouteEvidence(verifier_report_id="vr-xq02"),
        ts=_iso_now(),
    )
    inbox1 = RollbackInbox.from_command(cmd, received_at_ms=0)
    inbox2 = RollbackInbox.from_command(cmd, received_at_ms=100)

    # 第一次
    ack1 = await receiver.consume_rollback(inbox1)
    assert ack1.forwarded is True

    # 第二次 (同 route_id)
    ack2 = await receiver.consume_rollback(inbox2)
    assert ack2.forwarded is True
    # state_transition 仅 1 次 (IC14Consumer 幂等内部缓存)
    assert len(state_ep.calls) == 1


# ============================================================
# TC-26 · 错误传播 · cross_project 拒
# ============================================================


async def test_TC_WP07_CROSS_QL_03_cross_project_rejected() -> None:
    """IC-14 发到绑定 pid-A 的 session · command.project_id=pid-B → ValueError (PM-14)。"""
    pid_bound = "pid-wp07xq03a"
    bus = EventBusStub()
    state_ep = _MockStateTransition()
    ic14 = QualityLoopIC14Consumer(
        session_pid=pid_bound,
        state_transition=state_ep,
        event_bus=bus,
    )
    sched = TickScheduler.create_default(project_id=pid_bound)
    receiver = SupervisorReceiver(
        session_pid=pid_bound,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=ic14,
    )

    # command.project_id 为另一个 pid
    cmd = PushRollbackRouteCommand(
        route_id="route-xq03",
        project_id="pid-wp07xq03b",
        wp_id="wp-xq03",
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.S4,
        level_count=1,
        evidence=RouteEvidence(verifier_report_id="vr-xq03"),
        ts=_iso_now(),
    )
    inbox = RollbackInbox.from_command(cmd, received_at_ms=0)
    # Receiver 转发时 IC14Consumer 应拒 (cross project)
    # 不同实现可能抛 ValueError 或 ack.forwarded=False · 两者都接受
    try:
        ack = await receiver.consume_rollback(inbox)
        # 若没抛 · 至少应拒 (未转发 / reject_reason 非空)
        assert ack.forwarded is False or ack.reject_reason is not None
    except ValueError as e:
        assert "CROSS_PROJECT" in str(e).upper() or "project" in str(e).lower()
    # state_transition 应 0 次
    assert len(state_ep.calls) == 0
