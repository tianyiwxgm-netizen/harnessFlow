"""IC-08 · kb_promote 集成测试 · 5 TC.

覆盖 (对齐 ic-contracts.md §3.8 + WP04 任务表):
    TC-1 写入 (single promotion · session→project · auto_threshold OK)
    TC-2 晋升 idempotency (同 source_entry_id+to_scope · 再调返同 promotion_id)
    TC-3 拒绝 (skip-level · session→global 不允许)
    TC-4 读后写 (阈值不达 · KEPT verdict + reason_code)
    TC-5 SLO P95 ≤ 200ms (§3.8 SLO)
"""
from __future__ import annotations

import time

from app.knowledge_base.promoter.schemas import GLOBAL_THRESHOLD, PROJECT_THRESHOLD


class TestIC08Integration:
    """IC-08 集成 · PromotionExecutor 主入口."""

    # ---- TC-1 · 写入: session → project · auto_threshold ----
    def test_session_to_project_auto_threshold_promoted(
        self,
        executor,
        mock_observer,
        make_source_entry,
        make_request,
        make_target,
        project_id: str,
    ) -> None:
        # 预置 source entry · observed_count=2 (满阈值)
        src = make_source_entry(entry_id="kbe-tc1", observed_count=PROJECT_THRESHOLD)
        mock_observer._entries_by_project[project_id] = [src]

        target = make_target(
            entry_id="kbe-tc1",
            from_scope="session",
            to_scope="project",
            reason="auto_threshold",
        )
        resp = executor.kb_promote(make_request(target=target))

        assert resp.success is True
        assert resp.project_id == project_id
        assert resp.single_result is not None
        assert resp.single_result.promoted is True
        assert resp.single_result.verdict == "promoted"
        assert resp.single_result.final_scope == "project"
        assert resp.single_result.promotion_id is not None
        assert resp.single_result.reason_code == "auto_threshold"

    # ---- TC-2 · idempotency: 同 (source,to_scope) 重放返同 promotion_id ----
    def test_idempotent_replay_returns_same_promotion_id(
        self,
        executor,
        mock_observer,
        make_source_entry,
        make_request,
        make_target,
        project_id: str,
    ) -> None:
        src = make_source_entry(entry_id="kbe-tc2", observed_count=PROJECT_THRESHOLD)
        mock_observer._entries_by_project[project_id] = [src]

        target = make_target(entry_id="kbe-tc2")
        # 第 1 次 · 真实晋升
        r1 = executor.kb_promote(make_request(target=target, request_id="req-1"))
        # 第 2 次 · 幂等返
        r2 = executor.kb_promote(make_request(target=target, request_id="req-2"))

        assert r1.single_result.promoted is True
        assert r2.single_result.promoted is True
        # 同 (project_id, source_entry_id, to_scope) → 同 promotion_id
        assert r1.single_result.promotion_id == r2.single_result.promotion_id
        # 第 2 次 reason_code 标记为幂等重放
        assert r2.single_result.reason_code == "idempotent_replay"

    # ---- TC-3 · 拒绝: skip-level (session → global) ----
    def test_skip_layer_session_to_global_rejected(
        self,
        executor,
        mock_observer,
        make_source_entry,
        make_request,
        make_target,
        project_id: str,
    ) -> None:
        src = make_source_entry(entry_id="kbe-tc3", observed_count=GLOBAL_THRESHOLD)
        mock_observer._entries_by_project[project_id] = [src]

        target = make_target(
            entry_id="kbe-tc3",
            from_scope="session",
            to_scope="global",  # 跨层 → 拒
            reason="auto_threshold",
        )
        resp = executor.kb_promote(make_request(target=target))

        # IC-08 §3.8 跨层拒绝 · verdict=rejected · reason_code 含 SKIP_LAYER
        assert resp.single_result.promoted is False
        assert resp.single_result.verdict == "rejected"
        # reason_code/text 含 SKIP_LAYER_DENIED 错误码
        assert "SKIP" in str(resp.single_result.reason_code).upper()

    # ---- TC-4 · 读后写: 阈值不达 → KEPT (不是 rejected) ----
    def test_threshold_unmet_returns_kept_verdict(
        self,
        executor,
        mock_observer,
        make_source_entry,
        make_request,
        make_target,
        project_id: str,
    ) -> None:
        # observed=1 · 不满 PROJECT_THRESHOLD=2 + 不是 user_approved
        src = make_source_entry(entry_id="kbe-tc4", observed_count=1)
        mock_observer._entries_by_project[project_id] = [src]

        target = make_target(
            entry_id="kbe-tc4",
            from_scope="session",
            to_scope="project",
            reason="auto_threshold",
        )
        resp = executor.kb_promote(make_request(target=target))

        # KEPT verdict · 仍 success=True 但 promoted=False
        assert resp.single_result.promoted is False
        assert resp.single_result.verdict == "kept"
        assert "THRESHOLD" in str(resp.single_result.reason_code).upper()

    # ---- TC-5 · SLO P95 ≤ 200ms (§3.8) ----
    def test_slo_p95_within_200ms(
        self,
        executor,
        mock_observer,
        make_source_entry,
        make_request,
        make_target,
        project_id: str,
    ) -> None:
        srcs = [
            make_source_entry(entry_id=f"kbe-slo-{i}", observed_count=PROJECT_THRESHOLD)
            for i in range(10)
        ]
        mock_observer._entries_by_project[project_id] = list(srcs)

        latencies: list[float] = []
        for i in range(10):
            target = make_target(entry_id=f"kbe-slo-{i}")
            t0 = time.perf_counter()
            resp = executor.kb_promote(make_request(
                target=target, request_id=f"req-slo-{i}",
            ))
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert resp.success is True

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        # IC-08 SLO §3.8 · P95 ≤ 200ms
        assert p95 < 200.0, f"IC-08 P95 SLO 超时 {p95:.1f}ms"
