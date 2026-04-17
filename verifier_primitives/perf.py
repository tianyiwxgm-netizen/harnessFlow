"""Performance regression primitive (thin v1: reads a number from a user-supplied script)."""

from pathlib import Path

from ._shell import run


def benchmark_regression_delta(baseline: str, script_path: str = "scripts/perf_check.sh") -> tuple[float, dict]:
    """Expects a project-specific script that prints a float delta on stdout
    (e.g. 0.023 meaning +2.3% regression). Missing script → DependencyMissing
    so the Verifier degrades to INSUFFICIENT_EVIDENCE instead of FAIL."""
    p = Path(script_path)
    if not p.is_file():
        return 999.0, {
            "script_path": script_path,
            "baseline": baseline,
            "error": "perf_script_missing",
        }
    result = run(["bash", script_path, baseline], timeout=180.0)
    try:
        delta = float(result["stdout"].strip())
    except ValueError:
        return 999.0, {
            "script_path": script_path,
            "baseline": baseline,
            "error": "unparseable_output",
            "raw": result,
        }
    return delta, {"script_path": script_path, "baseline": baseline, "delta": delta, "raw": result}
