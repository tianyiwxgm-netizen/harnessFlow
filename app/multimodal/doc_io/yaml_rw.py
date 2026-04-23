"""L2-01 yaml_rw · read/write YAML files · reuses atomic_write + post-hash."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from app.multimodal.common.atomic_write_stub import atomic_write_text
from app.multimodal.common.errors import L108Error
from app.multimodal.doc_io.schemas import WriteResult, YAMLContent
from app.multimodal.path_safety.whitelist import PathWhitelistValidator


class YAMLRW:
    """Whitelist-guarded YAML reader/writer with atomic write + post-hash verification."""

    def __init__(self, validator: PathWhitelistValidator) -> None:
        self.validator = validator

    def read(self, path: str) -> YAMLContent:
        validation = self.validator.validate(path, action="read")
        assert validation.realpath is not None
        real = Path(validation.realpath)
        try:
            text = real.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise L108Error("not_found", str(real)) from e
        except PermissionError as e:
            raise L108Error("permission_denied", str(real)) from e
        except UnicodeDecodeError as e:
            raise L108Error("binary_unsupported", str(real)) from e
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise L108Error("type_mismatch", f"malformed YAML: {e}") from e
        if data is None:
            data = {}
        if not isinstance(data, (dict, list)):
            raise L108Error("type_mismatch", f"top-level YAML must be mapping or sequence, got {type(data).__name__}")
        return YAMLContent(path=path, realpath=str(real), data=data)

    def write(self, path: str, data: dict[str, Any] | list[Any]) -> WriteResult:
        validation = self.validator.validate(path, action="write")
        assert validation.realpath is not None
        real = Path(validation.realpath)
        if not isinstance(data, (dict, list)):
            raise L108Error("type_mismatch", f"top-level YAML must be mapping or sequence, got {type(data).__name__}")
        text = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=True)
        expected_hash = atomic_write_text(real, text)
        actual_bytes = real.read_bytes()
        actual_hash = hashlib.sha256(actual_bytes).hexdigest()
        if actual_hash != expected_hash:
            raise L108Error("type_mismatch", f"post-write hash mismatch for {real}")
        return WriteResult(
            path=path,
            realpath=str(real),
            bytes_written=len(actual_bytes),
            post_write_hash=actual_hash,
        )
