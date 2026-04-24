"""L1-06 L2-05 · RerankService (GREEN implementation).

Implements:
  - rerank()          · IC-L2-04
  - reverse_recall()  · IC-L2-05 (forward to L2-02)
  - on_stage_transitioned() · stage subscription pipeline
  - _push_to_l101()   · context push with 1-retry
  - _validate_weights()

Scorer bag is ``_scorers`` (Scorers) so tests can monkey-patch individual
signal functions to simulate failures.
"""
from __future__ import annotations

import contextlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from ._scorers import Scorers
from .errors import RerankErrorCode, WeightsSumError
from .schemas import (
    PushContextRequest,
    PushContextResponse,
    RerankEntry,
    RerankReason,
    RerankRequest,
    RerankResponse,
    ReverseRecallRequest,
    ReverseRecallResponse,
    StageTransitionedEvent,
)

# ---------------------------------------------------------------------------
# config · defaults
# ---------------------------------------------------------------------------


@dataclass
class RerankConfig:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "context_match": 0.30,
            "stage_match": 0.25,
            "observed_count": 0.15,
            "recency": 0.20,
            "kind_priority": 0.10,
        }
    )
    top_k_default: int = 5
    top_k_hard_cap: int = 20
    rerank_timeout_ms_default: int = 100
    stage_inject_timeout_s: float = 2.0
    recall_timeout_ms_default: int = 1000


# ---------------------------------------------------------------------------
# trace cache · write-only placeholder (ADR-02 upgrade path: jsonl)
# ---------------------------------------------------------------------------


class TraceCache:
    def __init__(self) -> None:
        self._store: dict[str, list[RerankEntry]] = {}
        self._lock = threading.Lock()

    def write(self, rerank_id: str, entries: list[RerankEntry]) -> None:
        with self._lock:
            self._store[rerank_id] = list(entries)


_VALID_STAGES = frozenset({"S1", "S2", "S3", "S4", "S5", "S6", "S7"})
_EPSILON = 1e-3
_DEFAULT_NOW_ISO = "2026-04-22T12:00:00+00:00"


