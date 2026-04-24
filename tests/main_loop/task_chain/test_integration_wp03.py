"""WP05 · 与 WP03 ChosenAction 真实集成 · 端到端 sanity.

覆盖:
    - decide() → ChosenAction → execute() → RouteDecision
    - 显式 raise asyncio.CancelledError → DOWNSTREAM_CANCELLED (补 cov 第 196 行)
    - 全部 4 decision_type 真实 IC 路由 sanity
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
        final_score=0.9,
        kb_boost=0.1,
        history_weight=0.05,
        base_score=0.75,
        reason="integration sanity chosen action",
    )


class TestExecuteAllFourDecisionTypes:
    """4 类 decision_type 均可路由 · 派发成功."""

    async def test_TC_WP05_I01_state_transition_dispatch(self) -> None:
        cfg = ExecutorConfig(ic_resolver=build_noop_resolver({"transitioned": True}))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action(
            "state_transition",
            {
                "from_state": "S1_plan",
                "to_state": "S2_impl",
                "reason": "plan signed · enter impl stage via stage gate",
                "evidence_refs": ["ev-1"],
                "gate_id": "gate-0",
            },
        )
        result = await executor.execute(
            action, project_id="pid-I01", await_result=True,
        )
        assert result.accepted is True
        assert result.route is not None
        assert result.route.target_l1 == "L1-02"
        assert result.ic_reply == {"transitioned": True}

    async def test_TC_WP05_I02_get_next_wp_dispatch(self) -> None:
        cfg = ExecutorConfig(ic_resolver=build_noop_resolver({"wp_id": "wp-x"}))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action(
            "get_next_wp",
            {"query_id": "q-1", "requester_tick": "t-1"},
        )
        result = await executor.execute(
            action, project_id="pid-I02", await_result=True,
        )
        assert result.route is not None
        assert result.route.target_l1 == "L1-03"
        assert result.route.ic_code == "IC-02"

    async def test_TC_WP05_I03_assign_wp_dispatch(self) -> None:
        cfg = ExecutorConfig(ic_resolver=build_noop_resolver({"assigned": True}))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("assign_wp", {"wp_id": "wp-1", "assignee": "agentA"})
        result = await executor.execute(
            action, project_id="pid-I03", await_result=True,
        )
        assert result.route is not None
        assert result.route.target_l1 == "L1-03"
        assert result.route.ic_code == "IC-03"
        assert result.route.wp_id == "wp-1"

    async def test_TC_WP05_I04_invoke_skill_dispatch(self) -> None:
        cfg = ExecutorConfig(ic_resolver=build_noop_resolver({"skill_result": "ok"}))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action(
            "invoke_skill",
            {"capability": "dod.lint", "invocation_id": "inv-1"},
        )
        result = await executor.execute(
            action, project_id="pid-I04", await_result=True,
        )
        assert result.route is not None
        assert result.route.target_l1 == "L1-05"


class TestDoneCallbackCancelled:
    """显式 asyncio.CancelledError · 覆盖 DOWNSTREAM_CANCELLED 分支."""

    async def test_TC_WP05_I10_explicit_cancelled_error_marks_canceled(
        self,
    ) -> None:
        """task body 主动 raise CancelledError · done_callback 经 classify 走 CANCELED 分支."""

        def _self_cancel_resolver(_route: RouteDecision) -> ICCallable:
            async def _call(_r: RouteDecision) -> dict:
                # 手动 raise CancelledError 模拟 asyncio 取消语义
                raise asyncio.CancelledError()
            return _call

        cfg = ExecutorConfig(ic_resolver=_self_cancel_resolver)
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x.y"})
        result = await executor.execute(action, project_id="pid-I10")
        assert result.accepted is True
        handle = executor.spawner.get(result.task_id, project_id="pid-I10")
        # 等 task done
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await handle.task  # type: ignore[union-attr]
        await asyncio.sleep(0)
        state = executor.get_state("pid-I10")
        assert state.get_status(result.task_id) == TaskStatus.CANCELED
        # CANCELED 不计 consecutive_failures
        assert state.consecutive_failures == 0
        assert state.total_failed == 0


class TestResultImmutability:
    """TaskChainResult 冻结 · 保审计完整性."""

    async def test_TC_WP05_I20_result_route_frozen(self) -> None:
        cfg = ExecutorConfig(ic_resolver=build_noop_resolver({}))
        executor = TaskChainExecutor(config=cfg)
        action = _mk_action("invoke_skill", {"capability": "x"})
        result = await executor.execute(
            action, project_id="pid-I20", await_result=True,
        )
        # RouteDecision frozen
        import dataclasses
        assert result.route is not None
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.route.ic_code = "IC-99"  # type: ignore[misc]
