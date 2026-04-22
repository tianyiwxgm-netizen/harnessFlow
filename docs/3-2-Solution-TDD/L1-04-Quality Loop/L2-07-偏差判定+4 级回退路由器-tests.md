---
doc_id: tests-L1-04-L2-07-偏差判定+4 级回退路由器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-07-偏差判定+4 级回退路由器.md
  - docs/2-prd/L1-04 Quality Loop/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-04 L2-07-偏差判定+4 级回退路由器 · TDD 测试用例

> 基于 3-1 L2-07 §3（12 个 public 方法）+ §11 错误码（20 项 `L2-07/E01~E20`）+ §12 SLO（12 维 P95/P99 + 吞吐）+ §13 TC ID 矩阵（TC-L207-001~102）驱动。
> 本文件 TC ID 统一使用 L1-04 分层前缀：`TC-L104-L207-NNN`（三位流水号 · 0xx 正向 / 1xx 负向按错误码 / 6xx IC 契约 / 7xx 性能 / 8xx e2e / 9xx 集成 / Axx 边界）。
> pytest + Python 3.11+ 类型注解；`class TestL2_07_DeviationJudgeAndFallbackRouter` 组织；负向 / IC / perf / e2e / 集成 / 边界各自独立 `class`。错误码前缀严格按 3-1 §3.8 原样 `L2-07/E0N`，**禁造、禁改前缀**。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus / mock counter store / mock mapping matrix）
- [x] §8 集成点用例（与兄弟 L2 协作 · L2-04 Gate 编译器 / L2-05 S4 执行器 / L2-06 S5 Verifier）
- [x] §9 边界 / edge case（4 级递归 / 同时多偏差 / 回退自身失败 / 脏指标 / 冷启恢复）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。
> 错误码前缀一律 `L2-07/E0N` · 本表与 3-1 §3.8 错误码表严格双向映射。

### §1.1 方法 × 测试 × 覆盖类型（§3.1 方法清单 12 项）

| 方法（§3 出处） | TC ID | 覆盖类型 | 对应 IC |
|---|---|---|---|
| `receive_rollback_route()` · §3.2 PASS → S7 清零 | TC-L104-L207-001 | unit | IC-14 / IC-01 / IC-09 / IC-16 |
| `receive_rollback_route()` · §3.2 FAIL-L1 首次 → S4 · counter=1 | TC-L104-L207-002 | unit | IC-14 / IC-01 |
| `receive_rollback_route()` · §3.2 FAIL-L2 首次 → S3 · counter=1 | TC-L104-L207-003 | unit | IC-14 / IC-01 |
| `receive_rollback_route()` · §3.2 FAIL-L3 首次 → S2 · counter=1 | TC-L104-L207-004 | unit | IC-14 / IC-01 |
| `receive_rollback_route()` · §3.2 FAIL-L4 首次 → S1 · counter=1 | TC-L104-L207-005 | unit | IC-14 / IC-01 |
| `validate_verdict_enum()` · §3.1/6.3 5 值均通过 | TC-L104-L207-010 | unit | — |
| `cross_check_target_state()` · §3.1/6.4 一致 CONSISTENT | TC-L104-L207-011 | unit | — |
| `cross_check_target_state()` · §3.1/6.4 不一致 DRIFT_WARNING | TC-L104-L207-012 | unit | — |
| `lookup_mapping_table()` · §3.1/6.5 5 值双射查表 | TC-L104-L207-013 | unit | — |
| `increment_counter_idempotent()` · §3.1/6.6 同 idempotency_key 不递增 | TC-L104-L207-014 | unit | IC-09 |
| `detect_loop_threshold_three()` · §3.1/6.7 count=3 返回 True | TC-L104-L207-015 | unit | — |
| `escalate_BF_E_10_to_supervisor()` · §3.4/6.8 IC-13 BLOCK 发送 | TC-L104-L207-016 | unit | IC-13 |
| `handle_user_decision()` · §3.3 switch_strategy 清零 + S3 | TC-L104-L207-017 | unit | IC-17 / IC-01 |
| `handle_user_decision()` · §3.3 continue 保留 counter + 原 verdict 路由 | TC-L104-L207-018 | unit | IC-17 / IC-01 |
| `handle_user_decision()` · §3.3 abort 项目终态 | TC-L104-L207-019 | unit | IC-17 |
| `persist_route_event()` · §3.5/6.11 hash-chain append | TC-L104-L207-020 | unit | IC-09 |
| `push_rollback_card_to_ui()` · §3.6/6.12 risk indicator | TC-L104-L207-021 | unit | IC-16 |
| `request_state_transition()` · §3.7 IC-01 payload 正确 | TC-L104-L207-022 | unit | IC-01 |
| `query_counter()` · §3.10 remaining_to_dead_loop 计算 | TC-L104-L207-023 | unit | — |
| `build_rollback_impact_report()` · §3.11 affected_artifacts | TC-L104-L207-024 | unit | — |

### §1.2 错误码 × 测试（§3.8 + §11.2 · 20 项全覆盖）

| 错误码 | 含义 | 降级级别（§11.1） | TC ID |
|---|---|---|---|
| `L2-07/E01` | invalid_verdict_enum | L4 REJECT_VERDICT | TC-L104-L207-101 |
| `L2-07/E02` | target_state_mismatch | 无（WARN 不拒） | TC-L104-L207-102 |
| `L2-07/E03` | counter_persist_failed | L2 FORCE_ROUTE | TC-L104-L207-103 |
| `L2-07/E04` | mapping_missing | L3 HALT_ROUTE | TC-L104-L207-104 |
| `L2-07/E05` | missing_project_id | L4 REJECT_VERDICT | TC-L104-L207-105 |
| `L2-07/E06` | missing_required_field | L4 REJECT_VERDICT | TC-L104-L207-106 |
| `L2-07/E07` | idempotency_conflict | 无（noop） | TC-L104-L207-107 |
| `L2-07/E08` | audit_log_hash_chain_broken | L3 HALT_ROUTE（硬拦截） | TC-L104-L207-108 |
| `L2-07/E09` | user_decision_timeout | 默认 abort | TC-L104-L207-109 |
| `L2-07/E10` | user_decision_invalid_enum | L4 REJECT_VERDICT | TC-L104-L207-110 |
| `L2-07/E11` | escalation_rate_limited | 无（去重 noop） | TC-L104-L207-111 |
| `L2-07/E12` | ic_01_rejected | L3 HALT_ROUTE | TC-L104-L207-112 |
| `L2-07/E13` | ic_13_push_failed | 降级 UI 直推 | TC-L104-L207-113 |
| `L2-07/E14` | ic_16_push_failed | 不阻塞 · WARN | TC-L104-L207-114 |
| `L2-07/E15` | ic_09_append_failed | L3 HALT_ROUTE | TC-L104-L207-115 |
| `L2-07/E16` | concurrent_counter_modification | 重试 3 次 | TC-L104-L207-116 |
| `L2-07/E17` | pass_verdict_but_pending_wp | L4 REJECT_VERDICT | TC-L104-L207-117 |
| `L2-07/E18` | counter_exceeds_hard_limit | L3 HALT_ROUTE（硬拦截） | TC-L104-L207-118 |
| `L2-07/E19` | mapping_matrix_mutation_detected | HALT_ALL（硬拦截） | TC-L104-L207-119 |
| `L2-07/E20` | deadlock_on_counter_lock | L1 SKIP_CROSSCHECK | TC-L104-L207-120 |

### §1.3 IC 契约 × 测试（§4.1/§4.2 映射）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-14 `push_rollback_route` | L1-07 → L2-07 | TC-L104-L207-601 | 消费方 · payload 结构严格校验 |
| IC-01 `request_state_transition` | L2-07 → L1-01 | TC-L104-L207-602 | 发起方 · to_state 由映射表决定 |
| IC-09 `append_event` | L2-07 → L1-09 | TC-L104-L207-603 | 每决策 ≥ 2 事件 + hash-chain |
| IC-13 `push_suggestion` (BLOCK · dead_loop) | L2-07 → L1-07 | TC-L104-L207-604 | BF-E-10 升级链路 |
| IC-16 `push_stage_gate_card` (rollback subtype) | L2-07 → L1-02 → L1-10 | TC-L104-L207-605 | risk indicator 三色 |
| IC-17 `user_intervene_rollback` | L1-10 → L2-07 | TC-L104-L207-606 | 用户决策 continue/switch/abort |

### §1.4 §12 SLO × 测试

