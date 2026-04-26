"""Tests for pipelines.contract_loader."""
from __future__ import annotations

import pytest

from pipelines.contract_loader import load_contract, get_node_def, NodeDef


def test_load_contract_returns_13_nodes():
    contract = load_contract()
    assert len(contract.nodes) == 13


def test_load_contract_node_ids_are_n1_through_n13():
    contract = load_contract()
    ids = [n.node_id for n in contract.nodes]
    assert ids == [f"N{i}" for i in range(1, 14)]


def test_get_node_def_returns_n3_correctly():
    n3 = get_node_def("N3")
    assert isinstance(n3, NodeDef)
    assert n3.name == "目标分析+锁定"
    assert n3.phase == "initiating"
    assert "delivery_goal" in n3.dashboard_card_mapping


def test_get_node_def_unknown_id_raises():
    with pytest.raises(KeyError, match="N99"):
        get_node_def("N99")


def test_n13_is_dag_terminal_no_forward_edges():
    """N13 (closing/CLOSED) must have no forward edges — it's the DAG terminal."""
    n13 = get_node_def("N13")
    forward_edges = [e for e in n13.edges_out if e.get("kind") == "forward"]
    assert forward_edges == [], f"N13 should have no forward edges, got: {forward_edges}"
