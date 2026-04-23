"""L2-02 fallback · regex-level ASTTree when tree-sitter fails."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.multimodal.code_structure.schemas import ASTTree

_DEF_RE = re.compile(
    r"^(\s*)(?:class|def|function|fn|func|struct|type)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)


def coarse_parse(file_path: Path, lang: str) -> ASTTree:
    """Return an ASTTree with coarse=True via regex scan · safe fallback."""
    source = file_path.read_bytes()
    text = source.decode("utf-8", errors="ignore")
    match_count = sum(1 for _ in _DEF_RE.finditer(text))
    return ASTTree(
        lang=lang,
        file_path=str(file_path),
        file_hash=hashlib.sha256(source).hexdigest(),
        root_type="coarse_root",
        node_count=max(1, match_count * 2),
        loc=source.count(b"\n") + (1 if source and not source.endswith(b"\n") else 0),
        coarse=True,
    )
