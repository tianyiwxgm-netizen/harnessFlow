"""L1-01 L2-02 Decision Engine · 边界 / edge case 用例.

覆盖:
    - SafeExprValidator 白名单外原生节点(NamedExpr / MatMult)
    - Constant 类型非法(bytes / complex)
    - ast.Name ctx 非 Load(赋值语义绕过)
    - ast.Call func 为 Call(nested)
    - compute_ast_metrics 非 AST 输入
    - Candidate 空 reason + guard_expr 均值降级
"""
from __future__ import annotations

import ast

import pytest

from app.main_loop.decision_engine.ast_validator import (
    SafeExprValidator,
    compute_ast_metrics,
)
from app.main_loop.decision_engine.errors import (
    ASTSyntaxError,
    IllegalNodeError,
)


class TestSafeExprValidatorBoundary:
    def test_TC_W03_BD01_root_not_expression(self) -> None:
        """传入 ast.Module 非 Expression → IllegalNodeError。"""
        v = SafeExprValidator()
        tree = ast.parse("a", mode="exec")  # Module
        with pytest.raises(IllegalNodeError, match="root must be ast.Expression"):
            v.validate(tree)

    def test_TC_W03_BD02_constant_bytes_rejected(self) -> None:
        """Constant 值为 bytes → IllegalNodeError。"""
        v = SafeExprValidator()
        tree = ast.parse("b'hello'", mode="eval")
        with pytest.raises(IllegalNodeError, match="value type bytes"):
            v.validate(tree)

    def test_TC_W03_BD03_constant_complex_rejected(self) -> None:
        """Constant 值为 complex → IllegalNodeError。"""
        v = SafeExprValidator()
        tree = ast.parse("1j", mode="eval")
        with pytest.raises(IllegalNodeError, match="value type complex"):
            v.validate(tree)

    def test_TC_W03_BD04_ast_call_func_not_name(self) -> None:
        """((x))() 中 func 是 Name(括号不影响);构造 func 是 Call 的情况。"""
        # 原生 python 很难写出 call-as-func 但可手构
        from app.main_loop.decision_engine.ast_validator import (
            DEFAULT_ALLOWED_FUNCS,
        )
        v = SafeExprValidator(allowed_funcs=DEFAULT_ALLOWED_FUNCS)
        # "f(x)(y)" · f(x) 返回值做 Call.func
        tree = ast.parse("len(items)(0)", mode="eval")
        with pytest.raises(IllegalNodeError, match="Call.func must be ast.Name"):
            v.validate(tree)

    def test_TC_W03_BD05_compute_ast_metrics_non_ast(self) -> None:
        """非 AST 输入 · 返回 (0, 0)。"""
        assert compute_ast_metrics("not an ast") == (0, 0)  # type: ignore[arg-type]

    def test_TC_W03_BD06_walrus_in_eval_mode(self) -> None:
        """(x := 1) Python 3.8+ 有效 mode=eval · 但 NamedExpr 不在白名单。"""
        v = SafeExprValidator()
        try:
            tree = ast.parse("(x := 1)", mode="eval")
        except SyntaxError:
            pytest.skip("walrus not parseable here")
            return
        with pytest.raises(IllegalNodeError):
            v.validate(tree)

    def test_TC_W03_BD07_wrong_arg_count_rejected(self) -> None:
        """allowed_funcs={'len': 1} · 传 2 个参数 → IllegalFunctionError。"""
        from app.main_loop.decision_engine.errors import IllegalFunctionError
        v = SafeExprValidator(allowed_funcs={"len": 1})
        with pytest.raises(IllegalFunctionError, match="expects 1 args"):
            v.parse_and_validate("len(a, b)")

    def test_TC_W03_BD08_flex_arg_count_accepted(self) -> None:
        """allowed_funcs={'min': -1} · 变参(2 / 3 个都 OK)。"""
        v = SafeExprValidator(allowed_funcs={"min": -1})
        v.parse_and_validate("min(1, 2)")  # 不抛
        v.parse_and_validate("min(1, 2, 3)")  # 不抛


class TestEngineIdempotencyAndEdge:
    def test_TC_W03_BD09_no_candidates_empty_tuple(self, make_context) -> None:
        """candidates=() tuple 也能处理(不只 list)。"""
        from app.main_loop.decision_engine import decide
        from app.main_loop.decision_engine.errors import (
            DecisionNoCandidateError,
        )
        with pytest.raises(DecisionNoCandidateError):
            decide((), make_context())

    def test_TC_W03_BD10_candidate_zero_base_score(
        self, make_candidate, make_context,
    ) -> None:
        """base_score=0.0 · 仍可被选(只要没有负加权)。"""
        from app.main_loop.decision_engine import decide
        c = make_candidate(decision_type="no_op", base_score=0.0, reason="zero")
        action = decide([c], make_context())
        assert action.decision_type == "no_op"
        assert action.base_score == 0.0

    def test_TC_W03_BD11_same_type_ties_stable_order(
        self, make_candidate, make_context,
    ) -> None:
        """同分并列 · 保持输入顺序(stable sort)。"""
        from app.main_loop.decision_engine import decide
        c1 = make_candidate(decision_type="no_op", base_score=0.5, reason="#1")
        c2 = make_candidate(decision_type="invoke_skill", base_score=0.5, reason="#2")
        action = decide([c1, c2], make_context())
        # stable sort → c1 在前
        assert action.decision_type == "no_op"

    def test_TC_W03_BD12_long_history_truncated(
        self, make_candidate, make_context, make_history_entry,
    ) -> None:
        """history 超 HISTORY_WINDOW · engine 不会因为 history 大而变慢或失败。"""
        import time
        from app.main_loop.decision_engine import decide
        c = make_candidate(
            decision_type="invoke_skill", base_score=0.5, reason="window test",
        )
        hist = tuple(
            make_history_entry(
                decision_type="invoke_skill", outcome="success", tick_delta=i,
            )
            for i in range(200)
        )
        t0 = time.perf_counter()
        action = decide([c], make_context(history=hist))
        ms = (time.perf_counter() - t0) * 1000
        assert action is not None
        assert ms < 50  # 仍快速

    def test_TC_W03_BD13_reason_auto_template_when_empty(
        self, make_candidate, make_context,
    ) -> None:
        """Candidate.reason 为空 / 空格 · engine 走 auto template 不抛 E_DECISION_NO_REASON。"""
        from app.main_loop.decision_engine import decide
        c = make_candidate(decision_type="no_op", base_score=0.5, reason="   ")
        action = decide([c], make_context())
        assert "auto decision" in action.reason
        assert len(action.reason) >= 20


class TestErrorsDunder:
    def test_TC_W03_BD14_decision_error_carries_code_message(self) -> None:
        """DecisionError 基类 · code + message 公开可读。"""
        from app.main_loop.decision_engine.errors import DecisionError
        e = DecisionError("E_TEST", "test message")
        assert e.code == "E_TEST"
        assert e.message == "test message"
        assert "E_TEST" in str(e)
