"""L1-04 · L2-06 · S5 TDDExe Verifier 编排器.

**职责**：接收 S4 ExecutionTrace → 调 Verifier subagent (IC-20 双签) → 返 VerifiedResult

**锚点**：
- docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-06-S5 TDDExe Verifier 编排器.md
- docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-06-S5 TDDExe Verifier 编排器-tests.md
- docs/3-1-Solution-Technical/integration/ic-contracts.md §3.20 IC-20 delegate_verifier

**包结构**：
- schemas.py              · VerificationRequest / VerifiedResult / IC20Command
- trace_adapter.py        · 从 L2-05 S4 ExecutionTrace 适配（WP05 mock · 将来真）
- signature_checker.py    · 双签验证（blueprint_slice + s4_snapshot）
- ic_20_dispatcher.py     · IC-20 delegate_verifier 生产端（调 L1-05 subagent · mock stub）
- orchestrator.py         · 主入口 orchestrate_s5(trace) → VerifiedResult
"""
from __future__ import annotations

from app.quality_loop.verifier.schemas import (
    IC20Command,
    IC20DispatchResult,
    SignatureCheckResult,
    VerificationRequest,
    VerifiedResult,
    VerifierError,
    VerifierVerdict,
)

__all__ = [
    "IC20Command",
    "IC20DispatchResult",
    "SignatureCheckResult",
    "VerificationRequest",
    "VerifiedResult",
    "VerifierError",
    "VerifierVerdict",
]
