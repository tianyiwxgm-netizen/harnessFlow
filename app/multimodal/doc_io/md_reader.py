"""L2-01 md_reader · whitelist-guarded UTF-8 markdown reader with pagination."""

from __future__ import annotations

from pathlib import Path

from app.multimodal.common.errors import L108Error
from app.multimodal.doc_io import frontmatter_parser, paginator
from app.multimodal.doc_io.schemas import MDContent, MDPage
from app.multimodal.path_safety.whitelist import PathWhitelistValidator


class MDReader:
    """Read markdown files with policy guard · frontmatter parse · pagination."""

    def __init__(self, validator: PathWhitelistValidator) -> None:
        self.validator = validator

    def read(
        self,
        path: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
    ) -> MDContent:
        """Read `path` · return MDContent · paginate if > MAX_LINES_PER_PAGE.

        `offset` / `limit` subset the BODY lines (1-based offset). They do NOT affect
        `total_lines` — that still reflects the full file — but `body` is sliced and
        `pages` is None when a subset is returned.
        """
        validation = self.validator.validate(path, action="read")
        assert validation.realpath is not None
        real = Path(validation.realpath)
        try:
            raw_bytes = real.read_bytes()
        except FileNotFoundError as e:
            raise L108Error("not_found", str(real)) from e
        except PermissionError as e:
            raise L108Error("permission_denied", str(real)) from e
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise L108Error("binary_unsupported", str(real)) from e

        metadata, body = frontmatter_parser.parse(raw_text)
        total_lines = len(body.splitlines())

        # Subset request
        if offset is not None or limit is not None:
            off = offset if offset is not None else 1
            if off < 1:
                raise L108Error("invalid_path", f"offset must be >= 1, got {off}")
            lines = body.splitlines(keepends=True)
            if off - 1 >= len(lines):
                # past EOF · return empty slice
                sub_body = ""
            else:
                end = off - 1 + limit if limit is not None else len(lines)
                sub_body = "".join(lines[off - 1:end])
            return MDContent(
                path=path, realpath=str(real),
                frontmatter=metadata, body=sub_body,
                total_lines=total_lines, pages=None,
            )

        # Full read
        pages: list[MDPage] | None = None
        if total_lines > paginator.MAX_LINES_PER_PAGE:
            pages = paginator.paginate(body)
        return MDContent(
            path=path, realpath=str(real),
            frontmatter=metadata, body=body,
            total_lines=total_lines, pages=pages,
        )
