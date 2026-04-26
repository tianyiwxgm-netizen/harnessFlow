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
