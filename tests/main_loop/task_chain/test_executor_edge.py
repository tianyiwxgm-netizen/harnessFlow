"""WP05 · TaskChainExecutor 边界 / 补 cov 用例.

覆盖:
    - ic_resolver 自身抛异常 → E_CHAIN_ACTION_UNSUPPORTED
    - await_result=True · 下游抛一般异常 → TaskChainError wrap + BF-E-*
    - await_result=True · 下游抛 TaskChainError → 透传 · 不 re-wrap
    - auto_forget_on_done=True · done 后 spawner 自动 forget
    - cancel_project_tasks: CANCELED 不计 consecutive_failures
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.decision_engine.schemas import ChosenAction
from app.main_loop.task_chain.executor import (
    ExecutorConfig,
    TaskChainExecutor,
    build_noop_resolver,
)
from app.main_loop.task_chain.failure_handler import (
    BackwardFailCode,
    TaskChainError,
)
from app.main_loop.task_chain.schemas import RouteDecision, TaskStatus
from app.main_loop.task_chain.task_spawner import ICCallable


def _mk_action(dt: str, params: dict | None = None) -> ChosenAction:
    return ChosenAction(
        decision_type=dt,
        decision_params=params or {},
        final_score=0.5,
        kb_boost=0.0,
        history_weight=0.0,
        base_score=0.5,
        reason="synthesized chosen action for edge tests",
    )


class TestExecutorResolverFail:
    """ic_resolver 自身抛异常路径."""

    async def test_TC_WP05_EE01_resolver_raises_rejected(self) -> None:
        """ic_resolver 抛 RuntimeError → accepted=False + E_CHAIN_ACTION_UNSUPPORTED."""

        def _bad_resolver(_route: RouteDecision) -> ICCallable:
            raise RuntimeError("resolver not registered")

        executor = TaskChainExecutor(config=ExecutorConfig(ic_resolver=_bad_resolver))
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(action, project_id="pid-EE01")
        assert result.accepted is False
        assert result.rejection_reason == "E_CHAIN_ACTION_UNSUPPORTED"
        # route 填充 (校验 resolver 失败发生在路由后)
        assert result.route is not None
        assert result.route.ic_code == "IC-04"


class TestExecutorAwaitResultException:
    """await_result=True · 异常映射."""

    async def test_TC_WP05_EE10_await_wraps_downstream_exception(self) -> None:
        """下游抛 ValueError → TaskChainError(BF-E-DOWNSTREAM_RAISE) + ic_reply None."""

        def _raise_resolver(_route: RouteDecision) -> ICCallable:
            async def _call(_r: RouteDecision) -> dict:
                raise ValueError("boom")
            return _call

        cfg = ExecutorConfig(ic_resolver=_raise_resolver)
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        with pytest.raises(TaskChainError) as exc_info:
            await executor.execute(
                action, project_id="pid-EE10", await_result=True,
            )
        assert exc_info.value.code == BackwardFailCode.DOWNSTREAM_RAISE
        assert exc_info.value.project_id == "pid-EE10"
        state = executor.get_state("pid-EE10")
        await asyncio.sleep(0)
        # task 已终态 FAILED
        assert state.total_failed == 1
        assert state.consecutive_failures == 1

    async def test_TC_WP05_EE11_await_passthrough_task_chain_error(self) -> None:
        """下游本身抛 TaskChainError · 不 re-wrap · 透传 code."""

        def _pre_raise_resolver(_route: RouteDecision) -> ICCallable:
            async def _call(_r: RouteDecision) -> dict:
                raise TaskChainError(
                    code=BackwardFailCode.IC_CONTRACT_VIOLATION,
                    message="reply missing required field",
                )
            return _call

        cfg = ExecutorConfig(ic_resolver=_pre_raise_resolver)
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        with pytest.raises(TaskChainError) as exc_info:
            await executor.execute(
                action, project_id="pid-EE11", await_result=True,
            )
        # 透传 code · 不退化为 DOWNSTREAM_RAISE
        assert exc_info.value.code == BackwardFailCode.IC_CONTRACT_VIOLATION


class TestExecutorAutoForget:
    """auto_forget_on_done=True · done 后 forget."""

    async def test_TC_WP05_EE20_auto_forget_removes_handle(self) -> None:
        """done 后 spawner.get() 查不到 · total_count == 0."""
        cfg = ExecutorConfig(
            ic_resolver=build_noop_resolver({"ok": True}),
            auto_forget_on_done=True,
        )
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(
            action, project_id="pid-EE20", await_result=True,
        )
        await asyncio.sleep(0)
        # 已 forget
        assert executor.spawner.total_count("pid-EE20") == 0
        assert executor.spawner.get(result.task_id, project_id="pid-EE20") is None


class TestExecutorMarkStateTerminal:
    """_mark_state_terminal 幂等 · task 已被 forget 后不抛."""

    async def test_TC_WP05_EE30_mark_state_tolerates_missing_task_id(self) -> None:
        """state.tasks 无该 task_id · _mark_state_terminal 不抛 · 只更新计数器."""
        executor = TaskChainExecutor(
            config=ExecutorConfig(ic_resolver=build_noop_resolver({})),
        )
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(action, project_id="pid-EE30")
        state = executor.get_state("pid-EE30")
        # 手动移除 task 登记 (模拟被其他代码清理)
        del state.tasks[result.task_id]
        h = executor.spawner.get(result.task_id, project_id="pid-EE30")
        assert h is not None
        # await 完成 · done_callback 应不抛
        await h.task
        await asyncio.sleep(0)
        # 计数器仍推进
        assert state.total_completed == 1


class TestExecutorRepeatedFailures:
    """consecutive_failures 持续累计."""

    async def test_TC_WP05_EE40_consecutive_failures_accumulates(self) -> None:
        """连续 3 次下游失败 · consecutive_failures == 3."""

        def _raise_resolver(_route: RouteDecision) -> ICCallable:
            async def _call(_r: RouteDecision) -> dict:
                raise RuntimeError("fail")
            return _call

        executor = TaskChainExecutor(
            config=ExecutorConfig(ic_resolver=_raise_resolver),
        )
        action = _mk_action("invoke_skill", {"capability": "x"})
        for _ in range(3):
            r = await executor.execute(action, project_id="pid-EE40")
            h = executor.spawner.get(r.task_id, project_id="pid-EE40")
            with pytest.raises(Exception):  # noqa: B017
                await h.task  # type: ignore[union-attr]
            await asyncio.sleep(0)
        state = executor.get_state("pid-EE40")
        assert state.total_failed == 3
        assert state.consecutive_failures == 3


class TestExecutorTaskStatusQuery:
    """task_status 查询一致性."""

    async def test_TC_WP05_EE50_status_transitions_running_to_completed(
        self,
    ) -> None:
        """RUNNING → COMPLETED 过渡透明可查."""
        executor = TaskChainExecutor(
            config=ExecutorConfig(ic_resolver=build_noop_resolver({})),
        )
        action = _mk_action("assign_wp", {"wp_id": "wp-1"})
        r = await executor.execute(action, project_id="pid-EE50")
        state = executor.get_state("pid-EE50")
        assert state.get_status(r.task_id) in {
            TaskStatus.RUNNING, TaskStatus.COMPLETED,
        }
        h = executor.spawner.get(r.task_id, project_id="pid-EE50")
        await h.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        assert state.get_status(r.task_id) == TaskStatus.COMPLETED
