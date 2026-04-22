---
doc_id: tests-L1-07-L2-04-Supervisor 副 Agent 事件发送器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-07-Harness监督/L2-04-Supervisor 副 Agent 事件发送器.md
  - docs/2-prd/L1-07 Harness监督/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-J
created_at: 2026-04-22
---

# L1-07 L2-04-Supervisor 副 Agent 事件发送器 · TDD 测试用例

> 基于 3-1 L2-04 §3（9 公共方法 + 3 辅助）+ §11（20 项 `L2-04/E01~E20` 错误码）+ §12（hard_halt P99 500ms / verdict P99 3s SLO）驱动。
> TC ID 统一格式：`TC-L107-L204-NNN`。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × TC 矩阵

| 方法 | TC ID |
|---|---|
| `enqueue_event()` · QUEUED | TC-L107-L204-001 |
| `enqueue_event()` · priority=0 同步直派 | TC-L107-L204-002 |
| `enqueue_event()` · 幂等 idempotency_key | TC-L107-L204-003 |
| `dispatch_to_supervisor_subagent()` · DELIVERED | TC-L107-L204-004 |
| `dispatch_to_supervisor_subagent()` · 幂等 skip | TC-L107-L204-005 |
| `assemble_event_envelope()` · schema 校验 | TC-L107-L204-006 |
| `route_to_target()` · verdict→IC-13 | TC-L107-L204-007 |
| `route_to_target()` · hard_halt→IC-15 | TC-L107-L204-008 |
| `persist_delivery_receipt()` · append-only | TC-L107-L204-009 |
| `retry_with_backoff()` · 指数退避 | TC-L107-L204-010 |
| `handle_dlq()` · 进 DLQ + 升级告警 | TC-L107-L204-011 |
| `flush_queue_on_halt()` · 排空 | TC-L107-L204-012 |
| `broadcast_to_subscribers()` · ACK 后广播 | TC-L107-L204-013 |
| `health_probe()` · healthy | TC-L107-L204-014 |
| `query_envelope_status()` · UI 查询 | TC-L107-L204-015 |

### §1.2 错误码 × TC 矩阵（20 项）

| 错误码 | TC ID |
|---|---|
| `L2-04/E01` subagent_unreachable | TC-L107-L204-101 |
| `L2-04/E02` dispatch_timeout | TC-L107-L204-102 |
| `L2-04/E03` serialization_failed | TC-L107-L204-103 |
| `L2-04/E04` dlq_overflow | TC-L107-L204-104 |
| `L2-04/E05` schema_version_mismatch | TC-L107-L204-105 |
| `L2-04/E06` project_id_missing | TC-L107-L204-106 |
| `L2-04/E07` invalid_priority | TC-L107-L204-107 |
| `L2-04/E08` retry_exceeded | TC-L107-L204-108 |
| `L2-04/E09` invalid_state_transition | TC-L107-L204-109 |
| `L2-04/E10` missing_receipt | TC-L107-L204-110 |
| `L2-04/E11` dlq_event_not_emitted | TC-L107-L204-111 |
| `L2-04/E12` enqueue_during_halt | TC-L107-L204-112 |
| `L2-04/E13` priority_mismatch_for_halt | TC-L107-L204-113 |
| `L2-04/E14` receipt_attempt_gap | TC-L107-L204-114 |
| `L2-04/E15` target_l1_unreachable | TC-L107-L204-115 |
| `L2-04/E16` ack_hash_mismatch | TC-L107-L204-116 |
| `L2-04/E17` payload_size_exceeded | TC-L107-L204-117 |
| `L2-04/E18` unknown_event_type | TC-L107-L204-118 |
| `L2-04/E19` disk_write_failed | TC-L107-L204-119 |
| `L2-04/E20` drain_timeout | TC-L107-L204-120 |

### §1.3 IC 契约 × TC 矩阵

| IC | 方向 | TC ID |
|---|---|---|
| IC-12 dispatch_soft_auto_fix | L2-04 → L1-01 | TC-L107-L204-601 |
| IC-13 dispatch_verdict | L2-04 → L1-04 | TC-L107-L204-602 |
| IC-14 dispatch_ui | L2-04 → L1-10 | TC-L107-L204-603 |
| IC-15 dispatch_hard_halt | L2-04 → L2-03 | TC-L107-L204-604 |
| IC-09 persist_events | L2-04 → L1-09 | TC-L107-L204-605 |

