"""SLO-04 · gate_latency_p95 ≤ 3s · DoD AST 编译 + 评估 (无测试).

阈值: 3000ms P95 (general-dod §3.2)
来源: DoD compile_batch + gate evaluate_gate · 不含 test 跑

度量定义:
- compile_batch (clauses → CompiledDoD) + evaluate_gate (CompiledDoD + metrics → GateVerdict) 全链 wall ms
- 实测 P95 ≈ 0.4ms · 3000ms 阈值 = 7500x 余量 (留给真实大型 DoD)

6 TC:
- T1 baseline · 100 次单 hard 表达式 · P95 ≤ 3000ms
- T2 cold start · 首次 50 次 P95 ≤ 3000ms
- T3 持续 5 个滑窗 (每窗 100)
- T4 大表达式 · 10 hard + 10 soft · P95 ≤ 3000ms
- T5 evaluate-only (compile 一次 · eval 多次) · P95 << 1000ms (热路径)
- T6 退化告警 · 注入 sleep · 反向触发
"""
from __future__ import annotations

import time
import uuid

import pytest

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    DoDEvaluator,
    DoDExpressionCompiler,
)
from app.quality_loop.dod_compiler.predicate_eval import WhitelistRegistry
from app.quality_loop.dod_compiler.schemas import (
    DoDClause,
    DoDExpressionKind,
    Priority,
)
from app.quality_loop.gate_compiler.dod_adapter import DoDAdapter
from app.quality_loop.gate_compiler.gate import (
    EvaluateGateCommand,
    GateCompiler,
    RewordCounter,
)
from app.quality_loop.gate_compiler.metric_sampler import MetricSampler
from tests.shared.perf_helpers import LatencySample, assert_p95_under, assert_p99_under

SLO_BUDGET_P95_MS = 3000.0


def _new_gate() -> tuple[DoDExpressionCompiler, GateCompiler]:
    reg = WhitelistRegistry()
    compiler = DoDExpressionCompiler(
        whitelist_registry=reg, offline_admin_mode=False,
    )
    evaluator = DoDEvaluator(compiler, whitelist_registry=reg, eval_timeout_ms=500)
    gate = GateCompiler(
        dod_adapter=DoDAdapter(evaluator=evaluator),
        metric_sampler=MetricSampler(),
        rework_counter=RewordCounter(),
    )
    return compiler, gate


def _compile_simple_dod(compiler: DoDExpressionCompiler, project_id: str = "p1"):
    """单 hard expression: line_coverage() >= 0.8."""
    cmd = CompileBatchCommand(
        command_id=f"cmd-{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        blueprint_id="bp-perf",
        clauses=[
            DoDClause(
                clause_id=f"c-{uuid.uuid4().hex[:8]}",
                clause_text="line_coverage() >= 0.8",
                source_ac_ids=["ac-001"],
                priority=Priority.P0,
                kind=DoDExpressionKind.HARD,
            ),
        ],
        ac_matrix={"acs": [{"id": "ac-001"}]},
        ts="2026-04-23T00:00:00Z",
    )
    return compiler.compile_batch(cmd).compiled


def _compile_large_dod(compiler: DoDExpressionCompiler, project_id: str = "p1"):
    """10 hard + 10 soft 大表达式 · 模拟真实大型 DoD."""
    clauses = []
    ac_entries = []
    hard_exprs = [
        "line_coverage() >= 0.8",
        "branch_coverage() >= 0.7",
        "test_pass_rate() >= 0.9",
        "p0_cases_all_pass()",
        "lint_warnings() < 10",
        "ac_coverage() >= 0.9",
        "line_coverage() < 1.01",
        "test_pass_rate() < 1.01",
        "branch_coverage() < 1.01",
        "lint_warnings() < 100",
    ]
    for i, expr in enumerate(hard_exprs):
        ac = f"ac-h-{i:03d}"
        clauses.append(DoDClause(
            clause_id=f"c-h-{i}-{uuid.uuid4().hex[:8]}",
            clause_text=expr,
            source_ac_ids=[ac],
            priority=Priority.P0,
            kind=DoDExpressionKind.HARD,
        ))
        ac_entries.append({"id": ac})
    soft_exprs = [
        "line_coverage() >= 0.85",
        "branch_coverage() >= 0.75",
        "test_pass_rate() >= 0.95",
        "lint_warnings() < 5",
        "ac_coverage() >= 0.95",
        "line_coverage() >= 0.9",
        "branch_coverage() >= 0.8",
        "test_pass_rate() >= 0.99",
        "lint_warnings() < 3",
        "ac_coverage() >= 0.99",
    ]
    for i, expr in enumerate(soft_exprs):
        ac = f"ac-s-{i:03d}"
        clauses.append(DoDClause(
            clause_id=f"c-s-{i}-{uuid.uuid4().hex[:8]}",
            clause_text=expr,
            source_ac_ids=[ac],
            priority=Priority.P1,
            kind=DoDExpressionKind.SOFT,
        ))
        ac_entries.append({"id": ac})
    cmd = CompileBatchCommand(
        command_id=f"cmd-{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        blueprint_id="bp-perf-large",
        clauses=clauses,
        ac_matrix={"acs": ac_entries},
        ts="2026-04-23T00:00:00Z",
    )
    return compiler.compile_batch(cmd).compiled


