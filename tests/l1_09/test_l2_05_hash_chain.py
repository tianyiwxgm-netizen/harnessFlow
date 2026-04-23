"""L2-05 · WP α-WP02 · hash chain · RFC 8785 JCS + sha256 · TDD 红→绿.

对齐：
- 3-1 L2-05 §6.3.1 canonical_json_without_hash
- 3-1 L2-05 §6.3.2 compute_hash_chain_link
- 3-1 L2-05 §7.5 HashChainLink
- 3-2 L2-05-tests §4 hash chain 完整性（复用 verify 路径 · WP02 只验 compute/canonicalize）

覆盖：
  GENESIS + 3 连续链 + 篡改检测 + JCS 边界（unicode/数字/空对象/sorted keys）+ prev_hash 格式校验
  合计 ~10 TC。
"""
from __future__ import annotations

import hashlib

import pytest

from app.l1_09.crash_safety.canonical_json import canonical_json_without_hash
from app.l1_09.crash_safety.hash_chain import (
    GENESIS_HASH,
    compute_hash_chain_link,
    verify_chain_link,
)
from app.l1_09.crash_safety.schemas import HashChainLink


class TestCanonicalJson:
    """§6.3.1 canonical_json_without_hash · RFC 8785 JCS."""

    def test_drops_hash_field(self) -> None:
        body = {"seq": 1, "data": "x", "hash": "abcdef"}
        canon = canonical_json_without_hash(body)
        assert b'"hash"' not in canon
        assert b'"seq":1' in canon

    def test_sorted_keys(self) -> None:
        """RFC 8785 · 键按 UTF-16 code unit 升序."""
        body_a = {"a": 1, "b": 2, "c": 3}
        body_b = {"c": 3, "b": 2, "a": 1}
        assert canonical_json_without_hash(body_a) == canonical_json_without_hash(body_b)

    def test_no_whitespace(self) -> None:
        """RFC 8785 · 无冗余空格."""
        canon = canonical_json_without_hash({"k": "v"})
        assert b" " not in canon

    def test_integer_no_trailing_zero(self) -> None:
        """RFC 8785 · 整数不带 .0."""
        canon = canonical_json_without_hash({"n": 42})
        assert b"42.0" not in canon
        assert b"42" in canon

    def test_unicode_passthrough(self) -> None:
        """RFC 8785 · 非控制字符 Unicode 原样（不转 \\uXXXX）."""
        canon = canonical_json_without_hash({"name": "你好"})
        # 原样 utf-8 编码 · 不是 你好
        assert "你好".encode() in canon

    def test_empty_object(self) -> None:
        canon = canonical_json_without_hash({})
        assert canon == b"{}"


class TestComputeHashChainLink:
    """§6.3.2 compute_hash_chain_link · sha256(prev_bytes + canonical_bytes)."""

    def test_genesis_link(self) -> None:
        """GENESIS · prev_hash = '0' * 64."""
        body = {"seq": 0, "type": "system", "data": "boot"}
        link = compute_hash_chain_link(GENESIS_HASH, body)
        assert isinstance(link, HashChainLink)
        assert link.prev_hash == GENESIS_HASH
        assert len(link.curr_hash) == 64
        assert all(c in "0123456789abcdef" for c in link.curr_hash)

        # 手工验算
        canonical = canonical_json_without_hash(body)
        expected = hashlib.sha256(bytes.fromhex(GENESIS_HASH) + canonical).hexdigest()
        assert link.curr_hash == expected

    def test_chain_3_links(self) -> None:
        """连续 3 链 · 每链 prev == 上链 curr."""
        l1 = compute_hash_chain_link(GENESIS_HASH, {"seq": 1, "data": "a"})
        l2 = compute_hash_chain_link(l1.curr_hash, {"seq": 2, "data": "b"})
        l3 = compute_hash_chain_link(l2.curr_hash, {"seq": 3, "data": "c"})

        assert l2.prev_hash == l1.curr_hash
        assert l3.prev_hash == l2.curr_hash
        assert len({l1.curr_hash, l2.curr_hash, l3.curr_hash}) == 3

    def test_different_body_different_hash(self) -> None:
        """不同 body · hash 必不同（防碰撞）."""
        l1 = compute_hash_chain_link(GENESIS_HASH, {"seq": 1, "data": "a"})
        l2 = compute_hash_chain_link(GENESIS_HASH, {"seq": 1, "data": "b"})
        assert l1.curr_hash != l2.curr_hash

    def test_key_order_invariant(self) -> None:
        """键顺序不影响 hash（JCS 保证）."""
        l1 = compute_hash_chain_link(GENESIS_HASH, {"a": 1, "b": 2})
        l2 = compute_hash_chain_link(GENESIS_HASH, {"b": 2, "a": 1})
        assert l1.curr_hash == l2.curr_hash

    def test_hash_field_excluded_from_calc(self) -> None:
        """body 中的 hash 字段被忽略（canonical_json_without_hash）."""
        l1 = compute_hash_chain_link(GENESIS_HASH, {"seq": 1, "data": "x"})
        l2 = compute_hash_chain_link(GENESIS_HASH, {"seq": 1, "data": "x", "hash": "fake"})
        assert l1.curr_hash == l2.curr_hash

    def test_prev_hash_format_invalid(self) -> None:
        """prev_hash 非 64 位小写 hex · 抛 AssertionError."""
        with pytest.raises(AssertionError):
            compute_hash_chain_link("short", {"seq": 1})
        with pytest.raises(AssertionError):
            compute_hash_chain_link("ABCDEF" + "0" * 58, {"seq": 1})  # 大写
        with pytest.raises(AssertionError):
            compute_hash_chain_link("g" * 64, {"seq": 1})  # 非 hex


class TestVerifyChainLink:
    """mutation test · 篡改检测."""

    def test_tamper_detected(self) -> None:
        """篡改 body 后 · verify_chain_link 返 False."""
        body = {"seq": 1, "data": "original"}
        link = compute_hash_chain_link(GENESIS_HASH, body)

        # 原 body 验证通过
        assert verify_chain_link(link, body) is True

        # 篡改 body
        tampered = {**body, "data": "tampered"}
        assert verify_chain_link(link, tampered) is False

    def test_truncated_chain_still_verifies_prefix(self) -> None:
        """删掉末尾 1 条 · 前缀仍可验（Tier 3 恢复锚点）."""
        bodies = [{"seq": i, "data": f"d{i}"} for i in range(5)]
        prev = GENESIS_HASH
        links = []
        for body in bodies:
            link = compute_hash_chain_link(prev, body)
            links.append(link)
            prev = link.curr_hash

        # 前 4 条验证通过
        for i, link in enumerate(links[:-1]):
            assert verify_chain_link(link, bodies[i]) is True
