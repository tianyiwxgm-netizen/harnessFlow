"""cross_session_state 测试 fixtures · 真实 L1-09 + SnapshotJob/RecoveryAttempt.

继承 tests/shared 共享 fixture · 本 conftest 仅补:
    - snapshot_job: 真实 L2-04 SnapshotJob(root=event_bus_root · 同 bus 共根)
    - recovery_attempt: 真实 L2-04 RecoveryAttempt
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Re-export shared fixtures
from tests.shared.conftest import (  # noqa: F401
    audit_sink,
    callback_waiter,
    ckpt_root,
    delegate_stub,
    event_bus_root,
    fake_kb_repo,
    fake_llm,
    fake_reranker,
    fake_scope_checker,
    fake_skill_invoker,
    fake_tool_client,
    kb_root,
    lock_root,
    no_sleep,
    other_project_id,
    project_id,
    projects_root,
    real_event_bus,
    state_spy,
    tmp_root,
)

from app.l1_09.checkpoint.recovery import RecoveryAttempt
from app.l1_09.checkpoint.snapshot import SnapshotJob
from app.l1_09.event_bus.core import EventBus


@pytest.fixture
def snapshot_job(event_bus_root: Path, real_event_bus: EventBus) -> SnapshotJob:
    """真实 L2-04 SnapshotJob · root 与 real_event_bus 共根 · 不注 lock."""
    return SnapshotJob(event_bus_root, event_bus=real_event_bus)


@pytest.fixture
def recovery_attempt(event_bus_root: Path, real_event_bus: EventBus) -> RecoveryAttempt:
    """真实 L2-04 RecoveryAttempt · 共根."""
    return RecoveryAttempt(event_bus_root, event_bus=real_event_bus)
