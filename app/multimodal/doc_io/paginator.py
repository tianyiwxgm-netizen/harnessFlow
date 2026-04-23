"""Markdown pagination · split into ≤ MAX_LINES_PER_PAGE pages."""

from __future__ import annotations

from app.multimodal.doc_io.schemas import MDPage

MAX_LINES_PER_PAGE: int = 2000


def paginate(body: str) -> list[MDPage]:
    """Split body into MDPage list. Always returns ≥ 1 page (possibly empty last)."""
    # splitlines keepends=True so we preserve byte-for-byte equivalence.
    lines = body.splitlines(keepends=True)
    total = len(lines)
    if total == 0:
        return [MDPage(index=0, lines_start=1, lines_end=0, body="")]
    pages: list[MDPage] = []
    idx = 0
    while idx * MAX_LINES_PER_PAGE < total:
        start_line = idx * MAX_LINES_PER_PAGE  # 0-based slice index
        end_line = min(start_line + MAX_LINES_PER_PAGE, total)
        page_body = "".join(lines[start_line:end_line])
        pages.append(
            MDPage(
                index=idx,
                lines_start=start_line + 1,
                lines_end=end_line,
                body=page_body,
            )
        )
        idx += 1
    return pages


def merge(pages: list[MDPage]) -> str:
    """Re-join pages → original body string. Inverse of paginate."""
    return "".join(p.body for p in sorted(pages, key=lambda p: p.index))


def invariant_preserves_body(body: str) -> bool:
    """Return True iff paginate+merge round-trips exactly."""
    return merge(paginate(body)) == body
