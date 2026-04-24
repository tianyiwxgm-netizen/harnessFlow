"""L1-01 L2-04 · Task Chain Executor (WP05 · 精简范围).

本 package 聚焦 WP05 范围:
    - 接 Tick 决策 (ChosenAction · WP03 产出) → 路由到 L1-02/03/04/05
    - 发对应 IC:
        IC-01 state_transition   · Dev-δ `app.project_lifecycle.stage_gate`
        IC-02 get_next_wp        · Dev-ε `app.l1_03`
        IC-03 assign_wp          · Dev-ε `app.l1_03`
        IC-04 invoke_skill       · Dev-γ `app.skill_dispatch`
    - `asyncio.Task` 管理 · per-project · per-wp
    - 异常捕获 · 下游 L1 失败 → BF-E-* backward fail

对齐:
    docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-04-任务链执行器.md §3 + §11
    docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-04-*-tests.md

公共入口:
    from app.main_loop.task_chain import (
        TaskChainExecutor,
        TaskChainState,
        RouteDecision,
        TaskChainResult,
        TaskChainError,
    )
"""
from __future__ import annotations

from .executor import TaskChainExecutor
from .failure_handler import (
    BF_ERROR_CODES,
    BackwardFailCode,
    TaskChainError,
    classify_exception,
)
from .router import RouteTarget, route_decision
from .schemas import (
    RouteDecision,
    TaskChainResult,
    TaskChainState,
    TaskStatus,
)
from .task_spawner import TaskHandle, TaskSpawner

__all__ = [
    "BF_ERROR_CODES",
    "BackwardFailCode",
    "RouteDecision",
    "RouteTarget",
    "TaskChainError",
    "TaskChainExecutor",
    "TaskChainResult",
    "TaskChainState",
    "TaskHandle",
    "TaskSpawner",
    "TaskStatus",
    "classify_exception",
    "route_decision",
]
