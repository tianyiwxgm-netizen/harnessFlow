"""L1-06 L2-01 · SLO perf tests · 3-2 §5.

Marked ``@pytest.mark.perf`` — runs P99 latency budget checks by calling the
hot path N times and computing a simple percentile. pytest-benchmark's API
is only used for its plugin registration; the tests compute stats manually
to avoid coupling to benchmark-library internals.
"""
from __future__ import annotations

import gc
import time

import pytest

from app.l1_06.l2_01.schemas import (
    ActivateEvent,
    ExpireScanTrigger,
    PromotionRequest,
    ScopeDecisionRequest,
    WriteSlotRequest,
)
from app.l1_06.l2_01.tier_manager import TierManager


class _NoopBus:
    """Lightweight bus for perf tests.

    ``MagicMock`` records every call, which over hundreds of iterations adds
    per-call overhead (and eventually GC pressure) that swamps the microsecond
    hot path being measured.
    """

    def append(self, **_kw) -> None:  # noqa: D401
        return None


@pytest.fixture
def sut_perf(
    mock_project_id: str,
    mock_session_id: str,
    mock_clock,
    mock_fs,
) -> TierManager:
    tm = TierManager(
        clock=mock_clock,
        event_bus=_NoopBus(),
        fs_root=mock_fs,
        tier_layout_path=mock_fs / "configs" / "tier-layout.yaml",
    )
    tm._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
    tm._session_idx.register_session(mock_project_id, mock_session_id)
    return tm


_WARMUP = 50


def _p99_ms(samples_s: list[float]) -> float:
    """P99 in milliseconds, measured on samples after the warmup window."""
    measured = samples_s[_WARMUP:] if len(samples_s) > _WARMUP else samples_s
    if not measured:
        return 0.0
    samples_ms = sorted(s * 1000.0 for s in measured)
    # Use ceil(N * 0.99) - 1 in 0-indexed terms.
    idx = max(0, int(round(len(samples_ms) * 0.99)) - 1)
    return samples_ms[idx]


@pytest.mark.perf
class TestL2_01_SLO:

    def test_TC_L106_L201_501_resolve_scope_p99_le_5ms(
        self, sut_perf: TierManager, mock_project_id: str, mock_session_id: str
    ) -> None:
        req = ScopeDecisionRequest(
            request_id="p1",
            project_id=mock_project_id,
            session_id=mock_session_id,
            requester_bc="BC-01",
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 500):
                t0 = time.perf_counter()
                sut_perf.resolve_read_scope(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        assert _p99_ms(samples) <= 5.0, f"P99 = {_p99_ms(samples):.2f}ms"

    def test_TC_L106_L201_502_allocate_slot_p99_le_10ms(
        self,
        sut_perf: TierManager,
        mock_project_id: str,
        mock_session_id: str,
        make_entry_candidate,
    ) -> None:
        cand = make_entry_candidate(kind="pattern", title="perf")
        req = WriteSlotRequest(
            request_id="p2",
            project_id=mock_project_id,
            session_id=mock_session_id,
            entry_candidate=cand,
            requester_bc="BC-01",
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 300):
                t0 = time.perf_counter()
                sut_perf.allocate_session_write_slot(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        assert _p99_ms(samples) <= 10.0, f"P99 = {_p99_ms(samples):.2f}ms"

    def test_TC_L106_L201_503_promotion_p99_le_20ms(
        self, sut_perf: TierManager, mock_project_id: str
    ) -> None:
        req = PromotionRequest(
            request_id="p3",
            project_id=mock_project_id,
            entry_id="ent-perf",
            from_scope="session",
            to_scope="project",
            observed_count=2,
            approval={
                "type": "auto",
                "approver": "system",
                "approved_at": "2026-04-22T10:00:00Z",
            },
            requester_bc="BC-07",
        )
        gc.collect()
        gc.disable()
        try:
            samples: list[float] = []
            for _ in range(_WARMUP + 200):
                t0 = time.perf_counter()
                sut_perf.check_promotion_rule(req)
                samples.append(time.perf_counter() - t0)
        finally:
            gc.enable()
        assert _p99_ms(samples) <= 20.0

    def test_TC_L106_L201_504_expire_scan_le_30s(
        self, sut: TierManager, fake_fs_with_entries
    ) -> None:
        """Scan N×M entries ≤ 30s.

        Note: full 100k-entry scan runs too long under CI; use a representative
        10-project × 100-entries fixture here (=1000 entries) and budget
        accordingly. The 30s upper bound is the hard ceiling; this sample must
        be well under it.
        """
        fake_fs_with_entries(project_count=10, entries_per_project=100)
        sut._tier_repo.register_projects([f"p-seed-{i:03d}" for i in range(10)])
        trig = ExpireScanTrigger(
            trigger_id="perf-scan",
            trigger_at="2026-04-22T03:00:00Z",
            scan_mode="all",
            ttl_days=7,
        )
        t0 = time.perf_counter()
        sut.run_expire_scan(trig)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 30.0, f"scan {elapsed:.2f}s > 30s"
        # Also assert throughput: 1k entries should complete well under 5s
        assert elapsed <= 5.0, f"1k-entry scan too slow: {elapsed:.2f}s"

    def test_TC_L106_L201_505_activate_e2e_le_1s(self, sut: TierManager) -> None:
        evt = ActivateEvent(
            event_type="L1-02:project_created",
            project_id="p-perf",
            project_name="P",
            stage="S0_gate",
            created_at="2026-04-22T10:00:00Z",
            resumed_from_snapshot=False,
        )
        t0 = time.perf_counter()
        sut.on_project_activated(evt)
        assert (time.perf_counter() - t0) <= 1.0
