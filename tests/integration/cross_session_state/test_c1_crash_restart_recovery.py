"""C1 · 崩溃 → 重启 → 状态恢复 · 5 TC.

L1-09 SnapshotJob 周期写检查点 · RecoveryAttempt 重启读检查点恢复.
模拟"崩溃" = 丢弃 process 内存(EventBus 实例)· 重新构造 EventBus + RecoveryAttempt.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.checkpoint.recovery import RecoveryAttempt
from app.l1_09.checkpoint.schemas import (
    NoCheckpoint,
    Tier,
    Trigger,
)
from app.l1_09.checkpoint.snapshot import SnapshotJob
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


def _write_n_events(bus: EventBus, project_id: str, n: int) -> None:
    """给 pid 写 n 条事件."""
    for i in range(n):
        evt = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"i": i},
            timestamp=datetime.now(UTC),
        )
        bus.append(evt)


class TestC1CrashRestartRecovery:
    """C1 · 崩溃恢复 · 5 TC."""

    def test_c1_01_take_snapshot_then_recover_tier1(
        self,
        real_event_bus: EventBus,
        snapshot_job: SnapshotJob,
        recovery_attempt: RecoveryAttempt,
        project_id: str,
    ) -> None:
        """C1.1: 写 5 事件 → take_snapshot → recover · TIER_1 · checkpoint 恢复."""
        _write_n_events(real_event_bus, project_id, 5)
        # take snapshot
        snap = snapshot_job.take_snapshot(project_id, trigger=Trigger.PERIODIC_TIMER)
        assert snap.last_event_sequence == 5
        # recovery
        rec = recovery_attempt.recover_from_checkpoint(project_id)
        assert rec.tier == Tier.TIER_1
        assert rec.last_event_sequence_replayed == 5
        assert rec.hash_chain_valid is True

    def test_c1_02_recover_after_crash_simulated(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C1.2: 模拟崩溃 — 写事件 + checkpoint 后销毁 EventBus 实例 · 重建 · recover.

        recovery 应能从持久化文件恢复 · 不依赖 process 内存.
        """
        # Session 1
        bus1 = EventBus(event_bus_root)
        _write_n_events(bus1, project_id, 4)
        snap_job1 = SnapshotJob(event_bus_root, event_bus=bus1)
        snap_job1.take_snapshot(project_id, trigger=Trigger.PERIODIC_TIMER)
        # 写两条 post-checkpoint
        _write_n_events(bus1, project_id, 2)
        # 模拟崩溃 — 销毁 bus1
        del bus1
        del snap_job1
        # Session 2 · 重启
        bus2 = EventBus(event_bus_root)
        rec_attempt = RecoveryAttempt(event_bus_root, event_bus=bus2)
        rec = rec_attempt.recover_from_checkpoint(project_id)
        # checkpoint 处 seq=4 · 后续 2 条尾段 replay
        assert rec.tier == Tier.TIER_1
        # last_event_sequence_replayed = 4 + 2 (post 2 条 replay)
        assert rec.last_event_sequence_replayed == 6

    def test_c1_03_no_checkpoint_no_events_raises(
        self,
        recovery_attempt: RecoveryAttempt,
        project_id: str,
    ) -> None:
        """C1.3: 全无数据 · raise NoCheckpoint(Tier 4 早退)."""
        with pytest.raises(NoCheckpoint):
            recovery_attempt.recover_from_checkpoint(project_id)

    def test_c1_04_tier2_full_replay_when_no_checkpoint(
        self,
        real_event_bus: EventBus,
        recovery_attempt: RecoveryAttempt,
        project_id: str,
    ) -> None:
        """C1.4: 有 events.jsonl 但无 checkpoint · TIER_2 全量回放."""
        _write_n_events(real_event_bus, project_id, 3)
        # 无 checkpoint
        rec = recovery_attempt.recover_from_checkpoint(project_id)
        assert rec.tier == Tier.TIER_2
        assert rec.events_replayed_count == 3
        assert rec.hash_chain_valid is True

    def test_c1_05_recover_preserves_pid_isolation(
        self,
        event_bus_root: Path,
    ) -> None:
        """C1.5: 跨 pid recovery · A 的恢复不影响 B 的 events 物理状态."""
        pid_a = "proj-c1-a"
        pid_b = "proj-c1-b"
        bus = EventBus(event_bus_root)
        _write_n_events(bus, pid_a, 3)
        _write_n_events(bus, pid_b, 5)
        snap = SnapshotJob(event_bus_root, event_bus=bus)
        snap.take_snapshot(pid_a, trigger=Trigger.PERIODIC_TIMER)
        snap.take_snapshot(pid_b, trigger=Trigger.PERIODIC_TIMER)
        rec_attempt = RecoveryAttempt(event_bus_root, event_bus=bus)
        # 恢复 A
        rec_a = rec_attempt.recover_from_checkpoint(pid_a)
        assert rec_a.tier == Tier.TIER_1
        assert rec_a.last_event_sequence_replayed == 3
        # 恢复 B
        rec_b = rec_attempt.recover_from_checkpoint(pid_b)
        assert rec_b.tier == Tier.TIER_1
        assert rec_b.last_event_sequence_replayed == 5
        # A/B 的物理 events 文件互不污染
        path_a = event_bus_root / "projects" / pid_a / "events.jsonl"
        path_b = event_bus_root / "projects" / pid_b / "events.jsonl"
        a_lines = path_a.read_bytes().splitlines()
        b_lines = path_b.read_bytes().splitlines()
        assert len(a_lines) == 3
        assert len(b_lines) == 5
