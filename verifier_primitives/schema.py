"""JSON Schema primitive."""

import json
from pathlib import Path

from .errors import DependencyMissing


def schema_valid(data, schema_path: str) -> tuple[bool, dict]:
    try:
        import jsonschema
        from jsonschema import exceptions as jse
    except ImportError as exc:
        raise DependencyMissing("jsonschema", str(exc)) from exc

    sp = Path(schema_path)
    if not sp.is_file():
        return False, {"schema_path": schema_path, "error": "schema_not_found"}
    try:
        schema = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, {"schema_path": schema_path, "error": f"schema_load_failed: {exc}"}

    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            return False, {"schema_path": schema_path, "error": f"data_parse_failed: {exc}"}

    try:
        jsonschema.validate(instance=data, schema=schema)
        return True, {"schema_path": schema_path, "valid": True}
    except jse.ValidationError as exc:
        return False, {
            "schema_path": schema_path,
            "valid": False,
            "error_path": list(exc.absolute_path),
            "message": exc.message,
        }
