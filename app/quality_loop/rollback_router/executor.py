"""`RollbackExecutor` · 执行回退 · 调 L1-02 IC-01 `state_transition`（mock Dev-δ）。

输入：`RouteDecision`（来自 `StageMapper`）
输出：调用 `state_transition` · 并经 `event_bus.append_event` 记 IC-09 审计

**审计事件**：
- `L1-04:rollback_executed` · 每次执行后必 emit
- `L1-04:rollback_escalated` · 升级路径（escalated=True）附加 emit
- `L1-04:rollback_failed` · state_transition 异常时 emit（随后 re-raise）

**PM-14**：
- `session_pid` 可选；提供时 decision.project_id 必须一致（跨 pid 拒绝）
- 审计事件 project_id 与 decision.project_id 一致（root pid）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.quality_loop.rollback_router.schemas import RouteDecision


class StateTransitionTarget(Protocol):
    """L1-02 IC-01 state_transition 端点协议（mock Dev-δ）。"""

    async def state_transition(
        self,
        *,
        project_id: str,
        wp_id: str,
        new_wp_state: str,
        escalated: bool,
        route_id: str,
        **extra: Any,
    ) -> dict[str, Any]: ...


class EventBusProtocol(Protocol):
    """L1-09 IC-09 append_event 协议。"""

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str: ...


@dataclass
class RollbackExecutor:
    """回退执行器 · 单元可替换。"""

    state_transition: StateTransitionTarget
    event_bus: EventBusProtocol
    # 可选 · 提供后做 PM-14 pid 一致性校验（严格模式）
    session_pid: str | None = None

    async def execute(self, decision: RouteDecision) -> dict[str, Any]:
        """执行回退 · 返回 state_transition 的响应。

        顺序：
        1. PM-14 校验（若 session_pid 给定）
        2. 调 state_transition（异常时 emit rollback_failed 并 re-raise）
        3. emit rollback_executed
        4. escalated=True 时附加 emit rollback_escalated
        """
        # Step 1: PM-14 · 跨 pid 拒绝（对齐 Dev-ζ E_ROUTE_CROSS_PROJECT）
        if self.session_pid is not None and decision.project_id != self.session_pid:
            raise ValueError(
                f"E_ROUTE_CROSS_PROJECT: {decision.project_id} != {self.session_pid}"
            )

        # Step 2: 调 state_transition
        try:
            result = await self.state_transition.state_transition(
                project_id=decision.project_id,
                wp_id=decision.wp_id,
                new_wp_state=decision.new_wp_state.value,
                escalated=decision.escalated,
                route_id=decision.route_id,
                target_stage=decision.target_stage.value,
                severity=decision.severity.value,
                level_count=decision.level_count,
            )
        except Exception as e:
            # 失败事件 · 不吞 · 记录后 re-raise
            await self.event_bus.append_event(
                project_id=decision.project_id,
                type="L1-04:rollback_failed",
                payload={
                    "route_id": decision.route_id,
                    "wp_id": decision.wp_id,
                    "new_wp_state": decision.new_wp_state.value,
                    "error": str(e),
                },
            )
            raise

        # Step 3: 审计 · rollback_executed（PM-14 · root pid）
        await self.event_bus.append_event(
            project_id=decision.project_id,
            type="L1-04:rollback_executed",
            payload={
                "route_id": decision.route_id,
                "wp_id": decision.wp_id,
                "target_stage": decision.target_stage.value,
                "new_wp_state": decision.new_wp_state.value,
                "severity": decision.severity.value,
                "escalated": decision.escalated,
                "level_count": decision.level_count,
            },
        )

        # Step 4: 升级路径附加事件
        if decision.escalated:
            await self.event_bus.append_event(
                project_id=decision.project_id,
                type="L1-04:rollback_escalated",
                payload={
                    "route_id": decision.route_id,
                    "wp_id": decision.wp_id,
                    "level_count": decision.level_count,
                    "target_stage": decision.target_stage.value,
                    "severity": decision.severity.value,
                },
            )

        return result
