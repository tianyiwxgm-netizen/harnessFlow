"""IC-16 · task_chain_step 集成测试 · 5 TC.

(WP04 任务表 IC-16 重映射 = main-2 L1-01 TaskChainExecutor.execute 任务链推进)

覆盖:
    TC-1 链推进: ChosenAction → RouteDecision → 派发 (accepted=True · task_id)
    TC-2 暂停: 不支持的 decision_type (router 拒绝) → accepted=False + 错误码
    TC-3 恢复: 同 project_id 多次 dispatch · state 计数累加
    TC-4 失败回退: ic_resolver 抛异常 · 同步等 → state.total_failed++
    TC-5 幂等: 路由前拒绝 (空 pid) → 不创 state 不计 dispatched
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.task_chain.schemas import TaskStatus

from .conftest import make_action, make_echo_config, make_raising_config


def run_async(coro):
    return asyncio.run(coro)


class TestIC16Integration:
    """IC-16 集成 · TaskChainExecutor 任务链推进."""

    # ---- TC-1 · 链推进: ChosenAction → 派发成功 ----
    def test_chain_step_invoke_skill_accepted(
        self, executor, project_id: str,
    ) -> None:
        action = make_action("invoke_skill", {"capability": "dod.lint"})

        async def _go():
            result = await executor.execute(action, project_id=project_id)
            # drain task
            handle = executor.spawner.get(result.task_id, project_id=project_id)
            if handle:
                await handle.task
            return result

        result = run_async(_go())

        assert result.accepted is True
        assert result.task_id is not None
        assert result.route is not None
        assert result.route.ic_code == "IC-04"  # invoke_skill → IC-04
        assert result.rejection_reason is None

        state = executor.get_state(project_id)
        assert state.total_dispatched == 1

    # ---- TC-2 · 暂停: 不支持的 decision_type → router 拒 ----
    def test_unsupported_decision_type_rejected(
        self, executor, project_id: str,
    ) -> None:
        # decision_type 在 12 类内但非 routable (router only routes 4 types)
        action = make_action("kb_read", {"query": "x"})

        result = run_async(executor.execute(action, project_id=project_id))

        # WP05 router 只路由 4 类 (state_transition / get_next_wp / assign_wp / invoke_skill)
        # · kb_read 不在 routable
        assert result.accepted is False
        assert result.rejection_reason is not None
        assert result.rejection_reason.startswith("E_CHAIN_")

    # ---- TC-3 · 恢复: 多次 dispatch · state 累加 ----
    def test_multi_dispatch_state_accumulates(
        self, executor, project_id: str,
    ) -> None:
        async def _go():
            results = []
            for i in range(3):
                action = make_action(
                    "invoke_skill", {"capability": f"cap-{i}"},
                )
                r = await executor.execute(action, project_id=project_id)
                results.append(r)
                handle = executor.spawner.get(r.task_id, project_id=project_id)
                if handle:
                    await handle.task
            return results

        results = run_async(_go())

        assert all(r.accepted is True for r in results)
        state = executor.get_state(project_id)
        assert state.total_dispatched == 3
        # 同 project_id 的所有 task 都在该 state
        assert len(state.tasks) == 3

    # ---- TC-4 · 失败回退: ic_resolver 抛 → state.total_failed++ ----
    def test_ic_resolver_exception_records_failure(
        self, executor_factory, project_id: str,
    ) -> None:
        cfg = make_raising_config(RuntimeError("downstream L1 broken"))
        executor = executor_factory(cfg)

        action = make_action("invoke_skill", {"capability": "x"})

        async def _go():
            result = await executor.execute(action, project_id=project_id)
            # 等异步 task 完成
            if result.task_id:
                handle = executor.spawner.get(
                    result.task_id, project_id=project_id,
                )
                if handle:
                    # task.exception() 会捕获异常 · done callback 推进 state.FAILED
                    try:
                        await handle.task
                    except Exception:
                        pass
            # 让 done_callback 跑
            await asyncio.sleep(0.01)
            return result

        result = run_async(_go())

        # accepted=True (派发成功 · 异常在 task 内部)
        assert result.accepted is True
        state = executor.get_state(project_id)
        # done_callback 把 task 标记为 FAILED
        assert state.total_failed >= 1

    # ---- TC-5 · 幂等: 空 pid 路由前拒绝 → 不创 state ----
    def test_empty_pid_rejected_does_not_create_state(
        self, executor,
    ) -> None:
        action = make_action("invoke_skill", {"capability": "x"})

        # 空 pid · router 拒绝 (PM-14 守护)
        result = run_async(executor.execute(action, project_id=""))

        assert result.accepted is False
        assert result.rejection_reason is not None
        # router 拒绝阶段 · 不应创建空 pid 的脏 state bucket
        assert "" not in executor.states
