"""L2-04 PMP 9 计划生产器测试。

核心 TC：
  - TC-001/002 produce_all_9 full green
  - TC-015/016 bundle_hash 幂等 + 顺序不变
  - TC-101 PM14 violation
  - TC-102 PLAN_UPSTREAM_MISSING
  - TC-103 CORE_KDA_FAILED (scope 失败)
  - TC-104 NON_CORE_LIMIT_EXCEEDED (5 非核心失败)
  - 并发 · 9 个 render_template 调用
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.pmp import (
    CORE_KDAS,
    PMP_9_KDAS,
    PmpBundleResult,
    PmpError,
    PmpPlansProducer,
)
from app.project_lifecycle.pmp.errors import (
    E_CORE_KDA_FAILED,
    E_NON_CORE_LIMIT_EXCEEDED,
    E_PLAN_UPSTREAM_MISSING,
    E_PM14_OWNERSHIP_VIOLATION,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def pid() -> str:
    return "p_pmp00000-1234-5678-9abc-def012345678"


@pytest.fixture
def template_ok() -> MagicMock:
    m = MagicMock()
    m.render_template = lambda **kw: MagicMock(
        output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\n# {kw['kind']}\nbody {kw['kind']}"
    )
    return m


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(template_ok, event_bus) -> PmpPlansProducer:
    return PmpPlansProducer(template=template_ok, event_bus=event_bus)


class TestL2_04_ProduceAll9:

    @pytest.mark.asyncio
    async def test_TC_L102_L204_001_produce_all_9_full_green(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        result: PmpBundleResult = await sut.produce_all_9(
            pid, project_root=str(tmp_project_root),
        )
        assert result.status == "ok"
        assert len(result.kdas) == 9
        assert all(r.status == "ok" for r in result.kdas.values())
        # 9 文件落盘
        for kda in PMP_9_KDAS:
            p = tmp_project_root / "projects" / pid / "pmp" / f"{kda}.md"
            assert p.exists()
        # bundle_hash 格式
        assert len(result.bundle_hash) == 64
        assert result.togaf_alignment is True

    @pytest.mark.asyncio
    async def test_TC_L102_L204_002_9_plans_ready_event(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
        event_bus: MagicMock,
    ) -> None:
        await sut.produce_all_9(pid, project_root=str(tmp_project_root))
        events = [c.kwargs["event_type"] for c in event_bus.append_event.call_args_list]
        assert "9_plans_ready" in events

    @pytest.mark.asyncio
    async def test_TC_L102_L204_9_render_calls(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
        template_ok: MagicMock,
    ) -> None:
        """IC-L2-02 · render_template 调用 9 次（每 kda 1 次）· caller_l2=L2-04。"""
        template_ok.render_template = MagicMock(side_effect=lambda **kw: MagicMock(
            output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\nbody"
        ))
        sut._template = template_ok
        await sut.produce_all_9(pid, project_root=str(tmp_project_root))
        calls = template_ok.render_template.call_args_list
        assert len(calls) == 9
        kinds = {c.kwargs["kind"] for c in calls}
        expected = {f"pmp.{k}" for k in PMP_9_KDAS}
        assert kinds == expected
        for c in calls:
            assert c.kwargs["caller_l2"] == "L2-04"


class TestL2_04_BundleHash:

    @pytest.mark.asyncio
    async def test_TC_L102_L204_015_bundle_hash_idempotent(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        """同 kda 内容两次跑 · bundle_hash 相等。"""
        r1 = await sut.produce_all_9(pid + "a", project_root=str(tmp_project_root))
        r2 = await sut.produce_all_9(pid + "b", project_root=str(tmp_project_root))
        # pid 不同但 body content 一致（template render 不带 pid）
        # 实际上 render body 含 kind 不含 pid（看 template_ok fixture）· 所以 body_hash 同 · bundle_hash 同
        assert r1.bundle_hash == r2.bundle_hash


class TestL2_04_ErrorCodes:

    @pytest.mark.asyncio
    async def test_TC_L102_L204_101_pm14_ownership_violation(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        with pytest.raises(PmpError) as exc:
            await sut.produce_all_9(
                pid, project_root=str(tmp_project_root), caller_l2="L2-02",
            )
        assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION

    @pytest.mark.asyncio
    async def test_TC_L102_L204_102_plan_upstream_missing(
        self, sut: PmpPlansProducer, pid: str, tmp_project_root: Path,
    ) -> None:
        with pytest.raises(PmpError) as exc:
            await sut.produce_all_9(
                pid, project_root=str(tmp_project_root),
                upstream_four_set_manifest="/nonexistent/manifest.yaml",
            )
        assert exc.value.error_code == E_PLAN_UPSTREAM_MISSING

    @pytest.mark.asyncio
    async def test_TC_L102_L204_103_core_kda_failed(
        self, event_bus, pid: str, tmp_project_root: Path,
    ) -> None:
        """scope（核心 kda）render 失败 · 整批 E_CORE_KDA_FAILED。"""
        bad_template = MagicMock()

        def _render(**kw):
            kind = kw["kind"]
            if kind == "pmp.scope":
                return MagicMock(output="")  # 空 body 触发 failed
            return MagicMock(output=f"---\ntemplate_id: {kind}.v1.0\n---\nbody")

        bad_template.render_template = _render
        sut = PmpPlansProducer(template=bad_template, event_bus=event_bus)
        with pytest.raises(PmpError) as exc:
            await sut.produce_all_9(pid, project_root=str(tmp_project_root))
        assert exc.value.error_code == E_CORE_KDA_FAILED

    @pytest.mark.asyncio
    async def test_TC_L102_L204_104_non_core_limit_exceeded(
        self, event_bus, pid: str, tmp_project_root: Path,
    ) -> None:
        """5 非核心 kda 失败 · E_NON_CORE_LIMIT_EXCEEDED。"""
        bad_template = MagicMock()
        # quality, resource, communication, risk, procurement 失败 = 5 非核心
        fail_kinds = {
            "pmp.quality", "pmp.resource", "pmp.communication",
            "pmp.risk", "pmp.procurement",
        }

        def _render(**kw):
            if kw["kind"] in fail_kinds:
                return MagicMock(output="")
            return MagicMock(output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\nbody")

        bad_template.render_template = _render
        sut = PmpPlansProducer(template=bad_template, event_bus=event_bus)
        with pytest.raises(PmpError) as exc:
            await sut.produce_all_9(pid, project_root=str(tmp_project_root))
        assert exc.value.error_code == E_NON_CORE_LIMIT_EXCEEDED

    @pytest.mark.asyncio
    async def test_TC_L102_L204_partial_3_non_core_failures(
        self, event_bus, pid: str, tmp_project_root: Path,
    ) -> None:
        """3 非核心失败（≤4）· status=partial · degraded_kdas 列出。"""
        bad_template = MagicMock()
        fail_kinds = {"pmp.resource", "pmp.communication", "pmp.risk"}

        def _render(**kw):
            if kw["kind"] in fail_kinds:
                return MagicMock(output="")
            return MagicMock(output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\nbody")

        bad_template.render_template = _render
        sut = PmpPlansProducer(template=bad_template, event_bus=event_bus)
        result = await sut.produce_all_9(pid, project_root=str(tmp_project_root))
        assert result.status == "partial"
        assert set(result.degraded_kdas) == {"resource", "communication", "risk"}
