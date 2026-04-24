"""L1-01 L2-02 Decision Engine · AST safe_eval 正向求值测试.

覆盖 guard_expr 真实业务场景:
    - 布尔 / 逻辑 / 比较
    - 容器 in / not in 成员测试
    - 白名单函数调用(len/min/max/abs)
    - 变量引用 guard_vars
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.ast_validator import (
    DEFAULT_ALLOWED_FUNCS,
    SafeExprValidator,
    compute_ast_metrics,
    safe_eval,
)
from app.main_loop.decision_engine.errors import EvaluationError


class TestASTPositiveEval:
    """guard_expr 真实 True/False 求值。"""

    def test_TC_W03_EV01_literal_true(self) -> None:
        assert safe_eval("True", {}) is True

    def test_TC_W03_EV02_literal_false(self) -> None:
        assert safe_eval("False", {}) is False

    def test_TC_W03_EV03_bool_and(self) -> None:
        assert safe_eval("True and False", {}) is False
        assert safe_eval("True and True", {}) is True

    def test_TC_W03_EV04_bool_or(self) -> None:
        assert safe_eval("False or True", {}) is True
        assert safe_eval("False or False", {}) is False

    def test_TC_W03_EV05_not(self) -> None:
        assert safe_eval("not True", {}) is False
        assert safe_eval("not False", {}) is True

    def test_TC_W03_EV06_compare_eq(self) -> None:
        assert safe_eval("state == 'S4_execute'", {"state": "S4_execute"}) is True
        assert safe_eval("state == 'S4_execute'", {"state": "S1_plan"}) is False

    def test_TC_W03_EV07_compare_numeric(self) -> None:
        assert safe_eval("score > 0.5", {"score": 0.8}) is True
        assert safe_eval("score > 0.5", {"score": 0.2}) is False

    def test_TC_W03_EV08_compare_chain(self) -> None:
        """链式比较 0 <= x <= 10。"""
        assert safe_eval("0 <= x <= 10", {"x": 5}) is True
        assert safe_eval("0 <= x <= 10", {"x": 20}) is False

    def test_TC_W03_EV09_in_list(self) -> None:
        assert safe_eval(
            "state in ['S4_execute', 'S5_verify']",
            {"state": "S4_execute"},
        ) is True
        assert safe_eval(
            "state in ['S4_execute', 'S5_verify']",
            {"state": "S0_init"},
        ) is False

    def test_TC_W03_EV10_not_in(self) -> None:
        assert safe_eval(
            "state not in ['S0_init']",
            {"state": "S4_execute"},
        ) is True

    def test_TC_W03_EV11_call_len(self) -> None:
        assert safe_eval("len(items) > 0", {"items": [1, 2, 3]}) is True
        assert safe_eval("len(items) > 0", {"items": []}) is False

    def test_TC_W03_EV12_call_max(self) -> None:
        assert safe_eval("max(a, b) >= 10", {"a": 5, "b": 12}) is True

    def test_TC_W03_EV13_call_abs(self) -> None:
        assert safe_eval("abs(x) == 3", {"x": -3}) is True

    def test_TC_W03_EV14_name_not_in_env_raises(self) -> None:
        """未绑定变量 → E_AST_EVAL_FAIL。"""
        with pytest.raises(EvaluationError, match="not in guard_vars"):
            safe_eval("foo", {})

    def test_TC_W03_EV15_compute_ast_metrics(self) -> None:
        """compute_ast_metrics 返回 (depth, node_count)。"""
        import ast
        tree = ast.parse("a and b", mode="eval")
        depth, nodes = compute_ast_metrics(tree)
        assert depth >= 1
        assert nodes >= 4

    def test_TC_W03_EV16_tuple_membership(self) -> None:
        assert safe_eval(
            "tag in ('trap', 'anti_pattern')",
            {"tag": "trap"},
        ) is True

    def test_TC_W03_EV17_reports_used_names(self) -> None:
        """SafeExprValidator.used_names 应收集所有 Name。"""
        v = SafeExprValidator(allowed_funcs=DEFAULT_ALLOWED_FUNCS)
        v.parse_and_validate("a and b or c")
        assert v.used_names == frozenset({"a", "b", "c"})

    def test_TC_W03_EV18_reports_used_functions(self) -> None:
        v = SafeExprValidator(allowed_funcs=DEFAULT_ALLOWED_FUNCS)
        v.parse_and_validate("len(x) > 0")
        assert v.used_functions == frozenset({"len"})
