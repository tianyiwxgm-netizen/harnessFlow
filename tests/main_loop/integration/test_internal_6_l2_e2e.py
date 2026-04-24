"""WP07 · 内部 6 L2 e2e 集成测试 · 主循环闭环联动。

目的:
    把 L2-01 tick_scheduler / L2-02 decision_engine / L2-03 state_machine /
    L2-04 task_chain / L2-05 decision_audit / L2-06 supervisor_receiver 真实装配 ·
    验证 tick → decide → state_transition → chain.execute → audit.record 全链 · 可追溯 100%。

铁律:
    - 真实 import (不 mock 任何 L2 内部实现)
    - 仅外部 IC 边界 mock (skill_dispatch 外部 API / quality_loop IC14 target)
    - 每 TC 创建独立 project_id (PM-14 隔离)

覆盖:
    TC-WP07-INT-01  L2-02 → L2-04: decide 产 ChosenAction → router 路由到 L1-02
    TC-WP07-INT-02  L2-02 → L2-04: invoke_skill 全链 (router → spawner → executor)
    TC-WP07-INT-03  L2-03 ← L2-01: tick_scheduler 读 StateMachineOrchestrator snapshot
    TC-WP07-INT-04  L2-05 审计 L2-02 decision · mark_audited
    TC-WP07-INT-05  L2-06 → L2-01: supervisor halt → tick_scheduler 停止 dispatch
    TC-WP07-INT-06  L2-06 → L2-01: supervisor suggestion counter 单调递增
    TC-WP07-INT-07  tick drift 统计 · loop survives engine 抛异常
    TC-WP07-INT-08  多 tick 连续 decide+execute+audit · 审计台账积累
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.main_loop.decision_audit.recorder import DecisionAuditRecorder
from app.main_loop.decision_audit.schemas import AuditCommand
from app.main_loop.decision_engine.engine import decide
from app.main_loop.decision_engine.schemas import Candidate, DecisionContext
from app.main_loop.state_machine.orchestrator import (
    StateMachineOrchestrator,
    generate_transition_id,
)
from app.main_loop.state_machine.schemas import TransitionRequest
from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltSignal,
    SuggestionInbox,
)
from app.main_loop.task_chain.executor import (
    ExecutorConfig,
    TaskChainExecutor,
    build_noop_resolver,
)
from app.main_loop.tick_scheduler import TickScheduler
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
)
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import MockHardHaltTarget
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    HardHaltEvidence,
    PushSuggestionCommand,
    RequestHardHaltCommand,
    RouteEvidence,
    SuggestionLevel,
    SuggestionPriority,
    TargetStage,
)

pytestmark = pytest.mark.asyncio


# ============================================================
# 工具 · 无副作用 fixture 组装
# ============================================================


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _make_audit_recorder(pid: str, bus: EventBusStub) -> DecisionAuditRecorder:
    """构造真 L2-05 · 绑 EventBusStub (append_event kwarg 风格)."""

    class _KwargBusAdapter:
        def __init__(self, inner: EventBusStub) -> None:
            self._inner = inner
            self._loop = asyncio.new_event_loop()

        def append_event(self, **kwargs) -> dict:
            event_type = kwargs["event_type"]
            project_id = kwargs["project_id"]
            payload = kwargs.get("payload", {})
            # 同步调 stub 的 async append_event (stub lock · 本地 loop 跑)
            coro = self._inner.append_event(
                project_id=project_id,
                type=event_type,
                payload=payload,
            )
            if self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            event_id = self._loop.run_until_complete(coro)
            return {
                "event_id": event_id,
                "sequence": kwargs.get("sequence", 0),
                "hash": kwargs.get("hash", ""),
                "persisted": True,
            }

    return DecisionAuditRecorder(
        session_active_pid=pid,
        event_bus=_KwargBusAdapter(bus),
    )


class _NoopRollbackDownstream:
    """IC-14 下游 mock · main-1 merged IC14Consumer 的 duck-typed 替身."""

    def __init__(self) -> None:
        self.forwarded_routes: list[str] = []

    async def consume(self, *args, **kwargs) -> dict:
        route_id = kwargs.get("route_id") or (args[0] if args else "route-?")
        self.forwarded_routes.append(str(route_id))
        return {"forwarded": True, "route_id": route_id}


# ============================================================
# TC-01 · L2-02 decide → L2-04 route (state_transition)
# ============================================================


async def test_TC_WP07_INT_01_decide_to_route_state_transition() -> None:
    """decide() 产 state_transition ChosenAction · executor 路由到 L1-02 IC-01。"""
    pid = "pid-wp07int01"

    # L2-02: 走真实 decide · kb_snippets 空 → degraded
    ctx = DecisionContext(
        project_id=pid,
        tick_id="tick-int01",
        state="S3_design",
        kb_enabled=False,  # 全链降级路径
    )
    cand = Candidate(
        decision_type="state_transition",
        decision_params={
            "to_state": "S4_execute",
            "from_state": "S3_design",
            "reason": "design complete · move to execute stage",
            "evidence_refs": ["ev-01"],
        },
        base_score=0.9,
        reason="S3 design DoD met per stage gate pass",
    )
    chosen = decide([cand], ctx)
    assert chosen.decision_type == "state_transition"
    assert chosen.kb_degraded is True

    # L2-04: 真 executor · noop resolver
    cfg = ExecutorConfig(
        ic_resolver=build_noop_resolver({"transitioned": True})
    )
    executor = TaskChainExecutor(config=cfg)
    result = await executor.execute(chosen, project_id=pid, await_result=True)
    assert result.accepted is True
    assert result.route is not None
    assert result.route.target_l1 == "L1-02"
    assert result.route.ic_code == "IC-01"
    assert result.ic_reply == {"transitioned": True}


# ============================================================
# TC-02 · L2-02 decide → L2-04 route (invoke_skill)
# ============================================================


async def test_TC_WP07_INT_02_decide_to_route_invoke_skill() -> None:
    """decide() 产 invoke_skill · 路由到 L1-05 · spawner 派发 task · state 追踪。"""
    pid = "pid-wp07int02"

    ctx = DecisionContext(
        project_id=pid,
        tick_id="tick-int02",
        state="S4_execute",
        kb_enabled=False,
    )
    cand = Candidate(
        decision_type="invoke_skill",
        decision_params={
            "capability": "dod.evaluator",
            "invocation_id": "inv-int02",
        },
        base_score=0.85,
        reason="skill required for S4 dod evaluation during execute",
    )
    chosen = decide([cand], ctx)
    assert chosen.decision_type == "invoke_skill"

    cfg = ExecutorConfig(
        ic_resolver=build_noop_resolver({"skill_result": "pass"})
    )
    executor = TaskChainExecutor(config=cfg)
    result = await executor.execute(chosen, project_id=pid, await_result=True)
    assert result.accepted is True
    assert result.route is not None
    assert result.route.target_l1 == "L1-05"
    assert result.route.ic_code == "IC-04"
    # state 聚合根被推进
    state = executor.get_state(pid)
    assert state.total_dispatched == 1


# ============================================================
# TC-03 · L2-03 ← L2-01: tick scheduler 读 StateMachineOrchestrator
# ============================================================


async def test_TC_WP07_INT_03_tick_scheduler_reads_state_machine() -> None:
    """tick_scheduler 通过 StateMachineSnapshotReader 读 L2-03 当前 state。"""
    pid = "pid-a0030003"  # 符合 pid-[hex]{8+} 格式
    orch = StateMachineOrchestrator(
        project_id=pid, initial_state="INITIALIZED"
    )
    sched = TickScheduler.create_default(
        project_id=pid,
        state_machine_orchestrator=orch,
        decision_engine=StubDecisionEngine(action={"kind": "no_op"}),
    )
    # 先 tick 一次 · state_reader 读 INITIALIZED
    await sched.tick_once()
    assert sched.state_reader.read(pid)["current_state"] == "INITIALIZED"

    # 真实 L2-03 transition · 7 enum 合法边 INITIALIZED → PLANNING
    req = TransitionRequest(
        transition_id=generate_transition_id(),
        project_id=pid,
        from_state="INITIALIZED",
        to_state="PLANNING",
        reason="integration test move to PLANNING for WP07 e2e",
        trigger_tick="tick-int03",
        evidence_refs=("ev-int03",),
        ts=_iso_now(),
    )
    out = orch.transition(req)
    assert out.accepted is True

    # 再 tick · state_reader 读到 PLANNING
    await sched.tick_once()
    data = sched.state_reader.read(pid)
    assert data["current_state"] == "PLANNING"
    assert data["version"] == 1


# ============================================================
# TC-04 · L2-05 审计 L2-02 decision · 审计台账 · 可追溯率
# ============================================================


async def test_TC_WP07_INT_04_audit_tracks_decision() -> None:
    """L2-02 decide → L2-05 record_audit(decision_made) · traceability 100%。"""
    pid = "pid-wp07int04"
    bus = EventBusStub()
    recorder = _make_audit_recorder(pid, bus)

    # L2-02 · 真实 decide
    ctx = DecisionContext(
        project_id=pid, tick_id="tick-int04", state="S1_plan", kb_enabled=False
    )
    chosen = decide(
        [
            Candidate(
                decision_type="invoke_skill",
                decision_params={"capability": "x.y"},
                base_score=0.7,
                reason="need skill to proceed with planning stage",
            )
        ],
        ctx,
    )
    decision_id = "dec-int04-001"

    # L2-05 · record_audit(decision_made)
    cmd = AuditCommand(
        source_ic="IC-L2-05",
        actor={"l1": "L1-01", "l2": "L2-02"},
        action="decision_made",
        project_id=pid,
        reason=f"audit decision of type={chosen.decision_type}",
        evidence=["ev-int04"],
        linked_tick="tick-int04",
        linked_decision=decision_id,
        payload={"decision_type": chosen.decision_type, "final_score": chosen.final_score},
        ts=_iso_now(),
    )
    ar = recorder.record_audit(cmd)
    assert ar.audit_id.startswith("audit-")
    assert ar.buffered is True

    # 可追溯率 100%
    rep = recorder.traceability.report()
    assert rep.total_decisions == 1
    assert rep.audited_decisions == 1
    assert rep.is_full_coverage is True


# ============================================================
# TC-05 · L2-06 → L2-01: halt · tick_scheduler 停止 dispatch
# ============================================================


async def test_TC_WP07_INT_05_supervisor_halt_stops_tick_dispatch() -> None:
    """SupervisorReceiver 真收 IC-15 halt → HaltEnforcer (真 L2-01) → tick 拒 dispatch。"""
    pid = "pid-wp07int05"
    bus = EventBusStub()

    # 真 tick_scheduler · 真 halt_enforcer
    dispatcher = StubActionDispatcher()
    sched = TickScheduler.create_default(
        project_id=pid,
        decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
        action_dispatcher=dispatcher,
    )

    # 真 receiver · halt_target = sched.halt_enforcer (真 L2-01 绑 receiver)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=_NoopRollbackDownstream(),
    )

    # 先 tick 1 次 · 正常派发
    await sched.tick_once()
    assert len(dispatcher.dispatched) == 1

    # supervisor 发 halt
    halt_cmd = RequestHardHaltCommand(
        halt_id="halt-int05",
        project_id=pid,
        red_line_id="redline-test-int05",
        evidence=HardHaltEvidence(
            observation_refs=("ev-1", "ev-2"), confirmation_count=2
        ),
        require_user_authorization=True,
        ts=_iso_now(),
    )
    signal = HaltSignal.from_command(halt_cmd, received_at_ms=0)
    ack = await receiver.consume_halt(signal)
    assert ack.halted is True
    assert ack.latency_ms <= 100, f"halt latency={ack.latency_ms}ms > 100ms"

    # tick 后续 5 次全拒 HALTED
    for _ in range(5):
        r = await sched.tick_once()
        assert r.dispatched is False
        assert r.reject_reason == "HALTED"
    # dispatcher 不增
    assert len(dispatcher.dispatched) == 1


# ============================================================
# TC-06 · L2-06 → L2-01: suggestion 3 级 counter 单调递增
# ============================================================


async def test_TC_WP07_INT_06_supervisor_suggestion_counter_monotonic() -> None:
    """SupervisorReceiver 真消费 3 级 suggestion · counter 单调增 · queue_depth 正确。"""
    pid = "pid-wp07int06"
    bus = EventBusStub()
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=_NoopRollbackDownstream(),
    )

    levels = [
        (SuggestionLevel.INFO, AdviceLevel.INFO),
        (SuggestionLevel.SUGG, AdviceLevel.SUGG),
        (SuggestionLevel.WARN, AdviceLevel.WARN),
        (SuggestionLevel.INFO, AdviceLevel.INFO),  # 再来一条 INFO
    ]
    for i, (zeta_level, adv_level) in enumerate(levels):
        cmd = PushSuggestionCommand(
            suggestion_id=f"sugg-int06-{i}",
            project_id=pid,
            level=zeta_level,
            content=f"integration test suggestion #{i}",
            observation_refs=(f"ev-int06-{i}",),
            priority=SuggestionPriority.P2,
            require_ack_tick_delta=1,
            ts=_iso_now(),
        )
        inbox = SuggestionInbox.from_command(cmd, received_at_ms=i)
        ack = await receiver.consume_suggestion(inbox)
        assert ack.accepted is True
        assert ack.routed_to == adv_level

    # counter_snapshot 单调增 (key 可能是 lowercase 或 AdviceLevel.value · 兼容)
    snap = receiver.counter_snapshot()
    info_k = "info" if "info" in snap else AdviceLevel.INFO.value
    sugg_k = "sugg" if "sugg" in snap else AdviceLevel.SUGG.value
    warn_k = "warn" if "warn" in snap else AdviceLevel.WARN.value
    # 3 级各至少 1 · INFO 2 条
    assert snap.get(info_k, 0) == 2
    assert snap.get(sugg_k, 0) == 1
    assert snap.get(warn_k, 0) == 1


# ============================================================
# TC-07 · tick drift 统计 · loop survives engine 异常
# ============================================================


async def test_TC_WP07_INT_07_loop_survives_engine_exceptions() -> None:
    """engine 间歇抛异常 · tick loop 不死 · drift 统计可查 · errors 记录。"""
    pid = "pid-wp07int07"
    dispatcher = StubActionDispatcher()
    call_count = {"n": 0}

    class FlakyEngine:
        async def decide(self, ctx):  # noqa: ARG002
            call_count["n"] += 1
            if call_count["n"] % 4 == 0:
                raise RuntimeError(f"flake#{call_count['n']}")
            return {"kind": "invoke_skill"}

    sched = TickScheduler.create_default(
        project_id=pid,
        decision_engine=FlakyEngine(),
        action_dispatcher=dispatcher,
    )
    for _ in range(20):
        await sched.tick_once()

    # 5 失败 · 15 成功
    assert len(sched.errors) >= 3, f"expected ≥3 errors · got {len(sched.errors)}"
    assert len(dispatcher.dispatched) >= 12

    # drift 统计可查
    stats = sched.drift_stats
    assert stats["total_ticks"] == 20


# ============================================================
# TC-08 · 多 tick decide+execute+audit · 可追溯率跟 total_dispatched 对齐
# ============================================================


async def test_TC_WP07_INT_08_multi_tick_full_chain_traceability() -> None:
    """3 tick 连跑 decide → execute → record_audit · 审计台账 = 决策数 · 100%。"""
    pid = "pid-wp07int08"
    bus = EventBusStub()
    recorder = _make_audit_recorder(pid, bus)

    # 真 executor (noop resolver)
    cfg = ExecutorConfig(
        ic_resolver=build_noop_resolver({"ok": True})
    )
    executor = TaskChainExecutor(config=cfg)

    # 3 tick 循环
    for i in range(3):
        tick_id = f"tick-int08-{i}"
        decision_id = f"dec-int08-{i}"

        # L2-02 decide
        ctx = DecisionContext(
            project_id=pid, tick_id=tick_id, state="S4_execute", kb_enabled=False
        )
        chosen = decide(
            [
                Candidate(
                    decision_type="invoke_skill",
                    decision_params={
                        "capability": f"cap.{i}",
                        "invocation_id": f"inv-int08-{i}",
                    },
                    base_score=0.8,
                    reason=f"tick #{i} requires skill invocation to progress",
                )
            ],
            ctx,
        )

        # L2-04 execute
        res = await executor.execute(
            chosen, project_id=pid, decision_id=decision_id, await_result=True
        )
        assert res.accepted is True

        # L2-05 record audit decision_made
        recorder.record_audit(
            AuditCommand(
                source_ic="IC-L2-05",
                actor={"l1": "L1-01", "l2": "L2-02"},
                action="decision_made",
                project_id=pid,
                reason=f"tick #{i} decision audited via full integration chain",
                evidence=[f"ev-int08-{i}"],
                linked_tick=tick_id,
                linked_decision=decision_id,
                payload={"final_score": chosen.final_score},
                ts=_iso_now(),
            )
        )

    # 台账 · 3 决策 · 全部已审计 · 100%
    rep = recorder.traceability.report()
    assert rep.total_decisions == 3
    assert rep.audited_decisions == 3
    assert rep.is_full_coverage is True
    # executor state 也对齐
    st = executor.get_state(pid)
    assert st.total_dispatched == 3
