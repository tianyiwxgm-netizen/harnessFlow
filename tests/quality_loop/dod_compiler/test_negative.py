"""§3 负向 TC · TC-L104-L202-101 ~ 122(每错误码 ≥ 1).

覆盖 §3.6 + §11.1 错误码:
    - NO_PROJECT_ID / CROSS_PROJECT / AST_SYNTAX / AST_ILLEGAL_NODE /
      AST_ILLEGAL_FUNCTION / AC_REVERSE_LOOKUP_FAILED / RECURSION_LIMIT /
      DATA_SOURCE_INVALID / DATA_SOURCE_UNKNOWN_TYPE /
      WHITELIST_VERSION_MISMATCH / CALLER_UNAUTHORIZED / IDEMPOTENCY_VIOLATION /
      ONLINE_WHITELIST_MUTATION / COMPILE_OVERSIZED.

AST 非法场景含 exec / import / dunder / Attribute / Lambda / 多语句 / Starred.
"""
from __future__ import annotations

import pytest

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    DoDEvaluator,
    DoDExpressionCompiler,
    EvalCommand,
    IllegalFunctionError,
    IllegalNodeError,
    ValidateCommand,
)
from app.quality_loop.dod_compiler.errors import (
    CrossProjectError,
    DataSourceUnknownTypeError,
    IdempotencyViolationError,
    NoProjectIdError,
    OnlineWhitelistMutationError,
    WhitelistVersionMismatchError,
)
from app.quality_loop.dod_compiler.schemas import (
    DoDClause,
    DoDExpressionKind,
)


