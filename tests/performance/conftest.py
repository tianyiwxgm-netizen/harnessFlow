"""tests/performance · 共享 fixtures · warmup / stable_load / latency_collector.

铁律:
- 真实 import L1 模块 · 不 mock 跨 L2 边界
- 每 TC tmp_path 独立 · pid 命名安全 (PM-14 ^[a-z0-9_-]{1,40}$)
- warmup 50 次消除 JIT/cache 冷启动 · stable_load 让系统进 steady state

所有 SLO 测试都标 @pytest.mark.perf · 性能可能不稳但容忍 0% flake.
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.perf_helpers import LatencyStats


@pytest.fixture
def perf_project_id() -> str:
    """性能测试 project_id · 8 位 hex 后缀避冲突."""
    return f"perf-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def perf_pid_dashes() -> str:
    """panic_handler schema 要求 ^pid-... · 单独的 pid fixture."""
    return f"pid-perf-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def perf_bus_root(tmp_path: Path) -> Path:
    """L1-09 EventBus 根目录 · 每 TC 隔离."""
    return tmp_path / "perf_bus"


@pytest.fixture
def perf_event_bus(perf_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · 性能场景共享."""
    return EventBus(perf_bus_root)


@pytest.fixture
def warmup_event_bus(perf_event_bus: EventBus, perf_project_id: str) -> EventBus:
    """warmup 50 次 dummy event · 消除 JIT/cache 冷启动 · 用于稳定 P99."""
    for i in range(50):
        evt = Event(
            project_id=perf_project_id,
            type="L1-01:decision_made",
            actor="main_loop",
            payload={"warmup_idx": i},
            timestamp=datetime.now(UTC),
        )
        perf_event_bus.append(evt)
    return perf_event_bus


@pytest.fixture
def latency_collector():
    """收集 latency_ms 列表 · 末尾返 LatencyStats · 一次性使用."""
    samples_ms: list[float] = []

    def _collect(ms: float) -> None:
        samples_ms.append(ms)

    _collect.samples = samples_ms  # type: ignore[attr-defined]
    return _collect


def latencies_to_stats(samples_ms: list[float]) -> LatencyStats:
    """list[float ms] → LatencyStats · 用 LatencySample 封装."""
    from tests.shared.perf_helpers import LatencySample

    return LatencyStats.compute([LatencySample(elapsed_ms=v) for v in samples_ms])


# Make latencies_to_stats available without import (re-exported)
@pytest.fixture
def to_stats():
    """convert list[float ms] → LatencyStats · fixture 入口."""
    return latencies_to_stats


@pytest.fixture
def perf_now_iso():
    """ISO timestamp 工厂 · panic / halt schema 要求 ts 字段."""

    def _now() -> str:
        return datetime.now(UTC).isoformat()

    return _now


def measure_call_ms(fn, *args, **kwargs) -> tuple[float, object]:
    """sync function 执行延时 · 返 (ms, payload).

    用于性能测试核心循环 · 不引入 asyncio overhead.
    """
    t0 = time.perf_counter()
    payload = fn(*args, **kwargs)
    return (time.perf_counter() - t0) * 1000.0, payload


@pytest.fixture
def measure_ms():
    """fixture 入口 · sync 调用计时."""
    return measure_call_ms