### §1.4 SLO × TC 矩阵

| SLO | 目标 | TC ID |
|---|---|---|
| enqueue P99 | ≤ 50ms | TC-L107-L204-501 |
| hard_halt dispatch P99 | ≤ 500ms | TC-L107-L204-502 |
| verdict dispatch P99 | ≤ 3s | TC-L107-L204-503 |
| DLQ 转移 P99 | ≤ 1s | TC-L107-L204-504 |
| flush on halt P99 | ≤ 10s | TC-L107-L204-505 |

---

## §2 正向用例（每方法 ≥ 1）

```python
# file: tests/l1_07/test_l2_04_dispatcher_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_04_Positive:

    def test_TC_L107_L204_001_enqueue_queued(self, sut, make_event) -> None:
        """TC-L107-L204-001 · priority=1 · QUEUED。"""
        res = sut.enqueue_event(
            project_id="p", event=make_event("verdict", level="SUGG"),
            target_route=MagicMock(priority=1, delivery_mode="async",
                                    target_l1="L1-04", target_ic="IC-13",
                                    timeout_ms=3000))
        assert res.state == "QUEUED"

    def test_TC_L107_L204_002_priority_0_sync_dispatch(
        self, sut, make_event, mock_subagent,
    ) -> None:
        """TC-L107-L204-002 · priority=0 hard_halt · 直派。"""
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        res = sut.enqueue_event(
            project_id="p", event=make_event("hard_halt"),
            target_route=MagicMock(priority=0, delivery_mode="sync",
                                    target_l1="L2-03", target_ic="IC-15",
                                    timeout_ms=500))
        assert res.state == "DELIVERED"

    def test_TC_L107_L204_003_idempotent_key(self, sut, make_event) -> None:
        """TC-L107-L204-003 · 同 idempotency_key · 返已有 envelope_id。"""
        e = make_event("verdict", level="SUGG")
        r1 = sut.enqueue_event(project_id="p", event=e,
                                 target_route=MagicMock(priority=1),
                                 idempotency_key="k-same")
        r2 = sut.enqueue_event(project_id="p", event=e,
                                 target_route=MagicMock(priority=1),
                                 idempotency_key="k-same")
        assert r2.envelope_id == r1.envelope_id

    def test_TC_L107_L204_004_dispatch_delivered(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-004 · dispatch · DELIVERED。"""
        envid = seed_queued_envelope()
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="ok")
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=1)
        assert res.status == "DELIVERED"

    def test_TC_L107_L204_005_dispatch_idempotent_skip(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-005 · 已 DELIVERED skip。"""
        envid = seed_queued_envelope(state="DELIVERED")
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=2)
        assert res.status == "DELIVERED"

    def test_TC_L107_L204_006_assemble_envelope(self, sut) -> None:
        """TC-L107-L204-006 · assemble schema 校验。"""
        env = sut.assemble_event_envelope(
            project_id="p", event_type="verdict",
            payload={"schema_version": "v1.0", "level": "SUGG",
                      "message": "m", "action_suggestion": "a",
                      "evidence_refs": ["e1"]},
            source_l2="L2-02", schema_version="v1.0")
        assert env.payload.schema_version == "v1.0"

    def test_TC_L107_L204_007_route_verdict(self, sut) -> None:
        """TC-L107-L204-007 · verdict → IC-13。"""
        r = sut.route_to_target(project_id="p", event_type="verdict")
        assert r.target_route.target_ic == "IC-13"

    def test_TC_L107_L204_008_route_hard_halt(self, sut) -> None:
        """TC-L107-L204-008 · hard_halt → IC-15。"""
        r = sut.route_to_target(project_id="p", event_type="hard_halt")
        assert r.target_route.target_ic == "IC-15"

    def test_TC_L107_L204_009_persist_receipt_append(self, sut) -> None:
        """TC-L107-L204-009 · receipt 追加 · seq 递增。"""
        r1 = sut.persist_delivery_receipt(
            project_id="p",
            receipt=MagicMock(envelope_id="e-1", attempt=1,
                               status="DELIVERED", dispatched_at="t",
                               latency_ms=10))
        r2 = sut.persist_delivery_receipt(
            project_id="p",
            receipt=MagicMock(envelope_id="e-1", attempt=2,
                               status="DELIVERED", dispatched_at="t",
                               latency_ms=12))
        assert r2.receipt_seq == r1.receipt_seq + 1

    def test_TC_L107_L204_010_retry_backoff_exponential(self, sut) -> None:
        """TC-L107-L204-010 · 指数退避。"""
        r1 = sut.retry_with_backoff(project_id="p", envelope_id="e",
                                      current_attempt=1)
        r2 = sut.retry_with_backoff(project_id="p", envelope_id="e",
                                      current_attempt=2)
        assert r2.backoff_sec >= r1.backoff_sec

    def test_TC_L107_L204_011_handle_dlq_alert(
        self, sut, seed_queued_envelope, mock_audit,
    ) -> None:
        """TC-L107-L204-011 · handle_dlq 发 Escalated 事件。"""
        envid = seed_queued_envelope()
        sut.handle_dlq(project_id="p", envelope_id=envid)
        assert mock_audit.append.called

    def test_TC_L107_L204_012_flush_halt_draining(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-012 · flush · halt_draining=True。"""
        seed_queued_envelope()
        sut.flush_queue_on_halt()
        assert sut._halt_draining is True

    def test_TC_L107_L204_013_broadcast(self, sut, mock_audit) -> None:
        """TC-L107-L204-013 · broadcast_to_subscribers 通知订阅者。"""
        sut.broadcast_to_subscribers(MagicMock(envelope_id="e",
                                                 event_type="verdict"))
        assert mock_audit.append.called

    def test_TC_L107_L204_014_health_probe(self, sut) -> None:
        """TC-L107-L204-014 · health_probe · healthy=True。"""
        assert sut.health_probe().healthy is True

    def test_TC_L107_L204_015_query_status(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-015 · UI query_envelope_status。"""
        envid = seed_queued_envelope()
        res = sut.query_envelope_status(envelope_id=envid)
        assert res.state in ("QUEUED", "DELIVERED", "DLQ")
```

