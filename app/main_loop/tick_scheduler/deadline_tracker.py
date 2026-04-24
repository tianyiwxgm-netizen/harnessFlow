"""L2-01 · DeadlineTracker · 单 tick 预算 + drift 测量。

核心职责:
1. 每 tick 开始时分配 TickBudget (monotonic perf_counter_ns)
2. tick 结束测 actual_interval · 计算 drift = |actual - expected|
3. 若 drift > drift_slo_ms · 产 DriftViolationRecord 供 HRL-04 审计
4. 环形 buffer 保留最近 N 条 drift 记录 (供 P99 自检 · 非权威)

HRL-04 释义:
- 权威 P99 由 pytest-benchmark 外部测 · 本 tracker 只记"超阈值"二值事件
- bench 跑时 tracker 关掉 audit sink (噪声) · 只用 monotonic 时钟做起止
"""
from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from app.main_loop.tick_scheduler.schemas import (
    TICK_DRIFT_SLO_MS,
    DriftViolationRecord,
    TickBudget,
)


@dataclass
class DeadlineTracker:
    """tick 级预算分配 + drift 观测器。

    用法:
        tracker = DeadlineTracker(project_id="pid-x", interval_ms=100)
        budget = tracker.start_tick("tick-1")
        ... run tick ...
        violation = tracker.end_tick(budget)  # None 或 DriftViolationRecord

    - project_id:       PM-14 根字段 · 所有 violation 记录必带
    - interval_ms:      期望 interval (default 100)
    - drift_slo_ms:     drift 判红阈值 (default 100)
    - violations_max:   环形 buffer 上限(default 1000)
    - clock_ns:         纯 monotonic perf_counter_ns · 测试可替换
    """

    project_id: str
    interval_ms: int = 100
    drift_slo_ms: int = TICK_DRIFT_SLO_MS
    violations_max: int = 1000
    clock_ns: Callable[[], int] = time.perf_counter_ns

    _last_tick_end_ns: int | None = field(default=None, init=False)
    _violations: deque[DriftViolationRecord] = field(
        default_factory=lambda: deque(maxlen=1000), init=False
    )
    _total_ticks: int = field(default=0, init=False)
    _violation_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id required (PM-14)")
        if self.interval_ms <= 0:
            raise ValueError(f"interval_ms must be positive · got {self.interval_ms}")
        if self.drift_slo_ms <= 0:
            raise ValueError(f"drift_slo_ms must be positive · got {self.drift_slo_ms}")
        # rebind deque with correct maxlen (post-init)
        self._violations = deque(maxlen=max(1, self.violations_max))

    def start_tick(self, tick_id: str) -> TickBudget:
        """开始新 tick · 返回 TickBudget(含 deadline_ns)。"""
        start_ns = self.clock_ns()
        deadline_ns = start_ns + self.interval_ms * 1_000_000
        return TickBudget(
            tick_id=tick_id,
            interval_ms=self.interval_ms,
            started_at_ns=start_ns,
            deadline_ns=deadline_ns,
            drift_slo_ms=self.drift_slo_ms,
        )

    def end_tick(
        self, budget: TickBudget, *, context: dict[str, object] | None = None,
    ) -> DriftViolationRecord | None:
        """tick 结束 · 测 drift · 超阈值返回 violation · 否则 None。

        drift 定义(本 WP04 方案):
        - 基线为 interval_ms (期望周期)
        - actual_interval_ms = (end_ns - budget.started_at_ns) // 1e6
        - drift_ms = max(0, actual_interval_ms - interval_ms)  (只惩罚"慢" · 快 tick 无害)

        此定义符合 asyncio loop 实际语义:
        - 提前完成 = 下次 sleep 补齐 · 无累积偏离
        - 超时完成 = 累积 drift · 需告警(HRL-04)
        """
        end_ns = self.clock_ns()
        actual_ns = max(0, end_ns - budget.started_at_ns)
        actual_ms = actual_ns // 1_000_000
        drift_ms = max(0, int(actual_ms - budget.interval_ms))

        self._total_ticks += 1
        self._last_tick_end_ns = end_ns

        if drift_ms <= budget.drift_slo_ms:
            return None

        # 违反 · 产 record
        violation = DriftViolationRecord(
            tick_id=budget.tick_id,
            project_id=self.project_id,
            expected_interval_ms=budget.interval_ms,
            actual_interval_ms=int(actual_ms),
            drift_ms=drift_ms,
            ts_ns=end_ns,
            context=dict(context) if context else {},
        )
        self._violations.append(violation)
        self._violation_count += 1
        return violation

    def measure_latency_ms(self, budget: TickBudget) -> int:
        """测当前 latency (不结束 tick · 供 panic/halt 临时取值)。"""
        return int(max(0, self.clock_ns() - budget.started_at_ns) // 1_000_000)

    def measure_drift_ms(self, budget: TickBudget) -> int:
        """测当前 drift (latency - interval) · 可为 0 (提前完成)。"""
        latency = self.measure_latency_ms(budget)
        return max(0, latency - budget.interval_ms)

    # ------------------------------------------------------------------
    # stats
    # ------------------------------------------------------------------
    @property
    def total_ticks(self) -> int:
        return self._total_ticks

    @property
    def violation_count(self) -> int:
        return self._violation_count

    @property
    def violation_rate(self) -> float:
        if self._total_ticks == 0:
            return 0.0
        return self._violation_count / self._total_ticks

    def recent_violations(self) -> tuple[DriftViolationRecord, ...]:
        return tuple(self._violations)

    def reset(self) -> None:
        """测试辅助 · 清零计数(用于多场景复用同一 tracker)。"""
        self._violations.clear()
        self._total_ticks = 0
        self._violation_count = 0
        self._last_tick_end_ns = None


__all__ = ["DeadlineTracker"]
