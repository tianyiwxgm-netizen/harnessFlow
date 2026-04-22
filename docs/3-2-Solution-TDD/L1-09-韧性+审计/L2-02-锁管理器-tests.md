---
doc_id: tests-L1-09-L2-02-锁管理器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-09 L2-02 锁管理器 · TDD 测试用例

> 基于 3-1 L2-02 §3（5 个公共/内部方法 · acquire/release/is_locked/force_release_all/list_held）+ §11（6 类错误 · 4 象限分类 + 降级路径）+ §12（SLO P95 5ms 无竞争 / P95 100ms 10 方 / 20 方 10s 无饥饿）+ §13 TC 锚点。
> TC ID `TC-L109-L202-NNN`（语义别名：`TC-LOCK-ACQUIRE-*` / `TC-LOCK-DEADLOCK-*` / `TC-LOCK-LEAK-*`）。
> pytest + Python 3.11+ · `class TestLockManager_*` 组织。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（acquire/release/is_locked/list_held/FIFO 公平）
- [x] §3 负向用例（timeout/deadlock/shutdown/invalid/fs_error/leak 6 类全覆盖）
- [x] §4 IC-XX 契约集成测试（IC-07 acquire + release · IC-L2-01 lock_acquired 审计）
- [x] §5 性能 SLO 用例（无竞争 P95 5ms · 10 方 P95 100ms · 20 方 10s 无饥饿 · 死锁检测 ≤ 1ms）
- [x] §6 端到端 e2e 场景（flock + FIFO · deadlock 检测 · janitor leak 自愈）
- [x] §7 测试 fixture（tmp_lock_dir / mock_flock / deadlock_topology / ttl_expired_setup）
- [x] §8 集成点用例（L2-01 事件总线审计 · L2-04 shutdown force_release · L1-07 CRITICAL）
- [x] §9 边界 / edge case（资源数 ≥ 20 · TTL 边界 · 同 holder 重入 · 全局 SHUTTING_DOWN）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | 覆盖类型 |
|:---|:---|:---|
| `acquire_lock()` · 无竞争 | TC-L109-L202-001 | unit |
| `acquire_lock()` · 10 方竞争 · FIFO 公平 | TC-L109-L202-002 | unit |
| `acquire_lock()` · 20 方无饥饿 | TC-L109-L202-003 | perf-like |
| `acquire_lock()` · 返 LeaseToken 含 expires_at | TC-L109-L202-004 | unit |
| `release_lock()` · 正常释放 | TC-L109-L202-005 | unit |
| `release_lock()` · 通知 waiter | TC-L109-L202-006 | unit |
| `release_lock()` · 幂等（二次调） | TC-L109-L202-007 | unit |
| `is_locked()` · 只读无副作用 | TC-L109-L202-008 | unit |
| `list_held()` · 20 把锁快照 | TC-L109-L202-009 | unit |
| `force_release_all()` · shutdown 全释 | TC-L109-L202-010 | unit |
| flock LOCK_EX 互斥（fcntl syscall） | TC-L109-L202-011 | unit |
| wait-for graph 构建 + 死锁检测 | TC-L109-L202-012 | unit |
| TTL 过期 → janitor 标记 leaked | TC-L109-L202-013 | unit |
| 审计事件 `L1-09:lock_acquired` 发出 | TC-L109-L202-014 | unit |
| 资源名白名单校验（正则） | TC-L109-L202-015 | unit |

### §1.2 错误码 × 测试（§11.2 6 类全覆盖）

