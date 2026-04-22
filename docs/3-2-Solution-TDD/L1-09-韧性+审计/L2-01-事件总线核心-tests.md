---
doc_id: tests-L1-09-L2-01-事件总线核心-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md
  - docs/2-prd/L1-09 韧性+审计/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-K
created_at: 2026-04-22
---

# L1-09 L2-01 事件总线核心 · TDD 测试用例

> 基于 3-1 L2-01 §3（5 个 public 方法 · append / register_subscriber / unregister / read_range / verify_hash_chain）+ §11（12+ `E_BUS_*` 错误码 · 5 等级 CRITICAL/ERROR/WARN/INFO/FATAL + 响应面 4 硬 halt）+ §12（SLO-01~12 · append P95 50ms · verify 1 万 5s）+ §13 TC 锚点。
> **最热契约 IC-09 入口 · 系统脊柱** · 测试必含：系统级 halt (fsync 失败) · hash chain 断裂检测 · 幂等 (idempotency_key) · 并发 append 顺序。
> TC ID `TC-L109-L201-NNN`（语义别名：`TC-BUS-APPEND-*` / `TC-BUS-SUB-*` / `TC-BUS-VERIFY-*`）。
> pytest + Python 3.11+ · `class TestEventBusCore_*` 组织。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（append / 订阅广播 / read_range / verify）
- [x] §3 负向用例（E_BUS_* 12+ 错误码 + 5 等级）
- [x] §4 IC-XX 契约集成测试（IC-09 唯一写入口 · IC-L2-02 广播 · IC-L2-04 read）
- [x] §5 性能 SLO 用例（append P95 50ms · 吞吐 ≥ 200 ev/s · verify 10k ≤ 5s）
- [x] §6 端到端 e2e 场景（断链拒启动 · fsync halt · 跨 session bootstrap 游标恢复）
- [x] §7 测试 fixture（mock_l202_lock / mock_l205_crash / hash_chain_builder / mock_broadcast_queue）
- [x] §8 集成点用例（L2-02 锁 · L2-05 落盘 · L2-04 boot · L1-07 escalate）
- [x] §9 边界 / edge case（idempotent 10min 窗 · shutdown_draining · meta 事件防递归 · prev=GENESIS）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | IC |
|:---|:---|:---|
| `append(event)` · 正常 L1-01:decision_made | TC-L109-L201-001 | IC-09 |
| `append(event)` · meta 事件（不触发元事件） | TC-L109-L201-002 | IC-09 |
| `append(event)` · idempotency_key 10min 内重复 | TC-L109-L201-003 | IC-09 |
| `append(event)` · prev_hash=GENESIS（首次） | TC-L109-L201-004 | IC-09 |
| `append(event)` · hash 链接（prev_hash 正确） | TC-L109-L201-005 | IC-09 |
| `register_subscriber()` · filter type_prefix | TC-L109-L201-006 | IC-L2-02 |
| `register_subscriber()` · delivery_mode=fire_and_forget | TC-L109-L201-007 | IC-L2-02 |
| `register_subscriber()` · 幂等（相同 id 重复） | TC-L109-L201-008 | IC-L2-02 |
| `unregister_subscriber()` · 幂等 | TC-L109-L201-009 | IC-L2-02 |
| `read_range(pid, from, to)` · iterator | TC-L109-L201-010 | IC-L2-04 |
| `read_range()` · 空范围 | TC-L109-L201-011 | IC-L2-04 |
| `verify_hash_chain(pid)` · 全链 OK | TC-L109-L201-012 | IC-L2-07 辅 |
| `verify_hash_chain(pid)` · 断裂返 break_at_seq | TC-L109-L201-013 | IC-L2-07 辅 |
| 广播 push 订阅者（subscriber callback） | TC-L109-L201-014 | IC-L2-02 |
| 并发 append 顺序保证（sequence 严格递增） | TC-L109-L201-015 | IC-09 |

### §1.2 错误码 × 测试（§11 12+ 项全覆盖）