class TestNegativeInputValidation:
    """入参校验(pid / idempotency)."""

    def test_TC_L104_L202_101_no_project_id_rejected(
        self, sut: DoDExpressionCompiler, make_compile_request,
    ) -> None:
        req = make_compile_request(clause_count=1, project_id="")
        with pytest.raises(NoProjectIdError) as exc:
            sut.compile_batch(req)
        assert exc.value.error_code == "E_L204_L202_NO_PROJECT_ID"

    def test_TC_L104_L202_118_idempotency_violation_same_id_different_clauses(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req_a = make_compile_request(
            project_id=mock_project_id, clause_count=2, command_id="cmd-dup-01",
        )
        sut.compile_batch(req_a)
        req_b = make_compile_request(
            project_id=mock_project_id, clause_count=3, command_id="cmd-dup-01",
        )
        with pytest.raises(IdempotencyViolationError) as exc:
            sut.compile_batch(req_b)
        assert exc.value.error_code == "E_L204_L202_IDEMPOTENCY_VIOLATION"


class TestNegativeAstSafety:
    """AST 白名单 · 核心安全."""

    # 103 · AST_SYNTAX_ERROR
    def test_TC_L104_L202_103_ast_syntax_error_in_single_clause(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(
            project_id=mock_project_id,
            clause_count=3,
            inject_syntax_error_indices=[1],
        )
        resp = sut.compile_batch(req)
        assert resp.compiled_count == 2
        assert len(resp.errors) == 1
        assert resp.errors[0].error_code == "E_L204_L202_AST_SYNTAX_ERROR"

    # 104 · AST_ILLEGAL_NODE · import 类
    @pytest.mark.parametrize("dangerous", [
        "__import__('os')",
        "import os",
        "from os import system",
        "lambda x: x + 1",
        "coverage.line_rate >= 0.8",  # Attribute on non-whitelist name
        "line_coverage() ; lint_errors()",  # 多语句
        "line_coverage().__class__",
        "__builtins__",
        "eval('1+1')",
        "exec('pass')",
    ])
    def test_TC_L104_L202_104_illegal_node_forms_rejected_compile(
        self,
        sut: DoDExpressionCompiler,
        mock_project_id: str,
        dangerous: str,
    ) -> None:
        cmd = CompileBatchCommand(
            command_id="cmd-dangerous",
            project_id=mock_project_id,
            blueprint_id="bp-dangerous",
            clauses=[DoDClause(
                clause_id=f"c-danger-{hash(dangerous)}",
                clause_text=dangerous,
                source_ac_ids=["ac-danger-1"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-danger-1"}]},
        )
        with pytest.raises((IllegalNodeError, IllegalFunctionError)):
            sut.compile_batch(cmd)

    # 104 · 再在 validate_expression 确认同样拒绝(干跑路径也必须安全)
    @pytest.mark.parametrize("dangerous", [
        "__import__('os')",
        "import os",
        "lambda x: x + 1",
        "line_coverage() ; lint_errors()",
        "__class__",
        "eval('1+1')",
    ])
    def test_TC_L104_L202_104b_illegal_node_rejected_validate(
        self, sut: DoDExpressionCompiler, mock_project_id: str, dangerous: str,
    ) -> None:
        resp = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id,
            expression_text=dangerous,
        ))
        assert resp.valid is False

    # 105 · AST_ILLEGAL_FUNCTION (非白名单函数调用)
    def test_TC_L104_L202_105_ast_illegal_function_not_in_whitelist(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        cmd = CompileBatchCommand(
            command_id="cmd-illegal-fn",
            project_id=mock_project_id,
            blueprint_id="bp-1",
            clauses=[DoDClause(
                clause_id="c-illegal",
                clause_text="sqrt(4) > 0",
                source_ac_ids=["ac-i-1"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-i-1"}]},
        )
        with pytest.raises(IllegalFunctionError) as exc:
            sut.compile_batch(cmd)
        assert exc.value.error_code == "E_L204_L202_AST_ILLEGAL_FUNCTION"

    # 109 · RECURSION_LIMIT (深度 · BoolOp 实际建深度)
    def test_TC_L104_L202_109a_recursion_limit_depth(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        # 用嵌套 not 构造真实 AST 深度(每层 UnaryOp)
        # 40 层 not → UnaryOp(Not, UnaryOp(Not, ...))
        expr = ("not " * 40) + "p0_cases_all_pass()"
        resp = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id, expression_text=expr,
        ))
        assert resp.valid is False
        assert any(
            v.violation_type.value in ("exceeds_depth", "exceeds_size", "syntax_error")
            for v in resp.violations
        )

    # 109 · RECURSION_LIMIT (节点数)
    def test_TC_L104_L202_109b_recursion_limit_node_count(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        # " and line_coverage() >= 0.8" 重复 · 每次 +6 节点 · 要超 200 需要 ~34
        parts = ["line_coverage() >= 0.8"] * 40
        expr = " and ".join(parts)
        resp = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id, expression_text=expr,
        ))
        assert resp.valid is False

    def test_TC_L104_L202_104c_starred_args_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        args = [1, 2, 3]  # noqa: F841 (doc)
        resp = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id,
            expression_text="length(*args)",
        ))
        assert resp.valid is False

    def test_TC_L104_L202_104d_keyword_args_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        resp = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id,
            expression_text='has_file(path="x")',
        ))
        assert resp.valid is False


class TestNegativeEvalErrors:
    """eval 运行期负向."""

    # 102 · CROSS_PROJECT
    def test_TC_L104_L202_102_cross_project_eval_blocked(
        self, evaluator: DoDEvaluator, mock_project_id: str,
        ready_expr_id_of_other_project: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id_of_other_project,
            coverage_value=0.9,
        )
        with pytest.raises(CrossProjectError):
            evaluator.eval_expression(req)

    # 111 · DATA_SOURCE_UNKNOWN_TYPE
    def test_TC_L104_L202_111_data_source_unknown_type(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
            inject_unknown_data_source={"evil_source": {"key": "value"}},
        )
        with pytest.raises(DataSourceUnknownTypeError):
            evaluator.eval_expression(req)

    # 112 · WHITELIST_VERSION_MISMATCH
    def test_TC_L104_L202_112_whitelist_version_mismatch(
        self,
        sut_offline_admin: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
        make_eval_request,
        make_add_whitelist_rule_request,
    ) -> None:
        # 1. 先编一条
        req = make_compile_request(project_id=mock_project_id, clause_count=1)
        resp = sut_offline_admin.compile_batch(req)
        expr_id = resp.compiled.all_expressions()[0].expr_id

        # 2. 提升 whitelist 版本
        sut_offline_admin.add_whitelist_rule(make_add_whitelist_rule_request())

        # 3. 再 eval (expr 记录的版本已经过时 · 抛 mismatch)
        evaluator2 = DoDEvaluator(sut_offline_admin)
        eval_req = make_eval_request(
            project_id=mock_project_id, expr_id=expr_id, coverage_value=0.9,
        )
        with pytest.raises(WhitelistVersionMismatchError):
            evaluator2.eval_expression(eval_req)

    # 119 · CALLER_UNAUTHORIZED
    def test_TC_L104_L202_119_caller_unauthorized_is_blocked_by_pydantic(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
    ) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            # caller 不在 enum · Pydantic 就拦截 (即 SA-07)
            EvalCommand(
                command_id="cmd-bad-caller",
                project_id=mock_project_id,
                expr_id=ready_expr_id,
                data_sources_snapshot={"coverage": {"line_rate": 0.9}},
                caller="evil_hacker",  # type: ignore[arg-type]
                timeout_ms=500,
            )

    def test_TC_L104_L202_119b_no_project_id_in_eval(
        self, evaluator: DoDEvaluator, ready_expr_id: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id="", expr_id=ready_expr_id, coverage_value=0.9,
        )
        with pytest.raises(NoProjectIdError):
            evaluator.eval_expression(req)

    def test_TC_L104_L202_120_expr_not_found(
        self, evaluator: DoDEvaluator, mock_project_id: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id="expr-does-not-exist",
            coverage_value=0.9,
        )
        from app.quality_loop.dod_compiler.errors import DoDEvalError
        with pytest.raises(DoDEvalError):
            evaluator.eval_expression(req)


class TestNegativeOnlineWhitelistMutation:
    """114 · ONLINE_WHITELIST_MUTATION · 生产态禁 add_whitelist_rule."""

    def test_TC_L104_L202_114_production_add_whitelist_rule_blocked(
        self, sut: DoDExpressionCompiler, make_add_whitelist_rule_request,
    ) -> None:
        # sut 是非 offline_admin_mode
        cmd = make_add_whitelist_rule_request()
        with pytest.raises(OnlineWhitelistMutationError) as exc:
            sut.add_whitelist_rule(cmd)
        assert exc.value.error_code == "E_L204_L202_ONLINE_WHITELIST_MUTATION"


class TestNegativeACLookup:
    """107 · AC_REVERSE_LOOKUP_FAILED."""

    def test_TC_L104_L202_107_ac_reverse_lookup_failed(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(
            project_id=mock_project_id, clause_count=2,
            inject_invalid_ac_indices=[1],
        )
        resp = sut.compile_batch(req)
        # 第 0 条编译成功 · 第 1 条因 ac 不在 matrix 进 errors
        assert resp.compiled_count == 1
        assert any(
            e.error_code == "E_L204_L202_AC_REVERSE_LOOKUP_FAILED"
            for e in resp.errors
        )


class TestNegativeOversize:
    """117 · COMPILE_OVERSIZED."""

    def test_TC_L104_L202_117_oversized_clause_text_rejected_by_schema(
        self, mock_project_id: str,
    ) -> None:
        # schema max_length=2000 · pydantic 直接拦
        from pydantic import ValidationError
        oversized = "x" * 2001
        with pytest.raises(ValidationError):
            DoDClause(
                clause_id="c-oversize",
                clause_text=oversized,
                source_ac_ids=["ac-1"],
                kind=DoDExpressionKind.HARD,
            )

    def test_TC_L104_L202_117b_compile_oversized_batch_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        # 构造一堆 1800 字符的 clause 拼总量 > 500KB
        from app.quality_loop.dod_compiler.errors import CompileOversizedError
        big_text = " and ".join(["line_coverage() >= 0.8"] * 70)  # ~1700 chars
        clauses = [DoDClause(
            clause_id=f"c-big-{i}",
            clause_text=big_text,
            source_ac_ids=[f"ac-{i}"],
            kind=DoDExpressionKind.HARD,
        ) for i in range(300)]  # 300 * 1700 ~ 500KB+

        cmd = CompileBatchCommand(
            command_id="cmd-oversize",
            project_id=mock_project_id,
            blueprint_id="bp-big",
            clauses=clauses,
            ac_matrix={"acs": [{"id": f"ac-{i}"} for i in range(300)]},
        )
        with pytest.raises(CompileOversizedError):
            sut.compile_batch(cmd)
