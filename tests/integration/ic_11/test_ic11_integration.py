"""IC-11 · lock_release 集成测试 · 5 TC.

(WP04 任务表 IC-11 重映射 = L1-09 LockManager.release_lock + force_release)

覆盖:
    TC-1 正常释放: ack.idempotent=False · is_locked=False
    TC-2 双释 (重复 release): 第 2 次 ack.idempotent=True
    TC-3 token 签名错 (篡改 holder_sig) → LockInvalidToken
    TC-4 跨 holder 释放: 用别的 token 释放 → 错位 (返 idempotent / fail)
    TC-5 force_release_all 孤儿清理: 多 lock + force → 全释放
"""
from __future__ import annotations

import dataclasses

import pytest

from app.l1_09.lock_manager.schemas import (
    LeaseToken,
    LockAccessDenied,
    LockInvalidToken,
)


class TestIC11Integration:
    """IC-11 集成 · LockManager.release_lock + force_release_all."""

    # ---- TC-1 · 正常释放 ----
    def test_normal_release_returns_non_idempotent_ack(
        self, lock_manager, make_resource, make_holder,
    ) -> None:
        rs = make_resource("task_board")
        h = make_holder("L1-04", "verifier-A")

        token = lock_manager.acquire_lock(rs, h, timeout_ms=300)
        assert lock_manager.is_locked(rs) is True

        ack = lock_manager.release_lock(token)

        assert ack.idempotent is False
        assert ack.released_at > 0
        assert ack.hold_duration_ms >= 0
        assert lock_manager.is_locked(rs) is False

    # ---- TC-2 · 双释: 第 2 次 idempotent=True ----
    def test_double_release_is_idempotent(
        self, lock_manager, make_resource, make_holder,
    ) -> None:
        rs = make_resource("state")
        h = make_holder("L1-02", "stage_gate")

        token = lock_manager.acquire_lock(rs, h, timeout_ms=300)
        ack1 = lock_manager.release_lock(token)
        ack2 = lock_manager.release_lock(token)

        assert ack1.idempotent is False
        # IC-11 §3.3 幂等 release · 第 2 次 idempotent=True
        assert ack2.idempotent is True
        assert ack2.hold_duration_ms == 0  # 已不持

    # ---- TC-3 · 篡改 token 签名: raise LockInvalidToken ----
    def test_tampered_token_sig_rejected(
        self, lock_manager, make_resource, make_holder,
    ) -> None:
        rs = make_resource("kb")
        h = make_holder("L1-06", "promoter")
        token = lock_manager.acquire_lock(rs, h, timeout_ms=300)

        # 改 holder_sig · verify_sig() 失败
        bad_token = dataclasses.replace(token, holder_sig="badbadbadbadbad0")

        with pytest.raises(LockInvalidToken) as exc:
            lock_manager.release_lock(bad_token)
        assert "invalid_token" in str(exc.value).lower()

        # 真 token 仍可释放 · 不被污染
        ack = lock_manager.release_lock(token)
        assert ack.idempotent is False

    # ---- TC-4 · 用 H1 token 拿后 · 用伪 LeaseToken (相同字段) 不行 ----
    def test_release_with_unsigned_fake_token_rejected(
        self, lock_manager, make_resource, make_holder,
    ) -> None:
        rs = make_resource("manifest")
        h = make_holder("L1-04", "actor-1")
        real_token = lock_manager.acquire_lock(rs, h, timeout_ms=300)

        # 构造一个无效签名的伪 LeaseToken (仿冒 holder)
        fake = LeaseToken(
            token_id=real_token.token_id,
            lock_id=real_token.lock_id,
            resource=real_token.resource,
            holder="L1-04:malicious",  # 改 holder
            issued_at=real_token.issued_at,
            expires_at=real_token.expires_at,
            holder_sig=real_token.holder_sig,  # 旧 sig 与新 holder 不匹配
        )
        # verify_sig 失败 → LockInvalidToken
        with pytest.raises(LockInvalidToken):
            lock_manager.release_lock(fake)

        # 真 token 仍 OK
        lock_manager.release_lock(real_token)

    # ---- TC-5 · force_release_all 孤儿清理: shutdown caller 强释 ----
    def test_force_release_all_clears_orphan_locks(
        self, lock_manager, make_resource, make_holder,
    ) -> None:
        # 多 holder 同时持锁
        r1 = make_resource("task_board")
        r2 = make_resource("state")
        r3 = make_resource("manifest")
        h1 = make_holder("L1-01", "main_loop")
        h2 = make_holder("L1-02", "stage_gate")
        h3 = make_holder("L1-04", "verifier")

        lock_manager.acquire_lock(r1, h1, timeout_ms=300)
        lock_manager.acquire_lock(r2, h2, timeout_ms=300)
        lock_manager.acquire_lock(r3, h3, timeout_ms=300)
        # 验证 3 个 lock 全持
        assert len(lock_manager.list_held()) == 3

        # 非授权 caller · 拒绝
        with pytest.raises(LockAccessDenied):
            lock_manager.force_release_all(reason="shutdown", caller="some-rogue")

        # 授权 caller · 全释放
        result = lock_manager.force_release_all(
            reason="shutdown", caller="L2-04-shutdown",
        )
        assert result["released_count"] == 3
        assert len(lock_manager.list_held()) == 0
        # shutdown 后再 acquire 拒绝 (除非 reset_shutdown)
        lock_manager.reset_shutdown()
