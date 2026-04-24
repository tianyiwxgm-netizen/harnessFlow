"""L2-04 · replay_events · IC-10.

流式 replay · 用于 recovery 或 retro audit.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.l1_09.checkpoint.schemas import ReplayResult


def replay_events(
    event_bus,
    project_id: str,
    *,
    from_seq: int = 0,
    to_seq: int | None = None,
    callback: Callable[[dict], None] | None = None,
    verify_hash: bool = True,
) -> ReplayResult:
    """流式回放 · 对齐 IC-10 · 失败返 hash_chain_valid=False."""
    start_s = time.time()
    count = 0
    last_seq = from_seq - 1
    chain_ok = True
    corrupt_at = None

    try:
        for body in event_bus.read_range(
            project_id,
            from_seq=from_seq,
            to_seq=to_seq,
            verify_hash_on_read=verify_hash,
        ):
            count += 1
            last_seq = int(body.get("sequence", last_seq))
            if callback is not None:
                callback(body)
    except Exception as e:
        chain_ok = False
        corrupt_at = getattr(e, "seq", None) or last_seq + 1

    duration_ms = int((time.time() - start_s) * 1000)
    return ReplayResult(
        project_id=project_id,
        events_replayed=count,
        hash_chain_valid=chain_ok,
        last_sequence_processed=last_seq,
        duration_ms=duration_ms,
        corrupt_at_sequence=corrupt_at,
    )


__all__ = ["replay_events"]
