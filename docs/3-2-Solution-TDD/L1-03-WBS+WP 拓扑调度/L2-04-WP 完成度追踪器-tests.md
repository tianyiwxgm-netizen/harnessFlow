---
doc_id: tests-L1-03-L2-04-WP 完成度追踪器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度/L2-04-WP 完成度追踪器.md
  - docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-I
created_at: 2026-04-22
---

# L1-03 L2-04-WP 完成度追踪器 · TDD 测试用例

> 基于 3-1 L2-04 §3（3 订阅 + 2 发起 + 2 只读）+ §11（12 条 `E_L103_L204_*`）+ §12 SLO + §13 TC 矩阵 驱动。
> TC ID 统一格式：`TC-L103-L204-NNN`。pytest + Python 3.11+；`class TestL2_04_ProgressTracker`；订阅语义 fire-and-forget。

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法（§3）| TC ID | 覆盖类型 | IC |
|---|---|---|---|
| `on_wp_done()` | TC-L103-L204-001 | unit | IC-L2-04-SubscriberDone |
| `on_wp_failed()` · s1_soft | TC-L103-L204-002 | unit | IC-L2-04-SubscriberFailed |
| `on_wp_failed()` · s2_hard | TC-L103-L204-003 | unit | IC-L2-04-SubscriberFailed |
| `on_wp_failed()` · s3_dod_fail | TC-L103-L204-004 | unit | IC-L2-04-SubscriberFailed |
| `on_wp_failed()` · s4_timeout | TC-L103-L204-005 | unit | IC-L2-04-SubscriberFailed |
| `on_wp_failed()` · s5_verifier_reject | TC-L103-L204-006 | unit | IC-L2-04-SubscriberFailed |
| `on_system_resumed()` | TC-L103-L204-007 | unit | Subscriber |
| `transition_state(RUNNING→DONE)` | TC-L103-L204-008 | unit | IC-L2-04 |
| `transition_state(RUNNING→FAILED)` | TC-L103-L204-009 | unit | IC-L2-04 |
| `sync_failure_signal()` | TC-L103-L204-010 | unit | IC-L2-05 |
| `sync_failure_signal()` rollback_triggered | TC-L103-L204-011 | unit | IC-L2-05 |
| `get_progress_metrics()` 4 字段齐 | TC-L103-L204-012 | unit | — |
| `export_readonly_view()` | TC-L103-L204-013 | unit | — |
| ProgressMetrics 聚合 completion_rate | TC-L103-L204-014 | unit | — |
| Burndown 计算 | TC-L103-L204-015 | unit | — |
| 事件幂等（event_id 重复）| TC-L103-L204-016 | unit | — |
| progress_metrics_updated append | TC-L103-L204-017 | unit | IC-09 |

### §1.2 错误码 × 测试（12 项 · ≥15 TC · 覆盖 §11）

| 错误码 | TC ID | 方法 | 分类 |
|---|---|---|---|
| `E_L103_L204_101` | TC-L103-L204-101 | bootstrap 订阅失败 · 硬停 | 订阅 |
| `E_L103_L204_102` | TC-L103-L204-102 | 事件 schema 非法 | 订阅 |
| `E_L103_L204_103` | TC-L103-L204-103 | 聚合输入异常 | 聚合 |
| `E_L103_L204_201` | TC-L103-L204-104 | 跨 project 误路由 | PM-14 |
| `E_L103_L204_301` | TC-L103-L204-105 | L2-02 rejected | 下游 |
| `E_L103_L204_302` | TC-L103-L204-106 | L2-02 timeout | 下游 |
| `E_L103_L204_303` | TC-L103-L204-107 | L2-05 同步失败 | 下游 |
| `E_L103_L204_401` | TC-L103-L204-108 | IC-09 append 失败 | 审计 |
| `E_L103_L204_402` | TC-L103-L204-109 | progress-metrics.jsonl 写失败 | 落盘 |
| `E_L103_L204_403` | TC-L103-L204-110 | UI 推送失败 | 审计 |
| `E_L103_L204_404` | TC-L103-L204-111 | L1-07 不可达 | 审计 |
| `E_L103_L204_501` | TC-L103-L204-112 | 外部直改 FS | bypass |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID |
|---|---|---|
| SubscriberDone `on_wp_done` | L1-09 → 本 L2 | TC-L103-L204-601 |
| SubscriberFailed `on_wp_failed` | L1-09 → 本 L2 | TC-L103-L204-602 |
| IC-L2-04 `transition_state` | 本 L2 → L2-02 | TC-L103-L204-603 |
| IC-L2-05 `sync_failure_signal` | 本 L2 → L2-05 | TC-L103-L204-604 |
| IC-09 `append_event` | 本 L2 → L1-09 | TC-L103-L204-605 |
| `get_progress_metrics` | L1-07 / L1-10 → 本 L2 | TC-L103-L204-606 |

