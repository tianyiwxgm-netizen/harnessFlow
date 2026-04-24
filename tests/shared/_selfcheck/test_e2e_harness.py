"""Smoke: e2e_harness 单步 / tick_n / panic 路径."""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler import TickState
from tests.shared.e2e_harness import E2EHarness, run_with_timeout


@pytest.mark.asyncio
async def test_harness_step_returns_tick_result(e2e_harness: E2EHarness) -> None:
    res = await e2e_harness.step()
    assert res.tick_id is not None
    assert e2e_harness.tick_seq == 1


@pytest.mark.asyncio
async def test_harness_tick_n(e2e_harness: E2EHarness) -> None:
    results = await e2e_harness.tick_n(3)
    assert len(results) == 3
    # tick_id 格式与 scheduler 内部一致 · 不直接断言具体值
    assert all(r.tick_id is not None for r in results)
    assert e2e_harness.tick_seq == 3


@pytest.mark.asyncio
async def test_harness_tick_n_rejects_zero(e2e_harness: E2EHarness) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        await e2e_harness.tick_n(0)


@pytest.mark.asyncio
async def test_harness_panic_pauses(e2e_harness: E2EHarness) -> None:
    await e2e_harness.step()
    e2e_harness.panic(reason="test_pause")
    assert e2e_harness.state == TickState.PAUSED


@pytest.mark.asyncio
async def test_harness_factory_custom_pid(e2e_harness_factory) -> None:
    # harness 会自动把 proj-* 归一到 pid-* 以过 PanicSignal 护栏
    h = e2e_harness_factory(pid="proj-custom")
    assert h.project_id == "pid-proj-custom"
    await h.step()
    assert h.tick_seq == 1


@pytest.mark.asyncio
async def test_run_with_timeout_passes_through() -> None:
    async def _ok() -> int:
        return 42

    assert await run_with_timeout(_ok(), timeout_s=1.0, description="ok") == 42


@pytest.mark.asyncio
async def test_run_with_timeout_fails_on_timeout() -> None:
    import asyncio as _asyncio

    async def _slow() -> None:
        await _asyncio.sleep(0.5)

    import _pytest.outcomes as _outcomes
    with pytest.raises(_outcomes.Failed, match="timed out"):
        await run_with_timeout(_slow(), timeout_s=0.05, description="slow")