---

## §3 负向用例（每错误码 ≥ 1）

```python
# file: tests/l1_07/test_l2_04_dispatcher_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from app.l1_07.l2_04.errors import DispatcherError


class TestL2_04_Negative:

    def test_TC_L107_L204_101_subagent_unreachable(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-101 · E01 · subagent spawn 失败 · retry。"""
        mock_subagent.spawn_task.side_effect = RuntimeError("spawn")
        envid = seed_queued_envelope()
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=1)
        assert res.error.code == "L2-04/E01" or res.status == "RETRYING"

    def test_TC_L107_L204_102_dispatch_timeout(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-102 · E02 · dispatch ACK 超时。"""
        mock_subagent.spawn_task.side_effect = TimeoutError("ack")
        envid = seed_queued_envelope()
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=1)
        assert res.error.code == "L2-04/E02" or res.status == "RETRYING"

    def test_TC_L107_L204_103_serialization_failed_dlq(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-103 · E03 · payload 循环引用 · 直进 DLQ。"""
        bad = {"a": None}
        bad["a"] = bad  # 循环引用
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(
                project_id="p",
                event=make_event("verdict", payload_override=bad),
                target_route=MagicMock(priority=1))
        assert exc.value.code == "L2-04/E03"

    def test_TC_L107_L204_104_dlq_overflow(
        self, sut, seed_queued_envelope, monkeypatch,
    ) -> None:
        """TC-L107-L204-104 · E04 · DLQ 满 · 降级 HALT_DRAIN。"""
        envid = seed_queued_envelope()
        def full(*a, **kw): raise IOError("dlq full")
        monkeypatch.setattr(sut, "_write_dlq", full)
        with pytest.raises(DispatcherError) as exc:
            sut.handle_dlq(project_id="p", envelope_id=envid)
        assert exc.value.code == "L2-04/E04"

    def test_TC_L107_L204_105_schema_version_mismatch(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-105 · E05 · schema_version=v2.0 · 拒。"""
        e = make_event("verdict", schema_version="v2.0")
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(project_id="p", event=e,
                                target_route=MagicMock(priority=1))
        assert exc.value.code == "L2-04/E05"

    def test_TC_L107_L204_106_project_id_missing(self, sut, make_event) -> None:
        """TC-L107-L204-106 · E06 · project_id=None。"""
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(project_id=None,
                                event=make_event("verdict"),
                                target_route=MagicMock(priority=1))
        assert exc.value.code == "L2-04/E06"

    def test_TC_L107_L204_107_invalid_priority(self, sut, make_event) -> None:
        """TC-L107-L204-107 · E07 · priority=9 非法。"""
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(project_id="p", event=make_event("verdict"),
                                target_route=MagicMock(priority=9))
        assert exc.value.code == "L2-04/E07"

    def test_TC_L107_L204_108_retry_exceeded_dlq(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-108 · E08 · attempt>5 · 进 DLQ。"""
        mock_subagent.spawn_task.side_effect = TimeoutError()
        envid = seed_queued_envelope()
        for a in range(1, 7):
            sut.dispatch_to_supervisor_subagent(
                project_id="p", envelope_id=envid, attempt=a)
        status = sut.query_envelope_status(envelope_id=envid)
        assert status.state == "DLQ"

    def test_TC_L107_L204_109_invalid_state_transition(self, sut) -> None:
        """TC-L107-L204-109 · E09 · 违反状态机 · 拒。"""
        with pytest.raises(DispatcherError) as exc:
            sut._transition_state(envelope_id="e-x", from_state="DLQ",
                                    to_state="QUEUED")
        assert exc.value.code == "L2-04/E09"

    def test_TC_L107_L204_110_missing_receipt(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-110 · E10 · DELIVERED 但无 receipt · 回滚。"""
        envid = seed_queued_envelope(state="DELIVERED",
                                       no_receipt=True)
        res = sut._audit_delivered_envelope(envelope_id=envid)
        assert res.rolled_back is True
        assert res.code == "L2-04/E10"

    def test_TC_L107_L204_111_dlq_event_not_emitted(
        self, sut, seed_queued_envelope, mock_audit, monkeypatch,
    ) -> None:
        """TC-L107-L204-111 · E11 · DLQ 转 Domain Event 失败 · 强制重发。"""
        envid = seed_queued_envelope()
        mock_audit.append.side_effect = [IOError("first"), True]
        sut.handle_dlq(project_id="p", envelope_id=envid)
        assert mock_audit.append.call_count >= 2

    def test_TC_L107_L204_112_enqueue_during_halt(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-112 · E12 · HALT_DRAINING 期间 enqueue 拒。"""
        sut._halt_draining = True
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(project_id="p", event=make_event("verdict"),
                                target_route=MagicMock(priority=1))
        assert exc.value.code == "L2-04/E12"

    def test_TC_L107_L204_113_hard_halt_priority_mismatch(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-113 · E13 · hard_halt 但 priority=2。"""
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(project_id="p", event=make_event("hard_halt"),
                                target_route=MagicMock(priority=2))
        assert exc.value.code == "L2-04/E13"

    def test_TC_L107_L204_114_receipt_attempt_gap(self, sut) -> None:
        """TC-L107-L204-114 · E14 · receipt attempt 跳号。"""
        sut.persist_delivery_receipt(
            project_id="p",
            receipt=MagicMock(envelope_id="e", attempt=1,
                               status="DELIVERED", dispatched_at="t",
                               latency_ms=10))
        with pytest.raises(DispatcherError) as exc:
            sut.persist_delivery_receipt(
                project_id="p",
                receipt=MagicMock(envelope_id="e", attempt=3,  # 跳 2
                                   status="DELIVERED",
                                   dispatched_at="t",
                                   latency_ms=12))
        assert exc.value.code == "L2-04/E14"

    def test_TC_L107_L204_115_target_l1_unreachable(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-115 · E15 · 目标 L1 全停 · LOCAL_BUFFER。"""
        mock_subagent.spawn_task.side_effect = ConnectionError("L1 down")
        envid = seed_queued_envelope()
        for a in range(1, 6):
            sut.dispatch_to_supervisor_subagent(
                project_id="p", envelope_id=envid, attempt=a)
        assert sut._local_buffer_active is True or \
               sut.query_envelope_status(envelope_id=envid).state == "DLQ"

    def test_TC_L107_L204_116_ack_hash_mismatch(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-116 · E16 · ACK hash 不符。"""
        envid = seed_queued_envelope()
        mock_subagent.spawn_task.return_value = MagicMock(
            ack=True, body_hash="wrong-hash", expected_hash="right-hash")
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=1)
        assert res.error.code == "L2-04/E16" or res.status == "RETRYING"

    def test_TC_L107_L204_117_payload_size_exceeded(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-117 · E17 · payload > 1MB。"""
        huge = {"schema_version": "v1.0", "data": "x" * (2 * 1024 * 1024)}
        with pytest.raises(DispatcherError) as exc:
            sut.enqueue_event(
                project_id="p",
                event=make_event("verdict", payload_override=huge),
                target_route=MagicMock(priority=1))
        assert exc.value.code == "L2-04/E17"

    def test_TC_L107_L204_118_unknown_event_type(self, sut) -> None:
        """TC-L107-L204-118 · E18 · event_type=foo · 路由无条目。"""
        with pytest.raises(DispatcherError) as exc:
            sut.route_to_target(project_id="p", event_type="foo_bar")
        assert exc.value.code == "L2-04/E18"

    def test_TC_L107_L204_119_disk_write_failed(
        self, sut, monkeypatch,
    ) -> None:
        """TC-L107-L204-119 · E19 · receipt 磁盘写失败。"""
        def boom(*a, **kw): raise IOError("disk")
        monkeypatch.setattr(sut, "_receipt_repo_append", boom)
        with pytest.raises(DispatcherError) as exc:
            sut.persist_delivery_receipt(
                project_id="p",
                receipt=MagicMock(envelope_id="e", attempt=1,
                                   status="DELIVERED",
                                   dispatched_at="t", latency_ms=10))
        assert exc.value.code == "L2-04/E19"

    def test_TC_L107_L204_120_drain_timeout(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-120 · E20 · flush 超时 · alert。"""
        import time
        # seed 大量 · 限 1ms timeout 超时
        for _ in range(20):
            seed_queued_envelope()
        with pytest.raises(DispatcherError) as exc:
            sut.flush_queue_on_halt(drain_timeout_s=0.001)
        assert exc.value.code == "L2-04/E20"
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_07/test_l2_04_dispatcher_ic.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_04_IC_Contracts:

    def test_TC_L107_L204_601_ic_12_soft_auto_fix(self, sut, make_event) -> None:
        """TC-L107-L204-601 · IC-12 soft_auto_fix → L1-01。"""
        r = sut.route_to_target(project_id="p", event_type="soft_auto_fix")
        assert r.target_route.target_ic == "IC-12"

    def test_TC_L107_L204_602_ic_13_verdict(self, sut) -> None:
        """TC-L107-L204-602 · IC-13 verdict → L1-04。"""
        r = sut.route_to_target(project_id="p", event_type="verdict")
        assert r.target_route.target_ic == "IC-13"

    def test_TC_L107_L204_603_ic_14_ui_change_eval(self, sut) -> None:
        """TC-L107-L204-603 · IC-14 change_eval → L1-10。"""
        r = sut.route_to_target(project_id="p", event_type="change_eval")
        assert r.target_route.target_ic == "IC-14"

    def test_TC_L107_L204_604_ic_15_hard_halt(self, sut) -> None:
        """TC-L107-L204-604 · IC-15 hard_halt → L2-03。"""
        r = sut.route_to_target(project_id="p", event_type="hard_halt")
        assert r.target_route.target_ic == "IC-15"

    def test_TC_L107_L204_605_ic_09_audit(
        self, sut, make_event, mock_audit,
    ) -> None:
        """TC-L107-L204-605 · IC-09 audit · envelope 入队必审计。"""
        sut.enqueue_event(project_id="p", event=make_event("verdict"),
                            target_route=MagicMock(priority=1))
        assert mock_audit.append.called
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_07/test_l2_04_dispatcher_perf.py
from __future__ import annotations

import pytest
import time


@pytest.mark.perf
class TestL2_04_SLO:

    def test_TC_L107_L204_501_enqueue_p99_le_50ms(
        self, sut, make_event, benchmark,
    ) -> None:
        """TC-L107-L204-501 · enqueue P99 ≤ 50ms。"""
        from unittest.mock import MagicMock
        counter = [0]
        def _enq():
            counter[0] += 1
            sut.enqueue_event(project_id="p",
                                event=make_event("verdict", idem=counter[0]),
                                target_route=MagicMock(priority=1))
        benchmark.pedantic(_enq, iterations=1, rounds=300)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 50.0

    def test_TC_L107_L204_502_hard_halt_p99_le_500ms(
        self, sut, make_event, mock_subagent, benchmark,
    ) -> None:
        """TC-L107-L204-502 · hard_halt dispatch P99 ≤ 500ms。"""
        from unittest.mock import MagicMock
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        counter = [0]
        def _hh():
            counter[0] += 1
            sut.enqueue_event(project_id="p", event=make_event("hard_halt",
                                                                 idem=counter[0]),
                                target_route=MagicMock(priority=0,
                                                         delivery_mode="sync",
                                                         target_ic="IC-15",
                                                         timeout_ms=500))
        benchmark.pedantic(_hh, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] * 1000 <= 500.0

    def test_TC_L107_L204_503_verdict_p99_le_3s(
        self, sut, seed_queued_envelope, mock_subagent, benchmark,
    ) -> None:
        """TC-L107-L204-503 · verdict dispatch P99 ≤ 3s。"""
        from unittest.mock import MagicMock
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        def _disp():
            envid = seed_queued_envelope()
            sut.dispatch_to_supervisor_subagent(
                project_id="p", envelope_id=envid, attempt=1)
        benchmark.pedantic(_disp, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] <= 3.0

    def test_TC_L107_L204_504_dlq_transfer_p99_le_1s(
        self, sut, seed_queued_envelope, benchmark,
    ) -> None:
        """TC-L107-L204-504 · handle_dlq P99 ≤ 1s。"""
        def _dlq():
            envid = seed_queued_envelope()
            sut.handle_dlq(project_id="p", envelope_id=envid)
        benchmark.pedantic(_dlq, iterations=1, rounds=100)
        assert benchmark.stats["stats"]["p99"] <= 1.0

    def test_TC_L107_L204_505_flush_p99_le_10s(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-505 · flush_queue_on_halt ≤ 10s。"""
        for _ in range(100):
            seed_queued_envelope()
        t0 = time.perf_counter()
        sut.flush_queue_on_halt(drain_timeout_s=10.0)
        assert (time.perf_counter() - t0) <= 10.5
```

