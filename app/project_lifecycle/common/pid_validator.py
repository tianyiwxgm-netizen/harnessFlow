"""PM-14 pid 格式校验 · ULID 26 char · Crockford base32。"""
from __future__ import annotations

import re

_ULID_REGEX = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def is_valid_pid(pid: str | None) -> bool:
    """ULID 格式硬校验 · 禁任意 UUID/随机字符串。"""
    if not pid:
        return False
    return bool(_ULID_REGEX.match(pid))


def ensure_pid(pid: str) -> str:
    """校验后返回 · 不合法 raise ValueError。"""
    if not is_valid_pid(pid):
        raise ValueError(f"invalid pid format (not ULID-26): {pid!r}")
    return pid
