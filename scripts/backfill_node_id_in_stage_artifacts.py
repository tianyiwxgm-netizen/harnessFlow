"""Backfill stage_artifacts[].node_id for historical task-boards.

Derives 13-node outputs from existing task-board fields (state_history,
verifier_report, supervisor_interventions, commit_sha, retro_link, etc).

Idempotent: tasks already 13/13 node-tagged are skipped.

Usage:
    python scripts/backfill_node_id_in_stage_artifacts.py --dry-run
    python scripts/backfill_node_id_in_stage_artifacts.py
    python scripts/backfill_node_id_in_stage_artifacts.py --task-id <id>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NODE_IDS = [f"N{i}" for i in range(1, 14)]

NODE_META: dict[str, dict] = {
    "N1":  {"stage_id": "INIT",         "name": "任务采集 · 用户请求登记"},
    "N2":  {"stage_id": "CLARIFY",      "name": "资料收集 · 上下文与依赖参考"},
    "N3":  {"stage_id": "CLARIFY",      "name": "目标分析+锁定 · goal-anchor 写盘"},
    "N4":  {"stage_id": "ROUTE_SELECT", "name": "项目章程 · charter (or skipped)"},
    "N5":  {"stage_id": "PLAN",         "name": "PRD 编写 · plan-as-PRD 头部"},
    "N6":  {"stage_id": "PLAN",         "name": "TDD 用例设计"},
    "N7":  {"stage_id": "PLAN",         "name": "详细技术方案"},
    "N8":  {"stage_id": "PLAN",         "name": "范围 Scope · DoD primitives"},
    "N9":  {"stage_id": "PLAN",         "name": "WBS 工作包拆分"},
    "N10": {"stage_id": "VERIFY",       "name": "TDD 测试用例 · 实跑结果"},
    "N11": {"stage_id": "IMPL",         "name": "实施 Implementation · 代码与配置落地"},
    "N12": {"stage_id": "VERIFY",       "name": "监督 Monitoring · sidecar 事件流"},
    "N13": {"stage_id": "RETRO_CLOSE",  "name": "收口 Closure · retro + archive"},
}


def is_already_backfilled(tb: dict) -> bool:
    sas = tb.get("stage_artifacts") or []
    tagged = {s.get("node_id") for s in sas if s.get("node_id") in NODE_IDS}
    return len(tagged) == 13


def _state_ts(tb: dict, state_name: str) -> str | None:
    for entry in tb.get("state_history", []) or []:
        if entry.get("state") == state_name:
            return entry.get("timestamp")
    return None


def _first_ts(tb: dict, *fallback_states: str) -> str | None:
    for s in fallback_states:
        ts = _state_ts(tb, s)
        if ts:
            return ts
    return tb.get("created_at")


def derive_per_node_artifacts(tb: dict) -> list[dict]:
    """Build 13 stage_artifacts entries from existing task-board fields."""
    task_id = tb.get("task_id", "")
    goal = tb.get("goal_anchor") or {}
    route_id = tb.get("route_id") or tb.get("route") or "B"
    size = tb.get("size", "?")
    task_type = tb.get("task_type", "?")
    risk = tb.get("risk", "?")
    dod = tb.get("dod_expression", "")
    state_history = tb.get("state_history") or []
    verifier = tb.get("verifier_report") or {}
    sup_events = tb.get("supervisor_interventions") or []
    commit_sha = tb.get("commit_sha")
    retro_link = tb.get("retro_link")
    final_outcome = tb.get("final_outcome")
    archive_link = tb.get("archive_entry_link")
    artifacts = tb.get("artifacts") or []
    existing_sa = tb.get("stage_artifacts") or []

    initial_input = (
        tb.get("initial_user_input")
        or tb.get("task_description_initial")
        or tb.get("user_request")
        or goal.get("text", "")[:200]
    )

    n1 = {
        "node_id": "N1",
        "stage_id": NODE_META["N1"]["stage_id"],
        "name": NODE_META["N1"]["name"],
        "produced_at": _first_ts(tb, "INIT") or tb.get("created_at"),
        "outputs": {
            "user_request_text": initial_input or "(no initial input)",
            "task_id": task_id,
            "received_via": "/harnessFlow",
        },
    }

    n2 = {
        "node_id": "N2",
        "stage_id": NODE_META["N2"]["stage_id"],
        "name": NODE_META["N2"]["name"],
        "produced_at": _first_ts(tb, "CLARIFY", "INIT"),
        "outputs": {
            "internal_refs_read": [
                "harnessFlow.md (主 skill)",
                "state-machine.md",
                "delivery-checklist.md",
                "routing-matrix.md",
            ],
            "note": "backfilled from task-board metadata; original references not preserved",
        },
    }

    n3_outputs: dict = {
        "size": size,
        "task_type": task_type,
        "risk": risk,
    }
    if goal.get("text"):
        n3_outputs["goal_text"] = goal["text"][:500]
    if goal.get("hash"):
        n3_outputs["goal_anchor_hash_sha256"] = goal["hash"]
    if goal.get("claude_md_path"):
        n3_outputs["goal_anchor_block_path"] = goal["claude_md_path"]
    n3 = {
        "node_id": "N3",
        "stage_id": NODE_META["N3"]["stage_id"],
        "name": NODE_META["N3"]["name"],
        "produced_at": _first_ts(tb, "CLARIFY"),
        "outputs": n3_outputs,
    }

    if route_id in {"C", "E"}:
        n4_outputs: dict = {
            "charter_status": "lite",
            "rationale": f"{route_id} route — minimal charter from goal_anchor + plan",
            "route_decision": f"{route_id} route",
        }
    else:
        n4_outputs = {
            "charter_status": "SKIPPED_FOR_B_ROUTE",
            "rationale": f"{route_id} route ({route_id}) — Charter skipped (lite PRP承载)",
            "route_decision": f"{route_id}@auto-pick",
        }
    if tb.get("route_decision", {}).get("scores"):
        n4_outputs["scores"] = tb["route_decision"]["scores"]
    n4 = {
        "node_id": "N4",
        "stage_id": NODE_META["N4"]["stage_id"],
        "name": NODE_META["N4"]["name"],
        "produced_at": _first_ts(tb, "ROUTE_SELECT", "CLARIFY"),
        "outputs": n4_outputs,
    }

    plan_doc_path = None
    for sa in existing_sa:
        outs = sa.get("outputs") or {}
        if outs.get("plan_path"):
            plan_doc_path = outs["plan_path"]
            break
    n5 = {
        "node_id": "N5",
        "stage_id": NODE_META["N5"]["stage_id"],
        "name": NODE_META["N5"]["name"],
        "produced_at": _first_ts(tb, "PLAN"),
        "outputs": {
            "prd_doc_path": plan_doc_path or "(plan markdown not recorded)",
            "goal_statement": (goal.get("text") or initial_input or "")[:300],
            "tech_stack_inferred": ["from goal_anchor + dod_expression"],
        },
    }

    n6_funcs: list[str] = []
    if isinstance(verifier.get("evidence_checks"), list):
        for ec in verifier["evidence_checks"]:
            name = ec.get("name") or ec.get("primitive")
            if name:
                n6_funcs.append(name)
    n6 = {
        "node_id": "N6",
        "stage_id": NODE_META["N6"]["stage_id"],
        "name": NODE_META["N6"]["name"],
        "produced_at": _first_ts(tb, "PLAN"),
        "outputs": {
            "test_primitives_designed": n6_funcs[:10] or ["（未单独记录测试函数；见 dod_expression）"],
            "coverage_target": dod[:200] if dod else "see goal_anchor",
        },
    }

    n7 = {
        "node_id": "N7",
        "stage_id": NODE_META["N7"]["stage_id"],
        "name": NODE_META["N7"]["name"],
        "produced_at": _first_ts(tb, "PLAN"),
        "outputs": {
            "rationale": (tb.get("route_decision") or {}).get("rationale", "") or "(not recorded)",
            "dod_expression": dod or "(not recorded)",
        },
    }

    n8 = {
        "node_id": "N8",
        "stage_id": NODE_META["N8"]["stage_id"],
        "name": NODE_META["N8"]["name"],
        "produced_at": _first_ts(tb, "PLAN"),
        "outputs": {
            "dod_primitives_raw": dod or "(not recorded)",
            "size_class": size,
            "scope_inferred_from_goal": (goal.get("text") or "")[:300],
        },
    }

    state_count = len(state_history)
    wbs_estimate = max(1, state_count // 3) if state_count else 1
    n9 = {
        "node_id": "N9",
        "stage_id": NODE_META["N9"]["stage_id"],
        "name": NODE_META["N9"]["name"],
        "produced_at": _first_ts(tb, "PLAN"),
        "outputs": {
            "wbs_packages_estimated": wbs_estimate,
            "size_class": size,
            "state_transitions_count": state_count,
            "note": "backfilled estimate from state_history length (real WBS not preserved)",
        },
    }

    n10_overall = verifier.get("overall") or "(no verifier_report)"
    n10 = {
        "node_id": "N10",
        "stage_id": NODE_META["N10"]["stage_id"],
        "name": NODE_META["N10"]["name"],
        "produced_at": _first_ts(tb, "VERIFY"),
        "outputs": {
            "verifier_overall": n10_overall,
            "evidence_checks_count": len(verifier.get("evidence_checks") or []),
            "evidence_checks": (verifier.get("evidence_checks") or [])[:5],
        },
    }

    n11_outputs: dict = {
        "files_produced_count": len(artifacts),
        "artifacts_sample": [a.get("path") for a in artifacts[:10] if a.get("path")],
    }
    if commit_sha:
        n11_outputs["commit_sha"] = commit_sha
    n11 = {
        "node_id": "N11",
        "stage_id": NODE_META["N11"]["stage_id"],
        "name": NODE_META["N11"]["name"],
        "produced_at": _first_ts(tb, "IMPL"),
        "outputs": n11_outputs,
    }

    breakdown = {"INFO": 0, "WARN": 0, "BLOCK": 0}
    for ev in sup_events:
        lvl = ev.get("level")
        if lvl in breakdown:
            breakdown[lvl] += 1
    n12 = {
        "node_id": "N12",
        "stage_id": NODE_META["N12"]["stage_id"],
        "name": NODE_META["N12"]["name"],
        "produced_at": _first_ts(tb, "VERIFY", "IMPL"),
        "outputs": {
            "events_total": len(sup_events),
            "events_breakdown": breakdown,
            "red_lines_triggered": tb.get("red_lines") or [],
            "events_sample": [
                {"code": ev.get("code"), "message": (ev.get("message") or "")[:100]}
                for ev in sup_events[:5]
            ],
        },
    }

    n13_outputs: dict = {}
    if retro_link:
        n13_outputs["retro_link"] = retro_link
    if archive_link:
        n13_outputs["archive_entry_link"] = archive_link
    if final_outcome:
        n13_outputs["final_outcome"] = final_outcome
    n13_outputs["closed_at"] = tb.get("closed_at") or _first_ts(tb, "CLOSED", "RETRO_CLOSE")
    if not n13_outputs.get("retro_link") and not n13_outputs.get("final_outcome"):
        n13_outputs["note"] = "task not yet closed or retro_link missing"
    n13 = {
        "node_id": "N13",
        "stage_id": NODE_META["N13"]["stage_id"],
        "name": NODE_META["N13"]["name"],
        "produced_at": _first_ts(tb, "RETRO_CLOSE", "CLOSED"),
        "outputs": n13_outputs,
    }

    return [n1, n2, n3, n4, n5, n6, n7, n8, n9, n10, n11, n12, n13]


def apply_backfill(tb: dict) -> tuple[dict, int]:
    """Append missing-node entries to stage_artifacts; idempotent."""
    if is_already_backfilled(tb):
        return tb, 0
    existing_ids = {s.get("node_id") for s in (tb.get("stage_artifacts") or []) if s.get("node_id") in NODE_IDS}
    derived = derive_per_node_artifacts(tb)
    new_entries = [a for a in derived if a["node_id"] not in existing_ids]
    tb.setdefault("stage_artifacts", []).extend(new_entries)
    return tb, len(new_entries)


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill stage_artifacts.node_id for harnessFlow task-boards")
    ap.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    ap.add_argument("--task-id", help="Process only one task-board by stem")
    ap.add_argument("--task-boards-dir", default="task-boards", help="Directory containing task-boards")
    args = ap.parse_args()

    base = Path(args.task_boards_dir)
    if not base.exists():
        print(f"task-boards dir not found: {base}")
        return 2

    paths: list[Path] = sorted(base.glob("*.json"))
    paths.extend(sorted(base.glob("legacy/*.json")))
    paths.extend(sorted(base.glob("cross-project/*.json")))

    total_changed = 0
    total_skipped = 0
    for p in paths:
        if args.task_id and p.stem != args.task_id:
            continue
        try:
            tb = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"skip {p.name}: invalid JSON ({e})")
            continue
        new_tb, n_added = apply_backfill(tb)
        if n_added > 0:
            total_changed += 1
            if not args.dry_run:
                p.write_text(json.dumps(new_tb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tag = "DRY " if args.dry_run else ""
            print(f"{tag}{p.name}: +{n_added} node entries")
        else:
            total_skipped += 1
            print(f"{p.name}: skip (already 13/13 tagged)")

    print()
    print(f"total changed: {total_changed}")
    print(f"total skipped: {total_skipped}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
