"""CLI entry point invoked by hooks/PostToolUse-supervisor-wake.sh."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .wake import should_pulse


def _resolve_repo_root() -> Path:
    p = Path(__file__).resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / ".git").exists():
            return ancestor
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--state-dir")
    parser.add_argument("--task-boards-dir")
    args = parser.parse_args()

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    repo_root = _resolve_repo_root()
    state_dir = (
        Path(args.state_dir)
        if args.state_dir
        else repo_root / "archive" / "supervisor_wake" / "state"
    )
    task_boards_dir = (
        Path(args.task_boards_dir)
        if args.task_boards_dir
        else repo_root / "task-boards"
    )

    result = should_pulse(args.task_id, payload, state_dir, task_boards_dir)
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