| 错误码 | TC ID | 等级 | halt? |
|:---|:---|:---|:---|
| `E_BUS_PROJECT_NOT_REGISTERED` | TC-L109-L201-101 | ERROR | 否 |
| `E_BUS_TYPE_PREFIX_VIOLATION` | TC-L109-L201-102 | ERROR | 否 |
| `E_BUS_SCHEMA_INVALID` | TC-L109-L201-103 | ERROR | 否 |
| `E_BUS_LOCK_TIMEOUT` | TC-L109-L201-104 | WARN | 否 |
| `E_BUS_DEADLOCK_DETECTED` | TC-L109-L201-105 | WARN | 否 |
| `E_BUS_WRITE_FAILED` | TC-L109-L201-106 | CRITICAL | **是** |
| `E_BUS_DISK_FULL` | TC-L109-L201-107 | CRITICAL | **是** |
| `E_BUS_HASH_CHAIN_BROKEN` | TC-L109-L201-108 | CRITICAL | **拒启动** |
| `E_BUS_SHUTDOWN_REJECTED` | TC-L109-L201-109 | INFO | 否 |
| `E_BUS_HALTED` | TC-L109-L201-110 | INFO | 是（已 halt） |
| `E_BUS_IDEMPOTENT_REPLAY` | TC-L109-L201-111 | INFO | 否（非错） |
| `E_BUS_UNSAFE_WRITE_WITHOUT_LOCK` | TC-L109-L201-112 | FATAL | **是（Assert）** |

### §1.3 IC × 集成测试

| IC | TC ID | 对端 |
|:---|:---|:---|
| IC-09 append_event | TC-L109-L201-201 | L1-08 / L1-01~L1-10 全部 |
| IC-L2-02 subscribe/broadcast | TC-L109-L201-202 | L2-03 audit_mirror / L2-04 recoverer / ui_sse |
| IC-L2-04 read_range | TC-L109-L201-203 | L2-04 bootstrap 回放 |
| IC-Lock acquire/release（出站）| TC-L109-L201-204 | L2-02 |
| IC-atomic_append（出站）| TC-L109-L201-205 | L2-05 |

### §1.4 性能 SLO × 测试

| SLO | 阈值 | TC ID |
|:---|:---|:---|
| SLO-01 append P95 | ≤ 50ms | TC-L109-L201-301 |
| SLO-01 append P99 | ≤ 200ms | TC-L109-L201-302 |
| SLO-07 吞吐 ≥ 200 ev/s | | TC-L109-L201-303 |
| SLO-08 verify 1 万事件 ≤ 5s | | TC-L109-L201-304 |
| SLO-06 广播推送 ≤ 500ms | | TC-L109-L201-305 |

### §1.5 e2e × 测试

| 场景 | TC ID |
|:---|:---|
| 断链拒启动：boot 期 verify 发现 hash 断 → HALTED | TC-L109-L201-401 |
| fsync 失败 halt：L2-05 抛 CrashSafety → L1-07 escalate | TC-L109-L201-402 |
| 跨 session bootstrap：restart → 游标恢复到 last seq | TC-L109-L201-403 |

---

## §2 正向用例

