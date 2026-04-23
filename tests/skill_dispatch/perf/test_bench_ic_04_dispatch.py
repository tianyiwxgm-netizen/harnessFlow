"""Perf bench: IC-04 invoke_skill dispatch 延迟 P99 ≤ 200ms (10 候选 · 100 次迭代)."""
from __future__ import annotations

import shutil
import time

import pytest


@pytest.mark.perf
def test_ic_04_dispatch_latency_p99(tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock):
    from app.skill_dispatch.intent_selector import IntentSelector
    from app.skill_dispatch.invoker.executor import SkillExecutor
    from app.skill_dispatch.invoker.schemas import InvocationRequest
    from app.skill_dispatch.registry.ledger import LedgerWriter
    from app.skill_dispatch.registry.loader import RegistryLoader
    from app.skill_dispatch.registry.query_api import RegistryQueryAPI

    cache = tmp_project / "skills" / "registry-cache"
    shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
    snap = RegistryLoader(project_root=tmp_project).load()
    api = RegistryQueryAPI(snapshot=snap)
    selector = IntentSelector(registry=api, event_bus=ic09_bus, kb=kb_mock)
    ledger = LedgerWriter(project_root=tmp_project, lock=lock_mock)

    def runner(skill, params, ctx):
        return {"ok": True}

    executor = SkillExecutor(
        selector=selector, event_bus=ic09_bus, ledger=ledger, skill_runner=runner,
    )
    durations: list[float] = []
    for i in range(100):
        req = InvocationRequest(
            invocation_id=f"inv{i}", project_id="p1", capability="write_test",
            params={"i": i}, caller_l1="L1-04", context={"project_id": "p1"},
        )
        t0 = time.perf_counter()
        executor.invoke(req)
        durations.append((time.perf_counter() - t0) * 1000)
    durations.sort()
    p50 = durations[49]
    p95 = durations[94]
    p99 = durations[98]
    print(f"\nIC-04 dispatch latency: p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    assert p99 < 200.0, f"IC-04 dispatch P99 breach: {p99:.2f}ms"
