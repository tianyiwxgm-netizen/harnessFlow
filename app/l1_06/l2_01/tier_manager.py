"""L1-06 L2-01 · TierManager (GREEN implementation).

Implements the 8 algorithms in 3-1 §6 (A1-A8) + the 6 IC surfaces in §3.
Internal collaborators live in ``_collaborators.py``; events sink through
L1-09 IC-09 ``event_bus.append(event_type=..., payload=...)``.
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ._collaborators import (
    AuditTracker,
    IsolationEnforcer,
    SchemaValidator,
    SessionIndex,
    TierLayoutRepo,
)
from .errors import TierErrorCode
from .schemas import (
    KIND_WHITELIST,
    ActivateEvent,
    DeduplicationHint,
    ExpireScanSummary,
    ExpireScanTrigger,
    IsolationContext,
    PromotionDecision,
    PromotionRequest,
    ScopeDecision,
    ScopeDecisionRequest,
    TierPaths,
    ValidationResult,
    Violation,
    WriteSlot,
    WriteSlotRequest,
    now_iso,
)

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

_PID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_SESSION_TTL_DAYS = 7

_PROMOTION_MATRIX: dict[tuple[str, str], dict[str, Any]] = {
    ("session", "project"): {
        "required_observed_count": 2,
        "approval_required": False,
        "approval_allowed_override": True,
    },
    ("project", "global"): {
        "required_observed_count": 3,
        "approval_required": True,
        "approval_allowed_override": False,
    },
}

_EVENTBUS_FAIL_BUDGET = 5  # consecutive failures before degrading


# ---------------------------------------------------------------------------
# TierManager
# ---------------------------------------------------------------------------


class TierManager:
    """Application Service · 6 IC surfaces · in-process lib (no network)."""

    def __init__(
        self,
        clock: Any,
        event_bus: Any,
        fs_root: Path,
        tier_layout_path: Path,
    ) -> None:
        self._clock = clock
        self._event_bus = event_bus
        self._fs_root = Path(fs_root)
        self._tier_layout_path = Path(tier_layout_path)

        # Internal collaborators (exposed for TDD)
        self._tier_repo = TierLayoutRepo(
            self._fs_root,
            self._tier_layout_path,
            on_corrupt=self._on_registry_corrupt,
        )
        self._session_idx = SessionIndex()
        self._isolation = IsolationEnforcer()
        self._audit = AuditTracker()
        self._schema = SchemaValidator()

        self._degradation_level: str = "FULL"
        self._bus_fail_count: int = 0
        self._buffer_in_mem: list[dict[str, Any]] = []
        self._activate_lock = threading.Lock()

    # ------------------------------------------------------------------ A1

    def resolve_read_scope(self, req: ScopeDecisionRequest) -> ScopeDecision:
        """A1 ResolveScope + A2 EnforceIsolation · IC-L2-01."""
        # Step 1 · pid format + E-TIER-010
        if not _is_valid_pid(req.project_id):
            return self._scope_deny(
                req,
                TierErrorCode.PATH_RESOLUTION_FAIL,
                "invalid project_id",
            )

        # Step 1b · session_id non-empty + E-TIER-012 (edge 905)
        if not req.session_id:
            return self._scope_deny(
                req, TierErrorCode.SESSION_ID_NOT_FOUND, "empty session_id"
            )

        # Step 2 · PM-14 cross-project check (E-TIER-002)
        forced_owner = self._isolation.forced_owner_for(req.project_id)
        if forced_owner is not None and forced_owner != req.project_id:
            self._emit_cross_project_denied(
                accessor_pid=req.project_id,
                owner_pid=forced_owner,
                request_id=req.request_id,
            )
            return self._scope_deny(
                req,
                TierErrorCode.CROSS_PROJECT_READ_DENIED,
                f"accessor={req.project_id} owner={forced_owner}",
            )

        # Step 3 · activation check (E-TIER-001)
        project_ready = self._tier_repo.is_activated(req.project_id, "project")
        global_ready = self._tier_repo.is_activated(req.project_id, "global")
        if not (project_ready or global_ready):
            return self._scope_deny(
                req, TierErrorCode.TIER_NOT_ACTIVATED, "project tier not activated"
            )

        # Step 4 · session membership (E-TIER-012)
        if not self._session_idx.belongs_to(req.session_id, req.project_id):
            return self._scope_deny(
                req,
                TierErrorCode.SESSION_ID_NOT_FOUND,
                f"session {req.session_id} not found under {req.project_id}",
            )

        # Step 5 · allowed_scopes (S > P > G)
        allowed = ["session"]
        if project_ready:
            allowed.append("project")
        if global_ready:
            allowed.append("global")

        # Step 6 · tier paths
        paths = self._tier_paths(req.project_id, req.session_id)

        # Step 7 · expired_exclusion_ts (uses clock fixture for determinism)
        now = self._now()
        excl_ts = (now - timedelta(days=_SESSION_TTL_DAYS)).isoformat()

        # Step 8 · post-filter: mark any session entries older than excl_ts
        cutoff = now - timedelta(days=_SESSION_TTL_DAYS)
        for meta in self._session_idx.entries_for(req.project_id, req.session_id):
            if _is_before(meta.last_observed_at, cutoff):
                self._audit.mark_expired(meta.entry_id)

        # Step 9 · audit event
        self._try_emit(
            "L1-06:kb_scope_resolved",
            {
                "request_id": req.request_id,
                "project_id": req.project_id,
                "allowed_scopes": allowed,
            },
        )

        return ScopeDecision(
            request_id=req.request_id,
            verdict="ALLOW",
            allowed_scopes=allowed,
            isolation_context=IsolationContext(
                accessor_pid=req.project_id,
                owner_pid_project_layer=req.project_id if project_ready else None,
                owner_pid_session_layer=req.project_id,
                global_layer="no_owner",
            ),
            tier_paths=paths,
            expired_exclusion_ts=excl_ts,
            emitted_at=now_iso(),
        )

    def _scope_deny(
        self, req: ScopeDecisionRequest, code: TierErrorCode, reason: str
    ) -> ScopeDecision:
        return ScopeDecision(
            request_id=req.request_id,
            verdict="DENY",
            error_code=code.value,
            deny_reason=reason,
            emitted_at=now_iso(),
        )

    # ------------------------------------------------------------------ A5

    def allocate_session_write_slot(self, req: WriteSlotRequest) -> WriteSlot:
        """A5 AllocateSessionWriteSlot · IC-L2-02 (+ A3 schema + A4 kind)."""
        cand = req.entry_candidate

        # 1 · scope must be "session" (E-TIER-005)
        if cand.scope != "session":
            return self._slot_deny(
                req,
                TierErrorCode.WRONG_SCOPE_FOR_WRITE,
                f"write scope={cand.scope} not allowed (session-only)",
            )

        # 2 · kind whitelist (A4 · E-TIER-003)
        kind_ok = cand.kind in KIND_WHITELIST
        if not kind_ok:
            self._try_emit(
                "L1-06:kb_invalid_kind_denied",
                {
                    "invalid_kind": cand.kind,
                    "whitelist": sorted(KIND_WHITELIST),
                },
            )
            return WriteSlot(
                request_id=req.request_id,
                verdict="DENY",
                error_code=TierErrorCode.INVALID_KIND.value,
                deny_reason=f"kind '{cand.kind}' not in whitelist",
                kind_validation=ValidationResult(
                    passed=False,
                    violations=[Violation(field="kind", rule="whitelist")],
                    error_code=TierErrorCode.INVALID_KIND.value,
                ),
                emitted_at=now_iso(),
            )

        # 3 · schema validation (A3 · E-TIER-004)
        passed, raw = self._schema.validate(cand.to_dict())
        violations = [Violation(**v) for v in raw]
        if not passed:
            return WriteSlot(
                request_id=req.request_id,
                verdict="DENY",
                error_code=TierErrorCode.SCHEMA_VIOLATION.value,
                deny_reason=f"{len(violations)} schema violation(s)",
                schema_validation=ValidationResult(
                    passed=False,
                    violations=violations,
                    error_code=TierErrorCode.SCHEMA_VIOLATION.value,
                ),
                kind_validation=ValidationResult(passed=True),
                emitted_at=now_iso(),
            )

        # 4 · activation (E-TIER-001)
        if not self._tier_repo.is_activated(req.project_id, "project") and not self._tier_repo.is_activated(req.project_id, "global"):
            return self._slot_deny(
                req, TierErrorCode.TIER_NOT_ACTIVATED, "project not activated"
            )

        # 5 · dedup lookup
        existing = self._session_idx.lookup_dedup(
            project_id=req.project_id,
            session_id=req.session_id,
            title=cand.title,
            kind=cand.kind,
        )
        dedup = (
            DeduplicationHint(
                existing_entry_id=existing, merge_strategy="increment_observed"
            )
            if existing
            else DeduplicationHint(merge_strategy="new_entry")
        )

        # 6 · write path (relative per PM-14 doc contract)
        write_path = f"task-boards/{req.project_id}/{req.session_id}.kb.jsonl"

        # 7 · auto-register dedup on first ALLOW so repeat writes hint
        #     `increment_observed`. L2-03 may still override with its own id.
        if existing is None:
            self._session_idx.register(
                project_id=req.project_id,
                session_id=req.session_id,
                title=cand.title,
                kind=cand.kind,
                entry_id=cand.id,
            )

        return WriteSlot(
            request_id=req.request_id,
            verdict="ALLOW",
            write_path=write_path,
            deduplication_hint=dedup,
            schema_validation=ValidationResult(passed=True),
            kind_validation=ValidationResult(passed=True),
            emitted_at=now_iso(),
        )

    def _slot_deny(
        self, req: WriteSlotRequest, code: TierErrorCode, reason: str
    ) -> WriteSlot:
        return WriteSlot(
            request_id=req.request_id,
            verdict="DENY",
            error_code=code.value,
            deny_reason=reason,
            kind_validation=ValidationResult(passed=True),
            schema_validation=ValidationResult(passed=True),
            emitted_at=now_iso(),
        )

    # ------------------------------------------------------------------ A6

    def check_promotion_rule(self, req: PromotionRequest) -> PromotionDecision:
        """A6 CheckPromotionRule · IC-L2-03."""
        key = (req.from_scope, req.to_scope)

        # 1 · skip-level hard deny (session→global)
        if key == ("session", "global"):
            self._try_emit("L1-06:promotion_skip_level_denied", {
                "entry_id": req.entry_id,
                "project_id": req.project_id,
            })
            return PromotionDecision(
                request_id=req.request_id,
                verdict="DENY",
                reason_code="SKIP_LEVEL",
                error_code=TierErrorCode.PROMOTION_SKIP_LEVEL.value,
                deny_reason="cannot skip Project tier",
                emitted_at=now_iso(),
            )

        if key not in _PROMOTION_MATRIX:
            return PromotionDecision(
                request_id=req.request_id,
                verdict="DENY",
                reason_code="INVALID_TRANSITION",
                error_code=TierErrorCode.PROMOTION_SKIP_LEVEL.value,
                deny_reason=f"invalid promotion {req.from_scope}→{req.to_scope}",
                emitted_at=now_iso(),
            )

        rule = _PROMOTION_MATRIX[key]

        # 2 · threshold check
        has_user_override = (
            req.approval.get("type") == "user_explicit"
            and bool(rule["approval_allowed_override"])
        )
        if req.observed_count < int(rule["required_observed_count"]) and not has_user_override:
            return PromotionDecision(
                request_id=req.request_id,
                verdict="DENY",
                reason_code="BELOW_THRESHOLD",
                error_code=TierErrorCode.PROMOTION_BELOW_THRESHOLD.value,
                required_observed_count=int(rule["required_observed_count"]),
                deny_reason=(
                    f"observed_count={req.observed_count} < "
                    f"{rule['required_observed_count']}"
                ),
                emitted_at=now_iso(),
            )

        # 3 · approval required
        if rule["approval_required"] and req.approval.get("type") != "user_explicit":
            return PromotionDecision(
                request_id=req.request_id,
                verdict="DENY",
                reason_code="MISSING_APPROVAL",
                error_code=TierErrorCode.PROMOTION_MISSING_APPROVAL.value,
                required_observed_count=int(rule["required_observed_count"]),
                deny_reason="user_explicit approval required",
                emitted_at=now_iso(),
            )

        # 4 · target tier readiness (Project tier must be activated)
        target_ready = True
        if req.to_scope == "project":
            target_ready = self._tier_repo.is_activated(req.project_id, "project")
            if not target_ready:
                return PromotionDecision(
                    request_id=req.request_id,
                    verdict="DENY",
                    reason_code="TARGET_NOT_READY",
                    error_code=TierErrorCode.TIER_NOT_ACTIVATED.value,
                    target_tier_ready=False,
                    required_observed_count=int(rule["required_observed_count"]),
                    deny_reason="target project tier not activated",
                    emitted_at=now_iso(),
                )

        # 5 · build decision
        if req.to_scope == "global":
            target_path = "global_kb/entries/"
            override_owner: str | None = None  # INV-8
        else:
            target_path = f"projects/{req.project_id}/kb/entries/"
            override_owner = req.project_id

        self._try_emit("L1-06:kb_promotion_allowed", {
            "entry_id": req.entry_id,
            "from_scope": req.from_scope,
            "to_scope": req.to_scope,
            "project_id": req.project_id,
        })

        return PromotionDecision(
            request_id=req.request_id,
            verdict="ALLOW",
            reason_code="OK",
            expected_write_path=target_path,
            target_tier_ready=target_ready,
            required_observed_count=int(rule["required_observed_count"]),
            override_owner_project_id=override_owner,
            emitted_at=now_iso(),
        )

    # ------------------------------------------------------------------ A7

    def run_expire_scan(self, trigger: ExpireScanTrigger) -> ExpireScanSummary:
        """A7 ExpirationScanner · IC-L2-07."""
        start = time.perf_counter()
        cutoff = self._now() - timedelta(days=trigger.ttl_days)
        summary = ExpireScanSummary(trigger_id=trigger.trigger_id)

        if trigger.scan_mode == "single_project":
            pids = (
                [trigger.target_project_id]
                if trigger.target_project_id
                else []
            )
        else:
            pids = self._tier_repo.list_all_projects()

        for pid in pids:
            if not pid:
                continue
            summary.scanned_project_count += 1
            for file in self._iter_session_files(pid):
                try:
                    for line_no, raw in enumerate(file.read_text().splitlines(), 1):
                        if not raw.strip():
                            continue
                        try:
                            entry = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        summary.scanned_entry_count += 1
                        last_obs = entry.get("last_observed_at", "")
                        if last_obs and _is_before(last_obs, cutoff):
                            summary.expired_marked_count += 1
                            self._append_expire_mark(
                                pid=pid,
                                entry_id=entry.get("id", ""),
                                cutoff=cutoff,
                                source_file=str(file),
                                source_line=line_no,
                            )
                            self._try_emit(
                                "L1-06:kb_entry_expired",
                                {
                                    "project_id": pid,
                                    "entry_id": entry.get("id", ""),
                                    "cutoff_ts": cutoff.isoformat(),
                                },
                            )
                except OSError as e:
                    summary.warnings.append(
                        {"project_id": pid, "file": str(file), "reason": str(e)}
                    )

        summary.duration_ms = int((time.perf_counter() - start) * 1000)
        self._try_emit("L1-06:expire_scan_completed", summary.to_dict())
        return summary

    def _iter_session_files(self, pid: str) -> list[Path]:
        session_dir = self._fs_root / "task-boards" / pid
        if not session_dir.exists():
            return []
        return sorted(session_dir.glob("*.kb.jsonl"))

    def _append_expire_mark(
        self,
        *,
        pid: str,
        entry_id: str,
        cutoff: datetime,
        source_file: str,
        source_line: int,
    ) -> None:
        kb_dir = self._fs_root / "projects" / pid / "kb"
        kb_dir.mkdir(parents=True, exist_ok=True)
        marks_file = kb_dir / "expire-marks.jsonl"
        payload = {
            "project_id": pid,
            "entry_id": entry_id,
            "marked_at": now_iso(),
            "cutoff_ts": cutoff.isoformat(),
            "source_file": source_file,
            "source_line": source_line,
        }
        with marks_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    # ------------------------------------------------------------------ A8

    def on_project_activated(self, event: ActivateEvent) -> None:
        """A8 ActivateProjectContext · IC-L2-activate."""
        pid = event.project_id
        if not _is_valid_pid(pid):
            return

        # idempotent mkdir + flag + registration (guarded for concurrent races)
        with self._activate_lock:
            session_dir = self._fs_root / "task-boards" / pid
            project_dir = self._fs_root / "projects" / pid / "kb" / "entries"
            global_dir = self._fs_root / "global_kb" / "entries"
            for d in (session_dir, project_dir, global_dir):
                d.mkdir(parents=True, exist_ok=True)

            flag = project_dir.parent / ".tier-ready.flag"
            flag.write_text(
                json.dumps(
                    {
                        "project_id": pid,
                        "activated_at": now_iso(),
                        "source_event": event.event_type,
                    }
                )
            )
            self._tier_repo.set_tier_ready(pid, project=True, global_=True)

        # emit (may fail → degrade + buffer)
        self._emit_kb_tier_ready(
            project_id=pid,
            session_path=str(self._fs_root / "task-boards" / pid) + "/",
            project_path=str(self._fs_root / "projects" / pid / "kb") + "/",
            global_path=str(self._fs_root / "global_kb" / "entries") + "/",
            tier_ready_flag=str(flag),
            activated_at=now_iso(),
        )

    # --------------------------------------------------------- emit helpers

    def _emit_kb_tier_ready(
        self,
        *,
        project_id: str,
        session_path: str,
        project_path: str,
        global_path: str,
        tier_ready_flag: str,
        activated_at: str,
    ) -> None:
        self._try_emit(
            "L1-06:kb_tier_ready",
            {
                "project_id": project_id,
                "session_path": session_path,
                "project_path": project_path,
                "global_path": global_path,
                "tier_ready_flag": tier_ready_flag,
                "activated_at": activated_at,
            },
        )

    def _emit_kb_entry_expired(
        self, *, project_id: str, entry_id: str, expired_at: str
    ) -> None:
        self._try_emit(
            "L1-06:kb_entry_expired",
            {"project_id": project_id, "entry_id": entry_id, "expired_at": expired_at},
        )

    def _emit_cross_project_denied(
        self, *, accessor_pid: str, owner_pid: str, request_id: str
    ) -> None:
        self._try_emit(
            "L1-06:kb_cross_project_denied",
            {
                "accessor_pid": accessor_pid,
                "owner_pid": owner_pid,
                "request_id": request_id,
            },
        )

    # ------------------------------------------------------- degradation

    def _try_emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit via bus; on failure, buffer + upgrade degradation level."""
        try:
            self._event_bus.append(event_type=event_type, payload=payload)
            # success resets the failure budget
            self._bus_fail_count = 0
        except TimeoutError:
            self._bus_fail_count += 1
            self._buffer_in_mem.append({"event_type": event_type, "payload": payload})
            self._persist_emit_buffer(payload.get("project_id", ""), event_type, payload)
            if self._bus_fail_count >= _EVENTBUS_FAIL_BUDGET:
                self._degradation_level = "READ_ONLY_ISOLATION"

    def _persist_emit_buffer(
        self, pid: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        if not pid:
            return
        kb_dir = self._fs_root / "projects" / pid / "kb"
        kb_dir.mkdir(parents=True, exist_ok=True)
        buf_file = kb_dir / ".l201-emit-buffer.jsonl"
        try:
            with buf_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"event_type": event_type, "payload": payload}) + "\n")
        except OSError:
            # fs failure → keep in-memory only; next level degradation handled by caller
            pass

    # ----------------------------------------------- degradation callbacks

    def _on_registry_corrupt(self) -> None:
        """Called by TierLayoutRepo when yaml reload fails (§11 L2 lockdown)."""
        self._degradation_level = "EMERGENCY_LOCKDOWN"

    # --------------------------------------------------------- utilities

    def _now(self) -> datetime:
        """Obtain current UTC time; uses injected ``clock.now()`` for tests."""
        try:
            raw = self._clock.now()
        except Exception:
            raw = datetime.now(UTC)
        now: datetime = raw if isinstance(raw, datetime) else datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now

    def _tier_paths(self, pid: str, session_id: str) -> TierPaths:
        return TierPaths(
            session=f"task-boards/{pid}/{session_id}.kb.jsonl",
            project=f"projects/{pid}/kb/entries/",
            global_=str(self._fs_root / "global_kb" / "entries") + "/",
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_valid_pid(pid: str) -> bool:
    if not pid:
        return False
    return bool(_PID_RE.fullmatch(pid))


def _is_before(ts_str: str, cutoff: datetime) -> bool:
    """Return True when ISO-8601 ``ts_str`` < cutoff. False if unparseable."""
    if not ts_str:
        return False
    try:
        # Accept either "...Z" or "...+HH:MM"
        normalized = ts_str.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed < cutoff
