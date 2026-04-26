"""Slice A — gate_predicate evaluator (white-listed AST)."""
from __future__ import annotations

import ast
import re
from typing import Any

_NULL_TOKEN_RE = re.compile(r"\bnull\b")


class GateEvalError(Exception):
    pass


_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.Compare, ast.Name, ast.Constant,
    ast.Attribute, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.Load,
)


def _resolve(name_or_attr: ast.AST, ctx: dict) -> Any:
    """Resolve `a.b.c` → ctx['a']['b']['c'], returning None if any missing."""
    parts: list[str] = []
    n = name_or_attr
    while isinstance(n, ast.Attribute):
        parts.insert(0, n.attr)
        n = n.value
    if not isinstance(n, ast.Name):
        raise GateEvalError(f"unsupported lvalue: {ast.dump(n)}")
    parts.insert(0, n.id)
    cur: Any = ctx
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def _eval(node: ast.AST, ctx: dict) -> Any:
    if not isinstance(node, _ALLOWED_NODES):
        raise GateEvalError(f"forbidden AST node: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _resolve(node, ctx)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, ctx) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(vals)
        if isinstance(node.op, ast.Or):
            return any(vals)
        raise GateEvalError(f"forbidden BoolOp: {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ctx)
            if isinstance(op, ast.Eq):
                if not (left == right):
                    return False
            elif isinstance(op, ast.NotEq):
                if not (left != right):
                    return False
            elif isinstance(op, ast.Lt):
                if not (left is not None and right is not None and left < right):
                    return False
            elif isinstance(op, ast.LtE):
                if not (left is not None and right is not None and left <= right):
                    return False
            elif isinstance(op, ast.Gt):
                if not (left is not None and right is not None and left > right):
                    return False
            elif isinstance(op, ast.GtE):
                if not (left is not None and right is not None and left >= right):
                    return False
            else:
                raise GateEvalError(f"forbidden cmp op: {type(op).__name__}")
            left = right
        return True
    raise GateEvalError(f"unhandled node: {type(node).__name__}")


def eval_predicate(expr: str, ctx: dict) -> bool:
    """Eval a gate_predicate expression against task-board ctx.

    `null` literal → Python None. AND/OR (uppercase) accepted as alias.
    `null` is replaced only at word boundaries so `null_field` is preserved.
    """
    normalized = expr.replace(" AND ", " and ").replace(" OR ", " or ")
    normalized = _NULL_TOKEN_RE.sub("None", normalized)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as e:
        raise GateEvalError(f"parse error in {expr!r}: {e}") from e
    try:
        result = _eval(tree, ctx)
    except GateEvalError as e:
        raise GateEvalError(f"{e} (in expr {expr!r})") from e
    return bool(result)
