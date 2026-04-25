"""Scenario 07 · T1-T3 · 候选入队 + user 操作 + IC-07 写.

T1: ≥5 candidate snapshot 入队 · observer.provide_candidate_snapshot 命中
T2: user 选 promote · session → project · 成功
T3: IC-07 写入审计 · audit 含 promotion_id
"""
from __future__ import annotations

from app.knowledge_base.promoter.promotion_executor import PromotionExecutor
from app.knowledge_base.promoter.schemas import (
    Approver,
    KBPromoteRequest,
    PromoteTarget,
)
from tests.shared.gwt_helpers import GWT


def test_t1_five_candidates_in_observer_snapshot(
    project_id: str,
    fake_observer,
    gwt: GWT,
) -> None:
    """T1 · 5 candidate 在 observer snapshot 中 (KB 候选队列 ≥ 5)."""
    with gwt("T1 · 候选入队 · ≥5 observation"):
        gwt.given(f"observer 含 5 candidate · pid={project_id}")
        snap = fake_observer.provide_candidate_snapshot(
            project_id=project_id,
            min_observed_count=2,
        )

        gwt.then("snapshot.entries 长度 = 5 · 全过 min_observed_count=2 阈值")
        # 我们造的 candidate observed_count=2..4 (2,3,4,2,3) · 全 ≥ 2
        assert len(snap.entries) == 5
        assert snap.error_code is None

        gwt.then("候选 entry_id 都是 sess-001..sess-005")
        ids = {e.entry_id for e in snap.entries}
        assert ids == {f"sess-{i:03d}" for i in range(1, 6)}


def test_t2_user_promote_session_to_project(
    project_id: str,
    promotion_executor: PromotionExecutor,
    gwt: GWT,
) -> None:
    """T2 · user 选 promote · session → project · 成功."""
    with gwt("T2 · user promote sess-001 session → project"):
        gwt.given("user 在 UI 点 promote · sess-001 from session to project")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t2-promote",
            target=PromoteTarget(
                entry_id="sess-001",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-alice"),
            ),
        )

        gwt.when("PromotionExecutor.kb_promote · 处理 single promote")
        resp = promotion_executor.kb_promote(req)

        gwt.then("promote 成功 · final_scope=project · verdict=promoted")
        assert resp.success is True
        assert resp.single_result is not None
        assert resp.single_result.promoted is True
        assert resp.single_result.final_scope == "project"
        assert resp.single_result.verdict == "promoted"


def test_t3_promotion_writes_audit_with_promotion_id(
    project_id: str,
    promotion_executor: PromotionExecutor,
    target_store,
    gwt: GWT,
) -> None:
    """T3 · IC-07 写 · target_store 含 promotion_id · audit 闭环."""
    with gwt("T3 · IC-07 写 · audit 含 promotion_id"):
        gwt.given("user 提 promote sess-002")
        req = KBPromoteRequest(
            project_id=project_id,
            mode="single",
            trigger="user_manual",
            request_id="req-t3-promote",
            target=PromoteTarget(
                entry_id="sess-002",
                from_scope="session",
                to_scope="project",
                reason="user_approved",
                approver=Approver(user_id="user-bob"),
            ),
        )

        gwt.when("kb_promote 执行")
        resp = promotion_executor.kb_promote(req)

        gwt.then("promotion_id 已写入 · target_store 内有 sess-002 source")
        assert resp.single_result.promotion_id is not None
        assert resp.single_result.promotion_id.startswith("prm-") or len(
            resp.single_result.promotion_id
        ) > 0

        gwt.then("target_store 含 promoted entry · source_entry_id=sess-002")
        promoted = target_store.list_project(project_id)
        assert len(promoted) == 1
        assert promoted[0].source_entry_id == "sess-002"
        assert promoted[0].scope == "project"
