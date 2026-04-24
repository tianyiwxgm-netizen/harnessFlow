"""WP-ζ-07 集成 TC · SDP-02 WP 循环 → IC-13 WARN → 3 次后升级 IC-14。

ζ1 escalator 的 5 态机逻辑 + soft_drift SDP-02 联调。
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.escalator.counter import FailureCounter
from app.supervisor.escalator.escalation_logic import EscalationLogic
from app.supervisor.escalator.schemas import WpFailEvent, WpFailLevel
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)
from app.supervisor.soft_drift.matcher import SoftDriftMatcher
from app.supervisor.soft_drift.schemas import Tick, TrapPatternId


@pytest.fixture
def pid() -> str:
    return "proj-sdp"


@pytest.fixture
def bus() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def sugg_consumer() -> MockSuggestionConsumer:
    return MockSuggestionConsumer()


@pytest.fixture
def rb_target() -> MockRollbackRouteTarget:
    return MockRollbackRouteTarget(known_wps={"wp-42"}, done_wps=set())


@pytest.fixture
def suggestion_pusher(
    pid: str, sugg_consumer: MockSuggestionConsumer, bus: EventBusStub
) -> SuggestionPusher:
    return SuggestionPusher(
        session_pid=pid, consumer=sugg_consumer, event_bus=bus
    )


@pytest.fixture
def rollback_pusher(
    pid: str, rb_target: MockRollbackRouteTarget, bus: EventBusStub
) -> RollbackPusher:
    return RollbackPusher(session_pid=pid, target=rb_target, event_bus=bus)


@pytest.fixture
def escalator(
    pid: str, rollback_pusher: RollbackPusher
) -> EscalationLogic:
    return EscalationLogic(
        session_pid=pid,
        counter=FailureCounter(),
        rollback_pusher=rollback_pusher,
    )


class TestSdpRollbackE2E:
    @pytest.mark.asyncio
    async def test_sdp_02_fires_warn_and_escalator_upgrades(
        self,
        pid: str,
        bus: EventBusStub,
        suggestion_pusher: SuggestionPusher,
        escalator: EscalationLogic,
        rb_target: MockRollbackRouteTarget,
    ) -> None:
        """
        流程：
        1. tick with wp_fail_count=3 → SDP-02 命中 → IC-13 WARN
        2. 3 次 WP 失败（L2）喂给 escalator → 第 3 次升级 IC-14 UPGRADE_TO_L1_01
        """
        matcher = SoftDriftMatcher(
            session_pid=pid,
            suggestion_pusher=suggestion_pusher,
            event_bus=bus,
        )

        # Step 1: SDP-02 WARN
        report = await matcher.feed(
            Tick(
                tick_seq=1,
                project_id=pid,
                captured_at_ms=1000,
                wp_fail_count=3,
            )
        )
        assert len(report.matches) >= 1
        assert any(
            m.pattern_id is TrapPatternId.SDP_02_WP_LOOP for m in report.matches
        )

        # Step 2: escalator 收 3 次 FAIL_L2
        for i in range(3):
            ev = WpFailEvent(
                project_id=pid,
                wp_id="wp-42",
                verdict_level=WpFailLevel.L2,
                verifier_report_id=f"vr-{i}",
                ts=datetime.now(UTC).isoformat(),
            )
            ack = await escalator.on_wp_failed(ev)
            if i < 2:
                assert ack is None  # 前 2 次不升级
        # 第 3 次升级
        assert ack is not None
        assert ack.escalated is True
        # 验证 upgrade target
        assert "upgrade" in ack.new_wp_state.value.lower() or ack.new_wp_state.value.startswith(
            "upgrade"
        )
        # rollback target 被调用 1 次（upgrade）
        assert rb_target.apply_call_count == 1

    @pytest.mark.asyncio
    async def test_sdp_warn_alone_does_not_trigger_escalator(
        self,
        pid: str,
        bus: EventBusStub,
        suggestion_pusher: SuggestionPusher,
        escalator: EscalationLogic,
        rb_target: MockRollbackRouteTarget,
    ) -> None:
        """SDP-02 WARN 本身不触发 escalator · escalator 靠独立的 WpFailEvent。"""
        matcher = SoftDriftMatcher(
            session_pid=pid,
            suggestion_pusher=suggestion_pusher,
            event_bus=bus,
        )
        await matcher.feed(
            Tick(
                tick_seq=1,
                project_id=pid,
                captured_at_ms=1000,
                wp_fail_count=3,
            )
        )
        # escalator 未收到任何 fail · rb_target 零调用
        assert rb_target.apply_call_count == 0
