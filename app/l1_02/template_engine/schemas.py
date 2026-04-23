"""L2-07 数据类型 · 对齐 L2-07 tech §3.3 + §7。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RenderedOutput:
    """render_template 返回值。对齐 tech §3.3。"""

    request_id: str
    template_id: str
    template_version: str
    slots_hash: str
    output: str
    body_sha256: str
    lines: int
    frontmatter: dict[str, Any]
    rendered_at: str
    engine_version: str


@dataclass(frozen=True)
class TemplateEntry:
    """in-memory TemplateRegistry 单元。"""

    id: str
    kind: str
    version: str
    slot_schema: dict[str, Any]
    template_obj: Any  # jinja2.Template
    file_path: str
    file_sha256: str


@dataclass(frozen=True)
class ValidationResult:
    """validate_slots 返回值。"""

    ok: bool
    error_code: str | None = None
    details: Any = None

    def is_ok(self) -> bool:
        return self.ok

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(ok=True)

    @classmethod
    def fail(cls, error: str, details: Any = None) -> "ValidationResult":
        return cls(ok=False, error_code=error, details=details)
