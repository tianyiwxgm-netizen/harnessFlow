"""L2-02 Intent Selector · 入口类 IntentSelector.

编排:
  1. registry.query_candidates(capability)
  2. kb_booster.fetch(pid, capability)  （可选 · 默认用 KBBooster 包 kb · 失败降级空）
  3. scorer.rank(skills, ledger_idx, kb_hits, constraints)
  4. 构造 Chain (primary + fallbacks) · 装配 ExplanationCard
  5. emit IC-09 `capability_chain_produced` 审计事件
"""
from __future__ import annotations

from typing import Any

from ..registry.query_api import NoAvailableCapabilityError, RegistryQueryAPI
from .fallback_advancer import FallbackAdvancer
from .kb_boost import KBBooster
from .schemas import (
    Chain,
    ExplanationCard,
    IntentRequest,
    ScoredCandidate,
)
from .scorer import DEFAULT_WEIGHTS, Scorer

__all__ = ["IntentSelector"]


class IntentSelector:
    """L2-02 对外主入口 · select(request) → Chain."""

    def __init__(
        self,
        *,
        registry: RegistryQueryAPI,
        event_bus: Any,
        kb: Any | None = None,
        kb_booster: KBBooster | None = None,
        scorer: Scorer | None = None,
    ) -> None:
        self._registry = registry
        self._bus = event_bus
        self._scorer = scorer or Scorer()
        if kb_booster is not None:
            self._kb = kb_booster
        elif kb is not None:
            self._kb = KBBooster(kb=kb, timeout_ms=150)
        else:
            self._kb = None
        self.advancer = FallbackAdvancer(event_bus=event_bus)

    def select(self, request: IntentRequest) -> Chain:
        """主入口 · 产链 · emit IC-09 · PM-14 pid 已由 IntentRequest 校验."""
        skills = self._registry.query_candidates(request.capability)
        ledger_idx = self._registry.snapshot.ledger_index
        kb_hits: dict[str, float] = {}
        if self._kb is not None:
            kb_hits = self._kb.fetch(project_id=request.project_id, capability=request.capability)
        ranked: list[ScoredCandidate] = self._scorer.rank(
            skills=skills,
            ledger_idx=ledger_idx,
            kb_hits=kb_hits,
            constraints=request.constraints,
        )
        if not ranked:
            # P0 契约红线：全链失败不 raise 泛型 RuntimeError · 改抛
            # NoAvailableCapabilityError（CapabilityNotFoundError 子类）· 让
            # SkillExecutor Phase 1 原有捕获路径直接落 success=false · 不逃逸给调用方.
            raise NoAvailableCapabilityError(
                f"E_INTENT_NO_AVAILABLE: no candidate passed constraints · "
                f"capability={request.capability}"
            )
        primary = ranked[0]
        fallbacks = ranked[1:]
        chain = Chain(capability=request.capability, primary=primary, fallbacks=fallbacks)
        self._emit_chain_produced(request, chain)
        return chain

    def _emit_chain_produced(self, request: IntentRequest, chain: Chain) -> None:
        try:
            explanation = ExplanationCard.build(
                why=(
                    f"primary={chain.primary.skill.skill_id} "
                    f"(score={chain.primary.score:.3f}) "
                    f"fallbacks={[c.skill.skill_id for c in chain.fallbacks]}"
                ),
                scores={
                    chain.primary.skill.skill_id: chain.primary.score,
                    **{c.skill.skill_id: c.score for c in chain.fallbacks},
                },
                weights=dict(DEFAULT_WEIGHTS),
            )
            self._bus.append_event(
                project_id=request.project_id,
                l1="L1-05",
                event_type="capability_chain_produced",
                payload={
                    "capability": request.capability,
                    "primary": chain.primary.skill.skill_id,
                    "fallbacks": [c.skill.skill_id for c in chain.fallbacks],
                    "explanation": {
                        "why": explanation.why,
                        "scores": explanation.scores,
                        "truncated": explanation.truncated,
                    },
                },
            )
        except Exception:
            pass
