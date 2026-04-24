"""WP-ζ-07 集成 TC · tick → dim_collector → deviation_judge → event_sender 出口。"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.deviation_judge import (
    DeviationLevel,
    default_matrix,
    evaluate_deviation,
    filter_actionable,
)
from app.supervisor.deviation_judge.schemas import DimensionKey
from app.supervisor.dim_collector.schemas import (
    DegradationLevel,
    EightDimensionVector,
    SupervisorSnapshot,
    TriggerSource,
)
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    HardHaltEvidence,
    PushRollbackRouteCommand,
    PushSuggestionCommand,
    RequestHardHaltCommand,
    RouteEvidence,
    SuggestionLevel,
    SuggestionPriority,
    TargetStage,
)
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)


@pytest.fixture
def pid() -> str:
    return "proj-integ"


@pytest.fixture
def bus() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def sugg_consumer() -> MockSuggestionConsumer:
    return MockSuggestionConsumer()


@pytest.fixture
def halt_target() -> MockHardHaltTarget:
    return MockHardHaltTarget()


@pytest.fixture
def rb_target() -> MockRollbackRouteTarget:
    return MockRollbackRouteTarget(known_wps={"wp-42"}, done_wps=set())


def _make_snap(
    pid: str,
    *,
    latency_p99: int | None = None,
    self_repair: float | None = None,
    rollback_24h: int | None = None,
) -> SupervisorSnapshot:
    vec_kwargs: dict = {}
    if latency_p99 is not None:
        vec_kwargs["latency_slo"] = {"p99_ms": latency_p99}
    if self_repair is not None:
        vec_kwargs["self_repair_rate"] = {"rate": self_repair}
    if rollback_24h is not None:
        vec_kwargs["rollback_counter"] = {"count_24h": rollback_24h}
    vec = EightDimensionVector(**vec_kwargs)
    return SupervisorSnapshot(
        project_id=pid,
        snapshot_id="snap-integ0001",
        captured_at_ms=1000,
        trigger=TriggerSource.TICK,
        eight_dim_vector=vec,
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=10,
    )


# ==================== WARN → IC-13 ====================


class TestWarnPath:
    @pytest.mark.asyncio
    async def test_warn_triggers_ic13(
        self,
        pid: str,
        bus: EventBusStub,
        sugg_consumer: MockSuggestionConsumer,
    ) -> None:
        """latency_slo.p99_ms=250 · WARN · 推 IC-13。"""
        snap = _make_snap(pid, latency_p99=250)
        verdicts = evaluate_deviation(snap, default_matrix())
        actionable = filter_actionable(verdicts)
        assert len(actionable) == 1
        assert actionable[0].level is DeviationLevel.WARN

        sp = SuggestionPusher(session_pid=pid, consumer=sugg_consumer, event_bus=bus)
        for v in actionable:
            cmd = PushSuggestionCommand(
                suggestion_id=f"sugg-{v.verdict_id}",
                project_id=pid,
                level=SuggestionLevel.WARN,
                content=f"[WARN] {v.reason}",
                observation_refs=(f"snap-{v.snapshot_id}",),
                priority=SuggestionPriority.P1,
                ts=datetime.now(UTC).isoformat(),
            )
            ack = await sp.push_suggestion(cmd)
            assert ack.enqueued is True

        evs = await bus.read_event_stream(pid)
        assert any(e.type == "L1-07:suggestion_pushed" for e in evs)


# ==================== ERROR → IC-14 ====================


class TestErrorPath:
    @pytest.mark.asyncio
    async def test_error_triggers_ic14(
        self,
        pid: str,
        bus: EventBusStub,
        rb_target: MockRollbackRouteTarget,
    ) -> None:
        """latency_slo.p99_ms=600 · ERROR · 推 IC-14 L2。"""
        snap = _make_snap(pid, latency_p99=600)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.ERROR

        rp = RollbackPusher(session_pid=pid, target=rb_target, event_bus=bus)
        cmd = PushRollbackRouteCommand(
            route_id=f"route-{latency_v.verdict_id[:12]}",
            project_id=pid,
            wp_id="wp-42",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-latency-error"),
            ts=datetime.now(UTC).isoformat(),
        )
        ack = await rp.push_rollback_route(cmd)
        assert ack.applied is True

        evs = await bus.read_event_stream(pid)
        assert any(e.type == "L1-07:rollback_route_pushed" for e in evs)


# ==================== CRITICAL → IC-15 ====================


class TestCriticalPath:
    @pytest.mark.asyncio
    async def test_critical_triggers_ic15(
        self,
        pid: str,
        bus: EventBusStub,
        halt_target: MockHardHaltTarget,
    ) -> None:
        """latency_slo.p99_ms=5000 · CRITICAL · 推 IC-15。"""
        snap = _make_snap(pid, latency_p99=5000)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.CRITICAL

        hr = HaltRequester(session_pid=pid, target=halt_target, event_bus=bus)
        cmd = RequestHardHaltCommand(
            halt_id=f"halt-{latency_v.verdict_id[:12]}",
            project_id=pid,
            red_line_id=f"REDLINE-CRITICAL-{latency_v.dimension.value}",
            evidence=HardHaltEvidence(
                observation_refs=(f"snap-{latency_v.snapshot_id}",),
                confirmation_count=2,
            ),
            ts=datetime.now(UTC).isoformat(),
        )
        ack = await hr.request_hard_halt(cmd)
        assert ack.halted is True
        assert halt_target.halt_call_count == 1

        evs = await bus.read_event_stream(pid)
        assert any(e.type == "L1-01:hard_halted" for e in evs)


# ==================== Multi-dim · multi-IC ====================


class TestMultiDimMultiIC:
    @pytest.mark.asyncio
    async def test_three_dims_route_to_three_ICs(
        self,
        pid: str,
        bus: EventBusStub,
        sugg_consumer: MockSuggestionConsumer,
        halt_target: MockHardHaltTarget,
        rb_target: MockRollbackRouteTarget,
    ) -> None:
        """
        latency CRITICAL (IC-15) + self_repair WARN (IC-13) + rollback ERROR (IC-14)
        在一次 snapshot 里全部触发。
        """
        snap = _make_snap(
            pid,
            latency_p99=5000,  # CRITICAL
            self_repair=0.4,   # WARN
            rollback_24h=7,    # ERROR
        )
        verdicts = evaluate_deviation(snap, default_matrix())
        by_dim = {v.dimension: v for v in verdicts}
        assert by_dim[DimensionKey.LATENCY_SLO].level is DeviationLevel.CRITICAL
        assert by_dim[DimensionKey.SELF_REPAIR_RATE].level is DeviationLevel.WARN
        assert by_dim[DimensionKey.ROLLBACK_COUNTER].level is DeviationLevel.ERROR

        # 分别走 3 个 IC
        sp = SuggestionPusher(session_pid=pid, consumer=sugg_consumer, event_bus=bus)
        rp = RollbackPusher(session_pid=pid, target=rb_target, event_bus=bus)
        hr = HaltRequester(session_pid=pid, target=halt_target, event_bus=bus)

        # WARN → IC-13
        warn_v = by_dim[DimensionKey.SELF_REPAIR_RATE]
        await sp.push_suggestion(
            PushSuggestionCommand(
                suggestion_id=f"sugg-{warn_v.verdict_id}",
                project_id=pid,
                level=SuggestionLevel.WARN,
                content=f"[WARN] {warn_v.reason}",
                observation_refs=(f"snap-{warn_v.snapshot_id}",),
                priority=SuggestionPriority.P1,
                ts=datetime.now(UTC).isoformat(),
            )
        )

        # ERROR → IC-14
        err_v = by_dim[DimensionKey.ROLLBACK_COUNTER]
        await rp.push_rollback_route(
            PushRollbackRouteCommand(
                route_id=f"route-{err_v.verdict_id[:12]}",
                project_id=pid,
                wp_id="wp-42",
                verdict=FailVerdict.FAIL_L2,
                target_stage=TargetStage.S4,
                level_count=1,
                evidence=RouteEvidence(verifier_report_id="vr-rb-err"),
                ts=datetime.now(UTC).isoformat(),
            )
        )

        # CRITICAL → IC-15
        crit_v = by_dim[DimensionKey.LATENCY_SLO]
        await hr.request_hard_halt(
            RequestHardHaltCommand(
                halt_id=f"halt-{crit_v.verdict_id[:12]}",
                project_id=pid,
                red_line_id="REDLINE-LATENCY-CRIT",
                evidence=HardHaltEvidence(
                    observation_refs=(f"snap-{crit_v.snapshot_id}",),
                    confirmation_count=2,
                ),
                ts=datetime.now(UTC).isoformat(),
            )
        )

        # 验证 3 套事件都写进了 bus
        evs = await bus.read_event_stream(pid)
        types = {e.type for e in evs}
        assert "L1-07:suggestion_pushed" in types
        assert "L1-07:rollback_route_pushed" in types
        assert "L1-01:hard_halted" in types
        assert halt_target.halt_call_count == 1
