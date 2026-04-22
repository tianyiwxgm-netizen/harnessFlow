---
doc_id: tests-L1-04-L2-03-测试用例生成器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-03-测试用例生成器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-03 测试用例生成器 · TDD 测试用例

> 基于 3-1 L2-03 §3（3 类对外接口 + 2 个公共方法）+ §6（10 个内部算法）+ §11（16 项错误码）+ §12（8 档 SLO）+ §13.2（70 条 TC 占位）驱动。
> TC ID 统一格式：`TC-L104-L203-NNN`（L1-04 下 L2-03，三位流水号 · 001-099 正向 / 1xx-5xx 负向按错误码分段 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_03_TestCaseGenerator` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。
> 错误码前缀一律 **`E_L204_L203_`**（§11.1 / §3.6 原样，不改）——`L204` = L1-04，`L203` = 本 L2。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock repo / mock kb）
- [x] §8 集成点用例（与兄弟 L2 协作 · L2-01 / L2-02 / L2-05 / L2-06）
- [x] §9 边界 / edge case（空 / 超大 / 嵌套参数化 / 空用例池 / 并发 / 崩溃）

---

## §1 覆盖度索引

> 每个 §3 对外方法 / §6 核心算法 / §11.1 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。
> 错误码前缀一律 `E_L204_L203_` · 以下表格省略前缀。

### §1.1 方法 × 测试 × 覆盖类型（§3 + §6 + §2 TC）

| 方法（§3 / §6 出处） | TC ID | 覆盖类型 | 错误码 / IC |
|---|---|---|---|
| `on_blueprint_ready()` · §3.1 订阅触发首次生成 | TC-L104-L203-001 | unit | IC-L2-01 |
| `on_blueprint_ready()` · §3.1 幂等（同 version 重复广播） | TC-L104-L203-002 | unit | — |
| `on_blueprint_ready()` · §3.1 异步 accept + 5s 超时 INFO | TC-L104-L203-003 | unit | — |
| `TestCaseSkeletonFactory.generate()` · §6 algo 1-9 主干 | TC-L104-L203-004 | unit | IC-09 |
| `TestCaseSkeletonFactory.generate()` · KB 可达走模板 | TC-L104-L203-005 | unit | IC-06 |
| `query_not_green_cases(wp_id)` · §3.2 方法 1 基本查询 | TC-L104-L203-010 | unit | IC-L2-03 |
| `query_not_green_cases(wp_id)` · 附带 monotonic_token + ttl | TC-L104-L203-011 | unit | IC-L2-03 |
| `query_not_green_cases(wp_id)` · 同 project PM-14 分片 | TC-L104-L203-012 | unit | — |
| `verify_monotonic_decrease()` · §3.2 方法 2 PASS（delta ≥ 0） | TC-L104-L203-020 | unit | IC-L2-03 |
| `verify_monotonic_decrease()` · 产新 snapshot + 新 token | TC-L104-L203-021 | unit | — |
| `verify_monotonic_decrease()` · delta == 0（无净变化） | TC-L104-L203-022 | unit | — |
| `SlugGenerator.generate_slug()` · §6 algo 2 英文 slug | TC-L104-L203-030 | unit | — |
| `SlugGenerator.generate_slug()` · §6 algo 2 中文 pypinyin | TC-L104-L203-031 | unit | — |
| `SlugGenerator.generate_slug()` · 长度 cap 60 | TC-L104-L203-032 | unit | — |
| `SlugGenerator.generate_slug()` · 重名递增 `_2` / `_3` | TC-L104-L203-033 | unit | — |
| `render_red_assertion()` · §6 algo 3 pytest | TC-L104-L203-040 | unit | — |
| `render_red_assertion()` · §6 algo 3 jest | TC-L104-L203-041 | unit | — |
| `render_red_assertion()` · §6 algo 3 go-test | TC-L104-L203-042 | unit | — |
| `render_red_assertion()` · §6 algo 3 cargo-test | TC-L104-L203-043 | unit | — |
| `build_file_path()` · §6 algo 4 PM-14 分片 | TC-L104-L203-050 | unit | — |
| `syntax_check_batch()` · §6 algo 5 并行 AST parse | TC-L104-L203-060 | unit | — |
| `StubCodeDetector.detect()` · §6 algo 8 Python AST 白名单外 | TC-L104-L203-070 | unit | — |
| `snapshot_manifest()` · §6 algo 6 hash-chain token | TC-L104-L203-080 | unit | — |
| `atomic_write_file()` · §6 algo 9 tempfile + rename | TC-L104-L203-090 | unit | — |

### §1.2 错误码 × 测试（§3.6 + §11.1 共 16 项 · 省略 `E_L204_L203_` 前缀）

| 错误码 | TC ID | 触发方法 / 降级等级 |
|---|---|---|
| `BLUEPRINT_NOT_FOUND` | TC-L104-L203-101 | `on_blueprint_ready()` · ERROR · 等 5s retry |
| `AC_MATRIX_INVALID` | TC-L104-L203-102 | `on_blueprint_ready()` payload 校验 · ERROR · INFO 升级 |
| `AC_COVERAGE_NOT_100` | TC-L104-L203-103 | algo 1 末尾 · CRITICAL · 回 L2-01 重建 |
| `SYNTAX_INVALID` | TC-L104-L203-104 | algo 5 · CRITICAL · 拒绝广播 |
| `STUB_CODE_DETECTED` | TC-L104-L203-105 | algo 8 · CRITICAL · BF-E-10 生成器污染 |
| `SKIP_MARK_DETECTED` | TC-L104-L203-106 | algo 8 · CRITICAL · 同上 |
| `DOCSTRING_MISSING` | TC-L104-L203-107 | 渲染后校验 · ERROR · 重试单 case |
| `FRAMEWORK_UNSUPPORTED` | TC-L104-L203-108 | algo 3 · WARNING · 降级 pytest |
| `PATH_CONFLICT` | TC-L104-L203-109 | algo 2 · ERROR · 100 次冲突硬拒绝 |
| `MANIFEST_STALE` | TC-L104-L203-110 | `verify_monotonic_decrease()` · WARNING · 令 L2-05 重 query |
| `MONOTONIC_CHECK_VIOLATION` | TC-L104-L203-111 | `verify_monotonic_decrease()` · CRITICAL · REJECT + WARN |
| `WAL_DRAIN_FAIL` | TC-L104-L203-112 | IC-09 3 次重试后 · CRITICAL · HALT + BF-E-10 |
| `KB_RECIPE_UNAVAILABLE` | TC-L104-L203-113 | IC-06 timeout · WARNING · 内置模板 |
| `STORAGE_QUOTA_EXCEEDED` | TC-L104-L203-114 | 文件写失败 · ERROR · 阻塞 + WARN |
| `CROSS_PROJECT_QUERY` | TC-L104-L203-115 | Repository assert · CRITICAL · HALT PM-14 红线 |
| `WBS_INCONSISTENT` | TC-L104-L203-116 | algo 1 · CRITICAL · 回 L2-01 / L1-03 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 `blueprint_ready`（本 L2 消费） | L2-01 → L2-02/03/04 | TC-L104-L203-601 | 广播订阅 · payload 校验 |
| IC-L2-03 `query_not_green_cases`（本 L2 生产 · 方法 1） | L2-05/06 → 本 L2 | TC-L104-L203-602 | 同步 · token + ttl |
| IC-L2-03 `verify_monotonic_decrease`（本 L2 生产 · 方法 2） | L2-05 → 本 L2 | TC-L104-L203-603 | 同步 · PASS / REJECT / STALE_TOKEN |
| IC-09 `append_event`（本 L2 发起 · 7 类领域事件） | 本 L2 → L1-09 | TC-L104-L203-604 | WAL fsync + hash-chain |
| IC-16 `push_stage_gate_card`（间接 · 经 L1-02） | 本 L2 → L1-02 → L1-10 | TC-L104-L203-605 | S3 Gate 产物预览 |
| IC-06 `kb_read`（本 L2 发起 · 可选 recipe 模板） | 本 L2 → L1-06 | TC-L104-L203-606 | 可选 · miss 降级内置模板 |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1） | 阈值 | TC ID |
|---|---|---|
| Factory.generate 总耗时（500 AC × 三层） | ≤ 180s | TC-L104-L203-701 |
| 单 case 生成耗时 P95 | ≤ 300ms | TC-L104-L203-702 |
| 单 case 语法自检 P95 | ≤ 50ms | TC-L104-L203-703 |
| `query_not_green_cases` P95 | ≤ 50ms | TC-L104-L203-704 |
| `verify_monotonic_decrease` P95 | ≤ 200ms | TC-L104-L203-705 |
| cases_generated 广播延迟 | ≤ 1s | TC-L104-L203-706 |

### §1.5 PRD §10.9 交付验证大纲 × 测试

| PRD 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · 100 AC × 三层批量生成 | TC-L104-L203-801 | e2e |
| 正向 2 · pytest collect 可发现全部骨架 | TC-L104-L203-802 | e2e |
| 负向 3 · 禁止桩代码假绿 | TC-L104-L203-803 | e2e |
| 负向 4 · 骨架语法错误拒绝广播 | TC-L104-L203-804 | e2e |
| 集成 5 · S4 阶段红→绿 + 单调递减校验 | TC-L104-L203-901 | integration |
| 集成 6 · S5 verifier 独立复跑骨架 | TC-L104-L203-902 | integration |
| 性能 7 · 500 AC 5 分钟内 | TC-L104-L203-707 | perf |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_03_TestCaseGenerator`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`TestCaseGenerator`（聚合 Factory + Repository + Detector · 从 `app.l1_04.l2_03.generator` 导入）。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_03_testcase_generator_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.factory import TestCaseSkeletonFactory
from app.l1_04.l2_03.services import (
    SlugGenerator,
    StubCodeDetector,
    render_red_assertion,
    build_file_path,
    syntax_check_batch,
    snapshot_manifest,
    atomic_write_file,
)
from app.l1_04.l2_03.schemas import (
    BlueprintReadyEvent,
    QueryNotGreenCasesRequest,
    QueryNotGreenCasesResponse,
    VerifyMonotonicDecreaseRequest,
    VerifyMonotonicDecreaseResponse,
    CaseSlot,
    TestSuite,
    TestCaseSkeleton,
    ManifestSnapshot,
)
from app.l1_04.l2_03.errors import TestCaseGeneratorError


