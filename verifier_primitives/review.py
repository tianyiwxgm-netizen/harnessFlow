"""Code review verdict primitive.

v1: reads the most recent code-reviewer output that the main skill has
written to `harnessFlow /reviews/<task_id>.json`. The Verifier never calls
the code-reviewer subagent itself; the main skill does that separately.
"""

import json
from pathlib import Path


def code_review_verdict(task_id: str, reviews_dir: str = "harnessFlow /reviews") -> tuple[str, dict]:
    p = Path(reviews_dir) / f"{task_id}.json"
    if not p.is_file():
        return "MISSING", {"path": str(p), "error": "review_not_found"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "MISSING", {"path": str(p), "error": f"read_failed: {exc}"}
    verdict = str(data.get("verdict", "MISSING")).upper()
    if verdict not in {"PASS", "FAIL", "WARNING"}:
        verdict = "MISSING"
    return verdict, {"path": str(p), "verdict": verdict, "issue_count": len(data.get("issues", []))}
