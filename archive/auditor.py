"""archive.auditor — route-weight failure-rate auditor.

Source: method3 § 7.2 / § 7.3 (每 20 次任务审计 + 只建议不改 matrix).
Phase 7 plan § Tasks 4.

Exposes:
    audit(archive_path, routing_matrix_path=None, interval=20, min_samples_per_cell=3,
          output_dir=None) -> AuditReport
    need_audit(archive_path, interval=20) -> bool
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
DEFAULT_ARCHIVE_PATH = HERE.parent / "failure-archive.jsonl"
DEFAULT_MATRIX_PATH = HERE.parent / "routing-matrix.json"
DEFAULT_OUTPUT_DIR = HERE.parent / "audit-reports"

WEIGHT_CAP = 1.0
DOWNWEIGHT_FACTOR = 0.8
UPWEIGHT_FACTOR = 1.1
DOWNWEIGHT_THRESHOLD = 0.5   # failure_rate > 0.5 → downweight
UPWEIGHT_THRESHOLD = 0.1     # failure_rate < 0.1 → upweight
UPWEIGHT_MIN_SAMPLES = 10    # more conservative for升权


@dataclass
class AuditCellSuggestion:
    cell: tuple[str, str]          # (size, task_type)
    route: str                     # A..F
    current_weight: Optional[float]
    suggested_weight: float
    reason: str
    sample_count: int
    failure_rate: float
    direction: str                 # "down" | "up" | "noop"


@dataclass
class AuditReport:
    generated_at: str
    interval: int
    min_samples_per_cell: int
    archive_path: str
    matrix_path: Optional[str]
    suggestions: list[AuditCellSuggestion] = field(default_factory=list)
    report_path: Optional[str] = None  # set by audit() when output_dir is provided

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "interval": self.interval,
            "min_samples_per_cell": self.min_samples_per_cell,
            "archive_path": self.archive_path,
            "matrix_path": self.matrix_path,
            "path": self.report_path,  # harnessFlow-skill.md § 8.6 reads arc_out["audit_report"]["path"]
            "suggestions": [
                {
                    "cell": list(s.cell),
                    "route": s.route,
                    "current_weight": s.current_weight,
                    "suggested_weight": s.suggested_weight,
                    "reason": s.reason,
                    "sample_count": s.sample_count,
                    "failure_rate": s.failure_rate,
                    "direction": s.direction,
                }
                for s in self.suggestions
            ],
        }


def _read_jsonl(path: Path) -> list[dict]:
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
            continue  # auditor tolerates bad lines, writer will raise
    return out


def _count_entries(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            n += 1
    return n


def need_audit(archive_path: str | Path = DEFAULT_ARCHIVE_PATH, interval: int = 20) -> bool:
    """Return True iff the archive count is ≥ interval and divisible by interval.

    Source: method3 § 7.3 default (every 20 tasks). Writer callers check this
    after each append to decide whether to trigger audit().
    """
    count = _count_entries(Path(archive_path))
    if count < interval:
        return False
    return count % interval == 0


def _lookup_current_weight(matrix: dict, size: str, task_type: str, route: str) -> Optional[float]:
    if not matrix:
        return None
    cell = (matrix.get(size) or {}).get(task_type)
    if not cell:
        return None
    for item in cell:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] == route:
            try:
                return float(item[1])
            except (TypeError, ValueError):
                return None
        if isinstance(item, dict) and item.get("route") == route:
            try:
                return float(item.get("weight"))
            except (TypeError, ValueError):
                return None
    return None


def audit(
    archive_path: str | Path = DEFAULT_ARCHIVE_PATH,
    routing_matrix_path: str | Path | None = DEFAULT_MATRIX_PATH,
    interval: int = 20,
    min_samples_per_cell: int = 3,
    output_dir: str | Path | None = DEFAULT_OUTPUT_DIR,
    tail_only: bool = False,
) -> AuditReport:
    """Build an AuditReport from archive.jsonl; optionally write to output_dir.

    Only suggests; never mutates routing-matrix.json (method3 § 7.3 evolution boundary:
    human approval required before writing matrix changes).
    """
    archive_path = Path(archive_path)
    entries = _read_jsonl(archive_path)

    if tail_only and len(entries) > interval:
        entries = entries[-interval:]

    matrix: dict = {}
    matrix_path_str: Optional[str] = None
    if routing_matrix_path and Path(routing_matrix_path).exists():
        matrix_path_str = str(routing_matrix_path)
        try:
            matrix = json.loads(Path(routing_matrix_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            matrix = {}

    # Group by (size, task_type, route); tally failure vs success
    groups: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"total": 0, "failed": 0}
    )
    for e in entries:
        size = e.get("size")
        tt = e.get("task_type")
        route = e.get("route")
        outcome = e.get("final_outcome")
        if not (size and tt and route and outcome):
            continue
        key = (size, tt, route)
        groups[key]["total"] += 1
        if outcome in ("failed", "aborted", "false_complete_reported"):
            groups[key]["failed"] += 1

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    report = AuditReport(
        generated_at=generated_at,
        interval=interval,
        min_samples_per_cell=min_samples_per_cell,
        archive_path=str(archive_path),
        matrix_path=matrix_path_str,
    )

    for (size, tt, route), counts in sorted(groups.items()):
        total = counts["total"]
        failed = counts["failed"]
        if total < min_samples_per_cell:
            continue
        failure_rate = failed / total if total else 0.0
        current_w = _lookup_current_weight(matrix, size, tt, route)

        direction = "noop"
        suggested_w = current_w if current_w is not None else 0.0
        reason = ""
        if failure_rate > DOWNWEIGHT_THRESHOLD:
            direction = "down"
            base = current_w if current_w is not None else 1.0
            suggested_w = round(base * DOWNWEIGHT_FACTOR, 4)
            reason = (
                f"failure_rate={failure_rate:.2f} > {DOWNWEIGHT_THRESHOLD}"
                f" (samples={total}); suggest weight *= {DOWNWEIGHT_FACTOR}"
            )
        elif failure_rate < UPWEIGHT_THRESHOLD and total >= UPWEIGHT_MIN_SAMPLES:
            direction = "up"
            base = current_w if current_w is not None else 1.0 / UPWEIGHT_FACTOR
            suggested_w = round(min(WEIGHT_CAP, base * UPWEIGHT_FACTOR), 4)
            reason = (
                f"failure_rate={failure_rate:.2f} < {UPWEIGHT_THRESHOLD}"
                f" (samples={total} ≥ {UPWEIGHT_MIN_SAMPLES}); suggest weight *= {UPWEIGHT_FACTOR},"
                f" capped at {WEIGHT_CAP}"
            )
        else:
            continue

        report.suggestions.append(
            AuditCellSuggestion(
                cell=(size, tt),
                route=route,
                current_weight=current_w,
                suggested_weight=suggested_w,
                reason=reason,
                sample_count=total,
                failure_rate=round(failure_rate, 4),
                direction=direction,
            )
        )

    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.replace(":", "").replace("-", "")
        out_path = out_dir / f"audit-{stamp}.json"
        report.report_path = str(out_path)
        out_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    return report
