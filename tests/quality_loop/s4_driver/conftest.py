"""main-1 WP05 · L2-05 S4 Driver · 共享 fixture。

对齐 3-2 §7 测试 fixture：
  - mock_project_id / mock_clock / mock_event_bus
  - mock_skill_invoker（flaky 控制）
  - mock_test_runner（剧本控制）
  - make_wp_input · 构造 WPExecutionInput
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from app.quality_loop.s4_driver.driver import Clock, DriverConfig, S4Driver
from app.quality_loop.s4_driver.metric_collector import MetricCollector, MetricCollectorConfig
from app.quality_loop.s4_driver.schemas import (
    ExecutionTrace,
    SubagentInvokeResult,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
    WPExecutionInput,
)
from app.quality_loop.s4_driver.subagent_dispatcher import (
    MockSkillBridge,
    SubagentDispatcher,
)
from app.quality_loop.s4_driver.test_runner import StubTestExecutor, TestRunner


@pytest.fixture
def mock_project_id() -> str:
    return "pid-wp05"


class FrozenClock(Clock):
    """可注入时钟（测试用）· monotonic_ms 手动递增或自动跳。"""

    def __init__(self, *, start_iso: str = "2026-04-23T00:00:00.000000Z", start_ms: int = 0) -> None:
        self._iso = start_iso
        self._ms = start_ms
        self._auto_advance_ms: int = 0

    def now_iso(self) -> str:
        return self._iso

    def monotonic_ms(self) -> int:
        # 每次查询时自动跳一定量（模拟真实流逝）· 默认 0（不跳）
        self._ms += self._auto_advance_ms
        return self._ms

    def advance_ms(self, dt: int) -> None:
        self._ms += dt

    def set_auto_advance(self, dt_per_call: int) -> None:
        """每次 monotonic_ms() 被调 · 自动跳 dt_per_call ms（模拟长耗时）。"""
        self._auto_advance_ms = dt_per_call


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def mock_skill_bridge() -> MockSkillBridge:
    """默认 mock bridge · 全 success。"""
    return MockSkillBridge()


@pytest.fixture
def mock_dispatcher(mock_skill_bridge: MockSkillBridge) -> SubagentDispatcher:
    return SubagentDispatcher(bridge=mock_skill_bridge)


@pytest.fixture
def make_wp_input(mock_project_id: str) -> Callable[..., WPExecutionInput]:
    def _factory(**kw: Any) -> WPExecutionInput:
        return WPExecutionInput(
            project_id=kw.pop("project_id", mock_project_id),
            wp_id=kw.pop("wp_id", "wp-1"),
            suite_id=kw.pop("suite_id", "suite-1"),
            attempt_budget=kw.pop("attempt_budget", 3),
            timeout_ms=kw.pop("timeout_ms", 180_000),
            skill_intent_plan=kw.pop(
                "skill_intent_plan",
                ("red_test_creation", "green_test_implementation"),
            ),
        )

    return _factory


@pytest.fixture
def happy_stub_runner() -> TestRunner:
    """所有 run 返全绿 · 最简 happy-path fixture。"""
    return TestRunner(executor=StubTestExecutor(default_all_green=True))


@pytest.fixture
def red_stub_runner() -> TestRunner:
    """所有 run 返全红 · 用于 exhausted 路径。"""
    return TestRunner(executor=StubTestExecutor(default_all_green=False))


def _make_red_run(test_ids: list[str]) -> TestRunResult:
    cases = tuple(
        TestCaseOutcome(tid, TestOutcomeStatus.RED, failure_message="plan red")
        for tid in test_ids
    )
    return TestRunResult(
        cases=cases,
        red_count=len(test_ids),
        green_count=0,
        error_count=0,
        total_duration_ms=10 * max(1, len(test_ids)),
    )


def _make_green_run(test_ids: list[str]) -> TestRunResult:
    cases = tuple(TestCaseOutcome(tid, TestOutcomeStatus.GREEN) for tid in test_ids)
    return TestRunResult(
        cases=cases,
        red_count=0,
        green_count=len(test_ids),
        error_count=0,
        total_duration_ms=10 * max(1, len(test_ids)),
    )


@pytest.fixture
def make_plan_runner() -> Callable[..., TestRunner]:
    """按 plan 剧本返的 runner · 每次 plan 弹一个。"""

    def _factory(plan: list[TestRunResult]) -> TestRunner:
        return TestRunner(executor=StubTestExecutor(plan=list(plan)))

    return _factory


@pytest.fixture
def make_mixed_runner() -> Callable[..., TestRunner]:
    """按 mode 生成混合剧本的工厂（最常用）。

    modes:
      - ("red",) * n → 前 n 次全红
      - ("red", "green") → 先红后绿
      - ("green",)   → 第 1 次就绿
    """

    def _factory(modes: tuple[str, ...], test_ids: list[str]) -> TestRunner:
        plan = []
        for m in modes:
            if m == "red":
                plan.append(_make_red_run(test_ids or ["t1"]))
            elif m == "green":
                plan.append(_make_green_run(test_ids or ["t1"]))
            else:
                raise ValueError(f"unknown mode {m!r}")
        return TestRunner(executor=StubTestExecutor(plan=plan))

    return _factory


@pytest.fixture
def make_driver(
    mock_dispatcher: SubagentDispatcher,
    happy_stub_runner: TestRunner,
    frozen_clock: FrozenClock,
) -> Callable[..., S4Driver]:
    """driver 工厂 · 允许 per-test 覆盖。"""

    def _factory(
        *,
        dispatcher: SubagentDispatcher | None = None,
        runner: TestRunner | None = None,
        collector: MetricCollector | None = None,
        clock: Clock | None = None,
        config: DriverConfig | None = None,
    ) -> S4Driver:
        return S4Driver(
            dispatcher=dispatcher or mock_dispatcher,
            runner=runner or happy_stub_runner,
            collector=collector or MetricCollector(),
            clock=clock or frozen_clock,
            config=config or DriverConfig(),
        )

    return _factory
