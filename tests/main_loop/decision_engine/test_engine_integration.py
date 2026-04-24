"""L1-01 L2-02 Decision Engine · 端到端集成.

覆盖真实业务场景:
    - 复杂 guard_expr(AST + Compare + Call + BoolOp)过滤
    - KB boost + history + base 三方权重组合
    - 降级无 KB → 退回纯 base + history
    - kb_trap 触发负向 → 选备选
    - 大量候选(性能 smoke)
"""
from __future__ import annotations

import time

import pytest

from app.main_loop.decision_engine import decide


class TestEngineIntegration:
    """跨组件集成。"""

    def test_TC_W03_IT01_state_based_filter_real_scenario(
        self, make_candidate, make_context,
    ) -> None:
        """真实场景:S4 阶段只允许 invoke_skill / use_tool · state_transition 走 S5 守卫。"""
        c_skill = make_candidate(
            decision_type="invoke_skill",
            base_score=0.8,
            guard_expr="state in ['S4_execute', 'S5_verify']",
            reason="ready to execute",
        )
        c_trans = make_candidate(
            decision_type="state_transition",
            decision_params={"from": "S4_execute", "to": "S5_verify",
                             "evidence_refs": [], "trigger_tick": "t1"},
            base_score=0.9,
            guard_expr="dod_complete",
            reason="move to verify",
        )
        ctx = make_context(
            state="S4_execute",
            guard_vars={"state": "S4_execute", "dod_complete": False},
        )
        action = decide([c_skill, c_trans], ctx)
        # state_transition 被 guard 过滤(dod_complete=False)
        assert action.decision_type == "invoke_skill"

    def test_TC_W03_IT02_kb_boost_with_history_combine(
        self, make_candidate, make_context, make_kb_snippet, make_history_entry,
    ) -> None:
        """base=0.5 + kb + hist · 三项线性组合。"""
        c = make_candidate(
            decision_type="invoke_skill",
            base_score=0.5,
            kb_tags=("deepseek",),
            reason="combine test",
        )
        snip = make_kb_snippet(
            kind="pattern", tags=("deepseek",), rerank_score=0.8,
        )
        hist = (make_history_entry(
            decision_type="invoke_skill", outcome="success", tick_delta=1,
        ),)
        ctx = make_context(kb_snippets=(snip,), history=hist)
        action = decide([c], ctx)
        # final = base + kb_boost + hist_weight
        assert action.final_score == pytest.approx(
            action.base_score + action.kb_boost + action.history_weight,
            abs=1e-6,
        )
        assert action.kb_boost > 0
        assert action.history_weight > 0

    def test_TC_W03_IT03_kb_trap_pushes_alt(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """c1 base 高但 KB 里 trap · c2 base 低无 trap · c2 最终胜。"""
        c1 = make_candidate(
            decision_type="invoke_skill",
            base_score=0.6,
            kb_tags=("risky",),
            reason="risky skill",
        )
        c2 = make_candidate(
            decision_type="use_tool",
            base_score=0.55,
            reason="safe tool",
        )
        trap = make_kb_snippet(
            kind="trap", tags=("risky",), rerank_score=1.0, observed_count=64,
        )
        ctx = make_context(kb_snippets=(trap,))
        action = decide([c1, c2], ctx)
        assert action.decision_type == "use_tool"
        assert action.kb_boost >= 0.0  # use_tool 无 kb_tags 命中

    def test_TC_W03_IT04_kb_disabled_degrades_silently(
        self, make_candidate, make_context, make_kb_snippet,
    ) -> None:
        """即使 snippets 存在 · kb_enabled=False → 完全降级,不抛。"""
        c = make_candidate(
            decision_type="invoke_skill",
            kb_tags=("x",),
            reason="would boost but disabled",
        )
        snip = make_kb_snippet(kind="pattern", tags=("x",), rerank_score=1.0)
        ctx = make_context(kb_enabled=False, kb_snippets=(snip,))
        action = decide([c], ctx)
        assert action.kb_degraded is True
        assert action.kb_boost == 0.0

    def test_TC_W03_IT05_history_consec_fail_flips_choice(
        self, make_candidate, make_context, make_history_entry,
    ) -> None:
        """c1 base 高但 history 3 连败 · c2 无历史 · c2 最终胜。"""
        c1 = make_candidate(
            decision_type="invoke_skill", base_score=0.7,
            reason="often failed",
        )
        c2 = make_candidate(
            decision_type="use_tool", base_score=0.5,
            reason="fresh tool",
        )
        hist = tuple(
            make_history_entry(
                decision_type="invoke_skill", outcome="fail", tick_delta=1,
            )
            for _ in range(4)  # 4 连败 > 3 触发 CONSEC_FAIL_EXTRA
        )
        ctx = make_context(history=hist)
        action = decide([c1, c2], ctx)
        assert action.decision_type == "use_tool"

    def test_TC_W03_IT06_perf_smoke_30_candidates(
        self, make_candidate, make_context,
    ) -> None:
        """30 个候选 · decide() 应在 50ms 内完成(纯计算)。"""
        cands = [
            make_candidate(
                decision_type="invoke_skill",
                base_score=0.5 + (i % 10) * 0.03,
                guard_expr="score > 0.0",
                reason=f"#{i} candidate",
            )
            for i in range(30)
        ]
        ctx = make_context(guard_vars={"score": 0.5})
        t0 = time.perf_counter()
        action = decide(cands, ctx)
        elapsed = (time.perf_counter() - t0) * 1000
        assert action is not None
        assert elapsed < 50  # ms

    def test_TC_W03_IT07_empty_guard_vars_still_passes(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr='True' 常量 · 不需要 guard_vars 也能通过。"""
        c = make_candidate(
            decision_type="no_op", guard_expr="True", reason="trivial guard",
        )
        ctx = make_context(guard_vars={})
        action = decide([c], ctx)
        assert action.decision_type == "no_op"

    def test_TC_W03_IT08_winner_dict_params_independent(
        self, make_candidate, make_context,
    ) -> None:
        """修改 ChosenAction.decision_params 不影响原 Candidate.decision_params。"""
        original = {"tool_name": "grep", "args": {"pattern": "x"}}
        c = make_candidate(
            decision_type="use_tool",
            decision_params=original,
            reason="params iso test",
        )
        action = decide([c], make_context())
        # frozen=True 阻止重新赋值;但内部 dict 可变
        action.decision_params["added"] = "side"
        assert "added" not in c.decision_params  # c 原始未被污染
        assert c.decision_params == {"tool_name": "grep", "args": {"pattern": "x"}}
