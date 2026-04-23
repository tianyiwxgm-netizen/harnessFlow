"""WP-η-02 L2-01 doc_io foundation tests · schemas + frontmatter + paginator."""

from __future__ import annotations

import pytest

from app.multimodal.common.errors import L108Error
from app.multimodal.doc_io import frontmatter_parser, paginator
from app.multimodal.doc_io.schemas import MDContent, MDPage, WriteResult, YAMLContent


# --- schemas ---

def test_md_page_basic() -> None:
    p = MDPage(index=0, lines_start=1, lines_end=10, body="hi\n")
    assert p.index == 0
    assert p.body.startswith("hi")


def test_md_page_rejects_negative_index() -> None:
    with pytest.raises(Exception):
        MDPage(index=-1, lines_start=1, lines_end=1, body="")


def test_md_content_single_page_is_paged_false() -> None:
    c = MDContent(
        path="a.md", realpath="/tmp/a.md",
        frontmatter={}, body="# hi\n", total_lines=1,
        pages=None,
    )
    assert c.is_paged is False


def test_md_content_many_pages_is_paged_true() -> None:
    pages = [MDPage(index=0, lines_start=1, lines_end=1, body="a\n"),
             MDPage(index=1, lines_start=2, lines_end=2, body="b\n")]
    c = MDContent(
        path="a.md", realpath="/tmp/a.md",
        frontmatter={}, body="a\nb\n", total_lines=2, pages=pages,
    )
    assert c.is_paged is True


def test_md_content_one_page_list_is_not_paged() -> None:
    """Single-element pages list should still read as not paged."""
    pages = [MDPage(index=0, lines_start=1, lines_end=1, body="a\n")]
    c = MDContent(path="a.md", realpath="/tmp/a.md",
                  frontmatter={}, body="a\n", total_lines=1, pages=pages)
    assert c.is_paged is False


def test_yaml_content_accepts_dict() -> None:
    y = YAMLContent(path="a.yaml", realpath="/tmp/a.yaml", data={"k": 1})
    assert y.data["k"] == 1


def test_yaml_content_accepts_list() -> None:
    y = YAMLContent(path="a.yaml", realpath="/tmp/a.yaml", data=[1, 2, 3])
    assert y.data == [1, 2, 3]


def test_write_result_shape() -> None:
    r = WriteResult(path="a.md", realpath="/tmp/a.md", bytes_written=42,
                    post_write_hash="deadbeef" * 8)
    assert r.bytes_written == 42
    assert len(r.post_write_hash) == 64


# --- frontmatter ---

def test_frontmatter_parses_valid_block() -> None:
    raw = "---\ndoc_id: abc\ndoc_type: plan\n---\n# Hello\n"
    meta, body = frontmatter_parser.parse(raw)
    assert meta["doc_id"] == "abc"
    assert meta["doc_type"] == "plan"
    assert body.strip() == "# Hello"


def test_frontmatter_no_block_returns_empty_meta() -> None:
    raw = "# Just a heading\nline two\n"
    meta, body = frontmatter_parser.parse(raw)
    assert meta == {}
    assert "# Just a heading" in body


def test_frontmatter_malformed_raises_type_mismatch() -> None:
    # opening delimiter, malformed YAML inside
    raw = "---\nkey: [unbalanced\n---\n# body\n"
    with pytest.raises(L108Error) as ei:
        frontmatter_parser.parse(raw)
    assert ei.value.code == "type_mismatch"


def test_frontmatter_required_keys_ok() -> None:
    frontmatter_parser.assert_required_keys({"doc_id": "x", "doc_type": "y"})


def test_frontmatter_required_keys_missing_raises() -> None:
    with pytest.raises(L108Error) as ei:
        frontmatter_parser.assert_required_keys({"doc_id": "x"})  # missing doc_type
    assert ei.value.code == "type_mismatch"


def test_frontmatter_dump_roundtrip() -> None:
    meta = {"doc_id": "abc", "doc_type": "plan"}
    body = "# Title\npara\n"
    rendered = frontmatter_parser.dump(meta, body)
    meta2, body2 = frontmatter_parser.parse(rendered)
    assert meta2 == meta
    assert body2.strip() == body.strip()


# --- paginator ---

def test_paginate_empty_body_returns_single_page() -> None:
    pages = paginator.paginate("")
    assert len(pages) == 1
    assert pages[0].body == ""


def test_paginate_small_body_single_page() -> None:
    pages = paginator.paginate("a\nb\nc\n")
    assert len(pages) == 1
    assert pages[0].lines_start == 1
    assert pages[0].lines_end == 3
    assert pages[0].body == "a\nb\nc\n"


def test_paginate_exact_threshold_single_page() -> None:
    body = "\n".join(f"l{i}" for i in range(paginator.MAX_LINES_PER_PAGE)) + "\n"
    pages = paginator.paginate(body)
    assert len(pages) == 1
    assert pages[0].lines_end == paginator.MAX_LINES_PER_PAGE


def test_paginate_over_threshold_two_pages() -> None:
    body = "\n".join(f"l{i}" for i in range(paginator.MAX_LINES_PER_PAGE + 1)) + "\n"
    pages = paginator.paginate(body)
    assert len(pages) == 2
    assert pages[0].lines_start == 1
    assert pages[0].lines_end == paginator.MAX_LINES_PER_PAGE
    assert pages[1].lines_start == paginator.MAX_LINES_PER_PAGE + 1


