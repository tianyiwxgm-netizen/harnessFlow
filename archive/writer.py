"""archive.writer — structured failure-archive.jsonl entry writer.

Source: method3 § 7.3 archive schema; Phase 7 plan § Tasks 3.

One public entry point:
    write_archive_entry(task_id, task_board_path, ...) -> dict
        Returns the persisted entry dict (schema-valid fields) with an extra
        non-schema key `_line_no` set to the 1-based line number of the line
        just appended to `failure-archive.jsonl` (used by the subagent to
        build `task-board.archive_entry_link = "...#L<n>"`).

Raises ArchiveWriteError on:
    - task_board / verifier_report file missing or malformed
    - schema validation failure on derived entry
    - fcntl lock acquisition failure after retries
"""

from __future__ import annotations

import fcntl
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from jsonschema import Draft7Validator
except ImportError as exc:  # pragma: no cover
    raise ImportError("archive.writer requires jsonschema; pip install jsonschema") from exc

HERE = Path(__file__).resolve().parent
DEFAULT_SCHEMA_PATH = HERE.parent / "schemas" / "failure-archive.schema.json"
DEFAULT_ARCHIVE_PATH = HERE.parent / "failure-archive.jsonl"

NODE_MAP = {
    "INIT": "other",
    "CLARIFY": "clarify",
    "ROUTE_SELECT": "route_select",
    "PLAN": "plan",
    "CHECKPOINT_SAVE": "plan",
    "IMPL": "impl",
    "MID_CHECKPOINT": "impl",
    "MID_RETRO": "impl",
    "UI_SCREENSHOT": "impl",
    "NODE_UNIT_TEST": "impl",
    "GRAPH_COMPILE": "impl",
    "RESEARCH": "impl",
    "DECISION_LOG": "impl",
    "VERIFY": "verifier",
    "SANTA_LOOP": "verifier",
    "COMMIT": "impl",
    "RETRO_CLOSE": "retro",
    "CLOSED": "other",
}
TERMINAL_STATES = {"CLOSED", "ABORTED", "PAUSED_ESCALATED"}

TASK_TYPE_ALIASES = {
    "纯代码": "后端feature",
    "后端 feature": "后端feature",
    "后端feature": "后端feature",
    "UI": "UI_feature",
    "UI_feature": "UI_feature",
    "agent graph": "后端feature",
    "视频出片": "视频出片",
    "文档": "文档",
    "重构": "重构",
    "研究": "研究",
}

_ALLOWED_ROUTES = {"A", "B", "C", "D", "E", "F"}
_ALLOWED_SIZES = {"XS", "S", "M", "L", "XL"}
_ALLOWED_RISKS = {"低", "中", "高", "不可逆"}


class ArchiveWriteError(Exception):
    """Specific exception for archive write failures.

    Not silent: any Caller upstream must handle or surface this to the user
    (method3 § 7.3 — archive is retro gold; losing entries defeats the evolution chain).
    """


@dataclass
class _DerivedFields:
    base: dict[str, Any]
    frequency_match_key: tuple


def _now_utc_iso() -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ts = now.isoformat().replace("+00:00", "Z")
    date = ts.split("T", 1)[0]
    return date, ts


def _read_json(path: Path, label: str) -> dict:
    if not path.exists():
        raise ArchiveWriteError(f"{label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchiveWriteError(f"{label} unreadable: {path}: {exc}") from exc


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ArchiveWriteError(
                f"archive.jsonl malformed at {path}:{lineno}: {exc}"
            ) from exc
    return out


def _map_node(task_board: dict) -> str:
    state = task_board.get("current_state") or "other"
    if state in TERMINAL_STATES:
        for entry in reversed(task_board.get("state_history", []) or []):
            prev = entry.get("state")
            if prev and prev not in TERMINAL_STATES:
                return NODE_MAP.get(prev, "other")
        return "other"
    return NODE_MAP.get(state, "other")


def _map_task_type(task_board: dict) -> str:
    raw = task_board.get("task_type") or ""
    return TASK_TYPE_ALIASES.get(raw, "其他")


def _derive_retry_fields(task_board: dict) -> tuple[int, list[str]]:
    retries = task_board.get("retries", []) or []
    count = len(retries)
    levels: list[str] = []
    for r in retries:
        lv = r.get("level")
        if lv in ("L0", "L1", "L2", "L3") and lv not in levels:
            levels.append(lv)
    return count, levels


def _derive_error_type(task_board: dict, verifier_report: Optional[dict]) -> str:
    red = task_board.get("red_lines", []) or []
    red_codes = set()
    for rl in red:
        if isinstance(rl, dict):
            code = rl.get("code")
            if code:
                red_codes.add(code)
        elif isinstance(rl, str):
            red_codes.add(rl)
    if verifier_report:
        red_codes.update(verifier_report.get("red_lines", []) or [])

    if "DRIFT_CRITICAL" in red_codes:
        return "DRIFT"
    if "IRREVERSIBLE_HALT" in red_codes:
        return "IRREVERSIBLE_HALT"
    if "DOD_GAP_ALERT" in red_codes:
        return "DOD_GAP"

    abort = (task_board.get("abort_reason") or "").lower()
    if "token" in abort or "budget" in abort:
        return "TOKEN_BUDGET"
    if "user" in abort or "abort" in abort:
        return "USER_ABORT"
    if "dependency" in abort or "missing" in abort:
        return "DEPENDENCY_MISSING"

    if verifier_report and verifier_report.get("priority_applied") == "P3_cap_exceeded":
        return "STUCK"

    if verifier_report and verifier_report.get("verdict") == "FAIL":
        return "DOD_GAP"

    return "OTHER"


def _derive_missing_subcontract(
    verifier_report: Optional[dict],
) -> list[str]:
    if not verifier_report:
        return []
    failed = verifier_report.get("failed_conditions", []) or []
    out: list[str] = []
    for cond in failed:
        if not isinstance(cond, str):
            continue
        m = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)", cond)
        if m:
            out.append(m.group(1))
        else:
            out.append(cond[:120])
    return out[:64]


