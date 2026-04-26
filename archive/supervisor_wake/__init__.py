"""Supervisor wake heuristics for harnessFlow PostToolUse hook chain."""
from .wake import (
    DEDUP_WINDOW_SEC,
    PULSE_CODES,
    TOOL_CALL_THRESHOLD,
    SupervisorWakeState,
    should_pulse,
)

__all__ = [
    "DEDUP_WINDOW_SEC",
    "PULSE_CODES",
    "TOOL_CALL_THRESHOLD",
    "SupervisorWakeState",
    "should_pulse",
]
