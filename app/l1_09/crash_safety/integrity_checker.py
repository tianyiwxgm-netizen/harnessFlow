"""L2-05 · verify_integrity + recover_partial_write · 对齐 3-1 §3.4 / §3.5 / §6.4 / §6.5 / §7.8.

3 种校验方法（`IntegrityMethod`）：

- **HASH_CHAIN** · 逐行扫 jsonl · 验 prev_hash / curr_hash 链
- **HEADER_CHECKSUM** · 读前 128B header · 验 header.sha256 == sha256(body)
- **TAIL_CONSISTENCY** · 读最后一部分 · 验 JSON parse + `version` 字段存在

3 态（`IntegrityState`）：
- **OK** · 全链完整
- **PARTIAL** · 末尾部分损坏 · 可截断恢复 · `first_good_hash` 非 None
- **CORRUPT** · 无可用 prefix · 不可恢复

recover_partial_write 修复策略：
- 扫父目录孤儿 tmp（只删 ≥ TMP_ORPHAN_AGE_HOURS 的）
- jsonl PARTIAL → 截断到 `first_good_hash` 对应的 byte offset · fsync
- snapshot PARTIAL / CORRUPT → ABORT（L2-04 Tier 2/4 处理）
- OK → NO_ACTION
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from app.l1_09.crash_safety.canonical_json import canonical_json_without_hash
from app.l1_09.crash_safety.hash_chain import GENESIS_HASH, compute_hash_chain_link
from app.l1_09.crash_safety.schemas import (
    TMP_ORPHAN_AGE_HOURS,
    IntegrityMethod,
    IntegrityReport,
    IntegrityState,
    InvalidArgumentError,
    RecoveryAction,
    RecoveryActionKind,
)

HEADER_SIZE: int = 128  # §7.8 · 64B sha256 hex + \n + 0x00 padding · 128B 总头


def _make_report(
    *,
    target_path: Path | str,
    method: IntegrityMethod,
    state: IntegrityState,
    scan_duration_ms: float,
    total_items: int,
    failure_range: tuple[int, int] | None = None,
    first_bad_hash: str | None = None,
    first_good_hash: str | None = None,
    details: dict[str, Any] | None = None,
) -> IntegrityReport:
    """显式构造 IntegrityReport · 统一默认值（辅助 mypy · 避免 Field default 警告）."""
    return IntegrityReport(
        target_path=str(target_path),
        method=method,
        state=state,
        scan_duration_ms=scan_duration_ms,
        total_items=total_items,
        failure_range=failure_range,
        first_bad_hash=first_bad_hash,
        first_good_hash=first_good_hash,
        details=details or {},
    )


def compose_header(body: bytes) -> bytes:
    """§7.8 构造 HEADER_CHECKSUM 格式的 header（128 bytes · 0x00 padding）.

    layout:
        offset 0..63  · sha256(body) lowercase hex ASCII (64 bytes)
        offset 64     · '\\n' (1 byte)
        offset 65..127· 0x00 padding (63 bytes)
    """
    checksum_hex = hashlib.sha256(body).hexdigest().encode("ascii")
    assert len(checksum_hex) == 64
    header = bytearray(HEADER_SIZE)
    header[:64] = checksum_hex
    header[64] = ord("\n")
    # 65..HEADER_SIZE 保持 0x00（bytearray 默认值）
    return bytes(header)


# =========================================================
# HASH_CHAIN verify
# =========================================================

def _verify_hash_chain(target_path: Path) -> IntegrityReport:
    """§6.3.3 · 逐行扫 jsonl · 验 prev/curr hash chain."""
    start_ms = time.monotonic() * 1000.0
    prev_hash = GENESIS_HASH
    first_good_hash: str | None = None
    first_bad_seq: int | None = None
    first_bad_hash: str | None = None
    total_items = 0
    bytes_scanned = 0
    state = IntegrityState.OK

    if not target_path.exists() or target_path.stat().st_size == 0:
        scan_ms = time.monotonic() * 1000.0 - start_ms
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.HASH_CHAIN,
            state=IntegrityState.OK,
            scan_duration_ms=scan_ms,
            total_items=0,
            details={"bytes_scanned": 0},
        )

    with open(target_path, "rb") as f:
        for seq, raw_line in enumerate(f):
            bytes_scanned += len(raw_line)
            # parse
            try:
                body = json.loads(raw_line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                first_bad_seq = seq
                first_bad_hash = None
                state = (
                    IntegrityState.PARTIAL
                    if first_good_hash is not None
                    else IntegrityState.CORRUPT
                )
                break

            claimed_prev = body.get("prev_hash")
            claimed_hash = body.get("hash")
            if claimed_prev != prev_hash:
                first_bad_seq = seq
                first_bad_hash = claimed_hash if _is_hex64(claimed_hash) else None
                state = (
                    IntegrityState.PARTIAL
                    if first_good_hash is not None
                    else IntegrityState.CORRUPT
                )
                break
            # compute
            body_for_hash = {k: v for k, v in body.items() if k != "hash"}
            link = compute_hash_chain_link(prev_hash, body_for_hash)
            if link.curr_hash != claimed_hash:
                first_bad_seq = seq
                first_bad_hash = claimed_hash if _is_hex64(claimed_hash) else None
                state = (
                    IntegrityState.PARTIAL
                    if first_good_hash is not None
                    else IntegrityState.CORRUPT
                )
                break
            # 该行通过
            prev_hash = link.curr_hash
            first_good_hash = link.curr_hash
            total_items += 1

    scan_ms = time.monotonic() * 1000.0 - start_ms
    failure_range = (first_bad_seq, total_items) if first_bad_seq is not None else None
    return _make_report(
        target_path=str(target_path),
        method=IntegrityMethod.HASH_CHAIN,
        state=state,
        scan_duration_ms=scan_ms,
        total_items=total_items,
        failure_range=failure_range,
        first_bad_hash=first_bad_hash,
        first_good_hash=first_good_hash if state != IntegrityState.OK else None,
        details={"bytes_scanned": bytes_scanned},
    )


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


# =========================================================
# HEADER_CHECKSUM verify
# =========================================================

def _verify_header_checksum(target_path: Path) -> IntegrityReport:
    """§6.4 · 读 HEADER_SIZE header · 验 sha256(body) == header.checksum."""
    start_ms = time.monotonic() * 1000.0
    content = target_path.read_bytes()
    scan_ms_now = lambda: time.monotonic() * 1000.0 - start_ms  # noqa: E731

    if len(content) < HEADER_SIZE:
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.HEADER_CHECKSUM,
            state=IntegrityState.CORRUPT,
            scan_duration_ms=scan_ms_now(),
            total_items=len(content),
            failure_range=(0, len(content)),
            details={"reason": "file shorter than HEADER_SIZE"},
        )

    header = content[:HEADER_SIZE]
    body = content[HEADER_SIZE:]
    claimed = header[:64].decode("ascii", errors="replace")
    actual = hashlib.sha256(body).hexdigest()

    if not _is_hex64(claimed):
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.HEADER_CHECKSUM,
            state=IntegrityState.CORRUPT,
            scan_duration_ms=scan_ms_now(),
            total_items=len(body),
            failure_range=(0, 64),
            details={"reason": "header checksum not valid hex"},
        )

    if claimed != actual:
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.HEADER_CHECKSUM,
            state=IntegrityState.CORRUPT,
            scan_duration_ms=scan_ms_now(),
            total_items=len(body),
            failure_range=(HEADER_SIZE, len(content)),
            first_bad_hash=actual,
            details={"reason": "body hash mismatch", "claimed": claimed},
        )

    return _make_report(
        target_path=str(target_path),
        method=IntegrityMethod.HEADER_CHECKSUM,
        state=IntegrityState.OK,
        scan_duration_ms=scan_ms_now(),
        total_items=len(body),
        details={"body_hash": actual, "header_size": HEADER_SIZE},
    )


# =========================================================
# TAIL_CONSISTENCY verify
# =========================================================

def _verify_tail_consistency(target_path: Path) -> IntegrityReport:
    """§6.4 · task-board 专用 · 验 JSON parse + `version` 字段存在."""
    start_ms = time.monotonic() * 1000.0
    content = target_path.read_bytes()
    scan_ms_now = lambda: time.monotonic() * 1000.0 - start_ms  # noqa: E731

    try:
        obj = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.TAIL_CONSISTENCY,
            state=IntegrityState.CORRUPT,
            scan_duration_ms=scan_ms_now(),
            total_items=len(content),
            failure_range=(0, len(content)),
            details={"reason": f"JSON parse failed: {e}"},
        )

    if not isinstance(obj, dict) or "version" not in obj:
        return _make_report(
            target_path=str(target_path),
            method=IntegrityMethod.TAIL_CONSISTENCY,
            state=IntegrityState.CORRUPT,
            scan_duration_ms=scan_ms_now(),
            total_items=len(content),
            failure_range=(0, len(content)),
            details={"reason": "missing 'version' field"},
        )

    return _make_report(
        target_path=str(target_path),
        method=IntegrityMethod.TAIL_CONSISTENCY,
        state=IntegrityState.OK,
        scan_duration_ms=scan_ms_now(),
        total_items=len(content),
        details={"version": obj["version"]},
    )


# =========================================================
# verify_integrity · 总入口
# =========================================================

def verify_integrity(target_path: Path, *, method: IntegrityMethod) -> IntegrityReport:
    """§3.4 三态完整性校验 · 只读 · 无副作用.

    raises InvalidArgumentError if method not recognized.
    """
    if method == IntegrityMethod.HASH_CHAIN:
        return _verify_hash_chain(target_path)
    if method == IntegrityMethod.HEADER_CHECKSUM:
        return _verify_header_checksum(target_path)
    if method == IntegrityMethod.TAIL_CONSISTENCY:
        return _verify_tail_consistency(target_path)
    raise InvalidArgumentError(
        f"unknown IntegrityMethod: {method!r}", target=str(target_path)
    )


# =========================================================
# recover_partial_write
# =========================================================

def _infer_method_from_path(target_path: Path) -> IntegrityMethod:
    """§6.5 · 按路径推断 method（§7.7 白名单参考）.

    - *.jsonl → HASH_CHAIN
    - task_board.json → TAIL_CONSISTENCY
    - 其他 .json → HEADER_CHECKSUM
    """
    name = target_path.name
    if name.endswith(".jsonl"):
        return IntegrityMethod.HASH_CHAIN
    if name == "task_board.json":
        return IntegrityMethod.TAIL_CONSISTENCY
    return IntegrityMethod.HEADER_CHECKSUM


def _find_good_prefix_offset(target_path: Path, good_line_count: int) -> int:
    """返回前 `good_line_count` 行结束后的 byte offset（即 truncate 位置）."""
    if good_line_count == 0:
        return 0
    with open(target_path, "rb") as f:
        offset = 0
        for i, raw_line in enumerate(f):
            offset += len(raw_line)
            if i + 1 == good_line_count:
                return offset
    return offset  # 文件行数 < good_line_count · 返 EOF


def _truncate_jsonl(target_path: Path, good_offset: int) -> int:
    """truncate 到 good_offset · fsync · 返被截断字节数."""
    original_size = target_path.stat().st_size
    with open(target_path, "r+b") as f:
        f.truncate(good_offset)
        with contextlib.suppress(OSError):
            os.fsync(f.fileno())
    return original_size - good_offset


def _scan_orphan_tmps(target_path: Path) -> tuple[list[Path], list[Path]]:
    """扫父目录孤儿 tmp · 返 (all_tmps, old_tmps ≥ TMP_ORPHAN_AGE_HOURS)."""
    pattern = f"{target_path.name}.tmp.*"
    all_tmps = sorted(target_path.parent.glob(pattern))
    now = time.time()
    threshold_s = TMP_ORPHAN_AGE_HOURS * 3600
    old_tmps: list[Path] = []
    for tmp in all_tmps:
        try:
            mtime = tmp.stat().st_mtime
        except OSError:
            continue
        if now - mtime >= threshold_s:
            old_tmps.append(tmp)
    return all_tmps, old_tmps


def recover_partial_write(target_path: Path) -> RecoveryAction:
    """§3.5 / §6.5 · 检测 + 修复 target 及相关 tmp 的部分写问题.

    铁律：
        - 绝不 `target_path.unlink()`（不删原文件）
        - truncate 后必 fsync + 再 verify
        - orphan_tmp_paths + affected_bytes + rationale 必明写 · 供 L2-04 落审计
    """
    all_tmps, old_tmps = _scan_orphan_tmps(target_path)
    deleted_tmps: list[str] = []
    for tmp in old_tmps:
        try:
            tmp.unlink()
            deleted_tmps.append(str(tmp))
        except OSError:
            # best-effort · 跳过本 tmp · 记入 rationale
            pass

    # target 必须存在才能 verify · 若不存在 · 仅返回 tmp 清理结果
    if not target_path.exists():
        if deleted_tmps:
            return RecoveryAction(
                target_path=str(target_path),
                action_kind=RecoveryActionKind.DELETE_ORPHAN_TMP,
                affected_bytes=None,
                orphan_tmp_paths=deleted_tmps,
                rationale=f"target missing · cleaned {len(deleted_tmps)} orphan tmp(s) ≥ {TMP_ORPHAN_AGE_HOURS}h",
                post_integrity=None,
            )
        return RecoveryAction(
            target_path=str(target_path),
            action_kind=RecoveryActionKind.NO_ACTION,
            affected_bytes=None,
            orphan_tmp_paths=[],
            rationale="target missing · no orphan tmp · nothing to recover",
            post_integrity=None,
        )

    method = _infer_method_from_path(target_path)
    report = verify_integrity(target_path, method=method)

    # 健康
    if report.state == IntegrityState.OK:
        if deleted_tmps:
            return RecoveryAction(
                target_path=str(target_path),
                action_kind=RecoveryActionKind.DELETE_ORPHAN_TMP,
                affected_bytes=None,
                orphan_tmp_paths=deleted_tmps,
                rationale=f"target healthy · cleaned {len(deleted_tmps)} orphan tmp(s)",
                post_integrity=report,
            )
        young_note = "" if not all_tmps else f" · {len(all_tmps)} young tmp(s) kept (<{TMP_ORPHAN_AGE_HOURS}h)"
        return RecoveryAction(
            target_path=str(target_path),
            action_kind=RecoveryActionKind.NO_ACTION,
            affected_bytes=None,
            orphan_tmp_paths=[],
            rationale=f"target healthy · nothing to recover{young_note}",
            post_integrity=report,
        )

    # PARTIAL jsonl · 可截断
    if (
        report.state == IntegrityState.PARTIAL
        and method == IntegrityMethod.HASH_CHAIN
        and report.total_items > 0
    ):
        good_offset = _find_good_prefix_offset(target_path, report.total_items)
        affected = _truncate_jsonl(target_path, good_offset)
        post = verify_integrity(target_path, method=method)
        return RecoveryAction(
            target_path=str(target_path),
            action_kind=RecoveryActionKind.TRUNCATE_TAIL,
            affected_bytes=affected,
            orphan_tmp_paths=deleted_tmps,
            rationale=(
                f"truncated partial write at line={report.total_items} · "
                f"good_offset={good_offset} · post_state={post.state}"
            ),
            post_integrity=post,
        )

    # CORRUPT 或 snapshot PARTIAL · ABORT
    return RecoveryAction(
        target_path=str(target_path),
        action_kind=RecoveryActionKind.ABORT,
        affected_bytes=None,
        orphan_tmp_paths=deleted_tmps,
        rationale=f"state={report.state.value} · method={method.value} · cannot auto-recover",
        post_integrity=report,
    )


# 为测试保留的参考
__all__ = [
    "HEADER_SIZE",
    "compose_header",
    "verify_integrity",
    "recover_partial_write",
]
_ = canonical_json_without_hash  # 静默 import · 测试用
