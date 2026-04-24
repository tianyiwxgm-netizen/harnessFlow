"""L1-01 L2-02 · Decision Engine · 主入口 `decide()`.

流程(线性 5 阶段):
    1. validate_ctx: PM-14 root + state 必含
    2. filter_candidates: guard_expr AST 白名单 · 过滤非 True 候选
    3. score_each: base_score + kb_boost(kb_booster) + history_weight(history_weighter)
    4. pick_top: argmax(final_score)
    5. shape_result: 拼 reason + alternatives + kb_degraded flag

错误码:
    - E_CTX_NO_PROJECT_ID  · project_id 缺失
    - E_CTX_STATE_MISSING  · state 缺失 / 非法
    - E_AST_*              · guard_expr 相关(validator 层已抛)
    - E_DECISION_TYPE_INVALID · 12 类白名单外
    - E_DECISION_NO_CANDIDATE · 全部被否且无 fallback
    - E_DECISION_NO_REASON    · reason 补全失败
"""
from __future__ import annotations

from .ast_validator import safe_eval
from .errors import (
    CtxNoProjectIdError,
    CtxStateMissingError,
    DecisionError,
    DecisionNoCandidateError,
    DecisionNoReasonError,
    InvalidDecisionTypeError,
)
from .history_weighter import compute_history_weight
from .kb_booster import compute_kb_boost
from .schemas import (
    DECISION_TYPES,
    Candidate,
    ChosenAction,
    DecisionContext,
)

# ========== 合法 state 枚举(对齐 L2-02 §3.1 state 字段) ==========

VALID_STATES: frozenset[str] = frozenset({
    "S0_init", "S1_plan", "S2_split", "S3_design",
    "S4_execute", "S5_verify", "S6_wrap",
})

# ========== 常量 ==========

REASON_MIN_LEN = 20


def decide(
    candidates: list[Candidate] | tuple[Candidate, ...],
    ctx: DecisionContext,
) -> ChosenAction:
    """主决策入口。

    Args:
        candidates: 候选列表(顺序不重要;过滤 + 评分后按 final_score 降序)。
        ctx: DecisionContext(PM-14 根 · 含历史 · KB 片段已 prefetch 或 kb_enabled=False)。

    Returns:
        ChosenAction 冻结对象(dataclass frozen=True · 不可变)。

    Raises:
        DecisionError: 各 E_* 错误码。
    """
    # 1. validate_ctx
    _validate_ctx(ctx)

    # 2. filter by AST guard + decision_type whitelist
    surviving = _filter_candidates(candidates, ctx)

    # 3. score_each
    scored: list[tuple[Candidate, float, float, float]] = []
    for cand in surviving:
        kb_boost = compute_kb_boost(cand, ctx)
        hist_weight = compute_history_weight(cand, ctx.history)
        final = cand.base_score + kb_boost + hist_weight
        scored.append((cand, final, kb_boost, hist_weight))

    # 4. pick top
    if not scored:
        if ctx.fallback_candidate is not None:
            fb = ctx.fallback_candidate
            _validate_decision_type(fb)
            fb_kb = 0.0  # fallback 不走 KB(纯降级)
            fb_hist = compute_history_weight(fb, ctx.history)
            fb_final = fb.base_score + fb_kb + fb_hist
            scored = [(fb, fb_final, fb_kb, fb_hist)]
        else:
            raise DecisionNoCandidateError()

    # 按 final_score 降序稳定排序;并列时保持候选原序
    scored.sort(key=lambda item: item[1], reverse=True)

    winner_cand, winner_final, winner_kb, winner_hist = scored[0]

    # 5. shape result
    kb_degraded = not ctx.kb_enabled or not ctx.kb_snippets
    reason_text = _build_reason(
        winner_cand,
        winner_final,
        winner_kb,
        winner_hist,
        kb_degraded=kb_degraded,
    )
    if len(reason_text) < REASON_MIN_LEN:
        raise DecisionNoReasonError(
            f"reason too short: {len(reason_text)} < {REASON_MIN_LEN}"
        )

    # alternatives:最多 top-3(不含被选中者)
    alts_raw = scored[1:4]
    alternatives = tuple((c.decision_type, float(s)) for c, s, _, _ in alts_raw)

    return ChosenAction(
        decision_type=winner_cand.decision_type,
        decision_params=dict(winner_cand.decision_params),
        final_score=float(winner_final),
        kb_boost=float(winner_kb),
        history_weight=float(winner_hist),
        base_score=float(winner_cand.base_score),
        reason=reason_text,
        kb_degraded=kb_degraded,
        alternatives=alternatives,
    )


# ========== Stage helpers ==========


def _validate_ctx(ctx: DecisionContext) -> None:
    if not isinstance(ctx, DecisionContext):
        raise DecisionError(
            "E_CTX_INVALID_TYPE",
            f"ctx must be DecisionContext, got {type(ctx).__name__}",
        )
    if not ctx.project_id or not isinstance(ctx.project_id, str):
        raise CtxNoProjectIdError()
    if not ctx.state or ctx.state not in VALID_STATES:
        raise CtxStateMissingError(
            f"state '{ctx.state}' not in {sorted(VALID_STATES)}"
        )


def _validate_decision_type(cand: Candidate) -> None:
    if cand.decision_type not in DECISION_TYPES:
        raise InvalidDecisionTypeError(cand.decision_type)


def _filter_candidates(
    candidates: list[Candidate] | tuple[Candidate, ...],
    ctx: DecisionContext,
) -> list[Candidate]:
    """对每个候选:
    - 校验 decision_type 白名单(非法 → 立即抛,严格模式)
    - 若 guard_expr 非空 → safe_eval(env=ctx.guard_vars);False 丢弃
    - 非 guard_expr 的候选直接保留
    """
    out: list[Candidate] = []
    for cand in candidates:
        _validate_decision_type(cand)
        if cand.guard_expr:
            env = dict(ctx.guard_vars)
            # 白名单决策 eval · 禁危险
            result = safe_eval(cand.guard_expr, env)
            if not result:
                continue
        out.append(cand)
    return out


def _build_reason(
    cand: Candidate,
    final: float,
    kb_boost: float,
    hist_weight: float,
    *,
    kb_degraded: bool,
) -> str:
    """拼接 reason(≥ 20 字)。

    模板:"<cand.reason | auto>; score=<base>+kb(<kb>)+hist(<hist>)=<final>[; kb_degraded]"
    """
    head = cand.reason.strip() if cand.reason and cand.reason.strip() else (
        f"auto decision: {cand.decision_type}"
    )
    body = (
        f"score={cand.base_score:.3f}+kb({kb_boost:+.3f})"
        f"+hist({hist_weight:+.3f})={final:.3f}"
    )
    tail = "; kb_degraded" if kb_degraded else ""
    return f"{head}; {body}{tail}"


__all__ = [
    "REASON_MIN_LEN",
    "VALID_STATES",
    "decide",
]
