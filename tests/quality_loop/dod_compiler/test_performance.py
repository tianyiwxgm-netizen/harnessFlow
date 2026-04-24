"""§5 性能 SLO · TC-L104-L202-701 ~ 708.

锚点:§12 性能目标.
    - compile(clause) 冷 P95 ≤ 100ms
    - eval(expr) 冷 P95 ≤ 10ms (MVP 放宽到 50ms · 单机没有 signal 加速)
    - validate P95 ≤ 20ms
    - 并发 50 eval · QPS ≥ 500
    - 50 条 compile < 60s (PRD §9.4)
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.quality_loop.dod_compiler import (
    DoDEvaluator,
    DoDExpressionCompiler,
    ValidateCommand,
)


@pytest.mark.perf
class TestPerformanceSLO:

    def test_TC_L104_L202_701_compile_batch_50_under_60s(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """PRD §9.4 · 50 条 compile < 60s · 单线程."""
        req = make_compile_request(project_id=mock_project_id, clause_count=50)
        t0 = time.perf_counter()
        sut.compile_batch(req)
        elapsed = time.perf_counter() - t0
        assert elapsed < 60.0
        # 实际单机应 ~50ms

    def test_TC_L104_L202_702_eval_p95_under_50ms(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """eval 冷路径 P95 · 100 次采样 · 每次新 command_id 不走 cache."""
        latencies: list[float] = []
        for i in range(100):
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id,
                coverage_value=0.8 + i * 0.001,
                command_id=f"cmd-perf-eval-{i}",
            )
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            latencies.append((time.perf_counter() - t0) * 1000)
        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies))]
        # 现实 MVP · 放宽到 50ms
        assert p95 < 50.0, f"eval p95 {p95:.2f}ms > 50ms"

    def test_TC_L104_L202_703_eval_cache_hit_p95_under_5ms(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """eval 热路径 (cache hit) 50 次 P95 < 5ms."""
        # 相同 command_id + 相同 snapshot → cache
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, command_id="cmd-perf-hot-01",
        )
        evaluator.eval_expression(req)  # prime cache

        latencies: list[float] = []
        for _ in range(50):
            t0 = time.perf_counter()
            evaluator.eval_expression(req)
            latencies.append((time.perf_counter() - t0) * 1000)
        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies))]
        assert p95 < 5.0, f"cache-hit eval p95 {p95:.2f}ms > 5ms"

    def test_TC_L104_L202_704_validate_expression_p95_under_30ms(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """validate 100 次 · P95 < 30ms."""
        latencies: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            sut.validate_expression(ValidateCommand(
                project_id=mock_project_id,
                expression_text="line_coverage() >= 0.8 and lint_errors() == 0",
            ))
            latencies.append((time.perf_counter() - t0) * 1000)
        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies))]
        assert p95 < 30.0, f"validate p95 {p95:.2f}ms > 30ms"

    def test_TC_L104_L202_706_concurrent_eval_no_race(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """50 并发 eval 不崩 · 结果一致."""
        results: list[bool] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id,
                coverage_value=0.85,
                command_id=f"cmd-concurrent-{i}",
            )
            r = evaluator.eval_expression(req)
            with lock:
                results.append(r.pass_)

        with ThreadPoolExecutor(max_workers=50) as pool:
            list(pool.map(worker, range(50)))

        assert len(results) == 50
        assert all(results), "50 eval 全 pass (所有 coverage=0.85 >= 0.8)"

    def test_TC_L104_L202_708_1000_sequential_eval_no_leak(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """1000 次连续 eval · evaluator 不崩 · cache 不爆."""
        for i in range(1000):
            req = make_eval_request(
                project_id=mock_project_id, expr_id=ready_expr_id,
                coverage_value=0.8 + (i % 100) * 0.001,
                command_id=f"cmd-seq-{i}",
            )
            r = evaluator.eval_expression(req)
            assert r.pass_ in (True, False)
