"""L2-05 Validator · jsonschema Draft 2020-12 · SCHEMA_UNAVAILABLE 硬失败 + E09 silent_patch.

契约红线:
  - schema_pointer is None 或文件不存在 → status=schema_unavailable · 硬失败（禁放行）
  - output 携带 input 未提供且非 schema.required 的字段 → status=silent_patch (E09 防默认补齐)
  - schema 本身不合法 → SchemaCompilationError raise

SLO: 校验 P99 ≤ 50ms (lru_cache 64 schemas)

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-05-异步结果回收器.md §3
  - docs/superpowers/plans/Dev-γ-impl.md §7 Task 05.2
"""
from __future__ import annotations

import functools
import json
import pathlib
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from .schemas import ValidationResult


class SchemaCompilationError(ValueError):
    """Schema 本身不合法 JSON Schema."""


class Validator:
    """L2-05 校验器 · 绑 registry_root 查找 schema_pointer 相对路径."""

    def __init__(self, registry_root: pathlib.Path) -> None:
        self._root = pathlib.Path(registry_root)

    @functools.lru_cache(maxsize=64)
    def _load(self, pointer: str) -> Draft202012Validator:
        path = self._root / pointer
        if not path.exists():
            raise FileNotFoundError(pointer)
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(raw)
        except jsonschema.SchemaError as e:
            raise SchemaCompilationError(str(e)) from e
        return Draft202012Validator(raw)

    def validate(
        self,
        *,
        raw_return: Any,
        schema_pointer: str | None,
        input_params: dict | None = None,
    ) -> ValidationResult:
        if schema_pointer is None:
            return ValidationResult(status="schema_unavailable")
        if not isinstance(raw_return, dict):
            return ValidationResult(
                status="format_invalid",
                errors=[{"kind": "type", "expected": "object", "actual": type(raw_return).__name__}],
            )
        try:
            validator = self._load(schema_pointer)
        except FileNotFoundError:
            return ValidationResult(status="schema_unavailable")

        errors = sorted(validator.iter_errors(raw_return), key=lambda e: tuple(e.path))
        if errors:
            return ValidationResult(
                status="format_invalid",
                errors=[
                    {
                        "kind": e.validator,
                        "path": list(e.path),
                        "message": e.message,
                    }
                    for e in errors
                ],
            )
        if input_params is not None and self._is_silent_patch(
            input_params, raw_return, validator.schema,
        ):
            return ValidationResult(status="silent_patch")
        return ValidationResult(status="passed")

    def _is_silent_patch(
        self, inp: dict, out: dict, schema: dict,
    ) -> bool:
        """E09 · output 新增的字段 · 既非 input 提供 · 也非 schema.required → 视为静默补齐."""
        required = set(schema.get("required", []))
        extra = set(out.keys()) - set(inp.keys()) - required
        return len(extra) > 0
