"""Atomic file writer · tempfile + os.replace · returns sha256 hash of final bytes.

This is a LOCAL STUB standing in for Dev-α's L1-09 L2-05 atomic_write until the real
one ships. Same contract: either the final file contains the new bytes entirely or
nothing changes on disk.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path


def atomic_write_bytes(target: Path, data: bytes) -> str:
    """Write `data` to `target` atomically via tempfile + os.replace.

    Returns sha256 hex digest of `data`.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # tempfile in same dir so os.replace is same-filesystem atomic.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return hashlib.sha256(data).hexdigest()


def atomic_write_text(target: Path, text: str, encoding: str = "utf-8") -> str:
    return atomic_write_bytes(target, text.encode(encoding))
