"""L2-01 md_writer · atomic write + post-hash verification + edit operations."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.multimodal.common.atomic_write_stub import atomic_write_text
from app.multimodal.common.errors import L108Error
from app.multimodal.doc_io import frontmatter_parser
from app.multimodal.doc_io.schemas import WriteResult
from app.multimodal.path_safety.whitelist import PathWhitelistValidator


class MDWriter:
    """Whitelist-guarded markdown writer with atomic write + post-hash check."""

    def __init__(
        self,
        validator: PathWhitelistValidator,
        *,
        require_frontmatter_keys: bool = True,
    ) -> None:
        self.validator = validator
        self.require_frontmatter_keys = require_frontmatter_keys

    def write(self, path: str, content: str) -> WriteResult:
        """Create or overwrite `path` with `content` atomically.

        Before writing, content is parsed for frontmatter · required keys enforced.
        After writing, the file is re-read to verify the hash matches what was written.
        """
        validation = self.validator.validate(path, action="write")
        assert validation.realpath is not None
        real = Path(validation.realpath)

        # Validate frontmatter (if policy requires)
        if self.require_frontmatter_keys:
            metadata, _body = frontmatter_parser.parse(content)
            frontmatter_parser.assert_required_keys(metadata)

        try:
            expected_hash = atomic_write_text(real, content)
        except PermissionError as e:
            raise L108Error("permission_denied", str(real)) from e

        # Post-write hash verification
        actual_bytes = real.read_bytes()
        actual_hash = hashlib.sha256(actual_bytes).hexdigest()
        if actual_hash != expected_hash:
            raise L108Error(
                "type_mismatch",
                f"post-write hash mismatch for {real}: wrote {expected_hash}, read {actual_hash}",
            )
        return WriteResult(
            path=path,
            realpath=str(real),
            bytes_written=len(actual_bytes),
            post_write_hash=actual_hash,
        )

    def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        *,
        replace_all: bool = False,
    ) -> WriteResult:
        """Find & replace inside an existing md file · atomic.

        If `replace_all=False`, `old_string` must match EXACTLY ONCE (otherwise error).
        Writes use atomic_write_text + post-hash verification (re-uses write()'s logic).
        """
        validation = self.validator.validate(path, action="write")
        assert validation.realpath is not None
        real = Path(validation.realpath)

        try:
            current = real.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise L108Error("not_found", str(real)) from e
        except PermissionError as e:
            raise L108Error("permission_denied", str(real)) from e
        except UnicodeDecodeError as e:
            raise L108Error("binary_unsupported", str(real)) from e

        occurrences = current.count(old_string)
        if occurrences == 0:
            raise L108Error(
                "invalid_path",
                f"edit: old_string not found in {real}",
            )
        if occurrences > 1 and not replace_all:
            raise L108Error(
                "invalid_path",
                f"edit: old_string found {occurrences}x in {real}; pass replace_all=True",
            )

        new_content = (
            current.replace(old_string, new_string)
            if replace_all
            else current.replace(old_string, new_string, 1)
        )

        # atomic write + post-hash (skip frontmatter-keys check on edits — they may not touch frontmatter)
        expected_hash = atomic_write_text(real, new_content)
        actual_bytes = real.read_bytes()
        actual_hash = hashlib.sha256(actual_bytes).hexdigest()
        if actual_hash != expected_hash:
            raise L108Error(
                "type_mismatch",
                f"post-write hash mismatch for {real}",
            )
        return WriteResult(
            path=path,
            realpath=str(real),
            bytes_written=len(actual_bytes),
            post_write_hash=actual_hash,
        )
