"""DoD 编译器适配层 · WP01 L2-02 DoD 表达式编译器的接口代理。

当前 WP01 (`agent a449da3beb3010017`) 仍在并行开发 · DoD YAML 语法 / CompiledDoD schema
均未最终定型 · 本 WP02 **用 MockDoDAdapter 解耦**。WP01 完成后 · 本模块将：

  1. import app.quality_loop.dod_compiler.compile_dod / eval_predicate
  2. 把 ACItem.structured["expected"] 通过 compile_dod 编译成 CompiledDoD
  3. 将编译结果作为 priority_annotation 的辅助（§1.4 L2-02 "回传 dod_unmappable"）

同步给 WP01 的接口预期（主会话备忘）：

    class DoDCompiler(Protocol):
        def compile_dod(self, expression: str) -> CompiledDoD: ...
        def eval_predicate(self, compiled: CompiledDoD, evidence: dict) -> EvalResult: ...
        def compute_dod_hash(self, compiled: CompiledDoD) -> str: ...

    class CompiledDoD(Protocol):
        expression: str
        ast_hash: str
        hard: list[str]
        soft: list[str]
        metric: list[str]

    class EvalResult(Protocol):
        passed: bool
        reason: str
        missing: list[str]

WP01 落地后 · `DoDAdapter` 做 Protocol → 具体实现的桥接。本 WP 只提供 MockDoDAdapter。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# 接口 Protocol（与 WP01 约定）
# ---------------------------------------------------------------------------


class DoDAdapter(Protocol):
    """抽象 DoD 适配器。WP02 只用 compile / hash · eval 留给 L2-04/06。"""

    def compile_expression(self, expression: str) -> "CompiledExpr":
        """编译 DoD 表达式为可复用的 CompiledExpr · 同表达式返回同 hash。"""
        ...

    def compute_dod_hash(self, compiled: "CompiledExpr") -> str:
        ...


@dataclass(frozen=True)
class CompiledExpr:
    expression: str
    ast_hash: str
    whitelisted: bool = True
    notes: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mock 实现（供 WP02 单测 + 首次集成）
# ---------------------------------------------------------------------------


class MockDoDAdapter:
    """Mock · 幂等 hash 基于表达式字符串（WP01 完后替换成真 AST hash）。"""

    def __init__(self) -> None:
        self._cache: dict[str, CompiledExpr] = {}

    def compile_expression(self, expression: str) -> CompiledExpr:
        expr = (expression or "").strip()
        cached = self._cache.get(expr)
        if cached is not None:
            return cached
        # 粗白名单 · 不含 exec/eval/import/dunder
        forbidden = ("exec", "eval(", "__", "import ")
        whitelisted = not any(bad in expr for bad in forbidden)
        compiled = CompiledExpr(
            expression=expr,
            ast_hash=self._hash(expr),
            whitelisted=whitelisted,
            notes={"mock": True},
        )
        self._cache[expr] = compiled
        return compiled

    def compute_dod_hash(self, compiled: CompiledExpr) -> str:
        return compiled.ast_hash

    @staticmethod
    def _hash(expression: str) -> str:
        import hashlib
        return "mock-sha256:" + hashlib.sha256(expression.encode("utf-8")).hexdigest()[:24]


__all__ = ["DoDAdapter", "CompiledExpr", "MockDoDAdapter"]