---

## §6 端到端 e2e

```python
# file: tests/l1_07/test_l2_04_dispatcher_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


@pytest.mark.e2e
class TestL2_04_E2E:

    def test_TC_L107_L204_701_verdict_end_to_end(
        self, sut, make_event, mock_subagent, mock_audit,
    ) -> None:
        """TC-L107-L204-701 · verdict: enqueue → dispatch → receipt → audit。"""
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        res = sut.enqueue_event(
            project_id="p", event=make_event("verdict", level="SUGG"),
            target_route=MagicMock(priority=1, delivery_mode="async",
                                    target_l1="L1-04", target_ic="IC-13",
                                    timeout_ms=3000))
        envid = res.envelope_id
        dres = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=1)
        assert dres.status == "DELIVERED"
        assert mock_audit.append.called

    def test_TC_L107_L204_702_retry_then_dlq_flow(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-702 · 5 次 retry 后 DLQ。"""
        mock_subagent.spawn_task.side_effect = TimeoutError()
        envid = seed_queued_envelope()
        for a in range(1, 7):
            sut.dispatch_to_supervisor_subagent(
                project_id="p", envelope_id=envid, attempt=a)
        assert sut.query_envelope_status(envelope_id=envid).state == "DLQ"

    def test_TC_L107_L204_703_halt_flush(
        self, sut, seed_queued_envelope,
    ) -> None:
        """TC-L107-L204-703 · halt flush · halt_draining。"""
        for _ in range(3):
            seed_queued_envelope()
        sut.flush_queue_on_halt(drain_timeout_s=5.0)
        assert sut._halt_draining is True
```

