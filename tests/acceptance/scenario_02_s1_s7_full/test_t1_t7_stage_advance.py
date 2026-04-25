"""scenario_02 · T1-T7 · 7 阶段切换正向 · 每阶段 1 TC.

7 阶段 TC 映射 (对齐 stage-dod.md §4):
    T1 · S1 = INITIALIZED → PLANNING (gate + IC-01 真发起)
    T2 · S2 = PLANNING → TDD_PLANNING
    T3 · S3 = TDD_PLANNING → EXECUTING
    T4 · S4 stage_progress 信号 (EXECUTING 内推进 · 无 transition)
    T5 · S5 = EXECUTING → CLOSING (合并 S5/S6 的 transition)
    T6 · S6 stage_progress 信号 (CLOSING 内 · 无 transition)
    T7 · S7 = CLOSING → CLOSED (final gate)

每 TC Then 检查:
    - IC-01 唯一发起 (l1_01_spy.calls 增 1)
    - IC-09 落盘 (gate_decision_computed + state_transition_authorized + gate_closed)
    - hash chain 完整
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.project_lifecycle.stage_gate import StageGateController
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


async def test_t1_s1_initialized_to_planning(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T1 · S1 gate pass · IC-01 INITIALIZED → PLANNING · IC-09 落盘."""
    async with gwt("T1 · S1 gate pass · IC-01 transition + IC-09 audit"):
        gwt.given(f"project={project_id} 处 INITIALIZED · stage_gate 干净 · audit-ledger 空")
        before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert before == 0
        assert l1_01_spy.calls == []

        gwt.when("提交 S1 全量 evidence(charter_ready + stakeholders_ready + goal_anchor_hash_locked) + user approve")
        dec, result = advance_stage("S1", current_state="INITIALIZED")

        gwt.then("S1 gate decision = pass · from=INITIALIZED · to=PLANNING")
        assert dec.decision == "pass"
        assert dec.from_state == "INITIALIZED"
        assert dec.to_state == "PLANNING"

        gwt.then("user approve 触发 IC-01 唯一发起 · l1_01_spy 调用 1 次")
        assert len(l1_01_spy.calls) == 1
        ic01 = l1_01_spy.calls[0]
        assert ic01["from_state"] == "INITIALIZED"
        assert ic01["to_state"] == "PLANNING"
        assert ic01["project_id"] == project_id
        assert ic01["evidence_refs"] == (dec.gate_id,)

        gwt.then("IC-09 audit · 至少 4 events: gate_decision_computed + ic_16_push + state_transition_authorized + gate_closed")
        assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision_computed",
        )
        assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:state_transition_authorized",
        )
        assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_closed",
        )

        gwt.then("hash chain 完整跨多 event")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n >= 4, f"S1 切换至少 4 audit events · 实际={n}"


