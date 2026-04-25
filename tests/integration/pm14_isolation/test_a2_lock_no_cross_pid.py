"""A2 · L1-09 LockManager 互斥不跨 pid (IC-10/11) · 3 TC.

资源名格式 `<pid>:<type>` · pid_a:task_board 与 pid_b:task_board 是**不同物理资源**.
A 持锁不阻 B 同名 type · 完全独立.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.lock_manager.manager import LockManager


class TestA2LockNoCrossPid:
    """A2 · 锁互斥 PM-14 切片 · 3 TC."""

    def test_a2_01_a_holds_b_can_acquire_same_type(
        self,
        lock_root: Path,
        two_pids: tuple[str, str],
    ) -> None:
        """A2.1: A 持 task_board 锁 · B 同 type 能立即获取.

        资源名: pid_a:task_board / pid_b:task_board · 物理 .lock 路径不同.
        """
        pid_a, pid_b = two_pids
        lm = LockManager(lock_root)
        token_a = lm.acquire_lock(
            f"{pid_a}:task_board", "L1-04:verifier", timeout_ms=2000,
        )
        # B 应能立即拿(不被 A 阻塞)
        token_b = lm.acquire_lock(
            f"{pid_b}:task_board", "L1-04:verifier", timeout_ms=500,
        )
        assert token_a.resource == f"{pid_a}:task_board"
        assert token_b.resource == f"{pid_b}:task_board"
        assert lm.is_locked(f"{pid_a}:task_board") is True
        assert lm.is_locked(f"{pid_b}:task_board") is True
        # 释放
        lm.release_lock(token_a)
        lm.release_lock(token_b)

    def test_a2_02_a_release_does_not_affect_b(
        self,
        lock_root: Path,
        two_pids: tuple[str, str],
    ) -> None:
        """A2.2: A 释放 state 锁 · B 的 state 锁(同名)仍持有.

        PM-14: A 的 release 不能误清 B 的锁.
        """
        pid_a, pid_b = two_pids
        lm = LockManager(lock_root)
        token_a = lm.acquire_lock(
            f"{pid_a}:state", "L1-02:state_machine", timeout_ms=1000,
        )
        token_b = lm.acquire_lock(
            f"{pid_b}:state", "L1-02:state_machine", timeout_ms=1000,
        )
        # 释 A · B 不变
        lm.release_lock(token_a)
        assert lm.is_locked(f"{pid_a}:state") is False
        assert lm.is_locked(f"{pid_b}:state") is True
        # 收尾
        lm.release_lock(token_b)

    def test_a2_03_b_acquire_succeeds_when_a_blocking_same_pid_only(
        self,
        lock_root: Path,
        two_pids: tuple[str, str],
    ) -> None:
        """A2.3: A 内同 pid 已持 manifest · 第 2 次 same pid 取 will timeout · 但 B 同 type 能正常拿.

        强化跨 pid 锁不跨 + 同 pid 锁互斥的对偶事实.
        """
        from app.l1_09.lock_manager.schemas import LockTimeout

        pid_a, pid_b = two_pids
        lm = LockManager(lock_root)
        # A 先持
        token_a1 = lm.acquire_lock(
            f"{pid_a}:manifest", "L1-04:verifier", timeout_ms=1000,
        )
        # 同 pid 再要 · timeout(应该等不到)
        with pytest.raises(LockTimeout):
            lm.acquire_lock(
                f"{pid_a}:manifest", "L1-04:verifier-2", timeout_ms=200,
            )
        # 但 B 能立即拿同 type
        token_b = lm.acquire_lock(
            f"{pid_b}:manifest", "L1-04:verifier", timeout_ms=200,
        )
        assert token_b.resource == f"{pid_b}:manifest"
        # 收尾
        lm.release_lock(token_a1)
        lm.release_lock(token_b)
