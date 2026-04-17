"""Verifier executor: parse DoD expression, call primitives, decide verdict.

This is the Python reference implementation the `harnessFlow:verifier`
subagent follows. It is also what `tests/test_p20_fake_completion.py`
drives directly in-process to prove fake-completion is caught.

Only supports top-level AND-composed DoD expressions (method3 § 6.1
templates ① ② ③ ④ ⑤ are all pure AND). Future OR / nesting goes here.
"""

from __future__ import annotations

import ast
import datetime
from dataclasses import dataclass, field
from typing import Any, Callable

from . import classify_tier
from .errors import DependencyMissing


@dataclass
class Condition:
    raw: str
    primitive: str
    args: list[Any]
    op: str           # "==" / ">" / ">=" / "<" / "<=" / "!=" / "bool"
    expected: Any     # The RHS literal (or True for bool predicates)
    kw: str | None = None  # For attribute access like oss_head(...).status_code


@dataclass
class VerifierReport:
    task_id: str
    verdict: str
    priority_applied: str
    evidence_chain: dict[str, list[dict]] = field(default_factory=lambda: {"existence": [], "behavior": [], "quality": []})
    failed_conditions: list[str] = field(default_factory=list)
    red_lines: list[str] = field(default_factory=list)
    insufficient_evidence_count_after_this: int = 0
    dod_expression: str = ""
    ts: str = ""


# ---------- parser ----------


def parse_dod(expr: str) -> list[Condition]:
    """Parse a DoD expression into conditions.

    Accepts:
        file_exists("x.mp4")
        ffprobe_duration("x.mp4") > 0
        oss_head("...").status_code == 200
        code_review_verdict == "PASS"
        schema_valid(curl_json("http://..."), "schemas/x.json")   # nested call — treated as single primitive with string-ified arg
    Joined by top-level 'AND'.
    """
    # Normalize boolean connective so `ast` parses it
    normalized = expr.replace(" AND ", " and ").replace(" OR ", " or ")
    tree = ast.parse(normalized, mode="eval").body

    conds: list[Condition] = []
    nodes = _flatten_and(tree)
    for node in nodes:
        conds.append(_build_condition(node))
    return conds


def _flatten_and(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        out: list[ast.AST] = []
        for v in node.values:
            out.extend(_flatten_and(v))
        return out
    return [node]


def _build_condition(node: ast.AST) -> Condition:
    raw = ast.unparse(node)

    # Pattern: `primitive(args) OP literal`
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left = node.left
        op = _stringify_op(node.ops[0])
        right = node.comparators[0]
        primitive, args, kw = _extract_primitive(left)
        expected = _literal(right)
        return Condition(raw=raw, primitive=primitive, args=args, kw=kw, op=op, expected=expected)

    # Pattern: bare call like `file_exists("x")`
    if isinstance(node, ast.Call):
        primitive, args, kw = _extract_primitive(node)
        return Condition(raw=raw, primitive=primitive, args=args, kw=kw, op="bool", expected=True)

    # Pattern: bare identifier like `retro_exists` (unlikely but safe)
    if isinstance(node, ast.Name):
        return Condition(raw=raw, primitive=node.id, args=[], kw=None, op="bool", expected=True)

    raise ValueError(f"Unsupported DoD sub-expression: {raw}")


def _extract_primitive(node: ast.AST) -> tuple[str, list[Any], str | None]:
    # Handle `<call>.attr` (e.g. oss_head(...).status_code)
    if isinstance(node, ast.Attribute):
        base_name, base_args, _ = _extract_primitive(node.value)
        return base_name, base_args, node.attr
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            raise ValueError(f"Unsupported call target: {ast.unparse(node)}")
        args = [_literal(a) for a in node.args]
        return name, args, None
    if isinstance(node, ast.Name):
        return node.id, [], None
    raise ValueError(f"Unsupported primitive shape: {ast.unparse(node)}")


class _NestedCall:
    """Sentinel for a nested primitive call in a DoD arg.

    Preserved until eval time; `eval_verifier` resolves it by invoking the
    inner primitive first, then substituting the `actual` return into the
    outer primitive's arg list. Prevents the silent false-PASS when
    `schema_valid(curl_json(...), ...)` was stringified to a dict."""

    def __init__(self, node: ast.Call):
        self.node = node
        self.raw = ast.unparse(node)


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Call):
        return _NestedCall(node)
    if isinstance(node, ast.Name):
        return {"__name__": node.id}
    return ast.unparse(node)


_OP_MAP = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Lt: "<",
    ast.LtE: "<=",
}


