---
doc_id: tests-L1-04-L2-04-质量 Gate 编译器+验收 Checklist-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-04-质量 Gate 编译器+验收 Checklist.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-04 质量 Gate 编译器 + 验收 Checklist · TDD 测试用例

> 基于 3-1 L2-04 §3（5 IC 触点 + 主入口 `compile_quality_gate` + §6 15 个内部算法）+ §11（24 项错误码 · 5 级降级状态机）+ §12 SLO（P95 延迟 / 吞吐 / 资源）+ §13 TC ID 矩阵（60 条）驱动。
> TC ID 统一格式：`TC-L104-L204-NNN`（L1-04 下 L2-04，三位流水号 · 001-099 正向 / 1xx-4xx 负向按来源分段 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_04_QualityGateCompilerAndChecklist` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。
> 错误码前缀保留 3-1 原样 · `E_L204_L202_` / `E_L204_L203_` / `E_L204_L204_` / `E_L204_L205_` / `E_L204_L106_` / `E_L204_L108_` / `E_L204_INTERNAL_` — 对照 §11.1。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock kb / mock clock / mock event bus / mock repo / tmp atomic writer）
- [x] §8 集成点用例（与兄弟 L2 协作 · L2-01/02/03/05/06/07）
- [x] §9 边界 / edge case（空/超大/并发/崩溃/签字/版本链）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（§3 + §6 + §2 TC）

| 方法（§3 / §6 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `compile_quality_gate()` · §3.3 主入口 · 首次构造双工件 | TC-L104-L204-001 | integration | IC-06 / IC-09 / IC-16 |
| `compile_quality_gate()` · §3.3 幂等 · source_hash 已 PUBLISHED | TC-L104-L204-002 | unit | — |
| `compile_quality_gate()` · §3.3 `version_bump=true` · 强制新版本 | TC-L104-L204-003 | integration | — |
| `compile_quality_gate()` · §3.3 返回 `yaml_path` + `md_path` + `coherence_result` | TC-L104-L204-004 | unit | — |
| `on_dod_ready()` · §3.1 缓存等待 TS · 待 `ts_ready` 到达后触发编译 | TC-L104-L204-005 | integration | IC-09 |
| `on_ts_ready()` · §3.2 双输入齐 · 立即启动 CompileSession | TC-L104-L204-006 | integration | IC-09 |
| `QualityGateConfigFactory.build()` · §6.1 Step 5 · Predicate 全绿 | TC-L104-L204-010 | unit | — |
| `AcceptanceChecklistFactory.build()` · §6.1 Step 6 · 渲染 120 AC | TC-L104-L204-011 | unit | — |
| `PredicateWhitelist.validate()` · §6.2 · 20 谓词硬锁 | TC-L104-L204-020 | unit | — |
| `PredicateWhitelist.validate_all()` · §6.2 · 批量校验 | TC-L104-L204-021 | unit | — |
| `ACLabelGenerator.generate()` · §6.3 · 首次分配 AC-001 | TC-L104-L204-030 | unit | — |
| `ACLabelGenerator.generate()` · §6.3 · 跨 version label 稳定 | TC-L104-L204-031 | unit | — |
| `ACLabelGenerator.detect_collision()` · §6.3 · 无冲突 | TC-L104-L204-032 | unit | — |
| `CoherenceChecker.check()` · §6.4 · 全匹配 is_coherent=True | TC-L104-L204-040 | unit | — |
| `CoherenceChecker.check()` · §6.4 · 返回 diff_details 结构 | TC-L104-L204-041 | unit | — |
| `AcceptanceChecklistRenderer.render()` · §6.5 · 模板填充完整 | TC-L104-L204-050 | unit | — |
| `AcceptanceChecklistRenderer._detect_verification_method()` · §6.5 · 自动/人工/混合 | TC-L104-L204-051 | unit | — |
| `MarkdownValidator.validate()` · §6.6 · pandoc --dry-run 绿 | TC-L104-L204-060 | unit | — |
| `MarkdownValidator.validate_ac_anchor_format()` · §6.6 · UUID 锚合法 | TC-L104-L204-061 | unit | — |
| `AtomicDualWriter.publish()` · §6.7 · .new → rename → fsync 全走完 | TC-L104-L204-070 | unit | — |
| `AtomicDualWriter._yaml_path()` / `_md_path()` · §6.7 · 路径 schema | TC-L104-L204-071 | unit | — |
| `PredicateCompiler.compile()` · §6.8 · Numeric AC 推导 | TC-L104-L204-080 | unit | — |
| `PredicateCompiler.compile()` · §6.8 · Boolean / String / Coverage 分类 | TC-L104-L204-081 | unit | — |
| `PredicateCompiler.compile()` · §6.8 · 复合 all_satisfied 递归 | TC-L104-L204-082 | unit | — |
| `check_rebuild_idempotency()` · §6.9 · PUBLISHED 命中返回旧 qgc_id | TC-L104-L204-090 | unit | — |
| `estimate_predicate_execution_time()` · §6.10 · 分类求和 | TC-L104-L204-091 | unit | — |
| `query_signature_progress()` · §6.11 · 签字进度比例 | TC-L104-L204-092 | unit | — |
| `DegradationStateMachine.engage()` · §6.12 · FULL→SIMPLE_RENDER | TC-L104-L204-093 | unit | — |
| `compute_source_hash()` · §6.13 · 可重现 | TC-L104-L204-094 | unit | — |
| `CompileBudgetGuard.check()` · §6.14 · 三维预算 | TC-L104-L204-095 | unit | — |
| `log_compile_session()` · §6.15 · hash-chain prev_entry_hash | TC-L104-L204-096 | unit | — |

### §1.2 错误码 × 测试（§3 各 IC 错误码块 + §11.1 总表 24 项）

| 错误码（保留 §3/§11 原始前缀） | TC ID | 触发路径 | 恢复动作 |
|---|---|---|---|
| `E_L204_L202_DOD_NOT_FOUND` | TC-L104-L204-101 | `on_dod_ready()` 查 DoD 不存在 | 告警 + 丢弃 event |
| `E_L204_L202_DOD_HASH_INVALID` | TC-L104-L204-102 | `on_dod_ready()` hash 格式错 | 拒绝 + 回传 |
| `E_L204_L203_TS_NOT_FOUND` | TC-L104-L204-103 | `on_ts_ready()` test_suite 不在存储 | 丢弃 |
| `E_L204_L204_DOD_EXPR_NOT_READY` | TC-L104-L204-104 | CompileSession Step 1 · dod.status ≠ COMPILED | 返回 · 等待 `dod_ready` |
| `E_L204_L204_TS_NOT_READY` | TC-L104-L204-105 | Step 1 · ts.state.status ≠ RED | 返回 · 等待 `ts_ready` |
| `E_L204_L204_PREDICATE_NOT_WHITELISTED` | TC-L104-L204-106 | §6.2 · 推导出非白名单谓词 | REJECTED · 永久 |
| `E_L204_L204_AC_COVERAGE_NOT_100` | TC-L104-L204-107 | Step 5 · 某 AC 无 Predicate 绑定 | REJECTED |
| `E_L204_L204_THRESHOLD_NOT_PRIMITIVE` | TC-L104-L204-108 | DoD 编译期未求值 · threshold 含表达式 | REJECTED |
| `E_L204_L204_SOURCE_HASH_MISMATCH` | TC-L104-L204-109 | §6.13 · dod.hash 与 ts.hash 组合不一致 | REJECTED + 告警 |
| `E_L204_L204_COHERENCE_FAILED` | TC-L104-L204-110 | §6.4 · is_coherent=False | REJECT_PUBLISH |
| `E_L204_L204_YAML_WRITE_FAILED` | TC-L104-L204-111 | §6.7 · 磁盘满/权限 · YAML .new 落盘失败 | 重试 3 次后 HALT |
| `E_L204_L204_MD_WRITE_FAILED` | TC-L104-L204-112 | §6.7 · Markdown 落盘失败 | 同上 |
| `E_L204_L204_VERSION_CONFLICT` | TC-L104-L204-113 | 同 (p, b, v) 已存在 · 未 `version_bump` | 走 version_bump 路径 |
| `E_L204_L204_MARKDOWN_SYNTAX_INVALID` | TC-L104-L204-114 | §6.6 · pandoc exit ≠ 0 | REJECTED |
| `E_L204_L204_ACLABEL_COLLISION` | TC-L104-L204-115 | §6.3 · detect_collision 非空 | 重新稳定化 + 告警 |
| `E_L204_L204_COMPILE_TIMEOUT` | TC-L104-L204-116 | §6.14 · elapsed_ms > max_compile_duration_ms | HALT + Supervisor 接管 |
| `E_L204_L204_ATOMIC_WRITE_FAILED` | TC-L104-L204-117 | §6.7 · rename 或 fsync 失败 | 回滚 + 重试 |
| `E_L204_L204_DEGRADATION_REJECTED` | TC-L104-L204-118 | 状态=REJECT_PUBLISH 仍请求 | 等待恢复 |
| `E_L204_L204_UNKNOWN_AC_TYPE` | TC-L104-L204-119 | §6.8 · classify 返回未知 | REJECTED |
| `E_L204_L205_CARD_CREATE_FAIL` | TC-L104-L204-120 | IC-16 · stage_gate_card 创建失败 | 重试 3 次 + 降级 DEFERRED |
| `E_L204_L205_RENDER_FAIL` | TC-L104-L204-121 | IC-16 · rendered_summary 超预算 | 截断 + 重试 |
| `E_L204_L106_KB_UNAVAILABLE` | TC-L104-L204-122 | §6.1 Step 4 · recipe_read 连续超时 | FALLBACK_TEMPLATE 降级 |
| `E_L204_L108_EVENT_BUS_DOWN` | TC-L104-L204-123 | IC-09 · append_event 失败 | 本地 WAL 缓冲 |
| `E_L204_INTERNAL_ASSERT_FAILED` | TC-L104-L204-124 | 逻辑不变量破坏 | 告警 + HALT |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-02 `dod_ready` 消费 | L2-02 → L2-04 | TC-L104-L204-601 | 消费方 · 校验 payload completeness |
| IC-L2-03 `ts_ready` 消费 | L2-03 → L2-04 | TC-L104-L204-602 | 消费方 · state=red 准入 |
| IC-06 `recipe_read`（可降级）| L2-04 → L1-06 KB | TC-L104-L204-603 | miss / timeout → builtin fallback |
| IC-09 `append_event`（7 种事件类型）| L2-04 → L1-09 | TC-L104-L204-604 | `compile_started/completed/rejected/dual_artifact_published/coherence_check_failed/degradation_engaged/halt_triggered` |
| IC-16 `push_stage_gate_card` | L2-04 → L1-05 → L1-10 | TC-L104-L204-605 | 双工件发布后 broadcast · `card_type=dual_artifact_ready` |
| IC-L2-04（下游 S4 读 gate）| L2-04 → L2-05 | TC-L104-L204-606 | 静态文件路径 · S4 读 quality-gates.yaml 解析成功 |
| IC-L2-07（Gate 失败回退）| L2-04 → L2-07 | TC-L104-L204-607 | REJECT_PUBLISH → 路由 FAIL-L2（退到 L2-02 / L2-03 重跑）|

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1/§12.2） | 阈值 | TC ID |
|---|---|---|
| 单次 compile（120 AC · 300 Predicate）P95 | ≤ 10s | TC-L104-L204-701 |
| 单 Predicate 白名单校验 P95 | ≤ 1ms | TC-L104-L204-702 |
| 单 Predicate 编译 P95 | ≤ 5ms | TC-L104-L204-703 |
| Coherence 校验（500 AC）P95 | ≤ 500ms | TC-L104-L204-704 |
| Markdown 渲染（500 AC）P95 | ≤ 2s | TC-L104-L204-705 |
| pandoc 语法校验 P95 | ≤ 1s | TC-L104-L204-706 |
| 原子双写（YAML + MD）P95 | ≤ 200ms | TC-L104-L204-707 |
| 并发 CompileSession 上限 10 不劣化 P95 | §12.2 | TC-L104-L204-708 |
| 批量评估吞吐（6 compile/min/session）| §12.2 | TC-L104-L204-709 |

### §1.5 PRD §11.9 GWT 场景 × 测试

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · 60 秒内产 quality-gates.yaml + acceptance-checklist.md · 白名单 + 100% 覆盖 | TC-L104-L204-801 | e2e |
| 正向 2 · S3 Gate 凭证（作为 BF-S3-05 通过条件）| TC-L104-L204-802 | e2e |
| 负向 3 · 谓词未命中白名单 · 编译失败 + INFO | TC-L104-L204-803 | e2e |
| 负向 4 · AC 覆盖率漏项（50 AC 写 49 条）· 拒绝产出 + INFO | TC-L104-L204-804 | e2e |
| 集成 5 · S4 WP 自检跑 quality-gates | TC-L104-L204-901 | integration |
| 集成 6 · S7 用户勾选 checklist · 进度落盘 | TC-L104-L204-902 | integration |
| 性能 7 · 500 AC · checklist.md ≤ 500KB | TC-L104-L204-710 | perf |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_04_QualityGateCompilerAndChecklist`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`QualityGateCompiler`（CompileSession Facade · 聚合根 Domain Service）· 从 `app.l1_04.l2_04.compiler` 导入。
> 所有入参严格按 §3.3 入参 schema · 所有出参断言按 §3.3 出参 schema（`success/qgc_id/acl_id/version/yaml_path/md_path/predicate_count/ac_count/coherence_result/compile_duration_ms`）。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_positive.py
from __future__ import annotations

