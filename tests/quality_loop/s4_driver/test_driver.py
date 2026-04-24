"""main-1 WP05 · L2-05 S4 Driver · S4Driver 主流程 unit + integration tests。

对齐 3-2 §2 正向 · §3 负向 · §4 IC · §6 e2e · §9 边界：
  - TC-L104-L205-003  · execute_wp attempt=0 全绿 happy
  - TC-L104-L205-012  · self-repair 1 次即绿
  - TC-L104-L205-039  · 幂等（同 key 二次调用返同 trace）
  - TC-L104-L205-105  · WP_NOT_FOUND
  - TC-L104-L205-109  · SELF_REPAIR_EXHAUSTED
  - TC-L104-L205-114  · WP_TIMEOUT
  - TC-L104-L205-601  · e2e happy（attempt=0 → candidate + metric）
  - TC-L104-L205-602  · e2e exhausted
  - TC-L104-L205-901  · 空 suite_test_ids
"""
from __future__ import annotations

import pytest

from app.quality_loop.s4_driver.driver import (
    DriverConfig,
    S4Driver,
    drive_s4,
)
from app.quality_loop.s4_driver.metric_collector import MetricCollector
from app.quality_loop.s4_driver.schemas import (
    INTERNAL_ASSERT,
    SELF_REPAIR_EXHAUSTED,
    SUITE_MISSING,
    TEST_RUN_CRASH,
    WP_NOT_FOUND,
    WP_TIMEOUT,
    DriverError,
    DriverState,
    ExecutionTrace,
    MetricData,
    WPExecutionInput,
)
from app.quality_loop.s4_driver.subagent_dispatcher import (
    MockSkillBridge,
    SubagentDispatcher,
)
from app.quality_loop.s4_driver.test_runner import StubTestExecutor, TestRunner


