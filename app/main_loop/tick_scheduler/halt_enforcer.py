"""L2-01 · HaltEnforcer · IC-15 halt 协议执行器。

HRL-05 释义(与 IC-15 consumer 对齐):
- 收 IC-15 hard_halt 信号后 · state=HALTED ≤ 100ms (硬约束)
- HALTED 期间 · tick loop 拒所有 action dispatch (§3.1.1 E_TICK_HALTED_REJECT)
- 只有 IC-17 user_intervene(authorize) 可清除 HALTED (WP04 暂不实现 resume)

本组件契约(对 ic_15_consumer.HaltTargetProtocol):
- halt(halt_id, red_line_id) -> HardHaltState
- current_state -> HardHaltState

并发语义:
- asyncio 主 loop 单协程 · 不需要跨线程锁
- enforce_halted() 在 loop 每个 iteration 头部做 O(1) 判定
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from app.main_loop.tick_scheduler.schemas import (
    E_TICK_HALTED_REJECT,
    E_TICK_HALT_SLO_VIOLATION,
    HARD_HALT_SLO_MS,
    TickError,
    TickState,
)
from app.supervisor.event_sender.schemas import HardHaltState


@dataclass
class HaltEnforcer:
    """IC-15 halt target · 实现 HaltTargetProtocol(供 ic_15_consumer 直接绑)。

    用法:
        halt_enforcer = HaltEnforcer(project_id="pid-x")
        # 绑到 IC15Consumer:
        consumer = IC15Consumer(
            session_pid="pid-x",
            halt_target=halt_enforcer,     # ← 本组件
            event_bus=bus,
        )

    状态保证:
    - 初始 current_state = RUNNING (对齐 HardHaltState 默认)
    - halt() 单调进入 HALTED · 不再迁出
    - is_halted() / enforce_allowed() 供主 loop O(1) 判定
    """

    project_id: str
    slo_ms: int = HARD_HALT_SLO_MS

    _state: HardHaltState = field(default=HardHaltState.RUNNING, init=False)
    _active_halt_id: str | None = field(default=None, init=False)
    _active_red_line_id: str | None = field(default=None, init=False)
    _halt_history: list[dict[str, Any]] = field(default_factory=list, init=False)
    # reject 计数 · 审计用
    _reject_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id required (PM-14)")
        if self.slo_ms <= 0:
            raise ValueError(f"slo_ms must be positive · got {self.slo_ms}")

    # ------------------------------------------------------------------
    # HaltTargetProtocol 接口 (对齐 ic_15_consumer)
    # ------------------------------------------------------------------
    @property
    def current_state(self) -> HardHaltState:
        """返回 HardHaltState enum · 供 IC15Consumer.state_before 读。"""
        return self._state

    async def halt(self, halt_id: str, red_line_id: str) -> HardHaltState:
        """阻塞式执行 halt · 返回 state_before · ≤ 100ms 硬约束(HRL-05)。

        实现细节:
        - 单调进入 HALTED · 幂等(重复 halt_id 不抛 · 但 state_before=HALTED)
        - 无 I/O 路径 · 内存状态翻转 + history append (O(1))
        - 不调 await · 保证 ≤ 1us 完成(pytest-benchmark 验)

        返回 state_before · IC15Consumer 据此计算 latency 和 state_before 字段。
        """
        # start_ns: 供内部 SLO 告警 (consumer 侧有权威 latency)
        start_ns = time.perf_counter_ns()
        state_before = self._state

        # 幂等 · 重复 halt 不二次翻转 · 但挂到 history
        if self._state != HardHaltState.HALTED:
            self._state = HardHaltState.HALTED
            self._active_halt_id = halt_id
            self._active_red_line_id = red_line_id

        end_ns = time.perf_counter_ns()
        latency_ms = (end_ns - start_ns) // 1_000_000

        self._halt_history.append(
            {
                "halt_id": halt_id,
                "red_line_id": red_line_id,
                "state_before": state_before.value,
                "state_after": self._state.value,
                "latency_ms": int(latency_ms),
                "slo_violated": latency_ms > self.slo_ms,
                "ts_ns": end_ns,
            }
        )
        # 尝试 await 一下让出协程(不阻塞) · 供其他等待者观测(非必需)
        # await asyncio.sleep(0)  -- 跳过以保证 ≤ 100us

        return state_before

    # ------------------------------------------------------------------
    # 主 loop 侧判定 API
    # ------------------------------------------------------------------
    def is_halted(self) -> bool:
        """O(1) 判定 · 供 tick loop 每 iteration 头部拒绝 action。"""
        return self._state == HardHaltState.HALTED

    def assert_not_halted(self) -> None:
        """HALTED 期间任何 action dispatch 都应先调此方法 · 抛 E_TICK_HALTED_REJECT。"""
        if self._state == HardHaltState.HALTED:
            self._reject_count += 1
            raise TickError(
                error_code=E_TICK_HALTED_REJECT,
                message=(
                    f"action rejected · state=HALTED · halt_id={self._active_halt_id} · "
                    f"red_line_id={self._active_red_line_id}"
                ),
                project_id=self.project_id,
                context={
                    "halt_id": self._active_halt_id,
                    "red_line_id": self._active_red_line_id,
                    "reject_count": self._reject_count,
                },
            )

    def as_tick_state(self) -> TickState:
        """映射 HardHaltState → TickState (4 态)。"""
        if self._state == HardHaltState.HALTED:
            return TickState.HALTED
        if self._state == HardHaltState.PAUSED:
            return TickState.PAUSED
        return TickState.RUNNING  # HardHaltState 仅 3 值 · 其余都是 RUNNING

    @property
    def reject_count(self) -> int:
        return self._reject_count

    @property
    def halt_history(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._halt_history)

    @property
    def active_halt_id(self) -> str | None:
        return self._active_halt_id

    def mark_panic(self) -> None:
        """标 PAUSED · 供 panic_handler 调 · 不经 IC-15 路径。

        注意:PAUSED 可逆(user resume) · HALTED 不可逆。
        PAUSED 状态下 · enforce_not_halted 仍 pass · 但 enforce_can_dispatch 拒。
        """
        if self._state == HardHaltState.HALTED:
            # 已 HALTED 不降级为 PAUSED
            return
        self._state = HardHaltState.PAUSED

    def clear_panic(self) -> None:
        """user resume · PAUSED → RUNNING (HALTED 不受影响)。"""
        if self._state == HardHaltState.PAUSED:
            self._state = HardHaltState.RUNNING

    def assert_can_dispatch(self) -> None:
        """HALTED/PAUSED 期间 dispatch action 先调此 · 都拒。"""
        from app.main_loop.tick_scheduler.schemas import E_TICK_PAUSED_REJECT

        if self._state == HardHaltState.HALTED:
            self._reject_count += 1
            raise TickError(
                error_code=E_TICK_HALTED_REJECT,
                message="action rejected · state=HALTED",
                project_id=self.project_id,
                context={"halt_id": self._active_halt_id},
            )
        if self._state == HardHaltState.PAUSED:
            self._reject_count += 1
            raise TickError(
                error_code=E_TICK_PAUSED_REJECT,
                message="action rejected · state=PAUSED (panic)",
                project_id=self.project_id,
            )


__all__ = ["HaltEnforcer"]