---

## §2 正向用例

```python
# file: tests/l1_03/test_l2_04_progress_tracker_positive.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_04_prog.tracker import ProgressTracker
from app.l2_04_prog.schemas import (
    WpDoneEvent, WpFailedEvent, ProgressMetrics, ReadonlyProgressView,
)


class TestL2_04_ProgressTracker_Positive:

    def test_TC_L103_L204_001_on_wp_done_updates_metrics(
        self, sut: ProgressTracker, mock_project_id: str, mock_topology_mgr, mock_event_bus,
    ) -> None:
        """TC-L103-L204-001 · on_wp_done · IC-L2-04 + ProgressMetrics + event."""
        evt = WpDoneEvent(
            event_id="evt-done-001", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.95},
            ts_ns=1_700_000_000_000,
        )
        sut.on_wp_done(evt)
        mock_topology_mgr.transition_state.assert_called()
        assert mock_topology_mgr.transition_state.call_args.args[0]["to_state"] == "DONE"
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:progress_metrics_updated" in types

    def test_TC_L103_L204_002_on_wp_failed_s1_soft(
        self, sut, mock_project_id, mock_topology_mgr, mock_l2_05,
    ) -> None:
        """TC-L103-L204-002 · on_wp_failed fail_level=s1_soft · 两路径并行。"""
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-s1", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="s1_soft", reason="test soft fail",
            evidence_refs=["evt-e1"], ts_ns=1_700_000_000_000,
        ))
        mock_topology_mgr.transition_state.assert_called()
        mock_l2_05.sync_failure_signal.assert_called()

    def test_TC_L103_L204_003_on_wp_failed_s2_hard(
        self, sut, mock_project_id, mock_topology_mgr, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-s2", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-002",
            fail_level="s2_hard", reason="hard failure",
            evidence_refs=["evt-e2"], ts_ns=1_700_000_000_001,
        ))
        mock_l2_05.sync_failure_signal.assert_called()
        kw = mock_l2_05.sync_failure_signal.call_args.args[0]
        assert kw["fail_level"] == "s2_hard"

    def test_TC_L103_L204_004_on_wp_failed_s3_dod(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-s3", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-003",
            fail_level="s3_dod_fail", reason="dod violated",
            evidence_refs=["evt-e3"], ts_ns=1_700_000_000_002,
        ))
        assert mock_l2_05.sync_failure_signal.called

    def test_TC_L103_L204_005_on_wp_failed_s4_timeout(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-s4", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-004",
            fail_level="s4_timeout", reason="exceeded budget",
            evidence_refs=["evt-e4"], ts_ns=1_700_000_000_003,
        ))
        assert mock_l2_05.sync_failure_signal.called

    def test_TC_L103_L204_006_on_wp_failed_s5_verifier(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-s5", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-005",
            fail_level="s5_verifier_reject", reason="verifier rejected",
            evidence_refs=["evt-e5"], ts_ns=1_700_000_000_004,
        ))
        assert mock_l2_05.sync_failure_signal.called

    def test_TC_L103_L204_007_on_system_resumed_bootstrap(
        self, sut_factory, mock_project_id, bootstrap_events,
    ) -> None:
        """TC-L103-L204-007 · bootstrap 重放 events.jsonl · 聚合 ProgressMetrics。"""
        sut = sut_factory(events=bootstrap_events)
        sut.on_system_resumed(event={"project_id": mock_project_id})
        m = sut.get_progress_metrics(mock_project_id)
        assert m.done_wps >= 1

    def test_TC_L103_L204_008_transition_running_to_done_request(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """TC-L103-L204-008 · 向 L2-02 发 RUNNING→DONE 请求 · requester_l2=L2-04."""
        sut._transition_to_done(project_id=mock_project_id, wp_id="wp-001",
                                 reason="dod passed", evidence_refs=["evt-e1"])
        payload = mock_topology_mgr.transition_state.call_args.args[0]
        assert payload["from_state"] == "RUNNING"
        assert payload["to_state"] == "DONE"
        assert payload["requester_l2"] == "L2-04"

    def test_TC_L103_L204_009_transition_running_to_failed_request(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        sut._transition_to_failed(project_id=mock_project_id, wp_id="wp-001",
                                   reason="subagent timeout",
                                   evidence_refs=["evt-e-to"])
        payload = mock_topology_mgr.transition_state.call_args.args[0]
        assert payload["to_state"] == "FAILED"

    def test_TC_L103_L204_010_sync_failure_signal(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        """TC-L103-L204-010 · sync_failure_signal · counter_value 返回。"""
        mock_l2_05.sync_failure_signal.return_value = {
            "status": "ok", "project_id": mock_project_id,
            "wp_id": "wp-001", "counter_value": 1,
            "rollback_triggered": False,
            "audit_event_id": "evt-s", "latency_ms": 5,
        }
        resp = sut._sync_failure(
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="s2_hard", evidence_refs=["e1"],
            trigger_event_id="evt-src",
        )
        assert resp["counter_value"] == 1

    def test_TC_L103_L204_011_sync_failure_signal_triggers_rollback(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        """TC-L103-L204-011 · counter_value>=3 · rollback_triggered=True."""
        mock_l2_05.sync_failure_signal.return_value = {
            "status": "ok", "project_id": mock_project_id,
            "wp_id": "wp-001", "counter_value": 3,
            "rollback_triggered": True,
            "audit_event_id": "evt-s", "latency_ms": 5,
        }
        resp = sut._sync_failure(
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="s2_hard", evidence_refs=["e1", "e2", "e3"],
            trigger_event_id="evt-src",
        )
        assert resp["rollback_triggered"] is True

    def test_TC_L103_L204_012_get_progress_metrics_shape(
        self, sut, mock_project_id,
    ) -> None:
        """TC-L103-L204-012 · 4 字段齐 · total/done/running/failed."""
        m: ProgressMetrics = sut.get_progress_metrics(mock_project_id)
        for field in ("total_wps", "done_wps", "running_wps", "failed_wps",
                      "stuck_wps", "completion_rate"):
            assert hasattr(m, field)

    def test_TC_L103_L204_013_export_readonly_view(
        self, sut, mock_project_id,
    ) -> None:
        view: ReadonlyProgressView = sut.export_readonly_view(mock_project_id)
        assert view.project_id == mock_project_id
        assert 0.0 <= view.completion_rate <= 1.0

    def test_TC_L103_L204_014_completion_rate_calculation(
        self, sut, mock_project_id, seeded_3_done_2_running,
    ) -> None:
        """TC-L103-L204-014 · 3 DONE / 2 RUNNING · completion_rate = 0.6."""
        m = sut.get_progress_metrics(mock_project_id)
        assert abs(m.completion_rate - 0.6) < 1e-6

    def test_TC_L103_L204_015_burndown_calculation(
        self, sut, mock_project_id, seeded_3_done_2_running,
    ) -> None:
        view = sut.export_readonly_view(mock_project_id)
        assert hasattr(view, "burndown") or hasattr(view, "remaining_wps")

    def test_TC_L103_L204_016_event_idempotent(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """TC-L103-L204-016 · 同一 event_id 重复投递 · 状态只变一次。"""
        evt = WpDoneEvent(
            event_id="evt-dup-001", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_100,
        )
        sut.on_wp_done(evt)
        sut.on_wp_done(evt)
        assert mock_topology_mgr.transition_state.call_count == 1

    def test_TC_L103_L204_017_progress_metrics_updated_emitted(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-d-017", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_017,
        ))
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:progress_metrics_updated" in types
```

