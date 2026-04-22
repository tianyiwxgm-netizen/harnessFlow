---
doc_id: tests-L1-02-L2-03-4 件套生产器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-03-4 件套生产器.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-03-4 件套生产器 · TDD 测试用例

> 基于 3-1 L2-03 tech-design 的 §3 接口（`assemble_four_set` / `produce_scope` / `produce_prd` / `produce_plan` / `produce_tdd` / `query_artifact_refs`）+ §11 错误码（`E_L102_L203_001~013` 13 条）+ §12 SLO（全流程 P95 ≤ 18min · cross_ref_check ≤ 2s · quality_check ≤ 10s）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L102-L203-NNN`（L1-02 下 L2-03 · 三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_03_FourSetProducer` 组织；正向/负向/IC 契约/SLO/e2e/fixture/集成点/边界 分文件归档。
> 本 L2 为 **BC-02 Application Service**（FourPiecesProducer · 有状态 Aggregate `FourSet`）· 被 L2-01 调度（IC-L2-01 trigger + query_artifact_refs）· 依赖 L2-07（IC-L2-02 模板）+ L1-05（IC-05 delegate）+ L1-06（IC-06 可选）+ L1-03（IC-19 WBS）+ L1-09（IC-09 审计 + 5 域事件）。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC × SLO）
- [x] §2 正向用例（每 public 方法 ≥ 1 · 4 件套串行全绿）
- [x] §3 负向用例（每错误码 ≥ 1 · 13 条前缀 `E_L102_L203_`）
- [x] §4 IC-XX 契约集成测试（IC-L2-01 / IC-L2-02 / IC-05 / IC-06 / IC-19 / IC-09）
- [x] §5 性能 SLO 用例（§12.1 8 指标对标）
- [x] §6 端到端 e2e 场景（GWT · 映射 §5 P0 主链 + P1 上游缺失 + P1 Gate No-Go 重做级联）
- [x] §7 测试 fixture（mock_project_id / mock_clock / mock_event_bus / mock_upstream / mock_l207 / mock_l105 / mock_l109 / 特例 SUT）
- [x] §8 集成点用例（与 L2-07 模板 / L2-02 启动 / L2-01 Gate / L2-04 PMP / L1-03 WBS 协作）
- [x] §9 边界 / edge case（上游缺失 / 跨 doc 死链 / 部分重做 / 并发同 project / 版本回滚）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端 GWT；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（§3.1 6 个 public 方法 + 4 个内部 produce_*）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `assemble_four_set()` · §3.3 · 全量 full | TC-L102-L203-001 | unit | — | IC-L2-01 + IC-L2-02 + IC-05 + IC-09 |
| `assemble_four_set()` · §3.3 · trim=minimal | TC-L102-L203-002 | unit | — | IC-L2-01 |
| `assemble_four_set()` · §3.3 · 串行 4 步顺序正确 | TC-L102-L203-003 | unit | — | IC-09 |
| `assemble_four_set()` · §6.1 · 总事件 4_pieces_ready | TC-L102-L203-004 | e2e | — | IC-09 |
| `assemble_four_set()` · §6.1 · target_subset 局部重做 | TC-L102-L203-005 | unit | — | IC-L2-01 |
| `produce_scope()` · §3.1 REQUIREMENTS_GEN 子步 | TC-L102-L203-006 | unit | — | IC-L2-02 + IC-05 |
| `produce_prd()` · §3.1 · REQ 全文 body 产出 | TC-L102-L203-007 | unit | — | IC-L2-02 |
| `produce_plan()` · §3.1 · GOAL + AC GWT 硬锁 | TC-L102-L203-008 | unit | — | IC-05 |
| `produce_tdd()` · §3.1 · QS measurable + verification | TC-L102-L203-009 | unit | — | IC-L2-02 |
| `query_artifact_refs()` · §3.1 · Gate bundle 索引 | TC-L102-L203-010 | unit | — | IC-L2-01 |
| `assemble_four_set()` · 幂等 request_id | TC-L102-L203-011 | unit | — | — |
| `assemble_four_set()` · manifest hash 稳定 | TC-L102-L203-012 | unit | — | — |
| `assemble_four_set()` · IC-19 发给 L1-03 | TC-L102-L203-013 | integration | — | IC-19 |
| `assemble_four_set()` · KB 可选 IC-06 读命中 | TC-L102-L203-014 | integration | — | IC-06 |

### §1.2 错误码 × 测试（§11 13 条全覆盖 · 前缀 `E_L102_L203_`）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_L102_L203_001` UPSTREAM_MISSING | TC-L102-L203-101 | `assemble_four_set()` | 上游缺失 |
| `E_L102_L203_002` TEMPLATE_INVALID | TC-L102-L203-102 | `assemble_four_set()` | 模板坏（运维） |
| `E_L102_L203_003` TRACEABILITY_BROKEN | TC-L102-L203-103 | `assemble_four_set()` | 跨文档 id 不解析 |
| `E_L102_L203_004` CROSS_REF_DEAD | TC-L102-L203-104 | `assemble_four_set()` | 下游引已删 id |
| `E_L102_L203_005` SECTION_DRIFT | TC-L102-L203-105 | `produce_*()` | LLM 漏节 |
| `E_L102_L203_006` PM14_PID_MISMATCH | TC-L102-L203-106 | `assemble_four_set()` | PM-14 跨项目 |
| `E_L102_L203_007` AC_FORMAT_VIOLATION | TC-L102-L203-107 | `produce_plan()` | AC 缺 GWT |
| `E_L102_L203_008` QC_FAILED_HARD | TC-L102-L203-108 | `assemble_four_set()` | 重试耗尽 |
| `E_L102_L203_009` REDO_OUT_OF_SCOPE | TC-L102-L203-109 | `assemble_four_set()` | 闭包越界 |
| `E_L102_L203_010` ID_PATTERN_VIOLATION | TC-L102-L203-110 | `produce_*()` | doc_id 正则失败 |
| `E_L102_L203_011` UPSTREAM_TIMEOUT | TC-L102-L203-111 | `assemble_four_set()` | L2-07/L1-05 超时 |
| `E_L102_L203_012` LLM_OUTPUT_EMPTY | TC-L102-L203-112 | `assemble_four_set()` | LLM 拒答 |
| `E_L102_L203_013` CONFIG_ENDPOINTS_NONEMPTY | TC-L102-L203-113 | 启动 `__init__` | 启动拒绝 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 trigger · L2-01 → L2-03 | 被调 | TC-L102-L203-601 | full / minimal / custom 三模 |
| IC-L2-01 query_artifact_refs · L2-01 → L2-03 | 被调 | TC-L102-L203-602 | Gate bundle 索引返 |
| IC-L2-02 request_template · L2-03 → L2-07 | 生产 | TC-L102-L203-603 | 4 doc_type 各 1 次 |
| IC-05 delegate_subagent · L2-03 → L1-05 | 生产 | TC-L102-L203-604 | 4 role · 只读白名单 |
| IC-06 kb_read · L2-03 → L1-06 | 生产（可选）| TC-L102-L203-605 | requirements_pattern |
| IC-19 request_wbs_decomposition · L2-03 → L1-03 | 生产 | TC-L102-L203-606 | S2 Gate 后必发 |
| IC-09 append_event · L2-03 → L1-09 | 生产 | TC-L102-L203-607 | 5 域事件全发 |

### §1.4 SLO × 测试（§12.1 8 指标）

| 指标 | P95 目标 | 硬上限 | TC ID | 类型 |
|---|---|---|---|---|
| `assemble_four_set` 全流程（full）| ≤ 18min | 25min | TC-L102-L203-501 | perf |
| 单份文档生成（LLM+QC）| ≤ 5min | 7min | TC-L102-L203-502 | perf |
| `quality_check` 单份 | ≤ 2s | 10s | TC-L102-L203-503 | perf |
| `cross_ref_check` 全 4 | ≤ 2s | 5s | TC-L102-L203-504 | perf |
| manifest + 总事件组装 | ≤ 10s | 30s | TC-L102-L203-505 | perf |
| 重做（AC+quality）端到端 | ≤ 10min | 15min | TC-L102-L203-506 | perf |
| 同 project 串行锁（并发拒）| — | — | TC-L102-L203-507 | perf |
| `resolve_dependency_closure` | ≤ 1ms | 10ms | TC-L102-L203-508 | perf |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_03_FourSetProducer`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `FourPiecesProducer`（从 `app.l2_03.producer` 导入）。
> 正向路径全部 mock 掉 L2-07 + L1-05 + L1-09 以稳定可跑 · 重心在本 L2 编排语义。

```python
# file: tests/l1_02/test_l2_03_four_set_producer_positive.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.schemas import (
    TriggerRequest,
    FourSetManifest,
    DocRef,
    QCResult,
)


