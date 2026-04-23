"""L2-02 ast_parser · tree-sitter wrapper for Python / TypeScript / Go / Rust / Java."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser

from app.multimodal.code_structure.cache import LRUCache
from app.multimodal.code_structure.schemas import ASTTree
from app.multimodal.common.errors import L108Error


def _load_registry() -> dict[str, Language]:
    registry: dict[str, Language] = {}
    try:
        import tree_sitter_python as _py
        registry["python"] = Language(_py.language())
    except Exception:
        pass
    try:
        import tree_sitter_typescript as _ts
        registry["typescript"] = Language(_ts.language_typescript())
    except Exception:
        pass
    try:
        import tree_sitter_go as _go
        registry["go"] = Language(_go.language())
    except Exception:
        pass
    try:
        import tree_sitter_rust as _rs
        registry["rust"] = Language(_rs.language())
    except Exception:
        pass
    try:
        import tree_sitter_java as _ja
        registry["java"] = Language(_ja.language())
    except Exception:
        pass
    return registry


LANG_REGISTRY: dict[str, Language] = _load_registry()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _count_nodes(root: Any) -> int:  # type: ignore[misc]
    n = 1
    stack = list(root.children)
    while stack:
        node = stack.pop()
        n += 1
        stack.extend(node.children)
    return n


class ASTParser:
    def __init__(self, cache: LRUCache | None = None) -> None:
        self.cache = cache or LRUCache()

    def available_languages(self) -> set[str]:
        return set(LANG_REGISTRY.keys())

    def parse(self, file_path: Path, lang: str, *, pid: str = "default") -> ASTTree:
        if lang not in LANG_REGISTRY:
            raise L108Error(
                "type_mismatch",
                f"language {lang!r} not available (installed: {sorted(LANG_REGISTRY)})",
            )
        if not file_path.exists():
            raise L108Error("not_found", str(file_path))
        source = file_path.read_bytes()
        h = _sha256_bytes(source)

        cached = self.cache.get(pid, lang, h)
        if cached is not None:
            assert isinstance(cached, ASTTree)
            return cached

        parser = Parser(LANG_REGISTRY[lang])
        tree = parser.parse(source)
        root = tree.root_node
        result = ASTTree(
            lang=lang,
            file_path=str(file_path),
            file_hash=h,
            root_type=root.type,
            node_count=_count_nodes(root),
            loc=source.count(b"\n") + (1 if source and not source.endswith(b"\n") else 0),
            coarse=False,
        )
        self.cache.put(pid, lang, h, result)
        return result