def _derive_final_outcome(
    task_board: dict, verifier_report: Optional[dict], override: Optional[str]
) -> str:
    if override in ("success", "failed", "aborted", "false_complete_reported"):
        return override
    fo = task_board.get("final_outcome")
    if fo in ("success", "failed", "aborted"):
        return fo
    state = task_board.get("current_state")
    if state == "ABORTED":
        return "aborted"
    if state == "PAUSED_ESCALATED":
        return "failed"
    if state == "CLOSED":
        if verifier_report and verifier_report.get("verdict") == "FAIL":
            return "false_complete_reported"
        return "success"
    return "failed"


def _count_supervisor_events(path: Optional[Path], task_board: dict) -> dict:
    out = {"INFO": 0, "WARN": 0, "BLOCK": 0}
    if path is not None:
        entries = _read_jsonl(path) if path.exists() else []
        for ev in entries:
            if ev.get("task_id") and ev.get("task_id") != task_board.get("task_id"):
                continue
            sev = ev.get("severity")
            if sev in out:
                out[sev] += 1
        if any(out.values()):
            return out
    for ev in task_board.get("supervisor_interventions", []) or []:
        sev = ev.get("severity")
        if sev in out:
            out[sev] += 1
    return out


def _count_user_interrupts(task_board: dict) -> dict:
    out = {"DRIFT": 0, "DOD_GAP": 0, "IRREVERSIBLE": 0, "废问题": 0}
    for rl in task_board.get("red_lines", []) or []:
        code = rl.get("code") if isinstance(rl, dict) else rl
        if code == "DRIFT_CRITICAL":
            out["DRIFT"] += 1
        elif code == "DOD_GAP_ALERT":
            out["DOD_GAP"] += 1
        elif code == "IRREVERSIBLE_HALT":
            out["IRREVERSIBLE"] += 1
    for ev in task_board.get("supervisor_interventions", []) or []:
        code = ev.get("code", "") or ""
        if "废问题" in code or "wasted_question" in code:
            out["废问题"] += 1
    return out


def _derive_budget(task_board: dict) -> tuple[Optional[float], Optional[float], Optional[float]]:
    tb_time = task_board.get("time_budget") or {}
    elapsed_sec = tb_time.get("elapsed_sec")
    elapsed_min = round(elapsed_sec / 60.0, 2) if isinstance(elapsed_sec, (int, float)) else None
    tb_cost = task_board.get("cost_budget") or {}
    tu = tb_cost.get("token_used")
    tc = tb_cost.get("token_cap")
    token_used = float(tu) if isinstance(tu, (int, float)) else None
    token_budget = float(tc) if isinstance(tc, (int, float)) else None
    return elapsed_min, token_used, token_budget


def _check_route(route: Any) -> str:
    if route in _ALLOWED_ROUTES:
        return route
    if isinstance(route, str):
        base = route.split("-", 1)[0]
        if base in _ALLOWED_ROUTES:
            return base
    raise ArchiveWriteError(f"route invalid: {route!r}; must be one of {sorted(_ALLOWED_ROUTES)}")


def _check_enum(value: Any, allowed: set, label: str) -> str:
    if value in allowed:
        return value
    raise ArchiveWriteError(f"{label} invalid: {value!r}; must be one of {sorted(allowed)}")