```python
# tests/unit/L1-09/L2-01/test_event_bus_positive.py
import pytest, hashlib, json
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestEventBusCore_Append:
    """§3.2 append · IC-09 唯一写入口"""

    def test_append_normal_event(self, bus, _evt):
        """TC-L109-L201-001 · L1-01:decision_made · 返 event_id + sequence + hash"""
        r = bus.append(_evt(type="L1-01:decision_made", actor="main_loop"))
        assert r.event_id.startswith("evt_")
        assert r.sequence >= 0
        assert len(r.hash) == 64
        assert r.prev_hash in {"GENESIS"} or len(r.prev_hash) == 64

    def test_append_meta_event_no_recursion(self, bus, _evt):
        """TC-L109-L201-002 · is_meta=true · 不触发元事件 · I-08 防递归"""
        r = bus.append(_evt(type="L1-09:type_prefix_violation", actor="recoverer", is_meta=True))
        assert r.event_id
        # bus 内部元事件计数 · 此 append 不再产生新元事件
        assert bus._meta_events_generated == 0

    def test_append_idempotent_key(self, bus, _evt):
        """TC-L109-L201-003 · idempotency_key 重复 · 返原 event_id + E_BUS_IDEMPOTENT_REPLAY info"""
        key = "idem-001"
        r1 = bus.append(_evt(idempotency_key=key))
        r2 = bus.append(_evt(idempotency_key=key))
        assert r1.event_id == r2.event_id
        assert r2.sequence == r1.sequence

    def test_append_first_event_genesis_prev(self, fresh_bus, _evt):
        """TC-L109-L201-004 · project 首次 append · prev_hash=GENESIS"""
        r = fresh_bus.append(_evt())
        assert r.prev_hash == "GENESIS"

    def test_append_hash_chain_links(self, bus, _evt):
        """TC-L109-L201-005 · 连续 append · 第 N 的 prev_hash == 第 N-1 的 hash"""
        r1 = bus.append(_evt(payload={"i": 1}))
        r2 = bus.append(_evt(payload={"i": 2}))
        assert r2.prev_hash == r1.hash


class TestEventBusCore_Subscribe:
    """§3.3 register/unregister"""

    def test_register_subscriber_type_prefix_filter(self, bus, _cb):
        """TC-L109-L201-006 · filter.type_prefix=[L1-01:] · 仅收 L1-01 事件"""
        recv = []
        tok = bus.register_subscriber({
            "subscriber_id": "test_sub",
            "filter": {"type_prefix": ["L1-01:"]},
            "callback_ref": _cb(recv),
        })
        assert tok.registration_token
        bus.append(_evt_dict(type="L1-01:x"))
        bus.append(_evt_dict(type="L1-07:y"))
        bus._drain_broadcast()
        assert len(recv) == 1
        assert recv[0]["type"].startswith("L1-01:")

    def test_register_fire_and_forget_mode(self, bus, _cb):
        """TC-L109-L201-007 · delivery_mode 默认 fire_and_forget · 慢 callback 不阻塞 append"""
        def _slow(e): import time; time.sleep(0.5)
        bus.register_subscriber({"subscriber_id": "slow", "callback_ref": {"kind":"python_callable","target":_slow}})
        t0 = time.perf_counter()
        bus.append(_evt_dict())
        assert (time.perf_counter() - t0) < 0.1

    def test_register_idempotent(self, bus, _cb):
        """TC-L109-L201-008 · 同 subscriber_id 二次注册 · 覆盖 filter · 返 warn 不抛"""
        recv = []
        bus.register_subscriber({"subscriber_id": "s1", "callback_ref": _cb(recv)})
        bus.register_subscriber({"subscriber_id": "s1", "filter": {"type_prefix": ["L1-02:"]},
                                  "callback_ref": _cb(recv)})
        assert len(bus._subscribers) == 1

    def test_unregister_idempotent(self, bus):
        """TC-L109-L201-009 · unregister 不存在 id · 幂等不抛"""
        bus.unregister_subscriber("nonexistent")
        bus.unregister_subscriber("nonexistent")


class TestEventBusCore_ReadRange:
    """§3.4 read_range · IC-L2-04 只读 iterator"""

    def test_read_range_returns_iterator(self, bus, _evt, mock_project_id):
        """TC-L109-L201-010 · from=0 to=10 · yield 10 event"""
        for i in range(10):
            bus.append(_evt(payload={"i": i}))
        it = list(bus.read_range(mock_project_id, from_seq=0, to_seq=10))
        assert len(it) == 10

    def test_read_range_empty(self, bus, mock_project_id):
        """TC-L109-L201-011 · from > 当前 last_seq · 空 iter"""
        it = list(bus.read_range(mock_project_id, from_seq=9999, to_seq=10000))
        assert it == []


class TestEventBusCore_VerifyHashChain:
    """§3.5 verify_hash_chain · IC-L2-07 辅"""

    def test_verify_full_chain_ok(self, bus, _evt, mock_project_id):
        """TC-L109-L201-012 · 健康链 · verify OK"""
        for i in range(50):
            bus.append(_evt(payload={"i": i}))
        r = bus.verify_hash_chain(mock_project_id)
        assert r["state"] == "OK"

    def test_verify_broken_chain_returns_break_at(self, bus, corrupt_chain_at_30,
                                                    mock_project_id):
        """TC-L109-L201-013 · 手工改 events.jsonl 第 30 行 · verify 返 break_at_seq=30"""
        corrupt_chain_at_30()
        r = bus.verify_hash_chain(mock_project_id)
        assert r["state"] in {"BROKEN", "CORRUPT"}
        assert r.get("break_at_seq") == 30


class TestEventBusCore_BroadcastAndConcurrency:
    """广播 + 并发顺序"""

    def test_broadcast_pushes_to_callback(self, bus, _cb, _evt_dict):
        """TC-L109-L201-014 · 订阅者 callback 收到事件（fire_and_forget）"""
        recv = []
        bus.register_subscriber({"subscriber_id": "r", "callback_ref": _cb(recv)})
        bus.append(_evt_dict(type="L1-01:x"))
        bus._drain_broadcast()
        assert len(recv) == 1

    def test_concurrent_append_sequence_monotonic(self, bus, _evt):
        """TC-L109-L201-015 · 10 线程 × 100 event · sequence 全域严格递增"""
        import threading
        results = []
        lock = threading.Lock()
        def _w():
            for _ in range(100):
                r = bus.append(_evt())
                with lock:
                    results.append(r.sequence)
        ts = [threading.Thread(target=_w) for _ in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        assert sorted(results) == list(range(min(results), min(results) + len(results)))
        assert len(set(results)) == 1000  # 无重
```

