"""TC-WP06-SCHEMAS · 3 inbox envelope 基本构造 + ack 字段约束。

覆盖：
- TC-WP06-001 · `SuggestionInbox.from_command` 派生 level=WARN
- TC-WP06-002 · `SuggestionInbox.from_command` 派生 level=INFO / SUGG
- TC-WP06-003 · `RollbackInbox.from_command` wrap · received_at_ms 透传
- TC-WP06-004 · `HaltSignal.from_command` wrap · confirmation_count 透传
- TC-WP06-005 · `HaltAck` · slo_violated=true when latency>100
"""
from __future__ import annotations

from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltAck,
    HaltState,
    SuggestionInbox,
)
from app.supervisor.event_sender.schemas import SuggestionLevel


def test_TC_WP06_001_suggestion_inbox_warn_derives_level(
    make_suggestion_cmd,
) -> None:
    """TC-WP06-001 · WARN 级 Dev-ζ command → AdviceLevel.WARN."""
    cmd = make_suggestion_cmd(level=SuggestionLevel.WARN)
    inbox = SuggestionInbox.from_command(cmd, received_at_ms=123)
    assert inbox.level == AdviceLevel.WARN
    assert inbox.command is cmd
    assert inbox.received_at_ms == 123


def test_TC_WP06_002_suggestion_inbox_info_and_sugg_levels(
    make_suggestion_cmd,
) -> None:
    """TC-WP06-002 · INFO / SUGG 两级均正确派生。"""
    cmd_info = make_suggestion_cmd(level=SuggestionLevel.INFO)
    cmd_sugg = make_suggestion_cmd(level=SuggestionLevel.SUGG)
    inbox_info = SuggestionInbox.from_command(cmd_info, received_at_ms=0)
    inbox_sugg = SuggestionInbox.from_command(cmd_sugg, received_at_ms=0)
    assert inbox_info.level == AdviceLevel.INFO
    assert inbox_sugg.level == AdviceLevel.SUGG


def test_TC_WP06_003_rollback_inbox_wraps_command(make_rollback_inbox) -> None:
    """TC-WP06-003 · RollbackInbox 透传 Dev-ζ PushRollbackRouteCommand 字段。"""
    inbox = make_rollback_inbox(received_at_ms=456, wp_id="wp-wrap-001")
    assert inbox.received_at_ms == 456
    assert inbox.command.wp_id == "wp-wrap-001"


def test_TC_WP06_004_halt_signal_wraps_command(make_halt_signal) -> None:
    """TC-WP06-004 · HaltSignal 透传 Dev-ζ RequestHardHaltCommand · confirmation 保留。"""
    sig = make_halt_signal(received_at_ms=789, red_line_id="redline-wrap-001")
    assert sig.received_at_ms == 789
    assert sig.command.red_line_id == "redline-wrap-001"
    assert sig.command.evidence.confirmation_count == 2


def test_TC_WP06_005_halt_ack_slo_violated_flag(
) -> None:
    """TC-WP06-005 · HaltAck.slo_violated 可独立传 true（latency_ms > 100 时调用侧自觉标）。"""
    ack_ok = HaltAck(
        halt_id="halt-001",
        halted=True,
        latency_ms=50,
        state_before=HaltState.RUNNING,
    )
    ack_slo = HaltAck(
        halt_id="halt-002",
        halted=True,
        latency_ms=120,
        state_before=HaltState.RUNNING,
        slo_violated=True,
    )
    assert ack_ok.slo_violated is False
    assert ack_slo.slo_violated is True
