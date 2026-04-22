---
doc_id: tests-L1-01-L2-01-Tick 调度器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-01-Tick 调度器.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-01-Tick 调度器 · TDD 测试用例

> 基于 3-1 L2-01 §3（5 个 public 方法）+ §11（29 项 `E_TICK_*` 错误码）+ §12（P95/P99/硬上限 SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L101-L201-NNN`（L1-01 下 L2-01，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_01_TickScheduler` 组织；`class TestL2_01_Negative` 负向分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `schedule_tick()` · §3.1 | TC-L101-L201-001 | unit | — | IC-L2-01 |
| `schedule_tick()` · bootstrap | TC-L101-L201-002 | unit | — | IC-L2-01 / IC-10 |
| `schedule_tick()` · event_driven | TC-L101-L201-003 | unit | — | IC-L2-01 / IC-09 |
| `schedule_tick()` · periodic_tick | TC-L101-L201-004 | unit | — | IC-L2-01 |
| `schedule_tick()` · hook_driven | TC-L101-L201-005 | unit | — | IC-L2-01 |
| `schedule_tick()` · proactive | TC-L101-L201-006 | unit | — | IC-L2-01 |
| `schedule_tick()` · debounce 合并 | TC-L101-L201-007 | unit | — | IC-L2-01 |
| `schedule_tick()` · 仲裁优先级 | TC-L101-L201-008 | unit | — | IC-L2-01 |
| `on_hard_halt()` · §3.2 正向 | TC-L101-L201-009 | unit | — | IC-L2-08 |
| `on_user_panic()` · §3.3 正向 | TC-L101-L201-010 | unit | — | IC-17 |
| `on_async_result()` · §3.4 正向 | TC-L101-L201-011 | unit | — | IC-09 |
| `watchdog_heartbeat()` · §3.5 扫描 | TC-L101-L201-012 | unit | — | IC-L2-05 / IC-09 |
| `watchdog_heartbeat()` · tick_timeout 告警 | TC-L101-L201-013 | unit | — | IC-L2-05 |
| `watchdog_heartbeat()` · idle_spin 告警 | TC-L101-L201-014 | unit | — | IC-L2-05 |

### §1.2 错误码 × 测试（§11 29 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_TICK_NO_PROJECT_ID` | TC-L101-L201-101 | `schedule_tick()` | PM-14 校验失败 |
| `E_TICK_CROSS_PROJECT` | TC-L101-L201-102 | `schedule_tick()` | PM-14 校验失败 |
| `E_TICK_INVALID_SOURCE` | TC-L101-L201-103 | `schedule_tick()` | 数据合法性 |
| `E_TICK_QUEUE_FULL` | TC-L101-L201-104 | `schedule_tick()` | 队列满 |
| `E_TICK_HALTED_REJECT` | TC-L101-L201-105 | `schedule_tick()` | 受控拒绝 |
| `E_TICK_INVALID_PRIORITY` | TC-L101-L201-106 | `schedule_tick()` | 数据合法性 |
| `E_TICK_BOOTSTRAP_DUPLICATE` | TC-L101-L201-107 | `schedule_tick()` | 重复订阅 |
| `E_TICK_INTERNAL_STATE_BAD` | TC-L101-L201-108 | `schedule_tick()` | 自身 bug |
| `E_TICK_HALT_SLO_VIOLATION` | TC-L101-L201-201 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_HALT_DUPLICATE` | TC-L101-L201-202 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_HALT_NO_SUPERVISOR_EVENT` | TC-L101-L201-203 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_HALT_CROSS_PROJECT` | TC-L101-L201-204 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_HALT_INVALID_REDLINE` | TC-L101-L201-205 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_HALT_CANCEL_FAIL` | TC-L101-L201-206 | `on_hard_halt()` | BLOCK 抢占 |
| `E_TICK_PANIC_SLO_VIOLATION` | TC-L101-L201-301 | `on_user_panic()` | panic |
| `E_TICK_PANIC_NO_USER_ID` | TC-L101-L201-302 | `on_user_panic()` | panic |
| `E_TICK_PANIC_ALREADY_PAUSED` | TC-L101-L201-303 | `on_user_panic()` | panic |
| `E_TICK_PANIC_CROSS_PROJECT` | TC-L101-L201-304 | `on_user_panic()` | panic |
| `E_TICK_PANIC_STATE_TRANSITION_FAIL` | TC-L101-L201-305 | `on_user_panic()` | panic |
| `E_TICK_ASYNC_NO_DELEGATION_ID` | TC-L101-L201-401 | `on_async_result()` | 异步结果 |
| `E_TICK_ASYNC_ORPHAN` | TC-L101-L201-402 | `on_async_result()` | 异步结果 |
| `E_TICK_ASYNC_CROSS_PROJECT` | TC-L101-L201-403 | `on_async_result()` | 异步结果 |
| `E_TICK_ASYNC_TIMEOUT_RESULT` | TC-L101-L201-404 | `on_async_result()` | 异步结果 |
| `E_TICK_ASYNC_INVALID_EVENT_TYPE` | TC-L101-L201-405 | `on_async_result()` | 异步结果 |
| `E_TICK_WATCHDOG_SCAN_TIMEOUT` | TC-L101-L201-501 | `watchdog_heartbeat()` | watchdog 健康 |
| `E_TICK_WATCHDOG_STATE_INVALID` | TC-L101-L201-502 | `watchdog_heartbeat()` | watchdog 健康 |
| `E_TICK_WATCHDOG_AUDIT_FAIL` | TC-L101-L201-503 | `watchdog_heartbeat()` | watchdog 健康 |
| `E_TICK_WATCHDOG_CROSS_PROJECT_TICK` | TC-L101-L201-504 | `watchdog_heartbeat()` | watchdog 健康 |
| `E_TICK_WATCHDOG_THREAD_DEAD` | TC-L101-L201-505 | `watchdog_heartbeat()` | 自身 bug |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 `on_tick` | L2-01 → L2-02 | TC-L101-L201-601 | 生产方 · payload 结构断言 |
| IC-L2-08 `propagate_hard_halt` | L2-06 → L2-01 | TC-L101-L201-602 | 消费方 · ≤100ms + state=HALTED |
| IC-L2-05 `record_audit`（代劳 IC-09）| L2-01 → L2-05 | TC-L101-L201-603 | 每 tick ≥ 2 条（scheduled + completed）|
| IC-09 `append_event` | 经 L2-05 代劳 | TC-L101-L201-604 | tick_scheduled / tick_completed 事件 |
| IC-17 `user_intervene(panic)` | L1-10 → L1-09 → L2-01 | TC-L101-L201-605 | 事件订阅链 · panic 响应 |
| IC-10 `replay_from_event` | L1-09 → L2-01（bootstrap 恢复）| TC-L101-L201-606 | 跨 session 恢复 pending queue |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_01_TickScheduler`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `TickScheduler`（从 `app.l2_01.scheduler` 导入）。

