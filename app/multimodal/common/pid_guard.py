"""PM-14 project_id cross-project guard."""

from __future__ import annotations

from app.multimodal.common.errors import L108Error


def assert_same_project(expected_pid: str, incoming_pid: str) -> None:
    """Raise invalid_project_id if incoming_pid differs or is empty."""
    if not incoming_pid or not incoming_pid.strip():
        raise L108Error("invalid_project_id", "project_id missing or empty")
    if incoming_pid != expected_pid:
        raise L108Error(
            "invalid_project_id",
            f"cross-project access refused: expected {expected_pid!r}, got {incoming_pid!r}",
        )
