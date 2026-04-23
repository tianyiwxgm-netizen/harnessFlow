"""L1-06 L2-02 · SLO perf (5 TC) · 3-2 §5."""
from __future__ import annotations

import gc
import time

import pytest

from app.knowledge_base.reader.schemas import ApplicableContext, ReadRequest
from app.knowledge_base.reader.service import KBReadService

_WARMUP = 20


def _pXX_ms(samples_s: list[float], percentile: float) -> float:
    measured = samples_s[_WARMUP:] if len(samples_s) > _WARMUP else samples_s
    if not measured:
        return 0.0
    samples_ms = sorted(s * 1000.0 for s in measured)
    idx = max(0, int(round(len(samples_ms) * percentile)) - 1)
    return samples_ms[idx]


@pytest.mark.perf
class TestL2_02_SLO:

    def test_TC_L106_L202_501_p50_le_50ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=3, project=3, global_=3)
        req = ReadRequest(
            trace_id="perf",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=5,
            cache_enabled=False,
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 100):
                t0 = time.perf_counter()
                sut.read(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p50 = _pXX_ms(samples, 0.50)
        assert p50 <= 50.0, f"P50 = {p50:.2f}ms"

    def test_TC_L106_L202_502_p95_le_200ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=10, project=10, global_=10)
        req = ReadRequest(
            trace_id="perf",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=10,
            cache_enabled=False,
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 200):
                t0 = time.perf_counter()
                sut.read(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p95 = _pXX_ms(samples, 0.95)
        assert p95 <= 200.0, f"P95 = {p95:.2f}ms"

    def test_TC_L106_L202_503_p99_le_500ms(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=100, project=100, global_=100)
        req = ReadRequest(
            trace_id="perf",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=10,
            cache_enabled=False,
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 100):
                t0 = time.perf_counter()
                sut.read(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        p99 = _pXX_ms(samples, 0.99)
        assert p99 <= 500.0, f"P99 = {p99:.2f}ms"

    def test_TC_L106_L202_504_cache_hit_rate_ge_60pct(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=2, project=2, global_=2)
        req = ReadRequest(
            trace_id="perf-cache",
            project_id=mock_project_id,
            session_id=mock_session_id,
            applicable_context=ApplicableContext(),
            top_k=3,
            cache_enabled=True,
        )
        hits = 0
        total = 10
        for _ in range(total):
            res = sut.read(req)
            if res.meta.cache_hit:
                hits += 1
        assert hits / total >= 0.6

    def test_TC_L106_L202_505_error_rate_le_0_5_pct(
        self, sut: KBReadService, fake_repo, mock_project_id, mock_session_id
    ) -> None:
        fake_repo.seed(session=3, project=3, global_=3)
        errors = 0
        total = 200
        for i in range(total):
            req = ReadRequest(
                trace_id=f"err-{i}",
                project_id=mock_project_id,
                session_id=mock_session_id,
                applicable_context=ApplicableContext(),
                top_k=3,
                cache_enabled=False,
            )
            if sut.read(req).error_hint:
                errors += 1
        assert errors / total <= 0.005
