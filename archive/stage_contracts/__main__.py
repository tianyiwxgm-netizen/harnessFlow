"""CLI for archive.stage_contracts (v1.2).

Subcommands:
    python -m archive.stage_contracts list
    python -m archive.stage_contracts validate <task_board.json> <stage_id> <enter|exit>

Design constraint: read-only; never writes task-board / contract files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from archive.stage_contracts import (
    StageValidationError,
    load_contracts,
    validate_stage_io,
)
from archive.stage_contracts.parser import ParseError


def _resolve_tb(arg_path: str) -> Path:
    """Resolve task-board path: absolute / relative cwd / under harnessFlow/task-boards/."""
    p = Path(arg_path)
    if p.exists():
        return p
    harness_root = Path(__file__).resolve().parents[2]
    alt = harness_root / "task-boards" / arg_path
    if alt.exists():
        return alt
    alt2 = harness_root / "task-boards" / (arg_path + ".json")
    if alt2.exists():
        return alt2
    return p  # return original; caller will see not-found


def cmd_list(_args: argparse.Namespace) -> int:
    try:
        contracts = load_contracts()
    except ParseError as e:
        print(f"parse error: {e}", file=sys.stderr)
        return 1

    print(f"{len(contracts)} stage contracts loaded from stage-contracts.md:\n")
    print(f"{'stage_id':<30} {'route':<8} {'state':<18} {'phase':<12} skill")
    print("-" * 110)
    for c in sorted(contracts, key=lambda x: x.stage_id):
        print(
            f"{c.stage_id:<30} {c.route:<8} {c.state:<18} {c.phase_label:<12} {c.skill_invoked}"
        )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    tb_path = _resolve_tb(args.task_board)
    if not tb_path.exists():
        print(f"task-board not found: {tb_path}", file=sys.stderr)
        return 1
    try:
        task_board = json.loads(tb_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"task-board JSON invalid: {e}", file=sys.stderr)
        return 1

    try:
        verdict, violations = validate_stage_io(
            task_board, args.stage_id, phase=args.phase
        )
    except StageValidationError as e:
        print(f"validation infra error: {e}", file=sys.stderr)
        return 1
    except ParseError as e:
        print(f"parse error: {e}", file=sys.stderr)
        return 1

    print(f"task_board: {tb_path}")
    print(f"stage_id:   {args.stage_id}")
    print(f"phase:      {args.phase}")
    print(f"verdict:    {verdict}")
    if violations:
        print(f"violations ({len(violations)}):")
        for v in violations:
            print(f"  - [{v.kind}] {v.artifact_ref or '-'} from {v.from_stage or '-'}: {v.reason}")
    else:
        print("violations: none")
    return 0 if verdict in ("OK", "WARN") else 2


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m archive.stage_contracts",
        description="Stage Contract v1.2 CLI (harnessFlow)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list all stage contracts")
    p_list.set_defaults(func=cmd_list)

    p_val = sub.add_parser(
        "validate",
        help="validate a task-board against a stage's enter/exit contract",
    )
    p_val.add_argument("task_board", help="path or task_id (.json resolved automatically)")
    p_val.add_argument("stage_id", help="e.g. C-IMPL, B-VERIFY")
    p_val.add_argument(
        "phase",
        choices=["enter", "exit"],
        help="which side to check",
    )
    p_val.set_defaults(func=cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