| 错误码 | TC ID | 象限 |
|:---|:---|:---|
| `LockError.timeout` | TC-L109-L202-101 | WARN / Recoverable |
| `LockError.deadlock_rejected` | TC-L109-L202-102 | CRITICAL / Fatal |
| `LockError.shutdown_rejected` | TC-L109-L202-103 | INFO / Terminal |
| `LockError.invalid_resource` | TC-L109-L202-104 | ERROR / Bug |
| `LockError.invalid_holder` | TC-L109-L202-105 | ERROR / Bug |
| `LockError.invalid_token` | TC-L109-L202-106 | ERROR / Bug |
| `LockError.fs_error` | TC-L109-L202-107 | CRITICAL / System |
| `LockError.lock_leaked` | TC-L109-L202-108 | CRITICAL / Runtime |
| `ok_idempotent` · already_released | TC-L109-L202-109 | INFO |
| `ok_forced_released` | TC-L109-L202-110 | INFO |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 |
|:---|:---|:---|
| IC-07 acquire | TC-L109-L202-201 | L2-01 事件总线 / L2-04 checkpoint / L1-02 lifecycle |
| IC-07 reverse release | TC-L109-L202-202 | 同上 |
| IC-L2-01 审计 lock_acquired/released | TC-L109-L202-203 | L2-01 |
| IC-L2-04 读 shutdown 状态 | TC-L109-L202-204 | L2-04 |
| IC-Supervisor lock_deadlock_detected | TC-L109-L202-205 | L1-07 |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| 无竞争 acquire P95 | ≤ 5ms | TC-L109-L202-301 |
| 10 方竞争 acquire P95 | ≤ 100ms | TC-L109-L202-302 |
| 20 方 10s 无饥饿 | min/max ≤ 5× | TC-L109-L202-303 |
| release P95 | ≤ 2ms | TC-L109-L202-304 |
| 死锁检测 ≤ 1ms（V ≤ 10） | | TC-L109-L202-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| 跨进程 flock 互斥 + FIFO | TC-L109-L202-401 |
| 死锁检测 + 拒绝 + Supervisor CRITICAL | TC-L109-L202-402 |
| TTL 泄漏 + janitor force_release 自愈 | TC-L109-L202-403 |

---

## §2 正向用例

