"""render_core 单次渲染 pipeline · 对齐 tech §6.1。

10 步：
  1. caller 白名单
  2. kind 正则
  3. registry lookup
  4. version pin
  5. slots_hash mismatch
  6. jsonschema 校验 slots
  7. Sandbox 渲染（带超时）
  8. 输出大小 ≤ MAX_OUTPUT_BYTES
  9. 注入 frontmatter metadata + 计算 hash
  10. 解析 frontmatter 回返 RenderedOutput
"""
from __future__ import annotations

import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import jinja2
import jinja2.sandbox
import jsonschema
import yaml

try:
    from yaml import CSafeDumper as _YamlSafeDumper
except ImportError:  # pragma: no cover
    from yaml import SafeDumper as _YamlSafeDumper  # type: ignore[assignment]

from app.project_lifecycle.template_engine.errors import (
    E_CALLER_NOT_WHITELISTED,
    E_FRONTMATTER_PARSE_FAIL,
    E_HASH_COMPUTE_FAIL,
    E_INVALID_KIND_NAME,
    E_OUTPUT_TOO_LARGE,
    E_RENDER_TIMEOUT,
    E_SLOT_REQUIRED_MISSING,
    E_SLOT_SCHEMA_VIOLATION,
    E_SLOTS_HASH_MISMATCH,
    E_TEMPLATE_CODE_EXEC,
    E_TEMPLATE_NOT_FOUND,
    E_VERSION_MISMATCH,
    TemplateEngineError,
)
from app.project_lifecycle.template_engine.hashing import (
    canonical_slots_hash,
    compute_output_hash,
    split_frontmatter,
)
from app.project_lifecycle.template_engine.registry import TemplateRegistry
from app.project_lifecycle.template_engine.schemas import RenderedOutput, TemplateEntry