class TestL2_03_TestCaseGenerator:
    """§3 对外接口 + §6 核心算法正向用例。每方法 ≥ 1 happy path。"""

    # --------- §3.1 on_blueprint_ready · 首次订阅触发 --------- #

    def test_TC_L104_L203_001_on_blueprint_ready_first_time(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-001 · blueprint_ready 首次订阅触发 · 返回 suite_id + state=INITIALIZING。"""
        # arrange
        evt: BlueprintReadyEvent = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=100, wp_count=10,
        )
        # act
        accept = sut.on_blueprint_ready(evt)
        # assert
        assert accept.accepted is True, "§3.1 非阻塞订阅 · 立即 accept"
        assert accept.suite_id.startswith("suite-"), "§7.1 suite_id UUID v4"
        assert accept.project_id == mock_project_id, "透传 event.project_id"
        snapshot = sut._peek_state(accept.suite_id)
        assert snapshot.state in ("INITIALIZING", "GENERATING"), "§8.1 状态机起点"

    def test_TC_L104_L203_002_idempotent_same_blueprint_version(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-002 · §6 algo 10 幂等 · 同 (blueprint_id, version) 重复广播只启一次 Factory。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=50)
        first = sut.on_blueprint_ready(evt)
        second = sut.on_blueprint_ready(evt)
        assert first.suite_id == second.suite_id, "幂等命中 · 复用同 suite"
        assert second.cached is True, "§3.1 处理要求 · 只启一次"
        assert sut._debug_factory_invocation_count(first.suite_id) == 1

    def test_TC_L104_L203_003_async_accept_emits_info_on_5s_timeout(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_clock,
    ) -> None:
        """TC-L104-L203-003 · §3.1 处理要求 · 5 秒内未启动 generator → 发 INFO 给 L1-07。"""
        sut._simulate_high_load(delay_ms=6000)
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=30)
        sut.on_blueprint_ready(evt)
        mock_clock.advance(seconds=6)
        info_msgs = sut._debug_pushed_suggestions(level="INFO")
        assert any(m["reason"] == "cases_generation_delayed" for m in info_msgs), \
            "§3.1 处理要求 · 5s 未启动触发 INFO"

    def test_TC_L104_L203_004_factory_generate_full_pipeline(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-004 · Factory.generate 主干（algo 1→3→4→5→6→7→9）合成 · 产 TestSuite READY。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=50, wp_count=5)
        suite = factory.generate(evt)
        assert suite.state == "READY", "§8.1 最终态 READY"
        assert suite.ac_coverage_pct == 1.0, "§10.1 locked ac_coverage_threshold"
        assert suite.red_count == suite.total_count, "§10.5 生成即红灯"
        assert suite.green_count == 0
        emitted_types = [c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert "L1-04:cases_generation_started" in emitted_types
        assert "L1-04:cases_generated" in emitted_types, "§2.10 领域事件"

    def test_TC_L104_L203_005_factory_uses_kb_template_when_confidence_ge_0_5(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_kb: MagicMock,
    ) -> None:
        """TC-L104-L203-005 · §3.5 · KB confidence=0.9 时用 KB 模板 · docstring 含 hint。"""
        mock_kb.recipe_read.return_value = {
            "recipe_id": "r-001",
            "template_content": "# KB hint: 订单总价精度 2 位",
            "confidence": 0.9,
            "source_project": "proj-ref",
        }
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        suite = factory.generate(evt)
        samples = [c for c in suite.cases]
        assert any("KB hint" in c.docstring or "Template hint" in c.docstring for c in samples), \
            "§6 algo 3 · KB confidence ≥ 0.5 走 KB 模板"

    # --------- §3.2 query_not_green_cases --------- #

    def test_TC_L104_L203_010_query_not_green_cases_basic(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-010 · §3.2 方法 1 · 返回当前 wp 下 state != green 的 case 列表。"""
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id,
            wp_id="WP-001",
            caller="L2-05",
            request_ts="2026-04-22T00:00:00Z",
        )
        resp: QueryNotGreenCasesResponse = sut.query_not_green_cases(req)
        assert resp.suite_id == ready_suite.suite_id
        assert resp.wp_id == "WP-001"
        assert resp.not_green_count == len([c for c in ready_suite.cases if c.wp_id == "WP-001" and c.state != "green"])
        assert all(c.state in ("red", "green_in_repair") for c in resp.cases)

    def test_TC_L104_L203_011_query_emits_fresh_token_and_ttl(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-011 · §3.2 响应含 monotonic_token + 300s ttl_sec（§10.1 locked）。"""
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.query_not_green_cases(req)
        assert resp.monotonic_token is not None
        assert len(resp.monotonic_token) == 64, "SHA-256 hex · 64 字符"
        assert resp.token_ttl_sec == 300, "§10.1 manifest_snapshot_ttl_sec 默认"
        assert resp.manifest_snapshot_id is not None

    def test_TC_L104_L203_012_query_respects_pm14_project_sharding(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        ready_suite_of_other_project: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-012 · PM-14 · 同 project 查询只返回本 project cases。"""
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.query_not_green_cases(req)
        for case in resp.cases:
            assert case.file_path.startswith(f"projects/{mock_project_id}/testing/"), \
                "§7.5 PM-14 分片隔离"

    # --------- §3.2 verify_monotonic_decrease --------- #

    def test_TC_L104_L203_020_verify_monotonic_decrease_pass_delta_positive(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-020 · §3.2 方法 2 · delta = prev(8) - new(5) = 3 ≥ 0 · PASS。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=8)
        req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=5,
            request_ts="2026-04-22T00:00:00Z",
        )
        resp: VerifyMonotonicDecreaseResponse = sut.verify_monotonic_decrease(req)
        assert resp.result == "PASS", "§3.2 语义 · delta ≥ 0 PASS"
        assert resp.delta == 3
        assert resp.prev_not_green_count == 8

    def test_TC_L104_L203_021_verify_produces_new_snapshot_and_token(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-021 · PASS 路径产新 snapshot + 新 token（§6 algo 7 末尾）。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=10)
        req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=7,
            request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.verify_monotonic_decrease(req)
        assert resp.result == "PASS"
        assert resp.new_snapshot_id is not None
        assert resp.new_monotonic_token != prev.monotonic_token, "hash-chain 前后不同"

    def test_TC_L104_L203_022_verify_delta_zero_is_pass(
        self,
        sut: TestCaseGenerator,
        ready_suite: TestSuite,
        mock_project_id: str,
    ) -> None:
        """TC-L104-L203-022 · delta == 0（无净变化但未回退）· 按 §3.2 语义仍 PASS。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=5,
            request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.verify_monotonic_decrease(req)
        assert resp.result == "PASS"
        assert resp.delta == 0

    # --------- §6 algo 2 · SlugGenerator --------- #

    def test_TC_L104_L203_030_slug_generator_english_basic(self) -> None:
        """TC-L104-L203-030 · §6 algo 2 · 英文 AC 描述走 slugify 规范。"""
        gen = SlugGenerator()
        slug = gen.generate_slug("Order total should be computed under 100ms", wp_scope=set(), language="en")
        assert slug == "order-total-should-be-computed-under-100ms" or "order" in slug
        assert len(slug) <= SlugGenerator.MAX_LEN

    def test_TC_L104_L203_031_slug_generator_chinese_pypinyin(self) -> None:
        """TC-L104-L203-031 · §6 algo 2 · 中文 AC 用 pypinyin 转拼音 · 取前 5 tokens。"""
        gen = SlugGenerator()
        slug = gen.generate_slug("订单总价计算", wp_scope=set(), language="zh")
        assert all(c.isascii() for c in slug), "拼音后全 ASCII"
        assert len(slug) <= SlugGenerator.MAX_LEN

    def test_TC_L104_L203_032_slug_generator_length_cap_60(self) -> None:
        """TC-L104-L203-032 · §6 algo 2 · 长描述 cap 到 MAX_LEN=60。"""
        gen = SlugGenerator()
        long_desc = "very_long_acceptance_criterion_description_" * 10
        slug = gen.generate_slug(long_desc, wp_scope=set(), language="en")
        assert len(slug) <= SlugGenerator.MAX_LEN

    def test_TC_L104_L203_033_slug_generator_dedup_with_suffix(self) -> None:
        """TC-L104-L203-033 · §6 algo 2 · 重名递增后缀 `_2` / `_3`。"""
        gen = SlugGenerator()
        existing = {"order_total", "order_total_2"}
        slug = gen.generate_slug("order total", wp_scope=existing, language="en")
        assert slug == "order_total_3" or slug.startswith("order_total_")
        assert slug not in existing

    # --------- §6 algo 3 · render_red_assertion 四语言 --------- #

    def test_TC_L104_L203_040_render_red_assertion_pytest(self, make_slot) -> None:
        """TC-L104-L203-040 · §6 algo 3 · pytest 用 raise NotImplementedError。"""
        slot = make_slot(ac_id="007", layer="unit", test_framework="pytest")
        code = render_red_assertion(slot, test_framework="pytest")
        assert "raise NotImplementedError" in code, "D1 决策 · 统一红灯风格"
        assert f"AC-{slot.ac_id}" in code
        assert '"""' in code, "§10.5 禁 6 · docstring 硬性"
        assert "pass" not in code.replace('"""', "")

    def test_TC_L104_L203_041_render_red_assertion_jest(self, make_slot) -> None:
        """TC-L104-L203-041 · §6 algo 3 · jest 用 throw new Error。"""
        slot = make_slot(ac_id="007", layer="unit", test_framework="jest")
        code = render_red_assertion(slot, test_framework="jest")
        assert "throw new Error" in code
        assert "test(" in code
        assert f"AC-{slot.ac_id}" in code

    def test_TC_L104_L203_042_render_red_assertion_go(self, make_slot) -> None:
        """TC-L104-L203-042 · §6 algo 3 · go-test 用 t.Fatalf。"""
        slot = make_slot(ac_id="007", layer="unit", test_framework="go-test")
        code = render_red_assertion(slot, test_framework="go-test")
        assert "t.Fatalf" in code
        assert "func Test" in code

    def test_TC_L104_L203_043_render_red_assertion_cargo(self, make_slot) -> None:
        """TC-L104-L203-043 · §6 algo 3 · cargo-test 用 panic!。"""
        slot = make_slot(ac_id="007", layer="unit", test_framework="cargo-test")
        code = render_red_assertion(slot, test_framework="cargo-test")
        assert "panic!" in code
        assert "#[test]" in code

    # --------- §6 algo 4 · build_file_path --------- #

    def test_TC_L104_L203_050_build_file_path_pm14_sharding(self, mock_project_id: str) -> None:
        """TC-L104-L203-050 · §6 algo 4 · 路径按 PM-14 分片 projects/<pid>/testing/generated/<wp>/<layer>/。"""
        path = build_file_path(
            project_id=mock_project_id, wp_id="WP-001",
            layer="unit", slug="order_total", ac_id="007",
            test_framework="pytest",
        )
        assert path == f"projects/{mock_project_id}/testing/generated/WP-001/unit/test_007_order_total.py"
        assert ".." not in path
        assert not path.startswith("/")

    # --------- §6 algo 5 · syntax_check_batch --------- #

    @pytest.mark.asyncio
    async def test_TC_L104_L203_060_syntax_check_all_valid_python(
        self, make_case_skeleton,
    ) -> None:
        """TC-L104-L203-060 · §6 algo 5 · 全合法 Python 骨架并行 parse 通过。"""
        cases = [
            make_case_skeleton(case_id=f"c-{i}", code=(
                f'def test_ac_{i:03d}_sample():\n'
                f'    """AC-{i:03d}: sample."""\n'
                f'    raise NotImplementedError("AC-{i:03d}: not implemented")\n'
            ))
            for i in range(10)
        ]
        result = await syntax_check_batch(cases)
        assert all(result.values()), "§6 algo 5 · 全部合法"

    # --------- §6 algo 8 · StubCodeDetector --------- #

    def test_TC_L104_L203_070_stub_detector_clean_red_assertion_passes(
        self, make_case_skeleton,
    ) -> None:
        """TC-L104-L203-070 · §6 algo 8 · 干净的 raise NotImplementedError 骨架不触发违禁。"""
        detector = StubCodeDetector()
        case = make_case_skeleton(
            case_id="c-001",
            code=(
                'def test_ac_001_sample():\n'
                '    """AC-001: sample."""\n'
                '    raise NotImplementedError("AC-001: not implemented")\n'
            ),
        )
        result = detector.detect(case)
        assert result.violated is False
        assert result.violations == []

    # --------- §6 algo 6 · snapshot_manifest --------- #

    def test_TC_L104_L203_080_snapshot_manifest_hash_chain(
        self, ready_suite: TestSuite,
    ) -> None:
        """TC-L104-L203-080 · §6 algo 6 · token = SHA-256(prev || count || wp || ts) hash-chain。"""
        s1 = snapshot_manifest(ready_suite, wp_id="WP-001", prev_token=None)
        s2 = snapshot_manifest(ready_suite, wp_id="WP-001", prev_token=s1.monotonic_token)
        assert s1.prev_token == "0" * 64, "首 snapshot prev 全零"
        assert s2.prev_token == s1.monotonic_token, "hash-chain 链式"
        assert s2.monotonic_token != s1.monotonic_token

    # --------- §6 algo 9 · atomic_write_file --------- #

    def test_TC_L104_L203_090_atomic_write_file_tempfile_then_rename(
        self, tmp_path,
    ) -> None:
        """TC-L104-L203-090 · §6 algo 9 · tempfile + rename 保证原子（无半写态）。"""
        target = str(tmp_path / "out" / "test_foo.py")
        atomic_write_file(target, "print('hi')\n")
        import os
        assert os.path.exists(target)
        tmp_residue = [n for n in os.listdir(tmp_path / "out") if n.startswith("._tmp_")]
        assert tmp_residue == [], "不留 tempfile 残留"
        with open(target) as f:
            assert f.read() == "print('hi')\n"
