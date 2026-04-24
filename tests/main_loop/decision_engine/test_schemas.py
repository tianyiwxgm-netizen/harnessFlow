"""L1-01 L2-02 Decision Engine · schemas 单元.

TC-L101-L202-W03-SC01 … W03-SC05
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.schemas import (
    DECISION_TYPES,
    Candidate,
    ChosenAction,
    DecisionContext,
    HistoryEntry,
    KBSnippet,
)


class TestSchemas:
    """数据契约不可变性 + 默认值 + 12 类白名单。"""

    def test_TC_W03_SC01_candidate_defaults(self) -> None:
        """Candidate 默认值构造 OK · base_score=0.5 · 空 kb_tags / guard_expr / params。"""
        c = Candidate(decision_type="no_op")
        assert c.decision_type == "no_op"
        assert c.base_score == 0.5
        assert c.guard_expr == ""
        assert c.kb_tags == ()
        assert c.decision_params == {}

    def test_TC_W03_SC02_candidate_is_frozen(self) -> None:
        """frozen=True · 直接赋值报 FrozenInstanceError。"""
        c = Candidate(decision_type="invoke_skill")
        with pytest.raises(Exception):
            c.base_score = 0.9  # type: ignore[misc]

    def test_TC_W03_SC03_decision_types_whitelist(self) -> None:
        """12 类决策 · 全部在白名单内。"""
        for t in (
            "invoke_skill", "use_tool", "delegate_subagent",
            "kb_read", "kb_write", "process_content",
            "request_user", "state_transition", "start_chain",
            "warn_response", "fill_discipline_gap", "no_op",
        ):
            assert t in DECISION_TYPES
        assert len(DECISION_TYPES) == 12

    def test_TC_W03_SC04_context_defaults(self) -> None:
        """DecisionContext 默认值:kb_enabled=True · 空 history / snippets。"""
        ctx = DecisionContext(project_id="pid-x")
        assert ctx.project_id == "pid-x"
        assert ctx.kb_enabled is True
        assert ctx.history == ()
        assert ctx.kb_snippets == ()
        assert ctx.fallback_candidate is None

    def test_TC_W03_SC05_chosen_action_shape(self) -> None:
        """ChosenAction 必含全部评分字段。"""
        a = ChosenAction(
            decision_type="no_op",
            decision_params={"note": "idle"},
            final_score=0.5,
            kb_boost=0.0,
            history_weight=0.0,
            base_score=0.5,
            reason="test reason long enough to pass",
        )
        assert a.kb_degraded is False
        assert a.alternatives == ()
        assert a.decision_params == {"note": "idle"}

    def test_TC_W03_SC06_history_entry_defaults(self) -> None:
        """HistoryEntry 默认值:outcome=unknown · tick_delta=1。"""
        h = HistoryEntry(decision_type="invoke_skill")
        assert h.outcome == "unknown"
        assert h.tick_delta == 1

    def test_TC_W03_SC07_kb_snippet_defaults(self) -> None:
        """KBSnippet 默认:kind=pattern · observed_count=1。"""
        s = KBSnippet()
        assert s.kind == "pattern"
        assert s.tags == ()
        assert s.observed_count == 1
