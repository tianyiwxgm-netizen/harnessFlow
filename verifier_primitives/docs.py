"""Docs primitives: cross_refs_all_resolvable."""

import re
from pathlib import Path


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def cross_refs_all_resolvable(doc_path: str) -> tuple[bool, dict]:
    p = Path(doc_path)
    if not p.is_file():
        return False, {"doc_path": doc_path, "error": "not_a_file"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return False, {"doc_path": doc_path, "error": f"read_failed: {exc}"}

    base = p.parent
    missing: list[dict] = []
    checked = 0
    for m in _MD_LINK_RE.finditer(text):
        target = m.group(2).split("#", 1)[0].split(" ", 1)[0].strip()
        if not target:
            continue
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        checked += 1
        candidate = (base / target).resolve()
        if not candidate.exists():
            missing.append({"link_text": m.group(1), "target": target})
            if len(missing) > 20:
                break
    ok = len(missing) == 0
    return ok, {"doc_path": doc_path, "checked": checked, "missing_count": len(missing), "missing_sample": missing[:10]}
