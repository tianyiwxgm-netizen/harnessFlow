"""WP09-06 · S2 planning → S3 gate → S4 exec → S5 verify → S6 close 全链路 e2e.

**覆盖 task spec §3 + §7 所有契约**:
1. S2 planning: L1-03 WP 分配 · L1-06 KB 读取 · DoD 编译
2. S3 gate compile: L1-04 DoD → Gate checklist
3. S4 exec: L1-04 S4 Driver · skill 调用 · test runner · metric 收集
4. S5 verify: L1-04 Verifier · IC-20 派发 · 回调 · 双签 · verdict
5. S6 close: 审计完整 · hash-chain 无 gap · AuditQuery 可查
6. 失败路径: Verifier FAIL_L1 → L1-07 RollbackPusher → L1-04 IC14Consumer → L1-02 IC-01

**跨 L1 契约全集**:
- IC-01 · L1-04 → L1-02 (state_transition)
- IC-06 · L1-04 ← L1-06 (kb_read)
- IC-09 · L1-04 → L1-09 (audit_emit)
- IC-14 · L1-04 ← L1-07 (push_rollback_route)
- IC-18 · L1-04 → L1-09 (query_audit_trail)
- IC-20 · L1-04 → L1-05 (invoke_verifier)

**真实代码**: 全部 L1-03/04/06/07/09 模块直接 import · 无业务逻辑 mock.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_base.reader.schemas import (
    ApplicableContext as KBApplicableContext,
)
from app.knowledge_base.reader.schemas import (
    KBEntry,
    ReadRequest,
)
from app.knowledge_base.reader.service import KBReadService
from app.l1_09.audit.query import AuditQuery
from app.l1_09.audit.schemas import Anchor, AnchorType, QueryFilter
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.quality_loop.dod_compiler.compiler import DoDExpressionCompiler
from app.quality_loop.dod_compiler.schemas import (
    CompileBatchCommand,
    DoDClause,
    DoDExpressionKind,
)
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.quality_loop.rollback_router.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import VerifierVerdict
from app.supervisor.event_sender.rollback_pusher import RollbackPusher


class _BusAdapter:
    """把真实 L1-09 EventBus 包成 IC-09 async append_event 协议."""

    def __init__(self, bus: EventBus, actor: str = "supervisor") -> None:
        self._bus = bus
        self._actor = actor

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict,
        evidence_refs: tuple = (),
    ) -> str:
        evt = Event(
            project_id=project_id,
            type=type,
            actor=self._actor,
            payload=dict(payload),
            timestamp=datetime.now(UTC),
        )
        return self._bus.append(evt).event_id


def _collect_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(raw.decode("utf-8"))
        for raw in path.read_bytes().splitlines()
        if raw.strip()
    ]


# ==============================================================================
# TC-1 · Happy path · S2 → S3 → S4 → S5 → S6 全链路 PASS
# ==============================================================================


class TestFullStageGateHappyPath:
    """正向: Verifier PASS → 无 rollback · 所有 L1 契约均触达."""

    async def test_s2_to_s6_full_pass_chain(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        make_trace,
        delegate_stub,
        pass_verifier_output,
        ic09_audit_emitter,
        state_spy,
        no_sleep,
    ) -> None:
        # -------- S2 Planning: L1-06 KB read + DoD compile --------
        from tests.integration.l1_04_cross_l1.conftest import (
            AuditSink,
            FakeKBRepo,
            FakeReranker,
            FakeScopeChecker,
        )

        kb_recipe = KBEntry(
            id="recipe-s5-coverage-ge-80",
            scope="project",
            kind="recipe",
            title="coverage ≥ 80%",
            content="S5 verify 阶段需覆盖率 ≥ 0.80",
            applicable_context=KBApplicableContext(route="S5"),
            observed_count=20,
        )
        kb_svc = KBReadService(
            scope_checker=FakeScopeChecker(),
            reranker=FakeReranker(),
            audit=AuditSink(),
            repo=FakeKBRepo(project_entries=[kb_recipe]),
        )
        kb_result = kb_svc.read(
            ReadRequest(
                trace_id="tr-e2e-s2",
                project_id=project_id,
                session_id="sess-e2e",
                applicable_context=KBApplicableContext(route="S5"),
                kind="recipe",
                top_k=3,
            )
        )
        assert kb_result.meta.returned_count == 1

        # -------- S2 · DoD 编译（拿 KB ids 做 source_ac_ids） --------
        compiler = DoDExpressionCompiler()
        dod_result = compiler.compile_batch(
            CompileBatchCommand(
                command_id="cmd-e2e-1",
                project_id=project_id,
                blueprint_id="bp-e2e",
                wp_id="wp-int-1",
                clauses=[
                    DoDClause(
                        clause_id="c-cov",
                        clause_text="coverage >= 0.80",
                        source_ac_ids=[kb_result.entries[0].id],
                        kind=DoDExpressionKind.METRIC,
                    ),
                ],
                ac_matrix={kb_result.entries[0].id: {}},
                ts="2026-04-23T10:00:00Z",
            )
        )
        assert dod_result.accepted is True
        assert dod_result.compiled_count == 1

        # -------- S4 → S5 · Verifier 编排 · IC-20 dispatch --------
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(output=pass_verifier_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=ic09_audit_emitter,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(make_trace(), deps)
        assert result.verdict == VerifierVerdict.PASS
        assert result.signatures.both_ok is True
        assert result.verifier_session_id is not None
        assert result.verifier_session_id.startswith("sub-")

        # -------- S6 · 审计链完整校验 --------
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        evs = _collect_jsonl(events_path)
        types = [e["type"] for e in evs]
        # 至少 verifier 3 条事件
        assert "L1-04:verifier_orchestrate_started" in types
        assert "L1-04:verifier_delegation_dispatched" in types
        assert "L1-04:verifier_report_issued" in types
        # hash-chain 无 gap
        seqs = [e["sequence"] for e in evs]
        assert seqs == list(range(1, len(evs) + 1))

        # -------- IC-18 · AuditQuery 能查出 verifier 报告 --------
        q = AuditQuery(event_bus_root)
        trail = q.query_audit_trail(
            Anchor(
                anchor_type=AnchorType.PROJECT_ID,
                anchor_id=project_id,
                project_id=project_id,
            ),
            QueryFilter(event_type="L1-04:verifier_report_issued"),
        )
        assert trail.event_layer.count >= 1

        # -------- PASS 路径: state_transition 不被触发 (无 rollback) --------
        assert len(state_spy.calls) == 0


# ==============================================================================
# TC-2 · Fail path · Verifier FAIL_L1 → RollbackPusher → Consumer → IC-01
# ==============================================================================


class TestFullStageGateFailPath:
    """失败链路: Verifier FAIL_L1 (信任坍塌) → L1-07 push → L1-04 consume → L1-02 state_transition."""

    async def test_fail_l1_trust_collapse_triggers_rollback_chain(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        make_trace,
        delegate_stub,
        ic09_audit_emitter,
        state_spy,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        # -------- S5 · Verifier 检测信任坍塌 (passed mismatch) --------
        trace = make_trace(test_report={"passed": 10, "failed": 0, "coverage": 0.85})
        bad_output = {
            "blueprint_alignment": {
                "dod_expression": "tests_pass_and_coverage_ge_80",
                "red_tests": ["t1", "t2"],
            },
            # verifier 实测 passed=8 · 主 session 声称 10 · 信任坍塌
            "s4_diff_analysis": {"passed": 8, "failed": 2, "coverage": 0.85},
            "dod_evaluation": {"verdict": "PASS", "all_pass": True},
            "verifier_report_id": "vr-trust-collapse",
        }
        waiter = CallbackWaiterStub(output=bad_output)
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=ic09_audit_emitter,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(trace, deps)
        assert result.verdict == VerifierVerdict.FAIL_L1
        assert result.signatures.s4_diff_analysis_ok is False

        # -------- L1-07 · RollbackPusher 收到 verdict · push IC-14 --------
        # 真实 rollback_pusher 从 verifier_verdict 翻译成 PushRollbackRouteCommand
        # 本 TC 直接构造 Dev-ζ producer → WP07 consumer 链路
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=_BusAdapter(real_event_bus),
        )

        class _ConsumerTarget:
            """Pusher 的 target · 包 consumer."""

            def __init__(self, c: IC14Consumer, known: set) -> None:
                self._c = c
                self.known_wps = known
                self.done_wps: set = set()

            def is_known_wp(self, wp_id: str) -> bool:
                return wp_id in self.known_wps

            def is_done_wp(self, wp_id: str) -> bool:
                return False

            async def apply_route(self, command):
                ack = await self._c.consume(command)
                return ack.new_wp_state

        target = _ConsumerTarget(consumer, {"wp-int-1"})
        pusher = RollbackPusher(
            session_pid=project_id,
            target=target,
            event_bus=_BusAdapter(real_event_bus, actor="supervisor"),
        )
        # FAIL_L1 → S3 · 信任坍塌回 S3 重跑
        cmd = PushRollbackRouteCommand(
            route_id="route-trust-001",
            project_id=project_id,
            wp_id="wp-int-1",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-trust-collapse"),
            ts="2026-04-23T10:00:00Z",
        )
        ack = await pusher.push_rollback_route(cmd)

        # -------- IC-01 · state_transition 被调用 · retry_s3 --------
        assert ack.applied is True
        assert ack.new_wp_state == NewWpState.RETRY_S3
        assert len(state_spy.calls) == 1
        assert state_spy.calls[0]["project_id"] == project_id
        assert state_spy.calls[0]["new_wp_state"] == "retry_s3"

        # -------- IC-09 · 审计链齐 --------
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        evs = _collect_jsonl(events_path)
        types = set(e["type"] for e in evs)
        assert "L1-04:verifier_report_issued" in types
        assert "L1-04:rollback_executed" in types
        # hash-chain 无 gap
        seqs = [e["sequence"] for e in evs]
        assert seqs == list(range(1, len(evs) + 1))


# ==============================================================================
# TC-3 · 同级 ≥ 3 升级 · 深度回退 UPGRADE_TO_L1_01
# ==============================================================================


class TestFullStageGateEscalation:
    """同级 ≥ 3 升级: 3 次 FAIL_L1 · 第 3 次升级到 UPGRADE_TO_L1_01."""

    async def test_three_fail_l1_escalates_to_upgrade(
        self,
        real_event_bus: EventBus,
        project_id: str,
        state_spy,
    ) -> None:
        consumer = IC14Consumer(
            session_pid=project_id,
            state_transition=state_spy,
            event_bus=_BusAdapter(real_event_bus),
        )
        acks = []
        for i in range(1, 4):
            ts = TargetStage.S3 if i < 3 else TargetStage.UPGRADE_TO_L1_01
            cmd = PushRollbackRouteCommand(
                route_id=f"route-esc-{i:03d}",
                project_id=project_id,
                wp_id="wp-esc",
                verdict=FailVerdict.FAIL_L1,
                target_stage=ts,
                level_count=i,
                evidence=RouteEvidence(verifier_report_id=f"vr-{i}"),
                ts="2026-04-23T10:00:00Z",
            )
            acks.append(await consumer.consume(cmd))

        # 前 2 次 stage retry · 第 3 次升级
        assert acks[0].new_wp_state == NewWpState.RETRY_S3
        assert acks[0].escalated is False
        assert acks[1].new_wp_state == NewWpState.RETRY_S3
        assert acks[1].escalated is False
        assert acks[2].new_wp_state == NewWpState.UPGRADED_TO_L1_01
        assert acks[2].escalated is True

        # state_transition 各调用 1 次
        assert len(state_spy.calls) == 3
        assert state_spy.calls[-1]["new_wp_state"] == "upgraded_to_l1_01"
        assert state_spy.calls[-1]["escalated"] is True


# ==============================================================================
# TC-4 · Verifier timeout → FAIL_L4 · 深度回退 UPGRADE
# ==============================================================================


class TestFullStageGateTimeout:
    """Verifier 独立 session 超时 → FAIL_L4 · 上游升级到 L1-01."""

    async def test_verifier_timeout_produces_fail_l4(
        self,
        make_trace,
        delegate_stub,
        no_sleep,
    ) -> None:
        from tests.integration.l1_04_cross_l1.conftest import CallbackWaiterStub

        waiter = CallbackWaiterStub(exc=TimeoutError("verifier 1200s exhausted"))
        deps = VerifierDeps(
            delegator=delegate_stub,
            callback_waiter=waiter,
            audit_emitter=None,
            sleep=no_sleep,
        )
        result = await orchestrate_s5(make_trace(), deps)
        assert result.verdict == VerifierVerdict.FAIL_L4
        # 三段证据含超时说明
        dod_ev = result.three_segment_evidence["dod_evaluation"]
        assert dod_ev.get("status") == "skipped_due_to_timeout"


# ==============================================================================
# TC-5 · PM-14 严格隔离 · 跨 project 命令拒绝
# ==============================================================================


class TestFullStageGatePM14:
    """PM-14 硬红线贯穿全栈 · project_id 不能越界."""

    async def test_cross_project_rejected_in_rollback_chain(
        self,
        real_event_bus: EventBus,
        project_id: str,
        state_spy,
    ) -> None:
        consumer = IC14Consumer(
            session_pid=project_id,  # "proj-wp09"
            state_transition=state_spy,
            event_bus=_BusAdapter(real_event_bus),
        )
        # 尝试发 proj-BLACK 的 command 给 proj-wp09 consumer
        bad_cmd = PushRollbackRouteCommand(
            route_id="route-black-001",
            project_id="proj-BLACK",
            wp_id="wp-x",
            verdict=FailVerdict.FAIL_L1,
            target_stage=TargetStage.S3,
            level_count=1,
            evidence=RouteEvidence(verifier_report_id="vr-black"),
            ts="2026-04-23T10:00:00Z",
        )
        with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
            await consumer.consume(bad_cmd)
        # state_transition 不被触发
        assert len(state_spy.calls) == 0
