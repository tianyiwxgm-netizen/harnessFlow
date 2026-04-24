"""L1-01 L2-04 · TaskSpawner · asyncio.Task 管理 (per-project / per-wp).

职责:
    - 将 RouteDecision 转为 asyncio.Task (派发到下游 L1)
    - per-project 维度持有所有 task 句柄 (TaskHandle · 封装 task_id + project_id + wp_id)
    - 提供 cancel / cancel_project / iter_active 管控能力
    - 与 TaskChainState 解耦:spawner 只管 asyncio 资源;state 管语义状态

与 router/executor 的协作:
    router.route_decision() → RouteDecision
                       ↓
    spawner.spawn(route, ic_callable) → TaskHandle (asyncio.Task)
                       ↓
    executor 注册到 TaskChainState · done_callback 更新状态

对齐:
    - L2-04 §6.3 "步派发 · IC 路由"
    - PM-14 per-project 隔离 (task_handle.project_id 必填)
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .schemas import RouteDecision

# IC 调用签名 · spawner 不关心具体 IC · 只关心能 await 返回 dict
ICCallable = Callable[[RouteDecision], Awaitable[dict[str, Any]]]


@dataclass
class TaskHandle:
    """asyncio.Task 的语义封装 · 不可穿越 project 边界.

    Attributes:
        task_id: "task-{uuid-v4}" 唯一标识.
        project_id: PM-14 根 · 与 RouteDecision.project_id 严格一致.
        wp_id: 关联的 wp_id (若有 · 如 assign_wp / get_next_wp).
        decision_type: 对应的 decision_type (审计分类).
        task: 实际的 asyncio.Task 对象.
        route: RouteDecision 快照 (审计/重放用).
    """

    task_id: str
    project_id: str
    decision_type: str
    task: asyncio.Task[Any]
    route: RouteDecision
    wp_id: str | None = None

    def cancel(self) -> bool:
        """取消任务 · 返 True 即底层 task.cancel() 成功."""
        return self.task.cancel()

    def done(self) -> bool:
        return self.task.done()


@dataclass
class TaskSpawner:
    """asyncio.Task 池 · per-project 分片 · 对齐 PM-14.

    内部结构:
        _handles_by_project: {project_id: {task_id: TaskHandle}}
            · 所有 spawn 出的 task 按 project_id 分片
            · cancel_project() 清掉单个 project 全部 task
    """

    _handles_by_project: dict[str, dict[str, TaskHandle]] = field(default_factory=dict)

    def spawn(
        self,
        route: RouteDecision,
        ic_callable: ICCallable,
        *,
        task_id: str | None = None,
    ) -> TaskHandle:
        """派发 RouteDecision 到下游 · 返回 TaskHandle.

        Args:
            route: 路由产出 (必带 project_id).
            ic_callable: async (route) → dict 的 IC 调用函数.
            task_id: 自定义 task_id (空则 task-{uuid4}).

        Returns:
            TaskHandle · 已注入 _handles_by_project.

        Raises:
            ValueError: route.project_id 空时拒绝 spawn.
        """
        if not route.project_id:
            raise ValueError(
                "TaskSpawner.spawn: route.project_id is empty (PM-14 violation)"
            )
        tid = task_id or f"task-{uuid.uuid4()}"

        # 构造 asyncio.Task · 运行 ic_callable(route)
        task = asyncio.ensure_future(ic_callable(route))

        handle = TaskHandle(
            task_id=tid,
            project_id=route.project_id,
            wp_id=route.wp_id,
            decision_type=route.decision_type,
            task=task,
            route=route,
        )
        # 按 project 分片写入
        bucket = self._handles_by_project.setdefault(route.project_id, {})
        bucket[tid] = handle
        return handle

    def get(self, task_id: str, *, project_id: str) -> TaskHandle | None:
        """按 project_id + task_id 查句柄 · 跨 project 查不到."""
        return self._handles_by_project.get(project_id, {}).get(task_id)

    def iter_active(self, project_id: str) -> list[TaskHandle]:
        """返回单个 project 当前未 done 的 TaskHandle 列表."""
        bucket = self._handles_by_project.get(project_id, {})
        return [h for h in bucket.values() if not h.done()]

    def cancel_task(self, task_id: str, *, project_id: str) -> bool:
        """取消单个 task · 找不到返 False · 已 done 返 False.

        Note: 取消语义交给 asyncio.Task.cancel() · 不做同步 join;
        调用方若需等待 cancel 生效 · 需自行 await handle.task.
        """
        handle = self.get(task_id, project_id=project_id)
        if handle is None or handle.done():
            return False
        return handle.cancel()

    def cancel_project(self, project_id: str) -> int:
        """取消某 project 全部 task · 返被取消的数量 (PM-14 BLOCK 抢占用)."""
        bucket = self._handles_by_project.get(project_id, {})
        canceled = 0
        for h in bucket.values():
            if not h.done() and h.cancel():
                canceled += 1
        return canceled

    def forget(self, task_id: str, *, project_id: str) -> bool:
        """从 pool 移除记录 (GC 用) · 不 cancel · 仅删引用."""
        bucket = self._handles_by_project.get(project_id, {})
        if task_id in bucket:
            del bucket[task_id]
            return True
        return False

    def active_count(self, project_id: str) -> int:
        """某 project 未 done 的 task 数."""
        return len(self.iter_active(project_id))

    def total_count(self, project_id: str) -> int:
        """某 project 所有 task 数 (含 done · 未 forget 的)."""
        return len(self._handles_by_project.get(project_id, {}))


__all__ = [
    "ICCallable",
    "TaskHandle",
    "TaskSpawner",
]
