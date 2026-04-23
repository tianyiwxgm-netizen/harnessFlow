"""L2-02 意图选择器 · 共 ~40 TC.

文档参照:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md
  - docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器-tests.md
  - docs/superpowers/plans/Dev-γ-impl.md §4

错误码覆盖:
  E_INTENT_BOUNDARY_VIOLATION / E_INTENT_NO_AVAILABLE / E_INTENT_KB_TIMEOUT /
  E_INTENT_EXPLANATION_TRUNCATED / E_INTENT_CHAIN_EXHAUSTED / E_INTENT_HARDCODED_SKILL
"""
from __future__ import annotations

import pytest


class TestIntentSchemas:
    """Task 02.1 · Pydantic v2 schemas · SignalScores / ScoredCandidate / Chain / IntentRequest."""

    def test_signal_scores_six_dimensions(self):
        from app.skill_dispatch.intent_selector.schemas import SignalScores

        s = SignalScores(
            availability=True,
            cost=0.8,
            success_rate=0.9,
            failure_memory=0.95,
            recency=0.7,
            kb_boost=0.1,
        )
        assert s.availability is True
        assert 0.0 <= s.cost <= 1.0
        assert 0.0 <= s.success_rate <= 1.0

    def test_signal_scores_reject_out_of_range(self):
        from app.skill_dispatch.intent_selector.schemas import SignalScores

        with pytest.raises(ValueError):
            SignalScores(
                availability=True,
                cost=1.5,   # > 1.0 · 越界
                success_rate=0.9,
                failure_memory=0.9,
                recency=0.7,
                kb_boost=0.0,
            )

    def test_scored_candidate_score_in_unit_interval(self):
        from app.skill_dispatch.intent_selector.schemas import ScoredCandidate, SignalScores
        from app.skill_dispatch.registry.schemas import SkillSpec

        skill = SkillSpec(skill_id="a", availability=True, cost_usd=0.01, timeout_s=30)
        sc = ScoredCandidate(
            skill=skill,
            score=0.75,
            signals=SignalScores(
                availability=True, cost=0.9, success_rate=0.8,
                failure_memory=1.0, recency=0.6, kb_boost=0.0,
            ),
        )
        assert 0.0 <= sc.score <= 1.0

    def test_chain_builtin_fallback_at_tail(self):
        from app.skill_dispatch.intent_selector.schemas import Chain, ScoredCandidate, SignalScores
        from app.skill_dispatch.registry.schemas import SkillSpec

        primary = ScoredCandidate(
            skill=SkillSpec(skill_id="a", availability=True, cost_usd=0.01, timeout_s=30),
            score=0.9,
            signals=SignalScores(
                availability=True, cost=0.9, success_rate=0.8,
                failure_memory=1.0, recency=0.6, kb_boost=0.0,
            ),
        )
        fb = ScoredCandidate(
            skill=SkillSpec(
                skill_id="builtin:a_min",
                availability=True,
                cost_usd=0.0,
                timeout_s=10,
                is_builtin_fallback=True,
            ),
            score=0.3,
            signals=SignalScores(
                availability=True, cost=1.0, success_rate=0.5,
                failure_memory=1.0, recency=0.1, kb_boost=0.0,
            ),
        )
        chain = Chain(primary=primary, fallbacks=[fb], capability="write_test")
        assert chain.primary.skill.skill_id == "a"
        assert chain.fallbacks[-1].skill.is_builtin_fallback

    def test_chain_advance_pops_primary(self):
        """fallback 前进：advance() 返新 chain · primary 从 fallbacks[0] 抬起."""
        from app.skill_dispatch.intent_selector.schemas import Chain, ScoredCandidate, SignalScores
        from app.skill_dispatch.registry.schemas import SkillSpec

        def _sc(sid: str, score: float, is_fb: bool = False):
            return ScoredCandidate(
                skill=SkillSpec(
                    skill_id=sid, availability=True, cost_usd=0.0, timeout_s=30,
                    is_builtin_fallback=is_fb,
                ),
                score=score,
                signals=SignalScores(
                    availability=True, cost=0.5, success_rate=0.5,
                    failure_memory=1.0, recency=0.5, kb_boost=0.0,
                ),
            )

        chain = Chain(
            primary=_sc("a", 0.9),
            fallbacks=[_sc("b", 0.6), _sc("builtin:x", 0.3, is_fb=True)],
            capability="c",
        )
        advanced = chain.advance("timeout")
        assert advanced.primary.skill.skill_id == "b"
        assert len(advanced.fallbacks) == 1
        assert advanced.advance_reason == "timeout"

    def test_chain_advance_exhausted_raises(self):
        from app.skill_dispatch.intent_selector.schemas import (
            Chain,
            ChainExhaustedError,
            ScoredCandidate,
            SignalScores,
        )
        from app.skill_dispatch.registry.schemas import SkillSpec

        solo = ScoredCandidate(
            skill=SkillSpec(skill_id="only", availability=True, cost_usd=0.0, timeout_s=10),
            score=0.5,
            signals=SignalScores(
                availability=True, cost=0.5, success_rate=0.5,
                failure_memory=1.0, recency=0.5, kb_boost=0.0,
            ),
        )
        chain = Chain(primary=solo, fallbacks=[], capability="c")
        with pytest.raises(ChainExhaustedError, match="E_INTENT_CHAIN_EXHAUSTED"):
            chain.advance("all_failed")

    def test_intent_request_requires_project_id(self):
        from app.skill_dispatch.intent_selector.schemas import Constraints, IntentRequest

        with pytest.raises(ValueError):
            IntentRequest(
                project_id="",
                capability="c",
                constraints=Constraints(),
                context={"project_id": ""},
            )

    def test_explanation_card_truncates_over_limit(self):
        """explanation_card 超大自动截断 + 标注."""
        from app.skill_dispatch.intent_selector.schemas import ExplanationCard

        huge_reason = "x" * 5000
        card = ExplanationCard.build(
            why=huge_reason,
            scores={"a": 0.9, "b": 0.6},
            weights={"success_rate": 0.45, "cost": 0.15},
        )
        assert len(card.why) <= 2048
        if len(huge_reason) > 2048:
            assert card.truncated is True
