"""Perf bench: 子 Agent spawn P99 ≤ 1.2s (100 次迭代 · 不含子 Agent 实际运行)."""
from __future__ import annotations

import time

import pytest


class _NoopAdapter:
    """最快 adapter · spawn 立即返 uuid · await 立即返空 artifacts."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    async def spawn_session(self, *, role, allowed_tools, context, timeout_s):
        import uuid

        sid = f"noop-{uuid.uuid4().hex[:16]}"
        self.sessions[sid] = {"state": "running"}
        return sid

    async def await_result(self, session_id, timeout_s):
        return {"artifacts": [], "final_message": "noop"}

    async def terminate(self, session_id, *, force=False):
        self.sessions.pop(session_id, None)


@pytest.mark.perf
@pytest.mark.asyncio
async def test_subagent_spawn_latency_p99(ic09_bus):
    from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient
    from app.skill_dispatch.subagent.delegator import Delegator
    from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter
    from app.skill_dispatch.subagent.schemas import DelegationRequest

    adapter = _NoopAdapter()
    client = ClaudeSDKClient(adapter=adapter, sigterm_grace_s=0.01)
    limiter = ResourceLimiter(max_concurrent=100, max_queue=500)
    d = Delegator(sdk_client=client, limiter=limiter, event_bus=ic09_bus)

    durations: list[float] = []
    for i in range(100):
        req = DelegationRequest(
            delegation_id=f"d{i}", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        t0 = time.perf_counter()
        await d.delegate_subagent(req)
        durations.append((time.perf_counter() - t0) * 1000)
    durations.sort()
    p50 = durations[49]
    p95 = durations[94]
    p99 = durations[98]
    print(f"\nsubagent spawn latency: p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    assert p99 < 1200.0, f"subagent spawn P99 breach: {p99:.2f}ms"
