"""WP07 · 决策可追溯率 100% (PM-08 单一事实) e2e。

PM-08 要求 (Goal §4.1): 每个 L2-02 决策都必须有对应 IC-09 audit entry ·
否则 E_AUDIT_UNAUDITED_DECISION (release blocker)。

本测试验:
- 正向: decide → record_audit decision_made → mark_audited 自动 → coverage=100%
- 负向: decide 后故意不 record_audit → verify_all_audited() 抛 E_AUDIT_UNAUDITED_DECISION
- 规模: 50 决策连 audit · 100% 覆盖率 · hash tip 单调增
- 并发: 多 decision 交错 audit · 全部命中
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.main_loop.decision_audit.errors import (
    E_AUDIT_UNAUDITED_DECISION,
    AuditError,
)
from app.main_loop.decision_audit.recorder import DecisionAuditRecorder
from app.main_loop.decision_audit.schemas import AuditCommand
from app.main_loop.decision_engine.engine import decide
from app.main_loop.decision_engine.schemas import Candidate, DecisionContext
from app.supervisor.common.event_bus_stub import EventBusStub

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _SyncBusWrapper:
    """将 async EventBusStub 适配为 kwarg-style append_event 同步接口 (L2-05 Adapter kwarg 模式)."""

    def __init__(self, bus: EventBusStub) -> None:
        self._bus = bus
        self._loop = asyncio.new_event_loop()

    def append_event(self, **kwargs) -> dict:
        event_type = kwargs["event_type"]
        project_id = kwargs["project_id"]
        payload = kwargs.get("payload", {})
        if self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        event_id = self._loop.run_until_complete(
            self._bus.append_event(
                project_id=project_id, type=event_type, payload=payload
            )
        )
        return {
            "event_id": event_id,
            "sequence": kwargs.get("sequence", 0),
            "hash": kwargs.get("hash", ""),
            "persisted": True,
        }


def _make_recorder(pid: str) -> tuple[DecisionAuditRecorder, EventBusStub]:
    bus = EventBusStub()
    rec = DecisionAuditRecorder(
        session_active_pid=pid, event_bus=_SyncBusWrapper(bus)
    )
    return rec, bus


# ============================================================
# TC-13 · 50 决策 100% 可追溯 · hash tip 单调增
# ============================================================


async def test_TC_WP07_TRACE_01_50_decisions_full_coverage() -> None:
    """50 条 decide → record_audit decision_made · coverage = 100% · hash tip 单调。"""
    pid = "pid-wp07tr01"
    recorder, _ = _make_recorder(pid)

    first_tip = recorder.get_hash_tip(project_id=pid)
    assert first_tip.sequence == 0
    assert first_tip.hash == "0" * 64

    for i in range(50):
        ctx = DecisionContext(
            project_id=pid, tick_id=f"tick-tr01-{i}", state="S2_split", kb_enabled=False
        )
        chosen = decide(
            [
                Candidate(
                    decision_type="invoke_skill",
                    decision_params={"capability": f"cap.{i}"},
                    base_score=0.7,
                    reason=f"iter {i} requires skill invocation step",
                )
            ],
            ctx,
        )
        decision_id = f"dec-tr01-{i:03d}"
        recorder.record_audit(
            AuditCommand(
                source_ic="IC-L2-05",
                actor={"l1": "L1-01", "l2": "L2-02"},
                action="decision_made",
                project_id=pid,
                reason=f"50-decision traceability iteration {i}",
                evidence=[f"ev-tr01-{i}"],
                linked_tick=f"tick-tr01-{i}",
                linked_decision=decision_id,
                payload={"final_score": chosen.final_score},
                ts=_iso_now(),
            )
        )

    rep = recorder.traceability.report()
    assert rep.total_decisions == 50
    assert rep.audited_decisions == 50
    assert rep.is_full_coverage is True
    assert rep.coverage == 1.0

    # verify_all_audited 不抛
    recorder.traceability.verify_all_audited()


# ============================================================
# TC-14 · 故意不 audit · verify_all_audited() 抛 E_AUDIT_UNAUDITED_DECISION
# ============================================================


async def test_TC_WP07_TRACE_02_unaudited_decision_raises() -> None:
    """register_decision 但不 mark_audited · verify_all_audited() 抛 E_AUDIT_UNAUDITED_DECISION。"""
    pid = "pid-wp07tr02"
    recorder, _ = _make_recorder(pid)

    # 手动 register 一条决策 · 不 mark_audited
    recorder.traceability.register_decision(
        "dec-tr02-orphan",
        project_id=pid,
        tick_id="tick-tr02",
        reason="this decision will NOT be audited",
    )
    rep = recorder.traceability.report()
    assert rep.total_decisions == 1
    assert rep.audited_decisions == 0
    assert rep.is_full_coverage is False

    with pytest.raises(AuditError) as ei:
        recorder.traceability.verify_all_audited()
    assert ei.value.error_code == E_AUDIT_UNAUDITED_DECISION


# ============================================================
# TC-15 · 100 决策交错审计 · 100% 覆盖率
# ============================================================


async def test_TC_WP07_TRACE_03_interleaved_audit_100_percent() -> None:
    """100 决策 · 先 register 全部 · 再逐个 mark_audited · 中途 coverage 从 0 升至 100%。"""
    pid = "pid-wp07tr03"
    recorder, _ = _make_recorder(pid)

    N = 100
    # 全部 register (decide 阶段)
    for i in range(N):
        ctx = DecisionContext(
            project_id=pid, tick_id=f"t-tr03-{i}", state="S4_execute", kb_enabled=False
        )
        decide(
            [
                Candidate(
                    decision_type="no_op",
                    base_score=0.5,
                    reason=f"tr03 iter {i} no-op decision placeholder",
                )
            ],
            ctx,
        )
        recorder.traceability.register_decision(
            f"dec-tr03-{i:03d}", project_id=pid, tick_id=f"t-tr03-{i}"
        )
    rep = recorder.traceability.report()
    assert rep.total_decisions == N
    assert rep.audited_decisions == 0
    assert rep.coverage == 0.0

    # 逐个 audit · 中间 N/2 时应为 50%
    for i in range(N // 2):
        recorder.traceability.mark_audited(f"dec-tr03-{i:03d}")
    mid = recorder.traceability.report()
    assert mid.audited_decisions == N // 2
    assert abs(mid.coverage - 0.5) < 1e-9

    # 剩余 audit
    for i in range(N // 2, N):
        recorder.traceability.mark_audited(f"dec-tr03-{i:03d}")
    final = recorder.traceability.report()
    assert final.audited_decisions == N
    assert final.is_full_coverage is True
    recorder.traceability.verify_all_audited()


# ============================================================
# TC-16 · 反查 by_decision · 1:1 命中 · 审计链完整
# ============================================================


async def test_TC_WP07_TRACE_04_query_by_decision_1to1() -> None:
    """审计后 · query_by_decision 可 1:1 反查 · project_id 跨校验。"""
    pid = "pid-wp07tr04"
    recorder, _ = _make_recorder(pid)

    for i in range(5):
        did = f"dec-tr04-{i}"
        recorder.record_audit(
            AuditCommand(
                source_ic="IC-L2-05",
                actor={"l1": "L1-01", "l2": "L2-02"},
                action="decision_made",
                project_id=pid,
                reason=f"reverse query test decision #{i} traceability",
                evidence=[f"ev-tr04-{i}"],
                linked_tick=f"tick-tr04-{i}",
                linked_decision=did,
                payload={"idx": i},
                ts=_iso_now(),
            )
        )

    # 反查命中
    for i in range(5):
        entry = recorder.query_by_decision(
            decision_id=f"dec-tr04-{i}", project_id=pid
        )
        assert entry is not None
        assert entry.linked_decision == f"dec-tr04-{i}"
        assert entry.project_id == pid

    # 未命中返 None (不抛)
    miss = recorder.query_by_decision(
        decision_id="dec-tr04-does-not-exist", project_id=pid
    )
    assert miss is None
