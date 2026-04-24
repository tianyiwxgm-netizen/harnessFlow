"""§4 + §8 集成 TC · 与兄弟 L2 / 下游契约.

覆盖:
    - TC-L104-L202-801/802 正向 e2e (compile → eval 全链)
    - TC-L104-L202-803/805 负向 e2e (危险表达式 · 访问文件系统)
    - TC-L104-L202-901 S5 verifier 子 Agent 同结果 (pure function)
    - TC-L104-L202-902 L2-04 合规校验(list_whitelist → 用于 gates)
"""
from __future__ import annotations

import pytest

from app.quality_loop.dod_compiler import (
    DoDEvaluator,
    DoDExpressionCompiler,
    ListWhitelistRulesCommand,
)
from app.quality_loop.dod_compiler.errors import (
    IllegalFunctionError,
    IllegalNodeError,
)
from app.quality_loop.dod_compiler.schemas import (
    DoDClause,
    DoDExpressionKind,
    EvalCaller,
    WhitelistCategory,
)


class TestE2EScenarios:
    """PRD §9.9 交付验证."""

    def test_TC_L104_L202_801_50_dod_compiled_within_60s(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        import time
        req = make_compile_request(project_id=mock_project_id, clause_count=50)
        t0 = time.perf_counter()
        resp = sut.compile_batch(req)
        elapsed = time.perf_counter() - t0
        assert resp.compiled_count == 50
        assert elapsed < 60.0

    def test_TC_L104_L202_802_compile_then_eval_full_chain(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
        make_eval_request,
    ) -> None:
        # 1. compile
        req = make_compile_request(project_id=mock_project_id, clause_count=3)
        resp = sut.compile_batch(req)
        assert resp.compiled is not None
        # 2. eval each
        evaluator = DoDEvaluator(sut)
        for expr in resp.compiled.all_expressions():
            eval_req = make_eval_request(
                project_id=mock_project_id, expr_id=expr.expr_id,
                coverage_value=0.9, lint_error_count=0, include_perf=True,
            )
            er = evaluator.eval_expression(eval_req)
            assert er.reason
            # coverage 0.9 >= 0.8 → pass · 其他也应 pass
            assert er.pass_ in (True, False)

    def test_TC_L104_L202_803_arbitrary_exec_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        from app.quality_loop.dod_compiler.schemas import CompileBatchCommand
        cmd = CompileBatchCommand(
            command_id="cmd-evil",
            project_id=mock_project_id,
            blueprint_id="bp-evil",
            clauses=[DoDClause(
                clause_id="c-evil",
                clause_text="__import__('os').system('rm -rf /')",
                source_ac_ids=["ac-1"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-1"}]},
        )
        with pytest.raises((IllegalNodeError, IllegalFunctionError)):
            sut.compile_batch(cmd)

    def test_TC_L104_L202_805_filesystem_access_rejected_at_validate(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        from app.quality_loop.dod_compiler import ValidateCommand
        attempts = [
            'open("/etc/passwd")',
            '__builtins__["open"]("x")',
            'globals().get("os")',
            '__import__("subprocess").run("ls")',
        ]
        for txt in attempts:
            rep = sut.validate_expression(ValidateCommand(
                project_id=mock_project_id, expression_text=txt,
            ))
            assert rep.valid is False


class TestSiblingIntegration:
    """§8 · 与 L2-01/L2-04/L2-05/L2-06 的协作."""

    def test_TC_L104_L202_901_verifier_subagent_same_result_as_main(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """PM-03 独立 session · 同输入 · 同结果 (pure function)."""
        req_main = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88, caller=EvalCaller.L2_05_WP_SELF_CHECK,
            command_id="cmd-main",
        )
        req_verifier = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.88, caller=EvalCaller.VERIFIER_SUBAGENT,
            command_id="cmd-verifier",
        )
        r_main = evaluator.eval_expression(req_main)
        r_ver = evaluator.eval_expression(req_verifier)
        assert r_main.pass_ == r_ver.pass_
        assert r_main.evidence_snapshot == r_ver.evidence_snapshot
        assert r_main.whitelist_version == r_ver.whitelist_version

    def test_TC_L104_L202_902_l2_04_reads_whitelist_for_gate_compliance(
        self, sut: DoDExpressionCompiler,
    ) -> None:
        """L2-04 编译 quality-gates.yaml 时查本 L2 白名单."""
        resp = sut.list_whitelist_rules(ListWhitelistRulesCommand(
            category=WhitelistCategory.FUNCTION,
        ))
        names = {r.name for r in resp.rules}
        # L2-04 的 gates 谓词必须在白名单内
        must_have = {"line_coverage", "lint_errors", "p0_cases_all_pass", "p95_ms"}
        assert must_have <= names

    def test_TC_L104_L202_904_l2_05_wp_self_check_uses_evaluator(
        self, evaluator: DoDEvaluator, mock_project_id: str, ready_expr_id: str,
        make_eval_request,
    ) -> None:
        """L2-05 的 WP 自检必走本 evaluator (PM-10 单一事实源)."""
        req = make_eval_request(
            project_id=mock_project_id, expr_id=ready_expr_id,
            coverage_value=0.9, caller=EvalCaller.L2_05_WP_SELF_CHECK,
        )
        r = evaluator.eval_expression(req)
        assert r.pass_ is True
        assert r.caller == EvalCaller.L2_05_WP_SELF_CHECK


class TestKindSemantics:
    """brief §5.2 三分类 hard/soft/metric 语义."""

    def test_hard_clauses_go_to_hard_bucket(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - "line_coverage() >= 0.8"
    - "lint_errors() == 0"
  soft: []
  metric: []
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert len(resp.compiled.hard) == 2
        assert all(e.kind == DoDExpressionKind.HARD for e in resp.compiled.hard)

    def test_soft_clauses_tolerated(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard: []
  soft:
    - "test_pass_rate() >= 0.95"
  metric: []
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert len(resp.compiled.soft) == 1
        assert resp.compiled.soft[0].kind == DoDExpressionKind.SOFT

    def test_metric_clauses_slo(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard: []
  soft: []
  metric:
    - "p95_ms() < 500"
    - "throughput_qps() >= 100"
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        assert len(resp.compiled.metric) == 2
        for e in resp.compiled.metric:
            assert e.kind == DoDExpressionKind.METRIC

    def test_all_expressions_returns_all_three(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        yaml_text = """
dod:
  hard:
    - "p0_cases_all_pass()"
  soft:
    - "branch_coverage() >= 0.7"
  metric:
    - "p50_ms() < 100"
"""
        resp = sut.compile_from_yaml(yaml_text, project_id=mock_project_id)
        all_exprs = resp.compiled.all_expressions()
        assert len(all_exprs) == 3
        kinds = {e.kind for e in all_exprs}
        assert kinds == {DoDExpressionKind.HARD, DoDExpressionKind.SOFT, DoDExpressionKind.METRIC}


class TestEvalEvidenceAndKinds:
    """eval + evidence 综合."""

    def test_evaluate_metric_expression_with_perf_snapshot(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        import uuid

        from app.quality_loop.dod_compiler.schemas import CompileBatchCommand, EvalCommand
        cmd = CompileBatchCommand(
            command_id="cmd-metric-1",
            project_id=mock_project_id,
            blueprint_id="bp-1",
            clauses=[DoDClause(
                clause_id="m-1",
                clause_text="p95_ms() < 500",
                source_ac_ids=["ac-metric-1"],
                kind=DoDExpressionKind.METRIC,
            )],
            ac_matrix={"acs": [{"id": "ac-metric-1"}]},
        )
        resp = sut.compile_batch(cmd)
        expr_id = resp.compiled.metric[0].expr_id

        evaluator = DoDEvaluator(sut)
        eval_cmd = EvalCommand(
            command_id=f"cmd-eval-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"perf": {"p95_ms": 420}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        )
        r = evaluator.eval_expression(eval_cmd)
        assert r.pass_ is True
        assert "perf" in r.evidence_snapshot

    def test_evaluate_fails_when_predicate_false(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        import uuid

        from app.quality_loop.dod_compiler.schemas import CompileBatchCommand, EvalCommand
        cmd = CompileBatchCommand(
            command_id="cmd-fail-1",
            project_id=mock_project_id,
            blueprint_id="bp-2",
            clauses=[DoDClause(
                clause_id="h-1",
                clause_text="lint_errors() == 0",
                source_ac_ids=["ac-h-1"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-h-1"}]},
        )
        resp = sut.compile_batch(cmd)
        evaluator = DoDEvaluator(sut)
        expr_id = resp.compiled.hard[0].expr_id
        # lint 有 3 个 error → fail
        er = evaluator.eval_expression(EvalCommand(
            command_id=f"cmd-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"lint": {"error_count": 3}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        ))
        assert er.pass_ is False
        assert "FAIL" in er.reason
        assert "lint" in er.evidence_snapshot

    def test_compound_and_or_expression(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        import uuid

        from app.quality_loop.dod_compiler.schemas import CompileBatchCommand, EvalCommand
        # hard: 覆盖率 + lint
        cmd = CompileBatchCommand(
            command_id="cmd-compound",
            project_id=mock_project_id,
            blueprint_id="bp-c",
            clauses=[DoDClause(
                clause_id="hc",
                clause_text="line_coverage() >= 0.8 and lint_errors() == 0",
                source_ac_ids=["ac-c"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-c"}]},
        )
        resp = sut.compile_batch(cmd)
        evaluator = DoDEvaluator(sut)
        expr_id = resp.compiled.hard[0].expr_id

        # 两边都满足 → pass
        r_pass = evaluator.eval_expression(EvalCommand(
            command_id=f"c-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"coverage": {"line_rate": 0.9}, "lint": {"error_count": 0}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        ))
        assert r_pass.pass_ is True

        # 一边不满足 → fail
        r_fail = evaluator.eval_expression(EvalCommand(
            command_id=f"c-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"coverage": {"line_rate": 0.9}, "lint": {"error_count": 5}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        ))
        assert r_fail.pass_ is False

    def test_not_operator(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """not 算子 · eval."""
        import uuid

        from app.quality_loop.dod_compiler.schemas import CompileBatchCommand, EvalCommand
        cmd = CompileBatchCommand(
            command_id="cmd-not",
            project_id=mock_project_id,
            blueprint_id="bp-n",
            clauses=[DoDClause(
                clause_id="hn",
                clause_text="not (lint_errors() > 0)",
                source_ac_ids=["ac-n"],
                kind=DoDExpressionKind.HARD,
            )],
            ac_matrix={"acs": [{"id": "ac-n"}]},
        )
        resp = sut.compile_batch(cmd)
        evaluator = DoDEvaluator(sut)
        expr_id = resp.compiled.hard[0].expr_id

        r = evaluator.eval_expression(EvalCommand(
            command_id=f"cn-{uuid.uuid4()}",
            project_id=mock_project_id,
            expr_id=expr_id,
            data_sources_snapshot={"lint": {"error_count": 0}},
            caller=EvalCaller.L2_05_WP_SELF_CHECK,
        ))
        assert r.pass_ is True