class TestDriverHappyPath:
    """§2 正向 · attempt=0 直接绿 · candidate 构建 · delegation 委托。"""

    def test_TC_L104_L205_003_attempt_0_all_green(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-003 · attempt=0 首跑 · 全绿 · 构 candidate + metric。"""
        d = make_driver()
        tr = d.drive_s4(
            make_wp_input(wp_id="wp-happy"),
            suite_test_ids=["t1", "t2", "t3"],
        )
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code is None
        assert tr.attempt_count == 1, "只跑了 attempt=0 一次"
        assert tr.attempts[-1].is_all_green is True
        assert tr.is_success is True

    def test_TC_L104_L205_003b_metric_collected_on_success(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-003b · COMPLETED 时 · metric 必被 collect。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(), suite_test_ids=["t1"])
        assert isinstance(tr.metric, MetricData)
        assert tr.metric.test_pass_ratio == 1.0

    def test_TC_L104_L205_003c_subagent_calls_logged(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-003c · red + green 两次 skill call 都进 trace.subagent_calls。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(), suite_test_ids=["t1"])
        assert len(tr.subagent_calls) == 2
        assert tr.subagent_calls[0].skill_intent == "red_test_creation"
        assert tr.subagent_calls[1].skill_intent == "green_test_implementation"

    def test_TC_L104_L205_003d_facade_drive_s4_works(
        self,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-003d · facade drive_s4() 简单调用不创建外部 driver · 也能跑通。"""
        tr = drive_s4(make_wp_input(wp_id="wp-facade"), suite_test_ids=[])
        assert tr.state == DriverState.COMPLETED


class TestDriverSelfRepair:
    """§2 + §6.3 · self-repair 循环。"""

    def test_TC_L104_L205_012_self_repair_once_recovers(
        self,
        make_driver,
        make_wp_input,
        make_mixed_runner,
    ) -> None:
        """TC-L104-L205-012 · attempt=0 红 · attempt=1 绿 · attempt_count=2。"""
        runner = make_mixed_runner(modes=("red", "green"), test_ids=["t1"])
        d = make_driver(runner=runner)
        tr = d.drive_s4(make_wp_input(wp_id="wp-fix1"), suite_test_ids=["t1"])
        assert tr.state == DriverState.COMPLETED
        assert tr.attempt_count == 2, "attempt_count = 首次 + 1 次 self-repair"
        assert tr.self_repair_count == 1
        assert tr.error_code is None
        assert tr.is_success is True

    def test_TC_L104_L205_012b_self_repair_intent_is_code_fix_attempt(
        self,
        make_driver,
        make_wp_input,
        make_mixed_runner,
    ) -> None:
        """TC-L104-L205-012b · self-repair attempt 走 code_fix_attempt intent。"""
        runner = make_mixed_runner(modes=("red", "green"), test_ids=["t1"])
        d = make_driver(runner=runner)
        tr = d.drive_s4(make_wp_input(), suite_test_ids=["t1"])
        # 第 3 次 skill call（attempt=1）应该是 code_fix_attempt
        assert tr.subagent_calls[-1].skill_intent == "code_fix_attempt"


class TestDriverExhausted:
    """§2 + §6.3 · self-repair 硬锁耗尽。"""

    def test_TC_L104_L205_109_exhausted_after_budget(
        self,
        make_driver,
        make_wp_input,
        red_stub_runner,
    ) -> None:
        """TC-L104-L205-109 · budget=3 · 全红 · attempt 0+3=4 次红 · 触发 EXHAUSTED。"""
        d = make_driver(runner=red_stub_runner)
        tr = d.drive_s4(make_wp_input(attempt_budget=3), suite_test_ids=["t1"])
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code == SELF_REPAIR_EXHAUSTED
        assert tr.is_exhausted is True
        assert tr.attempt_count == 4, "0 + 3 self-repair = 4 attempts total"
        assert tr.self_repair_count == 3

    def test_TC_L104_L205_109b_exhausted_still_no_self_verdict(
        self,
        make_driver,
        make_wp_input,
        red_stub_runner,
    ) -> None:
        """TC-L104-L205-109b · no-self-verdict · exhausted 也不直接置 HALTED · 是 COMPLETED（供 L2-06 裁）。"""
        d = make_driver(runner=red_stub_runner)
        tr = d.drive_s4(make_wp_input(attempt_budget=1), suite_test_ids=["t1"])
        assert tr.state == DriverState.COMPLETED, "本 L2 不自决 · 由 L2-06 裁"
        assert tr.error_code == SELF_REPAIR_EXHAUSTED

    def test_TC_L104_L205_109c_budget_1_only_2_attempts(
        self,
        make_driver,
        make_wp_input,
        red_stub_runner,
    ) -> None:
        """TC-L104-L205-109c · budget=1 · 0+1=2 次 · exhausted。"""
        d = make_driver(runner=red_stub_runner)
        tr = d.drive_s4(make_wp_input(attempt_budget=1), suite_test_ids=["t1"])
        assert tr.attempt_count == 2
        assert tr.is_exhausted is True


class TestDriverNegative:
    """§3 负向 · 错误码路由。"""

    def test_TC_L104_L205_105_wp_not_found(self, make_driver, make_wp_input) -> None:
        """TC-L104-L205-105 · wp_id 为空 · WP_NOT_FOUND。"""
        d = make_driver()
        with pytest.raises(DriverError) as exc:
            d.drive_s4(make_wp_input(wp_id=""), suite_test_ids=["t1"])
        assert exc.value.code == WP_NOT_FOUND

    def test_TC_L104_L205_105b_suite_missing(self, make_driver, make_wp_input) -> None:
        """TC-L104-L205-105b · suite_id 为空 · SUITE_MISSING。"""
        d = make_driver()
        with pytest.raises(DriverError) as exc:
            d.drive_s4(make_wp_input(suite_id=""), suite_test_ids=["t1"])
        assert exc.value.code == SUITE_MISSING

    def test_TC_L104_L205_105c_project_id_missing_internal_assert(
        self, make_driver, make_wp_input
    ) -> None:
        """TC-L104-L205-105c · PM-14 · project_id 空 → INTERNAL_ASSERT。"""
        d = make_driver()
        with pytest.raises(DriverError) as exc:
            d.drive_s4(make_wp_input(project_id=""), suite_test_ids=["t1"])
        assert exc.value.code == INTERNAL_ASSERT

    def test_TC_L104_L205_108_test_run_crash_triggers_retry_then_exhaust(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-108 · test_runner 第 1 次 crash · 后续也 crash · budget=1 · exhausted。"""
        crashy = TestRunner(executor=StubTestExecutor(crash_on_call_n=1))
        d = make_driver(runner=crashy)
        tr = d.drive_s4(make_wp_input(attempt_budget=1), suite_test_ids=["t1"])
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code == SELF_REPAIR_EXHAUSTED


class TestDriverTimeout:
    """§3 + §12.1 · WP_TIMEOUT（前置 check）。"""

    def test_TC_L104_L205_114_wp_timeout_before_main_loop(
        self,
        make_driver,
        make_wp_input,
        frozen_clock,
    ) -> None:
        """TC-L104-L205-114 · clock 每次 query 自动跳大值 · 第二个 attempt 入口即超时 HALTED。"""
        # 构造：timeout_ms=1000 · 每次 monotonic_ms 调用自动跳 600ms
        # drive_s4 调用 monotonic_ms 次数：
        #   t0 (started_ms)        → 跳 600
        #   loop attempt=0 check   → 跳 600（elapsed=600 · 未超）
        #   loop attempt=1 check   → 跳 600（elapsed=1200 · 超 1000 → HALTED）
        d = make_driver(runner=TestRunner(executor=StubTestExecutor(default_all_green=False)))
        wp = make_wp_input(timeout_ms=1000, attempt_budget=3)
        frozen_clock.set_auto_advance(600)
        tr = d.drive_s4(wp, suite_test_ids=["t1"])
        assert tr.state == DriverState.HALTED
        assert tr.error_code == WP_TIMEOUT


class TestDriverIdempotent:
    """§2 + §6.16 · 幂等（同 key 二次调用返同 trace）。"""

    def test_TC_L104_L205_039_idempotent_second_call_returns_same_trace(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-039 · 同 (pid, wp_id, suite_id) 二次调用 · 返同一 trace 实例。"""
        d = make_driver()
        inp = make_wp_input(wp_id="wp-idem")
        t1 = d.drive_s4(inp, suite_test_ids=["t1"])
        t2 = d.drive_s4(inp, suite_test_ids=["t1"])
        assert t1 is t2, "§6.16 幂等 · 同 key 返原 trace"
        assert t1.trace_id == t2.trace_id


class TestDriverEdge:
    """§9 边界 · 空 suite / 零 attempts / 空 input。"""

    def test_TC_L104_L205_901_empty_suite_test_ids_still_completes(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-901 · 空 suite_test_ids · 空 WP · 仍应 COMPLETED（无失败即视绿）。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(wp_id="wp-empty"), suite_test_ids=[])
        assert tr.state == DriverState.COMPLETED
        assert tr.attempts[-1].is_all_green is True

    def test_TC_L104_L205_901b_metric_has_zero_count_for_empty(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-901b · 空 suite · metric.test_pass_ratio=1.0（空 → 1.0 语义）。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(), suite_test_ids=[])
        assert tr.metric.test_pass_ratio == 1.0


class TestDriverE2E:
    """§6 e2e · prd §5.5 · 端到端 scenarios。"""

    def test_TC_L104_L205_601_happy_chain_artifacts_ready_to_candidate(
        self,
        make_driver,
        make_wp_input,
    ) -> None:
        """TC-L104-L205-601 · 正向 · 从 artifacts_ready 到 candidate_built + metric · e2e happy。"""
        d = make_driver()
        tr = d.drive_s4(make_wp_input(wp_id="wp-e2e-happy"), suite_test_ids=["t1", "t2"])
        # 端到端断言：trace 完整 · metric 有值 · 无 error
        assert tr.state == DriverState.COMPLETED
        assert tr.metric is not None
        assert tr.started_at and tr.ended_at
        assert tr.attempt_count == 1
        assert len(tr.subagent_calls) == 2

    def test_TC_L104_L205_602_exhausted_path_end_to_end(
        self,
        make_driver,
        make_wp_input,
        red_stub_runner,
    ) -> None:
        """TC-L104-L205-602 · e2e exhausted · self-repair 3 次耗尽 · 仍 candidate-ready。"""
        d = make_driver(runner=red_stub_runner)
        tr = d.drive_s4(
            make_wp_input(wp_id="wp-e2e-exhausted", attempt_budget=3),
            suite_test_ids=["t1"],
        )
        assert tr.state == DriverState.COMPLETED
        assert tr.error_code == SELF_REPAIR_EXHAUSTED
        assert tr.self_repair_count == 3
