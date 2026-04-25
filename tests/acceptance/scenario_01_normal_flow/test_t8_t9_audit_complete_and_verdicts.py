"""Scenario 01 · T8-T9 · audit 完整 + 7 IC × 14 verdict 全 PASS.

T8: 全 7 stage 走完 · audit hash chain 完整 · 无 GAP / 无 BLOCK 类型
T9: 14 verdict 全 PASS · happy-path 不应出 FAIL_L*
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from tests.acceptance.scenario_01_normal_flow.conftest import (
    HAPPY_STAGES,
    HAPPY_VERDICTS,
)
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


def test_t8_full_stage_sequence_audit_chain_intact(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
) -> None:
    """T8 · 7 stage 全跑 · IC-09 hash chain 完整 · 无 BLOCK 类事件."""
    with gwt("T8 · 全程 7 stage audit chain 完整"):
        gwt.given("audit 干净起点")
        assert assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id) == 0

        gwt.when("依次 emit 7 stage gate_decision pass · 模拟 happy-path")
        for i, stage in enumerate(HAPPY_STAGES):
            emit_audit(
                "L1-02:gate_decision",
                {"stage": stage, "decision": "pass", "seq": i},
            )

        gwt.then(f"hash chain 完整 · 共 {len(HAPPY_STAGES)} 条 · seq=1..N")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == len(HAPPY_STAGES) == 7

        gwt.then("无任何 BLOCK / panic / redline 类事件")
        all_events = list_events(event_bus_root, project_id)
        forbidden_types = (
            "L1-04:rollback_executed",
            "L1-04:rollback_failed",
            "L1-01:hard_halted",
            "L1-09:bus_halted",
            "L1-07:hard_halt_requested",
        )
        for evt in all_events:
            assert evt["type"] not in forbidden_types, (
                f"happy-path 不应出 BLOCK 事件 实际={evt['type']}"
            )


def test_t9_fourteen_verdicts_all_pass(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
) -> None:
    """T9 · 14 verdict 全 PASS · happy-path 不应出现 FAIL_L*."""
    with gwt("T9 · 14 verdict 全 PASS"):
        gwt.given("audit 干净 · 14 verdict 队列就位")
        assert len(HAPPY_VERDICTS) == 14

        gwt.when("依次 emit 14 verdict_decided 事件 · 全 PASS")
        for vid, stage, signal in HAPPY_VERDICTS:
            emit_audit(
                "L1-02:verdict_decided",
                {
                    "verdict_id": f"v{vid:02d}",
                    "stage": stage,
                    "signal": signal,
                    "verdict": "PASS",
                },
            )

        gwt.then("14 verdict 全 PASS · 无 FAIL_L1/2/3/4")
        passed = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:verdict_decided",
            payload_contains={"verdict": "PASS"},
            min_count=14,
        )
        assert len(passed) == 14

        gwt.then("不应出任何 FAIL verdict (happy-path 铁律)")
        all_events = list_events(
            event_bus_root,
            project_id,
            type_exact="L1-02:verdict_decided",
        )
        fails = [
            e for e in all_events
            if "FAIL" in str(e.get("payload", {}).get("verdict", ""))
        ]
        assert fails == [], f"happy-path 不应出 FAIL · 实际={fails}"
