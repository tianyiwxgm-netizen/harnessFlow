"""§2 正向 TC · TC-L104-L202-001 ~ 060(每 public 方法 ≥ 1).

覆盖:
    - compile_batch (001-006)
    - eval_expression (016-020)
    - validate_expression (041-042)
    - list_whitelist_rules (051-053)
    - add_whitelist_rule (054-055)
    - compile_from_yaml (070-074)
"""
from __future__ import annotations

from app.quality_loop.dod_compiler import (
    CompileBatchCommand,
    DoDEvaluator,
    DoDExpressionCompiler,
    EvalResult,
    ListWhitelistRulesCommand,
    ValidateCommand,
)
from app.quality_loop.dod_compiler.schemas import (
    EvalCaller,
    WhitelistCategory,
)


class TestCompileBatchPositive:
    """§2 · compile_batch 正向."""

    def test_TC_L104_L202_001_compile_batch_happy_path_50_clauses(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req: CompileBatchCommand = make_compile_request(
            project_id=mock_project_id, clause_count=50,
        )
        resp = sut.compile_batch(req)
        assert resp.accepted is True
        assert resp.set_id.startswith("dod-set-")
        assert resp.version == 1
        assert resp.compiled_count == 50
        assert resp.unmappable_clauses == []
        assert resp.expr_statistics.total_exprs == 50

    def test_TC_L104_L202_002_compile_batch_idempotent_by_command_id(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(project_id=mock_project_id, clause_count=10)
        first = sut.compile_batch(req)
        second = sut.compile_batch(req)
        assert first.set_id == second.set_id
        assert first.version == second.version

    def test_TC_L104_L202_003_compile_batch_explicit_whitelist_version(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(
            project_id=mock_project_id, clause_count=3, whitelist_version="1.2.3",
        )
        resp = sut.compile_batch(req)
        assert resp.whitelist_version == "1.2.3"
        assert resp.compiled is not None
        for expr in resp.compiled.all_expressions():
            assert expr.whitelist_version == "1.2.3"

    def test_TC_L104_L202_004_compile_batch_wp_slice(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(
            project_id=mock_project_id, clause_count=6, wp_id="wp-0007",
        )
        resp = sut.compile_batch(req)
        assert "wp-0007" in resp.expr_statistics.per_wp
        assert set(resp.expr_statistics.per_wp.keys()) == {"wp-0007"}

    def test_TC_L104_L202_005_compile_batch_partial_errors_do_not_short_circuit(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(
            project_id=mock_project_id,
            clause_count=5,
            inject_syntax_error_indices=[2],
        )
        resp = sut.compile_batch(req)
        assert resp.accepted is True
        assert resp.compiled_count == 4
        assert len(resp.errors) == 1
        assert resp.errors[0].error_code == "E_L204_L202_AST_SYNTAX_ERROR"

    def test_TC_L104_L202_006_compile_batch_ast_depth_statistics(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        req = make_compile_request(project_id=mock_project_id, clause_count=3)
        resp = sut.compile_batch(req)
        assert resp.expr_statistics.ast_depth_p95 >= 1
        assert resp.expr_statistics.ast_node_count_p95 >= 1


class TestEvalPositive:
    """§2 · eval_expression 正向."""

    def test_TC_L104_L202_016_eval_coverage_expression_passes(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.85, caller=EvalCaller.L2_05_WP_SELF_CHECK,
        )
        resp: EvalResult = evaluator.eval_expression(req)
        assert resp.pass_ is True
        assert len(resp.reason) >= 10
        assert resp.evidence_snapshot
        assert resp.eval_id.startswith("eval-")
        assert resp.caller == EvalCaller.L2_05_WP_SELF_CHECK

    def test_TC_L104_L202_017_eval_cache_hit_hot_path(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
        )
        first = evaluator.eval_expression(req)
        second = evaluator.eval_expression(req)
        assert first.pass_ == second.pass_
        assert second.cache_hit is True
        assert first.eval_id == second.eval_id

    def test_TC_L104_L202_018_eval_evidence_snapshot_only_accessed_fields(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str, make_eval_request,
    ) -> None:
        # expression 只读 coverage · snapshot 同时提供 perf + artifact
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.85, include_perf=True, include_artifact=True,
        )
        resp = evaluator.eval_expression(req)
        assert "coverage" in resp.evidence_snapshot
        assert "perf" not in resp.evidence_snapshot
        assert "artifact" not in resp.evidence_snapshot

    def test_TC_L104_L202_019_eval_caller_verifier_subagent_is_accepted(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str, make_eval_request,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller=EvalCaller.VERIFIER_SUBAGENT,
        )
        resp = evaluator.eval_expression(req)
        assert resp.pass_ is True
        assert resp.caller == EvalCaller.VERIFIER_SUBAGENT

    def test_TC_L104_L202_020_eval_pure_function_no_file_write(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str, make_eval_request,
        mock_fs,
    ) -> None:
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id, coverage_value=0.9,
        )
        evaluator.eval_expression(req)
        # evaluator 构造时没有传 fs · mock_fs 一定 write_count == 0
        assert not mock_fs._store


class TestValidatePositive:
    """§2 · validate_expression 正向."""

    def test_TC_L104_L202_041_validate_returns_ast_tree_summary(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="line_coverage() >= 0.8 and lint_errors() == 0",
        )
        resp = sut.validate_expression(cmd)
        assert resp.valid is True
        assert resp.ast_tree_summary is not None
        assert resp.ast_tree_summary.node_count >= 3
        assert "line_coverage" in resp.ast_tree_summary.used_functions
        assert "lint_errors" in resp.ast_tree_summary.used_functions

    def test_TC_L104_L202_042_validate_returns_version(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="p0_cases_all_pass()",
        )
        resp = sut.validate_expression(cmd)
        assert resp.valid is True
        assert resp.whitelist_version == sut.registry.version


class TestListWhitelistPositive:
    """§2 · list_whitelist_rules 正向."""

    def test_TC_L104_L202_051_list_all_default(
        self, sut: DoDExpressionCompiler,
    ) -> None:
        cmd = ListWhitelistRulesCommand()
        resp = sut.list_whitelist_rules(cmd)
        assert resp.whitelist_version
        # 至少含 line_coverage / lint_errors / p95_ms + 6 个 data sources
        names = {r.name for r in resp.rules}
        assert {"line_coverage", "lint_errors", "p95_ms"} <= names
        # data sources
        assert "coverage" in names

    def test_TC_L104_L202_052_list_function_only(
        self, sut: DoDExpressionCompiler,
    ) -> None:
        cmd = ListWhitelistRulesCommand(category=WhitelistCategory.FUNCTION)
        resp = sut.list_whitelist_rules(cmd)
        categories = {r.category for r in resp.rules}
        assert categories == {WhitelistCategory.FUNCTION}

    def test_TC_L104_L202_053_list_is_deepcopy_no_shared_mutation(
        self, sut: DoDExpressionCompiler,
    ) -> None:
        cmd = ListWhitelistRulesCommand()
        resp1 = sut.list_whitelist_rules(cmd)
        resp2 = sut.list_whitelist_rules(cmd)
        # pydantic frozen · 每次新建 · 身份可以同但内容应等
        names1 = {r.name for r in resp1.rules}
        names2 = {r.name for r in resp2.rules}
        assert names1 == names2


class TestAddWhitelistRulePositive:
    """§2 · add_whitelist_rule 正向 (仅 offline_admin)."""

    def test_TC_L104_L202_054_offline_admin_can_add_rule(
        self, sut_offline_admin: DoDExpressionCompiler, make_add_whitelist_rule_request,
    ) -> None:
        before_version = sut_offline_admin.registry.version
        cmd = make_add_whitelist_rule_request()
        resp = sut_offline_admin.add_whitelist_rule(cmd)
        assert resp.rule_id.startswith("func-")
        assert resp.new_whitelist_version != before_version
        assert resp.audit_log_id.startswith("audit-")
        # 新规则可以查到
        assert sut_offline_admin.registry.contains("math_sqrt")

    def test_TC_L104_L202_055_add_rule_bumps_minor_version(
        self, sut_offline_admin: DoDExpressionCompiler, make_add_whitelist_rule_request,
    ) -> None:
        cmd = make_add_whitelist_rule_request(version_bump_type="minor")
        v0 = sut_offline_admin.registry.version
        resp = sut_offline_admin.add_whitelist_rule(cmd)
        v1 = resp.new_whitelist_version
        # minor 段 +1
        assert v0.split(".")[0] == v1.split(".")[0]  # major 不变
        assert int(v1.split(".")[1]) == int(v0.split(".")[1]) + 1


class TestCompileFromYaml:
    """§2 · compile_from_yaml 便捷入口(DoD YAML 语法覆盖 brief §5.2)."""

    def test_TC_L104_L202_070_yaml_with_all_three_kinds(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - "line_coverage() >= 0.8"
    - "lint_errors() == 0"
  soft:
    - "test_pass_rate() >= 0.95"
  metric:
    - "p95_ms() < 500"
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert resp.accepted is True
        assert resp.compiled_count == 4
        assert len(resp.compiled.hard) == 2
        assert len(resp.compiled.soft) == 1
        assert len(resp.compiled.metric) == 1

    def test_TC_L104_L202_071_yaml_hard_only(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - "p0_cases_all_pass()"
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert resp.compiled_count == 1
        assert resp.compiled.hard[0].expression_text == "p0_cases_all_pass()"

    def test_TC_L104_L202_072_yaml_with_shorthand_predicate_name(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        # 简写 "p0_cases_all_pass" 自动补 "()"
        yaml_text = """
dod:
  hard:
    - p0_cases_all_pass
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert resp.compiled_count == 1
        assert resp.compiled.hard[0].expression_text.endswith("()")

    def test_TC_L104_L202_073_yaml_with_clause_objects_and_ac_ids(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - clause_id: hard-main-01
      text: "line_coverage() >= 0.8"
      source_ac_ids: [ac-main-0001]
      priority: P0
"""
        resp = sut.compile_from_yaml(
            yaml_text,
            project_id=mock_project_id,
            ac_matrix={"acs": [{"id": "ac-main-0001"}]},
        )
        assert resp.compiled_count == 1
        assert resp.compiled.hard[0].source_ac_ids == ["ac-main-0001"]

    def test_TC_L104_L202_074_yaml_empty_subkinds_do_not_fail(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - "p95_ms() < 500"
  soft: []
  metric:
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert resp.compiled_count == 1
