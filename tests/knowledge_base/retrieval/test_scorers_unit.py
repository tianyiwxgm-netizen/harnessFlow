"""L1-06 L2-05 · Unit tests for individual scorers.

P3-01 follow-up: lift _scorers.py coverage from 67.6% → ≥ 80% by covering
edge branches:
  - _jaccard both-empty / empty-union
  - _parse_iso invalid string / empty
  - context_match missing applicable_context
  - stage_match missing applicable_context / no stage
  - observed_count zero / very large
  - recency missing last_observed_at / invalid now_iso / naive dt
  - kind_priority empty priority list / kind not in list / dynamic step

All scorer functions are pure (take dataclass-like entry + context), so we
use lightweight SimpleNamespace fixtures rather than the heavy SUT stack.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.knowledge_base.retrieval._scorers import (
    _jaccard,
    _parse_iso,
    Scorers,
)


# ---------------------------------------------------------------------------
# _jaccard
# ---------------------------------------------------------------------------


class TestJaccardHelper:
    def test_both_empty_returns_zero(self) -> None:
        assert _jaccard(set(), set()) == 0.0

    def test_union_becomes_empty_via_disjoint_empty(self) -> None:
        # sanity: |a|+|b| = 0 → return 0.0 short-circuit
        assert _jaccard(set(), set()) == 0.0

    def test_full_overlap_returns_one(self) -> None:
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_partial_overlap(self) -> None:
        assert _jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_disjoint_sets_returns_zero(self) -> None:
        assert _jaccard({"a"}, {"b"}) == 0.0


# ---------------------------------------------------------------------------
# _parse_iso
# ---------------------------------------------------------------------------


class TestParseIsoHelper:
    def test_empty_string_returns_none(self) -> None:
        assert _parse_iso("") is None

    def test_invalid_string_returns_none(self) -> None:
        assert _parse_iso("not-a-date") is None

    def test_z_suffix_normalized(self) -> None:
        dt = _parse_iso("2026-04-20T00:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_offset_form(self) -> None:
        dt = _parse_iso("2026-04-20T00:00:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# Scorers.context_match
# ---------------------------------------------------------------------------


class TestContextMatch:
    def test_missing_applicable_context_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(applicable_context=None)
        ctx = SimpleNamespace(task_type="coding", tech_stack=[], current_stage="S3")
        assert s.context_match(entry, ctx) == 0.0

    def test_full_match_all_three_signals(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(
            task_types=["coding"], tech_stacks=["python"], stages=["S3"]
        )
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(
            task_type="coding", tech_stack=["python"], current_stage="S3"
        )
        # 0.4 + 0.3*1.0 + 0.3*1.0 = 1.0
        assert s.context_match(entry, ctx) == pytest.approx(1.0)

    def test_no_task_type_match_partial(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(
            task_types=["other"], tech_stacks=["python"], stages=["S3"]
        )
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(
            task_type="coding", tech_stack=["python"], current_stage="S3"
        )
        # 0.0 + 0.3 + 0.3 = 0.6
        assert s.context_match(entry, ctx) == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# Scorers.stage_match
# ---------------------------------------------------------------------------


class TestStageMatch:
    def test_missing_applicable_context_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(applicable_context=None)
        ctx = SimpleNamespace(current_stage="S3")
        assert s.stage_match(entry, ctx) == 0.0

    def test_exact_match_returns_one(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(stages=["S2", "S3"])
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(current_stage="S3")
        assert s.stage_match(entry, ctx) == 1.0

    def test_adjacent_stage_returns_half(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(stages=["S4"])
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(current_stage="S3")
        assert s.stage_match(entry, ctx) == 0.5

    def test_miss_returns_zero(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(stages=["S6"])
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(current_stage="S3")
        assert s.stage_match(entry, ctx) == 0.0

    def test_no_current_stage_returns_zero(self) -> None:
        s = Scorers()
        ac = SimpleNamespace(stages=["S3"])
        entry = SimpleNamespace(applicable_context=ac)
        ctx = SimpleNamespace(current_stage=None)
        assert s.stage_match(entry, ctx) == 0.0


# ---------------------------------------------------------------------------
# Scorers.observed_count
# ---------------------------------------------------------------------------


class TestObservedCount:
    def test_zero_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(observed_count=0)
        assert s.observed_count(entry) == 0.0

    def test_negative_treated_as_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(observed_count=-5)
        assert s.observed_count(entry) == 0.0

    def test_max_value_returns_one(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(observed_count=s.observed_count_max)
        assert s.observed_count(entry) == pytest.approx(1.0)

    def test_monotonic_increase(self) -> None:
        s = Scorers()
        low = s.observed_count(SimpleNamespace(observed_count=1))
        high = s.observed_count(SimpleNamespace(observed_count=50))
        assert high > low

    def test_custom_max_override(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(observed_count=10)
        # With max_count=10, log(11)/log(11) = 1.0
        assert s.observed_count(entry, max_count=10) == pytest.approx(1.0)

    def test_missing_observed_count_field(self) -> None:
        s = Scorers()
        entry = SimpleNamespace()
        assert s.observed_count(entry) == 0.0


# ---------------------------------------------------------------------------
# Scorers.recency
# ---------------------------------------------------------------------------


class TestRecency:
    def test_missing_last_observed_at_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(last_observed_at=None)
        assert s.recency(entry, now_iso="2026-04-20T00:00:00+00:00") == 0.0

    def test_empty_last_observed_at_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="")
        assert s.recency(entry, now_iso="2026-04-20T00:00:00+00:00") == 0.0

    def test_invalid_last_observed_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="garbage")
        assert s.recency(entry, now_iso="2026-04-20T00:00:00+00:00") == 0.0

    def test_now_iso_invalid_falls_back_to_now(self) -> None:
        """When now_iso is unparseable, use datetime.now(UTC)."""
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="2026-04-20T00:00:00Z")
        # Should not raise. The returned value just needs to be a float in [0,1].
        v = s.recency(entry, now_iso="bad-iso")
        assert 0.0 <= v <= 1.0

    def test_same_time_returns_one(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="2026-04-20T00:00:00+00:00")
        v = s.recency(entry, now_iso="2026-04-20T00:00:00+00:00")
        assert v == pytest.approx(1.0)

    def test_no_now_iso_uses_datetime_now(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="2026-04-20T00:00:00+00:00")
        v = s.recency(entry, now_iso=None)
        assert 0.0 <= v <= 1.0

    def test_naive_last_observed_treated_as_utc(self) -> None:
        """last_observed without tz should be normalised to UTC."""
        s = Scorers()
        entry = SimpleNamespace(last_observed_at="2026-04-20T00:00:00")
        v = s.recency(entry, now_iso="2026-04-20T00:00:00+00:00")
        assert v == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Scorers.kind_priority
# ---------------------------------------------------------------------------


class TestKindPriority:
    def test_no_current_stage_returns_neutral(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(kind="pattern")
        ctx = SimpleNamespace(current_stage=None)
        assert s.kind_priority(entry, ctx) == 0.5

    def test_unknown_stage_returns_neutral(self) -> None:
        s = Scorers()
        entry = SimpleNamespace(kind="pattern")
        ctx = SimpleNamespace(current_stage="S999")
        assert s.kind_priority(entry, ctx) == 0.5

    def test_kind_not_in_priority_list_returns_zero(self) -> None:
        s = Scorers()
        # S1 priority list = [trap, pattern, recipe] — "recipe_unknown" is not there
        entry = SimpleNamespace(kind="recipe_unknown")
        ctx = SimpleNamespace(current_stage="S1")
        assert s.kind_priority(entry, ctx) == 0.0

    def test_dynamic_step_s7_two_items(self) -> None:
        """S7 has ['effective_combo', 'pattern'] → steps 1.0, 0.5."""
        s = Scorers()
        # rank 0
        top = SimpleNamespace(kind="effective_combo")
        ctx = SimpleNamespace(current_stage="S7")
        assert s.kind_priority(top, ctx) == pytest.approx(1.0)
        # rank 1 → 1.0 - 0.5*1 = 0.5
        second = SimpleNamespace(kind="pattern")
        assert s.kind_priority(second, ctx) == pytest.approx(0.5)

    def test_dynamic_step_s1_three_items(self) -> None:
        """S1 list = [trap, pattern, recipe] → steps 1, 2/3, 1/3."""
        s = Scorers()
        ctx = SimpleNamespace(current_stage="S1")
        # rank 0
        assert s.kind_priority(SimpleNamespace(kind="trap"), ctx) == pytest.approx(1.0)
        # rank 1
        assert s.kind_priority(SimpleNamespace(kind="pattern"), ctx) == pytest.approx(
            2 / 3
        )
        # rank 2
        assert s.kind_priority(SimpleNamespace(kind="recipe"), ctx) == pytest.approx(
            1 / 3
        )

    def test_missing_kind_field_returns_zero(self) -> None:
        s = Scorers()
        entry = SimpleNamespace()
        ctx = SimpleNamespace(current_stage="S1")
        assert s.kind_priority(entry, ctx) == 0.0
