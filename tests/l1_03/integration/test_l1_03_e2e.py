"""ε-WP06 · L1-03 端到端集成测试。

验证 5 L2 联调全链：WBS 拆解 → 拓扑装图 → 调度 → 完成追踪 → 失败回退。

场景覆盖：
1. 正向：3 WP 全跑通 · 进度 100%
2. 失败路径：1 WP 连续失败 3 次 → L2-05 升级 → IC-14 push
3. 死锁路径：所有 WP 都 STUCK → dispatcher deadlock → L2-05 IC-15 halt
4. 差量合并：WP 升级后 SPLIT_WP → L2-01 diff_merge → 新拓扑装图
"""

from __future__ import annotations

import pytest

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.common.skill_client_stub import SkillClientStub
from app.l1_03.progress import ProgressTracker, WPCompletionEvent, WPFailureEvent
from app.l1_03.rollback import Escalator, RollbackCoordinator
from app.l1_03.scheduler import GetNextWPQuery, WaitingReason, WPDispatcher
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_03.wbs_decomposer import (
    ArchitectureOutput,
    FourSetPlan,
    decompose_wbs,
)

# =====================================================================
# fixtures
# =====================================================================

@pytest.fixture
def four_pack() -> FourSetPlan:
    return FourSetPlan(
        charter_path="p/c", plan_path="p/p",
        requirements_path="p/r", risk_path="p/k",
    )


@pytest.fixture
def arch_out() -> ArchitectureOutput:
    return ArchitectureOutput(togaf_phases=["B", "C", "D"], adr_path="adr.md")


@pytest.fixture
def ecosystem(project_id: str, event_bus: EventBusStub):
    """全 5 L2 联起来的完整系统。"""
    skill = SkillClientStub()
    manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    escalator = Escalator()
    rollback = RollbackCoordinator(
        project_id=project_id, escalator=escalator,
        manager=manager, event_bus=event_bus,
    )
    tracker = ProgressTracker(manager, event_bus, rollback_coordinator=rollback)
    tracker.register()
    dispatcher = WPDispatcher(manager, event_bus)
    return {
        "skill": skill, "manager": manager, "escalator": escalator,
        "rollback": rollback, "tracker": tracker, "dispatcher": dispatcher,
        "event_bus": event_bus,
    }


# =====================================================================
# TC1 · 正向端到端
# =====================================================================

def test_TC_L103_E2E_001_full_pipeline_three_wps(
    ecosystem, project_id: str, four_pack, arch_out,
) -> None:
    """WBS 拆解 → 装图 → 调度 → 完成 → 进度 100%。"""
    env = ecosystem
    # Step A: L2-01 拆解
    draft = decompose_wbs(
        four_set_plan=four_pack, architecture_output=arch_out,
        project_id=project_id, skill_client=env["skill"], event_bus=env["event_bus"],
    )
    assert draft.wp_count == 3

    # Step B: L2-02 装图
    env["manager"].load_topology(draft.wp_list, draft.dag_edges)

    # Step C: 第一次 IC-02 → wp-a（唯一 READY · 无 deps）
    q1 = GetNextWPQuery(query_id="q1", project_id=project_id, requester_tick="t1")
    r1 = env["dispatcher"].get_next_wp(q1)
    assert r1.wp_id == "wp-a"
    assert r1.deps_met is True

    # Step D: L2-04 wp_done 事件 → state DONE · progress 更新
    env["tracker"].on_wp_done(WPCompletionEvent(
        wp_id="wp-a", project_id=project_id, event_id="evt-1",
    ))
    snap1 = env["tracker"].progress_snapshot()
    assert snap1.done_wps == ["wp-a"]
    assert snap1.completion_rate == pytest.approx(2.0 / 6.5)  # stub fixture: 2/(2+1.5+3)

    # Step E: 第二次 IC-02 → wp-b 或 wp-c（都 deps wp-a · 都 ready 了）
    q2 = GetNextWPQuery(query_id="q2", project_id=project_id, requester_tick="t2")
    r2 = env["dispatcher"].get_next_wp(q2)
    assert r2.wp_id in ("wp-b", "wp-c")

    # Step F: 把剩下的都跑完（串行，避开 concurrency cap）
    second_wp_id = r2.wp_id
    assert second_wp_id is not None
    env["tracker"].on_wp_done(WPCompletionEvent(
        wp_id=second_wp_id, project_id=project_id, event_id="evt-2",
    ))
    q3 = GetNextWPQuery(query_id="q3", project_id=project_id, requester_tick="t3")
    r3 = env["dispatcher"].get_next_wp(q3)
    assert r3.wp_id is not None
    env["tracker"].on_wp_done(WPCompletionEvent(
        wp_id=r3.wp_id, project_id=project_id, event_id="evt-3",
    ))

    # Step G: 所有 DONE · IC-02 返 null + all_done
    q4 = GetNextWPQuery(query_id="q4", project_id=project_id, requester_tick="t4")
    r4 = env["dispatcher"].get_next_wp(q4)
    assert r4.wp_id is None
    assert r4.waiting_reason == WaitingReason.ALL_DONE
    final_snap = env["tracker"].progress_snapshot()
    assert final_snap.completion_rate == 1.0


