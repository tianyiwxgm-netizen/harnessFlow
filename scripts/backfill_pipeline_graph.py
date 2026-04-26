"""One-shot script: backfill _derived.pipeline for archived task-boards.

Reads task-boards/*.json, derives pipeline_graph view from state_history +
stage_artifacts, writes back to _derived.pipeline (does NOT touch original
task_board fields).

Usage:
    python scripts/backfill_pipeline_graph.py --dry-run
    python scripts/backfill_pipeline_graph.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.contract_loader import emit_pipeline_graph

TASK_BOARDS_DIR = REPO_ROOT / "task-boards"
SKIP_LOG = REPO_ROOT / "archive" / "backfill-skipped.jsonl"


def backfill_one(task_board: dict) -> dict:
    """Compute _derived.pipeline (do not mutate original keys)."""
    pg = emit_pipeline_graph(task_board)
    if pg is None:
        task_board.setdefault("_derived", {})["pipeline"] = None
        return task_board

    state = task_board.get("current_state", "INIT")
    state_history = task_board.get("state_history") or []

    # Map state → step (rough)
    state_to_step = {
        "INIT": 1, "CLARIFY": 3, "ROUTE_SELECT": 4, "PLAN": 10,
        "IMPL": 11, "MID_CHECKPOINT": 11, "MID_RETRO": 11,
        "VERIFY": 12, "SANTA_LOOP": 11, "COMMIT": 13,
        "RETRO_CLOSE": 13, "CLOSED": 13, "ABORTED": 0,
        "PAUSED_ESCALATED": 11,
    }
    last_step = state_to_step.get(state, 0)

    if state == "CLOSED":
        for n in pg["nodes"]:
            n["status"] = "passed"
    elif state == "ABORTED":
        # Last reached step → failed; rest pending
        last_real = next(
            (e["state"] for e in reversed(state_history)
             if e.get("state") not in ("ABORTED", "PAUSED_ESCALATED")),
            None,
        )
        last_step = state_to_step.get(last_real or "", 0)
        for n in pg["nodes"]:
            if n["step"] < last_step:
                n["status"] = "passed"
            elif n["step"] == last_step:
                n["status"] = "failed"
            else:
                n["status"] = "pending"
    else:  # in-progress / PAUSED_ESCALATED
        for n in pg["nodes"]:
            if n["step"] < last_step:
                n["status"] = "passed"
            elif n["step"] == last_step:
                n["status"] = "running"
            else:
                n["status"] = "pending"

    task_board.setdefault("_derived", {})["pipeline"] = pg
    return task_board


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print stats; no writes")
    ap.add_argument("--apply", action="store_true", help="write back to disk")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        ap.error("must pass --dry-run or --apply")

    SKIP_LOG.parent.mkdir(parents=True, exist_ok=True)
    processed, skipped = 0, 0
    for p in sorted(TASK_BOARDS_DIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            with p.open("r", encoding="utf-8") as f:
                tb = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"path": str(p), "error": str(e)}) + "\n")
            skipped += 1
            continue
        try:
            backfill_one(tb)
        except Exception as e:
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"path": str(p), "error": str(e)}) + "\n")
            skipped += 1
            continue
        processed += 1
        if args.apply:
            with p.open("w", encoding="utf-8") as f:
                json.dump(tb, f, indent=2, ensure_ascii=False)

    print(f"processed={processed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
