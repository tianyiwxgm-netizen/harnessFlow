"""archive CLI entry point (Phase 8.2).

Usage (from harnessFlow/ parent dir):
    python3 -m archive list [--recent N] [--archive PATH]
    python3 -m archive audit [--dry-run] [--interval N] [--archive PATH]
    python3 -m archive stats [--archive PATH]

Design constraints:
    - **No modifications** to writer.py / auditor.py public API.
    - Read-only operations (list/stats). For audit, dry-run skips writing
      any audit-reports/*.json (respects method3 § 7.3 evolution boundary).
    - CWD-independent: default `archive_path` resolves relative to the
      harnessFlow root (which is the parent of the archive/ package).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from .auditor import audit, need_audit
from .writer import _read_jsonl  # type: ignore[attr-defined]

# archive/ lives inside harnessFlow/; defaults resolve relative to that root.
HERE = Path(__file__).resolve().parent
HARNESS_ROOT = HERE.parent
DEFAULT_ARCHIVE = HARNESS_ROOT / "failure-archive.jsonl"
DEFAULT_MATRIX = HARNESS_ROOT / "routing-matrix.json"


def _resolve_archive(path: Optional[str]) -> Path:
    if path:
        return Path(path).resolve()
    return DEFAULT_ARCHIVE


def _read_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue  # tolerate bad lines (writer fail would have raised)
    return out


def cmd_list(args: argparse.Namespace) -> int:
    path = _resolve_archive(args.archive)
    entries = _read_entries(path)
    if not entries:
        print(f"(archive {path} is empty or missing)")
        return 0

    recent = entries[-args.recent:] if args.recent > 0 else entries
    print(f"{'task_id':<24} {'date':<12} {'route':<5} {'outcome':<24} {'error_type':<14} freq")
    print("-" * 92)
    for e in recent:
        print(
            f"{e.get('task_id', '-'):<24} "
            f"{e.get('date', '-'):<12} "
            f"{e.get('route', '-'):<5} "
            f"{e.get('final_outcome', '-'):<24} "
            f"{e.get('error_type', '-'):<14} "
            f"{e.get('frequency', '-')}"
        )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    path = _resolve_archive(args.archive)
    if not path.exists():
        print(f"archive missing: {path}", file=sys.stderr)
        return 1

    # dry-run: call audit with output_dir=None so no file is written
    output_dir = None if args.dry_run else HARNESS_ROOT / "audit-reports"
    report = audit(
        archive_path=path,
        routing_matrix_path=DEFAULT_MATRIX,
        interval=args.interval,
        min_samples_per_cell=args.min_samples,
        output_dir=output_dir,
    )
    d = report.to_dict()
    print(f"generated_at:       {d['generated_at']}")
    print(f"interval:           {d['interval']}")
    print(f"min_samples_per_cell: {d['min_samples_per_cell']}")
    print(f"archive:            {d['archive_path']}")
    print(f"matrix (read-only): {d['matrix_path']}")
    print(f"report_path:        {d.get('path') or '(dry-run, not written)'}")
    print(f"suggestions:        {len(d['suggestions'])}")
    for s in d["suggestions"]:
        cell = "/".join(str(x) for x in s["cell"])
        print(
            f"  [{s['direction']:<4}] cell={cell} route={s['route']} "
            f"weight {s['current_weight']} -> {s['suggested_weight']} "
            f"({s['reason']}; samples={s['sample_count']}, fail_rate={s['failure_rate']})"
        )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    path = _resolve_archive(args.archive)
    entries = _read_entries(path)
    if not entries:
        print(f"(archive {path} is empty or missing)")
        return 0

    total = len(entries)
    by_outcome: Counter = Counter(e.get("final_outcome", "-") for e in entries)
    by_error: Counter = Counter(e.get("error_type", "-") for e in entries)
    by_route: Counter = Counter(e.get("route", "-") for e in entries)
    by_cell: Counter = Counter(
        (e.get("task_type", "-"), e.get("size", "-"), e.get("risk", "-"))
        for e in entries
    )

    print(f"=== archive stats: {path} ===")
    print(f"total entries: {total}")
    print()
    print("by final_outcome:")
    for k, v in by_outcome.most_common():
        print(f"  {k:<26} {v}")
    print()
    print("by error_type:")
    for k, v in by_error.most_common():
        print(f"  {k:<14} {v}")
    print()
    print("by route:")
    for k, v in by_route.most_common():
        print(f"  {k:<5} {v}")
    print()
    print("by (task_type, size, risk) cell:")
    for (tt, sz, rk), v in by_cell.most_common():
        print(f"  {tt:<16} {sz:<4} {rk:<10} {v}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m archive",
        description="harnessFlow failure-archive runtime inspector (Phase 8.2)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list recent archive entries")
    p_list.add_argument("--recent", type=int, default=10, help="last N entries (default 10; 0=all)")
    p_list.add_argument("--archive", type=str, help="path to failure-archive.jsonl (default: harnessFlow root)")
    p_list.set_defaults(func=cmd_list)

    p_audit = sub.add_parser("audit", help="run auditor (default dry-run=False writes audit-reports/)")
    p_audit.add_argument("--dry-run", action="store_true", help="do not write audit-reports/*.json")
    p_audit.add_argument("--interval", type=int, default=20, help="audit interval (default 20)")
    p_audit.add_argument("--min-samples", type=int, default=3, help="min samples per cell (default 3)")
    p_audit.add_argument("--archive", type=str, help="path to failure-archive.jsonl")
    p_audit.set_defaults(func=cmd_audit)

    p_stats = sub.add_parser("stats", help="aggregate frequency stats")
    p_stats.add_argument("--archive", type=str, help="path to failure-archive.jsonl")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
