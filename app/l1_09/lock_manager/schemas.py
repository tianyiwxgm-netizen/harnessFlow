"""L2-02 锁管理器 · schemas · 对齐 3-1 §7.

LeaseToken / Lock / LockError / ResourceName.
"""
from __future__ import annotations

import dataclasses
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ===================== 常量 / 白名单 =====================

LOCK_WAIT_TIMEOUT_MS_MAX = 5000
JANITOR_SCAN_INTERVAL_SEC = 5.0
TTL_GRACE_MS = 500  # janitor 额外宽限

# 资源类型白名单（除 _index 外，都需 <pid>: 前缀）
ALLOWED_RESOURCE_TYPES: frozenset[str] = frozenset({
    "event_bus",
    "task_board",
    "state",
    "manifest",
    "checkpoint_window",
    "kb",
})

# 资源类型默认 TTL（毫秒）· 对齐 3-1 §7.1
DEFAULT_TTL_MS: dict[str, int] = {
    "_index": 1000,
    "event_bus": 500,
    "task_board": 5000,
    "state": 5000,
    "manifest": 2000,
    "checkpoint_window": 20000,
    "kb": 10000,
    "wp": 600_000,  # 10 分钟
}

# 正则：资源名 · `^(_index|[a-z0-9_-]+:[a-z0-9_-]+(-[a-z0-9]+)?)$`
_RESOURCE_PATTERN = re.compile(
    r"^(_index|[a-z0-9_-]+:[a-z0-9_]+(?:-[a-z0-9]+)?)$"
)

# holder 格式：`<L-id>:<subcomponent>[:<context>]`
_HOLDER_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]+:[A-Za-z0-9_-]+(?::[A-Za-z0-9_.:-]+)?$"
)


# ===================== 资源名解析 =====================

@dataclass(frozen=True)
class ResourceName:
    """资源名 VO · 对齐 3-1 §7.1."""

    project_id: str | None
    resource_type: str
    sub_id: str | None

    @classmethod
    def parse(cls, raw: str) -> "ResourceName":
        """解析资源名 · 不合法 raise ValueError."""
        if not _RESOURCE_PATTERN.match(raw):
            raise ValueError(f"invalid_resource: {raw!r}")
        if raw == "_index":
            return cls(None, "_index", None)
        # `<pid>:<type>[-<sub_id>]`
        pid, rest = raw.split(":", 1)
        if "-" in rest:
            rtype, sub = rest.split("-", 1)
        else:
            rtype, sub = rest, None
        # 只允许 wp-<wp_id>（带 - 的）
        if sub is not None and rtype != "wp":
            # 例如 `foo:task_board-xxx` · 非 wp 类型有 sub · 不合法
            raise ValueError(f"invalid_resource: {raw!r} (only wp-<id> allows sub_id)")
        return cls(project_id=pid, resource_type=rtype, sub_id=sub)

    def to_lock_path(self, workdir: Path) -> Path:
        """返回物理 .lock 文件路径."""
        if self.resource_type == "_index":
            return workdir / "tmp" / ".index.lock"
        sub = f"-{self.sub_id}" if self.sub_id else ""
        return (
            workdir
            / "projects"
            / self.project_id
            / "tmp"
            / f".{self.resource_type}{sub}.lock"
        )

    @property
    def ttl_ms(self) -> int:
        """按 resource_type 查默认 TTL."""
        if self.resource_type == "wp":
            return DEFAULT_TTL_MS["wp"]
        return DEFAULT_TTL_MS.get(self.resource_type, 5000)


def is_valid_resource(raw: str) -> bool:
    """返回 True 若资源名合法（不检查白名单 · 只检查语法）."""
    try:
        ResourceName.parse(raw)
        return True
    except ValueError:
        return False


def is_valid_holder(raw: str) -> bool:
    if not raw or not isinstance(raw, str):
        return False
    return bool(_HOLDER_PATTERN.match(raw))


# ===================== LeaseToken =====================

