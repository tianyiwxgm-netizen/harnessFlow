---
doc_id: tests-L1-04-L2-01-TDD 蓝图生成器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-01-TDD 蓝图生成器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-01 TDD 蓝图生成器 · TDD 测试用例

> 基于 3-1 L2-01 §3（4 个 public 方法）+ §11 错误码（10 类降级错误 · 与 §3.5 错误码总表映射的 19 项接口错误码）+ §12 SLO（延迟 / 吞吐 / 并发）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L104-L201-NNN`（L1-04 下 L2-01，三位流水号 · 001-099 正向 / 1xx-4xx 负向按方法分段 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_01_TDDBlueprintGenerator` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock repo）
- [x] §8 集成点用例（与兄弟 L2 协作 · L2-02/03/04）
- [x] §9 边界 / edge case（空/超大/并发/崩溃/版本链）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。
> 错误码前缀一律 `E_L204_L201_` · 以下表格省略前缀。

### §1.1 方法 × 测试 × 覆盖类型（§3 + §2 TC）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `generate_blueprint()` · §3.1 正常首次构造 | TC-L104-L201-001 | unit | IC-03 / IC-09 |
| `generate_blueprint()` · §3.1 幂等 cache 命中 | TC-L104-L201-002 | unit | — |
| `generate_blueprint()` · §3.1 异步 accept + estimated_completion | TC-L104-L201-003 | unit | — |
| `generate_blueprint()` · §3.1 FAIL-L2 重建（previous_blueprint_id） | TC-L104-L201-004 | unit | — |
| `generate_blueprint()` · §3.1 retry_focus 局部重做 | TC-L104-L201-005 | unit | — |
| `generate_blueprint()` · §3.1 config_overrides 生效 | TC-L104-L201-006 | unit | — |
| `generate_blueprint()` · §3.1 version = old+1 | TC-L104-L201-007 | unit | — |
| `get_blueprint()` · §3.2 mode=full 返回整份 | TC-L104-L201-010 | unit | — |
| `get_blueprint()` · §3.2 mode=wp_slice 返回切片 | TC-L104-L201-011 | unit | — |
| `get_blueprint()` · §3.2 mode=metadata_only 不含 matrix | TC-L104-L201-012 | unit | — |
| `get_blueprint()` · §3.2 指定 version 定点读 | TC-L104-L201-013 | unit | — |
| `validate_coverage()` · §3.3 AC 覆盖率 = 1.0 通过 | TC-L104-L201-020 | unit | — |
| `validate_coverage()` · §3.3 三角形比例归一化 | TC-L104-L201-021 | unit | — |
| `validate_coverage()` · §3.3 strict=false 降级 warn | TC-L104-L201-022 | unit | — |
| `broadcast_ready()` · §3.4 fanout 到 3 订阅者 | TC-L104-L201-030 | unit | IC-L2-01 |
| `broadcast_ready()` · §3.4 幂等二次调用静默 | TC-L104-L201-031 | unit | — |
| `broadcast_ready()` · §3.4 latency_ms 记录 | TC-L104-L201-032 | unit | — |

### §1.2 错误码 × 测试（§3 + §11 · 映射后并集 10+4+2+3 = 19 项 + §11 额外 P2/WARN 等级扩展）

| 错误码（省略 `E_L204_L201_` 前缀） | TC ID | 方法 / 触发 | 降级等级 |
|---|---|---|---|
| `BLUEPRINT_NO_PROJECT_ID` | TC-L104-L201-101 | `generate_blueprint()` | PM-14 硬红线 |
| `CROSS_PROJECT_BLUEPRINT` | TC-L104-L201-102 | `generate_blueprint()` | PM-14 硬红线 |
| `INVALID_PHASE` | TC-L104-L201-103 | `generate_blueprint()` | 拒绝 · 静默 |
| `AC_EMPTY` | TC-L104-L201-104 | `generate_blueprint()` | 推 INFO 澄清 |
| `BLUEPRINT_AC_MISSING` | TC-L104-L201-105 | `generate_blueprint()` | DRAFT 补缺 |
| `FOUR_PIECES_MISSING` | TC-L104-L201-106 | `generate_blueprint()` | 等 L1-02 完成重试 |
| `WBS_NOT_READY` | TC-L104-L201-107 | `generate_blueprint()` | 等 WBS ready 重试 |
| `BUILD_TIMEOUT` | TC-L104-L201-108 | `generate_blueprint()` | 🟠 P2 · fast-path 降级 |
| `SOURCE_REFS_MUTATED` | TC-L104-L201-109 | `generate_blueprint()` | Repository 重试一次 |
| `BLUEPRINT_TOO_LARGE` | TC-L104-L201-110 | `generate_blueprint()` | WARN L1-07 |
| `BLUEPRINT_NOT_FOUND` | TC-L104-L201-201 | `get_blueprint()` | 调用方订阅事件 |
| `CROSS_PROJECT_READ` | TC-L104-L201-202 | `get_blueprint()` | PM-14 违规告警 |
| `WP_SLICE_NOT_FOUND` | TC-L104-L201-203 | `get_blueprint(wp_slice)` | 回查 L1-03 |
| `VERSION_NOT_FOUND` | TC-L104-L201-204 | `get_blueprint(version)` | 回退 latest |
| `VALIDATION_BLUEPRINT_NOT_FOUND` | TC-L104-L201-301 | `validate_coverage()` | 调用方确认 id |
| `VALIDATION_STALE_READ` | TC-L104-L201-302 | `validate_coverage()` | 重试一次 |
| `BROADCAST_SLO_VIOLATION` | TC-L104-L201-401 | `broadcast_ready()` | 记审计 + WARN L1-07 |
| `BROADCAST_FANOUT_INCOMPLETE` | TC-L104-L201-402 | `broadcast_ready()` | 3 次重试 · 不阻塞 |
| `DUPLICATE_BROADCAST` | TC-L104-L201-403 | `broadcast_ready()` | 静默 + 审计 |
| `AC_COVERAGE_NOT_100`（§11 FAIL-L3）| TC-L104-L201-501 | S3 Gate · `validate_coverage(strict=true)` | 🔴 FAIL-L3 硬红线 |
| `AC_CASE_EXPLOSION`（§11 WARN）| TC-L104-L201-502 | `generate_blueprint()` · 派生超限 | 🟡 WARN · 截断 |
| `NLP_PARSE_FAILED`（§11 P2）| TC-L104-L201-503 | `generate_blueprint()` · fallback regex | 🟠 P2 · fallback |
| `BROADCAST_FAILED`（§11 P2 · 聚合）| TC-L104-L201-504 | `broadcast_ready()` · 3 L2 ≥ 1 失败 | 🟠 P2 · FAIL-L2 |
| `AUDIT_APPEND_FAILED`（§11 FAIL-L1）| TC-L104-L201-505 | IC-09 写失败 | 🔴 FAIL-L1 · WAL 重试 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-03 `enter_quality_loop{phase=S3}` | L1-01 → L1-04 → 本 L2 | TC-L104-L201-601 | 消费方 · 仅接受 phase=S3 |
| IC-06 `kb_read`（可选 recipe 查询）| 本 L2 → L1-06 | TC-L104-L201-602 | 可选 · miss 不 fail |
| IC-09 `append_event`（6 种事件类型）| 本 L2 → L1-09 | TC-L104-L201-603 | 状态转换必写审计 |
| IC-L2-01 `blueprint_ready`（3 下游 fanout）| 本 L2 → L2-02/03/04 | TC-L104-L201-604 | 生产方 · payload 结构断言 |
| IC-13 `push_suggestion`（间接 · 由 L1-07 消费本 L2 WARN）| 本 L2 → L1-07 | TC-L104-L201-605 | WARN/P2 升级链 |
| IC-16 `push_stage_gate_card`（间接 · 经 L1-02）| 本 L2 → L1-10（经 L1-02）| TC-L104-L201-606 | S3 Gate 凭证 1 |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1/§12.2） | 阈值 | TC ID |
|---|---|---|
| `generate_blueprint` P95（50 AC · 非 LLM 后端）| ≤ 500ms | TC-L104-L201-701 |
| `generate_blueprint` P99（50 AC · non-LLM）| ≤ 2000ms | TC-L104-L201-702 |
| `get_blueprint(hit_cache)` P95 | ≤ 10ms | TC-L104-L201-703 |
| `validate_coverage` P95 | ≤ 30ms | TC-L104-L201-704 |
| `broadcast_blueprint_ready` P95（并发）| ≤ 150ms | TC-L104-L201-705 |
| 单节点并发 ≥ 10 project P95 不劣化 | §12.2 | TC-L104-L201-706 |

