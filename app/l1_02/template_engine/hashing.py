"""slots_hash + output_sha256 规范化 · 对齐 tech §6.2。

I-L207-01 幂等保证：
  - 同 slots → 同 slots_hash（规范化即递归 sort keys + YAML dump）
  - 同 body（排除 frontmatter 中 rendered_at/updated_at 可变字段）→ 同 output_sha256
"""
from __future__ import annotations

import hashlib
from typing import Any

import yaml

try:
    from yaml import CSafeDumper as _YamlSafeDumper
    from yaml import CSafeLoader as _YamlSafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeDumper as _YamlSafeDumper  # type: ignore[assignment]
    from yaml import SafeLoader as _YamlSafeLoader  # type: ignore[assignment]


def canonical_slots_hash(slots: dict[str, Any]) -> str:
    """slots 规范化为 sha256 hex（64 char）。"""
    normalized = _canonicalize(slots)
    payload = yaml.dump(normalized, Dumper=_YamlSafeDumper, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _canonicalize(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_canonicalize(i) for i in v]
    return v


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """分离 `---\\n<yaml>\\n---\\n<body>` · 无 frontmatter 返 ({}, text)。"""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    idx = rest.find("\n---")
    if idx < 0:
        return {}, text
    fm_str = rest[:idx]
    body = rest[idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    try:
        fm = yaml.load(fm_str, Loader=_YamlSafeLoader) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(fm, dict):
        return {}, text
    return fm, body


def compute_output_hash(body: str) -> str:
    """规范化 body + frontmatter（排除 rendered_at/updated_at）后 sha256 hex。"""
    fm, main = split_frontmatter(body)
    fm_filtered = {k: v for k, v in fm.items() if k not in ("rendered_at", "updated_at")}
    fm_str = yaml.dump(fm_filtered, Dumper=_YamlSafeDumper, sort_keys=True, allow_unicode=True)
    main_norm = main.strip().replace("\r\n", "\n")
    combined = (fm_str + "\n---\n" + main_norm).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()