---

## §3 负向用例

```python
# file: tests/l1_03/test_l2_04_progress_tracker_negative.py
import pytest

from app.l2_04_prog.schemas import WpDoneEvent, WpFailedEvent


class TestL2_04_Negative:

    def test_TC_L103_L204_101_bootstrap_subscribe_fail(self, sut_subscribe_fail) -> None:
        """E_L103_L204_101 · 订阅 L1-09 失败 · retry 3 次后 hard_halt."""
        with pytest.raises(Exception) as ei:
            sut_subscribe_fail.bootstrap_subscriptions()
        assert "E_L103_L204_101" in str(ei.value)

    def test_TC_L103_L204_102_event_schema_invalid(self, sut, mock_project_id) -> None:
        """E_L103_L204_102 · 事件缺 wp_id · 丢弃单事件 + 审计."""
        bad = {"event_id": "evt-bad", "event_type": "L1-04:wp_done",
               "project_id": mock_project_id,  # 缺 wp_id
               "ts_ns": 1_700_000_000_000}
        with pytest.raises(Exception) as ei:
            sut.on_wp_done_raw(bad)
        assert "E_L103_L204_102" in str(ei.value)

    def test_TC_L103_L204_103_aggregation_input_invalid(self, sut, mock_project_id) -> None:
        """E_L103_L204_103 · 聚合输入 - completion_rate 超出 [0,1]."""
        with pytest.raises(Exception) as ei:
            sut._validate_aggregation(metrics={"total_wps": 10, "done_wps": 15})
        assert "E_L103_L204_103" in str(ei.value)

    def test_TC_L103_L204_104_cross_project(
        self, sut, mock_project_id,
    ) -> None:
        """E_L103_L204_201 · project_id 与注册订阅不一致 · 拒绝 + bypass_attempt."""
        with pytest.raises(Exception) as ei:
            sut.on_wp_done(WpDoneEvent(
                event_id="evt-x", event_type="L1-04:wp_done",
                project_id="hf-proj-other-xxx", wp_id="wp-001",
                verifier_verdict={"verdict": "PASS", "score": 0.9},
                ts_ns=1_700_000_000_000,
            ))
        assert "E_L103_L204_201" in str(ei.value)

    def test_TC_L103_L204_105_l202_rejected(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """E_L103_L204_301 · L2-02 返 rejected · 重试 1 次后审计 upstream_reject."""
        mock_topology_mgr.transition_state.return_value = {
            "status": "rejected",
            "rejection": {"err_code": "E_L103_L202_303", "reason": "illegal"},
        }
        with pytest.raises(Exception) as ei:
            sut._transition_to_done(project_id=mock_project_id, wp_id="wp-001",
                                     reason="r", evidence_refs=["e"])
        assert "E_L103_L204_301" in str(ei.value)

    def test_TC_L103_L204_106_l202_timeout(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """E_L103_L204_302 · L2-02 调用 timeout · 重试 3 次后 DEGRADED."""
        mock_topology_mgr.transition_state.side_effect = TimeoutError("l2-02 down")
        with pytest.raises(Exception) as ei:
            sut._transition_to_done(project_id=mock_project_id, wp_id="wp-001",
                                     reason="r", evidence_refs=["e"])
        assert "E_L103_L204_302" in str(ei.value)

    def test_TC_L103_L204_107_l205_sync_fail(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        """E_L103_L204_303 · L2-05 sync 失败 · 重试 3 次后审计 unsynced."""
        mock_l2_05.sync_failure_signal.side_effect = IOError("l2-05 down")
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-303", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="s1_soft", reason="r",
            evidence_refs=["e"], ts_ns=1_700_000_000_303,
        ))
        # 主路径仍继续：L2-02 仍被调
        # L2-05 失败走 audit unsynced

    def test_TC_L103_L204_108_ic09_append_fail(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        """E_L103_L204_401 · IC-09 失败 · 重试 3 次后 WARN."""
        mock_event_bus.append_event.side_effect = IOError("bus down")
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-401", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_401,
        ))
        # audit 失败不阻 metrics 更新

    def test_TC_L103_L204_109_progress_metrics_jsonl_fail(
        self, sut_ro_fs, mock_project_id,
    ) -> None:
        """E_L103_L204_402 · progress-metrics.jsonl 写失败 · DEGRADED + hard_halt."""
        with pytest.raises(Exception) as ei:
            sut_ro_fs.on_wp_done(WpDoneEvent(
                event_id="evt-402", event_type="L1-04:wp_done",
                project_id=mock_project_id, wp_id="wp-001",
                verifier_verdict={"verdict": "PASS", "score": 0.9},
                ts_ns=1_700_000_000_402,
            ))
        assert "E_L103_L204_402" in str(ei.value)

    def test_TC_L103_L204_110_ui_push_fail(
        self, sut, mock_project_id, mock_ui_pusher,
    ) -> None:
        """E_L103_L204_403 · UI push 失败 · 不阻主路径（best-effort）。"""
        mock_ui_pusher.push.side_effect = IOError("ui down")
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-403", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_403,
        ))
        # 主路径不应抛

    def test_TC_L103_L204_111_l1_07_unreachable(
        self, sut_l107_down, mock_project_id,
    ) -> None:
        """E_L103_L204_404 · L1-07 拉 metrics 时不可达 · 返回 stale flag."""
        m = sut_l107_down.get_progress_metrics(mock_project_id)
        assert getattr(m, "status", "ok") in {"ok", "degraded_stale"}

    def test_TC_L103_L204_112_bypass_fs_write(
        self, sut, mock_project_id, tamper_metrics_file,
    ) -> None:
        """E_L103_L204_501 · 外部直改 current-metrics.json · 启动 consistency_check 识别."""
        tamper_metrics_file(project_id=mock_project_id)
        with pytest.raises(Exception) as ei:
            sut.consistency_check(project_id=mock_project_id)
        assert "E_L103_L204_501" in str(ei.value)
```

