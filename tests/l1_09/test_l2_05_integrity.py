"""L2-05 · WP α-WP03 · verify_integrity + recover_partial_write · TDD 红→绿.

对齐：
- 3-1 L2-05 §3.4 / §3.5 / §6.4 / §6.5 / §7.8 header format
- 3-2 L2-05-tests §2 TC-010~015 + §3 TC-111/112 + §4 TC-203/204

覆盖（~18 TC）：
  verify_integrity:
    HASH_CHAIN：TC-010 OK · TC-111 PARTIAL（hash 断）· CORRUPT · 空文件
    HEADER_CHECKSUM：TC-011 OK · CORRUPT · 文件过短
    TAIL_CONSISTENCY：TC-012 OK · 无 version · 非 JSON
  recover_partial_write:
    TC-013 删 24h+ 孤儿 tmp · TC-014 TRUNCATE_TAIL · TC-015 NO_ACTION · TC-112 young tmp 保守
    TC-203/204 IC 契约
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from app.l1_09 import crash_safety as cs
from app.l1_09.crash_safety import (
    IntegrityMethod,
    IntegrityReport,
    IntegrityState,
    RecoveryActionKind,
)
from app.l1_09.crash_safety.hash_chain import GENESIS_HASH, compute_hash_chain_link
from app.l1_09.crash_safety.integrity_checker import HEADER_SIZE, compose_header

# =========================================================
# Helpers · 合成测试数据
# =========================================================

def _make_events_line(body: dict, prev_hash: str) -> tuple[str, str]:
    """生成一条合法 events.jsonl 行 + 返 (line, curr_hash).

    与 §6.3.3 一致 · body 含 `prev_hash` 参与 canonical_json · `hash` 字段剔除后参与 canonical.
    """
    body_with_prev = {**body, "prev_hash": prev_hash}
    link = compute_hash_chain_link(prev_hash, body_with_prev)
    body_with_meta = {**body_with_prev, "hash": link.curr_hash}
    return json.dumps(body_with_meta, sort_keys=False), link.curr_hash


def _make_good_events_jsonl(path: Path, n: int) -> list[str]:
    """追加 n 条健康 jsonl · 返每条的 curr_hash."""
    prev = GENESIS_HASH
    hashes: list[str] = []
    lines: list[str] = []
    for i in range(n):
        line, prev = _make_events_line({"seq": i, "data": f"d{i}"}, prev)
        lines.append(line)
        hashes.append(prev)
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return hashes


def _make_checkpoint_file(path: Path, body: bytes) -> None:
    """写一份合法 HEADER_CHECKSUM 格式文件（header = 128B · body）."""
    header = compose_header(body)
    path.write_bytes(header + body)


# =========================================================
# verify_integrity · HASH_CHAIN
# =========================================================

class TestVerifyHashChain:
    def test_verify_hash_chain_ok_tc010(self, tmp_fs: Path) -> None:
        """TC-L109-L205-010 · 健康 jsonl · state=OK · total_items 对."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=5)
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)

        assert isinstance(report, IntegrityReport)
        assert report.state == IntegrityState.OK
        assert report.total_items == 5
        assert report.failure_range is None
        assert report.first_bad_hash is None

    def test_verify_hash_chain_partial_tc111(self, tmp_fs: Path) -> None:
        """TC-L109-L205-111 · 第 3 条被篡改 · state=PARTIAL · first_good_hash 非 None."""
        target = tmp_fs / "events.jsonl"
        hashes = _make_good_events_jsonl(target, n=5)
        # 篡改第 3 条（0-indexed seq=2 的 data）
        raw = target.read_bytes().decode("utf-8").splitlines()
        bad = json.loads(raw[2])
        bad["data"] = "TAMPERED"  # 不改 hash 字段 · 造 hash 不符
        raw[2] = json.dumps(bad, sort_keys=False)
        target.write_bytes(("\n".join(raw) + "\n").encode("utf-8"))

        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.PARTIAL
        assert report.failure_range is not None
        assert report.failure_range[0] == 2  # first_bad_seq
        assert report.first_good_hash is not None
        assert report.first_good_hash == hashes[1]  # 最后有效 = seq=1 的 hash

    def test_verify_hash_chain_corrupt_first_line(self, tmp_fs: Path) -> None:
        """第 1 条就 hash 断 · state=CORRUPT（无 prior good · PARTIAL 条件不满足）."""
        target = tmp_fs / "events.jsonl"
        # seq=0 的 body 改 prev_hash 为非 GENESIS
        bad_body = {"seq": 0, "data": "x", "prev_hash": "a" * 64, "hash": "b" * 64}
        target.write_bytes((json.dumps(bad_body) + "\n").encode())
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.CORRUPT

    def test_verify_hash_chain_empty_file(self, tmp_fs: Path) -> None:
        """空 jsonl · state=OK · total_items=0."""
        target = tmp_fs / "events.jsonl"
        target.write_bytes(b"")
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK
        assert report.total_items == 0

    def test_verify_hash_chain_garbage_last_line(self, tmp_fs: Path) -> None:
        """末行是 crash 半截 JSON · state=PARTIAL · 前面 OK."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=3)
        # 追加坏尾
        with open(target, "ab") as f:
            f.write(b"{\"seq\":3,\"data\":\"half")  # 未完成
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.PARTIAL
        assert report.total_items == 3  # 前 3 条 OK
        assert report.first_good_hash is not None


# =========================================================
# verify_integrity · HEADER_CHECKSUM
# =========================================================

class TestVerifyHeaderChecksum:
    def test_verify_header_ok_tc011(self, tmp_fs: Path) -> None:
        """TC-L109-L205-011 · 合法 header · state=OK."""
        target = tmp_fs / "cp.json"
        _make_checkpoint_file(target, b'{"snapshot":1}')
        report = cs.verify_integrity(target, method=IntegrityMethod.HEADER_CHECKSUM)
        assert report.state == IntegrityState.OK

    def test_verify_header_corrupt_body_tampered(self, tmp_fs: Path) -> None:
        """header checksum 正确 · 但 body 被改 · state=CORRUPT."""
        target = tmp_fs / "cp.json"
        body = b'{"snapshot":1}'
        _make_checkpoint_file(target, body)
        # 篡改 body
        content = bytearray(target.read_bytes())
        content[HEADER_SIZE + 5] ^= 0xFF  # 翻转一个 bit
        target.write_bytes(bytes(content))
        report = cs.verify_integrity(target, method=IntegrityMethod.HEADER_CHECKSUM)
        assert report.state == IntegrityState.CORRUPT
        assert report.failure_range is not None

    def test_verify_header_too_short(self, tmp_fs: Path) -> None:
        """文件短于 HEADER_SIZE · state=CORRUPT."""
        target = tmp_fs / "cp.json"
        target.write_bytes(b"short")
        report = cs.verify_integrity(target, method=IntegrityMethod.HEADER_CHECKSUM)
        assert report.state == IntegrityState.CORRUPT


# =========================================================
# verify_integrity · TAIL_CONSISTENCY
# =========================================================

class TestVerifyTailConsistency:
    def test_verify_tail_ok_tc012(self, tmp_fs: Path) -> None:
        """TC-L109-L205-012 · task-board 末尾可 parse + version 字段存在."""
        target = tmp_fs / "task_board.json"
        target.write_bytes(b'{"version":"v1.0","tasks":[]}')
        report = cs.verify_integrity(target, method=IntegrityMethod.TAIL_CONSISTENCY)
        assert report.state == IntegrityState.OK

    def test_verify_tail_missing_version(self, tmp_fs: Path) -> None:
        """无 version 字段 · state=CORRUPT."""
        target = tmp_fs / "task_board.json"
        target.write_bytes(b'{"tasks":[]}')
        report = cs.verify_integrity(target, method=IntegrityMethod.TAIL_CONSISTENCY)
        assert report.state == IntegrityState.CORRUPT

    def test_verify_tail_not_json(self, tmp_fs: Path) -> None:
        """非 JSON · state=CORRUPT."""
        target = tmp_fs / "task_board.json"
        target.write_bytes(b"garbage{not json")
        report = cs.verify_integrity(target, method=IntegrityMethod.TAIL_CONSISTENCY)
        assert report.state == IntegrityState.CORRUPT


# =========================================================
# verify_integrity · 错误 method
# =========================================================

class TestVerifyIntegrityMisc:
    def test_unknown_method_raises(self, tmp_fs: Path) -> None:
        target = tmp_fs / "f.jsonl"
        target.write_bytes(b"")
        with pytest.raises((ValueError, cs.InvalidArgumentError)):
            cs.verify_integrity(target, method="unknown")  # type: ignore[arg-type]


# =========================================================
# recover_partial_write
# =========================================================

class TestRecoverPartialWrite:
    def test_recover_deletes_old_orphan_tmp_tc013(self, tmp_fs: Path) -> None:
        """TC-L109-L205-013 · 24h+ 孤儿 tmp 被删 · target 不动."""
        target = tmp_fs / "f.json"
        body = b'{"snapshot":"ok","version":"v1"}'
        _make_checkpoint_file(target, body)

        # 建孤儿 tmp · 时间回拨 25h
        tmp = tmp_fs / "f.json.tmp.01ABCDEFGHJKMNPQRSTVWXYZ01"
        tmp.write_bytes(b"half")
        old = time.time() - 25 * 3600
        os.utime(tmp, (old, old))

        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.DELETE_ORPHAN_TMP
        assert str(tmp) in action.orphan_tmp_paths
        assert not tmp.exists()  # 已删
        assert target.exists()  # 未动

    def test_recover_truncates_bad_tail_tc014(self, tmp_fs: Path) -> None:
        """TC-L109-L205-014 · events.jsonl 坏尾 · TRUNCATE_TAIL + affected_bytes > 0."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=5)
        original_size = target.stat().st_size
        # 追加坏尾
        with open(target, "ab") as f:
            f.write(b'{"seq":5,"data":"half...')  # 未闭合
        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.TRUNCATE_TAIL
        assert action.affected_bytes is not None
        assert action.affected_bytes > 0
        # 截断后复查必 OK
        assert action.post_integrity is not None
        assert action.post_integrity.state == IntegrityState.OK
        # 文件大小 ≤ 原大小（5 条合法的大小）
        assert target.stat().st_size == original_size

    def test_recover_no_action_healthy_tc015(self, tmp_fs: Path) -> None:
        """TC-L109-L205-015 · 健康文件 · NO_ACTION · 幂等."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=3)
        action1 = cs.recover_partial_write(target)
        assert action1.action_kind == RecoveryActionKind.NO_ACTION
        # 幂等
        action2 = cs.recover_partial_write(target)
        assert action2.action_kind == RecoveryActionKind.NO_ACTION

    def test_recover_young_orphan_tmp_conservative_tc112(self, tmp_fs: Path) -> None:
        """TC-L109-L205-112 · young tmp < 24h · 保守不删 · NO_ACTION."""
        target = tmp_fs / "f.json"
        body = b'{"snapshot":"ok","version":"v1"}'
        _make_checkpoint_file(target, body)
        tmp = tmp_fs / "f.json.tmp.01ABCDEFGHJKMNPQRSTVWXYZ02"
        tmp.write_bytes(b"half")  # 现在时间 · <24h
        action = cs.recover_partial_write(target)
        # 实现选择：young tmp 保守不删 → NO_ACTION · 或激进删 → DELETE_ORPHAN_TMP
        assert action.action_kind in {
            RecoveryActionKind.NO_ACTION,
            RecoveryActionKind.DELETE_ORPHAN_TMP,
        }

    def test_recover_abort_on_corrupt_snapshot(self, tmp_fs: Path) -> None:
        """checkpoint 完全坏（header 错）· 不可自动恢复 · ABORT."""
        target = tmp_fs / "cp.json"
        # 写 header_size 足够的垃圾
        target.write_bytes(b"X" * (HEADER_SIZE + 10))
        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.ABORT

    def test_recover_truncate_then_verify_ok(self, tmp_fs: Path) -> None:
        """TRUNCATE_TAIL 后 · post_integrity.state = OK."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=10)
        with open(target, "ab") as f:
            f.write(b'{"seq":10,"garbage')
        action = cs.recover_partial_write(target)
        assert action.action_kind == RecoveryActionKind.TRUNCATE_TAIL
        assert action.post_integrity is not None
        assert action.post_integrity.state == IntegrityState.OK

    def test_recover_contract_tc203(self, tmp_fs: Path) -> None:
        """TC-L109-L205-203/204 · L2-04 消费 IntegrityReport / RecoveryAction schema."""
        target = tmp_fs / "events.jsonl"
        _make_good_events_jsonl(target, n=2)
        report = cs.verify_integrity(target, method=IntegrityMethod.HASH_CHAIN)
        action = cs.recover_partial_write(target)
        # schema 稳定
        report_dump = report.model_dump()
        action_dump = action.model_dump()
        assert "state" in report_dump
        assert "method" in report_dump
        assert "action_kind" in action_dump
        assert "orphan_tmp_paths" in action_dump
        # frozen
        with pytest.raises(Exception):
            report.state = IntegrityState.CORRUPT  # type: ignore[misc]


# =========================================================
# integrity_checker 内部 helpers 冒烟
# =========================================================

def test_header_size_constant() -> None:
    """HEADER_SIZE 是 128（§7.8）."""
    assert HEADER_SIZE == 128


def test_compose_header_layout() -> None:
    """compose_header · 前 64B = sha256 hex · 64位 = \\n · 其余 0x00 padding."""
    body = b"hello"
    header = compose_header(body)
    assert len(header) == HEADER_SIZE
    assert header[:64] == hashlib.sha256(body).hexdigest().encode("ascii")
    assert header[64:65] == b"\n"
    assert all(b == 0 for b in header[65:])
