"""WP09-04 · IC-01 state_transition · L1-04 RollbackExecutor → L1-02.

**契约**: L1-02 IC-01 `state_transition` 是 L1-02 项目生命周期状态机的唯一写入口.
L1-04 RollbackExecutor 在回退决策落地时必须调 IC-01，传：
- project_id (PM-14)
- wp_id
- new_wp_state (retry_s3 / retry_s4 / retry_s5 / upgraded_to_l1_01)
- escalated (bool)
- route_id (source decision)
- target_stage + severity + level_count (上下文字段)

**真实代码**:
- L1-04 `IC14Consumer` 路由决策 → `RollbackExecutor.execute` → 调 `StateTransitionTarget`
- L1-02 IC-01 Dev-δ merged · 真实跨进程实现暂不可在单元层直接挂 · 用 StateTransitionSpy 验契约字段
"""
from __future__ import annotations

import pytest

from app.quality_loop.rollback_router.executor import RollbackExecutor
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteCommand,
    RollbackSeverity,
    RouteDecision,
    RouteEvidence,
    TargetStage,
)


class _AsyncEventBus:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def append_event(self, **kw) -> str:
        self.events.append(kw)
        return f"ev-{len(self.events)}"


# ==============================================================================
# TC-1 · RollbackExecutor 直调 state_transition · 字段级校验
# ==============================================================================


class TestStateTransitionInvoke:
    """RollbackExecutor.execute → state_transition 参数字段校验."""

    async def test_fail_l1_fills_all_contract_fields(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """FAIL_L1 常规 · state_transition 必含完整字段集."""
        bus = _AsyncEventBus()
        executor = RollbackExecutor(state_transition=state_spy, event_bus=bus)
        decision = RouteDecision(
            target_stage=TargetStage.S3,
            new_wp_state=NewWpState.RETRY_S3,
            severity=RollbackSeverity.WARN,
            escalated=False,
            route_id="route-st-001",
            wp_id="wp-alpha",
            project_id=project_id,
            level_count=1,
        )
        await executor.execute(decision)
        assert len(state_spy.calls) == 1
        call = state_spy.calls[0]
        # PM-14 根字段
        assert call["project_id"] == project_id
        # 契约必要字段
        assert call["wp_id"] == "wp-alpha"
        assert call["new_wp_state"] == "retry_s3"
        assert call["escalated"] is False
        assert call["route_id"] == "route-st-001"
        # 上下文字段
        assert call["target_stage"] == "S3"
        assert call["severity"] == "WARN"
        assert call["level_count"] == 1

    async def test_upgrade_path_passes_upgrade_target(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """FAIL_L4 或 level_count≥3 · new_wp_state=upgraded_to_l1_01."""
        bus = _AsyncEventBus()
        executor = RollbackExecutor(state_transition=state_spy, event_bus=bus)
        decision = RouteDecision(
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            new_wp_state=NewWpState.UPGRADED_TO_L1_01,
            severity=RollbackSeverity.CRITICAL,
            escalated=True,
            route_id="route-up-001",
            wp_id="wp-upgrade",
            project_id=project_id,
            level_count=3,
        )
        await executor.execute(decision)
        call = state_spy.calls[0]
        assert call["new_wp_state"] == "upgraded_to_l1_01"
        assert call["escalated"] is True
        assert call["severity"] == "CRITICAL"


# ==============================================================================
# TC-2 · state_transition 异常 · rollback_failed 审计 + re-raise
# ==============================================================================


class TestStateTransitionFailure:
    """L1-02 IC-01 异常 · L1-04 emit rollback_failed 审计 · 不吞异常."""

    async def test_state_transition_exception_emits_failed_event(
        self,
        project_id: str,
    ) -> None:
        class _BadState:
            async def state_transition(self, **kw):
                raise RuntimeError("L1-02 backend unreachable")

        bus = _AsyncEventBus()
        executor = RollbackExecutor(state_transition=_BadState(), event_bus=bus)
        decision = RouteDecision(
            target_stage=TargetStage.S3,
            new_wp_state=NewWpState.RETRY_S3,
            severity=RollbackSeverity.WARN,
            escalated=False,
            route_id="route-fail-1",
            wp_id="wp-A",
            project_id=project_id,
            level_count=1,
        )
        with pytest.raises(RuntimeError, match="L1-02 backend unreachable"):
            await executor.execute(decision)
        # rollback_failed 审计已 emit
        types = [e["type"] for e in bus.events]
        assert "L1-04:rollback_failed" in types


# ==============================================================================
# TC-3 · IC-14 consumer → executor → state_transition · e2e
# ==============================================================================


class TestIC14ToStateTransitionE2E:
    """从 IC-14 command 流转到 L1-02 state_transition 的完整链路.

    链: command → consumer.consume → classifier → mapper → executor → state_transition
    """

    async def test_full_chain_emits_state_and_audit(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        bus = _AsyncEventBus()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=bus,
        )
        cmd = PushRollbackRouteCommand(
            route_id="route-chain-001",
            project_id=project_id,
            wp_id="wp-chain",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-chain"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S4

        # state_transition 收到正确的映射
        assert len(state_spy.calls) == 1
        call = state_spy.calls[0]
        assert call["new_wp_state"] == "retry_s4"
        assert call["target_stage"] == "S4"
        assert call["project_id"] == project_id

        # L1-04 rollback_executed 审计事件已 emit
        audit_types = [e["type"] for e in bus.events]
        assert "L1-04:rollback_executed" in audit_types
