"""LKG (Last-Known-Good) cache 契约测试。

- per-project 单槽位 · put 覆盖旧 snapshot
- TTL 默认 60s · 超时返 is_stale=True
- FrozenClock 驱动确定性时间推进
"""
from __future__ import annotations

from app.supervisor.common.clock import FrozenClock
from app.supervisor.dim_collector.schemas import (
    DegradationLevel,
    EightDimensionVector,
    SupervisorSnapshot,
    TriggerSource,
)
from app.supervisor.dim_collector.state_cache import StateCache


def _make_snapshot(pid_value: str, captured_ms: int) -> SupervisorSnapshot:
    return SupervisorSnapshot(
        project_id=pid_value,
        snapshot_id=f"snap-{captured_ms}",
        captured_at_ms=captured_ms,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(phase="S3"),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=10,
    )


def test_empty_cache_returns_none(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    assert cache.get_latest(pid.value) is None


def test_is_stale_on_missing_returns_false(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    assert cache.is_stale(pid.value) is False


def test_put_and_get_returns_same_snapshot(
    frozen_clock: FrozenClock, pid
) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    snap = _make_snapshot(pid.value, frozen_clock.monotonic_ms())
    cache.put(snap)
    latest = cache.get_latest(pid.value)
    assert latest is not None
    assert latest.snapshot_id == "snap-100"


def test_ttl_expiry_flags_stale(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    cache.put(_make_snapshot(pid.value, frozen_clock.monotonic_ms()))
    frozen_clock.advance(61_000)  # past TTL
    assert cache.get_latest(pid.value) is not None  # still returns
    assert cache.is_stale(pid.value) is True


def test_ttl_just_before_expiry_not_stale(
    frozen_clock: FrozenClock, pid
) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    cache.put(_make_snapshot(pid.value, frozen_clock.monotonic_ms()))
    frozen_clock.advance(59_000)
    assert cache.is_stale(pid.value) is False


def test_replace_keeps_only_latest(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    cache.put(_make_snapshot(pid.value, 100))
    cache.put(_make_snapshot(pid.value, 200))
    assert cache.get_latest(pid.value).snapshot_id == "snap-200"


def test_isolates_per_project(frozen_clock: FrozenClock) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    cache.put(_make_snapshot("proj-a", 1))
    cache.put(_make_snapshot("proj-b", 2))
    assert cache.get_latest("proj-a").snapshot_id == "snap-1"
    assert cache.get_latest("proj-b").snapshot_id == "snap-2"


def test_custom_ttl_respected(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=5_000)
    cache.put(_make_snapshot(pid.value, 0))
    frozen_clock.advance(5_001)
    assert cache.is_stale(pid.value) is True
