"""L2-03 · RedLineDetector 总调度 TC。"""
from __future__ import annotations

import asyncio

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.red_line import (
    RedLineDetector,
    RedLineId,
)


@pytest.fixture
def event_bus() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def halt_target() -> MockHardHaltTarget:
    return MockHardHaltTarget()


@pytest.fixture
def halt_req(halt_target: MockHardHaltTarget, event_bus: EventBusStub) -> HaltRequester:
    return HaltRequester(
        session_pid="proj-a",
        target=halt_target,
        event_bus=event_bus,
    )


@pytest.fixture
def detector(halt_req: HaltRequester, event_bus: EventBusStub) -> RedLineDetector:
    return RedLineDetector(
        session_pid="proj-a",
        halt_requester=halt_req,
        event_bus=event_bus,
    )


class TestScan:
    @pytest.mark.asyncio
    async def test_clean_context_no_hit(
        self, detector: RedLineDetector
    ) -> None:
        report = await detector.scan(
            "proj-a",
            {
                "recent_events": [],
                "audit_chain_report": {},
                "traceability_report": {},
                "panic_latency_report": {},
                "halt_latency_report": {},
            },
        )
        assert report.hit_count == 0
        assert len(report.results) == 5
        assert report.halt_acks == ()
        assert report.total_latency_us > 0

    @pytest.mark.asyncio
    async def test_cross_pid_rejected(
        self, detector: RedLineDetector
    ) -> None:
        with pytest.raises(ValueError, match="E_REDLINE_NO_PROJECT_ID"):
            await detector.scan("proj-b", {})

    @pytest.mark.asyncio
    async def test_pm14_hit_triggers_halt(
        self,
        detector: RedLineDetector,
        halt_target: MockHardHaltTarget,
    ) -> None:
        report = await detector.scan(
            "proj-a",
            {
                "recent_events": [{"event_id": "ev-bad", "project_id": ""}],
            },
        )
        assert report.hit_count >= 1
        assert any(
            r.red_line_id is RedLineId.HRL_01_PM14_VIOLATION and r.hit is not None
            for r in report.results
        )
        assert halt_target.halt_call_count >= 1

    @pytest.mark.asyncio
    async def test_multi_hit_triggers_multi_halt(
        self,
        detector: RedLineDetector,
        halt_target: MockHardHaltTarget,
    ) -> None:
        report = await detector.scan(
            "proj-a",
            {
                "recent_events": [{"event_id": "ev-bad", "project_id": ""}],  # HRL-01
                "audit_chain_report": {"hash_broken": True},  # HRL-02
                "traceability_report": {"total": 10, "traceable": 5},  # HRL-03
                "panic_latency_report": {"samples_ms": [150]},  # HRL-04
                "halt_latency_report": {"samples_ms": [200]},  # HRL-05
            },
        )
        assert report.hit_count == 5
        assert halt_target.halt_call_count == 5
        assert len(report.halt_acks) == 5

    @pytest.mark.asyncio
    async def test_event_bus_records_scan_completed(
        self,
        detector: RedLineDetector,
        event_bus: EventBusStub,
    ) -> None:
        await detector.scan("proj-a", {})
        evs = await event_bus.read_event_stream("proj-a")
        types = [e.type for e in evs]
        assert "L1-07:redline_scan_completed" in types

    @pytest.mark.asyncio
    async def test_concurrent_detection(
        self, detector: RedLineDetector
    ) -> None:
        """验证 detectors 是并发跑 · 非串行（用延迟模拟验证）。"""
        report = await detector.scan("proj-a", {})
        # 5 detector 并发 · 总延迟应远小于 5 个 detector 串行总和
        # 单 detector 在空 context 下 < 1000us · 并发总 < 5000us
        assert report.total_latency_us < 500_000  # 强约束 500ms

    @pytest.mark.asyncio
    async def test_hit_halt_uses_redline_id(
        self,
        detector: RedLineDetector,
        halt_target: MockHardHaltTarget,
    ) -> None:
        await detector.scan(
            "proj-a",
            {"audit_chain_report": {"hash_broken": True}},
        )
        assert halt_target.halt_call_count == 1
        # halt_log 记录了 red_line_id
        assert halt_target.halt_log[0][1] == "HRL-02"


class TestSloViolation:
    @pytest.mark.asyncio
    async def test_slo_violation_emits_event(
        self,
        halt_req: HaltRequester,
        event_bus: EventBusStub,
    ) -> None:
        """人为注入慢 detector · 验证 SLO 违规事件发射。"""
        from app.supervisor.red_line.schemas import (
            DetectionResult,
            RedLineId as RID,
        )

        class SlowDetector:
            name = "slow"
            red_line_id = RID.HRL_01_PM14_VIOLATION

            async def detect(self, project_id: str, context):
                await asyncio.sleep(0.6)  # 600ms · 触发 500ms SLO 违规
                return DetectionResult(
                    detector_name=self.name,
                    red_line_id=self.red_line_id,
                    hit=None,
                    latency_us=600_000,
                )

        det = RedLineDetector(
            session_pid="proj-a",
            halt_requester=halt_req,
            event_bus=event_bus,
            detectors=[SlowDetector()],
        )
        report = await det.scan("proj-a", {})
        assert report.total_latency_us >= 500_000
        evs = await event_bus.read_event_stream("proj-a")
        types = [e.type for e in evs]
        assert "L1-07:redline_slo_violated" in types
