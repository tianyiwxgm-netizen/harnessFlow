"""FailureCounter · per wp_id 失败计数 · reset on DONE。

TC：
- 初始 · count=0 · state=ACTIVE
- 连续 fail 推进 RETRY_1 → RETRY_2 → RETRY_3 → ESCALATED
- DONE 事件 reset counter · 回 ACTIVE
- 多 wp_id 独立计数
"""
from __future__ import annotations

import pytest

from app.supervisor.escalator.counter import FailureCounter
from app.supervisor.escalator.schemas import (
    EscalationState,
    WpDoneEvent,
    WpFailEvent,
    WpFailLevel,
)


def _fail(wp_id: str = "wp-a", verdict: WpFailLevel = WpFailLevel.L1) -> WpFailEvent:
    return WpFailEvent(
        project_id="proj-a",
        wp_id=wp_id,
        verdict_level=verdict,
        verifier_report_id="rep-1",
        ts="t",
    )


def _done(wp_id: str = "wp-a") -> WpDoneEvent:
    return WpDoneEvent(project_id="proj-a", wp_id=wp_id, ts="t")


def test_counter_initial_state_active() -> None:
    c = FailureCounter()
    assert c.state_for("wp-a") == EscalationState.ACTIVE
    assert c.fail_count_for("wp-a") == 0


def test_counter_single_fail_to_retry_1() -> None:
    c = FailureCounter()
    c.record_fail(_fail())
    assert c.state_for("wp-a") == EscalationState.RETRY_1
    assert c.fail_count_for("wp-a") == 1


def test_counter_three_fails_progression() -> None:
    c = FailureCounter()
    c.record_fail(_fail())
    c.record_fail(_fail())
    c.record_fail(_fail())
    # 第 3 次 fail → RETRY_3（下次再 fail 才升级）
    assert c.state_for("wp-a") == EscalationState.RETRY_3
    assert c.fail_count_for("wp-a") == 3


def test_counter_three_fails_triggers_escalation() -> None:
    """主会话仲裁：同级连 ≥3 fail → 触发升级。
    5 态机设计：第 3 次 fail → state=RETRY_3 · should_escalate=True（发一次 IC-14）。
    """
    c = FailureCounter()
    c.record_fail(_fail())  # count=1 · RETRY_1
    c.record_fail(_fail())  # count=2 · RETRY_2
    decision = c.record_fail(_fail())  # count=3 · RETRY_3 · should_escalate=True
    assert decision.should_escalate is True
    assert c.state_for("wp-a") == EscalationState.RETRY_3
    assert decision.fail_count == 3


def test_counter_fourth_fail_is_deduped() -> None:
    """已 escalate 过的 wp 再次 fail · dedup_hit=true · 不重复升级。"""
    c = FailureCounter()
    for _ in range(3):
        c.record_fail(_fail())
    # 第 4 次 fail
    decision = c.record_fail(_fail())
    assert decision.dedup_hit is True
    assert decision.should_escalate is False  # 不重复发 IC-14


def test_counter_done_resets_to_active() -> None:
    c = FailureCounter()
    c.record_fail(_fail())
    c.record_fail(_fail())
    c.record_done(_done())
    assert c.state_for("wp-a") == EscalationState.ACTIVE
    assert c.fail_count_for("wp-a") == 0


def test_counter_done_resets_even_after_escalated() -> None:
    """已升级的 wp 如果 DONE（ex: 手动 fix 后成功）· 也 reset。dedup set 清空 · 允许下次重新升级。"""
    c = FailureCounter()
    for _ in range(3):
        c.record_fail(_fail())
    c.record_done(_done())
    assert c.state_for("wp-a") == EscalationState.ACTIVE
    assert c.fail_count_for("wp-a") == 0
    # 再次 3 fail 应能再次触发升级
    c.record_fail(_fail())
    c.record_fail(_fail())
    decision = c.record_fail(_fail())
    assert decision.should_escalate is True  # 不被 dedup


def test_counter_multiple_wps_independent() -> None:
    c = FailureCounter()
    c.record_fail(_fail(wp_id="wp-a"))
    c.record_fail(_fail(wp_id="wp-b"))
    c.record_fail(_fail(wp_id="wp-a"))
    assert c.fail_count_for("wp-a") == 2
    assert c.fail_count_for("wp-b") == 1
    assert c.state_for("wp-a") == EscalationState.RETRY_2
    assert c.state_for("wp-b") == EscalationState.RETRY_1


def test_counter_done_on_other_wp_does_not_reset() -> None:
    c = FailureCounter()
    c.record_fail(_fail(wp_id="wp-a"))
    c.record_fail(_fail(wp_id="wp-b"))
    c.record_done(_done(wp_id="wp-a"))
    assert c.state_for("wp-a") == EscalationState.ACTIVE
    assert c.state_for("wp-b") == EscalationState.RETRY_1  # 保持


def test_counter_done_on_unknown_wp_noop() -> None:
    c = FailureCounter()
    # 从未 fail 的 wp · DONE 应无异常
    c.record_done(_done(wp_id="wp-never"))
    assert c.state_for("wp-never") == EscalationState.ACTIVE


def test_counter_fail_after_done_starts_fresh() -> None:
    """DONE 后再 fail · 从 RETRY_1 起算（不保留历史）。"""
    c = FailureCounter()
    c.record_fail(_fail())
    c.record_done(_done())
    c.record_fail(_fail())
    assert c.state_for("wp-a") == EscalationState.RETRY_1
    assert c.fail_count_for("wp-a") == 1
