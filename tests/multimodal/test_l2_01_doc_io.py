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


# --- atomic_write_stub ---

import hashlib

from app.multimodal.common.atomic_write_stub import atomic_write_bytes, atomic_write_text


def test_atomic_write_bytes_creates_file_with_hash(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    sha = atomic_write_bytes(target, b"hello")
    assert target.read_bytes() == b"hello"
    assert sha == hashlib.sha256(b"hello").hexdigest()


def test_atomic_write_bytes_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "b.bin"
    atomic_write_bytes(target, b"first")
    atomic_write_bytes(target, b"second")
    assert target.read_bytes() == b"second"


def test_atomic_write_text_encodes_utf8(tmp_path: Path) -> None:
    target = tmp_path / "c.md"
    atomic_write_text(target, "你好\n")
    assert target.read_text(encoding="utf-8") == "你好\n"


def test_atomic_write_leaves_no_tmp_files_on_success(tmp_path: Path) -> None:
    target = tmp_path / "d.md"
    atomic_write_text(target, "x")
    # only the final file should exist
    siblings = list(target.parent.iterdir())
    assert siblings == [target]


# --- md_writer.write ---

from app.multimodal.doc_io.md_writer import MDWriter


def _writer(root: Path, *, require_fm: bool = True) -> MDWriter:
    return MDWriter(
        PathWhitelistValidator(root, "p-001", ["docs/"]),
        require_frontmatter_keys=require_fm,
    )


def _docs2(root: Path) -> Path:
    d = root / "docs"
    d.mkdir(exist_ok=True)
    return d


def test_write_creates_new_md_with_frontmatter(tmp_project_root: Path) -> None:
    _docs2(tmp_project_root)
    content = "---\ndoc_id: x\ndoc_type: plan\n---\n# Body\n"
    result = _writer(tmp_project_root).write("docs/new.md", content)
    assert result.bytes_written == len(content.encode("utf-8"))
    assert (tmp_project_root / "docs" / "new.md").read_text() == content


def test_write_rejects_missing_required_keys(tmp_project_root: Path) -> None:
    _docs2(tmp_project_root)
    content = "---\ndoc_id: only_this\n---\n# Body\n"   # missing doc_type
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root).write("docs/bad.md", content)
    assert ei.value.code == "type_mismatch"


def test_write_without_frontmatter_allowed_when_policy_off(tmp_project_root: Path) -> None:
    _docs2(tmp_project_root)
    content = "# no frontmatter\n"
    result = _writer(tmp_project_root, require_fm=False).write("docs/nofm.md", content)
    assert result.bytes_written > 0


def test_write_overwrites_existing_file(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "over.md").write_text("old content\n")
    content = "---\ndoc_id: x\ndoc_type: t\n---\nnew content\n"
    _writer(tmp_project_root).write("docs/over.md", content)
    assert (docs / "over.md").read_text() == content


def test_write_path_forbidden(tmp_project_root: Path) -> None:
    (tmp_project_root / "secrets").mkdir()
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root, require_fm=False).write("secrets/x.md", "# hi\n")
    assert ei.value.code == "path_forbidden"


def test_write_post_hash_mismatch_raises(tmp_project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate external tampering by having read_bytes return wrong content after write."""
    docs = _docs2(tmp_project_root)
    content = "---\ndoc_id: x\ndoc_type: t\n---\n# Body\n"

    real_read_bytes = Path.read_bytes

    def fake_read_bytes(self: Path) -> bytes:
        if self.name == "tamper.md":
            return b"TAMPERED"
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root).write("docs/tamper.md", content)
    assert ei.value.code == "type_mismatch"
    assert "post-write hash mismatch" in ei.value.detail


# --- md_writer.edit ---

def test_edit_exact_single_match(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "e.md").write_text("---\ndoc_id: x\ndoc_type: t\n---\nhello world\n")
    result = _writer(tmp_project_root).edit("docs/e.md", "world", "earth")
    assert "hello earth" in (docs / "e.md").read_text()
    assert result.post_write_hash != ""


def test_edit_old_string_not_found(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "e.md").write_text("nothing here\n")
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root, require_fm=False).edit("docs/e.md", "unicorn", "pegasus")
    assert ei.value.code == "invalid_path"


def test_edit_multiple_matches_without_replace_all_rejects(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "e.md").write_text("foo bar foo\n")
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root, require_fm=False).edit("docs/e.md", "foo", "baz")
    assert ei.value.code == "invalid_path"


def test_edit_replace_all_accepts_multiple(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "e.md").write_text("foo bar foo\n")
    _writer(tmp_project_root, require_fm=False).edit("docs/e.md", "foo", "baz", replace_all=True)
    assert (docs / "e.md").read_text() == "baz bar baz\n"


def test_edit_missing_file_not_found(tmp_project_root: Path) -> None:
    _docs2(tmp_project_root)
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root, require_fm=False).edit("docs/nope.md", "a", "b")
    assert ei.value.code == "not_found"


def test_edit_binary_file_rejected(tmp_project_root: Path) -> None:
    docs = _docs2(tmp_project_root)
    (docs / "blob.md").write_bytes(b"\xff\xfe\x00binary")
    with pytest.raises(L108Error) as ei:
        _writer(tmp_project_root, require_fm=False).edit("docs/blob.md", "a", "b")
    assert ei.value.code == "binary_unsupported"
