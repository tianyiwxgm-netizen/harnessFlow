"""archive.stage_contracts — v1.2 runtime validator for harnessFlow stage contracts.

Public API:
    - StageContract (dataclass)
    - load_contracts(path) -> list[StageContract]
    - validate_stage_io(task_board, stage_id, phase) -> (verdict, violations)
    - eval_predicate(expr_str, context) -> bool

See stage-contracts.md § 9 for the full integration semantics.

v1.2 scope: parser + predicate_eval + validator + CLI. Stop gate + Supervisor
auto-trigger integration defers to v1.3 (explicit Edit in hooks/).
"""
from __future__ import annotations

from archive.stage_contracts.parser import StageContract, load_contracts
from archive.stage_contracts.predicate_eval import (
    PredicateEvalError,
    eval_predicate,
    WHITELIST_FUNCTIONS,
)
from archive.stage_contracts.validator import (
    StageValidationError,
    validate_stage_io,
)

__all__ = [
    "StageContract",
    "load_contracts",
    "eval_predicate",
    "PredicateEvalError",
    "WHITELIST_FUNCTIONS",
    "validate_stage_io",
    "StageValidationError",
]

__version__ = "1.2.0-alpha"
