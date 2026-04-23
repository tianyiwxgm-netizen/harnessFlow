"""L2-05 · hash 链算法 · 对齐 3-1 §6.3.

公式：`curr_hash = sha256(bytes.fromhex(prev_hash) + canonical_json_bytes).hex()`

GENESIS：`prev_hash = "0" * 64`（64 个零字符 · 对应 32 字节全零哈希）
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.l1_09.crash_safety.canonical_json import canonical_json_without_hash
from app.l1_09.crash_safety.schemas import HashChainLink

GENESIS_HASH: str = "0" * 64


def _assert_hex64(value: str, *, label: str) -> None:
    assert len(value) == 64, f"{label} must be 64 chars, got {len(value)}: {value[:12]!r}..."
    assert all(c in "0123456789abcdef" for c in value), (
        f"{label} must be lowercase hex, got {value[:12]!r}..."
    )


def compute_hash_chain_link(prev_hash: str, body: dict[str, Any]) -> HashChainLink:
    """§6.3.2 单条事件的 hash 链节点.

    前置断言：
        - prev_hash 64 位小写 hex（包括 GENESIS_HASH）
        - body 是 dict

    返回 HashChainLink(prev_hash, curr_hash, sequence, body_canonical_json).
    """
    _assert_hex64(prev_hash, label="prev_hash")

    body_canonical = canonical_json_without_hash(body)
    prev_bytes = bytes.fromhex(prev_hash)
    hasher = hashlib.sha256()
    hasher.update(prev_bytes)
    hasher.update(body_canonical)
    curr_hash = hasher.hexdigest()

    return HashChainLink(
        prev_hash=prev_hash,
        curr_hash=curr_hash,
        sequence=body.get("sequence") if isinstance(body.get("sequence"), int) else None,
        body_canonical_json=body_canonical,
    )


def verify_chain_link(link: HashChainLink, body: dict[str, Any]) -> bool:
    """验证 `link.curr_hash` 是否等于从 body + prev_hash 重算结果.

    True  · body 未篡改 · hash 一致
    False · body 被篡改（或 prev_hash 不符）
    """
    try:
        recomputed = compute_hash_chain_link(link.prev_hash, body)
    except AssertionError:
        return False
    return recomputed.curr_hash == link.curr_hash
