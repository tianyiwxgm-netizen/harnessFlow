"""L2-02 6 信号打分器 + rank() 排序.

打分维度与默认权重（PRD）:
  availability    硬过滤（非权重 · False → score=0 · True 参与加权）
  cost            15%   · 越低越好（线性反比 · 基准 MAX_COST_REF=5.0 USD）
  success_rate    45%   · Laplace smoothing: (s+1)/(s+f+2) · 无历史返中性 0.5
  failure_memory  25%   · 指数衰减（半衰期 24h）· 无失败 1.0 · 刚失败趋 0
  recency         10%   · 越近越高（7 日半衰期）
  kb_boost         5%   · KB Recipe 命中（0..1）

rank(skills, ledger_idx, kb_hits, constraints):
  1. 硬约束过滤（availability / max_cost / max_timeout / preferred_quality）
  2. 逐一 score_candidate
  3. 非 builtin 按 score desc · builtin_fallback 始终排末尾（按 score desc 放入末尾段）

SLO:
  rank 产链 P99 ≤ 30ms（10 候选 · 见 test_rank_scoring_latency_p99_under_30ms）

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §4 Task 02.3
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable

from ..registry.schemas import LedgerEntry, SkillSpec
from .schemas import Constraints, ScoredCandidate, SignalScores


# 用于 cost 归一化的参考上限 · 可由 weights 配置覆盖.
MAX_COST_REF: float = 5.0

# 24 小时半衰期（秒）· failure_memory 衰减.
_FAIL_HALF_LIFE_S: float = 24.0 * 3600.0

# 7 日半衰期 · recency 衰减.
_RECENCY_HALF_LIFE_S: float = 7.0 * 24.0 * 3600.0

DEFAULT_WEIGHTS: dict[str, float] = {
    "cost": 0.15,
    "success_rate": 0.45,
    "failure_memory": 0.25,
    "recency": 0.10,
    "kb_boost": 0.05,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _exp_decay(elapsed_s: float, half_life_s: float) -> float:
    """指数衰减: 半衰期 half_life_s · elapsed=0 返 0.0 · elapsed→∞ 趋 1.0."""
    if elapsed_s <= 0:
        return 0.0
    # decay = 1 - 2^(-elapsed / half_life)
    return 1.0 - math.pow(2.0, -elapsed_s / half_life_s)


class Scorer:
    """打分 + 排序器 · 纯函数式 · 便于单测."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.now_fn = now_fn

    # -------- signal 计算 --------
    def _signal_cost(self, cost_usd: float) -> float:
        if MAX_COST_REF <= 0:
            return 1.0
        return _clamp(1.0 - cost_usd / MAX_COST_REF)

    def _signal_success_rate(self, ledger: LedgerEntry | None) -> float:
        if ledger is None:
            return 0.5   # neutral prior
        s, f = ledger.success_count, ledger.failure_count
        # Laplace smoothing
        return _clamp((s + 1) / (s + f + 2))

    def _signal_failure_memory(self, ledger: LedgerEntry | None) -> float:
        if ledger is None or ledger.failure_count == 0 or not ledger.failure_reason:
            return 1.0
        elapsed = self.now_fn() - ledger.last_attempt_ts
        # 刚刚失败 → 接近 0；过了 half_life → 0.5；远远过 → 趋 1
        return _clamp(_exp_decay(elapsed, _FAIL_HALF_LIFE_S))

    def _signal_recency(self, ledger: LedgerEntry | None) -> float:
        if ledger is None or ledger.last_attempt_ts == 0:
            return 0.5   # neutral for first-time candidate
        elapsed = self.now_fn() - ledger.last_attempt_ts
        # 越近 recency 越高 → 返 1 - decay(elapsed, recency_half_life)
        return _clamp(1.0 - _exp_decay(elapsed, _RECENCY_HALF_LIFE_S))

    # -------- 主入口 --------
    def score_candidate(
        self,
        skill: SkillSpec,
        ledger: LedgerEntry | None,
        kb_hit_value: float = 0.0,
    ) -> ScoredCandidate:
        signals = SignalScores(
            availability=skill.availability,
            cost=self._signal_cost(skill.cost_usd),
            success_rate=self._signal_success_rate(ledger),
            failure_memory=self._signal_failure_memory(ledger),
            recency=self._signal_recency(ledger),
            kb_boost=_clamp(kb_hit_value),
        )
        score = 0.0 if not signals.availability else self._weighted_sum(signals)
        return ScoredCandidate(skill=skill, score=_clamp(score), signals=signals)

    def _weighted_sum(self, s: SignalScores) -> float:
        return (
            self.weights.get("cost", 0.0) * s.cost
            + self.weights.get("success_rate", 0.0) * s.success_rate
            + self.weights.get("failure_memory", 0.0) * s.failure_memory
            + self.weights.get("recency", 0.0) * s.recency
            + self.weights.get("kb_boost", 0.0) * s.kb_boost
        )

    # -------- 排序 --------
    def rank(
        self,
        skills: list[SkillSpec],
        ledger_idx: dict[str, LedgerEntry],
        kb_hits: dict[str, float],
        constraints: Constraints,
    ) -> list[ScoredCandidate]:
        """返回符合 constraints 的 ScoredCandidate 列表 · builtin_fallback 永远末尾."""
        filtered = self._apply_constraints(skills, constraints)
        scored = [
            self.score_candidate(
                sk,
                ledger=self._lookup_ledger(sk, ledger_idx),
                kb_hit_value=kb_hits.get(sk.skill_id, 0.0),
            )
            for sk in filtered
        ]
        non_fb = sorted(
            (x for x in scored if not x.skill.is_builtin_fallback),
            key=lambda x: x.score,
            reverse=True,
        )
        fb = sorted(
            (x for x in scored if x.skill.is_builtin_fallback),
            key=lambda x: x.score,
            reverse=True,
        )
        return non_fb + fb

    def _apply_constraints(
        self, skills: list[SkillSpec], constraints: Constraints
    ) -> list[SkillSpec]:
        out = []
        for sk in skills:
            if not sk.availability:
                continue
            if constraints.max_cost_usd is not None and sk.cost_usd > constraints.max_cost_usd:
                continue
            if constraints.max_timeout_s is not None and sk.timeout_s > constraints.max_timeout_s:
                continue
            out.append(sk)
        return out

    @staticmethod
    def _lookup_ledger(
        skill: SkillSpec, ledger_idx: dict[str, LedgerEntry]
    ) -> LedgerEntry | None:
        # ledger_idx key 由 loader 存为 "capability|skill_id"；这里只匹配 skill_id 部分
        for _key, rec in ledger_idx.items():
            if rec.skill_id == skill.skill_id:
                return rec
        return None
