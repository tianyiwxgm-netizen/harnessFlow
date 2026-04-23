"""Jinja2 SandboxedEnvironment 配置 · 对齐 tech §6.4。

硬约束：
- autoescape=False（md 产出无需 HTML escape）
- StrictUndefined（未定义变量即报错）
- ALLOWED_FILTERS 白名单（禁 import / getattr / subprocess）
- SandboxedEnvironment 默认已禁 __class__ / __mro__ / __subclasses__ 等
"""
from __future__ import annotations

import os
import tempfile
from typing import Any

from jinja2 import FileSystemBytecodeCache, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


def _safe_date_iso(d: Any) -> str:
    if d is None:
        return ""
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


def _safe_join(items: Any, sep: str = ",") -> str:
    if items is None:
        return ""
    return sep.join(str(i) for i in items)


def _safe_first(items: Any) -> Any:
    if not items:
        return None
    return items[0]


def _safe_trim(s: Any) -> str:
    return str(s).strip() if s is not None else ""


ALLOWED_FILTERS: dict[str, Any] = {
    "upper": lambda s: str(s).upper(),
    "lower": lambda s: str(s).lower(),
    "title": lambda s: str(s).title(),
    "trim": _safe_trim,
    "int": int,
    "round": round,
    "join": _safe_join,
    "length": len,
    "first": _safe_first,
    "date_iso": _safe_date_iso,
}


_DEFAULT_BYTECODE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "harnessflow-l207-jinja-bcache")


def build_sandbox_env(
    bytecode_cache_dir: str | None = _DEFAULT_BYTECODE_CACHE_DIR,
) -> SandboxedEnvironment:
    """构建 sandbox Environment · 仅允许白名单 filter + StrictUndefined + bytecode cache。

    bytecode_cache_dir: 首次启动 compile 后缓存到磁盘；后续启动直读 · P95 达 SLO 关键。
    传 None 禁用（测试环境）。
    """
    bcc: FileSystemBytecodeCache | None = None
    if bytecode_cache_dir:
        os.makedirs(bytecode_cache_dir, exist_ok=True)
        bcc = FileSystemBytecodeCache(directory=bytecode_cache_dir, pattern="%s.cache")

    env = SandboxedEnvironment(
        autoescape=False,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        bytecode_cache=bcc,
    )
    env.filters = dict(ALLOWED_FILTERS)
    return env
