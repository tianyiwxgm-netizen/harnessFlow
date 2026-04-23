"""L2-02 code_structure · ASTTree / SymbolDef / SymbolRef / DepEdge / DepGraph / SymbolIndex."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ASTTree(BaseModel):
    """Parsed AST metadata · we keep the tree-sitter root out of pydantic (opaque handle)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    lang: str
    file_path: str
    file_hash: str        # sha256 of file bytes · cache key
    root_type: str        # e.g. 'module', 'program', 'source_file'
    node_count: int       # total number of AST nodes
    loc: int              # newline-based line count of file
    coarse: bool = False  # True when produced by regex fallback instead of tree-sitter


class SymbolDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str          # 'class' | 'function' | 'const'
    name: str
    file_path: str
    line: int          # 1-based line of definition


class SymbolRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    file_path: str
    line: int


class SymbolIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defs: dict[str, list[SymbolDef]]         # name → definitions (same name may exist in multiple files)
    refs: dict[str, list[SymbolRef]]         # name → references


class DepEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str          # file_path importing
    dst: str          # imported module name (unresolved · not a file path)


class DepGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edges: list[DepEdge]
    cycles: list[list[str]]    # list of cycles · each cycle is list of file_paths
