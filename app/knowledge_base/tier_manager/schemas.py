"""L1-06 L2-01 schemas · IC-L2-01/02/03 + lifecycle events.

Anchored to:
  - docs/3-1-Solution-Technical/L1-06-3层知识库/L2-01-3 层分层管理器.md §3.2-3.6
  - docs/3-2-Solution-TDD/L1-06-3层知识库/L2-01-...-tests.md

TDD contract: tests construct these models and read the listed attributes,
so field names / nesting / defaults are part of the locked contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Kind whitelist · 8 kinds · ADR-03 编译期 const
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


# ---------------------------------------------------------------------------
# Value objects shared across IC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IsolationContext:
    """Returned alongside ScopeDecision · PM-14 audit trail."""

    accessor_pid: str
    owner_pid_project_layer: str | None = None
    owner_pid_session_layer: str | None = None
    global_layer: str = "no_owner"


@dataclass(frozen=True)
class TierPaths:
    """3-tier physical paths (string paths relative to fs_root)."""

    session: str
    project: str
    # `global` is a Python reserved word → use a trailing underscore; keep both
    # attribute spellings for test convenience (positional only via __init__).
    global_: str

    # Tests access `.global_` consistently (see §2 positive cases).


@dataclass
class Violation:
    field: str
    rule: str
    message: str = ""


@dataclass
class ValidationResult:
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    error_code: str | None = None


@dataclass
class DeduplicationHint:
    existing_entry_id: str | None = None
    merge_strategy: str = "new_entry"  # "new_entry" | "increment_observed"


# ---------------------------------------------------------------------------
# Entry candidate VO · IC-L2-02 写位申请入参
# ---------------------------------------------------------------------------


@dataclass
class ApplicableContext:
    stage: str = ""
    task_type: str = ""
    tech_stack: list[str] = field(default_factory=list)


@dataclass
class EntryCandidate:
    id: str
    scope: str = "session"
    kind: str = "pattern"
    title: str = ""
    content: str = ""
    applicable_context: list[ApplicableContext] = field(default_factory=list)
    observed_count: int = 1
    first_observed_at: str = ""
    last_observed_at: str = ""
    source_links: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "kind": self.kind,
            "title": self.title,
            "content": self.content,
            "applicable_context": [
                {
                    "stage": ac.stage,
                    "task_type": ac.task_type,
                    "tech_stack": ac.tech_stack,
                }
                for ac in self.applicable_context
            ],
            "observed_count": self.observed_count,
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "source_links": self.source_links,
        }


# ---------------------------------------------------------------------------
# IC-L2-01 · resolve_read_scope
# ---------------------------------------------------------------------------


@dataclass
class ScopeDecisionRequest:
    request_id: str
    project_id: str
    session_id: str
    kind_filter: list[str] = field(default_factory=list)
    stage_hint: str = ""
    requester_bc: str = ""


@dataclass
class ScopeDecision:
    request_id: str
    verdict: str  # "ALLOW" | "DENY"
    allowed_scopes: list[str] = field(default_factory=list)
    isolation_context: IsolationContext | None = None
    tier_paths: TierPaths | None = None
    expired_exclusion_ts: str = ""
    deny_reason: str = ""
    error_code: str | None = None
    emitted_at: str = ""


# ---------------------------------------------------------------------------
# IC-L2-02 · allocate_session_write_slot
# ---------------------------------------------------------------------------


@dataclass
class WriteSlotRequest:
    request_id: str
    project_id: str
    session_id: str
    entry_candidate: EntryCandidate
    requester_bc: str = ""


@dataclass
class WriteSlot:
    request_id: str
    verdict: str  # "ALLOW" | "DENY"
    write_path: str = ""
    deduplication_hint: DeduplicationHint = field(default_factory=DeduplicationHint)
    schema_validation: ValidationResult = field(
        default_factory=lambda: ValidationResult(passed=True)
    )
    kind_validation: ValidationResult = field(
        default_factory=lambda: ValidationResult(passed=True)
    )
    deny_reason: str = ""
    error_code: str | None = None
    emitted_at: str = ""


# ---------------------------------------------------------------------------
# IC-L2-03 · check_promotion_rule
# ---------------------------------------------------------------------------


@dataclass
class PromotionRequest:
    request_id: str
    project_id: str
    entry_id: str
    from_scope: str  # "session" | "project"
    to_scope: str  # "project" | "global"
    observed_count: int
    approval: dict[str, str] = field(default_factory=dict)
    requester_bc: str = ""


@dataclass
class PromotionDecision:
    request_id: str
    verdict: str  # "ALLOW" | "DENY"
    reason_code: str = ""  # "OK" | "SKIP_LEVEL" | "BELOW_THRESHOLD" | ...
    expected_write_path: str = ""
    target_tier_ready: bool = False
    required_observed_count: int = 0
    override_owner_project_id: str | None = None
    deny_reason: str = ""
    error_code: str | None = None
    emitted_at: str = ""


# ---------------------------------------------------------------------------
# IC-L2-07 · run_expire_scan
# ---------------------------------------------------------------------------


@dataclass
class ExpireScanTrigger:
    trigger_id: str
    trigger_at: str
    scan_mode: str = "all"  # "all" | "single_project"
    target_project_id: str | None = None
    ttl_days: int = 7


@dataclass
class ExpireScanSummary:
    trigger_id: str
    scanned_project_count: int = 0
    scanned_entry_count: int = 0
    expired_marked_count: int = 0
    duration_ms: int = 0
    warnings: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "scanned_project_count": self.scanned_project_count,
            "scanned_entry_count": self.scanned_entry_count,
            "expired_marked_count": self.expired_marked_count,
            "duration_ms": self.duration_ms,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# IC-L2-activate · on_project_activated
# ---------------------------------------------------------------------------


@dataclass
class ActivateEvent:
    event_type: str  # "L1-02:project_created" | "L1-02:project_resumed"
    project_id: str
    project_name: str = ""
    stage: str = ""
    created_at: str = ""
    resumed_from_snapshot: bool = False


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """UTC now as ISO-8601 string."""
    return datetime.now(UTC).isoformat()
