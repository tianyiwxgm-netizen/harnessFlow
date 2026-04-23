"""L2-02 IC 契约 + SLO 测试 · 对齐 3-2 TDD md §4-§5 + tech §12。

IC 契约 TC-201~207（IC-L2-01/02, IC-05, IC-09 · 已通过 mock 被覆盖 · 补字段 schema 契约）。
SLO TC-301~304（章程落盘 / anchor_hash 计算 / 4 事件组合 / activate）。
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.kickoff import (
    ActivateRequest,
    StartupProducer,
)
from app.project_lifecycle.kickoff.algo import (
    activate_project_id,
    atomic_write_chart,
    compute_anchor_hash,
    produce_kickoff,
)
from app.project_lifecycle.kickoff.schemas import KickoffRequest, KickoffSuccess


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def brainstorm_std() -> MagicMock:
    m = MagicMock()
    m.invoke.return_value = {
        "rounds": 2, "is_confirmed": True,
        "slots": {"goals": ["g"], "in_scope": ["a"]},
    }
    return m


@pytest.fixture
def template_std() -> MagicMock:
    m = MagicMock()

    def _render(**kwargs):
        # 记录调用
        kind = kwargs["kind"]
        return MagicMock(output=f"---\ntemplate_id: {kind}.v1.0\n---\n# {kind}\nbody")

    m.render_template.side_effect = _render
    return m


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


class TestL2_02_IcContracts:
    """IC 契约 · 字段 schema 验证。"""

    def test_TC_L102_L202_201_ic_l2_01_request_shape(
        self,
    ) -> None:
        """IC-L2-01 KickoffRequest 字段契约（tech §3.2.1）。"""
        req = KickoffRequest(
            trigger_id="t1", stage="S1",
            user_initial_goal="make wiki", caller_l2="L2-01",
        )
        assert req.trigger_id
        assert req.stage == "S1"
        assert req.caller_l2 == "L2-01"
        assert req.trim_level == "full"  # 默认
        assert req.preexisting_charter_path is None

    def test_TC_L102_L202_202_ic_l2_02_render_template_called_twice(
        self, tmp_project_root: Path, brainstorm_std, template_std, event_bus,
    ) -> None:
        """IC-L2-02: produce_kickoff 必调 template.render_template 2 次（goal + scope）· kind 精确。"""
        produce_kickoff(
            "x", brainstorm=brainstorm_std, template=template_std,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        calls = template_std.render_template.call_args_list
        assert len(calls) == 2
        kinds = {c.kwargs["kind"] for c in calls}
        assert kinds == {"kickoff.goal", "kickoff.scope"}
        # caller_l2 契约
        for c in calls:
            assert c.kwargs["caller_l2"] == "L2-02"

    def test_TC_L102_L202_203_ic_05_brainstorm_invoked(
        self, tmp_project_root: Path, brainstorm_std, template_std, event_bus,
    ) -> None:
        """IC-05 brainstorm.invoke 调用契约（user_utterance 传递）。"""
        produce_kickoff(
            "my goal", brainstorm=brainstorm_std, template=template_std,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        brainstorm_std.invoke.assert_called_once()
        call = brainstorm_std.invoke.call_args
        assert call.args[0] == "my goal"

    def test_TC_L102_L202_205_ic_09_4_events_payload_schema(
        self, tmp_project_root: Path, brainstorm_std, template_std, event_bus,
    ) -> None:
        """IC-09 4 事件 payload 必含关键字段（project_id + event_type）。"""
        produce_kickoff(
            "x", brainstorm=brainstorm_std, template=template_std,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        calls = event_bus.append_event.call_args_list
        assert len(calls) == 4
        for c in calls:
            assert c.kwargs["project_id"].startswith("p_")
            assert c.kwargs["event_type"] in (
                "project_created", "charter_ready",
                "stakeholders_ready", "goal_anchor_hash_locked",
            )
            assert isinstance(c.kwargs["payload"], dict)

    def test_TC_L102_L202_207_ic_17_user_intervene_triggers_activate(
        self, tmp_project_root: Path, brainstorm_std, template_std, event_bus,
    ) -> None:
        """IC-17: 用户 approve (user_confirmed=True) 经 L2-01 中转触发 activate。"""
        sut = StartupProducer(
            brainstorm=brainstorm_std, template=template_std,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        resp = sut.kickoff_create_project(KickoffRequest(
            trigger_id="t1", stage="S1",
            user_initial_goal="x", caller_l2="L2-01",
        ))
        assert resp.status in ("ok", "degraded")
        result: KickoffSuccess = resp.result  # type: ignore[assignment]
        # 模拟 L2-01 接收 user_intervene 后调 activate
        act_resp = activate_project_id(
            ActivateRequest(
                project_id=result.project_id,
                goal_anchor_hash=result.goal_anchor_hash,
                user_confirmed=True,
                charter_path=result.charter_path,
                stakeholders_path=result.stakeholders_path,
                caller_l2="L2-01",
            ),
            project_root=str(tmp_project_root),
        )
        assert act_resp.state == "INITIALIZED"


class TestL2_02_SLO:
    """SLO warm-cache 性能基准 · 对齐 tech §12.1。"""

    def test_TC_L102_L202_301_atomic_write_chart_p95_under_200ms(
        self, tmp_project_root: Path,
    ) -> None:
        """单份 md 原子落盘 · warm P95 ≤ 200ms。"""
        samples: list[float] = []
        for i in range(10):
            path = tmp_project_root / f"projects/p_pid_{i}_bench/chart/Doc.md"
            t = time.perf_counter()
            atomic_write_chart(str(path), "# body " * 500)
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1] if len(samples) > 1 else samples[-1]
        assert p95 < 200, f"atomic_write P95 {p95:.1f}ms > 200ms"

    def test_TC_L102_L202_302_anchor_hash_p95_under_30ms(
        self, tmp_project_root: Path,
    ) -> None:
        """anchor_hash 计算 · warm P95 ≤ 30ms。"""
        pid = "p_hash-test-123-456-789-abc-def012345678"
        root = tmp_project_root / "projects" / pid / "chart"
        root.mkdir(parents=True)
        (root / "HarnessFlowGoal.md").write_text("# G\n" + ("body " * 200), encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\n" + ("body " * 200), encoding="utf-8")
        # warm
        compute_anchor_hash(pid, root_dir=str(tmp_project_root))
        samples: list[float] = []
        for _ in range(20):
            t = time.perf_counter()
            compute_anchor_hash(pid, root_dir=str(tmp_project_root))
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1]
        assert p95 < 30, f"anchor_hash P95 {p95:.2f}ms > 30ms"

    def test_TC_L102_L202_303_4_events_combo_p95_under_180ms(
        self, tmp_project_root: Path,
    ) -> None:
        """produce_kickoff 全流程（含 4 事件 + 2 章程 + manifest + hash）· P95 ≤ 180ms（fast path · in-memory mocks）。"""
        brainstorm = MagicMock()
        brainstorm.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        template = MagicMock()
        template.render_template = lambda **kw: MagicMock(
            output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\nbody"
        )
        event_bus = MagicMock()
        # warm
        produce_kickoff(
            "x", brainstorm=brainstorm, template=template,
            event_bus=event_bus, project_root=str(tmp_project_root),
        )
        samples: list[float] = []
        for _ in range(10):
            t = time.perf_counter()
            produce_kickoff(
                "x", brainstorm=brainstorm, template=template,
                event_bus=event_bus, project_root=str(tmp_project_root),
            )
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p95 = samples[-1]  # 小样本
        assert p95 < 180, f"produce_kickoff P95 {p95:.1f}ms > 180ms"

    def test_TC_L102_L202_304_activate_p95_under_60ms(
        self, tmp_project_root: Path,
    ) -> None:
        """activate_project_id · warm P95 ≤ 60ms。"""
        # 先产一个 draft project
        brainstorm = MagicMock()
        brainstorm.invoke.return_value = {"rounds": 1, "is_confirmed": True, "slots": {}}
        template = MagicMock()
        template.render_template = lambda **kw: MagicMock(
            output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\nbody"
        )
        event_bus = MagicMock()
        samples: list[float] = []
        for i in range(5):
            result = produce_kickoff(
                "x", brainstorm=brainstorm, template=template,
                event_bus=event_bus, project_root=str(tmp_project_root),
            )
            req = ActivateRequest(
                project_id=result.project_id,
                goal_anchor_hash=result.goal_anchor_hash,
                user_confirmed=True,
                charter_path=result.charter_path,
                stakeholders_path=result.stakeholders_path,
                caller_l2="L2-01",
            )
            t = time.perf_counter()
            activate_project_id(req, project_root=str(tmp_project_root))
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p95 = samples[-1]
        assert p95 < 60, f"activate P95 {p95:.1f}ms > 60ms"