### §1.5 PRD §8 GWT 八场景 × 测试

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · 一次蓝图完整生成（4 件套 + WBS 10 WP + 50 AC）| TC-L104-L201-801 | e2e |
| 正向 2 · 蓝图作为 S3 Gate 凭证（与其他 4 件并齐）| TC-L104-L201-802 | e2e |
| 负向 3 · AC 覆盖率不达标（50 条漏 1 条）| TC-L104-L201-803 | e2e |
| 负向 4 · 4 件套缺失触发澄清（quality-standard.md 空）| TC-L104-L201-804 | e2e |
| 集成 5 · 与 L2-02/03/04 并行下游读同一 ac_matrix | TC-L104-L201-901 | integration |
| 集成 6 · FAIL-L2 回退后重建蓝图 | TC-L104-L201-902 | integration |
| 性能 7 · 大规模 AC（500 + 30 WP）| TC-L104-L201-707 | perf |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_01_TDDBlueprintGenerator`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`TDDBlueprintGenerator`（聚合根 Domain Service + Factory）· 从 `app.l1_04.l2_01.generator` 导入。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import (
    GenerateBlueprintRequest,
    GenerateBlueprintResponse,
    GetBlueprintQuery,
    GetBlueprintResponse,
    ValidateCoverageQuery,
    ValidateCoverageResponse,
    BroadcastReadyRequest,
    BroadcastReadyResponse,
)
from app.l1_04.l2_01.errors import TDDBlueprintError


class TestL2_01_TDDBlueprintGenerator:
    """§3 public 方法正向用例。每方法 ≥ 1 happy path。"""

    # --------- 3.1 generate_blueprint · 正常首次 --------- #

    def test_TC_L104_L201_001_generate_blueprint_happy_path_50_ac(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-001 · 首次构造 · 50 AC · 返回 blueprint_id + status=ACCEPTED。"""
        # arrange
        req: GenerateBlueprintRequest = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
        )
        # act
        resp: GenerateBlueprintResponse = sut.generate_blueprint(req)
        # assert
        assert resp.blueprint_id.startswith("bp-"), "§3.1 出参 format=bp-{uuid-v7}"
        assert resp.project_id == mock_project_id, "透传 request.project_id"
        assert resp.status == "ACCEPTED", "新构造 status=ACCEPTED"
        assert resp.version == 1, "首次版本 = 1"
        assert resp.ts_accepted is not None

    def test_TC_L104_L201_002_generate_blueprint_idempotent_cache_hit(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-002 · 同 (project_id, source_refs_hash) 二次调用返回首次 id · status=CACHED。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        first: GenerateBlueprintResponse = sut.generate_blueprint(req)
        second: GenerateBlueprintResponse = sut.generate_blueprint(req)
        assert first.blueprint_id == second.blueprint_id, "§3.1 幂等性 · 内存 LRU 缓存 256"
        assert second.status == "CACHED"

    def test_TC_L104_L201_003_generate_blueprint_async_accept_returns_estimated_ts(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-003 · 异步 accept · 不阻塞 L1-01 · 返回 estimated_completion_ts。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.estimated_completion_ts is not None, "§3.1 P95 ≤ 2 分钟 · 供 UI 进度条"
        # 异步 · 此时 state 应仍为 DRAFT 或 VALIDATING（未 READY）
        snapshot = sut._peek_state(resp.blueprint_id)
        assert snapshot.state in ("DRAFT", "VALIDATING"), "accept 后不阻塞 · 后台构造"

    def test_TC_L104_L201_004_generate_blueprint_fail_l2_rebuild_with_previous_id(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-004 · FAIL-L2 回退重建 · previous_blueprint_id 透传 · version=old+1。"""
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        first = sut.generate_blueprint(req1)
        sut._force_state(first.blueprint_id, "FAILED")  # 模拟 L2-07 判定 FAIL-L2

        req2 = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=first.blueprint_id,
        )
        second = sut.generate_blueprint(req2)
        assert second.blueprint_id != first.blueprint_id, "回退产新 bp id"
        assert second.version == first.version + 1, "§3.1 出参 · 版本号 = 旧 + 1"

    def test_TC_L104_L201_005_generate_blueprint_retry_focus_partial_rebuild(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-005 · retry_focus=['test_pyramid','coverage_target'] · 其他 section 保留。"""
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        first = sut.generate_blueprint(req1)
        sut._force_state(first.blueprint_id, "FAILED")

        req2 = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=first.blueprint_id,
            retry_focus=["test_pyramid", "coverage_target"],
        )
        second = sut.generate_blueprint(req2)
        assert second.status == "ACCEPTED"
        meta = sut._debug_rebuild_meta(second.blueprint_id)
        assert set(meta["rebuilt_sections"]) == {"test_pyramid", "coverage_target"}
        assert "ac_matrix" in meta["preserved_sections"], "未指定 focus 的 section 继承旧蓝图"

    def test_TC_L104_L201_006_generate_blueprint_config_overrides_applied(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-006 · config_overrides 覆盖 §10 默认 · pyramid_default_ratio=[0.6,0.3,0.1]。"""
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            config_overrides={"pyramid_default_ratio": [0.6, 0.3, 0.1]},
        )
        resp = sut.generate_blueprint(req)
        sut._await_ready(resp.blueprint_id)
        snapshot = sut.get_blueprint(
            GetBlueprintQuery(
                query_id="q-override-001",
                project_id=mock_project_id,
                blueprint_id=resp.blueprint_id,
                mode="full",
            )
        )
        assert snapshot.test_pyramid["unit_ratio"] == pytest.approx(0.6, abs=1e-6)
        assert snapshot.test_pyramid["integration_ratio"] == pytest.approx(0.3, abs=1e-6)
        assert snapshot.test_pyramid["e2e_ratio"] == pytest.approx(0.1, abs=1e-6)

    def test_TC_L104_L201_007_generate_blueprint_version_increment(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-007 · 连续 2 次 FAIL-L2 重建 · version 单调递增 1 → 2 → 3。"""
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        r1 = sut.generate_blueprint(req1)
        sut._force_state(r1.blueprint_id, "FAILED")
        req2 = make_generate_request(project_id=mock_project_id, clause_count=50, previous_blueprint_id=r1.blueprint_id)
        r2 = sut.generate_blueprint(req2)
        sut._force_state(r2.blueprint_id, "FAILED")
        req3 = make_generate_request(project_id=mock_project_id, clause_count=50, previous_blueprint_id=r2.blueprint_id)
        r3 = sut.generate_blueprint(req3)
        assert (r1.version, r2.version, r3.version) == (1, 2, 3)

    # --------- 3.2 get_blueprint · 3 mode --------- #

    def test_TC_L104_L201_010_get_blueprint_mode_full_returns_aggregate(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-010 · mode=full · 返回 test_pyramid + ac_matrix + coverage_target + test_env_blueprint。"""
        query = GetBlueprintQuery(
            query_id="q-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="full",
        )
        resp: GetBlueprintResponse = sut.get_blueprint(query)
        assert resp.state in ("READY", "PUBLISHED"), "§3.2 枚举 state"
        assert resp.test_pyramid is not None
        assert resp.ac_matrix is not None and len(resp.ac_matrix) > 0
        assert resp.coverage_target["ac"] == 1.0, "§3.2 const=1.0 硬锁"
        assert resp.test_env_blueprint is not None

    def test_TC_L104_L201_011_get_blueprint_mode_wp_slice_returns_slice(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
        sample_wp_id: str,
    ) -> None:
        """TC-L104-L201-011 · mode=wp_slice 返回 wp_id + related_ac_ids + coverage_slice。"""
        query = GetBlueprintQuery(
            query_id="q-002",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="wp_slice",
            wp_id=sample_wp_id,
        )
        resp = sut.get_blueprint(query)
        assert resp.wp_slice is not None
        assert resp.wp_slice["wp_id"] == sample_wp_id
        assert len(resp.wp_slice["related_ac_ids"]) >= 1
        assert "coverage_slice" in resp.wp_slice

    def test_TC_L104_L201_012_get_blueprint_mode_metadata_only_omits_matrix(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-012 · mode=metadata_only · 仅 header · 不含 ac_matrix。"""
        query = GetBlueprintQuery(
            query_id="q-003",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="metadata_only",
        )
        resp = sut.get_blueprint(query)
        assert resp.blueprint_id == ready_blueprint_id
        assert resp.version is not None
        assert resp.state is not None
        assert resp.ac_matrix is None, "metadata_only 不含 matrix"

    def test_TC_L104_L201_013_get_blueprint_version_pinned(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-013 · version=1 定点读 · 不受 latest 变更影响。"""
        query = GetBlueprintQuery(
            query_id="q-004",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="full",
            version=1,
        )
        resp = sut.get_blueprint(query)
        assert resp.version == 1

    # --------- 3.3 validate_coverage · AC 硬锁 --------- #

    def test_TC_L104_L201_020_validate_coverage_ac_100_passes(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-020 · AC 覆盖率 = 1.0 · valid=true · missing_ac_ids=[]。"""
        query = ValidateCoverageQuery(
            query_id="q-cov-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            strict_mode=True,
        )
        rep: ValidateCoverageResponse = sut.validate_coverage(query)
        assert rep.valid is True
        assert rep.ac_coverage == 1.0
        assert rep.missing_ac_ids == []
        assert rep.priority_annotation_complete is True

    def test_TC_L104_L201_021_validate_coverage_pyramid_ratios_normalized(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-021 · 三角形三层比例和 = 1.0 ± 0.01 · pyramid_ratios_valid=True。"""
        rep = sut.validate_coverage(
            ValidateCoverageQuery(
                query_id="q-cov-002",
                project_id=mock_project_id,
                blueprint_id=ready_blueprint_id,
                strict_mode=True,
            )
        )
        assert rep.pyramid_ratios_valid is True

    def test_TC_L104_L201_022_validate_coverage_strict_false_only_warns(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        blueprint_id_with_missing_ac: str,
    ) -> None:
        """TC-L104-L201-022 · strict=false · AC < 1.0 不 fail · valid=true + issue severity=WARN。"""
        rep = sut.validate_coverage(
            ValidateCoverageQuery(
                query_id="q-cov-003",
                project_id=mock_project_id,
                blueprint_id=blueprint_id_with_missing_ac,
                strict_mode=False,
            )
        )
        assert rep.valid is True, "strict=false · 不 fail（仅供调试）"
        assert any(iss["severity"] == "WARN" for iss in rep.issues)

    # --------- 3.4 broadcast_ready · IC-L2-01 --------- #

    def test_TC_L104_L201_030_broadcast_ready_fanout_to_three_subscribers(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-030 · fanout L2-02/03/04 · event_type=L1-04:blueprint_ready。"""
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp: BroadcastReadyResponse = sut.broadcast_ready(req)
        assert resp.published is True
        assert len(resp.fanout_acks) == 3
        assert {a["subscriber"] for a in resp.fanout_acks} == {"L2-02", "L2-03", "L2-04"}
        # IC-09 审计落盘
        calls = [c for c in mock_event_bus.append_event.call_args_list
                 if c.kwargs.get("event_type") == "L1-04:blueprint_ready"]
        assert len(calls) == 1

    def test_TC_L104_L201_031_broadcast_ready_duplicate_call_idempotent(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-031 · 同 blueprint_id 二次广播返回首次 event_id（防重触发下游）。"""
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        r1 = sut.broadcast_ready(req)
        r2 = sut.broadcast_ready(req)
        assert r1.event_id == r2.event_id, "§3.4 幂等性"

    def test_TC_L104_L201_032_broadcast_ready_records_latency_ms(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-032 · 出参含 latency_ms 整数 · 供 §12.5 基线回归比对。"""
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        assert isinstance(resp.latency_ms, int) and resp.latency_ms >= 0
```

