"""L1-06 L2-05 schemas · IC-L2-04 rerank + IC-L2-05 reverse_recall + stage events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Rerank context / candidate / response
# ---------------------------------------------------------------------------


@dataclass
class RerankContext:
    current_stage: str | None = None
    task_type: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    active_kinds: list[str] = field(default_factory=list)
    query_hint: str = ""


@dataclass
class CandidateSummary:
    entry_id: str
    scope: str = "project"
    kind: str = "pattern"
    entry_summary: Any = None  # MagicMock-compatible; holds title + applicable_context
    project_id: str | None = None


@dataclass
class RerankRequest:
    project_id: str | None
    rerank_id: str
    candidates: list[Any]
    context: RerankContext
    top_k: int = 5
    include_trace: bool = False
    trace_id: str = ""
    timeout_ms: int | None = None


@dataclass
class RerankReason:
    top_signal: str = ""
    top_value: float = 0.0
    bottom_signal: str = ""
    bottom_value: float = 0.0
    narrative: str = ""
    signals: dict[str, float] = field(default_factory=dict)


@dataclass
class RerankEntry:
    entry_id: str
    rank: int = 0
    score: float = 0.0
    reason: RerankReason | None = None


@dataclass
class RerankResponse:
    project_id: str | None
    rerank_id: str
    status: str = "success"  # success / degraded / rejected
    entries: list[RerankEntry] = field(default_factory=list)
    degraded: bool = False
    fallback_mode: str | None = None
    duration_ms: int = 0
    weights_applied: dict[str, float] = field(default_factory=dict)
    signals_skipped: list[str] = field(default_factory=list)
    top_k_capped: bool = False
    error_code: str | None = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reverse recall
# ---------------------------------------------------------------------------


@dataclass
class ReverseRecallRequest:
    project_id: str
    injection_id: str
    stage_to: str
    kinds: list[str]
    scope_priority: list[str]
    recall_top_k: int = 20
    trace_id: str = ""
    timeout_ms: int | None = None


@dataclass
class ReverseRecallResponse:
    project_id: str
    injection_id: str
    candidates: list[Any] = field(default_factory=list)
    recalled_count: int = 0
    duration_ms: int = 0
    scope_layers_hit: list[str] = field(default_factory=list)
    error_code: str | None = None


# ---------------------------------------------------------------------------
# stage_transitioned subscription
# ---------------------------------------------------------------------------


@dataclass
class StageTransitionedEvent:
    event_id: str
    event_type: str  # "L1-02:stage_transitioned"
    project_id: str
    stage_from: str
    stage_to: str
    transition_reason: str = ""
    transition_at: str = ""
    trace_id: str = ""
    gate_id: str | None = None


# ---------------------------------------------------------------------------
# push_to_l101
# ---------------------------------------------------------------------------


@dataclass
class PushContextRequest:
    project_id: str
    injection_id: str
    stage: str
    entries: list[Any]
    source: str = "L2-05_stage_injection"
    context_type: str = "kb_injection"
    trace_id: str = ""


@dataclass
class PushContextResponse:
    accepted: bool = False
    context_id: str | None = None
    rejection_reason: str | None = None
