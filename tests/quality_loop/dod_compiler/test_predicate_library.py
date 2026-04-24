"""predicate 库单元测试 · 覆盖所有白名单 predicate.

目标:覆盖 predicate_eval._make_library 里所有函数 · 测 safe_eval 路径各分支.
"""
from __future__ import annotations

import ast

import pytest

from app.quality_loop.dod_compiler.ast_nodes import SafeExprValidator
from app.quality_loop.dod_compiler.errors import (
    CachePoisonError,
    DataSourceUnknownTypeError,
    IllegalNodeError,
    SandboxEscapeDetectedError,
)
from app.quality_loop.dod_compiler.predicate_eval import (
    DEFAULT_WHITELIST_FUNCS,
    WHITELISTED_DATA_SOURCE_KEYS,
    WhitelistRegistry,
    safe_eval,
)


def _parse(text: str) -> ast.Expression:
    return ast.parse(text, mode="eval")


class TestPredicateLibrary:

    def test_line_coverage_read_rate(self) -> None:
        v, ev = safe_eval(_parse("line_coverage() >= 0.8"),
                          {"coverage": {"line_rate": 0.85}})
        assert v is True
        assert ev["coverage"]["line_rate"] == 0.85

    def test_line_coverage_fallback_key(self) -> None:
        # 也支持 coverage.line_coverage 字段名
        v, ev = safe_eval(_parse("line_coverage() >= 0.8"),
                          {"coverage": {"line_coverage": 0.9}})
        assert v is True

    def test_line_coverage_missing_returns_zero(self) -> None:
        v, ev = safe_eval(_parse("line_coverage() >= 0.8"),
                          {"coverage": {}})
        assert v is False

    def test_branch_coverage(self) -> None:
        v, ev = safe_eval(_parse("branch_coverage() >= 0.7"),
                          {"coverage": {"branch_rate": 0.75}})
        assert v is True
        v2, _ = safe_eval(_parse("branch_coverage() >= 0.7"),
                          {"coverage": {"branch_coverage": 0.8}})
        assert v2 is True

    def test_ac_coverage(self) -> None:
        v, ev = safe_eval(_parse("ac_coverage() >= 0.9"),
                          {"coverage": {"ac_coverage": 0.95}})
        assert v is True
        assert ev["coverage"]["ac_coverage"] == 0.95

    def test_test_counts_and_rate(self) -> None:
        v, ev = safe_eval(
            _parse("test_pass_count() > 0 and test_fail_count() == 0"),
            {"test_result": {"pass_count": 10, "fail_count": 0}},
        )
        assert v is True
        v2, ev2 = safe_eval(
            _parse("test_pass_rate() >= 0.95"),
            {"test_result": {"pass_count": 95, "fail_count": 5}},
        )
        assert v2 is True
        assert ev2["test_result"]["pass_rate"] == 0.95

    def test_test_skip_count(self) -> None:
        v, ev = safe_eval(_parse("test_skip_count() == 0"),
                          {"test_result": {"skip_count": 0}})
        assert v is True

    def test_test_pass_rate_empty_defaults_to_1(self) -> None:
        v, ev = safe_eval(_parse("test_pass_rate() >= 0.99"),
                          {"test_result": {}})
        assert v is True  # 无数据 → 保守返回 1.0

    def test_p0_cases_all_pass(self) -> None:
        v, _ = safe_eval(_parse("p0_cases_all_pass()"),
                        {"test_result": {"p0_all_pass": True}})
        assert v is True
        v2, _ = safe_eval(_parse("p0_cases_all_pass()"),
                         {"test_result": {"p0_all_pass": False}})
        assert v2 is False

    def test_lint_errors_and_warnings(self) -> None:
        v, ev = safe_eval(_parse("lint_errors() == 0 and lint_warnings() < 5"),
                          {"lint": {"error_count": 0, "warning_count": 3}})
        assert v is True
        # 兼容 ruff_errors 字段
        v2, _ = safe_eval(_parse("lint_errors() == 0"),
                          {"lint": {"ruff_errors": 0}})
        assert v2 is True

    def test_security_functions(self) -> None:
        v, ev = safe_eval(
            _parse("high_severity_count() == 0 and medium_severity_count() <= 2"),
            {"security_scan": {"high_severity_count": 0, "medium_severity_count": 1}},
        )
        assert v is True
        v2, _ = safe_eval(
            _parse("security_resolved_rate() >= 0.95"),
            {"security_scan": {"resolved_rate": 0.96}},
        )
        assert v2 is True

    def test_perf_functions(self) -> None:
        v, ev = safe_eval(
            _parse("p50_ms() < 200 and p95_ms() < 500 and throughput_qps() >= 100"),
            {"perf": {"p50_ms": 120, "p95_ms": 400, "throughput_qps": 150}},
        )
        assert v is True

    def test_artifact_file_count(self) -> None:
        v, ev = safe_eval(
            _parse("artifact_file_count() >= 1"),
            {"artifact": {"files": ["a.py", "b.py", "c.py"]}},
        )
        assert v is True
        assert ev["artifact"]["file_count"] == 3

    def test_has_file_match(self) -> None:
        v, _ = safe_eval(
            _parse('has_file("dist/app.js")'),
            {"artifact": {"files": ["dist/app.js", "dist/vendor.js"]}},
        )
        assert v is True

        v2, _ = safe_eval(
            _parse('has_file("unknown.js")'),
            {"artifact": {"files": []}},
        )
        assert v2 is False

    def test_length_helper(self) -> None:
        v, _ = safe_eval(_parse('length("abcdef") == 6'), {})
        assert v is True

    def test_length_on_unhashable_returns_zero(self) -> None:
        v, _ = safe_eval(_parse('length(42) == 0'), {})
        assert v is True