---

## §3 负向用例（每错误码 ≥ 1）

> 覆盖 §3.5 错误码总表（19 项）+ §11 降级等级错误码（5 项 P2/WARN/FAIL-L1/FAIL-L3 额外）。
> 所有错误码前缀 `E_L204_L201_` · 统一经 `TDDBlueprintError.code` 暴露 · 调用方通过 `code` 做路由而非 `isinstance`。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_negative.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import (
    GenerateBlueprintRequest,
    GetBlueprintQuery,
    ValidateCoverageQuery,
    BroadcastReadyRequest,
)
from app.l1_04.l2_01.errors import TDDBlueprintError


class TestL2_01_Negative_GenerateBlueprint:
    """§3.1 10 项错误码 + §11 扩展（NLP_PARSE_FAILED / AC_CASE_EXPLOSION / BUILD_TIMEOUT 等）。"""

    def test_TC_L104_L201_101_missing_project_id_raises(
        self, sut: TDDBlueprintGenerator, make_generate_request,
    ) -> None:
        """TC-L104-L201-101 · project_id 缺失 → E_L204_L201_BLUEPRINT_NO_PROJECT_ID（PM-14 硬红线）。"""
        req = make_generate_request(project_id=None, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_NO_PROJECT_ID"

    def test_TC_L104_L201_102_cross_project_previous_blueprint_rejected(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, other_project_id: str,
        make_generate_request, ready_blueprint_id_of_other_project: str,
    ) -> None:
        """TC-L104-L201-102 · previous_blueprint_id 属 other_project → E_L204_L201_CROSS_PROJECT_BLUEPRINT。"""
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            previous_blueprint_id=ready_blueprint_id_of_other_project,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_CROSS_PROJECT_BLUEPRINT"

    def test_TC_L104_L201_103_invalid_phase_rejected_silently(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-103 · entry_phase=S2 → E_L204_L201_INVALID_PHASE（§1.4 L2-01 入口唯一 S3）。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50, entry_phase="S2")
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_INVALID_PHASE"

    def test_TC_L104_L201_104_ac_empty_triggers_clarify_info(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-104 · clause_count=0 → E_L204_L201_AC_EMPTY + IC-09 validation_failed + 推 L1-07 INFO。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=0)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_AC_EMPTY"
        # IC-09 审计（§11 规定 INFO 级）
        types = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert "L1-04:blueprint_validation_failed" in types

    def test_TC_L104_L201_105_blueprint_ac_missing_goes_to_awaiting(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-105 · Factory 发现 AC 条某条无槽位 → E_L204_L201_BLUEPRINT_AC_MISSING + VALIDATING→AWAITING_CLARIFY。"""
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            inject_unmapped_ac_count=1,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_AC_MISSING"

    def test_TC_L104_L201_106_four_pieces_missing_rejects(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_fs,
    ) -> None:
        """TC-L104-L201-106 · requirements.md 缺文件 → E_L204_L201_FOUR_PIECES_MISSING。"""
        mock_fs.mark_missing("projects/pid-default/four-pieces/requirements.md")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_FOUR_PIECES_MISSING"

    def test_TC_L104_L201_107_wbs_not_ready_rejects(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_fs,
    ) -> None:
        """TC-L104-L201-107 · WBS topology.yaml 缺 → E_L204_L201_WBS_NOT_READY。"""
        mock_fs.mark_missing("projects/pid-default/wbs/topology.yaml")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_WBS_NOT_READY"

    def test_TC_L104_L201_108_build_timeout_over_5min(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_clock,
    ) -> None:
        """TC-L104-L201-108 · Factory 耗时 > 5min 硬上限 → E_L204_L201_BUILD_TIMEOUT + abort。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50, simulate_stage_delay_s=310)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req, _advance_clock=mock_clock)
        assert ei.value.code == "E_L204_L201_BUILD_TIMEOUT"

    def test_TC_L104_L201_109_source_refs_mutated_detected_at_save(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_fs,
    ) -> None:
        """TC-L104-L201-109 · save 时发现 four_pieces_hash 变 → E_L204_L201_SOURCE_REFS_MUTATED（I-L201-07）。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        # simulate 4 件套被并发改写 · hash 变
        mock_fs.mutate_after_load("projects/pid-default/four-pieces/requirements.md")
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_SOURCE_REFS_MUTATED"

    def test_TC_L104_L201_110_blueprint_too_large_warns(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-110 · master-test-plan.md > 1MB → E_L204_L201_BLUEPRINT_TOO_LARGE + WARN L1-07。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=5000)  # 极端 AC 数
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_TOO_LARGE"


class TestL2_01_Negative_GetBlueprint:
    """§3.2 4 项错误码。"""

    def test_TC_L104_L201_201_blueprint_not_found(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
    ) -> None:
        """TC-L104-L201-201 · 不存在的 blueprint_id → E_L204_L201_BLUEPRINT_NOT_FOUND。"""
        query = GetBlueprintQuery(
            query_id="q-nf-001",
            project_id=mock_project_id,
            blueprint_id="bp-does-not-exist",
            mode="full",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_NOT_FOUND"

    def test_TC_L104_L201_202_cross_project_read_blocked(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
        ready_blueprint_id_of_other_project: str,
    ) -> None:
        """TC-L104-L201-202 · query.project_id ≠ blueprint.project_id → E_L204_L201_CROSS_PROJECT_READ。"""
        query = GetBlueprintQuery(
            query_id="q-xp-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id_of_other_project,
            mode="full",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_CROSS_PROJECT_READ"

    def test_TC_L104_L201_203_wp_slice_not_found(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-203 · wp_id 不在聚合内 → E_L204_L201_WP_SLICE_NOT_FOUND。"""
        query = GetBlueprintQuery(
            query_id="q-wp-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="wp_slice",
            wp_id="wp-ghost-999",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_WP_SLICE_NOT_FOUND"

    def test_TC_L104_L201_204_version_not_found(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-204 · version=99 不存在 → E_L204_L201_VERSION_NOT_FOUND。"""
        query = GetBlueprintQuery(
            query_id="q-v-001",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
            mode="full",
            version=99,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.get_blueprint(query)
        assert ei.value.code == "E_L204_L201_VERSION_NOT_FOUND"


class TestL2_01_Negative_ValidateCoverage:
    """§3.3 2 项错误码。"""

    def test_TC_L104_L201_301_validation_blueprint_not_found(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
    ) -> None:
        """TC-L104-L201-301 · blueprint_id 不存在 → E_L204_L201_VALIDATION_BLUEPRINT_NOT_FOUND。"""
        query = ValidateCoverageQuery(
            query_id="q-cov-nf",
            project_id=mock_project_id,
            blueprint_id="bp-ghost",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.validate_coverage(query)
        assert ei.value.code == "E_L204_L201_VALIDATION_BLUEPRINT_NOT_FOUND"

    def test_TC_L104_L201_302_validation_stale_read_race(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-302 · 校验中 blueprint 被并发改 → E_L204_L201_VALIDATION_STALE_READ。"""
        sut._arm_concurrent_mutation(ready_blueprint_id)
        query = ValidateCoverageQuery(
            query_id="q-cov-stale",
            project_id=mock_project_id,
            blueprint_id=ready_blueprint_id,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.validate_coverage(query)
        assert ei.value.code == "E_L204_L201_VALIDATION_STALE_READ"


class TestL2_01_Negative_Broadcast:
    """§3.4 3 项错误码 + §11 BROADCAST_FAILED 聚合。"""

    def test_TC_L104_L201_401_broadcast_slo_violation(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
        mock_event_bus: MagicMock, mock_clock,
    ) -> None:
        """TC-L104-L201-401 · latency_ms > 1000 → E_L204_L201_BROADCAST_SLO_VIOLATION · 不 fail 广播 · WARN L1-07。"""
        mock_event_bus.set_broadcast_latency_ms(1500)
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        # §11 · 不 fail · 但 audit 要有 SLO_VIOLATION 记录
        assert resp.published is True
        types = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert any("blueprint_broadcast_slo_violation" in (t or "") for t in types)

    def test_TC_L104_L201_402_broadcast_fanout_incomplete_one_offline(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-402 · L2-02 ack 超时 · 重试 3 次 · E_L204_L201_BROADCAST_FANOUT_INCOMPLETE · 不阻塞 PUBLISHED。"""
        mock_event_bus.set_subscriber_timeout("L2-02")
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        resp = sut.broadcast_ready(req)
        assert resp.published is True, "§11.1 不阻塞本 L2 转 PUBLISHED"
        types = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert "L1-04:blueprint_subscriber_unreachable" in types

    def test_TC_L104_L201_403_duplicate_broadcast_silent(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-403 · 二次广播 · E_L204_L201_DUPLICATE_BROADCAST · 静默 + 审计。"""
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        sut.broadcast_ready(req)
        # 强制再次触发（非幂等路径）
        sut._force_redundant_broadcast(ready_blueprint_id)
        types = [c.kwargs.get("event_type") for c in mock_event_bus.append_event.call_args_list]
        assert "L1-04:blueprint_duplicate_broadcast" in types


class TestL2_01_Negative_DegradationChain:
    """§11 降级等级扩展（FAIL-L1/L3 · P2 · WARN）。"""

    def test_TC_L104_L201_501_ac_coverage_not_100_fail_l3(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-501 · AC 覆盖率 ≠ 1.0 · strict=true → E_L204_L201_AC_COVERAGE_NOT_100（FAIL-L3 硬红线）· S3 Gate REJECT。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50, inject_unmapped_ac_count=2)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        # §11.1 规定此错误码无降级 · 硬红线
        assert ei.value.code in (
            "E_L204_L201_AC_COVERAGE_NOT_100",
            "E_L204_L201_BLUEPRINT_AC_MISSING",  # Factory 首次检出亦可暴露此码
        )
        assert ei.value.severity == "FAIL-L3"

    def test_TC_L104_L201_502_ac_case_explosion_truncates_and_warns(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-502 · 单 AC 派生用例超 max_test_cases_per_ac → 截断 + WARN · 不 fail。"""
        req = make_generate_request(
            project_id=mock_project_id,
            clause_count=50,
            inject_ac_case_explosion_on_ac_index=3,
        )
        resp = sut.generate_blueprint(req)  # 不 raise
        meta = sut._debug_build_meta(resp.blueprint_id)
        assert meta["warnings"]
        assert any(w["code"] == "E_L204_L201_AC_CASE_EXPLOSION" for w in meta["warnings"])
        assert meta["truncated_slots_count"] > 0

    def test_TC_L104_L201_503_nlp_parse_failed_falls_back_to_regex(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_nlp_backend: MagicMock,
    ) -> None:
        """TC-L104-L201-503 · nlp_parser_backend 抛错 → fallback regex · 整体构造成功。"""
        mock_nlp_backend.side_effect = RuntimeError("nlp_service_down")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.status == "ACCEPTED"
        meta = sut._debug_build_meta(resp.blueprint_id)
        assert meta["nlp_fallback_used"] is True, "§11 · 自动 fallback 到 regex"

    def test_TC_L104_L201_504_broadcast_failed_fail_l2(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-504 · 3 L2 全部 unreachable · 2 次重试 + 串行降级仍失败 → FAIL-L2 · 卡 S3 Gate。"""
        mock_event_bus.set_broadcast_all_fail()
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.broadcast_ready(req)
        assert ei.value.code == "E_L204_L201_BROADCAST_FAILED"
        assert ei.value.severity == "FAIL-L2"

    def test_TC_L104_L201_505_audit_append_failed_triggers_halt_after_10(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-505 · IC-09 连续失败 10 次 → E_L204_L201_AUDIT_APPEND_FAILED（FAIL-L1）· 触发 L1-07 HALT。"""
        mock_event_bus.append_event.side_effect = RuntimeError("wal_lost")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        # 10 次失败阈值（§11.1）
        for _ in range(10):
            with pytest.raises(TDDBlueprintError):
                sut.generate_blueprint(req)
        assert sut._last_halt_signal() is not None, "PM-18 审计断链 fail-closed"
```

---

## §4 IC-XX 契约集成测试

> 验证本 L2 参与的 6 条 IC 契约：IC-03（消费入口）· IC-06（可选 KB 读）· IC-09（审计写）· IC-L2-01（广播生产方）· IC-13（WARN/P2 升级 L1-07）· IC-16（经 L1-02 S3 Gate 卡）。
> 契约测试目标：**两端 schema + 幂等性 + SLO** 互信。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import (
    GenerateBlueprintRequest,
    BroadcastReadyRequest,
)


class TestL2_01_ICContracts:
    """§4 · IC 契约集成测试（每 IC ≥ 1 join test）。"""

    def test_TC_L104_L201_601_ic_03_consumes_enter_quality_loop_phase_s3(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-601 · IC-03 消费方 · 仅接受 phase=S3。

        join：L1-01 → IC-03 → L1-04 路由 → 本 L2.generate_blueprint(request)
        契约点：`entry_phase ∈ {S3}` 单值枚举（§3.1 入参约束）。
        """
        req = make_generate_request(project_id=mock_project_id, clause_count=50, entry_phase="S3")
        resp = sut.generate_blueprint(req)
        assert resp.status in ("ACCEPTED", "CACHED")

    def test_TC_L104_L201_602_ic_06_optional_recipe_miss_does_not_fail(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
        mock_l1_06_kb: MagicMock,
    ) -> None:
        """TC-L104-L201-602 · IC-06 kb_read recipe 未命中（可选增强）· 构造仍成功 · E_L204_L201_KB_RECIPE_MISS 仅 INFO。"""
        mock_l1_06_kb.kb_read.return_value = {"hits": [], "miss": True}
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        assert resp.status == "ACCEPTED", "§11 KB_RECIPE_MISS 无降级 · recipe 为可选"

    def test_TC_L104_L201_603_ic_09_append_event_state_transitions(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-603 · IC-09 · 从 DRAFT→VALIDATING→READY→PUBLISHED 每次转换 append 一条 state_transition 事件。

        join：本 L2 状态机 → IC-09 append_event → L1-09 WAL + hash chain。
        """
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        resp = sut.generate_blueprint(req)
        sut._await_published(resp.blueprint_id)
        events = [
            c.kwargs for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-04:blueprint_state_transition"
        ]
        transitions = [(e["payload"]["prev_state"], e["payload"]["new_state"]) for e in events]
        assert ("DRAFT", "VALIDATING") in transitions
        assert ("VALIDATING", "READY") in transitions
        assert ("READY", "PUBLISHED") in transitions

    def test_TC_L104_L201_604_ic_l2_01_blueprint_ready_payload_schema(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L201-604 · IC-L2-01 `blueprint_ready` payload 8 必需字段全齐（§4.2.1 YAML schema）。

        join：本 L2 → L2-02/03/04 via L1-09 事件总线。
        """
        req = BroadcastReadyRequest(
            blueprint_id=ready_blueprint_id,
            project_id=mock_project_id,
            ts_publish="2026-04-22T00:00:00Z",
        )
        sut.broadcast_ready(req)
        call = next(
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-04:blueprint_ready"
        )
        p = call.kwargs["payload"]
        for k in (
            "blueprint_id", "project_id", "version",
            "master_test_plan_path", "ac_matrix_path",
            "coverage_target_summary", "publisher", "ts",
        ):
            assert k in p, f"IC-L2-01 payload 缺字段 {k}"
        assert p["publisher"] == "L1-04:L2-01"
        assert p["master_test_plan_path"].endswith("/tdd/master-test-plan.md")
        assert p["ac_matrix_path"].endswith("/tdd/ac-matrix.yaml")

    def test_TC_L104_L201_605_ic_13_warn_escalated_to_l1_07(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        make_generate_request,
        mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L201-605 · IC-13 间接路径 · 连续 3 次 P2（BUILD_TIMEOUT）→ 升级 SUGGEST 给 L1-07（§11.3）。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50, simulate_stage_delay_s=310)
        for _ in range(3):
            try:
                sut.generate_blueprint(req)
            except Exception:
                pass
        assert mock_l1_07.push_suggestion.call_count >= 1
        call = mock_l1_07.push_suggestion.call_args.kwargs
        assert call["level"] in ("WARN", "SUGGEST")

    def test_TC_L104_L201_606_ic_16_stage_gate_card_via_l1_02(
        self,
        sut: TDDBlueprintGenerator,
        mock_project_id: str,
        ready_blueprint_id: str,
        mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L201-606 · IC-16 间接 · 本 L2 READY → 经 L1-02 汇总 S3 Gate 卡片 artifacts_bundle。

        join：本 L2 在 PUBLISHED 后推 L1-02 · L1-02 聚合 5 件凭证后 push gate card 给 L1-10。
        """
        sut._publish(ready_blueprint_id)
        # L1-02 侧应收到 artifacts_bundle 中的 master-test-plan 条目
        calls = [
            c for c in mock_l1_02.receive_artifact.call_args_list
            if c.kwargs.get("artifact_type") == "master_test_plan"
        ]
        assert len(calls) >= 1
        assert calls[0].kwargs["project_id"] == mock_project_id
```

---

## §5 性能 SLO 用例

> 对齐 §12 延迟 / 吞吐 / 并发 · 用 `@pytest.mark.perf` 标记（CI 分流跑 · 不在 fast 组）· 与 `bench/test_blueprint_generate_latency.py` baseline 互镜像。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_perf.py
from __future__ import annotations

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import quantiles
from typing import Any

from app.l1_04.l2_01.generator import TDDBlueprintGenerator


@pytest.mark.perf
class TestL2_01_PerfSLO:
    """§12 · 6 项性能 SLO。P95 不劣化 > 10% 相对 baseline（§12.5）。"""

    def test_TC_L104_L201_701_generate_blueprint_p95_under_500ms(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-701 · generate_blueprint(50 AC, non-LLM) P95 ≤ 500ms（§12.1）。"""
        samples: list[float] = []
        for i in range(30):
            req = make_generate_request(project_id=mock_project_id, clause_count=50, nonce=i)
            t0 = time.perf_counter()
            sut.generate_blueprint(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 500.0, f"P95={p95:.1f}ms > 500ms · §12.1 劣化"

    def test_TC_L104_L201_702_generate_blueprint_p99_under_2000ms(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-702 · generate_blueprint P99 ≤ 2000ms · 超则走 FAST_PATH（§11.2）。"""
        samples: list[float] = []
        for i in range(100):
            req = make_generate_request(project_id=mock_project_id, clause_count=50, nonce=i)
            t0 = time.perf_counter()
            sut.generate_blueprint(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p99 = sorted(samples)[98]
        assert p99 < 2000.0

    def test_TC_L104_L201_703_get_blueprint_hit_cache_p95_under_10ms(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-703 · get_blueprint(hit_cache) P95 ≤ 10ms（§12.1）。"""
        from app.l1_04.l2_01.schemas import GetBlueprintQuery
        samples: list[float] = []
        q = GetBlueprintQuery(query_id="q-perf", project_id=mock_project_id, blueprint_id=ready_blueprint_id, mode="full")
        for _ in range(50):
            t0 = time.perf_counter()
            sut.get_blueprint(q)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 10.0

    def test_TC_L104_L201_704_validate_coverage_p95_under_30ms(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-704 · validate_coverage P95 ≤ 30ms（§12.1 纯 CPU bound）。"""
        from app.l1_04.l2_01.schemas import ValidateCoverageQuery
        samples: list[float] = []
        q = ValidateCoverageQuery(query_id="q-v-perf", project_id=mock_project_id, blueprint_id=ready_blueprint_id)
        for _ in range(50):
            t0 = time.perf_counter()
            sut.validate_coverage(q)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 30.0

    def test_TC_L104_L201_705_broadcast_ready_p95_under_150ms(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
        fresh_ready_blueprint_factory,
    ) -> None:
        """TC-L104-L201-705 · broadcast_blueprint_ready（并发）P95 ≤ 150ms（§12.1）。"""
        from app.l1_04.l2_01.schemas import BroadcastReadyRequest
        samples: list[float] = []
        for _ in range(30):
            bp_id = fresh_ready_blueprint_factory()
            req = BroadcastReadyRequest(blueprint_id=bp_id, project_id=mock_project_id, ts_publish="2026-04-22T00:00:00Z")
            t0 = time.perf_counter()
            sut.broadcast_ready(req)
            samples.append((time.perf_counter() - t0) * 1000.0)
        p95 = quantiles(samples, n=20)[18]
        assert p95 < 150.0

    def test_TC_L104_L201_706_concurrent_10_projects_no_slo_degrade(
        self, sut: TDDBlueprintGenerator, make_generate_request,
    ) -> None:
        """TC-L104-L201-706 · 单节点 10 project 并发 generate_blueprint · P95 不劣化 > 10%（§12.2）。"""
        def one_call(idx: int) -> float:
            req = make_generate_request(project_id=f"pid-perf-{idx}", clause_count=50)
            t0 = time.perf_counter()
            sut.generate_blueprint(req)
            return (time.perf_counter() - t0) * 1000.0

        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(one_call, i) for i in range(10)]
            samples = [f.result() for f in as_completed(futures)]
        p95 = sorted(samples)[8]
        assert p95 < 550.0, f"10 并发 P95={p95:.1f}ms 劣化 > 10%"

    def test_TC_L104_L201_707_500_ac_large_scale_within_3min(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-707 · PRD §8 性能场景 7 · 500 AC + 30 WP · ≤ 3 分钟硬上限。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=500, wp_count=30)
        t0 = time.perf_counter()
        resp = sut.generate_blueprint(req)
        elapsed = time.perf_counter() - t0
        assert resp.status in ("ACCEPTED", "CACHED")
        assert elapsed < 180.0, f"500 AC 耗时 {elapsed:.1f}s 超 3min（prd §8.4）"
```

---

## §6 端到端 e2e

> 对齐 PRD §8 GWT 八场景（正向 1/2 · 负向 3/4 · 集成 5/6）· 跨 L2-01 → L1-09 → L2-02/03/04 → L1-02 S3 Gate 全链路。
> 用 `@pytest.mark.e2e` 标记，用真实 tmp_path + 真实文件系统 + mock 的 IC-09 / 下游 L2。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_e2e.py
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import GenerateBlueprintRequest


@pytest.mark.e2e
class TestL2_01_E2E_PRDGWTScenarios:
    """PRD §8 GWT 场景 · 正向 1/2 · 负向 3/4 · 集成 5/6。"""

    def test_TC_L104_L201_801_positive_1_full_blueprint_generation(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
        make_generate_request, mock_event_bus: MagicMock,
        mock_l2_02: MagicMock, mock_l2_03: MagicMock, mock_l2_04: MagicMock,
    ) -> None:
        """TC-L104-L201-801 · PRD §8 正向 1 · 4 件套全齐 + WBS 10 WP + 50 AC → 蓝图完整生成 + 下游并行起跑。

        Given: 4 件套全齐 + WBS 10 WP + 50 AC
        When:  收到 IC-03 enter_quality_loop{phase=S3}
        Then:
          - blueprint_id 返回
          - master-test-plan.md 落盘
          - ac-matrix.yaml 落盘
          - blueprint_ready 广播给 L2-02/03/04
          - S3 Gate 凭证 1 就位
        """
        req = make_generate_request(project_id=mock_project_id, clause_count=50, wp_count=10)
        resp = sut.generate_blueprint(req)
        sut._await_published(resp.blueprint_id)

        # 文件落盘
        fs = sut.get_repo_fs()
        assert fs.exists(f"projects/{mock_project_id}/tdd/master-test-plan.md")
        assert fs.exists(f"projects/{mock_project_id}/tdd/ac-matrix.yaml")
        assert fs.exists(f"projects/{mock_project_id}/tdd/test-env-blueprint.yaml")
        # 广播下游
        assert mock_l2_02.on_blueprint_ready.called
        assert mock_l2_03.on_blueprint_ready.called
        assert mock_l2_04.on_blueprint_ready.called

    def test_TC_L104_L201_802_positive_2_blueprint_as_s3_gate_evidence(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
        make_generate_request, mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L201-802 · PRD §8 正向 2 · 蓝图作为 S3 Gate 凭证 1 · 经 L1-02 汇总 5 件提交 L1-10。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=50, wp_count=10)
        resp = sut.generate_blueprint(req)
        sut._await_published(resp.blueprint_id)
        # L1-02 收到 master_test_plan artifact（§4.4 五件产物依赖）
        artifact_types = [c.kwargs.get("artifact_type") for c in mock_l1_02.receive_artifact.call_args_list]
        assert "master_test_plan" in artifact_types

    def test_TC_L104_L201_803_negative_3_ac_coverage_not_100_rejects(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-803 · PRD §8 负向 3 · 50 条 AC 漏 1 · S3 Gate REJECT + 推 INFO 澄清。"""
        from app.l1_04.l2_01.errors import TDDBlueprintError
        req = make_generate_request(
            project_id=mock_project_id, clause_count=50, inject_unmapped_ac_count=1,
        )
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code in (
            "E_L204_L201_BLUEPRINT_AC_MISSING",
            "E_L204_L201_AC_COVERAGE_NOT_100",
        )

    def test_TC_L104_L201_804_negative_4_four_pieces_missing_awaits_clarify(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
        mock_fs,
    ) -> None:
        """TC-L104-L201-804 · PRD §8 负向 4 · quality-standard.md 空 → AWAITING_CLARIFY → IC-03 澄清后恢复。"""
        from app.l1_04.l2_01.errors import TDDBlueprintError
        mock_fs.mark_empty(f"projects/{mock_project_id}/four-pieces/quality-standard.md")
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_FOUR_PIECES_MISSING"
        # 模拟澄清：补 quality-standard.md
        mock_fs.write(f"projects/{mock_project_id}/four-pieces/quality-standard.md", "# Q\n- 覆盖率 ≥ 80%\n")
        # 重试成功
        resp = sut.generate_blueprint(req)
        assert resp.status == "ACCEPTED"
```

---

## §7 测试 fixture

> 共享 fixture：SUT 实例 / mock project_id / mock clock / mock event bus / mock repo / mock 下游 L2-02/03/04 / blueprint factory。
> 放在 `tests/l1_04/conftest.py` · autouse 的只开 event bus · 其余 opt-in。

```python
# file: tests/l1_04/conftest.py
from __future__ import annotations

import pytest
import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import GenerateBlueprintRequest


@pytest.fixture
def mock_project_id() -> str:
    return "pid-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-other-foreign"


@pytest.fixture
def mock_clock() -> MagicMock:
    clk = MagicMock()
    clk.now_ms = 1_713_744_000_000  # 2026-04-22T00:00:00Z
    def _advance(delta_ms: int) -> None:
        clk.now_ms += delta_ms
    clk.advance = _advance
    return clk


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append_event.return_value = {"ok": True}
    bus.set_broadcast_latency_ms = lambda ms: setattr(bus, "_lat", ms)
    bus.set_subscriber_timeout = lambda sub: setattr(bus, "_timeout_sub", sub)
    bus.set_broadcast_all_fail = lambda: setattr(bus, "_all_fail", True)
    return bus


@pytest.fixture
def mock_fs() -> MagicMock:
    fs = MagicMock()
    fs._missing: set[str] = set()
    fs.mark_missing = lambda p: fs._missing.add(p)
    fs.mark_empty = lambda p: fs._missing.add(p)
    fs.mutate_after_load = lambda p: fs._missing.add(p + ".mutated")
    fs.write = lambda p, c: fs._missing.discard(p)
    return fs


@pytest.fixture
def mock_l2_02() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_03() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_04() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_02() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_06_kb() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_07() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_nlp_backend() -> MagicMock: return MagicMock()


@pytest.fixture
def sut(
    mock_project_id, mock_clock, mock_event_bus, mock_fs,
    mock_l2_02, mock_l2_03, mock_l2_04, mock_l1_02, mock_l1_06_kb, mock_l1_07, mock_nlp_backend,
) -> TDDBlueprintGenerator:
    return TDDBlueprintGenerator(
        clock=mock_clock,
        event_bus=mock_event_bus,
        fs=mock_fs,
        l2_02=mock_l2_02, l2_03=mock_l2_03, l2_04=mock_l2_04,
        l1_02=mock_l1_02, l1_06_kb=mock_l1_06_kb, l1_07=mock_l1_07,
        nlp_backend=mock_nlp_backend,
    )


@pytest.fixture
def make_generate_request() -> Callable[..., GenerateBlueprintRequest]:
    def _factory(**overrides: Any) -> GenerateBlueprintRequest:
        base = dict(
            command_id=f"cmd-{uuid.uuid4()}",
            project_id="pid-default",
            entry_phase="S3",
            four_pieces_refs={
                "requirements_path": "projects/pid-default/four-pieces/requirements.md",
                "goals_path": "projects/pid-default/four-pieces/goals.md",
                "ac_list_path": "projects/pid-default/four-pieces/ac-list.md",
                "quality_standard_path": "projects/pid-default/four-pieces/quality-standard.md",
                "four_pieces_hash": "sha256:" + "a" * 64,
            },
            wbs_refs={
                "topology_path": "projects/pid-default/wbs/topology.yaml",
                "wbs_version": 1,
            },
            ac_clauses_refs={
                "ac_manifest_path": "projects/pid-default/four-pieces/ac-manifest.yaml",
                "clause_count": 50,
            },
            previous_blueprint_id=None,
            retry_focus=None,
            config_overrides=None,
            trigger_tick_id=f"tick-{uuid.uuid4()}",
        )
        # convenience flags
        if "clause_count" in overrides:
            base["ac_clauses_refs"]["clause_count"] = overrides.pop("clause_count")
        base.update({k: v for k, v in overrides.items() if k in base})
        return GenerateBlueprintRequest(**base)
    return _factory


@pytest.fixture
def ready_blueprint_id(sut, mock_project_id, make_generate_request) -> str:
    req = make_generate_request(project_id=mock_project_id, clause_count=50)
    resp = sut.generate_blueprint(req)
    sut._await_published(resp.blueprint_id)
    return resp.blueprint_id


@pytest.fixture
def fresh_ready_blueprint_factory(sut, mock_project_id, make_generate_request) -> Callable[[], str]:
    def _make() -> str:
        req = make_generate_request(project_id=mock_project_id, clause_count=50, nonce=uuid.uuid4())
        r = sut.generate_blueprint(req)
        sut._await_published(r.blueprint_id)
        return r.blueprint_id
    return _make


@pytest.fixture
def sample_wp_id() -> str: return "wp-0001"


@pytest.fixture
def blueprint_id_with_missing_ac(sut, mock_project_id, make_generate_request) -> str:
    """构造一个 ac_coverage < 1.0 的 blueprint（绕过 strict=true 的直接方式）。"""
    return sut._build_partial_blueprint_for_test(project_id=mock_project_id, unmapped_count=1)


@pytest.fixture
def ready_blueprint_id_of_other_project(sut, other_project_id, make_generate_request) -> str:
    req = make_generate_request(project_id=other_project_id, clause_count=50)
    r = sut.generate_blueprint(req)
    sut._await_published(r.blueprint_id)
    return r.blueprint_id
```

---

## §8 集成点用例

> 与兄弟 L2（L2-02 DoD 编译器 / L2-03 测试用例生成器 / L2-04 质量 Gate 编译器）的协作。
> 本 L2 是"总指挥 + 广播源"，下游三 L2 必须以 `get_blueprint(mode=full)` 读到同一份 `ac_matrix` —— 这是 `IC-L2-01` 契约的下游约束。

```python
# file: tests/l1_04/test_l2_01_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import GetBlueprintQuery, BroadcastReadyRequest


class TestL2_01_SiblingIntegration:
    """§8 · 与 L2-02 / L2-03 / L2-04 的协作（IC-L2-01 fanout + get_blueprint pull）。"""

    def test_TC_L104_L201_901_l2_02_03_04_read_same_ac_matrix(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-901 · PRD §8 集成 5 · L2-02/03/04 并行读到同一 ac_matrix（hash 一致）。"""
        q = GetBlueprintQuery(
            query_id="q-int-001", project_id=mock_project_id,
            blueprint_id=ready_blueprint_id, mode="full",
        )
        r_l202 = sut.get_blueprint(q)
        r_l203 = sut.get_blueprint(q)
        r_l204 = sut.get_blueprint(q)
        # 三者必须看到完全相同的 ac_matrix（IC-L2-01 broadcast 保障一致性）
        assert r_l202.ac_matrix == r_l203.ac_matrix == r_l204.ac_matrix
        assert r_l202.version == r_l203.version == r_l204.version

    def test_TC_L104_L201_902_fail_l2_rebuild_bumps_version_and_rebroadcasts(
        self, sut: TDDBlueprintGenerator, mock_project_id: str,
        make_generate_request, mock_l2_02: MagicMock, mock_l2_03: MagicMock, mock_l2_04: MagicMock,
    ) -> None:
        """TC-L104-L201-902 · PRD §8 集成 6 · FAIL-L2 回退 · version+1 · 重新广播 · 下游拿到 v2。"""
        req1 = make_generate_request(project_id=mock_project_id, clause_count=50)
        r1 = sut.generate_blueprint(req1)
        sut._await_published(r1.blueprint_id)
        mock_l2_02.on_blueprint_ready.reset_mock()
        mock_l2_03.on_blueprint_ready.reset_mock()
        mock_l2_04.on_blueprint_ready.reset_mock()

        sut._force_state(r1.blueprint_id, "FAILED")
        req2 = make_generate_request(
            project_id=mock_project_id, clause_count=50,
            previous_blueprint_id=r1.blueprint_id,
            retry_focus=["ac_matrix"],
        )
        r2 = sut.generate_blueprint(req2)
        sut._await_published(r2.blueprint_id)
        assert r2.version == 2
        assert mock_l2_02.on_blueprint_ready.called
        assert mock_l2_03.on_blueprint_ready.called
        assert mock_l2_04.on_blueprint_ready.called

    def test_TC_L104_L201_903_l2_04_calls_validate_coverage_at_gate_compile(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-903 · L2-04 编译 quality-gates.yaml 时回调 validate_coverage(strict=true)。"""
        from app.l1_04.l2_01.schemas import ValidateCoverageQuery
        q = ValidateCoverageQuery(
            query_id="q-l204-compile",
            project_id=mock_project_id, blueprint_id=ready_blueprint_id,
            strict_mode=True,
        )
        rep = sut.validate_coverage(q)
        assert rep.valid is True
        assert rep.ac_coverage == 1.0  # §3.3 AC 硬锁
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 并发读写 / 版本链边界 / 崩溃恢复 / 冷启动。至少 5 个 · 本文件 7 个。

```python
# file: tests/l1_04/test_l2_01_blueprint_generator_edge_cases.py
from __future__ import annotations

import pytest
import threading
from unittest.mock import MagicMock

from app.l1_04.l2_01.generator import TDDBlueprintGenerator
from app.l1_04.l2_01.schemas import GenerateBlueprintRequest, GetBlueprintQuery
from app.l1_04.l2_01.errors import TDDBlueprintError


class TestL2_01_EdgeCases:
    """§9 · 边界 · 空/超大/并发/崩溃/版本链/冷启动/脏数据。"""

    def test_TC_L104_L201_A01_ac_clause_count_zero_rejected_early(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-A01 · clause_count=0 · 极端空输入 · 早拒 + INFO 澄清（§11 AC_EMPTY）。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=0)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_AC_EMPTY"

    def test_TC_L104_L201_A02_oversized_blueprint_1MB_plus(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-A02 · master-test-plan.md > 1MB（prd §8.4 硬约束）· 拒绝 + WARN L1-07。"""
        req = make_generate_request(project_id=mock_project_id, clause_count=10000)  # 10k AC 会爆
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_TOO_LARGE"

    def test_TC_L104_L201_A03_concurrent_generate_same_project_lock_arbitrated(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-A03 · 10 线程并发 generate_blueprint 同 project_id · 锁仲裁 · 无 race · 结果一致。"""
        results: list[str] = []
        errors: list[Exception] = []
        def worker() -> None:
            try:
                req = make_generate_request(project_id=mock_project_id, clause_count=50)
                r = sut.generate_blueprint(req)
                results.append(r.blueprint_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)

        # 幂等：10 次调用全部返回同一 blueprint_id（同 source_refs_hash）
        assert len(set(results)) == 1, f"并发幂等失败：{set(results)}"
        assert errors == []

    def test_TC_L104_L201_A04_blueprint_lock_timeout_backoff_retry(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-A04 · 写锁被占 · 指数退避 50→200→800ms · 3 次后返错（§11 BLUEPRINT_LOCK_TIMEOUT）。"""
        sut._hold_write_lock(mock_project_id)
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        with pytest.raises(TDDBlueprintError) as ei:
            sut.generate_blueprint(req)
        assert ei.value.code == "E_L204_L201_BLUEPRINT_LOCK_TIMEOUT"

    def test_TC_L104_L201_A05_cold_start_loads_nlp_model_under_2s(
        self, mock_project_id: str, mock_clock, mock_event_bus, mock_fs,
        mock_l2_02, mock_l2_03, mock_l2_04, mock_l1_02, mock_l1_06_kb, mock_l1_07, mock_nlp_backend,
        make_generate_request,
    ) -> None:
        """TC-L104-L201-A05 · 冷启动首 generate · 加载 NLP 模型 P95 ≤ 2s（§12.4）。"""
        import time
        cold_sut = TDDBlueprintGenerator(
            clock=mock_clock, event_bus=mock_event_bus, fs=mock_fs,
            l2_02=mock_l2_02, l2_03=mock_l2_03, l2_04=mock_l2_04,
            l1_02=mock_l1_02, l1_06_kb=mock_l1_06_kb, l1_07=mock_l1_07,
            nlp_backend=mock_nlp_backend,
        )
        req = make_generate_request(project_id=mock_project_id, clause_count=50)
        t0 = time.perf_counter()
        cold_sut.generate_blueprint(req)
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"冷启动 {elapsed:.2f}s > 2s（§12.4）"

    def test_TC_L104_L201_A06_state_transition_invalid_guard(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, ready_blueprint_id: str,
    ) -> None:
        """TC-L104-L201-A06 · DRAFT → PUBLISHED 跳态 · guard 拒绝 · E_L204_L201_STATE_TRANSITION_INVALID。"""
        bp_id = sut._build_draft_for_test(project_id=mock_project_id)
        with pytest.raises(TDDBlueprintError) as ei:
            sut._illegal_transition(bp_id, from_state="DRAFT", to_state="PUBLISHED")
        assert ei.value.code == "E_L204_L201_STATE_TRANSITION_INVALID"

    def test_TC_L104_L201_A07_version_chain_monotonic_after_3_failures(
        self, sut: TDDBlueprintGenerator, mock_project_id: str, make_generate_request,
    ) -> None:
        """TC-L104-L201-A07 · 连续 3 次 FAIL-L2 · version 单调 1→2→3→4（不回退也不跳号）。"""
        versions: list[int] = []
        prev_id: str | None = None
        for _ in range(4):
            req = make_generate_request(
                project_id=mock_project_id, clause_count=50, previous_blueprint_id=prev_id,
            )
            r = sut.generate_blueprint(req)
            versions.append(r.version)
            sut._force_state(r.blueprint_id, "FAILED")
            prev_id = r.blueprint_id
        assert versions == [1, 2, 3, 4], f"版本链不单调: {versions}"
```

---

*— L1-04 L2-01 TDD 蓝图生成器 · TDD 测试用例 · 深度 B · 4 方法 × 16 正向 × 19+5 负向 × 6 IC × 7 SLO × 4 e2e × 3 集成 × 7 边界 全节完整 —*
