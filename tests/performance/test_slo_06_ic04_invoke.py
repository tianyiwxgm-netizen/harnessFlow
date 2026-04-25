"""SLO-06 · ic_04_invoke_p99 ≤ 200ms · skill 调用 (含 fallback).

阈值: 200ms (IC-04 §SLO · Dev-γ 已实测 P99 ≈ 0.78ms)
来源: SkillExecutor.invoke 6 阶段流水 (intent → context → audit → run → retry → finish)

度量定义:
- SkillExecutor.invoke(request) sync wall ms
- runner 是 stub callable · 测纯 executor 编排开销
- 真实模式下 runner 接 Claude SDK · 大头是网络

6 TC:
- T1 baseline · 1000 次 P99 ≤ 200ms
- T2 cold start · 首 50 次 P99 ≤ 200ms
- T3 持续 5 个滑窗
- T4 fallback path · primary 永远 raise · fallback 接管 · P99 ≤ 200ms
- T5 并发 10 executor x 50 invocations · P99 ≤ 200ms
- T6 退化告警 · 250ms 样本必触发
"""
from __future__ import annotations

import asyncio
import pathlib
import shutil
import time
import uuid

import pytest

from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
from app.skill_dispatch._mocks.ic09_mock import IC09EventBusMock
from app.skill_dispatch._mocks.lock_mock import AccountLockMock
from app.skill_dispatch.intent_selector import IntentSelector
from app.skill_dispatch.invoker.executor import SkillExecutor
from app.skill_dispatch.invoker.schemas import InvocationRequest
from app.skill_dispatch.registry.ledger import LedgerWriter
from app.skill_dispatch.registry.loader import RegistryLoader
from app.skill_dispatch.registry.query_api import RegistryQueryAPI
from tests.shared.perf_helpers import LatencySample, assert_p99_under

SLO_BUDGET_MS = 200.0

# Path to skill_dispatch fixtures (relative to repo root)
_FIXTURES_DIR = pathlib.Path(__file__).parents[1] / "skill_dispatch" / "fixtures"


def _build_executor(tmp_path: pathlib.Path, runner) -> tuple[SkillExecutor, str]:
    """构造完整 SkillExecutor + 隔离 project_root · 返 (executor, pid)."""
    pid = f"proj_perf_{uuid.uuid4().hex[:8]}"
    root = tmp_path / "projects" / pid
    cache = root / "skills" / "registry-cache"
    cache.mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir(parents=True, exist_ok=True)
    shutil.copy(_FIXTURES_DIR / "registry_valid.yaml", cache / "registry.yaml")
    snap = RegistryLoader(project_root=root).load()
    api = RegistryQueryAPI(snapshot=snap)
    bus = IC09EventBusMock()
    kb = IC06KBMock()
    lock = AccountLockMock()
    selector = IntentSelector(registry=api, event_bus=bus, kb=kb)
    ledger = LedgerWriter(project_root=root, lock=lock)
    return SkillExecutor(
        selector=selector, event_bus=bus, ledger=ledger, skill_runner=runner,
    ), pid


def _ok_runner(skill, params, ctx):
    return {"ok": True}


def _fallback_runner(skill, params, ctx):
    """primary 永远 raise · fallback 接管."""
    if skill.skill_id == "superpowers:tdd-workflow":
        raise ValueError("primary always fails")
    return {"ok": True}


