"""TC-WP04-DT01..DT10 · DeadlineTracker · drift 测量 + violation 记录。"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from app.main_loop.tick_scheduler.deadline_tracker import DeadlineTracker
from app.main_loop.tick_scheduler.schemas import DriftViolationRecord


# ------------------------------------------------------------------
# 虚拟 monotonic 时钟 (ns) · 测试 drift 不依赖真实 perf_counter
# ------------------------------------------------------------------
@dataclass
class FakeNsClock:
    now_ns: int = 0

    def advance_ms(self, ms: int) -> None:
        self.now_ns += ms * 1_000_000

    def __call__(self) -> int:
        return self.now_ns


@pytest.fixture
def clock() -> FakeNsClock:
    return FakeNsClock(now_ns=1_000_000_000)  # 1s baseline


@pytest.fixture
def tracker(clock: FakeNsClock) -> Iterator[DeadlineTracker]:
    t = DeadlineTracker(
        project_id="pid-test",
        interval_ms=100,
        drift_slo_ms=100,
        clock_ns=clock,
    )
    yield t


class TestDeadlineTracker:
    """DeadlineTracker · drift 测量 + violation 统计。"""

    def test_TC_WP04_DT01_start_tick_returns_budget(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT01 · start_tick 返回 TickBudget(started_at_ns / deadline_ns 正确)。"""
        b = tracker.start_tick("tick-1")
        assert b.tick_id == "tick-1"
        assert b.interval_ms == 100
        assert b.started_at_ns == clock.now_ns
        # deadline = start + 100ms
        assert b.deadline_ns == clock.now_ns + 100_000_000
        assert b.drift_slo_ms == 100

    def test_TC_WP04_DT02_end_tick_within_budget_no_violation(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT02 · 快速完成 tick (80ms) · 无 violation。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(80)
        v = tracker.end_tick(b)
        assert v is None
        assert tracker.total_ticks == 1
        assert tracker.violation_count == 0

    def test_TC_WP04_DT03_end_tick_exactly_interval_no_violation(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT03 · 准时完成 (100ms 正好) · drift=0 · 无 violation。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(100)
        v = tracker.end_tick(b)
        assert v is None
        assert tracker.violation_count == 0

    def test_TC_WP04_DT04_end_tick_exceeds_slo_produces_violation(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT04 · tick 耗 250ms · drift=150ms > 100 · 产 violation(HRL-04 证据)。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(250)
        v = tracker.end_tick(b)
        assert v is not None
        assert isinstance(v, DriftViolationRecord)
        assert v.tick_id == "tick-1"
        assert v.project_id == "pid-test"
        assert v.expected_interval_ms == 100
        assert v.actual_interval_ms == 250
        assert v.drift_ms == 150
        assert tracker.violation_count == 1
        assert tracker.violation_rate == 1.0

    def test_TC_WP04_DT05_end_tick_at_slo_boundary_no_violation(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT05 · drift 正好 = 100 · 不超阈 · 无 violation (<=, 非 <)。"""
        b = tracker.start_tick("tick-1")
        # interval=100 · advance 200ms · drift = 200-100 = 100
        clock.advance_ms(200)
        v = tracker.end_tick(b)
        assert v is None, "drift 正好 = slo · 不判红(<= 语义)"

    def test_TC_WP04_DT06_end_tick_just_over_slo_produces_violation(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT06 · drift = 101ms · 判红 (严格 >)。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(201)  # drift = 101
        v = tracker.end_tick(b)
        assert v is not None
        assert v.drift_ms == 101

    def test_TC_WP04_DT07_ring_buffer_caps_violations(
        self, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT07 · violations_max=3 · 第 4 条覆盖第 1 条 (环形 buffer)。"""
        t = DeadlineTracker(
            project_id="pid-x",
            interval_ms=50,
            drift_slo_ms=10,
            violations_max=3,
            clock_ns=clock,
        )
        for i in range(5):
            b = t.start_tick(f"tick-{i}")
            clock.advance_ms(200)  # drift >> 10
            t.end_tick(b)
        assert t.violation_count == 5, "总计数不清零"
        recent = t.recent_violations()
        assert len(recent) == 3, "环形 buffer maxlen=3"
        # 应保留最近 3 条 (tick-2 / tick-3 / tick-4)
        assert [v.tick_id for v in recent] == ["tick-2", "tick-3", "tick-4"]

    def test_TC_WP04_DT08_reset_clears_counts(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT08 · reset() 清零计数 + buffer。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(300)
        tracker.end_tick(b)
        assert tracker.total_ticks == 1
        tracker.reset()
        assert tracker.total_ticks == 0
        assert tracker.violation_count == 0
        assert tracker.recent_violations() == ()

    def test_TC_WP04_DT09_measure_latency_and_drift_mid_tick(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT09 · mid-tick 测 latency/drift (不结束 tick) · 供 panic/halt 用。"""
        b = tracker.start_tick("tick-1")
        clock.advance_ms(50)
        assert tracker.measure_latency_ms(b) == 50
        assert tracker.measure_drift_ms(b) == 0  # 还在 interval 内
        clock.advance_ms(70)  # total 120
        assert tracker.measure_latency_ms(b) == 120
        assert tracker.measure_drift_ms(b) == 20

    def test_TC_WP04_DT10_constructor_rejects_bad_config(self) -> None:
        """TC-WP04-DT10 · 非法 config (空 pid · 非正 interval) 构造拒绝。"""
        with pytest.raises(ValueError, match="project_id"):
            DeadlineTracker(project_id="", interval_ms=100)
        with pytest.raises(ValueError, match="interval_ms"):
            DeadlineTracker(project_id="pid-1", interval_ms=0)
        with pytest.raises(ValueError, match="drift_slo_ms"):
            DeadlineTracker(project_id="pid-1", interval_ms=100, drift_slo_ms=-1)

    def test_TC_WP04_DT11_violation_preserves_context(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT11 · end_tick 传 context · 挂到 violation 供追溯。"""
        b = tracker.start_tick("tick-x")
        clock.advance_ms(500)
        v = tracker.end_tick(b, context={"cause": "gc", "blocked_on": "L2-02"})
        assert v is not None
        assert v.context == {"cause": "gc", "blocked_on": "L2-02"}

    def test_TC_WP04_DT12_violation_rate_zero_on_all_fast(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT12 · 10 次快速 tick · violation_rate=0。"""
        for i in range(10):
            b = tracker.start_tick(f"tick-{i}")
            clock.advance_ms(50)
            tracker.end_tick(b)
        assert tracker.total_ticks == 10
        assert tracker.violation_count == 0
        assert tracker.violation_rate == 0.0

    def test_TC_WP04_DT13_violation_rate_mixed(
        self, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-DT13 · 10 次 · 3 超时 7 正常 · violation_rate=0.3。"""
        for i in range(10):
            b = tracker.start_tick(f"tick-{i}")
            clock.advance_ms(300 if i % 3 == 0 else 50)  # i=0/3/6/9 → 4 次超时
            tracker.end_tick(b)
        # i=0,3,6,9 4 次超时
        assert tracker.violation_count == 4
        assert tracker.violation_rate == pytest.approx(0.4)
