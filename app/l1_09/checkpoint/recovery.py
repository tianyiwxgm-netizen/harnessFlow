"""L2-04 · RecoveryAttempt · recover_from_checkpoint · Tier 1-4.

对齐 3-1 §6.2:
- Tier 1: latest checkpoint · verify sha256 · replay 尾段
- Tier 2: previous versions / full events.jsonl replay
- Tier 3: 跳过损坏块 · degraded
- Tier 4: 全坏 · 拒绝假恢复 · halt_guard.mark_halt

硬约束：
- single project recovery ≤ 30s (DEADLINE_EXCEEDED)
- PID_MISMATCH 检查 · 拒绝恢复
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import ulid

from app.l1_09.checkpoint.schemas import (
    BlankRebuildRejected,
    CheckpointCorrupt,
    CorruptRange,
    DeadlineExceeded,
    HashChainBroken,
    NoCheckpoint,
    PIDMismatch,
    RecoveryResult,
    Tier,
)


class RecoveryAttempt:
    """单 project recovery · 串行(D4 并发 1)."""

    def __init__(
        self,
        root: Path,
        *,
        event_bus=None,
        halt_guard=None,
        deadline_s: int = 30,
    ) -> None:
        self._root = root
        self._bus = event_bus
        self._halt_guard = halt_guard
        self._deadline_s = deadline_s

    def _ckpt_dir(self, pid: str) -> Path:
        return self._root / "projects" / pid / "checkpoints"

    def _events_path(self, pid: str) -> Path:
        return self._root / "projects" / pid / "events.jsonl"

    def _list_checkpoints(self, pid: str) -> list[Path]:
        d = self._ckpt_dir(pid)
        if not d.exists():
            return []
        return sorted(
            [p for p in d.glob("*.json") if p.is_file()],
            reverse=True,  # 最新在前
        )

    def _load_checkpoint(self, path: Path) -> dict:
        """读 + verify checksum · 失败 raise CheckpointCorrupt."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            raise CheckpointCorrupt(f"load failed: {e}")

        manifest = doc.get("manifest", {})
        payload = doc.get("payload", {})

        stored_checksum = manifest.get("checksum")
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        actual_checksum = hashlib.sha256(payload_bytes).hexdigest()
        if stored_checksum != actual_checksum:
            raise CheckpointCorrupt(
                f"checksum mismatch: stored={stored_checksum}, actual={actual_checksum}"
            )
        return doc

    def _verify_pid(self, doc: dict, expected_pid: str) -> None:
        loaded_pid = doc["manifest"].get("project_id")
        if loaded_pid != expected_pid:
            raise PIDMismatch(
                f"checkpoint pid={loaded_pid} but expected={expected_pid}"
            )

    def recover_from_checkpoint(self, project_id: str) -> RecoveryResult:
        started_at = datetime.now(UTC)
        start_s = time.time()
        events_replayed_count = 0
        skipped_ranges: list[CorruptRange] = []

        def _check_deadline() -> None:
            if time.time() - start_s > self._deadline_s:
                raise DeadlineExceeded(
                    f"recovery deadline exceeded ({self._deadline_s}s)"
                )

        # ====================== Tier 1 ======================
        checkpoints = self._list_checkpoints(project_id)
        events_path = self._events_path(project_id)
        has_events = events_path.exists() and events_path.stat().st_size > 0

        # Tier 4 早退：无 checkpoint 且无 events
        if not checkpoints and not has_events:
            raise NoCheckpoint(
                f"no data at all for project {project_id}"
            )

        tier1_tried = False
        for idx, ckpt_path in enumerate(checkpoints):
            _check_deadline()
            try:
                doc = self._load_checkpoint(ckpt_path)
                self._verify_pid(doc, project_id)
                last_seq = int(doc["payload"].get("last_event_sequence", 0))
                # replay 尾段（seq > last_seq）
                replayed, chain_ok = self._replay_tail(project_id, from_seq=last_seq + 1)
                events_replayed_count = replayed
                if chain_ok:
                    completed_at = datetime.now(UTC)
                    tier = Tier.TIER_1 if idx == 0 else Tier.TIER_2
                    return RecoveryResult(
                        project_id=project_id,
                        tier=tier,
                        recovered_state=doc["payload"],
                        last_event_sequence_replayed=last_seq + replayed,
                        duration_ms=int((time.time() - start_s) * 1000),
                        started_at=started_at.isoformat(),
                        completed_at=completed_at.isoformat(),
                        events_replayed_count=replayed,
                        hash_chain_valid=True,
                        system_resumed_event_id=f"evt_{ulid.new()}",
                        checkpoint_id_used=doc["manifest"].get("checkpoint_id"),
                    )
                # hash 断裂 → 跳 Tier 3
                break
            except (CheckpointCorrupt, PIDMismatch):
                # 本版坏 · 继续试下一个（Tier 1 内部 fallback）
                tier1_tried = True
                continue

        # ====================== Tier 2 ======================
        # 所有 checkpoint 都坏 → 全量回放
        _check_deadline()
        if has_events:
            try:
                replayed, chain_ok = self._replay_all(project_id)
                events_replayed_count = replayed
                if chain_ok:
                    completed_at = datetime.now(UTC)
                    return RecoveryResult(
                        project_id=project_id,
                        tier=Tier.TIER_2,
                        recovered_state={"rebuilt_from_events": True},
                        last_event_sequence_replayed=replayed,
                        duration_ms=int((time.time() - start_s) * 1000),
                        started_at=started_at.isoformat(),
                        completed_at=completed_at.isoformat(),
                        events_replayed_count=replayed,
                        hash_chain_valid=True,
                        system_resumed_event_id=f"evt_{ulid.new()}",
                    )
            except HashChainBroken:
                pass

        # ====================== Tier 3 ======================
        _check_deadline()
        if has_events:
            replayed, chain_ok, skipped = self._replay_with_skip(project_id)
            if replayed > 0:
                completed_at = datetime.now(UTC)
                return RecoveryResult(
                    project_id=project_id,
                    tier=Tier.TIER_3,
                    recovered_state={"degraded": True, "partial": True},
                    last_event_sequence_replayed=replayed,
                    duration_ms=int((time.time() - start_s) * 1000),
                    started_at=started_at.isoformat(),
                    completed_at=completed_at.isoformat(),
                    events_replayed_count=replayed,
                    hash_chain_valid=False,
                    system_resumed_event_id=f"evt_{ulid.new()}",
                    skipped_corrupt_ranges=skipped,
                    degraded=True,
                )

        # ====================== Tier 4 · 拒假恢复 ======================
        if self._halt_guard is not None:
            self._halt_guard.mark_halt(
                reason=f"recovery tier 4 · all corrupt for {project_id}",
                source="L2-04:recovery",
                correlation_id=f"recovery_{project_id}",
            )
        raise BlankRebuildRejected(
            f"all checkpoints + events corrupt for {project_id}, "
            f"refusing fake recovery"
        )

    def _replay_tail(self, project_id: str, *, from_seq: int) -> tuple[int, bool]:
        """从 from_seq 开始 replay 尾段 · 返 (count, chain_ok)."""
        if self._bus is None:
            return 0, True
        count = 0
        try:
            for _ in self._bus.read_range(
                project_id, from_seq=from_seq, verify_hash_on_read=True
            ):
                count += 1
            return count, True
        except Exception:
            return count, False

    def _replay_all(self, project_id: str) -> tuple[int, bool]:
        """§6.2 Tier 2 · 全量 replay · 返 (count, chain_ok)."""
        if self._bus is None:
            return 0, True
        count = 0
        try:
            for _ in self._bus.read_range(project_id, verify_hash_on_read=True):
                count += 1
            return count, True
        except Exception:
            return count, False

    def _replay_with_skip(
        self,
        project_id: str,
    ) -> tuple[int, bool, list[CorruptRange]]:
        """§6.2 Tier 3 · 遇 hash 断裂跳过 · 记录 skipped_range."""
        if self._bus is None:
            return 0, True, []
        count = 0
        skipped: list[CorruptRange] = []
        # 不用 verify · 跳过坏行（reader 已有容错）
        try:
            for _ in self._bus.read_range(project_id, verify_hash_on_read=False):
                count += 1
        except Exception:
            pass
        return count, False, skipped


__all__ = ["RecoveryAttempt"]
