"""L2-05 异步结果回收器 · 共 ~38 TC.

文档参照:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md
  - docs/superpowers/plans/Dev-γ-impl.md §7

错误码:
  E_COLLECT_SCHEMA_UNAVAILABLE / FORMAT_INVALID / DOD_GATE_TIMEOUT /
  SILENT_PATCH_DETECTED / RESULT_TIMEOUT / IDEMPOTENCY_KEY_CONFLICT
"""
from __future__ import annotations

import pytest


class TestReceiverSchemas:
    """Task 05.1 · VO + idempotency_key."""

    def test_validation_result_passed(self):
        from app.skill_dispatch.async_receiver.schemas import ValidationResult

        r = ValidationResult(status="passed")
        assert r.status == "passed"
        assert r.errors == []

    def test_validation_result_format_invalid_with_errors(self):
        from app.skill_dispatch.async_receiver.schemas import ValidationResult

        r = ValidationResult(
            status="format_invalid",
            errors=[{"kind": "type", "path": ["x"], "message": "expected int"}],
        )
        assert r.errors[0]["kind"] == "type"

    def test_validation_result_invalid_status(self):
        from app.skill_dispatch.async_receiver.schemas import ValidationResult

        with pytest.raises(ValueError):
            ValidationResult(status="???")   # type: ignore[arg-type]

    def test_pending_entry_requires_positive_deadline(self):
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        with pytest.raises(ValueError):
            PendingEntry(
                result_id="r", deadline_ts_ns=0,
                capability="c", project_id="p1",
            )

    def test_collection_record_status_enum(self):
        from app.skill_dispatch.async_receiver.schemas import CollectionRecord

        rec = CollectionRecord(
            result_id="r1", project_id="p1", capability="c",
            status="passed", assembled_at_ts_ns=1,
        )
        assert rec.status == "passed"

    def test_idempotency_key_stable(self):
        from app.skill_dispatch.async_receiver.schemas import idempotency_key

        k1 = idempotency_key("inv1", "skill_a", 1234567890)
        k2 = idempotency_key("inv1", "skill_a", 1234567890)
        k3 = idempotency_key("inv1", "skill_b", 1234567890)
        assert k1 == k2
        assert k1 != k3
        assert len(k1) == 32


class TestValidator:
    """Task 05.2 · jsonschema Draft 2020-12 · SCHEMA_UNAVAILABLE + silent_patch E09."""

    def _write_schema(self, root, pointer: str, body: dict):
        import json

        path = root / pointer
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    def test_validate_passes_valid_object(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/skill/ok.json",
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["n"],
                "properties": {"n": {"type": "integer"}},
            },
        )
        v = Validator(registry_root=tmp_path)
        result = v.validate(
            raw_return={"n": 1},
            schema_pointer="schemas/skill/ok.json",
        )
        assert result.status == "passed"

    def test_validate_format_invalid_on_type_mismatch(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/skill/ok.json",
            {
                "type": "object",
                "required": ["n"],
                "properties": {"n": {"type": "integer"}},
            },
        )
        v = Validator(registry_root=tmp_path)
        result = v.validate(
            raw_return={"n": "not-an-int"},
            schema_pointer="schemas/skill/ok.json",
        )
        assert result.status == "format_invalid"
        assert len(result.errors) >= 1

    def test_validate_format_invalid_on_missing_required(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/skill/ok.json",
            {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}},
        )
        v = Validator(registry_root=tmp_path)
        result = v.validate(raw_return={}, schema_pointer="schemas/skill/ok.json")
        assert result.status == "format_invalid"

    def test_schema_unavailable_returns_hard_fail(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        v = Validator(registry_root=tmp_path)
        result = v.validate(raw_return={"n": 1}, schema_pointer="schemas/missing.json")
        assert result.status == "schema_unavailable"

    def test_schema_pointer_none_returns_schema_unavailable(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        v = Validator(registry_root=tmp_path)
        result = v.validate(raw_return={"n": 1}, schema_pointer=None)
        assert result.status == "schema_unavailable"

    def test_non_dict_raw_return_rejected(self, tmp_path):
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(tmp_path, "schemas/s.json", {"type": "object"})
        v = Validator(registry_root=tmp_path)
        result = v.validate(raw_return="not a dict", schema_pointer="schemas/s.json")
        assert result.status == "format_invalid"

    def test_silent_patch_detected_when_output_has_unexpected_fields(self, tmp_path):
        """E09 · input 没 extra_field 但 output 有 · 且非 required → silent_patch."""
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/s.json",
            {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}},
        )
        v = Validator(registry_root=tmp_path)
        result = v.validate(
            raw_return={"n": 1, "_phantom_default": "injected"},
            schema_pointer="schemas/s.json",
            input_params={"n": 1},
        )
        assert result.status == "silent_patch"

    def test_no_silent_patch_when_required_fields_added(self, tmp_path):
        """若 output 新增的是 schema 的 required 字段 · 不算 silent_patch（合理补齐）."""
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/s.json",
            {
                "type": "object",
                "required": ["n", "computed"],
                "properties": {
                    "n": {"type": "integer"},
                    "computed": {"type": "string"},
                },
            },
        )
        v = Validator(registry_root=tmp_path)
        result = v.validate(
            raw_return={"n": 1, "computed": "x"},
            schema_pointer="schemas/s.json",
            input_params={"n": 1},
        )
        assert result.status == "passed"

    def test_schema_cached_second_read(self, tmp_path):
        """重复用同 pointer · 第二次不再读文件（lru_cache 验证通过）."""
        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(tmp_path, "schemas/s.json", {"type": "object"})
        v = Validator(registry_root=tmp_path)
        # 两次调用
        v.validate(raw_return={}, schema_pointer="schemas/s.json")
        # 删文件 · 第二次仍然 passed（来自 cache）
        (tmp_path / "schemas" / "s.json").unlink()
        r = v.validate(raw_return={}, schema_pointer="schemas/s.json")
        assert r.status == "passed"

    def test_invalid_schema_raises(self, tmp_path):
        """schema 本身不合法 JSON Schema → SchemaCompilationError."""
        from app.skill_dispatch.async_receiver.validator import (
            SchemaCompilationError,
            Validator,
        )

        self._write_schema(
            tmp_path, "schemas/bad.json",
            {"type": 123},   # type 必须是 string · 不合法
        )
        v = Validator(registry_root=tmp_path)
        with pytest.raises(SchemaCompilationError):
            v.validate(raw_return={}, schema_pointer="schemas/bad.json")

    def test_validate_latency_p99_under_50ms(self, tmp_path):
        """SLO: 校验 P99 ≤ 50ms."""
        import time

        from app.skill_dispatch.async_receiver.validator import Validator

        self._write_schema(
            tmp_path, "schemas/s.json",
            {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}},
        )
        v = Validator(registry_root=tmp_path)
        durations: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            v.validate(raw_return={"n": 1}, schema_pointer="schemas/s.json")
            durations.append((time.perf_counter() - t0) * 1000)
        durations.sort()
        p99 = durations[98]
        assert p99 < 50.0, f"validate p99 breach: {p99:.2f}ms"


