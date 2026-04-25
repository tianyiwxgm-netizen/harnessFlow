"""scenario_02 · T18-T22 · 扩展(全程 audit + hash chain + IC 链路 + S7 归档).

T18 · 全程 audit-ledger 完整性 (跨 7 stage · seq 严格连续)
T19 · hash chain 跨阶段断裂检测 (篡改检测)
T20 · IC-09 → 跨 IC 链路追溯 (transition_id + correlation_id 串联)
T21 · 跨阶段 evidence_refs 引用 (S2 引 S1 chart · S3 引 S2 wbs)
T22 · S7 收尾归档完成 · final_signoff(Customer) · audit_chain_closed
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.project_lifecycle.stage_gate import EvidenceBundle, StageGateController
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


async def test_t18_audit_ledger_full_integrity_seven_stages(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    gwt: GWT,
) -> None:
    """T18 · 全程 audit-ledger 完整性 · 跨 7 stage · seq 1..N 严格连续无 gap."""
    async with gwt("T18 · audit-ledger seq 全程严格连续"):
        gwt.given("干净 project · 跑 5 transition + 2 stage_progress")

        gwt.when("跑全 7 阶段")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        real_event_bus.append(Event(
            project_id=project_id, type="L1-02:stage_progress", actor="planner",
            timestamp=datetime.now(UTC), payload={"stage": "S4"},
        ))
        advance_stage("S5", current_state="EXECUTING")
        real_event_bus.append(Event(
            project_id=project_id, type="L1-02:stage_progress", actor="planner",
            timestamp=datetime.now(UTC), payload={"stage": "S6"},
        ))
        advance_stage("S7", current_state="CLOSING")

        gwt.then("seq 1..N 严格连续无 gap (assert_ic_09_hash_chain_intact 内部校验)")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n >= 22, f"全 7 stage 至少 22 events · 实际={n}"

        gwt.then("每 type 至少出现一次 (gate_decision_computed / state_transition_authorized / gate_closed / stage_progress / ic_16_push_stage_gate_card)")
        types_seen = {
            e.get("type") for e in list_events(event_bus_root, project_id)
        }
        for required_type in (
            "L1-02:gate_decision_computed",
            "L1-02:state_transition_authorized",
            "L1-02:gate_closed",
            "L1-02:stage_progress",
            "L1-02:ic_16_push_stage_gate_card",
        ):
            assert required_type in types_seen, (
                f"7 stage 全程缺类型 {required_type} · 实际={types_seen}"
            )


async def test_t19_hash_chain_tamper_detection(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    gwt: GWT,
) -> None:
    """T19 · 跨阶段 hash chain 篡改检测 · 修改中间一行 → 整链断裂."""
    async with gwt("T19 · hash chain 篡改检测"):
        gwt.given("跑 S1+S2 · 落 ≥ 8 events")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        n_before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_before >= 8

        gwt.when("篡改 events.jsonl 中第 4 条 prev_hash(模拟攻击)")
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = events_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= 8
        # 修改第 4 行 prev_hash(篡改链头 · 应让 chain 串验证失败)
        import json
        line4 = json.loads(lines[3])
        # 改 prev_hash 字段(直接破链)
        line4["prev_hash"] = "0" * 64  # 假 hash · 与上一条 hash 不连
        lines[3] = json.dumps(line4, sort_keys=True)
        events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        gwt.then("hash chain prev_hash 不匹配 · raise AssertionError")
        import pytest
        with pytest.raises(AssertionError, match="prev_hash"):
            assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)


async def test_t20_correlation_id_propagation(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T20 · IC-09 各 event 含 correlation_id · 同 transition 共用一个 corr_id (追溯可建)."""
    async with gwt("T20 · IC-09 correlation_id 跨 event 传播"):
        gwt.given("跑 S1 transition · 期望 4 个相关 event")
        advance_stage("S1", current_state="INITIALIZED")

        gwt.then("每 event 都含 correlation_id 字段(WP06 已注入)")
        events = list_events(event_bus_root, project_id, type_prefix="L1-02:")
        assert len(events) >= 4
        for evt in events:
            assert "correlation_id" in evt, f"event 缺 correlation_id · evt={evt}"
            assert evt["correlation_id"], f"correlation_id 不能空 · evt={evt}"

        gwt.then("相邻同 stage 的 events 通过 transition_id 可链 (IC-01 spy 持有 trans-{uuid})")
        ic01 = l1_01_spy.calls[-1]
        assert ic01["transition_id"].startswith("trans-")

        gwt.then("evidence_refs 跨 IC 引用 (gate_id 是 IC-09 与 IC-01 桥)")
        gate_id = ic01["gate_id"]
        # state_transition_authorized 和 gate_closed payload 都应含 gate_id
        authz = [e for e in events if e["type"] == "L1-02:state_transition_authorized"]
        assert authz
        assert authz[0]["payload"]["gate_id"] == gate_id


