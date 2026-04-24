"""IC-14 消费端 TC · receiver 侧转发 main-1 merged IC14Consumer。

真实 downstream · 非 mock · 对齐"真完成"原则（receiver + quality_loop 双层联调）。
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    NewWpState,
    TargetStage,
)

pytestmark = pytest.mark.asyncio


# ------------------------ §2 正向 ------------------------


async def test_TC_WP06_IC14_001_forwards_to_quality_loop_and_returns_new_state(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-001 · FAIL_L2 → S4 · receiver 转发 · downstream 返 retry_s4。"""
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(
        project_id=pid,
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.S4,
    )

    ack = await sut.consume(inbox)

    assert ack.forwarded is True
    assert ack.idempotent_hit is False
    assert ack.target_new_state == NewWpState.RETRY_S4.value


async def test_TC_WP06_IC14_002_emits_audit_event(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-002 · 成功转发后 emit L1-01:rollback_route_received。"""
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(project_id=pid)

    await sut.consume(inbox)

    types = [e.type for e in event_bus._events]
    assert "L1-01:rollback_route_received" in types


async def test_TC_WP06_IC14_003_idempotent_by_route_id(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-003 · 重复推同 route_id · idempotent_hit=true · downstream 自带缓存。"""
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(project_id=pid, route_id="route-idem-001")

    ack1 = await sut.consume(inbox)
    ack2 = await sut.consume(inbox)

    assert ack1.idempotent_hit is False
    assert ack2.idempotent_hit is True, "第二次 · receiver 层观测到重复"
    # 但 target_new_state 相同（downstream 返 cached ack）
    assert ack1.target_new_state == ack2.target_new_state
