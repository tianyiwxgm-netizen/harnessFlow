"""L1-01 L2-04 Task Chain Executor · 数据契约 (WP05 范围).

对齐:
    - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-04-任务链执行器.md §3
    - WP03 产出: app.main_loop.decision_engine.schemas.ChosenAction
    - WP04 产出: app.main_loop.tick_scheduler Tick decision → 本模块路由

不可变约定:
    - @dataclass(frozen=True) · 运行时状态用 @dataclass 可变聚合 (TaskChainState)
    - decision_type 必须在 ROUTABLE_DECISION_TYPES 白名单内
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# =========================================================
# 可路由的 decision_type 白名单 (WP05 范围 · 4 类)
# 对齐 task 描述:
#   state_transition → IC-01 → stage_gate     (Dev-δ)
#   get_next_wp      → IC-02 → l1_03 scheduler(Dev-ε)
#   assign_wp        → IC-03 → l1_03 scheduler(Dev-ε)
#   invoke_skill     → IC-04 → skill_dispatch (Dev-γ)
# =========================================================

ROUTABLE_DECISION_TYPES: frozenset[str] = frozenset({
    "state_transition",
    "get_next_wp",
    "assign_wp",
    "invoke_skill",
})


# =========================================================
# TaskStatus · 单任务 (per-project / per-wp) 状态
# =========================================================


class TaskStatus(StrEnum):
    """任务链单条 task 运行态。

    - PENDING:   已登记 · 未 spawn
    - RUNNING:   asyncio.Task 运行中
    - COMPLETED: 正常完成 · 已 IC 返回
    - FAILED:    下游 L1 失败 · 归类为 BF-E-*
    - CANCELED:  被 abort / BLOCK 取消
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset({
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELED,
})


# =========================================================
# RouteDecision · decision → L1 目标 · 路由产出 (不可变)
# =========================================================


@dataclass(frozen=True)
class RouteDecision:
    """路由产出 · router.route_decision() 返回。

    Attributes:
        decision_type: ChosenAction.decision_type (routable 白名单内).
        target_l1:     "L1-02" | "L1-03" | "L1-04" | "L1-05" (本 WP05 仅 4 类).
        ic_code:       "IC-01" | "IC-02" | "IC-03" | "IC-04".
        ic_payload:    拼装后的 IC 入参 (dict · 供 spawner 派发).
        project_id:    PM-14 根字段 · 从 ChosenAction.decision_params 透出.
        wp_id:         关联的 wp_id (若有 · 如 assign_wp / get_next_wp).
        decision_id:   审计追溯 ID (ChosenAction.final_score hash 或 caller 提供).
    """

    decision_type: str
    target_l1: str
    ic_code: str
    ic_payload: dict[str, Any]
    project_id: str
    wp_id: str | None = None
    decision_id: str | None = None


# =========================================================
# TaskChainState · 聚合根 · per-project 运行时
# =========================================================


@dataclass
class TaskChainState:
    """任务链聚合根 (WP05 简化 · 对齐 L2-04 §7.1 ChainExecution 精简).

    Attributes:
        project_id:     PM-14 根字段.
        tasks:          {task_id: (status, wp_id, decision_type)} 登记簿.
        consecutive_failures: 连续失败计数 (≥ 3 触发 L2-06 升级 · 本 WP 仅记录).
        total_dispatched: 总派发次数 (观测 + SLO 用).
        total_completed:  总完成次数.
        total_failed:     总失败次数 (BF-E-* 计数).
    """

    project_id: str
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    consecutive_failures: int = 0
    total_dispatched: int = 0
    total_completed: int = 0
    total_failed: int = 0

    def register(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        wp_id: str | None,
        decision_type: str,
    ) -> None:
        """登记 task 到 state (幂等:已存在 → 覆盖状态)."""
        self.tasks[task_id] = {
            "status": status,
            "wp_id": wp_id,
            "decision_type": decision_type,
        }

    def mark_status(self, task_id: str, status: TaskStatus) -> None:
        """更新 task 状态 (task_id 不存在 → KeyError)."""
        if task_id not in self.tasks:
            raise KeyError(f"task_id={task_id} not registered")
        self.tasks[task_id]["status"] = status

    def get_status(self, task_id: str) -> TaskStatus | None:
        """查询 task 状态 (不存在 → None · 不抛)."""
        entry = self.tasks.get(task_id)
        return entry["status"] if entry else None

    def active_tasks(self) -> list[str]:
        """返回当前 PENDING / RUNNING 的 task_id 列表."""
        return [
            tid for tid, entry in self.tasks.items()
            if entry["status"] not in TERMINAL_STATUSES
        ]


# =========================================================
# TaskChainResult · executor.execute() 返回
# =========================================================


@dataclass(frozen=True)
class TaskChainResult:
    """单次 execute() 返回 · 不可变.

    Attributes:
        accepted:      true = 路由 + 派发成功 · false = 路由前拒绝.
        task_id:       派发后返回的 task id (accepted=false 时为 None).
        route:         RouteDecision 快照 (审计用 · accepted=false 时为 None).
        rejection_reason: accepted=false 时的拒绝原因 (E_CHAIN_* 错误码).
        ic_reply:      下游 L1 同步调用的返回 (异步派发时为 None).
    """

    accepted: bool
    task_id: str | None = None
    route: RouteDecision | None = None
    rejection_reason: str | None = None
    ic_reply: dict[str, Any] | None = None


__all__ = [
    "ROUTABLE_DECISION_TYPES",
    "RouteDecision",
    "TERMINAL_STATUSES",
    "TaskChainResult",
    "TaskChainState",
    "TaskStatus",
]
