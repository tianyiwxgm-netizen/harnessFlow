"""WP-α-11/12 · L2-04 SnapshotJob + RecoveryAttempt · Tier 1-4."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.checkpoint import (
    BlankRebuildRejected,
    DeadlineExceeded,
    NoCheckpoint,
    PIDMismatch,
    RecoveryAttempt,
    SnapshotJob,
    Tier,
    Trigger,
)
from app.l1_09.event_bus import EventBus, HaltGuard
from app.l1_09.event_bus.schemas import Event


@pytest.fixture
def bus_with_events(tmp_fs: Path):
    bus = EventBus(root=tmp_fs)
    pid = "prjckpt"
    for i in range(5):
        bus.append(Event(
            project_id=pid,
            type=f"L1-05:task_{i}",
            actor="executor",
            timestamp=datetime.now(UTC),
            payload={"n": i},
        ))
    return bus, pid, tmp_fs


# ===================== SnapshotJob (WP-α-11) =====================

class TestSnapshot:
    def test_TC_L204_001_take_snapshot_happy(self, bus_with_events) -> None:
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        result = job.take_snapshot(pid, trigger=Trigger.PERIODIC_TIMER)

        assert result.checkpoint_id.startswith("cp-")
        assert result.project_id == pid
        assert result.last_event_sequence == 5
        assert result.trigger == Trigger.PERIODIC_TIMER
        assert Path(root / result.snapshot_path).exists()
        assert result.duration_ms >= 0
        assert result.checksum and len(result.checksum) == 64

    def test_TC_L204_002_snapshot_checksum_verifiable(self, bus_with_events) -> None:
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        result = job.take_snapshot(pid)
        # 从文件重算 checksum
        with open(root / result.snapshot_path) as f:
            doc = json.load(f)
        import hashlib
        payload_bytes = json.dumps(doc["payload"], sort_keys=True).encode()
        actual = hashlib.sha256(payload_bytes).hexdigest()
        assert actual == result.checksum

    def test_TC_L204_003_snapshot_5_versions_rotated(self, bus_with_events) -> None:
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        # 做 7 次 snapshot
        for i in range(7):
            # 每次 append 1 event · 制造不同 seq
            bus.append(Event(
                project_id=pid,
                type="L1-05:extra",
                actor="executor",
                timestamp=datetime.now(UTC),
                payload={"i": i},
            ))
            job.take_snapshot(pid)
        ckpts = job.list_checkpoints(pid)
        assert len(ckpts) <= 5

    def test_TC_L204_004_snapshot_empty_project(self, tmp_fs: Path) -> None:
        """空 project · 仍应能 snapshot(last_seq=0)."""
        bus = EventBus(root=tmp_fs)
        # 创建 dir 但不 append
        (tmp_fs / "projects" / "prjempty").mkdir(parents=True)
        job = SnapshotJob(root=tmp_fs, event_bus=bus)
        result = job.take_snapshot("prjempty")
        assert result.last_event_sequence == 0


# ===================== RecoveryAttempt (WP-α-12) =====================

class TestRecoveryTier1:
    def test_TC_L204_010_tier1_latest_ok(self, bus_with_events) -> None:
        """最新 checkpoint 完整 · replay 尾段 · Tier 1."""
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        job.take_snapshot(pid)

        # 再 append 2 event（尾段）
        for _ in range(2):
            bus.append(Event(
                project_id=pid, type="L1-05:post", actor="executor",
                timestamp=datetime.now(UTC), payload={},
            ))

        ra = RecoveryAttempt(root=root, event_bus=bus)
        result = ra.recover_from_checkpoint(pid)

        assert result.tier == Tier.TIER_1
        assert result.hash_chain_valid
        assert result.events_replayed_count == 2


class TestRecoveryTier4:
    def test_TC_L204_020_tier4_no_data(self, tmp_fs: Path) -> None:
        """无 checkpoint + 无 events → Tier 4 拒绝."""
        bus = EventBus(root=tmp_fs)
        halt_guard = HaltGuard(tmp_fs / ".halt")
        ra = RecoveryAttempt(root=tmp_fs, event_bus=bus, halt_guard=halt_guard)
        with pytest.raises(NoCheckpoint):
            ra.recover_from_checkpoint("prjghost")

    def test_TC_L204_021_tier4_all_corrupt_refuses_fake_recovery(
        self, bus_with_events
    ) -> None:
        """checkpoint 坏 · events 不存在 → Tier 4 拒 · halt."""
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        job.take_snapshot(pid)

        # 损坏 checkpoint
        ckpts = job.list_checkpoints(pid)
        for ckpt in ckpts:
            ckpt.write_bytes(b'{"manifest": {"checksum": "bad"}, "payload": {}}')

        # 删 events
        events_path = root / "projects" / pid / "events.jsonl"
        events_path.unlink()

        halt_guard = HaltGuard(root / ".halt")
        ra = RecoveryAttempt(root=root, event_bus=bus, halt_guard=halt_guard)
        # events 不存在 · 但 ckpt 在 · 走 tier1 fail → tier2 skip(no events) → tier3 skip → tier4 blank_rebuild
        with pytest.raises((BlankRebuildRejected, NoCheckpoint)):
            ra.recover_from_checkpoint(pid)

        # halt marker 落盘
        assert halt_guard.is_halted()


class TestRecoveryTier2:
    def test_TC_L204_030_tier2_all_ckpts_corrupt_events_ok(
        self, bus_with_events
    ) -> None:
        """所有 checkpoint 坏 · events 完整 → Tier 2 全量回放."""
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        job.take_snapshot(pid)

        # 损坏所有 checkpoint
        ckpts = job.list_checkpoints(pid)
        for ckpt in ckpts:
            ckpt.write_bytes(b'{"manifest": {"checksum": "bad"}, "payload": {}}')

        ra = RecoveryAttempt(root=root, event_bus=bus)
        result = ra.recover_from_checkpoint(pid)
        assert result.tier == Tier.TIER_2
        assert result.hash_chain_valid
        assert result.events_replayed_count == 5


class TestRecoveryDeadline:
    def test_TC_L204_040_deadline_exceeded(self, bus_with_events, monkeypatch) -> None:
        """deadline 1ms · 必超 · 抛 DeadlineExceeded."""
        bus, pid, root = bus_with_events
        ra = RecoveryAttempt(root=root, event_bus=bus, deadline_s=0)
        import time
        # 推时间 · 强制超 deadline
        ra._deadline_s = -1  # 负数 · 立即超
        with pytest.raises(DeadlineExceeded):
            ra.recover_from_checkpoint(pid)


class TestPIDMismatch:
    def test_TC_L204_050_pid_mismatch_auto_fallback(self, bus_with_events) -> None:
        """checkpoint pid 不对 · 自动跳过降 Tier 2."""
        bus, pid, root = bus_with_events
        job = SnapshotJob(root=root, event_bus=bus)
        job.take_snapshot(pid)

        # 改 checkpoint pid
        ckpts = job.list_checkpoints(pid)
        for ckpt in ckpts:
            with open(ckpt) as f:
                doc = json.load(f)
            doc["manifest"]["project_id"] = "some-other-pid"
            ckpt.write_text(json.dumps(doc, sort_keys=True))

        ra = RecoveryAttempt(root=root, event_bus=bus)
        result = ra.recover_from_checkpoint(pid)
        # pid mismatch · 但 events 完整 · 降 Tier 2
        assert result.tier == Tier.TIER_2
