"""main-1 WP05 · L2-05 S4 Driver · schema unit tests。

对齐 3-2 §2 正向 · 3-2 §9 边界 · 每 VO ≥ 1 正向 + ≥ 1 边界。

TC 分布：
  - TC-L104-L205-700 ~ 715 · schema / fixture 自检（3-2 §1 第 7xx 段）
  - TC-L104-L205-135 · 内部 assert 错误码（3-2 §1.2）
"""
from __future__ import annotations

import pytest

from app.quality_loop.s4_driver.schemas import (
    DriverError,
    DriverState,
    ExecutionTrace,
    MetricData,
    SELF_REPAIR_EXHAUSTED,
    SubagentInvokeResult,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
    WPExecutionInput,
)


class TestL2_05_Schemas:
    """§7 fixture / 基础 VO 自检（TC-700 段）。"""

    def test_TC_L104_L205_700_driver_error_carries_code(self) -> None:
        """TC-L104-L205-700 · DriverError 暴露 code · 不用 isinstance 路由。"""
        err = DriverError("E_L205_L205_WP_NOT_FOUND", message="no such wp")
        assert err.code == "E_L205_L205_WP_NOT_FOUND"
        assert err.severity == "ERROR"

    def test_TC_L104_L205_701_driver_error_context_kwargs(self) -> None:
        """TC-L104-L205-701 · DriverError kwargs 透传 context（§11 错误上下文）。"""
        err = DriverError("E_L205_L205_WP_TIMEOUT", wp_id="wp-42", elapsed_ms=200_000)
        assert err.context["wp_id"] == "wp-42"
        assert err.context["elapsed_ms"] == 200_000

    def test_TC_L104_L205_702_test_run_result_all_green_predicate(self) -> None:
        """TC-L104-L205-702 · §6.3 TestRunResult.is_all_green 判定条件（red=0 且 error=0）。"""
        cases = (
            TestCaseOutcome("t1", TestOutcomeStatus.GREEN),
            TestCaseOutcome("t2", TestOutcomeStatus.GREEN),
        )
        run = TestRunResult(cases=cases, red_count=0, green_count=2, error_count=0, total_duration_ms=100)
        assert run.is_all_green is True
        assert run.total_count == 2

    def test_TC_L104_L205_703_test_run_result_not_all_green_if_red(self) -> None:
        """TC-L104-L205-703 · red>0 → is_all_green=False。"""
        cases = (
            TestCaseOutcome("t1", TestOutcomeStatus.RED, failure_message="assert fail"),
        )
        run = TestRunResult(cases=cases, red_count=1, green_count=0, error_count=0, total_duration_ms=50)
        assert run.is_all_green is False

    def test_TC_L104_L205_704_test_run_result_not_all_green_if_error(self) -> None:
        """TC-L104-L205-704 · error>0 → is_all_green=False（子进程崩溃情形）。"""
        cases = (TestCaseOutcome("t1", TestOutcomeStatus.ERROR),)
        run = TestRunResult(cases=cases, red_count=0, green_count=0, error_count=1, total_duration_ms=10)
        assert run.is_all_green is False

    def test_TC_L104_L205_705_execution_trace_attempt_count_starts_zero(self) -> None:
        """TC-L104-L205-705 · trace 初始 attempt_count = 0。"""
        tr = ExecutionTrace(trace_id="tr-1", project_id="pid-wp05", wp_id="wp-1", suite_id="s-1")
        assert tr.attempt_count == 0
        assert tr.self_repair_count == 0
        assert tr.state == DriverState.PREPARING

    def test_TC_L104_L205_706_execution_trace_self_repair_count_formula(self) -> None:
        """TC-L104-L205-706 · self_repair_count = max(0, attempts - 1)（§2.3 公式）。"""
        tr = ExecutionTrace(trace_id="tr-1", project_id="pid-wp05", wp_id="wp-1", suite_id="s-1")
        tr.attempts.append(
            TestRunResult(cases=(), red_count=0, green_count=0, error_count=0, total_duration_ms=0, attempted_at=0)
        )
        assert tr.self_repair_count == 0
        tr.attempts.append(
            TestRunResult(cases=(), red_count=0, green_count=0, error_count=0, total_duration_ms=0, attempted_at=1)
        )
        assert tr.self_repair_count == 1

    def test_TC_L104_L205_707_metric_data_holds_four_core_fields(self) -> None:
        """TC-L104-L205-707 · MetricData 必含 4 核心字段 · 喂 WP04 Gate。"""
        m = MetricData(
            coverage_pct=0.92,
            latency_ms_p95=1500,
            test_pass_ratio=1.0,
            memory_peak_mb=128,
        )
        assert m.coverage_pct == 0.92
        assert m.latency_ms_p95 == 1500
        assert m.test_pass_ratio == 1.0
        assert m.memory_peak_mb == 128

    def test_TC_L104_L205_708_wp_input_defaults_attempt_budget_3(self) -> None:
        """TC-L104-L205-708 · §2.1 D3 · self-repair 硬锁 3 · WPExecutionInput 默认 attempt_budget=3。"""
        inp = WPExecutionInput(project_id="pid-wp05", wp_id="wp-1", suite_id="s-1")
        assert inp.attempt_budget == 3

    def test_TC_L104_L205_709_wp_input_defaults_timeout_3min(self) -> None:
        """TC-L104-L205-709 · §12.1 SLO · timeout 默认 180s=3min。"""
        inp = WPExecutionInput(project_id="pid-wp05", wp_id="wp-1", suite_id="s-1")
        assert inp.timeout_ms == 180_000

    def test_TC_L104_L205_710_subagent_result_default_status_strings(self) -> None:
        """TC-L104-L205-710 · SubagentInvokeResult status 字符串三态（success/partial/fail）。"""
        r = SubagentInvokeResult(invoke_id="iv-1", skill_intent="red_test_creation", status="success")
        assert r.status == "success"
        assert r.error_code is None

    def test_TC_L104_L205_711_execution_trace_is_success_requires_completed_and_green(self) -> None:
        """TC-L104-L205-711 · is_success 三条件：state=COMPLETED + 无 error + 最后 attempt 全绿。"""
        tr = ExecutionTrace(trace_id="tr-1", project_id="pid-wp05", wp_id="wp-1", suite_id="s-1")
        tr.attempts.append(
            TestRunResult(
                cases=(TestCaseOutcome("t1", TestOutcomeStatus.GREEN),),
                red_count=0, green_count=1, error_count=0, total_duration_ms=100,
            )
        )
        # 状态还没转 COMPLETED · 不 success
        assert tr.is_success is False
        tr.state = DriverState.COMPLETED
        assert tr.is_success is True

    def test_TC_L104_L205_712_is_exhausted_needs_completed_and_exhausted_code(self) -> None:
        """TC-L104-L205-712 · is_exhausted 要求 state=COMPLETED 且 error_code=SELF_REPAIR_EXHAUSTED。"""
        tr = ExecutionTrace(
            trace_id="tr-2", project_id="pid-wp05", wp_id="wp-2", suite_id="s-2",
            state=DriverState.COMPLETED,
            error_code=SELF_REPAIR_EXHAUSTED,
        )
        assert tr.is_exhausted is True
