"""L1-01 L2-02 Decision Engine · KB Booster 单元.

覆盖:
    - 降级路径(kb_enabled=False / 空 snippets / 无 tags)
    - tag 交集正向加权
    - kind 正负符号(pattern vs trap vs anti_pattern)
    - rerank_score / observed_count 饱和
    - clamp MAX_BOOST_ABS
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.kb_booster import (
    KIND_WEIGHTS,
    MAX_BOOST_ABS,
    compute_kb_boost,
)
from app.main_loop.decision_engine.schemas import KBSnippet


class TestKBBoosterDegradation:
    """降级铁律 · KB 不可用时静默返回 0.0 不失败。"""

    def test_TC_W03_KB01_kb_disabled_returns_zero(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """kb_enabled=False → 无论 snippets 是否命中,boost=0.0。"""
        cand = make_candidate(kb_tags=("security", "oss"))
        snip = make_kb_snippet(
            kind="pattern", tags=("security",), rerank_score=0.9, observed_count=8,
        )
        ctx = make_context(kb_enabled=False, kb_snippets=(snip,))
        assert compute_kb_boost(cand, ctx) == 0.0

    def test_TC_W03_KB02_empty_snippets_returns_zero(
        self, make_candidate, make_context,
    ) -> None:
        """kb_enabled=True 但 snippets 为空 → 0.0(降级)。"""
        cand = make_candidate(kb_tags=("x",))
        ctx = make_context(kb_enabled=True, kb_snippets=())
        assert compute_kb_boost(cand, ctx) == 0.0

    def test_TC_W03_KB03_cand_without_kb_tags_returns_zero(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """Candidate 无 kb_tags(无匹配面)→ 0.0。"""
        cand = make_candidate(kb_tags=())
        snip = make_kb_snippet(kind="pattern", tags=("anything",))
        ctx = make_context(kb_snippets=(snip,))
        assert compute_kb_boost(cand, ctx) == 0.0

    def test_TC_W03_KB04_no_tag_intersection_returns_zero(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """candidate.kb_tags 与 snippet.tags 无交集 → 0.0。"""
        cand = make_candidate(kb_tags=("alpha",))
        snip = make_kb_snippet(kind="pattern", tags=("beta",), rerank_score=1.0)
        ctx = make_context(kb_snippets=(snip,))
        assert compute_kb_boost(cand, ctx) == 0.0


class TestKBBoosterPositive:
    """tag 交集 + kind 正向加权。"""

    def test_TC_W03_KB05_single_pattern_hit_positive(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """单个 pattern 命中 1 tag → 正向 boost > 0。"""
        cand = make_candidate(kb_tags=("a",))
        snip = make_kb_snippet(kind="pattern", tags=("a",), rerank_score=0.5)
        ctx = make_context(kb_snippets=(snip,))
        boost = compute_kb_boost(cand, ctx)
        assert boost > 0.0
        assert boost <= MAX_BOOST_ABS

    def test_TC_W03_KB06_multiple_tag_hits_more_boost(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """2 tag 交集 > 1 tag 交集。"""
        cand = make_candidate(kb_tags=("a", "b", "c"))
        snip1 = make_kb_snippet(kind="pattern", tags=("a",))
        snip2 = make_kb_snippet(kind="pattern", tags=("a", "b"))
        ctx1 = make_context(kb_snippets=(snip1,))
        ctx2 = make_context(kb_snippets=(snip2,))
        assert compute_kb_boost(cand, ctx2) > compute_kb_boost(cand, ctx1)

    def test_TC_W03_KB07_rerank_score_contributes(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """相同 tag 交集,rerank_score 越高 boost 越高。"""
        cand = make_candidate(kb_tags=("a",))
        low = make_kb_snippet(kind="pattern", tags=("a",), rerank_score=0.0)
        high = make_kb_snippet(kind="pattern", tags=("a",), rerank_score=1.0)
        b_low = compute_kb_boost(cand, make_context(kb_snippets=(low,)))
        b_high = compute_kb_boost(cand, make_context(kb_snippets=(high,)))
        assert b_high > b_low

    def test_TC_W03_KB08_observed_count_saturates(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """observed_count 饱和:高 count 增量递减。"""
        cand = make_candidate(kb_tags=("a",))
        low = make_kb_snippet(kind="pattern", tags=("a",), observed_count=2)
        high = make_kb_snippet(kind="pattern", tags=("a",), observed_count=64)
        b_low = compute_kb_boost(cand, make_context(kb_snippets=(low,)))
        b_high = compute_kb_boost(cand, make_context(kb_snippets=(high,)))
        # high > low 但差距 < 0.5 (封顶)
        assert b_high > b_low
        assert b_high - b_low < 0.5


class TestKBBoosterNegative:
    """trap / anti_pattern 负向 kind。"""

    def test_TC_W03_KB09_trap_negates_score(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """kind=trap 命中 → boost < 0。"""
        cand = make_candidate(kb_tags=("dangerous",))
        snip = make_kb_snippet(kind="trap", tags=("dangerous",), rerank_score=0.9)
        ctx = make_context(kb_snippets=(snip,))
        boost = compute_kb_boost(cand, ctx)
        assert boost < 0.0

    def test_TC_W03_KB10_anti_pattern_negates_score(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """anti_pattern 比 trap 更负(系数 -1.2 > -1.0 绝对值)。"""
        cand = make_candidate(kb_tags=("x",))
        trap = make_kb_snippet(kind="trap", tags=("x",), rerank_score=0.5)
        anti = make_kb_snippet(kind="anti_pattern", tags=("x",), rerank_score=0.5)
        b_trap = compute_kb_boost(cand, make_context(kb_snippets=(trap,)))
        b_anti = compute_kb_boost(cand, make_context(kb_snippets=(anti,)))
        assert b_anti < b_trap  # anti 更负

    def test_TC_W03_KB11_mixed_positive_negative_sums(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """pattern + trap 相抵消 · 绝对值 < pattern 或 trap 单独值。"""
        cand = make_candidate(kb_tags=("x",))
        pat = make_kb_snippet(kind="pattern", tags=("x",), rerank_score=0.5)
        trap = make_kb_snippet(kind="trap", tags=("x",), rerank_score=0.5)
        b_pat = compute_kb_boost(cand, make_context(kb_snippets=(pat,)))
        b_mixed = compute_kb_boost(cand, make_context(kb_snippets=(pat, trap)))
        assert abs(b_mixed) < b_pat


class TestKBBoosterClamp:
    """MAX_BOOST_ABS clamp(放 10 个 pattern 强命中 · 总和不超 0.50)。"""

    def test_TC_W03_KB12_clamp_upper(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        cand = make_candidate(kb_tags=("a", "b"))
        snippets = tuple(
            make_kb_snippet(
                kind="pattern", tags=("a", "b"), rerank_score=1.0, observed_count=64,
            )
            for _ in range(10)
        )
        boost = compute_kb_boost(cand, make_context(kb_snippets=snippets))
        assert boost == MAX_BOOST_ABS

    def test_TC_W03_KB13_clamp_lower(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        cand = make_candidate(kb_tags=("a", "b"))
        snippets = tuple(
            make_kb_snippet(
                kind="anti_pattern", tags=("a", "b"), rerank_score=1.0, observed_count=64,
            )
            for _ in range(10)
        )
        boost = compute_kb_boost(cand, make_context(kb_snippets=snippets))
        assert boost == -MAX_BOOST_ABS

    def test_TC_W03_KB14_kind_weights_table_sane(self) -> None:
        """KIND_WEIGHTS 表内部不变式:pattern/recipe > 0 · trap/anti < 0。"""
        assert KIND_WEIGHTS["pattern"] > 0
        assert KIND_WEIGHTS["recipe"] > 0
        assert KIND_WEIGHTS["trap"] < 0
        assert KIND_WEIGHTS["anti_pattern"] < 0