class TestSafeEvalSafetyPaths:

    def test_data_source_unknown_rejected(self) -> None:
        with pytest.raises(DataSourceUnknownTypeError):
            safe_eval(_parse("line_coverage() >= 0.8"),
                      {"foreign_source": {"x": 1}})

    def test_non_expression_rejected(self) -> None:
        # 手造一个 ast.Module(非 Expression) 传入
        tree = ast.parse("1+1", mode="exec")
        with pytest.raises(IllegalNodeError):
            safe_eval(tree, {})  # type: ignore[arg-type]

    def test_runtime_revalidate_rejects_tampered_ast(self) -> None:
        """手工构造一个含 ast.Attribute 的 tree · 运行期 re-validate 应拒."""
        # 先合法 parse
        tree = ast.parse("line_coverage()", mode="eval")
        # 恶意替换 body 为 Attribute 访问(模拟 cache poison)
        # tree.body = ast.Attribute(value=ast.Name(id="os", ctx=ast.Load()),
        #                             attr="system", ctx=ast.Load())
        tree.body = ast.Attribute(
            value=ast.Name(id="os", ctx=ast.Load()),
            attr="system",
            ctx=ast.Load(),
        )
        ast.fix_missing_locations(tree)
        with pytest.raises(CachePoisonError):
            safe_eval(tree, {})

    def test_unknown_name_escapes_as_sandbox_error(self) -> None:
        """validator 允许 Name · 但 globals 没定义 · eval NameError → SandboxEscape."""
        tree = ast.parse("something_undefined", mode="eval")
        with pytest.raises(SandboxEscapeDetectedError):
            safe_eval(tree, {})


class TestWhitelistRegistry:

    def test_default_version(self) -> None:
        r = WhitelistRegistry()
        assert r.version == "1.0.3"

    def test_contains(self) -> None:
        r = WhitelistRegistry()
        assert r.contains("line_coverage")
        assert not r.contains("not_a_predicate")

    def test_allowed_funcs_is_copy(self) -> None:
        r = WhitelistRegistry()
        funcs = r.allowed_funcs()
        funcs["injected"] = 99
        assert not r.contains("injected")

    def test_list_rules_sorted(self) -> None:
        r = WhitelistRegistry()
        rules = r.list_rules()
        names = [n for n, _ in rules]
        assert names == sorted(names)

    def test_add_rule_bumps_version(self) -> None:
        r = WhitelistRegistry()
        v0 = r.version
        new_v = r.add_rule("my_new_predicate", 1, bump="patch")
        assert new_v != v0
        assert r.contains("my_new_predicate")

    def test_add_rule_duplicate_raises(self) -> None:
        r = WhitelistRegistry()
        with pytest.raises(ValueError):
            r.add_rule("line_coverage", 0)  # already exists

    def test_semver_bump_major(self) -> None:
        r = WhitelistRegistry(version="1.2.3")
        r.add_rule("x1", 0, bump="major")
        assert r.version == "2.0.0"

    def test_semver_bump_minor(self) -> None:
        r = WhitelistRegistry(version="1.2.3")
        r.add_rule("y1", 0, bump="minor")
        assert r.version == "1.3.0"

    def test_semver_bump_patch(self) -> None:
        r = WhitelistRegistry(version="1.2.3")
        r.add_rule("z1", 0, bump="patch")
        assert r.version == "1.2.4"


class TestSafeExprValidatorUnit:
    """§6.1 SafeExprValidator 单元."""

    def test_validate_empty_expression_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import ASTSyntaxError
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS)
        with pytest.raises(ASTSyntaxError):
            v.parse_and_validate("")

    def test_parse_and_validate_returns_tree(self) -> None:
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS)
        tree = v.parse_and_validate("line_coverage() >= 0.8")
        assert isinstance(tree, ast.Expression)

    def test_non_ast_object_rejected(self) -> None:
        v = SafeExprValidator()
        with pytest.raises(IllegalNodeError):
            v.validate("not an ast tree")  # type: ignore[arg-type]

    def test_module_object_rejected(self) -> None:
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS)
        mod = ast.parse("1+1", mode="exec")
        with pytest.raises(IllegalNodeError):
            v.validate(mod)

    def test_numeric_constant_overflow_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import RecursionLimitExceeded
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS, max_int_const=100)
        with pytest.raises(RecursionLimitExceeded):
            v.parse_and_validate("line_coverage() > 999")

    def test_string_constant_too_long_rejected(self) -> None:
        from app.quality_loop.dod_compiler.errors import RecursionLimitExceeded
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS, max_str_const=10)
        with pytest.raises(RecursionLimitExceeded):
            v.parse_and_validate(f'has_file("{"x" * 100}")')

    def test_used_functions_tracking(self) -> None:
        v = SafeExprValidator(allowed_funcs=DEFAULT_WHITELIST_FUNCS)
        v.parse_and_validate("line_coverage() >= 0.8 and lint_errors() == 0")
        assert "line_coverage" in v.used_functions
        assert "lint_errors" in v.used_functions

    def test_compute_ast_metrics_non_ast_returns_zero(self) -> None:
        from app.quality_loop.dod_compiler.ast_nodes import compute_ast_metrics
        assert compute_ast_metrics("not ast") == (0, 0)  # type: ignore[arg-type]
        assert compute_ast_metrics(None) == (0, 0)  # type: ignore[arg-type]


class TestDataSourceWhitelistConstants:

    def test_whitelist_has_expected_6_keys(self) -> None:
        assert frozenset({
            "test_result", "coverage", "lint",
            "security_scan", "perf", "artifact",
        }) == WHITELISTED_DATA_SOURCE_KEYS
