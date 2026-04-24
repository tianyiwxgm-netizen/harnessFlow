"""WP08 · e2e · 场景 1 · DoD YAML → dod_compiler.compile → Gate.evaluate_gate 全链.

覆盖 WP01 (L2-02 DoD 编译器) → WP04 (L2-04 Gate 编译器) 的真实集成。

**铁律**:
- 全部真实 import(不 mock L2 接口)
- project_id 一致(PM-14 硬锁)
- YAML → CompiledDoD → EvaluatedDoD → GateVerdict 全链合约对齐
- verdict 幂等(dod_hash + metric_hash + rework_count 决定 verdict_id)
"""
from __future__ import annotations

import pytest

from app.quality_loop.dod_compiler import (
    DoDEvaluator,
    DoDExpressionCompiler,
)
from app.quality_loop.dod_compiler.predicate_eval import WhitelistRegistry
from app.quality_loop.gate_compiler.baseline_evaluator import BaselineEvaluator
from app.quality_loop.gate_compiler.checklist_compiler import ChecklistCompiler
from app.quality_loop.gate_compiler.dod_adapter import DoDAdapter
from app.quality_loop.gate_compiler.gate import (
    EvaluateGateCommand,
    GateCompiler,
    GateEvaluateResult,
    RewordCounter,
)
from app.quality_loop.gate_compiler.metric_sampler import MetricSampler
from app.quality_loop.gate_compiler.schemas import Baseline, GateAction


# =============================================================================
# fixtures (本文件内 local · 不打 conftest)
# =============================================================================


@pytest.fixture
def pid() -> str:
    """PM-14 顶层 project_id · 整个 e2e 链用同一个。"""
    return "proj-wp08-dod-gate"


@pytest.fixture
def registry() -> WhitelistRegistry:
    return WhitelistRegistry()


@pytest.fixture
def compiler(registry: WhitelistRegistry) -> DoDExpressionCompiler:
    return DoDExpressionCompiler(whitelist_registry=registry)


@pytest.fixture
def evaluator(compiler: DoDExpressionCompiler) -> DoDEvaluator:
    return DoDEvaluator(compiler, whitelist_registry=compiler.registry)


@pytest.fixture
def gate(evaluator: DoDEvaluator) -> GateCompiler:
    """Gate 编排器 · WP04 真实组合 WP01 adapter。"""
    return GateCompiler(
        dod_adapter=DoDAdapter(evaluator=evaluator),
        metric_sampler=MetricSampler(),
        rework_counter=RewordCounter(),
        baseline_evaluator=BaselineEvaluator(),
        checklist_compiler=ChecklistCompiler(),
    )


# 典型 DoD YAML · 含 hard/soft/metric 三分类
_HAPPY_DOD_YAML = """
dod:
  hard:
    - clause_id: hard-line-cov
      text: "line_coverage() >= 0.8"
      source_ac_ids: [ac-0001]
    - clause_id: hard-lint
      text: "lint_errors() == 0"
      source_ac_ids: [ac-0002]
  soft:
    - clause_id: soft-test-pass
      text: "test_pass_rate() >= 0.9"
      source_ac_ids: [ac-0003]
  metric:
    - clause_id: metric-p95
      text: "p95_ms() < 500"
      source_ac_ids: [ac-0004]
"""


# =============================================================================
# 场景 1.1 · happy path · DoD YAML → compile → evaluate → HARD_PASS
# =============================================================================


