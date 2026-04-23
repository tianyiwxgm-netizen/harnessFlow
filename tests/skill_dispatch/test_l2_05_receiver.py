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
