"""L2-03 审计记录器 · schemas · 对齐 3-1 §3.2.

简化版：Trail / Anchor / EvidenceLayer / QueryFilter / GateState.
WP-α-09 覆盖 IC-18 核心 · 4 层 Evidence 为简化结构.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AnchorType(str, Enum):
    PROJECT_ID = "project_id"
    TICK_ID = "tick_id"
    EVENT_ID = "event_id"
    FILE_PATH = "file_path"
    ARTIFACT_ID = "artifact_id"
    DECISION_ID = "decision_id"


class LayerType(str, Enum):
    DECISION = "decision"
    EVENT = "event"
    SUPERVISOR = "supervisor"
    AUTHZ = "authz"


class Completeness(str, Enum):
    COMPLETE = "COMPLETE"
    BROKEN = "BROKEN"
    PARTIAL = "PARTIAL"


class GateStateEnum(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REBUILDING = "REBUILDING"


@dataclass(frozen=True)
class Anchor:
    anchor_type: AnchorType
    anchor_id: str
    project_id: str


@dataclass(frozen=True)
class QueryFilter:
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    actor: str | None = None
    event_type: str | None = None
    severity: str | None = None
    max_events_per_layer: int = 500
    max_depth: int = 4  # 1=immediate, 4=full_chain
    cursor: int = 0


@dataclass(frozen=True)
class EvidenceLayer:
    layer_type: LayerType
    entries: list[dict[str, Any]]
    count: int
    first_ts: str | None = None
    last_ts: str | None = None
    truncated_at: int | None = None


@dataclass(frozen=True)
class Trail:
    """IC-18 query_audit_trail 出参."""

    anchor: Anchor
    project_id: str
    depth: str  # "immediate" | "full_chain"
    decision_layer: EvidenceLayer
    event_layer: EvidenceLayer
    supervisor_layer: EvidenceLayer
    authz_layer: EvidenceLayer
    completeness: Completeness
    broken_layers: list[str]
    queried_at: str
    mirror_version: int
    latency_ms: int
    total_entries: int
    truncated: bool = False
    fallback_used: str = "none"
    hash_chain_gap: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class GateState:
    state: GateStateEnum
    project_id: str
    opened_at: str
    reason: str | None = None
    expected_open_at: str | None = None


@dataclass(frozen=True)
class RebuildReport:
    project_id: str
    events_replayed: int
    mirror_size_after: int
    duration_ms: int
    gate_state_after: GateStateEnum
    skipped_corrupt_events: int = 0


# ================== 错误码 ==================

class AuditError(Exception):
    """L2-03 基类."""

    error_code: str = "AUDIT_E_UNKNOWN"


class AuditProjectRequired(AuditError):
    error_code = "AUDIT_E_PROJECT_REQUIRED"


class AuditInvalidAnchor(AuditError):
    error_code = "AUDIT_E_INVALID_ANCHOR"


class AuditDeadlineExceeded(AuditError):
    error_code = "AUDIT_E_DEADLINE_EXCEEDED"


class AuditGateClosed(AuditError):
    error_code = "AUDIT_E_GATE_CLOSED"


class AuditGateRebuilding(AuditError):
    error_code = "AUDIT_E_GATE_REBUILDING"


class AuditInvalidStateTransition(AuditError):
    error_code = "AUDIT_E_INVALID_STATE_TRANSITION"


__all__ = [
    "AnchorType",
    "LayerType",
    "Completeness",
    "GateStateEnum",
    "Anchor",
    "QueryFilter",
    "EvidenceLayer",
    "Trail",
    "GateState",
    "RebuildReport",
    "AuditError",
    "AuditProjectRequired",
    "AuditInvalidAnchor",
    "AuditDeadlineExceeded",
    "AuditGateClosed",
    "AuditGateRebuilding",
    "AuditInvalidStateTransition",
]