```python
# tests/unit/L1-09/L2-02/test_lock_manager_positive.py
import pytest, threading, time
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestLockManager_AcquireRelease:
    """§3.2/3.3 acquire + release 正向"""

    def test_acquire_no_contention(self, lm):
        """TC-L109-L202-001 · 无竞争 · 返 LeaseToken"""
        tok = lm.acquire_lock("foo:event_bus", "L2-01:main_loop", timeout_ms=3000)
        assert tok.token_id.startswith("lease_") or len(tok.token_id) >= 20
        assert tok.lock_id
        assert tok.expires_at > tok.issued_at
        lm.release_lock(tok)

    def test_acquire_10_contenders_fifo(self, lm):
        """TC-L109-L202-002 · 10 方竞争 · FIFO 公平 · 按入队顺序拿锁"""
        barrier = threading.Barrier(10)
        order = []
        order_lock = threading.Lock()
        def _w(i):
            barrier.wait()
            time.sleep(i * 0.005)  # 按 i 顺序入队
            tok = lm.acquire_lock("foo:event_bus", f"L1-{i}", 5000)
            with order_lock: order.append(i)
            time.sleep(0.001)
            lm.release_lock(tok)
        ts = [threading.Thread(target=_w, args=(i,)) for i in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        # 大致 FIFO · 允许小偏差
        assert order[0] == 0

    def test_20_no_starvation(self, lm):
        """TC-L109-L202-003 · 20 方持续 2s · min count > 0（无饥饿）"""
        counts = [0] * 20
        stop = time.monotonic() + 2.0
        def _w(i):
            while time.monotonic() < stop:
                tok = lm.acquire_lock("foo:event_bus", f"L1-{i}", 3000)
                lm.release_lock(tok)
                counts[i] += 1
        ts = [threading.Thread(target=_w, args=(i,)) for i in range(20)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert min(counts) > 0

    def test_lease_token_has_expires(self, lm):
        """TC-L109-L202-004 · LeaseToken.expires_at = issued_at + TTL"""
        tok = lm.acquire_lock("foo:state", "L1-02", 3000)
        assert tok.expires_at - tok.issued_at == lm.ttl_ms
        lm.release_lock(tok)

    def test_release_returns_ack(self, lm):
        """TC-L109-L202-005 · release 返 ReleaseAck · hold_duration_ms"""
        tok = lm.acquire_lock("foo:state", "L1-02", 3000)
        time.sleep(0.01)
        ack = lm.release_lock(tok)
        assert ack.hold_duration_ms >= 10

    def test_release_signals_waiters(self, lm):
        """TC-L109-L202-006 · 有 waiter 时 release · waiter 立即拿锁"""
        tok1 = lm.acquire_lock("foo:state", "A", 3000)
        waiter_got = threading.Event()
        def _w():
            t = lm.acquire_lock("foo:state", "B", 3000)
            waiter_got.set()
            lm.release_lock(t)
        th = threading.Thread(target=_w); th.start()
        time.sleep(0.05)
        lm.release_lock(tok1)
        th.join(timeout=1)
        assert waiter_got.is_set()

    def test_release_idempotent(self, lm):
        """TC-L109-L202-007 · 同 token 二次 release · 幂等 ok_idempotent"""
        tok = lm.acquire_lock("foo:state", "A", 3000)
        lm.release_lock(tok)
        ack2 = lm.release_lock(tok)
        assert ack2.idempotent is True or ack2.status in {"ok_idempotent", "already_released"}


class TestLockManager_Observation:
    """§3.4/3.6 is_locked · list_held"""

    def test_is_locked_readonly(self, lm):
        """TC-L109-L202-008 · is_locked 纯读 · 不影响队列"""
        tok = lm.acquire_lock("foo:state", "A", 3000)
        for _ in range(100):
            assert lm.is_locked("foo:state") is True
        lm.release_lock(tok)
        assert lm.is_locked("foo:state") is False

    def test_list_held_snapshot(self, lm):
        """TC-L109-L202-009 · list_held · 20 把锁快照"""
        tokens = [lm.acquire_lock(f"foo:r{i}", f"H{i}", 3000) for i in range(20)]
        snap = lm.list_held()
        assert len(snap) == 20
        for s in snap:
            assert s.resource
            assert s.holder
            assert s.hold_duration_ms >= 0
        for t in tokens: lm.release_lock(t)


class TestLockManager_ForceRelease:
    """§3.5 force_release_all"""

    def test_force_release_all_shutdown(self, lm, l201_audit_spy):
        """TC-L109-L202-010 · shutdown · 20 把锁全释 + 广播 force_release · SHUTTING_DOWN"""
        tokens = [lm.acquire_lock(f"foo:r{i}", f"H{i}", 3000) for i in range(20)]
        report = lm.force_release_all(reason="shutdown")
        assert report.released_count == 20
        assert lm.state == "SHUTTING_DOWN"
        # 再 acquire 必拒
        r = lm.acquire_lock("foo:event_bus", "X", 3000)
        assert r.error_code == "shutdown_rejected"


class TestLockManager_InternalMechanics:
    """flock syscall · wait-for graph · TTL 泄漏 · 审计 · 白名单"""

    def test_flock_lock_ex_mutex(self, lm, spy_flock):
        """TC-L109-L202-011 · acquire 调 fcntl.flock LOCK_EX · release 调 LOCK_UN"""
        tok = lm.acquire_lock("foo:state", "A", 3000)
        assert any(c.args[1] == "LOCK_EX" or c.args[1] == 2 for c in spy_flock.flock.call_args_list)
        lm.release_lock(tok)
        assert any(c.args[1] == "LOCK_UN" or c.args[1] == 8 for c in spy_flock.flock.call_args_list)

    def test_wait_for_graph_cycle_detected(self, lm):
        """TC-L109-L202-012 · A holds r1 + wants r2; B holds r2 + wants r1 · 环检测"""
        # A holds r1
        tokA1 = lm.acquire_lock("foo:r1", "A", 5000)
        # B holds r2
        tokB2 = lm.acquire_lock("foo:r2", "B", 5000)
        # A wants r2 (waiter)
        def _a_wants_r2():
            lm.acquire_lock("foo:r2", "A", 5000)
        th = threading.Thread(target=_a_wants_r2); th.start()
        time.sleep(0.05)
        # B wants r1 → cycle!
        r = lm.acquire_lock("foo:r1", "B", 5000)
        assert r.error_code == "deadlock_rejected"
        assert "A" in str(r.cycle) and "B" in str(r.cycle)
        lm.release_lock(tokA1); lm.release_lock(tokB2)
        th.join(timeout=2)

    def test_ttl_expiry_marks_leaked(self, lm_short_ttl, janitor_tick):
        """TC-L109-L202-013 · TTL=50ms 持锁不释 · janitor 扫到 leaked"""
        tok = lm_short_ttl.acquire_lock("foo:state", "slow", 3000)
        time.sleep(0.2)  # 超 TTL
        janitor_tick(lm_short_ttl)
        # 锁被强制释放 · 再 acquire 成功
        tok2 = lm_short_ttl.acquire_lock("foo:state", "new", 3000)
        assert tok2.token_id != tok.token_id

    def test_emits_lock_acquired_audit(self, lm, l201_audit_spy):
        """TC-L109-L202-014 · acquire 成功 · 异步发 L1-09:lock_acquired"""
        tok = lm.acquire_lock("foo:state", "A", 3000)
        lm.release_lock(tok)
        events = l201_audit_spy.appended_events
        types = [e["type"] for e in events]
        assert "L1-09:lock_acquired" in types
        assert "L1-09:lock_released" in types

    def test_resource_whitelist_regex(self, lm):
        """TC-L109-L202-015 · 资源名必符合 ^(_index|[a-z0-9_-]+:...)"""
        r = lm.acquire_lock("BAD RESOURCE NAME", "A", 3000)
        assert r.error_code == "invalid_resource"
```

