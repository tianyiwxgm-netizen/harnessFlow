"""L1-04 · L2-02 · Pydantic VO + Command schemas.

锚点:
    - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md §2.3 + §3
    - 所有 VO 不可变(frozen=True)
    - PM-14: 所有 command 首字段 project_id(除 ValidateCommand · ListWhitelistRules 中亦带)
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ==================== 枚举 ====================


class DoDExpressionKind(str, Enum):
    """DoD 三分类(brief §5.2):hard / soft / metric."""

    HARD = "hard"
    SOFT = "soft"
    METRIC = "metric"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class ViolationType(str, Enum):
    """§3.3 validate_expression 违规分类."""

    ILLEGAL_NODE = "illegal_node"
    ILLEGAL_FUNCTION = "illegal_function"
    EXCEEDS_DEPTH = "exceeds_depth"
    EXCEEDS_SIZE = "exceeds_size"
    SYNTAX_ERROR = "syntax_error"
    EMPTY_EXPRESSION = "empty_expression"


class WhitelistCategory(str, Enum):
    NODE = "node"
    FUNCTION = "function"
    DATA_SOURCE = "data_source"
    ALL = "all"


class EvalCaller(str, Enum):
    """§3.2.2 caller 白名单(SA-07 防伪冒)."""

    L2_05_WP_SELF_CHECK = "L2-05_wp_self_check"
    L2_06_S5_VERIFIER = "L2-06_s5_verifier"
    VERIFIER_SUBAGENT = "verifier_subagent"
    L2_04_GATE_CONFIG_CHECK = "L2-04_gate_config_check"


class VersionBumpType(str, Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


# ==================== 核心 VO ====================


class DoDClause(BaseModel):
    """§3.1.2 compile_batch 入参 · clauses[i]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clause_id: str = Field(..., min_length=1)
    clause_text: str = Field(..., min_length=5, max_length=2000)
    source_ac_ids: list[str] = Field(..., min_length=1)
    priority: Priority = Priority.P1
    wp_id: str | None = None
    kind: DoDExpressionKind = DoDExpressionKind.HARD


