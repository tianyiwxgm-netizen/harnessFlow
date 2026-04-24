"""EscalationLogic · 订阅 wp_failed / wp_done · 调 IC-14 rollback_pusher 升级。

TC（按主会话仲裁）：
- 连续 3 fail · 触发 IC-14 push_rollback_route · target_stage=UPGRADE_TO_L1-01
- dedup：同 wp 只升级一次 · 4/5/6 次 fail 不再调 IC-14
- 不同 wp 独立升级
- wp_done 后 reset · 允许再次升级（dedup set 清空）
- 非 3-fail 路径不触发 IC-14
"""
from __future__ import annotations

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.escalator.counter import FailureCounter
from app.supervisor.escalator.escalation_logic import EscalationLogic
from app.supervisor.escalator.schemas import WpDoneEvent, WpFailEvent, WpFailLevel
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)


pytestmark = pytest.mark.asyncio


def _fail(wp_id: str = "wp-a", verdict: WpFailLevel = WpFailLevel.L2) -> WpFailEvent:
    return WpFailEvent(
        project_id="proj-a",
        wp_id=wp_id,
        verdict_level=verdict,
        verifier_report_id="rep-1",
        ts="t",
    )


def _done(wp_id: str = "wp-a") -> WpDoneEvent:
    return WpDoneEvent(project_id="proj-a", wp_id=wp_id, ts="t")


def _build_logic() -> tuple[EscalationLogic, MockRollbackRouteTarget, EventBusStub]:
    target = MockRollbackRouteTarget(known_wps={"wp-a", "wp-b"})
    bus = EventBusStub()
    pusher = RollbackPusher(session_pid="proj-a", target=target, event_bus=bus)
    counter = FailureCounter()
    logic = EscalationLogic(
        session_pid="proj-a", counter=counter, rollback_pusher=pusher
    )
    return logic, target, bus


async def test_single_fail_no_escalation() -> None:
    logic, target, _ = _build_logic()
    ack = await logic.on_wp_failed(_fail())
    assert ack is None
    assert target.apply_call_count == 0


async def test_two_fails_no_escalation() -> None:
    logic, target, _ = _build_logic()
    await logic.on_wp_failed(_fail())
    ack = await logic.on_wp_failed(_fail())
    assert ack is None
    assert target.apply_call_count == 0


async def test_three_fails_triggers_ic14_upgrade() -> None:
    logic, target, bus = _build_logic()
    await logic.on_wp_failed(_fail())
    await logic.on_wp_failed(_fail())
    ack = await logic.on_wp_failed(_fail())
    assert ack is not None
    assert ack.applied is True
    assert ack.escalated is True
    assert ack.new_wp_state.value == "upgraded_to_l1_01"
    assert target.apply_call_count == 1


async def test_fourth_fail_is_deduped_no_double_ic14() -> None:
    """dedup：第 4 次 fail 不应再调 IC-14。"""
    logic, target, _ = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail())
    ack = await logic.on_wp_failed(_fail())
    assert ack is None  # dedup
    assert target.apply_call_count == 1  # 仍然只 1 次


async def test_multiple_wps_independent_escalation() -> None:
    """wp-a 和 wp-b 独立计数。"""
    logic, target, _ = _build_logic()
    # wp-a 3 fail → 升级
    for _ in range(3):
        await logic.on_wp_failed(_fail(wp_id="wp-a"))
    # wp-b 2 fail → 未升级
    for _ in range(2):
        await logic.on_wp_failed(_fail(wp_id="wp-b"))
    assert target.apply_call_count == 1
    # wp-b 第 3 次 → 升级
    await logic.on_wp_failed(_fail(wp_id="wp-b"))
    assert target.apply_call_count == 2


async def test_wp_done_resets_counter_allows_re_escalation() -> None:
    """done 后 counter reset + dedup 清空 · 允许第二轮升级。"""
    logic, target, _ = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail())
    assert target.apply_call_count == 1
    # DONE
    logic.on_wp_done(_done())
    # 再连 3 fail · 再次升级
    for _ in range(3):
        await logic.on_wp_failed(_fail())
    assert target.apply_call_count == 2


async def test_escalation_emits_ic14_audit_event() -> None:
    logic, _, bus = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail())
    evs = await bus.read_event_stream(
        project_id="proj-a", types=["L1-07:rollback_route_pushed"]
    )
    assert len(evs) == 1
    # 升级路径 · 同时 emit L1-04:rollback_escalated
    esc_evs = await bus.read_event_stream(
        project_id="proj-a", types=["L1-04:rollback_escalated"]
    )
    assert len(esc_evs) == 1


async def test_escalation_uses_correct_level_count() -> None:
    """level_count=3 · 触发 IC-14 escalated=true 分支。"""
    logic, target, _ = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail())
    assert target.apply_log[0].level_count == 3


async def test_escalation_verdict_is_fail_l2() -> None:
    """默认本测试用 WpFailLevel.L2 · IC-14 verdict 应按此映射 FAIL_L2。"""
    logic, target, _ = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail(verdict=WpFailLevel.L2))
    cmd = target.apply_log[0]
    assert cmd.verdict.value == "FAIL_L2"
    assert cmd.target_stage.value == "UPGRADE_TO_L1-01"


async def test_escalation_verdict_l3() -> None:
    logic, target, _ = _build_logic()
    for _ in range(3):
        await logic.on_wp_failed(_fail(verdict=WpFailLevel.L3))
    assert target.apply_log[0].verdict.value == "FAIL_L3"


async def test_escalation_dedup_even_after_multiple_fails() -> None:
    """即使 fail 10 次也只升级 1 次（escaltion set 正确生效）。"""
    logic, target, _ = _build_logic()
    for _ in range(10):
        await logic.on_wp_failed(_fail())
    assert target.apply_call_count == 1