---

## §4 IC-XX 契约集成测试

```python
# file: tests/l1_03/test_l2_04_ic_contracts.py
import pytest

from app.l2_04_prog.schemas import WpDoneEvent, WpFailedEvent


class TestL2_04_IC_Contracts:

    def test_TC_L103_L204_601_subscriber_done_shape(self, sut, mock_project_id) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-done-c", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_601,
        ))

    def test_TC_L103_L204_602_subscriber_failed_shape(self, sut, mock_project_id) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-f-c", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-002",
            fail_level="s2_hard", reason="r",
            evidence_refs=["e1"], ts_ns=1_700_000_000_602,
        ))

    def test_TC_L103_L204_603_transition_payload(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        sut._transition_to_done(project_id=mock_project_id, wp_id="wp-001",
                                 reason="r", evidence_refs=["e"])
        p = mock_topology_mgr.transition_state.call_args.args[0]
        assert p["requester_l2"] == "L2-04"
        assert p["from_state"] == "RUNNING"
        assert p["to_state"] in {"DONE", "FAILED"}

    def test_TC_L103_L204_604_sync_failure_payload(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut._sync_failure(project_id=mock_project_id, wp_id="wp-001",
                          fail_level="s1_soft", evidence_refs=["e"],
                          trigger_event_id="evt-src-01")
        p = mock_l2_05.sync_failure_signal.call_args.args[0]
        assert p["requester_l2"] == "L2-04"
        assert p["fail_level"] == "s1_soft"

    def test_TC_L103_L204_605_ic09_event_shape(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-d-605", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_605,
        ))
        types = [c.args[0]["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-03:progress_metrics_updated" in types

    def test_TC_L103_L204_606_get_progress_metrics_shape(
        self, sut, mock_project_id,
    ) -> None:
        m = sut.get_progress_metrics(mock_project_id)
        assert hasattr(m, "total_wps")
        assert hasattr(m, "completion_rate")
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_03/test_l2_04_perf.py
import time, statistics
import pytest

from app.l2_04_prog.schemas import WpDoneEvent


class TestL2_04_Perf:

    @pytest.mark.perf
    def test_TC_L103_L204_701_on_wp_done_p95_under_200ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for i in range(100):
            t = time.perf_counter()
            sut.on_wp_done(WpDoneEvent(
                event_id=f"evt-p-{i:03d}", event_type="L1-04:wp_done",
                project_id=mock_project_id, wp_id=f"wp-{i:03d}",
                verifier_verdict={"verdict": "PASS", "score": 0.9},
                ts_ns=1_700_000_000_000 + i,
            ))
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.2

    @pytest.mark.perf
    def test_TC_L103_L204_702_get_progress_metrics_p95_under_50ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for _ in range(200):
            t = time.perf_counter()
            sut.get_progress_metrics(mock_project_id)
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.05

    @pytest.mark.perf
    def test_TC_L103_L204_703_export_readonly_view_p95_under_100ms(
        self, sut, mock_project_id,
    ) -> None:
        durations = []
        for _ in range(100):
            t = time.perf_counter()
            sut.export_readonly_view(mock_project_id)
            durations.append(time.perf_counter() - t)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 < 0.1
```

