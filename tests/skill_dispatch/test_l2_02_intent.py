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


class TestKBBoost:
    """Task 02.4 · KB boost (IC-06 旁路) + 150ms 超时降级 (不阻排序)."""

    def test_kb_boost_maps_recipes_to_success_rate(self, kb_mock):
        from app.skill_dispatch._mocks.ic06_mock import KBRecipe
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster

        kb_mock._recipes = [
            KBRecipe(capability="write_test", skill_id="s1", success_rate=0.9, last_seen_ts=0),
            KBRecipe(capability="write_test", skill_id="s2", success_rate=0.7, last_seen_ts=0),
            KBRecipe(capability="other", skill_id="s3", success_rate=0.8, last_seen_ts=0),
        ]
        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        hits = booster.fetch(project_id="p1", capability="write_test")
        assert hits == {"s1": 0.9, "s2": 0.7}
        assert "s3" not in hits

    def test_kb_timeout_degrades_to_empty_dict(self):
        """KB 调用超时 · 返 {} · 不 raise · 不阻 rank."""
        from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster

        slow = IC06KBMock(read_latency_ms=400)
        booster = KBBooster(kb=slow, timeout_ms=150)
        hits = booster.fetch(project_id="p1", capability="c")
        assert hits == {}

    def test_kb_empty_recipes_returns_empty(self, kb_mock):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster

        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        assert booster.fetch(project_id="p1", capability="c") == {}

    def test_kb_requires_project_id(self, kb_mock):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster

        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        with pytest.raises(ValueError, match="project_id"):
            booster.fetch(project_id="", capability="c")

    def test_kb_boost_latency_bounded_even_on_timeout(self):
        """超时场景下 · fetch 自身耗时不能大幅超过 timeout_ms."""
        import time

        from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster

        slow = IC06KBMock(read_latency_ms=5000)
        booster = KBBooster(kb=slow, timeout_ms=150)
        t0 = time.perf_counter()
        booster.fetch(project_id="p1", capability="c")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # 允许一点 overhead · 但不能到 5s
        assert elapsed_ms < 500, f"KB boost exceeded timeout budget: {elapsed_ms:.1f}ms"


class TestFallbackAdvancer:
    """Task 02.5 · advance chain + IC-09 事件 + capability_exhausted."""

    def _chain_with_fallbacks(self):
        from app.skill_dispatch.intent_selector.schemas import (
            Chain,
            ScoredCandidate,
            SignalScores,
        )
        from app.skill_dispatch.registry.schemas import SkillSpec

        def sc(sid, score, is_fb=False):
            return ScoredCandidate(
                skill=SkillSpec(
                    skill_id=sid, availability=True, cost_usd=0.0, timeout_s=30,
                    is_builtin_fallback=is_fb,
                ),
                score=score,
                signals=SignalScores(
                    availability=True, cost=1.0, success_rate=0.5,
                    failure_memory=1.0, recency=0.5, kb_boost=0.0,
                ),
            )

        return Chain(
            primary=sc("a", 0.9),
            fallbacks=[sc("b", 0.6), sc("builtin:x", 0.3, is_fb=True)],
            capability="write_test",
        )

    def test_advance_returns_next_chain(self, ic09_bus):
        from app.skill_dispatch.intent_selector.fallback_advancer import FallbackAdvancer

        adv = FallbackAdvancer(event_bus=ic09_bus)
        chain = self._chain_with_fallbacks()
        new_chain = adv.advance(chain, project_id="p1", reason="timeout")
        assert new_chain.primary.skill.skill_id == "b"
        assert new_chain.advance_reason == "timeout"

    def test_advance_emits_ic09_event(self, ic09_bus):
        from app.skill_dispatch.intent_selector.fallback_advancer import FallbackAdvancer

        adv = FallbackAdvancer(event_bus=ic09_bus)
        chain = self._chain_with_fallbacks()
        adv.advance(chain, project_id="p1", reason="timeout")
        events = ic09_bus.read_all("p1")
        assert any(
            e.event_type == "capability_fallback_advanced" and e.payload.get("reason") == "timeout"
            for e in events
        ), f"expected fallback_advanced event · got {[e.event_type for e in events]}"

    def test_advance_on_exhausted_raises_and_emits_ic15_signal_event(self, ic09_bus):
        """全链耗尽 · raise ChainExhaustedError · 同时 emit capability_exhausted."""
        from app.skill_dispatch.intent_selector.fallback_advancer import FallbackAdvancer
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
                availability=True, cost=1.0, success_rate=0.5,
                failure_memory=1.0, recency=0.5, kb_boost=0.0,
            ),
        )
        chain = Chain(primary=solo, fallbacks=[], capability="c")
        adv = FallbackAdvancer(event_bus=ic09_bus)
        with pytest.raises(ChainExhaustedError):
            adv.advance(chain, project_id="p1", reason="all_failed")
        events = ic09_bus.read_all("p1")
        assert any(e.event_type == "capability_exhausted" for e in events), (
            "expected capability_exhausted event emission"
        )

    def test_advance_requires_project_id(self, ic09_bus):
        from app.skill_dispatch.intent_selector.fallback_advancer import FallbackAdvancer

        adv = FallbackAdvancer(event_bus=ic09_bus)
        chain = self._chain_with_fallbacks()
        with pytest.raises(ValueError, match="project_id"):
            adv.advance(chain, project_id="", reason="x")


