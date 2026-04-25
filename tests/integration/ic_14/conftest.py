"""IC-14 集成 fixtures · 真实 orchestrate_s5 + ControlledDelegator/Waiter.

WP04 任务表 IC-14 = stage_gate_verdict (main-1 L1-04 verifier orchestrator).
铁律: 真实 import L1-04 verifier · 边界 (delegator / waiter / audit) 替身.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.quality_loop.verifier.schemas import IC20Command, IC20DispatchResult
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace


@pytest.fixture
def project_id() -> str:
    return "proj-ic14"


@pytest.fixture
def make_trace(project_id: str):
    """工厂 · 一行造合法 MockExecutionTrace."""

    def _make(
        *,
        wp_id: str = "wp-ic14-1",
        git_head: str = "abc123def4",
        passed: int = 10,
        failed: int = 0,
        coverage: float = 0.85,
        coverage_gate: float = 0.8,
        pid: str | None = None,
    ) -> MockExecutionTrace:
        return MockExecutionTrace(
            project_id=pid or project_id,
            wp_id=wp_id,
            git_head=git_head,
            blueprint_slice={
                "dod_expression": "tests_pass",
                "red_tests": ["r1"],
            },
            main_session_id="main-ic14",
            ts="2026-04-24T10:00:00Z",
            artifact_refs=("app/feature.py",),
            test_report={
                "passed": passed,
                "failed": failed,
                "coverage": coverage,
            },
            acceptance_criteria={"coverage_gate": coverage_gate},
        )

    return _make


class ControlledDelegator:
    """可配置 IC-20 delegator 替身 · queue 控制每次返回."""

    def __init__(self, *, queue: list[Any] | None = None) -> None:
        self.queue: list[Any] = list(queue or [])
        self.calls: list[IC20Command] = []

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.queue):
            b = self.queue[idx]
            if isinstance(b, Exception):
                raise b
            return b
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id="sub-default-001",
        )


class ControlledWaiter:
    """可配置 verifier callback waiter 替身."""

    def __init__(
        self,
        *,
        output: dict[str, Any] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.output = output
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    async def wait(
        self,
        *,
        delegation_id: str,
        verifier_session_id: str,
        timeout_s: int,
    ) -> dict[str, Any]:
        self.calls.append({
            "delegation_id": delegation_id,
            "verifier_session_id": verifier_session_id,
            "timeout_s": timeout_s,
        })
        if self.exc is not None:
            raise self.exc
        return self.output or {}


class InMemoryAuditEmitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, dict(payload)))


@pytest.fixture
def delegator() -> ControlledDelegator:
    return ControlledDelegator(queue=[
        IC20DispatchResult(
            delegation_id="ver-ic14",
            dispatched=True,
            verifier_session_id="sub-ic14-001",
        ),
    ])


@pytest.fixture
def audit_emitter() -> InMemoryAuditEmitter:
    return InMemoryAuditEmitter()


def out_pass() -> dict[str, Any]:
    return {
        "blueprint_alignment": {
            "dod_expression": "tests_pass",
            "red_tests": ["r1"],
        },
        "s4_diff_analysis": {
            "passed": 10,
            "failed": 0,
            "coverage": 0.85,
        },
        "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        "verifier_report_id": "vr-ic14-001",
    }


def out_fail_l3_dod_unmet() -> dict[str, Any]:
    return {
        "blueprint_alignment": {
            "dod_expression": "tests_pass",
            "red_tests": ["r1"],
        },
        "s4_diff_analysis": {
            "passed": 10,
            "failed": 0,
            "coverage": 0.65,  # 低于 gate 0.8
        },
        "dod_evaluation": {"verdict": "FAIL_L3", "all_pass": False},
        "verifier_report_id": "vr-ic14-002",
    }


async def no_sleep(_: float) -> None:
    return None