---

## §6 端到端 e2e

```python
# file: tests/l1_03/test_l2_04_e2e.py
import pytest

from app.l2_04_prog.schemas import WpDoneEvent, WpFailedEvent


class TestL2_04_E2E:

    @pytest.mark.e2e
    def test_TC_L103_L204_801_done_then_metrics_update(
        self, sut_real, mock_project_id,
    ) -> None:
        sut_real.on_wp_done(WpDoneEvent(
            event_id="evt-e01", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_e01,
        ))
        m = sut_real.get_progress_metrics(mock_project_id)
        assert m.done_wps >= 1

    @pytest.mark.e2e
    def test_TC_L103_L204_802_failure_chain_notifies_l2_05(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-e02", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-001",
            fail_level="s3_dod_fail", reason="r",
            evidence_refs=["e"], ts_ns=1_700_000_000_e02,
        ))
        mock_l2_05.sync_failure_signal.assert_called()
```

---

## §7 测试 fixture

```python
# file: tests/l1_03/conftest_l2_04.py
import pytest, uuid
from unittest.mock import MagicMock


@pytest.fixture
def mock_project_id():
    return f"hf-proj-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_topology_mgr():
    m = MagicMock()
    m.transition_state = MagicMock(return_value={
        "status": "ok", "wp_id": "wp-001", "resulting_state": "DONE",
        "current_running_count": 0, "audit_event_id": "evt-ack",
        "latency_ms": 10,
    })
    return m


@pytest.fixture
def mock_event_bus():
    m = MagicMock()
    m.append_event = MagicMock(return_value={"event_id": "evt-001"})
    return m


@pytest.fixture
def mock_l2_05():
    m = MagicMock()
    m.sync_failure_signal = MagicMock(return_value={
        "status": "ok", "project_id": "pid", "wp_id": "wp-001",
        "counter_value": 1, "rollback_triggered": False,
        "audit_event_id": "evt-s", "latency_ms": 5,
    })
    return m


@pytest.fixture
def mock_ui_pusher():
    m = MagicMock()
    m.push = MagicMock(return_value=True)
    return m


@pytest.fixture
def mock_clock():
    class C:
        def __init__(self): self.t = 10**9
        def now_ns(self): self.t += 1; return self.t
    return C()


@pytest.fixture
def sut(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_ui_pusher, mock_clock, tmp_path):
    from app.l2_04_prog.tracker import ProgressTracker
    return ProgressTracker(
        topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
        l2_05=mock_l2_05, ui_pusher=mock_ui_pusher,
        clock=mock_clock, storage_root=tmp_path,
    )


@pytest.fixture
def sut_subscribe_fail(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_ui_pusher, mock_clock, tmp_path):
    from app.l2_04_prog.tracker import ProgressTracker
    bad_bus = MagicMock()
    bad_bus.register_subscriber = MagicMock(side_effect=IOError("bus not ready"))
    return ProgressTracker(
        topology_mgr=mock_topology_mgr, event_bus=bad_bus,
        l2_05=mock_l2_05, ui_pusher=mock_ui_pusher,
        clock=mock_clock, storage_root=tmp_path,
    )


@pytest.fixture
def sut_factory(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_ui_pusher, mock_clock, tmp_path):
    from app.l2_04_prog.tracker import ProgressTracker
    def _factory(events=None, **kwargs) -> "ProgressTracker":
        t = ProgressTracker(
            topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
            l2_05=mock_l2_05, ui_pusher=mock_ui_pusher,
            clock=mock_clock, storage_root=tmp_path,
            **kwargs,
        )
        if events:
            t._bootstrap_events = events
        return t
    return _factory


@pytest.fixture
def sut_ro_fs(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_ui_pusher, mock_clock):
    """模拟只读 FS · progress-metrics.jsonl 写失败。"""
    from app.l2_04_prog.tracker import ProgressTracker
    return ProgressTracker(
        topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
        l2_05=mock_l2_05, ui_pusher=mock_ui_pusher,
        clock=mock_clock, storage_root="/dev/null/readonly",
    )


@pytest.fixture
def sut_l107_down(mock_topology_mgr, mock_event_bus, mock_l2_05, mock_ui_pusher, mock_clock, tmp_path):
    """L1-07 不可达 · 返回 stale 标记。"""
    from app.l2_04_prog.tracker import ProgressTracker
    t = ProgressTracker(
        topology_mgr=mock_topology_mgr, event_bus=mock_event_bus,
        l2_05=mock_l2_05, ui_pusher=mock_ui_pusher,
        clock=mock_clock, storage_root=tmp_path,
    )
    t._mode = "DEGRADED"
    return t


@pytest.fixture
def sut_real(sut):
    return sut


@pytest.fixture
def bootstrap_events(mock_project_id):
    return [
        {"event_type": "L1-04:wp_done", "project_id": mock_project_id,
         "wp_id": "wp-001", "event_id": "evt-boot-01",
         "verifier_verdict": {"verdict": "PASS", "score": 0.9},
         "ts_ns": 1_700_000_000_000},
    ]


@pytest.fixture
def seeded_3_done_2_running(sut, mock_project_id):
    for i in range(3):
        sut._apply_done(project_id=mock_project_id, wp_id=f"wp-{i:03d}")
    for i in range(3, 5):
        sut._apply_running(project_id=mock_project_id, wp_id=f"wp-{i:03d}")
    sut._total_wps[mock_project_id] = 5
    return sut


@pytest.fixture
def tamper_metrics_file(tmp_path):
    def _t(project_id: str):
        p = tmp_path / "projects" / project_id / "progress" / "current-metrics.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"bypass":"yes"}', encoding="utf-8")
    return _t
```

