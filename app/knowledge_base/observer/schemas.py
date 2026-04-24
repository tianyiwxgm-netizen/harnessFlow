"""L1-06 L2-03 schemas · IC-07 + IC-L2-06 + internal VOs.

3-1 §2.2 + §2.3 field-level YAML schemas translated to frozen dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KIND_WHITELIST: frozenset[str] = frozenset(
    {
        "pattern",
        "trap",
        "recipe",
        "tool_combo",
        "anti_pattern",
        "project_context",
        "external_ref",
        "effective_combo",
    }
)

TITLE_MAX_LEN = 200
SOFT_CAP_PER_PROJECT = 1000
HARD_CAP_PER_PROJECT = 10000
PROMOTION_THRESHOLD_SESSION_TO_PROJECT = 2


# ---------------------------------------------------------------------------
# IC-07 · kb_write_session
# ---------------------------------------------------------------------------


@dataclass
class ApplicableContext:
    """Filter-match keys for rerank / scope eligibility."""

    stage: list[str] = field(default_factory=list)
    task_type: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)


@dataclass
class KBEntryRequest:
    """Inbound entry payload to IC-07 kb_write_session (pre-storage)."""

    kind: str
    title: str
    content: dict[str, Any]
    applicable_context: ApplicableContext | None = None
    source_links: list[str] = field(default_factory=list)
    created_by: str = ""
    # Enforced = strip before write. If caller sets a non-None value,
    # service emits COUNT_OVERRIDE_IGNORED and replaces with actual count.
    observed_count: int | None = None
    project_id: str = ""
    scope: str = ""  # caller should leave empty; service forces "session"


@dataclass
class WriteSessionRequest:
    """Top-level IC-07 envelope (3-1 §3.1)."""

    project_id: str
    trace_id: str
    idempotency_key: str
    entry: KBEntryRequest
    emitted_by: str = ""
    emitted_at: str = ""


@dataclass
class PromotionHint:
    session_to_project_eligible: bool = False
    threshold: int = PROMOTION_THRESHOLD_SESSION_TO_PROJECT


@dataclass
class WriteSessionResponse:
    """IC-07 return VO · 3-1 §2.3 WriteResult."""

    success: bool
    action: str  # INSERTED / MERGED / REJECTED / DEGRADED
    entry_id: str = ""
    project_id: str = ""
    observed_count_after: int = 0
    first_observed_at: str = ""
    last_observed_at: str = ""
    was_normalized: bool = False
    promotion_hint: PromotionHint | None = None
    trace_id: str = ""
    audit_event_id: str = ""
    error_code: str | None = None
    error_message: str = ""
    degraded: bool = False


# ---------------------------------------------------------------------------
# IC-L2-06 · provide_candidate_snapshot
# ---------------------------------------------------------------------------


@dataclass
class CandidateSnapshotRequest:
    project_id: str
    trace_id: str = ""
    kind_filter: list[str] = field(default_factory=list)
    min_observed_count: int = PROMOTION_THRESHOLD_SESSION_TO_PROJECT
    include_hint: bool = True
    snapshot_ttl_s: int = 60


@dataclass
class SnapshotEntry:
    entry_id: str
    kind: str
    title: str
    observed_count: int
    first_observed_at: str
    last_observed_at: str
    applicable_context: ApplicableContext | None = None
    source_links_count: int = 0
    promotion_hint: PromotionHint | None = None


@dataclass
class SnapshotManifest:
    snapshot_id: str
    project_id: str
    requested_at: str = ""
    kind_filter: list[str] = field(default_factory=list)
    total_entries: int = 0
    entries: list[SnapshotEntry] = field(default_factory=list)
    snapshot_file_path: str = ""
    ttl_s: int = 60
    error_code: str | None = None


# ---------------------------------------------------------------------------
# Stored KB entry (session layer)
# ---------------------------------------------------------------------------


@dataclass
class StoredEntry:
    """Persisted representation under Session tier."""

    entry_id: str
    project_id: str
    kind: str
    title: str
    title_hash: str  # hex-form sha256[:16]
    content: dict[str, Any]
    applicable_context: ApplicableContext | None = None
    observed_count: int = 1
    first_observed_at: str = ""
    last_observed_at: str = ""
    source_links: list[str] = field(default_factory=list)
    created_by: str = ""
    scope: str = "session"
