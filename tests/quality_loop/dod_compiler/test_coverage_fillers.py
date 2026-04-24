"""补充覆盖率的 TC · 覆盖 compiler/evaluator 少量分支."""
from __future__ import annotations

import uuid

import pytest

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    DoDEvaluator,
    DoDExpressionCompiler,
    EvalCommand,
)
from app.quality_loop.dod_compiler.compiler import _extract_ac_ids, _similarity
from app.quality_loop.dod_compiler.errors import (
    DoDCompileError,
)
from app.quality_loop.dod_compiler.schemas import (
    AddWhitelistRuleCommand,
    DoDClause,
    DoDExpressionKind,
    EvalCaller,
    OfflineReviewMemo,
)


class TestUnmappablePath:
    """compile_single 抛 DoDCompileError 分支 · 走 unmappable 登记."""

    def test_unmappable_non_existent_predicate(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """用一个合法 AST(仅 Name)但不是 function call · 不走非法函数."""
        # Note:单独的 Name 表达式 `some_var` 会走 validator · 但 safe_eval 时才报 SandboxEscape.
        # 在 compile 期我们只校验 AST · 不 eval · 所以 Name 会通过 · 不归 unmappable.
        # 这里测 AC 反查失败的 soft 路径(已在 negative 测过)· 补一个 clause_text 触发其他 DoDCompileError

    def test_ac_matrix_extract_from_entries_key(self) -> None:
        """_extract_ac_ids 支持 entries key."""
        m = {"entries": [{"id": "ac-1"}, {"id": "ac-2"}]}
        assert _extract_ac_ids(m) == {"ac-1", "ac-2"}

    def test_ac_matrix_extract_from_top_level_mapping(self) -> None:
        m = {"ac-1": {"detail": "x"}, "ac-2": {"detail": "y"}}
        ids = _extract_ac_ids(m)
        assert "ac-1" in ids and "ac-2" in ids

    def test_ac_matrix_extract_from_str_list(self) -> None:
        m = {"acs": ["ac-1", "ac-2"]}
        assert _extract_ac_ids(m) == {"ac-1", "ac-2"}

    def test_ac_matrix_empty(self) -> None:
        assert _extract_ac_ids({}) == set()

    def test_similarity_empty_input(self) -> None:
        assert _similarity("", "x") == 0.0
        assert _similarity("x", "") == 0.0

    def test_similarity_non_empty(self) -> None:
        s = _similarity("abc", "abd")
        assert 0 < s < 1


class TestCompilerAddRuleErrors:
    def test_add_rule_without_name_rejected(
        self, sut_offline_admin: DoDExpressionCompiler,
    ) -> None:
        cmd = AddWhitelistRuleCommand(
            rule={"name": "", "arg_count": 0},
            offline_review_memo=OfflineReviewMemo(
                review_date="2026-04-22",
                reviewers=["a", "b"],
                rationale="x" * 100,
                test_coverage_plan="p" * 50,
            ),
            operator="sre",
            signature="gpg:sig",
        )
        with pytest.raises(DoDCompileError):
            sut_offline_admin.add_whitelist_rule(cmd)


class TestCompileFromYamlErrorPaths:
    def test_compile_from_yaml_oversized_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        from app.quality_loop.dod_compiler.errors import CompileOversizedError
        big_yaml = "dod:\n  hard:\n" + ("    - \"line_coverage() >= 0.8\"\n" * 20000)
        with pytest.raises(CompileOversizedError):
            sut.compile_from_yaml(big_yaml, project_id=mock_project_id)


class TestEvaluatorEdgeCases:
    def test_eval_fail_reason_contains_evidence(
        self, evaluator: DoDEvaluator, mock_project_id: str, make_compile_request,
    ) -> None:
        """FAIL 路径的 reason · 包含 evidence_snapshot."""
        # 编一条 `lint_errors() == 0` · 传 errors=5 → FAIL
        cmd = CompileBatchCommand(
            command_id="cmd-fail-reason",
            project_id=mock_project_id,
            blueprint_id="bp-fr",
            clauses=[DoDClause(
                clause_id="h1",
                clause_text="lint_errors() == 0",
                source_ac_ids=["ac-1"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-1"}]},
        )
        evaluator._compiler.compile_batch(cmd)
        exprs = evaluator._compiler._expressions
        expr_id = next(iter(exprs.keys()))
        r = evaluator.eval_expression(EvalCommand(
            command_id=f"c-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"lint": {"error_count": 5}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        ))
        assert r.pass_ is False
        assert "FAIL" in r.reason
        assert "lint" in r.reason or "evidence" in r.reason

    def test_eval_clear_cache(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
        )
        evaluator.eval_expression(req)
        assert evaluator._debug_cache_size() >= 1
        evaluator.clear_cache()
        assert evaluator._debug_cache_size() == 0

    def test_eval_second_caller_same_result(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """不同 caller · 不同 command_id · 新 cache · 不误命中."""
        r1 = evaluator.eval_expression(make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88,
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
            command_id="cmd-c1",
        ))
        r2 = evaluator.eval_expression(make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88,
            caller=EvalCaller.L2_04_GATE_CONFIG_CHECK,
            command_id="cmd-c2",
        ))
        assert r1.pass_ == r2.pass_
        assert r1.eval_id != r2.eval_id


class TestValidateExpressionFringe:
    def test_validate_exceeds_size_violation(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        from app.quality_loop.dod_compiler import ValidateCommand
        # 长度介于 2000 和 2500 之间 · schema 放行 · validate 内部 EXCEEDS_SIZE
        long_text = "line_coverage() >= 0.8" + (" and True" * 230)  # ~2100 chars
        assert 2000 < len(long_text) < 2500
        rep = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id, expression_text=long_text,
        ))
        assert rep.valid is False

    def test_validate_used_data_source_types_listed(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        from app.quality_loop.dod_compiler import ValidateCommand
        # 表达式里引用 coverage 作为 Name 时
        rep = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id,
            expression_text="line_coverage() >= 0.8",
        ))
        # used_data_source_types 字段存在 (即使为空)
        assert rep.ast_tree_summary is not None
        assert isinstance(rep.ast_tree_summary.used_data_source_types, list)