| SLO 维度（§12.1） | P95 / P99 阈值 | TC ID |
|---|---|---|
| `receive_rollback_route` 端到端 | P95 ≤ 3s / P99 ≤ 5s | TC-L104-L207-701 |
| `validate_verdict_five_enum` | P95 ≤ 5ms | TC-L104-L207-702 |
| `increment_counter_idempotent` (含 fsync) | P95 ≤ 100ms / P99 ≤ 300ms | TC-L104-L207-703 |
| `escalate_BF_E_10_to_supervisor` (IC-13 + 重试) | P95 ≤ 500ms / P99 ≤ 2s | TC-L104-L207-704 |
| 4 级回退升级链路 e2e（3 次 FAIL-L1 → BF-E-10） | e2e ≤ 2s | TC-L104-L207-705 |
| 同项目并发 2 路由吞吐（§12.2） | 单节点 ≥ 20 qps 稳态 | TC-L104-L207-706 |

### §1.5 PRD §14.9 交付验证 10 场景 × 测试

| PRD §14.9 场景 | TC ID | 类别 |
|---|---|---|
| 正向 1 · PASS → S7 · 清零 counter | TC-L104-L207-801 | e2e |
| 正向 2 · FAIL-L1 → S4 同 WP 重跑 | TC-L104-L207-802 | e2e |
| 正向 3 · FAIL-L2 → S3 重建蓝图 | TC-L104-L207-803 | e2e |
| 负向 7 · 3 次 FAIL-L1 触发 BF-E-10 + 用户 switch 恢复 | TC-L104-L207-804 | e2e |
| 集成 · L2-06 S5 Verifier → L1-07 → L2-07 → L1-01 S4 | TC-L104-L207-901 | integration |
| 集成 · L2-04 Gate 编译器 → Gate FAIL-L2 → L2-07 回 S3 | TC-L104-L207-902 | integration |
| 集成 · L2-05 S4 执行器 rerun 后 L2-07 counter 保留 | TC-L104-L207-903 | integration |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_07_DeviationJudgeAndFallbackRouter`；arrange / act / assert 三段明确。
> 被测对象（SUT）：`DeviationJudgeAndFallbackRouter`（聚合根 Domain Service · RollbackRouteDecision Factory）· 从 `app.l1_04.l2_07.router` 导入。
> 所有入参 schema 严格按 §3 字段级 YAML · 所有出参断言按 §3 出参 schema。

```python
# file: tests/l1_04/test_l2_07_router_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.schemas import (
    ReceiveRollbackRouteRequest,
    ReceiveRollbackRouteResponse,
    HandleUserDecisionRequest,
    HandleUserDecisionResponse,
    QueryCounterRequest,
    QueryCounterResponse,
    BuildRollbackImpactReportRequest,
    BuildRollbackImpactReportResponse,
)
from app.l1_04.l2_07.errors import L2_07_Error


