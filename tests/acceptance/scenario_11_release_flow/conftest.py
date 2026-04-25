"""Scenario 11 · release fixtures · 真实 L1-09 EventBus + 物理 release artifact 根.

acceptance-criteria 已通过 · deploy_script_executable + runbook_exists 双签.
"""
from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    """Scenario 11 · L1-09 严格 ^[a-z0-9_-]{1,40}$."""
    return "proj-acc11-release"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(event_bus_root)


@pytest.fixture
def release_root(tmp_path: Path, project_id: str) -> Path:
    """Release artifact 根 · projects/<pid>/release/"""
    root = tmp_path / "projects" / project_id / "release"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def deploy_script(release_root: Path) -> Path:
    """Deploy script (executable shell · 0o755)."""
    p = release_root / "deploy.sh"
    p.write_text(
        "#!/bin/bash\nset -e\necho 'deploy started'\necho 'OK'\n",
        encoding="utf-8",
    )
    # 0o755
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return p


@pytest.fixture
def runbook(release_root: Path) -> Path:
    """Runbook · 必含 prerequisites / steps / rollback 三段."""
    p = release_root / "runbook.md"
    p.write_text(
        """# Runbook
## prerequisites
- env vars set
## steps
1. backup
2. deploy
3. health check
## rollback
1. revert deploy
2. restore backup
""",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def changelog(release_root: Path) -> Path:
    p = release_root / "CHANGELOG.md"
    p.write_text("## v1.0.0\n- initial release\n", encoding="utf-8")
    return p


@pytest.fixture
def emit_release_event(real_event_bus: EventBus, project_id: str):
    """工厂 · emit release 相关 audit."""

    def _emit(event_type: str, payload: dict, actor: str = "main_loop") -> str:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit
