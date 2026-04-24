"""L1-01 L2-04 · TaskChainExecutor · WP05 主入口.

职责:
    - 接 WP03 产出 ChosenAction + TickContext
    - 走 router.route_decision() → RouteDecision
    - 走 task_spawner.spawn() → asyncio.Task
    - 更新 TaskChainState (per-project 聚合根)
    - 统一返回 TaskChainResult

对齐:
    L2-04 §3 + §11 (WP05 简化 · 4 decision_type)

调用方:
    WP04 TickScheduler/AsyncioTickLoop · 每 tick 调一次 execute(action, ctx)
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.main_loop.decision_engine.schemas import ChosenAction

from .failure_handler import BackwardFailCode, TaskChainError, classify_exception
from .router import RouterError, route_decision
from .schemas import (
    RouteDecision,
    TaskChainResult,
    TaskChainState,
    TaskStatus,
)
from .task_spawner import ICCallable, TaskHandle, TaskSpawner

logger = logging.getLogger("app.main_loop.task_chain.executor")


# =========================================================
# ICCallableResolver · 按 RouteDecision 挑选对应的 IC callable
# =========================================================

ICResolver = Callable[[RouteDecision], ICCallable]
"""(route) → async callable · 根据 target_l1/ic_code 路由到真实 IC.

