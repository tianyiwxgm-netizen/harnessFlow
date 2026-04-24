"""L1-01 L2-01 · Tick 调度器(心脏)· 100ms tick 硬约束。

WP04 简化包范围:
- fixed-interval asyncio loop (default 100ms)
- 每 tick: read state → DecisionEngine(Protocol · WP03 mock) → dispatch action
- tick drift ≤ 100ms P99 (release blocker · HRL-04 同级 IC-15)
- panic → PAUSED ≤ 100ms (IC-17)
- halt → 拒所有 action (IC-15 / IC-09)

依赖:
- app.main_loop.state_machine          · WP02 (merged) 真实 import
- app.main_loop.supervisor_receiver    · WP06 (merged) 真实 IC-15 HaltTargetProtocol
- DecisionEngine                        · WP03 (concurrent) · 用 Protocol mock 解耦

锚点:
- docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-01-Tick 调度器.md §3 + §11
- docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-01-Tick 调度器-tests.md
"""
from app.main_loop.tick_scheduler.schemas import (
    TickBudget,
    TickEvent,
    TickEventType,
    TickResult,
    TickState,
)

__all__ = [
    "TickBudget",
    "TickEvent",
    "TickEventType",
    "TickResult",
    "TickState",
]