async def test_t2_s2_planning_to_tdd_planning(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T2 · S2 gate pass · 4 件套 + 9 PMP 计划 + TOGAF + WBS."""
    async with gwt("T2 · S2 gate pass · 4-pieces + 9-plans + togaf + wbs"):
        gwt.given(f"已经历 S1 → 处 PLANNING · 准备进 S2 末 gate")
        # 先推进到 PLANNING
        advance_stage("S1", current_state="INITIALIZED")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("提交 S2 全量 evidence(4_pieces_ready + 9_plans_ready + togaf_ready + wbs_ready) + user approve")
        dec, _ = advance_stage("S2", current_state="PLANNING")

        gwt.then("S2 gate pass · from=PLANNING · to=TDD_PLANNING")
        assert dec.decision == "pass"
        assert dec.from_state == "PLANNING"
        assert dec.to_state == "TDD_PLANNING"

        gwt.then("IC-01 第二次调用")
        assert len(l1_01_spy.calls) == ic01_before + 1
        assert l1_01_spy.calls[-1]["to_state"] == "TDD_PLANNING"

        gwt.then("hash chain 跨 S1+S2 仍完整")
        assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)


async def test_t3_s3_tdd_planning_to_executing(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T3 · S3 = TDD_PLANNING → EXECUTING · 进 S4 实施段."""
    async with gwt("T3 · S3 gate pass · tdd_blueprint_ready"):
        gwt.given("已经 S1+S2 通过 · 处 TDD_PLANNING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")

        gwt.when("提交 S3 evidence(tdd_blueprint_ready) + approve")
        dec, _ = advance_stage("S3", current_state="TDD_PLANNING")

        gwt.then("S3 transition · TDD_PLANNING → EXECUTING")
        assert dec.decision == "pass"
        assert dec.from_state == "TDD_PLANNING"
        assert dec.to_state == "EXECUTING"

        gwt.then("IC-01 第三次")
        assert l1_01_spy.calls[-1]["to_state"] == "EXECUTING"


async def test_t4_s4_stage_progress_signal(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T4 · S4 stage_progress (EXECUTING 内 · 无 transition).

    S4 是 'TDD_PLANNING → EXECUTING (early)' · 但 transition 已在 T3 完成 ·
    S4 本身只是 IC-09 stage_progress 信号(WBS 全 WP 完成 · coverage / ruff / mypy 0).
    """
    async with gwt("T4 · S4 stage_progress · WBS WP 全 done"):
        gwt.given("已 S1+S2+S3 · 处 EXECUTING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("EXECUTING 内 · S4 全 WP 完成 · emit stage_progress signal")
        # 直接通过 real_event_bus 落 IC-09 stage_progress
        evt = Event(
            project_id=project_id,
            type="L1-02:stage_progress",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={
                "stage": "S4",
                "signal": "all_wp_complete",
                "test_pass_rate": 1.0,
                "coverage": 0.85,
                "ruff_errors": 0,
                "mypy_errors": 0,
            },
        )
        real_event_bus.append(evt)

        gwt.then("S4 不触发 IC-01 transition (仍 EXECUTING)")
        assert len(l1_01_spy.calls) == ic01_before, "S4 应无 IC-01 transition"

        gwt.then("IC-09 落盘 stage_progress signal")
        events = list_events(
            event_bus_root, project_id, type_exact="L1-02:stage_progress",
        )
        assert len(events) == 1
        assert events[0]["payload"]["stage"] == "S4"
        assert events[0]["payload"]["test_pass_rate"] == 1.0


async def test_t5_s5_executing_to_closing(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T5 · S5 = EXECUTING → CLOSING · integration 全绿 + acceptance + security_scan + perf SLO."""
    async with gwt("T5 · S5 gate pass · s5_pass evidence"):
        gwt.given("已 S1-S3 · 处 EXECUTING · S4 完成")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")

        gwt.when("S5 验证全 PASS · evidence(s5_pass) + approve")
        dec, _ = advance_stage("S5", current_state="EXECUTING")

        gwt.then("S5 transition · EXECUTING → CLOSING")
        assert dec.decision == "pass"
        assert dec.from_state == "EXECUTING"
        assert dec.to_state == "CLOSING"
        assert l1_01_spy.calls[-1]["to_state"] == "CLOSING"


async def test_t6_s6_stage_progress_signal(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T6 · S6 stage_progress · CLOSING 内推进(部署脚本 + runbook + user_signoff)."""
    async with gwt("T6 · S6 stage_progress · 部署 + runbook + signoff(PM)"):
        gwt.given("已 S1-S5 · 处 CLOSING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        advance_stage("S5", current_state="EXECUTING")
        ic01_before = len(l1_01_spy.calls)

        gwt.when("CLOSING 内 · S6 deploy + runbook + signoff 完成 · emit stage_progress")
        evt = Event(
            project_id=project_id,
            type="L1-02:stage_progress",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={
                "stage": "S6",
                "signal": "deploy_runbook_signoff",
                "deploy_script_executable": True,
                "runbook_ready": True,
                "user_signoff_pm_s6": True,
            },
        )
        real_event_bus.append(evt)

        gwt.then("S6 不触发 IC-01 transition (仍 CLOSING)")
        assert len(l1_01_spy.calls) == ic01_before

        gwt.then("IC-09 stage_progress S6 落盘")
        events = [
            e for e in list_events(event_bus_root, project_id, type_exact="L1-02:stage_progress")
            if e["payload"].get("stage") == "S6"
        ]
        assert len(events) == 1
        assert events[0]["payload"]["user_signoff_pm_s6"] is True


async def test_t7_s7_closing_to_closed_final(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T7 · S7 final gate · CLOSING → CLOSED · audit_chain_closed + retro + customer signoff."""
    async with gwt("T7 · S7 final gate pass · CLOSED"):
        gwt.given("已 S1-S6 · 处 CLOSING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        advance_stage("S5", current_state="EXECUTING")

        gwt.when("S7 evidence(delivery_bundled + retro_ready + archive_written) + customer approve")
        dec, _ = advance_stage("S7", current_state="CLOSING")

        gwt.then("S7 transition · CLOSING → CLOSED")
        assert dec.decision == "pass"
        assert dec.from_state == "CLOSING"
        assert dec.to_state == "CLOSED"
        assert l1_01_spy.calls[-1]["to_state"] == "CLOSED"

        gwt.then("hash chain 跨全部 5 transitions 完整")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        # S1+S2+S3+S5+S7 共 5 transitions · 每次至少 4 events(decision + push_card + authorized + closed)
        assert n >= 20, f"7 阶段跑下来至少 20 events · 实际={n}"
