"""L2-01 doc_io · MDContent / MDPage / YAMLContent / WriteResult schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class MDPage(BaseModel):
    """One page of a paginated markdown file."""
    model_config = ConfigDict(extra="forbid")

    index: int               # 0-based
    lines_start: int         # 1-based inclusive
    lines_end: int           # 1-based inclusive
    body: str

    @field_validator("index")
    @classmethod
    def _idx_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("index must be >= 0")
        return v


class MDContent(BaseModel):
    """Parsed markdown file · optionally paginated."""
    model_config = ConfigDict(extra="forbid")

    path: str
    realpath: str
    frontmatter: dict[str, Any]
    body: str                # full body (or merged if paginated)
    total_lines: int
    pages: list[MDPage] | None = None   # None when single-page

    @property
    def is_paged(self) -> bool:
        return self.pages is not None and len(self.pages) > 1


class YAMLContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    realpath: str
    data: dict[str, Any] | list[Any]


class WriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    realpath: str
    bytes_written: int
    post_write_hash: str     # sha256 hex of final file contents