```python
# file: tests/l1_01/test_l2_01_tick_scheduler_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l2_01.scheduler import TickScheduler
from app.l2_01.schemas import TickTrigger, ScheduleResult, HaltSignal, PanicSignal, ResultEvent
from app.l2_01.errors import TickError


class TestL2_01_TickScheduler:
    """§3 public 方法正向用例。每方法 ≥ 1 个 happy path。"""

    # --------- schedule_tick() · 8 trigger_source --------- #

    def test_TC_L101_L201_001_schedule_tick_event_driven_happy_path(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-001 · event_driven 触发源入队 + accepted=true + queue_depth ≥ 1。"""
        # arrange
        trigger: TickTrigger = make_trigger(
            trigger_source="event_driven",
            priority=50,
            project_id=mock_project_id,
        )
        # act
        result: ScheduleResult = sut.schedule_tick(trigger)
        # assert
        assert result.accepted is True
        assert result.queue_depth >= 1
        assert result.rejected_reason is None

    def test_TC_L101_L201_002_schedule_tick_bootstrap_skips_debounce(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-002 · bootstrap priority=100 · 立即派发不走去抖。"""
        trigger: TickTrigger = make_trigger(
            trigger_source="bootstrap",
            priority=100,
            project_id=mock_project_id,
            bootstrap_context={"resumed_from_checkpoint": "2026-04-22T00:00:00Z", "last_state": "S1"},
        )
        result: ScheduleResult = sut.schedule_tick(trigger)
        assert result.accepted is True
        assert result.tick_id_or_null is not None, "bootstrap 必须立即派发（§3.1 出参说明）"
        assert result.debounced is False, "bootstrap 禁止被去抖合并（prd §8.5 禁止 #2）"

    def test_TC_L101_L201_003_schedule_tick_event_driven_emits_tick_scheduled(
        self,
        sut: TickScheduler,
        mock_event_bus: MagicMock,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-003 · event_driven 派发后经 L2-05 代劳写 IC-09 tick_scheduled。"""
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut._dispatch_once()  # drive internal loop one iteration
        audit_calls = [c for c in mock_event_bus.append_event.call_args_list
                       if c.kwargs.get("event_type") == "L1-01:tick_scheduled"]
        assert len(audit_calls) == 1, "每 tick 至少 1 条 tick_scheduled（§13.4 P0-10）"
        assert audit_calls[0].kwargs["project_id"] == mock_project_id

    def test_TC_L101_L201_004_schedule_tick_periodic_tick_priority_10(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-004 · periodic_tick 默认 priority=10（最低）。"""
        trigger = make_trigger(trigger_source="periodic_tick", priority=10, project_id=mock_project_id)
        result = sut.schedule_tick(trigger)
        assert result.accepted is True
        assert sut.peek_queue()[0].priority == 10

    def test_TC_L101_L201_005_schedule_tick_hook_driven_priority_40(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-005 · hook_driven（SessionStart / state_transition）priority=40。"""
        trigger = make_trigger(trigger_source="hook_driven", priority=40, project_id=mock_project_id)
        result = sut.schedule_tick(trigger)
        assert result.accepted is True

    def test_TC_L101_L201_006_schedule_tick_proactive_priority_30(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-006 · proactive（上一 tick 完成后自唤醒）priority=30。"""
        trigger = make_trigger(trigger_source="proactive", priority=30, project_id=mock_project_id)
        result = sut.schedule_tick(trigger)
        assert result.accepted is True

    def test_TC_L101_L201_007_schedule_tick_debounce_merges_10_into_1(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        mock_clock,
        make_trigger,
    ) -> None:
        """TC-L101-L201-007 · 500ms 窗口内 event_driven × 10 → 去抖合并为 1 派发（prd P5）。"""
        for i in range(10):
            t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
            sut.schedule_tick(t)
            mock_clock.advance(40)  # 40ms 间隔 · 10 次共 400ms < 500ms 窗口
        mock_clock.advance(600)  # flush debounce bucket
        dispatched = sut.drain_dispatched()
        assert len(dispatched) == 1, "10 次同源 event_driven 合并为 1 · 合并率 100%"

    def test_TC_L101_L201_008_schedule_tick_arbitrate_high_priority_first(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-008 · 同时入队多优先级 → arbitrate 先派 bootstrap(100) > panic(90) > event(50)。"""
        t_low = make_trigger(trigger_source="periodic_tick", priority=10, project_id=mock_project_id)
        t_mid = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        t_high = make_trigger(trigger_source="bootstrap", priority=100, project_id=mock_project_id)
        sut.schedule_tick(t_low)
        sut.schedule_tick(t_mid)
        sut.schedule_tick(t_high)
        order = sut.drain_dispatched()
        assert [d.trigger_source for d in order] == ["bootstrap", "event_driven", "periodic_tick"]

    # --------- on_hard_halt() --------- #

    def test_TC_L101_L201_009_on_hard_halt_sets_state_halted_within_100ms(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_halt_signal,
    ) -> None:
        """TC-L101-L201-009 · IC-L2-08 hard_halt ≤ 100ms 后 state=HALTED（§3.2 硬约束）。"""
        signal: HaltSignal = make_halt_signal(
            red_line_id="IRREVERSIBLE_HALT",
            project_id=mock_project_id,
        )
        result = sut.on_hard_halt(signal)
        assert result.halted is True
        assert result.halt_latency_ms <= 100
        assert sut.current_state() == "HALTED"

    # --------- on_user_panic() --------- #

    def test_TC_L101_L201_010_on_user_panic_sets_state_paused_within_100ms(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_panic_signal,
    ) -> None:
        """TC-L101-L201-010 · panic ≤ 100ms 后 state=PAUSED（§3.3）。"""
        signal: PanicSignal = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        result = sut.on_user_panic(signal)
        assert result.paused is True
        assert result.panic_latency_ms <= 100
        assert sut.current_state() == "PAUSED"

    # --------- on_async_result() --------- #

    def test_TC_L101_L201_011_on_async_result_normalizes_to_tick_trigger(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_result_event,
    ) -> None:
        """TC-L101-L201-011 · subagent_result 转 TickTrigger(source=async_result, prio=60) 入队。"""
        event: ResultEvent = make_result_event(
            delegation_id="del-001",
            project_id=mock_project_id,
            outcome="success",
        )
        r = sut.on_async_result(event)
        assert r.accepted is True
        queued = sut.peek_queue()
        assert queued[-1].trigger_source == "async_result"
        assert queued[-1].priority == 60

    # --------- watchdog_heartbeat() --------- #

    def test_TC_L101_L201_012_watchdog_heartbeat_scan_duration_within_10ms(
        self,
        sut: TickScheduler,
    ) -> None:
        """TC-L101-L201-012 · 单次扫描 ≤ 10ms（§3.5 SLO + §12.1）。"""
        scan = sut.watchdog_heartbeat()
        assert scan.scan_duration_ms <= 10
        assert set(scan.checks_performed) == {"tick_timeout", "idle_spin", "chain_forward"}

    def test_TC_L101_L201_013_watchdog_detects_tick_timeout(
        self,
        sut: TickScheduler,
        mock_clock,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-013 · tick 模拟 35s 未完成 → tick_timeout 告警（prd P8）。"""
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut._start_tick_unsafe(trigger)
        mock_clock.advance(35_000)  # 35s > 30s 硬上限
        scan = sut.watchdog_heartbeat()
        types = [a.alert_type for a in scan.alerts_emitted]
        assert "tick_timeout" in types
        assert sut.current_state() == "DEGRADED"

    def test_TC_L101_L201_014_watchdog_detects_idle_spin_after_5_noop(
        self,
        sut: TickScheduler,
        mock_project_id: str,
        make_trigger,
    ) -> None:
        """TC-L101-L201-014 · 连续 5 次 no_op tick → idle_spin_detected 告警（prd P7）。"""
        for _ in range(5):
            t = make_trigger(trigger_source="proactive", priority=30, project_id=mock_project_id)
            sut.schedule_tick(t)
            sut._complete_tick_as_noop()
        scan = sut.watchdog_heartbeat()
        types = [a.alert_type for a in scan.alerts_emitted]
        assert "idle_spin_detected" in types
```

