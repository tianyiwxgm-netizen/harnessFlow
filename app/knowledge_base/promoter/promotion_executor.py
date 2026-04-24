"""L1-06 L2-04 · PromotionExecutor (GREEN implementation).

Implements the IC-08 ``kb_promote`` entry per 3-1 §6.1-§6.4:

  * PM-14 project_id enforcement (including entry-level mismatch · §3.4 code).
  * Cross-layer skip-level denial (session → global is forbidden).
  * Threshold arbitration:
      - session → project : observed_count ≥ 2 OR user_approved.
      - project → global  : observed_count ≥ 3 OR user_approved.
  * User approval gate · reason=user_approved requires approver.user_id.
  * Rejected-cannot-undo list · re-promotion of rejected entries blocked.
  * Promotion idempotency keyed on ``(source_entry_id, to_scope)`` → same
    promotion_id is returned for replayed commands.
  * Atomic write via injected ``target_store`` (in-memory by default).
  * Source Session marker · records session entry as "promoted".
  * Ceremony-level batch: pulls candidates from the observer snapshot
    (injected L2-03), iterates per-entry, collects
    promoted/rejected/kept/failed tallies, emits IC-09 audit.
"""
from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .errors import PromoterErrorCode
from .schemas import (
    GLOBAL_THRESHOLD,
    PROJECT_THRESHOLD,
    VALID_FROM_SCOPES,
    VALID_REASONS,
    VALID_TO_SCOPES,
    BatchResult,
    KBPromoteRequest,
    KBPromoteResponse,
    PromoteTarget,
    PromotedEntry,
    SingleResult,
)


# ---------------------------------------------------------------------------
# In-memory target store · reference implementation
# ---------------------------------------------------------------------------


@dataclass
class InMemoryTargetStore:
    """Default Project / Global tier store used when no repo is injected."""

    _project: dict[str, dict[str, PromotedEntry]] = field(default_factory=dict)
    _global: dict[str, PromotedEntry] = field(default_factory=dict)
    _rejected: set[tuple[str, str]] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def write_project(self, project_id: str, entry: PromotedEntry) -> None:
        with self._lock:
            bucket = self._project.setdefault(project_id, {})
            bucket[entry.target_entry_id] = entry

    def write_global(self, entry: PromotedEntry) -> None:
        with self._lock:
            self._global[entry.target_entry_id] = entry

    def list_project(self, project_id: str) -> list[PromotedEntry]:
        with self._lock:
            return list(self._project.get(project_id, {}).values())

    def list_global(self) -> list[PromotedEntry]:
        with self._lock:
            return list(self._global.values())

    def mark_rejected(self, project_id: str, entry_id: str) -> None:
        with self._lock:
            self._rejected.add((project_id, entry_id))

    def is_rejected(self, project_id: str, entry_id: str) -> bool:
        with self._lock:
            return (project_id, entry_id) in self._rejected


# ---------------------------------------------------------------------------
# PromotionExecutor
# ---------------------------------------------------------------------------


