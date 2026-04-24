"""Smoke: project_factory 可构造 workspace · 关键路径存在."""
from __future__ import annotations

from tests.shared.project_factory import ProjectWorkspace


def test_project_factory_creates_full_workspace(project_factory) -> None:
    p: ProjectWorkspace = project_factory("proj-smoke-1")
    assert p.pid == "proj-smoke-1"
    # 2-prd 4 件套
    assert p.charter_path.exists()
    assert p.plan_path.exists()
    assert p.requirements_path.exists()
    assert p.risk_path.exists()
    # TOGAF
    assert p.adr_path.exists()
    assert p.togaf_path.exists()
    # WBS
    assert p.wbs_path.exists()
    assert p.topology_path.exists()
    # KB / gate
    assert p.kb_session_path.exists()
    assert p.gate_state_path.exists()


def test_project_factory_isolates_multiple_pids(project_factory) -> None:
    foo = project_factory("proj-foo")
    bar = project_factory("proj-bar")
    assert foo.root != bar.root
    assert foo.pid != bar.pid


def test_project_workspace_single_pid(project_workspace, project_id: str) -> None:
    assert project_workspace.pid == project_id
    assert project_workspace.chart_dir.exists()
