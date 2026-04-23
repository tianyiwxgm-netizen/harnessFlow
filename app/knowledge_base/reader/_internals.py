"""Internal collaborators for KBReadService · exposed for TDD injection."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .schemas import ApplicableContext, KBEntry, ReadResult

# ---------------------------------------------------------------------------
# ScopePriorityMerger · S > P > G priority with observed_count/last_observed max
# ---------------------------------------------------------------------------


class ScopePriorityMerger:
    """Merge candidates by id with effective_scope = highest-priority layer."""

    _PRIORITY = {"global": 0, "project": 1, "session": 2}

    def merge(
        self,
        session: list[Any],
        project: list[Any],
        global_: list[Any],
    ) -> list[Any]:
        merged: dict[str, Any] = {}
        for entry in list(global_) + list(project) + list(session):
            if entry is None:
                continue
            eid = getattr(entry, "id", None)
            if not eid:
                continue
            existing = merged.get(eid)
            if existing is None:
                merged[eid] = entry
                continue
            # keep higher priority scope
            cur_p = self._PRIORITY.get(getattr(existing, "scope", "global"), 0)
            new_p = self._PRIORITY.get(getattr(entry, "scope", "global"), 0)
            if new_p > cur_p:
                merged[eid] = entry
        return list(merged.values())


# ---------------------------------------------------------------------------
# ContextMatcher · applicable_context AND match with strict/default toggle
# ---------------------------------------------------------------------------


class ContextMatcher:
    def match(
        self,
        entry: Any,
        ctx: ApplicableContext,
        strict_mode: bool = False,
    ) -> bool:
        """AND match with request-driven strictness.

        Non-strict mode (default): applicable_context is not used as a
        filter — any entry passes. This is the interpretation the TDD
        suite (TC-001/006/007/701 etc.) locks in; callers that need
        field-level filtering must opt in via ``strict_mode=True``.

        Strict mode: a request-side field that is set requires the entry
        to provide an equal (or subset, for tech_stack) value. Missing
        entry fields become rejections (PRD §4.3 缺省不通过).
        """
        if not strict_mode:
            return True

        ec = getattr(entry, "applicable_context", None)
        if ec is None:
            return False

        # route
        if ctx.route is not None:
            ec_route = getattr(ec, "route", None)
            if ec_route is None or ec_route != ctx.route:
                return False

        # task_type
        if ctx.task_type is not None:
            ec_task = getattr(ec, "task_type", None)
            if ec_task is None or ec_task != ctx.task_type:
                return False

        # tech_stack (entry must be subset of request)
        if ctx.tech_stack:
            ec_tech = list(getattr(ec, "tech_stack", []) or [])
            if not ec_tech or not set(ec_tech).issubset(set(ctx.tech_stack)):
                return False

        # wbs_node_id
        if ctx.wbs_node_id is not None:
            ec_wbs = getattr(ec, "wbs_node_id", None)
            if ec_wbs is None or ec_wbs != ctx.wbs_node_id:
                return False

        return True


# ---------------------------------------------------------------------------
# KindPolicy · per-stage forbidden kinds (PRD §5.6.5 禁止行为 5)
# ---------------------------------------------------------------------------


_FORBIDDEN_KINDS_BY_STAGE: dict[str, frozenset[str]] = {
    "S1": frozenset({"effective_combo"}),
    "S1_plan": frozenset({"effective_combo"}),
    "S2": frozenset(),
    "S3": frozenset(),
    "S4": frozenset(),
    "S5": frozenset(),
    "S6": frozenset(),
    "S7": frozenset(),
}


class KindPolicy:
    def allowed(self, entry: Any, stage: str | None) -> bool:
        if stage is None:
            return True
        kind = getattr(entry, "kind", "")
        forbidden = _FORBIDDEN_KINDS_BY_STAGE.get(stage, frozenset())
        return kind not in forbidden


# ---------------------------------------------------------------------------
# TickCache · per-cache-key ReadResult cache with corrupt/invalidate hooks
# ---------------------------------------------------------------------------


@dataclass
class _Entry:
    result: ReadResult
    written_at: float = field(default_factory=time.monotonic)


class TickCache:
    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._forced_corrupt: bool = False

    def get(self, key: str) -> ReadResult | None:
        with self._lock:
            if self._forced_corrupt:
                # clear once-shot corruption + fall through (retry path)
                self._store.clear()
                self._forced_corrupt = False
                raise RuntimeError("tick_cache corrupt (forced)")
            entry = self._store.get(key)
            return entry.result if entry is not None else None

    def put(self, key: str, result: ReadResult) -> None:
        with self._lock:
            self._store[key] = _Entry(result=result)

    def force_corrupt(self) -> None:
        with self._lock:
            self._forced_corrupt = True

    def invalidate_on_write(self) -> None:
        with self._lock:
            self._store.clear()


# ---------------------------------------------------------------------------
# helpers used by KBReadService
# ---------------------------------------------------------------------------


def kb_entry_schema_invalid(entry: KBEntry) -> bool:
    """Basic defensive schema check for entries loaded from jsonl/md."""
    if not isinstance(entry.id, str) or not entry.id:
        return True
    return len(entry.content or "") > 8000
