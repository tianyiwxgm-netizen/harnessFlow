"""IC-13 负向 / PM-14 / 严禁升格 · 4 TC.

覆盖:
- TC-1 · level=BLOCK 在 schema 层就被拒(走 IC-15 不走 IC-13)
- TC-2 · 跨 pid push · E_SUGG_CROSS_PROJECT
- TC-3 · content < 10 字符拒(质量门槛)
- TC-4 · observation_refs 空拒(必含 evidence)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.supervisor.event_sender.schemas import (
    PushSuggestionCommand,
    SuggestionLevel,
)
from app.supervisor.event_sender.suggestion_pusher import SuggestionPusher


async def test_block_level_rejected_by_schema(make_suggestion_command) -> None:
    """level=BLOCK 在 enum 层就不允许构造 · 走 IC-15 不走 IC-13."""
    # SuggestionLevel 枚举 INFO/SUGG/WARN · 没 BLOCK
    assert "BLOCK" not in [e.value for e in SuggestionLevel]
    # 用字面量传 BLOCK · pydantic 拒
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-block-attempt",
            project_id="proj-ic13",
            level="BLOCK",  # type: ignore[arg-type]
            content="试图升格 BLOCK 应被拒",
            observation_refs=("ev-1",),
            ts="2026-04-24T00:00:00Z",
        )


async def test_cross_project_push_rejected(
    pusher: SuggestionPusher,
    make_suggestion_command,
    other_project_id: str,
) -> None:
    """跨 project push · E_SUGG_CROSS_PROJECT(主会话仲裁)."""
    bad_cmd = make_suggestion_command(
        suggestion_id="sugg-cross-pid",
        sdp_id="SDP-01",
        content="跨 pid push · 应被拒",
        pid_override=other_project_id,
    )
    with pytest.raises(ValueError, match="E_SUGG_CROSS_PROJECT"):
        await pusher.push_suggestion(bad_cmd)


def test_short_content_rejected_by_schema() -> None:
    """content < 10 字 · pydantic min_length=10 拒."""
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-short",
            project_id="proj-ic13",
            level=SuggestionLevel.INFO,
            content="too short",  # < 10 chars
            observation_refs=("ev-1",),
            ts="2026-04-24T00:00:00Z",
        )


def test_empty_observation_refs_rejected_by_schema() -> None:
    """observation_refs 空 · pydantic min_length=1 拒(必含 evidence)."""
    with pytest.raises(ValidationError):
        PushSuggestionCommand(
            suggestion_id="sugg-no-evidence",
            project_id="proj-ic13",
            level=SuggestionLevel.WARN,
            content="完整内容但缺 evidence · 应被拒",
            observation_refs=(),  # 空
            ts="2026-04-24T00:00:00Z",
        )
