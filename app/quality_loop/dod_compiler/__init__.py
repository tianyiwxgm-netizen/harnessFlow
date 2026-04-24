"""L1-04 · L2-02 · DoD 表达式编译器.

对外暴露:
    - DoDExpressionCompiler  # 编译 DoD YAML → CompiledDoD
    - DoDEvaluator           # 运行期 eval CompiledDoD
    - schemas (Pydantic VO)
    - errors (错误码)

算法锚点:
    - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md §6
    - archive/stage_contracts/predicate_eval.py (AST 白名单基础)
"""
from __future__ import annotations

from app.quality_loop.dod_compiler.ast_nodes import (
    DENIED_NODE_TYPES,
    SafeExprValidator,
)
from app.quality_loop.dod_compiler.compiler import DoDExpressionCompiler
from app.quality_loop.dod_compiler.errors import (
    DoDCompileError,
    DoDEvalError,
    IllegalFunctionError,
    IllegalNodeError,
    RecursionLimitExceeded,
    WhitelistTamperingError,
)
from app.quality_loop.dod_compiler.evaluator import DoDEvaluator
from app.quality_loop.dod_compiler.schemas import (
    AddWhitelistRuleCommand,
    AddWhitelistRuleResult,
    CompileBatchCommand,
    CompileBatchResult,
    CompiledDoD,
    DoDClause,
    DoDExpression,
    DoDExpressionKind,
    EvalCommand,
    EvalResult,
    ListWhitelistRulesCommand,
    ListWhitelistRulesResult,
    ValidateCommand,
    ValidateResult,
    WhitelistASTRule,
)

__all__ = [
    "AddWhitelistRuleCommand",
    "AddWhitelistRuleResult",
    "CompileBatchCommand",
    "CompileBatchResult",
    "CompiledDoD",
    "DENIED_NODE_TYPES",
    "DoDClause",
    "DoDCompileError",
    "DoDEvalError",
    "DoDEvaluator",
    "DoDExpression",
    "DoDExpressionCompiler",
    "DoDExpressionKind",
    "EvalCommand",
    "EvalResult",
    "IllegalFunctionError",
    "IllegalNodeError",
    "ListWhitelistRulesCommand",
    "ListWhitelistRulesResult",
    "RecursionLimitExceeded",
    "SafeExprValidator",
    "ValidateCommand",
    "ValidateResult",
    "WhitelistASTRule",
    "WhitelistTamperingError",
]
