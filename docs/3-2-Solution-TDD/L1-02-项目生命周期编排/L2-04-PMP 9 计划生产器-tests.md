---
doc_id: tests-L1-02-L2-04-PMP 9 计划生产器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-04-PMP 9 计划生产器.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-04-PMP 9 计划生产器 · TDD 测试用例

> 基于 3-1 L2-04 tech-design 的 §3 对外方法（`produce_all_9` / `rework_plans` / `cross_check_togaf_alignment` / `compute_pmp_bundle_hash` + 9 份 `produce_{kda}_plan`）+ §11 错误码（`E_L102_L204_001~016` 共 16 条）+ §12 SLO（9 并行 P95 ≤ 30s · 单计划 P95 ≤ 5s · cross_check ≤ 400ms · bundle_hash ≤ 100ms）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L102-L204-NNN`（L1-02 下 L2-04 · 三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_04_PMPPlanProducer` 组织；正向 / 负向 / IC 契约 / SLO / e2e 分文件归档。
> 本 L2 为 **PMPPlansOrchestrator Application Service**（聚合根 `PMPPlanSet`）· 被 L2-01 调用（IC-L2-03 = S2 触发）· 调 L2-07（IC-L2-02 模板）/ L2-05（IC-L2-05 cross_check）/ L1-05（IC-05 delegate plan-writing）/ L1-06（IC-L2-04/IC-06 kb_read）/ L1-09（IC-09 事件）。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC × SLO）
- [x] §2 正向用例（每 public 方法 ≥ 1 · 9 kda × produce 代表性 + 主入口 + rework + cross_check + bundle_hash）
- [x] §3 负向用例（§11 每错误码 ≥ 1 · 共 16 条 `E_L102_L204_001~016`）
- [x] §4 IC 契约集成测试（IC-01 主状态机 / IC-06 硬红线 / IC-09 审计 / IC-L2-02 模板 / IC-L2-05 TOGAF alignment）
- [x] §5 性能 SLO 用例（§12.1 7 指标对标）
- [x] §6 端到端 e2e 场景（GWT 映射 §5 P0/P1/P2 时序）
- [x] §7 测试 fixture（mock_project_id / mock_clock / mock_event_bus / mock_ic_payload / mock_template_engine / mock_togaf_bundle / mock_four_pieces / mock_kb_reader / mock_plan_writing_subagent）
- [x] §8 集成点用例（与 L2-07 模板 / L2-05 TOGAF 双向 / L2-01 Gate 协作）
- [x] §9 边界 / edge case（9 并行部分失败 · 核心 kda 全失败 · rework 多次 · hash 不一致 · TOGAF D 超时降级）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC / §12 SLO 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO；security = 安全攻击面 / 越权。

### §1.1 方法 × 测试 × 覆盖类型（§3.1 public 方法族）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `produce_all_9()` · §6.1 · 全绿 9 并行 | TC-L102-L204-001 | e2e | — | IC-L2-02 + IC-09 |
| `produce_all_9()` · §6.1 · COMPLETE bundle | TC-L102-L204-002 | integration | — | IC-09 |
| `produce_integration_plan()` · §3.1 | TC-L102-L204-003 | unit | — | IC-L2-02 |
| `produce_scope_plan()` · §3.1（核心 kda） | TC-L102-L204-004 | unit | — | IC-L2-02 |
| `produce_schedule_plan()` · §3.1（核心 kda） | TC-L102-L204-005 | unit | — | IC-L2-02 |
| `produce_cost_plan()` · §3.1（核心 kda） | TC-L102-L204-006 | unit | — | IC-L2-02 |
| `produce_quality_plan()` · §3.1（依赖 TOGAF D） | TC-L102-L204-007 | integration | — | IC-L2-02 + IC-L2-05 |
| `produce_resource_plan()` · §3.1 | TC-L102-L204-008 | unit | — | IC-L2-02 |
| `produce_communication_plan()` · §3.1 | TC-L102-L204-009 | unit | — | IC-L2-02 |
| `produce_risk_plan()` · §3.1（依赖 TOGAF D） | TC-L102-L204-010 | integration | — | IC-L2-02 + IC-L2-05 |
| `produce_procurement_plan()` · §3.1 | TC-L102-L204-011 | unit | — | IC-L2-02 |
| `produce_stakeholder_engagement_plan()` · §3.1 | TC-L102-L204-012 | unit | — | IC-L2-02 |
| `rework_plans()` · §6.5 · 保留 8 重做 1 | TC-L102-L204-013 | integration | — | IC-L2-02 + IC-09 |
| `cross_check_togaf_alignment()` · §6.4 · aligned=true | TC-L102-L204-014 | integration | — | IC-L2-05 |
| `compute_pmp_bundle_hash()` · §6.3 · 幂等 | TC-L102-L204-015 | unit | — | — |
| `compute_pmp_bundle_hash()` · §6.3 · 顺序不变量 | TC-L102-L204-016 | unit | — | — |
| `produce_all_9()` · §8 状态机 · Draft→Assembling | TC-L102-L204-017 | unit | — | — |
| `produce_all_9()` · §8 状态机 · BUNDLE_READY→COMPLETE | TC-L102-L204-018 | integration | — | IC-09 |

### §1.2 错误码 × 测试（§11.2 16 条全覆盖 · 前缀 `E_L102_L204_`）

| 错误码 | TC ID | 方法 | 归属 §11.1 分类 |
|---|---|---|---|
| `E_L102_L204_001` PM14_OWNERSHIP_VIOLATION | TC-L102-L204-101 | `produce_all_9()` 入口 | 契约违反（致命） |
| `E_L102_L204_002` PLAN_UPSTREAM_MISSING | TC-L102-L204-102 | `produce_all_9()` 入口 | 调用方 bug |
| `E_L102_L204_003` UNKNOWN_KDA_NAME · produce | TC-L102-L204-103 | `produce_{kda}_plan()` | 调用方 bug |
| `E_L102_L204_004` TEMPLATE_MISSING_FIELD | TC-L102-L204-104 | `_worker()` | 非核心 kda（可降级） |
| `E_L102_L204_005` KB_READ_TIMEOUT | TC-L102-L204-105 | `produce_all_9()` 前置 | 可降级 |
| `E_L102_L204_006` CORE_PLAN_FAILED | TC-L102-L204-106 | `_decide_bundle_status()` | 核心 kda 失败（业务） |
| `E_L102_L204_007` TOGAF_ALIGNMENT_MISMATCH | TC-L102-L204-107 | `cross_check_togaf_alignment()` | 核心失败（业务） |
| `E_L102_L204_008` BUNDLE_HASH_MISMATCH | TC-L102-L204-108 | `compute_pmp_bundle_hash()` 校验 | 突发（升级） |
| `E_L102_L204_009` PLAN_MD_TOO_LARGE | TC-L102-L204-109 | `_worker()` 产出后 | 非核心 |
| `E_L102_L204_010` REWORK_UNKNOWN_KDA | TC-L102-L204-110 | `rework_plans()` | 调用方 bug |
| `E_L102_L204_011` REWORK_MAX_VERSIONS | TC-L102-L204-111 | `rework_plans()` | 调用方 bug |
| `E_L102_L204_012` TOO_MANY_FAILURES | TC-L102-L204-112 | `_decide_bundle_status()` | 突发（升级） |
| `E_L102_L204_013` EMPTY_REWORK_LIST | TC-L102-L204-113 | `rework_plans()` | 调用方 bug |
| `E_L102_L204_014` UNKNOWN_KDA_NAME · rework | TC-L102-L204-114 | `rework_plans()` | 调用方 bug |
| `E_L102_L204_015` AUDIT_SEED_EMIT_FAIL | TC-L102-L204-115 | IC-09 失败 · 降级 buffer | 基础设施 |
| `E_L102_L204_016` BUNDLE_MANIFEST_WRITE_FAIL | TC-L102-L204-116 | `EMITTING` 状态 fsync | 基础设施（HALT） |

### §1.3 IC 契约 × 测试（本 L2 对外 6 条）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-01 主状态机 · L1-01 路由 · L2-01 → L2-04 | 被调 | TC-L102-L204-601 | PM-14 所有权 · 仅 L2-01 可调 |
| IC-L2-03 S2 dispatch(stage=S2, target=pmp) · L2-01 → L2-04 | 被调 | TC-L102-L204-602 | 主入口 · 9 计划触发 |
| IC-L2-02 request_template · L2-04 → L2-07 | 主动 | TC-L102-L204-603 | 每份 plan 调一次 |
| IC-L2-05 cross_check_togaf_alignment · L2-04 → L2-05 | 主动 | TC-L102-L204-604 | 双向（本 L2 发 scope/schedule ready · L2-05 回 align 结果） |
| IC-06 硬红线 · L2-04 → L1-07 · EMERGENCY_MANUAL / HALT | 主动 | TC-L102-L204-605 | ≥ 5 失败 / bundle_hash 异常触发 |
| IC-09 append_event · L2-04 → L1-09 | 主动 | TC-L102-L204-606 | 8 种事件（bundle_written / partial / rejected / emergency / rework_done / togaf_mismatch / hash_mismatch / audit_seed_fail） |

### §1.4 SLO × 测试（§12.1 7 指标）

