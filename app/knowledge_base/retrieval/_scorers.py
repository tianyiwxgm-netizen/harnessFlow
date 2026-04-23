"""L1-06 L2-05 · 5-signal scorers (3-1 §6.2).

Each scorer is exposed as a bound method on the ``Scorers`` class so tests
can ``monkeypatch.setattr(sut._scorers, "stage_match", ...)`` without having
to reach into a module-level function table.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

# Stage adjacency · used by stage_match for partial credit on neighbours.
_ADJACENT_STAGES: dict[str, list[str]] = {
    "S1": ["S2"],
    "S2": ["S1", "S3"],
    "S3": ["S2", "S4"],
    "S4": ["S3", "S5"],
    "S5": ["S4", "S6"],
    "S6": ["S5", "S7"],
    "S7": ["S6"],
}

# Stage-specific kind priority table. Order = descending priority.
_KIND_PRIORITY_BY_STAGE: dict[str, list[str]] = {
    "S1": ["trap", "pattern", "recipe"],
    "S2": ["pattern", "recipe", "trap"],
    "S3": ["anti_pattern", "trap", "pattern"],
    "S4": ["pattern", "tool_combo", "recipe"],
    "S5": ["anti_pattern", "trap", "tool_combo"],
    "S6": ["effective_combo", "pattern", "recipe"],
    "S7": ["effective_combo", "pattern"],
}

_DEFAULT_OBSERVED_COUNT_MAX = 100  # log-normalization cap


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        normalized = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


class Scorers:
    """Bound-method scorer bag · monkey-patchable in tests."""

    recency_half_life_days: float = 30.0
    observed_count_max: int = _DEFAULT_OBSERVED_COUNT_MAX

    # ---- S1: context_match ------------------------------------------------

    def context_match(self, entry: Any, context: Any) -> float:
        ac = getattr(entry, "applicable_context", None)
        if ac is None:
            return 0.0
        task_types = list(getattr(ac, "task_types", []) or [])
        tech_stacks = set(getattr(ac, "tech_stacks", []) or [])
        task_type = getattr(context, "task_type", None)
        tech_stack = set(getattr(context, "tech_stack", []) or [])
        task_match = 1.0 if task_type and task_type in task_types else 0.0
        tech_overlap = _jaccard(tech_stack, tech_stacks)
        stages = list(getattr(ac, "stages", []) or [])
        current_stage = getattr(context, "current_stage", None)
        stage_overlap = 1.0 if current_stage and current_stage in stages else 0.0
        return 0.4 * task_match + 0.3 * tech_overlap + 0.3 * stage_overlap

    # ---- S2: stage_match --------------------------------------------------

    def stage_match(self, entry: Any, context: Any) -> float:
        ac = getattr(entry, "applicable_context", None)
        if ac is None:
            return 0.0
        stages = list(getattr(ac, "stages", []) or [])
        current = getattr(context, "current_stage", None)
        if current and current in stages:
            return 1.0
        adj = _ADJACENT_STAGES.get(current or "", [])
        for s in stages:
            if s in adj:
                return 0.5
        return 0.0

    # ---- S3: observed_count -----------------------------------------------

    def observed_count(self, entry: Any, max_count: int | None = None) -> float:
        c = int(getattr(entry, "observed_count", 0) or 0)
        if c <= 0:
            return 0.0
        max_c = max(max_count or self.observed_count_max, 1)
        return min(1.0, math.log(1 + c) / math.log(1 + max_c))

    # ---- S4: recency ------------------------------------------------------

    def recency(self, entry: Any, now_iso: str | None = None) -> float:
        last = _parse_iso(getattr(entry, "last_observed_at", "") or "")
        if last is None:
            return 0.0
        now = _parse_iso(now_iso) if now_iso else datetime.now(UTC)
        if now is None:
            now = datetime.now(UTC)
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        age_days = max(0.0, (now - last).total_seconds() / 86400.0)
        return math.exp(-age_days / self.recency_half_life_days)

    # ---- S5: kind_priority ------------------------------------------------

    def kind_priority(self, entry: Any, context: Any) -> float:
        kind = getattr(entry, "kind", "")
        current = getattr(context, "current_stage", None)
        priority_list = _KIND_PRIORITY_BY_STAGE.get(current or "", [])
        if not priority_list:
            return 0.5  # neutral
        if kind in priority_list:
            idx = priority_list.index(kind)
            return max(0.0, 1.0 - 0.1 * idx)
        return 0.0
