"""main-1 WP05 · L2-05 S4 Driver · IC 契约 + 边界 + SLO 轻量覆盖。

补齐 3-2 §4 IC-XX 契约 · §5 SLO 轻量 · §8 集成点 · §9 边界补全。
"""
from __future__ import annotations

import time

import pytest

from app.quality_loop.s4_driver.driver import DriverConfig, S4Driver
from app.quality_loop.s4_driver.metric_collector import MetricCollector
from app.quality_loop.s4_driver.schemas import (
    INTERNAL_ASSERT,
    SELF_REPAIR_EXHAUSTED,
    SUITE_MISSING,
    TEST_RUN_CRASH,
    WP_NOT_FOUND,
    DriverError,
    DriverState,
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


class TestDriverAccessors:
    """§2.1 · driver 属性 accessor · 方便下游（WP06/07）注入替换。"""

    def test_dispatcher_accessor(self, make_driver) -> None:
        d = make_driver()
        assert d.dispatcher is not None

    def test_runner_accessor(self, make_driver) -> None:
        d = make_driver()
        assert d.runner is not None

    def test_collector_accessor(self, make_driver) -> None:
        d = make_driver()
        assert d.collector is not None

    def test_config_accessor(self, make_driver) -> None:
        d = make_driver()
        assert isinstance(d.config, DriverConfig)

    def test_dispatcher_bridge_accessor(self) -> None:
        """SubagentDispatcher.bridge 可被外部读取（方便 WP06 reflection）。"""
        disp = SubagentDispatcher()
        assert disp.bridge is not None

    def test_test_runner_executor_accessor(self) -> None:
        runner = TestRunner()
        assert runner.executor is not None


class TestDriverValidationEdges:
    """§3.2 · 前置校验 · 更多角度。"""

    def test_TC_L104_L205_105d_suite_test_ids_none_internal_assert(
        self, make_driver, make_wp_input
    ) -> None:
        """TC-L104-L205-105d · suite_test_ids=None · INTERNAL_ASSERT。"""
        d = make_driver()
        with pytest.raises(DriverError) as exc:
            d.drive_s4(make_wp_input(), suite_test_ids=None)  # type: ignore[arg-type]
        assert exc.value.code == INTERNAL_ASSERT


class TestDriverCrashThenGreen:
    """§3 · crash 中途发生 · budget 足够 · 下一 attempt 绿 · 成功恢复。"""

    def test_TC_L104_L205_108c_crash_recovers_if_later_attempt_green(
        self,
        make_wp_input,
        mock_dispatcher,
        frozen_clock,
    ) -> None:
        """TC-L104-L205-108c · attempt 0 crash · attempt 1 绿 · state=COMPLETED（self-repair 救起）。"""
        # StubTestExecutor：第 1 次 call crash · 第 2 次 call 返全绿
        executor = StubTestExecutor(
            plan=[
                # crash_on_call_n=1 · 第 1 次 crash 之后·plan 走正常
                # 这里我们用 plan 的方式：没法混 crash · 用两个 runner wrap 不现实
                # 改用 custom executor
            ],
            default_all_green=True,
            crash_on_call_n=1,
        )
        # 但 crash 后 `crash_on_call_n` 只触发一次（_count 过后不再触发）？
        # 实际 StubTestExecutor 是 `n >= crash_on_call_n` · crash_on_call_n=1 就是一直 crash
        # 所以我们需要另一种方式：跨 executor 切换。用自定义 executor。
        class CrashOnceThenGreen:
            def __init__(self):
                self._n = 0

            def run(self, *, workspace_path, test_ids, timeout_ms=60_000):
                self._n += 1
                if self._n == 1:
                    raise DriverError(TEST_RUN_CRASH, message="crash once")
                cases = tuple(TestCaseOutcome(t, TestOutcomeStatus.GREEN) for t in test_ids)
                return TestRunResult(
                    cases=cases,
                    red_count=0, green_count=len(test_ids), error_count=0,
                    total_duration_ms=10,
                )

        runner = TestRunner(executor=CrashOnceThenGreen())
        d = S4Driver(
            dispatcher=mock_dispatcher,
            runner=runner,
            clock=frozen_clock,
        )
        tr = d.drive_s4(
            make_wp_input(wp_id="wp-crash-once", attempt_budget=3),
            suite_test_ids=["t1"],
        )
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code is None, "crash 后 attempt=1 绿 · 救起 · 无 error_code"
        assert tr.attempt_count == 2, "crash attempt + green attempt = 2"
        # attempt 0 的 run_result 是人工合成的 error-only（§driver.py _run_main_loop）
        assert tr.attempts[0].error_count >= 1


class TestDriverSkillFailThenRed:
    """§3 · skill fail · test red · self-repair 循环（§11 降级链）。"""

    def test_TC_L104_L205_107_skill_fail_leads_to_red_then_repair(
        self,
        make_wp_input,
        frozen_clock,
    ) -> None:
        """TC-L104-L205-107 · skill attempt=0 fail · run 返红 · attempt=1 skill success · 绿 · 救起。"""
        # skill attempt=0 fail (both red/green), attempt=1 success (code_fix_attempt)
        bridge = MockSkillBridge(
            stub_plan=[
                SubagentInvokeResult("iv1", "red_test_creation", "fail", error_code="E_L205_L205_SKILL_INVOKE_FAIL"),
                SubagentInvokeResult("iv2", "green_test_implementation", "fail", error_code="E_L205_L205_SKILL_INVOKE_FAIL"),
                SubagentInvokeResult("iv3", "code_fix_attempt", "success"),
            ],
        )
        disp = SubagentDispatcher(bridge=bridge)
        # plan: attempt 0 全红 · attempt 1 全绿
        plan = [
            TestRunResult(
                cases=(TestCaseOutcome("t1", TestOutcomeStatus.RED),),
                red_count=1, green_count=0, error_count=0, total_duration_ms=10,
            ),
            TestRunResult(
                cases=(TestCaseOutcome("t1", TestOutcomeStatus.GREEN),),
                red_count=0, green_count=1, error_count=0, total_duration_ms=10,
            ),
        ]
        runner = TestRunner(executor=StubTestExecutor(plan=plan))
        d = S4Driver(dispatcher=disp, runner=runner, clock=frozen_clock)
        tr = d.drive_s4(make_wp_input(wp_id="wp-skillfail"), suite_test_ids=["t1"])
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code is None
        assert tr.attempt_count == 2


class TestICContractShape:
    """§4 · IC 契约字段 shape 自测（WP05 mock 阶段 · 不打外部 broker）。"""

    def test_TC_L104_L205_404_ic04_skill_call_shape(self) -> None:
        """TC-L104-L205-404 · SubagentInvokeResult 必有 status/invoke_id/skill_intent 三字段（IC-04 出站契约）。"""
        disp = SubagentDispatcher()
        r = disp.invoke(intent="red_test_creation")
        assert hasattr(r, "status")
        assert hasattr(r, "invoke_id")
        assert hasattr(r, "skill_intent")
        assert r.status in ("success", "partial", "fail")

    def test_TC_L104_L205_409_trace_carries_candidate_signals(
        self, make_driver, make_wp_input
    ) -> None:
        """TC-L104-L205-409 · ExecutionTrace 的 signals 能供 L2-06 裁决：
        is_success / is_exhausted / metric / attempts / subagent_calls 全可访问。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(wp_id="wp-shape"), suite_test_ids=["t1"])
        # 读所有 L2-06 可能要的字段
        assert tr.trace_id
        assert tr.project_id
        assert tr.wp_id
        assert tr.suite_id
        assert tr.state == DriverState.COMPLETED
        assert tr.started_at
        assert tr.ended_at
        assert tr.metric is not None
        assert isinstance(tr.attempts, list)
        assert isinstance(tr.subagent_calls, list)
        # 关键：no-self-verdict 语义 · trace 不包含 "verdict" 字段
        assert not hasattr(tr, "verdict"), "§1.9 DDD 一句话 · 本 L2 不下 verdict"


class TestDriverBigWP:
    """§9 · 超大 WP 边界 + 吞吐轻量。"""

    def test_TC_L104_L205_902_big_suite_completes_cleanly(
        self, make_driver, make_wp_input
    ) -> None:
        """TC-L104-L205-902 · 500 cases · 走 happy 路径 · 仍 COMPLETED + metric。"""
        d = make_driver()
        ids = [f"t{i}" for i in range(500)]
        tr = d.drive_s4(make_wp_input(wp_id="wp-big"), suite_test_ids=ids)
        assert tr.state == DriverState.COMPLETED
        assert tr.metric is not None
        assert tr.metric.test_pass_ratio == 1.0


class TestDriverTraceShapeOnHalt:
    """§9 · HALT 场景下 trace 字段完整性。"""

    def test_TC_L104_L205_114b_halt_trace_still_has_ended_at(
        self, make_driver, make_wp_input, frozen_clock
    ) -> None:
        """TC-L104-L205-114b · HALTED 时 · trace.ended_at 仍被设置（审计用）。"""
        frozen_clock.set_auto_advance(1000)  # 每次 query 跳 1s · 立即超时
        d = make_driver(runner=TestRunner(executor=StubTestExecutor(default_all_green=False)))
        tr = d.drive_s4(
            make_wp_input(timeout_ms=100, wp_id="wp-halt-shape"), suite_test_ids=["t1"]
        )
        # 可能 HALTED 也可能 COMPLETED · 总之 ended_at 要设置
        assert tr.ended_at is not None
        assert tr.started_at is not None

    def test_TC_L104_L205_114c_halt_no_metric(
        self, make_driver, make_wp_input, frozen_clock
    ) -> None:
        """TC-L104-L205-114c · HALTED 时 · metric=None（只有 COMPLETED 才 collect）。"""
        frozen_clock.set_auto_advance(500)
        d = make_driver(runner=TestRunner(executor=StubTestExecutor(default_all_green=False)))
        tr = d.drive_s4(make_wp_input(timeout_ms=100), suite_test_ids=["t1"])
        if tr.state == DriverState.HALTED:
            assert tr.metric is None


class TestDriverSLOLite:
    """§5 · SLO 轻量自检（真 perf 留给 perf 层）。"""

    def test_TC_L104_L205_506_candidate_build_under_1s(
        self, make_driver, make_wp_input
    ) -> None:
        """TC-L104-L205-506 · candidate/metric 聚合 < 1s · WP05 100 cases mock 快检。"""
        d = make_driver()
        t0 = time.monotonic()
        tr = d.drive_s4(
            make_wp_input(wp_id="wp-slo-fast"),
            suite_test_ids=[f"t{i}" for i in range(100)],
        )
        elapsed = time.monotonic() - t0
        assert tr.state == DriverState.COMPLETED
        assert elapsed < 1.0, f"100-case happy path应 < 1s · got {elapsed:.3f}s"