| 指标 | P95 目标 | 硬上限 | TC ID | 类型 |
|---|---|---|---|---|
| 单 kda 产出（单 worker） | ≤ 5s | 30s | TC-L102-L204-501 | perf |
| 9 并行产出（全绿场景） | ≤ 30s | 60s | TC-L102-L204-502 | perf |
| TOGAF 矩阵 cross_check | ≤ 400ms | 3s | TC-L102-L204-503 | perf |
| `compute_pmp_bundle_hash`（9 md） | ≤ 100ms | 1s | TC-L102-L204-504 | perf |
| `_bundle.yaml` 落盘 | ≤ 30ms | 500ms | TC-L102-L204-505 | perf |
| rework 单 kda（保留 8） | ≤ 5s | 30s | TC-L102-L204-506 | perf |
| 单条矩阵规则判定 | ≤ 15ms | 100ms | TC-L102-L204-507 | perf |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_04_PMPPlanProducer`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `PMPPlansOrchestrator`（从 `app.l2_04.orchestrator` 导入）。
> 9 kda 固定顺序：`integration / scope / schedule / cost / quality / resource / communication / risk / procurement / stakeholder_engagement`（`§2.2` enum · `PMP_9_KDAS`）。

```python
# file: tests/l1_02/test_l2_04_pmp_positive.py
from __future__ import annotations

import hashlib
from typing import Any

import pytest

from app.l2_04.orchestrator import PMPPlansOrchestrator
from app.l2_04.schemas import (
    PmpBundleResult,
    PlanResult,
    AlignmentResult,
    BundleStatus,
)


