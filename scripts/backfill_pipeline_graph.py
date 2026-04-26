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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines.contract_loader import emit_pipeline_graph

TASK_BOARDS_DIR = REPO_ROOT / "task-boards"
SKIP_LOG = REPO_ROOT / "archive" / "backfill-skipped.jsonl"


def backfill_one(task_board: dict) -> dict:
    """Mutate task_board in-place (sets _derived.pipeline); also returns it for convenience.

    Side effects: sets task_board['_derived']['pipeline'], and if the pipeline is non-None,
    mutates each node dict's 'status' key. Original task_board fields outside _derived are
    not touched.
    """
    pg = emit_pipeline_graph(task_board)
    if pg is None:
        task_board.setdefault("_derived", {})["pipeline"] = None
        return task_board

    state = task_board.get("current_state", "INIT")
    state_history = task_board.get("state_history") or []

    # approximate mapping; unknown states default to 0 (treated as not yet reached)
    state_to_step = {
        "INIT": 1, "CLARIFY": 3, "ROUTE_SELECT": 4, "PLAN": 10,
        "IMPL": 11, "MID_CHECKPOINT": 11, "CHECKPOINT_SAVE": 11, "MID_RETRO": 11,
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
    if args.dry_run and args.apply:
        ap.error("--dry-run and --apply are mutually exclusive")
    if not args.dry_run and not args.apply:
        ap.error("must pass --dry-run or --apply")

    SKIP_LOG.parent.mkdir(parents=True, exist_ok=True)
    processed, skipped = 0, 0
    for p in sorted(TASK_BOARDS_DIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        tb_for_log = None
        try:
            with p.open("r", encoding="utf-8") as f:
                tb_for_log = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            entry = {
                "path": str(p),
                "task_id": None,
                "error": str(e),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            skipped += 1
            continue
        tb = tb_for_log
        try:
            backfill_one(tb)
        except Exception as e:
            entry = {
                "path": str(p),
                "task_id": tb.get("task_id") if isinstance(tb, dict) else None,
                "error": str(e),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            with SKIP_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            skipped += 1
            continue
        processed += 1
        if args.apply:
            tmp = p.with_suffix(".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as f:
                    json.dump(tb, f, indent=2, ensure_ascii=False)
                os.replace(tmp, p)
            except Exception:
                tmp.unlink(missing_ok=True)
                raise

    print(f"processed={processed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