def _stringify_op(op: ast.cmpop) -> str:
    return _OP_MAP.get(type(op), "?")


# ---------- eval ----------


_STRUCTURAL_TYPES = (dict, list, tuple, set)


def compare(actual: Any, expected: Any, op: str) -> bool | None:
    """Return True/False for pass/fail, or None when the comparison is
    ill-formed (treated as INSUFFICIENT_EVIDENCE by the caller)."""
    if op == "bool":
        # DoD like `oss_head("...")` without `.status_code` — a dict is
        # truthy but the author obviously meant to compare an attribute.
        # Refuse to rubber-stamp: return None → INSUFFICIENT_EVIDENCE.
        if isinstance(actual, _STRUCTURAL_TYPES) or actual is None:
            return None
        return bool(actual)
    try:
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        if op == ">":
            return actual > expected
        if op == ">=":
            return actual >= expected
        if op == "<":
            return actual < expected
        if op == "<=":
            return actual <= expected
    except TypeError:
        return False
    return False


def eval_verifier(
    task_id: str,
    dod_expression: str,
    task_board: dict,
    primitive_resolver: Callable[[str], Callable | None],
    cap: int = 2,
) -> VerifierReport:
    conds = parse_dod(dod_expression)
    report = VerifierReport(
        task_id=task_id,
        verdict="",
        priority_applied="",
        dod_expression=dod_expression,
        ts=_now(),
    )

    any_fail = False
    any_insufficient = False

    for c in conds:
        fn = primitive_resolver(c.primitive)
        if fn is None:
            any_insufficient = True
            _append(report, c, passed=False, actual=None, evidence={"error": "unknown_primitive"}, insufficient=True)
            continue

        # Resolve nested-call args before invoking the outer primitive.
        # Each inner call also produces a behavior-tier evidence entry so
        # readers can see what the inner primitive actually returned.
        resolved_args, inner_insufficient = _resolve_nested_args(
            c, primitive_resolver, report
        )
        if inner_insufficient:
            any_insufficient = True
            _append(
                report,
                c,
                passed=False,
                actual=None,
                evidence={"error": "nested_call_unresolvable"},
                insufficient=True,
            )
            continue

        try:
            actual_raw, evidence = fn(*resolved_args)
        except DependencyMissing as e:
            any_insufficient = True
            _append(
                report,
                c,
                passed=False,
                actual=None,
                evidence={"error": "dep_missing", "tool": e.tool, "detail": e.detail},
                insufficient=True,
            )
            continue
        except TypeError as e:
            # e.g. `code_review_verdict == "PASS"` called with args=[] but
            # the primitive requires a task_id. Do NOT crash — the resolver
            # is expected to wrap context-bound primitives; treat missing
            # wrap as INSUFFICIENT_EVIDENCE so the main skill can escalate.
            any_insufficient = True
            _append(
                report,
                c,
                passed=False,
                actual=None,
                evidence={"error": "primitive_call_failed", "detail": str(e)},
                insufficient=True,
            )
            continue
        except Exception as e:  # noqa: BLE001 — any other primitive bug → INSUFFICIENT
            any_insufficient = True
            _append(
                report,
                c,
                passed=False,
                actual=None,
                evidence={"error": "primitive_exception", "detail": f"{type(e).__name__}: {e}"},
                insufficient=True,
            )
            continue

        actual = actual_raw
        if c.kw is not None:
            if isinstance(actual_raw, dict):
                actual = actual_raw.get(c.kw)
            else:
                actual = getattr(actual_raw, c.kw, None)

        passed = compare(actual, c.expected, c.op)
        if passed is None:
            # Ill-formed comparison (e.g. `oss_head(...)` without `.status_code`
            # evaluated as bool against a dict). Refuse to rubber-stamp.
            any_insufficient = True
            _append(
                report,
                c,
                passed=False,
                actual=actual,
                evidence={**(evidence or {}), "error": "bool_on_structured_result"},
                insufficient=True,
            )
            continue

        _append(report, c, passed=passed, actual=actual, evidence=evidence)
        if not passed:
            any_fail = True
            report.failed_conditions.append(c.raw)

    # Red-line propagation: inherit whatever Supervisor / task-board has
    # already recorded. Any fail/insufficient that touches a DoD-critical
    # primitive (oss / ffprobe / schema / pytest / playback / curl) appends
    # DOD_GAP_ALERT. State-machine § 7 P3 requires insufficient evidence
    # also raises DOD_GAP_ALERT so the main skill can escalate instead of
    # silently looping.
    report.red_lines = list(task_board.get("red_lines", []) or [])

    _DOD_CRITICAL = (
        "oss_head",
        "ffprobe_duration",
        "playback_check",
        "schema_valid",
        "curl_status",
        "pytest",
        "playwright",
    )

    def _maybe_flag_gap(condition_raws):
        for raw in condition_raws:
            if any(k in raw for k in _DOD_CRITICAL):
                if "DOD_GAP_ALERT" not in report.red_lines:
                    report.red_lines.append("DOD_GAP_ALERT")
                return

    if any_fail:
        _maybe_flag_gap(report.failed_conditions)

    if any_insufficient:
        insufficient_raws = [
            e["primitive"] + "(" + ",".join(str(a) for a in e.get("args", [])) + ")"
            for tier in report.evidence_chain.values()
            for e in tier
            if e.get("insufficient")
        ]
        _maybe_flag_gap(insufficient_raws)

    # Verdict decision — mirrors state-machine § 7 P0-P3
    if any_fail and report.red_lines:
        report.verdict = "FAIL"
        report.priority_applied = "P0_red_line"
    elif any_fail:
        report.verdict = "FAIL"
        report.priority_applied = "P2_normal_fail"
    elif any_insufficient:
        current = int(task_board.get("insufficient_evidence_count", 0))
        if current + 1 >= cap:
            report.verdict = "FAIL"
            report.priority_applied = "P3_cap_exceeded"
            report.insufficient_evidence_count_after_this = current + 1
        else:
            report.verdict = "INSUFFICIENT_EVIDENCE"
            report.priority_applied = "P3_insufficient_evidence"
            report.insufficient_evidence_count_after_this = current + 1
    else:
        report.verdict = "PASS"
        report.priority_applied = "P1_pass"

    return report


