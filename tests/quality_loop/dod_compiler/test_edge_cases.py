"""§9 边界 / edge case · TC-L104-L202-A01 ~ A09.

覆盖:表达式注入 / 深层嵌套 / 无效 DSL / 空 clause / 并发 / 冷启动 / 超大表达式 /
      whitelist bump cache invalidate.
"""
from __future__ import annotations

import threading

import pytest
from pydantic import ValidationError

from app.quality_loop.dod_compiler import (
    DoDEvaluator,
    DoDExpressionCompiler,
    ValidateCommand,
)


class TestEdgeCases:

    def test_TC_L104_L202_A01_injection_via_multi_statement_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """表达式注入 · 分号多语句 / __import__ 拒绝."""
        cmd = ValidateCommand(
            project_id=mock_project_id,
            expression_text="line_coverage() >= 0.8; __import__('os').system('ls')",
        )
        rep = sut.validate_expression(cmd)
        assert rep.valid is False
        assert rep.violations

    def test_TC_L104_L202_A02_deep_nesting_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        """40 层 not 嵌套 → 深度超限."""
        expr = ("not " * 40) + "p0_cases_all_pass()"
        rep = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id, expression_text=expr,
        ))
        assert rep.valid is False

    def test_TC_L104_L202_A04_invalid_dsl_garbage(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        rep = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id,
            expression_text="???!!! foo bar",
        ))
        assert rep.valid is False

    def test_TC_L104_L202_A05_empty_clause_text_rejected_by_schema(self) -> None:
        # min_length=1 校验
        with pytest.raises(ValidationError):
            ValidateCommand(project_id="pid", expression_text="")

    def test_TC_L104_L202_A05b_whitespace_only_rejected(
        self, sut: DoDExpressionCompiler, mock_project_id: str,
    ) -> None:
        rep = sut.validate_expression(ValidateCommand(
            project_id=mock_project_id, expression_text="   ",
        ))
        assert rep.valid is False

    def test_TC_L104_L202_A06_concurrent_compile_idempotent_no_race(
        self, sut: DoDExpressionCompiler, mock_project_id: str, make_compile_request,
    ) -> None:
        """10 线程同 command_id · 幂等返回相同 set_id."""
        req = make_compile_request(
            project_id=mock_project_id,
            clause_count=3,
            command_id="cmd-race-001",
        )
        results: list[str] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                r = sut.compile_batch(req)
                results.append(r.set_id)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == []
        assert len(set(results)) == 1, f"不同 set_id: {set(results)}"

    def test_TC_L104_L202_A07_cold_start_compile_under_1s(
        self, fresh_registry, mock_project_id: str, make_compile_request,
    ) -> None:
        """冷启动:构造新 compiler 并编译 1 条 · < 1s."""
        import time
        t0 = time.perf_counter()
        cold_sut = DoDExpressionCompiler(whitelist_registry=fresh_registry)
        req = make_compile_request(project_id=mock_project_id, clause_count=1)
        cold_sut.compile_batch(req)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0

    def test_TC_L104_L202_A08_oversized_expression_rejected_by_schema(
        self, mock_project_id: str,
    ) -> None:
        """单条 clause_text > 2500 · Pydantic 拦截."""
        with pytest.raises(ValidationError):
            ValidateCommand(project_id=mock_project_id, expression_text="x" * 3000)

    def test_TC_L104_L202_A09_add_whitelist_bumps_version_old_expr_invalidates(
        self,
        sut_offline_admin: DoDExpressionCompiler,
        mock_project_id: str,
        make_compile_request,
        make_eval_request,
        make_add_whitelist_rule_request,
    ) -> None:
        """§3.5.3 · add_whitelist_rule bump 版本后 · 老 expr eval 失效."""
        req = make_compile_request(project_id=mock_project_id, clause_count=1)
        resp = sut_offline_admin.compile_batch(req)
        old_expr_id = resp.compiled.all_expressions()[0].expr_id

        # bump
        sut_offline_admin.add_whitelist_rule(make_add_whitelist_rule_request())

        # 新 evaluator 发现 expr.whitelist_version != current
        evaluator = DoDEvaluator(sut_offline_admin)
        eval_req = make_eval_request(
            project_id=mock_project_id, expr_id=old_expr_id, coverage_value=0.9,
        )
        from app.quality_loop.dod_compiler.errors import WhitelistVersionMismatchError
        with pytest.raises(WhitelistVersionMismatchError):
            evaluator.eval_expression(eval_req)