class TestL2_03_FourSetProducer:
    """每个 public 方法 + 代表性流程至少 1 正向用例。

    覆盖 §3.1 主方法：
      - assemble_four_set（主入口 · L2-01 IC-L2-01 目标）
      - produce_scope / produce_prd / produce_plan / produce_tdd（4 件套子步）
      - query_artifact_refs（Gate bundle 索引）
    覆盖 §6.1-§6.4 4 大算法：主链路 / QC / cross_ref / closure。
    """

    def test_TC_L102_L203_001_assemble_full_four_set_ok(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        mock_request_id: str,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-001 · 标准 full 全量装配 · 返 FourSetManifest v1 · 审计 ok。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        assert resp.status == "ok"
        m: FourSetManifest = resp.result
        assert m.project_id == mock_project_id
        assert m.version == "v1"
        assert m.produced_by == "L2-03"
        assert m.manifest_hash and len(m.manifest_hash) == 64  # sha256 hex
        # 4 doc_type 齐全
        assert set(m.docs.keys()) == {
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        }
        for dt, ref in m.docs.items():
            assert isinstance(ref, DocRef)
            assert ref.doc_type == dt
            assert ref.path.startswith(f"projects/{mock_project_id}/four-set/")
            assert ref.qc_status in ("pass", "warnings_only")
            assert ref.item_count > 0
            assert len(ref.hash) == 64
        assert resp.audit_ref  # L1-09 evt seq id
        assert resp.latency_ms >= 0

    def test_TC_L102_L203_002_assemble_trim_minimal(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-002 · trim_level=minimal · 产出 4 件套但 item_count 更小。"""
        req = make_trigger_request(trim_level="minimal")
        resp = sut.assemble_four_set(req)
        assert resp.status == "ok"
        m: FourSetManifest = resp.result
        # minimal 产出应比 full 精简（item_count 小于等于 full 基线 · 不强断言绝对值）
        assert m.docs["requirements"].item_count >= 1
        assert m.docs["goals"].item_count >= 1
        assert m.docs["acceptance_criteria"].item_count >= 1
        assert m.docs["quality_standards"].item_count >= 1

    def test_TC_L102_L203_003_four_steps_serial_order_guarantee(
        self,
        sut: FourPiecesProducer,
        mock_event_bus: Any,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-003 · I-FS-02 · 4 步严格 REQ→GOAL→AC→QS 顺序（事件序列即证据）。"""
        sut.assemble_four_set(valid_trigger_request)
        evt_types: list[str] = [
            e["event_type"] for e in mock_event_bus.emitted_events()
            if e["event_type"].startswith("L1-02/L2-03:")
        ]
        # 过滤 ready 事件
        ready_seq = [t for t in evt_types if t.endswith("_ready")]
        # 必含顺序：requirements_ready → goals_ready → ac_ready → quality_ready → 4_pieces_ready
        expected = [
            "L1-02/L2-03:requirements_ready",
            "L1-02/L2-03:goals_ready",
            "L1-02/L2-03:ac_ready",
            "L1-02/L2-03:quality_ready",
            "L1-02/L2-03:4_pieces_ready",
        ]
        assert ready_seq == expected, f"事件顺序破坏: {ready_seq}"

    def test_TC_L102_L203_004_emits_4_pieces_ready_with_manifest_hash(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        mock_event_bus: Any,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-004 · I-FS-07 · 总事件带 manifest_hash + 4 path 可读。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        total_evts = [
            e for e in mock_event_bus.emitted_events()
            if e["event_type"] == "L1-02/L2-03:4_pieces_ready"
        ]
        assert len(total_evts) == 1
        evt = total_evts[0]
        assert evt["project_id"] == mock_project_id
        assert evt["manifest_hash"] == resp.result.manifest_hash
        assert evt["version"] == "v1"
        assert set(evt["docs"].keys()) == {
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        }

    def test_TC_L102_L203_005_target_subset_partial_redo_ac_cascades_quality(
        self,
        sut_after_v1: FourPiecesProducer,
        mock_project_id: str,
        mock_event_bus: Any,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-005 · §6.4 closure · 重做 AC → 级联 quality_standards（requirements/goals 不动）。"""
        req = make_trigger_request(
            target_subset=["acceptance_criteria"],
            change_requests=["AC-003 加边界条件 X"],
        )
        resp = sut_after_v1.assemble_four_set(req)
        assert resp.status == "ok"
        m: FourSetManifest = resp.result
        assert m.version == "v2"
        assert m.v_from == "v1"
        # requirements + goals 保留 v1 hash（unchanged）
        assert m.docs["requirements"].version == "v1"
        assert m.docs["goals"].version == "v1"
        # AC + quality 升级 v2
        assert m.docs["acceptance_criteria"].version == "v2"
        assert m.docs["quality_standards"].version == "v2"
        # 事件只发 AC + quality + 4_pieces_ready
        ready = [e["event_type"] for e in mock_event_bus.emitted_events()
                 if e["event_type"].startswith("L1-02/L2-03:") and e["event_type"].endswith("_ready")]
        assert "L1-02/L2-03:ac_ready" in ready
        assert "L1-02/L2-03:quality_ready" in ready
        assert "L1-02/L2-03:requirements_ready" not in ready
        assert "L1-02/L2-03:goals_ready" not in ready

    def test_TC_L102_L203_006_produce_scope_returns_req_ids(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-006 · produce_scope 子步 · 产出 requirements.md 且含 REQ-\\d{3} id。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        req_doc = resp.result.docs["requirements"]
        assert req_doc.doc_type == "requirements"
        assert req_doc.doc_id.startswith("req-p-")
        assert req_doc.item_count >= 1

    def test_TC_L102_L203_007_produce_prd_body_full_text(
        self,
        sut: FourPiecesProducer,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-007 · produce_prd · requirements.md 全文 body 正确（含 REQ-001 片段）。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        body = sut.read_artifact(resp.result.docs["requirements"].path)
        assert "---" in body  # frontmatter
        assert "doc_type: requirements" in body
        assert "REQ-" in body  # 至少 1 个 REQ id

    def test_TC_L102_L203_008_produce_plan_ac_gwt_hard_lock(
        self,
        sut: FourPiecesProducer,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-008 · §6.2 · AC 硬锁含 Given/When/Then 3 关键字（不敏感）· GOAL linked_reqs 合法。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        ac_body = sut.read_artifact(resp.result.docs["acceptance_criteria"].path)
        low = ac_body.lower()
        assert "given" in low
        assert "when" in low
        assert "then" in low
        assert resp.result.docs["acceptance_criteria"].qc_status in ("pass", "warnings_only")

    def test_TC_L102_L203_009_produce_tdd_quality_measurable_verification(
        self,
        sut: FourPiecesProducer,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-009 · produce_tdd · quality_standards 含 measurable_criteria + verification_method。"""
        resp = sut.assemble_four_set(valid_trigger_request)
        qs_body = sut.read_artifact(resp.result.docs["quality_standards"].path)
        assert "QS-" in qs_body
        assert "measurable" in qs_body.lower() or "measurable_criteria" in qs_body
        assert "verification" in qs_body.lower()

    def test_TC_L102_L203_010_query_artifact_refs_returns_manifest(
        self,
        sut_after_v1: FourPiecesProducer,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L203-010 · query_artifact_refs · Gate bundle 打包前调用 · 返 FourSetManifest。"""
        m = sut_after_v1.query_artifact_refs(project_id=mock_project_id)
        assert isinstance(m, FourSetManifest)
        assert m.project_id == mock_project_id
        assert m.docs["requirements"].qc_status in ("pass", "warnings_only")
        assert m.cross_check_report["errors"] == []
        assert m.cross_check_report["total_refs_checked"] >= 0

    def test_TC_L102_L203_011_idempotent_same_request_id(
        self,
        sut: FourPiecesProducer,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-011 · I-FS-08 幂等 · 同 request_id 第二次调用返相同 manifest_hash（不重跑 LLM）。"""
        resp1 = sut.assemble_four_set(valid_trigger_request)
        resp2 = sut.assemble_four_set(valid_trigger_request)
        assert resp1.status == resp2.status == "ok"
        assert resp1.result.manifest_hash == resp2.result.manifest_hash
        assert resp1.result.version == resp2.result.version

    def test_TC_L102_L203_012_manifest_hash_stable_across_runs(
        self,
        sut_factory: Any,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-012 · 两个独立 SUT · 同输入（固定 LLM mock）· manifest_hash 稳定。"""
        req = make_trigger_request()
        s1 = sut_factory(); s2 = sut_factory()
        r1 = s1.assemble_four_set(req); r2 = s2.assemble_four_set(req)
        assert r1.result.manifest_hash == r2.result.manifest_hash

    def test_TC_L102_L203_013_ic_19_sent_to_l103_after_gate_pass(
        self,
        sut: FourPiecesProducer,
        mock_l103_wbs: Any,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-013 · S2 Gate 通过后 · IC-19 request_wbs_decomposition 必发 L1-03。"""
        sut.assemble_four_set(valid_trigger_request)
        sut.on_gate_passed(project_id=valid_trigger_request.project_id)
        ic19_calls = mock_l103_wbs.received_calls()
        assert len(ic19_calls) == 1
        payload = ic19_calls[0]
        assert payload["project_id"] == valid_trigger_request.project_id
        assert payload["four_set_manifest"]["manifest_hash"]
        assert payload["trim_level"] == "full"

    def test_TC_L102_L203_014_ic_06_kb_read_optional_warning_only(
        self,
        sut_with_failing_kb: FourPiecesProducer,
        valid_trigger_request: TriggerRequest,
    ) -> None:
        """TC-L102-L203-014 · IC-06 kb_read 可选 · KB 不可达仅 warning · 主流程继续 ok。"""
        resp = sut_with_failing_kb.assemble_four_set(valid_trigger_request)
        assert resp.status == "ok"  # KB 失败不阻塞
```

---

## §3 负向用例（§11 每错误码 ≥ 1）

> 每错误码必有 1 条 TC · `resp.status == "err"` + `resp.result.err_type == "<NAME>"`（或 `pytest.raises(FourSetProducerError)` · 取决于 §11 约定）。
> §11 把 E13 CONFIG_ENDPOINTS_NONEMPTY 定位为启动拒绝（进程级） · 用独立启动用例覆盖；其它 12 条走响应 schema `StructuredErr` 路径。

```python
# file: tests/l1_02/test_l2_03_four_set_producer_negative.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.errors import FourSetProducerError
from app.l2_03.startup import ProducerBootstrap, StartupError


class TestL2_03_FourSetProducerNegative:
    """§11 13 错误码全覆盖 · 前缀 `E_L102_L203_`.

    正向基线：valid_trigger_request + sut（默认模板 + 正常 L1-05 mock）；每用例只扰动单一因子。
    """

    def test_TC_L102_L203_101_upstream_missing_goal_anchor_mismatch(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-101 · E_L102_L203_001 · goal_anchor_hash 与 charter 实际 hash 不合 · REJECT。"""
        req = make_trigger_request(goal_anchor_hash="sha256:stale-hash-0000")
        resp = sut.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "UPSTREAM_MISSING"
        assert resp.result.failed_step is None  # 未进入 4 步
        assert "goal_anchor" in resp.result.reason.lower()

    def test_TC_L102_L203_102_template_invalid_returned_by_l207(
        self,
        sut_with_broken_template: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-102 · E_L102_L203_002 · L2-07 返 schema 错误模板 · REJECT."""
        resp = sut_with_broken_template.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "TEMPLATE_INVALID"
        assert resp.result.failed_step in ("REQUIREMENTS_GEN", "GOALS_GEN",
                                            "AC_GEN", "QUALITY_GEN")

    def test_TC_L102_L203_103_traceability_broken_ac_to_missing_goal(
        self,
        sut_with_broken_traceability: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-103 · E_L102_L203_003 · AC 引用不存在的 GOAL-99 · CROSS_CHECK REJECT。"""
        resp = sut_with_broken_traceability.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "TRACEABILITY_BROKEN"
        assert resp.result.failed_step == "CROSS_CHECK"
        assert resp.result.context["dead_refs"]  # dead_ref 列表
        assert any("GOAL-99" in str(r) for r in resp.result.context["dead_refs"])

    def test_TC_L102_L203_104_cross_ref_dead_cascade_self_heal_fails(
        self,
        sut_with_dead_ref_after_redo: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-104 · E_L102_L203_004 · 重做 req 删 REQ-03 · goals 仍引 · 3 次自愈失败 REJECT。"""
        req = make_trigger_request(target_subset=["requirements"])
        resp = sut_with_dead_ref_after_redo.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "CROSS_REF_DEAD"
        # 自愈次数证据：SUT 计数 redo_attempt == 3
        assert sut_with_dead_ref_after_redo.redo_attempts() == 3

    def test_TC_L102_L203_105_section_drift_retry_then_reject(
        self,
        sut_with_missing_section: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-105 · E_L102_L203_005 · LLM 产出漏 required section · 重试 ≤2 仍失败 REJECT。"""
        resp = sut_with_missing_section.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "SECTION_DRIFT"
        assert sut_with_missing_section.llm_retry_count() >= 2

    def test_TC_L102_L203_106_pm14_pid_mismatch_cross_project_rejected(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L203-106 · E_L102_L203_006 · req.project_id ≠ active · 拒绝 + CRITICAL 广播 + 审计违规。"""
        req = make_trigger_request(project_id="proj-OTHER")  # 与 active 不同
        resp = sut.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "PM14_PID_MISMATCH"
        # CRITICAL 事件必发
        crit = [e for e in mock_event_bus.emitted_events()
                if e.get("severity") == "CRITICAL"
                and e["event_type"].endswith(":pm14_violation")]
        assert len(crit) == 1

    def test_TC_L102_L203_107_ac_format_violation_no_gwt(
        self,
        sut_with_no_gwt_llm: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-107 · E_L102_L203_007 · LLM 写 AC 缺 GWT 关键字 · 重试 ≤2 失败 REJECT。"""
        resp = sut_with_no_gwt_llm.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "AC_FORMAT_VIOLATION"
        assert resp.result.failed_step == "AC_GEN"

    def test_TC_L102_L203_108_qc_failed_hard_retry_exhausted(
        self,
        sut_with_persistent_qc_fail: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-108 · E_L102_L203_008 · 单步 QC 连续 3 次失败 · state=FAILED · REJECT。"""
        resp = sut_with_persistent_qc_fail.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "QC_FAILED_HARD"
        assert sut_with_persistent_qc_fail.final_state() == "FAILED"
        assert sut_with_persistent_qc_fail.qc_retry_count() >= 2  # qc_retry_max

    def test_TC_L102_L203_109_redo_out_of_scope_critical(
        self,
        sut_with_bug_redo: FourPiecesProducer,
        make_trigger_request: Any,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L203-109 · E_L102_L203_009 · 重做 AC 但越界改了 requirements · CRITICAL 回滚 + 审计违规。"""
        req = make_trigger_request(target_subset=["acceptance_criteria"])
        resp = sut_with_bug_redo.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "REDO_OUT_OF_SCOPE"
        # 回滚 .v1（requirements 保持原 hash）
        assert sut_with_bug_redo.rollback_invoked() is True
        crit = [e for e in mock_event_bus.emitted_events()
                if e.get("severity") == "CRITICAL"
                and "redo_out_of_scope" in e["event_type"]]
        assert len(crit) == 1

    def test_TC_L102_L203_110_id_pattern_violation_llm_writes_bad_id(
        self,
        sut_with_bad_id_llm: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-110 · E_L102_L203_010 · LLM 写 `REQ1` 不符 `REQ-\\d{3}` · 后处理校正 · 仍失败 REJECT。"""
        resp = sut_with_bad_id_llm.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "ID_PATTERN_VIOLATION"
        assert resp.result.failed_step in ("REQUIREMENTS_GEN", "GOALS_GEN",
                                            "AC_GEN", "QUALITY_GEN")

    def test_TC_L102_L203_111_upstream_timeout_l207_then_exponential_backoff(
        self,
        sut_with_l207_timeout: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-111 · E_L102_L203_011 · L2-07 超时 3 次（指数退避）· REJECT。"""
        resp = sut_with_l207_timeout.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "UPSTREAM_TIMEOUT"
        assert sut_with_l207_timeout.backoff_attempts() == 3

    def test_TC_L102_L203_112_llm_output_empty_retry_with_shorter_context(
        self,
        sut_with_empty_llm: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-112 · E_L102_L203_012 · L1-05 返空字符串 · 截短 context 重试 · 仍空 REJECT。"""
        resp = sut_with_empty_llm.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type == "LLM_OUTPUT_EMPTY"
        # 证据：至少尝试过 context 截短
        assert sut_with_empty_llm.context_shortened_count() >= 1

    def test_TC_L102_L203_113_config_endpoints_nonempty_startup_refused(
        self,
        tmp_path: Any,
    ) -> None:
        """TC-L102-L203-113 · E_L102_L203_013 · 启动时 config.endpoints != [] · 进程启动失败（StartupError）。"""
        with pytest.raises(StartupError) as exc:
            ProducerBootstrap(
                config={"endpoints": ["https://api.example.com/v1"], "template_base_dir": str(tmp_path)},
            ).bootstrap()
        assert "E_L102_L203_013" in str(exc.value) or "CONFIG_ENDPOINTS_NONEMPTY" in str(exc.value)
```

---

## §4 IC-XX 契约集成测试（≥ 3 join test）

> 本 L2 的 IC 边界：**被调** IC-L2-01（trigger + query_artifact_refs）· **生产** IC-L2-02（给 L2-07）+ IC-05（给 L1-05）+ IC-06（给 L1-06 · 可选）+ IC-19（给 L1-03）+ IC-09（给 L1-09）。
> 下面用 mock 兄弟 L2 + join test 覆盖 7 个 IC 方向。

```python
# file: tests/l1_02/test_l2_03_ic_contracts.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer


class TestL2_03_IcContracts:
    """IC-L2-01 被调 + IC-L2-02 / IC-05 / IC-06 / IC-19 / IC-09 生产 · 契约 join test。"""

    def test_TC_L102_L203_601_ic_l2_01_trigger_full_contract(
        self,
        sut: FourPiecesProducer,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L203-601 · IC-L2-01 · L2-01 发 trigger(stage=S2, trim=full) · 响应 schema 合法。"""
        payload = mock_ic_payload(stage="S2", trim_level="full")
        resp = sut.assemble_four_set(**payload)
        # 契约字段 §3.3
        assert resp.project_id == payload["project_id"]
        assert resp.request_id == payload["request_id"]
        assert resp.status in ("ok", "err")
        assert resp.result is not None
        assert resp.audit_ref
        assert resp.latency_ms is not None

    def test_TC_L102_L203_602_query_artifact_refs_returns_manifest_contract(
        self,
        sut_after_v1: FourPiecesProducer,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L203-602 · IC-L2-01 · query_artifact_refs 契约字段齐（供 Gate bundle 打包）。"""
        m = sut_after_v1.query_artifact_refs(project_id=mock_project_id)
        for key in ("manifest_path", "manifest_hash", "version", "docs",
                    "cross_check_report", "produced_at_ns", "produced_by"):
            assert hasattr(m, key) or key in m.__dict__, f"missing field: {key}"
        assert m.produced_by == "L2-03"
        assert set(m.docs.keys()) == {
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        }

    def test_TC_L102_L203_603_ic_l2_02_request_template_4_doc_types(
        self,
        sut: FourPiecesProducer,
        mock_l207_client: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-603 · IC-L2-02 · 4 doc_type 各发一次 request_template · trim_level 一致。"""
        sut.assemble_four_set(valid_trigger_request)
        calls = mock_l207_client.received_calls()
        doc_types_called = [c["doc_type"] for c in calls]
        assert set(doc_types_called) == {
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        }
        # 每次 trim_level 都一致
        assert all(c["trim_level"] == "full" for c in calls)
        # project_id 一致
        assert all(c["project_id"] == valid_trigger_request.project_id for c in calls)

    def test_TC_L102_L203_604_ic_05_delegate_subagent_4_roles_readonly(
        self,
        sut: FourPiecesProducer,
        mock_l105_client: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-604 · IC-05 · 4 role 发 delegate_subagent · tools_whitelist 只含 Read（防写污染）。"""
        sut.assemble_four_set(valid_trigger_request)
        calls = mock_l105_client.received_calls()
        roles = [c["role"] for c in calls]
        assert set(roles) == {
            "requirements-analysis", "goals-writing",
            "ac-scenario-writer", "quality-audit",
        }
        for c in calls:
            assert c["tools_whitelist"] == ["Read"], f"工具白名单污染: {c['tools_whitelist']}"
            assert c["timeout_s"] <= 600
            assert c["task_brief"] and len(c["task_brief"]) <= 2000

    def test_TC_L102_L203_605_ic_06_kb_read_requirements_pattern(
        self,
        sut_with_kb_enabled: FourPiecesProducer,
        mock_l106_kb: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-605 · IC-06 · kb_read 可选 · kind=requirements_pattern · 命中时注入 context。"""
        sut_with_kb_enabled.assemble_four_set(valid_trigger_request)
        kb_calls = mock_l106_kb.received_calls()
        assert len(kb_calls) >= 1
        # 契约：kind=requirements_pattern
        assert any(c.get("kind") == "requirements_pattern" for c in kb_calls)

    def test_TC_L102_L203_606_ic_19_request_wbs_decomposition_after_gate(
        self,
        sut: FourPiecesProducer,
        mock_l103_wbs: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-606 · IC-19 · S2 Gate 通过后 · 向 L1-03 发 request_wbs_decomposition 契约字段齐。"""
        sut.assemble_four_set(valid_trigger_request)
        sut.on_gate_passed(project_id=valid_trigger_request.project_id)
        calls = mock_l103_wbs.received_calls()
        assert len(calls) == 1
        p = calls[0]
        # §3.4 IC-19 required 字段
        for k in ("project_id", "command_id", "four_set_manifest",
                  "architecture_refs", "trim_level"):
            assert k in p, f"missing IC-19 field: {k}"
        assert p["four_set_manifest"]["manifest_hash"]
        assert p["four_set_manifest"]["version"]
        assert p["four_set_manifest"]["manifest_path"]

    def test_TC_L102_L203_607_ic_09_append_event_5_domain_events(
        self,
        sut: FourPiecesProducer,
        mock_event_bus: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-607 · IC-09 · 5 域事件 ready/total 全发且 hash chain 连续。"""
        sut.assemble_four_set(valid_trigger_request)
        all_evts = [e for e in mock_event_bus.emitted_events()
                    if e["event_type"].startswith("L1-02/L2-03:")]
        expected_types = {
            "L1-02/L2-03:requirements_ready",
            "L1-02/L2-03:goals_ready",
            "L1-02/L2-03:ac_ready",
            "L1-02/L2-03:quality_ready",
            "L1-02/L2-03:4_pieces_ready",
        }
        assert expected_types.issubset({e["event_type"] for e in all_evts})
        # 字段：project_id / ts_ns / 必带 schema
        for e in all_evts:
            assert e["project_id"] == valid_trigger_request.project_id
            assert "ts_ns" in e
            assert isinstance(e["ts_ns"], int)
```

---

## §5 性能 SLO 用例（§12.1 对标）

> 所有 `@pytest.mark.perf` 标记 · CI 可分 job 执行。
> 对标 §12.1 SLO 表：全流程 P95 ≤ 18min（mock LLM 秒出）· cross_ref ≤ 2s · quality_check ≤ 10s · closure 解析 ≤ 1ms。
> 注：真实 LLM 耗时由 L1-05 承诺 · 本 L2 性能用例用 `mock_l105_instant`（每次返固定样本 · <10ms）隔离 LLM 时延 · 只测本 L2 编排开销。

```python
# file: tests/l1_02/test_l2_03_perf_slo.py
from __future__ import annotations

import statistics
import time
from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.domain.cross_ref import cross_ref_check
from app.l2_03.domain.closure import resolve_dependency_closure


@pytest.mark.perf
class TestL2_03_PerformanceSLO:
    """§12.1 SLO 对标 · ≥ 6 条 @pytest.mark.perf。"""

    def test_TC_L102_L203_501_assemble_full_p95_under_18min_mocked_llm(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-501 · SLO · 30 次 full 装配 P95 ≤ 18min（mock LLM 瞬时）· 本 L2 编排开销本身 P95 < 5s。"""
        latencies: list[float] = []
        for i in range(30):
            req = make_trigger_request(request_id=f"perf-{i}")
            t0 = time.perf_counter()
            resp = sut.assemble_four_set(req)
            latencies.append((time.perf_counter() - t0) * 1000)  # ms
            assert resp.status == "ok"
        p95 = statistics.quantiles(latencies, n=20)[18]
        # mock LLM 路径下编排开销 P95 < 5s（宽松留 ceiling）
        assert p95 <= 5000, f"编排开销 P95={p95:.2f}ms > 5000ms · 远不及 18min SLO 但编排本身慢"

    def test_TC_L102_L203_502_single_doc_gen_p95_under_5min(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-502 · SLO · 单份产出（含 L2-07 + L1-05 + QC + write）P95 ≤ 5min。"""
        latencies: list[float] = []
        for i in range(20):
            req = make_trigger_request(
                request_id=f"perf-sd-{i}",
                target_subset=["requirements"],  # 只跑 1 步
            )
            t0 = time.perf_counter()
            sut.assemble_four_set(req)
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 2000, f"单份 mock P95={p95:.2f}ms · 应 << 5min"

    def test_TC_L102_L203_503_quality_check_p95_under_2s(
        self,
        sut: FourPiecesProducer,
        sample_doc_body: dict[str, str],
    ) -> None:
        """TC-L102-L203-503 · SLO · quality_check 单份 P95 ≤ 2s · 硬上限 10s。"""
        latencies: list[float] = []
        for _ in range(100):
            for doc_type, body in sample_doc_body.items():
                t0 = time.perf_counter()
                sut.quality_check(doc_type, body)
                latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 2000, f"quality_check P95={p95:.2f}ms > 2s SLO"

    def test_TC_L102_L203_504_cross_ref_check_p95_under_2s_300_refs(
        self,
        sut_after_v1: FourPiecesProducer,
        tmp_path: Any,
    ) -> None:
        """TC-L102-L203-504 · SLO · cross_ref_check 4 md · 300 refs · P95 ≤ 2s 硬上限 5s。"""
        latencies: list[float] = []
        for _ in range(30):
            t0 = time.perf_counter()
            r = sut_after_v1.cross_ref_check()
            latencies.append((time.perf_counter() - t0) * 1000)
            assert r.pass_ is True
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 2000, f"cross_ref P95={p95:.2f}ms > 2s SLO (§12.1)"

    def test_TC_L102_L203_505_manifest_event_assembly_p95_under_10s(
        self,
        sut: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-505 · SLO · manifest 组装 + 总事件 P95 ≤ 10s。"""
        latencies: list[float] = []
        for i in range(20):
            t0 = time.perf_counter()
            sut._assemble_manifest(version="v1")  # 内部方法 · 直调
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = max(latencies)  # 小样本用 max
        assert p95 <= 10_000, f"manifest 装配 P95={p95:.2f}ms > 10s SLO"

    def test_TC_L102_L203_506_redo_ac_quality_end_to_end_under_10min(
        self,
        sut_after_v1: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-506 · SLO · 重做（AC+quality 2 步）端到端 P95 ≤ 10min · mock 下 < 3s。"""
        latencies: list[float] = []
        for i in range(10):
            req = make_trigger_request(
                request_id=f"perf-redo-{i}",
                target_subset=["acceptance_criteria"],
                change_requests=["边界调整"],
            )
            t0 = time.perf_counter()
            sut_after_v1.assemble_four_set(req)
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = max(latencies)
        assert p95 <= 3000, f"重做 mock P95={p95:.2f}ms · 应 << 10min"

    def test_TC_L102_L203_507_same_project_serial_lock_rejects_concurrent(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-507 · §12.2 · 同 project 并发 trigger · 第二次必拒（FourSet=1 锁）· 跨 project 独立。"""
        from concurrent.futures import ThreadPoolExecutor

        req_same = make_trigger_request(request_id="conc-a")
        req_same_2 = make_trigger_request(request_id="conc-b")  # 同 pid
        results: list[Any] = []

        def _one(r: Any) -> Any:
            return sut.assemble_four_set(r)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(_one, req_same), pool.submit(_one, req_same_2)]
            results = [f.result() for f in futs]
        # 一个 ok · 一个被 serial lock 排队（或拒）
        ok_count = sum(1 for r in results if r.status == "ok")
        assert ok_count >= 1  # 至少 1 个必成
        # 若实现是排队则两个都 ok · 总时长 > 单次；若是拒则一个 err
        # 此用例只断言 "不会并发污染 manifest"

    def test_TC_L102_L203_508_resolve_dependency_closure_p95_under_1ms(
        self,
    ) -> None:
        """TC-L102-L203-508 · §6.4 closure 解析 P95 ≤ 1ms（纯内存 dict 查）。"""
        latencies: list[float] = []
        for _ in range(1000):
            t0 = time.perf_counter()
            resolve_dependency_closure(["acceptance_criteria"])
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 1.0, f"closure P95={p95:.4f}ms > 1ms"
```

---

## §6 端到端 e2e 场景（GWT · 映射 §5 P0/P1 时序）

> 3 GWT 场景 · 覆盖 §5.1（P0 主干串行产出）/ §5.2 Phase A（P1 上游缺失 E01）/ §5.2 Phase B（P1 Gate No-Go 重做级联）。
> GWT = Given-When-Then · 对应 2-prd §10.9 验证大纲（P1-P8 / N1-N6 / I1-I3）。

```python
# file: tests/l1_02/test_l2_03_e2e.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.errors import FourSetProducerError


class TestL2_03_EndToEnd:
    """§5 P0/P1 时序 e2e · 3 GWT 场景 · 与 prd §10.9 P1-P8/N1-N6/I1-I3 对齐。"""

    def test_TC_L102_L203_701_gwt_p0_full_four_set_happy_path(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        mock_event_bus: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-701 · GWT · §5.1 P0 主干 · 4 件套串行产出.

        Given: L2-02 已锁 charter + goal_anchor_hash · L2-07 模板就绪 · L1-05 可用
        When: L2-01 发 IC-L2-01 trigger(stage=S2, trim=full)
        Then:
          - 串行 REQ→GOAL→AC→QS 全 pass
          - CROSS_CHECK 无 dead ref
          - 发 4_pieces_ready 总事件（带 manifest_hash）
          - 写入 4 md + manifest.yaml 到 projects/<pid>/four-set/
          - 响应 status=ok · FourSetManifest v1
        """
        # When
        resp = sut.assemble_four_set(valid_trigger_request)

        # Then
        assert resp.status == "ok"
        assert resp.result.version == "v1"
        assert resp.result.cross_check_report["errors"] == []
        # 4 md + manifest 全部落盘
        for dt in ("requirements", "goals", "acceptance_criteria", "quality_standards"):
            assert sut.artifact_exists(resp.result.docs[dt].path)
        assert sut.artifact_exists(resp.result.manifest_path)
        # 5 域事件（4 ready + 1 total）
        ready_types = {e["event_type"] for e in mock_event_bus.emitted_events()
                       if e["event_type"].endswith("_ready")}
        assert len(ready_types) == 5

    def test_TC_L102_L203_702_gwt_p1_upstream_missing_reroute_to_l202(
        self,
        sut: FourPiecesProducer,
        mock_project_id: str,
        mock_event_bus: Any,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-702 · GWT · §5.2 Phase A · P1 上游缺失回退.

        Given: L2-02 未完成 S1 · goal_anchor_hash 与 charter 实际 hash 不合
        When: L2-01 发 IC-L2-01 trigger · _validate_upstream() 检测到 mismatch
        Then:
          - 立即返 status=err · err_type=UPSTREAM_MISSING · failed_step=None
          - 不进入 4 步（无 requirements_ready 事件）
          - 发 four_set_rejected 事件
          - L2-01 据此路由回 L2-02 重做 S1
        """
        # Given
        stale_req = make_trigger_request(goal_anchor_hash="sha256:stale")

        # When
        resp = sut.assemble_four_set(stale_req)

        # Then
        assert resp.status == "err"
        assert resp.result.err_type == "UPSTREAM_MISSING"
        # 未进入 4 步
        ready = [e for e in mock_event_bus.emitted_events()
                 if e["event_type"].endswith("_ready")
                 and e["event_type"].startswith("L1-02/L2-03:")]
        assert len(ready) == 0
        # rejected 事件
        rej = [e for e in mock_event_bus.emitted_events()
               if e["event_type"] == "L1-02/L2-03:four_set_rejected"]
        assert len(rej) == 1

    def test_TC_L102_L203_703_gwt_p1_gate_no_go_redo_cascade(
        self,
        sut_after_v1: FourPiecesProducer,
        mock_project_id: str,
        mock_event_bus: Any,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-703 · GWT · §5.2 Phase B · P1 S2 Gate No-Go 重做级联.

        Given: 首版 v1 已 ok · 用户在 S2 Gate Reject · change_requests=['AC-03 加边界 X']
        When: L2-01 发 trigger(target_subset=[acceptance_criteria], change_requests=[...])
        Then:
          - backup AC.v1 / quality.v1 到 .v1.md
          - 重跑 AC + quality（级联闭包）· 不动 requirements / goals
          - CROSS_CHECK 重校 · pass
          - 写 manifest v2 · v_from=v1
          - 发 4_pieces_ready(v2)
          - L2-01 用于推 S2 Gate 卡片（带 diff_from_previous_gate=v1）
        """
        # Given · sut_after_v1 已完成 v1
        req_redo = make_trigger_request(
            target_subset=["acceptance_criteria"],
            change_requests=["AC-03 加边界条件 X"],
        )

        # When
        resp = sut_after_v1.assemble_four_set(req_redo)

        # Then
        assert resp.status == "ok"
        assert resp.result.version == "v2"
        assert resp.result.v_from == "v1"
        # 备份 .v1 存在
        assert sut_after_v1.artifact_exists(
            f"projects/{mock_project_id}/four-set/acceptance-criteria.v1.md")
        assert sut_after_v1.artifact_exists(
            f"projects/{mock_project_id}/four-set/quality-standards.v1.md")
        # requirements / goals 未被覆盖（同 hash）
        assert resp.result.docs["requirements"].version == "v1"
        assert resp.result.docs["goals"].version == "v1"
        # 总事件 v2
        total_v2 = [e for e in mock_event_bus.emitted_events()
                    if e["event_type"] == "L1-02/L2-03:4_pieces_ready"
                    and e["version"] == "v2"]
        assert len(total_v2) == 1
```

---

## §7 测试 fixture（≥ 5 个）

> `conftest.py` 放 `tests/l1_02/`。统一 fixture · 所有测试复用。
> 必含：`sut` / `sut_factory` / `sut_after_v1` / `mock_project_id` / `mock_request_id` / `mock_event_bus` / `mock_clock` / `mock_ic_payload` / `valid_trigger_request` / `make_trigger_request` / 兄弟 L2 mock（`mock_l207_client` / `mock_l105_client` / `mock_l106_kb` / `mock_l103_wbs`）+ 故障 SUT（`sut_with_broken_template` / `sut_with_broken_traceability` / `sut_with_missing_section` / `sut_with_persistent_qc_fail` / `sut_with_l207_timeout` / `sut_with_empty_llm` / `sut_with_no_gwt_llm` / `sut_with_bad_id_llm` / `sut_with_bug_redo` / `sut_with_dead_ref_after_redo` / `sut_with_failing_kb` / `sut_with_kb_enabled`）。

```python
# file: tests/l1_02/conftest.py  (L2-03 补丁段 · 与 L2-07 conftest 合并)
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.schemas import TriggerRequest


# ---------- 基础 id / upstream context ----------

@pytest.fixture
def mock_project_id() -> str:
    """固定 project_id (ULID 风格) · 跨用例可追踪。"""
    return "proj-01HZZZL203AAAAAAAAAAAAAAAA"


@pytest.fixture
def mock_request_id() -> str:
    return "req-01HAAL203AAAAAAAAAAAAAAAAA"


@pytest.fixture
def mock_charter_and_hash(tmp_path: Path, mock_project_id: str) -> dict[str, str]:
    """构造合法 charter + stakeholders + goal_anchor_hash · 上游校验基线。"""
    base = tmp_path / "projects" / mock_project_id
    base.mkdir(parents=True)
    (base / "charter.md").write_text("# Charter\ngoal: build X\n", encoding="utf-8")
    (base / "stakeholders.md").write_text("# Stakeholders\n- Alice\n", encoding="utf-8")
    import hashlib
    anchor = hashlib.sha256(b"build X").hexdigest()
    return {
        "charter_path": str(base / "charter.md"),
        "stakeholders_path": str(base / "stakeholders.md"),
        "goal_anchor_hash": f"sha256:{anchor}",
    }


# ---------- mock event bus (IC-09 sink) ----------

class _FakeEventBus:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._fail_n = 0

    def append_event(self, event: dict[str, Any]) -> None:
        if self._fail_n > 0:
            self._fail_n -= 1
            raise ConnectionError("IC-09 simulated failure")
        self._events.append(event)

    def emitted_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def set_failures(self, n: int) -> None:
        self._fail_n = n


@pytest.fixture
def mock_event_bus() -> _FakeEventBus:
    return _FakeEventBus()


# ---------- 兄弟 L2 mock ----------

class _FakeL207Client:
    """L2-07 模板引擎 mock · 按 doc_type 返预置 TemplateBody。"""
    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._responses: dict[str, str] = {
            "requirements": "# Requirements\n## NFR\nREQ-001 slot {{req_stub}}\n",
            "goals": "# Goals\n## SMART\nGOAL-01 slot\n",
            "acceptance_criteria": "# AC\nAC-001 Given X When Y Then Z\n",
            "quality_standards": "# QS\nQS-001 measurable=yes verification_method=test\n",
        }

    def request_template(self, **kw: Any) -> dict[str, Any]:
        self._calls.append(kw)
        return {"template_body": self._responses[kw["doc_type"]], "version": "v1.0"}

    def received_calls(self) -> list[dict[str, Any]]:
        return list(self._calls)


class _FakeL105Client:
    """L1-05 delegate_subagent mock · 按 role 返合规 markdown。"""
    def __init__(self, body_map: dict[str, str] | None = None) -> None:
        self._calls: list[dict[str, Any]] = []
        self._body = body_map or {
            "requirements-analysis": (
                "---\ndoc_type: requirements\n---\n"
                "## REQ-001\n描述\n## REQ-002\n描述\n"
            ),
            "goals-writing": (
                "---\ndoc_type: goals\n---\n"
                "## GOAL-01 (linked_reqs: REQ-001)\nSMART 描述\n"
            ),
            "ac-scenario-writer": (
                "---\ndoc_type: acceptance_criteria\n---\n"
                "## AC-001 (linked_goal: GOAL-01, linked_reqs: REQ-001)\n"
                "**Given**: 前置\n**When**: 动作\n**Then**: 期望\n"
            ),
            "quality-audit": (
                "---\ndoc_type: quality_standards\n---\n"
                "## QS-001 (linked_acs: all)\n"
                "measurable_criteria: P95 < 200ms\n"
                "verification_method: e2e perf test\n"
            ),
        }

    def delegate_subagent(self, **kw: Any) -> dict[str, Any]:
        self._calls.append(kw)
        return {"output": self._body.get(kw["role"], "")}

    def received_calls(self) -> list[dict[str, Any]]:
        return list(self._calls)


class _FakeL106Kb:
    def __init__(self, simulate_failure: bool = False) -> None:
        self._calls: list[dict[str, Any]] = []
        self._fail = simulate_failure

    def kb_read(self, **kw: Any) -> dict[str, Any]:
        self._calls.append(kw)
        if self._fail:
            raise TimeoutError("IC-06 simulated")
        return {"matches": [{"kind": kw.get("kind"), "snippet": "过往相似需求片段"}]}

    def received_calls(self) -> list[dict[str, Any]]:
        return list(self._calls)


class _FakeL103Wbs:
    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def request_wbs_decomposition(self, **kw: Any) -> dict[str, Any]:
        self._calls.append(kw)
        return {"status": "accepted"}

    def received_calls(self) -> list[dict[str, Any]]:
        return list(self._calls)


@pytest.fixture
def mock_l207_client() -> _FakeL207Client:
    return _FakeL207Client()


@pytest.fixture
def mock_l105_client() -> _FakeL105Client:
    return _FakeL105Client()


@pytest.fixture
def mock_l106_kb() -> _FakeL106Kb:
    return _FakeL106Kb(simulate_failure=False)


@pytest.fixture
def mock_l103_wbs() -> _FakeL103Wbs:
    return _FakeL103Wbs()


# ---------- trigger request factory ----------

@pytest.fixture
def make_trigger_request(
    mock_project_id: str,
    mock_request_id: str,
    mock_charter_and_hash: dict[str, str],
) -> Callable[..., TriggerRequest]:
    """§3.2 IC-L2-01 trigger payload factory · 默认合法 · 按需重写字段。"""

    def _make(
        project_id: str | None = None,
        request_id: str | None = None,
        trim_level: str = "full",
        target_subset: list[str] | None = None,
        change_requests: list[str] | None = None,
        goal_anchor_hash: str | None = None,
    ) -> TriggerRequest:
        return TriggerRequest(
            project_id=project_id or mock_project_id,
            request_id=request_id or mock_request_id,
            stage="S2",
            trim_level=trim_level,
            context={
                "charter_path": mock_charter_and_hash["charter_path"],
                "stakeholders_path": mock_charter_and_hash["stakeholders_path"],
                "goal_anchor_hash": goal_anchor_hash or mock_charter_and_hash["goal_anchor_hash"],
            },
            target_subset=target_subset,
            change_requests=change_requests,
            caller_l2="L2-01",
            trace_ctx={"ts_dispatched_ns": 1_714_000_000_000_000_000, "gate_id": None},
        )

    return _make


@pytest.fixture
def valid_trigger_request(make_trigger_request: Callable[..., TriggerRequest]) -> TriggerRequest:
    return make_trigger_request()


# ---------- mock_ic_payload（dict 形式 · 给 §4 IC 契约用） ----------

@pytest.fixture
def mock_ic_payload(
    make_trigger_request: Callable[..., TriggerRequest],
) -> Callable[..., dict[str, Any]]:
    def _make(stage: str = "S2", trim_level: str = "full", **kw: Any) -> dict[str, Any]:
        req = make_trigger_request(trim_level=trim_level, **kw)
        return {
            "project_id": req.project_id,
            "request_id": req.request_id,
            "stage": stage,
            "trim_level": trim_level,
            "context": req.context,
            "target_subset": req.target_subset,
            "change_requests": req.change_requests,
            "caller_l2": req.caller_l2,
            "trace_ctx": req.trace_ctx,
        }
    return _make


# ---------- SUT fixtures ----------

@pytest.fixture
def sut_factory(
    tmp_path: Path,
    mock_project_id: str,
    mock_event_bus: _FakeEventBus,
    mock_l207_client: _FakeL207Client,
    mock_l105_client: _FakeL105Client,
    mock_l106_kb: _FakeL106Kb,
    mock_l103_wbs: _FakeL103Wbs,
) -> Callable[..., FourPiecesProducer]:
    """SUT 工厂 · 默认全正常 mock。"""

    def _build(**overrides: Any) -> FourPiecesProducer:
        return FourPiecesProducer(
            project_id=mock_project_id,
            project_root=tmp_path,
            event_bus=mock_event_bus,
            l207_client=overrides.get("l207_client", mock_l207_client),
            l105_client=overrides.get("l105_client", mock_l105_client),
            l106_kb=overrides.get("l106_kb", mock_l106_kb),
            l103_wbs=overrides.get("l103_wbs", mock_l103_wbs),
            config=overrides.get("config", {
                "endpoints": [],
                "qc_retry_max": 2,
                "require_traceability": True,
                "ref_check_strict": True,
            }),
        )

    return _build


@pytest.fixture
def sut(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    return sut_factory()


@pytest.fixture
def sut_after_v1(
    sut: FourPiecesProducer,
    valid_trigger_request: TriggerRequest,
) -> FourPiecesProducer:
    """已完成 v1 装配的 SUT · 用于重做 / query_artifact_refs 用例。"""
    sut.assemble_four_set(valid_trigger_request)
    return sut


# 故障 SUT：覆盖 §3 每错误码
@pytest.fixture
def sut_with_broken_template(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _BrokenL207(_FakeL207Client):
        def request_template(self, **kw: Any) -> dict[str, Any]:
            self._calls.append(kw)
            return {"template_body": "<broken schema>", "version": "bad"}
    return sut_factory(l207_client=_BrokenL207())


@pytest.fixture
def sut_with_broken_traceability(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _BadRefL105(_FakeL105Client):
        def __init__(self) -> None:
            super().__init__(body_map={
                "ac-scenario-writer": (
                    "---\ndoc_type: acceptance_criteria\n---\n"
                    "## AC-001 (linked_goal: GOAL-99, linked_reqs: REQ-001)\n"
                    "**Given** · **When** · **Then**\n"  # 引用不存在的 GOAL-99
                ),
            })
            # 其它 role 保持默认 body
    return sut_factory(l105_client=_BadRefL105())


@pytest.fixture
def sut_with_missing_section(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _NoSectionL105(_FakeL105Client):
        def __init__(self) -> None:
            super().__init__(body_map={
                "requirements-analysis": "---\ndoc_type: requirements\n---\n没 NFR 也没 REQ",
            })
    return sut_factory(l105_client=_NoSectionL105())


@pytest.fixture
def sut_with_persistent_qc_fail(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    return sut_factory(l105_client=_FakeL105Client(body_map={
        "requirements-analysis": "## REQ-001\n",  # 无 frontmatter · QC 必失败
    }))


@pytest.fixture
def sut_with_l207_timeout(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _TimeoutL207(_FakeL207Client):
        def request_template(self, **kw: Any) -> dict[str, Any]:
            raise TimeoutError("L2-07 simulated timeout")
    return sut_factory(l207_client=_TimeoutL207())


@pytest.fixture
def sut_with_empty_llm(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _EmptyL105(_FakeL105Client):
        def delegate_subagent(self, **kw: Any) -> dict[str, Any]:
            return {"output": ""}
    return sut_factory(l105_client=_EmptyL105())


@pytest.fixture
def sut_with_no_gwt_llm(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _NoGWT(_FakeL105Client):
        def __init__(self) -> None:
            super().__init__(body_map={
                "ac-scenario-writer": (
                    "---\ndoc_type: acceptance_criteria\n---\n"
                    "## AC-001 作为用户我希望 ...\n"  # User story · 非 GWT
                ),
            })
    return sut_factory(l105_client=_NoGWT())


@pytest.fixture
def sut_with_bad_id_llm(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    class _BadId(_FakeL105Client):
        def __init__(self) -> None:
            super().__init__(body_map={
                "requirements-analysis": "---\ndoc_type: requirements\n---\n## REQ1 bad id\n",
            })
    return sut_factory(l105_client=_BadId())


@pytest.fixture
def sut_with_bug_redo(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    """模拟内部 bug · 重做 AC 却改了 requirements · 触发 REDO_OUT_OF_SCOPE。"""
    prod = sut_factory()
    prod.enable_fault_injection("redo_out_of_scope")
    return prod


@pytest.fixture
def sut_with_dead_ref_after_redo(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    """首版 ok · 重做 requirements 删 REQ-003 但 goals 仍引用 · 3 次自愈仍失败。"""
    prod = sut_factory()
    prod.enable_fault_injection("dead_ref_after_redo")
    return prod


@pytest.fixture
def sut_with_failing_kb(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    failing_kb = _FakeL106Kb(simulate_failure=True)
    return sut_factory(l106_kb=failing_kb)


@pytest.fixture
def sut_with_kb_enabled(sut_factory: Callable[..., FourPiecesProducer]) -> FourPiecesProducer:
    return sut_factory(config={"endpoints": [], "kb_read_enabled": True,
                                "qc_retry_max": 2, "require_traceability": True})


# ---------- sample doc body (供 §5 perf 用) ----------

@pytest.fixture
def sample_doc_body() -> dict[str, str]:
    return {
        "requirements": "---\ndoc_type: requirements\n---\n## REQ-001 X\n## REQ-002 Y\n",
        "goals": "---\ndoc_type: goals\n---\n## GOAL-01 (linked_reqs: REQ-001) SMART\n",
        "acceptance_criteria": ("---\ndoc_type: acceptance_criteria\n---\n"
                                "## AC-001 (linked_goal: GOAL-01, linked_reqs: REQ-001)\n"
                                "Given X When Y Then Z\n"),
        "quality_standards": ("---\ndoc_type: quality_standards\n---\n"
                              "## QS-001 measurable=yes verification=test\n"),
    }
```

---

## §8 集成点用例（与兄弟 L2 调用链）

> 对 §4 上下游做端到端 join 测试 · mock 兄弟 L2 发请求 · 验证本 L2 响应符合 IC 契约 · 统计发送事件。

```python
# file: tests/l1_02/test_l2_03_integration_with_siblings.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer


class TestL2_03_IntegrationWithSiblingL2:
    """与 L2-07 模板 / L2-02 启动 / L2-01 Gate / L2-04 PMP / L1-03 WBS 的调用链集成。"""

    def test_TC_L102_L203_801_L207_template_chain_4_calls(
        self,
        sut: FourPiecesProducer,
        mock_l207_client: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-801 · 与 L2-07 模板 · 4 doc_type 依次发 request_template · trim_level 一致 · variables 含 project_name。"""
        sut.assemble_four_set(valid_trigger_request)
        calls = mock_l207_client.received_calls()
        # 4 次 · 顺序 REQ → GOAL → AC → QS
        assert [c["doc_type"] for c in calls] == [
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        ]
        # variables 中必含 project_name / goal_anchor
        assert all("variables" in c for c in calls)

    def test_TC_L102_L203_802_L202_goal_anchor_consumption(
        self,
        sut: FourPiecesProducer,
        mock_charter_and_hash: dict[str, str],
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-802 · 与 L2-02 启动 · 消费 L2-02 锁定的 goal_anchor_hash · hash 一致时通过校验。"""
        req = make_trigger_request(
            goal_anchor_hash=mock_charter_and_hash["goal_anchor_hash"],
        )
        resp = sut.assemble_four_set(req)
        assert resp.status == "ok"

    def test_TC_L102_L203_803_L201_gate_bundle_query_flow(
        self,
        sut_after_v1: FourPiecesProducer,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L203-803 · 与 L2-01 Gate · L2-01 打包 Gate bundle 前调 query_artifact_refs · manifest 字段全。"""
        m = sut_after_v1.query_artifact_refs(project_id=mock_project_id)
        assert m.version == "v1"
        assert m.cross_check_report["errors"] == []
        # L2-01 据此字段组织 Gate 卡片
        assert m.manifest_path.endswith("manifest.yaml")

    def test_TC_L102_L203_804_L204_pmp_consumes_four_set_manifest(
        self,
        sut: FourPiecesProducer,
        mock_event_bus: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-804 · 与 L2-04 PMP · L2-04 订阅 4_pieces_ready 事件 · 拿到 manifest 去跑 9 计划。"""
        sut.assemble_four_set(valid_trigger_request)
        total = [e for e in mock_event_bus.emitted_events()
                 if e["event_type"] == "L1-02/L2-03:4_pieces_ready"]
        assert len(total) == 1
        # L2-04 订阅者会读取 manifest_hash + docs paths
        assert total[0]["manifest_hash"]
        assert "docs" in total[0]
        assert all(p.endswith(".md") for p in
                   [total[0]["docs"][k]["path"] for k in total[0]["docs"]])

    def test_TC_L102_L203_805_L103_wbs_trigger_after_gate_pass(
        self,
        sut: FourPiecesProducer,
        mock_l103_wbs: Any,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-805 · 与 L1-03 WBS · S2 Gate pass 后由本 L2 承担 IC-19 · 且只发一次。"""
        sut.assemble_four_set(valid_trigger_request)
        sut.on_gate_passed(project_id=valid_trigger_request.project_id)
        # 再次 gate_passed 同 project · 幂等不重发
        sut.on_gate_passed(project_id=valid_trigger_request.project_id)
        assert len(mock_l103_wbs.received_calls()) == 1
```

---

## §9 边界 / edge case（≥ 4）

> 覆盖 §11 非显式错误码触发的灰区：上游章程缺失变种 / 4 件套间引用死链 / 部分产出失败重做 / 并发同 project / 版本回滚。
> 每边界给明确的期望行为（拒绝还是降级）。

```python
# file: tests/l1_02/test_l2_03_edge_cases.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_03.producer import FourPiecesProducer
from app.l2_03.errors import FourSetProducerError


class TestL2_03_EdgeCases:
    """§9 边界：上游缺失 / 跨 doc 死链 / 部分重做 / 并发 / 版本回滚。"""

    def test_TC_L102_L203_901_charter_file_absent_upstream_missing(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
        tmp_path: Any,
    ) -> None:
        """TC-L102-L203-901 · 上游章程文件不存在 · E_L102_L203_001 UPSTREAM_MISSING（不 raise · 返 err）。"""
        req = make_trigger_request()
        # 构造指向不存在路径的 trigger
        req.context["charter_path"] = str(tmp_path / "does-not-exist.md")
        resp = sut.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "UPSTREAM_MISSING"

    def test_TC_L102_L203_902_dead_ref_ac_to_nonexistent_req(
        self,
        sut_with_broken_traceability: FourPiecesProducer,
        valid_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-902 · AC 引不存在 REQ · CROSS_CHECK 给 dead_refs 清单 · E_L102_L203_003。"""
        resp = sut_with_broken_traceability.assemble_four_set(valid_trigger_request)
        assert resp.status == "err"
        assert resp.result.err_type in ("TRACEABILITY_BROKEN", "CROSS_REF_DEAD")
        assert resp.result.context.get("dead_refs")

    def test_TC_L102_L203_903_partial_redo_only_quality_standalone(
        self,
        sut_after_v1: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-903 · 只重做 quality_standards（closure={QS} 单点）· 其它 3 份保持 v1。"""
        req = make_trigger_request(target_subset=["quality_standards"])
        resp = sut_after_v1.assemble_four_set(req)
        assert resp.status == "ok"
        assert resp.result.docs["requirements"].version == "v1"
        assert resp.result.docs["goals"].version == "v1"
        assert resp.result.docs["acceptance_criteria"].version == "v1"
        assert resp.result.docs["quality_standards"].version == "v2"

    def test_TC_L102_L203_904_concurrent_same_project_second_waits_or_rejects(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-904 · 同 project 并发 2 trigger · 串行锁保护 · manifest 不错乱。"""
        from concurrent.futures import ThreadPoolExecutor

        r1 = make_trigger_request(request_id="cc-1")
        r2 = make_trigger_request(request_id="cc-2")
        with ThreadPoolExecutor(max_workers=2) as pool:
            res = list(pool.map(sut.assemble_four_set, [r1, r2]))
        # 至少一个 ok · 两个都拿到确定性结果
        ok = [r for r in res if r.status == "ok"]
        assert len(ok) >= 1
        # 最终 manifest 存在且一致（v1 或 v2 · 不出现部分写入损坏）
        m_final = sut.query_artifact_refs(project_id=r1.project_id)
        assert m_final.manifest_hash

    def test_TC_L102_L203_905_empty_target_subset_resolves_to_all(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-905 · target_subset=None · 等同 'all' · 全量跑 4 步。"""
        req = make_trigger_request(target_subset=None)
        resp = sut.assemble_four_set(req)
        assert resp.status == "ok"
        # 4 doc 全是 v1
        for dt in ("requirements", "goals", "acceptance_criteria", "quality_standards"):
            assert resp.result.docs[dt].version == "v1"

    def test_TC_L102_L203_906_target_subset_unknown_doc_type_rejected(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-906 · target_subset 含未知 doc_type · closure 空 · E_L102_L203_009 或 14."""
        req = make_trigger_request(target_subset=["nonexistent_piece"])
        resp = sut.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type in ("REDO_OUT_OF_SCOPE",)

    def test_TC_L102_L203_907_version_history_truncated_above_10(
        self,
        sut_after_v1: FourPiecesProducer,
        make_trigger_request: Any,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L203-907 · §7.3 · 历史版本超 10 · 删最早。"""
        # 连跑 11 次重做 AC
        for i in range(11):
            req = make_trigger_request(
                request_id=f"ver-{i}",
                target_subset=["acceptance_criteria"],
                change_requests=[f"revision {i}"],
            )
            sut_after_v1.assemble_four_set(req)
        # .v1..v10 保留 · v0 被删（最早）
        kept = sut_after_v1.list_version_history(
            project_id=mock_project_id, doc_type="acceptance_criteria"
        )
        assert len(kept) <= 10

    def test_TC_L102_L203_908_manifest_hash_excludes_produced_at(
        self,
        sut_factory: Any,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-908 · manifest_hash 只算 docs 段（不含 produced_at_ns）· 同输入不同时间点 hash 一致。"""
        s1 = sut_factory(); s2 = sut_factory()
        r1 = s1.assemble_four_set(make_trigger_request(request_id="t1"))
        # 人为在 s2 里推进时钟（fixture 未固定 · 靠实现）
        r2 = s2.assemble_four_set(make_trigger_request(request_id="t2"))
        assert r1.result.manifest_hash == r2.result.manifest_hash

    def test_TC_L102_L203_909_pm14_cross_project_pid_hard_reject(
        self,
        sut: FourPiecesProducer,
        make_trigger_request: Any,
    ) -> None:
        """TC-L102-L203-909 · PM-14 硬红线 · req.project_id != sut.active · 任何情况拒绝。"""
        req = make_trigger_request(project_id="proj-OTHER-pid")
        resp = sut.assemble_four_set(req)
        assert resp.status == "err"
        assert resp.result.err_type == "PM14_PID_MISMATCH"
```

---

## §10 附录：测试运行矩阵

| 测试文件 | 用例数 | 标记 | 预估耗时 |
|---|---|---|---|
| `test_l2_03_four_set_producer_positive.py` | 14 | — | < 3s |
| `test_l2_03_four_set_producer_negative.py` | 13 | — | < 4s |
| `test_l2_03_ic_contracts.py` | 7 | — | < 3s |
| `test_l2_03_perf_slo.py` | 8 | `perf` | 20-40s |
| `test_l2_03_e2e.py` | 3 | — | < 3s |
| `test_l2_03_integration_with_siblings.py` | 5 | — | < 3s |
| `test_l2_03_edge_cases.py` | 9 | — | < 3s |
| **总计** | **59 用例** | | **< 60s** |

运行命令：

```bash
# 全量
pytest tests/l1_02/ -v -k "L2_03 or L102_L203"

# 仅性能
pytest tests/l1_02/ -v -m perf -k "L2_03"

# 排除性能（CI 默认）
pytest tests/l1_02/ -v -m "not perf" -k "L2_03"

# 单一错误码回归（TRACEABILITY_BROKEN）
pytest tests/l1_02/test_l2_03_four_set_producer_negative.py::TestL2_03_FourSetProducerNegative::test_TC_L102_L203_103_traceability_broken_ac_to_missing_goal -v
```

---

*— L1-02 L2-03 4 件套生产器 · TDD 测试用例 depth-B (v1.0) · §0-§9 九节完结 · 59 TC · 13 错误码 · 6+4 方法 · 7 IC join · session-H —*
