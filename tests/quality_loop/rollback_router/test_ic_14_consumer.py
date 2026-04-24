"""TC-L104-L207 · ic_14_consumer · IC-14 消费入口 · L1-07 → L2-07 端到端。

核心 TC：
- 消费 Dev-ζ PushRollbackRouteCommand · 正确分级 → map → 执行
- 幂等：同 route_id 多次 → 单次执行（对齐 Dev-ζ rollback_pusher 幂等）
- PM-14：跨 pid 拒绝
- 4 级完整链路（FAIL_L1 → S3 / FAIL_L2 → S4 / FAIL_L3 → S5 / FAIL_L4 → UPGRADE）
- 同级 ≥ 3 升级全链路
- 异常：wp_id 空 · verdict 非法 · target_stage 非法
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)


class MockStateTransition:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def state_transition(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"transitioned": True}


class MockEventBus:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def append_event(self, *, project_id: str, type: str,
                           payload: dict[str, Any],
                           evidence_refs: tuple[str, ...] = ()) -> str:
        self.events.append({"project_id": project_id, "type": type,
                            "payload": payload, "evidence_refs": evidence_refs})
        return f"ev-{len(self.events)}"


def _mk_cmd(verdict: FailVerdict, target: TargetStage,
            route_id: str = "route-abc123", wp_id: str = "wp-alpha",
            project_id: str = "proj-X", level_count: int = 1,
            vr_id: str = "vr-1") -> PushRollbackRouteCommand:
    return PushRollbackRouteCommand(
        route_id=route_id, project_id=project_id, wp_id=wp_id,
        verdict=verdict, target_stage=target, level_count=level_count,
        evidence=RouteEvidence(verifier_report_id=vr_id),
        ts="2026-04-23T10:00:00Z",
    )


def _make_consumer(pid: str = "proj-X") -> tuple[IC14Consumer, MockStateTransition, MockEventBus]:
    st = MockStateTransition()
    bus = MockEventBus()
    c = IC14Consumer(session_pid=pid, state_transition=st, event_bus=bus)
    return c, st, bus


class TestIC14Consumer4LevelMapping:
    """4 级完整路径 · verdict → target_stage → new_wp_state。"""

    @pytest.mark.asyncio
    async def test_fail_l1_routes_to_s3(self) -> None:
        """TC-L104-L207-consumer-01 · FAIL_L1 → retry_s3。"""
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3)
        ack: PushRollbackRouteAck = await c.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s3"
        assert ack.escalated is False
        assert st.calls[0]["new_wp_state"] == "retry_s3"

    @pytest.mark.asyncio
    async def test_fail_l2_routes_to_s4(self) -> None:
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L2, TargetStage.S4)
        ack = await c.consume(cmd)
        assert ack.new_wp_state.value == "retry_s4"

    @pytest.mark.asyncio
    async def test_fail_l3_routes_to_s5(self) -> None:
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L3, TargetStage.S5)
        ack = await c.consume(cmd)
        assert ack.new_wp_state.value == "retry_s5"

    @pytest.mark.asyncio
    async def test_fail_l4_routes_to_upgrade(self) -> None:
        """TC-L104-L207-consumer-04 · FAIL_L4 (CRITICAL) → UPGRADE_TO_L1_01。"""
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L4, TargetStage.UPGRADE_TO_L1_01)
        ack = await c.consume(cmd)
        assert ack.new_wp_state.value == "upgraded_to_l1_01"


class TestIC14ConsumerIdempotency:
    """幂等 · 同 route_id 多次 → 单次执行。"""

    @pytest.mark.asyncio
    async def test_same_route_id_twice_single_execution(self) -> None:
        """TC-L104-L207-consumer-idem-01 · 幂等 by route_id。"""
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3,
                      route_id="route-idem-111")
        ack1 = await c.consume(cmd)
        ack2 = await c.consume(cmd)
        assert ack1 == ack2  # 同一对象 or 内容一致
        assert len(st.calls) == 1, "state_transition 只能被调 1 次"

    @pytest.mark.asyncio
    async def test_different_route_ids_both_executed(self) -> None:
        c, st, bus = _make_consumer()
        cmd1 = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3, route_id="route-A111")
        cmd2 = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3, route_id="route-B222")
        await c.consume(cmd1)
        await c.consume(cmd2)
        assert len(st.calls) == 2


class TestIC14ConsumerPM14:
    """PM-14 · 跨 project_id 拒绝（对齐 Dev-ζ `E_ROUTE_CROSS_PROJECT`）。"""

    @pytest.mark.asyncio
    async def test_cross_project_rejected(self) -> None:
        c, st, bus = _make_consumer(pid="proj-session")
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3, project_id="proj-OTHER")
        with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
            await c.consume(cmd)
        assert len(st.calls) == 0


class TestIC14ConsumerEscalation:
    """同级连续 ≥ 3 升级。"""

    @pytest.mark.asyncio
    async def test_three_consecutive_fail_l1_escalates(self) -> None:
        """TC-L104-L207-consumer-esc-01 · FAIL_L1 × 3 · 第 3 次升级到 UPGRADE。"""
        c, st, bus = _make_consumer()
        for i in range(1, 4):
            cmd = _mk_cmd(
                FailVerdict.FAIL_L1,
                TargetStage.S3 if i < 3 else TargetStage.UPGRADE_TO_L1_01,
                route_id=f"route-esc-{i}", level_count=i,
            )
            ack = await c.consume(cmd)
            if i < 3:
                assert ack.escalated is False
                assert ack.new_wp_state.value == "retry_s3"
            else:
                # 第 3 次 · Dev-ζ 传的 target_stage 已经是 UPGRADE · 符合合法映射
                assert ack.escalated is True
                assert ack.new_wp_state.value == "upgraded_to_l1_01"

    @pytest.mark.asyncio
    async def test_pm_14_all_audit_events_carry_root_pid(self) -> None:
        """PM-14：所有回退必带 root pid（审计事件 project_id 字段）。"""
        c, st, bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3)
        await c.consume(cmd)
        assert all(ev["project_id"] == "proj-X" for ev in bus.events)
        assert len(bus.events) >= 1  # 至少 1 条审计


class TestIC14ConsumerValidation:
    """入参校验 · 对齐 Dev-ζ producer 的 _LEGAL_MAPPING。"""

    @pytest.mark.asyncio
    async def test_illegal_verdict_target_combo_rejected(self) -> None:
        """FAIL_L1 + target_stage=S4 不在合法映射内（FAIL_L1 → S3 或 UPGRADE）。"""
        c, st, bus = _make_consumer()
        # 构造一个"verdict 虽然合法 · 但 target_stage 不匹配" 的 command
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S4)  # FAIL_L1 合法 target 不含 S4
        with pytest.raises(ValueError, match="E_ROUTE_VERDICT_TARGET_MISMATCH"):
            await c.consume(cmd)
        assert len(st.calls) == 0


class TestIC14ConsumerConstruction:
    """构造时约束：空 session_pid 拒绝。"""

    def test_empty_session_pid_rejected(self) -> None:
        from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
        with pytest.raises(ValueError, match="E_ROUTE_NO_PROJECT_ID"):
            IC14Consumer(
                session_pid="   ",
                state_transition=MockStateTransition(),
                event_bus=MockEventBus(),
            )


class TestIC14ConsumerAuditHelpers:
    """辅助查询 API · 供调试 / 审计。"""

    @pytest.mark.asyncio
    async def test_is_processed_reflects_idem_cache(self) -> None:
        c, _st, _bus = _make_consumer()
        assert c.is_processed("route-unknown") is False
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3, route_id="route-proc-1")
        await c.consume(cmd)
        assert c.is_processed("route-proc-1") is True

    @pytest.mark.asyncio
    async def test_snapshot_cache_dumps_acks(self) -> None:
        c, _st, _bus = _make_consumer()
        cmd = _mk_cmd(FailVerdict.FAIL_L1, TargetStage.S3, route_id="route-snap-1")
        await c.consume(cmd)
        snap = c.snapshot_cache()
        assert "route-snap-1" in snap
        assert snap["route-snap-1"]["applied"] is True
