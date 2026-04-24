"""event_sender/schemas · IC-13/14/15 payload schema 契约校验。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.supervisor.event_sender.schemas import (
    FailVerdict,
    HardHaltEvidence,
    HardHaltState,
    NewWpState,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    PushSuggestionAck,
    PushSuggestionCommand,
    RequestHardHaltAck,
    RequestHardHaltCommand,
    RouteEvidence,
    SuggestionLevel,
    SuggestionPriority,
    TargetStage,
)


# ---------------- IC-13 PushSuggestionCommand ----------------


def test_sugg_command_valid_minimal() -> None:
    cmd = PushSuggestionCommand(
        suggestion_id="sugg-abcdef01",
        project_id="proj-a",
        level=SuggestionLevel.INFO,
        content="context 80% 建议压缩",
        observation_refs=("ev-1",),
        ts="2026-04-23T10:00:00Z",
    )
    assert cmd.priority == SuggestionPriority.P2
    assert cmd.level == SuggestionLevel.INFO


def test_sugg_command_rejects_empty_project_id() -> None:
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-abcdef01",
            project_id="",
            level=SuggestionLevel.INFO,
            content="abcdefghij",
            observation_refs=("ev-1",),
            ts="2026-04-23",
        )


def test_sugg_command_rejects_short_content() -> None:
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-abcdef01",
            project_id="p",
            level=SuggestionLevel.INFO,
            content="short",
            observation_refs=("ev-1",),
            ts="t",
        )


def test_sugg_command_rejects_empty_observation_refs() -> None:
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-abcdef01",
            project_id="p",
            level=SuggestionLevel.INFO,
            content="abcdefghij",
            observation_refs=(),
            ts="t",
        )


def test_sugg_level_is_3_only() -> None:
    # BLOCK is not in enum
    assert {s.value for s in SuggestionLevel} == {"INFO", "SUGG", "WARN"}


# ---------------- IC-14 PushRollbackRouteCommand ----------------


def test_route_command_valid() -> None:
    cmd = PushRollbackRouteCommand(
        route_id="route-abcdef01",
        project_id="p",
        wp_id="wp-abcdef01",
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.S4,
        level_count=1,
        evidence=RouteEvidence(verifier_report_id="rep-1"),
        ts="t",
    )
    assert cmd.verdict == FailVerdict.FAIL_L2


def test_route_command_level_count_min_1() -> None:
    with pytest.raises(ValidationError):
        PushRollbackRouteCommand(
            route_id="route-abcdef01",
            project_id="p",
            wp_id="wp-abcdef01",
            verdict=FailVerdict.FAIL_L2,
            target_stage=TargetStage.S4,
            level_count=0,
            evidence=RouteEvidence(verifier_report_id="rep-1"),
            ts="t",
        )


def test_route_ack_escalated_default_false() -> None:
    ack = PushRollbackRouteAck(
        route_id="route-abcdef01",
        applied=True,
        new_wp_state=NewWpState.RETRY_S4,
        ts="t",
    )
    assert ack.escalated is False


# ---------------- IC-15 RequestHardHaltCommand ----------------


def test_halt_command_valid() -> None:
    cmd = RequestHardHaltCommand(
        halt_id="halt-abcdef01",
        project_id="p",
        red_line_id="redline-rm-rf-system",
        evidence=HardHaltEvidence(
            observation_refs=("obs-1",),
            confirmation_count=2,
        ),
        ts="t",
    )
    assert cmd.require_user_authorization is True


def test_halt_command_rejects_confirmation_lt_2() -> None:
    with pytest.raises(ValidationError):
        HardHaltEvidence(observation_refs=("obs-1",), confirmation_count=1)


def test_halt_command_rejects_empty_observation_refs() -> None:
    with pytest.raises(ValidationError):
        HardHaltEvidence(observation_refs=(), confirmation_count=2)


def test_halt_command_rejects_user_auth_false() -> None:
    with pytest.raises(ValidationError):
        RequestHardHaltCommand(
            halt_id="halt-abcdef01",
            project_id="p",
            red_line_id="r",
            evidence=HardHaltEvidence(
                observation_refs=("o",), confirmation_count=2
            ),
            require_user_authorization=False,
            ts="t",
        )


def test_halt_ack_state_after_always_halted() -> None:
    ack = RequestHardHaltAck(
        halt_id="halt-abcdef01",
        halted=True,
        halt_latency_ms=50,
        state_before=HardHaltState.RUNNING,
        audit_entry_id="audit-1",
    )
    assert ack.state_after == HardHaltState.HALTED
