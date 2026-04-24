"""L2-02 · LockManager · 主类 · 对齐 3-1 §6.1-§6.2 / §8.

公共接口：
- acquire_lock(resource, holder, timeout_ms) -> LeaseToken
- release_lock(token) -> ReleaseAck
- is_locked(resource) -> bool
- list_held() -> list[LockStatus]
- force_release_all(reason, caller) -> {released_count, waiters_rejected_count, duration_ms}

WP-α-07 实现 · WP-α-08 扩展死锁 + janitor.
"""
from __future__ import annotations

import fcntl
import os
import threading
import time
from pathlib import Path

import ulid

from app.l1_09.lock_manager.fifo_queue import FIFOTicketQueue
from app.l1_09.lock_manager.schemas import (
    ALLOWED_RESOURCE_TYPES,
    LOCK_WAIT_TIMEOUT_MS_MAX,
    LeaseToken,
    Lock,
    LockAccessDenied,
    LockDeadlockRejected,
    LockError,
    LockInvalidHolder,
    LockInvalidResource,
    LockInvalidToken,
    LockShutdownRejected,
    LockState,
    LockStatus,
    LockTimeout,
    ReleaseAck,
    ResourceName,
    is_valid_holder,
    is_valid_resource,
)


# 允许调用 force_release_all 的 caller 前缀
_AUTHORIZED_FORCE_CALLERS: frozenset[str] = frozenset({
    "L2-04-shutdown",
    "L2-04:shutdown",
})


