"""WP-α-07 · L2-02 锁管理器 · acquire/release/is_locked 基础.

对齐 3-2 L2-02 TC-L109-L202-001~030 · 简化版本覆盖核心路径.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.l1_09.lock_manager import (
    LockManager,
    LockDeadlockRejected,
    LockInvalidHolder,
    LockInvalidResource,
    LockInvalidToken,
    LockShutdownRejected,
    LockTimeout,
    ResourceName,
    is_valid_holder,
    is_valid_resource,
)


# ===================== fixtures =====================

@pytest.fixture
def lm(tmp_fs: Path) -> LockManager:
    return LockManager(workdir=tmp_fs)


# ===================== schema =====================

class TestResourceName:
    """TC-L202-001~005 · 资源名解析."""

    def test_TC_L202_001_parse_index(self) -> None:
        rn = ResourceName.parse("_index")
        assert rn.project_id is None
        assert rn.resource_type == "_index"

    def test_TC_L202_002_parse_project_resource(self) -> None:
        rn = ResourceName.parse("foo:event_bus")
        assert rn.project_id == "foo"
        assert rn.resource_type == "event_bus"
        assert rn.sub_id is None

    def test_TC_L202_003_parse_wp_sub_id(self) -> None:
        rn = ResourceName.parse("foo:wp-042")
        assert rn.project_id == "foo"
        assert rn.resource_type == "wp"
        assert rn.sub_id == "042"

    def test_TC_L202_004_invalid_name_raises(self) -> None:
        with pytest.raises(ValueError):
            ResourceName.parse("UPPERCASE")

    def test_TC_L202_005_invalid_separator(self) -> None:
        with pytest.raises(ValueError):
            ResourceName.parse("foo/event_bus")

    def test_TC_L202_006_is_valid_resource_true(self) -> None:
        assert is_valid_resource("foo:event_bus")
        assert is_valid_resource("_index")
        assert is_valid_resource("proj-1:wp-042")

    def test_TC_L202_007_is_valid_resource_false(self) -> None:
        assert not is_valid_resource("")
        assert not is_valid_resource("UPPER:foo")
        assert not is_valid_resource("foo:")

    def test_TC_L202_008_is_valid_holder(self) -> None:
        assert is_valid_holder("L2-01:main_loop")
        assert is_valid_holder("L1-04:qc-loop:wp-042")
        assert not is_valid_holder("")
        assert not is_valid_holder("onlyonecolon")


# ===================== happy path =====================

class TestAcquireRelease:
    def test_TC_L202_010_uncontested_acquire_returns_token(self, lm: LockManager) -> None:
        """无竞争 · acquire 立即成功 · 返 LeaseToken."""
        token = lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=1000)
        assert token.resource == "foo:event_bus"
        assert token.holder == "L2-01:main"
        assert token.verify_sig()

    def test_TC_L202_011_release_after_acquire(self, lm: LockManager) -> None:
        token = lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=1000)
        ack = lm.release_lock(token)
        assert ack.idempotent is False
        assert ack.hold_duration_ms >= 0

    def test_TC_L202_012_idempotent_release(self, lm: LockManager) -> None:
        """同 token release 2 次 · 第 2 次 idempotent."""
        token = lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=1000)
        ack1 = lm.release_lock(token)
        assert ack1.idempotent is False
        ack2 = lm.release_lock(token)
        assert ack2.idempotent is True

    def test_TC_L202_013_is_locked_tracks_state(self, lm: LockManager) -> None:
        assert not lm.is_locked("foo:event_bus")
        token = lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=1000)
        assert lm.is_locked("foo:event_bus")
        lm.release_lock(token)
        assert not lm.is_locked("foo:event_bus")

    def test_TC_L202_014_list_held_returns_snapshot(self, lm: LockManager) -> None:
        t1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        t2 = lm.acquire_lock("foo:task_board", "L2-01:b", timeout_ms=1000)
        held = lm.list_held()
        resources = {h.resource for h in held}
        assert {"foo:event_bus", "foo:task_board"} <= resources
        lm.release_lock(t1)
        lm.release_lock(t2)


# ===================== 错误路径 =====================

class TestErrorCases:
    def test_TC_L202_020_invalid_resource_raises(self, lm: LockManager) -> None:
        with pytest.raises(LockInvalidResource):
            lm.acquire_lock("UPPERCASE", "L2-01:main", timeout_ms=1000)

    def test_TC_L202_021_invalid_holder_raises(self, lm: LockManager) -> None:
        with pytest.raises(LockInvalidHolder):
            lm.acquire_lock("foo:event_bus", "", timeout_ms=1000)

    def test_TC_L202_022_bad_timeout_raises(self, lm: LockManager) -> None:
        with pytest.raises(LockInvalidResource):
            lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=0)
        with pytest.raises(LockInvalidResource):
            lm.acquire_lock("foo:event_bus", "L2-01:main", timeout_ms=999_999)

    def test_TC_L202_023_invalid_token_raises(self, lm: LockManager) -> None:
        with pytest.raises(LockInvalidToken):
            lm.release_lock("not-a-token")  # type: ignore[arg-type]

    def test_TC_L202_024_whitelist_miss_raises(self, lm: LockManager) -> None:
        """非 wp / _index / 白名单 type 的资源 · invalid_resource."""
        with pytest.raises(LockInvalidResource):
            lm.acquire_lock("foo:unknown_type", "L2-01:main", timeout_ms=1000)


# ===================== 超时路径 =====================

class TestTimeout:
    def test_TC_L202_030_timeout_when_held(self, lm: LockManager) -> None:
        """A 持锁 · B acquire 超时."""
        t1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        start = time.time()
        with pytest.raises(LockTimeout):
            lm.acquire_lock("foo:event_bus", "L2-02:b", timeout_ms=200)
        elapsed = time.time() - start
        assert elapsed < 0.5  # 200ms + 调度开销 < 500ms
        lm.release_lock(t1)


# ===================== 并发场景 =====================

class TestConcurrency:
    def test_TC_L202_040_fifo_queue_order(self, lm: LockManager) -> None:
        """A 持锁 · B/C 依次等 · A release 后 · B 先获得（FIFO）."""
        t_a = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=3000)
        order = []

        def acquire(holder: str, tag: str) -> None:
            try:
                tok = lm.acquire_lock("foo:event_bus", holder, timeout_ms=2000)
                order.append(tag)
                lm.release_lock(tok)
            except Exception as e:  # noqa
                order.append(f"fail-{tag}-{type(e).__name__}")

        th_b = threading.Thread(target=acquire, args=("L2-01:b", "B"))
        th_c = threading.Thread(target=acquire, args=("L2-01:c", "C"))
        th_b.start()
        time.sleep(0.05)  # 确保 B 先入队
        th_c.start()
        time.sleep(0.05)

        lm.release_lock(t_a)
        th_b.join(timeout=3)
        th_c.join(timeout=3)
        assert order == ["B", "C"], f"FIFO violated: {order}"

    def test_TC_L202_041_transfer_after_release(self, lm: LockManager) -> None:
        """A release 后 · B 立即获得（< 100ms）."""
        t_a = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        events = []

        def acquire_b():
            tok = lm.acquire_lock("foo:event_bus", "L2-01:b", timeout_ms=2000)
            events.append(("got", time.time()))
            lm.release_lock(tok)

        th = threading.Thread(target=acquire_b)
        th.start()
        time.sleep(0.1)
        release_ts = time.time()
        lm.release_lock(t_a)
        th.join(timeout=3)
        assert len(events) == 1
        got_ts = events[0][1]
        assert got_ts - release_ts < 0.5  # 500ms 宽裕（CI）


# ===================== Deadlock detection =====================

class TestDeadlockDetection:
    def test_TC_L202_050_2cycle_deadlock_rejected(self, lm: LockManager) -> None:
        """A 持 R1 等 R2 · B 持 R2 等 R1 · B 第 2 次 acquire 应被拒（reject_self）."""
        t_a1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        t_b2 = lm.acquire_lock("foo:task_board", "L2-01:b", timeout_ms=1000)

        # A 想要 R2
        def a_wants_r2():
            try:
                tok = lm.acquire_lock("foo:task_board", "L2-01:a", timeout_ms=2000)
                lm.release_lock(tok)
            except Exception:
                pass

        th_a = threading.Thread(target=a_wants_r2)
        th_a.start()
        time.sleep(0.1)  # A 入等

        # B 想要 R1 · 应当被 deadlock rejected（A→B→A 环）
        with pytest.raises(LockDeadlockRejected):
            lm.acquire_lock("foo:event_bus", "L2-01:b", timeout_ms=1000)

        lm.release_lock(t_a1)
        lm.release_lock(t_b2)
        th_a.join(timeout=2)


# ===================== Shutdown =====================

class TestForceReleaseShutdown:
    def test_TC_L202_060_force_release_authorized(self, lm: LockManager) -> None:
        t1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        t2 = lm.acquire_lock("foo:task_board", "L2-01:b", timeout_ms=1000)
        report = lm.force_release_all(reason="shutdown", caller="L2-04-shutdown")
        assert report["released_count"] == 2

    def test_TC_L202_061_force_release_denied_nonauth(self, lm: LockManager) -> None:
        from app.l1_09.lock_manager import LockAccessDenied
        with pytest.raises(LockAccessDenied):
            lm.force_release_all(reason="shutdown", caller="L1-99:hacker")

    def test_TC_L202_062_shutdown_blocks_new_acquire(self, lm: LockManager) -> None:
        lm.force_release_all(reason="shutdown", caller="L2-04-shutdown")
        with pytest.raises(LockShutdownRejected):
            lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)

    def test_TC_L202_063_release_after_force_is_idempotent(self, lm: LockManager) -> None:
        t1 = lm.acquire_lock("foo:event_bus", "L2-01:a", timeout_ms=1000)
        lm.force_release_all(reason="shutdown", caller="L2-04-shutdown")
        ack = lm.release_lock(t1)
        assert ack.idempotent is True