class TestForwarder:
    """Task 05.3 · DoD gate 转发 L1-04 · IC-14 prev_hash · 10s 超时."""

    def test_forward_returns_verdict_on_pass(self, ic09_bus, dod_gate):
        from app.skill_dispatch.async_receiver.forwarder import DoDForwarder

        f = DoDForwarder(dod_gate=dod_gate, event_bus=ic09_bus, timeout_s=10.0)
        verdict = f.forward(
            project_id="p1", capability="c", result_id="r1",
            artifact={"ok": True}, prev_hash="a" * 64,
        )
        assert verdict == "PASS"

    def test_forward_emits_ic14_event_with_prev_hash(self, ic09_bus, dod_gate):
        from app.skill_dispatch.async_receiver.forwarder import DoDForwarder

        f = DoDForwarder(dod_gate=dod_gate, event_bus=ic09_bus, timeout_s=10.0)
        f.forward(
            project_id="p1", capability="c", result_id="r1",
            artifact={}, prev_hash="b" * 64,
        )
        events = ic09_bus.read_all("p1")
        forward_events = [e for e in events if e.event_type == "dod_gate_forward"]
        assert len(forward_events) >= 1
        assert forward_events[0].payload["prev_hash"] == "b" * 64

    def test_forward_timeout_raises_DoDGateTimeout(self, ic09_bus):
        import time

        from app.skill_dispatch._mocks.dod_gate_mock import DoDGateMock
        from app.skill_dispatch.async_receiver.forwarder import DoDForwarder, DoDGateTimeout

        class SlowGate(DoDGateMock):
            def dod_gate_check(self, project_id, capability, result_id, artifact):
                time.sleep(0.5)
                return super().dod_gate_check(project_id, capability, result_id, artifact)

        f = DoDForwarder(dod_gate=SlowGate(), event_bus=ic09_bus, timeout_s=0.1)
        with pytest.raises(DoDGateTimeout):
            f.forward(
                project_id="p1", capability="c", result_id="r", artifact={},
                prev_hash="c" * 64,
            )

    def test_forward_override_verdict_passes_through(self, ic09_bus):
        from app.skill_dispatch._mocks.dod_gate_mock import DoDGateMock
        from app.skill_dispatch.async_receiver.forwarder import DoDForwarder

        gate = DoDGateMock(overrides={"cap_fail": "FAIL_L2"})
        f = DoDForwarder(dod_gate=gate, event_bus=ic09_bus, timeout_s=10.0)
        v = f.forward(
            project_id="p1", capability="cap_fail", result_id="r",
            artifact={}, prev_hash="d" * 64,
        )
        assert v == "FAIL_L2"

    def test_forward_ic14_event_has_result_id_in_payload(self, ic09_bus, dod_gate):
        from app.skill_dispatch.async_receiver.forwarder import DoDForwarder

        f = DoDForwarder(dod_gate=dod_gate, event_bus=ic09_bus, timeout_s=10.0)
        f.forward(
            project_id="p1", capability="c", result_id="unique-r-123",
            artifact={}, prev_hash="0" * 64,
        )
        events = ic09_bus.read_all("p1")
        forward_events = [e for e in events if e.event_type == "dod_gate_forward"]
        assert forward_events[0].payload["result_id"] == "unique-r-123"


