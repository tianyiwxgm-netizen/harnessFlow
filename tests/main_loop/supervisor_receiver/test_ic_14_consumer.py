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


async def test_TC_WP06_IC14_004_escalated_passthrough(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-004 · level_count ≥ 3 · 升级 UPGRADE_TO_L1_01 · ack 透传。"""
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(
        project_id=pid,
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.UPGRADE_TO_L1_01,
        level_count=3,
    )

    ack = await sut.consume(inbox)

    assert ack.forwarded is True
    assert ack.target_new_state == NewWpState.UPGRADED_TO_L1_01.value


# ------------------------ §3 负向 ------------------------


async def test_TC_WP06_IC14_101_cross_project_rejected(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-101 · cross-project · 抛 E_ROUTE_CROSS_PROJECT · downstream 不被调。"""
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(project_id="pid-other")

    with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
        await sut.consume(inbox)

    # downstream 侧不应留下 route_id 痕迹
    assert rollback_downstream.is_processed(inbox.command.route_id) is False


async def test_TC_WP06_IC14_102_empty_session_pid_rejected(
    event_bus, rollback_downstream
) -> None:
    """TC-WP06-IC14-102 · session_pid 空 · __post_init__ 抛 E_ROUTE_NO_PROJECT_ID。"""
    with pytest.raises(ValueError, match="E_ROUTE_NO_PROJECT_ID"):
        IC14Consumer(session_pid="", downstream=rollback_downstream, event_bus=event_bus)


async def test_TC_WP06_IC14_103_downstream_failure_emits_failed_audit(
    pid, event_bus, rollback_downstream, make_rollback_inbox
) -> None:
    """TC-WP06-IC14-103 · downstream 抛 · receiver emit L1-01:rollback_route_failed · 向上抛。"""

    # 构造一个 mismatch 触发 downstream 的 _LEGAL_MAPPING 校验
    sut = IC14Consumer(
        session_pid=pid, downstream=rollback_downstream, event_bus=event_bus
    )
    inbox = make_rollback_inbox(
        project_id=pid,
        verdict=FailVerdict.FAIL_L1,
        target_stage=TargetStage.S5,  # FAIL_L1 → S5 非法
    )

    with pytest.raises(ValueError, match="E_ROUTE_VERDICT_TARGET_MISMATCH"):
        await sut.consume(inbox)

    types = [e.type for e in event_bus._events]
    assert "L1-01:rollback_route_failed" in types
