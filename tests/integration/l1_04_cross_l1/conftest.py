"""WP09 跨 L1 集成 · 共享 fixtures.

**真实代码**: EventBus / IC14Consumer / orchestrate_s5 / VerdictClassifier /
StageMapper / RollbackExecutor 等 L1 模块全部真实 import.

**测试替身** (仅跨进程边界):
- StateTransitionSpy · L1-02 IC-01 真实实现是跨进程 · spy 记录调用即可
- DelegateVerifierStub · L1-05 真实 delegator 跑独立 session · stub 返 dispatched=True
- CallbackWaiterStub · verifier 独立 session 异步回调 · stub 直接返约定 payload

**PM-14 红线**: 所有 fixture 默认 project_id="proj-wp09"，跨 pid 用例显式改值.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.quality_loop.verifier.schemas import IC20Command, IC20DispatchResult


# ---------------------------------------------------------------------------
# 通用 project_id fixture（PM-14 根字段）
# ---------------------------------------------------------------------------


@pytest.fixture
def project_id() -> str:
    """WP09 默认 project_id · 所有 TC 以此为根."""
    return "proj-wp09"


# ---------------------------------------------------------------------------
# 真实 EventBus (L1-09 IC-09) · 跨 L1 审计验证用
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 EventBus 物理根目录 · 每 TC 独立 tmp_path."""
    return tmp_path / "bus_root"


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · append 写 jsonl · 供 AuditQuery 真查.

    WP09 用真 bus 代替 MockEventBus · 确保 L1-04 → L1-09 IC-09 的实际
    hash-chain / shard / audit event 全链跑通.
    """
    return EventBus(event_bus_root)


# ---------------------------------------------------------------------------
# L1-02 IC-01 state_transition 替身 (真实跑 L1-02 需要跨进程状态机)
# ---------------------------------------------------------------------------


@dataclass
class StateTransitionSpy:
    """L1-02 IC-01 state_transition 测试替身 · 记录所有调用 · 返 OK.

    真实 L1-02 实现 (Dev-δ merged) 是跨进程状态机 · 在单元集成层无法直接挂.
    本 spy 验证 L1-04 → L1-02 契约字段完整（PM-14 project_id + wp_id +
    new_wp_state + escalated + route_id + target_stage + severity + level_count）.
    """

    calls: list[dict[str, Any]] = field(default_factory=list)

    async def state_transition(
        self,
        *,
        project_id: str,
        wp_id: str,
        new_wp_state: str,
        escalated: bool,
        route_id: str,
        **extra: Any,
    ) -> dict[str, Any]:
        record = {
            "project_id": project_id,
            "wp_id": wp_id,
            "new_wp_state": new_wp_state,
            "escalated": escalated,
            "route_id": route_id,
            **extra,
        }
        self.calls.append(record)
        return {"transitioned": True, **record}


@pytest.fixture
def state_spy() -> StateTransitionSpy:
    return StateTransitionSpy()


# ---------------------------------------------------------------------------
# L1-05 IC-20 delegator 替身 (verifier 独立 session 的起点)
# ---------------------------------------------------------------------------


@dataclass
class DelegateVerifierStub:
    """L1-05 IC-20 delegate_verifier 测试替身 · 模拟独立 session 分配.

    真实 Dev-γ delegator 会起 sub-agent session · 消耗 token / API.
    本 stub 直接返 dispatched=True + sub- 前缀合法 session_id · 保证
    L1-04 verifier orchestrator 的 IC-20 前缀硬红线校验通过.
    """

    session_prefix: str = "sub-wp09"
    calls: list[IC20Command] = field(default_factory=list)
    # 注入异常队列 (list of Exception | None) · 测试重试路径
    error_queue: list[Exception | None] = field(default_factory=list)

    async def delegate_verifier(self, command: IC20Command) -> IC20DispatchResult:
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.error_queue):
            err = self.error_queue[idx]
            if err is not None:
                raise err
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id=f"{self.session_prefix}-{len(self.calls):03d}",
        )


@pytest.fixture
def delegate_stub() -> DelegateVerifierStub:
    return DelegateVerifierStub()


# ---------------------------------------------------------------------------
# CallbackWaiter 替身 (verifier 独立 session 的异步回调)
# ---------------------------------------------------------------------------


@dataclass
class CallbackWaiterStub:
    """verifier 独立 session 回调等待器 · 测试直接返 in-memory dict.

    真实实现要么订阅 L1-09 事件 verifier_verdict · 要么 poll
    verifier_reports/<sid>.json · WP09 集成只验契约 payload 格式 ·
    stub 直接返预置结果.
    """

    output: dict[str, Any] | None = None
    exc: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

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
        return dict(self.output or {})


@pytest.fixture
def pass_verifier_output() -> dict[str, Any]:
    """verifier 独立 session 回调: 全绿 DoD PASS 标准 payload."""
    return {
        "blueprint_alignment": {
            "dod_expression": "tests_pass_and_coverage_ge_80",
            "red_tests": ["t1", "t2"],
        },
        "s4_diff_analysis": {"passed": 12, "failed": 0, "coverage": 0.85},
        "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        "verifier_report_id": "vr-wp09-001",
    }


@pytest.fixture
def fail_l3_verifier_output() -> dict[str, Any]:
    """verifier DoD gate 未过: 双签 OK · DoD 失败 → FAIL_L3.

    注意: blueprint_alignment 必须与 blueprint_slice 字段级完全一致（含 red_tests），
    s4_diff_analysis 必须与 test_report 字段一致（passed/failed 严格 · coverage ±0.05）.
    """
    return {
        "blueprint_alignment": {
            "dod_expression": "tests_pass_and_coverage_ge_80",
            "red_tests": ["t1", "t2"],  # 与 make_trace blueprint_slice 对齐
        },
        "s4_diff_analysis": {"passed": 10, "failed": 0, "coverage": 0.60},
        "dod_evaluation": {
            "verdict": "FAIL_L3",
            "all_pass": False,
            "failed_gates": ["coverage_ge_80"],
        },
        "verifier_report_id": "vr-wp09-fail3",
    }


# ---------------------------------------------------------------------------
# no_sleep · 加速测试（不实际 backoff）
# ---------------------------------------------------------------------------


@pytest.fixture
def no_sleep():
    """orchestrator 默认 asyncio.sleep · 替成 noop 避 4s/8s 退避."""
    async def _no_sleep(_: float) -> None:
        return None
    return _no_sleep


# ---------------------------------------------------------------------------
# trace fixture · 构造 S4 ExecutionTrace 交给 verifier
# ---------------------------------------------------------------------------


@pytest.fixture
def make_trace(project_id: str):
    """构造 MockExecutionTrace (WP06 trace_adapter 鸭子契约)."""
    from app.quality_loop.verifier.trace_adapter import MockExecutionTrace

    def _mk(**overrides: Any) -> MockExecutionTrace:
        defaults: dict[str, Any] = {
            "project_id": project_id,
            "wp_id": "wp-int-1",
            "git_head": "abc1234567",
            "blueprint_slice": {
                "dod_expression": "tests_pass_and_coverage_ge_80",
                "red_tests": ["t1", "t2"],
            },
            "main_session_id": "main-wp09",
            "ts": "2026-04-23T10:00:00Z",
            "artifact_refs": ("app/feature.py", "tests/test_feature.py"),
            "test_report": {"passed": 12, "failed": 0, "coverage": 0.85},
            "acceptance_criteria": {"coverage_gate": 0.8},
        }
        defaults.update(overrides)
        return MockExecutionTrace(**defaults)

    return _mk


# ---------------------------------------------------------------------------
# AuditEmitter · 挂到 L1-04 · 把 audit event 写 L1-09 真 bus
# ---------------------------------------------------------------------------


@pytest.fixture
def ic09_audit_emitter(real_event_bus: EventBus, project_id: str):
    """L1-04 orchestrator 的 audit_emitter 挂真 L1-09 EventBus.

    对齐 IC-09 真契约: L1-04 emit event type 必在白名单 L1-04:* ·
    actor=verifier · pid 必有（默认从 fixture project_id 取 · payload 可覆盖）.
    """
    from datetime import UTC, datetime

    from app.l1_09.event_bus.schemas import Event

    async def emit(event_type: str, payload: dict[str, Any]) -> None:
        pid = payload.get("project_id", project_id)
        evt = Event(
            project_id=pid,
            type=event_type,
            actor="verifier",
            payload=dict(payload),
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)

    return emit


# ---------------------------------------------------------------------------
# KB Read Service 替身 (真实 KBReadService 需要 scope_checker + reranker + repo)
# ---------------------------------------------------------------------------


@dataclass
class FakeKBRepo:
    """L1-06 KB repo 极简实现 · 返预置条目 · 供 DoD 编译时 kb_read 使用."""

    session_entries: list[Any] = field(default_factory=list)
    project_entries: list[Any] = field(default_factory=list)
    global_entries: list[Any] = field(default_factory=list)

    def read_session(self, _ctx: Any, kinds: Any) -> list[Any]:
        return list(self.session_entries)

    def read_project(self, _ctx: Any, kinds: Any) -> list[Any]:
        return list(self.project_entries)

    def read_global(self, kinds: Any) -> list[Any]:
        return list(self.global_entries)


@dataclass
class FakeScopeChecker:
    """L1-06 scope_checker 替身 · 允许所有请求 scope."""

    allowed: list[str] = field(default_factory=lambda: ["session", "project", "global"])

    def scope_check(self, req: Any) -> Any:
        from app.knowledge_base.reader.schemas import ScopeCheckResult

        return ScopeCheckResult(
            allowed_scopes=list(self.allowed),
            isolation_ctx={"project_id": req.project_id},
        )


@dataclass
class FakeReranker:
    """L1-06 reranker 替身 · 直接按 observed_count DESC 返."""

    def rerank(self, req: Any) -> Any:
        from app.knowledge_base.reader.schemas import RerankResponse

        ranked = sorted(
            req.candidates,
            key=lambda e: -int(getattr(e, "observed_count", 0) or 0),
        )[: req.top_k]
        return RerankResponse(ranked=ranked, signals_used=["observed_count"])


@dataclass
class AuditSink:
    """极简 audit sink · KBReadService 的 _emit 调用写这里."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def append(self, *, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, "payload": dict(payload)})