# =====================================================================
# TC2 · 失败升级路径
# =====================================================================

def test_TC_L103_E2E_002_failure_escalation_triggers_ic14(
    ecosystem, project_id: str, four_pack, arch_out,
) -> None:
    """wp-a 连续失败 3 次 → L2-05 IC-14 push_rollback_route + mark_stuck。"""
    env = ecosystem
    draft = decompose_wbs(
        four_set_plan=four_pack, architecture_output=arch_out,
        project_id=project_id, skill_client=env["skill"], event_bus=env["event_bus"],
    )
    env["manager"].load_topology(draft.wp_list, draft.dag_edges)

    for i in range(3):
        # 每轮：派 wp-a → RUNNING → failed → FAILED → READY（retry）
        env["manager"].transition_state("wp-a", State.READY, State.RUNNING)
        env["tracker"].on_wp_failed(WPFailureEvent(
            wp_id="wp-a", project_id=project_id, event_id=f"evt-fail-{i}",
            fail_level="L2", reason_summary=f"round {i+1}",
        ))
        # 在第 3 次失败前先把 wp-a 从 FAILED 弹回 READY（L2-05 retry 语义 · 这里手动）
        if i < 2:
            env["manager"].transition_state("wp-a", State.FAILED, State.READY)

    # 第 3 次失败 → L2-05 RETRY_3 → 发 IC-14
    assert len(env["escalator"].captured_routes) == 1
    advice = env["escalator"].captured_routes[0].advice
    assert advice.wp_id == "wp-a"
    assert advice.failure_count == 3
    assert len(advice.options) == 3
    # manager.mark_stuck 被调 · wp-a 已 STUCK
    wp = env["manager"].find_wp("wp-a")
    assert wp is not None and wp.state == State.STUCK


# =====================================================================
# TC3 · 死锁路径
# =====================================================================