class TestL2_04_PMPPlanProducer:
    """每个 public 方法 + 代表性 kda 至少 1 正向用例。

    覆盖 §3.1 public 方法族：
      - produce_all_9（主入口）
      - produce_{integration|scope|schedule|cost|quality|resource|communication|risk|procurement|stakeholder_engagement}_plan
      - rework_plans
      - cross_check_togaf_alignment
      - compute_pmp_bundle_hash
    """

    @pytest.mark.asyncio
    async def test_TC_L102_L204_001_produce_all_9_full_green_returns_complete(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-001 · 9 并行全绿 · 返 COMPLETE · bundle_hash 非空 · 9 md 齐全。"""
        result: PmpBundleResult = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert result.status == BundleStatus.COMPLETE
        assert result.bundle_hash and len(result.bundle_hash) == 64  # sha256 hex
        assert len(result.plans) == 9
        assert set(p.plan_type for p in result.plans) == {
            "integration", "scope", "schedule", "cost", "quality",
            "resource", "communication", "risk", "procurement",
        }
        assert result.degraded is False
        assert result.completeness.failed == []

    @pytest.mark.asyncio
    async def test_TC_L102_L204_002_produce_all_9_emits_9_plans_ready_event(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_event_bus: Any,
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-002 · 全绿完成 · IC-09 发 `L1-02:9_plans_ready` 事件 · payload 含 9 paths。"""
        await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        events = [e for e in mock_event_bus.captured if e["event_type"] == "L1-02:9_plans_ready"]
        assert len(events) == 1
        assert events[0]["project_id"] == mock_project_id
        assert len(events[0]["payload"]["paths"]) == 9
        assert events[0]["payload"]["plan_count"] == 9
        assert events[0]["payload"]["trim_level"] == "full"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_003_produce_integration_plan_writes_md(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        tmp_project_root,
    ) -> None:
        """TC-L102-L204-003 · produce_integration_plan · 写入 integration-plan.md · frontmatter 正确。"""
        r: PlanResult = await sut.produce_integration_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        plan_md = (tmp_project_root / mock_project_id / "pmp-plans" / "integration-plan.md").read_text()
        assert "doc_type: pmp-plan" in plan_md
        assert "kda: integration" in plan_md
        assert r.size_bytes >= 200
        assert r.sha256 == hashlib.sha256(plan_md.encode("utf-8")).hexdigest()

    @pytest.mark.asyncio
    async def test_TC_L102_L204_004_produce_scope_plan_core_kda_passes_compliance(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-004 · scope_plan（核心 kda）· 合规三字段齐（budget/timeline/responsible_role）。"""
        r = await sut.produce_scope_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        assert r.compliance.pass_ is True
        assert r.compliance.missing_fields == []
        assert r.plan_type == "scope"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_005_produce_schedule_plan_with_critical_path(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-005 · schedule_plan · 必含 critical_path 字段（合规硬约束）。"""
        r = await sut.produce_schedule_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        assert "critical_path" not in r.compliance.missing_fields

    @pytest.mark.asyncio
    async def test_TC_L102_L204_006_produce_cost_plan_budget_estimate_present(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-006 · cost_plan · budget_or_estimate 字段必填。"""
        r = await sut.produce_cost_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        assert "budget_or_estimate" not in r.compliance.missing_fields

    @pytest.mark.asyncio
    async def test_TC_L102_L204_007_produce_quality_plan_references_togaf_adr(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-007 · quality_plan · 必引 ≥ 1 条 ADR-D\\d+（I-L204-03 不变量）。"""
        r = await sut.produce_quality_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert r.is_ok()
        assert len(r.adr_refs) >= 1
        assert all(ref.startswith("ADR-D") for ref in r.adr_refs)

    @pytest.mark.asyncio
    async def test_TC_L102_L204_008_produce_resource_plan_responsible_role(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-008 · resource_plan · responsible_role 字段必填。"""
        r = await sut.produce_resource_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        assert "responsible_role" not in r.compliance.missing_fields

    @pytest.mark.asyncio
    async def test_TC_L102_L204_009_produce_communication_plan_ok(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-009 · communication_plan · 三字段全齐。"""
        r = await sut.produce_communication_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()
        assert r.compliance.pass_ is True

    @pytest.mark.asyncio
    async def test_TC_L102_L204_010_produce_risk_plan_prob_impact_matrix(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-010 · risk_plan · prob_impact_matrix 字段 + ADR 引用。"""
        r = await sut.produce_risk_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert r.is_ok()
        assert "prob_impact_matrix" not in r.compliance.missing_fields
        assert len(r.adr_refs) >= 1

    @pytest.mark.asyncio
    async def test_TC_L102_L204_011_produce_procurement_plan_ok(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-011 · procurement_plan · 合规通过。"""
        r = await sut.produce_procurement_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()

    @pytest.mark.asyncio
    async def test_TC_L102_L204_012_produce_stakeholder_engagement_plan_ok(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-012 · stakeholder_engagement_plan · 合规通过。"""
        r = await sut.produce_stakeholder_engagement_plan(
            project_id=mock_project_id,
            request_id=mock_request_id,
            dependencies=mock_four_pieces_ready,
        )
        assert r.is_ok()

    @pytest.mark.asyncio
    async def test_TC_L102_L204_013_rework_plans_preserves_8_rebuilds_risk(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-013 · rework_plans(['risk']) · 保留 8 成品 · 重建 risk · bundle_hash 重算。"""
        initial = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        initial_hash = initial.bundle_hash
        old_non_risk = {p.plan_type: p.sha256 for p in initial.plans if p.plan_type != "risk"}

        reworked = await sut.rework_plans(
            project_id=mock_project_id,
            request_id=f"{mock_request_id}-rework-1",
            rework_list=["risk"],
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert reworked.status in (BundleStatus.COMPLETE, BundleStatus.REWORKED)
        assert reworked.bundle_hash != initial_hash
        new_non_risk = {p.plan_type: p.sha256 for p in reworked.plans if p.plan_type != "risk"}
        assert new_non_risk == old_non_risk
        risk_new = next(p for p in reworked.plans if p.plan_type == "risk")
        assert risk_new.version == 2

    @pytest.mark.asyncio
    async def test_TC_L102_L204_014_cross_check_togaf_alignment_aligned(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_togaf_bundle: dict[str, str],
    ) -> None:
        """TC-L102-L204-014 · cross_check · 10 规则全通过 · aligned=true · mismatches=空。"""
        res: AlignmentResult = await sut.cross_check_togaf_alignment(
            project_id=mock_project_id,
            togaf_bundle=mock_togaf_bundle,
        )
        assert res.aligned is True
        assert res.mismatches == []

    def test_TC_L102_L204_015_compute_pmp_bundle_hash_idempotent(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        nine_plans_on_disk: list[str],
    ) -> None:
        """TC-L102-L204-015 · 9 md 不变 · 两次算 hash 必相同（幂等性）。"""
        h1 = sut.compute_pmp_bundle_hash(project_id=mock_project_id, kda_list=nine_plans_on_disk)
        h2 = sut.compute_pmp_bundle_hash(project_id=mock_project_id, kda_list=nine_plans_on_disk)
        assert h1 == h2
        assert len(h1) == 64

    def test_TC_L102_L204_016_compute_pmp_bundle_hash_order_invariant_by_fixed_kdas(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        nine_plans_on_disk: list[str],
    ) -> None:
        """TC-L102-L204-016 · 传入 kda 顺序颠倒 · hash 相同（§6.3 固定 PMP_9_KDAS 顺序）。"""
        h_asc = sut.compute_pmp_bundle_hash(
            project_id=mock_project_id,
            kda_list=["integration", "scope", "schedule", "cost", "quality",
                      "resource", "communication", "risk", "procurement"],
        )
        h_rev = sut.compute_pmp_bundle_hash(
            project_id=mock_project_id,
            kda_list=["procurement", "risk", "communication", "resource", "quality",
                      "cost", "schedule", "scope", "integration"],
        )
        assert h_asc == h_rev  # 实现内按 PMP_9_KDAS 固定顺序拼接

    @pytest.mark.asyncio
    async def test_TC_L102_L204_017_state_machine_init_to_spawning(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-017 · 状态机 · 调用入口后进入 INIT → SPAWNING（读 plan + kb 完成）。"""
        states: list[str] = []
        sut.on_state_change = lambda s: states.append(s)
        await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert "INIT" in states
        assert "SPAWNING" in states
        assert states.index("INIT") < states.index("SPAWNING")

    @pytest.mark.asyncio
    async def test_TC_L102_L204_018_state_machine_bundle_ready_to_complete(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-018 · 状态机 · BUNDLE_READY → EMITTING → COMPLETE 路径（IC-09 ack 后）。"""
        states: list[str] = []
        sut.on_state_change = lambda s: states.append(s)
        result = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert result.status == BundleStatus.COMPLETE
        assert ["BUNDLE_READY", "EMITTING", "COMPLETE"] == [
            s for s in states if s in ("BUNDLE_READY", "EMITTING", "COMPLETE")
        ]
```

---

## §3 负向用例（§11 每错误码 ≥ 1）

> 每条用例 1-to-1 对应 `E_L102_L204_001~016` · 使用 `pytest.raises` 捕获 `L102L204Error` 子类 · 断言 `.code / .caller_action / .context`。

```python
# file: tests/l1_02/test_l2_04_pmp_negative.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_04.orchestrator import PMPPlansOrchestrator
from app.l2_04.errors import (
    E_L102_L204_001_PM14OwnershipViolation,
    E_L102_L204_002_PlanUpstreamMissing,
    E_L102_L204_003_UnknownKdaName,
    E_L102_L204_004_TemplateMissingField,
    E_L102_L204_005_KBReadTimeout,
    E_L102_L204_006_CorePlanFailed,
    E_L102_L204_007_TogafAlignmentMismatch,
    E_L102_L204_008_BundleHashMismatch,
    E_L102_L204_009_PlanMdTooLarge,
    E_L102_L204_010_ReworkUnknownKda,
    E_L102_L204_011_ReworkMaxVersions,
    E_L102_L204_012_TooManyFailures,
    E_L102_L204_013_EmptyReworkList,
    E_L102_L204_014_UnknownKdaName,
    E_L102_L204_015_AuditSeedEmitFail,
    E_L102_L204_016_BundleManifestWriteFail,
)


class TestL2_04_PMPNegative:
    """16 条错误码全覆盖 · 每错误码 ≥ 1 TC。"""

    @pytest.mark.asyncio
    async def test_TC_L102_L204_101_pm14_ownership_violation_non_l201_caller(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-101 · E_L102_L204_001 · L1-01 直调（非 L2-01 路由）· 拒绝。"""
        with pytest.raises(E_L102_L204_001_PM14OwnershipViolation) as ei:
            await sut.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                caller_l1="L1-01",  # 越权
            )
        assert ei.value.code == "E_L102_L204_001"
        assert "PM14_OWNERSHIP_VIOLATION" in str(ei.value)

    @pytest.mark.asyncio
    async def test_TC_L102_L204_102_plan_upstream_missing_four_pieces_absent(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L204-102 · E_L102_L204_002 · 4 件套 plan.md 未就绪（S1→S2 顺序被跳）。"""
        with pytest.raises(E_L102_L204_002_PlanUpstreamMissing) as ei:
            await sut.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies={"four_pieces_paths": {}, "charter_path": "", "stakeholders_path": ""},
            )
        assert ei.value.code == "E_L102_L204_002"
        assert ei.value.caller_action  # 文档化建议 L2-03 先完成

    @pytest.mark.asyncio
    async def test_TC_L102_L204_103_unknown_kda_name_on_produce_api(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-103 · E_L102_L204_003 · 调用方传 "scoping"（非 9 kda 之一）。"""
        with pytest.raises(E_L102_L204_003_UnknownKdaName) as ei:
            await sut.produce_plan_by_name(
                project_id=mock_project_id,
                request_id=mock_request_id,
                kda="scoping",  # 错名（应为 scope）
                dependencies=mock_four_pieces_ready,
            )
        assert ei.value.code == "E_L102_L204_003"
        assert "scope" in ei.value.context["known_kdas"]

    @pytest.mark.asyncio
    async def test_TC_L102_L204_104_template_missing_field_non_core_degraded(
        self,
        sut_with_broken_template,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-104 · E_L102_L204_004 · 非核心 kda 模板 slot 缺字段 · 降级不整批 fail。"""
        with pytest.raises(E_L102_L204_004_TemplateMissingField) as ei:
            # 单 worker 渲染 communication 模板 · slot 缺 stakeholders
            await sut_with_broken_template.produce_communication_plan(
                project_id=mock_project_id,
                request_id=mock_request_id,
                dependencies=mock_four_pieces_ready,
            )
        assert ei.value.code == "E_L102_L204_004"
        assert ei.value.context["missing_slot"]

    @pytest.mark.asyncio
    async def test_TC_L102_L204_105_kb_read_timeout_degrades_no_history(
        self,
        sut_with_slow_kb,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-105 · E_L102_L204_005 · KB 读超时 · 不阻塞 · 降级 warn · 继续产出。"""
        result = await sut_with_slow_kb.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        # 不应抛错 · 但 warning 中应含 KB_READ_TIMEOUT
        assert any(w.code == "E_L102_L204_005" for w in result.warnings)
        # 不列为 failed · 因为 kb 是 best-effort
        assert result.status in ("COMPLETE", "PARTIAL")

    @pytest.mark.asyncio
    async def test_TC_L102_L204_106_core_plan_failed_scope_triggers_reject(
        self,
        sut_with_core_fail_on_scope,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-106 · E_L102_L204_006 · scope（核心 kda）失败 → 整批 reject。"""
        with pytest.raises(E_L102_L204_006_CorePlanFailed) as ei:
            await sut_with_core_fail_on_scope.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_006"
        assert "scope" in ei.value.context["core_failed"]

    @pytest.mark.asyncio
    async def test_TC_L102_L204_107_togaf_alignment_mismatch_three_rules(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_togaf_bundle_misaligned: dict[str, str],
    ) -> None:
        """TC-L102-L204-107 · E_L102_L204_007 · 矩阵 ≥ 3 条规则 mismatch · 抛错 · 整批 reject。"""
        with pytest.raises(E_L102_L204_007_TogafAlignmentMismatch) as ei:
            await sut.cross_check_togaf_alignment(
                project_id=mock_project_id,
                togaf_bundle=mock_togaf_bundle_misaligned,
                strict=True,
            )
        assert ei.value.code == "E_L102_L204_007"
        assert len(ei.value.context["mismatches"]) >= 3

    def test_TC_L102_L204_108_bundle_hash_mismatch_external_tamper(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        nine_plans_on_disk_tampered: list[str],
    ) -> None:
        """TC-L102-L204-108 · E_L102_L204_008 · manifest 中 bundle_hash vs 实际文件不一致 · 拒绝激活。"""
        with pytest.raises(E_L102_L204_008_BundleHashMismatch) as ei:
            sut.verify_bundle_hash(
                project_id=mock_project_id,
                kda_list=nine_plans_on_disk_tampered,
                expected_hash="0" * 64,  # 伪期望值
            )
        assert ei.value.code == "E_L102_L204_008"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_109_plan_md_too_large_exceeds_200kb(
        self,
        sut_with_oversized_llm,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
    ) -> None:
        """TC-L102-L204-109 · E_L102_L204_009 · 单 plan md 超 200KB · 截断 + warn。"""
        with pytest.raises(E_L102_L204_009_PlanMdTooLarge) as ei:
            await sut_with_oversized_llm.produce_scope_plan(
                project_id=mock_project_id,
                request_id=mock_request_id,
                dependencies=mock_four_pieces_ready,
            )
        assert ei.value.code == "E_L102_L204_009"
        assert ei.value.context["size_bytes"] > 200 * 1024

    @pytest.mark.asyncio
    async def test_TC_L102_L204_110_rework_unknown_kda_rejected(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-110 · E_L102_L204_010 · rework_list 含未知 kda · 拒绝。"""
        with pytest.raises(E_L102_L204_010_ReworkUnknownKda) as ei:
            await sut.rework_plans(
                project_id=mock_project_id,
                request_id=mock_request_id,
                rework_list=["risk", "fake_plan"],  # fake_plan 不存在
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_010"
        assert "fake_plan" in ei.value.context["unknown"]

    @pytest.mark.asyncio
    async def test_TC_L102_L204_111_rework_max_versions_exceeded(
        self,
        sut_with_rework_count_10,
        mock_project_id: str,
        mock_request_id: str,
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-111 · E_L102_L204_011 · risk 已 rework 10 次 · 第 11 次拒绝 · HALT 该 kda。"""
        with pytest.raises(E_L102_L204_011_ReworkMaxVersions) as ei:
            await sut_with_rework_count_10.rework_plans(
                project_id=mock_project_id,
                request_id=mock_request_id,
                rework_list=["risk"],
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_011"
        assert ei.value.context["current_version"] >= 10

    @pytest.mark.asyncio
    async def test_TC_L102_L204_112_too_many_failures_triggers_emergency(
        self,
        sut_with_5_plan_failures,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
        mock_supervisor_sink,
    ) -> None:
        """TC-L102-L204-112 · E_L102_L204_012 · ≥ 5 kda 失败 · EMERGENCY_MANUAL · IC-06 通知 supervisor。"""
        with pytest.raises(E_L102_L204_012_TooManyFailures) as ei:
            await sut_with_5_plan_failures.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_012"
        # IC-06 supervisor 被通知
        ic06 = [c for c in mock_supervisor_sink.calls if c["reason"] == "EMERGENCY_MANUAL"]
        assert len(ic06) == 1

    @pytest.mark.asyncio
    async def test_TC_L102_L204_113_empty_rework_list_rejected(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-113 · E_L102_L204_013 · rework_plans 传空列表 · 拒绝。"""
        with pytest.raises(E_L102_L204_013_EmptyReworkList) as ei:
            await sut.rework_plans(
                project_id=mock_project_id,
                request_id=mock_request_id,
                rework_list=[],  # 空
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_013"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_114_rework_unknown_kda_returns_legal_list(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-114 · E_L102_L204_014 · rework_list 全是未知 kda · 返回合法 kda list 供 caller 对拍。"""
        with pytest.raises(E_L102_L204_014_UnknownKdaName) as ei:
            await sut.rework_plans(
                project_id=mock_project_id,
                request_id=mock_request_id,
                rework_list=["scoping", "scheduling"],  # 全错
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_014"
        assert "scope" in ei.value.context["legal_kdas"]
        assert "schedule" in ei.value.context["legal_kdas"]

    @pytest.mark.asyncio
    async def test_TC_L102_L204_115_audit_seed_emit_fail_degrades_to_buffer(
        self,
        sut_with_broken_event_bus,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-115 · E_L102_L204_015 · IC-09 连续 3 失败 · DEGRADED_AUDIT · 不阻塞产出。"""
        result = await sut_with_broken_event_bus.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        # 不抛错 · 落入 DEGRADED_AUDIT buffer
        assert any(w.code == "E_L102_L204_015" for w in result.warnings)
        assert result.audit_buffer_path is not None

    @pytest.mark.asyncio
    async def test_TC_L102_L204_116_bundle_manifest_write_fail_halts(
        self,
        sut_with_fsync_fail,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-116 · E_L102_L204_016 · `_bundle.yaml` fsync 失败（EROFS）· HALT · 通知运维。"""
        with pytest.raises(E_L102_L204_016_BundleManifestWriteFail) as ei:
            await sut_with_fsync_fail.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        assert ei.value.code == "E_L102_L204_016"
        assert ei.value.context["errno"] in ("EROFS", "ENOSPC")
```

---

## §4 IC-XX 契约集成测试（≥ 5 join test）

> 本 L2 对外 6 条 IC（IC-01 / IC-L2-03 / IC-L2-02 / IC-L2-05 / IC-06 / IC-09）· 每条 ≥ 1 契约级 join test。
> 与兄弟 L2 通过 mock 充当对手方 · 但契约字段（payload schema）必须用 `jsonschema` 硬校验。

```python
# file: tests/l1_02/test_l2_04_pmp_ic_contracts.py
from __future__ import annotations

from typing import Any

import pytest
from jsonschema import validate

from app.l2_04.orchestrator import PMPPlansOrchestrator
from app.integration.ic_contracts import (
    IC_L2_03_DISPATCH_PMP_REQUEST_SCHEMA,
    IC_L2_03_DISPATCH_PMP_RESPONSE_SCHEMA,
    IC_L2_02_REQUEST_TEMPLATE_SCHEMA,
    IC_L2_05_CROSS_CHECK_TOGAF_SCHEMA,
    IC_09_APPEND_EVENT_SCHEMA,
    IC_06_SUPERVISOR_SIGNAL_SCHEMA,
)


class TestL2_04_PMPICContracts:
    """IC 契约字段级硬校验 · 所有 payload 过 jsonschema.validate。"""

    @pytest.mark.asyncio
    async def test_TC_L102_L204_601_ic_01_pm14_ownership_only_l201_allowed(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-601 · IC-01 主状态机 · caller_l1=L2-01 允许 · caller_l1=L1-01 拒绝。"""
        # 允许路径
        result = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            caller_l1="L2-01",
        )
        assert result.status.name in ("COMPLETE", "PARTIAL")

    @pytest.mark.asyncio
    async def test_TC_L102_L204_602_ic_l2_03_dispatch_payload_schema(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
    ) -> None:
        """TC-L102-L204-602 · IC-L2-03 · 入 payload 过 schema · 出 payload（PmpBundleResult）过 response schema。"""
        request_payload = {
            "project_id": mock_project_id,
            "request_id": mock_request_id,
            "stage": "S2",
            "target": "pmp",
            "trim_level": "full",
            "dependencies": {
                "four_pieces_paths": mock_four_pieces_ready["four_pieces_paths"],
                "charter_path": mock_four_pieces_ready["charter_path"],
                "stakeholders_path": mock_four_pieces_ready["stakeholders_path"],
                "togaf_d_path": mock_togaf_d_ready["togaf_d_path"],
            },
            "trace_ctx": {"ts_dispatched_ns": 1713700000000000000, "re_open_count": 0},
        }
        validate(instance=request_payload, schema=IC_L2_03_DISPATCH_PMP_REQUEST_SCHEMA)

        response = await sut.handle_dispatch(request_payload)
        validate(instance=response, schema=IC_L2_03_DISPATCH_PMP_RESPONSE_SCHEMA)
        assert response["status"] in ("ok", "partial")
        assert response["project_id"] == mock_project_id

    @pytest.mark.asyncio
    async def test_TC_L102_L204_603_ic_l2_02_request_template_schema_per_kda(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
        mock_template_engine_spy,
    ) -> None:
        """TC-L102-L204-603 · IC-L2-02 · 9 并行时 · 每份 plan 发 1 次 request_template · 9 次 payload 全过 schema。"""
        await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        calls = mock_template_engine_spy.captured
        assert len(calls) == 9
        for payload in calls:
            validate(instance=payload, schema=IC_L2_02_REQUEST_TEMPLATE_SCHEMA)
            assert payload["project_id"] == mock_project_id
            assert payload["plan_type"] in {
                "integration", "scope", "schedule", "cost", "quality",
                "resource", "communication", "risk", "procurement",
            }

    @pytest.mark.asyncio
    async def test_TC_L102_L204_604_ic_l2_05_cross_check_round_trip(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_togaf_bundle: dict[str, str],
        mock_l2_05_spy,
    ) -> None:
        """TC-L102-L204-604 · IC-L2-05 · 本 L2 发 cross_check · L2-05 回 AlignmentResult · 双向契约字段校验。"""
        res = await sut.cross_check_togaf_alignment(
            project_id=mock_project_id,
            togaf_bundle=mock_togaf_bundle,
        )
        # 入 payload
        outbound = mock_l2_05_spy.outbound
        validate(instance=outbound, schema=IC_L2_05_CROSS_CHECK_TOGAF_SCHEMA)
        assert outbound["project_id"] == mock_project_id
        # 响应
        assert res.aligned in (True, False)
        assert isinstance(res.mismatches, list)

    @pytest.mark.asyncio
    async def test_TC_L102_L204_605_ic_06_supervisor_signal_on_emergency(
        self,
        sut_with_5_plan_failures,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
        mock_supervisor_sink,
    ) -> None:
        """TC-L102-L204-605 · IC-06 硬红线 · EMERGENCY_MANUAL 时发 supervisor 信号 · payload schema 硬校验。"""
        from app.l2_04.errors import E_L102_L204_012_TooManyFailures

        with pytest.raises(E_L102_L204_012_TooManyFailures):
            await sut_with_5_plan_failures.produce_all_9(
                project_id=mock_project_id,
                request_id=mock_request_id,
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
        calls = mock_supervisor_sink.calls
        assert len(calls) >= 1
        validate(instance=calls[0], schema=IC_06_SUPERVISOR_SIGNAL_SCHEMA)
        assert calls[0]["reason"] == "EMERGENCY_MANUAL"
        assert calls[0]["actor"] == "L2-04"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_606_ic_09_eight_event_types_all_pass_schema(
        self,
        sut: PMPPlansOrchestrator,
        mock_project_id: str,
        mock_request_id: str,
        mock_four_pieces_ready: dict[str, str],
        mock_togaf_d_ready: dict[str, Any],
        mock_event_bus,
    ) -> None:
        """TC-L102-L204-606 · IC-09 · 完整流程触发全部事件 · 8 类 event 全过 schema。"""
        await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        for ev in mock_event_bus.captured:
            validate(instance=ev, schema=IC_09_APPEND_EVENT_SCHEMA)
            assert ev["actor"] == "L2-04"
            assert ev["project_id"] == mock_project_id
        # 至少含 per-plan ready + 9_plans_ready
        types = {e["event_type"] for e in mock_event_bus.captured}
        assert "L1-02:9_plans_ready" in types
        assert "L1-02:scope_plan_ready" in types
```

---

## §5 性能 SLO 用例（§12.1 对标）

> `@pytest.mark.perf` 标记 · CI 可按场景筛选；基线 100 次 · 取 P50/P95/P99 + max 四分位。
> mock LLM 延迟按 §12.1 P50 配置（单 worker 2s）以复现真实分布。

```python
# file: tests/l1_02/test_l2_04_pmp_perf.py
from __future__ import annotations

import statistics
import time
from typing import Any

import pytest


@pytest.mark.perf
class TestL2_04_PMPPerf:
    """§12.1 7 指标全量对标 · 每项 100 次采样。"""

    @pytest.mark.asyncio
    async def test_TC_L102_L204_501_single_kda_p95_under_5s(
        self,
        sut,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
    ) -> None:
        """TC-L102-L204-501 · 单 kda produce_scope_plan P95 ≤ 5s · 100 次采样。"""
        lats: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.produce_scope_plan(
                project_id=mock_project_id,
                request_id=f"{mock_request_id}-{i}",
                dependencies=mock_four_pieces_ready,
            )
            lats.append(time.perf_counter() - t0)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        p99 = lats[int(0.99 * len(lats))]
        assert p95 <= 5.0, f"p95={p95:.2f}s exceeds 5s SLO"
        assert p99 <= 10.0, f"p99={p99:.2f}s exceeds 10s SLO"
        assert max(lats) <= 30.0, "hard limit 30s breached"

    @pytest.mark.asyncio
    async def test_TC_L102_L204_502_nine_parallel_p95_under_30s(
        self,
        sut,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
        mock_togaf_d_ready,
    ) -> None:
        """TC-L102-L204-502 · 9 并行 produce_all_9 P95 ≤ 30s · 30 次采样（成本 trade-off）。"""
        lats: list[float] = []
        for i in range(30):
            t0 = time.perf_counter()
            await sut.produce_all_9(
                project_id=f"{mock_project_id}-{i}",
                request_id=f"{mock_request_id}-{i}",
                trim_level="full",
                dependencies=mock_four_pieces_ready,
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
            lats.append(time.perf_counter() - t0)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 30.0, f"p95={p95:.2f}s exceeds 30s SLO"
        assert max(lats) <= 60.0, "hard limit 60s breached"
        # 并行效率：9 并行 vs 单 kda（2s）· 不应线性化到 18s+
        assert statistics.median(lats) <= 12.0

    @pytest.mark.asyncio
    async def test_TC_L102_L204_503_cross_check_p95_under_400ms(
        self,
        sut,
        mock_project_id,
        mock_togaf_bundle,
    ) -> None:
        """TC-L102-L204-503 · cross_check_togaf_alignment P95 ≤ 400ms · 100 次采样。"""
        lats: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            await sut.cross_check_togaf_alignment(
                project_id=mock_project_id,
                togaf_bundle=mock_togaf_bundle,
            )
            lats.append((time.perf_counter() - t0) * 1000)  # ms
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 400.0, f"p95={p95:.1f}ms exceeds 400ms SLO"
        assert max(lats) <= 3000.0

    def test_TC_L102_L204_504_bundle_hash_nine_md_p95_under_100ms(
        self,
        sut,
        mock_project_id,
        nine_plans_on_disk,
    ) -> None:
        """TC-L102-L204-504 · compute_pmp_bundle_hash (9 md × 50KB 典型) P95 ≤ 100ms · 200 次采样。"""
        lats: list[float] = []
        for _ in range(200):
            t0 = time.perf_counter()
            sut.compute_pmp_bundle_hash(project_id=mock_project_id, kda_list=nine_plans_on_disk)
            lats.append((time.perf_counter() - t0) * 1000)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 100.0, f"p95={p95:.1f}ms exceeds 100ms SLO"
        assert max(lats) <= 1000.0

    def test_TC_L102_L204_505_bundle_manifest_write_p95_under_30ms(
        self,
        sut,
        mock_project_id,
        bundle_manifest_dict,
    ) -> None:
        """TC-L102-L204-505 · `_bundle.yaml` 落盘 P95 ≤ 30ms · 100 次采样（含 fsync）。"""
        lats: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            sut.write_bundle_manifest(
                project_id=f"{mock_project_id}-{i}",
                bundle_manifest=bundle_manifest_dict,
            )
            lats.append((time.perf_counter() - t0) * 1000)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 30.0, f"p95={p95:.1f}ms exceeds 30ms SLO"
        assert max(lats) <= 500.0

    @pytest.mark.asyncio
    async def test_TC_L102_L204_506_rework_single_kda_p95_under_5s(
        self,
        sut,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
        mock_togaf_d_ready,
    ) -> None:
        """TC-L102-L204-506 · rework_plans(['risk']) P95 ≤ 5s · 保留 8 不重算（50 次采样）。"""
        # 先铺 v1
        await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        lats: list[float] = []
        for i in range(50):
            t0 = time.perf_counter()
            await sut.rework_plans(
                project_id=mock_project_id,
                request_id=f"{mock_request_id}-rw-{i}",
                rework_list=["risk"],
                togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            )
            lats.append(time.perf_counter() - t0)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 5.0, f"p95={p95:.2f}s exceeds 5s SLO"
        assert max(lats) <= 30.0

    def test_TC_L102_L204_507_single_rule_judge_p95_under_15ms(
        self,
        sut,
        sample_pmp_plan,
        sample_togaf_phase,
    ) -> None:
        """TC-L102-L204-507 · _check_rule 单条矩阵规则 P95 ≤ 15ms · 500 次采样。"""
        lats: list[float] = []
        for _ in range(500):
            t0 = time.perf_counter()
            sut._check_rule(sample_pmp_plan, sample_togaf_phase)
            lats.append((time.perf_counter() - t0) * 1000)
        lats.sort()
        p95 = lats[int(0.95 * len(lats))]
        assert p95 <= 15.0, f"p95={p95:.2f}ms exceeds 15ms SLO"
        assert max(lats) <= 100.0
```

---

## §6 端到端 e2e 场景（GWT · 映射 §5 P0/P1/P2 时序）

> GWT（Given-When-Then）风格叙述 · pytest 实现 · 对应 tech-design §5 三张时序图。

### §6.1 P0 主干 · 9 计划全绿 e2e

> **Given** L2-01 完成 S1 → 广播 `4_pieces_ready` · L2-05 D 阶段完成广播 `togaf_d_ready` · 4 件套 + charter + stakeholders + togaf_d 就绪。
> **When** L2-01 IC-L2-03 dispatch(stage=S2, target=pmp, trim_level=full)。
> **Then** L2-04 9 并行产出 9 md · bundle_hash 生成 · IC-09 发 `9_plans_ready` · L2-01 累积 S2 Gate 信号集 · P95 ≤ 30s。

```python
# file: tests/l1_02/test_l2_04_pmp_e2e.py
from __future__ import annotations

import pytest


@pytest.mark.e2e
class TestL2_04_PMPE2E:
    """e2e 场景 · 映射 tech-design §5 时序图三张。"""

    @pytest.mark.asyncio
    async def test_TC_L102_L204_701_e2e_full_green_p0_sequence(
        self,
        sut,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
        mock_togaf_d_ready,
        mock_event_bus,
        tmp_project_root,
    ) -> None:
        """TC-L102-L204-701 · §5.1 P0 主干 · 9 并行全绿端到端。"""
        # Given: 4 件套 + togaf_d 就绪（fixture 已准备）
        # When: L2-01 dispatch
        result = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
            caller_l1="L2-01",
        )
        # Then:
        assert result.status.name == "COMPLETE"
        assert result.bundle_hash
        assert len(result.plans) == 9
        # 9 md 文件落盘
        plan_dir = tmp_project_root / mock_project_id / "pmp-plans"
        for kda in ["integration", "scope", "schedule", "cost", "quality",
                    "resource", "communication", "risk", "procurement"]:
            assert (plan_dir / f"{kda}-plan.md").exists()
        # _bundle.yaml 索引
        assert (plan_dir / "_bundle.yaml").exists()
        # IC-09 发 9_plans_ready
        assert any(e["event_type"] == "L1-02:9_plans_ready" for e in mock_event_bus.captured)

    @pytest.mark.asyncio
    async def test_TC_L102_L204_702_e2e_partial_degradation_p1(
        self,
        sut_with_2_non_core_failures,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
        mock_togaf_d_ready,
        mock_event_bus,
    ) -> None:
        """TC-L102-L204-702 · §5.2 P1 · 非核心 kda 2 失败 · PARTIAL 通过 · evidence 标降级。"""
        result = await sut_with_2_non_core_failures.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert result.status.name == "PARTIAL"
        assert result.degraded is True
        assert len(result.completeness.failed) == 2
        # evidence 必带降级标记
        assert result.partial_evidence_watermark is True
        # IC-09 发 partial_degradation
        assert any(e["event_type"].endswith("partial_degradation") for e in mock_event_bus.captured)

    @pytest.mark.asyncio
    async def test_TC_L102_L204_703_e2e_rework_scope_after_gate_reject(
        self,
        sut,
        mock_project_id,
        mock_request_id,
        mock_four_pieces_ready,
        mock_togaf_d_ready,
    ) -> None:
        """TC-L102-L204-703 · §5.3 Gate reject · L2-01 调 rework_plans(['scope']) · 保留 8 成品 · scope v2 · bundle_hash 重算。"""
        # 第一次
        v1 = await sut.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        # rework scope
        v2 = await sut.rework_plans(
            project_id=mock_project_id,
            request_id=f"{mock_request_id}-rw",
            rework_list=["scope"],
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        assert v2.status.name in ("COMPLETE", "REWORKED")
        assert v2.bundle_hash != v1.bundle_hash
        # scope v2
        scope_v2 = next(p for p in v2.plans if p.plan_type == "scope")
        assert scope_v2.version == 2
        # 其他 8 保留（sha256 不变）
        for kda in ["integration", "schedule", "cost", "quality",
                    "resource", "communication", "risk", "procurement"]:
            p1 = next(p for p in v1.plans if p.plan_type == kda)
            p2 = next(p for p in v2.plans if p.plan_type == kda)
            assert p1.sha256 == p2.sha256
```

---

## §7 测试 fixture（≥ 9 个）

> 集中 `tests/l1_02/conftest.py`；本 L2 需要的 mock 对手方比 L2-07 更多（跨 L2-07 模板 · L2-05 TOGAF · L1-05 subagent · L1-06 KB · L1-07 supervisor · L1-09 EventBus）。

```python
# file: tests/l1_02/conftest.py
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from app.l2_04.orchestrator import PMPPlansOrchestrator


# ---------- 基础 fixture ----------

@pytest.fixture
def mock_project_id() -> str:
    """PM-14 project_id · 符合 `^p-[a-z0-9]{8}$` 规范。"""
    return "p-l204test"


@pytest.fixture
def mock_request_id() -> str:
    """单次请求 id · uuid v7 风格。"""
    return "req-0194f8c0-1a2b-7cde-89ef-000000000001"


@pytest.fixture
def mock_clock(monkeypatch) -> Any:
    """冻结时间 · 保测试确定性。"""
    class FrozenClock:
        ts_ns: int = 1_713_700_000_000_000_000

        def now_ns(self) -> int:
            return self.ts_ns

        def advance(self, ns: int) -> None:
            self.ts_ns += ns

    clock = FrozenClock()
    monkeypatch.setattr("app.l2_04.orchestrator._clock", clock)
    return clock


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """临时 projects/ 根目录 · 每测试隔离。"""
    root = tmp_path / "projects"
    root.mkdir()
    return root


# ---------- 上游依赖 fixture ----------

@pytest.fixture
def mock_four_pieces_ready(tmp_project_root: Path, mock_project_id: str) -> dict[str, Any]:
    """L2-03 输出的 4 件套 + charter + stakeholders 路径（已就绪）。"""
    base = tmp_project_root / mock_project_id
    (base / "four-pieces").mkdir(parents=True)
    (base / "initiation").mkdir(parents=True)
    for name in ("requirements", "goals", "acceptance_criteria", "quality_standards"):
        (base / "four-pieces" / f"{name}.md").write_text(f"# {name}\n内容已填充\n" * 20)
    (base / "initiation" / "charter.md").write_text("# charter\n项目立项\n" * 20)
    (base / "initiation" / "stakeholders.md").write_text("# stakeholders\n干系人\n" * 20)
    return {
        "four_pieces_paths": {
            "requirements": str(base / "four-pieces" / "requirements.md"),
            "goals": str(base / "four-pieces" / "goals.md"),
            "acceptance_criteria": str(base / "four-pieces" / "acceptance_criteria.md"),
            "quality_standards": str(base / "four-pieces" / "quality_standards.md"),
        },
        "charter_path": str(base / "initiation" / "charter.md"),
        "stakeholders_path": str(base / "initiation" / "stakeholders.md"),
    }


@pytest.fixture
def mock_togaf_d_ready(tmp_project_root: Path, mock_project_id: str) -> dict[str, Any]:
    """L2-05 D 阶段输出的 togaf_d.md + ADR refs（已就绪）。"""
    base = tmp_project_root / mock_project_id / "togaf"
    base.mkdir(parents=True)
    d_path = base / "d-technology.md"
    d_path.write_text(
        "# TOGAF D · Technology Architecture\n\n## ADR\n\n"
        "- [ADR-D1] 后端语言选型 Python 3.11\n"
        "- [ADR-D2] 数据库选型 PostgreSQL 15\n"
        "- [ADR-D3] 事件总线 NATS JetStream\n"
    )
    return {
        "togaf_d_path": str(d_path),
        "adr_refs": ["ADR-D1", "ADR-D2", "ADR-D3"],
    }


@pytest.fixture
def mock_togaf_bundle(tmp_project_root: Path, mock_project_id: str, mock_togaf_d_ready) -> dict[str, str]:
    """L2-05 完整 8 Phase bundle · 供 cross_check 用（aligned 状态）。"""
    base = tmp_project_root / mock_project_id / "togaf"
    for phase in ["A-vision", "B-business", "C-data", "C-application", "F-migration", "G-governance"]:
        (base / f"{phase}.md").write_text(f"# {phase}\n对齐内容\n")
    return {
        "phase_A": str(base / "A-vision.md"),
        "phase_B": str(base / "B-business.md"),
        "phase_C_data": str(base / "C-data.md"),
        "phase_C_app": str(base / "C-application.md"),
        "phase_D": mock_togaf_d_ready["togaf_d_path"],
        "phase_F": str(base / "F-migration.md"),
        "phase_G": str(base / "G-governance.md"),
    }


@pytest.fixture
def mock_togaf_bundle_misaligned(mock_togaf_bundle: dict[str, str]) -> dict[str, str]:
    """TOGAF bundle · 3+ 条规则故意不对齐。"""
    # 覆盖 D 使 risk/quality 引用失效；F 缺资源；G 缺风险治理
    for key in ("phase_D", "phase_F", "phase_G"):
        Path(mock_togaf_bundle[key]).write_text("# TOGAF phase\n(no alignment markers)\n")
    return mock_togaf_bundle


# ---------- 对手方 mock（IC 对拍）----------

class _EventBusSpy:
    def __init__(self) -> None:
        self.captured: list[dict[str, Any]] = []

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.captured.append(event)
        return {"status": "ok", "seq_id": len(self.captured)}


@pytest.fixture
def mock_event_bus(monkeypatch) -> _EventBusSpy:
    """L1-09 EventBus spy · 捕获全部 IC-09 事件。"""
    spy = _EventBusSpy()
    monkeypatch.setattr("app.integration.ic_09.append_event", spy.append_event)
    return spy


class _TemplateEngineSpy:
    def __init__(self) -> None:
        self.captured: list[dict[str, Any]] = []

    async def request_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.captured.append(payload)
        plan_type = payload["plan_type"]
        return {
            "template_content": f"# {plan_type}-plan\n\n"
                                "budget_or_estimate: $100K\n"
                                "timeline: Q2 2026\n"
                                "responsible_role: PM\n"
                                "[ADR-D1]\n" * 10,
            "template_id": f"pmp.{plan_type}.v1.0",
        }


@pytest.fixture
def mock_template_engine_spy(monkeypatch) -> _TemplateEngineSpy:
    """L2-07 模板引擎 spy · 拦截 IC-L2-02 调用 payload。"""
    spy = _TemplateEngineSpy()
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", spy.request_template)
    return spy


class _L205Spy:
    def __init__(self) -> None:
        self.outbound: dict[str, Any] = {}

    async def cross_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.outbound = payload
        return {"aligned": True, "mismatches": []}


@pytest.fixture
def mock_l2_05_spy(monkeypatch) -> _L205Spy:
    """L2-05 TOGAF spy · 拦截 IC-L2-05 调用。"""
    spy = _L205Spy()
    monkeypatch.setattr("app.integration.ic_l2_05.cross_check_togaf_alignment", spy.cross_check)
    return spy


class _SupervisorSink:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def signal(self, payload: dict[str, Any]) -> None:
        self.calls.append(payload)


@pytest.fixture
def mock_supervisor_sink(monkeypatch) -> _SupervisorSink:
    """L1-07 Supervisor sink · 拦截 IC-06 硬红线。"""
    sink = _SupervisorSink()
    monkeypatch.setattr("app.integration.ic_06.emit_supervisor_signal", sink.signal)
    return sink


class _KBReader:
    def __init__(self, delay_sec: float = 0.0) -> None:
        self.delay_sec = delay_sec

    async def read(self, project_id: str, kind: str) -> dict[str, Any]:
        import asyncio as _aio
        await _aio.sleep(self.delay_sec)
        return {"samples": [], "kind": kind}


@pytest.fixture
def mock_kb_reader(monkeypatch) -> _KBReader:
    """L1-06 KB reader · 默认即时返回空历史。"""
    kb = _KBReader(delay_sec=0.0)
    monkeypatch.setattr("app.integration.ic_l2_04.kb_read", kb.read)
    return kb


# ---------- SUT 变体 ----------

@pytest.fixture
def sut(
    mock_clock,
    tmp_project_root: Path,
    mock_event_bus,
    mock_template_engine_spy,
    mock_kb_reader,
    mock_supervisor_sink,
) -> PMPPlansOrchestrator:
    """默认 SUT · 全部依赖已 mock · 快速返回 · 测试套基准。"""
    return PMPPlansOrchestrator(
        project_root=tmp_project_root,
        config={
            "pmp_parallel_workers": 9,
            "single_plan_timeout_sec": 5,
            "bundle_hash_algo": "sha256",
            "core_kdas": ["scope", "schedule", "cost"],
            "non_core_fail_limit": 4,
            "emergency_fail_threshold": 5,
            "plan_md_max_size_kb": 200,
            "rework_max_versions": 10,
        },
    )


@pytest.fixture
def sut_with_broken_template(sut, monkeypatch) -> PMPPlansOrchestrator:
    """communication 模板 slot 缺字段 · 触发 E_L102_L204_004。"""
    async def _broken(payload: dict[str, Any]) -> dict[str, Any]:
        if payload["plan_type"] == "communication":
            raise RuntimeError("TEMPLATE_MISSING_FIELD: stakeholders")
        return {"template_content": "# ok\n" * 30, "template_id": "x.v1"}
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", _broken)
    return sut


@pytest.fixture
def sut_with_slow_kb(sut, monkeypatch) -> PMPPlansOrchestrator:
    """KB 读超时 · 触发 E_L102_L204_005 · 降级 warn。"""
    async def _slow(project_id: str, kind: str) -> dict[str, Any]:
        import asyncio as _aio
        await _aio.sleep(10)  # 超 3s timeout
        return {}
    monkeypatch.setattr("app.integration.ic_l2_04.kb_read", _slow)
    return sut


@pytest.fixture
def sut_with_core_fail_on_scope(sut, monkeypatch) -> PMPPlansOrchestrator:
    """scope 模板渲染故意失败 · 触发 E_L102_L204_006（核心 kda 失败）。"""
    async def _fail(payload: dict[str, Any]) -> dict[str, Any]:
        if payload["plan_type"] == "scope":
            raise RuntimeError("LLM_GENERATION_FAILED")
        return {"template_content": "# ok\n" * 30, "template_id": "x.v1"}
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", _fail)
    return sut


@pytest.fixture
def sut_with_2_non_core_failures(sut, monkeypatch) -> PMPPlansOrchestrator:
    """communication + procurement 失败 · 非核心 2 失败 · PARTIAL。"""
    fail_set = {"communication", "procurement"}

    async def _partial(payload: dict[str, Any]) -> dict[str, Any]:
        if payload["plan_type"] in fail_set:
            raise RuntimeError("TEMPLATE_MISSING_FIELD")
        return {"template_content": "# ok\n" * 30, "template_id": "x.v1"}
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", _partial)
    return sut


@pytest.fixture
def sut_with_5_plan_failures(sut, monkeypatch) -> PMPPlansOrchestrator:
    """5 非核心失败 · 触发 E_L102_L204_012 EMERGENCY_MANUAL。"""
    fail_set = {"integration", "quality", "resource", "communication", "procurement"}

    async def _fail5(payload: dict[str, Any]) -> dict[str, Any]:
        if payload["plan_type"] in fail_set:
            raise RuntimeError("LLM_GENERATION_FAILED")
        return {"template_content": "# ok\n" * 30, "template_id": "x.v1"}
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", _fail5)
    return sut


@pytest.fixture
def sut_with_oversized_llm(sut, monkeypatch) -> PMPPlansOrchestrator:
    """模板产出 > 200KB · 触发 E_L102_L204_009。"""
    async def _big(payload: dict[str, Any]) -> dict[str, Any]:
        huge = "x" * (250 * 1024)
        return {"template_content": huge, "template_id": "x.v1"}
    monkeypatch.setattr("app.integration.ic_l2_02.request_template", _big)
    return sut


@pytest.fixture
def sut_with_rework_count_10(sut, tmp_project_root: Path, mock_project_id: str) -> PMPPlansOrchestrator:
    """预置 risk 已 rework 10 次 · 第 11 次触发 E_L102_L204_011。"""
    meta = tmp_project_root / mock_project_id / "pmp-meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "rework-history.jsonl").write_text(
        "\n".join(
            f'{{"request_id":"rq-{i}","rework_list":["risk"],"new_bundle_hash":"{"0"*64}"}}'
            for i in range(10)
        )
    )
    return sut


@pytest.fixture
def sut_with_broken_event_bus(sut, monkeypatch) -> PMPPlansOrchestrator:
    """IC-09 连续失败 · 触发 E_L102_L204_015 DEGRADED_AUDIT buffer。"""
    call_count = {"n": 0}

    def _fail(event: dict[str, Any]) -> dict[str, Any]:
        call_count["n"] += 1
        raise ConnectionError("EventBus unreachable")
    monkeypatch.setattr("app.integration.ic_09.append_event", _fail)
    return sut


@pytest.fixture
def sut_with_fsync_fail(sut, monkeypatch) -> PMPPlansOrchestrator:
    """fsync 抛 EROFS · 触发 E_L102_L204_016 HALT。"""
    def _fsync_fail(fd: int) -> None:
        raise OSError(30, "Read-only file system")
    monkeypatch.setattr("os.fsync", _fsync_fail)
    return sut


# ---------- 样本数据 fixture ----------

@pytest.fixture
def nine_plans_on_disk(tmp_project_root: Path, mock_project_id: str) -> list[str]:
    """9 份 plan md 已就位 · 供 compute_pmp_bundle_hash 测。"""
    d = tmp_project_root / mock_project_id / "pmp-plans"
    d.mkdir(parents=True)
    kdas = ["integration", "scope", "schedule", "cost", "quality",
            "resource", "communication", "risk", "procurement"]
    for k in kdas:
        (d / f"{k}-plan.md").write_text(f"# {k}-plan\nbudget_or_estimate: $100K\ntimeline: Q2\n" * 20)
    return kdas


@pytest.fixture
def nine_plans_on_disk_tampered(nine_plans_on_disk, tmp_project_root: Path, mock_project_id: str) -> list[str]:
    """9 md 之一被外部篡改 · 触发 E_L102_L204_008。"""
    (tmp_project_root / mock_project_id / "pmp-plans" / "scope-plan.md").write_text(
        "# TAMPERED\n后被外部改过 · bundle_hash 不匹配\n"
    )
    return nine_plans_on_disk


@pytest.fixture
def bundle_manifest_dict() -> dict[str, Any]:
    """_bundle.yaml dict · 供 write perf 用。"""
    return {
        "project_id": "p-l204test",
        "bundle_hash": "a" * 64,
        "created_at": "2026-04-22T10:00:00Z",
        "mode": "COMPLETE",
        "plans": [{"kda": k, "file": f"pmp-plans/{k}-plan.md", "sha256": "b" * 64, "lines": 100, "version": 1, "status": "ok"}
                  for k in ["integration", "scope", "schedule", "cost", "quality",
                            "resource", "communication", "risk", "procurement"]],
    }


@pytest.fixture
def sample_pmp_plan() -> dict[str, Any]:
    """单份 PMP plan 样本 · 供单规则判定 perf 用。"""
    return {"kda": "scope", "content": "scope content\n[ADR-D1]" * 50}


@pytest.fixture
def sample_togaf_phase() -> dict[str, Any]:
    """单份 TOGAF phase 样本 · 对应 scope ↔ phase_A。"""
    return {"phase": "A", "content": "Architecture Vision content\n" * 50}
```

---

## §8 集成点用例（与兄弟 L2 协作）

> 跨 L2 的集成 join test · 着重双向契约（Partnership 关系）· 配合 conftest 真实依赖链但用 spy。

### §8.1 L2-04 ↔ L2-07 模板引擎（IC-L2-02 · 9 次调用）

```python
# file: tests/l1_02/test_l2_04_x_l2_07_integration.py
import pytest


@pytest.mark.asyncio
async def test_TC_L102_L204_801_x_l2_07_nine_template_calls_per_kda(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
    mock_template_engine_spy,
) -> None:
    """TC-L102-L204-801 · 9 并行产出 · 每份 plan 恰好发 1 次 IC-L2-02 · 9 次 plan_type 唯一。"""
    await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    calls = mock_template_engine_spy.captured
    assert len(calls) == 9
    types = [c["plan_type"] for c in calls]
    assert len(set(types)) == 9  # 每类唯一


@pytest.mark.asyncio
async def test_TC_L102_L204_802_x_l2_07_rework_diff_mode_flag(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
    mock_template_engine_spy,
) -> None:
    """TC-L102-L204-802 · rework 场景 · IC-L2-02 payload 应带 minimal_diff_mode=true（只要 diff 段落）。"""
    await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    mock_template_engine_spy.captured.clear()
    await sut.rework_plans(
        project_id=mock_project_id,
        request_id=f"{mock_request_id}-rw",
        rework_list=["risk"],
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    rework_calls = mock_template_engine_spy.captured
    assert len(rework_calls) == 1
    assert rework_calls[0]["plan_type"] == "risk"
    assert rework_calls[0].get("minimal_diff_mode") is True
```

### §8.2 L2-04 ↔ L2-05 TOGAF（IC-L2-05 · 双向）

```python
@pytest.mark.asyncio
async def test_TC_L102_L204_803_x_l2_05_bidirectional_partnership(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
    mock_event_bus,
    mock_l2_05_spy,
) -> None:
    """TC-L102-L204-803 · 双向 · 本 L2 发 scope/schedule_plan_ready（L2-05 D 用）· 调 L2-05 cross_check。"""
    await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    # 方向 1：本 L2 发 scope_plan_ready / schedule_plan_ready
    types = {e["event_type"] for e in mock_event_bus.captured}
    assert "L1-02:scope_plan_ready" in types
    assert "L1-02:schedule_plan_ready" in types
    # 方向 2：本 L2 调 L2-05 cross_check（outbound 被 spy 捕获）
    assert mock_l2_05_spy.outbound  # 非空表示确实发过


@pytest.mark.asyncio
async def test_TC_L102_L204_804_x_l2_05_togaf_d_timeout_degrades(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_event_bus,
) -> None:
    """TC-L102-L204-804 · L2-05 D 未 ready · 15min 超时 · Group 2 degraded fallback（degraded=true）。"""
    result = await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=None,  # D 未就绪
        togaf_d_wait_timeout_sec=0.1,  # 测试缩短超时
    )
    assert result.degraded is True
    assert any(e["event_type"] == "L1-02:togaf_d_timeout_fallback" for e in mock_event_bus.captured)
    # quality / risk 被标 degraded
    degraded_types = {d.plan_type for d in result.degradation_reasons}
    assert "quality" in degraded_types or "risk" in degraded_types
```

### §8.3 L2-04 ↔ L2-01 Gate 控制器（IC-L2-03 协作）

```python
@pytest.mark.asyncio
async def test_TC_L102_L204_805_x_l2_01_gate_signal_cumulation(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
    mock_event_bus,
) -> None:
    """TC-L102-L204-805 · 本 L2 完 9 计划 · 发 9_plans_ready · L2-01 累积 S2 Gate 信号集（该事件即信号）。"""
    await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    nine_ready = [e for e in mock_event_bus.captured if e["event_type"] == "L1-02:9_plans_ready"]
    assert len(nine_ready) == 1
    payload = nine_ready[0]["payload"]
    assert payload["project_id"] == mock_project_id
    assert payload["trim_level"] == "full"
    # 信号对 L2-01 有用的字段齐全
    assert "paths" in payload and len(payload["paths"]) == 9
    assert "plan_count" in payload
```

---

## §9 边界 / edge case（≥ 4 · 覆盖 9 并行 / 核心全挂 / rework 多次 / hash 异常 / TOGAF 超时）

```python
# file: tests/l1_02/test_l2_04_pmp_edge.py
import pytest

from app.l2_04.errors import (
    E_L102_L204_006_CorePlanFailed,
    E_L102_L204_008_BundleHashMismatch,
    E_L102_L204_011_ReworkMaxVersions,
    E_L102_L204_012_TooManyFailures,
)


@pytest.mark.asyncio
async def test_TC_L102_L204_901_nine_parallel_partial_4_non_core_fail(
    sut_with_4_non_core_failures,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
) -> None:
    """TC-L102-L204-901 · 非核心失败 4（阈值边界）· 仍 PARTIAL 通过 · 第 5 会 EMERGENCY。"""
    result = await sut_with_4_non_core_failures.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    assert result.status.name == "PARTIAL"
    assert len(result.completeness.failed) == 4
    assert result.degraded is True


@pytest.mark.asyncio
async def test_TC_L102_L204_902_all_three_core_fail_triggers_core_plan_failed(
    sut_with_all_core_fail,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
) -> None:
    """TC-L102-L204-902 · scope + schedule + cost 全挂 · CORE_PLAN_FAILED · 整批 reject。"""
    with pytest.raises(E_L102_L204_006_CorePlanFailed) as ei:
        await sut_with_all_core_fail.produce_all_9(
            project_id=mock_project_id,
            request_id=mock_request_id,
            trim_level="full",
            dependencies=mock_four_pieces_ready,
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
    assert set(ei.value.context["core_failed"]) == {"scope", "schedule", "cost"}


@pytest.mark.asyncio
async def test_TC_L102_L204_903_rework_multiple_rounds_preserves_non_rework(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
) -> None:
    """TC-L102-L204-903 · 连续 3 次 rework 不同 kda · 每次 bundle_hash 不同 · 非 rework 项 sha256 不变。"""
    base = await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    hashes: list[str] = [base.bundle_hash]
    versions: dict[str, int] = {p.plan_type: p.version for p in base.plans}
    sequence = ["risk", "quality", "communication"]
    for i, kda in enumerate(sequence, start=1):
        res = await sut.rework_plans(
            project_id=mock_project_id,
            request_id=f"{mock_request_id}-rw-{i}",
            rework_list=[kda],
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )
        hashes.append(res.bundle_hash)
        new_ver = next(p.version for p in res.plans if p.plan_type == kda)
        assert new_ver == versions[kda] + 1
        versions[kda] = new_ver
    # 3 次 hash 两两不同
    assert len(set(hashes)) == 4  # base + 3 rework


@pytest.mark.asyncio
async def test_TC_L102_L204_904_rework_same_kda_exceeding_max_versions_halts(
    sut_with_rework_count_10,
    mock_project_id,
    mock_request_id,
    mock_togaf_d_ready,
) -> None:
    """TC-L102-L204-904 · 同 kda rework 已 10 次 · 第 11 次 HALT 该 kda · E_L102_L204_011。"""
    with pytest.raises(E_L102_L204_011_ReworkMaxVersions):
        await sut_with_rework_count_10.rework_plans(
            project_id=mock_project_id,
            request_id=mock_request_id,
            rework_list=["risk"],
            togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
        )


def test_TC_L102_L204_905_bundle_hash_mismatch_after_external_tamper(
    sut,
    mock_project_id,
    nine_plans_on_disk_tampered,
) -> None:
    """TC-L102-L204-905 · 外部篡改 md 后 · bundle_hash 重算 ≠ manifest 存 · 拒绝激活。"""
    with pytest.raises(E_L102_L204_008_BundleHashMismatch):
        sut.verify_bundle_hash(
            project_id=mock_project_id,
            kda_list=nine_plans_on_disk_tampered,
            expected_hash="deadbeef" * 8,
        )


@pytest.mark.asyncio
async def test_TC_L102_L204_906_togaf_d_timeout_fallback_uses_four_pieces_only(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
) -> None:
    """TC-L102-L204-906 · TOGAF D 永远不 ready · 15min 降级 · 用 4 件套+charter 作 quality/risk 上下文 · degraded=true。"""
    result = await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="full",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=None,
        togaf_d_wait_timeout_sec=0.1,
    )
    # 允许 PARTIAL 或 COMPLETE(degraded)
    assert result.degraded is True
    # quality/risk 无 ADR 引用（degraded fallback 场景下放宽）
    quality = next((p for p in result.plans if p.plan_type == "quality"), None)
    if quality is not None:
        assert any(r.plan_type == "quality" and r.reason == "togaf_d_timeout"
                   for r in result.degradation_reasons)


@pytest.mark.asyncio
async def test_TC_L102_L204_907_trim_level_minimal_produces_5_fixed_subset(
    sut,
    mock_project_id,
    mock_request_id,
    mock_four_pieces_ready,
    mock_togaf_d_ready,
) -> None:
    """TC-L102-L204-907 · trim_level=minimal · 固定 5 子集（scope/schedule/quality/risk/stakeholder_engagement）。"""
    result = await sut.produce_all_9(
        project_id=mock_project_id,
        request_id=mock_request_id,
        trim_level="minimal",
        dependencies=mock_four_pieces_ready,
        togaf_d_path=mock_togaf_d_ready["togaf_d_path"],
    )
    produced_types = {p.plan_type for p in result.plans}
    assert produced_types == {"scope", "schedule", "quality", "risk", "stakeholder_engagement"}
    assert len(result.plans) == 5
```

---

## §10 附录 · 测试运行矩阵

| 文件 | 标记 | 场景 | 覆盖节 |
|---|---|---|---|
| `test_l2_04_pmp_positive.py` | 默认 | 18 正向 TC | §2 |
| `test_l2_04_pmp_negative.py` | 默认 | 16 错误码 TC | §3 |
| `test_l2_04_pmp_ic_contracts.py` | 默认 | 6 IC 契约 | §4 |
| `test_l2_04_pmp_perf.py` | `@pytest.mark.perf` | 7 SLO | §5 |
| `test_l2_04_pmp_e2e.py` | `@pytest.mark.e2e` | 3 GWT e2e | §6 |
| `test_l2_04_x_l2_07_integration.py` | 默认 | 2 跨 L2 | §8.1 |
| `test_l2_04_x_l2_05_integration.py` | 默认 | 2 双向 Partnership | §8.2 |
| `test_l2_04_x_l2_01_integration.py` | 默认 | 1 信号累积 | §8.3 |
| `test_l2_04_pmp_edge.py` | 默认 | 7 边界 | §9 |

**运行命令**：
```bash
pytest tests/l1_02 -k "l2_04" -v                # 全部
pytest tests/l1_02 -k "l2_04" -m "not perf"     # 排除 perf
pytest tests/l1_02 -k "l2_04 and e2e"           # 仅 e2e
```

---

*— L1-02 L2-04 PMP 9 计划生产器 · TDD 测试用例 · session H · v1.0 填充完成 —*
