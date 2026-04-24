"""L1-06 · WP06 组内集成 · 跨 5 L2 联调 + PM-14 双 project 隔离 E2E.

覆盖:
  · observer(write) → observer(snapshot) → promoter(single/batch) 完整链
  · PM-14: project A 写不污染 project B · 跨 pid 硬隔离
  · dedup merge 后 observed_count ≥ 2 · promoter 能按阈值自动晋升
  · promoter 晋升条目 · target_store 可查
  · IC-09 审计事件在关键节点落盘 (observer / promoter 各自 audit_log)

SUT 组装: observer=ObserveAccumulator · promoter=PromotionExecutor + observer.
tier_manager / reader / retrieval 为独立 L2 · 按需组装。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.observer.accumulator import (
    ObserveAccumulator,
    _InMemorySessionStore,
)
from app.knowledge_base.observer.schemas import (
    ApplicableContext,
    KBEntryRequest,
    WriteSessionRequest,
)
from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import (
    BatchScope,
    KBPromoteRequest,
    PromoteTarget,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_entry(
    observer: ObserveAccumulator,
    project_id: str,
    title: str = "pattern X",
    kind: str = "pattern",
    trace_id: str = "tr",
    source_links: list[str] | None = None,
):
    req = WriteSessionRequest(
        project_id=project_id,
        trace_id=trace_id,
        idempotency_key="",
        entry=KBEntryRequest(
            kind=kind,
            title=title,
            content={"x": 1},
            applicable_context=ApplicableContext(
                stage=["S3"], task_type=["coding"], tech_stack=["python"]
            ),
            source_links=source_links or ["d:1"],
        ),
    )
    return observer.kb_write_session(req)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


class TestCrossL2Wire:
    @pytest.fixture
    def observer_repo(self) -> _InMemorySessionStore:
        return _InMemorySessionStore()

    @pytest.fixture
    def target_store(self) -> InMemoryTargetStore:
        return InMemoryTargetStore()

    @pytest.fixture
    def observer(self, observer_repo) -> ObserveAccumulator:
        return ObserveAccumulator(
            tier_manager=None, event_bus=MagicMock(), repo=observer_repo
        )

    @pytest.fixture
    def promoter(
        self, observer: ObserveAccumulator, target_store
    ) -> PromotionExecutor:
        # Bridge: expose observer.provide_candidate_snapshot as the promoter
        # source of truth (real IC-L2-06 wiring).
        return PromotionExecutor(
            observer=observer,
            event_bus=MagicMock(),
            target_store=target_store,
        )

    # ------------------------------------------------------------------ E2E
    def test_TC_L106_INT_001_write_then_merge_then_promote_single(
        self, observer, promoter, target_store
    ) -> None:
        """Full happy path: 2 writes → merge → promoter auto-threshold → promoted."""
        r1 = _write_entry(observer, "pE2E", trace_id="t1")
        r2 = _write_entry(observer, "pE2E", trace_id="t2")
        assert r1.entry_id == r2.entry_id  # dedup merge
        assert r2.observed_count_after == 2

        promote = promoter.kb_promote(
            KBPromoteRequest(
                project_id="pE2E",
                mode="single",
                trigger="user_manual",
                request_id="p1",
                target=PromoteTarget(
                    entry_id=r2.entry_id,
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        assert promote.single_result.verdict == "promoted"
        assert len(target_store.list_project("pE2E")) == 1

    def test_TC_L106_INT_002_batch_ceremony_promotes_eligible(
        self, observer, promoter, target_store
    ) -> None:
        # Seed 3 pattern titles · each merged twice → eligible
        for title in ["ta", "tb", "tc"]:
            _write_entry(observer, "pB", title=title, trace_id="s1")
            _write_entry(observer, "pB", title=title, trace_id="s2")
        # One low-count entry
        _write_entry(observer, "pB", title="td", trace_id="s-low")
        resp = promoter.kb_promote(
            KBPromoteRequest(
                project_id="pB",
                mode="batch",
                trigger="s7_batch",
                request_id="bat-1",
                batch_scope=BatchScope(),
            )
        )
        br = resp.batch_result
        assert br is not None
        assert len(br.promoted) == 3
        assert "td" not in br.promoted
        assert len(target_store.list_project("pB")) == 3

    # ----------------------------------------------------------- PM-14 iso
    def test_TC_L106_INT_003_pm14_two_projects_isolated_on_write(
        self, observer
    ) -> None:
        rA = _write_entry(observer, "pA", trace_id="tA")
        rB = _write_entry(observer, "pB", trace_id="tB")
        assert rA.entry_id != rB.entry_id
        assert rA.project_id == "pA"
        assert rB.project_id == "pB"

    def test_TC_L106_INT_004_pm14_snapshot_per_project_only(
        self, observer
    ) -> None:
        _write_entry(observer, "pA", trace_id="ta1")
        _write_entry(observer, "pA", trace_id="ta2")
        _write_entry(observer, "pB", trace_id="tb1")
        _write_entry(observer, "pB", trace_id="tb2")
        snapA = observer.provide_candidate_snapshot(project_id="pA")
        snapB = observer.provide_candidate_snapshot(project_id="pB")
        assert snapA.project_id == "pA"
        assert snapB.project_id == "pB"
        assert all(e.entry_id != f.entry_id for e in snapA.entries for f in snapB.entries)

    def test_TC_L106_INT_005_pm14_promoter_isolates_project_buckets(
        self, observer, promoter, target_store
    ) -> None:
        # Two projects each promote an entry
        for pid in ["pIsoA", "pIsoB"]:
            _write_entry(observer, pid, trace_id="x1")
            _write_entry(observer, pid, trace_id="x2")
        for pid in ["pIsoA", "pIsoB"]:
            snap = observer.provide_candidate_snapshot(project_id=pid)
            entry_id = snap.entries[0].entry_id
            promoter.kb_promote(
                KBPromoteRequest(
                    project_id=pid,
                    mode="single",
                    trigger="user_manual",
                    request_id=f"p-{pid}",
                    target=PromoteTarget(
                        entry_id=entry_id,
                        from_scope="session",
                        to_scope="project",
                        reason="auto_threshold",
                    ),
                )
            )
        a_entries = target_store.list_project("pIsoA")
        b_entries = target_store.list_project("pIsoB")
        assert len(a_entries) == 1
        assert len(b_entries) == 1
        assert a_entries[0].source_project_id == "pIsoA"
        assert b_entries[0].source_project_id == "pIsoB"

    # ------------------------------------------------- IC-09 audit presence
    def test_TC_L106_INT_006_observer_audit_emits_on_write(
        self, observer
    ) -> None:
        _write_entry(observer, "paud", trace_id="t1")
        events = [
            rec["event_type"]
            for rec in observer._audit_log
            if rec["event_type"] in {"kb_entry_written", "kb_entry_write_rejected"}
        ]
        assert "kb_entry_written" in events

    def test_TC_L106_INT_007_promoter_audit_emits_on_promote(
        self, observer, promoter
    ) -> None:
        _write_entry(observer, "pauP", trace_id="t1")
        _write_entry(observer, "pauP", trace_id="t2")
        snap = observer.provide_candidate_snapshot(project_id="pauP")
        eid = snap.entries[0].entry_id
        promoter.kb_promote(
            KBPromoteRequest(
                project_id="pauP",
                mode="single",
                trigger="user_manual",
                request_id="p-aud",
                target=PromoteTarget(
                    entry_id=eid,
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        events = [rec["event_type"] for rec in promoter._audit_log]
        assert "kb_entry_promoted" in events

    # --------------------------------------------------------- negative E2E
    def test_TC_L106_INT_008_promote_before_threshold_kept(
        self, observer, promoter, target_store
    ) -> None:
        _write_entry(observer, "pKeep", trace_id="only")
        snap = observer.provide_candidate_snapshot(
            project_id="pKeep", min_observed_count=1
        )
        eid = snap.entries[0].entry_id
        resp = promoter.kb_promote(
            KBPromoteRequest(
                project_id="pKeep",
                mode="single",
                trigger="user_manual",
                request_id="p-keep",
                target=PromoteTarget(
                    entry_id=eid,
                    from_scope="session",
                    to_scope="project",
                    reason="auto_threshold",
                ),
            )
        )
        assert resp.single_result.verdict == "kept"
        assert len(target_store.list_project("pKeep")) == 0

    def test_TC_L106_INT_009_promote_idempotent_across_calls(
        self, observer, promoter
    ) -> None:
        _write_entry(observer, "pIdem", trace_id="t1")
        _write_entry(observer, "pIdem", trace_id="t2")
        snap = observer.provide_candidate_snapshot(project_id="pIdem")
        eid = snap.entries[0].entry_id
        payload = KBPromoteRequest(
            project_id="pIdem",
            mode="single",
            trigger="user_manual",
            request_id="idem-r1",
            target=PromoteTarget(
                entry_id=eid,
                from_scope="session",
                to_scope="project",
                reason="auto_threshold",
            ),
        )
        r1 = promoter.kb_promote(payload)
        payload2 = KBPromoteRequest(**{**payload.__dict__, "request_id": "idem-r2"})
        r2 = promoter.kb_promote(payload2)
        assert r1.single_result.promotion_id == r2.single_result.promotion_id

    def test_TC_L106_INT_010_observer_dedup_idempotency_key(
        self, observer
    ) -> None:
        """Replay with same idempotency_key returns cached response without incrementing."""
        req = WriteSessionRequest(
            project_id="pIdKey",
            trace_id="t1",
            idempotency_key="k-1",
            entry=KBEntryRequest(
                kind="pattern",
                title="dedup title",
                content={"x": 1},
                applicable_context=ApplicableContext(),
                source_links=["d:1"],
            ),
        )
        r1 = observer.kb_write_session(req)
        r2 = observer.kb_write_session(req)
        assert r1.entry_id == r2.entry_id
        assert r1.observed_count_after == r2.observed_count_after == 1
