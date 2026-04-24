"""IC-04 · 5 SLO TC · invoke_skill 性能预算.

Dev-γ 实测 P99 ≈ 0.78ms(纯 executor 不含 skill) · 本测试验真实集成路径的
P99 在合理预算内(≤ 200ms · 对齐 L1-09 L2-01 Registry SLO 表 §1654).

覆盖:
    TC-1 · 连续 50 次 invoke · P99 ≤ 200ms (夜间上界)
    TC-2 · 连续 50 次 invoke · P95 ≤ 100ms (工作区间)
    TC-3 · 均值 invoke · avg ≤ 50ms
    TC-4 · 单次冷启动 invoke · ≤ 500ms (首次含 registry 加载)
    TC-5 · primary fail + fallback 路径 · P99 ≤ 300ms
"""
from __future__ import annotations

import time

from app.skill_dispatch.invoker.schemas import InvocationRequest


class TestIC04Slo:
    """5 SLO TC · P99 / P95 / avg / 冷启动 / fallback 分路径."""

    def test_invoke_p99_under_200ms(self, make_executor, project_id: str) -> None:
        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        latencies_ms: list[float] = []
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-slo1-{i}",
                project_id=project_id,
                capability="write_test",
                params={"i": i},
                caller_l1="L1-04",
                context={"project_id": project_id},
            )
            t0 = time.perf_counter()
            rsp = exe.invoke(req)
            latencies_ms.append((time.perf_counter() - t0) * 1000)
            assert rsp.success is True

        latencies_ms.sort()
        p99 = latencies_ms[int(len(latencies_ms) * 0.99) - 1]
        assert p99 < 200, f"IC-04 P99 超 · 实测 {p99:.2f}ms"

    def test_invoke_p95_under_100ms(self, make_executor, project_id: str) -> None:
        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        latencies_ms: list[float] = []
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-slo2-{i}",
                project_id=project_id,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": project_id},
            )
            t0 = time.perf_counter()
            exe.invoke(req)
            latencies_ms.append((time.perf_counter() - t0) * 1000)

        latencies_ms.sort()
        p95 = latencies_ms[int(len(latencies_ms) * 0.95) - 1]
        assert p95 < 100, f"IC-04 P95 超 · 实测 {p95:.2f}ms"

    def test_invoke_avg_under_50ms(self, make_executor, project_id: str) -> None:
        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        latencies_ms: list[float] = []
        # skip 冷启动首次
        for i in range(30):
            req = InvocationRequest(
                invocation_id=f"inv-slo3-{i}",
                project_id=project_id,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": project_id},
            )
            t0 = time.perf_counter()
            exe.invoke(req)
            latencies_ms.append((time.perf_counter() - t0) * 1000)

        avg = sum(latencies_ms) / len(latencies_ms)
        assert avg < 50, f"IC-04 avg 超 · 实测 {avg:.2f}ms"

    def test_invoke_cold_start_under_500ms(
        self, make_executor, project_id: str,
    ) -> None:
        """冷启动含 registry yaml 加载 · 首次 ≤ 500ms."""

        def runner(skill, params, ctx):
            return {"ok": True}

        t_setup_0 = time.perf_counter()
        exe = make_executor(runner)
        t_setup_ms = (time.perf_counter() - t_setup_0) * 1000

        req = InvocationRequest(
            invocation_id="inv-slo4",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        t0 = time.perf_counter()
        rsp = exe.invoke(req)
        cold_ms = (time.perf_counter() - t0) * 1000
        assert rsp.success is True
        assert cold_ms + t_setup_ms < 500, (
            f"IC-04 冷启动超 · setup {t_setup_ms:.1f}ms + invoke {cold_ms:.1f}ms"
        )

    def test_invoke_fallback_path_p99_under_300ms(
        self, make_executor, project_id: str,
    ) -> None:
        """primary 失败走 fallback 路径 · P99 ≤ 300ms (含 primary 失败开销)."""

        def runner(skill, params, ctx):
            if skill.skill_id == "superpowers:tdd-workflow":
                raise ValueError("primary always fails")
            return {"ok": True}

        exe = make_executor(runner)
        latencies_ms: list[float] = []
        for i in range(50):
            req = InvocationRequest(
                invocation_id=f"inv-slo5-{i}",
                project_id=project_id,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": project_id},
            )
            t0 = time.perf_counter()
            rsp = exe.invoke(req)
            latencies_ms.append((time.perf_counter() - t0) * 1000)
            assert rsp.success is True
            assert rsp.fallback_used is True

        latencies_ms.sort()
        p99 = latencies_ms[int(len(latencies_ms) * 0.99) - 1]
        assert p99 < 300, f"IC-04 fallback P99 超 · 实测 {p99:.2f}ms"
