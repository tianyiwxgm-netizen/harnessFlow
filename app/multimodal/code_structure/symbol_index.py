"""L2-02 symbol_index · class/function/const definitions + references per language."""

from __future__ import annotations

import re
from pathlib import Path

from app.multimodal.code_structure.schemas import SymbolDef, SymbolIndex, SymbolRef

# --- regex-based definition/reference extractors (lang-agnostic enough for WP-03) ---

_PY_DEF = re.compile(r"^(\s*)(class|def)\s+([A-Za-z_]\w*)", re.MULTILINE)
_PY_CONST = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=", re.MULTILINE)
_PY_CALL = re.compile(r"([A-Za-z_]\w*)\s*\(")     # call-site: name followed by (
_PY_DEF_KW = re.compile(r"\b(def|class)\s+$")     # preceding token is def/class keyword

_TS_DEF = re.compile(r"^\s*(class|function)\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
_TS_CONST = re.compile(r"^\s*const\s+([A-Za-z_$][\w$]*)", re.MULTILINE)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def extract_python(text: str, file_path: str) -> tuple[list[SymbolDef], list[SymbolRef]]:
    defs: list[SymbolDef] = []
    for m in _PY_DEF.finditer(text):
        indent, kind_kw, name = m.group(1), m.group(2), m.group(3)
        kind = "class" if kind_kw == "class" else "function"
        defs.append(SymbolDef(kind=kind, name=name, file_path=file_path, line=_line_of(text, m.start())))
    for m in _PY_CONST.finditer(text):
        defs.append(SymbolDef(kind="const", name=m.group(1), file_path=file_path, line=_line_of(text, m.start())))

    refs: list[SymbolRef] = []
    # Exclude the def-name itself from its own line to avoid self-ref noise.
    def_names = {d.name for d in defs}
    for m in _PY_CALL.finditer(text):
        name = m.group(1)
        # Skip Python keywords that look like calls
        if name in {"if", "while", "for", "return", "yield", "print", "range", "len", "int", "str", "float", "list", "dict", "set", "tuple", "bool", "type", "isinstance", "super"}:
            continue
        # Skip definition sites: if the text before this match ends with 'def ' or 'class '
        preceding = text[:m.start()]
        if _PY_DEF_KW.search(preceding):
            continue
        refs.append(SymbolRef(name=name, file_path=file_path, line=_line_of(text, m.start())))
    return defs, refs


def extract_typescript(text: str, file_path: str) -> tuple[list[SymbolDef], list[SymbolRef]]:
    defs: list[SymbolDef] = []
    for m in _TS_DEF.finditer(text):
        kind = "class" if m.group(1) == "class" else "function"
        defs.append(SymbolDef(kind=kind, name=m.group(2), file_path=file_path, line=_line_of(text, m.start())))
    for m in _TS_CONST.finditer(text):
        defs.append(SymbolDef(kind="const", name=m.group(1), file_path=file_path, line=_line_of(text, m.start())))
    refs: list[SymbolRef] = []
    return defs, refs


def build_symbol_index(sources: dict[str, str]) -> SymbolIndex:
    """Build cross-file symbol index. sources: path → text."""
    defs_by_name: dict[str, list[SymbolDef]] = {}
    refs_by_name: dict[str, list[SymbolRef]] = {}
    for path_str, text in sources.items():
        path = Path(path_str)
        suffix = path.suffix.lower()
        if suffix == ".py":
            ds, rs = extract_python(text, path_str)
        elif suffix in {".ts", ".tsx"}:
            ds, rs = extract_typescript(text, path_str)
        else:
            ds, rs = [], []
        for d in ds:
            defs_by_name.setdefault(d.name, []).append(d)
        for r in rs:
            refs_by_name.setdefault(r.name, []).append(r)
    return SymbolIndex(defs=defs_by_name, refs=refs_by_name)
