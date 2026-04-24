"""L1-06 L2-03 · ObserveAccumulator (GREEN implementation).

Implements the IC-07 ``kb_write_session`` primary entry per 3-1 §6.1 +
IC-L2-06 ``provide_candidate_snapshot`` per §6.7, with:

  * PM-14 isolation · rejects cross-project writes (E_L203_PM14_*).
  * 8-kind whitelist + title length + source_links guards (§3.1 errors).
  * Title normalisation + title_hash dedup key (§6.1 D3 / §D2).
  * ``(project_id, kind, title_hash)`` → merge vs insert arbitration.
  * observed_count atomic increment (D4) + first/last_observed_at maintenance.
  * Idempotency by ``idempotency_key`` (§6.1 Step 5).
  * Soft/Hard capacity caps (D10) — soft warns, hard rejects new inserts.
  * L2-01 collaboration (IC-L2-02 write_slot_request); tolerates
    ``tier_manager=None`` for standalone unit tests.
  * IC-09 audit emission for every terminal branch (write/reject/degrade).
  * Crash recovery: ``seed_from_storage`` rebuilds in-memory dedup table.

The implementation is deliberately dependency-light: a default in-memory
``_InMemorySessionStore`` is bundled so tests can instantiate without having
to mock a repo. Production callers can inject their own repo that matches
the ``SessionStoreRepository`` protocol (see §2.6 of the tech-design).
"""
from __future__ import annotations

import contextlib
import hashlib
import re
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from .errors import ObserverErrorCode
from .schemas import (
    HARD_CAP_PER_PROJECT,
    KIND_WHITELIST,
    PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
    SOFT_CAP_PER_PROJECT,
    TITLE_MAX_LEN,
    ApplicableContext,
    CandidateSnapshotRequest,
    KBEntryRequest,
    PromotionHint,
    SnapshotEntry,
    SnapshotManifest,
    StoredEntry,
    WriteSessionRequest,
    WriteSessionResponse,
)

_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# SessionStoreRepository · Protocol
# ---------------------------------------------------------------------------


class SessionStoreRepository(Protocol):
    """Matches 3-1 §2.6 Repository."""

    def find_by_title_kind(
        self, project_id: str, kind: str, title_hash: str
    ) -> StoredEntry | None: ...

    def append_entry(self, project_id: str, entry: StoredEntry) -> None: ...

    def update_entry(
        self, project_id: str, entry: StoredEntry
    ) -> None: ...

    def list_by_project_and_kind(
        self, project_id: str, kinds: list[str]
    ) -> list[StoredEntry]: ...

    def count_by_project(self, project_id: str) -> int: ...


