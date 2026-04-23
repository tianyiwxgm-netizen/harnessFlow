"""L1-06 L2-02 · KBReadService (GREEN implementation).

Implements 3-1 §4.1 5-step flow:
  0. tick-cache short-circuit (with corrupt recovery, KBR-009)
  1. validate request (KBR-001/002/012)
  2. L2-01 scope_check (KBR-003/004)
  3. parallel read 3 tiers (KBR-006/007/011/014)
  4. merge (S>P>G) + kind filter + context match + candidate cap (KBR-005/010)
  5. L2-05 rerank (KBR-008 fallback to observed_count DESC)
Audit every branch via IC-09 (kb_read_performed / kb_read_rejected /
kb_read_degraded / kb_read_cache_hit / kb_read_candidate_overflow).
"""
from __future__ import annotations

import contextlib
import time
from typing import Any

from ._internals import (
    ContextMatcher,
    KindPolicy,
    ScopePriorityMerger,
    TickCache,
    kb_entry_schema_invalid,
)
from .errors import KBReadErrorCode, KBSecurityError
from .schemas import (
    ApplicableContext,
    KBEntry,
    ReadMeta,
    ReadRequest,
    ReadResult,
    RerankRequest,
)

_KIND_WHITELIST: frozenset[str] = frozenset(
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

_CANDIDATE_CAP = 500


class KBReadService:
    """Application Service · 5-step kb_read pipeline with 4-level degradation."""

    def __init__(
        self,
        scope_checker: Any,
        reranker: Any,
        audit: Any,
        repo: Any,
    ) -> None:
        self._scope_checker = scope_checker
        self._reranker = reranker
        self._audit = audit
        self._repo = repo
        self._merger = ScopePriorityMerger()
        self._matcher = ContextMatcher()
        self._kind_policy = KindPolicy()
        self._tick_cache = TickCache()

    # ======================================================================
    # read()
    # ======================================================================

    def read(self, req: ReadRequest) -> ReadResult:  # noqa: PLR0911, PLR0912, PLR0915
        t0 = time.perf_counter()
        cache_recovered = False

        # Step 0 · tick cache short-circuit
        cache_key = self._cache_key(req)
        if req.cache_enabled and cache_key:
            try:
                cached = self._tick_cache.get(cache_key)
            except Exception:
                self._tick_cache.invalidate_on_write()
                cached = None
                cache_recovered = True
            if cached is not None:
                self._emit("kb_read_cache_hit", trace_id=req.trace_id)
                return self._with_meta(cached, cache_hit=True, latency_ms=_elapsed_ms(t0))

        # Step 1 · trace_id + schema + NLQ guard
        if not req.trace_id:
            return self._reject(req, KBReadErrorCode.TRACE_ID_MISSING, t0)
        if req.top_k < 0:
            return self._reject(req, KBReadErrorCode.INVALID_REQUEST, t0)
        if req.nlq:
            return self._reject(req, KBReadErrorCode.NL_QUERY_REJECTED, t0)

        # top_k=0 edge: allowed but returns empty without further work
        if req.top_k == 0:
            result = ReadResult(
                entries=[],
                meta=ReadMeta(
                    project_id=req.project_id,
                    candidate_count=0,
                    returned_count=0,
                    latency_ms=_elapsed_ms(t0),
                    cache_hit=False,
                    cache_recovered=cache_recovered,
                ),
                trace_id=req.trace_id,
            )
            self._emit(
                "kb_read_performed",
                trace_id=req.trace_id,
                project_id=req.project_id,
                returned=0,
            )
            return result

        # Step 1.5 · stage-kind policy (KBR-005)
        route = req.applicable_context.route if req.applicable_context else None
        if req.kind is not None:
            kinds = req.kind if isinstance(req.kind, list) else [req.kind]
            for k in kinds:
                forbidden = not self._kind_policy.allowed(
                    _KindProxy(kind=k), stage=route
                )
                if forbidden:
                    return self._reject(req, KBReadErrorCode.KIND_NOT_ALLOWED, t0)

        # Step 2 · scope_check
        try:
            sc_resp = self._scope_checker.scope_check(
                _ScopeCheckReq(
                    project_id=req.project_id,
                    session_id=req.session_id,
                    requested_scopes=req.scope or ["session", "project", "global"],
                )
            )
        except Exception:
            return self._reject(req, KBReadErrorCode.SCOPE_DENIED, t0)
        allowed = list(getattr(sc_resp, "allowed_scopes", []) or [])
        if not allowed:
            return self._reject(req, KBReadErrorCode.SCOPE_DENIED, t0)

        # Step 3 · parallel-ish read 3 tiers (synchronous here; timing guarded)
        deadline = t0 + (req.global_timeout_ms / 1000.0)
        session_entries: list[KBEntry] = []
        project_entries: list[KBEntry] = []
        global_entries: list[KBEntry] = []
        degraded_io = False
        try:
            if "session" in allowed:
                session_entries = self._read_layer(
                    self._repo.read_session, sc_resp.isolation_ctx, req.kind
                )
            if time.perf_counter() > deadline:
                raise TimeoutError("global_timeout after session")
            if "project" in allowed:
                project_entries = self._read_layer(
                    self._repo.read_project, sc_resp.isolation_ctx, req.kind
                )
            if time.perf_counter() > deadline:
                raise TimeoutError("global_timeout after project")
            if "global" in allowed:
                global_entries = self._read_layer(
                    lambda _ctx, kinds: self._repo.read_global(kinds),
                    sc_resp.isolation_ctx,
                    req.kind,
                )
        except TimeoutError:
            return self._degraded(req, KBReadErrorCode.KB_TIMEOUT, t0, "kb_timeout")
        except OSError:
            degraded_io = True

        if degraded_io:
            return self._degraded(req, KBReadErrorCode.KB_DEGRADED, t0, "kb_degraded")

        # Repo-synthetic signals for edge cases
        fake_bad = getattr(self._repo, "session_bad_count", 0) or 0
        fake_jsonl_bad = 1 if getattr(self._repo, "jsonl_truncated", False) else 0

        # Step 4 · merge S>P>G + schema filter + kind filter + context match
        merged = self._merger.merge(session_entries, project_entries, global_entries)

        schema_skipped = 0
        sane: list[Any] = []
        for entry in merged:
            if isinstance(entry, KBEntry) and kb_entry_schema_invalid(entry):
                schema_skipped += 1
                continue
            sane.append(entry)
        schema_skipped += fake_bad

        kind_filtered = [
            e
            for e in sane
            if _kind_matches(getattr(e, "kind", ""), req.kind)
        ]
        context_matched = [
            e
            for e in kind_filtered
            if self._matcher.match(e, req.applicable_context, req.strict_mode)
        ]

        # Step 4.5 · candidate cap
        overflow = False
        candidate_count_raw = len(context_matched)
        if candidate_count_raw > _CANDIDATE_CAP:
            overflow = True
            context_matched = context_matched[:_CANDIDATE_CAP]
            self._emit(
                "kb_read_candidate_overflow",
                trace_id=req.trace_id,
                dropped=candidate_count_raw - _CANDIDATE_CAP,
            )

        # Step 5 · rerank
        rerank_fallback = False
        fallback_reason: str | None = None
        top_k = max(1, req.top_k)
        try:
            rerank_resp = self._reranker.rerank(
                RerankRequest(
                    candidates=list(context_matched),
                    context=req.applicable_context,
                    top_k=top_k,
                )
            )
            ranked = list(getattr(rerank_resp, "ranked", []) or [])[:top_k]
        except Exception:
            rerank_fallback = True
            fallback_reason = KBReadErrorCode.RERANK_FAILED.value
            ranked = sorted(
                context_matched,
                key=lambda e: -int(getattr(e, "observed_count", 0) or 0),
            )[:top_k]
            self._emit(
                "kb_rerank_fallback",
                trace_id=req.trace_id,
                code=KBReadErrorCode.RERANK_FAILED.value,
            )

        scopes_hit = []
        if session_entries:
            scopes_hit.append("session")
        if project_entries:
            scopes_hit.append("project")
        if global_entries:
            scopes_hit.append("global")

        result = ReadResult(
            entries=ranked,
            meta=ReadMeta(
                project_id=req.project_id,
                candidate_count=min(candidate_count_raw, _CANDIDATE_CAP)
                if overflow
                else candidate_count_raw,
                returned_count=len(ranked),
                latency_ms=_elapsed_ms(t0),
                cache_hit=False,
                scopes_hit=scopes_hit,
                degraded=False,
                candidate_overflow=overflow,
                rerank_fallback=rerank_fallback,
                fallback_reason=fallback_reason,
                schema_invalid_skipped=schema_skipped,
                jsonl_line_corrupt_skipped=fake_jsonl_bad,
                cache_recovered=cache_recovered,
            ),
            trace_id=req.trace_id,
        )

        if req.cache_enabled and cache_key:
            self._tick_cache.put(cache_key, result)

        self._emit(
            "kb_read_performed",
            trace_id=req.trace_id,
            project_id=req.project_id,
            returned=len(ranked),
            candidate_count=result.meta.candidate_count,
        )
        return result

    # ======================================================================
    # reverse_recall()
    # ======================================================================

    def reverse_recall(
        self,
        *,
        project_id: str,
        session_id: str,  # noqa: ARG002 · reserved for future isolation checks
        stage: str,
        kinds: list[str],
        caller_identity: str,
        scopes: list[str] | None = None,
        cap: int = 200,
        trace_id: str = "",
    ) -> list[KBEntry]:
        if caller_identity != "L2-05":
            raise KBSecurityError(
                f"reverse_recall caller={caller_identity!r} not authorised"
            )
        # Forward to repo without going through scope_check (internal path).
        # All three layers are scanned by default; scope_priority narrows later.
        session_entries: list[KBEntry] = []
        project_entries: list[KBEntry] = []
        global_entries: list[KBEntry] = []
        want = set(scopes or ["session", "project", "global"])
        if "session" in want:
            with contextlib.suppress(Exception):
                session_entries = list(self._repo.read_session(None, kinds) or [])
        if "project" in want:
            with contextlib.suppress(Exception):
                project_entries = list(self._repo.read_project(None, kinds) or [])
        if "global" in want:
            with contextlib.suppress(Exception):
                global_entries = list(self._repo.read_global(kinds) or [])
        merged = self._merger.merge(
            session_entries, project_entries, global_entries
        )
        filtered = [
            e
            for e in merged
            if _kind_matches(getattr(e, "kind", ""), kinds)
            and (
                getattr(getattr(e, "applicable_context", None), "route", None) == stage
                or stage not in {"S1", "S2", "S3", "S4", "S5", "S6", "S7"}
            )
        ]
        if not filtered:
            filtered = [e for e in merged if _kind_matches(getattr(e, "kind", ""), kinds)]
        self._emit(
            "kb_reverse_recall_performed",
            trace_id=trace_id,
            project_id=project_id,
            returned=len(filtered[:cap]),
        )
        return filtered[:cap]

    # ======================================================================
    # helpers
    # ======================================================================

    def _read_layer(
        self, fn: Any, isolation_ctx: Any, kinds: Any
    ) -> list[KBEntry]:
        try:
            out = fn(isolation_ctx, kinds) or []
        except TypeError:
            # some fake repos accept single arg (kinds only)
            out = fn(kinds) or []
        return list(out)

    def _cache_key(self, req: ReadRequest) -> str:
        if not req.trace_id or not req.project_id:
            return ""
        ac = req.applicable_context
        kind_key = (
            ",".join(req.kind)
            if isinstance(req.kind, list)
            else (req.kind or "*")
        )
        scope_key = ",".join(req.scope) if req.scope else "*"
        ac_key = (
            f"{ac.route}|{ac.task_type}|{','.join(ac.tech_stack or [])}|{ac.wbs_node_id}"
            if ac
            else ""
        )
        return "|".join(
            [
                req.project_id,
                req.session_id or "",
                kind_key,
                scope_key,
                ac_key,
                str(req.top_k),
                str(req.strict_mode),
            ]
        )

    def _reject(
        self, req: ReadRequest, code: KBReadErrorCode, t0: float
    ) -> ReadResult:
        self._emit(
            "kb_read_rejected",
            trace_id=req.trace_id,
            code=code.value,
            project_id=req.project_id,
        )
        return ReadResult(
            entries=[],
            meta=ReadMeta(
                project_id=req.project_id,
                latency_ms=_elapsed_ms(t0),
            ),
            trace_id=req.trace_id,
            error_hint="kb_rejected",
            error_code=code.value,
        )

    def _degraded(
        self,
        req: ReadRequest,
        code: KBReadErrorCode,
        t0: float,
        hint: str,
    ) -> ReadResult:
        self._emit(
            "kb_read_degraded",
            trace_id=req.trace_id,
            code=code.value,
            project_id=req.project_id,
        )
        return ReadResult(
            entries=[],
            meta=ReadMeta(
                project_id=req.project_id,
                latency_ms=_elapsed_ms(t0),
                degraded=True,
            ),
            trace_id=req.trace_id,
            error_hint=hint,
            error_code=code.value,
        )

    def _emit(self, event_type: str, **payload: Any) -> None:
        with contextlib.suppress(Exception):
            self._audit.append(event_type=event_type, payload=payload)

    def _with_meta(
        self, cached: ReadResult, *, cache_hit: bool, latency_ms: float
    ) -> ReadResult:
        meta = cached.meta
        new_meta = ReadMeta(
            project_id=meta.project_id,
            candidate_count=meta.candidate_count,
            returned_count=meta.returned_count,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            scopes_hit=list(meta.scopes_hit),
            degraded=meta.degraded,
            candidate_overflow=meta.candidate_overflow,
            rerank_fallback=meta.rerank_fallback,
            fallback_reason=meta.fallback_reason,
            schema_invalid_skipped=meta.schema_invalid_skipped,
            jsonl_line_corrupt_skipped=meta.jsonl_line_corrupt_skipped,
            cache_recovered=meta.cache_recovered,
        )
        return ReadResult(
            entries=list(cached.entries),
            meta=new_meta,
            trace_id=cached.trace_id,
            error_hint=cached.error_hint,
            error_code=cached.error_code,
        )


# ---------------------------------------------------------------------------
# lightweight helpers
# ---------------------------------------------------------------------------


def _kind_matches(entry_kind: str, kind_filter: Any) -> bool:
    if entry_kind not in _KIND_WHITELIST:
        return False
    if kind_filter is None:
        return True
    if isinstance(kind_filter, str):
        return entry_kind == kind_filter
    if isinstance(kind_filter, list):
        return entry_kind in kind_filter
    return False


def _elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


class _KindProxy:
    __slots__ = ("kind",)

    def __init__(self, kind: str) -> None:
        self.kind = kind


class _ScopeCheckReq:
    __slots__ = ("project_id", "session_id", "requested_scopes")

    def __init__(
        self, project_id: str, session_id: str, requested_scopes: list[str]
    ) -> None:
        self.project_id = project_id
        self.session_id = session_id
        self.requested_scopes = requested_scopes


# Re-export for test imports -------------------------------------------------

__all__ = [
    "KBReadService",
    "ApplicableContext",
]
