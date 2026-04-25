"""Row L1-05 Skill → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-05 → L1-01 · IC-04 (response) 调用结果回返 (success / fail / timeout)
    L1-05 → L1-09 · IC-09 invoke_audit (审计落盘)
    L1-05 → L1-06 · IC-08 子 Agent 委托使用 KB (KB 读 / Rerank)
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_04_invoked,
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-05 → L1-01 · IC-04 (response) 调用结果回返 (6 TC)
# =============================================================================


class TestRowL1_05_to_L1_01:
    """L1-05 Skill → L1-01 主决策 · IC-04 response (success / fail / timeout)."""

    async def test_happy_skill_response_success(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · skill 调用成功 · 返预置 output 给 L1-01."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["plan_review"] = {
            "status": "ok", "approved": True, "score": 0.92,
        }
        result = await fake_skill_invoker.invoke(
            skill_id="plan_review", args={"project_id": project_id},
        )
        assert result["approved"] is True
        assert result["score"] == 0.92
        # IC-04 调用记录
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="plan_review",
            project_id=project_id,
        )
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.HAPPY)

    async def test_happy_skill_returns_complex_payload(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · skill 返复杂结构 (list + dict)."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["wbs_decompose"] = {
            "wps": [{"id": "wp-1"}, {"id": "wp-2"}],
            "edges": [{"from": "wp-1", "to": "wp-2"}],
        }
        result = await fake_skill_invoker.invoke(
            skill_id="wbs_decompose", args={"project_id": project_id},
        )
        assert len(result["wps"]) == 2
        assert result["edges"][0]["from"] == "wp-1"
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.HAPPY)

    async def test_negative_skill_runtime_failure(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """NEGATIVE · skill 运行时错误 · 异常透传给 L1-01."""
        from .conftest import record_cell

        fake_skill_invoker.error_queue = [RuntimeError("skill crash")]
        with pytest.raises(RuntimeError) as exc_info:
            await fake_skill_invoker.invoke(
                skill_id="failing_skill", args={"project_id": project_id},
            )
        assert "skill crash" in str(exc_info.value)
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.NEGATIVE)

    async def test_negative_pm14_skill_pid_isolation(
        self,
        project_id: str,
        other_project_id: str,
        fake_skill_invoker,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自调 skill · args 内 pid 区分."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["shared_skill"] = {"status": "ok"}
        await fake_skill_invoker.invoke(
            skill_id="shared_skill", args={"project_id": project_id},
        )
        await fake_skill_invoker.invoke(
            skill_id="shared_skill", args={"project_id": other_project_id},
        )
        # 各自 pid 独立
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="shared_skill",
            project_id=project_id,
        )
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="shared_skill",
            project_id=other_project_id,
        )
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.PM14)

    async def test_slo_response_under_100ms(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """SLO · skill stub 调用响应 < 100ms."""
        from .conftest import record_cell

        t0 = time.monotonic()
        await fake_skill_invoker.invoke(
            skill_id="quick", args={"project_id": project_id},
        )
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-04 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.HAPPY)

    async def test_e2e_5_skills_chain(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """E2E · 5 skill 串行调用 · 全部正确返."""
        from .conftest import record_cell

        skills = ["plan", "tdd", "wbs", "verify", "review"]
        for sid in skills:
            fake_skill_invoker.outputs[sid] = {"step": sid}
        for sid in skills:
            await fake_skill_invoker.invoke(
                skill_id=sid, args={"project_id": project_id},
            )
        assert len(fake_skill_invoker.call_log) == 5
        assert [c["skill_id"] for c in fake_skill_invoker.call_log] == skills
        record_cell(matrix_cov, "L1-05", "L1-01", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-05 → L1-09 · IC-09 invoke_audit (6 TC)
# =============================================================================


class TestRowL1_05_to_L1_09:
    """L1-05 Skill → L1-09 EventBus · invoke_audit 落盘."""

    def _invoke_event(
        self,
        project_id: str,
        skill_id: str = "plan_review",
        invocation_id: str = "inv-1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-05:skill_invocation_started",
            actor="executor",
            payload={
                "invocation_id": invocation_id,
                "capability": skill_id,
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_invoke_started_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · invoke 起始 audit · capability 完整记录."""
        from .conftest import record_cell

        evt = self._invoke_event(project_id, skill_id="plan_review")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-05:skill_invocation_started",
            payload_contains={"capability": "plan_review"},
        )
        assert events[0]["payload"]["invocation_id"] == "inv-1"
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.HAPPY)

    def test_happy_invoke_completed_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · invoke 完成 audit · success status 记录."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-05:skill_invocation_completed",
            actor="executor",
            payload={"invocation_id": "inv-2", "status": "ok",
                     "duration_ms": 250},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-05:skill_invocation_completed",
            min_count=1,
        )
        assert events[0]["payload"]["status"] == "ok"
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.HAPPY)

    def test_negative_invoke_failed_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · invoke 失败 · audit 记 error_code."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-05:skill_invocation_completed",
            actor="executor",
            payload={"invocation_id": "inv-fail", "status": "error",
                     "error_code": "E_SKILL_TIMEOUT"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-05:skill_invocation_completed",
            payload_contains={"status": "error"},
        )
        assert events[0]["payload"]["error_code"] == "E_SKILL_TIMEOUT"
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_invoke_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 invoke audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._invoke_event(project_id, invocation_id="inv-A"))
        real_event_bus.append(self._invoke_event(
            other_project_id, invocation_id="inv-B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-05:skill_invocation_started",
            payload_contains={"invocation_id": "inv-A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-05:skill_invocation_started",
            payload_contains={"invocation_id": "inv-B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.PM14)

    def test_slo_invoke_audit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · invoke audit emit < 50ms."""
        from .conftest import record_cell

        evt = self._invoke_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-09 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.HAPPY)

    def test_e2e_5_skill_invocations_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 skill 调用 · 各 start+complete · 共 10 audit."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(self._invoke_event(
                project_id, invocation_id=f"inv-e2e-{i}", skill_id=f"skill-{i}",
            ))
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-05:skill_invocation_completed",
                actor="executor",
                payload={"invocation_id": f"inv-e2e-{i}", "status": "ok"},
                timestamp=datetime.now(UTC),
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10
        record_cell(matrix_cov, "L1-05", "L1-09", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-05 → L1-06 · IC-08 子 Agent 委托使用 KB (KB 读 / Rerank) (6 TC)
# =============================================================================


class TestRowL1_05_to_L1_06:
    """L1-05 Skill 子 Agent → L1-06 KB · IC-08 KB read / Rerank."""

    def test_happy_kb_read_session_scope(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """HAPPY · 子 Agent 读 session scope KB · 返预置 entries."""
        from .conftest import record_cell

        fake_kb_repo.session_entries = [
            type("Entry", (), {"id": "e-1", "kind": "pattern",
                                "content": "x", "observed_count": 5})(),
        ]
        entries = fake_kb_repo.read_session(None, ["pattern"])
        assert len(entries) == 1
        assert entries[0].id == "e-1"
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.HAPPY)

    def test_happy_kb_read_project_scope(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """HAPPY · 读 project scope · 返多 entry."""
        from .conftest import record_cell

        fake_kb_repo.project_entries = [
            type("E", (), {"id": f"e-{i}", "kind": "gotcha",
                           "observed_count": i + 1})() for i in range(3)
        ]
        entries = fake_kb_repo.read_project(None, ["gotcha"])
        assert len(entries) == 3
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.HAPPY)

    def test_negative_empty_kb_returns_empty(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """NEGATIVE · KB 空 · 返空 list (不 raise)."""
        from .conftest import record_cell

        entries = fake_kb_repo.read_session(None, ["pattern"])
        assert entries == []
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.NEGATIVE)

    def test_negative_pm14_kb_scope_isolation(
        self, project_id: str, other_project_id: str, fake_scope_checker, matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · scope_check 用 pid 隔离."""
        from .conftest import record_cell

        # 两个不同 pid req · 各自 isolation_ctx
        req_a = type("Req", (), {"project_id": project_id})()
        req_b = type("Req", (), {"project_id": other_project_id})()
        result_a = fake_scope_checker.scope_check(req_a)
        result_b = fake_scope_checker.scope_check(req_b)
        assert result_a.isolation_ctx["project_id"] == project_id
        assert result_b.isolation_ctx["project_id"] == other_project_id
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.PM14)

    def test_slo_kb_read_under_50ms(
        self, project_id: str, fake_kb_repo, matrix_cov,
    ) -> None:
        """SLO · KB 读 < 50ms (in-memory stub)."""
        from .conftest import record_cell

        fake_kb_repo.session_entries = [type("E", (), {"id": f"e-{i}",
                                                        "observed_count": 1})()
                                          for i in range(10)]
        t0 = time.monotonic()
        entries = fake_kb_repo.read_session(None, ["pattern"])
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-08 SLO {elapsed_ms:.2f}ms"
        assert len(entries) == 10
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.HAPPY)

    def test_e2e_3_layer_read_with_rerank(
        self, project_id: str, fake_kb_repo, fake_reranker, matrix_cov,
    ) -> None:
        """E2E · session+project+global 3 层读 + rerank · 返 top_k."""
        from .conftest import record_cell

        # 3 层各填 entries (按 observed_count 排序, rerank 应取 top by observed_count)
        for level, attr_name in (
            (3, "session_entries"), (5, "project_entries"), (7, "global_entries"),
        ):
            entries = [
                type("E", (), {
                    "id": f"e-{attr_name}-{i}", "kind": "pattern",
                    "observed_count": level - i, "content": f"c-{i}",
                })()
                for i in range(level)
            ]
            setattr(fake_kb_repo, attr_name, entries)
        # 收集所有 candidates
        all_entries = (
            fake_kb_repo.read_session(None, [])
            + fake_kb_repo.read_project(None, [])
            + fake_kb_repo.read_global([])
        )
        assert len(all_entries) == 15
        # rerank top-5
        req = type("R", (), {"candidates": all_entries, "top_k": 5})()
        resp = fake_reranker.rerank(req)
        assert len(resp.ranked) == 5
        # 由 observed_count DESC 排序
        ocs = [e.observed_count for e in resp.ranked]
        assert ocs == sorted(ocs, reverse=True)
        record_cell(matrix_cov, "L1-05", "L1-06", CaseType.DEGRADE)