ENGINE_VERSION = "1.0.0"
KIND_PATTERN = re.compile(r"^[a-z0-9._-]+$")
ALLOWED_CALLERS = frozenset({"L2-01", "L2-02", "L2-03", "L2-04", "L2-05", "L2-06"})
DEFAULT_TIMEOUT_MS = 2000
MAX_TIMEOUT_MS = 10000
MIN_TIMEOUT_MS = 50
MAX_OUTPUT_BYTES = 204800  # 200KB


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _inject_metadata(
    body: str,
    entry: TemplateEntry,
    doc_id_suffix: str,
) -> str:
    """渲染后注入 frontmatter 元数据（template_id / version / rendered_at / doc_id / doc_type）。

    若原 frontmatter 已含字段则保留；否则由引擎兜底。保证 I-L207-03。
    """
    fm, main = split_frontmatter(body)
    fm["template_id"] = entry.id
    fm["template_version"] = entry.version
    fm.setdefault("rendered_at", _now_iso())
    fm.setdefault("doc_id", f"{entry.kind}-{doc_id_suffix[:12]}")
    fm.setdefault("doc_type", entry.kind)
    fm_str = yaml.dump(
        fm,
        Dumper=_YamlSafeDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    return f"---\n{fm_str}\n---\n{main}"


def _render_with_timeout(
    entry: TemplateEntry,
    slots: dict[str, Any],
    timeout_ms: int,
) -> str:
    """Threading-based soft timeout · 对 Python 无中断式线程合理工作的 SafeGuard。"""
    result: dict[str, Any] = {}

    def _do() -> None:
        try:
            result["body"] = entry.template_obj.render(**slots)
        except BaseException as exc:  # noqa: BLE001
            result["exc"] = exc

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    t.join(timeout=timeout_ms / 1000.0)
    if t.is_alive():
        raise TimeoutError(f"render timed out after {timeout_ms}ms")
    if "exc" in result:
        raise result["exc"]
    return result["body"]


def render_core(
    registry: TemplateRegistry,
    request_id: str,
    project_id: str,
    kind: str,
    slots: dict[str, Any],
    caller_l2: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    expected_version: str | None = None,
    expected_slots_hash: str | None = None,
    hash_fn: Callable[[dict[str, Any]], str] = canonical_slots_hash,
    output_hash_fn: Callable[[str], str] = compute_output_hash,
) -> RenderedOutput:
    # 1. caller 白名单
    if caller_l2 not in ALLOWED_CALLERS:
        raise TemplateEngineError(
            error_code=E_CALLER_NOT_WHITELISTED,
            message=f"caller_l2={caller_l2!r} not in whitelist {sorted(ALLOWED_CALLERS)}",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    # 2. kind 正则（防路径穿越、空格、大小写）
    if not kind or not KIND_PATTERN.match(kind):
        raise TemplateEngineError(
            error_code=E_INVALID_KIND_NAME,
            message=f"kind {kind!r} violates [a-z0-9._-]+",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    # 3. registry lookup
    entry = registry.lookup(kind)
    if entry is None:
        raise TemplateEngineError(
            error_code=E_TEMPLATE_NOT_FOUND,
            message=f"kind {kind!r} not registered",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    # 4. version pin
    if expected_version and expected_version != entry.version:
        raise TemplateEngineError(
            error_code=E_VERSION_MISMATCH,
            message=f"expected {expected_version} but registry pinned {entry.version}",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    # 5. slots hash mismatch
    if expected_slots_hash is not None:
        try:
            actual = hash_fn(slots)
        except Exception as exc:  # noqa: BLE001
            raise TemplateEngineError(
                error_code=E_HASH_COMPUTE_FAIL,
                message=f"slots_hash compute failed: {exc}",
                caller_l2=caller_l2,
                project_id=project_id,
            ) from exc
        if actual != expected_slots_hash:
            raise TemplateEngineError(
                error_code=E_SLOTS_HASH_MISMATCH,
                message="slots_hash mismatch",
                caller_l2=caller_l2,
                project_id=project_id,
            )

    # 6. jsonschema 校验 slots
    validator = jsonschema.Draft202012Validator(entry.slot_schema)
    errors = sorted(validator.iter_errors(slots), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        err_code = (
            E_SLOT_REQUIRED_MISSING if first.validator == "required" else E_SLOT_SCHEMA_VIOLATION
        )
        raise TemplateEngineError(
            error_code=err_code,
            message=first.message,
            caller_l2=caller_l2,
            project_id=project_id,
            context={"validation_errors": [e.message for e in errors]},
        )

    # 7. sandbox 渲染（超时）
    timeout_ms = min(max(MIN_TIMEOUT_MS, timeout_ms), MAX_TIMEOUT_MS)
    try:
        rendered = _render_with_timeout(entry, slots, timeout_ms)
    except TimeoutError as exc:
        raise TemplateEngineError(
            error_code=E_RENDER_TIMEOUT,
            message=f"render exceeded {timeout_ms}ms",
            caller_l2=caller_l2,
            project_id=project_id,
        ) from exc
    except jinja2.sandbox.SecurityError as exc:
        raise TemplateEngineError(
            error_code=E_TEMPLATE_CODE_EXEC,
            message=f"sandbox violation: {exc}",
            caller_l2=caller_l2,
            project_id=project_id,
            context={"kind": kind},
        ) from exc

    # 8. 输出大小校验
    if len(rendered.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise TemplateEngineError(
            error_code=E_OUTPUT_TOO_LARGE,
            message=f"output {len(rendered)} bytes > {MAX_OUTPUT_BYTES}",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    # 9. 计算 hash + 注入 metadata
    try:
        slots_hash = hash_fn(slots)
        # 先算初步 hash 作 doc_id 后缀
        prelim_hash = output_hash_fn(rendered)
        body_with_meta = _inject_metadata(rendered, entry, prelim_hash)
        # 最终 output_sha256 基于注入元数据后的稳定字段（rendered_at 在 compute_output_hash 已排除）
        output_sha256 = output_hash_fn(body_with_meta)
    except Exception as exc:  # noqa: BLE001
        raise TemplateEngineError(
            error_code=E_HASH_COMPUTE_FAIL,
            message=f"hash compute failed: {exc}",
            caller_l2=caller_l2,
            project_id=project_id,
        ) from exc

    # 10. 解析回返 frontmatter
    fm_after, _main_after = split_frontmatter(body_with_meta)
    if not fm_after or "template_id" not in fm_after:
        raise TemplateEngineError(
            error_code=E_FRONTMATTER_PARSE_FAIL,
            message="rendered body missing frontmatter template_id",
            caller_l2=caller_l2,
            project_id=project_id,
        )

    return RenderedOutput(
        request_id=request_id,
        template_id=entry.id,
        template_version=entry.version,
        slots_hash=slots_hash,
        output=body_with_meta,
        body_sha256=output_sha256,
        lines=body_with_meta.count("\n") + 1,
        frontmatter=fm_after,
        rendered_at=str(fm_after.get("rendered_at") or _now_iso()),
        engine_version=ENGINE_VERSION,
    )