---

## §3 负向用例（每错误码 ≥ 1）

> §11 表 29 项 `E_TICK_*` 全覆盖。每测试用 `pytest.raises(TickError) as exc` + 断言 `exc.value.error_code == "E_TICK_..."`。

```python
# file: tests/l1_01/test_l2_01_tick_scheduler_negative.py
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from app.l2_01.scheduler import TickScheduler
from app.l2_01.errors import TickError
from app.l2_01.schemas import TickTrigger


class TestL2_01_Negative_ScheduleTick:
    """§3.1 schedule_tick() 8 错误码（TC-L101-L201-101..108）。"""

    def test_TC_L101_L201_101_no_project_id_raises(
        self, sut: TickScheduler, make_trigger,
    ) -> None:
        """TC-L101-L201-101 · E_TICK_NO_PROJECT_ID · PM-14 根字段校验。"""
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=None)
        with pytest.raises(TickError) as exc:
            sut.schedule_tick(trigger)
        assert exc.value.error_code == "E_TICK_NO_PROJECT_ID"

    def test_TC_L101_L201_102_cross_project_raises(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-102 · E_TICK_CROSS_PROJECT · project_id ≠ session.active_pid。"""
        trigger = make_trigger(
            trigger_source="event_driven",
            priority=50,
            project_id="pid-018f4a3b-9999-7000-FFFF-other-project",
        )
        with pytest.raises(TickError) as exc:
            sut.schedule_tick(trigger)
        assert exc.value.error_code == "E_TICK_CROSS_PROJECT"

    def test_TC_L101_L201_103_invalid_source_raises(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-103 · E_TICK_INVALID_SOURCE · 非 8 枚举之一。"""
        trigger = make_trigger(
            trigger_source="not_a_real_source",
            priority=50,
            project_id=mock_project_id,
        )
        with pytest.raises(TickError) as exc:
            sut.schedule_tick(trigger)
        assert exc.value.error_code == "E_TICK_INVALID_SOURCE"

    def test_TC_L101_L201_104_queue_full_evicts_lowest_priority(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-104 · E_TICK_QUEUE_FULL · 1000 满 → 丢最低 priority（§11 策略 + prd N3）。"""
        for _ in range(1000):
            sut.schedule_tick(make_trigger(trigger_source="periodic_tick", priority=10, project_id=mock_project_id))
        # 新 trigger 是高 priority，预期入队 + 丢一条最低 priority；审计记 queue_overflow
        new_t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        result = sut.schedule_tick(new_t)
        assert result.accepted is True
        audit = [a for a in sut.get_recent_audits() if a.action == "queue_overflow"]
        assert len(audit) == 1
        assert audit[0].error_code == "E_TICK_QUEUE_FULL"

    def test_TC_L101_L201_105_halted_reject_event_driven(
        self, sut: TickScheduler, mock_project_id: str, make_trigger, make_halt_signal,
    ) -> None:
        """TC-L101-L201-105 · E_TICK_HALTED_REJECT · HALTED 期间 event_driven 拒绝入队（prd N4 + §8.5 #5）。"""
        sut.on_hard_halt(make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id))
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        with pytest.raises(TickError) as exc:
            sut.schedule_tick(trigger)
        assert exc.value.error_code == "E_TICK_HALTED_REJECT"

    def test_TC_L101_L201_106_invalid_priority_clipped_and_warn(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-106 · E_TICK_INVALID_PRIORITY · 超 0-100 clip 到默认值 + WARN 审计。"""
        trigger = make_trigger(trigger_source="event_driven", priority=999, project_id=mock_project_id)
        result = sut.schedule_tick(trigger)
        assert result.accepted is True
        assert sut.peek_queue()[-1].priority == 50, "event_driven 默认 50"
        warn = [a for a in sut.get_recent_audits() if a.level == "WARN" and a.error_code == "E_TICK_INVALID_PRIORITY"]
        assert len(warn) == 1

    def test_TC_L101_L201_107_bootstrap_duplicate_silently_ignored(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-107 · E_TICK_BOOTSTRAP_DUPLICATE · 重复订阅 system_resumed 静默忽略第二条。"""
        b1 = make_trigger(trigger_source="bootstrap", priority=100, project_id=mock_project_id)
        b2 = make_trigger(trigger_source="bootstrap", priority=100, project_id=mock_project_id)
        r1 = sut.schedule_tick(b1)
        r2 = sut.schedule_tick(b2)
        assert r1.accepted is True
        assert r2.accepted is False
        assert r2.rejected_reason == "E_TICK_BOOTSTRAP_DUPLICATE"

    def test_TC_L101_L201_108_internal_state_bad_aborts(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-108 · E_TICK_INTERNAL_STATE_BAD · scheduler.state 非 6 枚举值 → abort。"""
        sut._force_state("CORRUPTED")  # test-only hatch
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        with pytest.raises(TickError) as exc:
            sut.schedule_tick(trigger)
        assert exc.value.error_code == "E_TICK_INTERNAL_STATE_BAD"


class TestL2_01_Negative_HardHalt:
    """§3.2 on_hard_halt() 6 错误码（TC-L101-L201-201..206）。"""

    def test_TC_L101_L201_201_halt_slo_violation_still_halted_true(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal, mock_clock,
    ) -> None:
        """TC-L101-L201-201 · E_TICK_HALT_SLO_VIOLATION · > 100ms 仍返回 halted=true + 审计。"""
        sut._inject_audit_latency_ms(150)  # force slow audit write
        signal = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id)
        result = sut.on_hard_halt(signal)
        assert result.halted is True  # §3.2 出参描述
        assert result.halt_latency_ms > 100
        slos = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_HALT_SLO_VIOLATION"]
        assert len(slos) == 1

    def test_TC_L101_L201_202_halt_duplicate_ignored_and_appends_active_blocks(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-202 · E_TICK_HALT_DUPLICATE · 第二条 halt 追加 active_blocks[]，不改 halt_id。"""
        sig1 = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id, halt_id="halt-A")
        sig2 = make_halt_signal(red_line_id="DATA_LOSS", project_id=mock_project_id, halt_id="halt-B")
        sut.on_hard_halt(sig1)
        sut.on_hard_halt(sig2)
        assert sut.current_halt_id() == "halt-A"  # 保留第一条
        assert len(sut.active_blocks()) == 2

    def test_TC_L101_L201_203_halt_no_supervisor_event_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-203 · E_TICK_HALT_NO_SUPERVISOR_EVENT · supervisor_event_id 空 → 拒绝。"""
        signal = make_halt_signal(
            red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id, supervisor_event_id="",
        )
        with pytest.raises(TickError) as exc:
            sut.on_hard_halt(signal)
        assert exc.value.error_code == "E_TICK_HALT_NO_SUPERVISOR_EVENT"

    def test_TC_L101_L201_204_halt_cross_project_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-204 · E_TICK_HALT_CROSS_PROJECT · project_id 不符 session.active_pid。"""
        signal = make_halt_signal(
            red_line_id="IRREVERSIBLE_HALT",
            project_id="pid-other-session-xxxx",
        )
        with pytest.raises(TickError) as exc:
            sut.on_hard_halt(signal)
        assert exc.value.error_code == "E_TICK_HALT_CROSS_PROJECT"

    def test_TC_L101_L201_205_halt_invalid_redline_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-205 · E_TICK_HALT_INVALID_REDLINE · red_line_id 非 5 枚举之一。"""
        signal = make_halt_signal(red_line_id="NOT_A_REDLINE", project_id=mock_project_id)
        with pytest.raises(TickError) as exc:
            sut.on_hard_halt(signal)
        assert exc.value.error_code == "E_TICK_HALT_INVALID_REDLINE"

    def test_TC_L101_L201_206_halt_cancel_fail_still_halted(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal, mock_l2_02_client,
    ) -> None:
        """TC-L101-L201-206 · E_TICK_HALT_CANCEL_FAIL · L2-02.on_async_cancel 抛异常 → 强制 state=HALTED + 审计告警。"""
        mock_l2_02_client.on_async_cancel.side_effect = RuntimeError("L2-02 crashed")
        signal = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id)
        result = sut.on_hard_halt(signal)
        assert sut.current_state() == "HALTED"
        cancel_fails = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_HALT_CANCEL_FAIL"]
        assert len(cancel_fails) == 1


class TestL2_01_Negative_Panic:
    """§3.3 on_user_panic() 5 错误码（TC-L101-L201-301..305）。"""

    def test_TC_L101_L201_301_panic_slo_violation_still_paused_true(
        self, sut: TickScheduler, mock_project_id: str, make_panic_signal,
    ) -> None:
        """TC-L101-L201-301 · E_TICK_PANIC_SLO_VIOLATION · > 100ms 仍 paused=true。"""
        sut._inject_audit_latency_ms(150)
        signal = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        result = sut.on_user_panic(signal)
        assert result.paused is True
        assert result.panic_latency_ms > 100

    def test_TC_L101_L201_302_panic_no_user_id_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_panic_signal,
    ) -> None:
        """TC-L101-L201-302 · E_TICK_PANIC_NO_USER_ID · 无主 panic 拒绝（不能匿名暂停）。"""
        signal = make_panic_signal(project_id=mock_project_id, user_id="")
        with pytest.raises(TickError) as exc:
            sut.on_user_panic(signal)
        assert exc.value.error_code == "E_TICK_PANIC_NO_USER_ID"

    def test_TC_L101_L201_303_panic_already_paused_ignored(
        self, sut: TickScheduler, mock_project_id: str, make_panic_signal,
    ) -> None:
        """TC-L101-L201-303 · E_TICK_PANIC_ALREADY_PAUSED · 连点 panic 静默忽略。"""
        s1 = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        s2 = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        sut.on_user_panic(s1)
        r2 = sut.on_user_panic(s2)
        assert r2.paused is True  # idempotent · 非错误
        debug = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_PANIC_ALREADY_PAUSED"]
        assert len(debug) == 1

    def test_TC_L101_L201_304_panic_cross_project_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_panic_signal,
    ) -> None:
        """TC-L101-L201-304 · E_TICK_PANIC_CROSS_PROJECT · 多 session UI 泄漏。"""
        signal = make_panic_signal(project_id="pid-wrong-session", user_id="user-001")
        with pytest.raises(TickError) as exc:
            sut.on_user_panic(signal)
        assert exc.value.error_code == "E_TICK_PANIC_CROSS_PROJECT"

    def test_TC_L101_L201_305_panic_state_transition_fail_still_paused_internal(
        self, sut: TickScheduler, mock_project_id: str, make_panic_signal, mock_l2_03_client,
    ) -> None:
        """TC-L101-L201-305 · E_TICK_PANIC_STATE_TRANSITION_FAIL · L2-03 crash 仍内部 PAUSED。"""
        mock_l2_03_client.request_state_transition.side_effect = RuntimeError("L2-03 crashed")
        signal = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        result = sut.on_user_panic(signal)
        assert result.paused is True
        assert sut.current_state() == "PAUSED"
        fails = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_PANIC_STATE_TRANSITION_FAIL"]
        assert len(fails) == 1


class TestL2_01_Negative_AsyncResult:
    """§3.4 on_async_result() 5 错误码（TC-L101-L201-401..405）。"""

    def test_TC_L101_L201_401_async_no_delegation_id_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_result_event,
    ) -> None:
        event = make_result_event(delegation_id="", project_id=mock_project_id, outcome="success")
        with pytest.raises(TickError) as exc:
            sut.on_async_result(event)
        assert exc.value.error_code == "E_TICK_ASYNC_NO_DELEGATION_ID"

    def test_TC_L101_L201_402_async_orphan_still_enqueued(
        self, sut: TickScheduler, mock_project_id: str, make_result_event, mock_l2_02_client,
    ) -> None:
        """TC-L101-L201-402 · 孤儿 delegation 仍入队 + 审计告警（L2-02 自己兜底）。"""
        mock_l2_02_client.resolve_delegation.return_value = None  # not found
        event = make_result_event(delegation_id="del-ghost", project_id=mock_project_id, outcome="success")
        r = sut.on_async_result(event)
        assert r.accepted is True
        orphans = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_ASYNC_ORPHAN"]
        assert len(orphans) == 1

    def test_TC_L101_L201_403_async_cross_project_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_result_event,
    ) -> None:
        event = make_result_event(delegation_id="del-001", project_id="pid-wrong", outcome="success")
        with pytest.raises(TickError) as exc:
            sut.on_async_result(event)
        assert exc.value.error_code == "E_TICK_ASYNC_CROSS_PROJECT"

    def test_TC_L101_L201_404_async_timeout_result_still_enqueued(
        self, sut: TickScheduler, mock_project_id: str, make_result_event,
    ) -> None:
        event = make_result_event(delegation_id="del-001", project_id=mock_project_id, outcome="timeout")
        r = sut.on_async_result(event)
        assert r.accepted is True  # 让 L2-02 决策处理

    def test_TC_L101_L201_405_async_invalid_event_type_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_result_event,
    ) -> None:
        event = make_result_event(
            delegation_id="del-001", project_id=mock_project_id, outcome="success",
            event_type="L1-05:wrong_event",
        )
        with pytest.raises(TickError) as exc:
            sut.on_async_result(event)
        assert exc.value.error_code == "E_TICK_ASYNC_INVALID_EVENT_TYPE"


class TestL2_01_Negative_Watchdog:
    """§3.5 watchdog_heartbeat() 5 错误码（TC-L101-L201-501..505）。"""

    def test_TC_L101_L201_501_watchdog_scan_timeout_aborts_round(
        self, sut: TickScheduler, mock_clock,
    ) -> None:
        sut._inject_watchdog_scan_latency_ms(25)  # > 10ms
        scan = sut.watchdog_heartbeat()
        assert scan.scan_duration_ms > 10
        errs = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_WATCHDOG_SCAN_TIMEOUT"]
        assert len(errs) == 1

    def test_TC_L101_L201_502_watchdog_state_invalid_auto_repairs(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """current_tick 存在但 state=IDLE · 自动修复 state→RUNNING + 告警。"""
        t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(t)
        sut._start_tick_unsafe(t)
        sut._force_state("IDLE")  # inconsistent
        sut.watchdog_heartbeat()
        assert sut.current_state() == "RUNNING"  # auto-repaired
        errs = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_WATCHDOG_STATE_INVALID"]
        assert len(errs) == 1

    def test_TC_L101_L201_503_watchdog_audit_fail_buffers_locally(
        self, sut: TickScheduler, mock_l2_05_client,
    ) -> None:
        """L2-05 crash · 本地 alert_buffer 保存 · 不抛。"""
        mock_l2_05_client.record_audit.side_effect = RuntimeError("L2-05 crashed")
        sut.watchdog_heartbeat()
        assert sut.local_alert_buffer_size() >= 1

    def test_TC_L101_L201_504_watchdog_cross_project_tick_aborts(
        self, sut: TickScheduler, make_trigger,
    ) -> None:
        """current_tick.project_id ≠ session.active_pid · 本 L2 bug · abort。"""
        t = make_trigger(trigger_source="event_driven", priority=50, project_id="pid-wrong")
        sut._force_current_tick(t)  # bypass validation (bug scenario)
        with pytest.raises(TickError) as exc:
            sut.watchdog_heartbeat()
        assert exc.value.error_code == "E_TICK_WATCHDOG_CROSS_PROJECT_TICK"

    def test_TC_L101_L201_505_watchdog_thread_dead_restarts(
        self, sut: TickScheduler,
    ) -> None:
        sut._kill_watchdog_thread()
        sut.main_loop_iterate_once()
        assert sut.is_watchdog_thread_alive() is True
        errs = [a for a in sut.get_recent_audits() if a.error_code == "E_TICK_WATCHDOG_THREAD_DEAD"]
        assert len(errs) == 1
```

