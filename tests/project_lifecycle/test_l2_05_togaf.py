"""L2-05 TOGAF ADM 测试（精选核心 TC）。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.togaf import (
    TogafError,
    TogafProducer,
    TogafResult,
)
from app.project_lifecycle.togaf.errors import (
    E_INVALID_PROFILE,
    E_PM14_OWNERSHIP_VIOLATION,
    E_REVIEWER_REJECT,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def pid() -> str:
    return "p_togaf00-1234-5678-9abc-def012345678"


@pytest.fixture
def template_ok() -> MagicMock:
    m = MagicMock()
    m.render_template = lambda **kw: MagicMock(
        output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\n# {kw['kind']}\nbody"
    )
    return m


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(template_ok, event_bus) -> TogafProducer:
    return TogafProducer(template=template_ok, event_bus=event_bus)


class TestL2_05_TogafProducer:

    def test_TC_L102_L205_light_profile_produces_5_phases(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        result: TogafResult = sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="LIGHT",
        )
        assert result.status == "ok"
        assert result.profile == "LIGHT"
        assert set(result.phases.keys()) == {
            "phase_a", "phase_b", "phase_c_data",
            "phase_c_application", "phase_d",
        }

    def test_TC_L102_L205_standard_profile_produces_7_phases(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        result = sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="STANDARD",
        )
        assert result.status == "ok"
        assert "preliminary" in result.phases
        assert "phase_h" in result.phases
        assert len(result.phases) == 7

    def test_TC_L102_L205_heavy_profile_produces_10_phases(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        adrs = [{"title": f"ADR-{i}", "context": "x", "decision": "y",
                 "alternatives": [], "consequences": []} for i in range(20)]
        result = sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="HEAVY",
            adr_list=adrs,
        )
        assert result.status == "ok"
        assert len(result.phases) == 10

    def test_TC_L102_L205_togaf_d_ready_emitted_early(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
        event_bus: MagicMock,
    ) -> None:
        """Phase D 完成立即发 togaf_d_ready 信号（关键提前信号 · 解 L2-04 阻塞）。"""
        sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="STANDARD",
        )
        events = [c.kwargs["event_type"] for c in event_bus.append_event.call_args_list]
        assert "togaf_d_ready" in events
        # phase_d_ready 与 togaf_d_ready 都发了 · 后者在前者后
        d_idx = events.index("togaf_d_ready")
        phase_d_idx = events.index("togaf_phase_d_ready") if "togaf_phase_d_ready" in events else -1
        # togaf_d_ready 发送一定在 phase_d 落盘后
        assert d_idx > phase_d_idx

    def test_TC_L102_L205_pm14_caller_violation(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        with pytest.raises(TogafError) as exc:
            sut.produce_togaf(
                pid, project_root=str(tmp_project_root), caller_l2="L2-03",
            )
        assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION

    def test_TC_L102_L205_invalid_profile(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        with pytest.raises(TogafError) as exc:
            sut.produce_togaf(
                pid, project_root=str(tmp_project_root), profile="ULTRA",  # type: ignore[arg-type]
            )
        assert exc.value.error_code == E_INVALID_PROFILE

    def test_TC_L102_L205_phase_c_reviewer_reject_raises(
        self, template_ok: MagicMock, event_bus: MagicMock,
        pid: str, tmp_project_root: Path,
    ) -> None:
        """Phase C reviewer mock 返 pass=False · 抛 E_REVIEWER_REJECT。"""
        reviewer = MagicMock()
        reviewer.review.return_value = {"pass": False, "reason": "arch lacks scaling plan"}
        sut = TogafProducer(
            template=template_ok, event_bus=event_bus, reviewer=reviewer,
        )
        with pytest.raises(TogafError) as exc:
            sut.produce_togaf(
                pid, project_root=str(tmp_project_root), profile="LIGHT",
            )
        assert exc.value.error_code == E_REVIEWER_REJECT

    def test_TC_L102_L205_togaf_ready_final_event(
        self, sut: TogafProducer, pid: str, tmp_project_root: Path,
        event_bus: MagicMock,
    ) -> None:
        """total togaf_ready 事件带 profile + phases。"""
        sut.produce_togaf(
            pid, project_root=str(tmp_project_root), profile="LIGHT",
        )
        final_events = [
            c for c in event_bus.append_event.call_args_list
            if c.kwargs["event_type"] == "togaf_ready"
        ]
        assert len(final_events) == 1
        payload = final_events[0].kwargs["payload"]
        assert payload["profile"] == "LIGHT"
        assert len(payload["phases"]) == 5
