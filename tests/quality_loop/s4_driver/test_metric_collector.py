"""main-1 WP05 · L2-05 S4 Driver · MetricCollector unit tests。

对齐 3-2 §2 正向 · §5 性能 SLO · §9 边界：
  - TC-L104-L205-020 ~ 022 · run_predicates → MetricData 聚合（WP05 简化版）
  - TC-L104-L205-501 ~ 506 · 聚合函数性能（WP05 只做单元覆盖 · 真 P95 留 perf 层）
  - 边界：空 attempts / 千级 case / 0 分母 test_pass_ratio=1.0
"""
from __future__ import annotations

import pytest

from app.quality_loop.s4_driver.metric_collector import (
    MetricCollector,
    MetricCollectorConfig,
    aggregate_durations,
    aggregate_skill_durations,
    compute_latency_p95,
    compute_test_pass_ratio,
)
from app.quality_loop.s4_driver.schemas import (
    DriverState,
    ExecutionTrace,
    SubagentInvokeResult,
    TestCaseOutcome,
    TestOutcomeStatus,
    TestRunResult,
)


def _make_run(
    greens: int = 0, reds: int = 0, errors: int = 0, duration_per: int = 10, attempted_at: int = 0
) -> TestRunResult:
    cases = (
        tuple(TestCaseOutcome(f"g{i}", TestOutcomeStatus.GREEN, duration_ms=duration_per) for i in range(greens))
        + tuple(TestCaseOutcome(f"r{i}", TestOutcomeStatus.RED, duration_ms=duration_per) for i in range(reds))
        + tuple(TestCaseOutcome(f"e{i}", TestOutcomeStatus.ERROR, duration_ms=duration_per) for i in range(errors))
    )
    return TestRunResult(
        cases=cases,
        red_count=reds, green_count=greens, error_count=errors,
        total_duration_ms=duration_per * max(1, len(cases)),
        attempted_at=attempted_at,
    )


def _make_trace(**kw) -> ExecutionTrace:
    return ExecutionTrace(
        trace_id=kw.get("trace_id", "tr-1"),
        project_id=kw.get("project_id", "pid-wp05"),
        wp_id=kw.get("wp_id", "wp-1"),
        suite_id=kw.get("suite_id", "s-1"),
        state=kw.get("state", DriverState.COMPLETED),
        attempts=kw.get("attempts", []),
        subagent_calls=kw.get("subagent_calls", []),
    )


class TestPassRatioHelper:
    """§6.7 · compute_test_pass_ratio 纯函数。"""

    def test_TC_L104_L205_020_all_green_ratio_one(self) -> None:
        """TC-L104-L205-020 · 全绿 · ratio=1.0。"""
        r = compute_test_pass_ratio(_make_run(greens=5))
        assert r == 1.0

    def test_TC_L104_L205_020b_half_red_ratio_half(self) -> None:
        """TC-L104-L205-020b · 半绿半红 · ratio=0.5。"""
        r = compute_test_pass_ratio(_make_run(greens=2, reds=2))
        assert r == 0.5

    def test_TC_L104_L205_020c_empty_run_ratio_defaults_one(self) -> None:
        """TC-L104-L205-020c · 空 run · 分母 0 → 视为 1.0（无失败）。"""
        r = compute_test_pass_ratio(_make_run())
        assert r == 1.0

    def test_TC_L104_L205_020d_error_counts_as_failure(self) -> None:
        """TC-L104-L205-020d · error 也算失败（非 green）。"""
        r = compute_test_pass_ratio(_make_run(greens=3, errors=1))
        assert r == 0.75


class TestLatencyP95Helper:
    """§12.1 · compute_latency_p95 nearest-rank 算法。"""

    def test_TC_L104_L205_501_single_value_returns_that_value(self) -> None:
        """TC-L104-L205-501 · 单元素 · P95 就是它本身。"""
        assert compute_latency_p95([42]) == 42

    def test_TC_L104_L205_501b_empty_returns_zero(self) -> None:
        """TC-L104-L205-501b · 空列表 · P95=0 边界。"""
        assert compute_latency_p95([]) == 0

    def test_TC_L104_L205_501c_increasing_sequence(self) -> None:
        """TC-L104-L205-501c · [1..100] · P95=95 nearest-rank = ceil(0.95*100) = 95。"""
        vals = list(range(1, 101))
        assert compute_latency_p95(vals) == 95

    def test_TC_L104_L205_501d_unsorted_input_is_sorted(self) -> None:
        """TC-L104-L205-501d · 乱序输入 · 内部自动 sort。"""
        vals = [50, 10, 20, 100, 30]
        # 5 elements · nearest rank = ceil(0.95*5)=5 · 取最大
        assert compute_latency_p95(vals) == 100


