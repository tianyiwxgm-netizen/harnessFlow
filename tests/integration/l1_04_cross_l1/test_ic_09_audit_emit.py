"""WP09-01 · IC-09 产生端 · L1-04 (Verifier + RollbackRouter) → L1-09 EventBus.

**契约清单** (IC-09 生产端):
- Verifier orchestrate_s5 路径: L1-04:verifier_orchestrate_started /
  verifier_delegation_dispatched / verifier_report_issued (+ verifier_timeout /
  verifier_delegation_failed 负向路径)
- RollbackRouter 执行路径: L1-04:rollback_executed / rollback_escalated /
  rollback_failed

**真实集成**: L1-09 真 `EventBus` (hash-chain + shard + jsonl) · audit_emitter
封装为真实 IC-09 `append` 调用 · verify 通过 AuditQuery 读回.

**硬校验**:
- 事件 type 前缀属于 L1-09 白名单（L1-04: 合法 · 非法前缀会被 Pydantic 拒绝）
- 每事件 project_id 必与 decision/verdict 的根 pid 一致 (PM-14)
- hash-chain 序列递增 · 无 gap
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.l1_09.audit.query import AuditQuery
from app.l1_09.audit.schemas import Anchor, AnchorType, QueryFilter
from app.l1_09.event_bus.core import EventBus
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import VerifierVerdict


def _collect_jsonl_events(events_path: Path) -> list[dict]:
    """直读 events.jsonl · 避 AuditQuery 层过滤 · 严格校审计落盘."""
    if not events_path.exists():
        return []
    out = []
    for raw in events_path.read_bytes().splitlines():
        if raw.strip():
            out.append(json.loads(raw.decode("utf-8")))
    return out


# ==============================================================================
# TC-1 · Verifier PASS → L1-09 收到 3 条 L1-04:verifier_* 审计事件
# ==============================================================================


class TestVerifierPathEmitsIC09:
    """L1-04 Verifier → L1-09 IC-09 · 成功 happy path 至少 3 条审计.

    契约对齐 L2-06 §6 主算法: Step 1/2/7 各产审计事件.
    """

    async def test_verifier_pass_emits_started_dispatched_issued(
        self,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        ic09_audit_emitter,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=ic09_audit_emitter,
            sleep=no_sleep,
        )
        trace = make_trace()
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.PASS

        # 真实 bus 的 events.jsonl 里应至少有 3 条 L1-04:verifier_* 事件
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        all_events = _collect_jsonl_events(events_path)
        types = [e["type"] for e in all_events]
        assert "L1-04:verifier_orchestrate_started" in types
        assert "L1-04:verifier_delegation_dispatched" in types
        assert "L1-04:verifier_report_issued" in types

    async def test_audit_events_carry_hash_chain(
        self,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        ic09_audit_emitter,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        no_sleep,
    ) -> None:
        """hash-chain 完整 · 3 条事件 prev_hash 正确链接（PM-08 + L1-09 §5.1）."""
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=ic09_audit_emitter,
            sleep=no_sleep,
        )
        await orchestrate_s5(make_trace(), deps)

        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        evs = _collect_jsonl_events(events_path)
        assert len(evs) >= 3
        # sequence 递增无 gap
        seqs = [e["sequence"] for e in evs]
        assert seqs == list(range(1, len(evs) + 1))
        # prev_hash 链
        for i in range(1, len(evs)):
            assert evs[i]["prev_hash"] == evs[i - 1]["hash"]


# ==============================================================================
# TC-2 · RollbackRouter 执行路径 → L1-09 rollback_executed 审计
# ==============================================================================


class TestRollbackPathEmitsIC09:
    """L1-04 RollbackRouter → L1-09 IC-09 · rollback_executed/escalated 审计."""

    async def test_rollback_executed_event_recorded(
        self,
        real_event_bus: EventBus,
        state_spy,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """IC-14 消费 → state_transition + rollback_executed 审计事件."""

        # Adapter: 把 real EventBus 转成 IC14 consumer 的 EventBusProtocol
        class _BusAdapter:
            def __init__(self, bus: EventBus) -> None:
                self._bus = bus

            async def append_event(
                self,
                *,
                project_id: str,
                type: str,
                payload: dict,
                evidence_refs: tuple[str, ...] = (),
            ) -> str:
                from datetime import UTC, datetime

                from app.l1_09.event_bus.schemas import Event

                evt = Event(
                    project_id=project_id,
                    type=type,
                    actor="supervisor",
                    payload=dict(payload),
                    timestamp=datetime.now(UTC),
                )
                r = self._bus.append(evt)
                return r.event_id

        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=_BusAdapter(real_event_bus),
        )
        cmd = PushRollbackRouteCommand(
            route_id="route-wp09-001",
            project_id=project_id,
            wp_id="wp-alpha",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-1"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True

        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        evs = _collect_jsonl_events(events_path)
        types = [e["type"] for e in evs]
        assert "L1-04:rollback_executed" in types

    async def test_rollback_escalated_event_when_level_ge_3(
        self,
        real_event_bus: EventBus,
        state_spy,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """同级 ≥ 3 升级 → 额外 rollback_escalated 审计事件."""

        class _BusAdapter:
            def __init__(self, bus: EventBus) -> None:
                self._bus = bus

            async def append_event(
                self,
                *,
                project_id: str,
                type: str,
                payload: dict,
                evidence_refs: tuple[str, ...] = (),
            ) -> str:
                from datetime import UTC, datetime

                from app.l1_09.event_bus.schemas import Event

                evt = Event(
                    project_id=project_id,
                    type=type,
                    actor="supervisor",
                    payload=dict(payload),
                    timestamp=datetime.now(UTC),
                )
                return self._bus.append(evt).event_id

        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=_BusAdapter(real_event_bus),
        )
        cmd = PushRollbackRouteCommand(
            route_id="route-esc-001",
            project_id=project_id,
            wp_id="wp-alpha",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            level_count=3,
            evidence=RouteEvidence(verifier_report_id="vr-esc"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await consumer.consume(cmd)
        assert ack.escalated is True

        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        evs = _collect_jsonl_events(events_path)
        types = [e["type"] for e in evs]
        assert "L1-04:rollback_executed" in types
        assert "L1-04:rollback_escalated" in types


# ==============================================================================
# TC-3 · IC-18 audit_query 能查到 L1-04 发的审计事件（L1-04 消费 L1-09）
# ==============================================================================


class TestAuditQueryConsumesL104Events:
    """L1-04 → L1-09 IC-09 emit · 再由 L1-04 Verifier 用 IC-18 audit_query 查出.

    这是 task spec §7 "IC-18 audit_query 消费 L1-09" 的真实回路验证.
    """

    async def test_audit_query_returns_verifier_events(
        self,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        ic09_audit_emitter,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=ic09_audit_emitter,
            sleep=no_sleep,
        )
        await orchestrate_s5(make_trace(), deps)

        q = AuditQuery(event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id,
            project_id=project_id,
        )
        trail = q.query_audit_trail(
            anchor,
            QueryFilter(event_type="L1-04:verifier_report_issued", max_depth=4),
        )
        # event_layer 层应至少包含 1 条 verifier_report_issued
        assert trail.event_layer.count >= 1
        assert any(
            e["type"] == "L1-04:verifier_report_issued"
            for e in trail.event_layer.entries
        )


# ==============================================================================
# TC-4 · verifier FAIL + emitter 异常 · 不阻塞主路径（resilience）
# ==============================================================================


class TestAuditEmitResilient:
    """audit emit 失败（磁盘 / schema 违反）绝不能影响 verdict 产出."""

    async def test_emitter_raises_does_not_break_verdict(
        self,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        async def broken_emitter(event_type: str, payload: dict) -> None:
            raise RuntimeError("audit disk failure")

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=broken_emitter,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(make_trace(), deps)
        assert result.verdict == VerifierVerdict.PASS
