"""L1-04 · L2-02 · DoDExpressionCompiler 主类.

锚点:§3.1 compile_batch · §3.3 validate · §3.4 list_rules · §3.5 add_rule · §6.4 compile_single.

MVP 职责:
    1. compile_batch(clauses) → CompiledDoD (按 kind 分组)
    2. validate_expression(text) → ValidateResult (干跑)
    3. list_whitelist_rules(category) → 只读视图
    4. add_whitelist_rule(...) → offline-only 扩展
    5. compile_from_yaml(yaml_text) → CompiledDoD (便捷)
    6. 幂等:同 command_id + 同 clauses 返回 cache
"""
from __future__ import annotations

import ast
import hashlib
import json
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.quality_loop.dod_compiler.ast_nodes import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_NODES,
    SafeExprValidator,
    compute_ast_metrics,
)
from app.quality_loop.dod_compiler.errors import (
    ACReverseLookupFailedError,
    ASTSyntaxError,
    CompileOversizedError,
    DoDCompileError,
    IdempotencyViolationError,
    IllegalFunctionError,
    IllegalNodeError,
    NoProjectIdError,
    RecursionLimitExceeded,
)
from app.quality_loop.dod_compiler.predicate_eval import (
    WHITELISTED_DATA_SOURCE_KEYS,
    WhitelistRegistry,
)
from app.quality_loop.dod_compiler.safety_guard import (
    assert_no_danger_tokens,
    assert_offline_admin,
)
from app.quality_loop.dod_compiler.schemas import (
    AddWhitelistRuleCommand,
    AddWhitelistRuleResult,
    ASTTreeSummary,
    CompileBatchCommand,
    CompileBatchError,
    CompileBatchResult,
    CompiledDoD,
    DoDClause,
    DoDExpression,
    DoDExpressionKind,
    ExprStatistics,
    ListWhitelistRulesCommand,
    ListWhitelistRulesResult,
    UnmappableClause,
    ValidateCommand,
    ValidateResult,
    ValidateViolation,
    ViolationType,
    WhitelistASTRule,
    WhitelistCategory,
)
from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml

_MAX_YAML_SIZE_BYTES = 500 * 1024  # §11.1 COMPILE_OVERSIZED
_CACHE_SIZE_LIMIT = 10000  # Top-level cache cap


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dod_hash(clauses: list[DoDClause]) -> str:
    """DoD 表达式集合的稳定 hash (用于 dod_hash / cache key)."""
    material = json.dumps(
        [(c.clause_id, c.clause_text, list(c.source_ac_ids), c.kind.value) for c in clauses],
        sort_keys=True,
        ensure_ascii=False,
    )
    return _sha256_hex(material)


