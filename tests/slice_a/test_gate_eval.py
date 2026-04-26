"""Tests for pipelines.gate_eval — gate_predicate AST evaluator."""
from __future__ import annotations

import pytest

from pipelines.gate_eval import eval_predicate, GateEvalError


def test_eval_simple_not_null():
    ctx = {"task_id": "test-001"}
    assert eval_predicate("task_id != null", ctx) is True


def test_eval_null_field_returns_false():
    ctx = {"task_id": None}
    assert eval_predicate("task_id != null", ctx) is False


def test_eval_nested_field_path():
    ctx = {"goal_anchor": {"hash": "deadbeef"}}
    assert eval_predicate("goal_anchor.hash != null", ctx) is True


def test_eval_and_combinator():
    ctx = {"a": 1, "b": 2}
    assert eval_predicate("a != null AND b != null", ctx) is True


def test_eval_and_one_false():
    ctx = {"a": 1, "b": None}
    assert eval_predicate("a != null AND b != null", ctx) is False


def test_eval_or_combinator():
    ctx = {"a": None, "b": 2}
    assert eval_predicate("a != null OR b != null", ctx) is True


def test_eval_string_comparison():
    ctx = {"verdict": "PASS"}
    assert eval_predicate("verdict == 'PASS'", ctx) is True


def test_eval_forbidden_import_raises():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("__import__('os').system('ls')", {})


def test_eval_forbidden_lambda_raises():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("lambda x: x", {})


def test_eval_null_substring_in_field_name_preserved():
    """Word-boundary replace: `null_field` must stay a Name, not become None_field."""
    ctx = {"null_field": "set"}
    assert eval_predicate("null_field != null", ctx) is True


def test_eval_chained_comparison():
    """Compare chain `1 < 2 < 3` evaluates with Python semantics → True."""
    assert eval_predicate("1 < 2 < 3", {}) is True
    assert eval_predicate("1 < 3 < 2", {}) is False


def test_eval_empty_ctx_missing_field_is_false():
    assert eval_predicate("a != null", {}) is False


def test_eval_error_message_includes_expression():
    """When eval fails, the original expression is in the error message — not just the AST node name."""
    with pytest.raises(GateEvalError, match="lambda x: x"):
        eval_predicate("lambda x: x", {})
