"""Smoke: stubs 各 mock 基础设施形态与错误注入."""
from __future__ import annotations

import pytest


# --------- StateTransitionSpy ---------


@pytest.mark.asyncio
async def test_state_spy_records(state_spy) -> None:
    result = await state_spy.state_transition(
        project_id="proj-x", wp_id="wp-1", new_wp_state="retry_s3",
        escalated=False, route_id="r-1", target_stage="S3",
    )
    assert result["transitioned"] is True
    assert len(state_spy.calls) == 1
    assert state_spy.calls[0]["target_stage"] == "S3"


# --------- DelegateVerifierStub ---------


@pytest.mark.asyncio
async def test_delegate_stub_returns_sub_prefix(delegate_stub) -> None:
    from app.quality_loop.verifier.schemas import IC20Command

    cmd = IC20Command(
        delegation_id="ver-del-001",
        project_id="proj-x",
        wp_id="wp-1",
        blueprint_slice={"dod_expression": "tests_pass", "red_tests": ["t1"]},
        s4_snapshot={"commit_sha": "abc123def"},
        acceptance_criteria={"coverage_gate": 0.8},
        timeout_s=600,
        allowed_tools=["bash"],
        ts="2026-04-24T10:00:00Z",
    )
    res = await delegate_stub.delegate_verifier(cmd)
    assert res.dispatched is True
    assert res.verifier_session_id.startswith("sub-")
    assert len(delegate_stub.calls) == 1


@pytest.mark.asyncio
async def test_delegate_stub_error_queue(delegate_stub) -> None:
    from app.quality_loop.verifier.schemas import IC20Command

    delegate_stub.error_queue = [TimeoutError("t1"), None]
    cmd = IC20Command(
        delegation_id="ver-del-001", project_id="proj-x", wp_id="wp-1",
        blueprint_slice={"dod_expression": "t", "red_tests": ["t1"]},
        s4_snapshot={"commit_sha": "abc123"},
        acceptance_criteria={"coverage_gate": 0.8},
        timeout_s=60, allowed_tools=["bash"], ts="2026-04-24T10:00:00Z",
    )
    with pytest.raises(TimeoutError):
        await delegate_stub.delegate_verifier(cmd)
    # 第 2 次成功
    res = await delegate_stub.delegate_verifier(cmd)
    assert res.dispatched is True


# --------- CallbackWaiterStub ---------


@pytest.mark.asyncio
async def test_callback_waiter_returns_preset(callback_waiter) -> None:
    callback_waiter.output = {"verdict": "PASS", "verifier_report_id": "vr-1"}
    res = await callback_waiter.wait(delegation_id="d-1", verifier_session_id="s-1", timeout_s=60)
    assert res["verdict"] == "PASS"
    assert len(callback_waiter.calls) == 1


@pytest.mark.asyncio
async def test_callback_waiter_raises_exc(callback_waiter) -> None:
    callback_waiter.exc = TimeoutError("callback timeout")
    with pytest.raises(TimeoutError):
        await callback_waiter.wait(delegation_id="d-1", verifier_session_id="s-1", timeout_s=1)


# --------- FakeKBRepo / ScopeChecker / Reranker ---------


def test_fake_kb_repo_returns_preset(fake_kb_repo) -> None:
    fake_kb_repo.session_entries = ["e1", "e2"]
    fake_kb_repo.project_entries = ["p1"]
    assert fake_kb_repo.read_session(None, None) == ["e1", "e2"]
    assert fake_kb_repo.read_project(None, None) == ["p1"]
    assert fake_kb_repo.read_global(None) == []


# --------- FakeLLMClient ---------


@pytest.mark.asyncio
async def test_fake_llm_matches_prompt_key(fake_llm) -> None:
    fake_llm.responses = {"generate_script": "draft_v1", "default": "fallback"}
    assert await fake_llm.complete("please generate_script for x") == "draft_v1"
    assert await fake_llm.complete("unrelated prompt") == "fallback"
    assert len(fake_llm.call_log) == 2


# --------- FakeSkillInvoker ---------


@pytest.mark.asyncio
async def test_fake_skill_invoker_maps_outputs(fake_skill_invoker) -> None:
    fake_skill_invoker.outputs = {"wbs-decomposer": {"wps": ["wp-1"]}}
    res = await fake_skill_invoker.invoke(skill_id="wbs-decomposer", args={})
    assert res == {"wps": ["wp-1"]}


@pytest.mark.asyncio
async def test_fake_skill_invoker_error_queue(fake_skill_invoker) -> None:
    fake_skill_invoker.error_queue = [RuntimeError("first fail")]
    with pytest.raises(RuntimeError, match="first fail"):
        await fake_skill_invoker.invoke(skill_id="s1", args={})


# --------- FakeToolClient ---------


@pytest.mark.asyncio
async def test_fake_tool_client_returns_default(fake_tool_client) -> None:
    res = await fake_tool_client.call("bash", {"cmd": "ls"})
    assert res == {"ok": True}


# --------- AuditSink ---------


def test_audit_sink_records(audit_sink) -> None:
    audit_sink.append(event_type="L1-06:kb_read_done", payload={"pid": "x"})
    assert len(audit_sink.events) == 1
    assert audit_sink.events[0]["type"] == "L1-06:kb_read_done"
