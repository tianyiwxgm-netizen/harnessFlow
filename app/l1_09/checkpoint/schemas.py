"""L2-04 checkpoint + recovery · schemas · 对齐 3-1 §3.2."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Trigger(str, Enum):
    PERIODIC_TIMER = "periodic_timer"
    KEY_EVENT = "key_event"
    SHUTDOWN_FINAL = "shutdown_final"
    MANUAL_FORCE = "manual_force"


class Tier(int, Enum):
    TIER_1 = 1  # latest checkpoint OK
    TIER_2 = 2  # previous checkpoint / full events replay
    TIER_3 = 3  # 跳过损坏块 (degraded)
    TIER_4 = 4  # 拒绝假恢复 (RECOVERY_FAILED)


class ShutdownState(str, Enum):
    REQUESTED = "REQUESTED"
    DRAINING = "DRAINING"
    FLUSHING = "FLUSHING"
    ACKED = "ACKED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True)
class SnapshotResult:
    checkpoint_id: str
    project_id: str
    last_event_sequence: int
    snapshot_path: str
    checksum: str
    duration_ms: int
    trigger: Trigger
    created_at: str
    bytes_written: int = 0
    superseded_checkpoint_id: str | None = None


@dataclass(frozen=True)
class CorruptRange:
    from_seq: int
    to_seq: int
    reason: str


@dataclass(frozen=True)
class RecoveryResult:
    project_id: str
    tier: Tier
    recovered_state: dict[str, Any]
    last_event_sequence_replayed: int
    duration_ms: int
    started_at: str
    completed_at: str
    events_replayed_count: int
    hash_chain_valid: bool
    system_resumed_event_id: str
    checkpoint_id_used: str | None = None
    skipped_corrupt_ranges: list[CorruptRange] = field(default_factory=list)
    degraded: bool = False


@dataclass(frozen=True)
class ShutdownToken:
    token_id: str
    requested_at: str
    reason: str
    drain_deadline: str
    state: ShutdownState
    in_flight_event_count_at_request: int = 0
    final_checkpoint_id: str | None = None
    flush_duration_ms: int = 0
    projects_snapshotted: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayResult:
    project_id: str
    events_replayed: int
    hash_chain_valid: bool
    last_sequence_processed: int
    duration_ms: int
    rebuilt_state: dict[str, Any] = field(default_factory=dict)
    corrupt_at_sequence: int | None = None


# ================== 错误 ==================

class RecoveryError(Exception):
    error_code: str = "RECOVERY_E_UNKNOWN"


class CheckpointCorrupt(RecoveryError):
    error_code = "RECOVERY_E_CHECKPOINT_CORRUPT"


class HashChainBroken(RecoveryError):
    error_code = "RECOVERY_E_HASH_CHAIN_BROKEN"


class DeadlineExceeded(RecoveryError):
    error_code = "RECOVERY_E_DEADLINE_EXCEEDED"


class NoCheckpoint(RecoveryError):
    error_code = "RECOVERY_E_NO_CHECKPOINT"


class PIDMismatch(RecoveryError):
    error_code = "RECOVERY_E_PID_MISMATCH"


class BlankRebuildRejected(RecoveryError):
    error_code = "RECOVERY_E_BLANK_REBUILD_REJECTED"


class SnapshotError(Exception):
    error_code: str = "SNAPSHOT_E_UNKNOWN"


class SnapshotLockTimeout(SnapshotError):
    error_code = "SNAPSHOT_E_LOCK_TIMEOUT"


class SnapshotDiskFull(SnapshotError):
    error_code = "SNAPSHOT_E_DISK_FULL"


class SnapshotIntegrityVerifyFail(SnapshotError):
    error_code = "SNAPSHOT_E_INTEGRITY_VERIFY_FAIL"


class ShutdownError(Exception):
    error_code: str = "SHUTDOWN_E_UNKNOWN"


class ShutdownDrainTimeout(ShutdownError):
    error_code = "SHUTDOWN_E_DRAIN_TIMEOUT"


class ShutdownReentrant(ShutdownError):
    error_code = "SHUTDOWN_E_REENTRANT"


__all__ = [
    "Trigger",
    "Tier",
    "ShutdownState",
    "SnapshotResult",
    "RecoveryResult",
    "ShutdownToken",
    "ReplayResult",
    "CorruptRange",
    "RecoveryError",
    "CheckpointCorrupt",
    "HashChainBroken",
    "DeadlineExceeded",
    "NoCheckpoint",
    "PIDMismatch",
    "BlankRebuildRejected",
    "SnapshotError",
    "SnapshotLockTimeout",
    "SnapshotDiskFull",
    "SnapshotIntegrityVerifyFail",
    "ShutdownError",
    "ShutdownDrainTimeout",
    "ShutdownReentrant",
]