class PromotionExecutor:
    """IC-08 kb_promote entry + IC-L2-03/IC-L2-06 collaborations."""

    def __init__(
        self,
        *,
        observer: Any = None,
        tier_manager: Any = None,
        event_bus: Any = None,
        target_store: InMemoryTargetStore | None = None,
    ) -> None:
        self._observer = observer
        self._tier_manager = tier_manager
        self._event_bus = event_bus
        self._target_store = target_store or InMemoryTargetStore()

        # idempotency keyed by (project_id, source_entry_id, to_scope)
        self._idem_lock = threading.Lock()
        self._idem_cache: dict[tuple[str, str, str], str] = {}
        # Running ceremony per project (E_L204_CEREMONY_ALREADY_RUNNING)
        self._ceremony_lock = threading.Lock()
        self._running_ceremonies: set[str] = set()
        # Inline audit buffer
        self._audit_log: list[dict[str, Any]] = []

    # ======================================================================
    # IC-08 · kb_promote · main entry
    # ======================================================================

    def kb_promote(self, req: KBPromoteRequest) -> KBPromoteResponse:
        response_id = f"prr-{uuid4()}"
        # 0 · PM-14
        if not req.project_id:
            return self._reject(
                req, response_id, PromoterErrorCode.PROJECT_ID_MISSING
            )
        # 1 · mode dispatch
        if req.mode == "single":
            return self._promote_single(req, response_id)
        if req.mode == "batch":
            return self._promote_batch(req, response_id)
        return self._reject(
            req,
            response_id,
            PromoterErrorCode.INVALID_FROM_TO,
            message=f"unknown mode={req.mode}",
        )

    # ----------------------------------------------------------------- single

    def _promote_single(
        self, req: KBPromoteRequest, response_id: str
    ) -> KBPromoteResponse:
        t = req.target
        if t is None:
            return self._reject(
                req,
                response_id,
                PromoterErrorCode.INVALID_FROM_TO,
                message="missing target for single mode",
            )

        # Schema checks on target
        if t.from_scope not in VALID_FROM_SCOPES or t.to_scope not in VALID_TO_SCOPES:
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.INVALID_FROM_TO,
                t,
                verdict="rejected",
            )
        if t.reason not in VALID_REASONS:
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.INVALID_FROM_TO,
                t,
                verdict="rejected",
            )

        # Skip-level denial · session → global
        if t.from_scope == "session" and t.to_scope == "global":
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.SKIP_LAYER_DENIED,
                t,
                verdict="rejected",
            )

        # user_approved requires approver.user_id
        if t.reason == "user_approved":
            if t.approver is None or not t.approver.user_id:
                return self._reject_with_single(
                    req,
                    response_id,
                    PromoterErrorCode.USER_APPROVAL_MISSING,
                    t,
                    verdict="rejected",
                )

        # Already rejected?
        if self._target_store.is_rejected(req.project_id, t.entry_id):
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.REJECTED_CANNOT_UNDO,
                t,
                verdict="rejected",
            )

        # Idempotency
        idem_key = (req.project_id, t.entry_id, t.to_scope)
        with self._idem_lock:
            cached_pid = self._idem_cache.get(idem_key)
        if cached_pid is not None:
            return KBPromoteResponse(
                response_id=response_id,
                request_id=req.request_id,
                project_id=req.project_id,
                mode="single",
                success=True,
                single_result=SingleResult(
                    promoted=True,
                    final_scope=t.to_scope,
                    promotion_id=cached_pid,
                    verdict="promoted",
                    reason_code="idempotent_replay",
                ),
            )

        # Fetch source entry (from observer snapshot — minimal viable path)
        source = self._lookup_source(req.project_id, t.entry_id)
        if source is None:
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.SOURCE_NOT_FOUND,
                t,
                verdict="rejected",
            )

        # PM-14 check at entry level
        if (
            getattr(source, "project_id", req.project_id) != req.project_id
        ):
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.PROJECT_ID_MISMATCH,
                t,
                verdict="rejected",
            )

        # Threshold / approval arbitration
        observed = int(getattr(source, "observed_count", 0))
        user_approved = t.reason == "user_approved"
        if t.to_scope == "project":
            if observed < PROJECT_THRESHOLD and not user_approved:
                return self._keep_with_single(
                    req,
                    response_id,
                    PromoterErrorCode.PROJECT_THRESHOLD_UNMET,
                    t,
                )
        elif t.to_scope == "global":
            if t.from_scope != "project":
                # should be caught above; belt-and-suspenders
                return self._reject_with_single(
                    req,
                    response_id,
                    PromoterErrorCode.SKIP_LAYER_DENIED,
                    t,
                    verdict="rejected",
                )
            if observed < GLOBAL_THRESHOLD and not user_approved:
                return self._keep_with_single(
                    req,
                    response_id,
                    PromoterErrorCode.GLOBAL_THRESHOLD_UNMET,
                    t,
                )

        # Atomic write
        promotion_id = f"prm-{uuid4()}"
        target_entry_id = f"kbe-promoted-{uuid4()}"
        promoted = PromotedEntry(
            target_entry_id=target_entry_id,
            source_entry_id=t.entry_id,
            source_project_id=req.project_id,
            scope=t.to_scope,
            kind=getattr(source, "kind", "pattern"),
            title=getattr(source, "title", ""),
            title_hash=getattr(source, "title_hash", ""),
            content=dict(getattr(source, "content", {})),
            observed_count=observed,
            promoted_at=_now_iso(),
            trigger=req.trigger,
            approver_user_id=(
                t.approver.user_id if t.approver is not None else None
            ),
        )
        try:
            if t.to_scope == "project":
                self._target_store.write_project(req.project_id, promoted)
            else:
                self._target_store.write_global(promoted)
        except Exception:
            # Review B-1 · any storage failure is infrastructure-level, not
            # a rule violation. It MUST NOT populate the rejected-cannot-undo
            # blacklist — transient errors (OSError / IOError / TimeoutError
            # / adapter-specific) must be retryable. verdict="error".
            return self._reject_with_single(
                req,
                response_id,
                PromoterErrorCode.WRITE_TARGET_FAIL,
                t,
                verdict="error",
            )

        with self._idem_lock:
            self._idem_cache[idem_key] = promotion_id

        self._audit(
            "kb_entry_promoted",
            project_id=req.project_id,
            source_entry_id=t.entry_id,
            target_entry_id=target_entry_id,
            final_scope=t.to_scope,
            trigger=req.trigger,
            promotion_id=promotion_id,
        )
        return KBPromoteResponse(
            response_id=response_id,
            request_id=req.request_id,
            project_id=req.project_id,
            mode="single",
            success=True,
            single_result=SingleResult(
                promoted=True,
                final_scope=t.to_scope,
                promotion_id=promotion_id,
                verdict="promoted",
                reason_code="auto_threshold"
                if not user_approved
                else "user_approved",
            ),
        )

    # ----------------------------------------------------------------- batch

    def _promote_batch(
        self, req: KBPromoteRequest, response_id: str
    ) -> KBPromoteResponse:
        # Per-project ceremony lock
        with self._ceremony_lock:
            if req.project_id in self._running_ceremonies:
                return self._reject(
                    req,
                    response_id,
                    PromoterErrorCode.CEREMONY_ALREADY_RUNNING,
                )
            self._running_ceremonies.add(req.project_id)
        try:
            ceremony_id = f"cer-{uuid4()}"
            t0 = datetime.now(UTC)
            result = BatchResult(ceremony_id=ceremony_id)

            if self._observer is None:
                # No observer → cannot pull candidates (fail fast)
                return self._reject(
                    req,
                    response_id,
                    PromoterErrorCode.CANDIDATE_PULL_FAIL,
                )

            try:
                manifest = self._observer.provide_candidate_snapshot(
                    project_id=req.project_id,
                    min_observed_count=PROJECT_THRESHOLD,
                    kind_filter=(
                        req.batch_scope.filter_kinds
                        if req.batch_scope is not None
                        else None
                    ),
                    trace_id=req.request_id,
                )
            except Exception:
                return self._reject(
                    req,
                    response_id,
                    PromoterErrorCode.CANDIDATE_PULL_FAIL,
                )
            if getattr(manifest, "error_code", None):
                return self._reject(
                    req,
                    response_id,
                    PromoterErrorCode.CANDIDATE_PULL_FAIL,
                )
            candidates = list(getattr(manifest, "entries", []) or [])
            result.candidates_total = len(candidates)

            for cand in candidates:
                entry_id = getattr(cand, "entry_id", "")
                observed = int(getattr(cand, "observed_count", 0) or 0)
                if observed < PROJECT_THRESHOLD:
                    result.kept.append(entry_id)
                    continue
                # Default per-candidate path: auto_threshold → project tier
                target = PromoteTarget(
                    entry_id=entry_id,
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                )
                single_req = KBPromoteRequest(
                    project_id=req.project_id,
                    mode="single",
                    trigger=req.trigger,
                    request_id=f"{req.request_id}-{entry_id}",
                    target=target,
                )
                sub = self._promote_single(single_req, response_id=f"{response_id}-{entry_id}")
                sr = sub.single_result
                if sr is None:
                    result.failed.append(
                        {
                            "entry_id": entry_id,
                            "failure_code": sub.error_code
                            or "UNKNOWN",
                            "will_retry": False,
                        }
                    )
                    continue
                if sr.verdict == "promoted":
                    result.promoted.append(entry_id)
                elif sr.verdict == "kept":
                    result.kept.append(entry_id)
                elif sr.verdict == "rejected":
                    result.rejected.append(entry_id)
                else:
                    # verdict == "error" or unknown → infra failure, retryable
                    result.failed.append(
                        {
                            "entry_id": entry_id,
                            "failure_code": sr.reason_code
                            or "UNKNOWN",
                            "will_retry": sr.verdict == "error",
                        }
                    )

            result.duration_ms = int(
                (datetime.now(UTC) - t0).total_seconds() * 1000
            )
            self._audit(
                "kb_ceremony_complete",
                project_id=req.project_id,
                ceremony_id=ceremony_id,
                promoted=len(result.promoted),
                rejected=len(result.rejected),
                kept=len(result.kept),
                failed=len(result.failed),
            )
            return KBPromoteResponse(
                response_id=response_id,
                request_id=req.request_id,
                project_id=req.project_id,
                mode="batch",
                success=True,
                batch_result=result,
            )
        finally:
            with self._ceremony_lock:
                self._running_ceremonies.discard(req.project_id)

    # ----------------------------------------------------------------- helpers

    def _lookup_source(
        self, project_id: str, entry_id: str
    ) -> Any | None:
        """Fetch the source entry for the given id via observer snapshot."""
        if self._observer is None:
            return None
        try:
            manifest = self._observer.provide_candidate_snapshot(
                project_id=project_id,
                min_observed_count=1,  # widen so low-count entries are visible
                trace_id="",
            )
        except Exception:
            return None
        if getattr(manifest, "error_code", None):
            return None
        for e in getattr(manifest, "entries", []) or []:
            if getattr(e, "entry_id", "") == entry_id:
                return e
        return None

    def _reject(
        self,
        req: KBPromoteRequest,
        response_id: str,
        code: PromoterErrorCode,
        message: str = "",
    ) -> KBPromoteResponse:
        self._audit(
            "kb_promotion_rejected",
            project_id=req.project_id,
            error_code=code.value,
            request_id=req.request_id,
        )
        return KBPromoteResponse(
            response_id=response_id,
            request_id=req.request_id,
            project_id=req.project_id,
            mode=req.mode,
            success=False,
            error_code=code.value,
            error_message=message or code.value,
        )

    def _reject_with_single(
        self,
        req: KBPromoteRequest,
        response_id: str,
        code: PromoterErrorCode,
        target: PromoteTarget,
        verdict: str = "rejected",
    ) -> KBPromoteResponse:
        # Mark rejected-cannot-undo ONLY for content-level rule rejections.
        # Review B-1 · verdict="error" (infra failure) MUST NOT mark_rejected.
        if verdict == "rejected":
            self._target_store.mark_rejected(req.project_id, target.entry_id)
        # Use a distinct audit event type for infra errors vs rule rejections
        event_type = (
            "kb_promotion_error"
            if verdict == "error"
            else "kb_promotion_rejected"
        )
        self._audit(
            event_type,
            project_id=req.project_id,
            entry_id=target.entry_id,
            error_code=code.value,
            request_id=req.request_id,
        )
        return KBPromoteResponse(
            response_id=response_id,
            request_id=req.request_id,
            project_id=req.project_id,
            mode="single",
            success=True,  # ceremony completed with a verdict, not aborted
            single_result=SingleResult(
                promoted=False,
                final_scope=target.from_scope,
                verdict=verdict,
                reason_code=code.value,
                reason_text=code.value,
            ),
        )

    def _keep_with_single(
        self,
        req: KBPromoteRequest,
        response_id: str,
        code: PromoterErrorCode,
        target: PromoteTarget,
    ) -> KBPromoteResponse:
        self._audit(
            "kb_promotion_kept",
            project_id=req.project_id,
            entry_id=target.entry_id,
            error_code=code.value,
            request_id=req.request_id,
        )
        return KBPromoteResponse(
            response_id=response_id,
            request_id=req.request_id,
            project_id=req.project_id,
            mode="single",
            success=True,
            single_result=SingleResult(
                promoted=False,
                final_scope=target.from_scope,
                verdict="kept",
                reason_code=code.value,
                reason_text=code.value,
            ),
        )

    def _audit(self, event_type: str, **payload: Any) -> None:
        record = {"event_type": event_type, "payload": payload}
        self._audit_log.append(record)
        if self._event_bus is None:
            return
        with contextlib.suppress(Exception):
            self._event_bus.append(event_type=event_type, payload=payload)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "PromotionExecutor",
    "InMemoryTargetStore",
]
