"""WP09-02 · IC-14 消费端 · L1-07 (Supervisor) → L1-04 (RollbackRouter).

**契约链**:
1. L1-07 Supervisor 判 WP 连续失败 → `RollbackPusher.push` (Dev-ζ producer)
2. 生成 `PushRollbackRouteCommand` (Dev-ζ schemas)
3. L1-04 `IC14Consumer.consume` (WP07 consumer · 本 WP) 收 command
4. 分类（VerdictClassifier）→ 映射（StageMapper）→ 执行（RollbackExecutor）
5. 调 L1-02 `state_transition` (Dev-δ merged)
6. emit L1-09 audit (rollback_executed / rollback_escalated)

**真实代码**:
- Dev-ζ `RollbackPusher` · `MockRollbackRouteTarget` · `_LEGAL_MAPPING` → 生产 command
- L1-04 `IC14Consumer` (WP07) → 消费 command
- 连起来: Dev-ζ producer 产的 PushRollbackRouteCommand 直接进 WP07 consumer

本 TC 验证 **真实生产者和真实消费者的 wire 正确**，而非各自单元.
"""
from __future__ import annotations

import pytest

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)


# ==============================================================================
# TC-1 · Producer-Consumer wire · Dev-ζ RollbackPusher → WP07 IC14Consumer
# ==============================================================================


class _ConsumerAsTarget:
    """把 WP07 IC14Consumer 包成 Dev-ζ pusher 期望的 target 协议.

    RollbackRouteTarget Protocol 要求:
    - `is_known_wp(wp_id) -> bool`
    - `is_done_wp(wp_id) -> bool`
    - `async apply_route(command) -> NewWpState`

    我们让 apply_route 调 WP07 consumer.consume · 然后返 ack.new_wp_state.
    这样 Dev-ζ 真实 pusher 走 validate → apply_route → wp07 走 classifier/mapper/executor → L1-02 state_transition.
    """

    def __init__(
        self,
        ic14_consumer: IC14Consumer,
        known_wps: set[str] | None = None,
        done_wps: set[str] | None = None,
    ) -> None:
        self._consumer = ic14_consumer
        self.known_wps = known_wps or set()
        self.done_wps = done_wps or set()
        self.apply_call_count = 0

    def is_known_wp(self, wp_id: str) -> bool:
        return wp_id in self.known_wps

    def is_done_wp(self, wp_id: str) -> bool:
        return wp_id in self.done_wps

    async def apply_route(self, command: PushRollbackRouteCommand) -> NewWpState:
        self.apply_call_count += 1
        ack = await self._consumer.consume(command)
        return ack.new_wp_state


class _AsyncEventBusCollector:
    """Dev-ζ EventBusStub-like · 只收事件不做 hash-chain (wire 测试用)."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def append_event(self, **kw) -> str:
        self.events.append(kw)
        return f"ev-{len(self.events)}"


class TestProducerConsumerWire:
    """Dev-ζ 真生产 PushRollbackRouteCommand · WP07 真消费 · 端到端跑通."""

    async def test_pusher_to_consumer_fail_l1_s3(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """IC-14 full e2e: Supervisor pusher → Consumer → L1-02 state_transition.

        FAIL_L1 → S3 · 常规 stage-retry · escalated=False.
        """
        bus = _AsyncEventBusCollector()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=bus,
        )
        target = _ConsumerAsTarget(consumer, known_wps={"wp-ic14-001"})
        pusher = RollbackPusher(
            session_pid=project_id, target=target, event_bus=bus,
        )

        # 构造 Dev-ζ 真 command
        cmd = PushRollbackRouteCommand(
            route_id="route-e2e-1",
            project_id=project_id,
            wp_id="wp-ic14-001",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-pw-1"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await pusher.push_rollback_route(cmd)

        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S3
        assert ack.escalated is False
        # 真 state_transition 被触发 (consumer → executor → state_transition)
        assert len(state_spy.calls) == 1
        assert state_spy.calls[0]["project_id"] == project_id
        assert state_spy.calls[0]["new_wp_state"] == "retry_s3"

    async def test_pusher_to_consumer_fail_l4_critical(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """FAIL_L4 · 首次即升级语义 · escalated=False (level_count=1)."""
        bus = _AsyncEventBusCollector()
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=bus,
        )
        target = _ConsumerAsTarget(consumer, known_wps={"wp-fail4"})
        pusher = RollbackPusher(
            session_pid=project_id, target=target, event_bus=bus,
        )

        cmd = PushRollbackRouteCommand(
            route_id="route-fail4-001",
            project_id=project_id,
            wp_id="wp-fail4",
            verdict=FailVerdict.FAIL_L4,
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-f4"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await pusher.push_rollback_route(cmd)
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.UPGRADED_TO_L1_01
        # state_transition 被触发 · target_stage 为 UPGRADE
        assert state_spy.calls[0]["target_stage"] == "UPGRADE_TO_L1-01"


# ==============================================================================
# TC-2 · 幂等 · 同 route_id 多次 · 只执行 1 次
# ==============================================================================


class TestIdempotency:
    """幂等 by route_id: Dev-ζ + WP07 双侧 · 真实 command 重复消费仅执行 1 次."""

    async def test_same_route_id_single_state_transition(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """同 route_id 送 consumer 3 次 · state_transition 只被调 1 次."""

        class _AsyncBus:
            async def append_event(self, **kw):
                return "ev"

        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=_AsyncBus(),
        )
        cmd = PushRollbackRouteCommand(
            route_id="route-idem-42",
            project_id=project_id,
            wp_id="wp-alpha",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-x"),
            ts="2026-04-23T10:00:00Z",
        )
        for _ in range(3):
            await consumer.consume(cmd)
        assert len(state_spy.calls) == 1


# ==============================================================================
# TC-3 · PM-14 跨 pid 拒绝 · 契约硬红线
# ==============================================================================


class TestPM14CrossProjectReject:
    async def test_consumer_rejects_cross_project(
        self,
        state_spy,
        project_id: str,
    ) -> None:
        """Consumer session_pid=proj-A · 收到 pid=proj-B 的 command · 必须 E_ROUTE_CROSS_PROJECT."""

        class _AsyncBus:
            async def append_event(self, **kw):
                return "ev"

        consumer = IC14Consumer(
            session_pid=project_id,  # "proj-wp09"
            state_transition=state_spy,
            event_bus=_AsyncBus(),
        )
        cmd = PushRollbackRouteCommand(
            route_id="route-cross-1",
            project_id="proj-OTHER",  # 不同 pid · 必拒
            wp_id="wp-1",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-cross"),
            ts="2026-04-23T10:00:00Z",
        )
        with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
            await consumer.consume(cmd)
        assert len(state_spy.calls) == 0
