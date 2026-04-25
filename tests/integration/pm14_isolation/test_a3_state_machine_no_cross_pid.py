"""A3 · L1-02 状态机 IC-01 不跨 pid · 3 TC.

PM-14: A 触发 wp 状态变迁 · 不应记录到 B 的状态机调用上.
StateTransitionSpy 记录每个 state_transition 调用 · 隔离断言对 pid 字段.
"""
from __future__ import annotations

import pytest

from tests.shared.ic_assertions import (
    assert_no_state_transition,
    assert_state_transition_to,
)
from tests.shared.stubs import StateTransitionSpy


class TestA3StateMachineNoCrossPid:
    """A3 · L1-02 IC-01 跨 pid 隔离 · 3 TC."""

    async def test_a3_01_pid_a_transition_does_not_record_for_pid_b(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A3.1: A 调 state_transition · spy.calls 仅 A 一条 · 用 pid filter B 应 0."""
        pid_a, pid_b = two_pids
        spy = StateTransitionSpy()
        await spy.state_transition(
            project_id=pid_a,
            wp_id="wp-001",
            new_wp_state="retry_s3",
            escalated=False,
            route_id="route-001",
        )
        # A 有一条
        assert_state_transition_to(
            spy.calls, wp_id="wp-001", new_wp_state="retry_s3",
            project_id=pid_a, min_count=1,
        )
        # B 应 0(用 pid filter)
        b_calls = [c for c in spy.calls if c.get("project_id") == pid_b]
        assert b_calls == [], f"PM-14 违反: pid_b 不应有任何 state_transition · 实际={b_calls}"

    async def test_a3_02_concurrent_a_b_transitions_isolated(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A3.2: A/B 同 wp_id 各调一次 · spy 记录两条 · 各 pid 自己看到自己."""
        pid_a, pid_b = two_pids
        spy = StateTransitionSpy()
        # A 与 B 用同 wp_id="wp-shared" · 但 pid 不同 = PM-14 切片下完全独立的 WP
        await spy.state_transition(
            project_id=pid_a, wp_id="wp-shared", new_wp_state="retry_s3",
            escalated=False, route_id="route-a",
        )
        await spy.state_transition(
            project_id=pid_b, wp_id="wp-shared", new_wp_state="upgrade_l1_01",
            escalated=True, route_id="route-b",
        )
        # 各分片各 1 条
        a_calls = [c for c in spy.calls if c.get("project_id") == pid_a]
        b_calls = [c for c in spy.calls if c.get("project_id") == pid_b]
        assert len(a_calls) == 1
        assert len(b_calls) == 1
        # A 看到 retry_s3 · B 看到 upgrade_l1_01 · 互不影响
        assert a_calls[0]["new_wp_state"] == "retry_s3"
        assert b_calls[0]["new_wp_state"] == "upgrade_l1_01"

    async def test_a3_03_no_transition_for_b_when_only_a_acts(
        self,
        two_pids: tuple[str, str],
    ) -> None:
        """A3.3: 只 A 调 5 次不同 wp · 用 pid filter 切到 B 应空 · 不串."""
        pid_a, pid_b = two_pids
        spy = StateTransitionSpy()
        for i in range(5):
            await spy.state_transition(
                project_id=pid_a, wp_id=f"wp-{i:03d}",
                new_wp_state="retry_s3",
                escalated=False, route_id=f"route-a-{i}",
            )
        b_calls = [c for c in spy.calls if c.get("project_id") == pid_b]
        # B 完全 0 条
        assert_no_state_transition(b_calls)
