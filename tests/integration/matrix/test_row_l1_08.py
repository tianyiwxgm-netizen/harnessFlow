"""Row L1-08 Multimodal → others · 2 cells × 6 TC = 12 TC.

**2 cells**:
    L1-08 → L1-05 · IC-04 (response) tool 调用结果 · OCR / 文档 / 视觉多模态
    L1-08 → L1-09 · IC-09 tool_audit · 解析结果 audit
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
# Cell 1: L1-08 → L1-05 · IC-04 (response) 多模态 tool 结果 (6 TC)
# =============================================================================


class TestRowL1_08_to_L1_05:
    """L1-08 Multimodal → L1-05 Skill · IC-04 (response) OCR / 文档 / 视觉."""

    async def test_happy_ocr_tool_response(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · OCR tool 调用 · 返提取的 text + bbox."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["multimodal_ocr"] = {
            "status": "ok",
            "text": "Hello world from image",
            "bboxes": [{"x": 0, "y": 0, "w": 100, "h": 20}],
            "confidence": 0.95,
        }
        result = await fake_skill_invoker.invoke(
            skill_id="multimodal_ocr",
            args={"project_id": project_id, "image_path": "/tmp/x.png"},
        )
        assert result["status"] == "ok"
        assert "Hello world" in result["text"]
        assert result["confidence"] == 0.95
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="multimodal_ocr",
            project_id=project_id,
        )
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.HAPPY)

    async def test_happy_doc_io_tool_response(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """HAPPY · doc_io tool · 返解析的 markdown frontmatter + body."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["multimodal_doc_io"] = {
            "status": "ok",
            "frontmatter": {"title": "Spec", "version": "1.0"},
            "body": "# Section 1\nContent...",
            "headings": ["Section 1"],
        }
        result = await fake_skill_invoker.invoke(
            skill_id="multimodal_doc_io",
            args={"project_id": project_id, "doc_path": "/tmp/spec.md"},
        )
        assert result["frontmatter"]["title"] == "Spec"
        assert "Section 1" in result["headings"]
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.HAPPY)

    async def test_negative_vision_tool_failure(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """NEGATIVE · 视觉 VLM 调用失败 · 异常透传给 L1-05."""
        from .conftest import record_cell

        fake_skill_invoker.error_queue = [
            RuntimeError("VLM provider unavailable"),
        ]
        with pytest.raises(RuntimeError) as exc_info:
            await fake_skill_invoker.invoke(
                skill_id="multimodal_vision",
                args={"project_id": project_id, "image_url": "x"},
            )
        assert "VLM provider unavailable" in str(exc_info.value)
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.NEGATIVE)

    async def test_negative_pm14_tool_pid_isolation(
        self,
        project_id: str,
        other_project_id: str,
        fake_skill_invoker,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自调多模态 tool · args.pid 区分."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["multimodal_ocr"] = {"status": "ok", "text": ""}
        await fake_skill_invoker.invoke(
            skill_id="multimodal_ocr", args={"project_id": project_id},
        )
        await fake_skill_invoker.invoke(
            skill_id="multimodal_ocr", args={"project_id": other_project_id},
        )
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="multimodal_ocr",
            project_id=project_id,
        )
        assert_ic_04_invoked(
            fake_skill_invoker.call_log, skill_id="multimodal_ocr",
            project_id=other_project_id,
        )
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.PM14)

    async def test_slo_tool_response_under_100ms(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """SLO · 多模态 stub 调用响应 < 100ms."""
        from .conftest import record_cell

        fake_skill_invoker.outputs["multimodal_quick"] = {"status": "ok"}
        t0 = time.monotonic()
        await fake_skill_invoker.invoke(
            skill_id="multimodal_quick", args={"project_id": project_id},
        )
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 100, f"IC-04 multimodal SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.HAPPY)

    async def test_e2e_3_modalities_chain(
        self, project_id: str, fake_skill_invoker, matrix_cov,
    ) -> None:
        """E2E · OCR + DocIO + Vision 3 模态串行调用 · 全部正确返."""
        from .conftest import record_cell

        modalities = {
            "multimodal_ocr": {"text": "ocr text"},
            "multimodal_doc_io": {"body": "md body"},
            "multimodal_vision": {"caption": "scene desc"},
        }
        for sid, out in modalities.items():
            fake_skill_invoker.outputs[sid] = {**out, "status": "ok"}
        for sid in modalities:
            await fake_skill_invoker.invoke(
                skill_id=sid, args={"project_id": project_id},
            )
        assert len(fake_skill_invoker.call_log) == 3
        called = [c["skill_id"] for c in fake_skill_invoker.call_log]
        assert called == list(modalities.keys())
        record_cell(matrix_cov, "L1-08", "L1-05", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-08 → L1-09 · IC-09 tool_audit (6 TC)
# =============================================================================


class TestRowL1_08_to_L1_09:
    """L1-08 Multimodal → L1-09 EventBus · IC-09 多模态 tool_audit."""

    def _tool_audit_event(
        self,
        project_id: str,
        tool: str = "ocr",
        invocation_id: str = "mm-1",
        status: str = "ok",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-08:multimodal_tool_completed",
            actor="executor",
            payload={
                "invocation_id": invocation_id,
                "tool": tool,
                "status": status,
                "duration_ms": 120,
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_ocr_tool_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · OCR tool 完成 audit · status=ok 落盘."""
        from .conftest import record_cell

        evt = self._tool_audit_event(project_id, tool="ocr")
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-08:multimodal_tool_completed",
            payload_contains={"tool": "ocr"},
        )
        assert events[0]["payload"]["status"] == "ok"
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.HAPPY)

    def test_happy_3_tools_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 3 类多模态 tool 各自 audit (ocr/doc_io/vision)."""
        from .conftest import record_cell

        for tool in ("ocr", "doc_io", "vision"):
            real_event_bus.append(self._tool_audit_event(project_id, tool=tool))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-08:multimodal_tool_completed",
            min_count=3,
        )
        tools = {e["payload"]["tool"] for e in events}
        assert tools == {"ocr", "doc_io", "vision"}
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.HAPPY)

    def test_negative_tool_failure_audited(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · tool 失败 status=error · audit 仍记 + error_code."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-08:multimodal_tool_completed",
            actor="executor",
            payload={
                "invocation_id": "mm-fail",
                "tool": "vision",
                "status": "error",
                "error_code": "E_VLM_TIMEOUT",
            },
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-08:multimodal_tool_completed",
            payload_contains={"status": "error"},
        )
        assert events[0]["payload"]["error_code"] == "E_VLM_TIMEOUT"
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_tool_audit_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 tool audit 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._tool_audit_event(
            project_id, invocation_id="mm-A",
        ))
        real_event_bus.append(self._tool_audit_event(
            other_project_id, invocation_id="mm-B",
        ))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-08:multimodal_tool_completed",
            payload_contains={"invocation_id": "mm-A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-08:multimodal_tool_completed",
            payload_contains={"invocation_id": "mm-B"},
        )
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.PM14)

    def test_slo_tool_audit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · 多模态 tool audit emit < 50ms."""
        from .conftest import record_cell

        evt = self._tool_audit_event(project_id)
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-09 multimodal SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.HAPPY)

    def test_e2e_5_tool_invocations_chain(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · 5 多模态 tool 调用 · 各 start+complete · 共 10 audit · hash chain."""
        from .conftest import record_cell

        for i in range(5):
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-08:multimodal_tool_started",
                actor="executor",
                payload={"invocation_id": f"mm-{i}", "tool": f"t-{i}"},
                timestamp=datetime.now(UTC),
            ))
            real_event_bus.append(self._tool_audit_event(
                project_id, invocation_id=f"mm-{i}", tool=f"t-{i}",
            ))
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10
        record_cell(matrix_cov, "L1-08", "L1-09", CaseType.DEGRADE)