@pytest.mark.perf
class TestSLO06IC04Invoke:
    """SLO-06: ic_04_invoke_p99 ≤ 200ms · 6 TC."""

    def test_t1_baseline_p99_under_200ms(self, tmp_path: pathlib.Path) -> None:
        """T1 · 1000 次 invoke · P99 ≤ 200ms · 含 50 次 warmup."""
        exe, pid = _build_executor(tmp_path, _ok_runner)
        # warmup
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-w-{i}",
                project_id=pid,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            exe.invoke(req)
        samples: list[LatencySample] = []
        for i in range(1000):
            req = InvocationRequest(
                invocation_id=f"inv-base-{i}",
                project_id=pid,
                capability="write_test",
                params={"i": i},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            t0 = time.perf_counter()
            rsp = exe.invoke(req)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            assert rsp.success is True
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic04_baseline")
        assert stats.p50 < 10.0, f"ic04 invoke P50 {stats.p50:.3f}ms 异常"

    def test_t2_cold_start_p99_under_200ms(self, tmp_path: pathlib.Path) -> None:
        """T2 · 冷启动首 50 次 · 含 registry 加载 (build_executor 已含)."""
        exe, pid = _build_executor(tmp_path, _ok_runner)
        samples: list[LatencySample] = []
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-cold-{i}",
                project_id=pid,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            t0 = time.perf_counter()
            exe.invoke(req)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic04_cold")

    def test_t3_sustained_5_windows(self, tmp_path: pathlib.Path) -> None:
        """T3 · 持续 5000 次 · 5 个滑窗 P99 全 ≤ 200ms."""
        exe, pid = _build_executor(tmp_path, _ok_runner)
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-w-{i}",
                project_id=pid,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            exe.invoke(req)
        ms_list: list[float] = []
        for i in range(5000):
            req = InvocationRequest(
                invocation_id=f"inv-sus-{i}",
                project_id=pid,
                capability="write_test",
                params={"i": i},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            t0 = time.perf_counter()
            exe.invoke(req)
            ms_list.append((time.perf_counter() - t0) * 1000.0)
        for window_idx in range(5):
            window = ms_list[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"ic04_window_{window_idx}",
            )

    def test_t4_fallback_path_p99_under_200ms(self, tmp_path: pathlib.Path) -> None:
        """T4 · 降级路径 · primary fail → fallback · P99 ≤ 200ms.

        含 primary 失败 + fallback 链路开销 · 仍要在预算内.
        """
        exe, pid = _build_executor(tmp_path, _fallback_runner)
        for i in range(20):  # warmup
            req = InvocationRequest(
                invocation_id=f"inv-w-fb-{i}",
                project_id=pid,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            exe.invoke(req)
        samples: list[LatencySample] = []
        for i in range(500):
            req = InvocationRequest(
                invocation_id=f"inv-fb-{i}",
                project_id=pid,
                capability="write_test",
                params={"i": i},
                caller_l1="L1-04",
                context={"project_id": pid},
            )
            t0 = time.perf_counter()
            rsp = exe.invoke(req)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            assert rsp.success is True
            assert rsp.fallback_used is True
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic04_fallback")

    def test_t5_concurrent_10_executors(self, tmp_path: pathlib.Path) -> None:
        """T5 · 并发负载 · 10 executor x 50 invocations · P99 ≤ 200ms.

        每 executor 独立 project_root · 防 ledger 互相干扰.
        用 asyncio.to_thread 并发 sync invoke.
        """

        async def one_run(idx: int) -> list[float]:
            exe, pid = _build_executor(tmp_path / f"c{idx}", _ok_runner)
            for i in range(10):
                exe.invoke(InvocationRequest(
                    invocation_id=f"inv-w-c{idx}-{i}",
                    project_id=pid,
                    capability="write_test",
                    params={},
                    caller_l1="L1-04",
                    context={"project_id": pid},
                ))
            ms: list[float] = []
            for i in range(50):
                req = InvocationRequest(
                    invocation_id=f"inv-c{idx}-{i}",
                    project_id=pid,
                    capability="write_test",
                    params={"i": i},
                    caller_l1="L1-04",
                    context={"project_id": pid},
                )
                t0 = time.perf_counter()
                exe.invoke(req)
                ms.append((time.perf_counter() - t0) * 1000.0)
            return ms

        async def run_all() -> list[list[float]]:
            return await asyncio.gather(
                *[asyncio.to_thread(lambda i=i: asyncio.run(one_run(i))) for i in range(10)]
            )

        results = asyncio.run(run_all())
        all_ms = [v for sub in results for v in sub]
        samples = [LatencySample(elapsed_ms=v) for v in all_ms]
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic04_concurrent")

    def test_t6_degradation_detection(self) -> None:
        """T6 · 退化告警 · 250ms 样本必触发."""
        samples = [LatencySample(elapsed_ms=250.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic04_degraded")
        boundary = [LatencySample(elapsed_ms=199.0) for _ in range(100)]
        stats = assert_p99_under(
            boundary, budget_ms=SLO_BUDGET_MS, metric_name="ic04_boundary",
        )
        assert stats.p99 == 199.0
