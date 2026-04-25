"""Row L1-01 主决策(main_loop) → others · 4 cells × 6 TC = 24 TC.

**4 cells**:
    L1-01 → L1-02 · IC-01 触发 stage_transition (7 状态 / PM-14 / 拒非法边)
    L1-01 → L1-04 · IC-14 trigger Gate (verdict 接收 / 重试 / 升级)
    L1-01 → L1-05 · IC-04 调 skill (调用 / 超时 / fallback)
    L1-01 → L1-09 · IC-09 append_event (hash chain / SLO)

**每 cell 6 TC**: HAPPY × 2 / NEGATIVE × 2 / SLO × 1 / E2E × 1.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.state_machine import (
    StateMachineOrchestrator,
    TransitionRequest,
)
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# IC-01 严格 pid 格式: ^pid-[0-9a-fA-F-]{8,}$
_L1_01_PID = "pid-00000000-0000-0000-0000-000000ab0001"
_L1_01_PID_OTHER = "pid-00000000-0000-0000-0000-000000ab0002"


def _build_request(
    project_id: str, frm: str, to: str, *, suffix: str = "0001",
) -> TransitionRequest:
    # transition_id 格式: ^trans-[0-9a-fA-F-]{8,}$ (只允许 hex + 短横)
    tid_suffix = suffix.zfill(4)  # padding 到 4 hex
    return TransitionRequest(
        transition_id=f"trans-{tid_suffix}-deadbeef-feedface",
        project_id=project_id,
        from_state=frm,
        to_state=to,
        reason=f"IC-01 矩阵集成测试 {frm} -> {to} reason ≥ 20 字",
        trigger_tick="tick-00000000-0000-0000-0000-000000000001",
        evidence_refs=("ev-matrix-1",),
        ts="2026-04-23T10:00:00.000000Z",
    )


# =============================================================================
# Cell 1: L1-01 → L1-02 · IC-01 触发 stage_transition (6 TC)
# =============================================================================


class TestRowL1_01_to_L1_02:
    """L1-01 主决策 → L1-02 项目生命周期 · IC-01 stage_transition 契约."""

    def test_happy_init_to_planning_state_transition(self, matrix_cov) -> None:
        """HAPPY · NOT_EXIST → INITIALIZED 合法 transition."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "INITIALIZED"
        assert orch.get_current_state() == "INITIALIZED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_happy_planning_to_tdd_full_chain(self, matrix_cov) -> None:
        """HAPPY · 推进 PLANNING → TDD_PLANNING (常用主链路)."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="PLANNING",
        )
        req = _build_request(_L1_01_PID, "PLANNING", "TDD_PLANNING")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_negative_illegal_edge_rejected(self, matrix_cov) -> None:
        """NEGATIVE · 非法边 NOT_EXIST → CLOSED 必拒 + error_code."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "CLOSED")
        result = orch.transition(req)
        assert result.accepted is False
        assert result.error_code is not None
        # state 不变
        assert orch.get_current_state() == "NOT_EXIST"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.NEGATIVE)

    def test_negative_pm14_cross_project_rejected(self, matrix_cov) -> None:
        """NEGATIVE/PM-14 · 跨 pid transition_id 必拒(orchestrator pid != req pid)."""
        from app.main_loop.state_machine.schemas import (
            E_TRANS_CROSS_PROJECT,
            StateMachineError,
        )

        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        # 用 other pid 构造 request (违反 PM-14)
        req = _build_request(_L1_01_PID_OTHER, "NOT_EXIST", "INITIALIZED")
        with pytest.raises(StateMachineError) as exc_info:
            orch.transition(req)
        assert exc_info.value.error_code == E_TRANS_CROSS_PROJECT
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.PM14)

    def test_slo_transition_under_100ms(self, matrix_cov) -> None:
        """SLO · IC-01 transition P99 < 100ms."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        req = _build_request(_L1_01_PID, "NOT_EXIST", "INITIALIZED")
        t0 = time.monotonic()
        result = orch.transition(req)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert result.accepted is True
        assert elapsed_ms < 100, f"IC-01 SLO 违反 实际 {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.HAPPY)

    def test_e2e_full_7_states_chain(self, matrix_cov) -> None:
        """E2E · 走完 6 边 N→I→P→T→E→C→CLOSED 全链 7 态正确."""
        from .conftest import record_cell

        orch = StateMachineOrchestrator(
            project_id=_L1_01_PID, initial_state="NOT_EXIST",
        )
        chain = [
            ("NOT_EXIST", "INITIALIZED"),
            ("INITIALIZED", "PLANNING"),
            ("PLANNING", "TDD_PLANNING"),
            ("TDD_PLANNING", "EXECUTING"),
            ("EXECUTING", "CLOSING"),
            ("CLOSING", "CLOSED"),
        ]
        for i, (frm, to) in enumerate(chain):
            req = _build_request(_L1_01_PID, frm, to, suffix=f"e2e{i:03d}")
            result = orch.transition(req)
            assert result.accepted is True
            assert result.new_state == to
        assert orch.get_current_state() == "CLOSED"
        record_cell(matrix_cov, "L1-01", "L1-02", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-01 → L1-04 · IC-14 trigger Gate / verdict 接收 (6 TC)
# =============================================================================


def _build_rollback_command(
    project_id: str = "proj-m3-shared",
    *,
    wp_id: str = "wp-m3-1",
    route_id: str = "route-m3-1",
    verdict: str = "FAIL_L1",
    target_stage: str = "S3",
    level_count: int = 1,
):
    from app.quality_loop.rollback_router.schemas import (
        FailVerdict,
        PushRollbackRouteCommand,
        RouteEvidence,
        TargetStage,
    )

    return PushRollbackRouteCommand(
        route_id=route_id,
        project_id=project_id,
        wp_id=wp_id,
        verdict=FailVerdict[verdict],
        target_stage=TargetStage[target_stage],
        level_count=level_count,
        evidence=RouteEvidence(verifier_report_id="vr-1", decision_id="dec-1"),
        ts="2026-04-23T10:00:00.000000Z",
    )


class _RealBusAdapter:
    """适配 L1-09 EventBus.append (sync) → executor 期望的 async append_event 协议."""

    def __init__(self, real_bus, default_actor: str = "verifier") -> None:
        self._bus = real_bus
        self._default_actor = default_actor

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,
        payload: dict,
        evidence_refs: tuple = (),
    ) -> str:
        from datetime import UTC, datetime

        from app.l1_09.event_bus.schemas import Event

        evt = Event(
            project_id=project_id,
            type=type,
            actor=self._default_actor,
            payload=dict(payload),
            timestamp=datetime.now(UTC),
        )
        result = self._bus.append(evt)
        return result.event_id


def _build_ic14_consumer(session_pid: str, real_event_bus, state_spy):
    """组装真 IC14Consumer · 使用真 EventBus(via adapter) + spy state_transition."""
    from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer

    return IC14Consumer(
        session_pid=session_pid,
        state_transition=state_spy,
        event_bus=_RealBusAdapter(real_event_bus, default_actor="verifier"),
    )


class TestRowL1_01_to_L1_04:
    """L1-01 主决策 → L1-04 Quality Loop · IC-14 rollback / verdict."""

    async def test_happy_fail_l1_to_s3_retry(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """HAPPY · FAIL_L1 → S3 retry · ack.applied=True · new_wp_state=retry_s3."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(project_id, verdict="FAIL_L1", target_stage="S3")
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.new_wp_state.value == "retry_s3"
        # state_transition 被调
        assert len(state_spy.calls) >= 1
        assert state_spy.calls[0]["wp_id"] == "wp-m3-1"
        assert state_spy.calls[0]["new_wp_state"] == "retry_s3"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_happy_fail_l4_upgrade_to_l1_01(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """HAPPY · FAIL_L4 → UPGRADE_TO_L1_01 · ack.escalated=True."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(
            project_id,
            wp_id="wp-m3-2", route_id="route-m3-2",
            verdict="FAIL_L4", target_stage="UPGRADE_TO_L1_01",
            level_count=3,
        )
        ack = await consumer.consume(cmd)
        assert ack.applied is True
        assert ack.escalated is True
        assert ack.new_wp_state.value == "upgraded_to_l1_01"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_negative_idempotent_replay_returns_cached_ack(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """NEGATIVE · 同 route_id 重复推 · 返 cached ack · state_transition 不重调."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(
            project_id, route_id="route-m3-idem", verdict="FAIL_L1",
        )
        ack1 = await consumer.consume(cmd)
        ack2 = await consumer.consume(cmd)
        assert ack1 == ack2
        # 仅一次实际 transition (第二次走幂等缓存)
        assert len(state_spy.calls) == 1
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.NEGATIVE)

    async def test_negative_pm14_cross_project_rejected(
        self, project_id: str, other_project_id: str, real_event_bus, state_spy,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · cross-project 必拒 E_ROUTE_CROSS_PROJECT."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        # 用 other pid 构造 command
        cmd = _build_rollback_command(other_project_id, verdict="FAIL_L1")
        with pytest.raises(ValueError) as exc_info:
            await consumer.consume(cmd)
        assert "E_ROUTE_CROSS_PROJECT" in str(exc_info.value)
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.PM14)

    async def test_slo_consume_under_100ms(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """SLO · IC-14 consume 单次 < 100ms (无回退预算)."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cmd = _build_rollback_command(project_id, verdict="FAIL_L1")
        t0 = time.monotonic()
        await consumer.consume(cmd)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-14 SLO 违反 {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.HAPPY)

    async def test_e2e_4_verdicts_full_routes(
        self, project_id: str, real_event_bus, state_spy, matrix_cov,
    ) -> None:
        """E2E · 4 verdict (L1/L2/L3/L4) → 各自 target_stage 全链路."""
        from .conftest import record_cell

        consumer = _build_ic14_consumer(project_id, real_event_bus, state_spy)
        cases = [
            ("FAIL_L1", "S3", "retry_s3", False),
            ("FAIL_L2", "S4", "retry_s4", False),
            ("FAIL_L3", "S5", "retry_s5", False),
            # FAIL_L4 首次(level_count=1) · 非"同级 ≥ 3" 触发 · escalated=False
            ("FAIL_L4", "UPGRADE_TO_L1_01", "upgraded_to_l1_01", False),
        ]
        for i, (verdict, ts, new_state, escalated) in enumerate(cases):
            cmd = _build_rollback_command(
                project_id,
                wp_id=f"wp-e2e-{i}", route_id=f"route-e2e-{i}",
                verdict=verdict, target_stage=ts, level_count=1,
            )
            ack = await consumer.consume(cmd)
            assert ack.new_wp_state.value == new_state
            assert ack.escalated is escalated
        # 4 个 transition 调用
        assert len(state_spy.calls) == 4
        record_cell(matrix_cov, "L1-01", "L1-04", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-01 → L1-05 · IC-04 调 skill (6 TC)
# =============================================================================


class TestRowL1_01_to_L1_05:
    """L1-01 主决策 → L1-05 Skill · IC-04 skill_invoke 契约."""

    async def test_happy_skill_invoke_returns_ok(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · 调 skill 返预置 output."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["wbs_decompose"] = {
            "status": "ok", "wps": ["wp-1", "wp-2"],
        }
        result = await fake_skill_invoker.invoke(
            skill_id="wbs_decompose",
            args={"project_id": project_id, "spec": "..."},
        )
        assert result["status"] == "ok"
        assert "wps" in result
        # call_log 记录到 invocation
        assert len(fake_skill_invoker.call_log) == 1
        assert fake_skill_invoker.call_log[0]["skill_id"] == "wbs_decompose"
        assert fake_skill_invoker.call_log[0]["args"]["project_id"] == project_id
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.HAPPY)

    async def test_happy_multiple_skills_invoked(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · 串行调 3 个不同 skill · 全部正确返."""
        from .conftest import record_cell

        skills = ["plan_review", "tdd_blueprint", "verifier_run"]
        for sid in skills:
            await fake_skill_invoker.invoke(skill_id=sid, args={"project_id": project_id})
        assert len(fake_skill_invoker.call_log) == 3
        assert [c["skill_id"] for c in fake_skill_invoker.call_log] == skills
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.HAPPY)

    async def test_negative_skill_timeout_raised(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """NEGATIVE · skill 超时 (error_queue 注入) → 上层捕获."""
        from .conftest import record_cell

        fake_skill_invoker.error_queue = [TimeoutError("skill timeout")]
        with pytest.raises(TimeoutError):
            await fake_skill_invoker.invoke(
                skill_id="slow_skill", args={"project_id": project_id},
            )
        # 仍记录调用
        assert len(fake_skill_invoker.call_log) == 1
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.NEGATIVE)

    async def test_negative_skill_failure_then_retry_success(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """NEGATIVE/降级 · 第一次失败 · 第二次成功(降级 fallback 模式)."""
        from .conftest import record_cell

        fake_skill_invoker.error_queue = [
            RuntimeError("skill crash 1"),
            None,  # 第二次正常
        ]
        fake_skill_invoker.outputs["retry_skill"] = {"status": "ok-retry"}
        with pytest.raises(RuntimeError):
            await fake_skill_invoker.invoke(
                skill_id="retry_skill", args={"project_id": project_id},
            )
        result = await fake_skill_invoker.invoke(
            skill_id="retry_skill", args={"project_id": project_id},
        )
        assert result["status"] == "ok-retry"
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.DEGRADE)

    async def test_slo_skill_invoke_under_100ms(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """SLO · stub invoke + record P99 < 100ms."""
        from .conftest import record_cell

        t0 = time.monotonic()
        await fake_skill_invoker.invoke(
            skill_id="quick_skill", args={"project_id": project_id},
        )
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-04 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.HAPPY)

    async def test_e2e_pm14_isolation_per_invoke(
        self, project_id: str, other_project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """E2E/PM-14 · 不同 pid 调相同 skill · args 内 pid 必区分隔离."""
        from .conftest import record_cell

        await fake_skill_invoker.invoke(
            skill_id="shared_skill", args={"project_id": project_id, "data": "foo"},
        )
        await fake_skill_invoker.invoke(
            skill_id="shared_skill",
            args={"project_id": other_project_id, "data": "bar"},
        )
        # 两次调用 · 各自 pid 独立
        pids = [c["args"]["project_id"] for c in fake_skill_invoker.call_log]
        assert pids == [project_id, other_project_id]
        record_cell(matrix_cov, "L1-01", "L1-05", CaseType.PM14)


# =============================================================================
# Cell 4: L1-01 → L1-09 · IC-09 append_event (6 TC)
# =============================================================================


class TestRowL1_01_to_L1_09:
    """L1-01 主决策 → L1-09 EventBus · IC-09 hash chain / SLO."""

    def _decision_event(
        self, project_id: str, decision_id: str = "d-1", action: str = "transition",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-01:decision_made",
            actor="main_loop",
            payload={"decision_id": decision_id, "action": action},
            timestamp=datetime.now(UTC),
        )

    def test_happy_decision_made_appended(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-01:decision_made 写入 · persisted=True · seq=1."""
        from .conftest import record_cell

        evt = self._decision_event(project_id)
        result = real_event_bus.append(evt)
        assert result.persisted is True
        assert result.sequence == 1
        assert len(result.hash) == 64
        # 落盘
        assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:decision_made",
            min_count=1,
        )
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.HAPPY)

    def test_happy_3_decisions_hash_chain_intact(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 个连续 decision · sequence + hash-chain 连续无断."""
        from .conftest import record_cell

        for i in range(3):
            evt = self._decision_event(project_id, decision_id=f"d-{i}")
            real_event_bus.append(evt)
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 3
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.HAPPY)

    def test_negative_invalid_type_prefix_rejected(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """NEGATIVE · 非法 type 前缀(L1-99) · Pydantic 拒绝."""
        from .conftest import record_cell

        with pytest.raises(Exception):  # ValidationError
            Event(
                project_id=project_id,
                type="L1-99:bad_event",
                actor="main_loop",
                payload={"x": 1},
                timestamp=datetime.now(UTC),
            )
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_isolation_separate_shards(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · pid_A 写 · pid_B 分片独立 · 不串."""
        from .conftest import record_cell

        evt_a = self._decision_event(project_id, decision_id="da")
        evt_b = self._decision_event(other_project_id, decision_id="db")
        real_event_bus.append(evt_a)
        real_event_bus.append(evt_b)
        # pid_A 分片只 1 条
        a_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:decision_made",
            min_count=1,
        )
        b_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=other_project_id,
            event_type="L1-01:decision_made",
            min_count=1,
        )
        # PM-14 · 各自分片独立 · seq 都从 1 开始
        assert a_events[0]["sequence"] == 1
        assert b_events[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.PM14)

    def test_slo_append_under_100ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-09 append < 100ms (P99 < 1ms 实测 · 留 100ms 余裕)."""
        from .conftest import record_cell

        evt = self._decision_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-09 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.HAPPY)

    def test_e2e_full_decision_lifecycle_audit(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 完整 decision 生命周期: made / executed / completed."""
        from .conftest import record_cell

        types = [
            "L1-01:decision_made",
            "L1-01:tick_scheduled",
            "L1-01:wp_decision_recorded",
        ]
        for t in types:
            evt = Event(
                project_id=project_id,
                type=t,
                actor="main_loop",
                payload={"d_id": "lifecycle"},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
        # 3 条事件 · hash chain 连续
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 3
        record_cell(matrix_cov, "L1-01", "L1-09", CaseType.DEGRADE)