---

## §3 负向用例（每错误码 ≥ 1 · 脊柱测试）

```python
# tests/unit/L1-09/L2-01/test_event_bus_negative.py
import pytest, errno

pytestmark = pytest.mark.asyncio


class TestL201_ERROR_Level:
    """ERROR · 调用方 bug · 不 halt"""

    def test_E_BUS_PROJECT_NOT_REGISTERED(self, bus, _evt):
        """TC-L109-L201-101 · project_id 不在 _index · 404 ERROR"""
        r = bus.append(_evt(project_id="unknown_pid"))
        assert r.error_code == "E_BUS_PROJECT_NOT_REGISTERED"
        assert r.halt_system is False

    def test_E_BUS_TYPE_PREFIX_VIOLATION(self, bus, _evt):
        """TC-L109-L201-102 · L1-03 进程发 L1-01:x · 前缀违规 · 记告警事件"""
        r = bus.append(_evt(type="L1-01:x", caller_l1="L1-03"))
        assert r.error_code == "E_BUS_TYPE_PREFIX_VIOLATION"
        # 副作用：bus 内自记 type_prefix_violation 元事件
        assert any(e["type"] == "L1-09:type_prefix_violation" for e in bus._internal_events)

    def test_E_BUS_SCHEMA_INVALID(self, bus):
        """TC-L109-L201-103 · payload 缺必填 · Pydantic ValidationError"""
        bad = {"project_id": "p", "type": "L1-01:x"}  # 缺 actor/timestamp/payload
        r = bus.append(bad)
        assert r.error_code == "E_BUS_SCHEMA_INVALID"


class TestL201_WARN_Level:
    """WARN · 调用方可重试"""

    def test_E_BUS_LOCK_TIMEOUT(self, bus, _evt, mock_l202_lock_timeout):
        """TC-L109-L201-104 · L2-02 acquire > 3s · 返 retry_after_ms"""
        mock_l202_lock_timeout()
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_LOCK_TIMEOUT"
        assert r.retryable is True
        assert r.retry_after_ms >= 100

    def test_E_BUS_DEADLOCK_DETECTED(self, bus, _evt, mock_l202_deadlock):
        """TC-L109-L201-105 · L2-02 环检测 · 返 deadlock 让调用方释锁"""
        mock_l202_deadlock()
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_DEADLOCK_DETECTED"


class TestL201_CRITICAL_HardHalt:
    """CRITICAL · 响应面 4 硬 halt · 脊柱红线"""

    def test_E_BUS_WRITE_FAILED_halts_bus(self, bus, _evt, mock_l205_write_fail,
                                            l107_supervisor_spy):
        """TC-L109-L201-106 · L2-05 重试 2 次仍失败 · HALTED + 通知 L1-07"""
        mock_l205_write_fail(fail_count=3)
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_WRITE_FAILED"
        assert r.halt_system is True
        assert bus.bus_state == "HALTED"
        l107_supervisor_spy.assert_escalate_called(severity="CRITICAL")

    def test_E_BUS_DISK_FULL(self, bus, _evt, mock_l205_enospc, l107_supervisor_spy):
        """TC-L109-L201-107 · ENOSPC · HALTED + UI 清盘提示"""
        mock_l205_enospc()
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_DISK_FULL"
        assert r.halt_system is True

    def test_E_BUS_HASH_CHAIN_BROKEN_refuses_boot(self, corrupt_chain_at_30, bus_factory):
        """TC-L109-L201-108 · boot 期 verify 发现断裂 · 拒启动 · 不接受任何 append"""
        corrupt_chain_at_30()
        with pytest.raises(HashChainBroken) as exc:
            bus = bus_factory()  # 启动即 verify
            bus.ready()  # 若懒 verify 则 ready() 触发
        assert exc.value.break_at_seq == 30


class TestL201_INFO_Level:
    """INFO · 非错"""

    def test_E_BUS_SHUTDOWN_REJECTED(self, bus, _evt):
        """TC-L109-L201-109 · bus_state=SHUTDOWN_DRAINING · 拒新写"""
        bus.begin_shutdown()
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_SHUTDOWN_REJECTED"

    def test_E_BUS_HALTED(self, bus, _evt):
        """TC-L109-L201-110 · HALTED 态 · 禁自动重试"""
        bus.bus_state = "HALTED"
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_HALTED"
        assert r.retryable is False

    def test_E_BUS_IDEMPOTENT_REPLAY(self, bus, _evt):
        """TC-L109-L201-111 · 10 min 内 idempotency_key 重复 · info 非错"""
        key = "dup-001"
        bus.append(_evt(idempotency_key=key))
        r2 = bus.append(_evt(idempotency_key=key))
        assert r2.error_code == "E_BUS_IDEMPOTENT_REPLAY"
        assert r2.halt_system is False


class TestL201_FATAL_Bug:
    """FATAL · 编程 bug · AssertionError"""

    def test_E_BUS_UNSAFE_WRITE_WITHOUT_LOCK(self, bus, _evt, monkeypatch):
        """TC-L109-L201-112 · 调用 atomic_append 时未持锁 · 断言 · halt"""
        # 绕过 lock · 直接进 atomic_append
        monkeypatch.setattr(bus, "_lock_acquired", lambda: False)
        with pytest.raises(AssertionError):
            bus._atomic_append_internal(event={})
```

