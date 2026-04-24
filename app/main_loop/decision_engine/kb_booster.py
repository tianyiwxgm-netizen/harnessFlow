"""L1-01 L2-02 · KB Booster · 将 KB 片段转换为候选评分增量.

功能:
    - 基于 Candidate.kb_tags 与 KBSnippet.tags 求交集权重
    - 基于 KBSnippet.kind(pattern vs trap vs anti_pattern)正负向加权
    - 聚合 rerank_score + observed_count 做归一
    - 降级:kb_enabled=False 或 ctx.kb_snippets 为空 → 返回 0.0(静默不失败)

对齐 L2-02 §3 KB 读取流程 + prd §9.6 #2 "除非 KB 层失败 · 本 L2 不硬失败"。
本模块不直接调 IC-06,由上游 orchestrator(如 engine.decide)注入 ctx.kb_snippets。
"""
from __future__ import annotations

from .schemas import Candidate, DecisionContext, KBSnippet

# ========== 加权系数 ==========

# kind → 正负符号 & 权重系数
# pattern/recipe/tool_combo/effective_combo 正向;trap/anti_pattern 负向
KIND_WEIGHTS: dict[str, float] = {
    "pattern": 1.0,
    "recipe": 1.0,
    "tool_combo": 0.9,
    "effective_combo": 1.1,
    "project_context": 0.6,
    "external_ref": 0.4,
    "trap": -1.0,
    "anti_pattern": -1.2,
}

# Candidate.kb_tags ∩ KBSnippet.tags 的单标签价值
TAG_INTERSECTION_VALUE = 0.10

# rerank_score 乘数(rerank_score ∈ [0,1] → 最多贡献 0.20)
RERANK_SCORE_MULTIPLIER = 0.20

# observed_count 饱和函数:log-like · +0.05 / doubling
OBSERVED_COUNT_CAP = 0.15

# 单候选的 boost 范围上限(clamp 最终 |boost| ≤ MAX_BOOST_ABS)
MAX_BOOST_ABS = 0.50


def compute_kb_boost(
    candidate: Candidate,
    ctx: DecisionContext,
) -> float:
    """计算 kb_boost ∈ [-MAX_BOOST_ABS, MAX_BOOST_ABS]。

    降级:
        - ctx.kb_enabled=False → 0.0
        - ctx.kb_snippets 为空 → 0.0
        - candidate 无 kb_tags → 0.0(无匹配面)
    """
    if not ctx.kb_enabled:
        return 0.0
    if not ctx.kb_snippets:
        return 0.0
    if not candidate.kb_tags:
        return 0.0

    cand_tags = set(candidate.kb_tags)
    total = 0.0
    for snip in ctx.kb_snippets:
        contribution = _snippet_contribution(snip, cand_tags)
        total += contribution

    # 归一 clamp
    if total > MAX_BOOST_ABS:
        total = MAX_BOOST_ABS
    elif total < -MAX_BOOST_ABS:
        total = -MAX_BOOST_ABS
    return total


def _snippet_contribution(snip: KBSnippet, cand_tags: set[str]) -> float:
    """单个 KB 片段的贡献:仅当 tag 有交集才计数。"""
    if not snip.tags:
        return 0.0
    hit_count = len(cand_tags & set(snip.tags))
    if hit_count == 0:
        return 0.0

    kind_w = KIND_WEIGHTS.get(snip.kind, 0.5)
    # tag 部分
    tag_part = TAG_INTERSECTION_VALUE * hit_count * kind_w
    # rerank 部分
    rerank_part = max(0.0, min(1.0, snip.rerank_score)) * RERANK_SCORE_MULTIPLIER * kind_w
    # observed_count 饱和(每 doubling ≈ +0.05)
    obs_part = _observed_saturation(snip.observed_count) * kind_w
    return tag_part + rerank_part + obs_part


def _observed_saturation(count: int) -> float:
    """count=1 → 0;count=2 → ~0.05;count=4 → ~0.10;封顶 OBSERVED_COUNT_CAP。"""
    if count <= 1:
        return 0.0
    # log2 doubling + cap
    import math
    val = math.log2(count) * 0.05
    if val > OBSERVED_COUNT_CAP:
        val = OBSERVED_COUNT_CAP
    return val


__all__ = [
    "KIND_WEIGHTS",
    "MAX_BOOST_ABS",
    "OBSERVED_COUNT_CAP",
    "RERANK_SCORE_MULTIPLIER",
    "TAG_INTERSECTION_VALUE",
    "compute_kb_boost",
]