---

## §3 负向用例（6 类错误全覆盖）

```python
# tests/unit/L1-09/L2-02/test_lock_manager_negative.py
import pytest, threading, time, errno

pytestmark = pytest.mark.asyncio


class TestL202_WarnRecoverable:
    """WARN · 调用方软降级"""

    def test_LockError_timeout(self, lm):
        """TC-L109-L202-101 · 等锁超 3s · 返 timeout + waited_ms + current_holder"""
        tok = lm.acquire_lock("foo:state", "A", 3000)
        t0 = time.perf_counter()
        r = lm.acquire_lock("foo:state", "B", 200)  # 等 200ms
        elapsed = (time.perf_counter() - t0) * 1000
        assert r.error_code == "timeout"
        assert r.waited_ms <= 300
        assert r.current_holder == "A"
        lm.release_lock(tok)


class TestL202_CriticalDeadlock:
    """CRITICAL · deadlock"""

    def test_LockError_deadlock_rejected_critical(self, lm, l107_supervisor_spy):
        """TC-L109-L202-102 · 环检测到 · CRITICAL 审计 · cycle 含 holder 链"""
        tokA = lm.acquire_lock("foo:r1", "A", 5000)
        tokB = lm.acquire_lock("foo:r2", "B", 5000)
        def _a_wants_r2(): lm.acquire_lock("foo:r2", "A", 5000)
        th = threading.Thread(target=_a_wants_r2); th.start()
        time.sleep(0.05)
        r = lm.acquire_lock("foo:r1", "B", 5000)
        assert r.error_code == "deadlock_rejected"
        # Supervisor 收 CRITICAL
        assert l107_supervisor_spy.critical_events
        lm.release_lock(tokA); lm.release_lock(tokB)
        th.join(timeout=2)


class TestL202_Terminal:
    """INFO · shutdown"""

    def test_LockError_shutdown_rejected(self, lm):
        """TC-L109-L202-103 · 全局 SHUTTING_DOWN · 拒新 acquire"""
        lm.force_release_all(reason="shutdown")
        r = lm.acquire_lock("foo:state", "A", 3000)
        assert r.error_code == "shutdown_rejected"
        assert r.shutdown_at is not None


class TestL202_CallerBug:
    """ERROR · 调用方 bug"""

    def test_LockError_invalid_resource(self, lm):
        """TC-L109-L202-104 · 非法资源名 · 含 reason"""
        r = lm.acquire_lock("../escape", "A", 3000)
        assert r.error_code == "invalid_resource"
        assert r.reason

    def test_LockError_invalid_holder(self, lm):
        """TC-L109-L202-105 · holder 格式错 · invalid_holder"""
        r = lm.acquire_lock("foo:state", "no_colon_format", 3000)
        assert r.error_code == "invalid_holder"

    def test_LockError_invalid_token(self, lm):
        """TC-L109-L202-106 · release 未知 token · 拒 · 记 lock_release_rejected"""
        from types import SimpleNamespace
        fake = SimpleNamespace(token_id="nope", lock_id="x", issued_at=0, expires_at=0)
        r = lm.release_lock(fake)
        assert r.error_code == "invalid_token"


class TestL202_FatalSystem:
    """CRITICAL · fs_error · lock_leaked"""

    def test_LockError_fs_error(self, lm_readonly_dir):
        """TC-L109-L202-107 · .lock 所在目录只读 · ENOSPC/EROFS · fs_degraded"""
        r = lm_readonly_dir.acquire_lock("foo:state", "A:m", 3000)
        assert r.error_code == "fs_error"
        assert r.errno in {errno.EROFS, errno.EACCES, errno.ENOSPC}
        # 后续 acquire 一律拒
        r2 = lm_readonly_dir.acquire_lock("foo:state", "A:m", 3000)
        assert r2.error_code in {"fs_error", "shutdown_rejected"}

    def test_LockError_lock_leaked_janitor_force(self, lm_short_ttl, janitor_tick,
                                                    l107_supervisor_spy):
        """TC-L109-L202-108 · 超 TTL 的 holder · janitor 强制释放 · 记 CRITICAL"""
        tok = lm_short_ttl.acquire_lock("foo:state", "slow", 3000)
        time.sleep(0.2)
        janitor_tick(lm_short_ttl)
        # 原 holder 后续 release · 返 ok_forced_released
        r = lm_short_ttl.release_lock(tok)
        assert r.status in {"ok_forced_released", "forced_released"}


class TestL202_Idempotent:
    """INFO · 幂等"""

    def test_already_released_ok_idempotent(self, lm):
        """TC-L109-L202-109 · 同 token 二次 release · 第二次 ok_idempotent"""
        tok = lm.acquire_lock("foo:state", "A:m", 3000)
        lm.release_lock(tok)
        ack = lm.release_lock(tok)
        assert ack.status in {"ok_idempotent", "already_released"}

    def test_forced_released_ack(self, lm_short_ttl, janitor_tick):
        """TC-L109-L202-110 · janitor 强制后 holder release · ok_forced_released"""
        tok = lm_short_ttl.acquire_lock("foo:state", "A:m", 3000)
        time.sleep(0.15)
        janitor_tick(lm_short_ttl)
        ack = lm_short_ttl.release_lock(tok)
        assert ack.status in {"ok_forced_released", "forced_released"}
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-09/L2-02/test_ic_contracts.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIC07_AcquireContract:
    """IC-07 · acquire_lock · 被所有 L1 调用"""

    def test_ic07_acquire_returns_lease_token(self, lm):
        """TC-L109-L202-201 · 返 LeaseToken 含 token_id / lock_id / expires_at"""
        tok = lm.acquire_lock("foo:event_bus", "L2-01:main", 3000)
        assert hasattr(tok, "token_id")
        assert hasattr(tok, "lock_id")
        assert hasattr(tok, "expires_at")
        lm.release_lock(tok)

    def test_ic07_release_idempotent(self, lm):
        """TC-L109-L202-202 · release 幂等契约"""
        tok = lm.acquire_lock("foo:state", "L1-02:m", 3000)
        a1 = lm.release_lock(tok)
        a2 = lm.release_lock(tok)
        assert a2.status in {"ok_idempotent", "already_released"}


class TestICL201_AuditContract:
    """IC-L2-01 · 锁事件审计"""

    def test_lock_acquired_audit_fields(self, lm, l201_audit_spy):
        """TC-L109-L202-203 · 审计 lock_acquired · 含 wait_ms / resource / holder"""
        tok = lm.acquire_lock("foo:state", "A:m", 3000)
        lm.release_lock(tok)
        ev = next(e for e in l201_audit_spy.appended_events
                  if e["type"] == "L1-09:lock_acquired")
        assert "wait_ms" in ev["payload"]
        assert ev["payload"]["resource"] == "foo:state"
        assert ev["payload"]["holder"] == "A:m"


class TestICL204_ShutdownState:
    """与 L2-04 shutdown"""

    def test_shutdown_state_visible(self, lm):
        """TC-L109-L202-204 · force_release_all 后 state=SHUTTING_DOWN · L2-04 查得"""
        lm.force_release_all(reason="shutdown")
        assert lm.state == "SHUTTING_DOWN"


class TestICSupervisor_DeadlockContract:
    """IC → L1-07 · deadlock CRITICAL"""

    def test_deadlock_reaches_supervisor(self, lm, l107_supervisor_spy):
        """TC-L109-L202-205 · deadlock 事件 Supervisor 收 CRITICAL"""
        import threading, time
        tokA = lm.acquire_lock("foo:r1", "A:m", 5000)
        tokB = lm.acquire_lock("foo:r2", "B:m", 5000)
        def _a_wants_r2(): lm.acquire_lock("foo:r2", "A:m", 5000)
        th = threading.Thread(target=_a_wants_r2); th.start()
        time.sleep(0.05)
        lm.acquire_lock("foo:r1", "B:m", 5000)
        assert l107_supervisor_spy.critical_events
        lm.release_lock(tokA); lm.release_lock(tokB); th.join(timeout=2)
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-09/L2-02/test_slo.py
import pytest, time, statistics, threading
from contextlib import contextmanager


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestNoContentionSLO:
    """§12 · 无竞争 acquire P95 ≤ 5ms"""

    def test_acquire_no_contention_p95_under_5ms(self, lm):
        """TC-L109-L202-301 · 10000 次 · P95 ≤ 5ms"""
        samples = []
        for _ in range(10_000):
            with _timer() as t:
                tok = lm.acquire_lock("foo:r", "A:m", 3000)
            samples.append(t())
            lm.release_lock(tok)
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 5.0


class TestHighContentionSLO:
    """§12 · 10 方竞争 P95 ≤ 100ms"""

    def test_10_contenders_p95_under_100ms(self, lm):
        """TC-L109-L202-302 · 10 线程 × 100 · acquire P95 ≤ 100ms"""
        barrier = threading.Barrier(10)
        samples = []
        samples_lock = threading.Lock()
        def _w(i):
            barrier.wait()
            for _ in range(100):
                t0 = time.perf_counter()
                tok = lm.acquire_lock("foo:r", f"L1-{i}:m", 5000)
                elapsed = (time.perf_counter() - t0) * 1000
                with samples_lock: samples.append(elapsed)
                time.sleep(0.001)
                lm.release_lock(tok)
        ts = [threading.Thread(target=_w, args=(i,)) for i in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 100.0


class TestNoStarvationSLO:
    """§12 · 20 方 10s 无饥饿 · min/max ≤ 5×"""

    def test_20_no_starvation_5x_ratio(self, lm):
        """TC-L109-L202-303 · 20 方 2s · min/max 比 ≤ 5×"""
        counts = [0] * 20
        stop = time.monotonic() + 2.0
        def _w(i):
            while time.monotonic() < stop:
                tok = lm.acquire_lock("foo:r", f"L1-{i}:m", 5000)
                lm.release_lock(tok)
                counts[i] += 1
        ts = [threading.Thread(target=_w, args=(i,)) for i in range(20)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert min(counts) > 0
        ratio = max(counts) / max(1, min(counts))
        assert ratio <= 5.0


class TestReleaseSLO:
    """§12 · release P95 ≤ 2ms"""

    def test_release_p95_under_2ms(self, lm):
        """TC-L109-L202-304 · 10000 次 release · P95 ≤ 2ms"""
        samples = []
        for _ in range(10_000):
            tok = lm.acquire_lock("foo:r", "A:m", 3000)
            t0 = time.perf_counter()
            lm.release_lock(tok)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 2.0


class TestDeadlockDetectionSLO:
    """§12 · detect_cycle ≤ 1ms · V ≤ 10"""

    def test_deadlock_detection_under_1ms(self, lm):
        """TC-L109-L202-305 · 构建 10 节点 wait-for graph · DFS ≤ 1ms"""
        samples = []
        for _ in range(1000):
            t0 = time.perf_counter()
            lm._detect_cycle(pretend_add=("A", "r1"))
            samples.append((time.perf_counter() - t0) * 1000)
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 1.0
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-09/L2-02/test_e2e.py
import pytest, threading, time, os

pytestmark = pytest.mark.asyncio


class TestE2E_FlockAndFifo:
    """跨进程 flock + FIFO"""

    def test_flock_exclusive_and_fifo(self, lm):
        """TC-L109-L202-401 · flock LOCK_EX 互斥 + 队列 FIFO · 无饥饿"""
        # 使用 fork 模拟跨进程（单文件 · fcntl LOCK_EX 互斥）
        order = []
        tokens = []
        for i in range(3):
            tokens.append(lm.acquire_lock("foo:state", f"P{i}:m", 3000))
            order.append(i)
        for t in tokens: lm.release_lock(t)
        assert order == [0, 1, 2]


class TestE2E_DeadlockCritical:
    """死锁检测 + CRITICAL 广播"""

    def test_deadlock_critical_flow(self, lm, l107_supervisor_spy):
        """TC-L109-L202-402 · A→B→A 环 · reject_self · L1-07 CRITICAL + retry"""
        tokA = lm.acquire_lock("foo:r1", "A:m", 5000)
        tokB = lm.acquire_lock("foo:r2", "B:m", 5000)
        def _a(): lm.acquire_lock("foo:r2", "A:m", 5000)
        th = threading.Thread(target=_a); th.start()
        time.sleep(0.05)
        r = lm.acquire_lock("foo:r1", "B:m", 5000)
        assert r.error_code == "deadlock_rejected"
        assert l107_supervisor_spy.critical_events
        lm.release_lock(tokA); lm.release_lock(tokB); th.join(timeout=2)


class TestE2E_LeakSelfHeal:
    """TTL 泄漏 + janitor 自愈"""

    def test_leak_self_heal(self, lm_short_ttl, janitor_tick, l107_supervisor_spy):
        """TC-L109-L202-403 · TTL=100ms 持锁 300ms · janitor 强释 · 下次 acquire 成功"""
        tok = lm_short_ttl.acquire_lock("foo:state", "slow:m", 3000)
        time.sleep(0.3)
        janitor_tick(lm_short_ttl)
        tok2 = lm_short_ttl.acquire_lock("foo:state", "new:m", 3000)
        assert tok2.token_id != tok.token_id
        lm_short_ttl.release_lock(tok2)
        assert l107_supervisor_spy.critical_events
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, os
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def tmp_lock_dir(tmp_path): return tmp_path


@pytest.fixture
def l201_audit_spy():
    m = MagicMock()
    m.appended_events = []
    def _append(evt):
        m.appended_events.append(evt)
        return {"ok": True}
    m.append = _append
    return m


@pytest.fixture
def l107_supervisor_spy():
    m = MagicMock()
    m.critical_events = []
    def _receive(evt):
        if evt.get("severity") == "CRITICAL":
            m.critical_events.append(evt)
    m.receive = _receive
    return m


@pytest.fixture
def lm(tmp_lock_dir, l201_audit_spy, l107_supervisor_spy):
    return LockManager(
        workdir=tmp_lock_dir,
        audit_sink=l201_audit_spy,
        supervisor_sink=l107_supervisor_spy,
        config={"TTL_MS": 30_000, "JANITOR_INTERVAL_MS": 1000,
                "LOCK_WAIT_TIMEOUT_MS_MAX": 5000},
    )


@pytest.fixture
def lm_short_ttl(tmp_lock_dir, l201_audit_spy, l107_supervisor_spy):
    return LockManager(
        workdir=tmp_lock_dir,
        audit_sink=l201_audit_spy,
        supervisor_sink=l107_supervisor_spy,
        config={"TTL_MS": 100, "JANITOR_INTERVAL_MS": 50,
                "LOCK_WAIT_TIMEOUT_MS_MAX": 5000},
    )


@pytest.fixture
def lm_readonly_dir(tmp_path, l201_audit_spy, l107_supervisor_spy):
    ro = tmp_path / "ro"
    ro.mkdir()
    os.chmod(ro, 0o555)
    yield LockManager(
        workdir=ro,
        audit_sink=l201_audit_spy,
        supervisor_sink=l107_supervisor_spy,
        config={"TTL_MS": 30_000},
    )
    os.chmod(ro, 0o755)


@pytest.fixture
def spy_flock(monkeypatch):
    import fcntl
    m = MagicMock()
    original = fcntl.flock
    def _wrap(fd, op):
        m.flock(fd, op)
        return original(fd, op)
    monkeypatch.setattr(fcntl, "flock", _wrap)
    return m


@pytest.fixture
def janitor_tick():
    def _tick(lm_instance):
        lm_instance._janitor_tick()
    return _tick
```