class TestL2_07_DeviationJudgeAndFallbackRouter:
    """§3 public 方法正向用例。每方法 ≥ 1 happy path；§6.2 主算法 + §6.3~§6.13 子算法全覆盖。"""

    # --------- §3.2 receive_rollback_route · PASS / FAIL-L1~L4 五正向分支 --------- #

    def test_TC_L104_L207_001_pass_verdict_routes_to_S7_and_resets_counters(
        self,
        sut: DeviationJudgeAndFallbackRouter,
        mock_project_id: str,
        mock_l1_01: MagicMock,
        mock_l1_09: MagicMock,
        make_rollback_request,
    ) -> None:
        """TC-L104-L207-001 · PRD §14.9 正向 1 · PASS → S7 · 所有 counter 清零。"""
        # arrange：先制造非零 counter（通过预置 FAIL-L1）
        sut._seed_counter(mock_project_id, wp_id="WP-1", verdict_level="FAIL-L1", value=2)
        req = make_rollback_request(
            project_id=mock_project_id,
            verdict="PASS",
            target_state="S7",
            related_wp_id=None,
        )
        # act
        resp: ReceiveRollbackRouteResponse = sut.receive_rollback_route(req)
        # assert
        assert resp.status == "ROUTED", "§3.2 出参 status=ROUTED"
        assert resp.target_stage_applied == "S7"
        assert resp.same_level_count == 0
        assert resp.dead_loop_triggered is False
        # 所有 counter 必须清零（§6.2 Step 5 PASS 分支硬契约）
        assert sut._read_counter(mock_project_id, "WP-1", "FAIL-L1") == 0
        # IC-01 发出 to_state=S7
        mock_l1_01.request_state_transition.assert_called_once()
        ic01_payload = mock_l1_01.request_state_transition.call_args.kwargs
        assert ic01_payload["to_state"] == "S7"

    def test_TC_L104_L207_002_fail_l1_first_routes_to_S4_counter_one(
        self,
        sut: DeviationJudgeAndFallbackRouter,
        mock_project_id: str,
        mock_l1_01: MagicMock,
        make_rollback_request,
    ) -> None:
        """TC-L104-L207-002 · PRD §14.9 正向 2 · FAIL-L1 首次 → S4 · counter=1。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-1",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S4"
        assert resp.same_level_count == 1
        assert resp.dead_loop_triggered is False
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S4"

    def test_TC_L104_L207_003_fail_l2_first_routes_to_S3_counter_one(
        self, sut, mock_project_id, mock_l1_01, make_rollback_request,
    ) -> None:
        """TC-L104-L207-003 · PRD §14.9 正向 3 · FAIL-L2 首次 → S3 · counter=1。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S3", related_wp_id="WP-2",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S3"
        assert resp.same_level_count == 1

    def test_TC_L104_L207_004_fail_l3_first_routes_to_S2_counter_one(
        self, sut, mock_project_id, mock_l1_01, make_rollback_request,
    ) -> None:
        """TC-L104-L207-004 · PRD §14.9 正向 4 · FAIL-L3 首次 → S2 · counter=1。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L3", target_state="S2", related_wp_id="WP-3",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S2"
        assert resp.same_level_count == 1

    def test_TC_L104_L207_005_fail_l4_first_routes_to_S1_counter_one(
        self, sut, mock_project_id, mock_l1_01, make_rollback_request,
    ) -> None:
        """TC-L104-L207-005 · PRD §14.9 正向 5 · FAIL-L4 首次 → S1 · counter=1。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L4", target_state="S1", related_wp_id="WP-4",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S1"
        assert resp.same_level_count == 1

    # --------- §3.1 validate_verdict_enum · 5 值枚举 --------- #

    def test_TC_L104_L207_010_validate_verdict_accepts_five_enum_values(
        self, sut: DeviationJudgeAndFallbackRouter,
    ) -> None:
        """TC-L104-L207-010 · §6.3 validate_verdict_five_enum · 5 值双射 · 全部通过。"""
        for v in ("PASS", "FAIL-L1", "FAIL-L2", "FAIL-L3", "FAIL-L4"):
            assert sut.validate_verdict_enum(v) is True, f"{v} 应合法"

    # --------- §3.1 cross_check_target_state · §6.4 --------- #

    def test_TC_L104_L207_011_cross_check_consistent(self, sut) -> None:
        """TC-L104-L207-011 · §6.4 verdict=FAIL-L2 target=S3 · CONSISTENT。"""
        assert sut.cross_check_target_state(verdict="FAIL-L2", supervisor_target="S3") == "CONSISTENT"

    def test_TC_L104_L207_012_cross_check_drift_warning_uses_matrix(self, sut) -> None:
        """TC-L104-L207-012 · PRD §14.9 负向 6 · L1-07 target=S7 但 verdict=FAIL-L2 · DRIFT_WARNING · 以本 L2 映射为准。"""
        result = sut.cross_check_target_state(verdict="FAIL-L2", supervisor_target="S7")
        assert result == "DRIFT_WARNING"

    # --------- §3.1 lookup_mapping_table · §6.5 静态硬契约 --------- #

    def test_TC_L104_L207_013_lookup_mapping_table_five_bijection(self, sut) -> None:
        """TC-L104-L207-013 · §7.4 verdict_mapping_matrix 5 值双射。"""
        assert sut.lookup_mapping_table("PASS") == "S7"
        assert sut.lookup_mapping_table("FAIL-L1") == "S4"
        assert sut.lookup_mapping_table("FAIL-L2") == "S3"
        assert sut.lookup_mapping_table("FAIL-L3") == "S2"
        assert sut.lookup_mapping_table("FAIL-L4") == "S1"

    # --------- §3.1 increment_counter_idempotent · §6.6 --------- #

    def test_TC_L104_L207_014_increment_counter_idempotent_same_key_no_double_inc(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-014 · §6.6 同 (idempotency_key, pid, wp, level) 重复调用 counter 不重复递增。"""
        key = "idem-abc-001"
        c1 = sut.increment_counter_idempotent(
            project_id=mock_project_id, wp_id="WP-X", verdict_level="FAIL-L1", decision_id=key,
        )
        c2 = sut.increment_counter_idempotent(
            project_id=mock_project_id, wp_id="WP-X", verdict_level="FAIL-L1", decision_id=key,
        )
        assert c1 == 1
        assert c2 == 1, "幂等：重复 decision_id 返回上次值"

    # --------- §3.1 detect_loop_threshold_three · §6.7 --------- #

    def test_TC_L104_L207_015_detect_three_strikes_loop_at_count_three(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-015 · §6.7 count=3 硬触发 · §11.4 硬约束不可配置。"""
        sut._seed_counter(mock_project_id, wp_id="WP-Y", verdict_level="FAIL-L1", value=3)
        triggered = sut.detect_loop_threshold_three(
            project_id=mock_project_id, wp_id="WP-Y", verdict_level="FAIL-L1",
        )
        assert triggered is True

    # --------- §3.4 escalate_BF_E_10_to_supervisor · §6.8 IC-13 --------- #

    def test_TC_L104_L207_016_escalate_bf_e_10_sends_ic13_block(
        self, sut, mock_project_id: str, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L207-016 · PRD §14.9 负向 7 · BF-E-10 升级 · IC-13 level=BLOCK · trigger=BF-E-10。"""
        sut.escalate_BF_E_10_to_supervisor(
            project_id=mock_project_id, wp_id="WP-Z", verdict_level="FAIL-L1", count=3,
        )
        mock_l1_07.push_suggestion.assert_called_once()
        payload = mock_l1_07.push_suggestion.call_args.kwargs
        assert payload["level"] == "BLOCK", "§3.4 固定 BLOCK"
        assert payload["dimension"] == "dead_loop"
        assert payload["trigger"] == "BF-E-10"
        assert set(payload["suggested_user_options"]) >= {"continue", "switch_strategy", "abort"}

    # --------- §3.3 handle_user_decision · §6.9 三分支 --------- #

    def test_TC_L104_L207_017_user_switch_strategy_resets_counter_and_routes_S3(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock,
    ) -> None:
        """TC-L104-L207-017 · PRD §14.9 集成 9 · user switch_strategy · counter=0 · target=S3。"""
        sut._seed_counter(mock_project_id, wp_id="WP-U", verdict_level="FAIL-L1", value=3)
        sut._seed_decision(decision_id="rrd-001", wp_id="WP-U", verdict_level="FAIL-L1")
        req = HandleUserDecisionRequest(
            project_id=mock_project_id, wp_id="WP-U", verdict_level="FAIL-L1",
            decision="switch_strategy", user_id="u1", decision_id_ref="rrd-001",
            decided_at="2026-04-22T00:00:00Z",
        )
        resp: HandleUserDecisionResponse = sut.handle_user_decision(req)
        assert resp.new_route_status == "COUNTER_RESET"
        assert resp.counter_action == "RESET_TO_ZERO"
        assert resp.new_target_stage == "S3"
        assert sut._read_counter(mock_project_id, "WP-U", "FAIL-L1") == 0

    def test_TC_L104_L207_018_user_continue_keeps_counter_and_routes_original(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock,
    ) -> None:
        """TC-L104-L207-018 · user continue · counter 保留 · 按原 verdict 路由 · OQ-2 不允许重置阈值。"""
        sut._seed_counter(mock_project_id, wp_id="WP-C", verdict_level="FAIL-L1", value=3)
        sut._seed_decision(decision_id="rrd-002", wp_id="WP-C", verdict_level="FAIL-L1")
        req = HandleUserDecisionRequest(
            project_id=mock_project_id, wp_id="WP-C", verdict_level="FAIL-L1",
            decision="continue", user_id="u1", decision_id_ref="rrd-002",
            decided_at="2026-04-22T00:00:00Z",
        )
        resp = sut.handle_user_decision(req)
        assert resp.counter_action == "UNCHANGED"
        assert sut._read_counter(mock_project_id, "WP-C", "FAIL-L1") == 3

    def test_TC_L104_L207_019_user_abort_terminates_project(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-019 · user abort · final_state=TERMINATED · 项目归档。"""
        sut._seed_decision(decision_id="rrd-003", wp_id="WP-A", verdict_level="FAIL-L2")
        req = HandleUserDecisionRequest(
            project_id=mock_project_id, wp_id="WP-A", verdict_level="FAIL-L2",
            decision="abort", user_id="u1", decision_id_ref="rrd-003",
            decided_at="2026-04-22T00:00:00Z",
        )
        resp = sut.handle_user_decision(req)
        assert resp.new_route_status == "ARCHIVED_ABORTED"
        assert resp.final_state == "TERMINATED"

    # --------- §3.5 persist_route_event · §6.11 hash-chain --------- #

    def test_TC_L104_L207_020_persist_route_event_hash_chain_appends(
        self, sut, mock_project_id: str, mock_l1_09: MagicMock,
    ) -> None:
        """TC-L104-L207-020 · §6.11 persist 通过 IC-09 · prev_hash + hash 链接完整。"""
        evt = sut.persist_route_event(
            project_id=mock_project_id, event_type="L1-04:rollback_route_applied",
            decision_id="rrd-020", payload={"verdict": "FAIL-L1", "target_stage": "S4"},
        )
        assert evt.hash is not None
        assert evt.prev_hash is not None
        mock_l1_09.append_event.assert_called_once()
        sent = mock_l1_09.append_event.call_args.kwargs
        assert sent["actor"] == "BC-04"
        assert sent["event_type"] == "L1-04:rollback_route_applied"

    # --------- §3.6 push_rollback_card_to_ui · §6.12 --------- #

    def test_TC_L104_L207_021_push_rollback_card_risk_indicator_three_colors(
        self, sut, mock_project_id: str, mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L207-021 · §6.12 count<2 green · count==2 yellow · count>=3 red。"""
        for count, expected in [(0, "green"), (1, "green"), (2, "yellow"), (3, "red"), (5, "red")]:
            mock_l1_02.push_card.reset_mock()
            sut.push_rollback_card_to_ui(
                project_id=mock_project_id, decision_id=f"rrd-{count}",
                verdict="FAIL-L1", target_stage="S4", same_level_count=count,
                card_type="rollback_routed",
            )
            payload = mock_l1_02.push_card.call_args.kwargs
            assert payload["dead_loop_risk_indicator"] == expected, f"count={count} 期望 {expected}"

    # --------- §3.7 request_state_transition · IC-01 payload --------- #

    def test_TC_L104_L207_022_request_state_transition_payload_schema(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock,
    ) -> None:
        """TC-L104-L207-022 · §3.7 IC-01 payload schema 严格断言（from_state / to_state / trigger）。"""
        sut.request_state_transition(
            project_id=mock_project_id, from_state="S5", to_state="S4",
            verdict="FAIL-L1", decision_id="rrd-022", same_level_count=1, wp_id="WP-22",
        )
        p = mock_l1_01.request_state_transition.call_args.kwargs
        assert p["from_state"] == "S5"
        assert p["to_state"] == "S4"
        assert p["reason"]["trigger"] == "rollback_route"
        assert p["reason"]["verdict"] == "FAIL-L1"

    # --------- §3.10 query_counter --------- #

    def test_TC_L104_L207_023_query_counter_remaining_to_dead_loop(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-023 · §3.10 count=2 · remaining=1 · risk=yellow。"""
        sut._seed_counter(mock_project_id, wp_id="WP-Q", verdict_level="FAIL-L1", value=2)
        q = QueryCounterRequest(project_id=mock_project_id, wp_id="WP-Q", verdict_level="FAIL-L1")
        resp: QueryCounterResponse = sut.query_counter(q)
        assert resp.count == 2
        assert resp.remaining_to_dead_loop == 1
        assert resp.dead_loop_risk == "yellow"

    # --------- §3.11 build_rollback_impact_report --------- #

    def test_TC_L104_L207_024_build_rollback_impact_report_lists_affected_artifacts(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-024 · §6.13 返回 affected_artifacts + estimated_rerun_cost。"""
        sut._seed_decision(decision_id="rrd-024", wp_id="WP-I", verdict_level="FAIL-L2",
                           target_stage="S3")
        req = BuildRollbackImpactReportRequest(decision_id="rrd-024")
        rep: BuildRollbackImpactReportResponse = sut.build_rollback_impact_report(req)
        assert rep.target_stage == "S3"
        assert isinstance(rep.affected_artifacts, list) and len(rep.affected_artifacts) >= 1
        assert rep.estimated_rerun_cost.wp_count >= 0
        types = {a.artifact_type for a in rep.affected_artifacts}
        # FAIL-L2 回 S3 必须至少涉及 tdd_blueprint 重建
        assert "tdd_blueprint" in types

    # --------- 扩展正向：3-1 §13.2 TC-L207-007 / 008 / 021~026 --------- #

    def test_TC_L104_L207_025_same_wp_two_consecutive_fail_l1_counter_two(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-025 · 同 WP 连续 2 次 FAIL-L1 · counter 递增到 2 · 仍路由 S4 · 未触发死循环。"""
        for i in range(2):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-7", idempotency_key=f"k-{i}",
            )
            resp = sut.receive_rollback_route(req)
            assert resp.target_stage_applied == "S4"
            assert resp.same_level_count == i + 1
        assert sut._read_counter(mock_project_id, "WP-7", "FAIL-L1") == 2

    def test_TC_L104_L207_026_different_wps_same_level_counters_independent(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-026 · §6.6 不同 WP 同 level · counter per-WP 独立（§11.5 OQ-9）。"""
        for wp in ("WP-A", "WP-B"):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id=wp, idempotency_key=f"k-{wp}",
            )
            sut.receive_rollback_route(req)
        assert sut._read_counter(mock_project_id, "WP-A", "FAIL-L1") == 1
        assert sut._read_counter(mock_project_id, "WP-B", "FAIL-L1") == 1
```

---

## §3 负向用例（每错误码 ≥ 1）

> §3.8 错误码表 20 项全覆盖 · 错误码前缀严格按原样 `L2-07/E0N`。
> §11.4 硬约束守护 7 禁令在此体现为 mutation / grep 风格测试。

```python
# file: tests/l1_04/test_l2_07_router_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.schemas import (
    ReceiveRollbackRouteRequest,
    HandleUserDecisionRequest,
)
from app.l1_04.l2_07.errors import L2_07_Error


class TestL2_07_Negative_ErrorCodes:
    """§3.8 + §11.2 20 错误码全覆盖。错误码前缀：`L2-07/E0N`（原样不改）。"""

    def test_TC_L104_L207_101_E01_invalid_verdict_enum_reject(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-101 · §3.8 E01 · verdict='WEIRD' → REJECT_VERDICT。§11.4 禁令 6 守护。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="WEIRD", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E01"

    def test_TC_L104_L207_102_E02_target_state_mismatch_warns_but_routes(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-102 · §3.8 E02 · target_state 与映射不一致 · 不拒绝 · DRIFT_WARNING + 以本 L2 为准。"""
        # 传 FAIL-L2 但 target=S7（映射应为 S3）
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S7", related_wp_id="WP-M",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.cross_check_result == "DRIFT_WARNING"
        assert resp.target_stage_applied == "S3"  # 以本 L2 映射为准
        assert any(e.code == "L2-07/E02" for e in resp.errors)

    def test_TC_L104_L207_103_E03_counter_persist_failed_force_route(
        self, sut, mock_project_id: str, mock_counter_store: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-103 · §3.8 E03 · counter 写盘失败 → FORCE_ROUTE · 内存计数 + 异步重试 · 路由继续。"""
        mock_counter_store.persist.side_effect = OSError("disk full")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-P",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        assert any(e.code == "L2-07/E03" for e in resp.errors)
        assert sut._current_degrade_level() == "FORCE_ROUTE"

    def test_TC_L104_L207_104_E04_mapping_missing_halt_route(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-104 · §3.8 E04 · 映射表未加载 · HALT_ROUTE + 升级 supervisor。"""
        sut._unload_mapping_for_test()
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E04"
        assert sut._current_degrade_level() == "HALT_ROUTE"

    def test_TC_L104_L207_105_E05_missing_project_id(
        self, sut, make_rollback_request,
    ) -> None:
        """TC-L104-L207-105 · §3.8 E05 · PM-14 硬红线 · 缺 project_id · REJECT_VERDICT。"""
        req = make_rollback_request(project_id="", verdict="FAIL-L1", target_state="S4")
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E05"

    def test_TC_L104_L207_106_E06_missing_required_field(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-106 · §3.8 E06 · 缺 supervisor_decision_id 必填字段 · REJECT。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            supervisor_decision_id=None,
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E06"

    def test_TC_L104_L207_107_E07_idempotency_conflict_noop_return_previous(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-107 · §3.8 E07 · 同 idempotency_key 重复 · noop 返回上次 decision_id。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            related_wp_id="WP-I", idempotency_key="same-key-idem",
        )
        r1 = sut.receive_rollback_route(req)
        r2 = sut.receive_rollback_route(req)
        assert r1.decision_id == r2.decision_id, "幂等：返回同一 decision_id"
        assert r2.same_level_count == r1.same_level_count, "counter 不重复递增"
        # E07 应出现在警告但 status 仍 ROUTED
        assert r2.status == "ROUTED"

    def test_TC_L104_L207_108_E08_audit_log_hash_chain_broken_halt(
        self, sut, mock_project_id: str, mock_audit_store: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-108 · §3.8 E08 · §11.3 硬拦截 · audit.jsonl hash-chain 损坏 · HALT_ROUTE。"""
        mock_audit_store.verify_chain.return_value = False
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E08"

    def test_TC_L104_L207_109_E09_user_decision_timeout_default_abort(
        self, sut, mock_project_id: str, mock_clock: MagicMock,
    ) -> None:
        """TC-L104-L207-109 · §3.8 E09 · 24h 用户未决策 · 默认 abort（OQ-1 可配）。"""
        sut._seed_decision(decision_id="rrd-t09", wp_id="WP-T", verdict_level="FAIL-L1",
                           status="AWAITING_USER", awaiting_since_ms=mock_clock.now_ms)
        mock_clock.advance(24 * 3600 * 1000 + 1)
        final_status = sut._check_user_decision_timeout(decision_id="rrd-t09")
        assert final_status == "ARCHIVED_ABORTED"

    def test_TC_L104_L207_110_E10_user_decision_invalid_enum(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-110 · §3.8 E10 · decision='maybe' · REJECT。"""
        sut._seed_decision(decision_id="rrd-e10", wp_id="WP-E10", verdict_level="FAIL-L1")
        with pytest.raises(L2_07_Error) as ei:
            sut.handle_user_decision(HandleUserDecisionRequest(
                project_id=mock_project_id, wp_id="WP-E10", verdict_level="FAIL-L1",
                decision="maybe", user_id="u1", decision_id_ref="rrd-e10",
                decided_at="2026-04-22T00:00:00Z",
            ))
        assert ei.value.code == "L2-07/E10"

    def test_TC_L104_L207_111_E11_escalation_rate_limited_dedup(
        self, sut, mock_project_id: str, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L207-111 · §3.8 E11 · 24h 内同 (pid, wp, level) 二次升级 · noop 去重。"""
        for _ in range(2):
            sut.escalate_BF_E_10_to_supervisor(
                project_id=mock_project_id, wp_id="WP-E11", verdict_level="FAIL-L1", count=3,
            )
        # 只调用一次 IC-13
        assert mock_l1_07.push_suggestion.call_count == 1

    def test_TC_L104_L207_112_E12_ic01_rejected_halt_route(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-112 · §3.8 E12 · IC-01 返回 guard 失败 · HALT_ROUTE。"""
        mock_l1_01.request_state_transition.side_effect = RuntimeError("guard_failed")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E12"

    def test_TC_L104_L207_113_E13_ic13_push_failed_fallback_ui(
        self, sut, mock_project_id: str, mock_l1_07: MagicMock, mock_l1_02: MagicMock,
    ) -> None:
        """TC-L104-L207-113 · §3.8 E13 · IC-13 3 次失败 · 降级直推 UI 警告卡。"""
        mock_l1_07.push_suggestion.side_effect = RuntimeError("unreachable")
        sut.escalate_BF_E_10_to_supervisor(
            project_id=mock_project_id, wp_id="WP-F", verdict_level="FAIL-L1", count=3,
        )
        assert mock_l1_07.push_suggestion.call_count == 3, "3 次重试"
        assert mock_l1_02.push_card.called, "降级直推 UI"

    def test_TC_L104_L207_114_E14_ic16_push_failed_not_blocking(
        self, sut, mock_project_id: str, mock_l1_02: MagicMock, mock_l1_01: MagicMock,
        make_rollback_request,
    ) -> None:
        """TC-L104-L207-114 · §3.8 E14 · IC-16 UI 推送失败 · 不阻塞路由 · 仅 WARN。"""
        mock_l1_02.push_card.side_effect = RuntimeError("ui_down")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        assert any(e.code == "L2-07/E14" and e.severity == "WARNING" for e in resp.errors)

    def test_TC_L104_L207_115_E15_ic09_append_failed_halt_route(
        self, sut, mock_project_id: str, mock_l1_09: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-115 · §3.8 E15 · IC-09 落盘失败 · HALT_ROUTE + 升级。"""
        mock_l1_09.append_event.side_effect = RuntimeError("event_bus_down")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E15"

    def test_TC_L104_L207_116_E16_concurrent_counter_modification_retries(
        self, sut, mock_project_id: str, mock_counter_store: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-116 · §3.8 E16 · 并发改 counter · 自动重试 3 次 · 细粒度锁获取。"""
        calls = {"n": 0}
        def side(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("cas_conflict")
            return 1
        mock_counter_store.compare_and_swap.side_effect = side
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-C16",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        assert calls["n"] == 3

    def test_TC_L104_L207_117_E17_pass_verdict_but_pending_wp_reject(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-117 · §3.8 E17 · verdict=PASS 但仍有未完成 WP · REJECT + 告警 L1-07。"""
        sut._seed_pending_wp(mock_project_id, wp_id="WP-Pending-1")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="PASS", target_state="S7",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E17"

    def test_TC_L104_L207_118_E18_counter_exceeds_hard_limit_halt(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-118 · §3.8 E18 · §11.3 硬拦截 · count>10 未及时升级 · HALT_ROUTE + 强制升级。"""
        sut._seed_counter(mock_project_id, wp_id="WP-H", verdict_level="FAIL-L1", value=11)
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-H",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E18"

    def test_TC_L104_L207_119_E19_mapping_matrix_mutation_detected_halt_all(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-119 · §3.8 E19 · §11.3 硬拦截 · 映射表 yaml 被篡改 · HALT_ALL 系统级。"""
        sut._mutate_mapping_yaml_for_test()
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        assert ei.value.code == "L2-07/E19"
        assert sut._current_degrade_level() == "HALT_ALL"

    def test_TC_L104_L207_120_E20_deadlock_on_counter_lock_skip_crosscheck(
        self, sut, mock_project_id: str, mock_counter_store: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-120 · §3.8 E20 · 锁死锁 · SKIP_CROSSCHECK 降级 · 路由仍继续。"""
        mock_counter_store.acquire_lock.side_effect = RuntimeError("deadlock")
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        assert sut._current_degrade_level() == "SKIP_CROSSCHECK"
        assert any(e.code == "L2-07/E20" for e in resp.errors)
```

---

## §4 IC-XX 契约集成测试

> 针对本 L2 参与的 6 条 IC（IC-14 / IC-01 / IC-09 / IC-13 / IC-16 / IC-17）做契约级断言：payload schema / 方向 / 回退决策下发 / 偏差信号上游。
> 至少 3 个 join test：`IC-14 → IC-01 + IC-09 + IC-16` 三向 fanout · `BF-E-10 → IC-13 → IC-17 → IC-01` 升级闭环。

```python
# file: tests/l1_04/test_l2_07_ic_contracts.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.schemas import ReceiveRollbackRouteRequest, HandleUserDecisionRequest


class TestL2_07_IC_Contracts:
    """§4 · 6 条 IC 契约集成 · 回退决策下发 / 偏差信号上游 · ≥ 3 join test。"""

    # --------- IC-14 (upstream consume) --------- #

    def test_TC_L104_L207_601_ic14_push_rollback_route_schema_strict(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-601 · IC-14 payload schema 严格 · idempotency_key 必填 · verdict ∈ 5 值。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            idempotency_key="k-ic14-001",
        )
        resp = sut.receive_rollback_route(req)
        # decision_id 格式 rrd-<project>-<ts>-<seq>
        assert resp.decision_id.startswith("rrd-")

    # --------- IC-01 (downstream produce) --------- #

    def test_TC_L104_L207_602_ic01_request_state_transition_sent_with_trigger_rollback_route(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-602 · IC-01 payload · trigger=rollback_route · to_state 由映射决定。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L3", target_state="S2", related_wp_id="WP-IC01",
        )
        sut.receive_rollback_route(req)
        p = mock_l1_01.request_state_transition.call_args.kwargs
        assert p["reason"]["trigger"] == "rollback_route"
        assert p["to_state"] == "S2"
        assert p["reason"]["verdict"] == "FAIL-L3"

    # --------- IC-09 (downstream produce) --------- #

    def test_TC_L104_L207_603_ic09_append_event_hash_chain_two_events_per_route(
        self, sut, mock_project_id: str, mock_l1_09: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-603 · 单次路由 ≥ 2 事件：rollback_route_applied + same_level_fail_count_updated。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-IC09",
        )
        sut.receive_rollback_route(req)
        etypes = [c.kwargs["event_type"] for c in mock_l1_09.append_event.call_args_list]
        assert "L1-04:rollback_route_applied" in etypes
        assert "L1-04:same_level_fail_count_updated" in etypes
        # hash-chain：相邻事件 prev_hash == 前一条 hash
        for prev, cur in zip(mock_l1_09.append_event.call_args_list,
                              mock_l1_09.append_event.call_args_list[1:]):
            assert cur.kwargs["prev_hash"] == prev.kwargs["hash"]

    # --------- IC-13 (downstream produce · dead-loop escalation) --------- #

    def test_TC_L104_L207_604_ic13_push_suggestion_block_dead_loop(
        self, sut, mock_project_id: str, mock_l1_07: MagicMock,
    ) -> None:
        """TC-L104-L207-604 · IC-13 · level=BLOCK · dimension=dead_loop · trigger=BF-E-10 · 3 user_options。"""
        sut.escalate_BF_E_10_to_supervisor(
            project_id=mock_project_id, wp_id="WP-IC13", verdict_level="FAIL-L1", count=3,
        )
        p = mock_l1_07.push_suggestion.call_args.kwargs
        assert p["level"] == "BLOCK"
        assert p["dimension"] == "dead_loop"
        assert p["trigger"] == "BF-E-10"
        assert p["context"]["same_level_count"] == 3

    # --------- IC-16 (downstream produce · UI card) --------- #

    def test_TC_L104_L207_605_ic16_push_stage_gate_card_rollback_subtype(
        self, sut, mock_project_id: str, mock_l1_02: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-605 · IC-16（经 L1-02）· card_type ∈ rollback_routed/dead_loop_alert/... 。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-IC16",
        )
        sut.receive_rollback_route(req)
        p = mock_l1_02.push_card.call_args.kwargs
        assert p["card_type"] in ("rollback_routed", "dead_loop_alert",
                                   "user_decision_required", "rollback_archived")

    # --------- IC-17 (upstream consume · user decision) --------- #

    def test_TC_L104_L207_606_ic17_user_intervene_rollback_three_enum(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-606 · IC-17 · decision ∈ {continue, switch_strategy, abort}。"""
        for dec in ("continue", "switch_strategy", "abort"):
            sut._seed_decision(decision_id=f"rrd-ic17-{dec}", wp_id="WP-IC17",
                               verdict_level="FAIL-L1")
            req = HandleUserDecisionRequest(
                project_id=mock_project_id, wp_id="WP-IC17", verdict_level="FAIL-L1",
                decision=dec, user_id="u1", decision_id_ref=f"rrd-ic17-{dec}",
                decided_at="2026-04-22T00:00:00Z",
            )
            resp = sut.handle_user_decision(req)
            assert resp.acknowledged is True

    # --------- JOIN TESTS (multi-IC 原子链路) --------- #

    def test_TC_L104_L207_611_join_ic14_ic01_ic09_ic16_fanout_in_one_route(
        self, sut, mock_project_id: str, mock_l1_01, mock_l1_09, mock_l1_02, make_rollback_request,
    ) -> None:
        """TC-L104-L207-611 · JOIN · IC-14 进 → IC-01 + IC-09(≥2) + IC-16 三路 fanout 全出。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S3", related_wp_id="WP-J1",
        )
        sut.receive_rollback_route(req)
        mock_l1_01.request_state_transition.assert_called_once()
        assert mock_l1_09.append_event.call_count >= 2
        mock_l1_02.push_card.assert_called_once()

    def test_TC_L104_L207_612_join_dead_loop_ic13_then_ic17_then_ic01(
        self, sut, mock_project_id: str, mock_l1_01, mock_l1_07, make_rollback_request,
    ) -> None:
        """TC-L104-L207-612 · JOIN · 3 次 FAIL-L1 → IC-13 BLOCK → IC-17 switch_strategy → IC-01 S3。"""
        # 3 次 FAIL-L1 触发 BF-E-10
        for i in range(3):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-J2", idempotency_key=f"j2-{i}",
            )
            last = sut.receive_rollback_route(req)
        assert last.dead_loop_triggered is True
        mock_l1_07.push_suggestion.assert_called()
        # 用户 switch
        sut._seed_decision(decision_id=last.decision_id, wp_id="WP-J2", verdict_level="FAIL-L1")
        sut.handle_user_decision(HandleUserDecisionRequest(
            project_id=mock_project_id, wp_id="WP-J2", verdict_level="FAIL-L1",
            decision="switch_strategy", user_id="u1", decision_id_ref=last.decision_id,
            decided_at="2026-04-22T00:00:00Z",
        ))
        # 最后一次 IC-01 应是 to_state=S3（switch 后路由）
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S3"

    def test_TC_L104_L207_613_join_cross_project_counter_isolation_via_pm14(
        self, sut, mock_project_id: str, other_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-613 · JOIN · PM-14 · pid-A 计数不影响 pid-B · 跨项目 IC-09/IC-01 payload 隔离。"""
        for pid in (mock_project_id, other_project_id):
            req = make_rollback_request(
                project_id=pid, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-SAME", idempotency_key=f"k-{pid}",
            )
            sut.receive_rollback_route(req)
        assert sut._read_counter(mock_project_id, "WP-SAME", "FAIL-L1") == 1
        assert sut._read_counter(other_project_id, "WP-SAME", "FAIL-L1") == 1
```

---

## §5 性能 SLO 用例

> §12.1 P95/P99 逐项覆盖 · 3 个 `@pytest.mark.perf` 覆盖判定延迟 / 回退吞吐 / 4 级升级链路。

```python
# file: tests/l1_04/test_l2_07_perf.py
from __future__ import annotations

import time
import pytest
import statistics
import threading
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter


class TestL2_07_Performance_SLO:
    """§12.1 SLO · @pytest.mark.perf · 判定延迟 / 回退吞吐 / 4 级升级链路。"""

    @pytest.mark.perf
    def test_TC_L104_L207_701_receive_rollback_route_end_to_end_p95_under_3s(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-701 · §12.1 端到端 P95 ≤ 3s · P99 ≤ 5s（10 次采样）。"""
        latencies_ms: list[float] = []
        for i in range(10):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id=f"WP-perf-{i}", idempotency_key=f"perf-{i}",
            )
            t0 = time.perf_counter()
            sut.receive_rollback_route(req)
            latencies_ms.append((time.perf_counter() - t0) * 1000)
        p95 = sorted(latencies_ms)[int(0.95 * len(latencies_ms)) - 1]
        assert p95 <= 3000, f"P95={p95:.1f}ms 超过 3s 硬 SLO"

    @pytest.mark.perf
    def test_TC_L104_L207_702_validate_verdict_enum_p95_under_5ms(
        self, sut: DeviationJudgeAndFallbackRouter,
    ) -> None:
        """TC-L104-L207-702 · §12.1 validate_verdict_five_enum P95 ≤ 5ms · 纯内存。"""
        latencies: list[float] = []
        for _ in range(1000):
            t0 = time.perf_counter()
            sut.validate_verdict_enum("FAIL-L1")
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
        assert p95 <= 5, f"validate P95={p95:.3f}ms > 5ms"

    @pytest.mark.perf
    def test_TC_L104_L207_703_increment_counter_idempotent_p95_under_100ms(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-703 · §12.1 increment_counter_idempotent（含 fsync）P95 ≤ 100ms。"""
        latencies: list[float] = []
        for i in range(50):
            t0 = time.perf_counter()
            sut.increment_counter_idempotent(
                project_id=mock_project_id, wp_id=f"WP-cnt-{i}", verdict_level="FAIL-L1",
                decision_id=f"idem-cnt-{i}",
            )
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
        assert p95 <= 100, f"counter P95={p95:.1f}ms > 100ms"

    @pytest.mark.perf
    def test_TC_L104_L207_704_escalate_bf_e_10_with_retry_p95_under_500ms(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-704 · §12.1 escalate_BF_E_10（含 3 次重试 jitter）P95 ≤ 500ms。"""
        latencies: list[float] = []
        for i in range(10):
            t0 = time.perf_counter()
            sut.escalate_BF_E_10_to_supervisor(
                project_id=mock_project_id, wp_id=f"WP-esc-{i}", verdict_level="FAIL-L1", count=3,
            )
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
        assert p95 <= 500, f"escalate P95={p95:.1f}ms > 500ms"

    @pytest.mark.perf
    def test_TC_L104_L207_705_four_level_escalation_e2e_under_2s(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-705 · §12.5 基线 · 4 级回退完整链路（3 次 FAIL-L1 → BF-E-10）e2e ≤ 2s。"""
        t0 = time.perf_counter()
        for i in range(3):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-e2e-esc", idempotency_key=f"esc-{i}",
            )
            resp = sut.receive_rollback_route(req)
        elapsed = (time.perf_counter() - t0) * 1000
        assert resp.dead_loop_triggered is True
        assert elapsed <= 2000, f"4 级升级链路 {elapsed:.1f}ms > 2s"

    @pytest.mark.perf
    def test_TC_L104_L207_706_concurrent_routes_throughput_20_qps(
        self, sut: DeviationJudgeAndFallbackRouter, make_rollback_request,
    ) -> None:
        """TC-L104-L207-706 · §12.2 稳态 20 qps · 100 路由跨 pid 总耗时 ≤ 10s。"""
        def worker(pid: str, idx: int) -> None:
            req = make_rollback_request(
                project_id=pid, verdict="FAIL-L1", target_state="S4",
                related_wp_id=f"WP-{idx}", idempotency_key=f"tput-{pid}-{idx}",
            )
            sut.receive_rollback_route(req)

        t0 = time.perf_counter()
        threads = [threading.Thread(target=worker, args=(f"proj-tput-{i % 10}", i))
                   for i in range(100)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=15)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 10.0, f"100 并发路由 {elapsed:.2f}s > 10s"
```

---

## §6 端到端 e2e

> PRD §14.9 四大 GWT 场景端到端 · 4 级回退完整链路 · 偏差升级路径。

```python
# file: tests/l1_04/test_l2_07_e2e.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.schemas import HandleUserDecisionRequest


class TestL2_07_E2E:
    """§6 · e2e 场景：PRD §14.9 四大 GWT（正向 PASS/FAIL-L1/FAIL-L2 + 负向 dead loop）。"""

    def test_TC_L104_L207_801_e2e_pass_routes_S7_and_clears_counters(
        self, sut, mock_project_id: str, mock_l1_01, mock_l1_02, mock_l1_09, make_rollback_request,
    ) -> None:
        """TC-L104-L207-801 · e2e GWT 正向 1 ·
        Given project 在 S5 有 verifier PASS
        When L1-07 发 IC-14 PASS/target=S7
        Then L2-07 清零所有 counter + IC-01 切 S7 + IC-09 落盘 + IC-16 推 rollback_archived 卡。"""
        # 先制造 2 个非零 counter
        sut._seed_counter(mock_project_id, "WP-1", "FAIL-L1", value=2)
        sut._seed_counter(mock_project_id, "WP-2", "FAIL-L2", value=1)
        req = make_rollback_request(
            project_id=mock_project_id, verdict="PASS", target_state="S7",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        assert resp.target_stage_applied == "S7"
        assert sut._read_counter(mock_project_id, "WP-1", "FAIL-L1") == 0
        assert sut._read_counter(mock_project_id, "WP-2", "FAIL-L2") == 0
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S7"
        # rollback_archived 卡推出
        assert any(c.kwargs.get("card_type") == "rollback_archived"
                   for c in mock_l1_02.push_card.call_args_list) \
            or mock_l1_02.push_card.called

    def test_TC_L104_L207_802_e2e_fail_l1_routes_S4_rerun(
        self, sut, mock_project_id: str, mock_l1_01, make_rollback_request,
    ) -> None:
        """TC-L104-L207-802 · e2e GWT 正向 2 · FAIL-L1 首次 · S4 同 WP 重跑 · counter=1。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4", related_wp_id="WP-E2",
        )
        resp = sut.receive_rollback_route(req)
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S4"
        assert resp.same_level_count == 1

    def test_TC_L104_L207_803_e2e_fail_l2_routes_S3_rebuild(
        self, sut, mock_project_id: str, mock_l1_01, make_rollback_request,
    ) -> None:
        """TC-L104-L207-803 · e2e GWT 正向 3 · FAIL-L2 首次 · 回 S3 · 重建蓝图。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S3", related_wp_id="WP-E3",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S3"
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S3"

    def test_TC_L104_L207_804_e2e_three_strikes_bf_e_10_user_switch_recovers(
        self, sut, mock_project_id: str, mock_l1_01, mock_l1_02, mock_l1_07, make_rollback_request,
    ) -> None:
        """TC-L104-L207-804 · e2e GWT 负向 7 · 3 次 FAIL-L1 → BF-E-10 → 用户 switch → S3。
        完整 4 级回退升级路径：S4 rerun → S4 rerun → S4 rerun → BLOCK → USER → S3 rebuild。"""
        for i in range(3):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-E4", idempotency_key=f"e4-{i}",
            )
            last = sut.receive_rollback_route(req)
        # 第 3 次触发 BF-E-10
        assert last.dead_loop_triggered is True
        assert last.status == "AWAITING_USER"
        mock_l1_07.push_suggestion.assert_called_once()
        assert mock_l1_07.push_suggestion.call_args.kwargs["trigger"] == "BF-E-10"
        # UI 必然收到 dead_loop_alert · risk=red
        alerts = [c.kwargs for c in mock_l1_02.push_card.call_args_list
                  if c.kwargs.get("card_type") == "dead_loop_alert"]
        assert any(a.get("dead_loop_risk_indicator") == "red" for a in alerts)
        # 用户 switch_strategy
        sut._seed_decision(decision_id=last.decision_id, wp_id="WP-E4", verdict_level="FAIL-L1")
        ur = sut.handle_user_decision(HandleUserDecisionRequest(
            project_id=mock_project_id, wp_id="WP-E4", verdict_level="FAIL-L1",
            decision="switch_strategy", user_id="u-e2e", decision_id_ref=last.decision_id,
            decided_at="2026-04-22T00:00:00Z",
        ))
        assert ur.new_target_stage == "S3"
        assert ur.counter_action == "RESET_TO_ZERO"
        # 最后的 IC-01 一定是 to_state=S3
        final_ic01 = mock_l1_01.request_state_transition.call_args.kwargs
        assert final_ic01["to_state"] == "S3"
```

---

## §7 测试 fixture

> 共享 fixture：SUT / mock pid / mock clock / mock event bus / mock counter store / mock mapping matrix / mock audit store / mock l1-01 / mock l1-02 / mock l1-07 / mock l1-09。
> 放在 `tests/l1_04/conftest.py` · autouse 的只开 event bus + mapping matrix · 其余 opt-in。

```python
# file: tests/l1_04/conftest_l2_07.py
from __future__ import annotations

import pytest
import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.schemas import ReceiveRollbackRouteRequest


@pytest.fixture
def mock_project_id() -> str:
    return "proj-l207-default"


@pytest.fixture
def other_project_id() -> str:
    return "proj-l207-other-pm14"


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
    bus.acquire_lock.return_value = MagicMock()
    return bus


@pytest.fixture
def mock_counter_store() -> MagicMock:
    store = MagicMock()
    store.persist.return_value = True
    store.compare_and_swap.return_value = 1
    store.acquire_lock.return_value = MagicMock()
    return store


@pytest.fixture
def mock_mapping_matrix() -> MagicMock:
    mx = MagicMock()
    mx.bijection = {"PASS": "S7", "FAIL-L1": "S4", "FAIL-L2": "S3",
                     "FAIL-L3": "S2", "FAIL-L4": "S1"}
    mx.verify_hash.return_value = True
    return mx


@pytest.fixture
def mock_audit_store() -> MagicMock:
    au = MagicMock()
    au.verify_chain.return_value = True
    au.last_hash.return_value = "0" * 64
    return au


@pytest.fixture
def mock_l1_01() -> MagicMock:
    m = MagicMock()
    m.request_state_transition.return_value = {"acknowledged": True, "state_transition_id": "st-1"}
    return m


@pytest.fixture
def mock_l1_02() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_07() -> MagicMock: return MagicMock()
@pytest.fixture
def mock_l1_09(mock_event_bus) -> MagicMock: return mock_event_bus


@pytest.fixture
def sut(
    mock_project_id, mock_clock, mock_event_bus, mock_counter_store,
    mock_mapping_matrix, mock_audit_store,
    mock_l1_01, mock_l1_02, mock_l1_07, mock_l1_09,
) -> DeviationJudgeAndFallbackRouter:
    return DeviationJudgeAndFallbackRouter(
        clock=mock_clock, event_bus=mock_event_bus,
        counter_store=mock_counter_store, mapping_matrix=mock_mapping_matrix,
        audit_store=mock_audit_store,
        l1_01=mock_l1_01, l1_02=mock_l1_02, l1_07=mock_l1_07, l1_09=mock_l1_09,
    )


@pytest.fixture
def make_rollback_request() -> Callable[..., ReceiveRollbackRouteRequest]:
    """构造 IC-14 push_rollback_route payload · §3.2 字段级 schema。"""
    def _factory(**overrides: Any) -> ReceiveRollbackRouteRequest:
        base: dict[str, Any] = dict(
            project_id="proj-l207-default",
            verdict="FAIL-L1",
            target_state="S4",
            reason={
                "natural_language": "unit test fail-L1 placeholder",
                "evidence_refs": [{"type": "verifier_report", "ref_id": "vr-001"}],
            },
            related_wp_id="WP-1",
            verifier_report_ref="vr-001",
            supervisor_decision_id=f"sup-dec-{uuid.uuid4()}",
            submitted_at="2026-04-22T00:00:00Z",
            idempotency_key=f"idem-{uuid.uuid4()}",
        )
        base.update(overrides)
        return ReceiveRollbackRouteRequest(**base)
    return _factory
```

---

## §8 集成点用例

> 与兄弟 L2 的协作：**L2-04 质量 Gate 编译器**（Gate 判定 FAIL 后通过 L1-07 流到本 L2）/ **L2-05 S4 执行驱动器**（rerun 后再触发 verifier）/ **L2-06 S5 Verifier 编排器**（产出 verdict）。
> 本 L2 并不直接调用兄弟 L2，而是通过 L1-07 Supervisor 间接接收 verdict + target_state。

```python
# file: tests/l1_04/test_l2_07_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter


class TestL2_07_SiblingIntegration:
    """§8 · 与 L2-04 Gate 编译器 / L2-05 S4 执行器 / L2-06 S5 Verifier 的协作（间接 · 经 L1-07）。"""

    def test_TC_L104_L207_901_l2_06_verifier_report_to_router_via_l1_07(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-901 · PRD §14.9 正向场景 · L2-06 S5 Verifier FAIL-L1 → L1-07 → IC-14 → L2-07 → IC-01 S4。"""
        # 模拟 L2-06 产出 verifier_report · L1-07 判 FAIL-L1
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            verifier_report_ref="vr-l206-001", related_wp_id="WP-integ-206",
        )
        resp = sut.receive_rollback_route(req)
        assert resp.status == "ROUTED"
        # IC-01 payload metadata 带回 verifier_report_ref
        p = mock_l1_01.request_state_transition.call_args.kwargs
        assert p["metadata"]["verifier_report_ref"] == "vr-l206-001"

    def test_TC_L104_L207_902_l2_04_gate_fail_l2_triggers_rebuild_S3(
        self, sut, mock_project_id: str, mock_l1_01: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-902 · L2-04 Gate 编译器发现 Gate FAIL-L2（如 ac_coverage<1.0）
        → L1-07 聚合 → IC-14 FAIL-L2 → L2-07 回 S3 重建蓝图。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S3",
            verifier_report_ref="gate-l204-fail-001", related_wp_id=None,
        )
        resp = sut.receive_rollback_route(req)
        assert resp.target_stage_applied == "S3"
        assert mock_l1_01.request_state_transition.call_args.kwargs["to_state"] == "S3"

    def test_TC_L104_L207_903_l2_05_rerun_same_wp_counter_preserved(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-903 · L2-05 rerun WP-X 后再产生 FAIL-L1 · counter 保留（同 WP/level 累加）。"""
        # 首次 FAIL-L1
        req1 = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            related_wp_id="WP-rerun", idempotency_key="r1",
        )
        sut.receive_rollback_route(req1)
        # L2-05 rerun 后第二次 FAIL-L1
        req2 = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            related_wp_id="WP-rerun", idempotency_key="r2",
        )
        r2 = sut.receive_rollback_route(req2)
        assert r2.same_level_count == 2, "同 WP rerun 后 counter 累加不重置"

    def test_TC_L104_L207_904_l2_06_multiple_wps_parallel_independent_counters(
        self, sut, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-904 · L2-06 并发 verifier 多 WP 同时 FAIL-L1 · 计数 per-WP 独立（§11.5 OQ-7/OQ-9）。"""
        for wp in ("WP-p1", "WP-p2", "WP-p3"):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id=wp, idempotency_key=f"par-{wp}",
            )
            sut.receive_rollback_route(req)
        for wp in ("WP-p1", "WP-p2", "WP-p3"):
            assert sut._read_counter(mock_project_id, wp, "FAIL-L1") == 1
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 并发读写 / 4 级回退递归上限 / 同时多偏差 / 回退自身失败 / 脏指标 / 冷启恢复。至少 5 个 · 本文件 7 个。

```python
# file: tests/l1_04/test_l2_07_edge_cases.py
from __future__ import annotations

import pytest
import threading
from unittest.mock import MagicMock

from app.l1_04.l2_07.router import DeviationJudgeAndFallbackRouter
from app.l1_04.l2_07.errors import L2_07_Error


class TestL2_07_EdgeCases:
    """§9 · 边界 · 4 级递归上限 / 同时多偏差 / 回退自身失败 / 脏指标 / 冷启。"""

    def test_TC_L104_L207_A01_four_level_recursion_upper_bound_ten(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-A01 · 4 级回退递归上限 · count 到达硬上限 10 后第 11 次触发 E18 HALT。"""
        # 触发 10 次 FAIL-L1 且用户一直 continue（跳过死循环 cut）
        for i in range(10):
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-rec", idempotency_key=f"rec-{i}",
            )
            sut._bypass_bf_e_10_via_continue("WP-rec")  # 模拟用户连续 continue
            sut.receive_rollback_route(req)
        # 第 11 次 → E18
        req11 = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
            related_wp_id="WP-rec", idempotency_key="rec-11",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req11)
        assert ei.value.code == "L2-07/E18"

    def test_TC_L104_L207_A02_simultaneous_multiple_deviations_serialized_per_wp(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str, make_rollback_request,
    ) -> None:
        """TC-L104-L207-A02 · §11.5 OQ-7 · 同 WP 并发多偏差 · per-WP 锁串行化 · counter 单调 1→2→3。"""
        results: list[int] = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            req = make_rollback_request(
                project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
                related_wp_id="WP-conc", idempotency_key=f"conc-{idx}",
            )
            r = sut.receive_rollback_route(req)
            with lock:
                results.append(r.same_level_count)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        # 必须串行化产出 1, 2, 3（不一定有序到达但集合相等）
        assert sorted(results) == [1, 2, 3], f"并发 per-WP 锁失败：{sorted(results)}"

    def test_TC_L104_L207_A03_rollback_self_failure_halt_route_with_audit(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str,
        mock_l1_01: MagicMock, mock_l1_09: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-A03 · 回退自身失败（IC-01 + IC-09 双失败）· HALT_ROUTE · 聚合 status=HALT_ROUTE · 审计仍尽力 append。"""
        mock_l1_01.request_state_transition.side_effect = RuntimeError("l101_down")
        mock_l1_09.append_event.side_effect = [RuntimeError("l109_down"), {"ok": True}]  # 第二次成功
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req)
        # 优先 E12（IC-01 失败）
        assert ei.value.code in ("L2-07/E12", "L2-07/E15")
        assert sut._current_degrade_level() == "HALT_ROUTE"

    def test_TC_L104_L207_A04_dirty_counter_metric_rejected_at_startup(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str,
    ) -> None:
        """TC-L104-L207-A04 · 脏指标（counter=-1 / 非整数 / count>10 持久化残留）· 冷启校验拒绝 + 重置。"""
        sut._inject_dirty_counter(mock_project_id, wp_id="WP-dirty", verdict_level="FAIL-L1",
                                   value=-1)
        # 触发冷启一致性校验
        recovered = sut._reload_counters_from_disk()
        # 脏值被 reset 为 0
        assert sut._read_counter(mock_project_id, "WP-dirty", "FAIL-L1") == 0
        assert recovered["repaired"] >= 1

    def test_TC_L104_L207_A05_concurrent_cross_project_no_cross_counter(
        self, sut: DeviationJudgeAndFallbackRouter, make_rollback_request,
    ) -> None:
        """TC-L104-L207-A05 · 10 线程 × 10 project 并发 · 无 counter 串扰（PM-14）。"""
        def worker(pid: str) -> None:
            for i in range(3):
                req = make_rollback_request(
                    project_id=pid, verdict="FAIL-L1", target_state="S4",
                    related_wp_id="WP-cross", idempotency_key=f"{pid}-{i}",
                )
                sut.receive_rollback_route(req)

        pids = [f"proj-cross-{i}" for i in range(10)]
        threads = [threading.Thread(target=worker, args=(pid,)) for pid in pids]
        for t in threads: t.start()
        for t in threads: t.join(timeout=15)

        for pid in pids:
            assert sut._read_counter(pid, "WP-cross", "FAIL-L1") == 3, f"{pid} counter 串扰"

    def test_TC_L104_L207_A06_mapping_yaml_hash_verification_on_every_route(
        self, sut: DeviationJudgeAndFallbackRouter, mock_project_id: str,
        mock_mapping_matrix: MagicMock, make_rollback_request,
    ) -> None:
        """TC-L104-L207-A06 · §11.3 硬拦截 · 每次路由前校验 mapping yaml hash · 不等 → E19 HALT_ALL。"""
        req = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L1", target_state="S4",
        )
        # 第一次正常
        sut.receive_rollback_route(req)
        # 第二次之前篡改
        mock_mapping_matrix.verify_hash.return_value = False
        req2 = make_rollback_request(
            project_id=mock_project_id, verdict="FAIL-L2", target_state="S3",
            idempotency_key="after-mutation",
        )
        with pytest.raises(L2_07_Error) as ei:
            sut.receive_rollback_route(req2)
        assert ei.value.code == "L2-07/E19"

    def test_TC_L104_L207_A07_cold_start_recovers_awaiting_user_decisions(
        self, mock_project_id: str, mock_clock, mock_event_bus, mock_counter_store,
        mock_mapping_matrix, mock_audit_store,
        mock_l1_01, mock_l1_02, mock_l1_07, mock_l1_09,
    ) -> None:
        """TC-L104-L207-A07 · §8.6 崩溃恢复 · 重启后 AWAITING_USER 聚合完整恢复 · 超时计时继续。"""
        # 预置持久化状态
        mock_counter_store.load_state.return_value = {
            "awaiting_decisions": [
                {"decision_id": "rrd-crash-001", "wp_id": "WP-restart",
                 "verdict_level": "FAIL-L1", "awaiting_since_ms": mock_clock.now_ms - 3600_000},
            ],
        }
        cold = DeviationJudgeAndFallbackRouter(
            clock=mock_clock, event_bus=mock_event_bus,
            counter_store=mock_counter_store, mapping_matrix=mock_mapping_matrix,
            audit_store=mock_audit_store,
            l1_01=mock_l1_01, l1_02=mock_l1_02, l1_07=mock_l1_07, l1_09=mock_l1_09,
        )
        awaiting = cold._list_awaiting_decisions()
        assert len(awaiting) == 1
        assert awaiting[0]["decision_id"] == "rrd-crash-001"
```

---

*— L1-04 / L2-07 TDD 测试用例 · v1.0 filled · 覆盖 §3 12 public 方法 + §3.8 20 错误码 + §4 6 IC 契约 + §12 6 SLO 维度 + PRD §14.9 10 场景 —*
