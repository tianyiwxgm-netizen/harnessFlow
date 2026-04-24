"""L2-01 · read_range · IC-L2-04 只读 iterator · 对齐 3-1 §3.4 / §6.4.

特性：
- 流式 · 逐行读 · 不 buffer 整个文件到内存（10 万 event < 50 MB）
- from_seq / to_seq 闭区间
- verify_hash_on_read 可选 · 启用则断裂时 raise ReadHashBrokenError
- include_meta 可过滤 is_meta=True 的行

限制（§3.6 稳定性承诺的最小集）：
- 返回 dict（jsonl body）· 不反序列化为 Event（减少 pydantic 开销）
- 每个文件独立打开 · 不共享 file handle
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from app.l1_09.crash_safety.hash_chain import GENESIS_HASH, compute_hash_chain_link
from app.l1_09.event_bus.schemas import (
    BusHashChainBroken,
    BusProjectNotRegistered,
)


class ReadHashBrokenError(BusHashChainBroken):
    """verify_hash_on_read 命中断裂 · 含 seq."""

    def __init__(self, *, seq: int, reason: str) -> None:
        super().__init__(f"hash chain broken at seq={seq}: {reason}")
        self.seq = seq


def read_range(
    events_path: Path,
    *,
    from_seq: int = 0,
    to_seq: int | None = None,
    include_meta: bool = True,
    verify_hash_on_read: bool = False,
    project_dir: Path | None = None,
) -> Iterator[dict]:
    """流式读 events.jsonl 的 [from_seq, to_seq] 闭区间.

    Args:
        events_path: 目标文件路径（通常 `projects/<pid>/events.jsonl`）
        from_seq: 起始 sequence（含）· 默认 0
        to_seq: 结束 sequence（含）· None = 读到文件尾
        include_meta: False 过滤 is_meta=True 行
        verify_hash_on_read: True 逐行验 hash chain · 断则 raise
        project_dir: 可选 · project 目录（用于 E-2 fix · 区分"未注册"vs"空"）

    Yields:
        dict · jsonl 每行的 body

    Raises:
        BusProjectNotRegistered · project 目录不存在（未注册）
        ReadHashBrokenError · 启用 verify 时 hash 断裂

    Notes:
        E-2 fix: events_path 不存在但 project_dir 存在 · 返回空迭代器（空 project）
        events_path 和 project_dir 都不存在 · raise BusProjectNotRegistered（未注册）
    """
    if not events_path.exists():
        # E-2 fix: 区分"未注册"（dir 不存在）vs"空"（dir 在 · events 未生成）
        if project_dir is not None and project_dir.exists():
            # 空 project · 返空 iterator（不 raise）
            return
        raise BusProjectNotRegistered(f"events file not found: {events_path}")

    assert from_seq >= 0, "from_seq must be ≥ 0"
    if to_seq is not None:
        assert to_seq >= from_seq, "to_seq must be ≥ from_seq"

    prev_hash = GENESIS_HASH
    with open(events_path, "rb") as f:
        for raw_line in f:
            if not raw_line.strip():
                continue
            try:
                body = json.loads(raw_line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                if verify_hash_on_read:
                    raise ReadHashBrokenError(
                        seq=-1, reason=f"jsonl parse failed: {e}"
                    ) from e
                # 不验证模式下 · 跳过坏行（防御 · 正常不发生）
                continue

            seq = int(body.get("sequence", -1))

            # verify hash 必须在 filter 之前 · 保证链完整性
            if verify_hash_on_read:
                body_for_hash = {k: v for k, v in body.items() if k != "hash"}
                link = compute_hash_chain_link(prev_hash, body_for_hash)
                if link.curr_hash != body.get("hash"):
                    raise ReadHashBrokenError(
                        seq=seq, reason=f"hash mismatch at seq={seq}"
                    )
                prev_hash = link.curr_hash

            # filter
            if seq < from_seq:
                continue
            if to_seq is not None and seq > to_seq:
                break
            if not include_meta and body.get("is_meta", False):
                continue

            yield body


__all__ = [
    "read_range",
    "ReadHashBrokenError",
]