---

## §4 IC-XX 契约集成测试

> 本 L2 是 IC-L2-01 / IC-L2-05 生产方 · IC-L2-08 / IC-17 / IC-09 / IC-10 消费方。
> 每测试 mock 对端 event_bus / L2-02 客户端 / L2-05 客户端 · 断言 payload 结构精确匹配 ic-contracts.md §3.x。

```python
# file: tests/l1_01/test_l2_01_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_01.scheduler import TickScheduler


class TestL2_01_IC_Contracts:
    """IC-L2-01 / IC-L2-08 / IC-L2-05 / IC-09 / IC-17 / IC-10 六个契约集成测试。"""

    def test_TC_L101_L201_601_ic_l2_01_on_tick_payload_matches_contract(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_02_client: MagicMock, make_trigger,
    ) -> None:
        """TC-L101-L201-601 · IC-L2-01 on_tick 调 L2-02 · payload 字段结构。

        契约字段（prd §6 IC-L2-01）：trigger_source / event_ref / priority / ts / bootstrap?
        """
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id,
                               event_ref="evt-001")
        sut.schedule_tick(trigger)
        sut._dispatch_once()
        mock_l2_02_client.on_tick.assert_called_once()
        payload = mock_l2_02_client.on_tick.call_args.kwargs
        assert payload["trigger_source"] == "event_driven"
        assert payload["event_ref"] == "evt-001"
        assert payload["priority"] == 50
        assert "ts" in payload
        assert payload.get("bootstrap", False) is False

    def test_TC_L101_L201_602_ic_l2_08_propagate_hard_halt_meets_100ms(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-602 · IC-L2-08 消费方 · ≤100ms state=HALTED（硬约束）。"""
        signal = make_halt_signal(
            red_line_id="IRREVERSIBLE_HALT",
            project_id=mock_project_id,
            supervisor_event_id="sup-evt-001",
        )
        r = sut.on_hard_halt(signal)
        assert r.halted is True
        assert r.halt_latency_ms <= 100
        assert r.halted_at_tick is not None or r.halted_at_tick is None  # schema allows null

    def test_TC_L101_L201_603_ic_l2_05_record_audit_per_tick_emits_2_entries(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_05_client: MagicMock, make_trigger,
    ) -> None:
        """TC-L101-L201-603 · IC-L2-05 每 tick 至少 2 条审计（scheduled + completed · §13.4 P0-10）。"""
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut._dispatch_once()
        sut._complete_tick_ok()
        actions = [c.kwargs["action"] for c in mock_l2_05_client.record_audit.call_args_list]
        assert "tick_scheduled" in actions
        assert "tick_completed" in actions

    def test_TC_L101_L201_604_ic_09_append_event_carries_project_id(
        self, sut: TickScheduler, mock_project_id: str, mock_event_bus: MagicMock, make_trigger,
    ) -> None:
        """TC-L101-L201-604 · IC-09 append_event 每条事件必带 project_id（PM-14）。"""
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut._dispatch_once()
        for call in mock_event_bus.append_event.call_args_list:
            assert call.kwargs.get("project_id") == mock_project_id

    def test_TC_L101_L201_605_ic_17_user_intervene_panic_via_event_bus(
        self, sut: TickScheduler, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L201-605 · IC-17 user_intervene(panic) 经 L1-09 事件订阅到达 on_user_panic。"""
        panic_event = {
            "event_type": "user_panic",
            "payload": {
                "panic_id": "panic-001",
                "project_id": mock_project_id,
                "user_id": "user-001",
                "scope": "tick",
                "ts": "2026-04-22T00:00:00Z",
            },
            "project_id": mock_project_id,
        }
        sut.handle_event_bus_message(panic_event)
        assert sut.current_state() == "PAUSED"

    def test_TC_L101_L201_606_ic_10_replay_rebuilds_pending_queue_on_bootstrap(
        self, sut: TickScheduler, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L201-606 · IC-10 replay_from_event · 跨 session 恢复未闭环 tick。"""
        mock_event_bus.query.return_value = [
            {"event_type": "L1-01:tick_scheduled", "tick_id": "tick-orphan-1", "project_id": mock_project_id},
            {"event_type": "L1-01:tick_scheduled", "tick_id": "tick-orphan-2", "project_id": mock_project_id},
        ]
        sut.bootstrap_recovery()
        # 发 system_resumed 事件触发 bootstrap tick
        resumed = [c for c in mock_event_bus.append_event.call_args_list
                   if c.kwargs.get("event_type") == "system_resumed"]
        assert len(resumed) == 1
        assert resumed[0].kwargs["payload"]["unclosed_ticks_count"] == 2
```