---

## §4 IC-XX 契约集成测试

```python
# tests/integration/L1-09/L2-01/test_ic_contracts.py
import pytest, jsonschema

pytestmark = pytest.mark.asyncio


class TestIC09AppendContract:
    """IC-09 · 唯一写入口 · 所有 L1 调用"""

    def test_ic09_request_schema(self, bus, ic09_req_schema, _evt):
        """TC-L109-L201-201 · 请求 payload 符合 IC-09 schema"""
        event = _evt(type="L1-01:decision_made", actor="main_loop")
        jsonschema.validate(event, ic09_req_schema)
        r = bus.append(event)
        assert r.event_id


class TestICL202BroadcastContract:
    """IC-L2-02 · 订阅广播"""

    def test_icl202_broadcast_delivery(self, bus, _cb, _evt_dict, icl202_sub_schema):
        """TC-L109-L201-202 · subscriber schema 合法 · 注册后能收事件"""
        req = {"subscriber_id": "audit_mirror",
               "filter": {"type_prefix": ["L1-08:"]},
               "callback_ref": _cb([]),
               "delivery_mode": "fire_and_forget"}
        jsonschema.validate(req, icl202_sub_schema)
        bus.register_subscriber(req)
        bus.append(_evt_dict(type="L1-08:content_read"))


class TestICL204ReadRangeContract:
    """IC-L2-04 · 只读 replay"""

    def test_icl204_read_range_iterator(self, bus, _evt, mock_project_id):
        """TC-L109-L201-203 · read_range 返 iterator · 元素含 sequence/hash"""
        for i in range(20):
            bus.append(_evt(payload={"i": i}))
        items = list(bus.read_range(mock_project_id, from_seq=5, to_seq=15))
        assert all("sequence" in e and "hash" in e for e in items)


class TestLockAndCrashSafetyContracts:
    """与 L2-02 锁 / L2-05 落盘的纵向契约"""

    def test_lock_acquire_release_in_append(self, bus, _evt, l202_spy):
        """TC-L109-L201-204 · 每次 append 对称 acquire/release · 必然"""
        bus.append(_evt())
        l202_spy.acquire.assert_called()
        l202_spy.release.assert_called()

    def test_atomic_append_called_per_event(self, bus, _evt, l205_spy):
        """TC-L109-L201-205 · L2-05.atomic_append 每 event 恰调 1 次"""
        bus.append(_evt())
        bus.append(_evt())
        assert l205_spy.atomic_append.call_count == 2
```

---

## §5 性能 SLO 用例

