"""ε-WP04 · L2-04 完成度追踪器单元测试（≥ 36 TC）。

覆盖：
- §1 burndown compute · effort-based（非 count）
- §2 ProgressSnapshot / BurndownPoint schemas
- §3 ProgressEventSubscriber · 事件解码 + 分发
- §4 ProgressTracker · on_wp_done / on_wp_failed 驱动 state 转换
- §5 ProgressTracker · 幂等（同 event_id 只处理一次）
- §6 ProgressTracker · PM-14 跨 pid 忽略
- §7 ProgressTracker · Rollback coordinator 转发
- §8 ProgressTracker · 订阅生命周期 · metrics_updated 事件
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.progress import (
    BurndownPoint,
    ProgressEventSubscriber,
    ProgressSnapshot,
    ProgressTracker,
    RollbackCoordinatorProtocol,
    WPCompletionEvent,
    WPFailureEvent,
    compute_burndown,
)
from app.l1_03.progress.burndown import completion_rate
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State

# =====================================================================
# fixtures
# =====================================================================

@pytest.fixture
def loaded_manager(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> WBSTopologyManager:
    mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    wps = [
        make_wp("wp-a", effort_estimate=2.0),
        make_wp("wp-b", effort_estimate=3.0),
        make_wp("wp-c", effort_estimate=1.0),
    ]
    mgr.load_topology(wps, [])
    return mgr


class _FakeRollback:
    """轻量 rollback coordinator · 捕获调用以便 assert。"""

    def __init__(self) -> None:
        self.failed_calls: list[tuple[str, str, str]] = []
        self.done_reset_calls: list[str] = []

    def on_wp_failed(
        self, wp_id: str, reason: str, fail_level: str = "L2",
        evidence_ref: str | None = None,
    ) -> None:
        self.failed_calls.append((wp_id, reason, fail_level))

    def on_wp_done_reset(self, wp_id: str) -> None:
        self.done_reset_calls.append(wp_id)


@pytest.fixture
def rollback() -> _FakeRollback:
    return _FakeRollback()


@pytest.fixture
def tracker(
    loaded_manager: WBSTopologyManager, event_bus: EventBusStub, rollback: _FakeRollback,
) -> ProgressTracker:
    t = ProgressTracker(loaded_manager, event_bus, rollback_coordinator=rollback)
    t.register()
    return t


# =====================================================================
# §1 burndown
# =====================================================================

class TestBurndown:
    def test_TC_L103_L204_001_effort_based(self, project_id: str, make_wp) -> None:
        """effort-based 计算 · 非 WP count。"""
        wps = [
            make_wp("wp-a", effort_estimate=2.0),
            make_wp("wp-b", effort_estimate=3.0),
            make_wp("wp-c", effort_estimate=1.0),
        ]
        total, done = compute_burndown(wps)
        assert total == 6.0
        assert done == 0.0
        wps[0].state = State.DONE
        total, done = compute_burndown(wps)
        assert total == 6.0
        assert done == 2.0
        wps[1].state = State.DONE
        total, done = compute_burndown(wps)
        assert done == 5.0  # 2+3 · 不是 2（即不是 count）

    def test_empty_wps_yields_zero(self) -> None:
        total, done = compute_burndown([])
        assert total == 0.0
        assert done == 0.0

    def test_completion_rate_zero_total(self) -> None:
        assert completion_rate(0.0, 0.0) == 0.0
        assert completion_rate(0.0, 5.0) == 0.0  # 防御：total=0 也返 0

    def test_completion_rate_bounded(self) -> None:
        assert completion_rate(10.0, 0.0) == 0.0
        assert completion_rate(10.0, 5.0) == 0.5
        assert completion_rate(10.0, 10.0) == 1.0
        # 边界防御：done > total 也封顶 1.0
        assert completion_rate(10.0, 15.0) == 1.0


# =====================================================================
# §2 Schemas
# =====================================================================

class TestSchemas:
    def test_burndown_point_frozen(self) -> None:
        bp = BurndownPoint(ts=1.0, remaining_effort=5.0, done_wp_count=2)
        with pytest.raises(ValidationError):
            bp.ts = 2.0  # type: ignore[misc]

    def test_burndown_point_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            BurndownPoint(ts=1.0, remaining_effort=-1.0, done_wp_count=0)
        with pytest.raises(ValidationError):
            BurndownPoint(ts=1.0, remaining_effort=0.0, done_wp_count=-1)

    def test_progress_snapshot_rate_in_range(self) -> None:
        with pytest.raises(ValidationError):
            ProgressSnapshot(
                project_id="pid-a",
                topology_version="v1",
                total_effort=10.0, done_effort=5.0, remaining_effort=5.0,
                completion_rate=1.5,  # 超 1
            )

    def test_progress_snapshot_defaults(self) -> None:
        s = ProgressSnapshot(
            project_id="pid-a",
            topology_version="v1",
            total_effort=0.0, done_effort=0.0,
            remaining_effort=0.0, completion_rate=0.0,
        )
        assert s.done_wps == []
        assert s.burndown_series == []


# =====================================================================
# §3 ProgressEventSubscriber
# =====================================================================

class TestEventSubscriberDecoding:
    def test_decodes_wp_executed(self, project_id: str) -> None:
        received: list[WPCompletionEvent] = []
        sub = ProgressEventSubscriber(on_done=lambda e: received.append(e))
        sub({
            "type": "L1-04:wp_executed",
            "event_id": "evt-1",
            "project_id": project_id,
            "content": {
                "wp_id": "wp-a", "commit_sha": "abc",
                "duration_ms": 1200, "verifier_verdict": "PASS",
            },
        })
        assert len(received) == 1
        assert received[0].wp_id == "wp-a"
        assert received[0].commit_sha == "abc"
        assert received[0].duration_ms == 1200

    def test_decodes_wp_verified_pass(self, project_id: str) -> None:
        received: list[WPCompletionEvent] = []
        sub = ProgressEventSubscriber(on_done=lambda e: received.append(e))
        sub({
            "type": "L1-04:wp_verified_pass",
            "event_id": "evt-2",
            "project_id": project_id,
            "content": {"wp_id": "wp-b"},
        })
        assert len(received) == 1
        assert received[0].wp_id == "wp-b"

    def test_decodes_wp_failed(self, project_id: str) -> None:
        received: list[WPFailureEvent] = []
        sub = ProgressEventSubscriber(on_failed=lambda e: received.append(e))
        sub({
            "type": "L1-04:wp_failed",
            "event_id": "evt-3",
            "project_id": project_id,
            "content": {
                "wp_id": "wp-c", "fail_level": "L3",
                "reason_summary": "boom",
            },
        })
        assert len(received) == 1
        assert received[0].wp_id == "wp-c"
        assert received[0].fail_level == "L3"

    def test_unknown_event_type_ignored(self, project_id: str) -> None:
        received_done: list = []
        received_fail: list = []
        sub = ProgressEventSubscriber(
            on_done=lambda e: received_done.append(e),
            on_failed=lambda e: received_fail.append(e),
        )
        sub({"type": "L1-03:wbs_decomposed", "event_id": "x", "project_id": project_id, "content": {}})
        assert received_done == []
        assert received_fail == []

    def test_missing_wp_id_skipped(self, project_id: str) -> None:
        received: list = []
        sub = ProgressEventSubscriber(on_done=lambda e: received.append(e))
        sub({
            "type": "L1-04:wp_executed", "event_id": "x",
            "project_id": project_id, "content": {},  # 缺 wp_id
        })
        assert received == []

    def test_no_handler_no_crash(self, project_id: str) -> None:
        sub = ProgressEventSubscriber()
        # 无 handler 时调用也不 crash
        sub({"type": "L1-04:wp_executed", "event_id": "x", "project_id": project_id,
             "content": {"wp_id": "wp-a"}})


# =====================================================================
# §4 Tracker · 事件驱动 state 转换
# =====================================================================

class TestTrackerStateTransitions:
    def test_TC_L103_L204_005_on_wp_done_transitions_to_done(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        ev = WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-1",
        )
        tracker.on_wp_done(ev)
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.DONE

    def test_on_wp_failed_transitions_to_failed(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str, rollback: _FakeRollback,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        ev = WPFailureEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-2",
            fail_level="L2", reason_summary="boom",
        )
        tracker.on_wp_failed(ev)
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.FAILED
        # 转发到 rollback
        assert rollback.failed_calls == [("wp-a", "boom", "L2")]

    def test_on_wp_done_triggers_reset_in_rollback(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str, rollback: _FakeRollback,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-1",
        ))
        assert rollback.done_reset_calls == ["wp-a"]


# =====================================================================
# §5 幂等性
# =====================================================================

class TestTrackerIdempotency:
    def test_TC_L103_L204_015_repeat_done_is_noop(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str, rollback: _FakeRollback,
    ) -> None:
        """同 event_id 重复触发只处理一次（transition 幂等 + rollback.on_done_reset 只调一次）。"""
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        ev = WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-dup",
        )
        tracker.on_wp_done(ev)
        tracker.on_wp_done(ev)  # 重放同 event_id
        tracker.on_wp_done(ev)
        assert rollback.done_reset_calls == ["wp-a"]  # 只一次

    def test_repeat_failed_is_noop(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str, rollback: _FakeRollback,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        ev = WPFailureEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-f",
            reason_summary="x",
        )
        tracker.on_wp_failed(ev)
        tracker.on_wp_failed(ev)
        tracker.on_wp_failed(ev)
        assert len(rollback.failed_calls) == 1

    def test_done_for_not_running_wp_silently_skipped(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str, rollback: _FakeRollback,
    ) -> None:
        """wp 不处于 RUNNING · 事件来了也不 raise · 静默 skip。"""
        # wp-a 在 READY（未 RUNNING）· 事件来
        ev = WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="evt-skip",
        )
        tracker.on_wp_done(ev)
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.READY  # 没变
        assert rollback.done_reset_calls == []  # 也不 reset

    def test_unknown_wp_silently_skipped(
        self, tracker: ProgressTracker, project_id: str,
    ) -> None:
        ev = WPCompletionEvent(
            wp_id="wp-ghost", project_id=project_id, event_id="evt-g",
        )
        tracker.on_wp_done(ev)  # 不 raise


# =====================================================================
# §6 PM-14
# =====================================================================

class TestTrackerPM14:
    def test_cross_pid_event_ignored(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        rollback: _FakeRollback,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        ev = WPCompletionEvent(
            wp_id="wp-a", project_id="pid-OTHER", event_id="evt-cross",
        )
        tracker.on_wp_done(ev)
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.RUNNING  # 未变
        assert rollback.done_reset_calls == []


# =====================================================================
# §7 subscribe 生命周期
# =====================================================================

class TestSubscriberLifecycle:
    def test_subscribe_receives_wp_done(
        self, loaded_manager: WBSTopologyManager, event_bus: EventBusStub,
        rollback: _FakeRollback, project_id: str,
    ) -> None:
        t = ProgressTracker(loaded_manager, event_bus, rollback_coordinator=rollback)
        t.register()
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        # 通过 event_bus append 触发订阅者
        event_bus.append(
            event_type="L1-04:wp_executed",
            content={"wp_id": "wp-a"},
            project_id=project_id,
        )
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.DONE

    def test_unregister_stops_subscription(
        self, loaded_manager: WBSTopologyManager, event_bus: EventBusStub,
        rollback: _FakeRollback, project_id: str,
    ) -> None:
        t = ProgressTracker(loaded_manager, event_bus, rollback_coordinator=rollback)
        t.register()
        t.unregister()
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        event_bus.append(
            event_type="L1-04:wp_executed",
            content={"wp_id": "wp-a"},
            project_id=project_id,
        )
        wp = loaded_manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.RUNNING  # 仍 RUNNING

    def test_event_bus_none_silent(
        self, loaded_manager: WBSTopologyManager,
    ) -> None:
        """event_bus=None · register/unregister no-op。"""
        t = ProgressTracker(loaded_manager, event_bus=None)
        t.register()
        t.unregister()  # 不 crash


# =====================================================================
# §8 progress_snapshot
# =====================================================================

class TestProgressSnapshot:
    def test_initial_snapshot_zero_done(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
    ) -> None:
        snap = tracker.progress_snapshot()
        assert snap.total_effort == 6.0  # 2+3+1
        assert snap.done_effort == 0.0
        assert snap.completion_rate == 0.0
        assert len(snap.ready_wps) == 3

    def test_snapshot_after_done(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="e1",
        ))
        snap = tracker.progress_snapshot()
        assert snap.done_effort == 2.0
        assert snap.completion_rate == 2.0 / 6.0
        assert "wp-a" in snap.done_wps

    def test_snapshot_burndown_series_grows(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="e1",
        ))
        loaded_manager.transition_state("wp-b", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-b", project_id=project_id, event_id="e2",
        ))
        snap = tracker.progress_snapshot()
        assert len(snap.burndown_series) == 2
        # 后面的 remaining 一定 ≤ 前面的
        assert snap.burndown_series[1].remaining_effort < snap.burndown_series[0].remaining_effort

    def test_snapshot_categorizes_by_state(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        project_id: str,
    ) -> None:
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        loaded_manager.transition_state("wp-b", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="e1",
        ))
        snap = tracker.progress_snapshot()
        assert "wp-a" in snap.done_wps
        assert "wp-b" in snap.running_wps
        assert "wp-c" in snap.ready_wps

    def test_snapshot_no_topology_yields_zero(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        t = ProgressTracker(mgr, event_bus)
        snap = t.progress_snapshot()
        assert snap.total_effort == 0.0
        assert snap.completion_rate == 0.0


# =====================================================================
# §9 metrics_updated event emit
# =====================================================================

class TestMetricsEmit:
    def test_emits_metrics_updated_on_done(
        self, loaded_manager: WBSTopologyManager, tracker: ProgressTracker,
        event_bus: EventBusStub, project_id: str,
    ) -> None:
        event_bus.reset()
        tracker = ProgressTracker(loaded_manager, event_bus)
        tracker.register()
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        tracker.on_wp_done(WPCompletionEvent(
            wp_id="wp-a", project_id=project_id, event_id="e1",
        ))
        ev = event_bus.filter(event_type="L1-03:progress_metrics_updated")
        assert len(ev) == 1
        assert ev[0].content["completion_rate"] == pytest.approx(2.0 / 6.0)
        assert "wp-a" in ev[0].content["done_wps"]

    def test_emits_metrics_updated_on_failed(
        self, loaded_manager: WBSTopologyManager, event_bus: EventBusStub,
        project_id: str,
    ) -> None:
        event_bus.reset()
        tracker = ProgressTracker(loaded_manager, event_bus)
        tracker.register()
        loaded_manager.transition_state("wp-a", State.READY, State.RUNNING)
        tracker.on_wp_failed(WPFailureEvent(
            wp_id="wp-a", project_id=project_id, event_id="f1",
            reason_summary="x",
        ))
        ev = event_bus.filter(event_type="L1-03:progress_metrics_updated")
        assert len(ev) == 1


# =====================================================================
# §10 Protocol 签名 · 冒烟
# =====================================================================

class TestRollbackProtocol:
    def test_protocol_signature(self) -> None:
        """fake 实现类符合 Protocol · 静态类型不在运行时强验 · 仅冒烟。"""
        fake: RollbackCoordinatorProtocol = _FakeRollback()
        fake.on_wp_failed("wp-x", "r")
        fake.on_wp_done_reset("wp-x")
