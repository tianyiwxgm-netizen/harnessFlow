"""L1-05 组内 5 L2 端到端集成 · invoke → registry → intent → invoker → receiver 全链.

文档参照:
  - docs/superpowers/plans/Dev-γ-impl.md §8 Task 06.1
"""
from __future__ import annotations

import json
import shutil

import pytest


def _wire_full_pipeline(tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
                        skill_runner):
    """装配全链 · 返 (selector, executor, validator, forwarder) 供 e2e 测试."""
    from app.skill_dispatch.async_receiver.forwarder import DoDForwarder
    from app.skill_dispatch.async_receiver.validator import Validator
    from app.skill_dispatch.intent_selector import IntentSelector
    from app.skill_dispatch.invoker.executor import SkillExecutor
    from app.skill_dispatch.registry.ledger import LedgerWriter
    from app.skill_dispatch.registry.loader import RegistryLoader
    from app.skill_dispatch.registry.query_api import RegistryQueryAPI

    cache = tmp_project / "skills" / "registry-cache"
    shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
    snap = RegistryLoader(project_root=tmp_project).load()
    api = RegistryQueryAPI(snapshot=snap)
    selector = IntentSelector(registry=api, event_bus=ic09_bus, kb=kb_mock)
    ledger = LedgerWriter(project_root=tmp_project, lock=lock_mock)
    executor = SkillExecutor(
        selector=selector, event_bus=ic09_bus, ledger=ledger, skill_runner=skill_runner,
    )
    validator = Validator(registry_root=cache)
    forwarder = DoDForwarder(dod_gate=dod_gate, event_bus=ic09_bus, timeout_s=10.0)
    return executor, validator, forwarder, api


def _write_schema(cache_dir, pointer, body):
    path = cache_dir / pointer
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")


@pytest.mark.e2e
class TestL105EndToEnd:
    """e2e 全链 · 覆盖 happy path + all-fail + schema validation."""

    def test_happy_path_full_pipeline(
        self, tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
    ):
        """invoke_skill → registry lookup → intent rank → invoker run →
        receiver validate → dod_gate → result 装配."""
        def runner(skill, params, ctx):
            return {"n": 42}

        cache = tmp_project / "skills" / "registry-cache"
        _write_schema(
            cache, "schemas/skill/write_test.v1.json",
            {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}},
        )
        executor, validator, forwarder, api = _wire_full_pipeline(
            tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate, runner,
        )
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        rsp = executor.invoke(InvocationRequest(
            invocation_id="inv", project_id="p1", capability="write_test",
            params={"n": 42}, caller_l1="L1-04",
            context={"project_id": "p1", "wp_id": "wp1"},
        ))
        assert rsp.success is True

        # Receiver 侧校验 · 用 schema_pointer 读出来的 schema 校验 rsp.result
        schema_pointer = api.query_schema_pointer("write_test")
        validation = validator.validate(
            raw_return=rsp.result,
            schema_pointer=schema_pointer,
            input_params={"n": 42},
        )
        assert validation.status == "passed"

        # DoD gate 最后决定
        verdict = forwarder.forward(
            project_id="p1", capability="write_test",
            result_id=f"{rsp.invocation_id}-{rsp.skill_id}",
            artifact=rsp.result,
            prev_hash="0" * 64,
        )
        assert verdict == "PASS"

    def test_all_candidates_fail_yields_success_false(
        self, tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
    ):
        def runner(skill, params, ctx):
            raise RuntimeError("all dead")

        executor, *_ = _wire_full_pipeline(
            tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate, runner,
        )
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        rsp = executor.invoke(InvocationRequest(
            invocation_id="inv_fail", project_id="p1", capability="write_test",
            params={}, caller_l1="L1-04",
            context={"project_id": "p1"},
        ))
        assert rsp.success is False
        assert rsp.error["code"] == "E_SKILL_ALL_FALLBACK_FAIL"
        assert len(rsp.fallback_trace) == 2

    def test_receiver_rejects_format_invalid_result(
        self, tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
    ):
        """skill 返回的 dict 不符 schema · receiver 标 format_invalid."""
        def runner(skill, params, ctx):
            return {"n": "not-an-int"}

        cache = tmp_project / "skills" / "registry-cache"
        _write_schema(
            cache, "schemas/skill/write_test.v1.json",
            {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}},
        )
        executor, validator, *_, api = _wire_full_pipeline(
            tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate, runner,
        )
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        rsp = executor.invoke(InvocationRequest(
            invocation_id="inv_bad", project_id="p1", capability="write_test",
            params={}, caller_l1="L1-04", context={"project_id": "p1"},
        ))
        assert rsp.success is True   # executor 自身不校验 · 由 receiver 后拉校验

        validation = validator.validate(
            raw_return=rsp.result,
            schema_pointer=api.query_schema_pointer("write_test"),
        )
        assert validation.status == "format_invalid"

    def test_ic09_audit_trail_is_complete(
        self, tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
    ):
        """一次完整调用应留下多条 IC-09 审计事件."""
        def runner(skill, params, ctx):
            return {"n": 1}

        executor, *_ = _wire_full_pipeline(
            tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate, runner,
        )
        from app.skill_dispatch.invoker.schemas import InvocationRequest

        executor.invoke(InvocationRequest(
            invocation_id="inv_audit", project_id="p1", capability="write_test",
            params={}, caller_l1="L1-04", context={"project_id": "p1"},
        ))
        types = [e.event_type for e in ic09_bus.read_all("p1")]
        # 至少这些审计事件:
        assert "capability_chain_produced" in types   # L2-02 rank
        assert "skill_invocation_started" in types    # L2-03 audit_start
        assert "skill_invocation_finished" in types   # L2-03 audit_finish