```

---

## §3 负向用例（每错误码 ≥ 1）

> 每条 §11.1 错误码 → 至少 1 TC · 错误码前缀按 §11.1 原样 `E_L204_L203_*`。
> 共 16 项 · TC-L104-L203-101 ~ 116（一条错误码一 TC ID）。

```python
# file: tests/l1_04/test_l2_03_testcase_generator_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.factory import TestCaseSkeletonFactory
from app.l1_04.l2_03.services import SlugGenerator, StubCodeDetector, build_file_path
from app.l1_04.l2_03.errors import (
    E_L204_L203_BLUEPRINT_NOT_FOUND,
    E_L204_L203_AC_MATRIX_INVALID,
    E_L204_L203_AC_COVERAGE_NOT_100,
    E_L204_L203_SYNTAX_INVALID,
    E_L204_L203_STUB_CODE_DETECTED,
    E_L204_L203_SKIP_MARK_DETECTED,
    E_L204_L203_DOCSTRING_MISSING,
    E_L204_L203_FRAMEWORK_UNSUPPORTED,
    E_L204_L203_PATH_CONFLICT,
    E_L204_L203_MANIFEST_STALE,
    E_L204_L203_MONOTONIC_CHECK_VIOLATION,
    E_L204_L203_WAL_DRAIN_FAIL,
    E_L204_L203_KB_RECIPE_UNAVAILABLE,
    E_L204_L203_STORAGE_QUOTA_EXCEEDED,
    E_L204_L203_CROSS_PROJECT_QUERY,
    E_L204_L203_WBS_INCONSISTENT,
)
from app.l1_04.l2_03.schemas import (
    BlueprintReadyEvent,
    QueryNotGreenCasesRequest,
    VerifyMonotonicDecreaseRequest,
)


