"""L2-03 · 5 detector 单测。"""
from __future__ import annotations

import pytest

from app.supervisor.red_line import (
    AuditChainBrokenDetector,
    HaltLatencyMissDetector,
    PanicLatencyMissDetector,
    PM14Violator,
    RedLineId,
    TraceabilityDetector,
)


# ==================== PM14Violator (HRL-01) ====================


class TestPM14Violator:
    @pytest.mark.asyncio
    async def test_no_events_no_hit(self) -> None:
        det = PM14Violator()
        res = await det.detect("proj-a", {"recent_events": []})
        assert res.hit is None
        assert res.red_line_id is RedLineId.HRL_01_PM14_VIOLATION

    @pytest.mark.asyncio
    async def test_missing_pid_hits(self) -> None:
        det = PM14Violator()
        events = [{"event_id": "ev-1", "project_id": ""}]
        res = await det.detect("proj-a", {"recent_events": events})
        assert res.hit is not None
        assert "violate PM-14" in res.hit.reason
        assert "ev-1" in res.hit.evidence.observation_refs

    @pytest.mark.asyncio
    async def test_cross_pid_hits(self) -> None:
        det = PM14Violator()
        events = [
            {"event_id": "ev-1", "project_id": "proj-a"},  # OK
            {"event_id": "ev-2", "project_id": "proj-b"},  # 污染
        ]
        res = await det.detect("proj-a", {"recent_events": events})
        assert res.hit is not None
        assert "ev-2" in res.hit.evidence.observation_refs
        assert "ev-1" not in res.hit.evidence.observation_refs

    @pytest.mark.asyncio
    async def test_clean_events_no_hit(self) -> None:
        det = PM14Violator()
        events = [
            {"event_id": f"ev-{i}", "project_id": "proj-a"} for i in range(5)
        ]
        res = await det.detect("proj-a", {"recent_events": events})
        assert res.hit is None


# ==================== AuditChainBrokenDetector (HRL-02) ====================


class TestAuditChainBroken:
    @pytest.mark.asyncio
    async def test_no_report_no_hit(self) -> None:
        det = AuditChainBrokenDetector()
        res = await det.detect("proj-a", {})
        assert res.hit is None

    @pytest.mark.asyncio
    async def test_hash_broken_hits(self) -> None:
        det = AuditChainBrokenDetector()
        res = await det.detect(
            "proj-a",
            {
                "audit_chain_report": {
                    "hash_broken": True,
                    "broken_at": "ev-99",
                }
            },
        )
        assert res.hit is not None
        assert "HRL-02" in res.hit.reason

    @pytest.mark.asyncio
    async def test_missing_events_hits(self) -> None:
        det = AuditChainBrokenDetector()
        res = await det.detect(
            "proj-a",
            {
                "audit_chain_report": {
                    "hash_broken": False,
                    "missing_events": ["ev-1", "ev-2"],
                }
            },
        )
        assert res.hit is not None
        assert "ev-1" in res.hit.evidence.observation_refs


# ==================== TraceabilityDetector (HRL-03) ====================


class TestTraceability:
    @pytest.mark.asyncio
    async def test_total_zero_no_hit(self) -> None:
        det = TraceabilityDetector()
        res = await det.detect(
            "proj-a", {"traceability_report": {"total": 0, "traceable": 0}}
        )
        assert res.hit is None

    @pytest.mark.asyncio
    async def test_rate_100_no_hit(self) -> None:
        det = TraceabilityDetector()
        res = await det.detect(
            "proj-a",
            {"traceability_report": {"total": 100, "traceable": 100}},
        )
        assert res.hit is None

    @pytest.mark.asyncio
    async def test_rate_99_hits(self) -> None:
        det = TraceabilityDetector()
        res = await det.detect(
            "proj-a",
            {
                "traceability_report": {
                    "total": 100,
                    "traceable": 99,
                    "untraceable_refs": ["ev-untraceable"],
                }
            },
        )
        assert res.hit is not None
        assert "99.000%" in res.hit.reason or "99.0" in res.hit.reason
        assert "ev-untraceable" in res.hit.evidence.observation_refs


# ==================== PanicLatencyMissDetector (HRL-04) ====================


class TestPanicLatency:
    @pytest.mark.asyncio
    async def test_all_under_threshold(self) -> None:
        det = PanicLatencyMissDetector()
        res = await det.detect(
            "proj-a",
            {"panic_latency_report": {"samples_ms": [50, 80, 99]}},
        )
        assert res.hit is None

    @pytest.mark.asyncio
    async def test_one_violation_hits(self) -> None:
        det = PanicLatencyMissDetector()
        res = await det.detect(
            "proj-a",
            {"panic_latency_report": {"samples_ms": [50, 150, 80]}},
        )
        assert res.hit is not None
        assert "max 150ms" in res.hit.reason

    @pytest.mark.asyncio
    async def test_custom_threshold(self) -> None:
        det = PanicLatencyMissDetector()
        res = await det.detect(
            "proj-a",
            {"panic_latency_report": {"samples_ms": [80], "threshold_ms": 50}},
        )
        assert res.hit is not None


# ==================== HaltLatencyMissDetector (HRL-05) ====================


class TestHaltLatency:
    @pytest.mark.asyncio
    async def test_all_under_threshold(self) -> None:
        det = HaltLatencyMissDetector()
        res = await det.detect(
            "proj-a",
            {"halt_latency_report": {"samples_ms": [50, 80, 99]}},
        )
        assert res.hit is None

    @pytest.mark.asyncio
    async def test_one_violation_hits(self) -> None:
        det = HaltLatencyMissDetector()
        res = await det.detect(
            "proj-a",
            {"halt_latency_report": {"samples_ms": [50, 200]}},
        )
        assert res.hit is not None
        assert "max 200ms" in res.hit.reason
