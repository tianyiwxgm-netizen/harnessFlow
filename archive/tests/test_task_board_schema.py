"""task-board.schema.json 自检 — 校验本地 task-boards/*.json 全部合法"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema  # type: ignore
except ImportError:
    jsonschema = None  # noqa: N816


HARNESS_DIR = Path(__file__).resolve().parents[2]
SCHEMA = HARNESS_DIR / "schemas" / "task-board.schema.json"
BOARDS_DIR = HARNESS_DIR / "task-boards"


def test_task_board_schema_exists() -> None:
    assert SCHEMA.exists(), f"missing {SCHEMA}"
    s = json.loads(SCHEMA.read_text())
    assert s["$id"].endswith("task-board.schema.json")
    # Critical fields that Stop gate / Supervisor read
    for field in ("task_id", "current_state", "goal_anchor"):
        assert field in s["required"], f"'{field}' must be required"


def test_task_board_schema_valid_itself() -> None:
    """Meta-validation: the schema doc is itself a valid JSON Schema."""
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text())
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.exceptions.SchemaError as e:
        pytest.fail(f"schema itself invalid: {e.message}")


def test_all_post_v1_1_task_boards_valid() -> None:
    """Every post-v1.1 task-board (task_id matches `p-*-<ts>`) must satisfy the schema.

    Legacy Phase 8 boards (`p8-*`, free-form task_id) are pre-v1.1 and grandfathered.
    The schema is contract for NEW task-boards written after v1.1; Stop gate / Supervisor
    apply it. 8.1's "risk=可逆" incident would have been caught by this contract if
    enforced at write time.
    """
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA.read_text())
    validator = jsonschema.Draft7Validator(schema)

    if not BOARDS_DIR.exists():
        pytest.skip("no task-boards/ dir yet")

    # Post-v1.1 boards use `p-<slug>-<utc_ts>` pattern. Legacy Phase 8 uses `p8-*`.
    import re
    v1_1_pattern = re.compile(r"^p-[a-z0-9-]+-\d{8}T\d{6}Z\.json$")
    boards = [b for b in BOARDS_DIR.glob("*.json") if v1_1_pattern.match(b.name)]
    legacy_boards = [b for b in BOARDS_DIR.glob("*.json") if not v1_1_pattern.match(b.name)]

    if not boards:
        pytest.skip("no post-v1.1 task-boards to validate")

    violations: list[str] = []
    for b in boards:
        try:
            data = json.loads(b.read_text())
        except json.JSONDecodeError as e:
            violations.append(f"{b.name}: JSON parse error: {e}")
            continue
        for err in validator.iter_errors(data):
            violations.append(f"{b.name} @ {list(err.absolute_path)}: {err.message}")

    print(f"[info] validated {len(boards)} post-v1.1 boards; {len(legacy_boards)} legacy boards grandfathered: {[b.name for b in legacy_boards]}")
    assert not violations, "post-v1.1 task-board schema violations:\n  - " + "\n  - ".join(violations)


def test_task_type_enum_includes_meta_task() -> None:
    """v1.1 P1 fix #5: task_type enum must cover meta-task / 元技能验证."""
    schema = json.loads(SCHEMA.read_text())
    enum = schema["properties"]["task_type"].get("enum", [])
    assert "元技能验证" in enum, "task_type enum must include '元技能验证'"
    assert "meta-task" in enum, "task_type enum must include 'meta-task'"