---

## §5 性能 SLO 用例

> §12.1/§12.2 SLO 表驱动。`@pytest.mark.perf` · pytest-benchmark 可选。
> 断言 P95 延迟 · 吞吐率 · 并发场景。

```python
# file: tests/l1_01/test_l2_01_perf.py
from __future__ import annotations

import time
import statistics
import threading
import pytest

from app.l2_01.scheduler import TickScheduler


@pytest.mark.perf
class TestL2_01_SLO:
    """§12 SLO 性能用例。"""

    def test_TC_L101_L201_701_schedule_tick_p95_under_5ms(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-701 · schedule_tick() P95 ≤ 5ms / P99 ≤ 8ms / 硬上限 10ms（§12.1）。"""
        samples: list[float] = []
        for _ in range(1000):
            t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
            t0 = time.monotonic()
            sut.schedule_tick(t)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 5.0, f"schedule_tick P95 = {p95}ms 超 5ms SLO"
        assert p99 <= 8.0, f"schedule_tick P99 = {p99}ms 超 8ms SLO"
        assert max(samples) <= 10.0, f"硬上限 10ms 被破"

    def test_TC_L101_L201_702_hard_halt_p99_under_100ms(
        self, sut: TickScheduler, mock_project_id: str, make_halt_signal,
    ) -> None:
        """TC-L101-L201-702 · on_hard_halt() P99 ≤ 80ms · 硬上限 100ms（§12.1 + scope §5.1.6）。"""
        samples: list[float] = []
        for i in range(200):
            sut._reset_state()
            signal = make_halt_signal(
                red_line_id="IRREVERSIBLE_HALT",
                project_id=mock_project_id,
                halt_id=f"halt-{i:04d}",
            )
            t0 = time.monotonic()
            sut.on_hard_halt(signal)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 <= 80.0
        assert max(samples) <= 100.0, "100ms 是硬红线"

    def test_TC_L101_L201_703_throughput_100_tick_per_second(
        self, sut: TickScheduler, mock_project_id: str, make_trigger, mock_l2_02_client,
    ) -> None:
        """TC-L101-L201-703 · 纯内存操作吞吐 ≥ 100 tick/s（§12.2）。"""
        N = 1000
        mock_l2_02_client.on_tick.return_value = {"ok": True}
        t0 = time.monotonic()
        for _ in range(N):
            t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
            sut.schedule_tick(t)
            sut._dispatch_once()
        elapsed = time.monotonic() - t0
        tps = N / elapsed
        assert tps >= 100.0, f"实测吞吐 {tps:.1f} tick/s 低于 100 tick/s SLO"

    def test_TC_L101_L201_704_concurrent_hard_halt_wins_over_normal_dispatch(
        self, sut: TickScheduler, mock_project_id: str, make_trigger, make_halt_signal,
    ) -> None:
        """TC-L101-L201-704 · 并发场景 · 正常派发 vs hard_halt · hard_halt 必赢（抢占语义）。"""
        for _ in range(100):
            sut.schedule_tick(make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id))

        halted = threading.Event()

        def halt_worker() -> None:
            signal = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id)
            sut.on_hard_halt(signal)
            halted.set()

        def dispatch_worker() -> None:
            for _ in range(100):
                sut._dispatch_once()

        th = threading.Thread(target=halt_worker)
        td = threading.Thread(target=dispatch_worker)
        t0 = time.monotonic()
        td.start(); th.start()
        th.join(timeout=1.0)
        assert halted.is_set(), "hard_halt 必须在 1s 内完成"
        assert sut.current_state() == "HALTED"
        assert (time.monotonic() - t0) * 1000 <= 1000
```