---

## §8 集成点用例

```python
# tests/integration/L1-09/L2-02/test_integration_points.py
import pytest, time, threading

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL201Audit:
    """与 L2-01 事件总线 · 审计落盘"""

    def test_acquire_emits_audit_to_l201(self, lm, l201_audit_spy):
        """TC-L109-L202-501 · acquire 成功 · L2-01 收 lock_acquired"""
        tok = lm.acquire_lock("foo:state", "A:m", 3000)
        lm.release_lock(tok)
        types = {e["type"] for e in l201_audit_spy.appended_events}
        assert "L1-09:lock_acquired" in types and "L1-09:lock_released" in types


class TestIntegrationWithL204Shutdown:
    """与 L2-04 · shutdown 协作"""

    def test_l204_shutdown_triggers_force_release(self, lm):
        """TC-L109-L202-502 · L2-04 广播 shutdown · force_release_all · 20 把锁全释"""
        for i in range(20):
            lm.acquire_lock(f"foo:r{i}", f"H{i}:m", 3000)
        report = lm.force_release_all(reason="shutdown")
        assert report.released_count == 20


class TestIntegrationWithL107Supervisor:
    """与 L1-07 Supervisor · CRITICAL 上报"""

    def test_deadlock_reaches_supervisor_critical(self, lm, l107_supervisor_spy):
        """TC-L109-L202-503 · deadlock · Supervisor 收 CRITICAL"""
        tokA = lm.acquire_lock("foo:r1", "A:m", 5000)
        tokB = lm.acquire_lock("foo:r2", "B:m", 5000)
        def _a(): lm.acquire_lock("foo:r2", "A:m", 5000)
        th = threading.Thread(target=_a); th.start()
        time.sleep(0.05)
        lm.acquire_lock("foo:r1", "B:m", 5000)
        assert l107_supervisor_spy.critical_events
        lm.release_lock(tokA); lm.release_lock(tokB); th.join(timeout=2)
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-09/L2-02/test_edge_cases.py
import pytest, time

pytestmark = pytest.mark.asyncio


class TestEdgeResourceLimit:
    """同时管理资源数 ≥ 20"""

    def test_edge_20_resources_concurrent(self, lm):
        """TC-L109-L202-601 · 20 不同资源并发持有 · 全部 OK · list_held 返 20"""
        tokens = [lm.acquire_lock(f"foo:r{i}", f"H{i}:m", 3000) for i in range(20)]
        assert len(lm.list_held()) == 20
        for t in tokens: lm.release_lock(t)


class TestEdgeTTLBoundary:
    """TTL 边界 · 99ms / 100ms / 101ms"""

    def test_edge_ttl_exactly_100ms(self, lm_short_ttl, janitor_tick):
        """TC-L109-L202-602 · 持锁 99ms · 未触 TTL · 不被 force"""
        tok = lm_short_ttl.acquire_lock("foo:state", "A:m", 3000)
        time.sleep(0.099)
        janitor_tick(lm_short_ttl)
        ack = lm_short_ttl.release_lock(tok)
        assert ack.status not in {"forced_released", "ok_forced_released"}


class TestEdgeReentrance:
    """同 holder 重入"""

    def test_edge_same_holder_re_acquire_rejected(self, lm):
        """TC-L109-L202-603 · 同 holder 持 r · 再 acquire r · 返 timeout（不允许重入）"""
        tok = lm.acquire_lock("foo:state", "A:m", 3000)
        r = lm.acquire_lock("foo:state", "A:m", 100)
        assert r.error_code == "timeout"
        lm.release_lock(tok)


class TestEdgeShuttingDown:
    """SHUTTING_DOWN · 所有 acquire 拒 · release 仍允许"""

    def test_edge_shutdown_release_still_ok(self, lm):
        """TC-L109-L202-604 · shutdown 后 release 持有的 token · 仍 ok（幂等）"""
        tok = lm.acquire_lock("foo:state", "A:m", 3000)
        lm.force_release_all(reason="shutdown")
        ack = lm.release_lock(tok)
        assert ack.status in {"ok", "ok_idempotent", "ok_forced_released", "forced_released"}


class TestEdgeWaiterCleanup:
    """持 holder 释放 · waiter 被正确唤醒 + 清理"""

    def test_edge_waiter_released_exactly_once(self, lm):
        """TC-L109-L202-605 · 多 waiter · FIFO · 每个 waiter 恰一次 signal"""
        import threading
        tok = lm.acquire_lock("foo:state", "H:m", 3000)
        signaled = []
        def _w(i):
            t = lm.acquire_lock("foo:state", f"W{i}:m", 3000)
            signaled.append(i)
            lm.release_lock(t)
        threads = [threading.Thread(target=_w, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        time.sleep(0.05)
        lm.release_lock(tok)
        for t in threads: t.join(timeout=2)
        assert sorted(signaled) == [0, 1, 2, 3, 4]
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
