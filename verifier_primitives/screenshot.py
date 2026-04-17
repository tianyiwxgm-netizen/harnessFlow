"""Screenshot primitive."""

from pathlib import Path


def screenshot_has_content(path: str, min_bytes: int = 2048) -> tuple[bool, dict]:
    p = Path(path)
    if not p.is_file():
        return False, {"path": str(p), "error": "not_a_file"}
    size = p.stat().st_size
    ok = size >= min_bytes
    return ok, {
        "path": str(p),
        "size_bytes": size,
        "min_bytes": min_bytes,
        "nonempty": ok,
    }