def _percentile(values: list[int], p: float = 95.0) -> int:
    """整数 p 百分位(简版 · 无 interpolation)."""
    if not values:
        return 0
    sorted_vals = sorted(values)
    k = int(round((p / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[max(0, min(k, len(sorted_vals) - 1))]


class DoDExpressionCompiler:
    """L1-04 L2-02 DoD 表达式编译器."""

    def __init__(
        self,
        *,
        whitelist_registry: WhitelistRegistry | None = None,
        offline_admin_mode: bool = False,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_nodes: int = DEFAULT_MAX_NODES,
    ) -> None:
        self._registry = whitelist_registry or WhitelistRegistry()
        self._offline_admin = bool(offline_admin_mode)
        self._max_depth = max_depth
        self._max_nodes = max_nodes
        # 幂等 cache: command_id → (input_hash, result)
        self._batch_cache: dict[str, tuple[str, CompileBatchResult]] = {}
        # expr_id → (DoDExpression, ast.Expression) 用于 evaluator 查找
        self._expressions: dict[str, tuple[DoDExpression, ast.Expression]] = {}
        self._lock = threading.Lock()
        # per-command lock · 串行化同 command_id 的并发 compile (§6.6 A06)
        self._command_locks: dict[str, threading.Lock] = {}
        self._command_locks_lock = threading.Lock()

    # ------------------------------------------------------------------
    # §3.1 compile_batch (主入口)
    # ------------------------------------------------------------------

    def compile_batch(self, cmd: CompileBatchCommand) -> CompileBatchResult:
        """批量编译 · 幂等 · 部分失败不 short-circuit."""
        if not cmd.project_id:
            raise NoProjectIdError("project_id is required")

        # 1. 取 per-command lock(防并发 compile 同 cmd_id · A06)
        with self._command_locks_lock:
            cmd_lock = self._command_locks.setdefault(cmd.command_id, threading.Lock())

        with cmd_lock:
            return self._compile_batch_locked(cmd)

    def _compile_batch_locked(self, cmd: CompileBatchCommand) -> CompileBatchResult:
        t0 = time.perf_counter()
        input_hash = self._cmd_fingerprint(cmd)

        with self._lock:
            cached = self._batch_cache.get(cmd.command_id)
            if cached is not None:
                fingerprint_prev, result = cached
                if fingerprint_prev != input_hash:
                    raise IdempotencyViolationError(
                        f"command_id {cmd.command_id} reused with different inputs"
                    )
                return result

        # 尺寸预检 (粗估)
        payload_size = sum(len(c.clause_text) for c in cmd.clauses)
        if payload_size > _MAX_YAML_SIZE_BYTES:
            raise CompileOversizedError(
                f"payload size {payload_size} > {_MAX_YAML_SIZE_BYTES}"
            )

        whitelist_version = cmd.whitelist_version or self._registry.version

        per_wp_counts: dict[str, int] = {}
        ast_depths: list[int] = []
        ast_node_counts: list[int] = []
        compiled_exprs: dict[DoDExpressionKind, list[DoDExpression]] = {
            DoDExpressionKind.HARD: [],
            DoDExpressionKind.SOFT: [],
            DoDExpressionKind.METRIC: [],
        }
        unmappable: list[UnmappableClause] = []
        errors: list[CompileBatchError] = []

        ac_ids_available = _extract_ac_ids(cmd.ac_matrix)

        new_expr_trees: list[tuple[DoDExpression, ast.Expression]] = []

        for clause in cmd.clauses:
            try:
                expr, tree = self._compile_single(
                    clause,
                    project_id=cmd.project_id,
                    whitelist_version=whitelist_version,
                    ac_ids_available=ac_ids_available,
                    enforce_ac_lookup=bool(cmd.ac_matrix),
                )
            except ACReverseLookupFailedError as exc:
                errors.append(CompileBatchError(
                    clause_id=clause.clause_id,
                    error_code=exc.error_code,
                    reason=str(exc),
                ))
                continue
            except (IllegalNodeError, IllegalFunctionError):
                # 安全红线:整体 reject(不加入 unmappable · 抛给调用方)
                raise
            except (ASTSyntaxError, RecursionLimitExceeded) as exc:
                errors.append(CompileBatchError(
                    clause_id=clause.clause_id,
                    error_code=exc.error_code,
                    reason=str(exc),
                ))
                continue
            except DoDCompileError as exc:
                # 归为 unmappable
                unmappable.append(UnmappableClause(
                    clause_id=clause.clause_id,
                    clause_text=clause.clause_text,
                    rejection_reason=f"{exc.error_code}: {exc}",
                    suggested_predicates=self._suggest_similar(clause.clause_text),
                ))
                continue

            compiled_exprs[clause.kind].append(expr)
            new_expr_trees.append((expr, tree))

            wp = expr.wp_id or "_global"
            per_wp_counts[wp] = per_wp_counts.get(wp, 0) + 1
            ast_depths.append(expr.ast_depth)
            ast_node_counts.append(expr.ast_node_count)

        compiled_count = sum(len(v) for v in compiled_exprs.values())

        # 构造 CompiledDoD
        set_id = f"dod-set-{uuid.uuid4()}"
        compiled_dod = CompiledDoD(
            set_id=set_id,
            project_id=cmd.project_id,
            blueprint_id=cmd.blueprint_id,
            wp_id=cmd.wp_id,
            hard=compiled_exprs[DoDExpressionKind.HARD],
            soft=compiled_exprs[DoDExpressionKind.SOFT],
            metric=compiled_exprs[DoDExpressionKind.METRIC],
            whitelist_version=whitelist_version,
            version=1,
            dod_hash=_dod_hash(list(cmd.clauses)),
            compiled_at=_now_iso(),
        )

        # 注册到 evaluator 可查表
        with self._lock:
            for expr, tree in new_expr_trees:
                self._expressions[expr.expr_id] = (expr, tree)
            # cache eviction
            if len(self._expressions) > _CACHE_SIZE_LIMIT:
                # 简单粗暴:丢一半
                half = len(self._expressions) // 2
                for k in list(self._expressions.keys())[:half]:
                    self._expressions.pop(k, None)

        result = CompileBatchResult(
            command_id=cmd.command_id,
            accepted=True,
            set_id=set_id,
            version=1,
            whitelist_version=whitelist_version,
            compiled_count=compiled_count,
            unmappable_clauses=unmappable,
            expr_statistics=ExprStatistics(
                total_exprs=compiled_count,
                per_wp=per_wp_counts,
                ast_depth_p95=_percentile(ast_depths, 95),
                ast_node_count_p95=_percentile(ast_node_counts, 95),
            ),
            duration_ms=int((time.perf_counter() - t0) * 1000),
            errors=errors,
            ts=_now_iso(),
            compiled=compiled_dod,
        )

        with self._lock:
            self._batch_cache[cmd.command_id] = (input_hash, result)

        return result

    # ------------------------------------------------------------------
    # 便捷:从 YAML 编译
    # ------------------------------------------------------------------

    def compile_from_yaml(
        self,
        yaml_text: str,
        *,
        project_id: str,
        blueprint_id: str | None = None,
        wp_id: str | None = None,
        ac_matrix: dict[str, Any] | None = None,
    ) -> CompileBatchResult:
        """YAML → CompileBatchResult · 封装 parse + compile_batch."""
        if len(yaml_text.encode("utf-8")) > _MAX_YAML_SIZE_BYTES:
            raise CompileOversizedError(
                f"yaml size > {_MAX_YAML_SIZE_BYTES} bytes"
            )
        grouped = parse_dod_yaml(yaml_text)
        all_clauses = (
            grouped[DoDExpressionKind.HARD]
            + grouped[DoDExpressionKind.SOFT]
            + grouped[DoDExpressionKind.METRIC]
        )
        cmd = CompileBatchCommand(
            command_id=f"cmd-{uuid.uuid4()}",
            project_id=project_id,
            blueprint_id=blueprint_id or "bp-yaml",
            clauses=all_clauses,
            ac_matrix=ac_matrix or {},
            wp_id=wp_id,
            ts=_now_iso(),
        )
        return self.compile_batch(cmd)

    # ------------------------------------------------------------------
    # §3.3 validate_expression (干跑 · 不固化)
    # ------------------------------------------------------------------

    def validate_expression(self, cmd: ValidateCommand) -> ValidateResult:
        """预校验 · 不 emit 事件 · 不缓存 · P95 ≤ 20ms."""
        text = cmd.expression_text
        violations: list[ValidateViolation] = []
        if not text.strip():
            violations.append(ValidateViolation(
                violation_type=ViolationType.EMPTY_EXPRESSION,
                detail="expression_text is empty",
            ))
            return ValidateResult(
                valid=False, violations=violations,
                whitelist_version=self._registry.version,
            )

        if len(text) > 2000:
            violations.append(ValidateViolation(
                violation_type=ViolationType.EXCEEDS_SIZE,
                detail=f"length {len(text)} > 2000",
            ))

        # 字符级危险 token 预检
        try:
            assert_no_danger_tokens(text)
        except IllegalNodeError as exc:
            violations.append(ValidateViolation(
                violation_type=ViolationType.ILLEGAL_NODE,
                detail=str(exc),
            ))
            return ValidateResult(
                valid=False, violations=violations,
                whitelist_version=self._registry.version,
            )

        # ast 级校验
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as exc:
            violations.append(ValidateViolation(
                violation_type=ViolationType.SYNTAX_ERROR,
                detail=str(exc),
                location={"lineno": exc.lineno or 0, "col_offset": exc.offset or 0},
            ))
            return ValidateResult(
                valid=False, violations=violations,
                whitelist_version=self._registry.version,
            )

        validator = SafeExprValidator(
            allowed_funcs=self._registry.allowed_funcs(),
            max_depth=self._max_depth,
            max_nodes=self._max_nodes,
        )
        try:
            validator.validate(tree)
        except IllegalFunctionError as exc:
            violations.append(ValidateViolation(
                violation_type=ViolationType.ILLEGAL_FUNCTION,
                detail=str(exc),
            ))
        except IllegalNodeError as exc:
            violations.append(ValidateViolation(
                violation_type=ViolationType.ILLEGAL_NODE,
                detail=str(exc),
            ))
        except RecursionLimitExceeded as exc:
            violations.append(ValidateViolation(
                violation_type=ViolationType.EXCEEDS_DEPTH,
                detail=str(exc),
            ))

        depth, node_count = compute_ast_metrics(tree)
        # 枚举 data_source 使用(扫 Name · 与 WHITELISTED_DATA_SOURCE_KEYS 对齐)
        used_ds: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id in WHITELISTED_DATA_SOURCE_KEYS:
                used_ds.add(n.id)
        summary = ASTTreeSummary(
            depth=depth,
            node_count=node_count,
            used_functions=sorted(validator.used_functions),
            used_data_source_types=sorted(used_ds),
        )
        return ValidateResult(
            valid=not violations,
            ast_tree_summary=summary,
            violations=violations,
            whitelist_version=self._registry.version,
        )

    # ------------------------------------------------------------------
    # §3.4 list_whitelist_rules (只读)
    # ------------------------------------------------------------------

    def list_whitelist_rules(self, cmd: ListWhitelistRulesCommand) -> ListWhitelistRulesResult:
        """返回当前白名单(deepcopy 防 SA-06 · frozen VO)."""
        rules: list[WhitelistASTRule] = []
        if cmd.category in (WhitelistCategory.ALL, WhitelistCategory.FUNCTION):
            for name, argc in self._registry.list_rules():
                rules.append(WhitelistASTRule(
                    rule_id=f"func-{name}",
                    name=name,
                    category=WhitelistCategory.FUNCTION,
                    arg_count=argc,
                    semantic_doc=f"predicate {name}",
                    added_version="1.0.0",
                    added_rationale="bootstrap default",
                ))
        if cmd.category in (WhitelistCategory.ALL, WhitelistCategory.DATA_SOURCE):
            for ds in sorted(WHITELISTED_DATA_SOURCE_KEYS):
                rules.append(WhitelistASTRule(
                    rule_id=f"ds-{ds}",
                    name=ds,
                    category=WhitelistCategory.DATA_SOURCE,
                    arg_count=0,
                    semantic_doc=f"data source {ds}",
                    added_version="1.0.0",
                    added_rationale="bootstrap default",
                    data_source_type=ds,
                ))
        return ListWhitelistRulesResult(
            whitelist_version=self._registry.version,
            rules=rules,
        )

    # ------------------------------------------------------------------
    # §3.5 add_whitelist_rule (仅 offline_admin)
    # ------------------------------------------------------------------

    def add_whitelist_rule(self, cmd: AddWhitelistRuleCommand) -> AddWhitelistRuleResult:
        assert_offline_admin(self._offline_admin, action="add_whitelist_rule")
        name = str(cmd.rule.get("name") or "")
        arg_count = int(cmd.rule.get("arg_count", 0))
        if not name:
            raise DoDCompileError("rule.name is required")
        new_version = self._registry.add_rule(name, arg_count, bump=cmd.version_bump_type.value)
        audit_id = f"audit-{uuid.uuid4()}"
        return AddWhitelistRuleResult(
            rule_id=f"func-{name}",
            new_whitelist_version=new_version,
            audit_log_id=audit_id,
            effective_at=_now_iso(),
        )

    # ------------------------------------------------------------------
    # evaluator 支撑接口 (internal)
    # ------------------------------------------------------------------

    def _get_expression_by_id(self, expr_id: str) -> tuple[DoDExpression, ast.Expression] | None:
        with self._lock:
            return self._expressions.get(expr_id)

    @property
    def registry(self) -> WhitelistRegistry:
        return self._registry

    @property
    def offline_admin_mode(self) -> bool:
        return self._offline_admin

    # ------------------------------------------------------------------
    # 内部 · 单条编译
    # ------------------------------------------------------------------

    def _compile_single(
        self,
        clause: DoDClause,
        *,
        project_id: str,
        whitelist_version: str,
        ac_ids_available: set[str],
        enforce_ac_lookup: bool,
    ) -> tuple[DoDExpression, ast.Expression]:
        """单条 · 失败抛异常."""
        text = clause.clause_text

        # 1. 预检字符级危险 token (字符串级防御)
        assert_no_danger_tokens(text)

        # 2. AST parse
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as exc:
            raise ASTSyntaxError(f"parse {clause.clause_id}: {exc}") from exc

        # 3. SafeExprValidator
        validator = SafeExprValidator(
            allowed_funcs=self._registry.allowed_funcs(),
            max_depth=self._max_depth,
            max_nodes=self._max_nodes,
        )
        validator.validate(tree)

        # 4. AC 反查
        if enforce_ac_lookup and ac_ids_available:
            missing = [a for a in clause.source_ac_ids if a not in ac_ids_available]
            if missing:
                raise ACReverseLookupFailedError(
                    f"source_ac_ids not in matrix: {missing}"
                )

        depth, node_count = compute_ast_metrics(tree)
        cache_key = _sha256_hex(f"{text}\u0001{whitelist_version}")
        expr_id = f"expr-{uuid.uuid4()}"
        expr = DoDExpression(
            expr_id=expr_id,
            project_id=project_id,
            wp_id=clause.wp_id,
            expression_text=text,
            kind=clause.kind,
            source_ac_ids=list(clause.source_ac_ids),
            whitelist_version=whitelist_version,
            cache_key=cache_key,
            ast_node_count=node_count,
            ast_depth=depth,
            compiled_at=_now_iso(),
            dod_hash=cache_key,
        )
        return expr, tree

    def _suggest_similar(self, text: str) -> list[dict[str, Any]]:
        """未命中白名单时的 suggest(Levenshtein-ish)."""
        names = [n for n, _ in self._registry.list_rules()]
        scores: list[tuple[float, str]] = []
        text_lower = text.lower()
        for name in names:
            s = _similarity(text_lower, name.lower())
            scores.append((s, name))
        scores.sort(reverse=True)
        return [
            {"predicate_name": name, "similarity_score": round(score, 3)}
            for score, name in scores[:3]
        ]

    def _cmd_fingerprint(self, cmd: CompileBatchCommand) -> str:
        """幂等 key:基于 clauses + ac_matrix + whitelist_version."""
        material = json.dumps(
            {
                "project_id": cmd.project_id,
                "blueprint_id": cmd.blueprint_id,
                "clauses": [
                    (c.clause_id, c.clause_text, list(c.source_ac_ids), c.kind.value)
                    for c in cmd.clauses
                ],
                "ac_matrix_keys": sorted((cmd.ac_matrix or {}).keys()),
                "whitelist_version": cmd.whitelist_version,
                "wp_id": cmd.wp_id,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return _sha256_hex(material)


# ========== helpers ==========


def _extract_ac_ids(ac_matrix: dict[str, Any]) -> set[str]:
    """从 ac_matrix 提取所有 ac id."""
    if not ac_matrix:
        return set()
    ids: set[str] = set()
    acs = ac_matrix.get("acs") or ac_matrix.get("entries") or []
    if isinstance(acs, list):
        for a in acs:
            if isinstance(a, dict) and "id" in a:
                ids.add(str(a["id"]))
            elif isinstance(a, str):
                ids.add(a)
    # 也支持顶层映射(ac_id → detail)
    for k, v in ac_matrix.items():
        if k in {"acs", "entries"}:
            continue
        if isinstance(v, dict) and isinstance(k, str):
            ids.add(k)
    return ids


def _similarity(a: str, b: str) -> float:
    """轻量 Jaccard-ish · 不引入 Levenshtein 依赖."""
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


__all__ = [
    "DoDExpressionCompiler",
]