默认实现见 ExecutorConfig.default_resolver · 各 L1 在集成时传自己的 resolver.
"""


@dataclass
class ExecutorConfig:
    """executor 配置 · 注入 IC callable / event_bus / logger.

    Attributes:
        ic_resolver: 必填 · (route) → async IC 调用 callable.
        event_bus:   可选 · 若有则发 L1-01:task_dispatched 等事件 (审计用).
        auto_forget_on_done: done 后是否自动 forget 句柄 (默认 False · 便于审计).
    """

    ic_resolver: ICResolver
    event_bus: Any = None
    auto_forget_on_done: bool = False


# =========================================================
# TaskChainExecutor · 主入口
# =========================================================


@dataclass
class TaskChainExecutor:
    """L2-04 主入口 · per-session 单例 (内部 per-project 分片).

    使用方式:
        executor = TaskChainExecutor(config=ExecutorConfig(ic_resolver=my_resolver))
        result = await executor.execute(chosen_action, ctx_project_id="pid-xx")
        # result.accepted == True · result.task_id 可查

    内部状态:
        spawner: per-session asyncio.Task 池
        states:  {project_id: TaskChainState} 聚合根字典
    """

    config: ExecutorConfig
    spawner: TaskSpawner = field(default_factory=TaskSpawner)
    states: dict[str, TaskChainState] = field(default_factory=dict)

    def get_state(self, project_id: str) -> TaskChainState:
        """懒加载 per-project 聚合根 (首次 call 自动创建)."""
        st = self.states.get(project_id)
        if st is None:
            st = TaskChainState(project_id=project_id)
            self.states[project_id] = st
        return st

    async def execute(
        self,
        action: ChosenAction,
        *,
        project_id: str,
        decision_id: str | None = None,
        await_result: bool = False,
    ) -> TaskChainResult:
        """执行一次 decision → L1 派发.

        Args:
            action: WP03 decide() 产出的 ChosenAction.
            project_id: ctx.project_id (PM-14 必填).
            decision_id: 审计追溯 id.
            await_result: True = 同步等 IC 返回 (测试用);False = 只派发返 task_id.

        Returns:
            TaskChainResult:
                accepted=True · 路由 + 派发成功 (task_id 可查)
                accepted=False · 路由前拒绝 (rejection_reason 填 E_CHAIN_* 码)

        Notes:
            - 永不抛:路由错误被捕获映射为 accepted=False.
            - await_result=True 时会 await handle.task 并填 ic_reply;
              但若下游 L1 抛异常 · 仍填 accepted=True(已派发) · rejection_reason=None;
              异常经 classify_exception 映射到 TaskChainError 写 task_status=FAILED.
        """
        # 1. 路由 (同步 · 无 IO)
        try:
            route = route_decision(
                action, project_id=project_id, decision_id=decision_id,
            )
        except RouterError as exc:
            logger.debug("route rejected: code=%s msg=%s", exc.code, exc.message)
            # 若 project_id 为空 · 本次不创建 state (避免脏 bucket)
            if project_id:
                st = self.get_state(project_id)
                st.total_dispatched += 0  # 路由阶段失败 · 不计派发
            return TaskChainResult(accepted=False, rejection_reason=exc.code)

        # 2. 派发 asyncio.Task
        state = self.get_state(project_id)
        try:
            ic_callable = self.config.ic_resolver(route)
        except Exception as exc:  # ic_resolver 自身出错 · 降级记 BF-E-*
            logger.warning("ic_resolver failed: %s", exc)
            return TaskChainResult(
                accepted=False,
                rejection_reason="E_CHAIN_ACTION_UNSUPPORTED",
                route=route,
            )

        handle = self.spawner.spawn(route, ic_callable)
        state.register(
            task_id=handle.task_id,
            status=TaskStatus.RUNNING,
            wp_id=handle.wp_id,
            decision_type=handle.decision_type,
        )
        state.total_dispatched += 1

        # 3. done_callback · 更新 state (不论同步/异步路径都挂一次)
        self._attach_done_callback(handle, state)

        # 4. 可选同步等待 (测试/debug 路径)
        ic_reply: dict[str, Any] | None = None
        if await_result:
            ic_reply = await self._await_handle(handle, state)

        return TaskChainResult(
            accepted=True,
            task_id=handle.task_id,
            route=route,
            ic_reply=ic_reply,
        )

    # ---------------------------------------------------------
    # 内部辅助
    # ---------------------------------------------------------

    def _attach_done_callback(
        self, handle: TaskHandle, state: TaskChainState,
    ) -> None:
        """挂 done callback · task 完成时推进 state."""

        def _on_done(task: Any) -> None:
            # task.exception() 会 raise 若 cancelled · 用 try/except 捕获
            try:
                exc = task.exception()
            except BaseException:  # noqa: BLE001 (cancelled)
                self._mark_state_terminal(handle, state, TaskStatus.CANCELED)
                return
            if exc is None:
                self._mark_state_terminal(handle, state, TaskStatus.COMPLETED)
            else:
                # 分类 BF-E-* · 连续失败计数 ++
                code = classify_exception(exc)
                logger.info(
                    "task %s failed · code=%s", handle.task_id, code.value,
                )
                if code == BackwardFailCode.DOWNSTREAM_CANCELLED:
                    self._mark_state_terminal(handle, state, TaskStatus.CANCELED)
                else:
                    self._mark_state_terminal(handle, state, TaskStatus.FAILED)

        handle.task.add_done_callback(_on_done)

    def _mark_state_terminal(
        self,
        handle: TaskHandle,
        state: TaskChainState,
        status: TaskStatus,
    ) -> None:
        """推进 state 至终态 · 计数器++."""
        # task_id 可能已被移除 · 幂等保护
        if handle.task_id in state.tasks:
            state.tasks[handle.task_id]["status"] = status
        if status == TaskStatus.COMPLETED:
            state.total_completed += 1
            state.consecutive_failures = 0
        elif status == TaskStatus.FAILED:
            state.total_failed += 1
            state.consecutive_failures += 1
        # CANCELED 不计 consecutive_failures · 不归为 BF-E-*

        if self.config.auto_forget_on_done:
            self.spawner.forget(handle.task_id, project_id=handle.project_id)

    async def _await_handle(
        self, handle: TaskHandle, state: TaskChainState,
    ) -> dict[str, Any] | None:
        """同步路径:等 task 结束并返回 reply (异常 → raise TaskChainError).

        此路径主要给单测/调试用.正常 tick 循环走 await_result=False.
        """
        try:
            return await handle.task
        except TaskChainError:
            raise
        except BaseException as exc:
            raise TaskChainError.from_cause(
                exc, project_id=handle.project_id, task_id=handle.task_id,
            ) from exc

    # ---------------------------------------------------------
    # BLOCK 抢占 · cancel 整个 project 所有任务
    # ---------------------------------------------------------

    def cancel_project_tasks(self, project_id: str) -> int:
        """cancel 某 project 全部未终态任务 (BLOCK 抢占用)."""
        return self.spawner.cancel_project(project_id)


# ExecutorConfig 可选直接构造默认 resolver (mock 路径)
def build_noop_resolver(
    reply: dict[str, Any] | None = None,
) -> ICResolver:
    """给测试用的 no-op resolver · 不论 route 是啥 · await 返 reply."""
    default_reply: dict[str, Any] = reply or {"ok": True}

    def _resolver(_route: RouteDecision) -> ICCallable:
        async def _call(_r: RouteDecision) -> dict[str, Any]:
            return default_reply
        return _call

    return _resolver


__all__ = [
    "ExecutorConfig",
    "ICResolver",
    "TaskChainExecutor",
    "build_noop_resolver",
]


# Awaitable export for typing ergonomics
_unused_awaitable_alias = Awaitable  # noqa: F841 (keep name exposed implicitly)