class LockManager:
    """进程内单例 · 跨进程用 flock 协调."""

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        (workdir / "tmp").mkdir(parents=True, exist_ok=True)
        (workdir / "projects").mkdir(parents=True, exist_ok=True)

        # 状态
        self._state_lock = threading.Lock()
        self._held_locks: dict[str, Lock] = {}  # resource -> Lock
        self._tokens: dict[str, Lock] = {}  # token_id -> Lock
        self._queues: dict[str, FIFOTicketQueue] = {}
        self._force_released_tokens: set[str] = set()
        self._shutting_down: bool = False

        # 死锁检测 (WP08) · 结构预留
        self._wait_for_graph: dict[str, set[str]] = {}  # holder -> holders it waits on

        # 事件回调（可选 · L2-01 注入）· WP-α-07 暂不强制
        self._event_callback = None

    # =========================================================
    # 事件 hook
    # =========================================================

    def set_event_callback(self, callback) -> None:
        """注入 L2-01 事件发送器 · 签名: (event_type: str, payload: dict) -> None."""
        self._event_callback = callback

    def _emit(self, event_type: str, payload: dict) -> None:
        if self._event_callback is None:
            return
        try:
            self._event_callback(event_type, payload)
        except Exception:
            # 事件失败不影响锁语义
            pass

    # =========================================================
    # 锁物理路径
    # =========================================================

    def _ensure_lock_file(self, resource_name: ResourceName) -> Path:
        path = resource_name.to_lock_path(self._workdir)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch(mode=0o644)
        return path

    def _get_queue(self, resource: str) -> FIFOTicketQueue:
        with self._state_lock:
            q = self._queues.get(resource)
            if q is None:
                q = FIFOTicketQueue()
                self._queues[resource] = q
            return q

    # =========================================================
    # 公共接口
    # =========================================================

    def acquire_lock(
        self,
        resource: str,
        holder: str,
        timeout_ms: int = 3000,
    ) -> LeaseToken:
        """§3.2 · 五阶段获取锁 · 失败 raise LockError 子类."""
        # Stage 0 · 参数校验
        if self._shutting_down:
            raise LockShutdownRejected(
                "system is shutting down",
                resource=resource,
                shutdown_at=int(time.time() * 1000),
            )
        if not is_valid_resource(resource):
            raise LockInvalidResource(
                f"invalid_resource: {resource!r}",
                resource=resource,
                reason="pattern_mismatch",
            )
        if not is_valid_holder(holder):
            raise LockInvalidHolder(
                f"invalid_holder: {holder!r}",
                holder=holder,
            )
        if not isinstance(timeout_ms, int) or timeout_ms <= 0 or timeout_ms > LOCK_WAIT_TIMEOUT_MS_MAX:
            raise LockInvalidResource(
                f"invalid_timeout_ms: {timeout_ms}",
                resource=resource,
                reason="timeout_out_of_range",
            )

        rn = ResourceName.parse(resource)
        # 白名单：除 _index 和 wp 外 · 必须 type 在白名单
        if rn.resource_type != "_index" and rn.resource_type != "wp":
            if rn.resource_type not in ALLOWED_RESOURCE_TYPES:
                raise LockInvalidResource(
                    f"resource_type not in whitelist: {rn.resource_type}",
                    resource=resource,
                    reason="whitelist_miss",
                )

        # Stage 1 · 进程内 thread_lock（快路径）· 同 resource 的 acquire 排队在同 condition 上
        queue = self._get_queue(resource)
        start_ts_ms = int(time.time() * 1000)
        deadline = start_ts_ms + timeout_ms
        ticket = queue.enqueue(start_ts_ms)

        # Stage 2 · 死锁检测（WP-α-08 · basic 存在 holder 冲突即检测）
        self._deadlock_check_or_raise(resource, holder, ticket, queue)

        # Stage 3 · FIFO 等
        try:
            with queue.condition:
                while True:
                    # 是否轮到自己
                    if self._try_acquire(rn, resource, holder, ticket, queue, start_ts_ms):
                        break
                    remaining = deadline - int(time.time() * 1000)
                    if remaining <= 0:
                        raise LockTimeout(
                            f"timeout after {timeout_ms}ms on {resource}",
                            resource=resource,
                            waited_ms=int(time.time() * 1000) - start_ts_ms,
                            current_holder=self._current_holder(resource),
                            queue_length=queue.size(),
                        )
                    queue.condition.wait(timeout=remaining / 1000.0)
        except LockError:
            queue.remove(ticket)
            raise
        except Exception:
            queue.remove(ticket)
            raise
        finally:
            # 成功或失败都清 wait graph 对应边
            self._clear_wait_edge(holder, resource)

        # 返回 token
        lock = self._held_locks[resource]
        return lock.token

    def _try_acquire(
        self,
        rn: ResourceName,
        resource: str,
        holder: str,
        ticket: int,
        queue: FIFOTicketQueue,
        start_ts_ms: int,
    ) -> bool:
        """判定是否可以真正取锁：队头 + 无其他 holder."""
        # 必须是队头才能尝试
        if not queue.is_head(ticket):
            return False
        with self._state_lock:
            if resource in self._held_locks:
                return False
        # flock EX（非阻塞尝试 · 失败直接返 False 等下轮）
        lock_path = self._ensure_lock_file(rn)
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        now_ms = int(time.time() * 1000)
        token_id = str(ulid.new())
        lock_id = str(ulid.new())
        token = LeaseToken.create(
            token_id=token_id,
            lock_id=lock_id,
            resource=resource,
            holder=holder,
            issued_at=now_ms,
            ttl_ms=rn.ttl_ms,
        )
        new_lock = Lock(
            lock_id=lock_id,
            resource=resource,
            holder=holder,
            acquired_at=now_ms,
            ttl_ms=rn.ttl_ms,
            state=LockState.HELD,
            fd=fd,
            token=token,
        )
        with self._state_lock:
            self._held_locks[resource] = new_lock
            self._tokens[token_id] = new_lock
        queue.dequeue(ticket)
        wait_ms = now_ms - start_ts_ms
        self._emit("L1-09:lock_acquired", {
            "lock_id": lock_id,
            "resource": resource,
            "holder": holder,
            "wait_ms": wait_ms,
        })
        return True

    def release_lock(self, token: LeaseToken) -> ReleaseAck:
        """§3.3 · 幂等 release."""
        if not isinstance(token, LeaseToken) or not token.verify_sig():
            raise LockInvalidToken("invalid_token: sig verify failed", token_id=getattr(token, "token_id", None))

        with self._state_lock:
            # force_released 过的 token · 幂等返
            if token.token_id in self._force_released_tokens:
                self._force_released_tokens.discard(token.token_id)
                return ReleaseAck(
                    released_at=int(time.time() * 1000),
                    hold_duration_ms=0,
                    waiters_signaled=0,
                    idempotent=True,
                )
            lock = self._tokens.get(token.token_id)
            if lock is None:
                # 已 release 过（幂等）· 对齐 §3.3 already_released
                return ReleaseAck(
                    released_at=int(time.time() * 1000),
                    hold_duration_ms=0,
                    waiters_signaled=0,
                    idempotent=True,
                )
            # 检查 resource 对齐
            if self._held_locks.get(lock.resource) is not lock:
                # token 对齐但 map 已被 force_release 等清除
                self._tokens.pop(token.token_id, None)
                return ReleaseAck(
                    released_at=int(time.time() * 1000),
                    hold_duration_ms=0,
                    waiters_signaled=0,
                    idempotent=True,
                )
            lock.state = LockState.RELEASING

        return self._do_release(lock)

    def _do_release(self, lock: Lock) -> ReleaseAck:
        now_ms = int(time.time() * 1000)
        hold_ms = now_ms - lock.acquired_at
        waiters_signaled = 0
        # 释放 flock
        if lock.fd is not None:
            try:
                fcntl.flock(lock.fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(lock.fd)
            except OSError:
                pass
        # 更新 map
        with self._state_lock:
            if self._held_locks.get(lock.resource) is lock:
                del self._held_locks[lock.resource]
            self._tokens.pop(lock.token.token_id, None)
            lock.state = LockState.FREE

        # 通知等待者
        queue = self._get_queue(lock.resource)
        with queue.condition:
            waiters_signaled = queue.size()
            queue.condition.notify_all()

        self._emit("L1-09:lock_released", {
            "lock_id": lock.lock_id,
            "resource": lock.resource,
            "hold_duration_ms": hold_ms,
        })
        return ReleaseAck(
            released_at=now_ms,
            hold_duration_ms=hold_ms,
            waiters_signaled=waiters_signaled,
            idempotent=False,
        )

    def is_locked(self, resource: str) -> bool:
        """§3.4 · 无副作用 · 查 map."""
        with self._state_lock:
            return resource in self._held_locks

    def list_held(self) -> list[LockStatus]:
        """§3.6 · 只读快照."""
        now_ms = int(time.time() * 1000)
        result: list[LockStatus] = []
        with self._state_lock:
            items = list(self._held_locks.items())
        for resource, lock in items:
            q = self._get_queue(resource)
            result.append(LockStatus(
                resource=resource,
                holder=lock.holder,
                acquired_at=lock.acquired_at,
                hold_duration_ms=now_ms - lock.acquired_at,
                ttl_ms=lock.ttl_ms,
                waiters_count=q.size(),
                waiters_oldest_wait_ms=q.oldest_wait_ms(now_ms),
            ))
        return result

    def _current_holder(self, resource: str) -> str | None:
        with self._state_lock:
            lock = self._held_locks.get(resource)
            return lock.holder if lock else None

    # =========================================================
    # 死锁检测（WP-α-08 · 在 acquire 尝试入队前调用）
    # =========================================================

    def _deadlock_check_or_raise(
        self,
        resource: str,
        holder: str,
        ticket: int,
        queue: FIFOTicketQueue,
    ) -> None:
        """若本次 acquire 构成死锁 · raise LockDeadlockRejected."""
        with self._state_lock:
            current = self._held_locks.get(resource)
            if current is None:
                return
            # 构造临时 wait-for：holder → current.holder
            self._wait_for_graph.setdefault(holder, set()).add(current.holder)
            # DFS 检环
            cycle = self._detect_cycle_from(holder)
            if cycle:
                # 撤销本次添加
                self._wait_for_graph[holder].discard(current.holder)
                if not self._wait_for_graph[holder]:
                    del self._wait_for_graph[holder]
                queue.remove(ticket)
                raise LockDeadlockRejected(
                    "deadlock_rejected",
                    cycle=cycle,
                    break_action="reject_self",
                )

    def _detect_cycle_from(self, start: str) -> list[str] | None:
        """DFS 从 start 找环 · 返环上节点列表 or None."""
        visited: set[str] = set()
        stack: list[str] = []

        def dfs(node: str) -> list[str] | None:
            if node in stack:
                # 找到环
                idx = stack.index(node)
                return stack[idx:] + [node]
            if node in visited:
                return None
            visited.add(node)
            stack.append(node)
            for nxt in self._wait_for_graph.get(node, set()):
                result = dfs(nxt)
                if result is not None:
                    return result
            stack.pop()
            return None

        return dfs(start)

    def _clear_wait_edge(self, holder: str, resource: str) -> None:
        """acquire 成功或失败后 · 清 wait_for_graph."""
        with self._state_lock:
            # 简化：清所有以 holder 为 key 的等待边（holder 不再等）
            self._wait_for_graph.pop(holder, None)

    # =========================================================
    # WP-α-08 · force_release_all · Janitor 支持
    # =========================================================

    def force_release_all(
        self,
        reason: str,
        caller: str = "L2-04-shutdown",
    ) -> dict:
        """§3.5 · 仅 L2-04 shutdown 专属.

        caller 必须在授权清单（默认 `L2-04-shutdown`）· 否则 LockAccessDenied.
        """
        if caller not in _AUTHORIZED_FORCE_CALLERS:
            raise LockAccessDenied(
                f"force_release_all rejected for caller={caller}",
                caller=caller,
            )
        valid_reasons = {"shutdown", "emergency_halt", "fatal_corruption"}
        if reason not in valid_reasons:
            raise LockError(f"invalid force_release reason: {reason}")

        start = int(time.time() * 1000)
        with self._state_lock:
            self._shutting_down = True
            locks = list(self._held_locks.values())
            self._held_locks.clear()
            self._tokens.clear()
            for lock in locks:
                self._force_released_tokens.add(lock.token.token_id)

        released_count = 0
        for lock in locks:
            if lock.fd is not None:
                try:
                    fcntl.flock(lock.fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                try:
                    os.close(lock.fd)
                except OSError:
                    pass
            released_count += 1
            self._emit("L1-09:force_release", {
                "lock_id": lock.lock_id,
                "resource": lock.resource,
                "holder": lock.holder,
                "reason": reason,
            })

        waiters_rejected = 0
        for q in list(self._queues.values()):
            with q.condition:
                waiters_rejected += q.size()
                q.condition.notify_all()

        duration_ms = int(time.time() * 1000) - start
        return {
            "released_count": released_count,
            "waiters_rejected_count": waiters_rejected,
            "duration_ms": duration_ms,
        }

    def reset_shutdown(self) -> None:
        """L2-04 重启后调用 · 恢复可 acquire."""
        with self._state_lock:
            self._shutting_down = False
            self._force_released_tokens.clear()


__all__ = ["LockManager"]
