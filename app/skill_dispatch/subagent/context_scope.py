"""L2-04 Context COW 快照 · PM-03 隔离 · checksum 护栏.

PM-03:
  - 子 Agent 独立 session · 只读上游 context 副本
  - 白名单字段暴露: project_id / wp_id / related_artifacts / dod_exprs / correlation_id
  - 黑名单（永不暴露）: task_board / 任何敏感 token/key/password

COW (Copy-on-Write) 约定:
  - 生成 child context 时 · 先 deep-extract 白名单字段 · 再用 MappingProxyType 包成只读
  - 产出 checksum (SHA-256) · 子 Agent 启动时可 verify_checksum() 检测父 session 篡改

跨 project 保护 (PM-14):
  - ctx.project_id 与 child_project_id 不一致 → ContextIsolationViolation

内存保护:
  - max_bytes 限制 · 超过 → ContextOverflow (默认 10 MB)

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §6 Task 04.2
"""
from __future__ import annotations

import hashlib
import json
import types
from typing import Any, Mapping

PUBLIC_CONTEXT_KEYS: frozenset[str] = frozenset(
    {
        "project_id",         # PM-14 主键
        "wp_id",               # WP 追溯
        "related_artifacts",   # 子 Agent 需读的文件/产物引用
        "dod_exprs",           # DoD 表达式（verifier 用）
        "correlation_id",      # 跨 L1 审计关联
    }
)

_DEFAULT_MAX_BYTES: int = 10 * 1024 * 1024   # 10 MB


class ContextIsolationViolation(PermissionError):
    """E_SUB_CONTEXT_ISOLATION_VIOLATION · 跨 project 或黑名单访问."""


class ContextOverflow(ValueError):
    """E_SUB_CONTEXT_OVERFLOW · context 副本超内存上限."""


def _canonical_bytes(ctx: Mapping[str, Any]) -> bytes:
    """稳定序列化 · 便于 checksum."""
    return json.dumps(dict(ctx), sort_keys=True, default=str).encode("utf-8")


def make_child_context(
    parent_ctx: Mapping[str, Any],
    *,
    child_project_id: str,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> tuple[Mapping[str, Any], str]:
    """生成子 Agent 只读 context + SHA-256 checksum.

    Returns:
        (child_ctx: MappingProxyType, checksum: 64-char hex)

    Raises:
        ValueError: child_project_id 为空（PM-14）
        ContextIsolationViolation: parent.project_id != child_project_id
        ContextOverflow: 白名单字段内容超 max_bytes
    """
    if not child_project_id:
        raise ValueError("make_child_context: child_project_id required (PM-14)")
    parent_pid = parent_ctx.get("project_id")
    if parent_pid and parent_pid != child_project_id:
        raise ContextIsolationViolation(
            f"E_SUB_CONTEXT_ISOLATION_VIOLATION: parent={parent_pid} child={child_project_id}"
        )

    filtered = {k: parent_ctx[k] for k in parent_ctx if k in PUBLIC_CONTEXT_KEYS}
    filtered["project_id"] = child_project_id   # 强制保证 pid 一致

    serialized = _canonical_bytes(filtered)
    if len(serialized) > max_bytes:
        raise ContextOverflow(
            f"E_SUB_CONTEXT_OVERFLOW: context size {len(serialized)} > {max_bytes}"
        )

    checksum = hashlib.sha256(serialized).hexdigest()
    # 只读视图 · 尝试 child[k] = v 会 TypeError
    return types.MappingProxyType(filtered), checksum


def verify_checksum(ctx: Mapping[str, Any], expected: str) -> bool:
    """校验 ctx 序列化后 hash 是否匹配 expected · 供子 Agent 启动时防篡改."""
    return hashlib.sha256(_canonical_bytes(ctx)).hexdigest() == expected