class TestCrashRecovery:
    """Task 05.4 · pending.jsonl + TimeoutWatcher asyncio."""

    def test_enroll_appends_to_pending_jsonl(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        store = PendingStore(project_root=tmp_project)
        store.enroll(PendingEntry(
            result_id="r1", deadline_ts_ns=1_000_000_000,
            capability="c", project_id="p1",
        ))
        path = tmp_project / "skills" / "registry-cache" / "pending.jsonl"
        assert path.exists()
        assert path.stat().st_size > 0

    def test_enroll_idempotent_same_result_id(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        store = PendingStore(project_root=tmp_project)
        e = PendingEntry(
            result_id="r1", deadline_ts_ns=1_000_000_000, capability="c", project_id="p1",
        )
        store.enroll(e)
        store.enroll(e)   # 幂等
        path = tmp_project / "skills" / "registry-cache" / "pending.jsonl"
        lines = [x for x in path.read_text().splitlines() if x.strip()]
        assert len(lines) == 1   # 只写一次

    def test_finalize_removes_from_active(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        store = PendingStore(project_root=tmp_project)
        store.enroll(PendingEntry(
            result_id="r1", deadline_ts_ns=1_000_000_000, capability="c", project_id="p1",
        ))
        store.finalize("r1", "passed")
        assert "r1" not in store._cache

    def test_timed_out_detects_past_deadline(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        store = PendingStore(project_root=tmp_project)
        store.enroll(PendingEntry(
            result_id="old", deadline_ts_ns=100,   # 远过期
            capability="c", project_id="p1",
        ))
        store.enroll(PendingEntry(
            result_id="future", deadline_ts_ns=10**18,   # 未来
            capability="c", project_id="p1",
        ))
        timed_out = store.timed_out(now_ns=10**10)
        ids = [e.result_id for e in timed_out]
        assert "old" in ids
        assert "future" not in ids

    def test_replay_loads_from_jsonl_on_restart(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        # 第一个 store 写入
        s1 = PendingStore(project_root=tmp_project)
        for i in range(5):
            s1.enroll(PendingEntry(
                result_id=f"r{i}", deadline_ts_ns=10**18, capability="c", project_id="p1",
            ))
        # 第二个 store 重 replay
        s2 = PendingStore(project_root=tmp_project)
        s2.replay()
        assert len(s2._cache) == 5

    def test_replay_tolerates_malformed_lines(self, tmp_project):
        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore

        path = tmp_project / "skills" / "registry-cache" / "pending.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"result_id":"r1","deadline_ts_ns":1,"capability":"c","project_id":"p1"}\n'
            'GARBAGE LINE NOT JSON\n'
            '{"result_id":"r2","deadline_ts_ns":1,"capability":"c","project_id":"p1"}\n',
            encoding="utf-8",
        )
        s = PendingStore(project_root=tmp_project)
        s.replay()
        assert "r1" in s._cache
        assert "r2" in s._cache
        # malformed 行被跳过 · 不 raise

    def test_crash_recovery_under_5s_for_1000_entries(self, tmp_project):
        """SLO: replay 1000 pending entries ≤ 5s."""
        import time

        from app.skill_dispatch.async_receiver.crash_recovery import PendingStore
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        s1 = PendingStore(project_root=tmp_project)
        for i in range(1000):
            s1.enroll(PendingEntry(
                result_id=f"r{i}", deadline_ts_ns=10**18 + i,
                capability="c", project_id="p1",
            ))
        s2 = PendingStore(project_root=tmp_project)
        t0 = time.perf_counter()
        s2.replay()
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"crash recovery {elapsed:.2f}s > 5s SLO"
        assert len(s2._cache) == 1000

    async def test_timeout_watcher_invokes_handler(self, tmp_project):
        import asyncio

        from app.skill_dispatch.async_receiver.crash_recovery import (
            PendingStore,
            TimeoutWatcher,
        )
        from app.skill_dispatch.async_receiver.schemas import PendingEntry

        store = PendingStore(project_root=tmp_project)
        store.enroll(PendingEntry(
            result_id="overdue", deadline_ts_ns=1, capability="c", project_id="p1",
        ))
        handled: list[str] = []

        def on_timeout(entry):
            handled.append(entry.result_id)

        watcher = TimeoutWatcher(store=store, tick_s=0.05)
        watcher.set_handler(on_timeout)
        await watcher.start()
        await asyncio.sleep(0.12)
        await watcher.stop()
        assert "overdue" in handled
