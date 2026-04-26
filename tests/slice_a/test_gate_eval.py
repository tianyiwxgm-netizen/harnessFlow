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


def test_eval_len_of_list_compares_against_constant():
    """len(X) >= 1 must work when X is a list."""
    ctx = {"items": ["a", "b"]}
    assert eval_predicate("len(items) >= 1", ctx) is True
    assert eval_predicate("len(items) >= 5", ctx) is False


def test_eval_len_of_missing_field_is_zero():
    """When the field is None/missing, len(...) yields 0 — gate should treat as empty."""
    assert eval_predicate("len(items) >= 1", {}) is False
    assert eval_predicate("len(items) >= 1", {"items": None}) is False


def test_eval_len_of_nested_path():
    ctx = {"_derived": {"wbs": [{"id": 1}, {"id": 2}, {"id": 3}]}}
    assert eval_predicate("len(_derived.wbs) >= 1", ctx) is True
    assert eval_predicate("len(_derived.wbs) >= 3", ctx) is True
    assert eval_predicate("len(_derived.wbs) >= 4", ctx) is False


def test_eval_len_of_string():
    """len() on a string also works (some predicates may use it for non-empty checks)."""
    ctx = {"s": "hello"}
    assert eval_predicate("len(s) >= 1", ctx) is True


def test_eval_disallows_call_to_other_functions():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("max(1, 2) >= 1", {})


def test_eval_disallows_len_with_kwargs():
    with pytest.raises(GateEvalError, match="forbidden"):
        eval_predicate("len(x, foo=1)", {"x": [1]})


def test_eval_len_with_combined_predicate():
    """The N8 pattern: len(...) >= 1 AND len(...) >= 1 AND field != null."""
    ctx = {
        "_derived": {
            "scope": {
                "in_scope": ["a"],
                "out_of_scope": ["b"],
                "dod_expression": "test()",
            }
        }
    }
    expr = (
        "len(_derived.scope.in_scope) >= 1 AND "
        "len(_derived.scope.out_of_scope) >= 1 AND "
        "_derived.scope.dod_expression != null"
    )
    assert eval_predicate(expr, ctx) is True


def test_eval_all_13_yaml_predicates_parse_against_empty_ctx():
    """Every gate_predicate.expression in the yaml contract must parse without raising
    (eval result against empty ctx is allowed to be False — we only assert no exception)."""
    from pipelines.contract_loader import load_contract
    contract = load_contract()
    for nd in contract.nodes:
        expr = nd.gate_predicate["expression"]
        # parse + eval against empty ctx; we don't care about the bool result, only that
        # no GateEvalError is raised
        eval_predicate(expr, {})  # should not raise
