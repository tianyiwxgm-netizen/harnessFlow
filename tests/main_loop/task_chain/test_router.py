"""WP05 · task_chain.router.route_decision() 用例.

覆盖:
    正向 4 decision_type (state_transition / get_next_wp / assign_wp / invoke_skill)
    负向 4 错误码 (NO_PROJECT / CROSS_PROJECT / ACTION_UNSUPPORTED / DEF_INVALID)
    边界: 默认值 / 可选 wp_id / payload 透传.
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.schemas import ChosenAction
from app.main_loop.task_chain.router import (
    DECISION_TYPE_TO_TARGET,
    E_CHAIN_ACTION_UNSUPPORTED,
    E_CHAIN_CROSS_PROJECT,
    E_CHAIN_DEF_INVALID,
    E_CHAIN_NO_PROJECT_ID,
    RouterError,
    route_decision,
)


def _mk_action(
    dt: str,
    params: dict | None = None,
    *,
    base_score: float = 0.7,
) -> ChosenAction:
    """小工具:构造最简 ChosenAction."""
    return ChosenAction(
        decision_type=dt,
        decision_params=params or {},
        final_score=base_score,
        kb_boost=0.0,
        history_weight=0.0,
        base_score=base_score,
        reason="unit-test synthesized chosen action for router",
    )


class TestRouteDecisionPositive:
    """4 decision_type 各一条正向."""

    def test_TC_WP05_R01_state_transition_ic01(self) -> None:
        """state_transition → L1-02 IC-01 (Dev-δ)."""
        action = _mk_action(
            "state_transition",
            {
                "from_state": "S1_plan",
                "to_state": "S2_impl",
                "reason": "plan done · enter impl",
                "trigger_tick": "tick-001",
                "evidence_refs": ["ev-1", "ev-2"],
                "gate_id": "gate-s1s2-0",
            },
        )
        rd = route_decision(action, project_id="pid-100", decision_id="dec-1")
        assert rd.target_l1 == "L1-02"
        assert rd.ic_code == "IC-01"
        assert rd.project_id == "pid-100"
        assert rd.decision_id == "dec-1"
        assert rd.ic_payload["to_state"] == "S2_impl"
        assert rd.ic_payload["from_state"] == "S1_plan"
        assert rd.ic_payload["evidence_refs"] == ("ev-1", "ev-2")

    def test_TC_WP05_R02_get_next_wp_ic02(self) -> None:
        """get_next_wp → L1-03 IC-02 (Dev-ε)."""
        action = _mk_action(
            "get_next_wp",
            {
                "query_id": "q-1",
                "requester_tick": "tick-002",
                "topology_id": "topo-x",
            },
        )
        rd = route_decision(action, project_id="pid-101")
        assert rd.target_l1 == "L1-03"
        assert rd.ic_code == "IC-02"
        assert rd.ic_payload["project_id"] == "pid-101"
        assert rd.ic_payload["query_id"] == "q-1"
        assert rd.wp_id is None  # get_next_wp 不带 wp_id

    def test_TC_WP05_R03_assign_wp_ic03(self) -> None:
        """assign_wp → L1-03 IC-03 (Dev-ε) · wp_id 必填."""
        action = _mk_action(
            "assign_wp",
            {
                "wp_id": "wp-42",
                "assignee": "AgentA",
                "assigner_tick": "tick-003",
            },
        )
        rd = route_decision(action, project_id="pid-102")
        assert rd.target_l1 == "L1-03"
        assert rd.ic_code == "IC-03"
        assert rd.wp_id == "wp-42"
        assert rd.ic_payload["wp_id"] == "wp-42"

    def test_TC_WP05_R04_invoke_skill_ic04(self) -> None:
        """invoke_skill → L1-05 IC-04 (Dev-γ)."""
        action = _mk_action(
            "invoke_skill",
            {
                "invocation_id": "inv-1",
                "capability": "dod.lint",
                "params": {"path": "app/"},
                "caller_l1": "L1-01",
                "context": {"project_id": "pid-103"},
                "timeout_ms": 15000,
            },
        )
        rd = route_decision(action, project_id="pid-103")
        assert rd.target_l1 == "L1-05"
        assert rd.ic_code == "IC-04"
        assert rd.ic_payload["capability"] == "dod.lint"
        assert rd.ic_payload["timeout_ms"] == 15000


class TestRouteDecisionNegative:
    """4 E_CHAIN_* 错误码."""

    def test_TC_WP05_R10_no_project_id_raises(self) -> None:
        """project_id 空 → E_CHAIN_NO_PROJECT_ID."""
        action = _mk_action("invoke_skill", {"capability": "x.y"})
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="")
        assert exc_info.value.code == E_CHAIN_NO_PROJECT_ID

    def test_TC_WP05_R11_cross_project_raises(self) -> None:
        """params.project_id ≠ ctx.project_id → E_CHAIN_CROSS_PROJECT."""
        action = _mk_action(
            "invoke_skill",
            {"capability": "x.y", "project_id": "pid-A"},
        )
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="pid-B")
        assert exc_info.value.code == E_CHAIN_CROSS_PROJECT

    def test_TC_WP05_R12_action_unsupported_raises(self) -> None:
        """decision_type 不在 ROUTABLE 白名单 → E_CHAIN_ACTION_UNSUPPORTED."""
        action = _mk_action("no_op", {})  # no_op 不在 WP05 路由白名单
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="pid-C")
        assert exc_info.value.code == E_CHAIN_ACTION_UNSUPPORTED

    def test_TC_WP05_R13_state_transition_missing_to_state(self) -> None:
        """state_transition 无 to_state → E_CHAIN_DEF_INVALID."""
        action = _mk_action("state_transition", {"from_state": "S1_plan"})
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="pid-D")
        assert exc_info.value.code == E_CHAIN_DEF_INVALID

    def test_TC_WP05_R14_assign_wp_missing_wp_id(self) -> None:
        """assign_wp 无 wp_id → E_CHAIN_DEF_INVALID."""
        action = _mk_action("assign_wp", {"assignee": "AgentB"})
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="pid-E")
        assert exc_info.value.code == E_CHAIN_DEF_INVALID

    def test_TC_WP05_R15_invoke_skill_missing_capability(self) -> None:
        """invoke_skill 无 capability → E_CHAIN_DEF_INVALID."""
        action = _mk_action("invoke_skill", {"params": {}})
        with pytest.raises(RouterError) as exc_info:
            route_decision(action, project_id="pid-F")
        assert exc_info.value.code == E_CHAIN_DEF_INVALID


class TestRouteDecisionEdge:
    """边界 / 默认值."""

    def test_TC_WP05_R20_decision_type_to_target_4_entries(self) -> None:
        """DECISION_TYPE_TO_TARGET 覆盖 4 类 decision_type."""
        assert set(DECISION_TYPE_TO_TARGET.keys()) == {
            "state_transition", "get_next_wp", "assign_wp", "invoke_skill",
        }

    def test_TC_WP05_R21_default_invoke_skill_timeout(self) -> None:
        """invoke_skill 无 timeout_ms → 默认 30000."""
        action = _mk_action("invoke_skill", {"capability": "x.y"})
        rd = route_decision(action, project_id="pid-G")
        assert rd.ic_payload["timeout_ms"] == 30000
        assert rd.ic_payload["allow_fallback"] is True

    def test_TC_WP05_R22_state_transition_from_none_ok(self) -> None:
        """state_transition · from_state 允许 None (首次 S0)."""
        action = _mk_action(
            "state_transition",
            {"to_state": "S1_plan", "reason": "bootstrap"},
        )
        rd = route_decision(action, project_id="pid-H")
        assert rd.ic_payload["from_state"] is None
        assert rd.ic_payload["to_state"] == "S1_plan"
