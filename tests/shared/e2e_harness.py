"""tests/shared/e2e_harness.py · 启动真 tick loop / step / tick_n(M3-WP01).

**定位**:
    给 acceptance 12 场景 + 大链路 integration 用的**真 tick 驱动器**.
    封装 L1-01 TickScheduler 的装配(真 L1-01 state_machine / decision_engine 用默认 stub 或
    测试注入) + step/tick_n 便捷 API + 隔离物理根 + 超时护栏.

**核心方法**:
    - harness.step()        单 tick(synchronous wrapper over tick_once)
    - harness.tick_n(n)     连续 N tick(供 acceptance scenario 驱动多步)
    - harness.events        所有 tick 产生的 TickEvent 列表
    - harness.panic(signal) 手动触发 IC-17 panic(acceptance_05 硬红线 100ms 约束用)
    - harness.state         当前 TickState(IDLE / RUNNING / PAUSED / HALTED)

**非目标**:
    - 不装配跨 L1 真实 SubAgent session(那是 WP09 深度集成)
    - 不跑真 LLM / 真 disk checkpoint(除非测试显式开启)

**用法(acceptance scenario_05 硬红线)**:
    async def test_panic_100ms(harness):
        harness.start()
        t0 = time.monotonic()
        res = await harness.panic()
        elapsed = (time.monotonic() - t0) * 1000
        assert elapsed < 100, f"panic to PAUSED took {elapsed}ms"
        assert harness.state == TickState.PAUSED
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

from app.main_loop.tick_scheduler import (
    PanicSignal,
    TickEvent,
    TickResult,
    TickScheduler,
    TickState,
)


def _normalize_pid_for_panic(pid: str) -> str:
    """PanicSignal 的 project_id 要求 `pid-*` 前缀 · 若不匹配则前置 `pid-`."""
    if pid.startswith("pid-"):
        return pid
    # 替换非法字符 · 保证前缀合法
    safe = pid.replace("_", "-")
    return f"pid-{safe}"


@dataclass
class E2EHarness:
    """封装 TickScheduler 的测试驱动器.

    **不是** 一个 subclass · 而是一个组合包装 · 让测试侧只需关心 step/tick_n.

    构造参数:
        scheduler: 已装配的 TickScheduler 实例(调 create_default 或自行装配).
        project_id: PM-14 根字段(与 scheduler 一致).
    """

    scheduler: TickScheduler
    project_id: str

    # ------------------------------------------------------------------
    # 单步 API
    # ------------------------------------------------------------------

    async def step(self) -> TickResult:
        """跑 1 tick · 返 TickResult(含 tick_seq / drift / action_dispatched)."""
        return await self.scheduler.tick_once()

    async def tick_n(self, n: int) -> list[TickResult]:
        """连续跑 n tick · 返 n 个 TickResult.

        每步之间不 asyncio.sleep(interval)· 立即相连, 仅校契约不校真实时序.
        acceptance 侧要精确时序应用 start() + 等待真 loop.
        """
        if n <= 0:
            raise ValueError(f"tick_n(n={n}) must be positive")
        out: list[TickResult] = []
        for _ in range(n):
            out.append(await self.scheduler.tick_once())
        return out

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """启动真 asyncio loop · 按 interval_ms 间隔持续 tick.

        仅推荐 acceptance 用 · integration TC 用 step / tick_n 即可.
        """
        await self.scheduler.start()

    async def stop(self) -> None:
        """停止 loop · 不 raise. 集成 TC teardown 必调."""
        await self.scheduler.stop()

    # ------------------------------------------------------------------
    # 快速路径 · IC-17 panic(≤ 100ms PAUSED 硬约束)
    # ------------------------------------------------------------------

    def panic(
        self,
        *,
        reason: str = "test_panic",
        user_id: str = "test-user",
    ) -> Any:
        """触发 IC-17 panic · scheduler → PAUSED.

        acceptance scenario_05 硬红线: panic_request_ts → PAUSED ts ≤ 100ms P99.
        """
        signal = PanicSignal(
            project_id=_normalize_pid_for_panic(self.project_id),
            panic_id=f"panic-{abs(id(self)) % 10**9}",
            reason=reason,
            user_id=user_id,
            ts=datetime.now(UTC).isoformat(),
        )
        # on_user_panic 是 sync 方法(仅调 panic_handler.handle)· 不 await
        return self.scheduler.on_user_panic(signal)

    def resume(self) -> Any:
        """panic 后手动 resume · 回到 IDLE / RUNNING(sync)."""
        return self.scheduler.resume_from_panic()

    # ------------------------------------------------------------------
    # Observers
    # ------------------------------------------------------------------

    @property
    def state(self) -> TickState:
        return self.scheduler.current_state

    @property
    def events(self) -> list[TickEvent]:
        return list(self.scheduler.events)

    @property
    def results(self) -> list[TickResult]:
        return list(self.scheduler.results)

    @property
    def drift_stats(self) -> dict[str, Any]:
        return dict(self.scheduler.drift_stats)

    @property
    def tick_seq(self) -> int:
        return self.scheduler.tick_seq


# =============================================================================
# Fixture · 按 project_id 装配 E2EHarness
# =============================================================================


@pytest.fixture
def e2e_harness(project_id: str) -> E2EHarness:
    """基础 E2EHarness fixture · stub engines · 供快速 tick 场景用.

    **PID 前缀一致**:
    - project_id fixture 默认 "proj-m3-shared"(适用 PM-14 shard 的通用格式)
    - 但 TickScheduler + PanicSignal 要求 `pid-*` 前缀
    - 所以 harness 内部用 `_normalize_pid_for_panic` 把所有 tick 相关 pid 统一到
      pid-* 格式 · 保持 scheduler / signal 两侧一致 · 避 cross-project 护栏误伤
    """
    tick_pid = _normalize_pid_for_panic(project_id)
    scheduler = TickScheduler.create_default(project_id=tick_pid)
    return E2EHarness(scheduler=scheduler, project_id=tick_pid)


@pytest.fixture
def e2e_harness_factory(project_id: str):
    """带参数的 harness 工厂 · 允许注入自定义组件."""
    def _factory(
        *,
        pid: str | None = None,
        interval_ms: int = 100,
        state_machine_orchestrator: Any = None,
        decision_engine: Any = None,
        state_reader: Any = None,
        action_dispatcher: Any = None,
    ) -> E2EHarness:
        tick_pid = _normalize_pid_for_panic(pid or project_id)
        scheduler = TickScheduler.create_default(
            project_id=tick_pid,
            interval_ms=interval_ms,
            state_machine_orchestrator=state_machine_orchestrator,
            decision_engine=decision_engine,
            state_reader=state_reader,
            action_dispatcher=action_dispatcher,
        )
        return E2EHarness(scheduler=scheduler, project_id=tick_pid)

    return _factory


# =============================================================================
# Timeout guard · 避免集成测试卡住 CI
# =============================================================================


async def run_with_timeout(coro: Any, *, timeout_s: float, description: str = "coro") -> Any:
    """便捷工具: 执行 coro · 超时则 raise pytest.fail · 默认 timeout 10s.

    给 acceptance scenario 的长链路加护栏:
        await run_with_timeout(harness.tick_n(50), timeout_s=5.0, description="tick_50")
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError as e:
        pytest.fail(f"{description} timed out after {timeout_s}s: {e}")
