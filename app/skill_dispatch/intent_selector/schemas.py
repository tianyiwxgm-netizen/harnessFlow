"""L2-02 意图选择器 Pydantic v2 schemas.

核心 VO:
  SignalScores       — 6 信号打分向量 (availability / cost / success_rate /
                       failure_memory / recency / kb_boost)
  ScoredCandidate    — 单候选 + 加权总分 + 各信号分
  Chain              — 候选链 (primary + fallbacks) · advance() 前进 · 耗尽 raise
  ExplanationCard    — 排序解释 · 自然语言 + 结构化 · 超限截断
  Constraints        — 调用方传入的硬约束 (max_cost, max_timeout, preferred_quality)
  IntentRequest      — select(request) 入参 · PM-14 pid 校验

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md §3
  - docs/superpowers/plans/Dev-γ-impl.md §4 Task 02.1
"""
from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field, model_validator

from ..registry.schemas import SkillSpec

# 解释卡 why 字段最大字符数（超出自动截断 · 标 truncated=True）.
_MAX_WHY_LEN: int = 2048


class SignalScores(BaseModel):
    """6 信号打分向量 · 全部归一化到 [0.0, 1.0] · availability 特例是 bool."""

    model_config = {"frozen": True}

    availability: bool
    cost: float = Field(ge=0.0, le=1.0)             # 权重 15%
    success_rate: float = Field(ge=0.0, le=1.0)     # 权重 45%
    failure_memory: float = Field(ge=0.0, le=1.0)   # 权重 25%（1.0 = 无负面记忆）
    recency: float = Field(ge=0.0, le=1.0)          # 权重 10%
    kb_boost: float = Field(ge=0.0, le=1.0)         # 权重 5%


class ScoredCandidate(BaseModel):
    """单候选的打分结果 · score = weighted_sum(signals) · availability=False 时 score=0."""

    model_config = {"frozen": True}

    skill: SkillSpec
    score: float = Field(ge=0.0, le=1.0)
    signals: SignalScores


class ChainExhaustedError(RuntimeError):
    """E_INTENT_CHAIN_EXHAUSTED · 全链耗尽 · 调用方决定下一步（通常 IC-15 hard_halt）."""


class Chain(BaseModel):
    """候选链 · primary 是首选 · fallbacks 按打分降序 · advance() 生成新 chain."""

    model_config = {"frozen": True}

    capability: str
    primary: ScoredCandidate
    fallbacks: list[ScoredCandidate] = Field(default_factory=list)
    advance_reason: str | None = None

    def advance(self, reason: str) -> Chain:
        """首选失败 · 返新 chain（fallbacks[0] 提升为 primary · 剩余 fallbacks[1:]）.

        链内无 fallback 时 raise `ChainExhaustedError`.
        """
        if not self.fallbacks:
            raise ChainExhaustedError(
                f"E_INTENT_CHAIN_EXHAUSTED: capability={self.capability} reason={reason}"
            )
        return Chain(
            capability=self.capability,
            primary=self.fallbacks[0],
            fallbacks=self.fallbacks[1:],
            advance_reason=reason,
        )


class ExplanationCard(BaseModel):
    """排序解释卡 · 自然语言 why + 结构化各候选分数 + 权重.

    超限 2048 字符自动截断 · truncated=True.
    """

    model_config = {"frozen": True}

    why: str
    scores: dict[str, float]
    weights: dict[str, float]
    truncated: bool = False

    MAX_WHY_LEN: ClassVar[int] = _MAX_WHY_LEN

    @classmethod
    def build(
        cls,
        *,
        why: str,
        scores: dict[str, float],
        weights: dict[str, float],
    ) -> ExplanationCard:
        if len(why) > _MAX_WHY_LEN:
            return cls(
                why=why[:_MAX_WHY_LEN],
                scores=scores,
                weights=weights,
                truncated=True,
            )
        return cls(why=why, scores=scores, weights=weights, truncated=False)


class Constraints(BaseModel):
    """调用方硬约束 · 超出者硬过滤（不降权 · 直接剔）."""

    model_config = {"frozen": True}

    max_cost_usd: float | None = None
    max_timeout_s: int | None = None
    preferred_quality: str | None = None   # e.g. "high" / "low"


class IntentRequest(BaseModel):
    """select(request) 入参 · PM-14 project_id 必填."""

    model_config = {"frozen": True}

    project_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    constraints: Constraints = Field(default_factory=Constraints)
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _pid_mirror(self) -> IntentRequest:
        ctx_pid = self.context.get("project_id")
        if ctx_pid and ctx_pid != self.project_id:
            raise ValueError(
                f"project_id mismatch: top={self.project_id} ctx={ctx_pid} (PM-14)"
            )
        return self
