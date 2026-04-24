"""tests/shared/ · 全局 pytest fixtures(M3-WP01).

**这是 main-3 集成测试共用 conftest** · 所有 tests/integration/ 与
tests/acceptance/ 子目录里的 fixture 可直接复用本模块导出的对象.

**契约**:
    - 所有 fixture 默认 `project_id` PM-14 根字段一致(`proj-m3-shared`)
    - `tmp_path` 隔离 · 每 TC 独立文件系统根
    - 真实 L1-09 EventBus(IC-09 唯一写入口) 挂在临时 bus 根
    - 其他 L1 · 真实 import(禁改 app/)

**设计目标**:
    - 给 IC 20 份 + matrix/pm14/failure/perf 共用 fixture
    - 给 acceptance 12 scenario 共用 fixture
    - 禁重复写 `project_id` / `event_bus` / `tmp_root` 的 boilerplate

**参考**:
    - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/main-3-integration-and-acceptance.md §3 WP01
    - tests/integration/l1_04_cross_l1/conftest.py(WP09 局部 conftest · 本模块是其提炼版)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus

# Re-export fixtures from sibling modules so `pytest` sees them
# automatically under tests/shared/**. 下游只要 conftest 被 pytest 收到 ·
# 不需再手 import 各文件里的 fixture.
from tests.shared.project_factory import project_factory, project_workspace  # noqa: F401
from tests.shared.stubs import (
    AuditSink,
    CallbackWaiterStub,
    DelegateVerifierStub,
    FakeKBRepo,
    FakeLLMClient,
    FakeReranker,
    FakeScopeChecker,
    FakeSkillInvoker,
    FakeToolClient,
    StateTransitionSpy,
)


# =============================================================================
# PM-14 分片根字段 · project_id
# =============================================================================


@pytest.fixture
def project_id() -> str:
    """集成测试默认 project_id · 所有跨 L1 fixture 以此为 PM-14 分片根.

    覆盖方法: 在测试文件内 override(如跨 pid 用例):
        @pytest.fixture
        def project_id() -> str:
            return "proj-other"
    """
    return "proj-m3-shared"


@pytest.fixture
def other_project_id() -> str:
    """PM-14 测试用的**另一** project_id · 专项跨 pid 隔离测试.

    用于 matrix / pm14-violation 测试:
        foo_pid = project_id, bar_pid = other_project_id,
        断言 foo 的事件不泄到 bar 的分片.
    """
    return "proj-m3-shared-other"


# =============================================================================
# tmp_root · 每 TC 独立文件系统根(L1-09 bus root / kb root / lock root 共根)
# =============================================================================


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """每 TC 独立物理根 · 下辖 bus / kb / lock / ckpt 子目录.

    结构:
        tmp_root/
            bus_root/       L1-09 event_bus 根(events.jsonl / meta.json)
            kb_root/        L1-06 kb 物理存储根
            lock_root/      L1-09 lock_manager 持锁根
            ckpt_root/      L1-09 checkpoint/crash_safety 根
            projects/       L1-02 stage_gate / L1-03 wbs 项目文件根
    """
    return tmp_path


@pytest.fixture
def event_bus_root(tmp_root: Path) -> Path:
    """L1-09 EventBus 物理根 · events.jsonl + meta.json 落盘位置."""
    root = tmp_root / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def kb_root(tmp_root: Path) -> Path:
    """L1-06 KB 物理存储根 · session/project/global 三层子目录."""
    root = tmp_root / "kb_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def lock_root(tmp_root: Path) -> Path:
    """L1-09 LockManager 持锁物理根(文件锁模式)."""
    root = tmp_root / "lock_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def ckpt_root(tmp_root: Path) -> Path:
    """L1-09 Checkpoint / crash_safety 物理根(ckpt_*.json)."""
    root = tmp_root / "ckpt_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def projects_root(tmp_root: Path) -> Path:
    """L1-02 stage_gate + L1-03 wbs · 项目工作目录根.

    每个 project_id 在此下建子目录: projects/<pid>/
    含 chart.json / wbs.json / gates.json / quality.json 等.
    """
    root = tmp_root / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


# =============================================================================
# L1-09 真实 EventBus · IC-09 审计唯一写入口
# =============================================================================


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · append 写 jsonl · 供跨 L1 集成侧真查.

    用 real_event_bus 而不 MockEventBus 的理由:
        1. M3 集成测试**就是要测 L1 → L1-09 IC-09 的端到端链**
        2. 真 bus 带 hash-chain / shard / halt_guard 全链路
        3. 下游的 assert_ic_09_emitted / assert_audit_event_in_pid
           必须查真实落盘的 events.jsonl
    """
    return EventBus(event_bus_root)


# =============================================================================
# no_sleep · 加速 backoff / 重试 · 避免集成测试实际跑 4s/8s 退避
# =============================================================================


@pytest.fixture
def no_sleep():
    """替换 asyncio.sleep 为 noop · 保留 await 语义 · 不阻塞.

    典型用法(集成 orchestrator 的重试退避):
        async def test_retry(no_sleep, monkeypatch):
            import asyncio
            monkeypatch.setattr(asyncio, "sleep", no_sleep)
            # ...
    """
    async def _no_sleep(_: float) -> None:
        return None
    return _no_sleep


# =============================================================================
# Stubs · 跨 L1 mock 基础设施 fixture(每 TC 独立实例 · 避共享状态泄)
# =============================================================================


@pytest.fixture
def state_spy() -> StateTransitionSpy:
    """L1-02 IC-01 state_transition spy · 每 TC 独立."""
    return StateTransitionSpy()


@pytest.fixture
def delegate_stub() -> DelegateVerifierStub:
    """L1-05 IC-20 delegate_verifier stub · 每 TC 独立."""
    return DelegateVerifierStub()


@pytest.fixture
def callback_waiter() -> CallbackWaiterStub:
    """Verifier 独立 session 回调等待 stub · 每 TC 独立.

    测试内手动 set output / exc 来控制:
        callback_waiter.output = {"verdict": "PASS", ...}
    """
    return CallbackWaiterStub()


@pytest.fixture
def fake_kb_repo() -> FakeKBRepo:
    """L1-06 KB 3 层 in-memory repo · 每 TC 独立."""
    return FakeKBRepo()


@pytest.fixture
def fake_scope_checker() -> FakeScopeChecker:
    return FakeScopeChecker()


@pytest.fixture
def fake_reranker() -> FakeReranker:
    return FakeReranker()


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    """通用 LLM 调用替身 · 支持 responses 映射.

    测试内注入:
        fake_llm.responses["decompose_wbs"] = "..."
    """
    return FakeLLMClient()


@pytest.fixture
def fake_skill_invoker() -> FakeSkillInvoker:
    """L1-05 skill invoker 替身 · 支持 outputs + error_queue."""
    return FakeSkillInvoker()


@pytest.fixture
def fake_tool_client() -> FakeToolClient:
    """通用工具客户端替身(L1-05/L1-08 跨工具用)."""
    return FakeToolClient()


@pytest.fixture
def audit_sink() -> AuditSink:
    """旁路 audit sink · 只记录不写盘(不取代 real_event_bus · 辅用)."""
    return AuditSink()
