"""TC-L104-L207 · executor · 执行回退 · 调 L1-02 state_transition (IC-01 mock Dev-δ)。

核心 TC：
- 执行回退时必调 L1-02 state_transition
- PM-14：必带 pid
- 4 级 new_wp_state 分别映射到 IC-01 state_transition payload
- UPGRADE_TO_L1_01 · 需携带 escalated=True 信号
- state_transition 失败（L1-02 抛） · 不静默吞 · 往上抛
- IC-09 审计：执行后 append_event
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.rollback_router.executor import RollbackExecutor
from app.quality_loop.rollback_router.schemas import (
    NewWpState,
    RollbackSeverity,
    RouteDecision,
    TargetStage,
)


class MockStateTransition:
    """Mock Dev-δ IC-01 state_transition endpoint."""

    def __init__(self, *, raise_on_call: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._raise = raise_on_call

    async def state_transition(self, *, project_id: str, wp_id: str,
                               new_wp_state: str, escalated: bool,
                               route_id: str, **extra: Any) -> dict[str, Any]:
        if self._raise:
            raise RuntimeError("E_STATE_TRANSITION_FAILED")
        self.calls.append({
            "project_id": project_id, "wp_id": wp_id,
            "new_wp_state": new_wp_state, "escalated": escalated,
            "route_id": route_id, **extra,
        })
        return {"transitioned": True, "project_id": project_id}


class MockEventBus:
    """Mock IC-09 append_event for audit."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def append_event(self, *, project_id: str, type: str,
                           payload: dict[str, Any],
                           evidence_refs: tuple[str, ...] = ()) -> str:
        self.events.append({
            "project_id": project_id, "type": type, "payload": payload,
            "evidence_refs": evidence_refs,
        })
        return f"ev-{len(self.events)}"


def _mk_decision(target: TargetStage, state: NewWpState, escalated: bool = False,
                 severity: RollbackSeverity = RollbackSeverity.WARN,
                 level_count: int = 1) -> RouteDecision:
    return RouteDecision(
        target_stage=target, new_wp_state=state, severity=severity,
        escalated=escalated, route_id="route-exec-1",
        wp_id="wp-1", project_id="proj-X", level_count=level_count,
    )


class TestExecutorStateTransition:
    """执行回退时必调 L1-02 state_transition · 4 级分别映射。"""

    @pytest.mark.asyncio
    async def test_warn_retry_s3_invokes_state_transition(self) -> None:
        """TC-L104-L207-exec-01 · FAIL_L1 → retry_s3 · 调 IC-01。"""
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(TargetStage.S3, NewWpState.RETRY_S3)
        await ex.execute(dec)
        assert len(st.calls) == 1
        call = st.calls[0]
        assert call["project_id"] == "proj-X"
        assert call["wp_id"] == "wp-1"
        assert call["new_wp_state"] == "retry_s3"
        assert call["escalated"] is False

    @pytest.mark.asyncio
    async def test_fail_retry_s4_invokes_state_transition(self) -> None:
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(TargetStage.S4, NewWpState.RETRY_S4,
                           severity=RollbackSeverity.FAIL)
        await ex.execute(dec)
        assert st.calls[0]["new_wp_state"] == "retry_s4"

    @pytest.mark.asyncio
    async def test_fail_retry_s5_invokes_state_transition(self) -> None:
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(TargetStage.S5, NewWpState.RETRY_S5,
                           severity=RollbackSeverity.FAIL)
        await ex.execute(dec)
        assert st.calls[0]["new_wp_state"] == "retry_s5"

    @pytest.mark.asyncio
    async def test_critical_upgrade_invokes_with_escalated_true(self) -> None:
        """TC-L104-L207-exec-04 · FAIL_L4 / 同级≥3 · UPGRADE_TO_L1_01 · escalated=True。"""
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(
            TargetStage.UPGRADE_TO_L1_01, NewWpState.UPGRADED_TO_L1_01,
            escalated=True, severity=RollbackSeverity.CRITICAL, level_count=3,
        )
        await ex.execute(dec)
        call = st.calls[0]
        assert call["new_wp_state"] == "upgraded_to_l1_01"
        assert call["escalated"] is True


class TestExecutorAuditIC09:
    """IC-09 审计 · 执行后必 append_event（type: L1-04:rollback_executed）。"""

    @pytest.mark.asyncio
    async def test_emits_audit_event_on_success(self) -> None:
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(TargetStage.S3, NewWpState.RETRY_S3)
        await ex.execute(dec)
        assert len(bus.events) == 1
        ev = bus.events[0]
        assert ev["type"] == "L1-04:rollback_executed"
        assert ev["project_id"] == "proj-X"
        assert ev["payload"]["route_id"] == "route-exec-1"
        assert ev["payload"]["new_wp_state"] == "retry_s3"

    @pytest.mark.asyncio
    async def test_escalated_emits_additional_event(self) -> None:
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(
            TargetStage.UPGRADE_TO_L1_01, NewWpState.UPGRADED_TO_L1_01,
            escalated=True, severity=RollbackSeverity.CRITICAL, level_count=3,
        )
        await ex.execute(dec)
        # 至少 2 条事件：rollback_executed + rollback_escalated
        types = {e["type"] for e in bus.events}
        assert "L1-04:rollback_executed" in types
        assert "L1-04:rollback_escalated" in types


class TestExecutorPM14:
    """PM-14 · 跨 project_id 拒绝。"""

    @pytest.mark.asyncio
    async def test_mismatched_session_pid_raises(self) -> None:
        st = MockStateTransition()
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus,
                              session_pid="proj-session")
        dec = _mk_decision(TargetStage.S3, NewWpState.RETRY_S3)
        # decision 的 project_id = proj-X ≠ session_pid
        with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
            await ex.execute(dec)


class TestExecutorFailurePropagation:
    """state_transition 失败不静默吞。"""

    @pytest.mark.asyncio
    async def test_state_transition_raises_propagated(self) -> None:
        st = MockStateTransition(raise_on_call=True)
        bus = MockEventBus()
        ex = RollbackExecutor(state_transition=st, event_bus=bus)
        dec = _mk_decision(TargetStage.S3, NewWpState.RETRY_S3)
        with pytest.raises(RuntimeError, match="E_STATE_TRANSITION_FAILED"):
            await ex.execute(dec)
        # 失败不 emit rollback_executed · 但可以 emit rollback_failed
        executed = [e for e in bus.events if e["type"] == "L1-04:rollback_executed"]
        assert not executed
