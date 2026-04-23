"""WP-η-03 L2-02 code_structure tests · schemas + ast_parser + cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.multimodal.code_structure.ast_parser import ASTParser, LANG_REGISTRY
from app.multimodal.code_structure.cache import LRUCache
from app.multimodal.code_structure.schemas import (
    ASTTree, DepEdge, DepGraph, SymbolDef, SymbolIndex, SymbolRef,
)
from app.multimodal.common.errors import L108Error


# --- schemas ---

def test_ast_tree_shape() -> None:
    t = ASTTree(lang="python", file_path="a.py", file_hash="abc", root_type="module", node_count=3, loc=1)
    assert t.coarse is False


def test_symbol_def_shape() -> None:
    d = SymbolDef(kind="function", name="foo", file_path="a.py", line=3)
    assert d.kind == "function"


def test_symbol_index_accepts_multiple_defs_per_name() -> None:
    si = SymbolIndex(
        defs={"foo": [SymbolDef(kind="function", name="foo", file_path="a.py", line=1),
                       SymbolDef(kind="function", name="foo", file_path="b.py", line=2)]},
        refs={},
    )
    assert len(si.defs["foo"]) == 2


def test_dep_edge_shape() -> None:
    e = DepEdge(src="a.py", dst="b")
    assert e.dst == "b"


def test_dep_graph_cycles() -> None:
    g = DepGraph(edges=[], cycles=[["a.py", "b.py", "a.py"]])
    assert g.cycles[0][0] == "a.py"


# --- LRUCache ---

def test_cache_basic_put_get() -> None:
    c = LRUCache(max_size=4)
    c.put("p-001", "python", "h1", "value-1")
    assert c.get("p-001", "python", "h1") == "value-1"


def test_cache_miss_returns_none() -> None:
    c = LRUCache(max_size=4)
    assert c.get("p-001", "python", "nope") is None


def test_cache_lru_evicts_oldest() -> None:
    c = LRUCache(max_size=2)
    c.put("p-001", "python", "a", 1)
    c.put("p-001", "python", "b", 2)
    c.put("p-001", "python", "c", 3)   # evicts 'a'
    assert c.get("p-001", "python", "a") is None
    assert c.get("p-001", "python", "b") == 2
    assert c.get("p-001", "python", "c") == 3


def test_cache_pid_isolation() -> None:
    c = LRUCache(max_size=4)
    c.put("p-001", "python", "h1", "A")
    c.put("p-002", "python", "h1", "B")
    assert c.get("p-001", "python", "h1") == "A"
    assert c.get("p-002", "python", "h1") == "B"


def test_cache_touch_moves_to_end() -> None:
    c = LRUCache(max_size=2)
    c.put("p", "py", "a", 1)
    c.put("p", "py", "b", 2)
    c.get("p", "py", "a")             # touch a → b becomes oldest
    c.put("p", "py", "c", 3)          # evicts b
    assert c.get("p", "py", "b") is None
    assert c.get("p", "py", "a") == 1


def test_cache_rejects_nonpositive_max_size() -> None:
    with pytest.raises(ValueError):
        LRUCache(max_size=0)


# --- ast_parser registry ---

def test_registry_has_all_five_languages() -> None:
    assert {"python", "typescript", "go", "rust", "java"} <= set(LANG_REGISTRY.keys())


# --- ast_parser.parse() · Python ---

def test_parse_python_def(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("def foo():\n    return 1\n")
    tree = ASTParser().parse(f, "python")
    assert tree.lang == "python"
    assert tree.root_type == "module"
    assert tree.node_count > 1
    assert tree.loc == 2


def test_parse_python_class(tmp_path: Path) -> None:
    f = tmp_path / "k.py"
    f.write_text("class A:\n    pass\n")
    tree = ASTParser().parse(f, "python")
    assert tree.root_type == "module"


def test_parse_python_import(tmp_path: Path) -> None:
    f = tmp_path / "i.py"
    f.write_text("import os\nfrom pathlib import Path\n")
    tree = ASTParser().parse(f, "python")
    assert tree.node_count > 3


# --- TypeScript ---

def test_parse_typescript_function(tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("function foo() { return 1; }\n")
    tree = ASTParser().parse(f, "typescript")
    assert tree.lang == "typescript"
    assert tree.node_count > 1


def test_parse_typescript_class(tmp_path: Path) -> None:
    f = tmp_path / "c.ts"
    f.write_text("class A { x = 1; }\n")
    tree = ASTParser().parse(f, "typescript")
    assert tree.node_count > 1


def test_parse_typescript_import(tmp_path: Path) -> None:
    f = tmp_path / "i.ts"
    f.write_text("import { X } from './y';\n")
    tree = ASTParser().parse(f, "typescript")
    assert tree.node_count > 1


# --- Go ---

def test_parse_go_func(tmp_path: Path) -> None:
    f = tmp_path / "a.go"
    f.write_text("package main\nfunc foo() {}\n")
    tree = ASTParser().parse(f, "go")
    assert tree.lang == "go"


def test_parse_go_import(tmp_path: Path) -> None:
    f = tmp_path / "b.go"
    f.write_text('package main\nimport "fmt"\n')
    tree = ASTParser().parse(f, "go")
    assert tree.node_count > 1


def test_parse_go_struct(tmp_path: Path) -> None:
    f = tmp_path / "c.go"
    f.write_text("package main\ntype A struct { X int }\n")
    tree = ASTParser().parse(f, "go")
    assert tree.node_count > 1


# --- Rust ---

def test_parse_rust_fn(tmp_path: Path) -> None:
    f = tmp_path / "a.rs"
    f.write_text("fn foo() {}\n")
    tree = ASTParser().parse(f, "rust")
    assert tree.lang == "rust"


def test_parse_rust_struct(tmp_path: Path) -> None:
    f = tmp_path / "s.rs"
    f.write_text("struct A { x: i32 }\n")
    tree = ASTParser().parse(f, "rust")
    assert tree.node_count > 1


def test_parse_rust_use(tmp_path: Path) -> None:
    f = tmp_path / "u.rs"
    f.write_text("use std::io::Read;\n")
    tree = ASTParser().parse(f, "rust")
    assert tree.node_count > 1


# --- Java ---

def test_parse_java_class(tmp_path: Path) -> None:
    f = tmp_path / "A.java"
    f.write_text("class A { void foo() {} }\n")
    tree = ASTParser().parse(f, "java")
    assert tree.lang == "java"


def test_parse_java_import(tmp_path: Path) -> None:
    f = tmp_path / "B.java"
    f.write_text("import java.util.List;\nclass B {}\n")
    tree = ASTParser().parse(f, "java")
    assert tree.node_count > 1


def test_parse_java_method(tmp_path: Path) -> None:
    f = tmp_path / "M.java"
    f.write_text("class M { public int foo() { return 1; } }\n")
    tree = ASTParser().parse(f, "java")
    assert tree.node_count > 1


# --- cache integration ---

def test_parser_uses_cache_on_second_call(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    parser = ASTParser()
    t1 = parser.parse(f, "python", pid="p-001")
    t2 = parser.parse(f, "python", pid="p-001")
    # Same cached object
    assert t1 is t2


def test_parser_no_cache_collision_across_pids(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    parser = ASTParser()
    t1 = parser.parse(f, "python", pid="p-001")
    t2 = parser.parse(f, "python", pid="p-002")
    # Same file, but different pid buckets; identity check is False because each pid re-parses.
    # Hash / content equal but object identity differs.
    assert t1 is not t2
    assert t1.file_hash == t2.file_hash


# --- error paths ---

def test_parser_unknown_language_raises(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("x=1\n")
    with pytest.raises(L108Error) as ei:
        ASTParser().parse(f, "cobol")
    assert ei.value.code == "type_mismatch"


def test_parser_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(L108Error) as ei:
        ASTParser().parse(tmp_path / "nope.py", "python")
    assert ei.value.code == "not_found"
