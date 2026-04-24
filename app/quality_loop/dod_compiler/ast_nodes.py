"""L1-04 · L2-02 · AST 白名单 + SafeExprValidator.

锚点:docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md §6.1
复用策略:vendor 自 archive/stage_contracts/predicate_eval.py 核心算法(AST walk)
         + 加强 L2-02 §6.1 白名单 + 深度 / 节点上限 / dunder / Starred / keyword 禁用.

安全红线:
    1. 禁 ast.Import / ast.ImportFrom
    2. 禁 ast.Attribute 作为 Call.func(防 __builtins__.eval 链式逃逸)
    3. 禁 ast.Lambda / FunctionDef / ClassDef
    4. 禁 Comprehensions / Loops / Try / Assign
    5. 禁 dunder name (__name__, __class__, __mro__, __import__, ...)
    6. 禁 keyword / starred args
    7. AST 深度 ≤ max_depth (防递归炸弹 · SA-03)
    8. AST 节点数 ≤ max_nodes (防资源耗尽)
    9. Constant 范围限制(str ≤ 500 · int ≤ 10^9)
"""
from __future__ import annotations

import ast
from collections.abc import Mapping

from app.quality_loop.dod_compiler.errors import (
    ASTSyntaxError,
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
    # 函数调用 (白名单 functions only)
    ast.Call,
    # 容器字面量(供 in / not in 使用)
    ast.List, ast.Tuple, ast.Set,
})

# 显式黑名单(冗余防御)
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


# ========== SafeExprValidator ==========


class SafeExprValidator:
    """AST 白名单 + 资源限制校验器.

    不执行 AST · 只 walk · 失败抛异常.
    """

    def __init__(
        self,
        *,
        allowed_funcs: Mapping[str, int] | None = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_nodes: int = DEFAULT_MAX_NODES,
        max_str_const: int = DEFAULT_MAX_STR_CONST,
        max_int_const: int = DEFAULT_MAX_INT_CONST,
    ) -> None:
        """构造.

        Args:
            allowed_funcs: {func_name -> arg_count}. None → 允许 _any_ Name Call
                但实际 compiler 应当传入固定白名单.
            max_depth / max_nodes / max_str_const / max_int_const: 安全预算.
        """
        self._allowed_funcs = dict(allowed_funcs) if allowed_funcs is not None else None
        self._max_depth = max_depth
        self._max_nodes = max_nodes
        self._max_str_const = max_str_const
        self._max_int_const = max_int_const
        # 每次 validate 调用都重置
        self._node_count = 0
        self._max_depth_seen = 0
        self._used_functions: set[str] = set()
        self._used_names: set[str] = set()

    # ---------- 公共入口 ----------

    def parse_and_validate(self, expression_text: str) -> ast.Expression:
        """合并 parse + walk · 返回合法 ast.Expression."""
        if not isinstance(expression_text, str) or not expression_text.strip():
            raise ASTSyntaxError("expression is empty")
        try:
            tree = ast.parse(expression_text, mode="eval")
        except SyntaxError as exc:
            raise ASTSyntaxError(f"ast.parse failed: {exc}") from exc
        self.validate(tree)
        return tree

    def validate(self, tree: ast.AST) -> None:
        """Walk AST · 失败抛异常 · 成功 return None.

        使用前请手动 reset 统计计数器(内部会做).
        """
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
        # 1. 节点计数
        self._node_count += 1
        if self._node_count > self._max_nodes:
            raise RecursionLimitExceeded(
                f"ast nodes={self._node_count} > max={self._max_nodes}"
            )
        # 2. 深度
        if depth > self._max_depth:
            raise RecursionLimitExceeded(
                f"ast depth={depth} > max={self._max_depth}"
            )
        if depth > self._max_depth_seen:
            self._max_depth_seen = depth

        node_type = type(node)
        # 3. 显式黑名单(先于白名单 · 冗余防御)
        if node_type in DENIED_NODE_TYPES:
            raise IllegalNodeError(
                f"denied ast node: {node_type.__name__}"
            )
        # 4. 白名单
        if node_type not in ALLOWED_NODE_TYPES:
            raise IllegalNodeError(
                f"ast node not in whitelist: {node_type.__name__}"
            )

        # 5. 针对性强化
        if isinstance(node, ast.Call):
            self._check_call(node)
        elif isinstance(node, ast.Constant):
            self._check_constant(node)
        elif isinstance(node, ast.Name):
            self._check_name(node)

        # 6. 递归下探
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
        # 白名单检查
        if self._allowed_funcs is not None and fname not in self._allowed_funcs:
            raise IllegalFunctionError(
                f"function '{fname}' not in whitelist"
            )
        # 禁止 keyword / starred args(降低注入面)
        if node.keywords:
            raise IllegalNodeError(
                "keyword arguments forbidden in DoD calls (positional only)"
            )
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                raise IllegalNodeError("*args (Starred) forbidden")
        # 签名简易校验(数量)
        if self._allowed_funcs is not None:
            expected = self._allowed_funcs[fname]
            if expected >= 0 and len(node.args) != expected:
                raise IllegalFunctionError(
                    f"function '{fname}' expects {expected} args, got {len(node.args)}"
                )
        self._used_functions.add(fname)

    def _check_constant(self, node: ast.Constant) -> None:
        v = node.value
        # 只允许 int/float/str/bool/None
        if not isinstance(v, (int, float, str, bool, type(None))):
            raise IllegalNodeError(
                f"ast.Constant value type {type(v).__name__} forbidden"
            )
        # str 限长
        if isinstance(v, str) and len(v) > self._max_str_const:
            raise RecursionLimitExceeded(
                f"str Constant len={len(v)} > max={self._max_str_const}"
            )
        # int 范围 (bool 也是 int 子类,先放过)
        if isinstance(v, int) and not isinstance(v, bool):
            if abs(v) > self._max_int_const:
                raise RecursionLimitExceeded(
                    f"int Constant {v} exceeds max={self._max_int_const}"
                )

    def _check_name(self, node: ast.Name) -> None:
        # 禁 dunder (__builtins__ / __import__ / __class__ / ...)
        if node.id.startswith("__") and node.id.endswith("__"):
            raise IllegalNodeError(
                f"dunder name '{node.id}' forbidden (SA-02 sandbox escape prevention)"
            )
        # 必须 Load ctx
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


# ========== 便捷函数 ==========


def compute_ast_metrics(tree: ast.AST) -> tuple[int, int]:
    """返回 (depth, node_count)."""
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
    "DENIED_NODE_TYPES",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MAX_NODES",
    "SafeExprValidator",
    "compute_ast_metrics",
]