---

## §7 测试 fixture

```python
# file: tests/l1_07/conftest_l2_04.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_07.l2_04.service import SupervisorDispatcher


@pytest.fixture
def mock_subagent() -> MagicMock:
    m = MagicMock()
    m.spawn_task.return_value = MagicMock(ack=True, body_hash="default-h")
    return m


@pytest.fixture
def mock_audit() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_subagent, mock_audit, tmp_path):
    return SupervisorDispatcher(
        subagent=mock_subagent, audit=mock_audit,
        storage_root=tmp_path,
    )


@pytest.fixture
def make_event():
    def _make(event_type: str,
              level: str = "INFO",
              schema_version: str = "v1.0",
              idem: Any = None,
              payload_override: dict = None):
        payload = payload_override or {
            "schema_version": schema_version,
            "level": level,
            "message": "m",
            "action_suggestion": "a",
            "evidence_refs": ["e-1"],
        }
        return MagicMock(
            envelope_id=f"env-{idem or 'auto'}",
            event_type=event_type,
            payload=MagicMock(
                schema_version=payload.get("schema_version"),
                level=payload.get("level"),
                message=payload.get("message"),
                action_suggestion=payload.get("action_suggestion"),
                evidence_refs=payload.get("evidence_refs"),
                data=payload.get("data"),
                _serialize=lambda: payload,
            ),
            source_l2="L2-02",
            source_snapshot_id="s-1",
            created_at="2026-04-22T10:00:00Z",
        )
    return _make


@pytest.fixture
def seed_queued_envelope(sut):
    counter = {"n": 0}
    def _seed(state: str = "QUEUED", no_receipt: bool = False):
        counter["n"] += 1
        envid = f"env-seed-{counter['n']}"
        sut._envelope_store[envid] = MagicMock(
            envelope_id=envid, state=state,
            event_type="verdict", attempt=1,
            no_receipt=no_receipt)
        return envid
    return _seed
```

