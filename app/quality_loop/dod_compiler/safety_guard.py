"""L1-04 · L2-02 · 安全红线断言 + 字符串级预检查.

锚点:
    - §6.1 黑名单前置检查
    - §11 E_AST_ILLEGAL_NODE + E_SANDBOX_ESCAPE_DETECTED

字符串级快速过滤(发现危险 token 直接拒编译 · 防御纵深):
    - 禁 exec / eval / compile / __import__
    - 禁 import / from X
    - 禁 dunder (__X__)
    - 禁 ;(多语句)
    - 禁 := (walrus · py3.8+)
"""
from __future__ import annotations

import re

from app.quality_loop.dod_compiler.errors import (
    IllegalNodeError,
    OnlineWhitelistMutationError,
    WhitelistTamperingError,
)

# 危险 token 快速扫描(发现立即 reject · 不走 AST)
_DANGER_TOKENS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(exec|eval|compile|__import__|open|globals|locals|vars|getattr|setattr|delattr|hasattr|breakpoint)\s*\("), "builtin-call"),
    (re.compile(r"\bimport\b"), "import-keyword"),
    (re.compile(r"\bfrom\s+\w+"), "from-import"),
    (re.compile(r"__\w+__"), "dunder-name"),
    (re.compile(r";"), "statement-separator"),
    (re.compile(r":="), "walrus-operator"),
    (re.compile(r"\blambda\b"), "lambda-keyword"),
    (re.compile(r"\byield\b"), "yield-keyword"),
    (re.compile(r"\basync\b|\bawait\b"), "async-keyword"),
]


def scan_danger_tokens(expression_text: str) -> list[str]:
    """扫描并返回触发的危险 token 类别 · 空列表 = 干净."""
    if not isinstance(expression_text, str):
        return ["non-string-input"]
    hits: list[str] = []
    for rx, label in _DANGER_TOKENS:
        if rx.search(expression_text):
            hits.append(label)
    return hits


def assert_no_danger_tokens(expression_text: str) -> None:
    """快速前置过滤 · 命中则抛 IllegalNodeError."""
    hits = scan_danger_tokens(expression_text)
    if hits:
        raise IllegalNodeError(
            f"dangerous tokens detected: {hits}"
        )


# ========== 白名单篡改检测 ==========


def assert_offline_admin(
    offline_admin_mode: bool,
    *,
    action: str = "add_whitelist_rule",
) -> None:
    """生产态调特权方法 → 立即 reject (§3.5)."""
    if not offline_admin_mode:
        raise OnlineWhitelistMutationError(
            f"{action} requires OFFLINE_ADMIN_MODE=1 (production call blocked)"
        )


def assert_registry_integrity(baseline_hash: str | None, current_hash: str | None) -> None:
    """白名单 watchdog 断言(§6.5)."""
    if baseline_hash is None or current_hash is None:
        return
    if baseline_hash != current_hash:
        raise WhitelistTamperingError(
            f"whitelist tampering detected: baseline={baseline_hash[:8]} != current={current_hash[:8]}"
        )


__all__ = [
    "assert_no_danger_tokens",
    "assert_offline_admin",
    "assert_registry_integrity",
    "scan_danger_tokens",
]
