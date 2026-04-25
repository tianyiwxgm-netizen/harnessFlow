"""Scenario 09 · T4-T6 · 锁不串 · KB 不串 · 资源 fair share.

T4: 锁不串 · pidA 持锁不影响 pidB
T5: KB 不串 · pidA promote 不影响 pidB tier
T6: 资源 fair share · 3 pid 各自 parallelism_limit 独立
"""
from __future__ import annotations

from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import (
    Approver,
    KBPromoteRequest,
    PromoteTarget,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from tests.acceptance.scenario_07_kb_promotion.conftest import (
    FakeObserver,
    _FakeSourceEntry,
)
from tests.shared.gwt_helpers import GWT


def test_t4_locks_isolated_per_pid(
    pid_a, pid_b, topo_factory, make_wp_for, gwt: GWT
) -> None:
    """T4 · pidA 持锁 (RUNNING 占 parallelism) 不影响 pidB."""
    with gwt("T4 · 锁/parallelism 不串 pid"):
        gwt.given("pid_a parallelism=1 · 已 RUNNING 1 WP · 满锁")
        ma = topo_factory(pid_a, parallelism=1)
        ma.load_topology([make_wp_for(pid_a, "wp-a-1")], [])
        ma.transition_state("wp-a-1", State.READY, State.RUNNING)

        gwt.when("pid_b 也 parallelism=1 · 起 1 WP")
        mb = topo_factory(pid_b, parallelism=1)
        mb.load_topology([make_wp_for(pid_b, "wp-b-1")], [])
        # pidB 不受 pidA 锁影响 · 可起 RUNNING
        mb.transition_state("wp-b-1", State.READY, State.RUNNING)

        gwt.then("两 pid 各自 1 WP RUNNING · 不互相阻塞")
        snap_a = ma.read_snapshot()
        snap_b = mb.read_snapshot()
        assert snap_a.wp_states["wp-a-1"] == State.RUNNING
        assert snap_b.wp_states["wp-b-1"] == State.RUNNING


def test_t5_kb_isolated_per_pid(pid_a, pid_b, gwt: GWT) -> None:
    """T5 · pidA promote 不影响 pidB · KB project tier 严格隔离."""
    with gwt("T5 · KB 不串 pid"):
        gwt.given("pid_a 含 candidate · pid_b 也含 candidate · 共享 target_store")
        store = InMemoryTargetStore()
        obs_a = FakeObserver([
            _FakeSourceEntry("sess-a-1", pid_a, observed_count=2),
        ])
        obs_b = FakeObserver([
            _FakeSourceEntry("sess-b-1", pid_b, observed_count=2),
        ])

        gwt.when("pid_a promote sess-a-1")
        ex_a = PromotionExecutor(observer=obs_a, target_store=store)
        ex_a.kb_promote(KBPromoteRequest(
            project_id=pid_a,
            mode="single",
            trigger="user_manual",
            request_id="req-a",
            target=PromoteTarget(
                entry_id="sess-a-1",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="u-a"),
            ),
        ))

        gwt.then("pid_a project tier 含 1 entry · pid_b 仍空")
        promoted_a = store.list_project(pid_a)
        promoted_b = store.list_project(pid_b)
        assert len(promoted_a) == 1
        assert len(promoted_b) == 0


def test_t6_resource_fair_share(
    pid_a, pid_b, pid_c, topo_factory, make_wp_for, gwt: GWT
) -> None:
    """T6 · 3 pid 各自 parallelism_limit 独立 · fair share."""
    with gwt("T6 · 3 pid 资源 fair share"):
        gwt.given("3 pid 各 parallelism=2 · 各 2 WP")
        managers = []
        for pid in [pid_a, pid_b, pid_c]:
            m = topo_factory(pid, parallelism=2)
            m.load_topology(
                [make_wp_for(pid, f"wp-{pid[-1]}-1"),
                 make_wp_for(pid, f"wp-{pid[-1]}-2")],
                [],
            )
            managers.append(m)

        gwt.when("3 pid 各自 RUNNING 2 WP (各 fully 用 parallelism)")
        for i, m in enumerate(managers):
            pid_short = [pid_a, pid_b, pid_c][i][-1]
            m.transition_state(f"wp-{pid_short}-1", State.READY, State.RUNNING)
            m.transition_state(f"wp-{pid_short}-2", State.READY, State.RUNNING)

        gwt.then("3 pid 各 2 个 RUNNING · fair share · 共 6 WP RUNNING")
        for i, m in enumerate(managers):
            snap = m.read_snapshot()
            running = [w for w, s in snap.wp_states.items() if s == State.RUNNING]
            assert len(running) == 2, f"pid {i} 应 2 RUNNING · 实际 {running}"
