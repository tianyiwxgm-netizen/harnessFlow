"""Parse stage-contracts.md yaml code blocks into StageContract objects.

Design:
    - Markdown file contains ```yaml code blocks; each block with `stage_id`
      is a contract.
    - No dependency on pyyaml if the caller wants a lightweight import path
      (we attempt `yaml.safe_load`, fall back to an informative error).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class InputRef:
    from_stage: str
    artifact_ref: str
    must_exist: bool = True
    validation: str | None = None


@dataclass(frozen=True)
class OutputDecl:
    artifact_ref: str
    format: str
    path_pattern: str | None = None
    schema_ref: str | None = None
    min_lines: int | None = None
    validation_primitive: str | None = None


@dataclass(frozen=True)
class StageContract:
    """One stage's I/O contract parsed from stage-contracts.md."""

    stage_id: str
    route: str
    state: str
    phase_label: str
    skill_invoked: str
    inputs_required: tuple[InputRef, ...]
    outputs_produced: tuple[OutputDecl, ...]
    gate_predicate: str
    on_input_missing: str  # WARN | BLOCK | ABORT
    on_output_missing: str
    parallel_with: tuple[str, ...] = field(default_factory=tuple)
    optional: bool = False
    notes: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StageContract":
        inputs = tuple(
            InputRef(
                from_stage=r["from_stage"],
                artifact_ref=r["artifact_ref"],
                must_exist=bool(r.get("must_exist", True)),
                validation=r.get("validation"),
            )
            for r in (d.get("inputs_required") or [])
        )
        outputs = tuple(
            OutputDecl(
                artifact_ref=o["artifact_ref"],
                format=o["format"],
                path_pattern=o.get("path_pattern"),
                schema_ref=o.get("schema_ref"),
                min_lines=o.get("min_lines"),
                validation_primitive=o.get("validation_primitive"),
            )
            for o in (d.get("outputs_produced") or [])
        )
        return cls(
            stage_id=d["stage_id"],
            route=d["route"],
            state=d["state"],
            phase_label=d["phase_label"],
            skill_invoked=d["skill_invoked"],
            inputs_required=inputs,
            outputs_produced=outputs,
            gate_predicate=d["gate_predicate"],
            on_input_missing=d["on_input_missing"],
            on_output_missing=d["on_output_missing"],
            parallel_with=tuple(d.get("parallel_with") or ()),
            optional=bool(d.get("optional", False)),
            notes=d.get("notes"),
        )


class ParseError(Exception):
    """Raised when stage-contracts.md cannot be parsed."""


def _resolve_default_path() -> Path:
    """Default stage-contracts.md sits at the harnessFlow root."""
    return Path(__file__).resolve().parents[2] / "stage-contracts.md"


def load_contracts(md_path: str | Path | None = None) -> list[StageContract]:
    """Parse the given markdown file (default: harnessFlow/stage-contracts.md)
    into a list of StageContract objects.

    Raises ParseError if yaml is unavailable or a block is malformed.
    """
    try:
        import yaml  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ParseError("pyyaml not installed; pip install pyyaml") from e

    path = Path(md_path) if md_path else _resolve_default_path()
    if not path.exists():
        raise ParseError(f"stage-contracts.md not found at {path}")

    content = path.read_text(encoding="utf-8")
    blocks = YAML_BLOCK_RE.findall(content)
    contracts: list[StageContract] = []
    for i, blk in enumerate(blocks):
        try:
            obj = yaml.safe_load(blk)
        except yaml.YAMLError as e:
            raise ParseError(f"yaml parse error in block #{i}: {e}") from e
        if not isinstance(obj, dict) or "stage_id" not in obj:
            continue  # non-contract yaml block (e.g. example)
        try:
            contracts.append(StageContract.from_dict(obj))
        except KeyError as e:
            raise ParseError(
                f"block #{i} (stage_id={obj.get('stage_id')}): missing required field {e}"
            ) from e
    if not contracts:
        raise ParseError(f"no stage contracts found in {path}")
    return contracts


def find_contract(
    contracts: list[StageContract], stage_id: str
) -> StageContract | None:
    """Linear lookup by stage_id. None if not found."""
    for c in contracts:
        if c.stage_id == stage_id:
            return c
    return None
