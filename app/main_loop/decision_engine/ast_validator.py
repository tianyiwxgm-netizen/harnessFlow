"""L1-01 L2-02 · AST 白名单表达式校验 + 求值.

锚点:
    - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md §6 §11
    - 参考实现:app.quality_loop.dod_compiler.ast_nodes.SafeExprValidator

安全红线(同 dod_compiler · 对齐 SA-01/02/03):
    1. 禁 ast.Import / ast.ImportFrom
    2. 禁 ast.Attribute 作为 Call.func(防 __builtins__.eval / __import__ 链)
    3. 禁 ast.Lambda / FunctionDef / ClassDef
    4. 禁 Comprehensions / Loops / Try / Assign / With
    5. 禁 dunder name (__class__ / __import__ / __builtins__ / __globals__ ...)
    6. 禁 keyword / starred args
    7. AST 深度 ≤ MAX_DEPTH
    8. AST 节点数 ≤ MAX_NODES
    9. str Constant ≤ MAX_STR_CONST
    10. int Constant |v| ≤ MAX_INT_CONST

与 dod_compiler 的差异:
    - decision_engine 不需要函数调用 → 默认不允许 ast.Call(更严格)
    - 允许 ast.Name 读取 guard_vars 命名空间(Load only)
    - 提供 `safe_eval(expr, env)` 一把梭入口(解析 + 走 + 求值)
"""
from __future__ import annotations

import ast
from typing import Any

from .errors import (
    ASTSyntaxError,
    EvaluationError,
    IllegalFunctionError,
    IllegalNodeError,
    RecursionLimitExceeded,
)

# ========== 白名单节点集 ==========

ALLOWED_NODE_TYPES: frozenset[type] = frozenset({
    ast.Expression,
    # 布尔 / 逻辑
    ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
    # 比较
    ast.Compare,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.Is, ast.IsNot,
    # 字面量 / 名称
    ast.Constant, ast.Name, ast.Load,
    # 可选:函数调用(仅白名单)
    ast.Call,
    # 容器字面量(供 in / not in 使用)
    ast.List, ast.Tuple, ast.Set,
})

# 显式黑名单(冗余防御 · 先于白名单判 · 错误信息更明确)
DENIED_NODE_TYPES: frozenset[type] = frozenset({
    ast.Import, ast.ImportFrom,
    ast.Attribute, ast.Subscript,
    ast.Lambda, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef,
    ast.For, ast.AsyncFor, ast.While,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.Try, ast.Raise, ast.With, ast.AsyncWith, ast.Assert,
    ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.Yield, ast.YieldFrom, ast.Await,
    ast.Starred, ast.FormattedValue, ast.JoinedStr,
    ast.Global, ast.Nonlocal, ast.Pass, ast.Break, ast.Continue,
    ast.Delete,
})


# ========== 默认预算 ==========


DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_NODES = 200
DEFAULT_MAX_STR_CONST = 500
DEFAULT_MAX_INT_CONST = 10**9


# ========== 决策引擎默认可用的安全函数白名单 ==========
# 只允许纯函数(无 IO · 无副作用);参数数 = 约束位。


DEFAULT_ALLOWED_FUNCS: dict[str, int] = {
    "len": 1,
    "min": -1,   # -1 = 不强制参数数
    "max": -1,
    "abs": 1,
    "bool": 1,
    "int": 1,
    "float": 1,
    "str": 1,
    "round": -1,
}