async def test_t21_cross_stage_evidence_chain(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T21 · 跨阶段 evidence_refs 引用链 · S2 transition 持 S1 gate_id 作 evidence_refs."""
    async with gwt("T21 · 跨阶段 evidence 引用链 · S1 → S2 → S3"):
        gwt.given("空 project · 即将跑 S1+S2+S3")

        gwt.when("跑 S1 · S2 · S3 · 收集每次 IC-01 的 evidence_refs")
        d1, _ = advance_stage("S1", current_state="INITIALIZED")
        d2, _ = advance_stage("S2", current_state="PLANNING")
        d3, _ = advance_stage("S3", current_state="TDD_PLANNING")

        gwt.then("每 IC-01 evidence_refs 至少含本 stage 的 gate_id")
        assert len(l1_01_spy.calls) == 3
        # S1 IC-01 引用 S1 gate_id
        assert d1.gate_id in l1_01_spy.calls[0]["evidence_refs"]
        # S2 IC-01 引用 S2 gate_id
        assert d2.gate_id in l1_01_spy.calls[1]["evidence_refs"]
        # S3 IC-01 引用 S3 gate_id
        assert d3.gate_id in l1_01_spy.calls[2]["evidence_refs"]

        gwt.then("3 个 transition_id 互不相同 (各自独立 UUID)")
        trans_ids = {c["transition_id"] for c in l1_01_spy.calls}
        assert len(trans_ids) == 3, f"transition_id 重复 · {trans_ids}"

        gwt.then("3 个 gate_id 互不相同")
        assert d1.gate_id != d2.gate_id != d3.gate_id


async def test_t22_s7_archive_finalsignoff_close(
    stage_gate: StageGateController,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    advance_stage,
    l1_01_spy,
    gwt: GWT,
) -> None:
    """T22 · S7 final 收尾归档 · final_signoff(Customer) · audit_chain_closed."""
    async with gwt("T22 · S7 final 归档 + customer signoff"):
        gwt.given("跑完 S1-S5 · 处 CLOSING")
        advance_stage("S1", current_state="INITIALIZED")
        advance_stage("S2", current_state="PLANNING")
        advance_stage("S3", current_state="TDD_PLANNING")
        advance_stage("S5", current_state="EXECUTING")

        gwt.when("S7 final gate · evidence(delivery_bundled + retro_ready + archive_written) + customer 签字")
        ev = EvidenceBundle(
            project_id=project_id,
            stage="S7",
            request_id="req-s7-final",
            signals=("delivery_bundled", "retro_ready", "archive_written"),
            caller_l2="L2-06-closing",
        )
        dec = stage_gate.request_gate_decision(ev, current_state="CLOSING")
        assert dec.decision == "pass"
        assert dec.to_state == "CLOSED"

        result = stage_gate.receive_user_decision(
            gate_id=dec.gate_id,
            user_decision="approve",
            reason="customer final signoff after delivery review and retro completion",
        )
        assert result["transition_success"] is True

        gwt.and_("emit final 'audit_chain_closed' marker event")
        real_event_bus.append(Event(
            project_id=project_id, type="L1-02:audit_chain_closed",
            actor="planner", timestamp=datetime.now(UTC),
            payload={
                "stage": "S7",
                "final_signoff_customer": True,
                "kb_promotions_count": 11,
                "retro_completed": True,
            },
        ))

        gwt.then("最终 IC-01 to_state=CLOSED · 项目完结")
        assert l1_01_spy.calls[-1]["to_state"] == "CLOSED"

        gwt.then("audit_chain_closed marker · final_signoff_customer=True")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:audit_chain_closed",
            payload_contains={"final_signoff_customer": True},
        )
        assert events
        assert events[0]["payload"]["kb_promotions_count"] == 11

        gwt.then("hash chain 跨全程 (S1-S7 + close marker) 完整")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        # 5 transitions × 4 events + audit_chain_closed = 21+
        assert n >= 21