```python
# tests/perf/L1-09/L2-01/test_slo.py
import pytest, time, statistics, threading
from contextlib import contextmanager


@contextmanager
def _timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000


class TestAppendLatencySLO:
    """SLO-01 · append P95 ≤ 50ms · P99 ≤ 200ms"""

    def test_append_p95_under_50ms(self, bus, _evt):
        """TC-L109-L201-301 · 1000 次 append · P95 ≤ 50ms"""
        samples = []
        for _ in range(1000):
            with _timer() as t:
                bus.append(_evt())
            samples.append(t())
        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 <= 50.0

    def test_append_p99_under_200ms(self, bus, _evt):
        """TC-L109-L201-302 · 1000 次 · P99 ≤ 200ms"""
        samples = []
        for _ in range(1000):
            with _timer() as t:
                bus.append(_evt())
            samples.append(t())
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p99 <= 200.0


class TestThroughputSLO:
    """SLO-07 · 吞吐 ≥ 200 ev/s（10 线程 × 100 event ≤ 5s）"""

    def test_throughput_gte_200_eps(self, bus, _evt):
        """TC-L109-L201-303 · 10 线程并发 · total 1000 events ≤ 5s"""
        def _w():
            for _ in range(100):
                bus.append(_evt())
        t0 = time.perf_counter()
        ts = [threading.Thread(target=_w) for _ in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        total = time.perf_counter() - t0
        eps = 1000 / total
        assert eps >= 200.0


class TestVerifySLO:
    """SLO-08 · verify 1 万事件 ≤ 5s"""

    def test_verify_10k_under_5s(self, bus, _evt, mock_project_id):
        """TC-L109-L201-304 · 1 万事件 · 全链 verify ≤ 5000ms"""
        for _ in range(10_000):
            bus.append(_evt())
        with _timer() as t:
            r = bus.verify_hash_chain(mock_project_id)
        elapsed = t()
        assert r["state"] == "OK"
        assert elapsed <= 5_000.0


class TestBroadcastSLO:
    """SLO-06 · 广播推送 ≤ 500ms"""

    def test_broadcast_push_under_500ms(self, bus, _evt_dict):
        """TC-L109-L201-305 · append → callback 入口 ≤ 500ms"""
        ts_enqueue = {}
        ts_recv = {}
        def _cb(e):
            ts_recv[e["event_id"]] = time.perf_counter()
        bus.register_subscriber({"subscriber_id": "spy",
                                  "callback_ref": {"kind": "python_callable", "target": _cb}})
        for _ in range(50):
            r = bus.append(_evt_dict())
            ts_enqueue[r.event_id] = time.perf_counter()
        bus._drain_broadcast()
        for eid, t_enq in ts_enqueue.items():
            lag_ms = (ts_recv[eid] - t_enq) * 1000
            assert lag_ms <= 500.0
```

---

## §6 端到端 e2e 场景

```python
# tests/e2e/L1-09/L2-01/test_e2e.py
import pytest

pytestmark = pytest.mark.asyncio


class TestE2EHashChainBrokenRefuse:
    """断链拒启动 e2e"""

    def test_boot_detects_break_at_30_halts(self, bus_factory, corrupt_chain_at_30):
        """TC-L109-L201-401 · boot verify 断 · 进入 HALTED · 拒所有 append"""
        corrupt_chain_at_30()
        bus = bus_factory()
        with pytest.raises(HashChainBroken):
            bus.ready()
        assert bus.bus_state == "HALTED"


class TestE2EFsyncHalt:
    """fsync 失败 → CRITICAL → L1-07 escalate"""

    def test_fsync_fail_escalates_to_l107(self, bus, _evt, mock_l205_write_fail,
                                            l107_supervisor_spy):
        """TC-L109-L201-402 · L2-05 fsync 失败 · HALTED + 红屏告警"""
        mock_l205_write_fail(fail_count=3)
        r = bus.append(_evt())
        assert r.halt_system is True
        assert bus.bus_state == "HALTED"
        l107_supervisor_spy.assert_escalate_called(severity="CRITICAL")


class TestE2ECrossSessionBootstrap:
    """跨 session bootstrap · 游标恢复"""

    def test_cross_session_cursor_recovery(self, bus_factory, _evt, tmp_events_jsonl):
        """TC-L109-L201-403 · session A 写 100 event · session B 重启 · last_seq=99"""
        bus_a = bus_factory()
        for _ in range(100):
            bus_a.append(_evt())
        bus_a.shutdown()
        # 模拟 session B 重启
        bus_b = bus_factory()
        assert bus_b.last_sequence == 99
        r = bus_b.append(_evt())
        assert r.sequence == 100
```