# 进程级 secret · 防跨进程伪造
_PROCESS_SECRET = secrets.token_bytes(32)


def _sign(token_id: str, holder: str, issued_at: int) -> str:
    import hmac
    import hashlib

    msg = f"{token_id}:{holder}:{issued_at}".encode()
    return hmac.new(_PROCESS_SECRET, msg, hashlib.sha256).hexdigest()[:16]


@dataclass(frozen=True)
class LeaseToken:
    """Lease token · 对齐 3-1 §7.2."""

    token_id: str
    lock_id: str
    resource: str
    holder: str
    issued_at: int
    expires_at: int
    holder_sig: str

    @classmethod
    def create(
        cls,
        *,
        token_id: str,
        lock_id: str,
        resource: str,
        holder: str,
        issued_at: int,
        ttl_ms: int,
    ) -> "LeaseToken":
        sig = _sign(token_id, holder, issued_at)
        return cls(
            token_id=token_id,
            lock_id=lock_id,
            resource=resource,
            holder=holder,
            issued_at=issued_at,
            expires_at=issued_at + ttl_ms,
            holder_sig=sig,
        )

    def verify_sig(self) -> bool:
        return self.holder_sig == _sign(self.token_id, self.holder, self.issued_at)

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), sort_keys=True)


# ===================== LockState / Lock =====================

class LockState(str, Enum):
    FREE = "free"
    HELD = "held"
    RELEASING = "releasing"
    CRASHED_CLEANUP = "crashed"


@dataclass
class Lock:
    """Lock Entity · 进程内内存态."""

    lock_id: str
    resource: str
    holder: str
    acquired_at: int  # ms
    ttl_ms: int
    state: LockState
    fd: int | None  # flock 句柄
    token: LeaseToken

    @property
    def is_expired(self) -> bool:
        return int(time.time() * 1000) - self.acquired_at > self.ttl_ms


@dataclass(frozen=True)
class LockStatus:
    """只读 snapshot · list_held / is_locked 返回."""

    resource: str
    holder: str
    acquired_at: int
    hold_duration_ms: int
    ttl_ms: int
    waiters_count: int
    waiters_oldest_wait_ms: int


@dataclass(frozen=True)
class ReleaseAck:
    released_at: int
    hold_duration_ms: int
    waiters_signaled: int
    idempotent: bool = False


# ===================== 错误码 =====================

class LockError(Exception):
    """L2-02 基类."""

    error_code: str = "unknown"

    def __init__(self, message: str = "", **context: object) -> None:
        super().__init__(message)
        self.context = dict(context)


class LockTimeout(LockError):
    error_code = "timeout"


class LockDeadlockRejected(LockError):
    error_code = "deadlock_rejected"


class LockShutdownRejected(LockError):
    error_code = "shutdown_rejected"


class LockInvalidResource(LockError):
    error_code = "invalid_resource"


class LockInvalidHolder(LockError):
    error_code = "invalid_holder"


class LockInvalidToken(LockError):
    error_code = "invalid_token"


class LockLeaked(LockError):
    error_code = "lock_leaked"


class LockAccessDenied(LockError):
    """force_release_all 非授权调用方."""

    error_code = "access_denied"


__all__ = [
    "LOCK_WAIT_TIMEOUT_MS_MAX",
    "JANITOR_SCAN_INTERVAL_SEC",
    "TTL_GRACE_MS",
    "ALLOWED_RESOURCE_TYPES",
    "DEFAULT_TTL_MS",
    "ResourceName",
    "is_valid_resource",
    "is_valid_holder",
    "LeaseToken",
    "LockState",
    "Lock",
    "LockStatus",
    "ReleaseAck",
    "LockError",
    "LockTimeout",
    "LockDeadlockRejected",
    "LockShutdownRejected",
    "LockInvalidResource",
    "LockInvalidHolder",
    "LockInvalidToken",
    "LockLeaked",
    "LockAccessDenied",
]
