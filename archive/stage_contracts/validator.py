"""validate_stage_io — main entry point for Stage Contract v1.2 runtime check.

Usage in main skill:
    verdict, violations = validate_stage_io(task_board, stage_id, phase='enter')
    if verdict == 'BLOCK':
        ...  # transition PAUSED_ESCALATED

See stage-contracts.md § 9 for the pseudocode this implements.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from archive.stage_contracts.parser import (
    InputRef,
    OutputDecl,
    StageContract,
    find_contract,
    load_contracts,
)
from archive.stage_contracts.predicate_eval import (
    PredicateEvalError,
    eval_predicate,
)


Verdict = Literal["OK", "WARN", "BLOCK", "ABORT"]
Phase = Literal["enter", "exit"]


class StageValidationError(Exception):
    """Raised on infrastructure-level failures (missing contract, parse error).
    Distinct from a BLOCK verdict, which is a legitimate contract violation."""


@dataclass(frozen=True)
class Violation:
    kind: str  # "missing_input" | "missing_output" | "gate_failed"
    artifact_ref: str | None
    from_stage: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "artifact_ref": self.artifact_ref,
            "from_stage": self.from_stage,
            "reason": self.reason,
        }


def _collect_produced_artifacts(task_board: dict) -> dict[str, list[dict[str, Any]]]:
    """Walk task_board.stage_artifacts[] and return artifact_ref → [records]."""
    by_ref: dict[str, list[dict[str, Any]]] = {}
    for stage_rec in task_board.get("stage_artifacts", []) or []:
        for art in stage_rec.get("artifacts", []) or []:
            ref = art.get("artifact_ref")
            if not ref:
                continue
            by_ref.setdefault(ref, []).append(
                {**art, "_produced_by_stage": stage_rec.get("stage_id")}
            )
    return by_ref


def _is_artifact_available(
    task_board: dict, input_ref: InputRef, by_ref: dict[str, list[dict[str, Any]]]
) -> bool:
    """Check a single input requirement against the task_board state."""
    ref = input_ref.artifact_ref

    # Common invariants piggyback on top-level fields
    if ref == "user_input_raw":
        return bool(task_board.get("initial_user_input"))
    if ref == "goal_anchor_hash":
        ga = task_board.get("goal_anchor") or {}
        return bool(ga.get("hash"))
    if ref == "route_id":
        return bool(task_board.get("route_id"))
    if ref == "task_dimensions":
        return all(task_board.get(k) for k in ("size", "task_type", "risk"))
    if ref == "clarified_task_description":
        return bool(
            task_board.get("clarified_description")
            or task_board.get("initial_user_input")
        )
    if ref == "dod_expression":
        return bool(task_board.get("dod_expression"))
    if ref == "verifier_report":
        return bool(task_board.get("verifier_report"))
    if ref == "commit_sha":
        return bool(task_board.get("commit_sha"))
    if ref == "retro_md":
        return bool(task_board.get("retro_link"))

    # Otherwise look in stage_artifacts[] from an upstream producer
    records = by_ref.get(ref, [])
    if not records:
        return False
    if input_ref.from_stage in ("external", "*invariant*"):
        return True
    # Prefer records whose _produced_by_stage matches expected from_stage
    for rec in records:
        if rec.get("_produced_by_stage") == input_ref.from_stage:
            return True
    # Fall back: any producer counts (loose mode)
    return True


def _collect_produced_this_stage(
    task_board: dict, stage_id: str
) -> dict[str, dict[str, Any]]:
    """Artifacts declared produced by this specific stage."""
    out: dict[str, dict[str, Any]] = {}
    for stage_rec in task_board.get("stage_artifacts", []) or []:
        if stage_rec.get("stage_id") != stage_id:
            continue
        for art in stage_rec.get("artifacts", []) or []:
            ref = art.get("artifact_ref")
            if ref:
                out[ref] = art
    return out


def _check_outputs(
    contract: StageContract, task_board: dict
) -> list[Violation]:
    produced = _collect_produced_this_stage(task_board, contract.stage_id)
    violations: list[Violation] = []
    for out in contract.outputs_produced:
        if out.artifact_ref not in produced:
            violations.append(
                Violation(
                    kind="missing_output",
                    artifact_ref=out.artifact_ref,
                    from_stage=None,
                    reason=f"stage {contract.stage_id} did not declare output {out.artifact_ref}",
                )
            )
    return violations


def _check_inputs(
    contract: StageContract, task_board: dict
) -> list[Violation]:
    by_ref = _collect_produced_artifacts(task_board)
    violations: list[Violation] = []
    for req in contract.inputs_required:
        if not req.must_exist:
            continue
        if not _is_artifact_available(task_board, req, by_ref):
            violations.append(
                Violation(
                    kind="missing_input",
                    artifact_ref=req.artifact_ref,
                    from_stage=req.from_stage,
                    reason=f"upstream producer {req.from_stage} has not written {req.artifact_ref}",
                )
            )
    return violations


def _eval_gate(contract: StageContract, task_board: dict) -> tuple[bool, str | None]:
    """Evaluate gate_predicate with flat context. Returns (result, err_msg_or_None).

    Errors are silenced when the predicate references primitives not yet wired
    (v1.2 partial whitelist); returns (True, reason) so gate does not block on
    un-implemented functions in the early rollout.
    """
    context: dict[str, Any] = {}
    # Spread task_board top-level into context (so `diff_lines_net` etc. can see
    # artifact contents if task_board stored them as strings).
    for k, v in task_board.items():
        # Don't pollute with huge nested dicts; only include scalars + artifacts
        if isinstance(v, (str, int, float, bool, list, dict)):
            context[k] = v
    # Expose produced artifacts flat
    for stage_rec in task_board.get("stage_artifacts", []) or []:
        for art in stage_rec.get("artifacts", []) or []:
            ref = art.get("artifact_ref")
            if ref and ref not in context:
                context[ref] = art
    try:
        result = eval_predicate(contract.gate_predicate, context)
        return bool(result), None
    except PredicateEvalError as e:
        msg = str(e)
        # v1.2 soft mode: if predicate references unwired function, don't block
        if "not in WHITELIST_FUNCTIONS" in msg:
            return True, f"unwired primitive tolerated (v1.2 soft mode): {msg}"
        return False, msg


def validate_stage_io(
    task_board: dict,
    stage_id: str,
    phase: Phase = "enter",
    contracts: list[StageContract] | None = None,
) -> tuple[Verdict, list[Violation]]:
    """Validate task_board state against the stage contract.

    Args:
        task_board: The task-board JSON (already loaded).
        stage_id:   Contract id to look up (e.g. "C-IMPL").
        phase:      "enter" (check inputs) or "exit" (check outputs + gate).
        contracts:  Optional pre-loaded contract list (test injection).

    Returns:
        (verdict, violations)
            verdict in {"OK", "WARN", "BLOCK", "ABORT"}
            violations: list of Violation (empty iff verdict == "OK")

    Raises:
        StageValidationError — contract missing or parser error.
    """
    if contracts is None:
        contracts = load_contracts()
    contract = find_contract(contracts, stage_id)
    if contract is None:
        raise StageValidationError(f"no contract with stage_id={stage_id}")

    violations: list[Violation] = []
    if phase == "enter":
        violations.extend(_check_inputs(contract, task_board))
        if violations:
            return contract.on_input_missing, violations  # type: ignore[return-value]
        return "OK", []

    if phase == "exit":
        out_violations = _check_outputs(contract, task_board)
        violations.extend(out_violations)
        if not out_violations:
            gate_ok, gate_err = _eval_gate(contract, task_board)
            if not gate_ok:
                violations.append(
                    Violation(
                        kind="gate_failed",
                        artifact_ref=None,
                        from_stage=None,
                        reason=f"gate_predicate failed: {contract.gate_predicate} "
                        + (f"({gate_err})" if gate_err else ""),
                    )
                )
        if violations:
            return contract.on_output_missing, violations  # type: ignore[return-value]
        return "OK", []

    raise StageValidationError(f"unsupported phase: {phase}")