class SafeExprValidator:
    """AST 白名单 + 资源限制校验器(不执行 · 只 walk)。"""

    def __init__(
        self,
        *,
        allowed_funcs: dict[str, int] | None = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_nodes: int = DEFAULT_MAX_NODES,
        max_str_const: int = DEFAULT_MAX_STR_CONST,
        max_int_const: int = DEFAULT_MAX_INT_CONST,
    ) -> None:
        self._allowed_funcs = dict(allowed_funcs) if allowed_funcs is not None else None
        self._max_depth = max_depth
        self._max_nodes = max_nodes
        self._max_str_const = max_str_const
        self._max_int_const = max_int_const
        self._node_count = 0
        self._max_depth_seen = 0
        self._used_functions: set[str] = set()
        self._used_names: set[str] = set()

    # ---------- 公共入口 ----------

    def parse_and_validate(self, expression_text: str) -> ast.Expression:
        if not isinstance(expression_text, str) or not expression_text.strip():
            raise ASTSyntaxError("expression is empty")
        try:
            tree = ast.parse(expression_text, mode="eval")
        except SyntaxError as exc:
            raise ASTSyntaxError(f"ast.parse failed: {exc}") from exc
        self.validate(tree)
        return tree

    def validate(self, tree: ast.AST) -> None:
        self._node_count = 0
        self._max_depth_seen = 0
        self._used_functions = set()
        self._used_names = set()
        if not isinstance(tree, ast.Expression):
            raise IllegalNodeError(
                f"root must be ast.Expression, got {type(tree).__name__}"
            )
        self._walk(tree, depth=0)

    # ---------- 内部递归 ----------

    def _walk(self, node: ast.AST, *, depth: int) -> None:
        self._node_count += 1
        if self._node_count > self._max_nodes:
            raise RecursionLimitExceeded(
                f"ast nodes={self._node_count} > max={self._max_nodes}"
            )
        if depth > self._max_depth:
            raise RecursionLimitExceeded(
                f"ast depth={depth} > max={self._max_depth}"
            )
        if depth > self._max_depth_seen:
            self._max_depth_seen = depth

        node_type = type(node)
        if node_type in DENIED_NODE_TYPES:
            raise IllegalNodeError(
                f"denied ast node: {node_type.__name__}"
            )
        if node_type not in ALLOWED_NODE_TYPES:
            raise IllegalNodeError(
                f"ast node not in whitelist: {node_type.__name__}"
            )

        if isinstance(node, ast.Call):
            self._check_call(node)
        elif isinstance(node, ast.Constant):
            self._check_constant(node)
        elif isinstance(node, ast.Name):
            self._check_name(node)

        for child in ast.iter_child_nodes(node):
            self._walk(child, depth=depth + 1)

    def _check_call(self, node: ast.Call) -> None:
        # 仅允许 Name 作为 Call.func(防 Attribute/Call-chain 逃逸)
        if not isinstance(node.func, ast.Name):
            raise IllegalNodeError(
                f"ast.Call.func must be ast.Name, got {type(node.func).__name__} "
                "(SA-01 attribute/call-chain escape prevented)"
            )
        fname = node.func.id
        if self._allowed_funcs is not None and fname not in self._allowed_funcs:
            raise IllegalFunctionError(
                f"function '{fname}' not in whitelist"
            )
        if node.keywords:
            raise IllegalNodeError(
                "keyword arguments forbidden (positional only)"
            )
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                raise IllegalNodeError("*args (Starred) forbidden")
        if self._allowed_funcs is not None:
            expected = self._allowed_funcs[fname]
            if expected >= 0 and len(node.args) != expected:
                raise IllegalFunctionError(
                    f"function '{fname}' expects {expected} args, got {len(node.args)}"
                )
        self._used_functions.add(fname)

    def _check_constant(self, node: ast.Constant) -> None:
        v = node.value
        if not isinstance(v, (int, float, str, bool, type(None))):
            raise IllegalNodeError(
                f"ast.Constant value type {type(v).__name__} forbidden"
            )
        if isinstance(v, str) and len(v) > self._max_str_const:
            raise RecursionLimitExceeded(
                f"str Constant len={len(v)} > max={self._max_str_const}"
            )
        if isinstance(v, int) and not isinstance(v, bool):
            if abs(v) > self._max_int_const:
                raise RecursionLimitExceeded(
                    f"int Constant {v} exceeds max={self._max_int_const}"
                )

    def _check_name(self, node: ast.Name) -> None:
        if node.id.startswith("__") and node.id.endswith("__"):
            raise IllegalNodeError(
                f"dunder name '{node.id}' forbidden (SA-02 sandbox escape prevention)"
            )
        if not isinstance(node.ctx, ast.Load):
            raise IllegalNodeError(
                f"ast.Name '{node.id}' ctx must be Load, got {type(node.ctx).__name__}"
            )
        self._used_names.add(node.id)

    # ---------- 报告访问器 ----------

    @property
    def node_count(self) -> int:
        return self._node_count

    @property
    def max_depth_seen(self) -> int:
        return self._max_depth_seen

    @property
    def used_functions(self) -> frozenset[str]:
        return frozenset(self._used_functions)

    @property
    def used_names(self) -> frozenset[str]:
        return frozenset(self._used_names)


# ========== AST 求值(仅在 validate 通过后才调用) ==========