class WhitelistASTRule(BaseModel):
    """§2.3.2 WhitelistASTRule · 白名单条目 VO · 运行期只读."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    name: str
    category: WhitelistCategory
    arg_count: int = 0
    signature: dict[str, Any] | None = None
    semantic_doc: str = Field(default="", min_length=0)
    added_version: str = "1.0.0"
    added_rationale: str = ""
    data_source_type: str | None = None


class DoDExpression(BaseModel):
    """§2.3.1 DoDExpression · 核心 VO · 编译产物.

    注:`ast` 字段为 dict (ast.dump → dict)· 防序列化带 ast.AST 对象.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr_id: str
    project_id: str
    wp_id: str | None = None
    expression_text: str
    kind: DoDExpressionKind = DoDExpressionKind.HARD
    source_ac_ids: list[str] = Field(default_factory=list, min_length=1)
    whitelist_version: str = "1.0.0"
    cache_key: str = ""
    ast_node_count: int = 0
    ast_depth: int = 0
    compiled_at: str = ""
    dod_hash: str = ""

    @field_validator("source_ac_ids")
    @classmethod
    def _non_empty_source_ac(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("source_ac_ids must have at least 1 entry (§9.4 硬约束 4)")
        return v


class CompiledDoD(BaseModel):
    """聚合根 VO · 对应 DoDExpressionSet · 一个 DoD YAML 编译产物.

    包含 hard/soft/metric 三类表达式集合.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    set_id: str
    project_id: str
    blueprint_id: str | None = None
    wp_id: str | None = None
    hard: list[DoDExpression] = Field(default_factory=list)
    soft: list[DoDExpression] = Field(default_factory=list)
    metric: list[DoDExpression] = Field(default_factory=list)
    whitelist_version: str = "1.0.0"
    version: int = 1
    dod_hash: str = ""
    compiled_at: str = ""

    def all_expressions(self) -> list[DoDExpression]:
        return list(self.hard) + list(self.soft) + list(self.metric)


class UnmappableClause(BaseModel):
    """§3.1.3 未命中白名单条款."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clause_id: str
    clause_text: str
    rejection_reason: str
    suggested_predicates: list[dict[str, Any]] = Field(default_factory=list)


# ==================== Command / Result ====================


class CompileBatchCommand(BaseModel):
    """§3.1.2 compile_batch 入参."""

    model_config = ConfigDict(extra="ignore")

    command_id: str
    project_id: str
    blueprint_id: str = "bp-default"
    clauses: list[DoDClause] = Field(..., min_length=1, max_length=500)
    ac_matrix: dict[str, Any] = Field(default_factory=dict)
    wp_id: str | None = None
    whitelist_version: str | None = None
    timeout_s: int = 120
    ts: str = ""


class ExprStatistics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_exprs: int = 0
    per_wp: dict[str, int] = Field(default_factory=dict)
    ast_depth_p95: int = 0
    ast_node_count_p95: int = 0


class CompileBatchError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    clause_id: str
    error_code: str
    reason: str


class CompileBatchResult(BaseModel):
    """§3.1.3 compile_batch 出参."""

    model_config = ConfigDict(extra="forbid")

    command_id: str
    accepted: bool
    set_id: str
    version: int = 1
    whitelist_version: str = "1.0.0"
    compiled_count: int = 0
    unmappable_clauses: list[UnmappableClause] = Field(default_factory=list)
    expr_statistics: ExprStatistics = Field(default_factory=ExprStatistics)
    duration_ms: int = 0
    errors: list[CompileBatchError] = Field(default_factory=list)
    ts: str = ""
    compiled: CompiledDoD | None = None


class EvalCommand(BaseModel):
    """§3.2.2 eval_expression 入参."""

    model_config = ConfigDict(extra="ignore")

    command_id: str
    project_id: str
    expr_id: str
    data_sources_snapshot: dict[str, Any] = Field(default_factory=dict)
    caller: EvalCaller = EvalCaller.L2_05_WP_SELF_CHECK
    timeout_ms: int = Field(default=500, le=2000, ge=1)
    ts: str = ""


class EvalResult(BaseModel):
    """§3.2.3 eval_expression 出参 (VO)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str
    eval_id: str
    project_id: str
    expr_id: str
    pass_: bool = Field(..., alias="pass")
    reason: str = Field(..., min_length=10)
    evidence_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    whitelist_version: str = "1.0.0"
    evaluated_at: str = ""
    caller: EvalCaller = EvalCaller.L2_05_WP_SELF_CHECK
    cache_hit: bool = False


class ValidateCommand(BaseModel):
    """§3.3 validate_expression 入参."""

    model_config = ConfigDict(extra="ignore")

    project_id: str = "_validate"
    expression_text: str = Field(..., min_length=1, max_length=2500)
    whitelist_version: str = "current"


class ASTTreeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int = 0
    node_count: int = 0
    used_functions: list[str] = Field(default_factory=list)
    used_data_source_types: list[str] = Field(default_factory=list)


class ValidateViolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    violation_type: ViolationType
    detail: str
    location: dict[str, int] = Field(default_factory=dict)


class ValidateResult(BaseModel):
    """§3.3 validate_expression 出参."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    ast_tree_summary: ASTTreeSummary | None = None
    violations: list[ValidateViolation] = Field(default_factory=list)
    whitelist_version: str = "1.0.0"


class ListWhitelistRulesCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: WhitelistCategory = WhitelistCategory.ALL


class ListWhitelistRulesResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    whitelist_version: str
    rules: list[WhitelistASTRule] = Field(default_factory=list)


class OfflineReviewMemo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    review_date: str
    reviewers: list[str] = Field(..., min_length=2)
    rationale: str = Field(..., min_length=50)
    test_coverage_plan: str = Field(..., min_length=20)


class AddWhitelistRuleCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rule: dict[str, Any]
    offline_review_memo: OfflineReviewMemo
    version_bump_type: VersionBumpType = VersionBumpType.MINOR
    operator: str
    signature: str


class AddWhitelistRuleResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    new_whitelist_version: str
    audit_log_id: str
    effective_at: str


__all__ = [
    "AddWhitelistRuleCommand",
    "AddWhitelistRuleResult",
    "ASTTreeSummary",
    "CompileBatchCommand",
    "CompileBatchError",
    "CompileBatchResult",
    "CompiledDoD",
    "DoDClause",
    "DoDExpression",
    "DoDExpressionKind",
    "EvalCaller",
    "EvalCommand",
    "EvalResult",
    "ExprStatistics",
    "ListWhitelistRulesCommand",
    "ListWhitelistRulesResult",
    "OfflineReviewMemo",
    "Priority",
    "UnmappableClause",
    "ValidateCommand",
    "ValidateResult",
    "ValidateViolation",
    "VersionBumpType",
    "ViolationType",
    "WhitelistASTRule",
    "WhitelistCategory",
]
