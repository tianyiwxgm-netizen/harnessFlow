"""IC-15 schema 级硬约束 · 4 TC.

覆盖:
- TC-1 · require_user_authorization=False 拒(硬编码 True)
- TC-2 · evidence.confirmation_count < 2 拒(L2-03 二次确认硬约束)
- TC-3 · evidence.observation_refs 空拒(必含 evidence)
- TC-4 · halt_id pattern 不匹配拒
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)


def test_require_user_authorization_must_be_true() -> None:
    """硬红线必须用户授权 · require_user_authorization=False 拒."""
    with pytest.raises(ValidationError, match="E_HALT_USER_AUTHORIZATION_MUST_BE_TRUE"):
        RequestHardHaltCommand(
            halt_id="halt-no-auth-needed",
            project_id="proj-ic15",
            red_line_id="HRL-01",
            evidence=HardHaltEvidence(
                observation_refs=("ev-1", "ev-2"),
                confirmation_count=2,
            ),
            require_user_authorization=False,  # 硬约束违反
            ts="2026-04-24T00:00:00Z",
        )


def test_confirmation_count_must_be_at_least_2() -> None:
    """L2-03 二次确认硬约束 · confirmation_count < 2 拒."""
    with pytest.raises(ValidationError):
        HardHaltEvidence(
            observation_refs=("ev-1",),
            confirmation_count=1,  # < 2 · ge=2 校
        )


def test_empty_observation_refs_rejected() -> None:
    """evidence.observation_refs 空 · pydantic min_length=1 拒."""
    with pytest.raises(ValidationError):
        HardHaltEvidence(
            observation_refs=(),
            confirmation_count=2,
        )


def test_halt_id_pattern_violation() -> None:
    """halt_id 不符 ^halt-[A-Za-z0-9_-]{3,} · pydantic 拒."""
    with pytest.raises(ValidationError):
        RequestHardHaltCommand(
            halt_id="bad-format",  # 不带 halt- 前缀
            project_id="proj-ic15",
            red_line_id="HRL-01",
            evidence=HardHaltEvidence(
                observation_refs=("ev-1", "ev-2"),
                confirmation_count=2,
            ),
            ts="2026-04-24T00:00:00Z",
        )
