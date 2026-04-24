"""WP-α-08 · L2-02 死锁检测 + LockJanitor.

对齐 3-1 L2-02 §6.3 / §6.4 · 扩展 WP07 基础.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.l1_09.lock_manager import (
    LockDeadlockRejected,
    LockJanitor,
    LockManager,
)


@pytest.fixture
def lm(tmp_fs: Path) -> LockManager:
    return LockManager(workdir=tmp_fs)


class TestDeadlockDFS:
    def test_TC_L208_001_3cycle_deadlock(self, lm: LockManager) -> None:
        """A→B→C→A 3 环 · C 第 2 次 acquire 应被拒."""
        t_a_r1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        t_b_r2 = lm.acquire_lock("foo:task_board", "L2-01:b", timeout_ms=1000)
        t_c_r3 = lm.acquire_lock("foo:state", "L2-01:c", timeout_ms=1000)

        results: list[str] = []

        def a_wants_r2() -> None:
            try:
                tok = lm.acquire_lock("foo:task_board", "L2-01:a", timeout_ms=1500)
                lm.release_lock(tok)
                results.append("a-ok")
            except Exception as e:
                results.append(f"a-{type(e).__name__}")

        def b_wants_r3() -> None:
            try:
                tok = lm.acquire_lock("foo:state", "L2-01:b", timeout_ms=1500)
                lm.release_lock(tok)
                results.append("b-ok")
            except Exception as e:
                results.append(f"b-{type(e).__name__}")

        th_a = threading.Thread(target=a_wants_r2)
        th_b = threading.Thread(target=b_wants_r3)
        th_a.start()
        time.sleep(0.05)
        th_b.start()
        time.sleep(0.05)

        # C 想要 R1 · 完成环 A→B→C→A · 应被拒
        with pytest.raises(LockDeadlockRejected):
            lm.acquire_lock("foo:event_bus", "L2-01:c", timeout_ms=1000)

        # 清理
        lm.release_lock(t_a_r1)
        lm.release_lock(t_b_r2)
        lm.release_lock(t_c_r3)
        th_a.join(timeout=3)
        th_b.join(timeout=3)

    def test_TC_L208_002_no_deadlock_when_no_cycle(self, lm: LockManager) -> None:
        """A→B 单边 · 无环 · acquire 应能成功（等待）."""
        t_a = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)

        def b_wants_r1() -> None:
            tok = lm.acquire_lock("foo:event_bus", "L2-01:b", timeout_ms=2000)
            lm.release_lock(tok)

        th = threading.Thread(target=b_wants_r1)
        th.start()
        time.sleep(0.1)
        # B 在等 A · 无环 · B 应正常等
        lm.release_lock(t_a)
        th.join(timeout=3)
        assert not th.is_alive()


class TestJanitor:
    def test_TC_L208_010_janitor_reclaims_expired(self, lm: LockManager) -> None:
        """TTL 超 · janitor 自动回收."""
        # 人工造一个已过期的 lock
        token = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        # 短 TTL · manipulate 直接改 acquired_at
        with lm._state_lock:
            lock = lm._held_locks["foo:event_bus"]
            # 推回 10s 前（event_bus TTL=500ms + TTL_GRACE=500ms · 10s 远超）
            lock.acquired_at = int(time.time() * 1000) - 10_000

        janitor = LockJanitor(lm, interval_sec=0.1)
        reclaimed = janitor.scan_once()
        assert reclaimed == 1
        assert not lm.is_locked("foo:event_bus")

    def test_TC_L208_011_janitor_noop_fresh(self, lm: LockManager) -> None:
        """新鲜锁 · janitor 不回收."""
        token = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        janitor = LockJanitor(lm)
        assert janitor.scan_once() == 0
        assert lm.is_locked("foo:event_bus")
        lm.release_lock(token)

    def test_TC_L208_012_janitor_thread_start_stop(self, lm: LockManager) -> None:
        """janitor 能 start · stop 不卡."""
        janitor = LockJanitor(lm, interval_sec=0.05)
        janitor.start()
        time.sleep(0.2)  # 至少扫 2 次
        janitor.stop(timeout=1.0)
        assert janitor._thread is None or not janitor._thread.is_alive()

    def test_TC_L208_013_janitor_force_release_is_idempotent_for_owner(
        self, lm: LockManager
    ) -> None:
        """janitor 强制释放后 · 原 holder 再 release · 幂等."""
        token = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        # 造过期
        with lm._state_lock:
            lm._held_locks["foo:event_bus"].acquired_at = int(time.time() * 1000) - 10_000
        janitor = LockJanitor(lm)
        janitor.scan_once()
        # 原 holder 再 release · idempotent
        ack = lm.release_lock(token)
        assert ack.idempotent is True
