"""WP05 · task_chain.task_spawner 用例.

覆盖:
    - spawn: 返回 TaskHandle · 加入 per-project 分片
    - get / iter_active / active_count / total_count
    - cancel_task: 单个 · 已 done/not-found 返 False
    - cancel_project: 批量抢占 (BLOCK)
    - forget: GC 移除
    - PM-14: project_id 空 → ValueError
    - PM-14: 跨 project 查不到
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.task_chain.schemas import RouteDecision
from app.main_loop.task_chain.task_spawner import TaskHandle, TaskSpawner


def _mk_route(project_id: str = "pid-X", wp_id: str | None = None) -> RouteDecision:
    return RouteDecision(
        decision_type="invoke_skill",
        target_l1="L1-05",
        ic_code="IC-04",
        ic_payload={"project_id": project_id, "capability": "x.y"},
        project_id=project_id,
        wp_id=wp_id,
    )


async def _fast_ic(_route: RouteDecision) -> dict:
    """立即完成的 mock IC."""
    return {"ok": True}


async def _slow_ic(_route: RouteDecision) -> dict:
    """等 1s 的 mock IC (测 cancel / iter_active 用)."""
    await asyncio.sleep(1.0)
    return {"ok": True}


class TestSpawnBasic:
    """spawn 基本流程."""

    async def test_TC_WP05_P01_spawn_returns_handle_with_project_id(self) -> None:
        """spawn 返回 TaskHandle · 字段齐."""
        spawner = TaskSpawner()
        route = _mk_route("pid-1", wp_id="wp-1")
        handle = spawner.spawn(route, _fast_ic)
        assert isinstance(handle, TaskHandle)
        assert handle.project_id == "pid-1"
        assert handle.wp_id == "wp-1"
        assert handle.decision_type == "invoke_skill"
        assert handle.task_id.startswith("task-")
        # 等 task 完成 · 避免未 await 警告
        reply = await handle.task
        assert reply == {"ok": True}

    async def test_TC_WP05_P02_spawn_custom_task_id(self) -> None:
        """spawn 支持自定义 task_id."""
        spawner = TaskSpawner()
        route = _mk_route("pid-2")
        handle = spawner.spawn(route, _fast_ic, task_id="custom-xyz")
        assert handle.task_id == "custom-xyz"
        await handle.task  # drain

    async def test_TC_WP05_P03_spawn_without_project_id_raises(self) -> None:
        """route.project_id 空 → ValueError (PM-14)."""
        spawner = TaskSpawner()
        route = RouteDecision(
            decision_type="invoke_skill",
            target_l1="L1-05",
            ic_code="IC-04",
            ic_payload={},
            project_id="",
        )
        with pytest.raises(ValueError, match="PM-14"):
            spawner.spawn(route, _fast_ic)


class TestSpawnerQuery:
    """get / iter_active / count."""

    async def test_TC_WP05_P10_get_finds_by_project_and_task_id(self) -> None:
        """get() 按 (project_id, task_id) 命中."""
        spawner = TaskSpawner()
        handle = spawner.spawn(_mk_route("pid-10"), _slow_ic)
        found = spawner.get(handle.task_id, project_id="pid-10")
        assert found is handle
        handle.cancel()
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await handle.task

    async def test_TC_WP05_P11_get_wrong_project_returns_none(self) -> None:
        """跨 project 查 task_id → None (PM-14 隔离)."""
        spawner = TaskSpawner()
        handle = spawner.spawn(_mk_route("pid-A"), _slow_ic)
        assert spawner.get(handle.task_id, project_id="pid-B") is None
        handle.cancel()
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await handle.task

    async def test_TC_WP05_P12_iter_active_excludes_done(self) -> None:
        """done 的 task 不在 iter_active 里."""
        spawner = TaskSpawner()
        h_fast = spawner.spawn(_mk_route("pid-12"), _fast_ic)
        h_slow = spawner.spawn(_mk_route("pid-12"), _slow_ic)
        # 等 fast 完成
        await h_fast.task
        # 给事件循环一拍让 done 状态稳定
        await asyncio.sleep(0)
        active = spawner.iter_active("pid-12")
        active_ids = {h.task_id for h in active}
        assert h_slow.task_id in active_ids
        assert h_fast.task_id not in active_ids
        assert spawner.active_count("pid-12") == 1
        assert spawner.total_count("pid-12") == 2
        h_slow.cancel()
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await h_slow.task


class TestSpawnerCancel:
    """cancel_task / cancel_project."""

    async def test_TC_WP05_P20_cancel_task_running_returns_true(self) -> None:
        """cancel 运行中 task · 返 True."""
        spawner = TaskSpawner()
        handle = spawner.spawn(_mk_route("pid-20"), _slow_ic)
        ok = spawner.cancel_task(handle.task_id, project_id="pid-20")
        assert ok is True
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await handle.task

    async def test_TC_WP05_P21_cancel_task_not_found_returns_false(self) -> None:
        """task_id 不存在 → False."""
        spawner = TaskSpawner()
        assert spawner.cancel_task("ghost-id", project_id="pid-21") is False

    async def test_TC_WP05_P22_cancel_project_cancels_all(self) -> None:
        """cancel_project 批量取消 · 返被取消数."""
        spawner = TaskSpawner()
        h1 = spawner.spawn(_mk_route("pid-22"), _slow_ic)
        h2 = spawner.spawn(_mk_route("pid-22"), _slow_ic)
        # pid-other 不受影响
        h3 = spawner.spawn(_mk_route("pid-other"), _slow_ic)
        n = spawner.cancel_project("pid-22")
        assert n == 2
        # drain
        for h in (h1, h2):
            with pytest.raises((asyncio.CancelledError, BaseException)):
                await h.task
        h3.cancel()
        with pytest.raises((asyncio.CancelledError, BaseException)):
            await h3.task

    async def test_TC_WP05_P23_cancel_done_returns_false(self) -> None:
        """已 done 的 task · cancel 返 False."""
        spawner = TaskSpawner()
        handle = spawner.spawn(_mk_route("pid-23"), _fast_ic)
        await handle.task
        await asyncio.sleep(0)
        ok = spawner.cancel_task(handle.task_id, project_id="pid-23")
        assert ok is False


class TestSpawnerForget:
    """forget / GC."""

    async def test_TC_WP05_P30_forget_removes_entry(self) -> None:
        """forget 从 pool 移除 task."""
        spawner = TaskSpawner()
        handle = spawner.spawn(_mk_route("pid-30"), _fast_ic)
        await handle.task
        assert spawner.total_count("pid-30") == 1
        ok = spawner.forget(handle.task_id, project_id="pid-30")
        assert ok is True
        assert spawner.total_count("pid-30") == 0

    async def test_TC_WP05_P31_forget_unknown_returns_false(self) -> None:
        """forget 不存在的 task → False."""
        spawner = TaskSpawner()
        assert spawner.forget("ghost", project_id="pid-31") is False