def _resolve_nested_args(
    c: Condition,
    resolver: Callable[[str], Callable | None],
    report: VerifierReport,
) -> tuple[list[Any], bool]:
    """Replace each _NestedCall arg with the primitive's actual return
    value, invoking the inner primitive with its own literal args.

    Inner-call evidence is appended to the behavior tier so observers can
    see the chained calls. Returns (resolved_args, inner_insufficient).
    """
    resolved: list[Any] = []
    insufficient = False
    for arg in c.args:
        if not isinstance(arg, _NestedCall):
            resolved.append(arg)
            continue
        inner_primitive, inner_args, inner_kw = _extract_primitive(arg.node)
        inner_args = [_literal(a) for a in arg.node.args]
        fn = resolver(inner_primitive)
        if fn is None:
            insufficient = True
            report.evidence_chain["behavior"].append({
                "primitive": inner_primitive,
                "args": inner_args,
                "nested_under": c.primitive,
                "evidence": {"error": "unknown_primitive"},
                "insufficient": True,
                "ts": _now(),
            })
            resolved.append(None)
            continue
        try:
            inner_actual_raw, inner_evidence = fn(*inner_args)
        except DependencyMissing as e:
            insufficient = True
            report.evidence_chain["behavior"].append({
                "primitive": inner_primitive,
                "args": inner_args,
                "nested_under": c.primitive,
                "evidence": {"error": "dep_missing", "tool": e.tool, "detail": e.detail},
                "insufficient": True,
                "ts": _now(),
            })
            resolved.append(None)
            continue
        except Exception as e:  # noqa: BLE001
            insufficient = True
            report.evidence_chain["behavior"].append({
                "primitive": inner_primitive,
                "args": inner_args,
                "nested_under": c.primitive,
                "evidence": {"error": "primitive_exception", "detail": f"{type(e).__name__}: {e}"},
                "insufficient": True,
                "ts": _now(),
            })
            resolved.append(None)
            continue
        inner_actual = inner_actual_raw
        if inner_kw is not None and isinstance(inner_actual_raw, dict):
            inner_actual = inner_actual_raw.get(inner_kw)
        report.evidence_chain["behavior"].append({
            "primitive": inner_primitive,
            "args": inner_args,
            "nested_under": c.primitive,
            "actual": inner_actual,
            "evidence": inner_evidence,
            "ts": _now(),
        })
        resolved.append(inner_actual)
    return resolved, insufficient


def _append(report: VerifierReport, c: Condition, *, passed: bool, actual, evidence, insufficient: bool = False) -> None:
    tier = classify_tier(c.primitive)
    report.evidence_chain[tier].append({
        "primitive": c.primitive,
        "args": c.args,
        "kw": c.kw,
        "expected": c.expected,
        "actual": actual,
        "passed": passed,
        "evidence": evidence,
        "insufficient": insufficient,
        "ts": _now(),
    })


def _now() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
