"""L1-06 L2-01 test fixtures · 3-2 §7 spec."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.tier_manager.schemas import ApplicableContext, EntryCandidate
from app.knowledge_base.tier_manager.tier_manager import TierManager


@pytest.fixture
def mock_project_id() -> str:
    return "p-fixture-001"


@pytest.fixture
def mock_session_id() -> str:
    return "s-fixture-aaa"


@pytest.fixture
def mock_clock() -> MagicMock:
    clk = MagicMock()
    clk.now.return_value = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return clk


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append = MagicMock(return_value={"event_id": "evt-001"})
    return bus


@pytest.fixture
def mock_fs(tmp_path: Path) -> Path:
    (tmp_path / "task-boards").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "global_kb" / "entries").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def make_entry_candidate():
    def _make(**overrides: Any) -> EntryCandidate:
        base: dict[str, Any] = {
            "id": "ent-" + (overrides.get("title") or "default"),
            "scope": "session",
            "kind": "pattern",
            "title": "default-title",
            "content": "some content >= 10 chars",
            "applicable_context": [
                ApplicableContext(
                    stage="S2_split", task_type="cli_tool", tech_stack=["python"]
                )
            ],
            "observed_count": 1,
            "first_observed_at": "2026-04-22T10:00:00Z",
            "last_observed_at": "2026-04-22T10:00:00Z",
            "source_links": [{"event_id": "e", "tick_id": "t"}],
        }
        base.update(overrides)
        return EntryCandidate(**base)

    return _make


@pytest.fixture
def corrupt_yaml(monkeypatch):
    """Monkey-patch yaml.safe_load to always raise YAMLError."""
    import yaml

    def _corrupt(_path: str) -> None:
        def bad(*_args, **_kw):
            raise yaml.YAMLError("fixture corruption")

        monkeypatch.setattr(yaml, "safe_load", bad)

    return _corrupt


@pytest.fixture
def fake_fs_with_entries(mock_fs: Path):
    """Seed N projects × M entries; `expired_count` rows per project use an old ts."""

    def _make(
        project_count: int = 1,
        entries_per_project: int = 10,
        expired_count: int = 0,
    ) -> Path:
        for i in range(project_count):
            pid = f"p-seed-{i:03d}"
            (mock_fs / "projects" / pid / "kb").mkdir(parents=True, exist_ok=True)
            (mock_fs / "projects" / pid / "kb" / ".tier-ready.flag").write_text(
                json.dumps({"project_id": pid})
            )
            sess_file = mock_fs / "task-boards" / pid / "s-aaa.kb.jsonl"
            sess_file.parent.mkdir(parents=True, exist_ok=True)
            with sess_file.open("w") as f:
                for j in range(entries_per_project):
                    ts = (
                        "2026-04-10T00:00:00+00:00"
                        if j < expired_count
                        else "2026-04-22T10:00:00+00:00"
                    )
                    f.write(
                        json.dumps(
                            {
                                "id": str(uuid.uuid4()),
                                "title": f"e-{j}",
                                "kind": "pattern",
                                "last_observed_at": ts,
                            }
                        )
                        + "\n"
                    )
        return mock_fs

    return _make


@pytest.fixture
def sut(
    mock_project_id: str,
    mock_session_id: str,
    mock_clock: MagicMock,
    mock_event_bus: MagicMock,
    mock_fs: Path,
) -> TierManager:
    """Subject Under Test · TierManager with injected collaborators."""
    tm = TierManager(
        clock=mock_clock,
        event_bus=mock_event_bus,
        fs_root=mock_fs,
        tier_layout_path=mock_fs / "configs" / "tier-layout.yaml",
    )
    # Default: the fixture project+session are known to tier_repo (positive tests).
    tm._tier_repo.set_tier_ready(mock_project_id, project=True, global_=True)
    tm._session_idx.register_session(mock_project_id, mock_session_id)
    return tm