class TestAggregateDurations:
    """§6.7 · case/skill duration 提取。"""

    def test_aggregate_durations_empty(self) -> None:
        assert aggregate_durations([]) == []

    def test_aggregate_durations_multi_attempts(self) -> None:
        a1 = _make_run(greens=2, duration_per=10)
        a2 = _make_run(greens=1, reds=1, duration_per=20)
        # a1: 2 cases at 10ms; a2: 2 cases at 20ms → [10, 10, 20, 20]
        out = aggregate_durations([a1, a2])
        assert len(out) == 4
        assert all(d in (10, 20) for d in out)

    def test_aggregate_skill_durations_drops_zero(self) -> None:
        """skill duration == 0 (未记录) · drop。"""
        calls = [
            SubagentInvokeResult(invoke_id="iv1", skill_intent="x", status="success", duration_ms=100),
            SubagentInvokeResult(invoke_id="iv2", skill_intent="x", status="success", duration_ms=0),
            SubagentInvokeResult(invoke_id="iv3", skill_intent="x", status="success", duration_ms=50),
        ]
        out = aggregate_skill_durations(calls)
        assert out == [100, 50]


class TestMetricCollectorCollect:
    """§6.7 MetricCollector.collect 主流程。"""

    def test_TC_L104_L205_707_collect_basic_shape(self) -> None:
        """TC-L104-L205-707 · MetricData 有 4 核心 · raw 带统计字段。"""
        tr = _make_trace(attempts=[_make_run(greens=3)], subagent_calls=[])
        mc = MetricCollector()
        m = mc.collect(tr)
        assert m.test_pass_ratio == 1.0
        assert m.coverage_pct == 0.0, "default_coverage_pct=0.0"
        assert m.latency_ms_p95 >= 0
        assert "attempt_count" in m.raw and m.raw["attempt_count"] == 1
        assert "self_repair_count" in m.raw

    def test_TC_L104_L205_707b_coverage_override_takes_effect(self) -> None:
        """TC-L104-L205-707b · coverage_pct_override 覆盖默认。"""
        tr = _make_trace(attempts=[_make_run(greens=1)])
        mc = MetricCollector()
        m = mc.collect(tr, coverage_pct_override=0.88)
        assert m.coverage_pct == 0.88

    def test_TC_L104_L205_707c_include_skill_latency_flag(self) -> None:
        """TC-L104-L205-707c · include_skill_latency=True · skill dur 参与 P95 计算。"""
        tr = _make_trace(
            attempts=[_make_run(greens=1, duration_per=10)],
            subagent_calls=[
                SubagentInvokeResult("iv1", "red_test_creation", "success", duration_ms=5000),
            ],
        )
        mc = MetricCollector()
        m = mc.collect(tr)
        # skill 5000ms >> case 10ms · P95 应接近 5000
        assert m.latency_ms_p95 == 5000

    def test_TC_L104_L205_707d_include_skill_latency_flag_off(self) -> None:
        """TC-L104-L205-707d · flag=False · skill dur 不混入。"""
        tr = _make_trace(
            attempts=[_make_run(greens=1, duration_per=10)],
            subagent_calls=[
                SubagentInvokeResult("iv1", "red_test_creation", "success", duration_ms=5000),
            ],
        )
        mc = MetricCollector(config=MetricCollectorConfig(include_skill_latency=False))
        m = mc.collect(tr)
        assert m.latency_ms_p95 == 10, "skill 不参与 · 只看 case"

    def test_TC_L104_L205_707e_raw_extra_merges(self) -> None:
        """TC-L104-L205-707e · raw_extra 合进 MetricData.raw。"""
        tr = _make_trace(attempts=[_make_run(greens=1)])
        mc = MetricCollector()
        m = mc.collect(tr, raw_extra={"span_id": "sp-abc", "hash": "sha256:xyz"})
        assert m.raw["span_id"] == "sp-abc"
        assert m.raw["hash"] == "sha256:xyz"

    def test_TC_L104_L205_901b_empty_trace_safe_metric(self) -> None:
        """TC-L104-L205-901b · 空 attempts · pass_ratio=1.0 · P95=0 · 不抛。"""
        tr = _make_trace(attempts=[])
        mc = MetricCollector()
        m = mc.collect(tr)
        assert m.test_pass_ratio == 1.0
        assert m.latency_ms_p95 == 0