def test_TC_L103_E2E_003_deadlock_triggers_hard_halt(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> None:
    """所有 WP 都 STUCK · dispatcher 返 deadlock · 外部通知 L2-05 发 IC-15。"""
    manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    escalator = Escalator()
    rollback = RollbackCoordinator(
        project_id=project_id, escalator=escalator,
        manager=manager, event_bus=event_bus,
    )
    dispatcher = WPDispatcher(manager, event_bus)
    wps = [make_wp("wp-a"), make_wp("wp-b")]
    manager.load_topology(wps, [])
    for wp_id in ("wp-a", "wp-b"):
        manager.transition_state(wp_id, State.READY, State.RUNNING)
        manager.transition_state(wp_id, State.RUNNING, State.FAILED)
        manager.mark_stuck(wp_id)

    q = GetNextWPQuery(query_id="q", project_id=project_id, requester_tick="t")
    r = dispatcher.get_next_wp(q)
    assert r.waiting_reason == WaitingReason.DEADLOCK

    # 把 deadlock 通知给 L2-05
    rollback.on_deadlock_notified(project_id, reason="all stuck")
    assert len(escalator.captured_halts) == 1


# =====================================================================
# TC4 · WBS → 装图链路（mock 事件）
# =====================================================================

def test_TC_L103_E2E_004_wbs_decomposed_then_loaded(
    ecosystem, project_id: str, four_pack, arch_out,
) -> None:
    """装图完成后 · 两个 L1-03 事件都进了 bus。"""
    env = ecosystem
    draft = decompose_wbs(
        four_set_plan=four_pack, architecture_output=arch_out,
        project_id=project_id, skill_client=env["skill"], event_bus=env["event_bus"],
    )
    env["manager"].load_topology(draft.wp_list, draft.dag_edges)
    bus: EventBusStub = env["event_bus"]
    assert len(bus.filter(event_type="L1-03:wbs_topology_ready")) == 1
    assert len(bus.filter(event_type="L1-03:wbs_decomposed")) == 1


# =====================================================================
# TC5 · 并发 cap
# =====================================================================

def test_TC_L103_E2E_005_concurrency_cap_across_layers(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> None:
    """2 WP RUNNING 后 · 调度第三个返 concurrency_cap。"""
    manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    dispatcher = WPDispatcher(manager, event_bus)
    wps = [make_wp("wp-a"), make_wp("wp-b"), make_wp("wp-c")]
    manager.load_topology(wps, [])
    q = GetNextWPQuery(query_id="q1", project_id=project_id, requester_tick="t1")
    r1 = dispatcher.get_next_wp(q)
    r2 = dispatcher.get_next_wp(q.model_copy(update={"query_id": "q2"}))
    assert r1.wp_id is not None and r2.wp_id is not None
    r3 = dispatcher.get_next_wp(q.model_copy(update={"query_id": "q3"}))
    assert r3.waiting_reason == WaitingReason.CONCURRENCY_CAP


# =====================================================================
# TC6 · tracker + rollback 联动 · done 后重置
# =====================================================================

def test_TC_L103_E2E_006_done_resets_failure_counter(
    ecosystem, project_id: str, four_pack, arch_out,
) -> None:
    """wp-a 失败 2 次 · 然后 done · FailureCounter 应 reset 到 NORMAL。"""
    env = ecosystem
    draft = decompose_wbs(
        four_set_plan=four_pack, architecture_output=arch_out,
        project_id=project_id, skill_client=env["skill"], event_bus=env["event_bus"],
    )
    env["manager"].load_topology(draft.wp_list, draft.dag_edges)
    env["manager"].transition_state("wp-a", State.READY, State.RUNNING)
    env["tracker"].on_wp_failed(WPFailureEvent(
        wp_id="wp-a", project_id=project_id, event_id="f1",
    ))
    env["manager"].transition_state("wp-a", State.FAILED, State.READY)
    env["manager"].transition_state("wp-a", State.READY, State.RUNNING)
    env["tracker"].on_wp_failed(WPFailureEvent(
        wp_id="wp-a", project_id=project_id, event_id="f2",
    ))
    from app.l1_03.rollback import FailureCounterState
    assert env["rollback"].counter.state_of("wp-a") == FailureCounterState.RETRY_2

    # 终于成功
    env["manager"].transition_state("wp-a", State.FAILED, State.READY)
    env["manager"].transition_state("wp-a", State.READY, State.RUNNING)
    env["tracker"].on_wp_done(WPCompletionEvent(
        wp_id="wp-a", project_id=project_id, event_id="d1",
    ))
    assert env["rollback"].counter.state_of("wp-a") == FailureCounterState.NORMAL


# =====================================================================
# TC7 · 多 event emit 验证
# =====================================================================

def test_TC_L103_E2E_007_events_emitted_end_to_end(
    ecosystem, project_id: str, four_pack, arch_out,
) -> None:
    """full pipeline 应 emit 至少 5 类 L1-03 事件。"""
    env = ecosystem
    draft = decompose_wbs(
        four_set_plan=four_pack, architecture_output=arch_out,
        project_id=project_id, skill_client=env["skill"], event_bus=env["event_bus"],
    )
    env["manager"].load_topology(draft.wp_list, draft.dag_edges)
    q = GetNextWPQuery(query_id="q1", project_id=project_id, requester_tick="t1")
    env["dispatcher"].get_next_wp(q)
    env["tracker"].on_wp_done(WPCompletionEvent(
        wp_id="wp-a", project_id=project_id, event_id="d1",
    ))

    bus: EventBusStub = env["event_bus"]
    emitted = {e.type for e in bus.events}
    # 至少包含以下 L1-03 类
    required = {
        "L1-03:wbs_topology_ready",        # L2-01 拆解
        "L1-03:wbs_decomposed",             # L2-02 装图
        "L1-03:wp_state_changed",           # L2-02 跃迁
        "L1-03:wp_ready_dispatched",        # L2-03 派发
        "L1-03:progress_metrics_updated",   # L2-04 进度
    }
    missing = required - emitted
    assert not missing, f"缺少事件：{missing}"
