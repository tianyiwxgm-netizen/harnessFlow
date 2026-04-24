"""L1-01 L2-02 Decision Engine · pytest fixtures.

单一来源 mock · 所有测试复用:
    - mock_project_id
    - make_candidate / make_context / make_history_entry / make_kb_snippet
"""
from __future__ import annotations

from typing import Any

import pytest

from app.main_loop.decision_engine.schemas import (
    Candidate,
    DecisionContext,
    HistoryEntry,
    KBSnippet,
)

MOCK_PID = "pid-018f4a3b-0000-7000-8b2a-9d5e1c8f3a20"


@pytest.fixture
def mock_project_id() -> str:
    return MOCK_PID


@pytest.fixture
def make_candidate():
    def _make(
        decision_type: str = "invoke_skill",
        decision_params: dict[str, Any] | None = None,
        base_score: float = 0.5,
        guard_expr: str = "",
        reason: str = "test candidate reason long enough",
        kb_tags: tuple[str, ...] = (),
    ) -> Candidate:
        return Candidate(
            decision_type=decision_type,
            decision_params=dict(decision_params) if decision_params else {},
            base_score=base_score,
            guard_expr=guard_expr,
            reason=reason,
            kb_tags=kb_tags,
        )
    return _make


@pytest.fixture
def make_context(mock_project_id):
    def _make(
        project_id: str | None = None,
        state: str = "S4_execute",
        history: tuple[HistoryEntry, ...] = (),
        kb_enabled: bool = True,
        kb_snippets: tuple[KBSnippet, ...] = (),
        guard_vars: dict[str, Any] | None = None,
        fallback_candidate: Candidate | None = None,
        tick_id: str = "tick-018f4a3b-7c1e-7000-8b2a-9d5e1c8f3a20",
    ) -> DecisionContext:
        return DecisionContext(
            project_id=project_id if project_id is not None else mock_project_id,
            tick_id=tick_id,
            state=state,
            history=history,
            kb_enabled=kb_enabled,
            kb_snippets=kb_snippets,
            guard_vars=dict(guard_vars) if guard_vars else {},
            fallback_candidate=fallback_candidate,
        )
    return _make


@pytest.fixture
def make_history_entry():
    def _make(
        decision_type: str = "invoke_skill",
        outcome: str = "success",
        tick_delta: int = 1,
        params_fingerprint: str = "",
    ) -> HistoryEntry:
        return HistoryEntry(
            decision_type=decision_type,
            outcome=outcome,
            tick_delta=tick_delta,
            params_fingerprint=params_fingerprint,
        )
    return _make


@pytest.fixture
def make_kb_snippet():
    def _make(
        kind: str = "pattern",
        tags: tuple[str, ...] = (),
        rerank_score: float = 0.0,
        observed_count: int = 1,
    ) -> KBSnippet:
        return KBSnippet(
            kind=kind,
            tags=tags,
            rerank_score=rerank_score,
            observed_count=observed_count,
        )
    return _make
