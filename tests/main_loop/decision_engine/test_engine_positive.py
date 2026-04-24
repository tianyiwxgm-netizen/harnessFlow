"""L1-01 L2-02 Decision Engine · engine.decide() 正向用例.

覆盖:
    - 单候选 → 必选
    - 多候选 → argmax(final_score)
    - guard_expr True/False 过滤
    - base_score + kb_boost + history_weight 线性组合
    - alternatives 填充 top-3
    - 降级无 KB 时 kb_degraded=True
    - fallback_candidate 兜底
    - reason 拼接 ≥ 20 字 + kb_degraded 标记
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine import decide
from app.main_loop.decision_engine.engine import REASON_MIN_LEN
from app.main_loop.decision_engine.schemas import ChosenAction


class TestEnginePositive:
    """主流 decide() 正向。"""

    def test_TC_W03_EN01_single_candidate_wins(
        self, make_candidate, make_context,
    ) -> None:
        """单候选 · 必选;kb/history 皆 0(空)→ final=base。"""
        c = make_candidate(decision_type="no_op", base_score=0.5,
                           reason="only candidate")
        ctx = make_context()
        action = decide([c], ctx)
        assert isinstance(action, ChosenAction)
        assert action.decision_type == "no_op"
        assert action.final_score == pytest.approx(0.5)
        assert action.kb_boost == 0.0
        assert action.history_weight == 0.0
        assert action.alternatives == ()
        assert len(action.reason) >= REASON_MIN_LEN

    def test_TC_W03_EN02_argmax_picks_highest(
        self, make_candidate, make_context,
    ) -> None:
        """3 候选 · 选 base_score 最高者。"""
        c1 = make_candidate(decision_type="no_op", base_score=0.3,
                            reason="low priority")
        c2 = make_candidate(decision_type="invoke_skill", base_score=0.9,
                            reason="primary action")
        c3 = make_candidate(decision_type="use_tool", base_score=0.5,
                            reason="mid priority")
        action = decide([c1, c2, c3], make_context())
        assert action.decision_type == "invoke_skill"
        # alternatives 降序,含其他 2 个
        alt_types = [t for t, _ in action.alternatives]
        assert "use_tool" in alt_types
        assert "no_op" in alt_types

    def test_TC_W03_EN03_guard_expr_true_keeps(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 求值 True → 候选被保留。"""
        c = make_candidate(decision_type="invoke_skill", base_score=0.9,
                           guard_expr="state == 'S4_execute'",
                           reason="conditional skill")
        ctx = make_context(state="S4_execute",
                           guard_vars={"state": "S4_execute"})
        action = decide([c], ctx)
        assert action.decision_type == "invoke_skill"

    def test_TC_W03_EN04_guard_expr_false_filters(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 求值 False → 候选被过滤;若只剩 fallback 则取之。"""
        c1 = make_candidate(
            decision_type="invoke_skill",
            base_score=0.9,
            guard_expr="score >= 1.0",
            reason="only when perfect",
        )
        fallback = make_candidate(
            decision_type="no_op",
            base_score=0.1,
            reason="fallback no-op",
        )
        ctx = make_context(
            guard_vars={"score": 0.5},
            fallback_candidate=fallback,
        )
        action = decide([c1], ctx)
        assert action.decision_type == "no_op"

    def test_TC_W03_EN05_kb_boost_flips_winner(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """KB boost 改变胜者:c1 低 base 但 KB 强匹配 → 最终赢。"""
        c1 = make_candidate(decision_type="invoke_skill", base_score=0.5,
                            kb_tags=("boost_tag",),
                            reason="skill with kb hit")
        c2 = make_candidate(decision_type="use_tool", base_score=0.6,
                            reason="plain tool")
        snip = make_kb_snippet(
            kind="pattern", tags=("boost_tag",),
            rerank_score=1.0, observed_count=64,
        )
        ctx = make_context(kb_enabled=True, kb_snippets=(snip,))
        action = decide([c1, c2], ctx)
        assert action.decision_type == "invoke_skill"
        assert action.kb_boost > 0.0
        assert action.kb_degraded is False

    def test_TC_W03_EN06_kb_disabled_flag_set(
        self, make_candidate, make_context,
    ) -> None:
        """kb_enabled=False → kb_degraded=True · kb_boost=0.0。"""
        c = make_candidate(decision_type="no_op", reason="degraded mode")
        ctx = make_context(kb_enabled=False)
        action = decide([c], ctx)
        assert action.kb_degraded is True
        assert action.kb_boost == 0.0
        assert "kb_degraded" in action.reason

    def test_TC_W03_EN07_empty_snippets_flag_set(
        self, make_candidate, make_context,
    ) -> None:
        """kb_enabled=True 但 kb_snippets 空 → 也视为降级。"""
        c = make_candidate(decision_type="no_op", reason="still degraded")
        ctx = make_context(kb_enabled=True, kb_snippets=())
        action = decide([c], ctx)
        assert action.kb_degraded is True

    def test_TC_W03_EN08_history_weight_applied(
        self, make_candidate, make_context, make_history_entry,
    ) -> None:
        """同 type history success → 正向 history_weight。"""
        c = make_candidate(decision_type="invoke_skill",
                           base_score=0.5, reason="has history")
        hist = (make_history_entry(
            decision_type="invoke_skill", outcome="success", tick_delta=1,
        ),)
        action = decide([c], make_context(history=hist))
        assert action.history_weight > 0.0
        assert action.final_score > action.base_score

    def test_TC_W03_EN09_reason_length_ge_20(
        self, make_candidate, make_context,
    ) -> None:
        """reason 最终长度 ≥ 20 字(含自动模板)。"""
        c = make_candidate(decision_type="no_op", base_score=0.5,
                           reason="x")  # 原始很短
        action = decide([c], make_context())
        assert len(action.reason) >= REASON_MIN_LEN

    def test_TC_W03_EN10_alternatives_top_3(
        self, make_candidate, make_context,
    ) -> None:
        """5 候选 · alternatives 最多 3 个(winner 之外)。"""
        cands = [
            make_candidate(decision_type="no_op", base_score=0.9, reason="#1"),
            make_candidate(decision_type="invoke_skill", base_score=0.8, reason="#2"),
            make_candidate(decision_type="use_tool", base_score=0.7, reason="#3"),
            make_candidate(decision_type="delegate_subagent", base_score=0.6, reason="#4"),
            make_candidate(decision_type="request_user", base_score=0.5, reason="#5"),
        ]
        action = decide(cands, make_context())
        assert action.decision_type == "no_op"
        assert len(action.alternatives) == 3

    def test_TC_W03_EN11_params_passthrough(
        self, make_candidate, make_context,
    ) -> None:
        """decision_params 从 winner Candidate 透传(不改动)。"""
        params = {"capability_tag": "deepseek.generate", "n": 3}
        c = make_candidate(
            decision_type="invoke_skill",
            decision_params=params,
            base_score=0.9,
            reason="param test",
        )
        action = decide([c], make_context())
        assert action.decision_params == params
        # 不共享同一 dict 引用(engine 内 dict(...))
        assert action.decision_params is not params

    def test_TC_W03_EN12_chosen_action_is_frozen(
        self, make_candidate, make_context,
    ) -> None:
        """ChosenAction 不可变 · 改 field 抛异常。"""
        c = make_candidate(decision_type="no_op", reason="frozen test")
        action = decide([c], make_context())
        with pytest.raises(Exception):
            action.final_score = 0.0  # type: ignore[misc]

    def test_TC_W03_EN13_base_score_recorded(
        self, make_candidate, make_context,
    ) -> None:
        """base_score 如实记录到 ChosenAction.base_score。"""
        c = make_candidate(decision_type="no_op", base_score=0.37, reason="t")
        action = decide([c], make_context())
        assert action.base_score == 0.37
