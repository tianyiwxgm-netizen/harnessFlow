"""Scenario 01 · T1-T2 · happy-path init + S0→S1 推进.

T1: 干净 project init · pid 形式合法 · 全 fixture 干净
T2: S0→S1 charter 阶段切换 · IC-09 audit 落盘 · 无 BLOCK / panic
"""
from __future__ import annotations

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


def test_t1_clean_project_init(
    project_id: str,
    topo_manager: WBSTopologyManager,
    real_event_bus: EventBus,
    event_bus_root,
    gwt: GWT,
) -> None:
    """T1 · 干净 project init · 全部 fixture 干净 · 无任何事件."""
    with gwt("T1 · 干净 project init"):
        gwt.given(f"project_id={project_id} 合法 · L1-03 manager 干净")
        assert project_id == "proj-acc01-happy"
        assert topo_manager.project_id == project_id

        gwt.given("L1-09 EventBus 干净 · 无任何 events")
        n_events = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_events == 0

        gwt.then("无任何 BLOCK / panic / redline · 完全 clean state")
        # WBSTopologyManager 初态: topology=None · 无 wp_list · 不能 read_snapshot
        # 这正是 happy-path 起点
        assert topo_manager._topology is None  # noqa: SLF001 (test 内访问 internal)


def test_t2_s0_to_s1_charter_transition(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
) -> None:
    """T2 · S0→S1 charter_ready · IC-09 落盘 · happy-path stage 切换 1 步."""
    with gwt("T2 · S0→S1 charter_ready"):
        gwt.given("S0 init done · 无 charter")
        n_before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_before == 0

        gwt.when("用户提交 charter · L1-02 emit charter_ready 事件")
        emit_audit(
            "L1-02:gate_decision",
            {"stage": "S1", "decision": "pass", "signal": "charter_ready"},
        )

        gwt.then("IC-09 1 条 charter_ready · hash chain 完整")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision",
            payload_contains={"stage": "S1", "decision": "pass"},
        )
        assert len(events) == 1
        assert events[0]["payload"]["signal"] == "charter_ready"

        gwt.then("hash chain 完整 · 单条事件入账 seq=1")
        n_after = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_after == 1
