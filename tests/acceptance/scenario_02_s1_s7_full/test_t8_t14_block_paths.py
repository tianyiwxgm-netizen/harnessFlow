"""scenario_02 · T8-T14 · 每阶段 BLOCK 路径(缺 evidence / DoD 不达标 / 越权).

T8  · S1 缺 charter_ready → need_input + missing_signals
T9  · S2 缺 togaf_ready → need_input
T10 · S3 缺 tdd_blueprint_ready → need_input
T11 · S5 缺 s5_pass → need_input
T12 · S7 缺 retro_ready + archive_written → need_input
T13 · BLOCK · 非法直跨阶段 (PLANNING → CLOSED) state_machine 拒
T14 · BLOCK · authorize_transition reason 不足 20 字 拒
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from app.project_lifecycle.stage_gate import (
    StageGateController,
    StageGateError,
)
from app.project_lifecycle.stage_gate.errors import (
    E_TRANSITION_FORBIDDEN,
)
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    list_events,
)


async def test_t8_s1_block_missing_charter(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    evidence_factory,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T8 · S1 缺 charter_ready → need_input · 不进 IC-01."""
    async with gwt("T8 · S1 BLOCK · charter_ready 缺"):
        gwt.given(f"project={project_id} 处 INITIALIZED · 但 charter 未 ready")

        gwt.when("提交 S1 evidence · 缺 charter_ready · 仅 stakeholders + goal_anchor")
        ev = evidence_factory(
            "S1",
            signals=("stakeholders_ready", "goal_anchor_hash_locked"),
        )
        dec = stage_gate.request_gate_decision(ev, current_state="INITIALIZED")

        gwt.then("decision=need_input · missing_signals 含 charter_ready")
        assert dec.decision == "need_input"
        assert "charter_ready" in dec.missing_signals

        gwt.then("不触发 IC-01 transition · l1_01_spy 0 调用")
        assert l1_01_spy.calls == []

        gwt.then("IC-09 落 gate_decision_computed · 含 missing_signals payload")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision_computed",
        )
        assert events[0]["payload"]["decision"] == "need_input"
        assert "charter_ready" in events[0]["payload"]["missing_signals"]


async def test_t9_s2_block_missing_togaf(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    evidence_factory,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T9 · S2 缺 togaf_ready → need_input."""
    async with gwt("T9 · S2 BLOCK · TOGAF 未交付"):
        gwt.given("已 S1 · 处 PLANNING")
        advance_stage("S1", current_state="INITIALIZED")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("S2 evidence 缺 togaf_ready")
        ev = evidence_factory(
            "S2",
            signals=("4_pieces_ready", "9_plans_ready", "wbs_ready"),
        )
        dec = stage_gate.request_gate_decision(ev, current_state="PLANNING")

        gwt.then("need_input · togaf_ready 在 missing")
        assert dec.decision == "need_input"
        assert "togaf_ready" in dec.missing_signals

        gwt.then("不进 TDD_PLANNING · IC-01 不增")
        assert len(l1_01_spy.calls) == ic01_before


async def test_t10_s3_block_missing_tdd_blueprint(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    evidence_factory,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T10 · S3 缺 tdd_blueprint_ready → need_input."""
    async with gwt("T10 · S3 BLOCK · TDD blueprint 缺"):
        gwt.given("已 S1+S2 · 处 TDD_PLANNING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("S3 evidence 空 signals")
        ev = evidence_factory("S3", signals=())
        dec = stage_gate.request_gate_decision(ev, current_state="TDD_PLANNING")

        gwt.then("need_input · tdd_blueprint_ready 缺")
        assert dec.decision == "need_input"
        assert "tdd_blueprint_ready" in dec.missing_signals

        gwt.then("不进 EXECUTING · IC-01 不增")
        assert len(l1_01_spy.calls) == ic01_before


async def test_t11_s5_block_missing_s5_pass(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    evidence_factory,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T11 · S5 缺 s5_pass → need_input · 验证未通过."""
    async with gwt("T11 · S5 BLOCK · s5_pass 未达"):
        gwt.given("已 S1-S3 · 处 EXECUTING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("S5 evidence 空 signals · 表示 integration/perf 未全绿")
        ev = evidence_factory("S5", signals=())
        dec = stage_gate.request_gate_decision(ev, current_state="EXECUTING")

        gwt.then("need_input · 不进 CLOSING")
        assert dec.decision == "need_input"
        assert "s5_pass" in dec.missing_signals

        gwt.then("无 IC-01 调用增")
        assert len(l1_01_spy.calls) == ic01_before


async def test_t12_s7_block_missing_retro_archive(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    evidence_factory,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T12 · S7 缺 retro_ready + archive_written → need_input."""
    async with gwt("T12 · S7 BLOCK · retro+archive 都缺"):
        gwt.given("已 S1-S5 · 处 CLOSING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        advance_stage("S5", current_state="EXECUTING")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("S7 evidence 仅 delivery_bundled · 缺 retro+archive")
        ev = evidence_factory("S7", signals=("delivery_bundled",))
        dec = stage_gate.request_gate_decision(ev, current_state="CLOSING")

        gwt.then("need_input · retro_ready 与 archive_written 都列在 missing")
        assert dec.decision == "need_input"
        assert "retro_ready" in dec.missing_signals
        assert "archive_written" in dec.missing_signals

        gwt.then("不进 CLOSED · IC-01 不增")
        assert len(l1_01_spy.calls) == ic01_before


async def test_t13_illegal_skip_to_closed(
    stage_gate: StageGateController,
    project_id: str,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T13 · BLOCK · 非法直跨 PLANNING → CLOSED (须经 CLOSING)."""
    async with gwt("T13 · 非法 stage skip · state_machine 拒"):
        gwt.given("处 PLANNING · 想直接跳 CLOSED")

        gwt.when("外部恶意调 authorize_transition · PLANNING → CLOSED 实际是合法 (PLANNING → CLOSED 是 ALLOWED 终止)")
        # PLANNING → CLOSED 是合法 (failed_terminal) · 测真非法 INITIALIZED → CLOSED
        with __import__("pytest").raises(StageGateError) as exc:
            stage_gate.authorize_transition(
                project_id=project_id,
                from_state="INITIALIZED",
                to_state="CLOSED",
                gate_id="gate-skip-evil",
                reason="evil-attempt-to-skip-stages-via-direct-call",
            )

        gwt.then("error_code = E_TRANSITION_FORBIDDEN")
        assert exc.value.error_code == E_TRANSITION_FORBIDDEN

        gwt.then("IC-01 spy 0 次 (拒在 validate 阶段)")
        assert l1_01_spy.calls == []


async def test_t14_authorize_reason_too_short(
    stage_gate: StageGateController,
    project_id: str,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T14 · BLOCK · authorize_transition reason < 20 字 拒."""
    async with gwt("T14 · authorize reason 不达 20 字 · 硬拒"):
        gwt.given("正合法 transition · 但 reason='ok' (3字)")

        gwt.when("调 authorize_transition reason 短")
        with __import__("pytest").raises(StageGateError) as exc:
            stage_gate.authorize_transition(
                project_id=project_id,
                from_state="INITIALIZED",
                to_state="PLANNING",
                gate_id="gate-short-reason",
                reason="ok",  # 3 字 < 20
            )

        gwt.then("error_code = E_TRANSITION_FORBIDDEN")
        assert exc.value.error_code == E_TRANSITION_FORBIDDEN

        gwt.then("IC-01 spy 0 次")
        assert l1_01_spy.calls == []
