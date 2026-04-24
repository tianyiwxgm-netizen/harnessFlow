"""WP-α-13 · L2-04 Shutdown + replay_events."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.checkpoint import (
    ShutdownOrchestrator,
    ShutdownState,
    SnapshotJob,
    Trigger,
    replay_events,
)
from app.l1_09.event_bus import EventBus
from app.l1_09.event_bus.schemas import Event
from app.l1_09.lock_manager import LockManager


@pytest.fixture
def setup(tmp_fs: Path):
    bus = EventBus(root=tmp_fs)
    pid = "prjshut"
    for i in range(3):
        bus.append(Event(
            project_id=pid, type=f"L1-05:t_{i}", actor="executor",
            timestamp=datetime.now(UTC), payload={"n": i},
        ))
    return bus, pid, tmp_fs


# ===================== Shutdown =====================

class TestShutdown:
    def test_TC_L204_060_clean_shutdown(self, setup) -> None:
        bus, pid, root = setup
        job = SnapshotJob(root=root, event_bus=bus)
        orch = ShutdownOrchestrator(
            snapshot_job=job, event_bus=bus,
        )
        token = orch.begin_shutdown(reason="manual_quit", active_projects=[pid])
        assert token.state == ShutdownState.ACKED
        assert token.reason == "manual_quit"
        assert token.flush_duration_ms >= 0
        assert pid in token.projects_snapshotted

    def test_TC_L204_061_reentrant_returns_same_token(self, setup) -> None:
        bus, pid, root = setup
        job = SnapshotJob(root=root, event_bus=bus)
        orch = ShutdownOrchestrator(snapshot_job=job, event_bus=bus)
        t1 = orch.begin_shutdown(reason="manual_quit", active_projects=[pid])
        t2 = orch.begin_shutdown(reason="sigint", active_projects=[pid])
        assert t1.token_id == t2.token_id

    def test_TC_L204_062_shutdown_with_lockmanager(self, setup) -> None:
        """shutdown 触发 lock_manager.force_release_all."""
        bus, pid, root = setup
        lm = LockManager(workdir=root)
        job = SnapshotJob(root=root, event_bus=bus, lock_manager=lm)
        orch = ShutdownOrchestrator(
            snapshot_job=job, event_bus=bus, lock_manager=lm,
        )
        # 预先 hold 一个锁
        token = lm.acquire_lock("foo:event_bus", "L2-01:test", timeout_ms=1000)
        orch.begin_shutdown(reason="sigterm", active_projects=[pid])
        # 应该被 force_release
        assert not lm.is_locked("foo:event_bus")

    def test_TC_L204_063_final_snapshot_degraded_ok(self, tmp_fs: Path) -> None:
        """pid 空（无事件）· shutdown 仍应 ACKED."""
        bus = EventBus(root=tmp_fs)
        job = SnapshotJob(root=tmp_fs, event_bus=bus)
        orch = ShutdownOrchestrator(snapshot_job=job, event_bus=bus)
        token = orch.begin_shutdown(reason="manual_quit", active_projects=[])
        assert token.state == ShutdownState.ACKED

    def test_TC_L204_064_is_shutting_down_false_after_ack(self, setup) -> None:
        bus, pid, root = setup
        job = SnapshotJob(root=root, event_bus=bus)
        orch = ShutdownOrchestrator(snapshot_job=job, event_bus=bus)
        orch.begin_shutdown(reason="manual_quit", active_projects=[pid])
        # ACKED 之后 · is_shutting_down 为 False
        assert not orch.is_shutting_down()


# ===================== replay_events (IC-10) =====================

class TestReplayEvents:
    def test_TC_L204_070_replay_all_ok(self, setup) -> None:
        bus, pid, root = setup
        result = replay_events(bus, pid)
        assert result.events_replayed == 3
        assert result.hash_chain_valid
        assert result.last_sequence_processed == 3

    def test_TC_L204_071_replay_from_seq(self, setup) -> None:
        bus, pid, root = setup
        result = replay_events(bus, pid, from_seq=2)
        # seq 2, 3 两条
        assert result.events_replayed == 2

    def test_TC_L204_072_replay_with_callback(self, setup) -> None:
        bus, pid, root = setup
        seen: list[int] = []
        replay_events(bus, pid, callback=lambda e: seen.append(e.get("sequence", -1)))
        assert seen == [1, 2, 3]

    def test_TC_L204_073_replay_corrupt_marked_invalid(self, setup) -> None:
        """人工损坏 events.jsonl · hash_chain_valid=False."""
        bus, pid, root = setup
        events_path = root / "projects" / pid / "events.jsonl"
        # 损坏第 2 行的 payload
        import json
        lines = events_path.read_bytes().splitlines()
        body = json.loads(lines[1])
        body["payload"] = {"TAMPERED": True}
        lines[1] = json.dumps(body, sort_keys=True).encode()
        events_path.write_bytes(b"\n".join(lines) + b"\n")

        result = replay_events(bus, pid, verify_hash=True)
        assert not result.hash_chain_valid
