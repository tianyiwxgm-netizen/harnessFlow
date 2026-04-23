"""L1-06 L2-02 KB read schemas · 3-1 §2.2-2.6."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicableContext:
    route: str | None = None
    task_type: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    wbs_node_id: str | None = None


@dataclass
class KBEntry:
    id: str
    project_id: str | None = None
    scope: str = "session"  # "session" | "project" | "global"
    kind: str = "pattern"
    title: str = ""
    content: str = ""
    applicable_context: ApplicableContext = field(default_factory=ApplicableContext)
    observed_count: int = 1
    first_observed_at: str = ""
    last_observed_at: str = ""
    source_links: list[str] = field(default_factory=list)
    rerank_score: float = 0.0
    rerank_reasons: list[str] = field(default_factory=list)


@dataclass
class ReadRequest:
    trace_id: str | None
    project_id: str
    session_id: str
    applicable_context: ApplicableContext
    kind: str | list[str] | None = None
    scope: list[str] | None = None
    top_k: int = 5
    strict_mode: bool = False
    cache_enabled: bool = True
    tick_id: str | None = None
    nlq: str | None = None
    global_timeout_ms: int = 1000


@dataclass
class ReadMeta:
    project_id: str
    candidate_count: int = 0
    returned_count: int = 0
    latency_ms: float = 0.0
    cache_hit: bool = False
    scopes_hit: list[str] = field(default_factory=list)
    degraded: bool = False
    candidate_overflow: bool = False
    rerank_fallback: bool = False
    fallback_reason: str | None = None
    schema_invalid_skipped: int = 0
    jsonl_line_corrupt_skipped: int = 0
    cache_recovered: bool = False


@dataclass
class ReadResult:
    entries: list[KBEntry]
    meta: ReadMeta
    trace_id: str | None
    error_hint: str | None = None
    error_code: str | None = None


@dataclass
class RerankRequest:
    candidates: list[KBEntry]
    context: ApplicableContext
    top_k: int = 5
    signals_requested: list[str] = field(default_factory=list)


@dataclass
class RerankResponse:
    ranked: list[KBEntry]
    signals_used: list[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class ScopeCheckResult:
    """VO shape that tests assemble via MagicMock; we use it when wiring real deps."""

    allowed_scopes: list[str] = field(default_factory=list)
    isolation_ctx: Any = None
    rejected_reason: str | None = None