class TestDodToGateHappyPath:
    """WP01 compile → WP04 Gate · happy full chain."""

    def test_TC_E2E_DOD_GATE_01_yaml_compile_then_gate_hard_pass(
        self,
        compiler: DoDExpressionCompiler,
        gate: GateCompiler,
        pid: str,
    ) -> None:
        """TC-E2E-DOD-GATE-01 · YAML → compile → evaluate_gate → HARD_PASS + ADVANCE.

        验证全链对齐: YAML 解析 → AST 白名单校验 → expr 注册 →
        metric_snapshot 喂入 → predicate_eval → baseline 判定 → GateVerdict。
        """
        # 1. WP01 · YAML → CompiledDoD
        compile_result = compiler.compile_from_yaml(
            _HAPPY_DOD_YAML,
            project_id=pid,
            blueprint_id="bp-e2e-01",
            wp_id="wp-e2e-01",
        )
        assert compile_result.accepted is True
        assert compile_result.compiled is not None
        compiled = compile_result.compiled
        assert compiled.project_id == pid
        # hard=2 · soft=1 · metric=1
        assert len(compiled.hard) == 2
        assert len(compiled.soft) == 1
        assert len(compiled.metric) == 1
        # dod_hash 非空 · 后续 Gate 幂等 key 所需
        assert compiled.dod_hash != ""

        # 2. WP04 · Gate.evaluate_gate(compiled, metric)
        metrics = {
            "coverage": {"line_rate": 0.92},
            "lint": {"error_count": 0},
            "test_result": {"pass_count": 95, "fail_count": 5},
            "perf": {"p95_ms": 420},
        }
        result: GateEvaluateResult = gate.evaluate_gate(
            EvaluateGateCommand(
                project_id=pid,
                compiled=compiled,
                metrics=metrics,
                wp_id="wp-e2e-01",
            )
        )

        # 3. 断言 verdict 链路对齐
        assert result.verdict.baseline == Baseline.HARD_PASS
        assert result.verdict.action == GateAction.ADVANCE
        assert result.verdict.project_id == pid
        assert result.verdict.wp_id == "wp-e2e-01"
        # evaluated DoD 反馈链 · 2 hard 全通过
        assert result.evaluated.hard_total == 2
        assert result.evaluated.hard_passed == 2
        # checklist 随行
        assert result.checklist.total >= 2
        assert result.checklist.passed >= 2

    def test_TC_E2E_DOD_GATE_02_compile_then_gate_hard_fail_rework(
        self,
        compiler: DoDExpressionCompiler,
        gate: GateCompiler,
        pid: str,
    ) -> None:
        """TC-E2E-DOD-GATE-02 · coverage 不达标 · hard fail → REWORK + RETRY_S4.

        验证: predicate_eval 返 pass=False · baseline 正确归 REWORK ·
        rework_counter 首次触发 count=0→1。
        """
        compile_result = compiler.compile_from_yaml(
            _HAPPY_DOD_YAML, project_id=pid, wp_id="wp-rework-01",
        )
        assert compile_result.accepted
        compiled = compile_result.compiled

        metrics = {
            "coverage": {"line_rate": 0.50},  # < 0.8 · hard fail
            "lint": {"error_count": 0},
            "test_result": {"pass_count": 80, "fail_count": 20},
            "perf": {"p95_ms": 400},
        }
        result = gate.evaluate_gate(
            EvaluateGateCommand(
                project_id=pid, compiled=compiled, metrics=metrics, wp_id="wp-rework-01",
            )
        )
        assert result.verdict.baseline == Baseline.REWORK
        assert result.verdict.action == GateAction.RETRY_S4
        # hard 有 1 条失败(line_coverage)· 另 1 条过(lint)
        assert result.evaluated.hard_total == 2
        assert result.evaluated.hard_passed == 1


# =============================================================================
# 场景 1.2 · 幂等 + 升级 · 连续 rework ≥ 3 → ABORT
# =============================================================================


class TestDodToGateRewordEscalation:
    """同一 (dod_hash, metric_hash) 反复 REWORK · counter ≥ 3 → ABORT/UPGRADE。"""

    def test_TC_E2E_DOD_GATE_03_three_consecutive_rework_then_abort(
        self,
        compiler: DoDExpressionCompiler,
        gate: GateCompiler,
        pid: str,
    ) -> None:
        """TC-E2E-DOD-GATE-03 · 连 3 次 REWORK 后 · 第 4 次转 ABORT+UPGRADE_STAGE_GATE.

        验证: RewordCounter 累计 · baseline_evaluator 在 rework_count ≥ 3 升级。
        """
        compile_result = compiler.compile_from_yaml(
            _HAPPY_DOD_YAML, project_id=pid, wp_id="wp-abort-01",
        )
        compiled = compile_result.compiled
        bad_metrics = {
            "coverage": {"line_rate": 0.40},
            "lint": {"error_count": 0},
            "test_result": {"pass_count": 50, "fail_count": 50},
            "perf": {"p95_ms": 400},
        }

        baselines: list[Baseline] = []
        for _ in range(4):
            result = gate.evaluate_gate(
                EvaluateGateCommand(
                    project_id=pid,
                    compiled=compiled,
                    metrics=bad_metrics,
                    wp_id="wp-abort-01",
                )
            )
            baselines.append(result.verdict.baseline)

        # 前 3 次 REWORK · 第 4 次 ABORT(baseline_evaluator 阈值)
        assert baselines[:3] == [Baseline.REWORK, Baseline.REWORK, Baseline.REWORK]
        assert baselines[3] == Baseline.ABORT

    def test_TC_E2E_DOD_GATE_04_verdict_id_idempotent(
        self,
        compiler: DoDExpressionCompiler,
        gate: GateCompiler,
        pid: str,
    ) -> None:
        """TC-E2E-DOD-GATE-04 · verdict_id 幂等 · 同 (dod_hash, metric_hash, rework_count).

        两次连续绿灯 · verdict_id 应稳定(rework_count=0 保持)。
        """
        compile_result = compiler.compile_from_yaml(
            _HAPPY_DOD_YAML, project_id=pid, wp_id="wp-idem-01",
        )
        compiled = compile_result.compiled
        metrics = {
            "coverage": {"line_rate": 0.95},
            "lint": {"error_count": 0},
            "test_result": {"pass_count": 100, "fail_count": 0},
            "perf": {"p95_ms": 300},
        }
        cmd = EvaluateGateCommand(
            project_id=pid, compiled=compiled, metrics=metrics, wp_id="wp-idem-01",
        )
        r1 = gate.evaluate_gate(cmd)
        r2 = gate.evaluate_gate(cmd)
        # HARD_PASS 不触发 rework 累计 · 两次应完全相同
        assert r1.verdict.verdict_id == r2.verdict.verdict_id
        assert r1.verdict.baseline == r2.verdict.baseline == Baseline.HARD_PASS