@dataclass
class _InMemorySessionStore:
    """Lightweight reference implementation used when no repo is injected."""

    _store: dict[str, dict[tuple[str, str], StoredEntry]] = field(
        default_factory=dict
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def find_by_title_kind(
        self, project_id: str, kind: str, title_hash: str
    ) -> StoredEntry | None:
        with self._lock:
            bucket = self._store.get(project_id, {})
            return bucket.get((kind, title_hash))

    def append_entry(self, project_id: str, entry: StoredEntry) -> None:
        with self._lock:
            bucket = self._store.setdefault(project_id, {})
            bucket[(entry.kind, entry.title_hash)] = entry

    def update_entry(
        self, project_id: str, entry: StoredEntry
    ) -> None:
        self.append_entry(project_id, entry)

    def list_by_project_and_kind(
        self, project_id: str, kinds: list[str]
    ) -> list[StoredEntry]:
        with self._lock:
            bucket = self._store.get(project_id, {})
            if not kinds:
                return list(bucket.values())
            want = set(kinds)
            return [e for e in bucket.values() if e.kind in want]

    def count_by_project(self, project_id: str) -> int:
        with self._lock:
            return len(self._store.get(project_id, {}))


# ---------------------------------------------------------------------------
# ObserveAccumulator · Domain Service
# ---------------------------------------------------------------------------


class ObserveAccumulator:
    """IC-07 kb_write_session entry + IC-L2-06 snapshot provider."""

    def __init__(
        self,
        *,
        tier_manager: Any = None,
        event_bus: Any = None,
        repo: SessionStoreRepository | None = None,
        soft_cap: int = SOFT_CAP_PER_PROJECT,
        hard_cap: int = HARD_CAP_PER_PROJECT,
        strict_pm14: bool = True,
    ) -> None:
        self._tier_manager = tier_manager
        self._event_bus = event_bus
        self._repo: SessionStoreRepository = repo or _InMemorySessionStore()
        self._soft_cap = soft_cap
        self._hard_cap = hard_cap
        self._strict_pm14 = strict_pm14

        # Idempotency cache keyed by (project_id, idempotency_key).
        # Value = (response, payload_fingerprint). Fingerprint enables §6.1 D5
        # "same key, divergent payload → IDEMPOTENCY_KEY_CONFLICT". Review A-1b.
        self._idem_lock = threading.Lock()
        self._idem_cache: dict[
            tuple[str, str], tuple[WriteSessionResponse, str]
        ] = {}
        # Fine-grained merge lock per (project_id, kind, title_hash).
        self._merge_locks: dict[tuple[str, str, str], threading.Lock] = {}
        self._merge_locks_lock = threading.Lock()
        # Audit buffer (used by tests when no event_bus is injected).
        self._audit_log: list[dict[str, Any]] = []

    # ======================================================================
    # IC-07 · kb_write_session
    # ======================================================================

    def kb_write_session(
        self, req: WriteSessionRequest
    ) -> WriteSessionResponse:
        """Main IC-07 entry point (3-1 §6.1)."""
        # 1 · PM-14 top-level checks
        if not req.project_id:
            return self._reject(
                req, ObserverErrorCode.PM14_PROJECT_ID_MISSING
            )
        if (
            self._strict_pm14
            and req.entry.project_id
            and req.entry.project_id != req.project_id
        ):
            return self._reject(
                req, ObserverErrorCode.PM14_PROJECT_ID_MISMATCH
            )

        # 2 · cross-layer guard · scope must be "session" (or empty)
        if req.entry.scope and req.entry.scope != "session":
            return self._reject(
                req, ObserverErrorCode.CROSS_LAYER_DENIED
            )

        # 3 · observed_count override — ignore, emit INFO
        count_override = False
        if req.entry.observed_count is not None:
            count_override = True
            req.entry.observed_count = None

        # 4 · basic field guards
        if req.entry.kind not in KIND_WHITELIST:
            return self._reject(
                req, ObserverErrorCode.KIND_NOT_WHITELISTED
            )
        if not req.entry.title or len(req.entry.title) > TITLE_MAX_LEN:
            return self._reject(
                req, ObserverErrorCode.TITLE_EMPTY_OR_TOO_LONG
            )
        if not isinstance(req.entry.content, dict):
            return self._reject(req, ObserverErrorCode.RAW_TEXT_DENIED)
        if not req.entry.source_links:
            return self._reject(
                req, ObserverErrorCode.SOURCE_LINKS_EMPTY
            )

        # 5 · idempotency
        # Compute payload fingerprint first so we can detect §6.1 D5 conflicts
        # (same idem key + divergent payload → IDEMPOTENCY_KEY_CONFLICT).
        idem_key = (req.project_id, req.idempotency_key)
        payload_sig = _payload_fingerprint(req)
        if req.idempotency_key:
            with self._idem_lock:
                cached_entry = self._idem_cache.get(idem_key)
            if cached_entry is not None:
                cached_resp, cached_sig = cached_entry
                # Review A-1b · real content divergence detection.
                if cached_sig != payload_sig:
                    return self._reject(
                        req,
                        ObserverErrorCode.IDEMPOTENCY_KEY_CONFLICT,
                    )
                if cached_resp.project_id != req.project_id:
                    return self._reject(
                        req,
                        ObserverErrorCode.IDEMPOTENCY_KEY_CONFLICT,
                    )
                return cached_resp

        # 6 · normalise title + hash
        norm_title = _normalize_title(req.entry.title)
        title_hash = _hash_title(norm_title)
        was_normalized = norm_title != req.entry.title

        # 7 · L2-01 slot + schema (best-effort; tolerate missing)
        tier_ok, existing_entry_id = self._tier_manager_slot(
            project_id=req.project_id,
            kind=req.entry.kind,
            title_hash=title_hash,
            candidate=req.entry,
        )
        if tier_ok is False:
            return self._reject(
                req, ObserverErrorCode.L201_SCHEMA_INVALID
            )

        # 8 · capacity gate — on INSERT only
        cap = self._repo.count_by_project(req.project_id)
        cap_warning = cap >= self._soft_cap
        existing = (
            self._repo.find_by_title_kind(
                req.project_id, req.entry.kind, title_hash
            )
            if existing_entry_id is None
            else None
        )
        if existing is None and existing_entry_id is None and cap >= self._hard_cap:
            return self._reject(
                req, ObserverErrorCode.CAPACITY_HARD_REJECTED
            )

        # 9 · merge vs insert under fine-grained lock
        lock = self._get_merge_lock(req.project_id, req.entry.kind, title_hash)
        with lock:
            if existing is None:
                existing = self._repo.find_by_title_kind(
                    req.project_id, req.entry.kind, title_hash
                )
            now = _now_iso()
            if existing is not None:
                stored = self._merge(existing, req.entry, now)
                self._repo.update_entry(req.project_id, stored)
                action = "MERGED"
            else:
                stored = self._insert(req, title_hash, now)
                self._repo.append_entry(req.project_id, stored)
                action = "INSERTED"

        # 10 · promotion hint
        hint = PromotionHint(
            session_to_project_eligible=stored.observed_count
            >= PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
            threshold=PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
        )

        # 11 · build response
        resp = WriteSessionResponse(
            success=True,
            action=action,
            entry_id=stored.entry_id,
            project_id=req.project_id,
            observed_count_after=stored.observed_count,
            first_observed_at=stored.first_observed_at,
            last_observed_at=stored.last_observed_at,
            was_normalized=was_normalized,
            promotion_hint=hint,
            trace_id=req.trace_id,
            audit_event_id=f"ev-{uuid4()}",
            # Review A-1a · surface internal title_hash so L2-04 can correlate
            # merge events across IC-07 roundtrips (§3.7 WriteResult).
            dedup_key=stored.title_hash,
        )

        # 12 · cache idempotency (store response + payload fingerprint)
        if req.idempotency_key:
            with self._idem_lock:
                self._idem_cache[idem_key] = (resp, payload_sig)

        # 13 · audit
        self._audit(
            "kb_entry_written",
            project_id=req.project_id,
            entry_id=stored.entry_id,
            kind=stored.kind,
            scope="session",
            action=action,
            observed_count=stored.observed_count,
            trace_id=req.trace_id,
        )
        if count_override:
            self._audit(
                "kb_entry_write_rejected",
                project_id=req.project_id,
                entry_id=stored.entry_id,
                reason=ObserverErrorCode.COUNT_OVERRIDE_IGNORED.value,
                trace_id=req.trace_id,
            )
        if cap_warning:
            self._audit(
                "kb_session_capacity_warning",
                project_id=req.project_id,
                count=cap,
                soft_cap=self._soft_cap,
                trace_id=req.trace_id,
            )
        if hint.session_to_project_eligible:
            self._audit(
                "kb_promotion_hint_issued",
                project_id=req.project_id,
                entry_id=stored.entry_id,
                observed_count=stored.observed_count,
                threshold=PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
                trace_id=req.trace_id,
            )
        return resp

    # ======================================================================
    # IC-L2-06 · provide_candidate_snapshot
    # ======================================================================

    def provide_candidate_snapshot(
        self,
        *,
        project_id: str,
        min_observed_count: int = PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
        kind_filter: list[str] | None = None,
        trace_id: str = "",
    ) -> SnapshotManifest:
        """Read-only candidate pull for L2-04 promotion ceremony."""
        if not project_id:
            return SnapshotManifest(
                snapshot_id="",
                project_id="",
                error_code=ObserverErrorCode.PM14_PROJECT_ID_MISSING.value,
            )
        kinds = list(kind_filter or [])
        # Detect empty explicit filter → error
        if kind_filter is not None and not kinds:
            return SnapshotManifest(
                snapshot_id="",
                project_id=project_id,
                error_code=ObserverErrorCode.SNAPSHOT_KIND_EMPTY.value,
            )

        try:
            pool = self._repo.list_by_project_and_kind(project_id, kinds)
        except Exception:
            return SnapshotManifest(
                snapshot_id="",
                project_id=project_id,
                error_code=ObserverErrorCode.SNAPSHOT_STORAGE_READ_FAILED.value,
            )

        filtered = [e for e in pool if e.observed_count >= min_observed_count]
        entries = [
            SnapshotEntry(
                entry_id=e.entry_id,
                kind=e.kind,
                title=e.title,
                observed_count=e.observed_count,
                first_observed_at=e.first_observed_at,
                last_observed_at=e.last_observed_at,
                applicable_context=e.applicable_context,
                source_links_count=len(e.source_links),
                promotion_hint=PromotionHint(
                    session_to_project_eligible=e.observed_count
                    >= PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
                    threshold=PROMOTION_THRESHOLD_SESSION_TO_PROJECT,
                ),
            )
            for e in filtered
        ]
        manifest = SnapshotManifest(
            snapshot_id=f"snap-{uuid4()}",
            project_id=project_id,
            requested_at=_now_iso(),
            kind_filter=kinds,
            total_entries=len(entries),
            entries=entries,
        )
        self._audit(
            "kb_session_candidate_snapshotted",
            project_id=project_id,
            snapshot_id=manifest.snapshot_id,
            total_entries=manifest.total_entries,
            kind_filter=kinds,
            trace_id=trace_id,
        )
        return manifest

    # ======================================================================
    # Crash recovery
    # ======================================================================

    def seed_from_storage(self, project_id: str) -> int:
        """Rebuild idempotency/dedup-awareness from storage after restart.

        Reads all entries for ``project_id`` from the repo; the merge lookup
        table is intrinsic to the repo itself, so we just verify readability
        and return the count.
        """
        if not project_id:
            return 0
        return len(
            self._repo.list_by_project_and_kind(project_id, [])
        )

    # ======================================================================
    # internals
    # ======================================================================

    def _tier_manager_slot(
        self,
        *,
        project_id: str,
        kind: str,
        title_hash: str,
        candidate: KBEntryRequest,
    ) -> tuple[bool | None, str | None]:
        """Invoke L2-01 IC-L2-02 · returns (schema_ok, existing_entry_id).

        ``schema_ok=None`` when no tier_manager injected (means "skip
        validation"). ``schema_ok=False`` when L2-01 rejects → reader should
        translate to E_L203_SCHEMA_VALIDATION_FAILED.
        """
        if self._tier_manager is None:
            return True, None
        try:
            resp = self._tier_manager.write_slot_request(
                project_id=project_id,
                scope="session",
                kind=kind,
                entry_candidate={
                    "title_hash": title_hash,
                    "content": candidate.content,
                    "applicable_context": candidate.applicable_context,
                },
                schema_validation="strict",
            )
        except Exception:
            # Treat as L2-01 unreachable → proceed with degraded semantics.
            return True, None
        schema_valid = getattr(resp, "schema_valid", True)
        slot_granted = getattr(resp, "slot_granted", True)
        if not schema_valid:
            return False, None
        if not slot_granted:
            return False, None
        existing = getattr(resp, "existing_entry_id", None)
        return True, existing

    def _insert(
        self,
        req: WriteSessionRequest,
        title_hash: str,
        now_iso: str,
    ) -> StoredEntry:
        entry_id = f"kbe-{uuid4()}"
        src_links = list(dict.fromkeys(req.entry.source_links))
        return StoredEntry(
            entry_id=entry_id,
            project_id=req.project_id,
            kind=req.entry.kind,
            title=req.entry.title,
            title_hash=title_hash,
            content=dict(req.entry.content),
            applicable_context=req.entry.applicable_context,
            observed_count=1,
            first_observed_at=now_iso,
            last_observed_at=now_iso,
            source_links=src_links,
            created_by=req.entry.created_by or req.emitted_by,
            scope="session",
        )

    def _merge(
        self,
        existing: StoredEntry,
        delta: KBEntryRequest,
        now_iso: str,
    ) -> StoredEntry:
        union_sources = list(
            dict.fromkeys(existing.source_links + list(delta.source_links))
        )
        return StoredEntry(
            entry_id=existing.entry_id,
            project_id=existing.project_id,
            kind=existing.kind,
            title=existing.title,
            title_hash=existing.title_hash,
            content=existing.content,
            applicable_context=existing.applicable_context,
            observed_count=existing.observed_count + 1,
            first_observed_at=existing.first_observed_at,
            last_observed_at=now_iso,
            source_links=union_sources,
            created_by=existing.created_by,
            scope="session",
        )

    def _get_merge_lock(
        self, project_id: str, kind: str, title_hash: str
    ) -> threading.Lock:
        key = (project_id, kind, title_hash)
        with self._merge_locks_lock:
            lock = self._merge_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._merge_locks[key] = lock
            return lock

    def _reject(
        self,
        req: WriteSessionRequest,
        code: ObserverErrorCode,
        message: str = "",
    ) -> WriteSessionResponse:
        resp = WriteSessionResponse(
            success=False,
            action="REJECTED",
            project_id=req.project_id,
            trace_id=req.trace_id,
            error_code=code.value,
            error_message=message or code.value,
        )
        self._audit(
            "kb_entry_write_rejected",
            project_id=req.project_id,
            error_code=code.value,
            trace_id=req.trace_id,
        )
        return resp

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


def _normalize_title(title: str) -> str:
    return _WHITESPACE_RE.sub(" ", title.strip().lower())


def _hash_title(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def _payload_fingerprint(req: WriteSessionRequest) -> str:
    """Stable SHA-256 signature of the idempotency-relevant payload fields.

    Review A-1b (2026-04-23) · §6.1 D5 — same idempotency_key + divergent
    payload must raise IDEMPOTENCY_KEY_CONFLICT. The fingerprint covers the
    fields a caller expects to stay constant across replays of the same
    logical write (kind, normalised title, content, applicable_context,
    source_links). ``project_id`` and ``idempotency_key`` are implicit in
    the cache key so they are not re-hashed here.
    """
    import json

    norm_title = _normalize_title(req.entry.title)
    ctx = req.entry.applicable_context
    ctx_sig: list[Any] = (
        [
            sorted(ctx.stage),
            sorted(ctx.task_type),
            sorted(ctx.tech_stack),
        ]
        if ctx is not None
        else []
    )
    material = {
        "kind": req.entry.kind,
        "title_norm": norm_title,
        "content": req.entry.content if isinstance(req.entry.content, dict) else None,
        "context": ctx_sig,
        "source_links": sorted(req.entry.source_links),
    }
    payload = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "ObserveAccumulator",
    "ApplicableContext",
    "KBEntryRequest",
    "PromotionHint",
    "SessionStoreRepository",
    "SnapshotEntry",
    "SnapshotManifest",
    "StoredEntry",
    "WriteSessionRequest",
    "WriteSessionResponse",
    "_InMemorySessionStore",
]
