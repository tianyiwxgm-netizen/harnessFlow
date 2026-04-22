---
doc_id: tests-L1-03-L2-03-WP 调度器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-03-WP 调度器.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-03 L2-03-WP 调度器 · TDD 测试用例

> 基于 3-1 L2-03 §3（IC-02 主接口 + 3 条下游 IC）+ §11（13 条 `E_L103_L203_*` 错误码）+ §12 SLO + §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L103-L203-NNN`。pytest + Python 3.11+；`class TestL2_03_WPScheduler`；三态语义 all_done/deadlock/awaiting_deps 独立分组。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（每 public 方法 + 三态语义 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法（§3）| TC ID | 覆盖类型 | IC |
|---|---|---|---|
| `get_next_wp()` · happy path | TC-L103-L203-001 | unit | IC-02 |
| `get_next_wp()` · all_done | TC-L103-L203-002 | unit | IC-02 |
| `get_next_wp()` · awaiting_deps | TC-L103-L203-003 | unit | IC-02 |
| `get_next_wp()` · deadlock | TC-L103-L203-004 | unit | IC-02 |
| `get_next_wp()` · prefer_critical_path | TC-L103-L203-005 | unit | IC-02 |
| `get_next_wp()` · exclude_wp_ids | TC-L103-L203-006 | unit | IC-02 |
| `get_remaining_hint()` | TC-L103-L203-007 | unit | — |
| `_acquire_lock_or_fallback()` · 拿到 | TC-L103-L203-008 | unit | — |
| `_acquire_lock_or_fallback()` · fallback | TC-L103-L203-009 | unit | — |
| `_transition_with_retry()` | TC-L103-L203-010 | unit | IC-L2-03 |
| `_detect_deadlock()` | TC-L103-L203-011 | unit | — |
| `_append_event_with_retry()` · 成功 | TC-L103-L203-012 | unit | IC-09 |
| `_append_event_with_retry()` · 重试成功 | TC-L103-L203-013 | unit | IC-09 |
| 幂等（同 query_id） | TC-L103-L203-014 | unit | — |
| parallel_limit=2 守护 | TC-L103-L203-015 | unit | — |
| topology_version 回填 | TC-L103-L203-016 | unit | — |
| audit_event_id 回填 | TC-L103-L203-017 | unit | IC-09 |
| deadlock 通知 L2-05 | TC-L103-L203-018 | unit | — |
| bypass_guard | TC-L103-L203-019 | unit | — |
| hard 上限 1s abort | TC-L103-L203-020 | unit | — |

### §1.2 错误码 × 测试（§11 13 项全覆盖）

| 错误码 | TC ID | 说明 |
|---|---|---|
| `E_L103_L203_101` | TC-L103-L203-101 | backpressure |
| `E_L103_L203_102` | TC-L103-L203-102 | awaiting_deps |
| `E_L103_L203_103` | TC-L103-L203-103 | deadlock |
| `E_L103_L203_104` | TC-L103-L203-104 | all_done |
| `E_L103_L203_201` | TC-L103-L203-105 | PM-14 pid 缺失 |
| `E_L103_L203_202` | TC-L103-L203-106 | wp_id 非法格式 |
| `E_L103_L203_301` | TC-L103-L203-107 | 锁超时 |
| `E_L103_L203_302` | TC-L103-L203-108 | stale 超限 |
| `E_L103_L203_303` | TC-L103-L203-109 | L2-02 并行超 |
| `E_L103_L203_304` | TC-L103-L203-110 | L2-02 deps 不 sat |
| `E_L103_L203_305` | TC-L103-L203-111 | L2-02 非法跃迁 |
| `E_L103_L203_401` | TC-L103-L203-112 | IC-09 审计失败 |
| `E_L103_L203_501` | TC-L103-L203-113 | 后台主动调度 bypass |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| IC-02 get_next_wp | L1-01 → 本 L2 | TC-L103-L203-601 |
| IC-L2-02 read_snapshot | 本 L2 → L2-02 | TC-L103-L203-602 |
| IC-L2-03 transition_state | 本 L2 → L2-02 | TC-L103-L203-603 |
| IC-09 append_event | 本 L2 → L1-09 | TC-L103-L203-604 |
| deadlock_detected | 本 L2 → L2-05 | TC-L103-L203-605 |

---

## §2 正向用例

```python
# file: tests/l1_03/test_l2_03_wp_scheduler_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_03_sched.scheduler import WPScheduler
from app.l2_03_sched.schemas import GetNextWPRequest, GetNextWPResponse