class TestSafetyGuardUnit:
    """§6.1 safety_guard 专项单元."""

    @pytest.mark.parametrize("text,expected_label", [
        ("eval('1+1')", "builtin-call"),
        ("exec('pass')", "builtin-call"),
        ("compile('x', 'f', 'eval')", "builtin-call"),
        ("__import__('os')", "builtin-call"),
        ("open('x')", "builtin-call"),
        ("globals()", "builtin-call"),
        ("getattr(x, 'y')", "builtin-call"),
        ("import os", "import-keyword"),
        ("from os import system", "from-import"),
        ("__class__", "dunder-name"),
        ("a ; b", "statement-separator"),
        ("x := 5", "walrus-operator"),
        ("lambda x: 1", "lambda-keyword"),
        ("yield 1", "yield-keyword"),
        ("await x", "async-keyword"),
    ])
    def test_scan_danger_tokens_detects_all(
        self, text: str, expected_label: str,
    ) -> None:
        from app.quality_loop.dod_compiler.safety_guard import scan_danger_tokens
        hits = scan_danger_tokens(text)
        assert expected_label in hits

    def test_scan_danger_tokens_clean_passes(self) -> None:
        from app.quality_loop.dod_compiler.safety_guard import scan_danger_tokens
        assert scan_danger_tokens("line_coverage() >= 0.8") == []
        assert scan_danger_tokens("a and b or not c") == []

    def test_assert_offline_admin_raises_in_production(self) -> None:
        from app.quality_loop.dod_compiler.errors import OnlineWhitelistMutationError
        from app.quality_loop.dod_compiler.safety_guard import assert_offline_admin
        with pytest.raises(OnlineWhitelistMutationError):
            assert_offline_admin(False)

    def test_assert_offline_admin_ok_in_offline(self) -> None:
        from app.quality_loop.dod_compiler.safety_guard import assert_offline_admin
        # 不抛
        assert_offline_admin(True)

    def test_assert_registry_integrity_detects_tamper(self) -> None:
        from app.quality_loop.dod_compiler.errors import WhitelistTamperingError
        from app.quality_loop.dod_compiler.safety_guard import assert_registry_integrity
        with pytest.raises(WhitelistTamperingError):
            assert_registry_integrity("abc123", "def456")

    def test_assert_registry_integrity_same_hash_passes(self) -> None:
        from app.quality_loop.dod_compiler.safety_guard import assert_registry_integrity
        assert_registry_integrity("abc", "abc")

    def test_assert_registry_integrity_none_is_noop(self) -> None:
        from app.quality_loop.dod_compiler.safety_guard import assert_registry_integrity
        assert_registry_integrity(None, None)
        assert_registry_integrity(None, "abc")


class TestYamlParserEdge:
    """yaml_parser edge cases."""

    def test_top_level_must_have_dod_key(self) -> None:
        from app.quality_loop.dod_compiler.errors import DoDCompileError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        with pytest.raises(DoDCompileError):
            parse_dod_yaml("foo: bar")

    def test_dod_value_must_be_mapping(self) -> None:
        from app.quality_loop.dod_compiler.errors import DoDCompileError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        with pytest.raises(DoDCompileError):
            parse_dod_yaml("dod: just-a-string")

    def test_unknown_kind_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import DoDCompileError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        yaml_text = """
dod:
  random_kind:
    - foo
"""
        with pytest.raises(DoDCompileError):
            parse_dod_yaml(yaml_text)

    def test_empty_yaml_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import ASTSyntaxError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        with pytest.raises(ASTSyntaxError):
            parse_dod_yaml("")

    def test_yaml_syntax_error_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import ASTSyntaxError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        with pytest.raises(ASTSyntaxError):
            parse_dod_yaml("dod:\n  hard:\n    - [unclosed")

    def test_kind_list_required(self) -> None:
        from app.quality_loop.dod_compiler.errors import DoDCompileError
        from app.quality_loop.dod_compiler.yaml_parser import parse_dod_yaml
        with pytest.raises(DoDCompileError):
            parse_dod_yaml("dod:\n  hard: not-a-list")
