"""Scenario 01 · T3-T7 · happy-path 每阶段顺利切换 (S2/S3/S4/S5/S6).

T3: S1→S2 plan + 4 件套 + 9 计划
T4: S2→S3 tdd_blueprint_ready
T5: S3→S4 wbs_ready · WP 派单
T6: S4→S5 verifier_pass
T7: S5→S6 delivery_bundled
"""
from __future__ import annotations

import pytest

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


# 5 stage 切换的 (test_id, payload_signal, payload_extra) 表
STAGE_CASES = [
    ("T3", "S2", "4_pieces_ready", {"plan_count": 9, "togaf_phase": "D"}),
    ("T4", "S3", "tdd_blueprint_ready", {"blueprint_id": "tdd-bp-1"}),
    ("T5", "S4", "wbs_ready", {"wp_count": 5, "topology_id": "topo-x1"}),
    ("T6", "S5", "verifier_pass", {"wp_id": "wp-1", "verdict": "PASS"}),
    ("T7", "S6", "delivery_bundled", {"bundle_path": "/delivery/v1"}),
]


@pytest.mark.parametrize("tid,stage,signal,extra", STAGE_CASES)
def test_t3_t7_stage_transition_happy(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
    tid: str,
    stage: str,
    signal: str,
    extra: dict,
) -> None:
    """T3-T7 · 每阶段 happy-path 切换 · IC-09 落盘 · 无 BLOCK."""
    with gwt(f"{tid} · {stage} · {signal} happy-path"):
        gwt.given(f"前序阶段已完成 · audit 干净起点")

        gwt.when(f"L1-02 emit {signal} · gate decision pass")
        payload = {"stage": stage, "decision": "pass", "signal": signal, **extra}
        emit_audit("L1-02:gate_decision", payload)

        gwt.then(f"IC-09 {stage} {signal} 落盘 · payload 含 stage 字段")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision",
            payload_contains={"stage": stage, "signal": signal},
        )
        assert len(events) == 1, f"{tid} · {stage} {signal} 未落盘"
        for k, v in extra.items():
            assert events[0]["payload"][k] == v

        gwt.then("hash chain 完整 · 1 条事件 seq=1")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 1