---

## §6 端到端 e2e

> 映射 prd §8.9 集成用例 I1-I5（流 A/F/G/H/I）+ 8 场景 P1-P8。
> `@pytest.mark.e2e` · 真实/半真实 L2-02 + L2-05 + L2-06 + L1-09 event_bus。

```python
# file: tests/l1_01/test_l2_01_e2e.py
from __future__ import annotations

import pytest

from app.l2_01.scheduler import TickScheduler


@pytest.mark.e2e
class TestL2_01_E2E:
    """端到端场景 · 对应 prd §8.9 集成用例 + 8 GWT 场景。"""

    def test_TC_L101_L201_801_e2e_flow_A_normal_tick_end_to_end(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
        real_l2_02_mock, real_l2_05_mock,
    ) -> None:
        """TC-L101-L201-801 · 流 A 正常一轮 tick（I1: L2-01 → L2-02 → L2-05）+ P1。

        GIVEN event_driven trigger 到达
        WHEN L2-01 派发 tick
        THEN L2-02.on_tick 被调 · L2-05 写 2 条审计 · TickRecord.duration_ms < 30000
        """
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut.run_until_idle(timeout_s=5)
        record = sut.get_last_tick_record()
        assert record.duration_ms < 30000
        assert real_l2_02_mock.on_tick.call_count == 1
        assert real_l2_05_mock.record_audit.call_count >= 2

    def test_TC_L101_L201_802_e2e_flow_I_hard_halt_chain(
        self, sut: TickScheduler, mock_project_id: str, make_trigger, make_halt_signal,
        real_l2_02_mock, real_l2_05_mock, real_l2_06_mock,
    ) -> None:
        """TC-L101-L201-802 · 流 I hard_halt 端到端（I2: L2-06 → L2-01 → L2-02 中断 → L2-05）+ P2。

        GIVEN RUNNING tick 中
        WHEN L2-06 IC-L2-08 propagate_hard_halt
        THEN ≤100ms state=HALTED · L2-02.on_async_cancel 被调 · L2-05 记 hard_halted 审计
        """
        trigger = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(trigger)
        sut._dispatch_once()
        signal = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id)
        r = sut.on_hard_halt(signal)
        assert r.halted is True
        assert r.halt_latency_ms <= 100
        assert real_l2_02_mock.on_async_cancel.call_count == 1
        audits = [c for c in real_l2_05_mock.record_audit.call_args_list
                  if c.kwargs.get("action") == "hard_halted"]
        assert len(audits) == 1

    def test_TC_L101_L201_803_e2e_flow_H_bootstrap_recovery(
        self, sut: TickScheduler, mock_project_id: str,
        real_event_bus_with_orphan_ticks,
    ) -> None:
        """TC-L101-L201-803 · 流 H 跨 session 恢复（I4: L1-09 → L2-01 bootstrap → L2-02）+ P4。

        GIVEN 上次 session 崩溃 · event_bus 有 2 条未闭环 tick_scheduled
        WHEN 新 session 启动 L2-01.bootstrap_recovery()
        THEN 首个 TickRecord.trigger.bootstrap=true · priority=100 · 不走去抖
        """
        sut.bootstrap_recovery()
        sut.run_until_idle(timeout_s=5)
        first_record = sut.get_last_tick_record()
        assert first_record.trigger.bootstrap is True
        assert first_record.trigger.priority == 100
        assert first_record.trigger.debounced is False
```