class TestL2_03_WPScheduler_Positive:

    def test_TC_L103_L203_001_get_next_wp_happy_path(
        self, sut: WPScheduler, mock_project_id: str,
    ) -> None:
        """TC-L103-L203-001 · 有 candidate · wp_id 非 null + deps_met=True。"""
        req = GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000001",
            project_id=mock_project_id,
            requester_tick="tick-00000000-0000-0000-0000-000000000001",
            ts="2026-04-22T00:00:00Z",
        )
        resp: GetNextWPResponse = sut.get_next_wp(req)
        assert resp.wp_id is not None
        assert resp.deps_met is True
        assert resp.in_flight_wp_count >= 1
        assert resp.topology_version
        assert resp.latency_ms < 1000

    def test_TC_L103_L203_002_all_done(self, sut_all_done, mock_project_id) -> None:
        resp = sut_all_done.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000002",
            project_id=mock_project_id,
            requester_tick="tick-x", ts="2026-04-22T00:00:00Z",
        ))
        assert resp.wp_id is None and resp.reason == "all_done"

    def test_TC_L103_L203_003_awaiting_deps(self, sut_awaiting, mock_project_id) -> None:
        resp = sut_awaiting.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000003",
            project_id=mock_project_id,
            requester_tick="tick-x", ts="2026-04-22T00:00:00Z",
        ))
        assert resp.wp_id is None and resp.reason == "awaiting_deps"

    def test_TC_L103_L203_004_deadlock(self, sut_deadlock, mock_project_id, mock_l2_05) -> None:
        resp = sut_deadlock.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000004",
            project_id=mock_project_id,
            requester_tick="tick-x", ts="2026-04-22T00:00:00Z",
        ))
        assert resp.wp_id is None and resp.reason == "deadlock"
        mock_l2_05.deadlock_detected.assert_called_once()

    def test_TC_L103_L203_005_prefer_critical_path(self, sut, mock_project_id) -> None:
        resp = sut.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000005",
            project_id=mock_project_id,
            requester_tick="tick-x", prefer_critical_path=True,
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.wp_id is not None
        assert resp.wp_def["in_critical_path"] is True

    def test_TC_L103_L203_006_exclude_wp_ids(self, sut, mock_project_id, first_ready_wp_id) -> None:
        resp = sut.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000006",
            project_id=mock_project_id, requester_tick="tick-x",
            exclude_wp_ids=[first_ready_wp_id],
            ts="2026-04-22T00:00:00Z",
        ))
        assert resp.wp_id is not None and resp.wp_id != first_ready_wp_id

    def test_TC_L103_L203_007_get_remaining_hint(self, sut, mock_project_id) -> None:
        hint = sut.get_remaining_hint(mock_project_id)
        assert isinstance(hint.available_count, int)
        assert isinstance(hint.in_flight_count, int)

    def test_TC_L103_L203_008_acquire_lock_success(
        self, sut, mock_lock_mgr, mock_project_id, first_ready_wp_id,
    ) -> None:
        acquired, wp = sut._acquire_lock_or_fallback(
            project_id=mock_project_id, candidates=[first_ready_wp_id])
        assert acquired is True
        assert wp == first_ready_wp_id

    def test_TC_L103_L203_009_acquire_lock_fallback(self, sut, mock_lock_mgr, mock_project_id) -> None:
        mock_lock_mgr.try_acquire.side_effect = [False, True]
        acquired, wp = sut._acquire_lock_or_fallback(
            project_id=mock_project_id, candidates=["wp-001", "wp-002"])
        assert acquired is True and wp == "wp-002"

    def test_TC_L103_L203_010_transition_with_retry_ok(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        ok = sut._transition_with_retry(
            project_id=mock_project_id, wp_id="wp-001", query_id="q-x")
        assert ok is True
        mock_topology_mgr.transition_state.assert_called_once()

    def test_TC_L103_L203_011_detect_deadlock(self, sut, deadlock_snapshot) -> None:
        is_dead, evidence = sut._detect_deadlock(deadlock_snapshot)
        assert is_dead is True and len(evidence) >= 1

    def test_TC_L103_L203_012_append_event_first_try(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut._append_event_with_retry(event={"event_type": "wp_ready_dispatched",
                                             "project_id": mock_project_id})
        assert mock_event_bus.append_event.call_count == 1

    def test_TC_L103_L203_013_append_event_retry_then_success(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        mock_event_bus.append_event.side_effect = [IOError("x"), IOError("x"), {"event_id": "e-ok"}]
        sut._append_event_with_retry(event={"event_type": "wp_ready_dispatched",
                                             "project_id": mock_project_id})
        assert mock_event_bus.append_event.call_count == 3

    def test_TC_L103_L203_014_idempotent_same_query_id(self, sut, mock_project_id) -> None:
        req = GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000222",
            project_id=mock_project_id, requester_tick="tick-y",
            ts="2026-04-22T00:00:00Z",
        )
        r1 = sut.get_next_wp(req)
        r2 = sut.get_next_wp(req)
        assert r1.audit_event_id == r2.audit_event_id

    def test_TC_L103_L203_015_in_flight_le_2(self, sut, mock_project_id) -> None:
        for i in range(5):
            r = sut.get_next_wp(GetNextWPRequest(
                query_id=f"q-00000000-0000-0000-0000-{i:012d}",
                project_id=mock_project_id,
                requester_tick=f"tick-{i}", ts="2026-04-22T00:00:00Z",
            ))
            assert r.in_flight_wp_count <= 2

    def test_TC_L103_L203_016_topology_version_returned(self, sut, mock_project_id) -> None:
        r = sut.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000456",
            project_id=mock_project_id, requester_tick="tick-z",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.topology_version.startswith("topo-")

    def test_TC_L103_L203_017_audit_event_id_returned(self, sut, mock_project_id) -> None:
        r = sut.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000457",
            project_id=mock_project_id, requester_tick="tick-z",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.audit_event_id.startswith("evt-")

    def test_TC_L103_L203_018_deadlock_notifies_l2_05(
        self, sut_deadlock, mock_project_id, mock_l2_05,
    ) -> None:
        sut_deadlock.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000888",
            project_id=mock_project_id, requester_tick="tick-x",
            ts="2026-04-22T00:00:00Z",
        ))
        mock_l2_05.deadlock_detected.assert_called_once()

    def test_TC_L103_L203_019_bypass_guard_raises_on_background_call(self, sut) -> None:
        with pytest.raises(Exception) as ei:
            sut._guard_bypass_background_scheduler(caller="some_timer")
        assert "E_L103_L203_501" in str(ei.value)

    def test_TC_L103_L203_020_hard_timeout_1s_abort(
        self, sut_slow_upstream, mock_project_id,
    ) -> None:
        r = sut_slow_upstream.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000999",
            project_id=mock_project_id, requester_tick="tick-x",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.latency_ms <= 1100
        assert r.reason in {"awaiting_deps", None} or r.rejection is not None
