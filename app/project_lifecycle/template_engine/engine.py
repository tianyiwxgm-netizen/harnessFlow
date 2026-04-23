"""TemplateEngine public API · 对齐 tech §3.1。

4 public 方法：
  - render_template  · 核心
  - list_available_templates
  - get_template_version
  - validate_slots
"""
from __future__ import annotations

from typing import Any

import jsonschema

from app.project_lifecycle.common.event_emitter import EventEmitter
from app.project_lifecycle.template_engine.errors import (
    E_SLOT_REQUIRED_MISSING,
    E_SLOT_SCHEMA_VIOLATION,
    E_TEMPLATE_CODE_EXEC,
    E_TEMPLATE_NOT_FOUND,
    TemplateEngineError,
)
from app.project_lifecycle.template_engine.hashing import canonical_slots_hash, compute_output_hash
from app.project_lifecycle.template_engine.registry import (
    REQUIRED_KINDS_DEFAULT,
    TemplateLoader,
    TemplateRegistry,
)
from app.project_lifecycle.template_engine.renderer import ENGINE_VERSION, render_core
from app.project_lifecycle.template_engine.schemas import RenderedOutput, ValidationResult


class TemplateEngine:
    """无状态 Domain Service · 持 TemplateRegistry + EventEmitter 引用。"""

    def __init__(
        self,
        registry: TemplateRegistry,
        event_emitter: EventEmitter | None = None,
    ) -> None:
        self._registry = registry
        self._emitter = event_emitter if event_emitter is not None else EventEmitter()
        self._hash_fn = canonical_slots_hash
        self._output_hash_fn = compute_output_hash

    @classmethod
    def load_from_dir(
        cls,
        template_dir: str,
        event_emitter: EventEmitter | None = None,
        required_kinds: list[str] | tuple[str, ...] | None = None,
        validate_slot_schemas: bool = False,
    ) -> TemplateEngine:
        loader = TemplateLoader(
            template_dir=template_dir,
            required_kinds=(
                required_kinds if required_kinds is not None else REQUIRED_KINDS_DEFAULT
            ),
            validate_slot_schemas=validate_slot_schemas,
        )
        registry = loader.load_all()
        return cls(registry=registry, event_emitter=event_emitter)

    # ---- public API ----

    def list_available_templates(self) -> list[str]:
        return self._registry.list()

    def get_template_version(self, kind: str) -> str | None:
        return self._registry.get_version(kind)

    def validate_slots(self, kind: str, slots: dict[str, Any]) -> ValidationResult:
        entry = self._registry.lookup(kind)
        if entry is None:
            return ValidationResult.fail(error=E_TEMPLATE_NOT_FOUND)
        validator = jsonschema.Draft202012Validator(entry.slot_schema)
        errors = sorted(validator.iter_errors(slots), key=lambda e: list(e.path))
        if not errors:
            return ValidationResult.success()
        first = errors[0]
        if first.validator == "required":
            return ValidationResult.fail(
                error=E_SLOT_REQUIRED_MISSING, details=[e.message for e in errors]
            )
        return ValidationResult.fail(
            error=E_SLOT_SCHEMA_VIOLATION, details=[e.message for e in errors]
        )

    def render_template(
        self,
        request_id: str,
        project_id: str,
        kind: str,
        slots: dict[str, Any],
        caller_l2: str,
        timeout_ms: int = 2000,
        expected_version: str | None = None,
        expected_slots_hash: str | None = None,
    ) -> RenderedOutput:
        try:
            out = render_core(
                registry=self._registry,
                request_id=request_id,
                project_id=project_id,
                kind=kind,
                slots=slots,
                caller_l2=caller_l2,
                timeout_ms=timeout_ms,
                expected_version=expected_version,
                expected_slots_hash=expected_slots_hash,
                hash_fn=self._hash_fn,
                output_hash_fn=self._output_hash_fn,
            )
        except TemplateEngineError as exc:
            # E005 sandbox 逃逸 → CRITICAL 事件
            if exc.error_code == E_TEMPLATE_CODE_EXEC:
                try:
                    self._emitter.emit(
                        project_id=project_id,
                        event_type="L1-02/L2-07:template_code_exec_attempt",
                        payload={
                            "template_id": kind,
                            "caller_l2": caller_l2,
                            "sandbox_violation_type": str(exc),
                        },
                        severity="CRITICAL",
                        caller_l2=caller_l2,
                    )
                except Exception:  # noqa: BLE001
                    pass
            raise

        # IC-09 emit template_rendered（不阻塞失败）
        try:
            self._emitter.emit(
                project_id=project_id,
                event_type="L1-02/L2-07:template_rendered",
                payload={
                    "template_id": out.template_id,
                    "template_version": out.template_version,
                    "caller_l2": caller_l2,
                    "slots_hash": out.slots_hash,
                    "output_sha256": out.body_sha256,
                    "rendered_at": out.rendered_at,
                    "engine_version": out.engine_version,
                },
                severity="INFO",
                caller_l2=caller_l2,
            )
        except Exception:  # noqa: BLE001
            pass
        return out

    # ---- 测试辅助接口 ----

    def audit_state(self) -> str:
        return self._emitter.state

    def audit_buffer(self) -> list:
        return list(self._emitter.buffer)


# 扩 __init__ export（此处通过模块内 import 即 re-export）
ENGINE_VERSION_EXPORT = ENGINE_VERSION
