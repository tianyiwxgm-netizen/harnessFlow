"""Filesystem primitives: file_exists / dir_exists / wc_lines / grep_count / retro_exists."""

import os
import re
from pathlib import Path


def file_exists(path: str):
    p = Path(path)
    ok = p.is_file()
    ev = {"path": str(p), "exists": ok}
    if ok:
        stat = p.stat()
        ev["size_bytes"] = stat.st_size
        ev["mtime_epoch"] = int(stat.st_mtime)
    return ok, ev


def dir_exists(path: str):
    p = Path(path)
    ok = p.is_dir()
    return ok, {"path": str(p), "is_dir": ok}


def wc_lines(path: str):
    p = Path(path)
    if not p.is_file():
        return -1, {"path": str(p), "error": "not_a_file"}
    try:
        count = sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
    except OSError as exc:
        return -1, {"path": str(p), "error": f"read_failed: {exc}"}
    return count, {"path": str(p), "lines": count}


def grep_count(pattern: str, path: str):
    p = Path(path)
    if not p.is_file():
        return -1, {"path": str(p), "pattern": pattern, "error": "not_a_file"}
    try:
        compiled = re.compile(pattern, re.MULTILINE)
    except re.error as exc:
        return -1, {"pattern": pattern, "error": f"invalid_regex: {exc}"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return -1, {"path": str(p), "error": f"read_failed: {exc}"}
    matches = compiled.findall(text)
    return len(matches), {"path": str(p), "pattern": pattern, "count": len(matches)}


def retro_exists(path: str):
    p = Path(path)
    ok = p.is_file() and p.stat().st_size > 0
    return ok, {"path": str(p), "nonempty": ok}