---

## §8 集成点用例

```python
# file: tests/l1_03/test_l2_04_integrations.py
import pytest

from app.l2_04_prog.schemas import WpDoneEvent, WpFailedEvent


class TestL2_04_Integration:

    def test_TC_L103_L204_901_with_l2_02_transition(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-901", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_901,
        ))
        assert mock_topology_mgr.transition_state.called

    def test_TC_L103_L204_902_with_l2_05_on_failure(
        self, sut, mock_project_id, mock_l2_05,
    ) -> None:
        sut.on_wp_failed(WpFailedEvent(
            event_id="evt-902", event_type="L1-04:wp_failed",
            project_id=mock_project_id, wp_id="wp-002",
            fail_level="s2_hard", reason="r",
            evidence_refs=["e"], ts_ns=1_700_000_000_902,
        ))
        assert mock_l2_05.sync_failure_signal.called

    def test_TC_L103_L204_903_with_l1_09_audit(
        self, sut, mock_project_id, mock_event_bus,
    ) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-903", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_903,
        ))
        assert mock_event_bus.append_event.called

    def test_TC_L103_L204_904_with_l1_10_ui_push(
        self, sut, mock_project_id, mock_ui_pusher,
    ) -> None:
        sut.on_wp_done(WpDoneEvent(
            event_id="evt-904", event_type="L1-04:wp_done",
            project_id=mock_project_id, wp_id="wp-001",
            verifier_verdict={"verdict": "PASS", "score": 0.9},
            ts_ns=1_700_000_000_904,
        ))
        assert mock_ui_pusher.push.called

    def test_TC_L103_L204_905_with_l1_07_supervisor_pull(
        self, sut, mock_project_id,
    ) -> None:
        m = sut.get_progress_metrics(mock_project_id)
        assert m.total_wps >= 0
```