_DEFAULT_METRICS = {
    "coverage": {"line_rate": 0.95, "branch_rate": 0.85, "ac_coverage": 0.95},
    "test_result": {"pass_count": 100, "fail_count": 0, "p0_all_pass": True},
    "lint": {"warning_count": 2},
}


@pytest.mark.perf
class TestSLO04GateLatency:
    """SLO-04: gate_latency_p95 ≤ 3000ms · 6 TC."""

    def test_t1_baseline_p95_under_3s(self) -> None:
        """T1 · 100 次 compile + evaluate · P95 ≤ 3000ms."""
        compiler, gate = _new_gate()
        # warmup
        for _ in range(20):
            cd = _compile_simple_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
        samples: list[LatencySample] = []
        for _ in range(100):
            t0 = time.perf_counter()
            cd = _compile_simple_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        stats = assert_p95_under(samples, budget_ms=SLO_BUDGET_P95_MS, metric_name="gate_baseline")
        # 健康度 · 简单 DoD P95 应 < 100ms
        assert stats.p95 < 100.0, f"gate baseline P95 {stats.p95:.3f}ms 异常"

    def test_t2_cold_start_p95_under_3s(self) -> None:
        """T2 · 冷启动首 50 次 · 不放宽."""
        compiler, gate = _new_gate()
        samples: list[LatencySample] = []
        for _ in range(50):
            t0 = time.perf_counter()
            cd = _compile_simple_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p95_under(samples, budget_ms=SLO_BUDGET_P95_MS, metric_name="gate_cold")

    def test_t3_sustained_5_windows(self) -> None:
        """T3 · 持续 500 次 · 5 个滑窗 P95 全 ≤ 3000ms."""
        compiler, gate = _new_gate()
        for _ in range(20):
            cd = _compile_simple_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
        ms_list: list[float] = []
        for _ in range(500):
            t0 = time.perf_counter()
            cd = _compile_simple_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
            ms_list.append((time.perf_counter() - t0) * 1000.0)
        for window_idx in range(5):
            window = ms_list[window_idx * 100 : (window_idx + 1) * 100]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p95_under(
                samples, budget_ms=SLO_BUDGET_P95_MS,
                metric_name=f"gate_window_{window_idx}",
            )

    def test_t4_large_dod_p95_under_3s(self) -> None:
        """T4 · 大 DoD (10H+10S) · P95 ≤ 3000ms · 模拟真实负载."""
        compiler, gate = _new_gate()
        # warmup
        for _ in range(10):
            cd = _compile_large_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
        samples: list[LatencySample] = []
        for _ in range(50):  # 50 次大 DoD 已能见 P95
            t0 = time.perf_counter()
            cd = _compile_large_dod(compiler)
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p95_under(samples, budget_ms=SLO_BUDGET_P95_MS, metric_name="gate_large")

    def test_t5_evaluate_only_hot_path(self) -> None:
        """T5 · 热路径 evaluate-only · compile 1 次 · evaluate 100 次 · P99 << 1s.

        实战路径 · DoD 通常编译一次后多次评估 · 测纯 eval 性能.
        """
        compiler, gate = _new_gate()
        cd = _compile_simple_dod(compiler)
        # warmup
        for _ in range(20):
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
        samples: list[LatencySample] = []
        for _ in range(500):
            t0 = time.perf_counter()
            gate.evaluate_gate(EvaluateGateCommand(
                project_id="p1", compiled=cd, metrics=_DEFAULT_METRICS, wp_id="wp-1",
            ))
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        # 热路径要求严: P99 ≤ 100ms (1000ms 留出大裕度也可)
        assert_p99_under(samples, budget_ms=1000.0, metric_name="gate_evaluate_only")

    def test_t6_degradation_detection(self) -> None:
        """T6 · 退化告警 · 4000ms 样本必触发 · 反向验 silent-pass 防呆."""
        samples = [LatencySample(elapsed_ms=4000.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p95 超标"):
            assert_p95_under(samples, budget_ms=SLO_BUDGET_P95_MS, metric_name="gate_degraded")
        # 边界: 2999ms 通过
        boundary = [LatencySample(elapsed_ms=2999.0) for _ in range(100)]
        stats = assert_p95_under(
            boundary, budget_ms=SLO_BUDGET_P95_MS, metric_name="gate_boundary",
        )
        assert stats.p95 == 2999.0
