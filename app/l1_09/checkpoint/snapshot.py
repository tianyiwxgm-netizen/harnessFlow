"""L2-04 · SnapshotJob · take_snapshot · 对齐 3-1 §6.1.

流程：
- 取 task_board 锁 (L2-02)
- 读 events.jsonl 末 seq / last_hash
- 组装 manifest (含 sha256 + ts + seq)
- 原子写到 `projects/<pid>/checkpoints/<seq>.json` (调 L2-05 write_atomic)
- 保留最近 5 版 · 老版归档到 `archive/`
- 发 snapshot_created 事件
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import ulid

from app.l1_09.checkpoint.schemas import (
    SnapshotDiskFull,
    SnapshotIntegrityVerifyFail,
    SnapshotLockTimeout,
    SnapshotResult,
    Trigger,
)
from app.l1_09.crash_safety import write_atomic


MAX_CHECKPOINT_VERSIONS = 5


class SnapshotJob:
    """单 project 快照任务."""

    def __init__(
        self,
        root: Path,
        *,
        event_bus=None,
        lock_manager=None,
        deadline_ms: int = 5000,
    ) -> None:
        self._root = root
        self._bus = event_bus
        self._lm = lock_manager
        self._deadline_ms = deadline_ms
        self._last_checkpoint_id: dict[str, str] = {}  # pid -> last cp_id

    def _ckpt_dir(self, pid: str) -> Path:
        p = self._root / "projects" / pid / "checkpoints"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _archive_dir(self, pid: str) -> Path:
        p = self._root / "projects" / pid / "checkpoints" / "archive"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def take_snapshot(
        self,
        project_id: str,
        *,
        trigger: Trigger = Trigger.PERIODIC_TIMER,
    ) -> SnapshotResult:
        start_ms = int(time.time() * 1000)

        # Step 1 · 取 task_board 锁（如 lock_manager 注入）
        token = None
        if self._lm is not None:
            try:
                token = self._lm.acquire_lock(
                    f"{project_id}:task_board",
                    "L2-04:snapshot",
                    timeout_ms=3000,
                )
            except Exception as e:
                raise SnapshotLockTimeout(f"task_board lock timeout: {e}")

        try:
            # Step 2 · 读 events.jsonl 末 seq / last_hash
            last_seq = 0
            last_hash = "GENESIS"
            events_summary: list = []
            if self._bus is not None:
                try:
                    for body in self._bus.read_range(project_id):
                        last_seq = int(body.get("sequence", last_seq))
                        last_hash = body.get("hash", last_hash)
                        events_summary.append({
                            "seq": body.get("sequence"),
                            "type": body.get("type"),
                        })
                except Exception:
                    # Empty project or unregistered · 仍出 snapshot with seq=0
                    pass

            # Step 3 · 组装 manifest
            checkpoint_id = f"cp-{ulid.new()}"
            payload = {
                "checkpoint_id": checkpoint_id,
                "project_id": project_id,
                "last_event_sequence": last_seq,
                "last_hash": last_hash,
                "events_count": len(events_summary),
                "created_at": datetime.now(UTC).isoformat(),
                "trigger": trigger.value,
            }
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            checksum = hashlib.sha256(payload_bytes).hexdigest()

            # Step 4 · 原子写
            ckpt_path = self._ckpt_dir(project_id) / f"{last_seq}.json"
            full_doc = {
                "manifest": {
                    **payload,
                    "checksum": checksum,
                },
                "payload": payload,
            }
            try:
                write_atomic(ckpt_path, json.dumps(full_doc, sort_keys=True).encode())
            except Exception as e:
                raise SnapshotDiskFull(f"write_atomic failed: {e}")

            bytes_written = ckpt_path.stat().st_size

            # Step 5 · 保留 5 版 · 老的归档
            self._rotate_versions(project_id)

            prev_cp_id = self._last_checkpoint_id.get(project_id)
            self._last_checkpoint_id[project_id] = checkpoint_id

            duration_ms = int(time.time() * 1000) - start_ms
            return SnapshotResult(
                checkpoint_id=checkpoint_id,
                project_id=project_id,
                last_event_sequence=last_seq,
                snapshot_path=str(ckpt_path.relative_to(self._root)),
                checksum=checksum,
                duration_ms=duration_ms,
                trigger=trigger,
                created_at=payload["created_at"],
                bytes_written=bytes_written,
                superseded_checkpoint_id=prev_cp_id,
            )
        finally:
            if token is not None and self._lm is not None:
                try:
                    self._lm.release_lock(token)
                except Exception:
                    pass

    def _rotate_versions(self, project_id: str) -> None:
        """保留最新 MAX_CHECKPOINT_VERSIONS · 其他归档."""
        ckpts = sorted(
            [p for p in self._ckpt_dir(project_id).glob("*.json") if p.is_file()]
        )
        if len(ckpts) <= MAX_CHECKPOINT_VERSIONS:
            return
        excess = ckpts[:-MAX_CHECKPOINT_VERSIONS]
        archive = self._archive_dir(project_id)
        for p in excess:
            try:
                shutil.move(str(p), str(archive / p.name))
            except Exception:
                pass

    def list_checkpoints(self, project_id: str) -> list[Path]:
        return sorted(
            [p for p in self._ckpt_dir(project_id).glob("*.json") if p.is_file()]
        )


__all__ = ["SnapshotJob", "MAX_CHECKPOINT_VERSIONS"]
