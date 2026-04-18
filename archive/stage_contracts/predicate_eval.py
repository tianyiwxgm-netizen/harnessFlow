"""Whitelisted AST evaluator for gate_predicate expressions.

Security model:
    - Parses a predicate string with ast.parse(mode='eval')
    - Walks the AST; rejects any node type not in ALLOWED_NODES
    - Function calls only allowed for names in WHITELIST_FUNCTIONS
    - Names resolve from a flat context dict (usually task_board fields
      + pre-computed artifact refs)
    - No assignments, no imports, no lambdas, no comprehensions, no await

This is *not* a general Python evaluator. Only boolean combinations of
literal comparisons + whitelist function calls + name lookups.

See stage-contracts.md § 8 for the EBNF and whitelist.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Callable


class PredicateEvalError(Exception):
    """Raised when a predicate cannot be evaluated safely."""


# ---------------- whitelist function implementations -----------------

def _fs_file_exists(path: str) -> bool:
    return Path(path).exists() and Path(path).is_file()


def _fs_wc_lines(path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))


def _fs_grep_count(pattern: str, path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error:
        return 0
    text = p.read_text(encoding="utf-8", errors="ignore")
    return len(rx.findall(text))


def _diff_lines_net(diff_text: str) -> int:
    """Approximate net line delta from a unified diff string.

    Counts lines starting with '+' minus lines starting with '-',
    excluding the '+++'/'---' header pairs.
    """
    if not isinstance(diff_text, str):
        return 0
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added - removed


def _diff_paths_match(diff_text: str, globs: list[str] | tuple[str, ...]) -> bool:
    """Check every file path touched in a unified diff matches one of the globs."""
    import fnmatch
    if not isinstance(diff_text, str) or not globs:
        return False
    paths: set[str] = set()
    for line in diff_text.splitlines():
        m = re.match(r"^(?:\+\+\+|---)\s+(?:a/|b/)?(\S+)", line)
        if m and m.group(1) != "/dev/null":
            paths.add(m.group(1))
    if not paths:
        return False
    for p in paths:
        if not any(fnmatch.fnmatch(p, g) for g in globs):
            return False
    return True


def _schema_valid(data: Any, schema_ref: str) -> bool:
    """Validate data against a JSON schema (path relative to harnessFlow root)."""
    try:
        import json as _json
        import jsonschema as _js
    except ImportError:
        return False
    schema_path = Path(__file__).resolve().parents[2] / schema_ref
    if not schema_path.exists():
        return False
    try:
        schema = _json.loads(schema_path.read_text(encoding="utf-8"))
        _js.Draft7Validator(schema).validate(data)
        return True
    except Exception:
        return False


def _len_helper(collection: Any) -> int:
    try:
        return len(collection)
    except TypeError:
        return 0


def _pytest_exit_code(target: str) -> int:
    """Run pytest on a target; return exit code (0 = all pass)."""
    import subprocess
    harness_root = Path(__file__).resolve().parents[2]
    try:
        r = subprocess.run(
            ["python3", "-m", "pytest", "-q", "--no-header", target],
            cwd=str(harness_root),
            capture_output=True,
            timeout=180,
        )
        return r.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 2


def _no_public_api_breaking_change(diff_text: str) -> bool:
    """Conservative heuristic: no removed `def public_...` or `class Public` lines.

    This is a soft check — for real API diff use a dedicated tool.
    """
    if not isinstance(diff_text, str):
        return True
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            stripped = line[1:].lstrip()
            if stripped.startswith(("def ", "class ", "async def ")):
                if not stripped.lstrip().startswith(("def _", "class _", "async def _")):
                    return False
    return True


WHITELIST_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "file_exists": _fs_file_exists,
    "wc_lines": _fs_wc_lines,
    "grep_count": _fs_grep_count,
    "diff_lines_net": _diff_lines_net,
    "diff_paths_match": _diff_paths_match,
    "schema_valid": _schema_valid,
    "len": _len_helper,
    "pytest_exit_code": _pytest_exit_code,
    "no_public_api_breaking_change": _no_public_api_breaking_change,
    # Placeholders for primitives that require external deps at call-time
    # (oss/curl/ffprobe/playback/screenshot/eval_regression_delta/sha256_of_block)
    # are intentionally omitted in v1.2; v1.3 will wire them via the
    # verifier_primitives package. If a contract uses them, we'll return
    # a PredicateEvalError so the user sees the missing capability clearly.
}


# ---------------- AST whitelist walker -----------------

# Allowed node types. Anything else → reject.
_ALLOWED_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.Index,  # removed in py3.9+ but safe to include
    ast.List,
    ast.Tuple,
    ast.Set,
)


def _walk_ast(node: ast.AST) -> None:
    """DFS: reject disallowed node types, reject call to non-whitelisted function."""
    if not isinstance(node, _ALLOWED_NODES):
        raise PredicateEvalError(
            f"disallowed AST node type: {type(node).__name__}"
        )
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in WHITELIST_FUNCTIONS:
                raise PredicateEvalError(
                    f"function '{func.id}' not in WHITELIST_FUNCTIONS"
                )
        elif isinstance(func, ast.Attribute):
            # Allow attribute calls ONLY if the head is a known context name
            # (e.g. verifier_report.red_lines_detected.append() would be rejected
            #  here because we don't recursively allow .append / .extend)
            # Strategy: only Attribute **access** is allowed (not .method()).
            raise PredicateEvalError(
                "attribute calls are not allowed (use whitelist function instead)"
            )
        else:
            raise PredicateEvalError(
                f"unsupported call target type: {type(func).__name__}"
            )
    for child in ast.iter_child_nodes(node):
        _walk_ast(child)


def eval_predicate(expr: str, context: dict[str, Any] | None = None) -> bool:
    """Safely evaluate a gate_predicate string.

    Args:
        expr: Python-subset boolean expression. See stage-contracts.md § 8.
        context: name → value map (task_board fields, artifact refs, etc).
                 Defaults to empty.

    Returns:
        bool — the predicate result.

    Raises:
        PredicateEvalError — on any unsafe syntax, unknown function, or eval error.
    """
    if not isinstance(expr, str) or not expr.strip():
        raise PredicateEvalError("predicate is empty or not a string")

    context = dict(context or {})

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise PredicateEvalError(f"predicate is not valid Python expr: {e}") from e

    _walk_ast(tree)

    # Globals = whitelist functions only. Locals = context (names resolved).
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_globals.update(WHITELIST_FUNCTIONS)

    try:
        value = eval(  # noqa: S307  (use is intentional + guarded by AST walk)
            compile(tree, filename="<predicate>", mode="eval"),
            safe_globals,
            context,
        )
    except Exception as e:
        raise PredicateEvalError(f"predicate eval failed: {e}") from e

    if not isinstance(value, bool):
        # Coerce: non-zero → True
        return bool(value)
    return value
