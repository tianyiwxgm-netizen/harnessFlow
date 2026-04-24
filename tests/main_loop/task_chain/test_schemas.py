"""WP05 · TaskChainState / RouteDecision / TaskChainResult schema 用例.

覆盖:
    - RouteDecision 不可变 · 必填字段
    - TaskStatus 枚举 · TERMINAL 子集
    - TaskChainState register / mark_status / get_status / active_tasks
    - TaskChainResult accepted=true / false 两态
"""
from __future__ import annotations

import dataclasses

import pytest

from app.main_loop.task_chain.schemas import (
    ROUTABLE_DECISION_TYPES,
    TERMINAL_STATUSES,
    RouteDecision,
    TaskChainResult,
    TaskChainState,
    TaskStatus,
)


class TestRoutableDecisionTypes:
    """ROUTABLE_DECISION_TYPES 白名单."""

    def test_TC_WP05_S01_whitelist_contains_4_types(self) -> None:
        """4 类 decision_type 均在白名单."""
        assert ROUTABLE_DECISION_TYPES == frozenset({
            "state_transition",
            "get_next_wp",
            "assign_wp",
            "invoke_skill",
        })

    def test_TC_WP05_S02_whitelist_immutable(self) -> None:
        """frozenset · 不可修改."""
        with pytest.raises(AttributeError):
            ROUTABLE_DECISION_TYPES.add("no_op")  # type: ignore[attr-defined]


class TestTaskStatus:
    """TaskStatus 枚举 + TERMINAL 子集."""

    def test_TC_WP05_S03_five_statuses_defined(self) -> None:
        """PENDING / RUNNING / COMPLETED / FAILED / CANCELED 5 态."""
        values = {s.value for s in TaskStatus}
        assert values == {"PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELED"}

    def test_TC_WP05_S04_terminal_statuses_subset(self) -> None:
        """TERMINAL = COMPLETED | FAILED | CANCELED."""
        assert TERMINAL_STATUSES == frozenset({
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELED,
        })

    def test_TC_WP05_S05_pending_not_terminal(self) -> None:
        """PENDING / RUNNING 不在 TERMINAL."""
        assert TaskStatus.PENDING not in TERMINAL_STATUSES
        assert TaskStatus.RUNNING not in TERMINAL_STATUSES


class TestRouteDecision:
    """RouteDecision 不可变 dataclass."""

    def test_TC_WP05_S06_route_decision_frozen(self) -> None:
        """frozen=True · 写字段抛 FrozenInstanceError."""
        rd = RouteDecision(
            decision_type="invoke_skill",
            target_l1="L1-05",
            ic_code="IC-04",
            ic_payload={"capability": "dod.lint"},
            project_id="pid-001",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            rd.target_l1 = "L1-03"  # type: ignore[misc]

    def test_TC_WP05_S07_route_decision_default_wp_decision_id(self) -> None:
        """wp_id / decision_id 默认 None."""
        rd = RouteDecision(
            decision_type="state_transition",
            target_l1="L1-02",
            ic_code="IC-01",
            ic_payload={},
            project_id="pid-002",
        )
        assert rd.wp_id is None
        assert rd.decision_id is None


class TestTaskChainState:
    """TaskChainState 可变聚合根."""

    def test_TC_WP05_S10_register_task(self) -> None:
        """register() 登记 task_id 到 tasks 字典."""
        state = TaskChainState(project_id="pid-010")
        state.register(
            task_id="task-001",
            status=TaskStatus.PENDING,
            wp_id="wp-01",
            decision_type="assign_wp",
        )
        assert state.tasks["task-001"]["status"] == TaskStatus.PENDING
        assert state.tasks["task-001"]["wp_id"] == "wp-01"
        assert state.tasks["task-001"]["decision_type"] == "assign_wp"

    def test_TC_WP05_S11_register_idempotent_overrides(self) -> None:
        """同 task_id 再 register · 覆盖 status (幂等)."""
        state = TaskChainState(project_id="pid-011")
        state.register(
            task_id="task-001", status=TaskStatus.PENDING,
            wp_id=None, decision_type="state_transition",
        )
        state.register(
            task_id="task-001", status=TaskStatus.RUNNING,
            wp_id=None, decision_type="state_transition",
        )
        assert state.tasks["task-001"]["status"] == TaskStatus.RUNNING

    def test_TC_WP05_S12_mark_status_updates(self) -> None:
        """mark_status 更新 task 状态."""
        state = TaskChainState(project_id="pid-012")
        state.register(
            task_id="t1", status=TaskStatus.PENDING,
            wp_id=None, decision_type="invoke_skill",
        )
        state.mark_status("t1", TaskStatus.COMPLETED)
        assert state.get_status("t1") == TaskStatus.COMPLETED

    def test_TC_WP05_S13_mark_status_unknown_raises(self) -> None:
        """mark_status 未登记 task → KeyError."""
        state = TaskChainState(project_id="pid-013")
        with pytest.raises(KeyError):
            state.mark_status("ghost", TaskStatus.FAILED)

    def test_TC_WP05_S14_get_status_missing_returns_none(self) -> None:
        """get_status 未登记 task → None (不抛)."""
        state = TaskChainState(project_id="pid-014")
        assert state.get_status("nothere") is None

    def test_TC_WP05_S15_active_tasks_excludes_terminal(self) -> None:
        """active_tasks 不含 COMPLETED / FAILED / CANCELED."""
        state = TaskChainState(project_id="pid-015")
        for tid, status in [
            ("t1", TaskStatus.PENDING),
            ("t2", TaskStatus.RUNNING),
            ("t3", TaskStatus.COMPLETED),
            ("t4", TaskStatus.FAILED),
            ("t5", TaskStatus.CANCELED),
        ]:
            state.register(
                task_id=tid, status=status,
                wp_id=None, decision_type="invoke_skill",
            )
        active = set(state.active_tasks())
        assert active == {"t1", "t2"}

    def test_TC_WP05_S16_counters_default_zero(self) -> None:
        """consecutive_failures / total_* 默认 0."""
        state = TaskChainState(project_id="pid-016")
        assert state.consecutive_failures == 0
        assert state.total_dispatched == 0
        assert state.total_completed == 0
        assert state.total_failed == 0


class TestTaskChainResult:
    """TaskChainResult 不可变产出."""

    def test_TC_WP05_S20_accepted_true_carries_task_id_and_route(self) -> None:
        """accepted=true · 必带 task_id + route."""
        rd = RouteDecision(
            decision_type="invoke_skill",
            target_l1="L1-05",
            ic_code="IC-04",
            ic_payload={},
            project_id="pid-020",
        )
        r = TaskChainResult(accepted=True, task_id="t-020", route=rd)
        assert r.accepted is True
        assert r.task_id == "t-020"
        assert r.route == rd
        assert r.rejection_reason is None

    def test_TC_WP05_S21_accepted_false_carries_reason(self) -> None:
        """accepted=false · rejection_reason 必填 (语义约束 · schema 不强校)."""
        r = TaskChainResult(
            accepted=False, rejection_reason="E_CHAIN_NO_PROJECT_ID",
        )
        assert r.accepted is False
        assert r.rejection_reason == "E_CHAIN_NO_PROJECT_ID"
        assert r.task_id is None
        assert r.route is None

    def test_TC_WP05_S22_result_frozen(self) -> None:
        """result frozen=True."""
        r = TaskChainResult(accepted=False, rejection_reason="E_X")
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.accepted = True  # type: ignore[misc]