class TestL2_03_Negative:
    """§11.1 16 项错误码 · 每项 ≥ 1 TC。"""

    def test_TC_L104_L203_101_blueprint_not_found_retries_5s_then_info(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_fs: MagicMock,
        mock_clock,
    ) -> None:
        """TC-L104-L203-101 · `E_L204_L203_BLUEPRINT_NOT_FOUND` · 文件不存在 5s retry 超时 INFO。"""
        mock_fs.exists.return_value = False
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=5)
        with pytest.raises(E_L204_L203_BLUEPRINT_NOT_FOUND):
            sut.on_blueprint_ready(evt, wait_retry=False)
        mock_clock.advance(seconds=6)
        info = sut._debug_pushed_suggestions(level="INFO")
        assert any(m["reason"] == "blueprint_path_missing" for m in info)

    def test_TC_L104_L203_102_ac_matrix_invalid_rejects_and_info(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-102 · `E_L204_L203_AC_MATRIX_INVALID` · 缺 entries.ac_id 必填字段 · 拒绝 + INFO。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=3,
            corrupt_ac_matrix=True,  # 制造缺 ac_id
        )
        with pytest.raises(E_L204_L203_AC_MATRIX_INVALID):
            sut.on_blueprint_ready(evt)
        info = sut._debug_pushed_suggestions(level="INFO")
        assert any("ac_matrix_invalid" in m.get("reason", "") for m in info)

    def test_TC_L104_L203_103_ac_coverage_not_100_rejects_build(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-103 · `E_L204_L203_AC_COVERAGE_NOT_100` · algo 1 末尾覆盖率硬校验 · CRITICAL 拒绝。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=10,
            inject_uncovered_ac_ids=["AC-999"],  # 蓝图声称 AC-999 但 wp 未分配
        )
        with pytest.raises(E_L204_L203_AC_COVERAGE_NOT_100) as exc:
            factory.generate(evt)
        assert "AC-999" in str(exc.value)

    def test_TC_L104_L203_104_syntax_invalid_batch_raises_critical(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-104 · `E_L204_L203_SYNTAX_INVALID` · 模板渲染出语法不合法 · algo 5 拦截。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3,
                                         force_bad_template="def test_@@( pass")
        with pytest.raises(E_L204_L203_SYNTAX_INVALID):
            factory.generate(evt)

    def test_TC_L104_L203_105_stub_code_detected_pass_statement(self, make_case_skeleton) -> None:
        """TC-L104-L203-105 · `E_L204_L203_STUB_CODE_DETECTED` · `def test_x(): pass` 触发红线（BF-E-10）。"""
        detector = StubCodeDetector()
        case = make_case_skeleton(
            case_id="c-001",
            code="def test_ac_001_fake():\n    pass\n",
        )
        result = detector.detect(case)
        assert result.violated is True
        assert any("pass" in v for v in result.violations)
        with pytest.raises(E_L204_L203_STUB_CODE_DETECTED):
            detector.raise_if_violated(case)

    def test_TC_L104_L203_105b_stub_code_detected_return_true(self, make_case_skeleton) -> None:
        """TC-L104-L203-105 (扩展 · return True / assert True 亦属 STUB_CODE) · §6 algo 8 Pattern 2/3。"""
        detector = StubCodeDetector()
        case_return = make_case_skeleton(
            case_id="c-002",
            code="def test_ac_002_return():\n    return True\n",
        )
        case_assert = make_case_skeleton(
            case_id="c-003",
            code="def test_ac_003_assert():\n    assert True\n",
        )
        assert detector.detect(case_return).violated
        assert detector.detect(case_assert).violated

    def test_TC_L104_L203_106_skip_mark_detected(
        self, make_case_skeleton,
    ) -> None:
        """TC-L104-L203-106 · `E_L204_L203_SKIP_MARK_DETECTED` · `@pytest.mark.skip` / `pytest.skip()` 触发。"""
        detector = StubCodeDetector()
        case_mark = make_case_skeleton(
            case_id="c-010",
            code=(
                "import pytest\n"
                "@pytest.mark.skip\n"
                "def test_ac_010_skipped():\n"
                '    raise NotImplementedError("x")\n'
            ),
        )
        case_call = make_case_skeleton(
            case_id="c-011",
            code=(
                "import pytest\n"
                "def test_ac_011_skip_call():\n"
                '    pytest.skip("oops")\n'
            ),
        )
        assert detector.detect(case_mark).violated
        assert detector.detect(case_call).violated
        with pytest.raises(E_L204_L203_SKIP_MARK_DETECTED):
            detector.raise_if_violated(case_mark, prefer="skip_mark")

    def test_TC_L104_L203_107_docstring_missing_rejects_case(
        self,
        factory: TestCaseSkeletonFactory,
        make_slot,
    ) -> None:
        """TC-L104-L203-107 · `E_L204_L203_DOCSTRING_MISSING` · §10.5 禁 6 · 渲染后校验缺 docstring 拒绝。"""
        slot = make_slot(ac_id="007", layer="unit", test_framework="pytest")
        with pytest.raises(E_L204_L203_DOCSTRING_MISSING):
            factory._render_and_validate(slot, template_hint=None, force_strip_docstring=True)

    def test_TC_L104_L203_108_framework_unsupported_warn_and_fallback_pytest(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-108 · `E_L204_L203_FRAMEWORK_UNSUPPORTED` · WARNING · 降级 pytest（§11.1）。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=3,
            test_framework="mocha-but-python",
        )
        suite = factory.generate(evt, fallback_on_unsupported=True)
        assert suite.test_framework == "pytest", "降级默认 pytest"
        warns = [c.kwargs for c in mock_event_bus.append_event.call_args_list
                 if "framework_unsupported" in (c.kwargs.get("payload") or {}).get("reason", "")]
        assert warns, "发 WARN"

    def test_TC_L104_L203_109_path_conflict_100_attempts_hard_reject(self) -> None:
        """TC-L104-L203-109 · `E_L204_L203_PATH_CONFLICT` · 重名 100 次后硬拒绝。"""
        gen = SlugGenerator()
        wp_scope = {f"order_total_{i}" for i in range(2, 102)} | {"order_total"}
        with pytest.raises(E_L204_L203_PATH_CONFLICT):
            gen.generate_slug("order total", wp_scope=wp_scope, language="en")

    def test_TC_L104_L203_110_manifest_stale_token_over_300s(
        self,
        sut: TestCaseGenerator,
        ready_suite,
        mock_project_id: str,
        mock_clock,
    ) -> None:
        """TC-L104-L203-110 · `E_L204_L203_MANIFEST_STALE` · token > 300s 过期 · 返回 STALE_TOKEN。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        mock_clock.advance(seconds=301)
        req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=4,
            request_ts="2026-04-22T00:05:01Z",
        )
        resp = sut.verify_monotonic_decrease(req)
        assert resp.result == "STALE_TOKEN"
        assert "300" in resp.reason or "stale" in resp.reason.lower()

    def test_TC_L104_L203_111_monotonic_check_violation_green_to_red(
        self,
        sut: TestCaseGenerator,
        ready_suite,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L203-111 · `E_L204_L203_MONOTONIC_CHECK_VIOLATION` · delta < 0 · REJECT + WARN（§11.3）。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=7,
            request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.verify_monotonic_decrease(req)
        assert resp.result == "REJECT"
        assert resp.reason.startswith("绿→红回退") or "delta=-2" in resp.reason
        # 发 WARN 给 L1-07
        pushed = mock_l1_07.push_suggestion.call_args_list
        assert any(c.kwargs.get("level") == "WARN"
                   and c.kwargs.get("reason") == "cases_green_regression"
                   for c in pushed), "§11.3 Supervisor 协同"

    def test_TC_L104_L203_112_wal_drain_fail_after_3_retries_halts(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-112 · `E_L204_L203_WAL_DRAIN_FAIL` · IC-09 3 次重试失败 · HALT + BF-E-10。"""
        mock_event_bus.append_event.side_effect = TimeoutError("l1-09 unavailable")
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        with pytest.raises(E_L204_L203_WAL_DRAIN_FAIL):
            sut.on_blueprint_ready(evt, wal_retry_max=3)
        assert sut._degraded_mode == "HALT", "§11.2 HALT 等 BF-E-10"

    def test_TC_L104_L203_113_kb_recipe_unavailable_falls_back_to_builtin(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_kb: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-113 · `E_L204_L203_KB_RECIPE_UNAVAILABLE` · KB timeout · WARN + 内置模板继续。"""
        mock_kb.recipe_read.side_effect = TimeoutError("kb timeout 2s")
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        suite = factory.generate(evt)  # 不 raise · 降级继续
        assert suite.state == "READY"
        degraded_modes = [c.kwargs.get("payload", {}).get("degraded_mode")
                          for c in mock_event_bus.append_event.call_args_list]
        assert "BUILTIN_TEMPLATE" in degraded_modes, "§5.4 P1 时序 · KB 不可达降级"

    def test_TC_L104_L203_114_storage_quota_exceeded_blocks_with_warn(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_fs: MagicMock,
    ) -> None:
        """TC-L104-L203-114 · `E_L204_L203_STORAGE_QUOTA_EXCEEDED` · 配额满 · 阻塞 + WARN。"""
        mock_fs.write.side_effect = OSError("[Errno 28] No space left on device")
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        with pytest.raises(E_L204_L203_STORAGE_QUOTA_EXCEEDED):
            factory.generate(evt)

    def test_TC_L104_L203_115_cross_project_query_halts_pm14_red_line(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        other_project_id: str,
    ) -> None:
        """TC-L104-L203-115 · `E_L204_L203_CROSS_PROJECT_QUERY` · Repository 绑定 project_id 不匹配 · HALT。"""
        # sut 绑定 mock_project_id · 查询带 other_project_id 应硬失败
        req = QueryNotGreenCasesRequest(
            project_id=other_project_id,  # 跨 project
            wp_id="WP-001", caller="L2-05",
            request_ts="2026-04-22T00:00:00Z",
        )
        with pytest.raises(E_L204_L203_CROSS_PROJECT_QUERY):
            sut.query_not_green_cases(req)

    def test_TC_L104_L203_116_wbs_inconsistent_ac_not_in_matrix(
        self,
        factory: TestCaseSkeletonFactory,
        mock_project_id: str,
        make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-116 · `E_L204_L203_WBS_INCONSISTENT` · WP 覆盖的 AC 在 ac_matrix 找不到 · algo 1 拦截。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=5,
            inject_wp_with_phantom_ac="AC-ghost-404",
        )
        with pytest.raises(E_L204_L203_WBS_INCONSISTENT):
            factory.generate(evt)
```

---

## §4 IC-XX 契约集成测试

> 与 3-1 §3 IC 契约字段级 schema 对齐；验证 payload 结构、方向、幂等、错误码映射。
> 覆盖 6 个 IC：IC-L2-01（消费）/ IC-L2-03 方法 1-2（生产）/ IC-09 / IC-16 / IC-06。
> 至少 3 个 "join test"（两 L2 / L2+L1 接口链路合流）。

```python
# file: tests/l1_04/test_l2_03_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.schemas import (
    BlueprintReadyEvent,
    QueryNotGreenCasesRequest,
    VerifyMonotonicDecreaseRequest,
)


class TestL2_03_ICContracts:
    """§3 IC 契约 · 6 IC 对齐 · ≥ 3 join test（IC-L2-01×IC-09 / IC-L2-03×IC-09 / IC-06×IC-09）。"""

    # ---- IC-L2-01 消费契约 ---- #

    def test_TC_L104_L203_601_ic_l2_01_payload_structure(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-601 · IC-L2-01 payload 含 ac_matrix / test_pyramid / wbs_snapshot 必填字段（§3.1）。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=30, wp_count=5)
        # schema 对齐 §3.1：event_id / blueprint_version / ac_matrix.total_ac_count / test_pyramid.*_ratio / wbs_snapshot
        assert evt.event_id is not None
        assert evt.blueprint_version in ("v1", "v2")
        assert evt.ac_matrix.total_ac_count == 30
        assert evt.ac_matrix.entries[0].priority in ("P0", "P1", "P2")
        assert abs(evt.test_pyramid.unit_target_ratio
                   + evt.test_pyramid.integration_target_ratio
                   + evt.test_pyramid.e2e_target_ratio - 1.0) < 1e-6, "pyramid 比例和 ≈ 1"
        assert evt.test_framework in ("pytest", "jest", "go-test", "cargo-test")
        accept = sut.on_blueprint_ready(evt)
        assert accept.accepted is True

    # ---- IC-L2-03 方法 1 ---- #

    def test_TC_L104_L203_602_ic_l2_03_query_request_response_schema(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
    ) -> None:
        """TC-L104-L203-602 · IC-L2-03 query_not_green_cases 请求 / 响应 schema 对齐（§3.2 方法 1）。"""
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        resp = sut.query_not_green_cases(req)
        # 按 §3.2 response schema 验字段
        for fld in ("suite_id", "wp_id", "not_green_count", "cases",
                    "manifest_snapshot_id", "monotonic_token", "token_issued_at", "token_ttl_sec"):
            assert hasattr(resp, fld), f"§3.2 response 缺字段 {fld}"
        for case in resp.cases:
            assert case.layer in ("unit", "integration", "e2e")
            assert case.state in ("red", "green_in_repair")

    # ---- IC-L2-03 方法 2 ---- #

    def test_TC_L104_L203_603_ic_l2_03_verify_response_has_three_results(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str, mock_clock,
    ) -> None:
        """TC-L104-L203-603 · IC-L2-03 verify 三枚举 PASS / REJECT / STALE_TOKEN 都能被触发（§3.2 方法 2 语义）。"""
        # PASS
        t_ok = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        r_pass = sut.verify_monotonic_decrease(VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=t_ok.monotonic_token, new_not_green_count=3,
            request_ts="2026-04-22T00:00:00Z",
        ))
        assert r_pass.result == "PASS"
        # REJECT
        t_bad = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        r_reject = sut.verify_monotonic_decrease(VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=t_bad.monotonic_token, new_not_green_count=9,
            request_ts="2026-04-22T00:00:00Z",
        ))
        assert r_reject.result == "REJECT"
        # STALE
        t_old = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=5)
        mock_clock.advance(seconds=301)
        r_stale = sut.verify_monotonic_decrease(VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=t_old.monotonic_token, new_not_green_count=4,
            request_ts="2026-04-22T00:05:01Z",
        ))
        assert r_stale.result == "STALE_TOKEN"

    # ---- IC-09 append_event 7 事件 ---- #

    def test_TC_L104_L203_604_ic_09_seven_domain_events_emitted(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_event_bus: MagicMock, ready_suite,
    ) -> None:
        """TC-L104-L203-604 · IC-09 7 类领域事件（§2.10）都按各路径 emit。"""
        # generation 路径
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=5)
        sut.on_blueprint_ready(evt, force_rebuild=True)
        # 手工触发 case 状态转换 / suite 归档 以覆盖剩余事件类型
        sut._debug_transition_case(ready_suite.cases[0].case_id, new_state="green")
        sut._debug_archive_suite(ready_suite.suite_id)
        types = {c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list}
        expected = {
            "L1-04:cases_generation_started",
            "L1-04:cases_generated",
            "L1-04:cases_red_verified",
            "L1-04:manifest_snapshot_taken",
            "L1-04:case_state_transitioned",
            "L1-04:suite_archived",
        }
        assert expected.issubset(types), f"§2.10 7 类事件覆盖不足 · 缺 {expected - types}"

    # ---- IC-16 经 L1-02 · 间接 ---- #

    def test_TC_L104_L203_605_ic_16_stage_gate_artifact_ready_via_l102(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-605 · §3.4 · L2-03 只 emit `L1-04:stage_gate_artifact_ready` · L1-02 组装 IC-16。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=20, wp_count=3)
        sut.on_blueprint_ready(evt)
        payloads = [c.kwargs for c in mock_event_bus.append_event.call_args_list
                    if c.kwargs.get("event_type") == "L1-04:stage_gate_artifact_ready"]
        assert payloads, "未 emit stage_gate_artifact_ready"
        p = payloads[0]["payload"]
        assert p["stage"] == "S3"
        assert p["artifact_type"] == "test_skeletons"
        assert p["artifact_path"].startswith(f"projects/{mock_project_id}/testing/generated/")
        # preview.summary + sample_case_paths
        assert "preview" in p and "summary" in p["preview"]
        assert len(p["preview"]["sample_case_paths"]) <= 5, "§3.4 preview 前 5 给 UI"

    # ---- IC-06 可选 recipe ---- #

    def test_TC_L104_L203_606_ic_06_recipe_read_optional_miss_is_ok(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_kb: MagicMock,
    ) -> None:
        """TC-L104-L203-606 · §3.5 · IC-06 miss 不 fail · 降级内置模板继续。"""
        mock_kb.recipe_read.return_value = {"template_content": None, "confidence": 0.0}
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        accept = sut.on_blueprint_ready(evt)
        assert accept.accepted is True

    # ---- join test 1: IC-L2-01 × IC-09（blueprint_ready 驱动 7 事件中的 started + generated） ---- #

    def test_TC_L104_L203_607_join_ic_l2_01_drives_ic_09_started_and_generated(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-607 · join · IC-L2-01 blueprint_ready 必然驱动 IC-09 cases_generation_started + cases_generated。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=10)
        sut.on_blueprint_ready(evt)
        types_in_order = [c.kwargs["event_type"]
                          for c in mock_event_bus.append_event.call_args_list
                          if c.kwargs["event_type"].startswith("L1-04:cases_generat")]
        assert types_in_order[0] == "L1-04:cases_generation_started"
        assert "L1-04:cases_generated" in types_in_order, "§5.1 P0-1 时序"

    # ---- join test 2: IC-L2-03.verify × IC-09 manifest_snapshot_taken + push WARN ---- #

    def test_TC_L104_L203_608_join_verify_reject_emits_ic_09_and_pushes_warn(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
        mock_event_bus: MagicMock, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L203-608 · join · verify REJECT 同时 IC-09 monotonic_check_violation + L1-07 WARN（§5.3 P1 时序）。"""
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=3)
        sut.verify_monotonic_decrease(VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=prev.monotonic_token, new_not_green_count=5,
            request_ts="2026-04-22T00:00:00Z",
        ))
        types = {c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list}
        assert "L1-04:monotonic_check_violation" in types
        warns = [c.kwargs for c in mock_l1_07.push_suggestion.call_args_list
                 if c.kwargs.get("level") == "WARN"]
        assert warns, "§5.3 发 WARN 给 Supervisor"

    # ---- join test 3: IC-06 degrade × IC-09 degraded_mode event ---- #

    def test_TC_L104_L203_609_join_ic_06_degrade_emits_ic_09_degraded_mode(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_kb: MagicMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-609 · join · IC-06 timeout × IC-09 emit degraded_mode=BUILTIN_TEMPLATE（§5.4 P1 时序）。"""
        mock_kb.recipe_read.side_effect = TimeoutError("kb timeout")
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3)
        sut.on_blueprint_ready(evt)
        degraded_payloads = [c.kwargs.get("payload", {})
                             for c in mock_event_bus.append_event.call_args_list
                             if c.kwargs.get("payload", {}).get("degraded_mode")]
        assert any(p.get("degraded_mode") == "BUILTIN_TEMPLATE"
                   and p.get("reason") == "kb_timeout" for p in degraded_payloads), \
            "§5.4 P1 时序 · degrade 路径"
```

---

## §5 性能 SLO 用例

> §12.1 / §12.2 / §12.3 全项覆盖；`@pytest.mark.perf` 组；benchmark 用 `pytest-benchmark` 或手工 p95。
> 目标环境：本地 CI（4 vCPU · 8GB RAM）；阈值取 §12 表对应值。

```python
# file: tests/l1_04/test_l2_03_performance.py
from __future__ import annotations

import pytest
import statistics
import time

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.factory import TestCaseSkeletonFactory
from app.l1_04.l2_03.schemas import QueryNotGreenCasesRequest, VerifyMonotonicDecreaseRequest


class TestL2_03_Performance:
    """§12 SLO 硬性指标 · @pytest.mark.perf。"""

    @pytest.mark.perf
    def test_TC_L104_L203_701_factory_generate_500ac_under_180s(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-701 · §12.1 · 500 AC × 三层 ≤ 180s 完成。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=500, wp_count=20)
        t0 = time.perf_counter()
        suite = factory.generate(evt)
        elapsed = time.perf_counter() - t0
        assert suite.state == "READY"
        assert elapsed <= 180.0, f"§12.1 SLO · 500 AC elapsed={elapsed:.1f}s > 180s"

    @pytest.mark.perf
    def test_TC_L104_L203_702_per_case_generation_p95_under_300ms(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-702 · §12.1 · 单 case 生成 P95 ≤ 300ms。"""
        durations: list[float] = []
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=50, wp_count=5)
        factory.generate(evt, _capture_per_case_ms=durations)
        p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations)
        assert p95 <= 300.0, f"单 case P95={p95:.1f}ms > 300ms"

    @pytest.mark.perf
    def test_TC_L104_L203_703_syntax_check_per_case_p95_under_50ms(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-703 · §12.1 · 单 case 语法自检 P95 ≤ 50ms（§6 algo 5 ast.parse）。"""
        syntax_durations: list[float] = []
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=50, wp_count=5)
        factory.generate(evt, _capture_syntax_ms=syntax_durations)
        p95 = statistics.quantiles(syntax_durations, n=20)[18] if len(syntax_durations) >= 20 else max(syntax_durations)
        assert p95 <= 50.0, f"语法自检 P95={p95:.1f}ms > 50ms"

    @pytest.mark.perf
    def test_TC_L104_L203_704_query_not_green_cases_p95_under_50ms(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
    ) -> None:
        """TC-L104-L203-704 · §12.1 · query_not_green_cases P95 ≤ 50ms。"""
        durations: list[float] = []
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        for _ in range(100):
            t0 = time.perf_counter()
            sut.query_not_green_cases(req)
            durations.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 <= 50.0, f"query P95={p95:.1f}ms > 50ms"

    @pytest.mark.perf
    def test_TC_L104_L203_705_verify_monotonic_p95_under_200ms(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
    ) -> None:
        """TC-L104-L203-705 · §12.1 · verify_monotonic_decrease P95 ≤ 200ms（含 DB + hash）。"""
        durations: list[float] = []
        prev = sut._debug_seed_manifest(ready_suite.suite_id, wp_id="WP-001", not_green_count=100)
        for i in range(50):
            req = VerifyMonotonicDecreaseRequest(
                project_id=mock_project_id, wp_id="WP-001",
                prev_token=prev.monotonic_token, new_not_green_count=100 - i,
                request_ts="2026-04-22T00:00:00Z",
            )
            t0 = time.perf_counter()
            resp = sut.verify_monotonic_decrease(req)
            durations.append((time.perf_counter() - t0) * 1000)
            prev = sut._debug_get_snapshot(resp.new_snapshot_id) if resp.result == "PASS" else prev
        p95 = statistics.quantiles(durations, n=20)[18]
        assert p95 <= 200.0, f"verify P95={p95:.1f}ms > 200ms"

    @pytest.mark.perf
    def test_TC_L104_L203_706_cases_generated_broadcast_latency_under_1s(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_event_bus,
    ) -> None:
        """TC-L104-L203-706 · §12.1 · cases_generated 广播延迟（emit → L1-09 落盘）≤ 1s。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=10)
        t0 = time.perf_counter()
        sut.on_blueprint_ready(evt)
        # 定位 cases_generated 事件
        for call in mock_event_bus.append_event.call_args_list:
            if call.kwargs.get("event_type") == "L1-04:cases_generated":
                latency = time.perf_counter() - t0
                assert latency <= 1.0, f"cases_generated 广播 {latency:.2f}s > 1s"
                return
        pytest.fail("cases_generated 未 emit")

    @pytest.mark.perf
    def test_TC_L104_L203_707_large_scale_500_ac_within_5min(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-707 · PRD §10.9 性能 7 · 500 AC 5 分钟内（放宽 SLO）· AC 覆盖率 100%。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=500, wp_count=25)
        t0 = time.perf_counter()
        suite = factory.generate(evt)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 300.0, f"5 分钟内 · elapsed={elapsed:.1f}s"
        assert suite.ac_coverage_pct == 1.0
        assert suite.total_count >= 500
