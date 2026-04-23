"""Shared fixtures for L1-08 multimodal tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """Return /tmp/…/projects/p-001 with a sibling p-other-project for cross_project tests."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    pid_root = projects_dir / "p-001"
    pid_root.mkdir()
    # Sibling project so realpath of ../p-other-project/... resolves to a real dir
    (projects_dir / "p-other-project").mkdir()
    (projects_dir / "p-other-project" / "secret.md").write_text("secret")
    return pid_root