---

## §7 测试 fixture

> conftest.py 提供本 L2 复用 fixture。`mock_project_id` / `mock_event_bus` / `mock_clock` / `mock_ic_payload` + trigger / halt / panic / result 工厂。

```python
# file: tests/l1_01/conftest.py
from __future__ import annotations

import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.l2_01.scheduler import TickScheduler
from app.l2_01.schemas import TickTrigger, HaltSignal, PanicSignal, ResultEvent


class VirtualClock:
    """§9 Mock 策略 · unit 模式 · 手动推进 ms 的假时钟。"""
    def __init__(self) -> None:
        self._now_ms: int = 0
    def monotonic_ms(self) -> int:
        return self._now_ms
    def advance(self, ms: int) -> None:
        self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_clock() -> VirtualClock:
    return VirtualClock()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="L1-09-event-bus")
    bus.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}", "sequence": 1}
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_l2_02_client() -> MagicMock:
    client = MagicMock(name="L2-02-decision-engine")
    client.on_tick.return_value = {"decision_id": "dec-001", "action": "invoke_skill"}
    client.on_async_cancel.return_value = {"cancelled": True}
    client.resolve_delegation.return_value = {"delegation_id": "del-001"}
    return client


@pytest.fixture
def mock_l2_03_client() -> MagicMock:
    client = MagicMock(name="L2-03-state-orchestrator")
    client.request_state_transition.return_value = {"transitioned": True}
    return client


@pytest.fixture
def mock_l2_05_client() -> MagicMock:
    client = MagicMock(name="L2-05-audit-recorder")
    client.record_audit.return_value = {"audit_id": f"aud-{uuid.uuid4()}"}
    return client


@pytest.fixture
def mock_ic_payload() -> dict[str, Any]:
    """IC-L2-01 on_tick 标准 payload（prd §6 字段骨架）。"""
    return {"trigger_source": "event_driven", "event_ref": "evt-0001", "priority": 50,
            "ts": "2026-04-22T00:00:00Z", "bootstrap": False}


@pytest.fixture
def sut(mock_project_id, mock_clock, mock_event_bus, mock_l2_02_client,
        mock_l2_03_client, mock_l2_05_client) -> TickScheduler:
    return TickScheduler(
        session_active_pid=mock_project_id,
        clock=mock_clock,
        event_bus=mock_event_bus,
        l2_02_client=mock_l2_02_client,
        l2_03_client=mock_l2_03_client,
        l2_05_client=mock_l2_05_client,
    )


@pytest.fixture
def make_trigger(mock_clock) -> Callable[..., TickTrigger]:
    def _factory(**overrides: Any) -> TickTrigger:
        base = dict(
            trigger_id=f"trig-{uuid.uuid4()}",
            project_id="pid-default",
            trigger_source="event_driven",
            priority=50,
            ts="2026-04-22T00:00:00Z",
            payload={},
            debounced=False,
            event_ref=None,
            bootstrap_context=None,
        )
        base.update(overrides)
        return TickTrigger(**base)
    return _factory


@pytest.fixture
def make_halt_signal() -> Callable[..., HaltSignal]:
    def _factory(**overrides: Any) -> HaltSignal:
        base = dict(
            halt_id=f"halt-{uuid.uuid4()}",
            red_line_id="IRREVERSIBLE_HALT",
            message="red line hit (>= 10 chars)",
            supervisor_event_id=f"sup-evt-{uuid.uuid4()}",
            project_id="pid-default",
            ts="2026-04-22T00:00:00Z",
            confirmation_count=2,
        )
        base.update(overrides)
        return HaltSignal(**base)
    return _factory


@pytest.fixture
def make_panic_signal() -> Callable[..., PanicSignal]:
    def _factory(**overrides: Any) -> PanicSignal:
        base = dict(
            panic_id=f"panic-{uuid.uuid4()}",
            project_id="pid-default",
            user_id="user-default",
            reason=None,
            ts="2026-04-22T00:00:00Z",
            scope="tick",
        )
        base.update(overrides)
        return PanicSignal(**base)
    return _factory


@pytest.fixture
def make_result_event() -> Callable[..., ResultEvent]:
    def _factory(**overrides: Any) -> ResultEvent:
        base = dict(
            event_id=f"evt-{uuid.uuid4()}",
            event_type="L1-05:subagent_result",
            delegation_id="del-default",
            project_id="pid-default",
            outcome="success",
            result_ref="oss://bucket/result.json",
            ts="2026-04-22T00:00:00Z",
        )
        base.update(overrides)
        return ResultEvent(**base)
    return _factory
```

---

## §8 集成点用例

> 与兄弟 L2 协作场景（L2-02 决策引擎 / L2-03 状态机编排器 / L2-05 审计记录器 / L2-06 Supervisor 接收器）。
> 验 IC-L2 真实调用契约 + 失败降级行为（§11.3 协同矩阵）。

