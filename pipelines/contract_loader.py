"""Slice A — 13_node_contract.yaml loader and runtime helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

import yaml

from pipelines.gate_eval import GateEvalError, eval_predicate

CONTRACT_PATH = Path(__file__).resolve().parent / "13_node_contract.yaml"


class IOSpec(TypedDict):
    field: str
    must_exist: bool


@dataclass
class NodeDef:
    node_id: str
    step: int
    phase: str
    name: str
    code: str
    owner_skill: str
    layout: dict
    inputs_required: list[IOSpec]
    outputs_produced: list[IOSpec]
    writes_to_field: list[str]
    gate_predicate: dict
    supervisor_pulse_code: str
    dashboard_card_mapping: list[str] = field(default_factory=list)
    edges_out: list[dict] = field(default_factory=list)


@dataclass
class Contract:
    schema_version: str
    nodes: list[NodeDef]


@lru_cache(maxsize=1)
def load_contract() -> Contract:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        nodes = [NodeDef(**n) for n in raw["nodes"]]
    except TypeError as exc:
        raise RuntimeError(f"contract yaml schema drift: {exc}") from exc
    return Contract(schema_version=raw["schema_version"], nodes=nodes)


def get_node_def(node_id: str) -> NodeDef:
    for n in load_contract().nodes:
        if n.node_id == node_id:
            return n
    raise KeyError(f"unknown node_id: {node_id}")


def emit_pipeline_graph(task_board: dict) -> dict | None:
    """Emit pipeline_graph[] blueprint at ROUTE_SELECT → IMPL boundary.

    Returns None for size=XS (Route A 豁免)；otherwise returns
    {nodes:[...13...], edges:[...], emitted_at, schema_version}.
    """
    if task_board.get("size") == "XS":
        return None

    contract = load_contract()
    nodes_view = []
    all_edges: list[dict] = []
    for nd in contract.nodes:
        nodes_view.append({
            "node_id": nd.node_id,
            "step": nd.step,
            "phase": nd.phase,
            "name": nd.name,
            "owner_skill": nd.owner_skill,
            "layout": dict(nd.layout),
            "writes_to_field": list(nd.writes_to_field),
            "status": "pending",
            "started_at": None,
            "completed_at": None,
        })
        for e in nd.edges_out:
            all_edges.append({
                "from": nd.node_id,
                "to": e["to"],
                "kind": e.get("kind", "forward"),
                "label": e.get("label"),
            })

    return {
        "schema_version": contract.schema_version,
        "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nodes": nodes_view,
        "edges": all_edges,
    }


def _resolve_field(task_board: dict, field_path: str) -> Any:
    cur: Any = task_board
    for p in field_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def validate_node_io(
    task_board: dict, node_id: str, phase: str
) -> tuple[str, list[dict]]:
    """Slice A node-level enter/exit gate.

    phase: 'enter' or 'exit'
    returns: (verdict, violations[])
      verdict: 'OK' | 'BLOCK'
      violations: list of {field, reason}
    """
    nd = get_node_def(node_id)
    violations: list[dict] = []

    if phase == "enter":
        for req in nd.inputs_required:
            if not req.get("must_exist"):
                continue
            field_path = req["field"]
            val = _resolve_field(task_board, field_path)
            empty = val is None or val == "" or val == [] or val == {}
            if empty:
                violations.append({
                    "field": field_path,
                    "reason": "required input missing or empty",
                })
        return ("BLOCK" if violations else "OK", violations)

    if phase == "exit":
        for out in nd.outputs_produced:
            if not out.get("must_exist"):
                continue
            field_path = out["field"]
            val = _resolve_field(task_board, field_path)
            if val is None:
                violations.append({
                    "field": field_path,
                    "reason": "declared output not produced",
                })
        if not violations:
            try:
                ok = eval_predicate(nd.gate_predicate["expression"], task_board)
            except GateEvalError as e:
                ok = False
                violations.append({
                    "field": "_gate",
                    "reason": f"gate_predicate parse error: {e}",
                })
            if not ok and not violations:
                violations.append({
                    "field": "_gate",
                    "reason": f"gate_predicate failed: {nd.gate_predicate['expression']}",
                })
        on_fail = nd.gate_predicate.get("on_fail", "BLOCK")
        return (on_fail if violations else "OK", violations)

    raise ValueError(f"unknown phase: {phase}")