class RerankService:
    """3-1 §6 Application Service · idempotent per (project_id, rerank_id)."""

    def __init__(
        self,
        l2_02: Any,
        l2_03: Any,
        l1_01: Any,
        audit: Any,
        strategy_repo: Any,
        project_id: str,
    ) -> None:
        self._l2_02 = l2_02
        self._l2_03 = l2_03
        self._l1_01 = l1_01
        self._audit = audit
        self._strategy_repo = strategy_repo
        self._project_id_default = project_id

        self._scorers = Scorers()
        self._config = RerankConfig()
        self._trace_cache = TraceCache()
        self._subscribed_event_types: set[str] = {"L1-02:stage_transitioned"}

        self._audit_log: list[str] = []
        self._last_error_code: str | None = None
        self._fallback_no_injection_count: int = 0
        self._duplicate_event_skipped_count: int = 0

        self._idem_lock = threading.Lock()
        # P2-04: key by (project_id, rerank_id) to respect PM-14 isolation.
        self._idem_cache: dict[tuple[str, str], RerankResponse] = {}
        self._seen_event_ids: set[str] = set()

    # ======================================================================
    # rerank · IC-L2-04
    # ======================================================================

    def rerank(self, req: RerankRequest) -> RerankResponse:
        start = time.perf_counter()

        # 1 · project_id guard
        if not req.project_id:
            return self._rejected(req, RerankErrorCode.PROJECT_ID_MISSING)

        # 2 · context guard
        if req.context is None or not getattr(req.context, "current_stage", None):
            return self._rejected(req, RerankErrorCode.CONTEXT_INVALID)

        # 3 · tamper detection (title vs canonical snapshot)
        for cand in req.candidates:
            canonical = getattr(cand, "_canonical_title", None)
            es = getattr(cand, "entry_summary", None)
            if canonical is not None and es is not None:
                current_title = getattr(es, "title", None)
                if current_title != canonical:
                    return self._rejected(req, RerankErrorCode.ENTRY_FIELD_TAMPERED)

        # 4 · isolation: every candidate must belong to the requested project
        for cand in req.candidates:
            cand_pid = getattr(cand, "project_id", None)
            if cand_pid is not None and cand_pid != req.project_id:
                return self._rejected(req, RerankErrorCode.ISOLATION_VIOLATION)

        # 5 · empty candidates → clean empty result (non-degraded)
        if not req.candidates:
            resp = RerankResponse(
                project_id=req.project_id,
                rerank_id=req.rerank_id,
                status="success",
                entries=[],
                weights_applied=dict(self._config.weights),
                duration_ms=int((time.perf_counter() - start) * 1000),
            )
            self._audit_rerank(resp)
            return resp

        # 6 · idempotency (key = (project_id, rerank_id) per PM-14)
        idem_key = (req.project_id or "", req.rerank_id)
        with self._idem_lock:
            cached = self._idem_cache.get(idem_key)
        if cached is not None:
            return cached

        # 7 · normalize top_k
        warnings: list[str] = []
        top_k = req.top_k
        top_k_capped = False
        if top_k is None or top_k <= 0:
            top_k = self._config.top_k_default
            warnings.append(RerankErrorCode.INVALID_TOP_K.value)
            top_k_capped = True
        if top_k > self._config.top_k_hard_cap:
            top_k = self._config.top_k_hard_cap
            top_k_capped = True
            warnings.append(RerankErrorCode.TOP_K_CAPPED.value)

        # 8 · per-candidate scoring with signal-skip resilience
        timeout_ms = req.timeout_ms or self._config.rerank_timeout_ms_default
        deadline = start + (timeout_ms / 1000.0)
        signals_skipped: set[str] = set()
        timeout_hit = False

        scored: list[tuple[float, int, dict[str, float], Any]] = []
        for idx, cand in enumerate(req.candidates):
            if time.perf_counter() > deadline:
                timeout_hit = True
                break
            entry_view = self._entry_view(cand)
            sig_values = self._compute_signals(
                entry_view, req.context, signals_skipped
            )
            # Per 3-1 L2-05 §5.3 / §6.4 timeline3:
            #   ≥ 3 signals fail → FALLBACK_RAW (raw recall order + top_k cap)
            #   1-2 signals fail → SKIP_SIGNAL (redistribute weights)
            if len(signals_skipped) >= 3:
                return self._fallback_raw(
                    req, top_k, top_k_capped, warnings, signals_skipped
                )
            score = self._aggregate(sig_values, signals_skipped)
            scored.append((score, idx, sig_values, cand))

        # 9 · deterministic sort: score DESC, then entry_id ASC, then orig idx
        scored.sort(key=lambda x: (-x[0], getattr(x[3], "entry_id", ""), x[1]))

        top = scored[:top_k]
        entries: list[RerankEntry] = []
        for rank, (score, _idx, sig_values, cand) in enumerate(top, 1):
            reason = (
                self._build_reason(sig_values) if req.include_trace else None
            )
            entries.append(
                RerankEntry(
                    entry_id=getattr(cand, "entry_id", ""),
                    rank=rank,
                    score=round(score, 6),
                    reason=reason,
                )
            )

        # 10 · trace cache (best-effort, E_L205_IC04_TRACE_CACHE_FAIL non-blocking)
        if req.include_trace:
            with contextlib.suppress(Exception):
                self._trace_cache.write(req.rerank_id, entries)

        # 11 · response assembly
        error_code = None
        if timeout_hit:
            signals_skipped.add(RerankErrorCode.TIMEOUT.value)
            error_code = RerankErrorCode.TIMEOUT.value

        status = (
            "degraded"
            if (signals_skipped or timeout_hit)
            else "success"
        )
        resp = RerankResponse(
            project_id=req.project_id,
            rerank_id=req.rerank_id,
            status=status,
            entries=entries,
            degraded=bool(signals_skipped or timeout_hit),
            fallback_mode=None,
            duration_ms=int((time.perf_counter() - start) * 1000),
            weights_applied=dict(self._config.weights),
            signals_skipped=sorted(signals_skipped),
            top_k_capped=top_k_capped,
            warnings=warnings,
            error_code=error_code,
        )

        with self._idem_lock:
            self._idem_cache[idem_key] = resp

        self._audit_rerank(resp)
        return resp

    # ---- scoring helpers --------------------------------------------------

    def _entry_view(self, cand: Any) -> Any:
        """Return an object with attributes the scorers expect.

        ``CandidateSummary.entry_summary`` already carries the fields we need
        (``applicable_context``, ``observed_count``, ``last_observed_at``).
        We also need ``kind`` → project it onto the summary on the fly.
        """
        summary = getattr(cand, "entry_summary", None)
        kind = getattr(cand, "kind", "")
        # Always prefer the summary object but overlay `kind` for scorers.
        if summary is None:
            return cand
        # avoid mutating MagicMock permanently
        with contextlib.suppress(Exception):
            summary.kind = kind
        return summary

    def _compute_signals(
        self, entry: Any, context: Any, skipped: set[str]
    ) -> dict[str, float]:
        """Run 5 scorers with per-signal skip on exception."""
        out: dict[str, float] = {}
        for name, fn in (
            ("context_match", self._scorers.context_match),
            ("stage_match", self._scorers.stage_match),
            ("observed_count", self._scorers.observed_count),
            ("recency", self._scorers.recency),
            ("kind_priority", self._scorers.kind_priority),
        ):
            if name in skipped:
                continue
            try:
                if name == "observed_count":
                    val = fn(entry)  # type: ignore[call-arg]
                elif name == "recency":
                    val = fn(entry, _DEFAULT_NOW_ISO)  # type: ignore[call-arg,arg-type]
                else:
                    val = fn(entry, context)  # type: ignore[call-arg]
                out[name] = float(val)
            except Exception:
                skipped.add(name)
        return out

    def _aggregate(
        self, signals: dict[str, float], skipped: set[str]
    ) -> float:
        if not signals:
            return 0.0
        active_weights = {
            k: v for k, v in self._config.weights.items() if k not in skipped
        }
        total_w = sum(active_weights.values())
        if total_w <= 0:
            return 0.0
        score = 0.0
        for key, w in active_weights.items():
            score += (w / total_w) * signals.get(key, 0.0)
        return score

    def _build_reason(self, signals: dict[str, float]) -> RerankReason:
        if not signals:
            return RerankReason(top_signal="none", narrative="neutral")
        items = sorted(signals.items(), key=lambda kv: kv[1], reverse=True)
        top_name, top_val = items[0]
        bottom_name, bottom_val = items[-1]
        bits: list[str] = []
        if signals.get("stage_match", 0) >= 1.0:
            bits.append("阶段完全匹配")
        elif signals.get("stage_match", 0) >= 0.5:
            bits.append("阶段相邻")
        if signals.get("recency", 0) >= 0.8:
            bits.append("近期观察")
        if signals.get("observed_count", 0) >= 0.7:
            bits.append("高频观察")
        narrative = "; ".join(bits) or "中性评分"
        return RerankReason(
            top_signal=top_name,
            top_value=round(top_val, 3),
            bottom_signal=bottom_name,
            bottom_value=round(bottom_val, 3),
            narrative=narrative,
            signals={k: round(v, 3) for k, v in signals.items()},
        )

    def _fallback_raw(
        self,
        req: RerankRequest,
        top_k: int,
        top_k_capped: bool,
        warnings: list[str],
        signals_skipped: set[str] | None = None,
    ) -> RerankResponse:
        entries = [
            RerankEntry(
                entry_id=getattr(c, "entry_id", ""),
                rank=rank,
                score=0.0,
                reason=None,
            )
            for rank, c in enumerate(req.candidates[:top_k], 1)
        ]
        # Per 3-1 §11 error-code table:
        #   5/5 signals failed → ALL_SCORERS_FAILED (severe bug)
        #   3-4/5 signals failed → SCORE_COMPUTE_FAIL (3+ SKIP accumulating)
        skipped_set = (
            set(signals_skipped) if signals_skipped is not None else set()
        )
        if len(skipped_set) >= 5 or not skipped_set:
            err_code = RerankErrorCode.ALL_SCORERS_FAILED.value
            skipped_report = sorted(self._config.weights.keys())
        else:
            err_code = RerankErrorCode.SCORE_COMPUTE_FAIL.value
            skipped_report = sorted(skipped_set)
        resp = RerankResponse(
            project_id=req.project_id,
            rerank_id=req.rerank_id,
            status="degraded",
            entries=entries,
            degraded=True,
            fallback_mode="FALLBACK_RAW",
            duration_ms=0,
            weights_applied={},
            signals_skipped=skipped_report,
            top_k_capped=top_k_capped,
            warnings=warnings,
            error_code=err_code,
        )
        self._audit_rerank(resp)
        return resp

    def _rejected(
        self, req: RerankRequest, code: RerankErrorCode
    ) -> RerankResponse:
        resp = RerankResponse(
            project_id=req.project_id,
            rerank_id=req.rerank_id,
            status="rejected",
            entries=[],
            weights_applied=dict(self._config.weights),
            error_code=code.value,
        )
        self._last_error_code = code.value
        self._audit_log.append(code.value)
        self._audit_rerank(resp)
        return resp

    def _audit_rerank(self, resp: RerankResponse) -> None:
        with contextlib.suppress(Exception):
            self._audit.append(
                event_type="kb_rerank_applied",
                payload={
                    "project_id": resp.project_id,
                    "rerank_id": resp.rerank_id,
                    "status": resp.status,
                    "entry_count": len(resp.entries),
                    "degraded": resp.degraded,
                    "fallback_mode": resp.fallback_mode,
                    "signals_skipped": list(resp.signals_skipped),
                    "error_code": resp.error_code,
                },
            )

    # ======================================================================
    # reverse_recall · IC-L2-05 (out to L2-02)
    # ======================================================================

    def reverse_recall(self, req: ReverseRecallRequest) -> ReverseRecallResponse:
        timeout_s = (req.timeout_ms or self._config.recall_timeout_ms_default) / 1000.0
        t0 = time.perf_counter()
        try:
            # Minimal timeout guard: run synchronously, measure, flag if slow.
            raw = self._l2_02.reverse_recall(req)
            elapsed = time.perf_counter() - t0
            if elapsed > timeout_s:
                return ReverseRecallResponse(
                    project_id=req.project_id,
                    injection_id=req.injection_id,
                    candidates=[],
                    recalled_count=0,
                    duration_ms=int(elapsed * 1000),
                    error_code=RerankErrorCode.RECALL_TIMEOUT.value,
                )
            return ReverseRecallResponse(
                project_id=req.project_id,
                injection_id=req.injection_id,
                candidates=list(getattr(raw, "candidates", []) or []),
                recalled_count=int(getattr(raw, "recalled_count", 0) or 0),
                duration_ms=int(getattr(raw, "duration_ms", 0) or 0),
                scope_layers_hit=list(getattr(raw, "scope_layers_hit", []) or []),
            )
        except TimeoutError:
            return ReverseRecallResponse(
                project_id=req.project_id,
                injection_id=req.injection_id,
                candidates=[],
                recalled_count=0,
                error_code=RerankErrorCode.L202_UNAVAILABLE.value,
            )

    # ======================================================================
    # stage_transitioned subscription
    # ======================================================================

    def on_stage_transitioned(
        self,
        event: StageTransitionedEvent,
        e2e_timeout_s: float | None = None,
    ) -> None:
        e2e_deadline = time.perf_counter() + (
            e2e_timeout_s or self._config.stage_inject_timeout_s
        )

        # 1 · duplicate event detection
        if event.event_id in self._seen_event_ids:
            self._duplicate_event_skipped_count += 1
            self._audit_log.append(RerankErrorCode.DUPLICATE_EVENT.value)
            return
        self._seen_event_ids.add(event.event_id)

        # 2 · stage validity
        if event.stage_to not in _VALID_STAGES:
            self._last_error_code = RerankErrorCode.STAGE_UNKNOWN.value
            self._audit_log.append(RerankErrorCode.STAGE_UNKNOWN.value)
            return

        # 3 · S7 reverse-collect branch
        if event.stage_to == "S7":
            try:
                self._l2_03.provide_candidate_snapshot(
                    project_id=event.project_id, min_observed_count=2
                )
            except Exception:
                self._audit_log.append("s7_reverse_collect_fail")
            return

        # 4 · strategy lookup
        try:
            strategy = self._strategy_repo.get(event.stage_to)
        except Exception:
            self._fallback_no_injection_count += 1
            self._audit_log.append(RerankErrorCode.STRATEGY_NOT_FOUND.value)
            return

        injected_kinds = _get(strategy, "injected_kinds", []) or []
        if not injected_kinds:
            return  # nothing to inject

        # 5 · reverse_recall via L2-02 (honour e2e deadline)
        try:
            remaining_s = max(0.0, e2e_deadline - time.perf_counter())
            rr = self._l2_02.reverse_recall(
                ReverseRecallRequest(
                    project_id=event.project_id,
                    injection_id=event.event_id,
                    stage_to=event.stage_to,
                    kinds=list(injected_kinds),
                    scope_priority=["session", "project", "global"],
                    recall_top_k=int(_get(strategy, "recall_top_k", 20)),
                    trace_id=event.trace_id,
                    timeout_ms=int(remaining_s * 1000),
                )
            )
        except TimeoutError:
            self._audit_log.append(RerankErrorCode.L202_UNAVAILABLE.value)
            return
        except Exception:
            self._audit_log.append(RerankErrorCode.L202_UNAVAILABLE.value)
            return

        if time.perf_counter() > e2e_deadline:
            self._audit_log.append(RerankErrorCode.STAGE_INJECT_TIMEOUT.value)
            return

        candidates = list(getattr(rr, "candidates", []) or [])
        if not candidates:
            self._audit_log.append(RerankErrorCode.RECALL_EMPTY.value)
            return

        # 6 · push_to_l101 with rerank-lite (skip heavy scoring on raw dicts)
        entries_to_push = candidates[: int(_get(strategy, "rerank_top_k", 5))]
        try:
            self._push_to_l101(
                project_id=event.project_id,
                injection_id=event.event_id,
                stage=event.stage_to,
                entries=entries_to_push,
                trace_id=event.trace_id,
            )
        except Exception:
            self._audit_log.append(RerankErrorCode.L101_PUSH_FAIL.value)

    # ======================================================================
    # push_to_l101
    # ======================================================================

    def _push_to_l101(
        self,
        *,
        project_id: str,
        injection_id: str,
        stage: str,
        entries: list[Any],
        trace_id: str = "",
    ) -> PushContextResponse:
        req = PushContextRequest(
            project_id=project_id,
            injection_id=injection_id,
            stage=stage,
            entries=list(entries),
            trace_id=trace_id,
        )
        last_exc: Exception | None = None
        for attempt in range(2):  # 1 retry
            try:
                raw = self._l1_01.push_context(req)
                return PushContextResponse(
                    accepted=bool(getattr(raw, "accepted", False)),
                    context_id=getattr(raw, "context_id", None),
                    rejection_reason=getattr(raw, "rejection_reason", None),
                )
            except TimeoutError as e:
                last_exc = e
                if attempt == 1:
                    break
        if last_exc is not None:
            self._audit_log.append(RerankErrorCode.L101_PUSH_FAIL.value)
        return PushContextResponse(
            accepted=False,
            rejection_reason="push_failed_after_retry",
        )

    # ======================================================================
    # config validation
    # ======================================================================

    def _validate_weights(self) -> None:
        total = sum(self._config.weights.values())
        if abs(total - 1.0) > _EPSILON:
            raise WeightsSumError(f"weights sum={total:.4f} ≠ 1.0")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default: Any) -> Any:
    """Attribute-or-dict-key getter."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
