"""L1-06 L2-02 test fixtures · adapted from 3-2 §7."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.reader.schemas import (
    ApplicableContext,
    KBEntry,
    RerankResponse,
)
from app.knowledge_base.reader.service import KBReadService

_PID = "hf-proj-l202"
_SID = "hf-sess-l202"


@pytest.fixture
def mock_project_id() -> str:
    return _PID


@pytest.fixture
def mock_session_id() -> str:
    return _SID


@pytest.fixture
def mock_l2_01() -> MagicMock:
    """IC-L2-01 scope_check · default allows all three tiers."""
    m = MagicMock()
    resp = MagicMock()
    resp.allowed_scopes = ["session", "project", "global"]
    resp.isolation_ctx = MagicMock()
    m.scope_check.return_value = resp
    return m


@pytest.fixture
def mock_l2_05() -> MagicMock:
    """IC-L2-04 rerank · default returns candidates[:top_k] in original order."""
    m = MagicMock()

    def _rerank(req, *_a, **_kw) -> RerankResponse:
        return RerankResponse(
            ranked=list(req.candidates[: req.top_k]),
            signals_used=["bm25"],
        )

    m.rerank.side_effect = _rerank
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


class _FakeRepo:
    """In-memory KBEntryRepository · supports seeding + failure injection."""

    def __init__(self) -> None:
        self._session: list[KBEntry] = []
        self._project: list[KBEntry] = []
        self._global: list[KBEntry] = []
        self._fail_all: Exception | None = None
        self._slow_ms: int = 0
        self._session_bad_count: int = 0
        self._jsonl_truncated: bool = False

    # ---- seeding -----------------------------------------------------------

    def seed(self, session: int = 0, project: int = 0, global_: int = 0) -> None:
        def _mk(n: int, scope: str) -> list[KBEntry]:
            return [
                KBEntry(
                    id=f"kbe-{scope}{i:05d}",
                    project_id=_PID,
                    scope=scope,
                    kind="pattern",
                    title=f"{scope}-t-{i}",
                    content="c" * 20,
                    applicable_context=ApplicableContext(route="S2"),
                    observed_count=i + 1,
                    first_observed_at="2026-04-22T10:00:00Z",
                    last_observed_at="2026-04-22T10:00:00Z",
                )
                for i in range(n)
            ]

        self._session = _mk(session, "session")
        self._project = _mk(project, "project")
        self._global = _mk(global_, "global")

    def seed_kinds(self, kinds: list[str], count_each: int) -> None:
        self._session = [
            KBEntry(
                id=f"kbe-{k}{i}",
                project_id=_PID,
                scope="session",
                kind=k,
                title=f"t-{k}-{i}",
                content="c" * 20,
                applicable_context=ApplicableContext(),
                observed_count=1,
                first_observed_at="t",
                last_observed_at="t",
            )
            for k in kinds
            for i in range(count_each)
        ]
        self._project = []
        self._global = []

    def seed_contexts(self, pairs: list[tuple[str | None, list[str]]]) -> None:
        self._session = [
            KBEntry(
                id=f"kbe-{i}",
                project_id=_PID,
                scope="session",
                kind="pattern",
                title=f"t-{i}",
                content="c" * 20,
                applicable_context=ApplicableContext(route=rt, tech_stack=list(tech)),
                observed_count=1,
                first_observed_at="t",
                last_observed_at="t",
            )
            for i, (rt, tech) in enumerate(pairs)
        ]

    def seed_conflict(
        self,
        entry_id: str,
        session_title: str,
        project_title: str,
        global_title: str,
    ) -> None:
        def _mk(scope: str, title: str) -> KBEntry:
            return KBEntry(
                id=entry_id,
                project_id=_PID,
                scope=scope,
                kind="pattern",
                title=title,
                content="c" * 20,
                applicable_context=ApplicableContext(route="S2"),
                observed_count=1,
                first_observed_at="t",
                last_observed_at="t",
            )

        self._session = [_mk("session", session_title)]
        self._project = [_mk("project", project_title)]
        self._global = [_mk("global", global_title)]

    def seed_for_stage(self, stage: str, kinds: list[str], count: int) -> None:
        self._session = [
            KBEntry(
                id=f"kbe-{k}{i}",
                project_id=_PID,
                scope="session",
                kind=k,
                title=f"{stage}-{k}-{i}",
                content="c" * 20,
                applicable_context=ApplicableContext(route=stage),
                observed_count=1,
                first_observed_at="t",
                last_observed_at="t",
            )
            for k in kinds
            for i in range(count)
        ]

    def seed_with_bad_entries(self, session_good: int, session_bad: int) -> None:
        self.seed(session=session_good)
        self._session_bad_count = session_bad

    def seed_with_truncated_jsonl(self, good_lines: int, bad_last_line: bool) -> None:
        self.seed(session=good_lines)
        self._jsonl_truncated = bad_last_line

    # ---- failure injection ------------------------------------------------

    def fail_all_layers(self, exc: Exception) -> None:
        self._fail_all = exc

    def slow_all_layers(self, delay_ms: int) -> None:
        self._slow_ms = delay_ms

    # ---- reads ------------------------------------------------------------

    def read_session(self, _ctx: Any, _kinds: Any) -> list[KBEntry]:
        self._apply_side_effects()
        return list(self._session)

    def read_project(self, _ctx: Any, _kinds: Any) -> list[KBEntry]:
        self._apply_side_effects()
        return list(self._project)

    def read_global(self, _kinds: Any) -> list[KBEntry]:
        self._apply_side_effects()
        return list(self._global)

    def _apply_side_effects(self) -> None:
        if self._fail_all is not None:
            raise self._fail_all
        if self._slow_ms:
            import time

            time.sleep(self._slow_ms / 1000.0)

    def all(self) -> list[KBEntry]:
        return list(self._session) + list(self._project) + list(self._global)

    # ---- synthesis hooks accessed by service ------------------------------

    @property
    def session_bad_count(self) -> int:
        return self._session_bad_count

    @property
    def jsonl_truncated(self) -> bool:
        return self._jsonl_truncated


@pytest.fixture
def fake_repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.fixture
def sut(
    mock_l2_01: MagicMock,
    mock_l2_05: MagicMock,
    mock_audit: MagicMock,
    fake_repo: _FakeRepo,
) -> KBReadService:
    return KBReadService(
        scope_checker=mock_l2_01,
        reranker=mock_l2_05,
        audit=mock_audit,
        repo=fake_repo,
    )