def test_paginate_three_pages_math() -> None:
    count = paginator.MAX_LINES_PER_PAGE * 2 + 50
    body = "\n".join(f"l{i}" for i in range(count)) + "\n"
    pages = paginator.paginate(body)
    assert len(pages) == 3
    assert pages[2].lines_end == count


def test_paginate_merge_roundtrip_small() -> None:
    body = "hello\nworld\n"
    assert paginator.invariant_preserves_body(body)


def test_paginate_merge_roundtrip_big() -> None:
    body = "\n".join(f"line_{i}" for i in range(3200)) + "\n"
    assert paginator.invariant_preserves_body(body)


def test_paginate_merge_roundtrip_no_trailing_newline() -> None:
    body = "x\ny\nz"  # no final \n
    assert paginator.invariant_preserves_body(body)


def test_paginate_pages_indices_are_sequential() -> None:
    body = "\n".join(f"l{i}" for i in range(5000)) + "\n"
    pages = paginator.paginate(body)
    assert [p.index for p in pages] == list(range(len(pages)))


# --- Task 02.3 md_reader tests ---

from pathlib import Path

from app.multimodal.doc_io.md_reader import MDReader
from app.multimodal.path_safety.whitelist import PathWhitelistValidator


def _reader(root: Path) -> MDReader:
    return MDReader(PathWhitelistValidator(root, "p-001", ["docs/"]))


def _docs(root: Path) -> Path:
    d = root / "docs"
    d.mkdir(exist_ok=True)
    return d


# Small file
def test_reader_small_file_returns_single_page_none(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("---\ndoc_id: a\ndoc_type: t\n---\n# Hi\nline 2\n")
    content = _reader(tmp_project_root).read("docs/a.md")
    assert content.is_paged is False
    assert content.pages is None
    assert content.frontmatter["doc_id"] == "a"
    assert content.total_lines == 2  # body lines after frontmatter stripped
    assert "# Hi" in content.body


def test_reader_no_frontmatter(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "plain.md").write_text("# Hello\nworld\n")
    content = _reader(tmp_project_root).read("docs/plain.md")
    assert content.frontmatter == {}
    assert content.total_lines == 2


def test_reader_returns_realpath(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("hi\n")
    content = _reader(tmp_project_root).read("docs/a.md")
    assert content.realpath.endswith("docs/a.md")


# Large file · paginated
def test_reader_large_file_paginated(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    body = "\n".join(f"line {i}" for i in range(3200)) + "\n"
    (docs / "big.md").write_text(body)
    content = _reader(tmp_project_root).read("docs/big.md")
    assert content.is_paged is True
    assert content.pages is not None
    assert len(content.pages) == 2
    assert content.total_lines == 3200


def test_reader_merge_of_pages_equals_body(tmp_project_root: Path) -> None:
    from app.multimodal.doc_io import paginator
    docs = _docs(tmp_project_root)
    body = "\n".join(f"l{i}" for i in range(3200)) + "\n"
    (docs / "big.md").write_text(body)
    content = _reader(tmp_project_root).read("docs/big.md")
    assert content.pages is not None
    assert paginator.merge(content.pages) == content.body


# offset / limit
def test_reader_offset_limit_slices_body(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("a\nb\nc\nd\ne\n")
    content = _reader(tmp_project_root).read("docs/a.md", offset=2, limit=2)
    assert content.body == "b\nc\n"
    assert content.total_lines == 5     # full-file total preserved
    assert content.pages is None


def test_reader_offset_past_eof_returns_empty_body(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("a\nb\n")
    content = _reader(tmp_project_root).read("docs/a.md", offset=99)
    assert content.body == ""


def test_reader_offset_zero_rejected(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("a\n")
    with pytest.raises(L108Error) as ei:
        _reader(tmp_project_root).read("docs/a.md", offset=0)
    assert ei.value.code == "invalid_path"


def test_reader_limit_without_offset_starts_at_line_1(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "a.md").write_text("a\nb\nc\n")
    content = _reader(tmp_project_root).read("docs/a.md", limit=2)
    assert content.body == "a\nb\n"


# Error codes
def test_reader_not_found(tmp_project_root: Path) -> None:
    _docs(tmp_project_root)
    with pytest.raises(L108Error) as ei:
        _reader(tmp_project_root).read("docs/missing.md")
    assert ei.value.code == "not_found"


def test_reader_binary_unsupported(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "blob.md").write_bytes(b"\xff\xfe\xfdbinary\x00content")
    with pytest.raises(L108Error) as ei:
        _reader(tmp_project_root).read("docs/blob.md")
    assert ei.value.code == "binary_unsupported"


def test_reader_path_forbidden(tmp_project_root: Path) -> None:
    (tmp_project_root / "node_modules").mkdir()
    (tmp_project_root / "node_modules" / "foo.md").write_text("hi\n")
    with pytest.raises(L108Error) as ei:
        _reader(tmp_project_root).read("node_modules/foo.md")
    assert ei.value.code == "path_forbidden"


def test_reader_malformed_frontmatter(tmp_project_root: Path) -> None:
    docs = _docs(tmp_project_root)
    (docs / "bad.md").write_text("---\nkey: [broken\n---\n# body\n")
    with pytest.raises(L108Error) as ei:
        _reader(tmp_project_root).read("docs/bad.md")
    assert ei.value.code == "type_mismatch"