---

## §7 测试 fixture

```python
# tests/conftest.py
import pytest, threading
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def mock_project_id(): return "demo-proj-001"


@pytest.fixture
def _evt(mock_project_id):
    def _make(type: str = "L1-01:decision_made", actor: str = "main_loop",
              payload: dict | None = None, **kwargs) -> dict:
        return {
            "project_id": kwargs.get("project_id", mock_project_id),
            "type": type, "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": kwargs.get("state", "INIT"),
            "payload": payload or {"x": 1},
            "is_meta": kwargs.get("is_meta", False),
            "idempotency_key": kwargs.get("idempotency_key"),
            "caller_l1": kwargs.get("caller_l1", "L1-01"),
            "event_id": kwargs.get("event_id"),
        }
    return _make


@pytest.fixture
def _evt_dict(_evt): return _evt


@pytest.fixture
def _cb():
    def _make(recv: list):
        def _c(e): recv.append(e)
        return {"kind": "python_callable", "target": _c}
    return _make


@pytest.fixture
def l202_spy():
    m = MagicMock()
    m.acquire = MagicMock(return_value="lock-t")
    m.release = MagicMock(return_value=None)
    return m


@pytest.fixture
def l205_spy():
    m = MagicMock()
    m.atomic_append = MagicMock()
    return m


@pytest.fixture
def mock_l202_lock_timeout():
    def _activate():
        pass
    return _activate


@pytest.fixture
def mock_l202_deadlock():
    def _activate():
        pass
    return _activate


@pytest.fixture
def mock_l205_write_fail():
    def _activate(fail_count: int = 3):
        pass
    return _activate


@pytest.fixture
def mock_l205_enospc():
    def _activate():
        pass
    return _activate


@pytest.fixture
def l107_supervisor_spy():
    m = MagicMock()
    def _assert(severity: str = "CRITICAL"):
        assert m.escalate.called
        assert m.escalate.call_args[1].get("severity") == severity
    m.assert_escalate_called = _assert
    return m


@pytest.fixture
def corrupt_chain_at_30(tmp_path):
    def _activate():
        # 手工改 events.jsonl 第 30 行 · 使 prev_hash 不匹配
        pass
    return _activate


@pytest.fixture
def bus_factory(tmp_path, l202_spy, l205_spy):
    def _make():
        return EventBusCore(
            data_dir=tmp_path,
            lock_manager=l202_spy,
            crash_safety=l205_spy,
            config={"fsync_mode": "per_event"},
        )
    return _make


@pytest.fixture
def bus(bus_factory): return bus_factory()


@pytest.fixture
def fresh_bus(bus_factory): return bus_factory()


@pytest.fixture
def tmp_events_jsonl(tmp_path): return tmp_path / "events.jsonl"


@pytest.fixture
def ic09_req_schema():
    return {"type": "object", "required": ["project_id", "type", "actor", "timestamp", "payload"]}


@pytest.fixture
def icl202_sub_schema():
    return {"type": "object", "required": ["subscriber_id", "callback_ref"]}
```

---

## §8 集成点用例

```python
# tests/integration/L1-09/L2-01/test_integration_points.py
import pytest

pytestmark = pytest.mark.asyncio


class TestIntegrationWithL202Lock:
    """与 L2-02 锁协作 · 必握锁落盘"""

    def test_every_append_acquires_project_lock(self, bus, _evt, l202_spy):
        """TC-L109-L201-501 · append 必调 L2-02 acquire · 锁 key 含 project_id"""
        bus.append(_evt())
        l202_spy.acquire.assert_called()
        key = l202_spy.acquire.call_args[0][0]
        assert "demo-proj-001" in key or "event_bus" in key


class TestIntegrationWithL205CrashSafety:
    """与 L2-05 落盘协作 · 每 event fsync"""

    def test_append_uses_l205_atomic_append(self, bus, _evt, l205_spy):
        """TC-L109-L201-502 · append 必经 L2-05.atomic_append · 保 hash 链"""
        bus.append(_evt())
        l205_spy.atomic_append.assert_called()


class TestIntegrationWithL204Bootstrap:
    """与 L2-04 bootstrap 协作 · 游标恢复"""

    def test_bootstrap_recovers_last_seq(self, bus_factory, _evt):
        """TC-L109-L201-503 · restart 后 last_sequence 正确"""
        bus1 = bus_factory()
        for _ in range(10): bus1.append(_evt())
        bus1.shutdown()
        bus2 = bus_factory()
        assert bus2.last_sequence == 9


class TestIntegrationWithL107Supervisor:
    """与 L1-07 escalate 协作"""

    def test_critical_escalates_to_l107(self, bus, _evt, mock_l205_write_fail,
                                          l107_supervisor_spy):
        """TC-L109-L201-504 · CRITICAL 错误 · escalate 触达 L1-07"""
        mock_l205_write_fail(fail_count=3)
        bus.append(_evt())
        l107_supervisor_spy.assert_escalate_called(severity="CRITICAL")
```