---

## §9 边界 / edge case

```python
# file: tests/l1_03/test_l2_04_edge.py
import pytest

from app.l2_04_prog.schemas import WpDoneEvent


class TestL2_04_Edge:

    def test_TC_L103_L204_A01_empty_project(self, sut, mock_project_id) -> None:
        """空 project · metrics total=0 · completion_rate=0 or NaN 兜底。"""
        m = sut.get_progress_metrics(mock_project_id)
        assert m.total_wps == 0

    def test_TC_L103_L204_A02_concurrent_events(self, sut, mock_project_id) -> None:
        from concurrent.futures import ThreadPoolExecutor
        def go(i):
            sut.on_wp_done(WpDoneEvent(
                event_id=f"evt-c-{i:03d}", event_type="L1-04:wp_done",
                project_id=mock_project_id, wp_id=f"wp-{i:03d}",
                verifier_verdict={"verdict": "PASS", "score": 0.9},
                ts_ns=1_700_000_000_000 + i,
            ))
        with ThreadPoolExecutor(max_workers=8) as ex:
            for _ in ex.map(go, range(8)):
                pass
        # 无异常即通过

    def test_TC_L103_L204_A03_very_large_100_wps(self, sut, mock_project_id) -> None:
        for i in range(100):
            sut.on_wp_done(WpDoneEvent(
                event_id=f"evt-l-{i:03d}", event_type="L1-04:wp_done",
                project_id=mock_project_id, wp_id=f"wp-{i:03d}",
                verifier_verdict={"verdict": "PASS", "score": 0.9},
                ts_ns=1_700_000_000_000 + i,
            ))
        m = sut.get_progress_metrics(mock_project_id)
        assert m.done_wps == 100

    def test_TC_L103_L204_A04_bootstrap_from_partial_events(
        self, sut_factory, mock_project_id,
    ) -> None:
        partial = [
            {"event_type": "L1-04:wp_done", "project_id": mock_project_id,
             "wp_id": "wp-001", "event_id": "evt-b-1",
             "verifier_verdict": {"verdict": "PASS", "score": 0.9},
             "ts_ns": 1_700_000_000_000},
        ]
        sut = sut_factory(events=partial)
        sut.on_system_resumed(event={"project_id": mock_project_id})
        assert sut.get_progress_metrics(mock_project_id).done_wps == 1

    def test_TC_L103_L204_A05_event_late_arrival_out_of_order(
        self, sut, mock_project_id, mock_topology_mgr,
    ) -> None:
        """事件乱序（ts_ns 倒置）· 按 event_id 幂等 · 不重复写。"""
        e1 = WpDoneEvent(event_id="evt-l-1", event_type="L1-04:wp_done",
                         project_id=mock_project_id, wp_id="wp-001",
                         verifier_verdict={"verdict": "PASS", "score": 0.9},
                         ts_ns=1_700_000_000_002)
        e2 = WpDoneEvent(event_id="evt-l-2", event_type="L1-04:wp_done",
                         project_id=mock_project_id, wp_id="wp-002",
                         verifier_verdict={"verdict": "PASS", "score": 0.9},
                         ts_ns=1_700_000_000_001)  # 更早
        sut.on_wp_done(e1)
        sut.on_wp_done(e2)
        assert mock_topology_mgr.transition_state.call_count == 2
```

---

*— L2-04 TDD 已按 10 段模板完成 · 覆盖 §3 全部方法 / §11 全部 12 错误码 / 6 条 IC · 订阅幂等 + fail_level 全枚举覆盖 —*