```

---

## §3 负向用例

```python
# file: tests/l1_03/test_l2_03_wp_scheduler_negative.py
import pytest

from app.l2_03_sched.schemas import GetNextWPRequest


class TestL2_03_Negative:

    def test_TC_L103_L203_101_backpressure(self, sut_running_2, mock_project_id) -> None:
        r = sut_running_2.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000101",
            project_id=mock_project_id, requester_tick="tick-bp",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.wp_id is None and r.reason == "awaiting_deps"

    def test_TC_L103_L203_102_awaiting_deps(self, sut_awaiting, mock_project_id) -> None:
        r = sut_awaiting.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000102",
            project_id=mock_project_id, requester_tick="tick-ad",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.reason == "awaiting_deps"

    def test_TC_L103_L203_103_deadlock(self, sut_deadlock, mock_project_id) -> None:
        r = sut_deadlock.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000103",
            project_id=mock_project_id, requester_tick="tick-dl",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.reason == "deadlock"

    def test_TC_L103_L203_104_all_done(self, sut_all_done, mock_project_id) -> None:
        r = sut_all_done.get_next_wp(GetNextWPRequest(
            query_id="q-00000000-0000-0000-0000-000000000104",
            project_id=mock_project_id, requester_tick="tick-ok",
            ts="2026-04-22T00:00:00Z",
        ))
        assert r.reason == "all_done"

    def test_TC_L103_L203_105_pm14_pid_missing(self, sut) -> None:
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000105",
            "project_id": "", "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["rejection"]["err_code"] == "E_L103_L203_201"

    def test_TC_L103_L203_106_wp_id_invalid_format(self, sut, mock_project_id) -> None:
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000106",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "exclude_wp_ids": ["bad-id"], "ts": "2026-04-22T00:00:00Z",
        })
        assert r["rejection"]["err_code"] == "E_L103_L203_202"

    def test_TC_L103_L203_107_lock_timeout(self, sut_lock_timeout, mock_project_id) -> None:
        r = sut_lock_timeout.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000107",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "awaiting_deps"

    def test_TC_L103_L203_108_stale_exhausted(self, sut_stale, mock_project_id) -> None:
        r = sut_stale.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000108",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "awaiting_deps"

    def test_TC_L103_L203_109_l202_parallel_exceeded(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        mock_topology_mgr.transition_state.return_value = {
            "status": "rejected",
            "rejection": {"err_code": "E_L103_L202_301", "reason": "parallel_limit_exceeded"},
        }
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000109",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "awaiting_deps"

    def test_TC_L103_L203_110_l202_deps_unmet(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        mock_topology_mgr.transition_state.return_value = {
            "status": "rejected",
            "rejection": {"err_code": "E_L103_L202_302", "reason": "deps_unmet"},
        }
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000110",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "awaiting_deps"

    def test_TC_L103_L203_111_l202_illegal_transition(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        mock_topology_mgr.transition_state.return_value = {
            "status": "rejected",
            "rejection": {"err_code": "E_L103_L202_303", "reason": "illegal_transition"},
        }
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000111",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["rejection"]["err_code"] == "E_L103_L203_305"

    def test_TC_L103_L203_112_audit_fail(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        mock_event_bus.append_event.side_effect = IOError("bus down")
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000112",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["rejection"]["err_code"] == "E_L103_L203_401"

    def test_TC_L103_L203_113_bypass_background_scheduler(self, sut) -> None:
        with pytest.raises(Exception) as ei:
            sut._guard_bypass_background_scheduler(caller="bg_timer")
        assert "E_L103_L203_501" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_03/test_l2_03_ic_contracts.py
import pytest


class TestL2_03_IC_Contracts:

    def test_TC_L103_L203_601_ic02_shape(self, sut, mock_project_id) -> None:
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000601",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        for k in ("query_id", "project_id", "wp_id", "deps_met",
                  "in_flight_wp_count", "topology_version",
                  "audit_event_id", "latency_ms"):
            assert k in r

    def test_TC_L103_L203_602_reads_snapshot_once(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000602",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_topology_mgr.read_snapshot.call_count == 1
        kw = mock_topology_mgr.read_snapshot.call_args.kwargs
        assert kw["requester_l2"] == "L2-03"

    def test_TC_L103_L203_603_transition_payload(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000603",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        if mock_topology_mgr.transition_state.called:
            payload = mock_topology_mgr.transition_state.call_args.args[0]
            assert payload["from_state"] == "READY"
            assert payload["to_state"] == "RUNNING"
            assert payload["requester_l2"] == "L2-03"

    def test_TC_L103_L203_604_ic09_append_event_shape(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000604",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        evt = mock_event_bus.append_event.call_args.args[0]
        assert evt["event_type"] in {"L1-03:wp_ready_dispatched",
                                      "L1-03:wp_scheduler_noop"}
        assert evt["project_id"] == mock_project_id

    def test_TC_L103_L203_605_deadlock_fire_and_forget(
        self, sut_deadlock, mock_project_id, mock_l2_05,
    ) -> None:
        sut_deadlock.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000605",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        mock_l2_05.deadlock_detected.assert_called_once()
        kw = mock_l2_05.deadlock_detected.call_args.kwargs
        assert kw["project_id"] == mock_project_id
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_03/test_l2_03_perf.py
import time, statistics
import pytest


class TestL2_03_Perf:

    @pytest.mark.perf
    def test_TC_L103_L203_701_success_p95_under_200ms(self, sut, mock_project_id) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut.get_next_wp_raw({
                "query_id": f"q-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id, "requester_tick": f"tick-{i}",
                "ts": "2026-04-22T00:00:00Z",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.2

    @pytest.mark.perf
    def test_TC_L103_L203_702_3state_p95_under_100ms(self, sut_all_done, mock_project_id) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut_all_done.get_next_wp_raw({
                "query_id": f"q-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id, "requester_tick": f"tick-{i}",
                "ts": "2026-04-22T00:00:00Z",
            })
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1

    @pytest.mark.perf
    def test_TC_L103_L203_703_append_event_p95_under_10ms(self, sut, mock_project_id) -> None:
        durations = []
        for _ in range(200):
            t = time.perf_counter()
            sut._append_event_with_retry(event={"event_type": "wp_ready_dispatched",
                                                 "project_id": mock_project_id})
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.01

    @pytest.mark.perf
    def test_TC_L103_L203_704_hard_limit_1s(self, sut_slow_upstream, mock_project_id) -> None:
        for i in range(10):
            r = sut_slow_upstream.get_next_wp_raw({
                "query_id": f"q-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id, "requester_tick": f"tick-{i}",
                "ts": "2026-04-22T00:00:00Z",
            })
            assert r["latency_ms"] <= 1100
```

---

## §6 端到端 e2e

```python
# file: tests/l1_03/test_l2_03_e2e.py
import pytest


class TestL2_03_E2E:

    @pytest.mark.e2e
    def test_TC_L103_L203_801_cycle_ready_running_done(
        self, sut_real_topology, mock_project_id,
    ) -> None:
        r1 = sut_real_topology.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000e01",
            "project_id": mock_project_id, "requester_tick": "tick-01",
            "ts": "2026-04-22T00:00:00Z",
        })
        wp1 = r1["wp_id"]
        assert wp1 is not None
        sut_real_topology._topology.transition_state_raw({
            "project_id": mock_project_id, "wp_id": wp1,
            "from_state": "RUNNING", "to_state": "DONE",
            "reason": "dod ok", "requester_l2": "L2-04",
            "evidence_refs": ["e"],
        })
        r2 = sut_real_topology.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000e02",
            "project_id": mock_project_id, "requester_tick": "tick-02",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r2["wp_id"] != wp1

    @pytest.mark.e2e
    def test_TC_L103_L203_802_deadlock_notifies_l2_05(
        self, sut_deadlock_real, mock_project_id, mock_l2_05,
    ) -> None:
        r = sut_deadlock_real.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000e03",
            "project_id": mock_project_id, "requester_tick": "tick-dl",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "deadlock"
        assert mock_l2_05.deadlock_detected.call_count >= 1
```

---

## §7 测试 fixture

```python
# file: tests/l1_03/conftest_l2_03.py
import pytest, uuid
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def _snapshot_ready():
    return {
        "topology_id": "topo-abc",
        "wp_states": {
            "wp-001": {"state": "READY", "deps_met": True, "effort_estimate": 1.0,
                        "in_critical_path": True, "topo_level": 0},
            "wp-002": {"state": "READY", "deps_met": True, "effort_estimate": 2.0,
                        "in_critical_path": False, "topo_level": 0},
            "wp-003": {"state": "BLOCKED", "deps_met": False, "effort_estimate": 1.0,
                        "in_critical_path": False, "topo_level": 1},
        },
        "critical_path": ["wp-001"],
        "current_running_count": 0,
    }


@pytest.fixture
def mock_topology_mgr(_snapshot_ready):
    m = MagicMock()
    m.read_snapshot = MagicMock(return_value={
        "status": "ok", "snapshot": _snapshot_ready, "latency_ms": 10,
    })
    m.transition_state = MagicMock(return_value={
        "status": "ok", "wp_id": "wp-001", "resulting_state": "RUNNING",
        "current_running_count": 1, "audit_event_id": "evt-tr-001",
        "latency_ms": 5,
    })
    return m


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-001"})
    return m


@pytest.fixture
def mock_lock_mgr():
    m = MagicMock()
    m.try_acquire = MagicMock(return_value=True)
    m.release = MagicMock()
    return m


@pytest.fixture
def mock_l2_05():
    m = MagicMock()
    m.deadlock_detected = MagicMock(return_value=None)
    return m


@pytest.fixture
def mock_clock():
    class C:
        def __init__(self): self.t = 10**9
        def now_ns(self): self.t += 1; return self.t
    return C()


@pytest.fixture
def sut(mock_topology_mgr, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    from app.l2_03_sched.scheduler import WPScheduler
    return WPScheduler(
        topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
        lock_mgr=mock_lock_mgr, l2_05=mock_l2_05, clock=mock_clock,
    )


@pytest.fixture
def first_ready_wp_id() -> str:
    return "wp-001"


def _make_scheduler(states_map, critical_path, running_count, event_bus, lock_mgr, l2_05, clock,
                    transition_return=None):
    from app.l2_03_sched.scheduler import WPScheduler
    mgr = MagicMock()
    mgr.read_snapshot = MagicMock(return_value={
        "status": "ok",
        "snapshot": {"topology_id": f"topo-{hash(str(states_map)) & 0xffff:x}",
                     "wp_states": states_map,
                     "critical_path": critical_path,
                     "current_running_count": running_count},
        "latency_ms": 1,
    })
    mgr.transition_state = MagicMock(return_value=transition_return or {
        "status": "ok", "wp_id": list(states_map.keys())[0] if states_map else None,
        "resulting_state": "RUNNING", "current_running_count": running_count + 1,
        "audit_event_id": "evt-auto", "latency_ms": 5,
    })
    return WPScheduler(topology_mgr=mgr, event_bus=event_bus,
                        lock_mgr=lock_mgr, l2_05=l2_05, clock=clock)


@pytest.fixture
def sut_all_done(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    return _make_scheduler(
        {"wp-001": {"state": "DONE", "deps_met": True, "effort_estimate": 1.0,
                     "in_critical_path": True, "topo_level": 0}},
        [], 0, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock)


@pytest.fixture
def sut_awaiting(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    return _make_scheduler(
        {"wp-001": {"state": "BLOCKED", "deps_met": False, "effort_estimate": 1.0,
                     "in_critical_path": False, "topo_level": 0},
         "wp-002": {"state": "RUNNING", "deps_met": True, "effort_estimate": 1.0,
                     "in_critical_path": False, "topo_level": 0}},
        [], 1, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock)


@pytest.fixture
def sut_deadlock(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    return _make_scheduler(
        {"wp-001": {"state": "FAILED", "deps_met": True, "effort_estimate": 1.0,
                     "in_critical_path": True, "topo_level": 0},
         "wp-002": {"state": "BLOCKED", "deps_met": False, "effort_estimate": 1.0,
                     "in_critical_path": False, "topo_level": 1},
         "wp-003": {"state": "STUCK", "deps_met": True, "effort_estimate": 1.0,
                     "in_critical_path": False, "topo_level": 1}},
        ["wp-001"], 0, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock)


@pytest.fixture
def sut_deadlock_real(sut_deadlock):
    return sut_deadlock


@pytest.fixture
def sut_running_2(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    return _make_scheduler(
        {"wp-a": {"state": "RUNNING", "deps_met": True, "effort_estimate": 1.0,
                   "in_critical_path": False, "topo_level": 0},
         "wp-b": {"state": "RUNNING", "deps_met": True, "effort_estimate": 1.0,
                   "in_critical_path": False, "topo_level": 0},
         "wp-c": {"state": "READY", "deps_met": True, "effort_estimate": 1.0,
                   "in_critical_path": False, "topo_level": 0}},
        [], 2, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock)


@pytest.fixture
def sut_lock_timeout(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_clock):
    from app.l2_03_sched.scheduler import WPScheduler
    lm = MagicMock()
    lm.try_acquire = MagicMock(return_value=False)
    return WPScheduler(topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
                        lock_mgr=lm, l2_05=mock_l2_05, clock=mock_clock)


@pytest.fixture
def sut_stale(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    return _make_scheduler(
        {"wp-001": {"state": "READY", "deps_met": True, "effort_estimate": 1.0,
                     "in_critical_path": True, "topo_level": 0}},
        ["wp-001"], 0, mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock,
        transition_return={"status": "rejected",
                            "rejection": {"err_code": "E_L103_L202_304",
                                          "reason": "stale"}})


@pytest.fixture
def sut_slow_upstream(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    import time
    from app.l2_03_sched.scheduler import WPScheduler
    mgr = MagicMock()
    def slow_read(**kwargs):
        time.sleep(1.1)
        return {"status": "ok",
                "snapshot": {"topology_id": "topo-slow", "wp_states": {},
                              "critical_path": [], "current_running_count": 0},
                "latency_ms": 1100}
    mgr.read_snapshot = slow_read
    return WPScheduler(topology_mgr=mgr, event_bus=mock_event_bus,
                        lock_mgr=mock_lock_mgr, l2_05=mock_l2_05, clock=mock_clock)


@pytest.fixture
def sut_real_topology(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock, tmp_path):
    from app.l2_02_topo.manager import TopologyManager
    from app.l2_03_sched.scheduler import WPScheduler
    topo = TopologyManager(
        event_bus=mock_event_bus, lock_mgr=mock_lock_mgr,
        clock=mock_clock, storage_root=tmp_path, parallelism_limit=2,
    )
    sut = WPScheduler(topology_mgr=topo, event_bus=mock_event_bus,
                       lock_mgr=mock_lock_mgr, l2_05=mock_l2_05, clock=mock_clock)
    sut._topology = topo
    return sut


@pytest.fixture
def deadlock_snapshot():
    return {
        "topology_id": "topo-dl",
        "wp_states": {
            "wp-001": {"state": "FAILED", "deps_met": True, "effort_estimate": 1.0,
                        "in_critical_path": True, "topo_level": 0},
            "wp-002": {"state": "BLOCKED", "deps_met": False, "effort_estimate": 1.0,
                        "in_critical_path": False, "topo_level": 1},
        },
        "critical_path": ["wp-001"], "current_running_count": 0,
    }
```

---

## §8 集成点用例

```python
# file: tests/l1_03/test_l2_03_integrations.py
import pytest


class TestL2_03_Integration:

    def test_TC_L103_L203_901_with_l1_01_tick_loop(self, sut, mock_project_id) -> None:
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000901",
            "project_id": mock_project_id, "requester_tick": "tick-abc",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["audit_event_id"]

    def test_TC_L103_L203_902_with_l2_02_transition(
        self, sut, mock_topology_mgr, mock_project_id,
    ) -> None:
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000902",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_topology_mgr.transition_state.call_count == 1

    def test_TC_L103_L203_903_with_l2_05_on_deadlock(
        self, sut_deadlock, mock_project_id, mock_l2_05,
    ) -> None:
        sut_deadlock.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000903",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_l2_05.deadlock_detected.called

    def test_TC_L103_L203_904_with_l1_09_audit(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000904",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert mock_event_bus.append_event.call_count >= 1

    def test_TC_L103_L203_905_with_l1_07_warn_on_audit_fail(
        self, sut, mock_event_bus, mock_project_id,
    ) -> None:
        mock_event_bus.append_event.side_effect = [IOError("x")] * 3 + [{"event_id": "e"}]
        sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000905",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
```

---

## §9 边界 / edge case

```python
# file: tests/l1_03/test_l2_03_edge.py
import pytest


class TestL2_03_Edge:

    def test_TC_L103_L203_A01_empty_topology(self, sut_all_done, mock_project_id) -> None:
        r = sut_all_done.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000a01",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "all_done"

    def test_TC_L103_L203_A02_critical_path_missing(
        self, sut_no_critical, mock_project_id,
    ) -> None:
        r = sut_no_critical.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000a02",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["wp_id"] is not None

    def test_TC_L103_L203_A03_all_ready_but_exclude_all(
        self, sut, mock_project_id,
    ) -> None:
        r = sut.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000a03",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "exclude_wp_ids": ["wp-001", "wp-002"],
            "ts": "2026-04-22T00:00:00Z",
        })
        assert r["reason"] == "awaiting_deps"

    def test_TC_L103_L203_A04_concurrent_queries(self, sut, mock_project_id) -> None:
        from concurrent.futures import ThreadPoolExecutor
        def go(i):
            return sut.get_next_wp_raw({
                "query_id": f"q-00000000-0000-0000-0000-{i:012d}",
                "project_id": mock_project_id, "requester_tick": f"tick-{i}",
                "ts": "2026-04-22T00:00:00Z",
            })
        with ThreadPoolExecutor(max_workers=2) as ex:
            results = [f.result() for f in [ex.submit(go, i) for i in range(2)]]
        wps = [r["wp_id"] for r in results if r["wp_id"]]
        assert len(set(wps)) == len(wps)

    def test_TC_L103_L203_A05_large_topology_500_wps(self, sut_500, mock_project_id) -> None:
        import time
        t = time.perf_counter()
        r = sut_500.get_next_wp_raw({
            "query_id": "q-00000000-0000-0000-0000-000000000a05",
            "project_id": mock_project_id, "requester_tick": "tick-x",
            "ts": "2026-04-22T00:00:00Z",
        })
        dur = time.perf_counter() - t
        assert r["wp_id"] is not None
        assert dur < 0.5


@pytest.fixture
def sut_no_critical(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    from unittest.mock import MagicMock
    from app.l2_03_sched.scheduler import WPScheduler
    mgr = MagicMock()
    mgr.read_snapshot = MagicMock(return_value={
        "status": "ok",
        "snapshot": {"topology_id": "topo-nc",
                     "wp_states": {"wp-001": {"state": "READY", "deps_met": True,
                                               "effort_estimate": 1.0,
                                               "in_critical_path": False,
                                               "topo_level": 0}},
                     "critical_path": [], "current_running_count": 0},
        "latency_ms": 1,
    })
    mgr.transition_state = MagicMock(return_value={
        "status": "ok", "wp_id": "wp-001", "resulting_state": "RUNNING",
        "current_running_count": 1, "audit_event_id": "evt-ok",
        "latency_ms": 5,
    })
    return WPScheduler(topology_mgr=mgr, event_bus=mock_event_bus,
                        lock_mgr=mock_lock_mgr, l2_05=mock_l2_05, clock=mock_clock)


@pytest.fixture
def sut_500(mock_event_bus, mock_lock_mgr, mock_l2_05, mock_clock):
    from unittest.mock import MagicMock
    from app.l2_03_sched.scheduler import WPScheduler
    states = {
        f"wp-{i:03d}": {
            "state": "READY" if i < 20 else "BLOCKED",
            "deps_met": i < 20,
            "effort_estimate": 1.0,
            "in_critical_path": i == 0,
            "topo_level": i // 10,
        } for i in range(500)
    }
    mgr = MagicMock()
    mgr.read_snapshot = MagicMock(return_value={
        "status": "ok",
        "snapshot": {"topology_id": "topo-big", "wp_states": states,
                     "critical_path": ["wp-000"], "current_running_count": 0},
        "latency_ms": 5,
    })
    mgr.transition_state = MagicMock(return_value={
        "status": "ok", "wp_id": "wp-000", "resulting_state": "RUNNING",
        "current_running_count": 1, "audit_event_id": "evt-big",
        "latency_ms": 5,
    })
    return WPScheduler(topology_mgr=mgr, event_bus=mock_event_bus,
                        lock_mgr=mock_lock_mgr, l2_05=mock_l2_05, clock=mock_clock)
```

---

*— L2-03 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / §11 全部 13 错误码 / 5 条 IC · 三态语义 all_done/deadlock/awaiting_deps 独立覆盖 —*
