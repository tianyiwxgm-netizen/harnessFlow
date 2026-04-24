"""L1-01 L2-02 Decision Engine · engine.decide() 负向 + 错误码用例.

覆盖 errors.py 中所有 E_* 错误码:
    - E_CTX_NO_PROJECT_ID
    - E_CTX_STATE_MISSING
    - E_DECISION_TYPE_INVALID
    - E_DECISION_NO_CANDIDATE
    - E_AST_* (通过 guard_expr 传入)
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine import decide
from app.main_loop.decision_engine.errors import (
    ASTSyntaxError,
    CtxNoProjectIdError,
    CtxStateMissingError,
    DecisionError,
    DecisionNoCandidateError,
    EvaluationError,
    IllegalFunctionError,
    IllegalNodeError,
    InvalidDecisionTypeError,
)
from app.main_loop.decision_engine.schemas import Candidate, DecisionContext


class TestEngineNegativeCtx:
    """CTX 合法性校验。"""

    def test_TC_W03_EN101_no_project_id(self, make_candidate) -> None:
        """project_id 为空 → E_CTX_NO_PROJECT_ID。"""
        c = make_candidate()
        ctx = DecisionContext(project_id="", state="S4_execute")
        with pytest.raises(CtxNoProjectIdError, match="E_CTX_NO_PROJECT_ID"):
            decide([c], ctx)

    def test_TC_W03_EN102_none_project_id(self, make_candidate) -> None:
        """project_id=None(类型错)→ E_CTX_NO_PROJECT_ID。"""
        c = make_candidate()
        ctx = DecisionContext(project_id=None, state="S4_execute")  # type: ignore[arg-type]
        with pytest.raises(CtxNoProjectIdError):
            decide([c], ctx)

    def test_TC_W03_EN103_state_missing(
        self, make_candidate, mock_project_id: str,
    ) -> None:
        """state='' → E_CTX_STATE_MISSING。"""
        c = make_candidate()
        ctx = DecisionContext(project_id=mock_project_id, state="")
        with pytest.raises(CtxStateMissingError, match="E_CTX_STATE_MISSING"):
            decide([c], ctx)

    def test_TC_W03_EN104_state_invalid_enum(
        self, make_candidate, mock_project_id: str,
    ) -> None:
        """state 不在白名单 → E_CTX_STATE_MISSING。"""
        c = make_candidate()
        ctx = DecisionContext(project_id=mock_project_id, state="S99_bogus")
        with pytest.raises(CtxStateMissingError):
            decide([c], ctx)

    def test_TC_W03_EN105_ctx_wrong_type(self, make_candidate) -> None:
        """ctx 类型错(dict 而非 DecisionContext)→ E_CTX_INVALID_TYPE。"""
        c = make_candidate()
        with pytest.raises(DecisionError, match="E_CTX_INVALID_TYPE"):
            decide([c], {"project_id": "x", "state": "S4_execute"})  # type: ignore[arg-type]


class TestEngineNegativeDecisionType:
    """decision_type 白名单严格校验。"""

    def test_TC_W03_EN106_invalid_decision_type(
        self, make_candidate, make_context,
    ) -> None:
        """candidate.decision_type 不在 12 类 → E_DECISION_TYPE_INVALID。"""
        c = Candidate(decision_type="bogus_type", reason="x" * 30)
        with pytest.raises(InvalidDecisionTypeError, match="E_DECISION_TYPE_INVALID"):
            decide([c], make_context())


class TestEngineNegativeNoCandidate:
    def test_TC_W03_EN107_empty_candidates_no_fallback(
        self, make_context,
    ) -> None:
        """空候选 + 无 fallback → E_DECISION_NO_CANDIDATE。"""
        with pytest.raises(DecisionNoCandidateError, match="E_DECISION_NO_CANDIDATE"):
            decide([], make_context())

    def test_TC_W03_EN108_all_filtered_out_no_fallback(
        self, make_candidate, make_context,
    ) -> None:
        """所有候选 guard_expr 返回 False + 无 fallback → E_DECISION_NO_CANDIDATE。"""
        c1 = make_candidate(
            decision_type="invoke_skill",
            guard_expr="False",
            reason="never picked",
        )
        c2 = make_candidate(
            decision_type="use_tool",
            guard_expr="False",
            reason="also never",
        )
        with pytest.raises(DecisionNoCandidateError):
            decide([c1, c2], make_context())


class TestEngineNegativeAST:
    """guard_expr 触发 AST 白名单错误。"""

    def test_TC_W03_EN109_guard_syntax_error(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 语法错 → E_AST_SYNTAX。"""
        c = make_candidate(guard_expr="a + + +", reason="bad syntax")
        with pytest.raises(ASTSyntaxError, match="E_AST_SYNTAX"):
            decide([c], make_context())

    def test_TC_W03_EN110_guard_illegal_node(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 含 Attribute(逃逸)→ E_AST_ILLEGAL_NODE。"""
        c = make_candidate(
            guard_expr="().__class__",
            reason="class mro escape",
        )
        with pytest.raises(IllegalNodeError, match="E_AST_ILLEGAL_NODE"):
            decide([c], make_context())

    def test_TC_W03_EN111_guard_illegal_function(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 调用未白名单函数 → E_AST_ILLEGAL_FUNCTION。"""
        c = make_candidate(
            guard_expr="open('file')",
            reason="file system escape",
        )
        with pytest.raises(IllegalFunctionError, match="E_AST_ILLEGAL_FUNCTION"):
            decide([c], make_context())

    def test_TC_W03_EN112_guard_missing_var(
        self, make_candidate, make_context,
    ) -> None:
        """guard_expr 引用未绑定变量 → E_AST_EVAL_FAIL。"""
        c = make_candidate(
            guard_expr="missing_var > 0",
            reason="unbound var",
        )
        with pytest.raises(EvaluationError, match="E_AST_EVAL_FAIL"):
            decide([c], make_context(guard_vars={}))


class TestEngineNegativeFallbackChain:
    """fallback 兜底自身不合法的情况。"""

    def test_TC_W03_EN113_fallback_with_invalid_type_raises(
        self, make_candidate, make_context,
    ) -> None:
        """fallback_candidate.decision_type 非法 → E_DECISION_TYPE_INVALID。"""
        fb = Candidate(decision_type="bogus", reason="x" * 30)
        c1 = make_candidate(
            decision_type="invoke_skill",
            guard_expr="False",
            reason="never picked",
        )
        ctx = make_context(fallback_candidate=fb)
        with pytest.raises(InvalidDecisionTypeError):
            decide([c1], ctx)
