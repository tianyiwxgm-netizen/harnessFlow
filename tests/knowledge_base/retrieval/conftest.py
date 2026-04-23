"""L1-06 L2-05 test fixtures · override parent L2-01 fixtures in this subtree only."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.retrieval.service import RerankService


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l205"


@pytest.fixture
def mock_l2_02() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l2_03() -> MagicMock:
    m = MagicMock()
    m.provide_candidate_snapshot.return_value = MagicMock(count=0, candidates=[])
    return m


@pytest.fixture
def mock_l1_01() -> MagicMock:
    m = MagicMock()
    m.push_context.return_value = MagicMock(
        accepted=True, context_id="ctx", rejection_reason=None
    )
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_strategy_repo() -> MagicMock:
    m = MagicMock()

    def _get(stage: str) -> dict[str, Any]:
        if stage == "S3":
            return {
                "injected_kinds": ["anti_pattern"],
                "recall_top_k": 20,
                "rerank_top_k": 5,
            }
        return {"injected_kinds": [], "recall_top_k": 0, "rerank_top_k": 0}

    m.get.side_effect = _get
    return m


@pytest.fixture
def sut(
    mock_l2_02: MagicMock,
    mock_l2_03: MagicMock,
    mock_l1_01: MagicMock,
    mock_audit: MagicMock,
    mock_strategy_repo: MagicMock,
    mock_project_id: str,
) -> RerankService:
    return RerankService(
        l2_02=mock_l2_02,
        l2_03=mock_l2_03,
        l1_01=mock_l1_01,
        audit=mock_audit,
        strategy_repo=mock_strategy_repo,
        project_id=mock_project_id,
    )


@pytest.fixture
def make_candidates():
    """Factory for CandidateSummary mocks with configurable fields."""

    def _make(
        count: int,
        project_override: str | None = None,
    ) -> list[Any]:
        from app.knowledge_base.retrieval.schemas import CandidateSummary

        result: list[CandidateSummary] = []
        for i in range(count):
            # entry_summary uses MagicMock (spec-free) so tests that assign
            # `.title = "TAMPERED"` work and tamper detection is exercised by
            # snapshotting the title at candidate construction time.
            es = MagicMock()
            es.title = f"entry-{i}"
            ac = MagicMock()
            ac.stages = ["S3", "S4"]
            ac.task_types = ["coding"]
            ac.tech_stacks = ["python", "fastapi"]
            es.applicable_context = ac
            es.observed_count = i + 1
            es.last_observed_at = "2026-04-20T00:00:00Z"
            c = CandidateSummary(
                entry_id=f"kbe-{i:06d}",
                scope="project" if i % 2 else "session",
                kind="anti_pattern" if i % 3 == 0 else "pattern",
                entry_summary=es,
                project_id=project_override or "hf-proj-l205",
            )
            # Snapshot the canonical title at build time so service can detect
            # in-flight tampering (E_L205_IC04_ENTRY_FIELD_TAMPERED).
            c.__dict__["_canonical_title"] = es.title
            result.append(c)
        return result

    return _make
