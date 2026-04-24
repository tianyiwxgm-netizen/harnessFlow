"""WP05 · TaskChainExecutor.execute() 集成用例.

覆盖:
    - 正向: ChosenAction → RouteDecision → TaskHandle → TaskStatus 推进
    - 反向: RouterError / ic_resolver fail → accepted=False + rejection_reason
    - 状态机: total_dispatched / total_completed / total_failed / consecutive_failures
    - BLOCK 抢占: cancel_project_tasks
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
from app.main_loop.task_chain.schemas import RouteDecision, TaskStatus
from app.main_loop.task_chain.task_spawner import ICCallable


def _mk_action(dt: str, params: dict | None = None) -> ChosenAction:
    return ChosenAction(
        decision_type=dt,
        decision_params=params or {},
        final_score=0.8,
        kb_boost=0.0,
        history_weight=0.0,
        base_score=0.8,
        reason="synthesized chosen action for executor tests",
    )


# ---- resolvers ----

def _make_echo_resolver(reply: dict) -> ExecutorConfig:
    return ExecutorConfig(ic_resolver=build_noop_resolver(reply))


def _make_raising_resolver(exc: Exception) -> ExecutorConfig:
    def _resolver(_route: RouteDecision) -> ICCallable:
        async def _call(_r: RouteDecision) -> dict:
            raise exc
        return _call
    return ExecutorConfig(ic_resolver=_resolver)


def _make_slow_resolver(sleep_s: float = 1.0) -> ExecutorConfig:
    def _resolver(_route: RouteDecision) -> ICCallable:
        async def _call(_r: RouteDecision) -> dict:
            await asyncio.sleep(sleep_s)
            return {"ok": True}
        return _call
    return ExecutorConfig(ic_resolver=_resolver)


# ==========================================================
# 正向
# ==========================================================


class TestExecutePositive:
    """ChosenAction → dispatch 成功路径."""

    async def test_TC_WP05_E01_invoke_skill_accepted(self) -> None:
        """invoke_skill 路由 + 派发 · accepted=True."""
        cfg = _make_echo_resolver({"result": {"foo": "bar"}})
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "dod.lint"})
        result = await executor.execute(action, project_id="pid-E01")
        assert result.accepted is True
        assert result.task_id is not None
        assert result.route is not None
        assert result.route.ic_code == "IC-04"
        assert result.rejection_reason is None
        # drain task
        handle = executor.spawner.get(result.task_id, project_id="pid-E01")
        assert handle is not None
        await handle.task
        await asyncio.sleep(0)  # 让 done_callback 跑一拍

    async def test_TC_WP05_E02_state_registered_as_running_then_completed(
        self,
    ) -> None:
        """派发后 state.tasks[task_id].status == RUNNING → done 后 COMPLETED."""
        executor = TaskChainExecutor(config=_make_echo_resolver({"ok": True}))
        action = _mk_action("assign_wp", {"wp_id": "wp-1"})
        result = await executor.execute(action, project_id="pid-E02")
        state = executor.get_state("pid-E02")
        # 派发时登记 RUNNING
        entry = state.tasks[result.task_id]
        assert entry["status"] in {TaskStatus.RUNNING, TaskStatus.COMPLETED}
        # 等 task done
        handle = executor.spawner.get(result.task_id, project_id="pid-E02")
        await handle.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        assert state.get_status(result.task_id) == TaskStatus.COMPLETED
        assert state.total_completed == 1
        assert state.consecutive_failures == 0

    async def test_TC_WP05_E03_await_result_returns_ic_reply(self) -> None:
        """await_result=True · TaskChainResult.ic_reply 有值."""
        cfg = _make_echo_resolver({"x": 42})
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "p.q"})
        result = await executor.execute(
            action, project_id="pid-E03", await_result=True,
        )
        assert result.accepted is True
        assert result.ic_reply == {"x": 42}

    async def test_TC_WP05_E04_decision_id_propagated_into_route(self) -> None:
        """decision_id 透传到 RouteDecision."""
        cfg = _make_echo_resolver({})
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(
            action, project_id="pid-E04", decision_id="dec-xyz",
        )
        assert result.route is not None
        assert result.route.decision_id == "dec-xyz"
        handle = executor.spawner.get(result.task_id, project_id="pid-E04")
        assert handle is not None
        await handle.task
        await asyncio.sleep(0)


# ==========================================================
# 反向
# ==========================================================


class TestExecuteNegative:
    """路由前拒绝 · accepted=False."""

    async def test_TC_WP05_E10_no_project_id_rejected(self) -> None:
        """project_id 空 → E_CHAIN_NO_PROJECT_ID · accepted=False."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(action, project_id="")
        assert result.accepted is False
        assert result.rejection_reason == "E_CHAIN_NO_PROJECT_ID"
        assert result.task_id is None

    async def test_TC_WP05_E11_action_unsupported_rejected(self) -> None:
        """decision_type=no_op 不在 routable → E_CHAIN_ACTION_UNSUPPORTED."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        action = _mk_action("no_op", {})
        result = await executor.execute(action, project_id="pid-E11")
        assert result.accepted is False
        assert result.rejection_reason == "E_CHAIN_ACTION_UNSUPPORTED"

    async def test_TC_WP05_E12_cross_project_rejected(self) -> None:
        """params.project_id ≠ ctx.project_id → E_CHAIN_CROSS_PROJECT."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        action = _mk_action(
            "invoke_skill",
            {"capability": "x", "project_id": "pid-OTHER"},
        )
        result = await executor.execute(action, project_id="pid-E12")
        assert result.accepted is False
        assert result.rejection_reason == "E_CHAIN_CROSS_PROJECT"

    async def test_TC_WP05_E13_def_invalid_assign_wp_no_wp_id(self) -> None:
        """assign_wp 缺 wp_id → E_CHAIN_DEF_INVALID."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        action = _mk_action("assign_wp", {})
        result = await executor.execute(action, project_id="pid-E13")
        assert result.accepted is False
        assert result.rejection_reason == "E_CHAIN_DEF_INVALID"


# ==========================================================
# 状态机 / 计数器
# ==========================================================


class TestExecutorState:
    """state.consecutive_failures / totals 推进."""

    async def test_TC_WP05_E20_total_dispatched_increments(self) -> None:
        """每次 accepted=True 派发 · total_dispatched += 1."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        for _ in range(3):
            action = _mk_action("invoke_skill", {"capability": "x"})
            await executor.execute(action, project_id="pid-E20")
        state = executor.get_state("pid-E20")
        assert state.total_dispatched == 3
        # drain active tasks
        for h in executor.spawner.iter_active("pid-E20"):
            await h.task
        await asyncio.sleep(0)

    async def test_TC_WP05_E21_rejected_does_not_increment_dispatched(
        self,
    ) -> None:
        """rejected 不计 total_dispatched."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        action = _mk_action("no_op", {})  # will be rejected
        await executor.execute(action, project_id="pid-E21")
        state = executor.get_state("pid-E21")
        assert state.total_dispatched == 0

    async def test_TC_WP05_E22_failure_increments_counters(self) -> None:
        """下游抛异常 → total_failed++ · consecutive_failures++."""
        cfg = _make_raising_resolver(ValueError("downstream boom"))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(action, project_id="pid-E22")
        assert result.accepted is True
        handle = executor.spawner.get(result.task_id, project_id="pid-E22")
        assert handle is not None
        # 等 task 结束 · 允许异常
        with pytest.raises(Exception):  # noqa: B017, BLE001
            await handle.task
        await asyncio.sleep(0)
        state = executor.get_state("pid-E22")
        assert state.total_failed == 1
        assert state.consecutive_failures == 1
        assert state.get_status(result.task_id) == TaskStatus.FAILED

    async def test_TC_WP05_E23_success_resets_consecutive_failures(self) -> None:
        """成功后 consecutive_failures 归零."""
        # 先失败一次
        fail_cfg = _make_raising_resolver(ValueError("x"))
        executor = TaskChainExecutor(config=fail_cfg)
        action1 = _mk_action("invoke_skill", {"capability": "x"})
        r1 = await executor.execute(action1, project_id="pid-E23")
        h1 = executor.spawner.get(r1.task_id, project_id="pid-E23")
        with pytest.raises(Exception):  # noqa: B017
            await h1.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        st = executor.get_state("pid-E23")
        assert st.consecutive_failures == 1

        # 换成功 resolver · 重建 executor (复用 state)
        executor.config = _make_echo_resolver({"ok": True})
        action2 = _mk_action("invoke_skill", {"capability": "y"})
        r2 = await executor.execute(action2, project_id="pid-E23")
        h2 = executor.spawner.get(r2.task_id, project_id="pid-E23")
        await h2.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        assert st.consecutive_failures == 0
        assert st.total_completed == 1


# ==========================================================
# BLOCK 抢占 · cancel_project_tasks
# ==========================================================


class TestExecutorCancel:
    """BLOCK 抢占 · cancel_project_tasks."""

    async def test_TC_WP05_E30_cancel_project_cancels_running(self) -> None:
        """cancel_project_tasks 取消 project 全部 running task."""
        executor = TaskChainExecutor(config=_make_slow_resolver(1.0))
        action = _mk_action("invoke_skill", {"capability": "x"})
        r1 = await executor.execute(action, project_id="pid-E30")
        r2 = await executor.execute(action, project_id="pid-E30")
        assert r1.accepted and r2.accepted
        n = executor.cancel_project_tasks("pid-E30")
        assert n == 2
        # drain cancelled tasks
        for tid in (r1.task_id, r2.task_id):
            h = executor.spawner.get(tid, project_id="pid-E30")
            with pytest.raises((asyncio.CancelledError, BaseException)):
                await h.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        state = executor.get_state("pid-E30")
        assert state.get_status(r1.task_id) == TaskStatus.CANCELED
        assert state.get_status(r2.task_id) == TaskStatus.CANCELED

    async def test_TC_WP05_E31_cancel_does_not_bump_consecutive_failures(
        self,
    ) -> None:
        """CANCELED 不计入 consecutive_failures (主动取消不算失败)."""
        executor = TaskChainExecutor(config=_make_slow_resolver(1.0))
        action = _mk_action("invoke_skill", {"capability": "x"})
        r = await executor.execute(action, project_id="pid-E31")
        executor.cancel_project_tasks("pid-E31")
        h = executor.spawner.get(r.task_id, project_id="pid-E31")
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await h.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        state = executor.get_state("pid-E31")
        assert state.consecutive_failures == 0
        assert state.total_failed == 0


# ==========================================================
# 多 project 隔离
# ==========================================================


class TestExecutorPM14:
    """PM-14 · 多 project 隔离."""

    async def test_TC_WP05_E40_states_per_project_isolated(self) -> None:
        """get_state 按 project_id 分片 · 互不影响."""
        executor = TaskChainExecutor(config=_make_echo_resolver({}))
        a = _mk_action("invoke_skill", {"capability": "x"})
        await executor.execute(a, project_id="pid-A")
        await executor.execute(a, project_id="pid-B")
        sa = executor.get_state("pid-A")
        sb = executor.get_state("pid-B")
        assert sa.total_dispatched == 1
        assert sb.total_dispatched == 1
        assert sa.project_id == "pid-A"
        assert sb.project_id == "pid-B"
        for h in executor.spawner.iter_active("pid-A"):
            await h.task
        for h in executor.spawner.iter_active("pid-B"):
            await h.task
        await asyncio.sleep(0)
