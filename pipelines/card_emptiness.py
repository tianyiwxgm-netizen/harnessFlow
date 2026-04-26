"""Slice A — 6 dashboard cards emptiness detection (Q5=A 黄警示数据源)."""
from __future__ import annotations

from typing import Any

# Map: card_id → (responsible_node_id, node_name)
CARD_NODE_MAP: dict[str, tuple[str, str]] = {
    "delivery_goal":    ("N3", "目标分析+锁定"),
    "scope":            ("N8", "范围收口"),
    "project_library":  ("N2", "资料收集"),
    "tdd":              ("N6", "TDD 用例设计"),
    "supervision":      ("N12", "质量验证"),
    "wbs":              ("N9", "WBS 拆解"),
}


def _resolve(tb: dict, path: str) -> Any:
    cur: Any = tb
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return cur


def is_card_empty(card_id: str, task_board: dict) -> bool:
    """Return True if the card has no/insufficient data to display."""
    if card_id == "delivery_goal":
        v = _resolve(task_board, "_derived.delivery_goal.locked_goal")
        return not v
    if card_id == "scope":
        in_s = _resolve(task_board, "_derived.scope.in_scope") or []
        out_s = _resolve(task_board, "_derived.scope.out_of_scope") or []
        return len(in_s) == 0 and len(out_s) == 0
    if card_id == "project_library":
        docs = _resolve(task_board, "_derived.project_library.docs") or []
        repos = _resolve(task_board, "_derived.project_library.repos") or []
        process = _resolve(task_board, "_derived.project_library.process_docs") or []
        return (len(docs) + len(repos) + len(process)) < 3
    if card_id == "tdd":
        defs = _resolve(task_board, "tdd_cases.definitions") or []
        if not defs and isinstance(task_board.get("tdd_cases"), list):
            return len(task_board["tdd_cases"]) == 0
        return len(defs) == 0
    if card_id == "supervision":
        interventions = task_board.get("supervisor_interventions") or []
        red = task_board.get("red_lines") or []
        return len(interventions) == 0 and len(red) == 0
    if card_id == "wbs":
        wbs = _resolve(task_board, "_derived.wbs") or []
        return len(wbs) == 0
    raise KeyError(f"unknown card_id: {card_id}")


def derive_card_states(task_board: dict) -> list[dict]:
    """Return list of 6 entries: {card_id, is_empty, waiting_for_node, waiting_for_node_name}."""
    out = []
    for card_id, (node_id, node_name) in CARD_NODE_MAP.items():
        empty = is_card_empty(card_id, task_board)
        out.append({
            "card_id": card_id,
            "is_empty": empty,
            "waiting_for_node": node_id if empty else None,
            "waiting_for_node_name": node_name if empty else None,
        })
    return out
