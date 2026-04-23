"""L1-06 L2-05 · perf · 3-2 §5."""
from __future__ import annotations

import gc
import time
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.retrieval.schemas import (
    RerankContext,
    RerankRequest,
    StageTransitionedEvent,
)

_WARMUP = 20


def _pXX_ms(samples_s: list[float], percentile: float) -> float:
    measured = samples_s[_WARMUP:] if len(samples_s) > _WARMUP else samples_s
    if not measured:
        return 0.0
    samples_ms = sorted(s * 1000.0 for s in measured)
    idx = max(0, int(round(len(samples_ms) * percentile)) - 1)
    return samples_ms[idx]


@pytest.mark.perf
class TestL2_05_SLO:

    def test_TC_L106_L205_501_rerank_100_p50_le_30ms(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        ctx = RerankContext(
            current_stage="S3", task_type="c", tech_stack=["python"]
        )
        # Precompute candidates once: SLO measures rerank() only,
        # not fixture construction (MagicMock ~0.5ms per object).
        cands = make_candidates(100)
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for i in range(_WARMUP + 100):
                req = RerankRequest(
                    project_id=mock_project_id,
                    rerank_id=f"p-{i}",
                    candidates=cands,
                    context=ctx,
                    top_k=5,
                    trace_id="t",
                )
                t0 = time.perf_counter()
                sut.rerank(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p50 = _pXX_ms(samples, 0.50)
        assert p50 <= 30.0, f"P50 = {p50:.2f}ms"

    def test_TC_L106_L205_502_rerank_100_p99_le_100ms(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        ctx = RerankContext(
            current_stage="S3", task_type="c", tech_stack=["python"]
        )
        cands = make_candidates(100)
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for i in range(_WARMUP + 200):
                req = RerankRequest(
                    project_id=mock_project_id,
                    rerank_id=f"p99-{i}",
                    candidates=cands,
                    context=ctx,
                    top_k=5,
                    trace_id="t",
                )
                t0 = time.perf_counter()
                sut.rerank(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p99 = _pXX_ms(samples, 0.99)
        assert p99 <= 100.0, f"P99 = {p99:.2f}ms"

    def test_TC_L106_L205_503_rerank_1k_p99_le_200ms(
        self, sut, mock_project_id, make_candidates
    ) -> None:
        ctx = RerankContext(
            current_stage="S3", task_type="c", tech_stack=["python"]
        )
        cands = make_candidates(1000)
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for i in range(_WARMUP + 50):
                req = RerankRequest(
                    project_id=mock_project_id,
                    rerank_id=f"1k-{i}",
                    candidates=cands,
                    context=ctx,
                    top_k=10,
                    trace_id="t",
                )
                t0 = time.perf_counter()
                sut.rerank(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p99 = _pXX_ms(samples, 0.99)
        assert p99 <= 200.0, f"P99 = {p99:.2f}ms"

    def test_TC_L106_L205_504_stage_injection_e2e_p95_le_2s(
        self, sut, mock_project_id, mock_l2_02, mock_l1_01
    ) -> None:
        mock_l2_02.reverse_recall.return_value = MagicMock(
            candidates=[{"entry_id": "c"}],
            recalled_count=1,
            scope_layers_hit=["project"],
            duration_ms=30,
        )
        samples: list[float] = []
        for i in range(20):
            t0 = time.perf_counter()
            sut.on_stage_transitioned(
                StageTransitionedEvent(
                    event_id=f"e-{i}",
                    event_type="L1-02:stage_transitioned",
                    project_id=mock_project_id,
                    stage_from="S2",
                    stage_to="S3",
                    transition_reason="gate",
                    transition_at="2026-04-22T10:00:00Z",
                    trace_id="t",
                )
            )
            samples.append(time.perf_counter() - t0)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1]
        assert p95 <= 2.0

    def test_TC_L106_L205_505_strategy_lookup_p99_le_5ms(
        self, sut
    ) -> None:
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 1000):
                t0 = time.perf_counter()
                sut._strategy_repo.get("S3")
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p99 = _pXX_ms(samples, 0.99)
        assert p99 <= 5.0, f"P99 = {p99:.2f}ms"