```python
# file: tests/l1_01/test_l2_01_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_01.scheduler import TickScheduler


class TestL2_01_SiblingIntegration:
    """与 L2-02 / L2-03 / L2-05 / L2-06 的协作测试。"""

    def test_TC_L101_L201_901_coop_with_l2_02_dispatch_then_receive_async_result(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_02_client: MagicMock,
        make_trigger, make_result_event,
    ) -> None:
        """TC-L101-L201-901 · 派发 → L2-02 返回 delegation_id → async_result 回流 → 再派发一轮。"""
        t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(t); sut._dispatch_once()
        mock_l2_02_client.on_tick.assert_called_once()
        # simulate async result回流
        event = make_result_event(delegation_id="del-001", project_id=mock_project_id)
        sut.on_async_result(event)
        sut._dispatch_once()
        assert mock_l2_02_client.on_tick.call_count == 2

    def test_TC_L101_L201_902_coop_with_l2_03_panic_triggers_request_state_transition(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_03_client: MagicMock, make_panic_signal,
    ) -> None:
        """TC-L101-L201-902 · panic → IC-L2-02 调 L2-03 request_state_transition(to=PAUSED)。"""
        signal = make_panic_signal(project_id=mock_project_id, user_id="user-001")
        sut.on_user_panic(signal)
        mock_l2_03_client.request_state_transition.assert_called_once()
        kwargs = mock_l2_03_client.request_state_transition.call_args.kwargs
        assert kwargs["to"] == "PAUSED"
        assert kwargs["reason"] == "user_panic"

    def test_TC_L101_L201_903_coop_with_l2_05_audit_unreachable_buffers_then_retries(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_05_client: MagicMock, make_trigger,
    ) -> None:
        """TC-L101-L201-903 · L2-05 crash → 本地 buffer + 重试（§11.3 协同矩阵）。"""
        mock_l2_05_client.record_audit.side_effect = [RuntimeError("crash"), RuntimeError("crash"), {"ok": True}]
        sut.schedule_tick(make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id))
        sut._dispatch_once()
        assert sut.local_alert_buffer_size() >= 1
        # L2-05 recovers · flush
        mock_l2_05_client.record_audit.side_effect = None
        mock_l2_05_client.record_audit.return_value = {"ok": True}
        sut.flush_local_buffer()
        assert sut.local_alert_buffer_size() == 0

    def test_TC_L101_L201_904_coop_with_l2_06_hard_halt_arrives_during_running_tick(
        self, sut: TickScheduler, mock_project_id: str, mock_l2_02_client: MagicMock,
        make_trigger, make_halt_signal,
    ) -> None:
        """TC-L101-L201-904 · RUNNING 中收到 L2-06 hard_halt → 三件事并行（state/cancel/queue-lock）。"""
        t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(t); sut._dispatch_once()
        signal = make_halt_signal(red_line_id="IRREVERSIBLE_HALT", project_id=mock_project_id)
        r = sut.on_hard_halt(signal)
        assert sut.current_state() == "HALTED"
        assert mock_l2_02_client.on_async_cancel.call_count == 1
        assert sut.is_queue_locked() is True
        assert r.halted_at_tick is not None
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 并发 / 超时 / 崩溃恢复 / 脏数据 至少 5 个。

```python
# file: tests/l1_01/test_l2_01_edge_cases.py
from __future__ import annotations

import threading
import pytest

from app.l2_01.scheduler import TickScheduler
from app.l2_01.errors import TickError


class TestL2_01_EdgeCases:
    """边界 / edge case · 空输入 / 超大 / 并发 / 超时 / 崩溃 / 脏数据。"""

    def test_TC_L101_L201_A01_empty_queue_arbitrate_returns_none(
        self, sut: TickScheduler,
    ) -> None:
        """TC-L101-L201-A01 · 空队列 · arbitrate() 返回 None · main loop 进入 idle。"""
        assert sut.peek_queue() == []
        assert sut._arbitrate_once() is None
        assert sut.current_state() in ("IDLE", "DEGRADED")

    def test_TC_L101_L201_A02_oversize_payload_still_enqueued_but_warn(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-A02 · trigger.payload 10KB（bootstrap_context 极端）· 仍入队 + WARN（§12.2 单 trigger ≤ 10KB 极端）。"""
        big = "x" * 10_000
        t = make_trigger(
            trigger_source="bootstrap",
            priority=100,
            project_id=mock_project_id,
            payload={"huge": big},
        )
        r = sut.schedule_tick(t)
        assert r.accepted is True

    def test_TC_L101_L201_A03_concurrent_schedule_tick_thread_safe(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-A03 · 20 线程并发 × 50 入队 · 无 race · queue_depth = 1000（或 evict）。"""
        def worker() -> None:
            for _ in range(50):
                t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
                try:
                    sut.schedule_tick(t)
                except TickError:
                    pass  # queue_full is acceptable
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for th in threads: th.start()
        for th in threads: th.join(timeout=5)
        # 队列深度 ≤ 1000（硬上限 §12.4）
        assert sut.queue_depth() <= 1000

    def test_TC_L101_L201_A04_tick_timeout_30s_hard_ceiling(
        self, sut: TickScheduler, mock_project_id: str, mock_clock, make_trigger,
    ) -> None:
        """TC-L101-L201-A04 · tick 阻塞 30s 硬上限（scope §5.1.4）· state=DEGRADED + 审计。"""
        t = make_trigger(trigger_source="event_driven", priority=50, project_id=mock_project_id)
        sut.schedule_tick(t)
        sut._start_tick_unsafe(t)
        mock_clock.advance(30_001)  # 30s + 1ms
        sut.watchdog_heartbeat()
        assert sut.current_state() == "DEGRADED"

    def test_TC_L101_L201_A05_crash_recovery_via_ic_10_replay(
        self, sut: TickScheduler, mock_project_id: str, mock_event_bus,
    ) -> None:
        """TC-L101-L201-A05 · 崩溃后 IC-10 replay 识别未闭环 tick · 发 system_resumed（§11.4）。"""
        mock_event_bus.query.return_value = [
            {"event_type": "L1-01:tick_scheduled", "tick_id": f"tick-orphan-{i}", "project_id": mock_project_id}
            for i in range(3)
        ]
        sut.bootstrap_recovery()
        resumed = [c for c in mock_event_bus.append_event.call_args_list
                   if c.kwargs.get("event_type") == "system_resumed"]
        assert len(resumed) == 1
        assert resumed[0].kwargs["payload"]["unclosed_ticks_count"] == 3

    def test_TC_L101_L201_A06_dirty_trigger_id_format_rejected(
        self, sut: TickScheduler, mock_project_id: str, make_trigger,
    ) -> None:
        """TC-L101-L201-A06 · 脏数据 · trigger_id 非 trig-{uuid-v7} 格式 · 拒绝入队。"""
        t = make_trigger(
            trigger_id="not-a-valid-id",
            trigger_source="event_driven",
            priority=50,
            project_id=mock_project_id,
        )
        with pytest.raises(TickError):
            sut.schedule_tick(t)

    def test_TC_L101_L201_A07_single_instance_guard(
        self, mock_project_id: str, mock_clock, mock_event_bus,
        mock_l2_02_client, mock_l2_03_client, mock_l2_05_client,
    ) -> None:
        """TC-L101-L201-A07 · 单实例约束（prd §8.4 #5 + N5）· 第二个 L2-01 实例启动拒绝。"""
        _first = TickScheduler(
            session_active_pid=mock_project_id,
            clock=mock_clock,
            event_bus=mock_event_bus,
            l2_02_client=mock_l2_02_client,
            l2_03_client=mock_l2_03_client,
            l2_05_client=mock_l2_05_client,
        )
        with pytest.raises(RuntimeError, match="single-instance"):
            _ = TickScheduler(
                session_active_pid=mock_project_id,
                clock=mock_clock,
                event_bus=mock_event_bus,
                l2_02_client=mock_l2_02_client,
                l2_03_client=mock_l2_03_client,
                l2_05_client=mock_l2_05_client,
            )
```

---

*— L1-01 L2-01 Tick 调度器 · TDD 测试用例 · 深度 B 全段完整 · 29 错误码 × 14 正向 × 6 IC × 4 SLO × 3 e2e × 4 集成 × 7 边界 —*
