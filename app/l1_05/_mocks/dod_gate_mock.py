"""L1-04 DoD gate mock — 波5 替换为主-1 L1-04 L2-02 真实 DoD evaluator.

TODO:MOCK-REPLACE-FROM-主-1 — 主-1 L1-04 L2-02 DoD expression compiler 完工后
删除本 mock · 改为 `from app.l1_04.l2_02.dod_evaluator import DoDEvaluator`。

契约：dod_gate_check(project_id, capability, result_id, artifact) -> DoDGateVerdict。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"]


@dataclass
class DoDGateVerdict:
    verdict: Verdict
    reason: str
    confidence: float      # 0..1
    evidence: dict[str, str]


class DoDGateMock:
    """默认放行（PASS）· 可注入特定 capability 的裁决 overrides."""

    def __init__(self, overrides: dict[str, Verdict] | None = None) -> None:
        self._overrides = overrides or {}

    def dod_gate_check(
        self,
        project_id: str,
        capability: str,
        result_id: str,
        artifact: dict,
    ) -> DoDGateVerdict:
        if not project_id:
            raise ValueError("DoDGate: project_id required (PM-14)")
        verdict: Verdict = self._overrides.get(capability, "PASS")
        return DoDGateVerdict(
            verdict=verdict,
            reason="mock-default" if verdict == "PASS" else "mock-override",
            confidence=1.0 if verdict == "PASS" else 0.0,
            evidence={"mock": "true", "result_id": result_id},
        )
