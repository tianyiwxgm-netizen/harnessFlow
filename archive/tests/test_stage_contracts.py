"""stage-contracts.md 自检（v1.1 Phase 9）

三段断言：
  1. schema valid —— 文档所有 yaml block 通过 stage-contract.schema.json
  2. coverage ≥ 80% —— A-F 每路线至少含 CLARIFY + (PLAN|RESEARCH) + (IMPL|DECISION_LOG) + VERIFY 4 必经 stage
  3. artifact catalog closure —— inputs_required[].artifact_ref 必须在其他 stage 的 outputs_produced[] 里有 producer（除 external / *invariant*）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover — optional dep
    yaml = None  # noqa: N816

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None  # noqa: N816


HARNESS_DIR = Path(__file__).resolve().parents[2]
STAGE_CONTRACTS_MD = HARNESS_DIR / "stage-contracts.md"
SCHEMA_JSON = HARNESS_DIR / "schemas" / "stage-contract.schema.json"

# yaml code block regex inside markdown
YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)

# Necessary-stage coverage per route: phase_label patterns that must appear
REQUIRED_PHASES_PER_ROUTE = {
    "A": {"@clarify", "@impl", "@verify", "@commit"},
    "B": {"@clarify", "@plan", "@impl", "@verify", "@commit"},
    "C": {"@clarify", "@plan", "@impl", "@verify", "@commit", "@retro"},
    "D": {"@impl", "@verify", "@commit"},
    "E": {"@plan", "@impl", "@verify", "@commit"},
    "F": {"@plan", "@verify"},
}


def load_contracts() -> list[dict]:
    """Parse all yaml code blocks from stage-contracts.md into a list of dicts."""
    if yaml is None:
        pytest.skip("pyyaml not installed")
    content = STAGE_CONTRACTS_MD.read_text(encoding="utf-8")
    blocks = YAML_BLOCK_RE.findall(content)
    contracts: list[dict] = []
    for blk in blocks:
        try:
            obj = yaml.safe_load(blk)
        except yaml.YAMLError as e:  # pragma: no cover
            pytest.fail(f"yaml parse error in stage-contracts.md block:\n{blk[:200]}\n{e}")
        if isinstance(obj, dict) and "stage_id" in obj:
            contracts.append(obj)
    assert contracts, "no stage contracts found in stage-contracts.md yaml blocks"
    return contracts


def test_stage_contracts_md_exists() -> None:
    assert STAGE_CONTRACTS_MD.exists(), f"missing {STAGE_CONTRACTS_MD}"


def test_schema_json_exists() -> None:
    assert SCHEMA_JSON.exists(), f"missing {SCHEMA_JSON}"
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    assert schema.get("$id", "").endswith("stage-contract.schema.json")
    assert "properties" in schema


def test_all_contracts_schema_valid() -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    contracts = load_contracts()
    errors: list[str] = []
    for c in contracts:
        for err in validator.iter_errors(c):
            errors.append(f"{c.get('stage_id')}: {err.message}")
    assert not errors, "schema violations:\n  - " + "\n  - ".join(errors)


def test_coverage_80_percent_per_route() -> None:
    """Every route A-F must cover at least 80% of its required phases."""
    contracts = load_contracts()
    by_route: dict[str, set[str]] = {r: set() for r in "ABCDEF"}
    for c in contracts:
        by_route[c["route"]].add(c["phase_label"])

    shortfall: list[str] = []
    for route, required in REQUIRED_PHASES_PER_ROUTE.items():
        actual = by_route.get(route, set())
        covered = required & actual
        ratio = len(covered) / len(required)
        if ratio < 0.8:
            missing = required - actual
            shortfall.append(f"{route}: coverage {ratio:.0%}, missing phases {missing}")

    assert not shortfall, "coverage shortfall:\n  - " + "\n  - ".join(shortfall)


def test_artifact_catalog_closure() -> None:
    """Every inputs_required[].artifact_ref must have a producer somewhere (same route or *invariant*/external)."""
    contracts = load_contracts()

    # Build producer set from outputs_produced across all contracts
    producers: dict[str, list[str]] = {}  # artifact_ref -> [stage_id, ...]
    for c in contracts:
        for out in c.get("outputs_produced", []):
            producers.setdefault(out["artifact_ref"], []).append(c["stage_id"])

    # external / invariant are allowed sources without a producer
    allowed_external = {"external", "*invariant*"}

    unresolved: list[str] = []
    for c in contracts:
        for req in c.get("inputs_required", []):
            ref = req["artifact_ref"]
            src = req["from_stage"]
            if src in allowed_external:
                continue
            # Check that src stage exists
            src_stage_exists = any(cc["stage_id"] == src for cc in contracts)
            if not src_stage_exists:
                unresolved.append(f"{c['stage_id']} inputs_required from {src} but no such stage_id")
                continue
            # Check that ref has any producer
            if ref not in producers:
                unresolved.append(f"{c['stage_id']} requires {ref} from {src}, but {ref} has no producer anywhere")

    assert not unresolved, "artifact catalog closure violations:\n  - " + "\n  - ".join(unresolved)


def test_no_circular_from_stage() -> None:
    """A stage cannot list itself in its inputs_required.from_stage."""
    contracts = load_contracts()
    circular: list[str] = []
    for c in contracts:
        for req in c.get("inputs_required", []):
            if req["from_stage"] == c["stage_id"]:
                circular.append(f"{c['stage_id']} depends on itself via {req['artifact_ref']}")
    assert not circular, "circular dependencies:\n  - " + "\n  - ".join(circular)


def test_stage_ids_unique() -> None:
    contracts = load_contracts()
    seen: set[str] = set()
    dups: list[str] = []
    for c in contracts:
        sid = c["stage_id"]
        if sid in seen:
            dups.append(sid)
        seen.add(sid)
    assert not dups, f"duplicate stage_ids: {dups}"


def test_flow_catalog_has_stage_contract_links() -> None:
    """flow-catalog.md should reference stage-contracts.md for each of 6 routes."""
    fc = HARNESS_DIR / "flow-catalog.md"
    content = fc.read_text(encoding="utf-8")
    links = re.findall(r"@stage-contract:", content)
    assert len(links) >= 6, f"expected ≥ 6 @stage-contract: links in flow-catalog.md, got {len(links)}"


def test_harnessflow_skill_has_validate_stage_io() -> None:
    hs = HARNESS_DIR / "harnessFlow-skill.md"
    content = hs.read_text(encoding="utf-8")
    assert "validate_stage_io" in content, "harnessFlow-skill.md must reference validate_stage_io (§ 5.5)"


def test_task_board_template_has_stage_artifacts_field() -> None:
    tbt = HARNESS_DIR / "task-board-template.md"
    content = tbt.read_text(encoding="utf-8")
    assert "stage_artifacts" in content, "task-board-template.md must declare stage_artifacts[] field"
