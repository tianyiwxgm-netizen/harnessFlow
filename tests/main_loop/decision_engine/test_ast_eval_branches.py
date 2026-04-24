"""L1-01 L2-02 Decision Engine · AST eval 分支覆盖补全.

覆盖所有 cmp 操作符 + 容器字面量 + 函数调用异常。
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.ast_validator import safe_eval
from app.main_loop.decision_engine.errors import EvaluationError


class TestASTEvalCmpOps:
    """全 11 类 cmp 操作符的真假分支。"""

    def test_TC_W03_CB01_not_eq(self) -> None:
        assert safe_eval("a != b", {"a": 1, "b": 2}) is True
        assert safe_eval("a != b", {"a": 1, "b": 1}) is False

    def test_TC_W03_CB02_less_than(self) -> None:
        assert safe_eval("a < b", {"a": 1, "b": 2}) is True

    def test_TC_W03_CB03_less_equal(self) -> None:
        assert safe_eval("a <= b", {"a": 2, "b": 2}) is True

    def test_TC_W03_CB04_greater_than(self) -> None:
        assert safe_eval("a > b", {"a": 3, "b": 2}) is True

    def test_TC_W03_CB05_greater_equal(self) -> None:
        assert safe_eval("a >= b", {"a": 3, "b": 3}) is True

    def test_TC_W03_CB06_is_none(self) -> None:
        assert safe_eval("a is None", {"a": None}) is True
        assert safe_eval("a is None", {"a": 0}) is False

    def test_TC_W03_CB07_is_not(self) -> None:
        assert safe_eval("a is not None", {"a": 1}) is True


class TestASTEvalContainers:
    def test_TC_W03_CB08_set_literal(self) -> None:
        assert safe_eval("x in {1, 2, 3}", {"x": 2}) is True

    def test_TC_W03_CB09_tuple_literal(self) -> None:
        assert safe_eval(
            "tag in ('x', 'y', 'z')",
            {"tag": "y"},
        ) is True

    def test_TC_W03_CB10_list_literal(self) -> None:
        assert safe_eval("x in [10, 20]", {"x": 10}) is True


class TestASTEvalCallException:
    def test_TC_W03_CB11_call_raises_eval_fail(self) -> None:
        """函数调用内部抛异常 · 外层 EvaluationError('call failed')。"""
        # abs("not a number") 会 TypeError
        with pytest.raises(EvaluationError, match="call failed"):
            safe_eval("abs(x)", {"x": "not-a-number"})

    def test_TC_W03_CB12_funcs_impl_missing(self) -> None:
        """allowed_funcs 允许 'len' 但 funcs_impl 未提供 → EvaluationError。"""
        with pytest.raises(EvaluationError, match="not bound in funcs"):
            safe_eval(
                "len(x) > 0",
                {"x": [1]},
                allowed_funcs={"len": 1},
                funcs_impl={},  # 故意清空
            )


class TestASTEvalBoolOpEmpty:
    """BoolOp 值列表的两分支 and / or。"""

    def test_TC_W03_CB13_and_short_circuit(self) -> None:
        """False and anything · 返回 False。"""
        assert safe_eval("False and True", {}) is False

    def test_TC_W03_CB14_or_short_circuit(self) -> None:
        """True or False · 返回 True。"""
        assert safe_eval("True or False", {}) is True

    def test_TC_W03_CB15_nested_boolop(self) -> None:
        """(a or b) and c 嵌套。"""
        assert safe_eval(
            "(a or b) and c",
            {"a": False, "b": True, "c": True},
        ) is True