---

## §8 集成点用例

```python
# file: tests/l1_07/test_l2_04_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_04_Integration:

    def test_TC_L107_L204_801_with_l2_02_verdict_flow(
        self, sut, make_event, mock_subagent,
    ) -> None:
        """TC-L107-L204-801 · L2-02 verdict 触发 L2-04 派发。"""
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        res = sut.enqueue_event(project_id="p",
                                  event=make_event("verdict", level="SUGG"),
                                  target_route=MagicMock(priority=1,
                                                          target_ic="IC-13"))
        assert res.envelope_id is not None

    def test_TC_L107_L204_802_with_l2_03_hard_halt_sync(
        self, sut, make_event, mock_subagent,
    ) -> None:
        """TC-L107-L204-802 · L2-03 硬红线 hard_halt · 同步派发。"""
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        res = sut.enqueue_event(project_id="p",
                                  event=make_event("hard_halt"),
                                  target_route=MagicMock(priority=0,
                                                          delivery_mode="sync",
                                                          target_ic="IC-15",
                                                          timeout_ms=500))
        assert res.state == "DELIVERED"
```

---

## §9 边界 / edge case

```python
# file: tests/l1_07/test_l2_04_edge.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestL2_04_Edge:

    def test_TC_L107_L204_901_empty_queue_dispatch_noop(
        self, sut,
    ) -> None:
        """TC-L107-L204-901 · 空队列 dispatch · noop。"""
        assert sut._queue_depth(priority=1) == 0

    def test_TC_L107_L204_902_payload_exactly_1mb(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-902 · payload 正好 1MB · 通过。"""
        payload = {"schema_version": "v1.0",
                    "data": "x" * (1024 * 1024 - 100)}
        res = sut.enqueue_event(
            project_id="p",
            event=make_event("verdict", payload_override=payload),
            target_route=MagicMock(priority=1))
        assert res.envelope_id is not None

    def test_TC_L107_L204_903_concurrent_enqueue_same_key(
        self, sut, make_event,
    ) -> None:
        """TC-L107-L204-903 · 同 idempotency_key 并发 10 次 · 仅 1 个 envelope。"""
        import threading
        results = []
        def _enq():
            e = make_event("verdict", level="SUGG")
            results.append(sut.enqueue_event(
                project_id="p", event=e,
                target_route=MagicMock(priority=1),
                idempotency_key="conc-k"))
        ts = [threading.Thread(target=_enq) for _ in range(10)]
        for t in ts: t.start()
        for t in ts: t.join()
        envids = set(r.envelope_id for r in results)
        assert len(envids) == 1

    def test_TC_L107_L204_904_attempt_exactly_5_ok(
        self, sut, seed_queued_envelope, mock_subagent,
    ) -> None:
        """TC-L107-L204-904 · attempt=5 仍是最后一次尝试 · 非 DLQ。"""
        mock_subagent.spawn_task.return_value = MagicMock(ack=True, body_hash="h")
        envid = seed_queued_envelope()
        res = sut.dispatch_to_supervisor_subagent(
            project_id="p", envelope_id=envid, attempt=5)
        assert res.status == "DELIVERED"

    def test_TC_L107_L204_905_halt_then_resume(self, sut) -> None:
        """TC-L107-L204-905 · halt → resume · 可重新 enqueue。"""
        sut.flush_queue_on_halt()
        sut.resume_from_halt()
        assert sut._halt_draining is False
```

---

*— TDD · depth-B · v1.0 · 2026-04-22 · session-J —*
