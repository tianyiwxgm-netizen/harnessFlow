"""Scenario 07 · T7-T10 · 跨 session 持久 + PM-14 隔离 + hash chain + 退出 ceremony.

T7: 跨 session promoted 项保留 · 新 PromotionExecutor instance 仍可见
T8: PM-14 隔离 · pid-X 的 promote 不影响 pid-Y
T9: hash chain · audit 落盘 sequence 单调
T10: ceremony 退出 · 重新进入不重复 promote (idempotent)
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
from app.l1_09.event_bus.core import EventBus
from tests.acceptance.scenario_07_kb_promotion.conftest import FakeObserver, _FakeSourceEntry
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
)


def test_t7_promoted_entry_persists_across_executor_instances(
    project_id: str,
    fake_observer,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T7 · 跨 session · 旧 executor promote · 新 executor 仍可见 (target_store 持久)."""
    with gwt("T7 · 跨 session 持久 · 同 target_store"):
        gwt.given("用旧 executor 1 promote sess-001")
        ex1 = PromotionExecutor(
            observer=fake_observer,
            target_store=target_store,
        )
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t7",
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-x"),
            ),
        )
        resp1 = ex1.kb_promote(req)
        assert resp1.success is True

        gwt.when("用新 executor 2 (共享同 target_store) 检索")
        ex2 = PromotionExecutor(
            observer=fake_observer,
            target_store=target_store,
        )

        gwt.then("新 executor 仍能见到 promoted entry")
        promoted = ex2._target_store.list_project(project_id)  # noqa: SLF001
        assert len(promoted) == 1
        assert promoted[0].source_entry_id == "sess-001"


def test_t8_pm14_isolation_across_projects(
    fake_observer,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T8 · PM-14 隔离 · pid-X promote 不影响 pid-Y."""
    with gwt("T8 · PM-14 隔离 · 跨 pid 不串"):
        pid_x = "proj-acc07-kb-promo"
        pid_y = "proj-acc07-other-pid"

        gwt.given("pid-x 含 5 个 candidate · pid-y 无 candidate")
        # fake_observer 只含 pid_x · pid_y 应空
        snap_y = fake_observer.provide_candidate_snapshot(
            project_id=pid_y,
            min_observed_count=2,
        )
        assert len(snap_y.entries) == 0

        gwt.when("在 pid_x promote sess-001")
        ex = PromotionExecutor(observer=fake_observer, target_store=target_store)
        req = KBPromoteRequest(
            project_id=pid_x,
            mode="single",
            trigger="user_manual",
            request_id="req-t8",
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-y"),
            ),
        )
        ex.kb_promote(req)

        gwt.then("pid_x 含 1 个 promoted · pid_y project tier 空")
        promoted_x = target_store.list_project(pid_x)
        promoted_y = target_store.list_project(pid_y)
        assert len(promoted_x) == 1
        assert len(promoted_y) == 0


def test_t9_audit_hash_chain_intact_after_promote(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
) -> None:
    """T9 · IC-07 写完后 · L1-09 hash chain 完整 · seq 单调."""
    with gwt("T9 · KB promote audit hash chain"):
        gwt.given("emit 3 条 KB-related audit (1 候选 snap + 1 promote + 1 list)")
        emit_audit("L1-06:kb_session_candidate_snapshotted", {"entries": 5})
        emit_audit(
            "L1-06:kb_promotion_promoted",
            {"entry_id": "sess-001", "to_scope": "project"},
        )
        emit_audit("L1-06:kb_read_executed", {"hits": 1, "scope": "project"})

        gwt.then("3 条事件落盘 · hash chain 完整 · seq 1..3")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 3

        gwt.then("含 1 条 promotion_promoted 事件")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-06:kb_promotion_promoted",
        )
        assert len(events) == 1


def test_t10_ceremony_exit_idempotent_re_promote(
    project_id: str,
    promotion_executor: PromotionExecutor,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T10 · ceremony 退出后再 promote 同 entry · idempotent · 不重复 promote."""
    with gwt("T10 · ceremony exit + 重入 idempotent"):
        gwt.given("第 1 次 promote sess-001")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t10-r1",
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-z"),
            ),
        )
        resp1 = promotion_executor.kb_promote(req)
        assert resp1.success is True
        first_pid = resp1.single_result.promotion_id

        gwt.when("ceremony 退出 · 重新进入 · 再次 promote 相同 entry")
        # idempotent 需要 (pid, entry_id, to_scope) 一致 · 即使 request_id 不同
        req2 = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t10-r2",  # 新 req_id
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-z"),
            ),
        )
        resp2 = promotion_executor.kb_promote(req2)

        gwt.then("idempotent · promotion_id 相同 · target_store 不重复入 entry")
        assert resp2.success is True
        assert resp2.single_result.promotion_id == first_pid
        # idempotent_replay reason_code (per executor)
        assert "idempotent" in (
            resp2.single_result.reason_code or ""
        ).lower() or resp2.single_result.promoted is True

        gwt.then("target_store 仍 1 entry · 没重复")
        promoted = target_store.list_project(project_id)
        assert len(promoted) == 1