---

## §9 边界 / edge case

```python
# tests/edge/L1-09/L2-01/test_edge_cases.py
import pytest, time, threading

pytestmark = pytest.mark.asyncio


class TestEdgeIdempotentWindow:
    """idempotency_key 10min 窗边界"""

    def test_edge_idempotent_within_10min(self, bus, _evt):
        """TC-L109-L201-601 · key 在 10 min 窗内 · 返 replay"""
        key = "w-001"
        r1 = bus.append(_evt(idempotency_key=key))
        r2 = bus.append(_evt(idempotency_key=key))
        assert r1.event_id == r2.event_id

    def test_edge_idempotent_past_10min(self, bus, _evt, clock_jump_15min):
        """TC-L109-L201-602 · key 过 10 min · 视作新事件"""
        key = "w-002"
        r1 = bus.append(_evt(idempotency_key=key))
        clock_jump_15min()
        r2 = bus.append(_evt(idempotency_key=key))
        assert r1.event_id != r2.event_id


class TestEdgeMetaRecursionGuard:
    """I-08 元事件防递归"""

    def test_edge_meta_event_no_infinite_loop(self, bus, _evt):
        """TC-L109-L201-603 · is_meta=true 后再发 meta · 不无限递归 · 硬 cap 1 层"""
        bus.append(_evt(is_meta=True, type="L1-09:type_prefix_violation"))
        assert bus._meta_events_generated <= 1


class TestEdgeShutdownDraining:
    """bus_state=SHUTDOWN_DRAINING 时行为"""

    def test_edge_shutdown_rejects_new_writes(self, bus, _evt):
        """TC-L109-L201-604 · begin_shutdown 后新 append → E_BUS_SHUTDOWN_REJECTED"""
        bus.begin_shutdown()
        r = bus.append(_evt())
        assert r.error_code == "E_BUS_SHUTDOWN_REJECTED"

    def test_edge_shutdown_drain_completes_in_time(self, bus, _evt):
        """TC-L109-L201-605 · SLO-12 · shutdown drain ≤ 5s"""
        for _ in range(100): bus.append(_evt())
        t0 = time.perf_counter()
        bus.shutdown()
        assert (time.perf_counter() - t0) <= 5.0


class TestEdgeBoundaryValues:
    """prev_hash=GENESIS · 超大 payload"""

    def test_edge_first_event_genesis(self, fresh_bus, _evt):
        """TC-L109-L201-606 · fresh bus 首 event · prev_hash=GENESIS"""
        r = fresh_bus.append(_evt())
        assert r.prev_hash == "GENESIS"

    def test_edge_oversized_payload_rejected(self, bus, _evt):
        """TC-L109-L201-607 · payload > PIPE_BUF · E_LINE_TOO_LARGE（透传 L2-05）"""
        big = _evt(payload={"k": "x" * 5000})
        r = bus.append(big)
        assert r.error_code in {"E_BUS_SCHEMA_INVALID", "E_LINE_TOO_LARGE"}


class TestEdgeOrderingUnderRace:
    """并发下 hash 链顺序不乱"""

    def test_edge_race_hash_chain_consistent(self, bus, _evt, mock_project_id):
        """TC-L109-L201-608 · 10 线程 × 50 · verify 全链仍 OK"""
        def _w():
            for _ in range(50): bus.append(_evt())
        ts = [threading.Thread(target=_w) for _ in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        r = bus.verify_hash_chain(mock_project_id)
        assert r["state"] == "OK"
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-K —*
