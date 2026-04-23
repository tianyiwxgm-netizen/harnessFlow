"""L2-02 dep_graph · import-level dependency extraction + cycle detection."""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from app.multimodal.code_structure.schemas import DepEdge, DepGraph


# Language → iterable of regexes capturing the imported module name (group 1).
_IMPORT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "python": [
        re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.MULTILINE),
        re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+", re.MULTILINE),
    ],
    "typescript": [
        re.compile(r"""^\s*import\s+[^;]*?from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.MULTILINE),
    ],
    "go": [
        re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.MULTILINE),
    ],
    "rust": [
        re.compile(r"^\s*use\s+([A-Za-z_][\w:]*)", re.MULTILINE),
    ],
    "java": [
        re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.MULTILINE),
    ],
}


def _language_for(path: Path) -> str | None:
    """Return language key from file extension · None for unknown."""
    mapping = {
        ".py": "python", ".ts": "typescript", ".tsx": "typescript",
        ".go": "go", ".rs": "rust", ".java": "java",
    }
    return mapping.get(path.suffix.lower())


def extract_imports(source: str, lang: str) -> list[str]:
    """Return list of imported module/name strings (order preserved, dedup)."""
    if lang not in _IMPORT_PATTERNS:
        return []
    seen: list[str] = []
    for pat in _IMPORT_PATTERNS[lang]:
        for m in pat.finditer(source):
            name = m.group(1)
            if name not in seen:
                seen.append(name)
    return seen


def build_dep_graph(files: list[Path]) -> DepGraph:
    """Build DepGraph from a list of source files · detect cycles."""
    edges: list[DepEdge] = []
    for path in files:
        lang = _language_for(path)
        if lang is None:
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for imp in extract_imports(source, lang):
            edges.append(DepEdge(src=str(path), dst=imp))

    # Build networkx DiGraph from edges where dst appears also as src (so cycles resolve within the set).
    g = nx.DiGraph()
    for e in edges:
        g.add_edge(e.src, e.dst)
    cycles_raw = list(nx.simple_cycles(g))
    # `simple_cycles` returns lists of nodes without the closing edge — normalize by repeating first node.
    cycles: list[list[str]] = [[*cycle, cycle[0]] for cycle in cycles_raw]
    return DepGraph(edges=edges, cycles=cycles)


def build_dep_graph_from_sources(sources: dict[str, str]) -> DepGraph:
    """Variant accepting pre-loaded content. `sources: path → text`. Lang inferred from extension."""
    edges: list[DepEdge] = []
    for path_str, text in sources.items():
        lang = _language_for(Path(path_str))
        if lang is None:
            continue
        for imp in extract_imports(text, lang):
            edges.append(DepEdge(src=path_str, dst=imp))
    g = nx.DiGraph()
    for e in edges:
        g.add_edge(e.src, e.dst)
    cycles_raw = list(nx.simple_cycles(g))
    cycles = [[*cycle, cycle[0]] for cycle in cycles_raw]
    return DepGraph(edges=edges, cycles=cycles)