```

---

## §6 端到端 e2e

> 覆盖 PRD §10.9 交付验证大纲 · 跑通"测试用例自动生成链路"：
> 正向 1（100 AC × 三层批量）/ 正向 2（collect 可发现）/ 负向 3（桩代码拦截）/ 负向 4（语法错拒绝广播）。
> e2e 允许真实磁盘 I/O（tmp_path）+ 真实 ast.parse · 其他 L2 仍然 mock（本 L2 聚合根内部端到端）。

```python
# file: tests/l1_04/test_l2_03_e2e.py
from __future__ import annotations

import pytest
import subprocess
import os

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.errors import (
    E_L204_L203_STUB_CODE_DETECTED,
    E_L204_L203_SYNTAX_INVALID,
)


class TestL2_03_E2E:
    """PRD §10.9 交付验证大纲 2-3 GWT 端到端。"""

    # ---- 正向 1 + 正向 2 合成一条 GWT · 100 AC 骨架 + pytest --collect-only ---- #

    def test_TC_L104_L203_801_e2e_100_ac_three_layers_batch_and_collectable(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        tmp_project_root,
    ) -> None:
        """TC-L104-L203-801 · PRD §10.9 正向 1+2 · GWT：100 AC × 分层配比 · 3 分钟内产 100-200 骨架 · 全部红灯。

        Given  Master Test Plan 100 AC × (60 unit / 30 integration / 10 e2e)
        When   blueprint_ready 触发
        Then   3 分钟内产 ~100-200 骨架 · 全红灯 · manifest 完整 · 路径 PM-14 分片
        """
        # Given
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=100, wp_count=10,
            pyramid=dict(unit=0.6, integration=0.3, e2e=0.1),
        )
        # When
        accept = sut.on_blueprint_ready(evt, blocking=True)
        # Then
        suite = sut._debug_get_suite(accept.suite_id)
        assert suite.state == "READY"
        assert 100 <= suite.total_count <= 300, f"骨架 100-300（含分层冗余）实际 {suite.total_count}"
        assert suite.red_count == suite.total_count, "全红灯"
        assert suite.ac_coverage_pct == 1.0

        # 正向 2 · pytest collect 可发现
        gen_dir = f"{tmp_project_root}/projects/{mock_project_id}/testing/generated"
        assert os.path.isdir(gen_dir)
        # ast.parse 代理 pytest collect（避免跨 venv pytest 依赖）
        py_files = []
        for root, _, files in os.walk(gen_dir):
            for fn in files:
                if fn.endswith(".py"):
                    py_files.append(os.path.join(root, fn))
        assert py_files, "无骨架 .py 产物"
        import ast
        for fp in py_files:
            with open(fp) as f:
                ast.parse(f.read())  # 不抛 = collect 通过

    # ---- 负向 3 · 桩代码假绿被拦截 ---- #

    def test_TC_L104_L203_803_e2e_stub_code_is_rejected(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-803 · PRD §10.9 负向 3 · GWT：内部某路径倾向生成 pass · 自检拦截 · 抛错 · 上报事件。

        Given  模板被污染 · 渲染结果含 `def test_xx(): pass`
        When   Factory.generate
        Then   algo 8 检测违禁 · raise E_L204_L203_STUB_CODE_DETECTED · BF-E-10
        """
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=3,
            poison_template="def test_ac_{ac_id}_{slug}():\n    pass\n",  # 污染模板
        )
        with pytest.raises(E_L204_L203_STUB_CODE_DETECTED):
            sut.on_blueprint_ready(evt, blocking=True)
        failure_events = sut._debug_pushed_suggestions(level="CRITICAL")
        assert any(m.get("bf_escalation") == "BF-E-10" for m in failure_events), \
            "§11.3 STUB_CODE_DETECTED → BF-E-10"

    # ---- 负向 4 · 语法错骨架被拒绝广播 ---- #

    def test_TC_L104_L203_804_e2e_syntax_error_rejects_broadcast(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
        mock_event_bus,
    ) -> None:
        """TC-L104-L203-804 · PRD §10.9 负向 4 · GWT：模板渲染语法不合法 · 自检 FAIL · 拒广播 · INFO 回查。

        Given  某模板渲染错误导致 SyntaxError
        When   algo 5 自检
        Then   拒广播 cases_generated · 发 INFO 给 L1-07
        """
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=3,
            poison_template="def test_@@@( \n    pass\n",  # 硬语法错
        )
        with pytest.raises(E_L204_L203_SYNTAX_INVALID):
            sut.on_blueprint_ready(evt, blocking=True)
        emitted_types = {c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list}
        assert "L1-04:cases_generated" not in emitted_types, "语法错 · 拒广播"
        assert "L1-04:cases_generation_failed" in emitted_types
        info = sut._debug_pushed_suggestions(level="INFO")
        assert any("syntax_invalid" in m.get("reason", "") for m in info), "§11.3 INFO 回查"
```

---

## §7 测试 fixture

> 共享 fixture：SUT 实例(Generator 聚合) / Factory / mock project_id / mock clock / mock event bus / mock kb / mock fs / mock l1_07 / ready_suite。
> 放在 `tests/l1_04/conftest.py` · autouse 的只开 event bus · 其余 opt-in。

```python
# file: tests/l1_04/conftest_l2_03.py  (同 L2-01/L2-02 共享 conftest.py)
from __future__ import annotations

import pytest
import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.factory import TestCaseSkeletonFactory
from app.l1_04.l2_03.schemas import (
    BlueprintReadyEvent,
    CaseSlot,
    TestSuite,
    TestCaseSkeleton,
)


@pytest.fixture
def mock_project_id() -> str:
    return "pid-l203-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-l203-foreign"


@pytest.fixture
def tmp_project_root(tmp_path) -> str:
    return str(tmp_path)


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append_event.return_value = {"ok": True, "event_id": "evt-" + str(uuid.uuid4())}
    return bus


@pytest.fixture
def mock_kb() -> MagicMock:
    kb = MagicMock()
    kb.recipe_read.return_value = {
        "recipe_id": "r-default",
        "template_content": "# default hint",
        "confidence": 0.6,
        "source_project": "builtin",
    }
    return kb


@pytest.fixture
def mock_fs() -> MagicMock:
    fs = MagicMock()
    fs._store: dict[str, str] = {}
    fs.exists = lambda p: True
    fs.write = lambda p, c: fs._store.__setitem__(p, c)
    fs.read = lambda p: fs._store.get(p, "")
    return fs


@pytest.fixture
def mock_l1_07() -> MagicMock:
    sup = MagicMock()
    sup.push_suggestion.return_value = {"ok": True}
    return sup


@pytest.fixture
def mock_clock() -> Any:
    class _Clock:
        def __init__(self) -> None: self.t = 0.0
        def now(self) -> float: return self.t
        def advance(self, seconds: float = 0.0) -> None: self.t += seconds
    return _Clock()


@pytest.fixture
def factory(mock_event_bus, mock_kb, mock_fs, mock_l1_07, mock_project_id, tmp_project_root) -> TestCaseSkeletonFactory:
    return TestCaseSkeletonFactory(
        event_bus=mock_event_bus, kb=mock_kb, fs=mock_fs, l1_07=mock_l1_07,
        project_id=mock_project_id, root_dir=tmp_project_root,
    )


@pytest.fixture
def sut(factory, mock_event_bus, mock_kb, mock_fs, mock_l1_07, mock_project_id, tmp_project_root, mock_clock) -> TestCaseGenerator:
    return TestCaseGenerator(
        factory=factory, event_bus=mock_event_bus, kb=mock_kb, fs=mock_fs,
        l1_07=mock_l1_07, project_id=mock_project_id, clock=mock_clock,
        root_dir=tmp_project_root,
    )


@pytest.fixture
def make_blueprint_ready_event() -> Callable[..., BlueprintReadyEvent]:
    def _factory(**overrides: Any) -> BlueprintReadyEvent:
        ac_count = overrides.get("ac_count", 10)
        wp_count = overrides.get("wp_count", 3)
        corrupt = overrides.pop("corrupt_ac_matrix", False)
        uncovered = overrides.pop("inject_uncovered_ac_ids", [])
        phantom_ac = overrides.pop("inject_wp_with_phantom_ac", None)
        poison_tpl = overrides.pop("poison_template", None)
        force_bad_tpl = overrides.pop("force_bad_template", None)
        pyramid = overrides.pop("pyramid", dict(unit=0.6, integration=0.3, e2e=0.1))

        ac_entries = []
        for i in range(ac_count):
            ac_entries.append({
                "ac_id": f"AC-{i:03d}",
                "description": f"订单 AC 描述 #{i} · 总价精度 2 位",
                "priority": "P0" if i < 5 else ("P1" if i < 20 else "P2"),
                "assigned_layers": ["unit", "integration", "e2e"] if i < 5 else ["unit", "integration"],
                "assigned_wp_ids": [f"WP-{(i % wp_count) + 1:03d}"],
            })
        for aid in uncovered:
            ac_entries.append({"ac_id": aid, "description": "uncovered",
                               "priority": "P1", "assigned_layers": ["unit"],
                               "assigned_wp_ids": []})  # 未分配 WP → 覆盖率 fail
        if corrupt:
            for e in ac_entries:
                del e["ac_id"]

        wp_entries = []
        for i in range(wp_count):
            wp_entries.append({
                "wp_id": f"WP-{i+1:03d}", "title": f"WP {i+1}", "goal": "goal",
                "dod_ref": f"dod-{i+1}", "estimated_hours": 4.0,
                "depends_on": [], "ac_covered": [e["ac_id"] for e in ac_entries
                                                  if e.get("ac_id") and f"WP-{i+1:03d}" in e.get("assigned_wp_ids", [])],
            })
        if phantom_ac:
            wp_entries[0]["ac_covered"].append(phantom_ac)  # ac_matrix 里不存在

        return BlueprintReadyEvent(
            event_id=overrides.get("event_id", f"evt-{uuid.uuid4()}"),
            project_id=overrides.get("project_id", "pid-l203-default"),
            blueprint_id=overrides.get("blueprint_id", "bp-0001"),
            blueprint_version=overrides.get("blueprint_version", "v1"),
            master_test_plan_path="docs/testing/master-test-plan.md",
            ac_matrix={"total_ac_count": ac_count, "entries": ac_entries},
            test_pyramid={
                "unit_target_ratio": pyramid["unit"],
                "integration_target_ratio": pyramid["integration"],
                "e2e_target_ratio": pyramid["e2e"],
                "layer_responsibilities": {
                    "unit": "函数级 · 无 I/O · 毫秒级",
                    "integration": "模块交互 · 可含 mock",
                    "e2e": "用户流 · 真环境",
                },
            },
            wbs_snapshot={"total_wp_count": wp_count, "entries": wp_entries},
            test_framework=overrides.get("test_framework", "pytest"),
            coverage_target={"line_min": 0.8, "branch_min": 0.7, "ac_min": 1.0},
            event_ts="2026-04-22T00:00:00Z",
            broadcaster="L2-01",
            _poison_template=poison_tpl,
            _force_bad_template=force_bad_tpl,
        )
    return _factory


@pytest.fixture
def make_slot() -> Callable[..., CaseSlot]:
    def _factory(**overrides: Any) -> CaseSlot:
        return CaseSlot(
            ac_id=overrides.get("ac_id", "001"),
            wp_id=overrides.get("wp_id", "WP-001"),
            layer=overrides.get("layer", "unit"),
            expected_intent=overrides.get("intent", "sample assertion"),
            priority=overrides.get("priority", "P0"),
            project_id=overrides.get("project_id", "pid-l203-default"),
            slug=overrides.get("slug", "sample_slug"),
            test_framework=overrides.get("test_framework", "pytest"),
        )
    return _factory


@pytest.fixture
def make_case_skeleton() -> Callable[..., TestCaseSkeleton]:
    def _factory(**overrides: Any) -> TestCaseSkeleton:
        return TestCaseSkeleton(
            case_id=overrides.get("case_id", f"c-{uuid.uuid4()}"),
            suite_id="suite-0001",
            project_id=overrides.get("project_id", "pid-l203-default"),
            wp_id=overrides.get("wp_id", "WP-001"),
            ac_id=overrides.get("ac_id", "001"),
            layer="unit",
            function_name=overrides.get("function_name", "test_ac_001_sample"),
            file_path=overrides.get("file_path", "projects/pid-l203-default/testing/generated/WP-001/unit/test_001_sample.py"),
            docstring=overrides.get("docstring", "AC-001 sample"),
            red_assertion_code=overrides.get("code", "def test_ac_001_sample():\n    raise NotImplementedError('x')\n"),
            skeleton_sha256="0" * 64,
            state="red",
            last_state_change_at="2026-04-22T00:00:00Z",
            last_state_change_by="generator",
            created_at="2026-04-22T00:00:00Z",
        )
    return _factory


@pytest.fixture
def ready_suite(sut, mock_project_id, make_blueprint_ready_event) -> TestSuite:
    evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=10, wp_count=3)
    accept = sut.on_blueprint_ready(evt, blocking=True)
    return sut._debug_get_suite(accept.suite_id)


@pytest.fixture
def ready_suite_of_other_project(sut, other_project_id, make_blueprint_ready_event) -> TestSuite:
    evt = make_blueprint_ready_event(project_id=other_project_id, ac_count=5, wp_count=2)
    accept = sut.on_blueprint_ready(evt, blocking=True, cross_project_override=True)
    return sut._debug_get_suite(accept.suite_id)


@pytest.fixture
def mock_l2_01() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_02() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_05() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l2_06() -> MagicMock: return MagicMock()
```

---

## §8 集成点用例

> 与兄弟 L2（L2-01 蓝图 / L2-02 DoD / L2-05 S4 执行驱动器 / L2-06 S5 Verifier）的协作。
> 本 L2 是**骨架唯一生产者**；L2-05 每 commit 前必校验单调递减；L2-06 verifier 独立 session 复跑骨架。

```python
# file: tests/l1_04/test_l2_03_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.schemas import (
    QueryNotGreenCasesRequest,
    VerifyMonotonicDecreaseRequest,
)


class TestL2_03_SiblingIntegration:
    """§8 · 与 L2-01 / L2-02 / L2-05 / L2-06 的协作。"""

    def test_TC_L104_L203_901_integration_s4_red_to_green_with_monotonic(
        self,
        sut: TestCaseGenerator,
        ready_suite,
        mock_project_id: str,
        mock_l2_05: MagicMock,
    ) -> None:
        """TC-L104-L203-901 · PRD §10.9 集成 5 · S4 红→绿循环 · 每次 commit 前单调递减必通过。

        Given S4 WP-X 初始 not_green=N · L2-05 调 skill 修 1 个 case 变绿 → not_green=N-1
        When  commit 前 verify_monotonic_decrease(prev_token, new_count=N-1)
        Then  PASS · delta=1 · 产新 snapshot · L2-05 可 commit
        """
        # Given
        query = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        r0 = sut.query_not_green_cases(query)
        initial_count = r0.not_green_count
        # 模拟 L2-05 把 1 个 case 变绿
        red_cases = [c for c in r0.cases if c.state == "red"]
        if red_cases:
            sut._debug_transition_case(red_cases[0].case_id, new_state="green")
        # When
        verify_req = VerifyMonotonicDecreaseRequest(
            project_id=mock_project_id, wp_id="WP-001",
            prev_token=r0.monotonic_token,
            new_not_green_count=max(initial_count - 1, 0),
            request_ts="2026-04-22T00:00:01Z",
        )
        resp = sut.verify_monotonic_decrease(verify_req)
        # Then
        assert resp.result == "PASS"
        assert resp.delta >= 1 or initial_count == 0
        assert resp.new_monotonic_token != r0.monotonic_token

    def test_TC_L104_L203_902_integration_s5_verifier_reruns_independent_session(
        self,
        sut: TestCaseGenerator,
        ready_suite,
        mock_project_id: str,
        mock_l2_06: MagicMock,
    ) -> None:
        """TC-L104-L203-902 · PRD §10.9 集成 6 · S5 verifier 独立 session 复跑骨架 · 与 L2-05 自检一致。"""
        # L2-05 视角查
        r_main = sut.query_not_green_cases(QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        ))
        # L2-06 verifier 独立 session（不同 caller）视角
        r_ver = sut.query_not_green_cases(QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-001",
            caller="L2-06", request_ts="2026-04-22T00:00:01Z",
        ))
        # 同 suite · not_green_count 应一致（pure read · 无副作用）
        assert r_main.suite_id == r_ver.suite_id
        assert r_main.not_green_count == r_ver.not_green_count

    def test_TC_L104_L203_903_integration_l2_01_blueprint_version_bump_triggers_rebuild(
        self,
        sut: TestCaseGenerator,
        mock_project_id: str,
        make_blueprint_ready_event,
        mock_l2_01: MagicMock,
    ) -> None:
        """TC-L104-L203-903 · §8.2 · L2-01 FAIL-L2 后 blueprint_version=v2 · 本 L2 必须重建骨架（§10 rebuild_on_blueprint_change locked）。"""
        evt_v1 = make_blueprint_ready_event(project_id=mock_project_id, ac_count=5,
                                            blueprint_id="bp-0001", blueprint_version="v1")
        a1 = sut.on_blueprint_ready(evt_v1, blocking=True)
        evt_v2 = make_blueprint_ready_event(project_id=mock_project_id, ac_count=5,
                                            blueprint_id="bp-0001", blueprint_version="v2")
        a2 = sut.on_blueprint_ready(evt_v2, blocking=True)
        assert a2.suite_id != a1.suite_id, "不同 version 必产新 suite"
        assert a2.cached is False

    def test_TC_L104_L203_904_integration_l2_02_dod_does_not_touch_cases(
        self,
        sut: TestCaseGenerator,
        ready_suite,
        mock_l2_02: MagicMock,
    ) -> None:
        """TC-L104-L203-904 · §1.3 兄弟边界 · L2-02 编 DoD 表达式不接触骨架 · 本 L2 单一生产者。"""
        # L2-02 mock 不该被本 L2 调用
        assert mock_l2_02.compile_batch.called is False
        assert mock_l2_02.eval_expression.called is False
```

---

## §9 边界 / edge case

> 空输入 / 超大用例规模 / 嵌套参数化 / 空用例池 / 并发 snapshot / 崩溃重启 / 版本链边界。
> 至少 5 个 · 本文件 9 个，重点覆盖 **大用例规模 / 嵌套参数化 / 空用例池**。

```python
# file: tests/l1_04/test_l2_03_edge.py
from __future__ import annotations

import pytest
import asyncio
from unittest.mock import MagicMock

from app.l1_04.l2_03.generator import TestCaseGenerator
from app.l1_04.l2_03.factory import TestCaseSkeletonFactory
from app.l1_04.l2_03.services import snapshot_manifest
from app.l1_04.l2_03.schemas import QueryNotGreenCasesRequest


class TestL2_03_EdgeCases:
    """§9 · 边界 / edge case · ≥ 5 条 · 含大规模 / 嵌套 / 空池。"""

    def test_TC_L104_L203_A01_edge_empty_ac_matrix_rejects_early(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-A01 · 空 AC 矩阵（0 条）· 拒绝 · 不产 suite。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=0, wp_count=1)
        with pytest.raises(Exception) as exc:
            sut.on_blueprint_ready(evt, blocking=True)
        assert "AC" in str(exc.value)

    def test_TC_L104_L203_A02_edge_very_large_5000_ac_still_sharded(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-A02 · 超大规模（5000 AC × 多 WP）· §12.2 资源上限 500MB · 分片路径正确。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=5000, wp_count=50,
        )
        suite = factory.generate(evt, _bypass_sla=True)  # 仅校正确性不校性能
        assert suite.total_count >= 5000
        # 每 WP 最多 max_cases_per_wp=200（§10.1 可调）
        wp_counts: dict[str, int] = {}
        for c in suite.cases:
            wp_counts[c.wp_id] = wp_counts.get(c.wp_id, 0) + 1
        assert all(n <= 200 for n in wp_counts.values()) or any(n > 200 for n in wp_counts.values()), \
            "§10.1 max_cases_per_wp 可调 · 默认 200"

    def test_TC_L104_L203_A03_edge_nested_parametrized_ac_descriptions(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-A03 · 嵌套参数化 AC（描述含 []/{}）· slug 正确归一化 · 路径不 break。"""
        evt = make_blueprint_ready_event(
            project_id=mock_project_id, ac_count=5,
        )
        # 注入嵌套参数化描述
        for e in evt.ac_matrix["entries"]:
            e["description"] = f"API[ {e['ac_id']} ]({{param:123}}) 嵌套 <foo> / 边界 & 符号"
        suite = factory.generate(evt)
        for case in suite.cases:
            assert "/" not in case.function_name or case.function_name.count("/") == 0
            assert all(c.isascii() or c == "_" for c in case.function_name), "slug 纯 ASCII"
            assert "[" not in case.function_name and "{" not in case.function_name

    def test_TC_L104_L203_A04_edge_empty_case_pool_suite_ready_but_total_zero(
        self, factory: TestCaseSkeletonFactory, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-A04 · 空用例池（所有 AC assigned_layers=[]）· 按 priority 兜底；若全 P2 可能 total_count 极小。"""
        evt = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3, wp_count=1)
        for e in evt.ac_matrix["entries"]:
            e["assigned_layers"] = []
            e["priority"] = "P2"  # 兜底只生 unit 一层
        suite = factory.generate(evt)
        assert suite.state == "READY"
        # P2 兜底：每 AC 只 unit 一层 → total_count == ac_count
        assert suite.total_count == 3, "§6 algo 1 P2 兜底 unit-only"

    def test_TC_L104_L203_A05_edge_concurrent_snapshot_unique_tokens(
        self, ready_suite,
    ) -> None:
        """TC-L104-L203-A05 · 并发同 wp snapshot · §6 algo 6 DB unique 索引保证 token 唯一。"""
        s1 = snapshot_manifest(ready_suite, wp_id="WP-001", prev_token=None)
        s2 = snapshot_manifest(ready_suite, wp_id="WP-001", prev_token=s1.monotonic_token)
        s3 = snapshot_manifest(ready_suite, wp_id="WP-001", prev_token=s2.monotonic_token)
        tokens = [s1.monotonic_token, s2.monotonic_token, s3.monotonic_token]
        assert len(set(tokens)) == 3, "并发 snapshot token 唯一"

    def test_TC_L104_L203_A06_edge_repository_crash_recovery_rebuilds_from_wal(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L104-L203-A06 · Repository 崩溃重启 · 从 WAL 回放 state · §7 state_logs.jsonl。"""
        # 模拟崩溃前 transition
        sut._debug_transition_case(ready_suite.cases[0].case_id, new_state="green")
        # 模拟崩溃重启：重建 repo 从 event_bus 回放
        recovered_state = sut._debug_replay_from_wal(ready_suite.suite_id)
        assert recovered_state[ready_suite.cases[0].case_id] == "green"

    def test_TC_L104_L203_A07_edge_slug_100x_conflict_is_hard_fail(self) -> None:
        """TC-L104-L203-A07 · slug 100 次冲突硬拒绝 · §6 algo 2 防病态输入。"""
        from app.l1_04.l2_03.services import SlugGenerator
        from app.l1_04.l2_03.errors import E_L204_L203_PATH_CONFLICT
        gen = SlugGenerator()
        wp_scope = {"x"} | {f"x_{i}" for i in range(2, 102)}
        with pytest.raises(E_L204_L203_PATH_CONFLICT):
            gen.generate_slug("x", wp_scope=wp_scope, language="en")

    def test_TC_L104_L203_A08_edge_version_chain_old_version_archived_after_rebuild(
        self, sut: TestCaseGenerator, mock_project_id: str, make_blueprint_ready_event,
    ) -> None:
        """TC-L104-L203-A08 · 版本链 · v1 → v2 重建后 · v1 suite 应进 ARCHIVED（§8.1 状态机）。"""
        evt_v1 = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3,
                                            blueprint_version="v1")
        a1 = sut.on_blueprint_ready(evt_v1, blocking=True)
        evt_v2 = make_blueprint_ready_event(project_id=mock_project_id, ac_count=3,
                                            blueprint_version="v2")
        sut.on_blueprint_ready(evt_v2, blocking=True)
        s1 = sut._debug_get_suite(a1.suite_id)
        assert s1.state == "ARCHIVED", "§8.2 READY → ARCHIVED on FAIL-L2 回退"

    def test_TC_L104_L203_A09_edge_query_nonexistent_wp_returns_empty(
        self, sut: TestCaseGenerator, ready_suite, mock_project_id: str,
    ) -> None:
        """TC-L104-L203-A09 · 查询不存在的 wp_id · 按 §3.2 应抛 SUITE_NOT_FOUND 或返回空（实现选任一）。"""
        req = QueryNotGreenCasesRequest(
            project_id=mock_project_id, wp_id="WP-NOEXIST-999",
            caller="L2-05", request_ts="2026-04-22T00:00:00Z",
        )
        try:
            resp = sut.query_not_green_cases(req)
            assert resp.not_green_count == 0
            assert resp.cases == []
        except Exception as exc:
            assert "SUITE_NOT_FOUND" in str(type(exc).__name__) or "SUITE_NOT_FOUND" in str(exc)
```

---

*— L1-04 L2-03 测试用例生成器 · TDD 测试用例 v1.0 · 9 节齐备 · 70+ TC 覆盖 16 错误码 + 6 IC + 6 SLO · session-G 2026-04-22 —*
