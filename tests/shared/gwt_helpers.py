"""tests/shared/gwt_helpers.py · GWT(Given-When-Then) DSL(M3-WP01).

**定位**:
    给 acceptance 12 场景提供标准 GWT 结构 · 可读性优先 · 避 500-1500 行
    scenario 文件变"一锅乱 setup + assert"的线性脚本.

**核心**:
    - GWT · class-based context 管理器 · 三段结构(given / when / then)
    - gwt(description) · 装饰器 · 给 pytest 函数套 GWT 外壳
    - record_step(phase, msg) · 结构化记录当前步骤 · 失败诊断用

**设计哲学**:
    保留 pytest 原生风格 · 不强依赖 behave/pytest-bdd · 轻量组合进现有 fixture.

**用法示例**(acceptance scenario_01):
    async def test_wp_quality_loop(gwt, project_workspace, e2e_harness):
        async with gwt("WP quality loop · red→green→verify→PASS"):
            # Given
            gwt.given("干净 project + TDD blueprint 已生成")
            project_workspace.wbs_seed([{"id": "wp-1", "status": "READY"}])

            # When
            gwt.when("执行 S3 → S4 → S5 三段")
            await e2e_harness.tick_n(3)

            # Then
            gwt.then("verifier 给出 PASS · rollback router 不触发")
            # ... assertions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pytest

Phase = Literal["given", "when", "then", "and"]


@dataclass
class GWTStep:
    """GWT 单步记录 · 用于失败诊断输出."""

    phase: Phase
    message: str


@dataclass
class GWT:
    """Given-When-Then 上下文 · 逐步记录 + 失败时打印步骤链."""

    scenario: str
    steps: list[GWTStep] = field(default_factory=list)
    _entered: bool = False

    # ---------- context manager ----------

    async def __aenter__(self) -> GWT:
        self._entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self._print_step_chain()
        return False

    def __enter__(self) -> GWT:
        self._entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self._print_step_chain()
        return False

    # ---------- phase recorders ----------

    def given(self, message: str) -> GWT:
        self._record("given", message)
        return self

    def when(self, message: str) -> GWT:
        self._record("when", message)
        return self

    def then(self, message: str) -> GWT:
        self._record("then", message)
        return self

    def and_(self, message: str) -> GWT:
        """链式 AND 子步(并列于最近一个 phase)."""
        self._record("and", message)
        return self

    # ---------- internals ----------

    def _record(self, phase: Phase, message: str) -> None:
        self.steps.append(GWTStep(phase=phase, message=message))

    def _print_step_chain(self) -> None:
        """失败时打印完整步骤链 · 便于定位出错 phase."""
        print(f"\n--- GWT Scenario · {self.scenario} ---")
        for step in self.steps:
            print(f"  [{step.phase.upper():5}] {step.message}")
        print("--- GWT end (failed at last step) ---")

    def summary(self) -> str:
        lines = [f"Scenario · {self.scenario}"]
        lines.extend(f"  [{s.phase.upper():5}] {s.message}" for s in self.steps)
        return "\n".join(lines)


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def gwt(request: pytest.FixtureRequest) -> GWT:
    """GWT fixture · scenario 描述默认用 test function name.

    用法:
        async def test_panic_hard_redline(gwt):
            gwt.given("scheduler 处 RUNNING · 无 halt")
            ...
            gwt.when("用户按 panic 按钮")
            ...
            gwt.then("≤100ms scheduler 进 PAUSED")

    或者:
        async def test_something(gwt):
            async with gwt("custom scenario name"):
                gwt.given(...)
                ...

    **失败时**: 自动打印 step chain 到 stdout · 便于快速定位 phase.
    """
    gwt_instance = GWT(scenario=request.node.name)

    # 也允许 test 里手动 override scenario 名(调用风格): gwt("new name")
    original_call = GWT.__call__ if hasattr(GWT, "__call__") else None

    def _call(scenario: str) -> GWT:
        gwt_instance.scenario = scenario
        return gwt_instance

    gwt_instance.__class__.__call__ = staticmethod(_call)  # type: ignore[assignment]

    yield gwt_instance

    # teardown: 清掉 __call__ 避免污染后续 TC
    if original_call is not None:
        gwt_instance.__class__.__call__ = original_call  # type: ignore[assignment]