def _safe_eval_node(
    node: ast.AST,
    env: dict[str, Any],
    funcs: dict[str, Any],
) -> Any:
    """纯 ast 求值;env + funcs 只读。

    env: {name -> value} 供 Name 查。
    funcs: {func_name -> callable} 供 Call 查(白名单 已 validate 过)。
    """
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body, env, funcs)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise EvaluationError(f"name '{node.id}' not in guard_vars")
        return env[node.id]
    if isinstance(node, ast.BoolOp):
        values = [_safe_eval_node(v, env, funcs) for v in node.values]
        if isinstance(node.op, ast.And):
            result = True
            for v in values:
                result = result and v
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for v in values:
                result = result or v
            return result
        raise EvaluationError(f"BoolOp.op {type(node.op).__name__} unsupported")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _safe_eval_node(node.operand, env, funcs)
        raise EvaluationError(f"UnaryOp.op {type(node.op).__name__} unsupported")
    if isinstance(node, ast.Compare):
        left = _safe_eval_node(node.left, env, funcs)
        for op, right_node in zip(node.ops, node.comparators, strict=False):
            right = _safe_eval_node(right_node, env, funcs)
            if not _apply_cmp(op, left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Call.func must be Name(validated)")
        fname = node.func.id
        if fname not in funcs:
            raise EvaluationError(f"function '{fname}' not bound in funcs")
        args = [_safe_eval_node(a, env, funcs) for a in node.args]
        try:
            return funcs[fname](*args)
        except Exception as exc:
            raise EvaluationError(f"function '{fname}' call failed: {exc}") from exc
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        items = [_safe_eval_node(e, env, funcs) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(items)
        if isinstance(node, ast.Set):
            return set(items)
        return items
    raise EvaluationError(f"unsupported ast node in eval: {type(node).__name__}")


def _apply_cmp(op: ast.cmpop, left: Any, right: Any) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    if isinstance(op, ast.Is):
        return left is right
    if isinstance(op, ast.IsNot):
        return left is not right
    raise EvaluationError(f"unsupported cmp op: {type(op).__name__}")


# ========== 对外快捷接口 ==========


def safe_eval(
    expression_text: str,
    env: dict[str, Any],
    *,
    allowed_funcs: dict[str, int] | None = None,
    funcs_impl: dict[str, Any] | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> Any:
    """一把梭:parse + validate + eval。

    Args:
        expression_text: guard 表达式。
        env: {name -> value} 供 Name 读取(只读)。
        allowed_funcs: {func_name -> arg_count};None = 使用 DEFAULT_ALLOWED_FUNCS 签名。
        funcs_impl: {func_name -> callable};None = 使用 builtins 对应函数(同名)。
        max_depth / max_nodes: 安全预算。
    """
    if allowed_funcs is None:
        allowed_funcs = DEFAULT_ALLOWED_FUNCS
    if funcs_impl is None:
        funcs_impl = _build_default_funcs_impl(allowed_funcs)
    validator = SafeExprValidator(
        allowed_funcs=allowed_funcs,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )
    tree = validator.parse_and_validate(expression_text)
    return _safe_eval_node(tree, env, funcs_impl)


def _build_default_funcs_impl(allowed: dict[str, int]) -> dict[str, Any]:
    """把白名单函数名映射到 builtins 的同名函数。"""
    builtin_map: dict[str, Any] = {
        "len": len,
        "min": min,
        "max": max,
        "abs": abs,
        "bool": bool,
        "int": int,
        "float": float,
        "str": str,
        "round": round,
    }
    out: dict[str, Any] = {}
    for name in allowed:
        if name in builtin_map:
            out[name] = builtin_map[name]
    return out


def compute_ast_metrics(tree: ast.AST) -> tuple[int, int]:
    """返回 (max_depth, node_count)。"""
    if not isinstance(tree, ast.AST):
        return 0, 0

    node_count = 0
    max_depth = 0

    def _walk(node: ast.AST, d: int) -> None:
        nonlocal node_count, max_depth
        node_count += 1
        if d > max_depth:
            max_depth = d
        for child in ast.iter_child_nodes(node):
            _walk(child, d + 1)

    _walk(tree, 0)
    return max_depth, node_count


__all__ = [
    "ALLOWED_NODE_TYPES",
    "DEFAULT_ALLOWED_FUNCS",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MAX_NODES",
    "DENIED_NODE_TYPES",
    "SafeExprValidator",
    "compute_ast_metrics",
    "safe_eval",
]
