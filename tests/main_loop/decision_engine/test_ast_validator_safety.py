"""L1-01 L2-02 Decision Engine · AST 白名单安全红线测试.

安全铁律 TC:禁 eval / exec / __import__ / dunder / Attribute / Lambda / ...
对齐 dod_compiler SA-01/02/03 参考实现。
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_engine.ast_validator import (
    SafeExprValidator,
    safe_eval,
)
from app.main_loop.decision_engine.errors import (
    ASTSyntaxError,
    IllegalFunctionError,
    IllegalNodeError,
    RecursionLimitExceeded,
)


class TestASTSafety:
    """SA-01/02/03 · 严禁 eval/exec/__import__ · 铁律。"""

    def test_TC_W03_AST01_empty_expression_rejected(self) -> None:
        """空表达式 → E_AST_SYNTAX。"""
        v = SafeExprValidator()
        with pytest.raises(ASTSyntaxError, match="empty"):
            v.parse_and_validate("")

    def test_TC_W03_AST02_syntax_error_rejected(self) -> None:
        """Python 语法错 → E_AST_SYNTAX。"""
        v = SafeExprValidator()
        with pytest.raises(ASTSyntaxError, match="ast.parse failed"):
            v.parse_and_validate("a + + + ")

    def test_TC_W03_AST03_ban_import_via_builtins(self) -> None:
        """禁 __import__('os') · SA-02 dunder 双保险(Call 白名单 or dunder name 兜底)。"""
        # __import__ 会被 function 白名单 或 dunder name 任一拦下,两种都是拒绝。
        with pytest.raises((IllegalFunctionError, IllegalNodeError)):
            safe_eval("__import__('os')", {})

    def test_TC_W03_AST04_ban_dunder_name(self) -> None:
        """禁任何 __foo__ 类 dunder name。"""
        for bad in ("__builtins__", "__class__", "__globals__", "__dict__"):
            with pytest.raises(IllegalNodeError, match="dunder"):
                safe_eval(bad, {bad: "trap"})

    def test_TC_W03_AST05_ban_attribute_access(self) -> None:
        """禁 ast.Attribute · 如 a.b → IllegalNodeError。"""
        with pytest.raises(IllegalNodeError, match="Attribute"):
            safe_eval("a.b", {"a": {"b": 1}})

    def test_TC_W03_AST06_ban_subscript(self) -> None:
        """禁 ast.Subscript · 如 a[0] → IllegalNodeError。"""
        with pytest.raises(IllegalNodeError, match="Subscript"):
            safe_eval("a[0]", {"a": [1, 2]})

    def test_TC_W03_AST07_ban_lambda(self) -> None:
        """禁 Lambda 表达式。"""
        with pytest.raises(IllegalNodeError, match="Lambda"):
            safe_eval("lambda x: x", {})

    def test_TC_W03_AST08_ban_list_comp(self) -> None:
        """禁 List Comprehension。"""
        with pytest.raises(IllegalNodeError, match="ListComp"):
            safe_eval("[x for x in [1, 2]]", {})

    def test_TC_W03_AST09_ban_starred_args(self) -> None:
        """禁 *args(Starred)·SA-01 参数展开绕过。"""
        with pytest.raises(IllegalNodeError, match="Starred"):
            safe_eval("len(*a)", {"a": [1, 2, 3]})

    def test_TC_W03_AST10_ban_keyword_args(self) -> None:
        """禁关键字参数(positional only · SA-01 签名伪造)。"""
        with pytest.raises(IllegalNodeError, match="keyword"):
            safe_eval("min(a, default=0)", {"a": [1, 2]})

    def test_TC_W03_AST11_ban_non_name_call_func(self) -> None:
        """禁 Attribute 作为 Call.func · 防 ().__class__.__mro__[...] 逃逸。"""
        with pytest.raises(IllegalNodeError, match="Attribute|Call.func"):
            safe_eval("().__class__()", {})

    def test_TC_W03_AST12_ban_call_to_unallowed_function(self) -> None:
        """调用白名单之外的函数 → IllegalFunctionError。"""
        with pytest.raises(IllegalFunctionError, match="not in whitelist"):
            safe_eval("print(1)", {})

    def test_TC_W03_AST13_recursion_limit_too_many_nodes(self) -> None:
        """节点数超限 → RecursionLimitExceeded。"""
        # 2 ** 6 = 64 个 Constant + 63 个 BinOp → 超过 max_nodes=10
        expr = " or ".join(["True"] * 50)
        with pytest.raises(RecursionLimitExceeded, match="nodes="):
            safe_eval(expr, {}, max_nodes=10)

    def test_TC_W03_AST14_recursion_limit_too_deep(self) -> None:
        """深度超限 → RecursionLimitExceeded。"""
        expr = "not " * 10 + "True"
        with pytest.raises(RecursionLimitExceeded, match="depth="):
            safe_eval(expr, {}, max_depth=3)

    def test_TC_W03_AST15_str_constant_too_long(self) -> None:
        """str Constant 超 max_str_const → RecursionLimitExceeded。"""
        long_str = "'" + "x" * 1000 + "'"
        v = SafeExprValidator(max_str_const=500)
        with pytest.raises(RecursionLimitExceeded, match="str Constant"):
            v.parse_and_validate(long_str)

    def test_TC_W03_AST16_int_constant_too_large(self) -> None:
        """int Constant 绝对值超限 → RecursionLimitExceeded。"""
        v = SafeExprValidator(max_int_const=100)
        with pytest.raises(RecursionLimitExceeded, match="int Constant"):
            v.parse_and_validate("99999")

    def test_TC_W03_AST17_walrus_operator_rejected(self) -> None:
        """:= (NamedExpr) 不在白名单 → IllegalNodeError。"""
        with pytest.raises(IllegalNodeError):
            safe_eval("(x := 1)", {})

    def test_TC_W03_AST18_ban_fstring(self) -> None:
        """禁 f-string(JoinedStr / FormattedValue · 可嵌表达式逃逸)。"""
        with pytest.raises(IllegalNodeError, match="JoinedStr|FormattedValue"):
            safe_eval("f'{a}'", {"a": 1})

    def test_TC_W03_AST19_ban_yield(self) -> None:
        """禁 yield。"""
        with pytest.raises((IllegalNodeError, ASTSyntaxError)):
            safe_eval("(yield 1)", {})

    def test_TC_W03_AST20_ban_assignment(self) -> None:
        """禁 Assign(顶层 expression 模式 parse 不出来但仍检查冗余)。"""
        with pytest.raises(ASTSyntaxError):
            # mode=eval 下直接语法错
            safe_eval("x = 1", {})
