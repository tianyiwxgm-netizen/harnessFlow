"""Fixtures for L1-03 WP01 (L2-02 topology manager) test suite.

Provides:
- `project_id`: standard test project id (ULID-shaped) satisfying PM-14 pattern.
- `event_bus`: in-memory ``EventBusStub``, reset per test.
- `skill_client`: in-memory ``SkillClientStub``.
- `manager`: fresh ``WBSTopologyManager`` bound to ``project_id`` and ``event_bus``.
- `make_wp`: factory for ``WorkPackage`` with sensible defaults (4-elements complete,
  ``effort_estimate=1.0``, ``state=READY``). Parameters override defaults.
- `linear_wbs_draft`: 3-WP linear chain (wp-001 -> wp-002 -> wp-003), acyclic, ready to load.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.common.skill_client_stub import SkillClientStub
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge, WorkPackage
from app.l1_03.topology.state_machine import State


@pytest.fixture
def project_id() -> str:
    return "pid-01HWBS000000000000000TEST"


@pytest.fixture
def event_bus() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def skill_client() -> SkillClientStub:
    return SkillClientStub()


@pytest.fixture
def manager(project_id: str, event_bus: EventBusStub) -> WBSTopologyManager:
    return WBSTopologyManager(project_id=project_id, event_bus=event_bus)


@pytest.fixture
def make_wp(project_id: str):
    """Factory producing a fully-filled WorkPackage for the standard test project."""

    def _make(
        wp_id: str,
        *,
        deps: list[str] | None = None,
        goal: str = "default goal",
        dod_expr_ref: str = "dod-default",
        effort_estimate: float = 1.0,
        recommended_skills: list[str] | None = None,
        state: State = State.READY,
        proj: str | None = None,
        **extra: Any,
    ) -> WorkPackage:
        return WorkPackage(
            wp_id=wp_id,
            project_id=proj if proj is not None else project_id,
            goal=goal,
            dod_expr_ref=dod_expr_ref,
            deps=list(deps or []),
            effort_estimate=effort_estimate,
            recommended_skills=list(recommended_skills or []),
            state=state,
            **extra,
        )

    return _make


@pytest.fixture
def linear_wbs_draft(project_id: str, make_wp) -> dict:
    """3-WP linear chain: wp-001 -> wp-002 -> wp-003. All READY, complete 4-elements."""
    wps = [
        make_wp("wp-001", deps=[], effort_estimate=2.0, goal="design schema"),
        make_wp("wp-002", deps=["wp-001"], effort_estimate=3.0, goal="implement core"),
        make_wp("wp-003", deps=["wp-002"], effort_estimate=1.5, goal="write tests"),
    ]
    edges = [
        DAGEdge(from_wp_id="wp-001", to_wp_id="wp-002"),
        DAGEdge(from_wp_id="wp-002", to_wp_id="wp-003"),
    ]
    return {
        "project_id": project_id,
        "wp_list": wps,
        "dag_edges": edges,
    }
