"""Slice A — 13_node_contract.yaml loader and runtime helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import yaml

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