def _derive_entry(
    task_id: str,
    task_board: dict,
    verifier_report: Optional[dict],
    supervisor_events_path: Optional[Path],
    retro_notes: Optional[dict],
    verifier_report_link: Optional[str],
    retro_link: Optional[str],
    explicit_project: Optional[str],
) -> dict:
    date, ts = _now_utc_iso()
    retry_count, retry_levels = _derive_retry_fields(task_board)
    error_type = _derive_error_type(task_board, verifier_report)
    missing_sub = _derive_missing_subcontract(verifier_report)
    final_outcome = _derive_final_outcome(
        task_board, verifier_report, (retro_notes or {}).get("final_outcome")
    )
    elapsed_min, token_used, token_budget = _derive_budget(task_board)
    sev_count = _count_supervisor_events(supervisor_events_path, task_board)
    user_int = _count_user_interrupts(task_board)

    root_cause = (
        (retro_notes or {}).get("root_cause")
        or (
            f"verifier failed_conditions: {'; '.join(missing_sub)}; verdict={verifier_report.get('verdict') if verifier_report else 'n/a'}"
            if missing_sub or verifier_report
            else "<待人工补充>"
        )
    )
    fix = (retro_notes or {}).get("fix") or "<待人工补充>"
    prevention = (retro_notes or {}).get("prevention") or "<待人工补充>"

    project = explicit_project or task_board.get("project") or "unknown"
    task_type = _map_task_type(task_board)
    size = _check_enum(task_board.get("size"), _ALLOWED_SIZES, "size")
    risk = _check_enum(task_board.get("risk"), _ALLOWED_RISKS, "risk")
    route = _check_route(task_board.get("route_id") or task_board.get("route"))
    node = _map_node(task_board)

    entry: dict[str, Any] = {
        "task_id": task_id,
        "date": date,
        "ts": ts,
        "project": project,
        "task_type": task_type,
        "size": size,
        "risk": risk,
        "route": route,
        "node": node,
        "error_type": error_type,
        "missing_subcontract": missing_sub,
        "retry_count": retry_count,
        "retry_levels_used": retry_levels,
        "final_outcome": final_outcome,
        "frequency": 1,  # patched below
        "root_cause": root_cause[:2000],
        "fix": fix[:2000],
        "prevention": prevention[:2000],
    }

    if verifier_report_link:
        entry["verifier_report_link"] = verifier_report_link
    if retro_link:
        entry["retro_link"] = retro_link
    entry["supervisor_events_count"] = sev_count
    entry["user_interrupts_count"] = user_int
    if elapsed_min is not None:
        entry["elapsed_min"] = elapsed_min
    if token_used is not None:
        entry["token_used"] = token_used
    if token_budget is not None:
        entry["token_budget"] = token_budget
    trap = (retro_notes or {}).get("trap_matched")
    if isinstance(trap, list) and trap:
        entry["trap_matched"] = [str(t)[:128] for t in trap[:32]]

    return entry


def _derive_frequency(entry: dict, existing: list[dict]) -> int:
    key = (entry["project"], entry["task_type"], entry["size"], entry["error_type"])
    new_sub = set(entry["missing_subcontract"])
    freq = 1
    for old in existing:
        if (
            old.get("project") == key[0]
            and old.get("task_type") == key[1]
            and old.get("size") == key[2]
            and old.get("error_type") == key[3]
        ):
            old_sub = set(old.get("missing_subcontract", []) or [])
            if not new_sub and not old_sub:
                freq += 1
            elif new_sub & old_sub:
                freq += 1
    return freq


def _acquire_lock(fh, retries: int = 3, delay: float = 5.0) -> None:
    last_exc: Optional[Exception] = None
    for _ in range(retries):
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError as exc:
            last_exc = exc
            time.sleep(delay)
    raise ArchiveWriteError(f"archive lock not acquired after {retries} retries: {last_exc}")


def write_archive_entry(
    task_id: str,
    task_board_path: str | Path,
    verifier_report_path: str | Path | None = None,
    supervisor_events_path: str | Path | None = None,
    retro_path: str | Path | None = None,
    retro_notes: Optional[dict] = None,
    archive_path: str | Path = DEFAULT_ARCHIVE_PATH,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    project: Optional[str] = None,
) -> dict:
    """Append one archive entry; returns the entry dict.

    Raises ArchiveWriteError on all failure modes (missing inputs, schema fail,
    lock fail). Never silently drops — per method3 § 7.3.
    """
    task_board_path = Path(task_board_path)
    archive_path = Path(archive_path)
    schema_path = Path(schema_path)
    vr_path = Path(verifier_report_path) if verifier_report_path else None
    sup_path = Path(supervisor_events_path) if supervisor_events_path else None

    task_board = _read_json(task_board_path, "task-board")
    verifier_report = _read_json(vr_path, "verifier-report") if vr_path else None
    schema = _read_json(schema_path, "schema")
    validator = Draft7Validator(schema)

    entry = _derive_entry(
        task_id=task_id,
        task_board=task_board,
        verifier_report=verifier_report,
        supervisor_events_path=sup_path,
        retro_notes=retro_notes,
        verifier_report_link=str(vr_path) if vr_path else None,
        retro_link=str(retro_path) if retro_path else None,
        explicit_project=project,
    )

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.touch(exist_ok=True)
    existing = _read_jsonl(archive_path)
    entry["frequency"] = _derive_frequency(entry, existing)

    errs = sorted(validator.iter_errors(entry), key=lambda e: e.path)
    if errs:
        detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:5])
        raise ArchiveWriteError(f"entry failed schema validation: {detail}")

    with archive_path.open("a", encoding="utf-8") as fh:
        _acquire_lock(fh)
        try:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fh.flush()
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass

    entry["_line_no"] = len(existing) + 1
    return entry
