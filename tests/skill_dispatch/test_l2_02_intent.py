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


class TestHardEdgeScan:
    """Task 02.2 · 启动硬编码扫描 · PM-09 红线：禁 superpowers/gstack/ecc/plugin:* 字面量."""

    def test_scan_passes_clean_tree(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan

        (tmp_path / "good.py").write_text('CAPABILITY = "write_test"\n', encoding="utf-8")
        # 不抛
        HardEdgeScan(roots=[tmp_path]).run()

    def test_scan_crashes_on_superpowers_literal(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import (
            HardcodedSkillViolation,
            HardEdgeScan,
        )

        bad = tmp_path / "offender.py"
        bad.write_text('SKILL = "superpowers:tdd-workflow"\n', encoding="utf-8")
        with pytest.raises(HardcodedSkillViolation, match="offender.py"):
            HardEdgeScan(roots=[tmp_path]).run()

    def test_scan_catches_gstack_and_ecc_patterns(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import (
            HardcodedSkillViolation,
            HardEdgeScan,
        )

        (tmp_path / "gs.py").write_text('S = "gstack:x"\n', encoding="utf-8")
        (tmp_path / "ec.py").write_text('S = "ecc:y"\n', encoding="utf-8")
        (tmp_path / "pl.py").write_text('S = "plugin:z"\n', encoding="utf-8")
        with pytest.raises(HardcodedSkillViolation) as ei:
            HardEdgeScan(roots=[tmp_path]).run()
        msg = str(ei.value)
        assert "gs.py" in msg and "ec.py" in msg and "pl.py" in msg

    def test_scan_ignores_tests_and_mocks_and_cache(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan

        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text('X = "superpowers:ok"\n', encoding="utf-8")
        (tmp_path / "_mocks").mkdir()
        (tmp_path / "_mocks" / "m.py").write_text('X = "superpowers:ok"\n', encoding="utf-8")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "c.py").write_text('X = "superpowers:ok"\n', encoding="utf-8")
        # tests / _mocks / __pycache__ 均被默认 ignore · 不抛
        HardEdgeScan(roots=[tmp_path]).run()

    def test_scan_reports_all_violations_not_first(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import (
            HardcodedSkillViolation,
            HardEdgeScan,
        )

        for i in range(3):
            (tmp_path / f"o{i}.py").write_text(f'S = "superpowers:x{i}"\n', encoding="utf-8")
        with pytest.raises(HardcodedSkillViolation) as ei:
            HardEdgeScan(roots=[tmp_path]).run()
        msg = str(ei.value)
        # 3 个文件都应在 violation list
        for i in range(3):
            assert f"o{i}.py" in msg, f"missing o{i}.py in {msg}"

    def test_scan_honors_custom_ignore(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan

        (tmp_path / "bench").mkdir()
        (tmp_path / "bench" / "b.py").write_text('X = "superpowers:benchmark"\n', encoding="utf-8")
        # 自定义 ignore=["bench"] · 不抛
        HardEdgeScan(roots=[tmp_path], ignore=["bench"]).run()


# ----------------------------------------------------------------------------
# Test helpers for scorer/rank tests
# ----------------------------------------------------------------------------

def _mk_skill(skill_id="s", cost=0.01, timeout=30, is_fb=False, avail=True):
    from app.skill_dispatch.registry.schemas import SkillSpec
    return SkillSpec(
        skill_id=skill_id,
        availability=avail,
        cost_usd=cost,
        timeout_s=timeout,
        is_builtin_fallback=is_fb,
    )


def _mk_ledger(capability="c", skill_id="s", success=0, fail=0, last_ts=0, reason=None):
    from app.skill_dispatch.registry.schemas import LedgerEntry
    return LedgerEntry(
        capability=capability,
        skill_id=skill_id,
        success_count=success,
        failure_count=fail,
        last_attempt_ts=last_ts,
        failure_reason=reason,
    )


class TestScorer:
    """Task 02.3 · 6 信号打分 · DEFAULT_WEIGHTS 15/45/25/10/5."""

    def test_availability_false_score_is_zero(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer

        scorer = Scorer()
        skill = _mk_skill(avail=False)
        sc = scorer.score_candidate(skill, ledger=None, kb_hit_value=0.0)
        assert sc.signals.availability is False
        assert sc.score == 0.0

    def test_cost_score_inverse_linear(self):
        """cost 越高 · cost signal 越低."""
        from app.skill_dispatch.intent_selector.scorer import MAX_COST_REF, Scorer

        scorer = Scorer()
        cheap = scorer.score_candidate(_mk_skill(cost=0.0), None, 0.0)
        mid = scorer.score_candidate(_mk_skill(cost=MAX_COST_REF / 2), None, 0.0)
        expensive = scorer.score_candidate(_mk_skill(cost=MAX_COST_REF), None, 0.0)
        assert cheap.signals.cost > mid.signals.cost > expensive.signals.cost
        assert cheap.signals.cost == 1.0
        assert expensive.signals.cost == 0.0

    def test_success_rate_with_ledger_history(self):
        """无历史（neutral 0.5）vs 有历史（laplace smoothing · 趋向真实率）."""
        from app.skill_dispatch.intent_selector.scorer import Scorer

        scorer = Scorer()
        no_hist = scorer.score_candidate(_mk_skill(), None, 0.0)
        high = scorer.score_candidate(
            _mk_skill(), _mk_ledger(success=50, fail=0), 0.0
        )
        low = scorer.score_candidate(
            _mk_skill(), _mk_ledger(success=0, fail=50), 0.0
        )
        assert no_hist.signals.success_rate == 0.5
        assert high.signals.success_rate > 0.9
        assert low.signals.success_rate < 0.1

    def test_failure_memory_decays_exponentially(self):
        """近期失败 · failure_memory 低；过 24h 后接近 1.0."""
        from app.skill_dispatch.intent_selector.scorer import Scorer

        now = 1_700_000_000
        scorer = Scorer(now_fn=lambda: now)
        recent_fail = _mk_ledger(fail=3, last_ts=now - 60, reason="timeout")   # 1min ago
        stale_fail = _mk_ledger(fail=3, last_ts=now - 7 * 24 * 3600, reason="timeout")  # 7 days ago
        no_fail = _mk_ledger(success=10, fail=0, last_ts=now - 60)

        r = scorer.score_candidate(_mk_skill(), recent_fail, 0.0)
        s = scorer.score_candidate(_mk_skill(), stale_fail, 0.0)
        n = scorer.score_candidate(_mk_skill(), no_fail, 0.0)

        assert r.signals.failure_memory < 0.5, "刚刚失败 · memory 应低"
        assert s.signals.failure_memory > 0.9, "7 日前失败 · memory 已恢复"
        assert n.signals.failure_memory == 1.0, "无失败 · memory 满分"

    def test_recency_newer_scores_higher(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer

        now = 1_700_000_000
        scorer = Scorer(now_fn=lambda: now)
        fresh = scorer.score_candidate(
            _mk_skill(), _mk_ledger(success=1, last_ts=now - 60), 0.0
        )
        stale = scorer.score_candidate(
            _mk_skill(), _mk_ledger(success=1, last_ts=now - 30 * 24 * 3600), 0.0
        )
        assert fresh.signals.recency > stale.signals.recency

    def test_kb_boost_passes_through(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer

        scorer = Scorer()
        sc = scorer.score_candidate(_mk_skill(), None, kb_hit_value=0.8)
        assert sc.signals.kb_boost == 0.8

    def test_kb_boost_clamped_to_unit_interval(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer

        scorer = Scorer()
        sc = scorer.score_candidate(_mk_skill(), None, kb_hit_value=5.0)
        assert sc.signals.kb_boost == 1.0

    def test_default_weights_sum_to_one(self):
        from app.skill_dispatch.intent_selector.scorer import DEFAULT_WEIGHTS

        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"weights sum to {total}, expected 1.0"

    def test_rank_filters_by_max_cost(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer
        from app.skill_dispatch.intent_selector.schemas import Constraints

        scorer = Scorer()
        skills = [_mk_skill(skill_id="cheap", cost=0.01), _mk_skill(skill_id="expensive", cost=10.0)]
        ranked = scorer.rank(
            skills=skills,
            ledger_idx={},
            kb_hits={},
            constraints=Constraints(max_cost_usd=1.0),
        )
        ids = [r.skill.skill_id for r in ranked]
        assert "expensive" not in ids
        assert "cheap" in ids

    def test_rank_filters_by_max_timeout(self):
        from app.skill_dispatch.intent_selector.scorer import Scorer
        from app.skill_dispatch.intent_selector.schemas import Constraints

        scorer = Scorer()
        skills = [_mk_skill(skill_id="fast", timeout=10), _mk_skill(skill_id="slow", timeout=600)]
        ranked = scorer.rank(
            skills=skills,
            ledger_idx={},
            kb_hits={},
            constraints=Constraints(max_timeout_s=60),
        )
        ids = [r.skill.skill_id for r in ranked]
        assert "slow" not in ids

    def test_rank_builtin_fallback_at_tail_even_with_higher_score(self):
        """builtin_fallback 永远排末尾 · 不按 score 排在前."""
        from app.skill_dispatch.intent_selector.scorer import Scorer
        from app.skill_dispatch.intent_selector.schemas import Constraints

        scorer = Scorer()
        # builtin 零成本可能 cost 分最高 · 但必须末尾
        skills = [
            _mk_skill(skill_id="real", cost=0.05, is_fb=False),
            _mk_skill(skill_id="builtin:x", cost=0.0, is_fb=True),
        ]
        ranked = scorer.rank(
            skills=skills,
            ledger_idx={},
            kb_hits={},
            constraints=Constraints(),
        )
        assert len(ranked) == 2
        assert ranked[-1].skill.is_builtin_fallback is True
        assert ranked[0].skill.skill_id == "real"

    def test_rank_scoring_latency_p99_under_30ms(self):
        """SLO: rank 产链 P99 ≤ 30ms · 10 候选 · 100 次采样."""
        import time

        from app.skill_dispatch.intent_selector.scorer import Scorer
        from app.skill_dispatch.intent_selector.schemas import Constraints

        scorer = Scorer()
        skills = [
            _mk_skill(skill_id=f"s{i}", cost=0.01 + i * 0.001, is_fb=(i == 9))
            for i in range(10)
        ]
        durations: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            scorer.rank(skills=skills, ledger_idx={}, kb_hits={}, constraints=Constraints())
            durations.append((time.perf_counter() - t0) * 1000)
        durations.sort()
        p99 = durations[98]
        assert p99 < 30.0, f"rank p99 exceeded 30ms SLO: {p99:.2f}ms"
