"""L2-03 · §4 IC-01 producer · emit state_transition 给 L1-02 StageGate (TC-43..47)。"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from app.main_loop.state_machine import (
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    IC01Producer,
    StateMachineError,
)
from app.main_loop.state_machine.ic_01_producer import IC01Envelope


class _FakeStageGate:
    """L1-02 StageGateController 的 mock · 捕获 IC-01 调用参数。"""

    def __init__(self, reply: Dict[str, Any] | None = None) -> None:
        self.last_kwargs: Dict[str, Any] = {}
        self.call_count = 0
        self._reply = reply or {"ok": True, "new_state": "PLANNING"}

    def request_state_transition(self, **kwargs: Any) -> Dict[str, Any]:
        self.last_kwargs = kwargs
        self.call_count += 1
        return self._reply


class TestIC01ProducerEmit:
    def test_tc43_emit_all_9_fields_populated(self):
        """TC-43 · emit() · 9 字段都透传给 StageGate。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        env, reply = producer.emit(
            project_id="pid-00000000-0000-0000-0000-000000000001",
            from_state="PLANNING",
            to_state="TDD_PLANNING",
            reason="planning complete proceed to tdd stage for coverage",
            trigger_tick="tick-00000000-0000-0000-0000-000000000002",
            evidence_refs=("gate-001",),
            gate_id="gate-001",
        )
        assert fake.call_count == 1
        kw = fake.last_kwargs
        # 9 必填字段对齐 ic-contracts §3.1
        assert kw["project_id"] == "pid-00000000-0000-0000-0000-000000000001"
        assert kw["from_state"] == "PLANNING"
        assert kw["to_state"] == "TDD_PLANNING"
        assert kw["reason"].startswith("planning complete")
        assert kw["trigger_tick"] == "tick-00000000-0000-0000-0000-000000000002"
        assert kw["evidence_refs"] == ("gate-001",)
        assert kw["gate_id"] == "gate-001"
        assert kw["transition_id"].startswith("trans-")
        assert kw["ts"].endswith("Z")
        # envelope 回传 caller
        assert isinstance(env, IC01Envelope)
        assert env.transition_id == kw["transition_id"]
        # reply 原样回流
        assert reply == {"ok": True, "new_state": "PLANNING"}

    def test_tc44_emit_default_transition_id_factory(self):
        """TC-44 · 不传 transition_id · Producer 自动生成 trans-{uuid}。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        env, _ = producer.emit(
            project_id="pid-00000000-0000-0000-0000-000000000001",
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            reason="first bootstrap initialization of new project baseline",
            trigger_tick="tick-init",
            evidence_refs=("seed-1",),
        )
        assert env.transition_id.startswith("trans-")
        assert len(env.transition_id) > len("trans-")

    def test_tc45_emit_gate_id_none_maps_to_empty_string(self):
        """TC-45 · gate_id=None · Producer 透传空串 (Dev-δ 签名要求非 None)。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        producer.emit(
            project_id="pid-00000000-0000-0000-0000-000000000001",
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            reason="bootstrap call with no gate context attached for test",
            trigger_tick="tick-1",
            evidence_refs=("ev-1",),
            gate_id=None,
        )
        assert fake.last_kwargs["gate_id"] == ""


class TestIC01ProducerValidation:
    def test_tc46_emit_no_project_id_raises(self):
        """TC-46 · project_id 空 → E_TRANS_NO_PROJECT_ID · 不调 target。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        with pytest.raises(StateMachineError) as exc:
            producer.emit(
                project_id="",
                from_state="NOT_EXIST",
                to_state="INITIALIZED",
                reason="reason is long enough but pid missing!!",
                trigger_tick="tick-x",
                evidence_refs=("ev",),
            )
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID
        assert fake.call_count == 0  # 不应到 target

    def test_tc47_emit_reason_too_short_raises(self):
        """TC-47 · reason 过短 → E_TRANS_REASON_TOO_SHORT · 不调 target。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        with pytest.raises(StateMachineError) as exc:
            producer.emit(
                project_id="pid-00000000-0000-0000-0000-000000000001",
                from_state="NOT_EXIST",
                to_state="INITIALIZED",
                reason="short",
                trigger_tick="tick-y",
                evidence_refs=("ev",),
            )
        assert exc.value.error_code == E_TRANS_REASON_TOO_SHORT
        assert fake.call_count == 0

    def test_tc48_emit_no_evidence_raises(self):
        """TC-48 · evidence_refs=() → E_TRANS_NO_EVIDENCE · 不调 target。"""
        fake = _FakeStageGate()
        producer = IC01Producer(target=fake)
        with pytest.raises(StateMachineError) as exc:
            producer.emit(
                project_id="pid-00000000-0000-0000-0000-000000000001",
                from_state="NOT_EXIST",
                to_state="INITIALIZED",
                reason="long enough reason string aligned with >=20 contract",
                trigger_tick="tick-z",
                evidence_refs=(),
            )
        assert exc.value.error_code == E_TRANS_NO_EVIDENCE
        assert fake.call_count == 0