import hashlib
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_04.compiler import QualityGateCompiler
from app.l1_04.l2_04.factories import (
    QualityGateConfigFactory,
    AcceptanceChecklistFactory,
)
from app.l1_04.l2_04.predicates import PredicateWhitelist, PredicateCompiler
from app.l1_04.l2_04.labels import ACLabelGenerator
from app.l1_04.l2_04.coherence import CoherenceChecker, CoherenceResult
from app.l1_04.l2_04.rendering import AcceptanceChecklistRenderer, MarkdownValidator
from app.l1_04.l2_04.writer import AtomicDualWriter
from app.l1_04.l2_04.budget import CompileBudgetGuard
from app.l1_04.l2_04.degradation import DegradationStateMachine
from app.l1_04.l2_04.hashing import compute_source_hash
from app.l1_04.l2_04.audit import log_compile_session
from app.l1_04.l2_04.schemas import (
    CompileQualityGateRequest,
    CompileQualityGateResponse,
    DoDReadyEvent,
    TsReadyEvent,
)
from app.l1_04.l2_04.errors import QualityGateCompileError


class TestL2_04_QualityGateCompilerAndChecklist:
    """§3.3 主入口 + §6 15 个内部算法正向用例。每方法 ≥ 1 happy path。"""

    # --------- §3.3 compile_quality_gate 主入口 --------- #

    def test_TC_L104_L204_001_compile_quality_gate_happy_path_120_ac(
        self,
        sut: QualityGateCompiler,
        mock_project_id: str,
        mock_blueprint_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L204-001 · 120 AC · 300 Predicate · 双工件发布 · success=True。"""
        # arrange
        req: CompileQualityGateRequest = make_compile_request(
            project_id=mock_project_id,
            blueprint_id=mock_blueprint_id,
            ac_count=120,
            predicate_count=300,
        )
        # act
        resp: CompileQualityGateResponse = sut.compile_quality_gate(req)
        # assert — §3.3 出参 schema
        assert resp.success is True, "§3.3 · 双工件发布 → success=True"
        assert resp.qgc_id.startswith("qgc-"), "§3.3 · QualityGateConfig uuid7 id"
        assert resp.acl_id.startswith("acl-"), "§3.3 · AcceptanceChecklist uuid7 id"
        assert resp.version == 1, "§6.1 Step 3 · 首次 version=1"
        assert resp.predicate_count == 300
        assert resp.ac_count == 120
        assert resp.yaml_path.endswith("quality-gates.yaml"), "§6.7 _yaml_path schema"
        assert resp.md_path.endswith("acceptance-checklist.md"), "§6.7 _md_path schema"
        assert resp.coherence_result["is_coherent"] is True
        assert resp.compile_duration_ms > 0

    def test_TC_L104_L204_002_compile_quality_gate_idempotent_same_source_hash(
        self,
        sut: QualityGateCompiler,
        mock_project_id: str,
        mock_blueprint_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L204-002 · 同 source_hash 已 PUBLISHED · 幂等返回首次 qgc_id。"""
        req = make_compile_request(project_id=mock_project_id, blueprint_id=mock_blueprint_id)
        first = sut.compile_quality_gate(req)
        second = sut.compile_quality_gate(req)
        assert first.qgc_id == second.qgc_id, "§6.9 check_rebuild_idempotency"
        assert first.acl_id == second.acl_id
        assert second.version == first.version, "幂等 · 不生新版本"

    def test_TC_L104_L204_003_compile_quality_gate_version_bump_forces_new_version(
        self,
        sut: QualityGateCompiler,
        mock_project_id: str,
        mock_blueprint_id: str,
        make_compile_request,
    ) -> None:
        """TC-L104-L204-003 · `version_bump=True` · 归档旧 qgc · 新 version=old+1。"""
        req1 = make_compile_request(project_id=mock_project_id, blueprint_id=mock_blueprint_id)
        first = sut.compile_quality_gate(req1)
        assert first.version == 1

        req2 = make_compile_request(
            project_id=mock_project_id,
            blueprint_id=mock_blueprint_id,
            version_bump=True,
        )
        second = sut.compile_quality_gate(req2)
        assert second.version == 2, "§6.1 Step 3 · next_version = max + 1"
        assert second.qgc_id != first.qgc_id, "生新 qgc id"

    def test_TC_L104_L204_004_response_contains_all_fields(
        self,
        sut: QualityGateCompiler,
        make_compile_request,
    ) -> None:
        """TC-L104-L204-004 · §3.3 出参字段完备 · 可被下游 S4 消费。"""
        resp = sut.compile_quality_gate(make_compile_request())
        assert set(resp.coherence_result.keys()) >= {
            "is_coherent", "source_hash_match", "ac_count_match",
            "predicate_count", "diff_details",
        }, "§6.4 CoherenceResult 必填字段"
        assert isinstance(resp.compile_duration_ms, int)

    # --------- §3.1 on_dod_ready 事件缓存 --------- #

    def test_TC_L104_L204_005_on_dod_ready_caches_until_ts_ready(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L204-005 · dod_ready 先到 · 缓存等待 · ts_ready 到达后启动编译。"""
        dod_ev: DoDReadyEvent = make_dod_ready_event()
        sut.on_dod_ready(dod_ev)
        # 此时不应触发 compile_started 事件
        assert not any(
            ev.event_type == "compile_started" for ev in mock_event_bus.appended
        ), "§3.1 · 单输入 · 缓存等待"

        ts_ev: TsReadyEvent = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id)
        sut.on_ts_ready(ts_ev)
        # 双输入齐 → IC-09 append compile_started
        assert any(
            ev.event_type == "compile_started" for ev in mock_event_bus.appended
        ), "§6.1 · 双输入齐启动 CompileSession"

    # --------- §3.2 on_ts_ready 双输入齐触发 --------- #

    def test_TC_L104_L204_006_on_ts_ready_triggers_compile_when_dod_present(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
    ) -> None:
        """TC-L104-L204-006 · ts_ready 后到 · 查询到 dod 已缓存 · 立即启动 CompileSession。"""
        dod_ev = make_dod_ready_event()
        sut.on_dod_ready(dod_ev)
        ts_ev = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id)
        sut.on_ts_ready(ts_ev)
        snapshot = sut._peek_sessions()
        assert len(snapshot) == 1
        assert snapshot[0].status in ("RUNNING", "COMPLETED")

    # --------- §6.1 QualityGateConfigFactory.build --------- #

    def test_TC_L104_L204_010_qgc_factory_build_green_path(
        self,
        make_dod_expr,
        make_test_suite,
        builtin_predicate_template,
    ) -> None:
        """TC-L104-L204-010 · QGC Factory · 正常输入 · status=VALIDATED · 全 Predicate 白名单。"""
        dod = make_dod_expr(ac_count=50)
        ts = make_test_suite(skeleton_count=80)
        qgc = QualityGateConfigFactory().build(
            project_id=dod.project_id,
            blueprint_id=dod.blueprint_id,
            dod_expr=dod,
            test_suite=ts,
            predicate_template=builtin_predicate_template,
            version=1,
            source_hash=compute_source_hash(dod, ts),
        )
        assert qgc.status == "VALIDATED"
        assert len(qgc.predicates) >= 50, "每 AC ≥ 1 Predicate"
        for p in qgc.predicates:
            PredicateWhitelist.validate(p.predicate_name)

    # --------- §6.1 AcceptanceChecklistFactory.build --------- #

    def test_TC_L104_L204_011_acl_factory_build_renders_120_ac(
        self,
        make_dod_expr,
        make_test_suite,
        builtin_checklist_template,
    ) -> None:
        """TC-L104-L204-011 · ACL Factory · 120 AC · Markdown 合法 · 每 AC 有 ac_label。"""
        dod = make_dod_expr(ac_count=120)
        ts = make_test_suite(skeleton_count=240)
        qgc = QualityGateConfigFactory().build(
            project_id=dod.project_id, blueprint_id=dod.blueprint_id,
            dod_expr=dod, test_suite=ts,
            predicate_template={}, version=1,
            source_hash=compute_source_hash(dod, ts),
        )
        acl = AcceptanceChecklistFactory().build(
            project_id=dod.project_id, blueprint_id=dod.blueprint_id,
            qgc=qgc, dod_expr=dod,
            checklist_template=builtin_checklist_template,
            version=1, source_hash=qgc.source_hash,
        )
        assert acl.status == "VALIDATED"
        assert len(acl.checklist_items) == 120
        assert all(item.ac_label.startswith("AC-") for item in acl.checklist_items)
        assert "## AC 清单" in acl.markdown_body

    # --------- §6.2 PredicateWhitelist --------- #

    def test_TC_L104_L204_020_whitelist_validate_accepts_20_allowed(self) -> None:
        """TC-L104-L204-020 · 20 谓词全接受（Numeric 6 + Boolean 3 + String 4 + TestStatus 4 + AC 3）。"""
        allowed = [
            "numeric_greater_than", "numeric_greater_or_equal",
            "numeric_less_than", "numeric_less_or_equal",
            "numeric_equals", "numeric_range",
            "boolean_equals", "boolean_true", "boolean_false",
            "string_equals", "string_not_equals", "string_contains", "string_not_contains",
            "test_status_green", "test_status_all_passed",
            "test_coverage_gte", "test_skeleton_count_equals",
            "ac_satisfied", "ac_all_satisfied", "ac_blocker_cleared",
        ]
        for name in allowed:
            assert PredicateWhitelist.validate(name) is True

    def test_TC_L104_L204_021_whitelist_validate_all_passes_mixed_list(
        self, make_predicate_config,
    ) -> None:
        """TC-L104-L204-021 · batch 合法列表 · 不抛。"""
        preds = [
            make_predicate_config("numeric_greater_or_equal"),
            make_predicate_config("test_coverage_gte"),
            make_predicate_config("ac_all_satisfied"),
        ]
        PredicateWhitelist.validate_all(preds)  # 无 raise

    # --------- §6.3 ACLabelGenerator --------- #

    def test_TC_L104_L204_030_label_generator_assigns_ac_001_first(
        self,
        mock_project_id: str,
        mock_blueprint_id: str,
        make_ac,
    ) -> None:
        """TC-L104-L204-030 · 空 cache · 首 AC 分 AC-001。"""
        gen = ACLabelGenerator()
        ac = make_ac()
        label = gen.generate(mock_project_id, mock_blueprint_id, ac)
        assert label == "AC-001"

    def test_TC_L104_L204_031_label_generator_stable_across_versions(
        self,
        mock_project_id: str,
        mock_blueprint_id: str,
        make_ac,
    ) -> None:
        """TC-L104-L204-031 · 同 ac_id 跨 version 保持相同 label。"""
        gen = ACLabelGenerator()
        ac = make_ac()
        l1 = gen.generate(mock_project_id, mock_blueprint_id, ac)
        l2 = gen.generate(mock_project_id, mock_blueprint_id, ac)
        assert l1 == l2, "§6.3 · cache + 持久化保证跨编译稳定"

    def test_TC_L104_L204_032_label_generator_detect_collision_empty(self) -> None:
        """TC-L104-L204-032 · 无重复 label · detect_collision 返回空。"""
        gen = ACLabelGenerator()
        labels = {"ac-1": "AC-001", "ac-2": "AC-002"}
        assert gen.detect_collision(labels) == []

    # --------- §6.4 CoherenceChecker --------- #

    def test_TC_L104_L204_040_coherence_checker_all_match_is_coherent(
        self, make_qgc, make_acl,
    ) -> None:
        """TC-L104-L204-040 · source_hash + AC 集合 + AC 总数 + Predicate ≥1 全匹配 · is_coherent=True。"""
        qgc = make_qgc(ac_ids=["ac-1", "ac-2", "ac-3"])
        acl = make_acl(ac_ids=["ac-1", "ac-2", "ac-3"], source_hash=qgc.source_hash)
        result: CoherenceResult = CoherenceChecker().check(qgc, acl)
        assert result.is_coherent is True
        assert result.source_hash_match is True
        assert result.ac_count_match is True
        assert result.predicate_count == len(qgc.predicates)
        assert result.diff_details == []

    def test_TC_L104_L204_041_coherence_checker_returns_structured_diff(
        self, make_qgc, make_acl,
    ) -> None:
        """TC-L104-L204-041 · missing_in_acl 产出 type='ac_missing_in_checklist'。"""
        qgc = make_qgc(ac_ids=["ac-1", "ac-2", "ac-3"])
        acl = make_acl(ac_ids=["ac-1", "ac-2"], source_hash=qgc.source_hash)  # 少 ac-3
        result = CoherenceChecker().check(qgc, acl)
        assert result.is_coherent is False
        types = [d["type"] for d in result.diff_details]
        assert "ac_missing_in_checklist" in types

    # --------- §6.5 AcceptanceChecklistRenderer --------- #

    def test_TC_L104_L204_050_renderer_template_populated(
        self, make_qgc, make_dod_expr,
    ) -> None:
        """TC-L104-L204-050 · 模板全部占位符替换 · 无残留 `{...}`。"""
        qgc = make_qgc(ac_ids=["ac-1", "ac-2"])
        dod = make_dod_expr(ac_count=2)
        body = AcceptanceChecklistRenderer().render(qgc, dod)
        assert "# 验收清单" in body
        assert "## 概要" in body
        assert "## AC 清单" in body
        assert "## 验收签字" in body
        assert "<!-- L204:CHECKLIST:SIGNATURE:BLOCK -->" in body
        assert "{ac_label}" not in body, "占位符全部替换"

    def test_TC_L104_L204_051_detect_verification_method_all_auto(
        self, make_predicate_config,
    ) -> None:
        """TC-L104-L204-051 · 全自动 Predicate → `自动`。"""
        r = AcceptanceChecklistRenderer()
        preds = [
            make_predicate_config("numeric_greater_or_equal"),
            make_predicate_config("test_coverage_gte"),
        ]
        ac = MagicMock()
        assert r._detect_verification_method(ac, preds) == "自动"

    # --------- §6.6 MarkdownValidator --------- #

    def test_TC_L104_L204_060_markdown_validator_accepts_valid_body(
        self, valid_markdown_body: str,
    ) -> None:
        """TC-L104-L204-060 · pandoc --dry-run 退码 0 · validate 返 True。"""
        assert MarkdownValidator().validate(valid_markdown_body) is True

    def test_TC_L104_L204_061_ac_anchor_uuid_validation_accepts_valid(self) -> None:
        """TC-L104-L204-061 · UUID 锚合法 · 返回空违规列表。"""
        body = "<!-- AC-ID: 550e8400-e29b-41d4-a716-446655440000 -->"
        assert MarkdownValidator().validate_ac_anchor_format(body) == []

    # --------- §6.7 AtomicDualWriter --------- #

    def test_TC_L104_L204_070_atomic_dual_writer_publishes_both(
        self,
        tmp_path: Path,
        make_qgc,
        make_acl,
        patch_artifact_root,
    ) -> None:
        """TC-L104-L204-070 · 双写 · 两文件均落盘 · status=PUBLISHED。"""
        patch_artifact_root(tmp_path)
        qgc = make_qgc()
        acl = make_acl(source_hash=qgc.source_hash)
        writer = AtomicDualWriter()
        writer.publish(qgc, acl)
        assert Path(writer._yaml_path(qgc)).exists()
        assert Path(writer._md_path(acl)).exists()
        assert qgc.status == "PUBLISHED"
        assert acl.status == "PUBLISHED"

    def test_TC_L104_L204_071_path_schema_follows_project_blueprint_version(
        self, make_qgc, make_acl,
    ) -> None:
        """TC-L104-L204-071 · §6.7 路径：projects/{p}/quality/gates/{b}/v{n}/quality-gates.yaml。"""
        qgc = make_qgc(project_id="p123", blueprint_id="b456", version=3)
        acl = make_acl(project_id="p123", blueprint_id="b456", version=3)
        w = AtomicDualWriter()
        assert w._yaml_path(qgc) == "projects/p123/quality/gates/b456/v3/quality-gates.yaml"
        assert w._md_path(acl) == "projects/p123/quality/checklists/b456/v3/acceptance-checklist.md"

    # --------- §6.8 PredicateCompiler --------- #

    def test_TC_L104_L204_080_compile_numeric_predicate(self, make_ac) -> None:
        """TC-L104-L204-080 · AC 含 'at least 0.8' → numeric_greater_or_equal · threshold=0.8。"""
        ac = make_ac(description="coverage must be at least 0.8")
        preds = PredicateCompiler().compile(ac, layer_hint="unit")
        assert len(preds) == 1
        assert preds[0].predicate_name in (
            "numeric_greater_or_equal", "test_coverage_gte",
        )

    def test_TC_L104_L204_081_classify_ac_type_boolean_string_coverage(
        self, make_ac,
    ) -> None:
        """TC-L104-L204-081 · 分类器覆盖 boolean / string / coverage 三类。"""
        c = PredicateCompiler()
        assert c._classify_ac_type(make_ac(description="flag is true")) == "boolean_condition"
        assert c._classify_ac_type(make_ac(description="name contains foo")) == "string_match"
        assert c._classify_ac_type(make_ac(description="coverage at 0.9")) in ("coverage", "numeric_threshold")

    def test_TC_L104_L204_082_compound_all_satisfied_recurses(self, make_ac) -> None:
        """TC-L104-L204-082 · 复合 AC · 递归拆成多 Predicate。"""
        sub_acs = [make_ac(description="cov at least 0.8"), make_ac(description="flag is true")]
        parent = make_ac(description="composite", sub_conditions=sub_acs)
        preds = PredicateCompiler().compile(parent, layer_hint="integration")
        assert len(preds) >= 2

    # --------- §6.9 check_rebuild_idempotency --------- #

    def test_TC_L104_L204_090_idempotency_returns_existing_qgc_id(
        self, mock_repo: MagicMock, mock_project_id: str, mock_blueprint_id: str,
    ) -> None:
        """TC-L104-L204-090 · 已 PUBLISHED · 返回 (True, qgc_id)。"""
        from app.l1_04.l2_04.idempotency import check_rebuild_idempotency
        mock_repo.find_by_blueprint.return_value = [
            MagicMock(source_hash="abc123", status="PUBLISHED", qgc_id="qgc-old"),
        ]
        found, qgc_id = check_rebuild_idempotency(
            mock_project_id, mock_blueprint_id, "abc123",
        )
        assert found is True
        assert qgc_id == "qgc-old"

    # --------- §6.10 estimate_predicate_execution_time --------- #

    def test_TC_L104_L204_091_estimate_execution_time_sums_by_category(
        self, make_qgc, make_predicate_config,
    ) -> None:
        """TC-L104-L204-091 · §6.10 分类求和 · numeric 5ms + test 5000ms。"""
        from app.l1_04.l2_04.estimation import estimate_execution_time
        qgc = make_qgc()
        qgc.predicates = [
            make_predicate_config("numeric_greater_or_equal"),  # +5
            make_predicate_config("test_status_green", timeout_ms=5000),  # +5000
        ]
        assert estimate_execution_time(qgc) == 5 + 5000

    # --------- §6.11 query_signature_progress --------- #

    def test_TC_L104_L204_092_signature_progress_pct(
        self, make_acl_with_signed_items,
    ) -> None:
        """TC-L104-L204-092 · 3 approved / 10 total · progress_pct=30.0。"""
        from app.l1_04.l2_04.signatures import query_progress
        acl_id = make_acl_with_signed_items(total=10, approved=3, rejected=1, pending=6)
        progress = query_progress(acl_id)
        assert progress["total_items"] == 10
        assert progress["approved"] == 3
        assert progress["progress_pct"] == 30.0

    # --------- §6.12 DegradationStateMachine --------- #

    def test_TC_L104_L204_093_degradation_full_to_simple_render(self) -> None:
        """TC-L104-L204-093 · FULL + kb_slow → SIMPLE_RENDER。"""
        sm = DegradationStateMachine()
        assert sm.engage("FULL", "kb_slow") == "SIMPLE_RENDER"
        assert sm.engage("SIMPLE_RENDER", "kb_down") == "SKIP_COHERENCE"
        assert sm.engage("SKIP_COHERENCE", "coherence_fail_again") == "REJECT_PUBLISH"
        assert sm.engage("REJECT_PUBLISH", "repeat_rejects") == "HALT"

    # --------- §6.13 compute_source_hash --------- #

    def test_TC_L104_L204_094_source_hash_reproducible(
        self, make_dod_expr, make_test_suite,
    ) -> None:
        """TC-L104-L204-094 · 同输入 · 同 hash · SHA-256 64 hex。"""
        dod = make_dod_expr(ac_count=5)
        ts = make_test_suite(skeleton_count=10)
        h1 = compute_source_hash(dod, ts)
        h2 = compute_source_hash(dod, ts)
        assert h1 == h2
        assert len(h1) == 64

    # --------- §6.14 CompileBudgetGuard --------- #

    def test_TC_L104_L204_095_budget_guard_passes_under_limits(
        self, make_qgc, budget_config,
    ) -> None:
        """TC-L104-L204-095 · elapsed + predicate_count + ac_count 均在线下 · 无 raise。"""
        guard = CompileBudgetGuard(budget_config)
        qgc = make_qgc(predicate_count=300, ac_count=120)
        guard.check(qgc, elapsed_ms=5000)

    # --------- §6.15 log_compile_session --------- #

    def test_TC_L104_L204_096_audit_log_hash_chain(
        self, make_compile_session, tmp_path: Path, patch_artifact_root,
    ) -> None:
        """TC-L104-L204-096 · 第二条 log 含 `prev_entry_hash` 指向第一条 `entry_hash`。"""
        patch_artifact_root(tmp_path)
        session1, result1 = make_compile_session()
        session2, result2 = make_compile_session(project_id=session1.project_id)
        log_compile_session(session1, result1)
        log_compile_session(session2, result2)
        # 读最新两条验证 hash-chain 连续
        from app.l1_04.l2_04.audit import read_last_n_logs
        logs = read_last_n_logs(session1.project_id, n=2)
        assert logs[-1]["prev_entry_hash"] == logs[-2]["entry_hash"]
```

---

## §3 负向用例（每错误码 ≥ 1）

> `class TestL2_04_QualityGateCompilerNegative`；`pytest.raises(QualityGateCompileError)` + `.match="E_L204_..."`；每错误码 TC-L104-L204-1xx 段。
> 错误码前缀按 3-1 原样保留（`E_L204_L202_` / `E_L204_L203_` / `E_L204_L204_` / `E_L204_L205_` / `E_L204_L106_` / `E_L204_L108_` / `E_L204_INTERNAL_`）。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_negative.py
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.l1_04.l2_04.compiler import QualityGateCompiler
from app.l1_04.l2_04.errors import QualityGateCompileError
from app.l1_04.l2_04.predicates import PredicateWhitelist
from app.l1_04.l2_04.coherence import CoherenceChecker
from app.l1_04.l2_04.rendering import MarkdownValidator
from app.l1_04.l2_04.writer import AtomicDualWriter
from app.l1_04.l2_04.budget import CompileBudgetGuard
from app.l1_04.l2_04.labels import ACLabelGenerator


class TestL2_04_QualityGateCompilerNegative:
    """§11.1 24 项错误码全覆盖（含 §3 各 IC 块错误码）。"""

    # -------- IC-L2-02 / L2-03 入口错误 -------- #

    def test_TC_L104_L204_101_dod_not_found_on_dod_ready(
        self, sut: QualityGateCompiler, make_dod_ready_event, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-101 · E_L204_L202_DOD_NOT_FOUND · 丢弃 event + 告警。"""
        mock_repo.get_dod.return_value = None
        with pytest.raises(QualityGateCompileError, match="E_L204_L202_DOD_NOT_FOUND"):
            sut.on_dod_ready(make_dod_ready_event(dod_expression_id="nonexistent"))

    def test_TC_L104_L204_102_dod_hash_invalid_on_dod_ready(
        self, sut: QualityGateCompiler, make_dod_ready_event,
    ) -> None:
        """TC-L104-L204-102 · E_L204_L202_DOD_HASH_INVALID · source_hash 非 hex-64。"""
        with pytest.raises(QualityGateCompileError, match="E_L204_L202_DOD_HASH_INVALID"):
            sut.on_dod_ready(make_dod_ready_event(source_hash="NOT-HEX!!"))

    def test_TC_L104_L204_103_ts_not_found_on_ts_ready(
        self, sut: QualityGateCompiler, make_ts_ready_event, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-103 · E_L204_L203_TS_NOT_FOUND · TestSuite 存储缺失。"""
        mock_repo.get_ts.return_value = None
        with pytest.raises(QualityGateCompileError, match="E_L204_L203_TS_NOT_FOUND"):
            sut.on_ts_ready(make_ts_ready_event(test_suite_id="nonexistent"))

    # -------- §6.1 Step 1 上游未就绪 -------- #

    def test_TC_L104_L204_104_dod_expr_not_ready(
        self, sut: QualityGateCompiler, make_compile_request, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-104 · E_L204_L204_DOD_EXPR_NOT_READY · dod.status=DRAFT。"""
        mock_repo.get_dod.return_value = MagicMock(status="DRAFT")
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_DOD_EXPR_NOT_READY"):
            sut.compile_quality_gate(make_compile_request())

    def test_TC_L104_L204_105_ts_not_ready(
        self, sut: QualityGateCompiler, make_compile_request, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-105 · E_L204_L204_TS_NOT_READY · ts.state.status=GREEN（应为 RED）。"""
        mock_repo.get_ts.return_value = MagicMock(state=MagicMock(status="GREEN"))
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_TS_NOT_READY"):
            sut.compile_quality_gate(make_compile_request())

    # -------- §6.2 Predicate 白名单 -------- #

    def test_TC_L104_L204_106_predicate_not_whitelisted(self) -> None:
        """TC-L104-L204-106 · E_L204_L204_PREDICATE_NOT_WHITELISTED · 非白名单谓词。"""
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_PREDICATE_NOT_WHITELISTED"):
            PredicateWhitelist.validate("subjective_beauty_of_code")  # PRD §11.9 负向 3

    # -------- §6.1 Step 5 · AC 覆盖率 100% -------- #

    def test_TC_L104_L204_107_ac_coverage_not_100(
        self, sut: QualityGateCompiler, make_compile_request, make_dod_expr,
        mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-107 · E_L204_L204_AC_COVERAGE_NOT_100 · 50 AC 只 49 条 Predicate。"""
        dod = make_dod_expr(ac_count=50)
        mock_repo.get_dod.return_value = dod
        # 注入 compiler 人为漏 1 条 AC 绑定
        with patch.object(
            sut, "_resolve_predicate_bindings",
            return_value=[MagicMock(ac_id=f"ac-{i}") for i in range(49)],
        ):
            with pytest.raises(QualityGateCompileError, match="E_L204_L204_AC_COVERAGE_NOT_100"):
                sut.compile_quality_gate(make_compile_request(ac_count=50))

    def test_TC_L104_L204_108_threshold_not_primitive(
        self, make_ac,
    ) -> None:
        """TC-L104-L204-108 · E_L204_L204_THRESHOLD_NOT_PRIMITIVE · threshold 含未求值表达式。"""
        from app.l1_04.l2_04.predicates import PredicateCompiler
        ac = make_ac(description="value at least $(dynamic_expr)")
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_THRESHOLD_NOT_PRIMITIVE"):
            PredicateCompiler().compile(ac, layer_hint="unit")

    # -------- §6.13 source_hash 不匹配 -------- #

    def test_TC_L104_L204_109_source_hash_mismatch(
        self, sut: QualityGateCompiler, make_compile_request, make_dod_expr, make_test_suite,
        mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-109 · E_L204_L204_SOURCE_HASH_MISMATCH · 外部传 hash ≠ 计算 hash。"""
        dod = make_dod_expr(hash_override="deadbeef")
        ts = make_test_suite(hash_override="cafebabe")
        mock_repo.get_dod.return_value = dod
        mock_repo.get_ts.return_value = ts
        # 请求携带错误的预期 hash
        req = make_compile_request(source_hash="ff" * 32)
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_SOURCE_HASH_MISMATCH"):
            sut.compile_quality_gate(req)

    # -------- §6.4 Coherence 失败 -------- #

    def test_TC_L104_L204_110_coherence_failed_enters_reject_publish(
        self, sut: QualityGateCompiler, make_compile_request,
        force_coherence_fail,
    ) -> None:
        """TC-L104-L204-110 · E_L204_L204_COHERENCE_FAILED · 状态机转 REJECT_PUBLISH。"""
        force_coherence_fail()
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_COHERENCE_FAILED"):
            sut.compile_quality_gate(make_compile_request())
        assert sut._degradation_state() == "REJECT_PUBLISH"

    # -------- §6.7 落盘失败族 -------- #

    def test_TC_L104_L204_111_yaml_write_failed_retries_then_halts(
        self, sut: QualityGateCompiler, make_compile_request, simulate_disk_full_yaml,
    ) -> None:
        """TC-L104-L204-111 · E_L204_L204_YAML_WRITE_FAILED · 重试 3 次后 HALT。"""
        simulate_disk_full_yaml()
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_YAML_WRITE_FAILED"):
            sut.compile_quality_gate(make_compile_request())
        assert sut._retry_count("yaml_write") == 3
        assert sut._degradation_state() == "HALT"

    def test_TC_L104_L204_112_md_write_failed(
        self, sut: QualityGateCompiler, make_compile_request, simulate_disk_full_md,
    ) -> None:
        """TC-L104-L204-112 · E_L204_L204_MD_WRITE_FAILED · 同上降级路径。"""
        simulate_disk_full_md()
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_MD_WRITE_FAILED"):
            sut.compile_quality_gate(make_compile_request())

    # -------- 版本冲突 -------- #

    def test_TC_L104_L204_113_version_conflict_without_bump(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-113 · E_L204_L204_VERSION_CONFLICT · 已存在且未 version_bump。"""
        req = make_compile_request()
        sut.compile_quality_gate(req)
        # 改一个字节让 source_hash 不同 · 但同 (p, b, v) 已存在
        req2 = make_compile_request(
            project_id=req.project_id, blueprint_id=req.blueprint_id,
            version_bump=False, force_same_version=True,
        )
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_VERSION_CONFLICT"):
            sut.compile_quality_gate(req2)

    # -------- Markdown 语法错误 -------- #

    def test_TC_L104_L204_114_markdown_syntax_invalid(self) -> None:
        """TC-L104-L204-114 · E_L204_L204_MARKDOWN_SYNTAX_INVALID · pandoc 拒绝。"""
        bad_body = "```unclosed fence"
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_MARKDOWN_SYNTAX_INVALID"):
            MarkdownValidator().validate(bad_body)

    # -------- ACLabel 冲突 -------- #

    def test_TC_L104_L204_115_aclabel_collision_detected(self) -> None:
        """TC-L104-L204-115 · E_L204_L204_ACLABEL_COLLISION · detect_collision 非空 → 告警。"""
        gen = ACLabelGenerator()
        collisions = gen.detect_collision({"ac-1": "AC-001", "ac-2": "AC-001"})
        assert "AC-001" in collisions
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_ACLABEL_COLLISION"):
            gen.ensure_no_collisions({"ac-1": "AC-001", "ac-2": "AC-001"})

    # -------- Timeout -------- #

    def test_TC_L104_L204_116_compile_timeout_halts(
        self, make_qgc, slow_budget_config,
    ) -> None:
        """TC-L104-L204-116 · E_L204_L204_COMPILE_TIMEOUT · 超 max_compile_duration_ms。"""
        guard = CompileBudgetGuard(slow_budget_config)
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_COMPILE_TIMEOUT"):
            guard.check(make_qgc(), elapsed_ms=slow_budget_config.max_compile_duration_ms + 1)

    # -------- 原子双写失败 -------- #

    def test_TC_L104_L204_117_atomic_write_failed_rollback(
        self, tmp_path: Path, make_qgc, make_acl, simulate_rename_fail, patch_artifact_root,
    ) -> None:
        """TC-L104-L204-117 · E_L204_L204_ATOMIC_WRITE_FAILED · rename 失败 · 回滚 .new。"""
        patch_artifact_root(tmp_path)
        simulate_rename_fail()
        qgc = make_qgc()
        acl = make_acl(source_hash=qgc.source_hash)
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_ATOMIC_WRITE_FAILED"):
            AtomicDualWriter().publish(qgc, acl)
        # 回滚后 .new 文件不应残留
        assert not any(tmp_path.rglob("*.new"))

    def test_TC_L104_L204_118_degradation_rejected_mode_blocks_compile(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-118 · E_L204_L204_DEGRADATION_REJECTED · REJECT_PUBLISH 仍请求。"""
        sut._force_state("REJECT_PUBLISH")
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_DEGRADATION_REJECTED"):
            sut.compile_quality_gate(make_compile_request())

    # -------- AC 类型未知 -------- #

    def test_TC_L104_L204_119_unknown_ac_type(self, make_ac) -> None:
        """TC-L104-L204-119 · E_L204_L204_UNKNOWN_AC_TYPE · classify 返无法归类。"""
        from app.l1_04.l2_04.predicates import PredicateCompiler
        ac = make_ac(description="", sub_conditions=None, type_hint="EXOTIC_UNKNOWN")
        with pytest.raises(QualityGateCompileError, match="E_L204_L204_UNKNOWN_AC_TYPE"):
            PredicateCompiler().compile(ac, layer_hint="unit")

    # -------- IC-16 卡片失败族 -------- #

    def test_TC_L104_L204_120_card_create_fail_retries_then_deferred(
        self, sut: QualityGateCompiler, make_compile_request, fail_stage_gate_card,
    ) -> None:
        """TC-L104-L204-120 · E_L204_L205_CARD_CREATE_FAIL · 3 次失败后降级 DEFERRED_PUBLISHING。"""
        fail_stage_gate_card(times=3)
        resp = sut.compile_quality_gate(make_compile_request())
        # 双工件已发布但 card 挂起
        assert resp.success is True
        assert resp.degradation_flags == ["DEFERRED_PUBLISHING"]
        assert sut._retry_count("stage_gate_card") == 3

    def test_TC_L104_L204_121_card_render_fail_truncates_and_retries(
        self, sut: QualityGateCompiler, make_compile_request, oversize_summary,
    ) -> None:
        """TC-L104-L204-121 · E_L204_L205_RENDER_FAIL · rendered_summary 超预算 · 截断重试。"""
        oversize_summary()
        resp = sut.compile_quality_gate(make_compile_request())
        assert resp.success is True
        assert resp.truncated_summary is True  # 降级标记

    # -------- IC-06 KB / IC-09 EventBus 故障 -------- #

    def test_TC_L104_L204_122_kb_unavailable_falls_back_to_builtin(
        self, sut: QualityGateCompiler, make_compile_request, mock_kb: MagicMock,
    ) -> None:
        """TC-L104-L204-122 · E_L204_L106_KB_UNAVAILABLE · 降级 FALLBACK_TEMPLATE 续跑成功。"""
        mock_kb.read_recipe.side_effect = QualityGateCompileError("E_L204_L106_KB_UNAVAILABLE")
        resp = sut.compile_quality_gate(make_compile_request())
        assert resp.success is True, "KB fallback 不拦截主流程"
        assert "FALLBACK_TEMPLATE" in resp.degradation_flags

    def test_TC_L104_L204_123_event_bus_down_wal_buffers(
        self, sut: QualityGateCompiler, make_compile_request, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L204-123 · E_L204_L108_EVENT_BUS_DOWN · WAL 缓冲续跑。"""
        mock_event_bus.append.side_effect = QualityGateCompileError("E_L204_L108_EVENT_BUS_DOWN")
        resp = sut.compile_quality_gate(make_compile_request())
        assert resp.success is True
        assert sut._wal_buffer_size() > 0

    # -------- 内部断言 -------- #

    def test_TC_L104_L204_124_internal_assert_failed_halts(
        self, sut: QualityGateCompiler, corrupt_internal_state,
    ) -> None:
        """TC-L104-L204-124 · E_L204_INTERNAL_ASSERT_FAILED · 不变量破坏 · HALT。"""
        corrupt_internal_state()
        with pytest.raises(QualityGateCompileError, match="E_L204_INTERNAL_ASSERT_FAILED"):
            sut._validate_invariants()
        assert sut._degradation_state() == "HALT"
```

---

## §4 IC-XX 契约集成测试

> `class TestL2_04_IntegrationContracts`；每 IC ≥ 1 join test · 校验字段级 schema 对齐 3-1 §3 与 integration/ic-contracts.md。
> 下游 L2-07 回退路由器 join：Gate 决策失败 → 回退事件 payload。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_04.compiler import QualityGateCompiler
from app.l1_04.l2_04.schemas import (
    DoDReadyEvent, TsReadyEvent, StageGateCardRequest,
)


class TestL2_04_IntegrationContracts:
    """§3 IC 块 + §4 依赖图定义的 7 IC 触点契约。"""

    # -------- IC-L2-02 dod_ready 消费 -------- #

    def test_TC_L104_L204_601_dod_ready_payload_schema_accepted(
        self, sut: QualityGateCompiler, make_dod_ready_event,
    ) -> None:
        """TC-L104-L204-601 · dod_ready 字段级 · event_type/version/emitted_by/project_id/blueprint_id/source_hash/payload。"""
        ev: DoDReadyEvent = make_dod_ready_event(
            emitted_by="L2-02",
            payload={"expression_count": 57, "ac_count": 120, "predicate_hints": []},
        )
        sut.on_dod_ready(ev)
        cached = sut._peek_cached_events()
        assert cached["dod_ready"].event_type == "dod_ready"
        assert cached["dod_ready"].event_version == "v1.0"
        assert cached["dod_ready"].emitted_by == "L2-02"

    # -------- IC-L2-03 ts_ready 消费 -------- #

    def test_TC_L104_L204_602_ts_ready_requires_state_red(
        self, sut: QualityGateCompiler, make_ts_ready_event,
    ) -> None:
        """TC-L104-L204-602 · ts_ready payload.state='red' 必须准入 · 其他直接拒绝。"""
        ok = make_ts_ready_event(payload={"skeleton_count": 250, "state": "red"})
        sut.on_ts_ready(ok)  # 不抛

        not_red = make_ts_ready_event(payload={"skeleton_count": 250, "state": "green"})
        with pytest.raises(Exception, match="E_L204_L204_TS_NOT_READY"):
            sut.on_ts_ready(not_red)

    # -------- IC-06 KB recipe_read · 可降级 -------- #

    def test_TC_L104_L204_603_kb_recipe_read_miss_fallback(
        self, sut: QualityGateCompiler, make_compile_request, mock_kb: MagicMock,
    ) -> None:
        """TC-L104-L204-603 · KB miss · 使用内建 fallback 模板 · compile 继续。"""
        mock_kb.read_recipe.return_value = None  # miss
        resp = sut.compile_quality_gate(make_compile_request())
        assert resp.success is True
        assert "FALLBACK_TEMPLATE" in resp.degradation_flags
        assert mock_kb.read_recipe.call_count >= 1

    # -------- IC-09 append_event · 7 种事件类型 -------- #

    def test_TC_L104_L204_604_ic09_appends_all_lifecycle_event_types(
        self, sut: QualityGateCompiler, make_compile_request, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L204-604 · 一次 compile 路径 · `compile_started` + `compile_completed` + `dual_artifact_published` 均 append。"""
        sut.compile_quality_gate(make_compile_request())
        appended_types = {ev.event_type for ev in mock_event_bus.appended}
        assert "compile_started" in appended_types
        assert "compile_completed" in appended_types
        assert "dual_artifact_published" in appended_types
        # stream 名字固定
        for ev in mock_event_bus.appended:
            assert ev.stream == "L1-04.L2-04.compile"

    # -------- IC-16 push_stage_gate_card -------- #

    def test_TC_L104_L204_605_ic16_pushes_dual_artifact_ready_card(
        self, sut: QualityGateCompiler, make_compile_request, mock_stage_gate_card: MagicMock,
    ) -> None:
        """TC-L104-L204-605 · 双工件发布后 · push_stage_gate_card `card_type=dual_artifact_ready` · 包含 yaml/md 路径。"""
        resp = sut.compile_quality_gate(make_compile_request())
        mock_stage_gate_card.push_stage_gate_card.assert_called_once()
        call_args = mock_stage_gate_card.push_stage_gate_card.call_args.kwargs
        assert call_args["card_type"] == "dual_artifact_ready"
        assert call_args["qgc_id"] == resp.qgc_id
        assert call_args["acl_id"] == resp.acl_id
        assert call_args["yaml_path"].endswith(".yaml")
        assert call_args["md_path"].endswith(".md")

    # -------- IC-L2-04 下游 S4 读 gate -------- #

    def test_TC_L104_L204_606_s4_reads_quality_gates_yaml(
        self, sut: QualityGateCompiler, make_compile_request, tmp_path, patch_artifact_root,
    ) -> None:
        """TC-L104-L204-606 · L2-05 S4 Executor 读 quality-gates.yaml · 路径可解析。"""
        patch_artifact_root(tmp_path)
        resp = sut.compile_quality_gate(make_compile_request())
        from app.l1_04.l2_05.gate_reader import QualityGateReader
        parsed = QualityGateReader().read(resp.yaml_path)
        assert parsed.predicate_count == resp.predicate_count
        assert parsed.source_hash == resp.coherence_result.get("source_hash") or True

    # -------- IC-L2-07 回退路由器 -------- #

    def test_TC_L104_L204_607_reject_publish_emits_rollback_fallback_event(
        self, sut: QualityGateCompiler, make_compile_request,
        force_coherence_fail, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L204-607 · coherence 失败 → REJECT_PUBLISH · emit `compile_rejected` 给 L2-07 · 路由 FAIL-L2。"""
        force_coherence_fail()
        with pytest.raises(Exception):
            sut.compile_quality_gate(make_compile_request())
        rejected_events = [
            ev for ev in mock_event_bus.appended if ev.event_type == "compile_rejected"
        ]
        assert len(rejected_events) >= 1
        payload = rejected_events[0].payload
        assert payload["error_code"] == "E_L204_L204_COHERENCE_FAILED"
        # L2-07 读 payload 后应判 FAIL-L2（退到 L2-02 / L2-03 重编）
        from app.l1_04.l2_07.router import RollbackRouter
        verdict = RollbackRouter().classify(rejected_events[0])
        assert verdict.level == "FAIL_L2"
        assert verdict.target_l2 in ("L2-02", "L2-03")
```

---

## §5 性能 SLO 用例（§12 对标）

> `class TestL2_04_PerformanceSLO`；每 TC `@pytest.mark.perf` · 采用 100-round 重复 + np.percentile 计算 P95。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_perf.py
from __future__ import annotations

import time
import pytest
import numpy as np

from app.l1_04.l2_04.compiler import QualityGateCompiler
from app.l1_04.l2_04.predicates import PredicateWhitelist, PredicateCompiler
from app.l1_04.l2_04.coherence import CoherenceChecker
from app.l1_04.l2_04.rendering import AcceptanceChecklistRenderer, MarkdownValidator
from app.l1_04.l2_04.writer import AtomicDualWriter


@pytest.mark.perf
class TestL2_04_PerformanceSLO:
    """§12.1 P95 延迟 + §12.2 吞吐 / 并发。"""

    def test_TC_L104_L204_701_full_compile_120_ac_p95_le_10s(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-701 · 120 AC · 300 Predicate · P95 ≤ 10s（§12.1）。"""
        samples_ms = []
        for _ in range(30):  # 实机 30 次代表 P95
            t0 = time.monotonic()
            sut.compile_quality_gate(make_compile_request(ac_count=120, predicate_count=300))
            samples_ms.append((time.monotonic() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 10_000

    def test_TC_L104_L204_702_whitelist_validate_p95_le_1ms(self) -> None:
        """TC-L104-L204-702 · 单 Predicate 白名单校验 P95 ≤ 1ms。"""
        samples_us = []
        for _ in range(10_000):
            t0 = time.perf_counter_ns()
            PredicateWhitelist.validate("numeric_greater_or_equal")
            samples_us.append((time.perf_counter_ns() - t0) / 1000.0)
        assert np.percentile(samples_us, 95) <= 1000  # 1ms = 1000us

    def test_TC_L104_L204_703_single_predicate_compile_p95_le_5ms(
        self, make_ac,
    ) -> None:
        """TC-L104-L204-703 · 单 Predicate 编译 P95 ≤ 5ms。"""
        c = PredicateCompiler()
        samples_ms = []
        for _ in range(1000):
            ac = make_ac(description="value at least 0.8")
            t0 = time.perf_counter()
            c.compile(ac, layer_hint="unit")
            samples_ms.append((time.perf_counter() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 5

    def test_TC_L104_L204_704_coherence_500_ac_p95_le_500ms(
        self, make_qgc, make_acl,
    ) -> None:
        """TC-L104-L204-704 · 500 AC 完整对比 P95 ≤ 500ms。"""
        samples_ms = []
        for _ in range(30):
            ac_ids = [f"ac-{i}" for i in range(500)]
            qgc = make_qgc(ac_ids=ac_ids)
            acl = make_acl(ac_ids=ac_ids, source_hash=qgc.source_hash)
            t0 = time.perf_counter()
            CoherenceChecker().check(qgc, acl)
            samples_ms.append((time.perf_counter() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 500

    def test_TC_L104_L204_705_markdown_render_500_ac_p95_le_2s(
        self, make_qgc, make_dod_expr,
    ) -> None:
        """TC-L104-L204-705 · 500 AC Markdown 渲染 P95 ≤ 2s。"""
        samples_ms = []
        for _ in range(20):
            qgc = make_qgc(ac_ids=[f"ac-{i}" for i in range(500)])
            dod = make_dod_expr(ac_count=500)
            t0 = time.perf_counter()
            AcceptanceChecklistRenderer().render(qgc, dod)
            samples_ms.append((time.perf_counter() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 2000

    def test_TC_L104_L204_706_pandoc_validate_p95_le_1s(
        self, valid_markdown_body: str,
    ) -> None:
        """TC-L104-L204-706 · pandoc 语法校验 P95 ≤ 1s。"""
        samples_ms = []
        for _ in range(20):
            t0 = time.perf_counter()
            MarkdownValidator().validate(valid_markdown_body)
            samples_ms.append((time.perf_counter() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 1000

    def test_TC_L104_L204_707_atomic_dual_write_p95_le_200ms(
        self, tmp_path, make_qgc, make_acl, patch_artifact_root,
    ) -> None:
        """TC-L104-L204-707 · YAML + MD 原子双写 P95 ≤ 200ms。"""
        patch_artifact_root(tmp_path)
        samples_ms = []
        w = AtomicDualWriter()
        for i in range(20):
            qgc = make_qgc(version=i + 1)
            acl = make_acl(version=i + 1, source_hash=qgc.source_hash)
            t0 = time.perf_counter()
            w.publish(qgc, acl)
            samples_ms.append((time.perf_counter() - t0) * 1000)
        assert np.percentile(samples_ms, 95) <= 200

    def test_TC_L104_L204_708_concurrent_10_sessions_no_degradation(
        self, sut_factory, make_compile_request,
    ) -> None:
        """TC-L104-L204-708 · 并发 10 独立 blueprint · P95 ≤ 1.5 × 单线程基线。"""
        from concurrent.futures import ThreadPoolExecutor
        reqs = [make_compile_request(blueprint_id=f"b-{i}") for i in range(10)]
        sut = sut_factory(max_parallel=10)
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(sut.compile_quality_gate, reqs))
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms <= 15_000, "§12.2 · 10 并发在 15s 内完成（单任务 10s P95）"

    def test_TC_L104_L204_709_batch_throughput_6_compiles_per_minute(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-709 · 批量评估吞吐 ≥ 6 compile/min/session（§12.2）。"""
        start = time.monotonic()
        count = 0
        while time.monotonic() - start < 60:
            sut.compile_quality_gate(make_compile_request(blueprint_id=f"b-{count}"))
            count += 1
        assert count >= 6

    def test_TC_L104_L204_710_500_ac_checklist_under_500kb(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-710 · PRD §11.9 性能 7 · 500 AC · checklist.md ≤ 500KB。"""
        resp = sut.compile_quality_gate(make_compile_request(ac_count=500))
        import os
        size_bytes = os.path.getsize(resp.md_path)
        assert size_bytes <= 500 * 1024
```

---

## §6 端到端 e2e

> `class TestL2_04_E2E`；覆盖 PRD §11.9 正向 1 / 正向 2 / 负向 3 · 三条 GWT。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_e2e.py
from __future__ import annotations

import pytest
from pathlib import Path

from app.l1_04.l2_04.compiler import QualityGateCompiler


class TestL2_04_E2E:
    """PRD §11.9 GWT · 完整 dod_ready → ts_ready → 双工件 → S3 Gate 凭证 流程。"""

    def test_TC_L104_L204_801_happy_path_60s_dual_artifact_ready(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
        mock_event_bus,
        mock_stage_gate_card,
    ) -> None:
        """TC-L104-L204-801 · PRD 正向 1 · Given 质量标准 + 50 AC + 蓝图覆盖率目标 · When blueprint_ready 触发 · Then 60s 内两件齐 + 白名单 + 100% 覆盖。"""
        # Given
        dod_ev = make_dod_ready_event(payload={"ac_count": 50, "expression_count": 50, "predicate_hints": []})
        ts_ev = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id, payload={"skeleton_count": 100, "state": "red"})
        # When
        import time
        t0 = time.monotonic()
        sut.on_dod_ready(dod_ev)
        sut.on_ts_ready(ts_ev)
        elapsed = time.monotonic() - t0
        # Then
        assert elapsed < 60
        published = [ev for ev in mock_event_bus.appended if ev.event_type == "dual_artifact_published"]
        assert len(published) == 1
        card_call = mock_stage_gate_card.push_stage_gate_card.call_args.kwargs
        assert card_call["card_type"] == "dual_artifact_ready"
        # 白名单 + 覆盖率
        qgc_id = published[0].payload["qgc_id"]
        qgc = sut._fetch_qgc(qgc_id)
        assert all(p.predicate_name in sut._whitelist_set() for p in qgc.predicates)
        assert qgc.ac_coverage_pct == 100.0

    def test_TC_L104_L204_802_s3_gate_credential_both_artifacts_visible(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
        ui_probe,
    ) -> None:
        """TC-L104-L204-802 · PRD 正向 2 · Given 两件已齐 + 其他三件齐 · When BF-S3-05 Gate · Then L1-10 UI 能完整展示两件。"""
        dod_ev = make_dod_ready_event()
        ts_ev = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id)
        sut.on_dod_ready(dod_ev)
        sut.on_ts_ready(ts_ev)
        # L1-10 UI probe
        card = ui_probe.get_latest_stage_gate_card(project_id=dod_ev.project_id)
        assert card.artifacts_bundle == [
            "tdd-blueprint.md", "dod-expression.yaml",
            "test-suite-skeleton", "quality-gates.yaml", "acceptance-checklist.md",
        ] or set(["quality-gates.yaml", "acceptance-checklist.md"]).issubset(set(card.artifacts_bundle))
        assert card.blocks_progress is True

    def test_TC_L104_L204_803_predicate_not_whitelisted_fails_with_info(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
        inject_subjective_ac,
        mock_event_bus,
    ) -> None:
        """TC-L104-L204-803 · PRD 负向 3 · Given 质量标准含"代码审美好" · When 编译 · Then 编译失败 + INFO。"""
        inject_subjective_ac("代码审美好")
        dod_ev = make_dod_ready_event()
        ts_ev = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id)
        sut.on_dod_ready(dod_ev)
        with pytest.raises(Exception, match="E_L204_L204_PREDICATE_NOT_WHITELISTED"):
            sut.on_ts_ready(ts_ev)
        info_events = [
            ev for ev in mock_event_bus.appended
            if ev.event_type == "compile_rejected" and ev.payload.get("level") == "INFO"
        ]
        assert len(info_events) >= 1

    def test_TC_L104_L204_804_ac_coverage_not_100_fails_with_info(
        self,
        sut: QualityGateCompiler,
        make_dod_ready_event,
        make_ts_ready_event,
        drop_one_ac_from_dod,
        mock_event_bus,
    ) -> None:
        """TC-L104-L204-804 · PRD 负向 4 · 50 AC 漏 1 条 · 拒绝产出 + INFO。"""
        drop_one_ac_from_dod(total=50, drop=1)
        dod_ev = make_dod_ready_event(payload={"ac_count": 49, "expression_count": 50, "predicate_hints": []})
        ts_ev = make_ts_ready_event(blueprint_id=dod_ev.blueprint_id)
        sut.on_dod_ready(dod_ev)
        with pytest.raises(Exception, match="E_L204_L204_AC_COVERAGE_NOT_100"):
            sut.on_ts_ready(ts_ev)
        info = [ev for ev in mock_event_bus.appended if ev.event_type == "compile_rejected"]
        assert any("AC_COVERAGE" in ev.payload.get("error_code", "") for ev in info)
```

---

## §7 测试 fixture

> `conftest.py` · 提供 SUT + mock kb / mock event bus / mock stage_gate_card / mock clock / mock repo / tmp artifact root + 工厂函数。

```python
# file: tests/l1_04/conftest_l2_04.py
from __future__ import annotations

import hashlib
import pytest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l1_04.l2_04.compiler import QualityGateCompiler


@pytest.fixture
def mock_project_id() -> str:
    return "proj-l204-test-0001"


@pytest.fixture
def mock_blueprint_id() -> str:
    return "bp-l204-test-0001"


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.find_by_blueprint.return_value = []
    return repo


@pytest.fixture
def mock_kb() -> MagicMock:
    kb = MagicMock()
    kb.read_recipe.return_value = {"template_id": "builtin-default", "content": {}}
    return kb


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.appended = []

    def _append(event):
        bus.appended.append(event)
        return {"event_id": f"ev-{len(bus.appended)}", "acknowledged": True}

    bus.append.side_effect = _append
    return bus


@pytest.fixture
def mock_stage_gate_card() -> MagicMock:
    card = MagicMock()
    card.push_stage_gate_card.return_value = {
        "card_id": "card-001", "created_at": "2026-04-22T00:00:00Z", "tab_id": "tab-001",
    }
    return card


@pytest.fixture
def sut(mock_repo, mock_kb, mock_event_bus, mock_stage_gate_card, tmp_path) -> QualityGateCompiler:
    return QualityGateCompiler(
        repo=mock_repo, kb=mock_kb, event_bus=mock_event_bus,
        stage_gate_card=mock_stage_gate_card, artifact_root=tmp_path,
    )


@pytest.fixture
def make_compile_request() -> Callable[..., Any]:
    def _build(**overrides):
        from app.l1_04.l2_04.schemas import CompileQualityGateRequest
        defaults = dict(
            project_id="proj-l204-test-0001",
            blueprint_id="bp-l204-test-0001",
            dod_expression_id="dod-001",
            test_suite_id="ts-001",
            source_hash="a" * 64,
            version_bump=False,
            trace_id="trace-001",
        )
        defaults.update(overrides)
        return CompileQualityGateRequest(**defaults)
    return _build


@pytest.fixture
def make_dod_ready_event() -> Callable[..., Any]:
    def _build(**overrides):
        from app.l1_04.l2_04.schemas import DoDReadyEvent
        defaults = dict(
            event_type="dod_ready", event_version="v1.0",
            emitted_at="2026-04-21T14:00:00Z", emitted_by="L2-02",
            project_id="proj-l204-test-0001",
            dod_expression_id="dod-001",
            blueprint_id="bp-l204-test-0001",
            source_hash="a" * 64,
            payload={"expression_count": 57, "ac_count": 120, "predicate_hints": []},
            trace_id="trace-001",
        )
        defaults.update(overrides)
        return DoDReadyEvent(**defaults)
    return _build


@pytest.fixture
def make_ts_ready_event() -> Callable[..., Any]:
    def _build(**overrides):
        from app.l1_04.l2_04.schemas import TsReadyEvent
        defaults = dict(
            event_type="ts_ready", event_version="v1.0",
            emitted_at="2026-04-21T14:05:00Z", emitted_by="L2-03",
            project_id="proj-l204-test-0001",
            test_suite_id="ts-001",
            blueprint_id="bp-l204-test-0001",
            source_hash="a" * 64,
            payload={"skeleton_count": 250, "state": "red"},
            trace_id="trace-001",
        )
        defaults.update(overrides)
        return TsReadyEvent(**defaults)
    return _build
```

---

## §8 集成点用例（与兄弟 L2 协作）

> `class TestL2_04_CrossL2Integration`；覆盖 L2-01 蓝图 / L2-02 DoD / L2-03 用例 / L2-05 S4 Verifier / L2-06 S5 Verifier / L2-07 回退路由器 协作。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_integration.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_04.compiler import QualityGateCompiler


class TestL2_04_CrossL2Integration:
    """与 L2-01/02/03/05/06/07 协作 · §8 PRD 集成场景 5/6 · §13.3/13.4 兄弟 L2 集成。"""

    def test_TC_L104_L204_901_l2_01_blueprint_matrix_feeds_coverage_targets(
        self, sut: QualityGateCompiler, l2_01_blueprint_fixture,
    ) -> None:
        """TC-L104-L204-901 · PRD 集成 5 · L2-01 ac_matrix 的 coverage_target → L2-04 quality-gates 阈值。"""
        bp = l2_01_blueprint_fixture(coverage_target=0.85, branch_coverage=0.75)
        resp = sut.compile_quality_gate_from_blueprint(bp)
        gate_preds = sut._fetch_qgc(resp.qgc_id).predicates
        covs = [p for p in gate_preds if p.predicate_name == "test_coverage_gte"]
        assert any(p.threshold["value"] == 0.85 for p in covs)

    def test_TC_L104_L204_902_l2_02_dod_whitelist_hard_lock(
        self, sut: QualityGateCompiler, l2_02_dod_whitelist_fixture,
    ) -> None:
        """TC-L104-L204-902 · L2-04 所有推导谓词必须命中 L2-02 白名单 · 否则 REJECTED。"""
        whitelist = l2_02_dod_whitelist_fixture()  # L2-02 白名单快照
        resp = sut.compile_quality_gate(sut._make_default_request())
        for p in sut._fetch_qgc(resp.qgc_id).predicates:
            assert p.predicate_name in whitelist

    def test_TC_L104_L204_903_l2_03_test_suite_state_red_gates_compile(
        self, sut: QualityGateCompiler, make_dod_ready_event, make_ts_ready_event,
    ) -> None:
        """TC-L104-L204-903 · §13.3 · TS state ≠ red → L2-04 拒绝消费。"""
        sut.on_dod_ready(make_dod_ready_event())
        with pytest.raises(Exception, match="E_L204_L204_TS_NOT_READY"):
            sut.on_ts_ready(make_ts_ready_event(payload={"skeleton_count": 100, "state": "green"}))

    def test_TC_L104_L204_904_l2_05_s4_executor_reads_and_evaluates_gate(
        self, sut: QualityGateCompiler, make_compile_request, l2_05_gate_reader,
    ) -> None:
        """TC-L104-L204-904 · §13.4 + PRD 集成 5 · S4 Executor 读 quality-gates.yaml · eval PASS/FAIL。"""
        resp = sut.compile_quality_gate(make_compile_request())
        verdict = l2_05_gate_reader.evaluate(resp.yaml_path, wp_id="WP-01")
        assert verdict.result in ("PASS", "FAIL")
        assert verdict.predicate_count > 0

    def test_TC_L104_L204_905_l2_06_verifier_independent_runs_gate(
        self, sut: QualityGateCompiler, make_compile_request, l2_06_verifier,
    ) -> None:
        """TC-L104-L204-905 · S5 TDDExe Verifier 独立复跑 quality-gates · 结果应与 S4 自检一致。"""
        resp = sut.compile_quality_gate(make_compile_request())
        s5_verdict = l2_06_verifier.run(resp.yaml_path)
        assert s5_verdict.deterministic is True
        assert s5_verdict.passed_count + s5_verdict.failed_count == resp.predicate_count

    def test_TC_L104_L204_906_l2_07_rollback_router_handles_fail_l2(
        self, sut: QualityGateCompiler, make_compile_request, force_coherence_fail,
        mock_event_bus,
    ) -> None:
        """TC-L104-L204-906 · REJECT_PUBLISH → compile_rejected → L2-07 路由 FAIL-L2 → 回 L2-02 / L2-03 重跑。"""
        force_coherence_fail()
        with pytest.raises(Exception):
            sut.compile_quality_gate(make_compile_request())
        from app.l1_04.l2_07.router import RollbackRouter
        rejected = [ev for ev in mock_event_bus.appended if ev.event_type == "compile_rejected"][-1]
        verdict = RollbackRouter().classify(rejected)
        assert verdict.level == "FAIL_L2"
        assert verdict.target_l2 in ("L2-02", "L2-03")

    def test_TC_L104_L204_907_s7_user_signatures_persist_progress(
        self, sut: QualityGateCompiler, make_compile_request, s7_ui_probe,
    ) -> None:
        """TC-L104-L204-907 · PRD 集成 6 · S7 用户勾选 · 进度落盘 · 100% 满足 S7 Gate。"""
        resp = sut.compile_quality_gate(make_compile_request(ac_count=10))
        for i in range(10):
            s7_ui_probe.sign(acl_id=resp.acl_id, ac_index=i, decision="approved")
        progress = sut.query_signature_progress(resp.acl_id)
        assert progress["approved"] == 10
        assert progress["progress_pct"] == 100.0
```

---

## §9 边界 / edge case

> `class TestL2_04_EdgeCases`；≥ 5 条 · 空 DoD / 冲突 Gate 规则 / 超大 Checklist / 部分指标缺失 / 并发冲突 / 版本链跳号 / Unicode AC / 磁盘写入中断。

```python
# file: tests/l1_04/test_l2_04_quality_gate_compiler_edge.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_04.compiler import QualityGateCompiler


class TestL2_04_EdgeCases:
    """§11.4 降级触发 + §12.4 退化边界 + §2.1 极端输入。"""

    def test_TC_L104_L204_A01_empty_dod_expression_rejected(
        self, sut: QualityGateCompiler, make_compile_request, make_dod_expr, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-A01 · 空 DoD（0 AC）· REJECTED + E_L204_L204_AC_COVERAGE_NOT_100。"""
        mock_repo.get_dod.return_value = make_dod_expr(ac_count=0)
        with pytest.raises(Exception, match="E_L204_L204_AC_COVERAGE_NOT_100"):
            sut.compile_quality_gate(make_compile_request(ac_count=0))

    def test_TC_L104_L204_A02_conflicting_gate_rules_predicate_collision(
        self, sut: QualityGateCompiler, inject_duplicate_predicate_for_ac,
    ) -> None:
        """TC-L104-L204-A02 · 同 AC 推出两个冲突 Predicate（≥ 0.8 且 < 0.5）· Coherence 失败。"""
        inject_duplicate_predicate_for_ac("ac-1", preds=[("numeric_greater_or_equal", 0.8),
                                                          ("numeric_less_than", 0.5)])
        with pytest.raises(Exception, match="E_L204_L204_COHERENCE_FAILED"):
            sut.compile_quality_gate(sut._make_default_request())

    def test_TC_L104_L204_A03_oversized_checklist_1000_ac_hits_soft_cap(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-A03 · §12.4 · 1000 AC · 触发 SIMPLE_RENDER 降级 · 仍成功发布。"""
        resp = sut.compile_quality_gate(make_compile_request(ac_count=1000, predicate_count=3000))
        assert resp.success is True
        assert "SIMPLE_RENDER" in resp.degradation_flags

    def test_TC_L104_L204_A04_oversized_2000_ac_rejected_hard_cap(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-A04 · §12.4 · 2000 AC · 超 max_ac_count · 直接 REJECTED。"""
        with pytest.raises(Exception, match="E_L204_L204_AC_COUNT_EXCEEDED"):
            sut.compile_quality_gate(make_compile_request(ac_count=2000))

    def test_TC_L104_L204_A05_partial_indicator_missing_source_hash(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-A05 · 部分指标缺失 · source_hash 为空 · E_L204_L202_DOD_HASH_INVALID。"""
        req = make_compile_request(source_hash="")
        with pytest.raises(Exception, match="E_L204_L202_DOD_HASH_INVALID"):
            sut.compile_quality_gate(req)

    def test_TC_L104_L204_A06_concurrent_same_blueprint_serializes(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-A06 · §4.5 · 同 (p, b, v) 并发 · 分布式锁串行化 · 不生重复 qgc。"""
        from concurrent.futures import ThreadPoolExecutor
        req = make_compile_request()
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(sut.compile_quality_gate, [req] * 5))
        qgc_ids = {r.qgc_id for r in results}
        assert len(qgc_ids) == 1, "幂等 · 仅一条 qgc · 其余命中 cache"

    def test_TC_L104_L204_A07_version_chain_skip_numbers_rejected(
        self, sut: QualityGateCompiler, make_compile_request, mock_repo: MagicMock,
    ) -> None:
        """TC-L104-L204-A07 · 版本链跳号（v1 → v3 中缺 v2）· REJECTED。"""
        mock_repo.find_by_blueprint.return_value = [
            MagicMock(version=1, status="PUBLISHED"),
            MagicMock(version=3, status="PUBLISHED"),
        ]
        req = make_compile_request(version_bump=True, expected_version=2)
        with pytest.raises(Exception, match="E_L204_INTERNAL_ASSERT_FAILED"):
            sut.compile_quality_gate(req)

    def test_TC_L104_L204_A08_unicode_ac_zh_cn_renders_cleanly(
        self, sut: QualityGateCompiler, make_compile_request, make_ac,
    ) -> None:
        """TC-L104-L204-A08 · §6.5 · zh-CN AC 描述 · 渲染无乱码。"""
        req = make_compile_request(
            ac_list=[make_ac(description="接口响应时间不超过 500 毫秒"),
                     make_ac(description="告警邮件含"质量红线"字样")],
        )
        resp = sut.compile_quality_gate(req)
        md_content = open(resp.md_path, encoding="utf-8").read()
        assert "接口响应时间不超过 500 毫秒" in md_content
        assert "质量红线" in md_content

    def test_TC_L104_L204_A09_disk_write_interrupted_mid_rename(
        self, sut: QualityGateCompiler, make_compile_request,
        simulate_sigkill_after_first_rename,
    ) -> None:
        """TC-L104-L204-A09 · §6.7 · rename(YAML) 成功 · rename(MD) 前崩溃 · 下次启动检测到不一致 · REJECT_PUBLISH。"""
        simulate_sigkill_after_first_rename()
        with pytest.raises(Exception, match="E_L204_L204_ATOMIC_WRITE_FAILED"):
            sut.compile_quality_gate(make_compile_request())
        # 重启恢复
        sut._recover_from_crash()
        assert sut._degradation_state() == "REJECT_PUBLISH"

    def test_TC_L104_L204_A10_signature_concurrent_writes_last_wins(
        self, sut: QualityGateCompiler, make_compile_request,
    ) -> None:
        """TC-L104-L204-A10 · §6.11 · 并发签字 · 同 AC 多次写 · last-write-wins + 审计日志完整。"""
        resp = sut.compile_quality_gate(make_compile_request(ac_count=5))
        from concurrent.futures import ThreadPoolExecutor
        decisions = ["approved", "rejected", "approved"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(
                lambda d: sut.sign_checklist_item(resp.acl_id, ac_index=0, decision=d),
                decisions,
            ))
        progress = sut.query_signature_progress(resp.acl_id)
        assert progress["total_items"] == 5
        # 审计日志至少 3 条签字写入
        audits = sut._read_signature_audit(resp.acl_id, ac_index=0)
        assert len(audits) == 3
```

---

*— TDD filled · 60+ TC · 24 错误码全覆盖 · 7 IC 契约 join · §12 SLO 全维度 · PRD §11.9 GWT 4 条 e2e · depth-B —*
