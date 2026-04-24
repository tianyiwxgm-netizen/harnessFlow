"""L1-06 L2-04 schemas · IC-08 kb_promote field-level structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Promotion thresholds (3-1 §11.4 hard constraints)
PROJECT_THRESHOLD = 2
GLOBAL_THRESHOLD = 3

VALID_FROM_SCOPES: frozenset[str] = frozenset({"session", "project"})
VALID_TO_SCOPES: frozenset[str] = frozenset({"project", "global"})
VALID_REASONS: frozenset[str] = frozenset({"auto_threshold", "user_approved"})


@dataclass
class Approver:
    user_id: str | None = None
    intent_source: str = "ui_click"


@dataclass
class PromoteTarget:
    entry_id: str
    from_scope: str
    to_scope: str
    reason: str
    approver: Approver | None = None


@dataclass
class BatchScope:
    pull_from_task_ids: list[str] | None = None
    filter_kinds: list[str] | None = None
    max_candidates_per_batch: int = 100


@dataclass
class KBPromoteRequest:
    """Top-level IC-08 envelope (3-1 §3.1.1)."""

    project_id: str
    mode: str  # single / batch
    trigger: str  # s7_batch / user_manual / user_manual_batch
    request_id: str
    requested_at: str = ""
    # single-mode
    target: PromoteTarget | None = None
    # batch-mode
    batch_scope: BatchScope | None = None
    timeout_ms: int = 30000


@dataclass
class SingleResult:
    promoted: bool = False
    final_scope: str | None = None
    promotion_id: str | None = None
    verdict: str = "kept"  # promoted / rejected / kept
    reason_code: str = ""
    reason_text: str = ""


@dataclass
class BatchResult:
    ceremony_id: str = ""
    candidates_total: int = 0
    promoted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class KBPromoteResponse:
    """IC-08 response (3-1 §3.1.2)."""

    response_id: str
    request_id: str
    project_id: str
    mode: str
    success: bool
    single_result: SingleResult | None = None
    batch_result: BatchResult | None = None
    error_code: str | None = None
    error_message: str = ""


@dataclass
class PromotedEntry:
    """Stored projection of a promoted entry (Project / Global tier)."""

    target_entry_id: str
    source_entry_id: str
    source_project_id: str
    scope: str  # project / global
    kind: str
    title: str
    title_hash: str
    content: dict[str, Any]
    observed_count: int
    promoted_at: str
    trigger: str
    approver_user_id: str | None = None