class TestIntentSelectorSelect:
    """Task 02.5 · IntentSelector.select(request) 主入口 · 编排 registry + kb + scorer."""

    def _prepare(self, tmp_project, fixtures_dir):
        import shutil

        from app.skill_dispatch.registry.loader import RegistryLoader
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        return RegistryQueryAPI(snapshot=snap)

    def test_select_returns_chain_with_primary_and_fallback(
        self, tmp_project, fixtures_dir, kb_mock, ic09_bus
    ):
        from app.skill_dispatch.intent_selector import IntentSelector
        from app.skill_dispatch.intent_selector.schemas import IntentRequest

        api = self._prepare(tmp_project, fixtures_dir)
        selector = IntentSelector(registry=api, kb_booster=None, kb=kb_mock, event_bus=ic09_bus)
        req = IntentRequest(project_id="p1", capability="write_test", context={"project_id": "p1"})
        chain = selector.select(req)
        assert chain.capability == "write_test"
        assert chain.primary.skill.skill_id == "superpowers:tdd-workflow"
        assert len(chain.fallbacks) == 1
        assert chain.fallbacks[0].skill.is_builtin_fallback

    def test_select_raises_on_empty_pid(self, tmp_project, fixtures_dir, kb_mock, ic09_bus):
        from app.skill_dispatch.intent_selector import IntentSelector
        from app.skill_dispatch.intent_selector.schemas import IntentRequest

        api = self._prepare(tmp_project, fixtures_dir)
        selector = IntentSelector(registry=api, kb_booster=None, kb=kb_mock, event_bus=ic09_bus)
        # IntentRequest 会先 raise ValueError（min_length=1 on project_id）
        with pytest.raises(ValueError):
            IntentRequest(project_id="", capability="c", context={"project_id": ""})
        # direct select 也拒 context mismatch（防御）
        req = IntentRequest(project_id="p1", capability="write_test", context={"project_id": "p1"})
        _ = selector.select(req)  # 正常路径仍应通

    def test_select_capability_unknown_raises(
        self, tmp_project, fixtures_dir, kb_mock, ic09_bus
    ):
        from app.skill_dispatch.intent_selector import IntentSelector
        from app.skill_dispatch.intent_selector.schemas import IntentRequest
        from app.skill_dispatch.registry.query_api import CapabilityNotFoundError

        api = self._prepare(tmp_project, fixtures_dir)
        selector = IntentSelector(registry=api, kb_booster=None, kb=kb_mock, event_bus=ic09_bus)
        req = IntentRequest(project_id="p1", capability="no_such", context={"project_id": "p1"})
        with pytest.raises(CapabilityNotFoundError):
            selector.select(req)

    def test_select_honors_constraints_max_cost(
        self, tmp_project, fixtures_dir, kb_mock, ic09_bus
    ):
        """max_cost 把非 builtin 剔光 · 只留 builtin_fallback."""
        from app.skill_dispatch.intent_selector import IntentSelector
        from app.skill_dispatch.intent_selector.schemas import Constraints, IntentRequest

        api = self._prepare(tmp_project, fixtures_dir)
        selector = IntentSelector(registry=api, kb_booster=None, kb=kb_mock, event_bus=ic09_bus)
        req = IntentRequest(
            project_id="p1",
            capability="write_test",
            constraints=Constraints(max_cost_usd=0.001),   # 只有 builtin (cost=0) 通过
            context={"project_id": "p1"},
        )
        chain = selector.select(req)
        assert chain.primary.skill.is_builtin_fallback is True
        assert chain.fallbacks == []

    def test_select_emits_ic09_chain_produced(
        self, tmp_project, fixtures_dir, kb_mock, ic09_bus
    ):
        from app.skill_dispatch.intent_selector import IntentSelector
        from app.skill_dispatch.intent_selector.schemas import IntentRequest

        api = self._prepare(tmp_project, fixtures_dir)
        selector = IntentSelector(registry=api, kb_booster=None, kb=kb_mock, event_bus=ic09_bus)
        req = IntentRequest(project_id="p1", capability="write_test", context={"project_id": "p1"})
        selector.select(req)
        events = ic09_bus.read_all("p1")
        assert any(e.event_type == "capability_chain_produced" for e in events)
