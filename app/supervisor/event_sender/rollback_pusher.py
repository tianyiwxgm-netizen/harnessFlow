"""IC-14 · RollbackPusher · L1-07 → L1-04 · 幂等 by route_id。

**主会话仲裁**：IC-14 方向 = L1-04 · push_rollback_route · 翻译 verdict → target_stage ·
同级 FAIL ≥ 3 自动升级（BF-E-10）。

幂等语义（§3.14.5）：
- key = route_id
- 重复推同 route_id 返回首次 apply 的 ack（含 new_wp_state / escalated）
- target 侧（L1-04 L2-07）只被调用一次

验证（§3.14.4 错误码）：
- project_id 跨 project → E_ROUTE_CROSS_PROJECT
- wp_id 不在拓扑 → E_ROUTE_WP_NOT_FOUND
- verdict→target_stage 非法映射 → E_ROUTE_VERDICT_TARGET_MISMATCH
- wp 已 done → E_ROUTE_WP_ALREADY_DONE

IC-09 审计：
- 每次 push（首次 apply · 非幂等命中）append `L1-07:rollback_route_pushed`
- escalated=true 时 append `L1-04:rollback_escalated`
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    TargetStage,
)


# -------- verdict → target_stage 合法映射表 --------

_LEGAL_MAPPING = {
    (FailVerdict.FAIL_L1, TargetStage.S3),
    (FailVerdict.FAIL_L2, TargetStage.S4),
    (FailVerdict.FAIL_L3, TargetStage.S5),
    (FailVerdict.FAIL_L4, TargetStage.UPGRADE_TO_L1_01),
    # 同级 ≥3 升级时：任何 FAIL_Lx + UPGRADE_TO_L1-01 合法
    (FailVerdict.FAIL_L1, TargetStage.UPGRADE_TO_L1_01),
    (FailVerdict.FAIL_L2, TargetStage.UPGRADE_TO_L1_01),
    (FailVerdict.FAIL_L3, TargetStage.UPGRADE_TO_L1_01),
}


_TARGET_TO_STATE = {
    TargetStage.S3: NewWpState.RETRY_S3,
    TargetStage.S4: NewWpState.RETRY_S4,
    TargetStage.S5: NewWpState.RETRY_S5,
    TargetStage.UPGRADE_TO_L1_01: NewWpState.UPGRADED_TO_L1_01,
}


class RollbackRouteTarget(Protocol):
    """L1-04 L2-07 路由器协议。"""

    def is_known_wp(self, wp_id: str) -> bool: ...
    def is_done_wp(self, wp_id: str) -> bool: ...

    async def apply_route(
        self, command: PushRollbackRouteCommand
    ) -> NewWpState: ...


@dataclass
class MockRollbackRouteTarget:
    """测试 target · 可注入 known_wps / done_wps。"""

    known_wps: set[str] = field(default_factory=set)
    done_wps: set[str] = field(default_factory=set)
    apply_call_count: int = 0
    apply_log: list[PushRollbackRouteCommand] = field(default_factory=list)

    def is_known_wp(self, wp_id: str) -> bool:
        return wp_id in self.known_wps

    def is_done_wp(self, wp_id: str) -> bool:
        return wp_id in self.done_wps

    async def apply_route(
        self, command: PushRollbackRouteCommand
    ) -> NewWpState:
        self.apply_call_count += 1
        self.apply_log.append(command)
        return _TARGET_TO_STATE[command.target_stage]


@dataclass
class RollbackPusher:
    """IC-14 push_rollback_route 实现 · 幂等 by route_id。"""

    session_pid: str
    target: RollbackRouteTarget
    event_bus: EventBusStub
    # 幂等缓存 · key=route_id · val=已返回 ack
    _idem_cache: dict[str, PushRollbackRouteAck] = field(default_factory=dict)

    async def push_rollback_route(
        self, command: PushRollbackRouteCommand
    ) -> PushRollbackRouteAck:
        # 幂等命中 → 直接返回 cached ack（target 不再调用）
        cached = self._idem_cache.get(command.route_id)
        if cached is not None:
            return cached

        # §3.14.4 负向校验
        if command.project_id != self.session_pid:
            raise ValueError(
                f"E_ROUTE_CROSS_PROJECT: {command.project_id} != {self.session_pid}"
            )
        if not self.target.is_known_wp(command.wp_id):
            raise ValueError(f"E_ROUTE_WP_NOT_FOUND: {command.wp_id}")
        if self.target.is_done_wp(command.wp_id):
            raise ValueError(f"E_ROUTE_WP_ALREADY_DONE: {command.wp_id}")
        if (command.verdict, command.target_stage) not in _LEGAL_MAPPING:
            raise ValueError(
                f"E_ROUTE_VERDICT_TARGET_MISMATCH: {command.verdict.value}→{command.target_stage.value}"
            )

        # apply
        new_state = await self.target.apply_route(command)
        escalated = command.level_count >= 3

        ack = PushRollbackRouteAck(
            route_id=command.route_id,
            applied=True,
            new_wp_state=new_state,
            escalated=escalated,
            ts=command.ts,
        )
        self._idem_cache[command.route_id] = ack

        # IC-09 审计
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-07:rollback_route_pushed",
            payload={
                "route_id": command.route_id,
                "wp_id": command.wp_id,
                "verdict": command.verdict.value,
                "target_stage": command.target_stage.value,
                "level_count": command.level_count,
                "new_wp_state": new_state.value,
                "escalated": escalated,
            },
            evidence_refs=(command.evidence.verifier_report_id,),
        )
        if escalated:
            await self.event_bus.append_event(
                project_id=self.session_pid,
                type="L1-04:rollback_escalated",
                payload={
                    "route_id": command.route_id,
                    "wp_id": command.wp_id,
                    "from_level": command.verdict.value,
                    "to": command.target_stage.value,
                    "level_count": command.level_count,
                },
                evidence_refs=(command.evidence.verifier_report_id,),
            )

        return ack
