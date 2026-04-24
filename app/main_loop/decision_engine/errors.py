"""L1-01 L2-02 · 决策引擎错误码(聚焦 WP03 AST + KB 分支)。

对齐 L2-02 §3.1.2 / §11 全量 17 项的相关子集;其余 10 余项由 L2-02 主体包实现,
本 WP03 仅实现 AST 白名单 + KB boost + history weight + 降级相关错误。
"""
from __future__ import annotations


class DecisionError(Exception):
    """所有决策引擎错误的基类。

    Attributes:
        code: 稳定错误码(`E_*`),调用方可 pattern-match。
        message: 人类可读说明。
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---- Context 合法性 ----


class CtxNoProjectIdError(DecisionError):
    def __init__(self, detail: str = "DecisionContext.project_id is falsy") -> None:
        super().__init__("E_CTX_NO_PROJECT_ID", detail)


class CtxStateMissingError(DecisionError):
    def __init__(self, detail: str = "DecisionContext.state missing or invalid") -> None:
        super().__init__("E_CTX_STATE_MISSING", detail)


# ---- AST 白名单 ----


class ASTSyntaxError(DecisionError):
    """guard_expr 语法错误;无法被 ast.parse。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_AST_SYNTAX", detail)


class IllegalNodeError(DecisionError):
    """guard_expr 包含不允许的 AST 节点类型。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_AST_ILLEGAL_NODE", detail)


class IllegalFunctionError(DecisionError):
    """guard_expr 调用了白名单之外的函数。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_AST_ILLEGAL_FUNCTION", detail)


class RecursionLimitExceeded(DecisionError):
    """AST 深度 / 节点数 / 常量长度超限;防资源耗尽。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_AST_RECURSION_LIMIT", detail)


class EvaluationError(DecisionError):
    """AST walk 合法但 evaluate 时异常(如变量未定义)。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_AST_EVAL_FAIL", detail)


# ---- KB 注入 ----


class KBInjectError(DecisionError):
    """KB 调用失败 且 降级也失败(罕见)。不建议抛出;默认降级静默继续。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_KB_INJECT_FAIL", detail)


# ---- 决策选择 ----


class DecisionNoCandidateError(DecisionError):
    """候选全部不合法且无 fallback_candidate。"""

    def __init__(self, detail: str = "no candidate survived and no fallback provided") -> None:
        super().__init__("E_DECISION_NO_CANDIDATE", detail)


class DecisionNoReasonError(DecisionError):
    """产出的 reason < 20 字;自动补全失败时抛。"""

    def __init__(self, detail: str) -> None:
        super().__init__("E_DECISION_NO_REASON", detail)


class InvalidDecisionTypeError(DecisionError):
    """decision_type 不在 12 类白名单内。"""

    def __init__(self, decision_type: str) -> None:
        super().__init__(
            "E_DECISION_TYPE_INVALID",
            f"decision_type '{decision_type}' not in whitelist",
        )


__all__ = [
    "ASTSyntaxError",
    "CtxNoProjectIdError",
    "CtxStateMissingError",
    "DecisionError",
    "DecisionNoCandidateError",
    "DecisionNoReasonError",
    "EvaluationError",
    "IllegalFunctionError",
    "IllegalNodeError",
    "InvalidDecisionTypeError",
    "KBInjectError",
    "RecursionLimitExceeded",
]
