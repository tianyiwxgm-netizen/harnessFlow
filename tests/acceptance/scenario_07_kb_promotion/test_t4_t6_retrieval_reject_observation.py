"""Scenario 07 · T4-T6 · IC-08 检索命中 + reject 不进 + 历史保留.

T4: IC-08 检索命中 · target_store 中可查到 promoted entry
T5: reject 项不进 KB · 后续 promote 同 entry 被拒 (REJECTED_CANNOT_UNDO)
T6: 历史观察保留 · session 候选不被 promote 也不删除
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
from tests.shared.gwt_helpers import GWT


def test_t4_ic08_retrieval_hits_promoted_entry(
    project_id: str,
    promotion_executor: PromotionExecutor,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T4 · promoted 后 IC-08 检索 (list_project) 命中."""
    with gwt("T4 · IC-08 检索命中"):
        gwt.given("先 promote sess-003 到 project")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t4",
            target=PromoteTarget(
                entry_id="sess-003",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-charlie"),
            ),
        )
        resp = promotion_executor.kb_promote(req)
        assert resp.success is True

        gwt.when("IC-08 检索 project tier")
        promoted = target_store.list_project(project_id)

        gwt.then("命中 sess-003 · scope=project · kind=pattern")
        assert len(promoted) == 1
        entry = promoted[0]
        assert entry.source_entry_id == "sess-003"
        assert entry.scope == "project"
        assert entry.kind == "pattern"


def test_t5_rejected_entry_cannot_re_promote(
    project_id: str,
    promotion_executor: PromotionExecutor,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T5 · reject 项不进 · 后续同 entry promote 被 REJECTED_CANNOT_UNDO."""
    with gwt("T5 · reject 项不可逆"):
        gwt.given("user 主动 reject sess-004 (target_store mark_rejected)")
        target_store.mark_rejected(project_id, "sess-004")

        gwt.when("尝试 promote sess-004 (应被拒)")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t5",
            target=PromoteTarget(
                entry_id="sess-004",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-d"),
            ),
        )
        resp = promotion_executor.kb_promote(req)

        gwt.then("verdict=rejected · error=REJECTED_CANNOT_UNDO")
        assert resp.success is False or (
            resp.single_result and resp.single_result.verdict == "rejected"
        )
        # 检查 reason_code 含 REJECTED_CANNOT_UNDO
        if resp.single_result:
            assert resp.single_result.verdict == "rejected"
            assert "REJECTED" in (
                resp.single_result.reason_code
                or resp.error_code
                or ""
            )

        gwt.then("target_store project tier 不含 sess-004")
        promoted = target_store.list_project(project_id)
        assert all(e.source_entry_id != "sess-004" for e in promoted)


def test_t6_unselected_observations_preserved(
    project_id: str,
    fake_observer,
    promotion_executor: PromotionExecutor,
    target_store: InMemoryTargetStore,
    gwt: GWT,
) -> None:
    """T6 · 仅 promote sess-001 · 其他 4 个仍在 observer (历史保留)."""
    with gwt("T6 · 历史观察保留 · 未 promote 项不删除"):
        gwt.given("5 candidate · 仅 promote sess-001")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t6",
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-e"),
            ),
        )
        promotion_executor.kb_promote(req)

        gwt.then("project tier 含 1 个 promoted entry")
        promoted = target_store.list_project(project_id)
        assert len(promoted) == 1

        gwt.then("observer snapshot 仍含 5 candidate (session 不删)")
        snap = fake_observer.provide_candidate_snapshot(
            project_id=project_id,
            min_observed_count=2,
        )
        assert len(snap.entries) == 5
