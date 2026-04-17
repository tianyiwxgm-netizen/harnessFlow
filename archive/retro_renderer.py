"""archive.retro_renderer — render the 11-item retro markdown from machine sources.

Source: method3 § 7.1 (11 items) + Phase 7 plan § 2 / § 5.

Public entry point:
    render_retro(task_id, task_board_path, verifier_report_path=None,
                 supervisor_events_path=None, retro_notes_path=None,
                 template_path=..., out_dir=...) -> str (path written)

Items 1-7 are derived from task-board + verifier-report + supervisor-events.
Items 8-11 are user-supplied via retro_notes_path (json); missing → `<待人工补充>`.

Idempotent append: same task_id called twice writes two `<!-- retro-<id>-<ts> -->`
blocks, never clobbers prior blocks.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_PATH = HERE.parent / "schemas" / "retro-template.md"
DEFAULT_OUT_DIR = HERE.parent / "retros"
TBD = "<待人工补充>"


def _read_json_optional(path: Optional[Path]) -> Optional[dict]:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl_optional(path: Optional[Path]) -> list[dict]:
    if path is None or not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _now_utc_iso() -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ts = now.isoformat().replace("+00:00", "Z")
    date = ts.split("T", 1)[0]
    return date, ts


# ---------------- field helpers (1..11) ----------------


def derive_1_dod_diff(task_board: dict, verifier_report: Optional[dict]) -> dict[str, str]:
    dod = task_board.get("dod_expression") or TBD
    rows: list[str] = []
    if verifier_report:
        for tier in ("existence", "behavior", "quality"):
            for e in verifier_report.get("evidence_chain", {}).get(tier, []) or []:
                prim = e.get("primitive") or e.get("nested_under") or "?"
                expected = e.get("expected", "-")
                actual = e.get("actual", "-")
                if e.get("insufficient"):
                    verdict = "INSUFFICIENT"
                elif e.get("passed") is True:
                    verdict = "PASS"
                elif e.get("passed") is False:
                    verdict = "FAIL"
                else:
                    verdict = "-"
                rows.append(f"| `{prim}` | `{expected}` | `{actual}` | {verdict} |")
        for failed in verifier_report.get("failed_conditions", []) or []:
            rows.append(f"| `{failed}` | - | - | FAIL |")
    if not rows:
        rows.append(f"| _（无 verifier_report）_ | - | - | {TBD} |")
    return {"dod_expression": dod, "dod_diff_table": "\n".join(rows)}


def derive_2_route_drift(
    task_board: dict, routing_events: list[dict]
) -> dict[str, str]:
    initial = task_board.get("initial_route_recommendation")
    actual = task_board.get("route_id") or task_board.get("route") or TBD
    drifted = "是" if (initial and initial != actual) else ("否" if initial else TBD)
    reasons: list[str] = []
    for ev in task_board.get("route_changes", []) or []:
        r = ev.get("reason") or ""
        if r:
            reasons.append(f"- {ev.get('from_route')} → {ev.get('to_route')}: {r}")
    for ev in routing_events:
        r = ev.get("reason") or ""
        if r:
            reasons.append(f"- {ev.get('from_route', '?')} → {ev.get('to_route', '?')}: {r}")
    snap_lines = [json.dumps(ev, ensure_ascii=False) for ev in routing_events[-10:]]
    return {
        "initial_route_recommendation": initial or TBD,
        "route": actual,
        "route_drifted": drifted,
        "route_drift_reason": "\n".join(reasons) if reasons else TBD,
        "routing_events_snapshot": "\n".join(snap_lines) if snap_lines else TBD,
    }


def derive_3_retry_breakdown(task_board: dict) -> dict[str, str]:
    retries = task_board.get("retries", []) or []
    counts = Counter((r.get("level") or "").upper() for r in retries)
    examples: dict[str, str] = {}
    for r in retries:
        lv = (r.get("level") or "").upper()
        if lv in ("L0", "L1", "L2", "L3") and lv not in examples:
            trig = r.get("trigger") or r.get("err_class") or "-"
            examples[lv] = trig
    out = {"retry_count": str(len(retries))}
    for lv in ("L0", "L1", "L2", "L3"):
        out[f"retry_{lv.lower()}_count"] = str(counts.get(lv, 0))
        out[f"retry_{lv.lower()}_example"] = examples.get(lv, "-")
    return out


def derive_4_verifier_fail(verifier_report: Optional[dict]) -> dict[str, str]:
    if not verifier_report:
        return {
            "verifier_fail_breakdown": TBD,
            "red_lines_triggered": TBD,
        }
    failed = verifier_report.get("failed_conditions", []) or []
    lines = []
    per_prim: Counter = Counter()
    for cond in failed:
        import re
        m = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)", cond)
        key = m.group(1) if m else cond[:60]
        per_prim[key] += 1
    for k, v in per_prim.most_common():
        lines.append(f"- `{k}`: {v} 次")
    if not lines:
        lines.append(f"- 无 FAIL 子契约（verdict={verifier_report.get('verdict', '-')}）")
    red = verifier_report.get("red_lines", []) or []
    return {
        "verifier_fail_breakdown": "\n".join(lines),
        "red_lines_triggered": ", ".join(red) if red else "无",
    }


def derive_5_user_interrupts(task_board: dict) -> dict[str, str]:
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
    return {
        "interrupt_drift_count": str(out["DRIFT"]),
        "interrupt_dod_gap_count": str(out["DOD_GAP"]),
        "interrupt_irreversible_count": str(out["IRREVERSIBLE"]),
        "interrupt_wasted_question_count": str(out["废问题"]),
    }


def derive_6_time(task_board: dict) -> dict[str, str]:
    tb = task_board.get("time_budget") or {}
    cap_sec = tb.get("cap_sec")
    elapsed_sec = tb.get("elapsed_sec")
    cap_min = round(cap_sec / 60.0, 2) if isinstance(cap_sec, (int, float)) else None
    used_min = round(elapsed_sec / 60.0, 2) if isinstance(elapsed_sec, (int, float)) else None
    if cap_min and used_min is not None:
        delta_pct = f"{(used_min - cap_min) / cap_min * 100:+.1f}%"
    else:
        delta_pct = TBD
    return {
        "time_budget_min": str(cap_min) if cap_min is not None else TBD,
        "elapsed_min": str(used_min) if used_min is not None else TBD,
        "time_delta_pct": delta_pct,
        "time_hotspot": TBD,
    }


def derive_7_cost(task_board: dict) -> dict[str, str]:
    tb = task_board.get("cost_budget") or {}
    used = tb.get("token_used")
    cap = tb.get("token_cap")
    cost_usd = tb.get("cost_usd")
    if isinstance(used, (int, float)) and isinstance(cap, (int, float)) and cap > 0:
        delta = f"{(used - cap) / cap * 100:+.1f}%"
    else:
        delta = TBD
    return {
        "token_budget": str(cap) if cap is not None else TBD,
        "token_used": str(used) if used is not None else TBD,
        "token_delta_pct": delta,
        "api_cost": f"${cost_usd}" if cost_usd is not None else TBD,
    }


def derive_8_traps(retro_notes: Optional[dict]) -> dict[str, str]:
    if retro_notes and retro_notes.get("new_traps"):
        lst = retro_notes["new_traps"]
        if isinstance(lst, list):
            return {"new_traps_found": "\n".join(f"- {t}" for t in lst)}
        return {"new_traps_found": str(lst)}
    return {"new_traps_found": TBD}


def derive_9_combos(retro_notes: Optional[dict]) -> dict[str, str]:
    if retro_notes and retro_notes.get("new_combinations"):
        lst = retro_notes["new_combinations"]
        if isinstance(lst, list):
            return {"new_effective_combinations": "\n".join(f"- {t}" for t in lst)}
        return {"new_effective_combinations": str(lst)}
    return {"new_effective_combinations": TBD}


def derive_10_evolution(retro_notes: Optional[dict], audit_report_link: Optional[str]) -> dict[str, str]:
    if retro_notes and retro_notes.get("evolution_suggestions"):
        val = retro_notes["evolution_suggestions"]
        if isinstance(val, list):
            suggestions = "\n".join(f"- {t}" for t in val)
        else:
            suggestions = str(val)
    else:
        suggestions = TBD
    return {
        "evolution_suggestions": suggestions,
        "audit_report_link": audit_report_link or TBD,
    }


def derive_11_next(retro_notes: Optional[dict], task_board: dict) -> dict[str, str]:
    rn = retro_notes or {}
    return {
        "next_time_recommendation": rn.get("next_recommendation") or TBD,
        "next_route_hint": rn.get("next_route_hint") or TBD,
        "next_must_verify": rn.get("next_must_verify") or TBD,
        "next_traps_to_avoid": rn.get("next_traps_to_avoid") or TBD,
    }


# ---------------- main render ----------------


def _collect_vars(
    task_id: str,
    task_board: dict,
    verifier_report: Optional[dict],
    routing_events: list[dict],
    retro_notes: Optional[dict],
    audit_report_link: Optional[str],
) -> dict[str, str]:
    date, ts = _now_utc_iso()
    time_fields = derive_6_time(task_board)
    cost_fields = derive_7_cost(task_board)
    vars_: dict[str, Any] = {
        "task_id": task_id,
        "ts": ts,
        "date": date,
        "project": task_board.get("project") or TBD,
        "task_type": task_board.get("task_type") or TBD,
        "size": task_board.get("size") or TBD,
        "risk": task_board.get("risk") or TBD,
        "route": task_board.get("route_id") or task_board.get("route") or TBD,
        "final_outcome": task_board.get("final_outcome") or TBD,
        "elapsed_min": time_fields["elapsed_min"],
        "token_used": cost_fields["token_used"],
        "token_budget": cost_fields["token_budget"],
        "verifier_report_link": task_board.get("verifier_report_link") or TBD,
    }
    vars_.update(derive_1_dod_diff(task_board, verifier_report))
    vars_.update(derive_2_route_drift(task_board, routing_events))
    vars_.update(derive_3_retry_breakdown(task_board))
    vars_.update(derive_4_verifier_fail(verifier_report))
    vars_.update(derive_5_user_interrupts(task_board))
    vars_.update(time_fields)
    vars_.update(cost_fields)
    vars_.update(derive_8_traps(retro_notes))
    vars_.update(derive_9_combos(retro_notes))
    vars_.update(derive_10_evolution(retro_notes, audit_report_link))
    vars_.update(derive_11_next(retro_notes, task_board))
    return {k: (v if isinstance(v, str) else str(v)) for k, v in vars_.items()}


def render_retro(
    task_id: str,
    task_board_path: str | Path,
    verifier_report_path: str | Path | None = None,
    supervisor_events_path: str | Path | None = None,
    routing_events_path: str | Path | None = None,
    retro_notes_path: str | Path | None = None,
    audit_report_link: Optional[str] = None,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
    out_dir: str | Path = DEFAULT_OUT_DIR,
) -> str:
    """Render an 11-item retro markdown block and append to retros/<task_id>.md.

    Returns the absolute path of the file written. Idempotent append — two calls
    produce two non-overlapping `<!-- retro-<id>-<ts> -->` blocks (different ts).
    """
    tb_path = Path(task_board_path)
    task_board = json.loads(tb_path.read_text(encoding="utf-8"))
    verifier_report = _read_json_optional(Path(verifier_report_path)) if verifier_report_path else None
    routing_events = _read_jsonl_optional(Path(routing_events_path)) if routing_events_path else []
    retro_notes = _read_json_optional(Path(retro_notes_path)) if retro_notes_path else None

    template = Path(template_path).read_text(encoding="utf-8")
    vars_ = _collect_vars(task_id, task_board, verifier_report, routing_events, retro_notes, audit_report_link)
    rendered = Template(template).safe_substitute(vars_)

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    out_path = out_dir_path / f"{task_id}.md"

    if out_path.exists() and out_path.stat().st_size > 0:
        sep = "\n\n---\n\n"
    else:
        sep = ""
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(sep + rendered + ("\n" if not rendered.endswith("\n") else ""))

    return str(out_path)
