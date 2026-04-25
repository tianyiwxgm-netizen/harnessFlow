"""IC-06 集成 fixtures · 真实 KBReadService + FakeKBRepo/ScopeChecker/Reranker.

铁律:
    - 真实 import L1-06 reader (KBReadService + 5-step pipeline)
    - 边界 (Repo / ScopeChecker / Reranker) 用 tests/shared.stubs 共用替身
    - audit sink 接入 ic_assertions 旁路验事件 emit
"""
from __future__ import annotations

from typing import Any

import pytest

from app.knowledge_base.reader.schemas import (
    ApplicableContext,
    KBEntry,
    ReadRequest,
)
from app.knowledge_base.reader.service import KBReadService
from tests.shared.stubs import (
    AuditSink,
    FakeKBRepo,
    FakeReranker,
    FakeScopeChecker,
)


@pytest.fixture
def project_id() -> str:
    return "proj-ic06"


@pytest.fixture
def session_id() -> str:
    return "sess-ic06-01"


@pytest.fixture
def fake_repo() -> FakeKBRepo:
    return FakeKBRepo()


@pytest.fixture
def fake_scope_checker() -> FakeScopeChecker:
    return FakeScopeChecker()


@pytest.fixture
def fake_reranker() -> FakeReranker:
    return FakeReranker()


@pytest.fixture
def audit_sink() -> AuditSink:
    return AuditSink()


@pytest.fixture
def reader(
    fake_scope_checker: FakeScopeChecker,
    fake_reranker: FakeReranker,
    audit_sink: AuditSink,
    fake_repo: FakeKBRepo,
) -> KBReadService:
    return KBReadService(
        scope_checker=fake_scope_checker,
        reranker=fake_reranker,
        audit=audit_sink,
        repo=fake_repo,
    )


@pytest.fixture
def make_entry(project_id: str):
    """工厂 · 一行造合法 KBEntry."""

    def _make(
        *,
        entry_id: str = "kbe-001",
        scope: str = "session",
        kind: str = "pattern",
        title: str = "default-title",
        content: str = "body",
        observed_count: int = 1,
        route: str | None = "S3",
        task_type: str | None = "coding",
        tech_stack: list[str] | None = None,
        pid: str | None = None,
    ) -> KBEntry:
        return KBEntry(
            id=entry_id,
            project_id=pid if pid is not None else project_id,
            scope=scope,
            kind=kind,
            title=title,
            content=content,
            observed_count=observed_count,
            applicable_context=ApplicableContext(
                route=route,
                task_type=task_type,
                tech_stack=tech_stack or ["python"],
                wbs_node_id=None,
            ),
        )

    return _make


@pytest.fixture
def make_request(project_id: str, session_id: str):
    """工厂 · 合法 ReadRequest."""

    def _make(
        *,
        trace_id: str | None = "trace-ic06-01",
        kind: str | list[str] | None = None,
        scope: list[str] | None = None,
        top_k: int = 5,
        strict_mode: bool = False,
        route: str | None = "S3",
        task_type: str | None = "coding",
        tech_stack: list[str] | None = None,
        cache_enabled: bool = True,
        nlq: str | None = None,
        pid_override: str | None = None,
    ) -> ReadRequest:
        return ReadRequest(
            trace_id=trace_id,
            project_id=pid_override or project_id,
            session_id=session_id,
            applicable_context=ApplicableContext(
                route=route,
                task_type=task_type,
                tech_stack=tech_stack or ["python"],
                wbs_node_id=None,
            ),
            kind=kind,
            scope=scope,
            top_k=top_k,
            strict_mode=strict_mode,
            cache_enabled=cache_enabled,
            nlq=nlq,
        )

    return _make
