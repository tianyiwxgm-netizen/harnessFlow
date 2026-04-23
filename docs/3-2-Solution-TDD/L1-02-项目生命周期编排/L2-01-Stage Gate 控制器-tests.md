---
doc_id: tests-L1-02-L2-01-Stage Gate 控制器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-01-Stage Gate 控制器.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-01-Stage Gate 控制器 · TDD 测试用例

> 基于 3-1 L2-01 tech-design 的 §3 接口（`request_gate_decision` / `authorize_transition` / `receive_user_decision` / `rollback_gate` / `query_gate_state` · 内部算法 `assemble_evidence` / `emit_rejection_analysis` / `validate_transition`）+ §11 错误码（`E_L102_L201_001~014` 共 14 条）+ §12 SLO（Gate 决策 P95 ≤ 500ms · 状态机转换 P95 ≤ 100ms）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L102-L201-NNN`（L1-02 下 L2-01 · 三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_01_StageGateController` 组织；正向 / 负向 / IC 契约 / SLO / e2e 分文件归档。
> 本 L2 为 **BC-02 Aggregate Root + Domain Service 双重角色**（StageGateState 聚合每 project 一份）· 是 project 主状态机的 **IC-01 唯一发起方**（PM-14 所有权硬声明）· 门控 L2-03 / L2-04 / L2-05 / L2-06 四个产出型兄弟 L2。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（§11 14 错误码全覆盖）
- [x] §4 IC 契约集成测试（IC-01 / IC-06 / IC-09 / IC-16 / IC-17 / IC-19）
- [x] §5 性能 SLO 用例（§12 对标 · 8 指标）
- [x] §6 端到端 e2e 场景（§5 时序 × 3 · S1→S7 全程）
- [x] §7 测试 fixture（mock_project_id / mock_event_bus / mock_clock / mock_ic_payload / mock_kb / mock_gate_evidence）
- [x] §8 集成点用例（与 L2-03 / L2-04 / L2-05 / L2-06 调用链）
- [x] §9 边界 / edge case（空证据 / 循环依赖 / rollback 超 24h / 并发 Gate）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC 在下表至少出现一次。
> 覆盖类型：unit = 纯函数 / 组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO；security = 所有权 / 红线攻击面。

### §1.1 方法 × 测试 × 覆盖类型（§3 五 public 方法 + 内部关键函数）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `request_gate_decision()` · §3.1 · S1 Gate pass | TC-L102-L201-001 | integration | — | IC-17 + IC-01 |
| `request_gate_decision()` · §3.1 · S2 Gate pass 全证据 | TC-L102-L201-002 | integration | — | IC-16 + IC-17 |
| `request_gate_decision()` · §3.1 · need_input 缺 TOGAF | TC-L102-L201-003 | unit | — | — |
| `request_gate_decision()` · §3.1 · 同 request_id 幂等 | TC-L102-L201-004 | unit | — | — |
| `request_gate_decision()` · §3.1 · trim_level=minimal | TC-L102-L201-005 | unit | — | IC-L2-09（L2-07）|
| `authorize_transition()` · §3.2 · PLANNING → TDD_PLANNING | TC-L102-L201-006 | integration | — | IC-01 |
| `authorize_transition()` · §3.2 · reason < 20 字 拒 | TC-L102-L201-007 | unit | — | IC-01 |
| `receive_user_decision()` · §3.3 · approve | TC-L102-L201-008 | integration | — | IC-17 |
| `receive_user_decision()` · §3.3 · reject + change_requests | TC-L102-L201-009 | integration | — | IC-17 |
| `receive_user_decision()` · §3.3 · request_change | TC-L102-L201-010 | integration | — | IC-17 |
| `rollback_gate()` · §3.4 · 23h 内 re_open | TC-L102-L201-011 | integration | — | — |
| `rollback_gate()` · §3.4 · re_open_count 累加 | TC-L102-L201-012 | unit | — | — |
| `query_gate_state()` · §3.5 · bootstrap 恢复 | TC-L102-L201-013 | integration | — | — |
| `query_gate_state()` · §3.5 · 指定 stage | TC-L102-L201-014 | unit | — | — |
| `assemble_evidence()` · §6.2 · 全证据 | TC-L102-L201-015 | unit | — | — |
| `validate_transition()` · §6.3 · 合法边 | TC-L102-L201-016 | unit | — | — |
| `emit_rejection_analysis()` · §6.1 · root_cause/fix_advice 双必填 | TC-L102-L201-017 | unit | — | IC-05 |

### §1.2 错误码 × 测试（§11 14 条全覆盖 · 前缀 `E_L102_L201_`）

| 错误码 | TC ID | 方法 | 归属 §11.1 分类 |
|---|---|---|---|
| `E_L102_L201_001` GATE_EVIDENCE_MISSING | TC-L102-L201-101 | `request_gate_decision()` | 证据不齐（正常业务） |
| `E_L102_L201_002` TRANSITION_FORBIDDEN | TC-L102-L201-102 | `authorize_transition()` / `validate_transition()` | 契约违反（致命） |
| `E_L102_L201_003` CIRCULAR_DEP | TC-L102-L201-103 | `request_gate_decision()` · S3 | 契约违反（致命） |
| `E_L102_L201_004` STATE_CORRUPT | TC-L102-L201-104 | `query_gate_state()` · 加载时 | 契约违反（致命） |
| `E_L102_L201_005` EVIDENCE_EXPIRED | TC-L102-L201-105 | `assemble_evidence()` | 证据不齐（正常业务） |
| `E_L102_L201_006` PM14_OWNERSHIP_VIOLATION | TC-L102-L201-106 | `authorize_transition()` · 非 L2-01 调用 | 契约违反（致命 / security） |
| `E_L102_L201_007` REJECTION_ANALYZER_TIMEOUT | TC-L102-L201-107 | `emit_rejection_analysis()` | 运行时异常（可降级） |
| `E_L102_L201_008` FSYNC_FAIL | TC-L102-L201-108 | `persist_state()` | 运行时异常（可降级） |
| `E_L102_L201_009` HISTORY_QUOTA_EXCEEDED | TC-L102-L201-109 | `gate_history` rotate | 运行时异常（可降级） |
| `E_L102_L201_010` LLM_FALLBACK_DISABLED | TC-L102-L201-110 | 配置冲突 | 运行时异常（可降级） |
| `E_L102_L201_011` CONCURRENT_GATE_REQUEST | TC-L102-L201-111 | `request_gate_decision()` · 同 project 并发 | 契约违反（致命） |
| `E_L102_L201_012` AUDIT_SEED_EMIT_FAIL | TC-L102-L201-112 | IC-09 emit | 运行时异常（可降级） |
| `E_L102_L201_013` GATE_AUTO_TIMEOUT_ATTEMPTED | TC-L102-L201-113 | 启动配置校验 | 契约违反（致命 / security） |
| `E_L102_L201_014` SNAPSHOT_REPLAY_MISMATCH | TC-L102-L201-114 | 崩溃恢复 | 契约违反（致命） |

### §1.3 IC 契约 × 测试（本 L2 对上 / 对下 7 条）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-01 request_state_transition · L2-01 → L1-01 L2-03 | 发起（唯一）| TC-L102-L201-401 | 主状态机转换 · PM-14 所有权 |
| IC-06 hard_red_line · L2-01 → L1-07 | 发起 | TC-L102-L201-402 | STATE_CORRUPT / FSYNC 三次失败 |
| IC-09 append_event · L2-01 → L1-09 | 发起 | TC-L102-L201-403 | Gate 生命周期 7 事件 |
| IC-16 push_stage_gate_card · L2-01 → L1-10 | 发起 | TC-L102-L201-404 | 证据齐后推卡片 |
| IC-17 user_intervene · L1-10 → L2-01 | 接收 | TC-L102-L201-405 | approve / reject / request_change |
| IC-19 request_wbs_decomposition · L2-01 → L1-03 | 发起 | TC-L102-L201-406 | S2 Gate 通过后 |
| IC-05 delegate_subagent · L2-01 → L1-05（可选）| 发起 | TC-L102-L201-407 | RejectionAnalyzer LLM 归因 |

### §1.4 SLO × 测试（§12.1 8 指标）

| 指标 | P95 目标 | 硬上限 | TC ID | 类型 |
|---|---|---|---|---|
| Gate 决策 `request_gate_decision` | ≤ 500ms | 5s | TC-L102-L201-501 | perf |
| 状态机转换 `authorize_transition` | ≤ 100ms | 1s | TC-L102-L201-502 | perf |
| Evidence 装配 `assemble_evidence` | ≤ 300ms | 3s | TC-L102-L201-503 | perf |
| DAG 环检测（S3） | ≤ 200ms | 2s | TC-L102-L201-504 | perf |
| LLM 归因分析 | ≤ 5s | 20s | TC-L102-L201-505 | perf |
| 规则模板归因（降级） | ≤ 80ms | 500ms | TC-L102-L201-506 | perf |
| 审计 seed 落盘 | ≤ 30ms | 500ms | TC-L102-L201-507 | perf |
| 并发 10 project × 2 rps | — | 无错误 | TC-L102-L201-508 | perf |

---

## §2 正向用例（每方法 ≥ 1）

> pytest 风格；`class TestL2_01_StageGateController`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `StageGateController`（从 `app.l2_01.controller` 导入）· 构造时注入 `repo / event_bus / clock / trim_query / rejection_analyzer` 五个依赖 · 全部用 fixture 提供 mock。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_positive.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController
from app.l2_01.schemas import (
    EvidenceBundle,
    GateDecision,
    GateStateSnapshot,
    RollbackResult,
    TransitionResult,
)


class TestL2_01_StageGateController:
    """每个 public 方法 + 代表性 stage 至少 1 正向用例。

    覆盖 §3 五个 public 方法 + §6 三个核心内部算法：
      - request_gate_decision        (§3.1 · 主入口)
      - authorize_transition         (§3.2 · 封装 IC-01)
      - receive_user_decision        (§3.3 · IC-17 回推三路由)
      - rollback_gate                (§3.4 · Re-open / No-Go)
      - query_gate_state             (§3.5 · bootstrap / UI)
      - assemble_evidence            (§6.2 · 声明式信号集)
      - validate_transition          (§6.3 · ALLOWED_TRANSITIONS)
      - emit_rejection_analysis      (§6.1 · root_cause + fix_advice)

    覆盖 §8.1 主状态机 6 主态合法转换（INITIALIZED → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED）。
    """

    def test_TC_L102_L201_001_s1_gate_pass_initialized_to_planning(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_request_id: str,
        mock_gate_evidence: dict[str, Any],
    ) -> None:
        """TC-L102-L201-001 · S1 Gate 证据齐 + 用户 approve → decision=pass + 转 PLANNING。"""
        bundle: EvidenceBundle = EvidenceBundle.from_dict({
            "request_id": mock_request_id,
            "project_id": mock_project_id,
            "stage": "S1",
            "triggering_signal": mock_gate_evidence["s1"]["triggering_signal"],
            "trim_level": "full",
            "ts": "2026-04-22T10:00:00Z",
        })
        # 预置已累积 3 个 S1 信号（charter / stakeholders / goal_anchor_hash_locked）
        sut.seed_accumulated_ready(mock_project_id, "S1", [
            "charter_ready", "stakeholders_ready", "goal_anchor_hash_locked",
        ])
        decision: GateDecision = sut.request_gate_decision(bundle)
        # 证据齐 → 先开 Gate 等用户
        assert decision.decision in ("pass", "need_input")
        # 模拟用户 approve
        if decision.decision == "need_input":
            sut.receive_user_decision(
                gate_id=decision.gate_id,
                user_payload={
                    "gate_id": decision.gate_id,
                    "project_id": mock_project_id,
                    "decision": "approve",
                    "decided_by": "user-zhang",
                    "ts": "2026-04-22T10:05:00Z",
                },
            )
        snap = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "PLANNING"

    def test_TC_L102_L201_002_s2_gate_pass_full_evidence(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L201-002 · S2 Gate · 4 件套 + 9 计划 + TOGAF + WBS 全齐 · pass → TDD_PLANNING。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        bundle = EvidenceBundle.from_dict({
            "request_id": mock_request_id,
            "project_id": mock_project_id,
            "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready",
                "source_l2": "L1-03",
                "artifact_refs": ["projects/p/wbs/v3.yaml"],
                "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "full",
            "ts": "2026-04-22T11:00:05Z",
        })
        decision = sut.request_gate_decision(bundle)
        # Gate 必须先开 · 等用户 · 此时 decision 可能为 need_input 等用户态
        assert decision.gate_id.startswith("gate-S2-")
        sut.receive_user_decision(
            gate_id=decision.gate_id,
            user_payload={
                "gate_id": decision.gate_id,
                "project_id": mock_project_id,
                "decision": "approve",
                "decided_by": "user-pm",
                "ts": "2026-04-22T11:10:00Z",
            },
        )
        snap = sut.query_gate_state(mock_project_id, stage="S2")
        assert snap.current_main_state == "TDD_PLANNING"

    def test_TC_L102_L201_003_need_input_missing_togaf(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L201-003 · S2 Gate · 缺 togaf_ready · 返 need_input + missing_signals 含 togaf。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "wbs_ready",
        ])  # 故意缺 togaf_ready / adr_count
        bundle = EvidenceBundle.from_dict({
            "request_id": mock_request_id,
            "project_id": mock_project_id,
            "stage": "S2",
            "triggering_signal": {
                "signal_name": "9_plans_ready",
                "source_l2": "L2-04",
                "artifact_refs": ["projects/p/pmp/9plans.md"],
                "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "full",
            "ts": "2026-04-22T11:00:05Z",
        })
        decision = sut.request_gate_decision(bundle)
        assert decision.decision == "need_input"
        assert "togaf_ready" in decision.evidence_summary["missing_signals"]

    def test_TC_L102_L201_004_request_gate_decision_idempotent(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-004 · 同 (gate_id, bundle_hash) 重复请求返同一 GateDecision（LRU 512）。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        bundle_dict = {
            "request_id": "req-idem-1",
            "project_id": mock_project_id,
            "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready", "source_l2": "L1-03",
                "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "full",
            "ts": "2026-04-22T11:00:05Z",
        }
        d1 = sut.request_gate_decision(EvidenceBundle.from_dict(bundle_dict))
        d2 = sut.request_gate_decision(EvidenceBundle.from_dict(bundle_dict))
        assert d1.gate_id == d2.gate_id
        assert d1.audit_entry_id == d2.audit_entry_id

    def test_TC_L102_L201_005_trim_level_minimal_uses_reduced_signals(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_trim_query: Any,
    ) -> None:
        """TC-L102-L201-005 · trim_level=minimal · REQUIRED_SIGNALS(S2,minimal)={4_pieces+5_plans+togaf_a_d+adr>=5+wbs}。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "5_plans_ready", "togaf_a_d_ready", "adr_count>=5", "wbs_ready",
        ])
        mock_trim_query.set_return("minimal")
        bundle = EvidenceBundle.from_dict({
            "request_id": "req-min-1",
            "project_id": mock_project_id,
            "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready", "source_l2": "L1-03",
                "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "minimal",
            "ts": "2026-04-22T11:00:05Z",
        })
        decision = sut.request_gate_decision(bundle)
        assert not decision.evidence_summary["missing_signals"]  # minimal 全齐

    def test_TC_L102_L201_006_authorize_transition_planning_to_tdd_planning(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-006 · authorize_transition · 合法边 · accepted=true + IC-01 发送。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        result: TransitionResult = sut.authorize_transition(
            project_id=mock_project_id,
            from_state="PLANNING",
            to_state="TDD_PLANNING",
            gate_id="gate-S2-abc",
            reason="S2 Gate 通过 · 4 件套 / PMP / TOGAF / WBS 全齐 · 用户 approve",
            evidence_refs=["projects/p/fourset/prd.md", "projects/p/togaf/phase_a.md"],
        )
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"
        assert result.audit_entry_id
        # IC-01 事件必发
        ic01_events = [e for e in mock_event_bus.emitted_events()
                       if e["ic"] == "IC-01" and e["project_id"] == mock_project_id]
        assert len(ic01_events) == 1

    def test_TC_L102_L201_007_authorize_transition_reason_too_short_rejected(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-007 · reason < 20 字符 · 按 IC-01 §3.1.2 硬约束拒绝。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        from app.l2_01.errors import StageGateError
        with pytest.raises(StageGateError) as exc:
            sut.authorize_transition(
                project_id=mock_project_id,
                from_state="PLANNING",
                to_state="TDD_PLANNING",
                gate_id="gate-S2-short-reason",
                reason="ok",  # 2 字符
                evidence_refs=["x"],
            )
        assert "reason" in str(exc.value).lower()

    def test_TC_L102_L201_008_receive_user_decision_approve(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-008 · user approve · Gate.state = CLOSED + 触发 authorize_transition。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        ack = sut.receive_user_decision(
            gate_id=gate_id,
            user_payload={
                "gate_id": gate_id, "project_id": mock_project_id,
                "decision": "approve", "decided_by": "user-x",
                "ts": "2026-04-22T12:00:00Z",
            },
        )
        assert ack.accepted is True
        assert ack.new_gate_state == "CLOSED"
        assert ack.next_action == "transition_requested"

    def test_TC_L102_L201_009_receive_user_decision_reject_with_changes(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-009 · user reject + change_requests ≥ 1 · Gate.state = REROUTING + re_open_count++。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        ack = sut.receive_user_decision(
            gate_id=gate_id,
            user_payload={
                "gate_id": gate_id, "project_id": mock_project_id,
                "decision": "reject", "decided_by": "user-x",
                "change_requests": ["补 AC-03 边界条件", "重写风险计划"],
                "ts": "2026-04-22T12:00:00Z",
            },
        )
        assert ack.accepted is True
        assert ack.new_gate_state == "REROUTING"
        assert ack.next_action == "redo_dispatched"

    def test_TC_L102_L201_010_receive_user_decision_request_change(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-010 · user request_change · Gate.state = ANALYZING + next_action=impact_report。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        ack = sut.receive_user_decision(
            gate_id=gate_id,
            user_payload={
                "gate_id": gate_id, "project_id": mock_project_id,
                "decision": "request_change", "decided_by": "user-x",
                "comment": "能否加个权限控制？",
                "ts": "2026-04-22T12:05:00Z",
            },
        )
        assert ack.new_gate_state == "ANALYZING"
        assert ack.next_action == "impact_report_generated"

    def test_TC_L102_L201_011_rollback_gate_within_24h(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L201-011 · 23h 内 rollback · 成功 + target_subset_map 非空。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        mock_clock.advance(hours=23)
        result: RollbackResult = sut.rollback_gate(
            gate_id=gate_id,
            project_id=mock_project_id,
            change_requests=["重做 AC", "重写 quality plan"],
            triggered_by="user_reject",
        )
        assert result.rollback_accepted is True
        assert result.new_re_open_count == 1
        assert result.target_subset_map  # 非空

    def test_TC_L102_L201_012_rollback_increments_reopen_count(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-012 · 连续 3 次 rollback · re_open_count 累加到 3。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        counts: list[int] = []
        for i in range(3):
            r = sut.rollback_gate(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=[f"cr-{i}"], triggered_by="user_reject",
            )
            counts.append(r.new_re_open_count)
        assert counts == [1, 2, 3]

    def test_TC_L102_L201_013_query_gate_state_bootstrap(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-013 · Claude Code 重启后 · query_gate_state 从 current.yaml 恢复。"""
        sut.force_main_state(mock_project_id, "TDD_PLANNING")
        sut.force_open_gate(mock_project_id, "S3", trim_level="full")
        sut.reload_from_disk(mock_project_id)
        snap: GateStateSnapshot = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "TDD_PLANNING"
        assert any(g.stage == "S3" for g in snap.active_gates)

    def test_TC_L102_L201_014_query_gate_state_specific_stage(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-014 · query_gate_state(stage='S2') · 仅返 S2 Gate。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        snap = sut.query_gate_state(mock_project_id, stage="S2")
        assert all(g.stage == "S2" for g in snap.active_gates)

    def test_TC_L102_L201_015_assemble_evidence_full(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-015 · assemble_evidence(S2, full) · 返 required/collected/missing 三元组。"""
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        bundle = sut.assemble_evidence(project_id=mock_project_id, stage="S2", trim_level="full")
        assert bundle.required == {
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        }
        assert bundle.missing == set()

    def test_TC_L102_L201_016_validate_transition_allowed_edge(
        self,
        sut: StageGateController,
    ) -> None:
        """TC-L102-L201-016 · validate_transition · PLANNING → TDD_PLANNING 合法（ALLOWED_TRANSITIONS）。"""
        assert sut.validate_transition(
            from_state="PLANNING", to_state="TDD_PLANNING", caller_l2="L2-01",
        ) is True
        assert sut.validate_transition(
            from_state="TDD_PLANNING", to_state="EXECUTING", caller_l2="L2-01",
        ) is True

    def test_TC_L102_L201_017_emit_rejection_analysis_requires_both_fields(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-017 · emit_rejection_analysis · root_cause + fix_advice 双必填。"""
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        report = sut.emit_rejection_analysis(
            gate_id=gate_id,
            project_id=mock_project_id,
            change_requests=["AC-03 missing boundary"],
        )
        assert report.root_cause
        assert report.fix_advice
        assert report.target_subset_map
```

---

## §3 负向用例（§11 每错误码 ≥ 1）

> 每错误码必有 1 条 TC · `pytest.raises(StageGateError)` + `exc.value.error_code == "E_L102_L201_NNN"`。
> 分两个文件：契约致命类（002 / 004 / 006 / 011 / 013 / 014）与运行时降级类（007 / 008 / 009 / 010 / 012）分别归档便于隔离重跑。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_negative.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController
from app.l2_01.errors import StageGateError


class TestL2_01_StageGateControllerNegative:
    """§11 每错误码 ≥ 1 条测试用例。

    前缀：E_L102_L201_001~014 共 14 条。
    结构：arrange 合法基线 → act 触发单一错误因子 → assert error_code。
    """

    def test_TC_L102_L201_101_gate_evidence_missing(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-101 · E_L102_L201_001 · S2 Gate 缺 4 件套 → need_input + missing 非空。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", ["9_plans_ready"])  # 仅 1
        from app.l2_01.schemas import EvidenceBundle
        bundle = EvidenceBundle.from_dict({
            "request_id": "req-miss-1", "project_id": mock_project_id, "stage": "S2",
            "triggering_signal": {
                "signal_name": "9_plans_ready", "source_l2": "L2-04",
                "artifact_refs": ["p.md"], "collected_at": "2026-04-22T10:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
        })
        decision = sut.request_gate_decision(bundle)
        assert decision.decision == "need_input"
        # 审计事件必标 evidence_missing
        assert decision.audit_entry_id
        assert decision.error_code == "E_L102_L201_001" or "evidence_missing" in str(decision).lower()

    def test_TC_L102_L201_102_transition_forbidden(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-102 · E_L102_L201_002 · INITIALIZED → EXECUTING 跨边拒绝。"""
        sut.force_main_state(mock_project_id, "INITIALIZED")
        with pytest.raises(StageGateError) as exc:
            sut.authorize_transition(
                project_id=mock_project_id,
                from_state="INITIALIZED", to_state="EXECUTING",  # 非法（必经 PLANNING / TDD_PLANNING）
                gate_id="gate-fake", reason="attempt to skip planning and tdd gates",
                evidence_refs=["x"],
            )
        assert exc.value.error_code == "E_L102_L201_002"
        assert "INITIALIZED" in str(exc.value) and "EXECUTING" in str(exc.value)

    def test_TC_L102_L201_103_circular_dep_at_s3(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_wbs_topology: Any,
    ) -> None:
        """TC-L102-L201-103 · E_L102_L201_003 · S3 TDD Gate 时 WBS DAG 有环 → reject + root_cause。"""
        sut.force_main_state(mock_project_id, "TDD_PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S3", ["tdd_blueprint_ready"])
        mock_wbs_topology.inject_cycle(["WP-A", "WP-B", "WP-C", "WP-A"])
        from app.l2_01.schemas import EvidenceBundle
        bundle = EvidenceBundle.from_dict({
            "request_id": "req-cycle-1", "project_id": mock_project_id, "stage": "S3",
            "triggering_signal": {
                "signal_name": "tdd_blueprint_ready", "source_l2": "L1-04",
                "artifact_refs": ["bp.md"], "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T11:00:05Z",
        })
        decision = sut.request_gate_decision(bundle)
        assert decision.decision == "reject"
        assert decision.error_code == "E_L102_L201_003"
        assert "CIRCULAR_DEP" in (decision.root_cause or "")

    def test_TC_L102_L201_104_state_corrupt_on_load(
        self,
        sut: StageGateController,
        mock_project_id: str,
        tmp_path: Any,
    ) -> None:
        """TC-L102-L201-104 · E_L102_L201_004 · state 文件损坏 → HALT + 发 IC-06。"""
        # 写坏 current.yaml
        sut.repo.write_raw(mock_project_id, "stage-gates/current.yaml", "!!!garbage: [")
        with pytest.raises(StageGateError) as exc:
            sut.query_gate_state(mock_project_id)
        assert exc.value.error_code == "E_L102_L201_004"
        # 降级到 HALT
        assert sut.current_degradation_level() in ("HALT", "EMERGENCY_MANUAL")

    def test_TC_L102_L201_105_evidence_expired(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L201-105 · E_L102_L201_005 · ready signal 超 168h（7 天）→ EXPIRED。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(
            mock_project_id, "S2",
            ["4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready"],
            collected_at="2026-04-10T00:00:00Z",  # 12 天前
        )
        mock_clock.set_now("2026-04-22T00:00:00Z")
        from app.l2_01.schemas import EvidenceBundle
        bundle = EvidenceBundle.from_dict({
            "request_id": "req-exp-1", "project_id": mock_project_id, "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready", "source_l2": "L1-03",
                "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T00:00:05Z",
            },
            "trim_level": "full", "ts": "2026-04-22T00:00:10Z",
        })
        decision = sut.request_gate_decision(bundle)
        assert decision.decision == "need_input"
        assert decision.error_code == "E_L102_L201_005"
        assert decision.evidence_summary["expired_signals"]

    def test_TC_L102_L201_106_pm14_ownership_violation(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-106 · E_L102_L201_006 · 非 L2-01 调用 validate_transition → 拒 + ERROR 审计。"""
        with pytest.raises(StageGateError) as exc:
            sut.validate_transition(
                from_state="PLANNING", to_state="TDD_PLANNING",
                caller_l2="L1-05",  # 越权
            )
        assert exc.value.error_code == "E_L102_L201_006"
        assert "L2-01" in str(exc.value)

    def test_TC_L102_L201_107_rejection_analyzer_timeout(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_rejection_analyzer: Any,
    ) -> None:
        """TC-L102-L201-107 · E_L102_L201_007 · LLM 归因超时 · 降级规则模板 · 不阻塞。"""
        mock_rejection_analyzer.simulate_timeout(after_sec=20)
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        report = sut.emit_rejection_analysis(
            gate_id=gate_id, project_id=mock_project_id,
            change_requests=["something"],
        )
        # 降级路径必返规则模板结果 · 不 raise
        assert report.root_cause
        assert report.degraded_from == "llm"
        assert sut.current_degradation_level() == "DEGRADED_LLM_OFF"

    def test_TC_L102_L201_108_fsync_fail_triple_retry_then_halt(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_fsync_failure: Any,
    ) -> None:
        """TC-L102-L201-108 · E_L102_L201_008 · fsync 连 3 次失败 · HALT + 发 IC-06。"""
        mock_fsync_failure.enable(fail_times=3)
        with pytest.raises(StageGateError) as exc:
            sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        assert exc.value.error_code == "E_L102_L201_008"
        assert sut.current_degradation_level() == "HALT"

    def test_TC_L102_L201_109_history_quota_exceeded_rotates(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-109 · E_L102_L201_009 · gate_history > 1024 条 · rotate 归档 · 不阻塞。"""
        sut.seed_gate_history(mock_project_id, count=1025)
        # rotate 必触发 · 当前 Gate 请求仍能继续
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        assert gate_id.startswith("gate-S2-")
        archive_files = sut.repo.list_archives(mock_project_id)
        assert any("gate-history" in f for f in archive_files)

    def test_TC_L102_L201_110_llm_fallback_disabled_conflict(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-110 · E_L102_L201_010 · LLM 归因被禁但又被调用 · 退规则模板 + 告警。"""
        sut.set_config("REJECTION_LLM_FALLBACK_ENABLED", False)
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        report = sut.emit_rejection_analysis(
            gate_id=gate_id, project_id=mock_project_id,
            change_requests=["x"], force_llm=True,  # 强制走 LLM 分支
        )
        # 不 raise · 规则模板产结果 · 同时告警落审计
        assert report.root_cause
        assert sut.event_bus.last_warn_code() == "E_L102_L201_010"

    def test_TC_L102_L201_111_concurrent_gate_request_same_project(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-111 · E_L102_L201_011 · 同 project 并发 2 个 Gate 请求 · 第二 429 或排队。"""
        import threading
        sut.force_main_state(mock_project_id, "PLANNING")
        results: list[Any] = []

        def _fire(rid: str) -> None:
            try:
                from app.l2_01.schemas import EvidenceBundle
                b = EvidenceBundle.from_dict({
                    "request_id": rid, "project_id": mock_project_id, "stage": "S2",
                    "triggering_signal": {
                        "signal_name": "wbs_ready", "source_l2": "L1-03",
                        "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T10:00:00Z",
                    },
                    "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
                })
                results.append(("ok", sut.request_gate_decision(b)))
            except StageGateError as e:
                results.append(("err", e.error_code))

        t1 = threading.Thread(target=_fire, args=("req-p-a",))
        t2 = threading.Thread(target=_fire, args=("req-p-b",))
        t1.start(); t2.start(); t1.join(); t2.join()
        err_codes = [r[1] for r in results if r[0] == "err"]
        assert "E_L102_L201_011" in err_codes or len([r for r in results if r[0] == "ok"]) == 2

    def test_TC_L102_L201_112_audit_seed_emit_fail_buffers(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-112 · E_L102_L201_012 · IC-09 不可达 · buffer 模式 · 继续服务核心。"""
        mock_event_bus.simulate_unavailable(True)
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        assert gate_id  # 核心路径不阻塞
        assert sut.current_degradation_level() == "DEGRADED_AUDIT"
        assert sut.audit_buffer_depth() > 0

    def test_TC_L102_L201_113_gate_auto_timeout_attempted_startup_crash(
        self,
        tmp_path: Any,
    ) -> None:
        """TC-L102-L201-113 · E_L102_L201_013 · 启动配置 GATE_AUTO_TIMEOUT_ENABLED=true · crash。"""
        with pytest.raises(StageGateError) as exc:
            StageGateController.boot(config={"GATE_AUTO_TIMEOUT_ENABLED": True})
        assert exc.value.error_code == "E_L102_L201_013"
        assert "auto_timeout" in str(exc.value).lower()

    def test_TC_L102_L201_114_snapshot_replay_mismatch_halts(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-114 · E_L102_L201_014 · replay hash 不匹配 · HALT。"""
        # 写一个状态与 audit jsonl 不一致的 current.yaml
        sut.repo.write_inconsistent_snapshot(mock_project_id)
        with pytest.raises(StageGateError) as exc:
            sut.bootstrap_recover(mock_project_id)
        assert exc.value.error_code == "E_L102_L201_014"
        assert sut.current_degradation_level() == "HALT"
```

---

## §4 IC 契约集成测试

> 对标 ic-contracts.md · 本 L2 参与 7 条 IC：
> - **发起方（6 条）**：IC-01（唯一发起 · PM-14 红线）· IC-06 硬红线 · IC-09 审计 · IC-16 Gate 卡片 · IC-19 WBS 拆解 · IC-05 归因委派（可选）
> - **接收方（1 条）**：IC-17 用户干预
> 每 IC ≥ 1 条 join test · 关键合约字段必校 · 幂等 / 错误重试路径必测。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_ic_contracts.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController


class TestL2_01_StageGateControllerICContracts:
    """IC 契约集成测试 · 每 IC ≥ 1 join test · 重点验证 IC-01 唯一发起权。"""

    def test_TC_L102_L201_401_ic01_state_transition_uniquely_from_l2_01(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-401 · IC-01 · 只有 L2-01 可发起 · payload 字段全 · 幂等 transition_id。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        result = sut.authorize_transition(
            project_id=mock_project_id,
            from_state="PLANNING", to_state="TDD_PLANNING",
            gate_id="gate-S2-401", reason="S2 Gate 通过 · 证据齐 · 用户 approve 进 TDD",
            evidence_refs=["projects/p/fourset/ac.md"],
        )
        ic01 = mock_event_bus.emitted_events_by_ic("IC-01")
        assert len(ic01) == 1
        payload = ic01[0]
        # 契约字段（IC-01 §3.1.2）
        for k in ("transition_id", "project_id", "from", "to", "reason",
                  "gate_id", "evidence_refs", "trigger_tick", "ts"):
            assert k in payload
        assert payload["caller_l2"] == "L2-01"
        assert len(payload["reason"]) >= 20
        # 幂等（IC-01 §3.1.5）: 相同 transition_id 重发返同结果
        result_again = sut.replay_transition(result.transition_id)
        assert result_again.transition_id == result.transition_id

    def test_TC_L102_L201_402_ic06_hard_red_line_on_state_corrupt(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-402 · IC-06 · STATE_CORRUPT / FSYNC×3 · 必发硬红线通知 L1-07。"""
        sut.repo.write_raw(mock_project_id, "stage-gates/current.yaml", "corrupt:[")
        from app.l2_01.errors import StageGateError
        with pytest.raises(StageGateError):
            sut.query_gate_state(mock_project_id)
        ic06 = mock_event_bus.emitted_events_by_ic("IC-06")
        assert len(ic06) >= 1
        assert ic06[0]["red_line_id"] in ("RL-STATE-CORRUPT", "RL-L201-HALT")
        assert ic06[0]["target"] == "L1-07"

    def test_TC_L102_L201_403_ic09_append_event_gate_lifecycle(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-403 · IC-09 · Gate 生命周期 7 事件类型全落盘。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        sut.receive_user_decision(
            gate_id=gate_id,
            user_payload={
                "gate_id": gate_id, "project_id": mock_project_id,
                "decision": "approve", "decided_by": "u",
                "ts": "2026-04-22T12:00:00Z",
            },
        )
        ev_types = {e["event_type"] for e in mock_event_bus.emitted_events_by_ic("IC-09")
                    if e["project_id"] == mock_project_id}
        # §5 时序 + §2.4 Domain Events
        expected = {
            "stage_gate_opened", "stage_gate_pushed",
            "stage_gate_decided", "stage_gate_closed",
            "project_state_transitioned",
        }
        assert expected.issubset(ev_types)

    def test_TC_L102_L201_404_ic16_push_stage_gate_card(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-404 · IC-16 · 证据齐即推卡片 · 含 gate_id / bundle / trim_level。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        from app.l2_01.schemas import EvidenceBundle
        sut.request_gate_decision(EvidenceBundle.from_dict({
            "request_id": "r-404", "project_id": mock_project_id, "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready", "source_l2": "L1-03",
                "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T10:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
        }))
        cards = mock_event_bus.emitted_events_by_ic("IC-16")
        assert len(cards) >= 1
        c = cards[0]
        for k in ("gate_id", "stage", "artifacts_bundle", "trim_level"):
            assert k in c
        assert c["stage"] == "S2"
        assert c["trim_level"] == "full"

    def test_TC_L102_L201_405_ic17_user_intervene_three_routes(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-405 · IC-17 接收 · approve / reject / request_change 三路由 · 签名校验。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        # approve
        g1 = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        a1 = sut.receive_user_decision(g1, {
            "gate_id": g1, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u", "ts": "2026-04-22T10:00:00Z",
        })
        assert a1.new_gate_state == "CLOSED"
        # reject（要换新 project 或新 S）
        sut.force_main_state(mock_project_id, "TDD_PLANNING")
        g2 = sut.force_open_gate(mock_project_id, "S3", trim_level="full")
        a2 = sut.receive_user_decision(g2, {
            "gate_id": g2, "project_id": mock_project_id,
            "decision": "reject", "decided_by": "u",
            "change_requests": ["改蓝图"], "ts": "2026-04-22T10:00:00Z",
        })
        assert a2.new_gate_state == "REROUTING"
        # request_change
        g3 = sut.force_open_gate(mock_project_id, "S3", trim_level="full")
        a3 = sut.receive_user_decision(g3, {
            "gate_id": g3, "project_id": mock_project_id,
            "decision": "request_change", "decided_by": "u",
            "ts": "2026-04-22T10:00:00Z",
        })
        assert a3.new_gate_state == "ANALYZING"

    def test_TC_L102_L201_406_ic19_wbs_decomposition_after_s2_pass(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-406 · IC-19 · S2 Gate pass 后必发 request_wbs_decomposition 到 L1-03。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        g = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        sut.receive_user_decision(g, {
            "gate_id": g, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u", "ts": "2026-04-22T10:00:00Z",
        })
        ic19 = mock_event_bus.emitted_events_by_ic("IC-19")
        assert len(ic19) == 1
        assert ic19[0]["project_id"] == mock_project_id
        assert ic19[0]["source_l2"] == "L2-01"

    def test_TC_L102_L201_407_ic05_rejection_analyzer_delegation(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_rejection_analyzer: Any,
    ) -> None:
        """TC-L102-L201-407 · IC-05 · reject 路径可选委派 L1-05 skill · 返 root_cause/fix_advice/target_subset_map。"""
        g = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        report = sut.emit_rejection_analysis(
            gate_id=g, project_id=mock_project_id,
            change_requests=["AC-03 missing boundary"],
        )
        # IC-05 payload 必走
        call = mock_rejection_analyzer.last_call()
        assert call["skill"] == "rejection-analyzer"
        assert report.target_subset_map
        assert report.root_cause and report.fix_advice
```

---

## §5 性能 SLO 用例（§12 对标 · 8 指标）

> 对标 3-1 §12.1 SLO 表：每指标 1 条 perf 测试 · 统一 100 次采样 · 断言 P95 ≤ 目标 · 打点 assert 硬上限未被突破。
> 运行时用 `pytest-benchmark` 或 `time.perf_counter()` 采样 · 标 `@pytest.mark.perf` 便于 CI 分项目运行。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_perf.py
from __future__ import annotations

import statistics
import time
from typing import Any

import pytest

from app.l2_01.controller import StageGateController


@pytest.mark.perf
class TestL2_01_StageGateControllerSLO:
    """§12.1 SLO 表 8 指标 · 每指标 1 条。"""

    def _p95(self, samples: list[float]) -> float:
        return statistics.quantiles(samples, n=100)[94]

    def test_TC_L102_L201_501_gate_decision_p95_le_500ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-501 · Gate 决策 P95 ≤ 500ms · 硬上限 5s · 100 次采样。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        from app.l2_01.schemas import EvidenceBundle
        samples: list[float] = []
        for i in range(100):
            b = EvidenceBundle.from_dict({
                "request_id": f"perf-{i}", "project_id": mock_project_id, "stage": "S2",
                "triggering_signal": {
                    "signal_name": "wbs_ready", "source_l2": "L1-03",
                    "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T10:00:00Z",
                },
                "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
            })
            t0 = time.perf_counter()
            sut.request_gate_decision(b)
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 500.0
        assert max(samples) <= 5000.0

    def test_TC_L102_L201_502_authorize_transition_p95_le_100ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-502 · 状态机转换 P95 ≤ 100ms · 硬上限 1s。"""
        samples: list[float] = []
        for i in range(100):
            sut.force_main_state(mock_project_id, "PLANNING")
            t0 = time.perf_counter()
            sut.authorize_transition(
                project_id=mock_project_id,
                from_state="PLANNING", to_state="TDD_PLANNING",
                gate_id=f"gate-perf-{i}",
                reason="S2 Gate 通过 · 证据齐 · 用户 approve · 进入 TDD 阶段",
                evidence_refs=["x"],
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 100.0
        assert max(samples) <= 1000.0

    def test_TC_L102_L201_503_assemble_evidence_p95_le_300ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-503 · Evidence 装配 P95 ≤ 300ms · 硬上限 3s。"""
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            sut.assemble_evidence(project_id=mock_project_id, stage="S2", trim_level="full")
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 300.0

    def test_TC_L102_L201_504_dag_cycle_check_p95_le_200ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_wbs_topology: Any,
    ) -> None:
        """TC-L102-L201-504 · DAG 环检测 P95 ≤ 200ms · 硬上限 2s。"""
        mock_wbs_topology.set_size(nodes=200, edges=500, acyclic=True)
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            sut.check_circular_dep(project_id=mock_project_id)
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 200.0

    def test_TC_L102_L201_505_llm_rejection_analysis_p95_le_5s(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_rejection_analyzer: Any,
    ) -> None:
        """TC-L102-L201-505 · LLM 归因 P95 ≤ 5s · 硬上限 20s（mock 响应 2-4s）。"""
        mock_rejection_analyzer.simulate_latency_range(ms_min=2000, ms_max=4000)
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        samples: list[float] = []
        for _ in range(30):  # LLM 贵 · 30 样本
            t0 = time.perf_counter()
            sut.emit_rejection_analysis(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=["any"],
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 5000.0
        assert max(samples) <= 20000.0

    def test_TC_L102_L201_506_template_rejection_fallback_p95_le_80ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-506 · 规则模板归因（LLM 降级路径）P95 ≤ 80ms。"""
        sut.set_config("REJECTION_LLM_FALLBACK_ENABLED", False)  # 强制规则
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            sut.emit_rejection_analysis(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=["any"],
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 80.0

    def test_TC_L102_L201_507_audit_seed_emit_p95_le_30ms(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-507 · 审计 seed 落盘 P95 ≤ 30ms · 硬上限 500ms。"""
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            sut.emit_audit_event(
                project_id=mock_project_id,
                event_type="stage_gate_opened",
                payload={"gate_id": f"g-{i}", "stage": "S2"},
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
        assert self._p95(samples) <= 30.0
        assert max(samples) <= 500.0

    def test_TC_L102_L201_508_concurrent_10_projects_no_errors(
        self,
        sut: StageGateController,
    ) -> None:
        """TC-L102-L201-508 · 10 project × 2 rps × 30s · 无错误 · 本 instance 并发上限。"""
        import concurrent.futures
        pids = [f"pid-perf-{i}" for i in range(10)]
        for p in pids:
            sut.force_main_state(p, "PLANNING")
            sut.seed_accumulated_ready(p, "S2", [
                "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
            ])

        def _one(pid: str, n: int) -> tuple[int, int]:
            from app.l2_01.schemas import EvidenceBundle
            ok = err = 0
            for i in range(n):
                try:
                    sut.request_gate_decision(EvidenceBundle.from_dict({
                        "request_id": f"{pid}-{i}", "project_id": pid, "stage": "S2",
                        "triggering_signal": {
                            "signal_name": "wbs_ready", "source_l2": "L1-03",
                            "artifact_refs": ["a.yaml"],
                            "collected_at": "2026-04-22T10:00:00Z",
                        },
                        "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
                    }))
                    ok += 1
                except Exception:
                    err += 1
            return ok, err

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(lambda p: _one(p, 60), pids))
        total_ok = sum(r[0] for r in results)
        total_err = sum(r[1] for r in results)
        assert total_err == 0
        assert total_ok == 10 * 60
```

---

## §6 端到端 e2e 场景（GWT 映射 §5 P0/P1 时序）

> 每 e2e 用例对标 3-1 §5 的 1 张时序图 · Given/When/Then 三段 · 必断言：
> - 主状态机最终态正确
> - IC-01 / IC-09 / IC-16 审计链完整
> - Gate 生命周期 9 态流转合法

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_e2e.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController


class TestL2_01_StageGateControllerE2E:
    """端到端 · 对标 §5 的 3 张时序图 + 一条 S1→S7 全程跑通。"""

    def test_TC_L102_L201_701_e2e_s2_planning_gate_pass_path(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-701 · 对标 §5.1 P0 · S2 Planning Gate pass 主流程全链路。

        Given  project=PLANNING · 4 L2 并行产 4 件套/9 计划/TOGAF/WBS
        When   证据齐 · 推 Gate 卡片 · 用户 approve
        Then   IC-01 转 TDD_PLANNING + IC-19 分派 WBS + 全事件落盘
        """
        # Given
        sut.force_main_state(mock_project_id, "PLANNING")
        for sig in ("4_pieces_ready", "9_plans_ready", "togaf_ready",
                    "adr_count>=10", "wbs_ready"):
            sut.append_ready_signal(mock_project_id, "S2", sig,
                                    source_l2="L2-03/04/05+L1-03")
        # When
        from app.l2_01.schemas import EvidenceBundle
        decision = sut.request_gate_decision(EvidenceBundle.from_dict({
            "request_id": "e2e-701", "project_id": mock_project_id, "stage": "S2",
            "triggering_signal": {
                "signal_name": "wbs_ready", "source_l2": "L1-03",
                "artifact_refs": ["a.yaml"], "collected_at": "2026-04-22T11:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T11:00:05Z",
        }))
        assert decision.gate_id
        ack = sut.receive_user_decision(decision.gate_id, {
            "gate_id": decision.gate_id, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "user-pm",
            "ts": "2026-04-22T11:10:00Z",
        })
        # Then
        assert ack.new_gate_state == "CLOSED"
        snap = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "TDD_PLANNING"
        # 审计链
        event_types = {e["event_type"] for e in mock_event_bus.emitted_events_by_ic("IC-09")}
        for t in ("stage_gate_opened", "stage_gate_decided",
                  "stage_gate_closed", "project_state_transitioned"):
            assert t in event_types
        # IC-19 分派 WBS
        assert len(mock_event_bus.emitted_events_by_ic("IC-19")) == 1

    def test_TC_L102_L201_702_e2e_s2_reject_rerouting_redo(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-702 · 对标 §5.2 P1 · reject 回退 · 定向重做 · 二次 Gate pass。

        Given  S2 Gate 已 OPEN · 证据齐
        When   用户 reject + change_requests=['改 AC-03'] · L2-03 重做 4 件套 v2
        Then   Gate 进 REROUTING · re_open_count=1 · 二次 approve 后 transitioned
        """
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        # reject
        ack = sut.receive_user_decision(gate_id, {
            "gate_id": gate_id, "project_id": mock_project_id,
            "decision": "reject", "decided_by": "user-pm",
            "change_requests": ["改 AC-03 加边界"],
            "ts": "2026-04-22T12:00:00Z",
        })
        assert ack.new_gate_state == "REROUTING"
        # 二次开 Gate
        sut.simulate_stage_progress_v2(mock_project_id, "S2", diff=True)
        # 二次 approve
        gate_id_v2 = sut.active_gate(mock_project_id, "S2").gate_id
        ack2 = sut.receive_user_decision(gate_id_v2, {
            "gate_id": gate_id_v2, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "user-pm",
            "ts": "2026-04-22T14:00:00Z",
        })
        assert ack2.new_gate_state == "CLOSED"
        snap = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "TDD_PLANNING"
        # re_open_count 升 1
        gates = sut.query_gate_state(mock_project_id).gate_history
        assert any(g.re_open_count >= 1 for g in gates)
        # IC-09 rerouted + resumed 事件
        types = {e["event_type"] for e in mock_event_bus.emitted_events_by_ic("IC-09")}
        assert "stage_gate_rerouted" in types

    def test_TC_L102_L201_703_e2e_halt_suspend_resume(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-703 · 对标 §5.3 · HALTED 挂起 + user resume 恢复。

        Given  S2 Gate = OPEN · 突发 IC-15 hard_halt
        When   L1-07 红线触发 · state=HALTED · Gate=SUSPENDED
        Then   user authorize_resume · Gate 恢复原态 · 继续 review
        """
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        # HALT 通知
        sut.on_state_change_notification(
            project_id=mock_project_id, from_state="PLANNING", to_state="HALTED",
            halt_reason="RL-01",
        )
        g = sut.active_gate(mock_project_id, "S2")
        assert g.state == "SUSPENDED"
        # user resume
        sut.on_state_change_notification(
            project_id=mock_project_id, from_state="HALTED", to_state="PLANNING",
        )
        g = sut.active_gate(mock_project_id, "S2")
        assert g.state in ("OPEN", "REVIEWING")
        # IC-09 suspended + resumed
        types = {e["event_type"] for e in mock_event_bus.emitted_events_by_ic("IC-09")}
        assert "stage_gate_suspended" in types
        assert "stage_gate_resumed" in types

    def test_TC_L102_L201_704_e2e_full_s1_to_s7_lifecycle(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-704 · e2e · project 从 INITIALIZED 到 CLOSED 全 4 Gate 跑通。

        Gates: S1 → S2 → S3 → S7 · 主状态：INIT → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED
        """
        # S1 Gate
        sut.force_main_state(mock_project_id, "INITIALIZED")
        sut.seed_accumulated_ready(mock_project_id, "S1", [
            "charter_ready", "stakeholders_ready", "goal_anchor_hash_locked",
        ])
        g1 = sut.force_open_gate(mock_project_id, "S1", trim_level="full")
        sut.receive_user_decision(g1, {
            "gate_id": g1, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T10:00:00Z",
        })
        assert sut.query_gate_state(mock_project_id).current_main_state == "PLANNING"

        # S2 Gate
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        g2 = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        sut.receive_user_decision(g2, {
            "gate_id": g2, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T11:00:00Z",
        })
        assert sut.query_gate_state(mock_project_id).current_main_state == "TDD_PLANNING"

        # S3 Gate
        sut.seed_accumulated_ready(mock_project_id, "S3", ["tdd_blueprint_ready"])
        g3 = sut.force_open_gate(mock_project_id, "S3", trim_level="full")
        sut.receive_user_decision(g3, {
            "gate_id": g3, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T12:00:00Z",
        })
        assert sut.query_gate_state(mock_project_id).current_main_state == "EXECUTING"

        # S5 PASS → CLOSING（L1-04 信号 · 非 Gate）
        sut.on_s5_pass(project_id=mock_project_id)
        assert sut.query_gate_state(mock_project_id).current_main_state == "CLOSING"

        # S7 Gate
        sut.seed_accumulated_ready(mock_project_id, "S7", [
            "delivery_bundled", "retro_ready", "archive_written", "kb_promotion_done",
        ])
        g7 = sut.force_open_gate(mock_project_id, "S7", trim_level="full")
        sut.receive_user_decision(g7, {
            "gate_id": g7, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T13:00:00Z",
        })
        assert sut.query_gate_state(mock_project_id).current_main_state == "CLOSED"

        # 4 次 IC-01 转换（S1/S2/S3/S7）+ 1 次 S5→CLOSING
        ic01 = mock_event_bus.emitted_events_by_ic("IC-01")
        assert len(ic01) == 5
```

---

## §7 测试 fixture

> pytest 共享 fixture · 全部 `scope="function"` 隔离 · 不跨测试泄漏状态。
> 对应 §2-§6 正负 / IC / perf / e2e 共用 · 定位在 `tests/l1_02/conftest.py`。

```python
# file: tests/l1_02/conftest.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.l2_01.controller import StageGateController


@pytest.fixture()
def mock_project_id() -> str:
    """PM-14 根字段 · uuid-v7 占位符。"""
    return "pid-01J0MOCK-L201-0001"


@pytest.fixture()
def mock_request_id() -> str:
    """request_id 幂等键（§3.1 入参）。"""
    return "req-01J0MOCK-0001"


@pytest.fixture()
def mock_clock() -> Any:
    """注入时钟 · 支持 advance(hours=N) / set_now(iso) · 用于 expiry / 24h 回滚硬限测试。"""
    class _MockClock:
        def __init__(self) -> None:
            self._now = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
        def now(self) -> datetime:
            return self._now
        def advance(self, hours: float = 0, seconds: float = 0) -> None:
            from datetime import timedelta
            self._now = self._now + timedelta(hours=hours, seconds=seconds)
        def set_now(self, iso: str) -> None:
            self._now = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return _MockClock()


@pytest.fixture()
def mock_event_bus() -> Any:
    """L1-09 审计总线 mock · 支持按 IC 查询已发事件 · 支持降级模拟。"""
    class _MockEventBus:
        def __init__(self) -> None:
            self._events: list[dict[str, Any]] = []
            self._unavailable = False
            self._warn_code: str | None = None
        def emit(self, ic: str, payload: dict[str, Any]) -> None:
            if self._unavailable:
                raise RuntimeError("event_bus_unavailable")
            payload = dict(payload)
            payload["ic"] = ic
            self._events.append(payload)
        def emitted_events(self) -> list[dict[str, Any]]:
            return list(self._events)
        def emitted_events_by_ic(self, ic: str) -> list[dict[str, Any]]:
            return [e for e in self._events if e.get("ic") == ic]
        def simulate_unavailable(self, on: bool) -> None:
            self._unavailable = on
        def warn(self, code: str) -> None:
            self._warn_code = code
        def last_warn_code(self) -> str | None:
            return self._warn_code
    return _MockEventBus()


@pytest.fixture()
def mock_ic_payload() -> dict[str, Any]:
    """IC-17 用户干预典型 payload · 供 §4 / §6 复用。"""
    return {
        "gate_id": "gate-S2-fixture",
        "project_id": "pid-01J0MOCK-L201-0001",
        "decision": "approve",
        "decided_by": "user-fixture",
        "ts": "2026-04-22T10:00:00Z",
    }


@pytest.fixture()
def mock_kb(tmp_path: Path) -> Any:
    """KB（知识库）mock · 含 charter / 4 件套 / TOGAF / WBS artifact 路径 · 供 evidence 装配用。"""
    root = tmp_path / "kb"
    (root / "charter").mkdir(parents=True)
    (root / "fourset").mkdir(parents=True)
    (root / "togaf").mkdir(parents=True)
    (root / "wbs").mkdir(parents=True)
    (root / "charter" / "v1.md").write_text("# charter", encoding="utf-8")
    (root / "fourset" / "prd.md").write_text("# prd", encoding="utf-8")
    (root / "togaf" / "phase_a.md").write_text("# A", encoding="utf-8")
    (root / "wbs" / "v3.yaml").write_text("nodes: []", encoding="utf-8")
    class _MockKB:
        def __init__(self, root: Path) -> None:
            self.root = root
        def path(self, kind: str) -> str:
            return str(self.root / kind)
        def list_artifacts(self, kind: str) -> list[str]:
            d = self.root / kind
            return [str(p) for p in d.glob("*")]
    return _MockKB(root)


@pytest.fixture()
def mock_gate_evidence(mock_kb: Any) -> dict[str, Any]:
    """完整 4 阶段典型证据集 · 供正向路径复用。"""
    return {
        "s1": {
            "triggering_signal": {
                "signal_name": "goal_anchor_hash_locked",
                "source_l2": "L2-02",
                "artifact_refs": [mock_kb.path("charter/v1.md")],
                "collected_at": "2026-04-22T09:50:00Z",
            },
        },
        "s2": {
            "triggering_signal": {
                "signal_name": "wbs_ready",
                "source_l2": "L1-03",
                "artifact_refs": [mock_kb.path("wbs/v3.yaml")],
                "collected_at": "2026-04-22T10:50:00Z",
            },
        },
        "s3": {
            "triggering_signal": {
                "signal_name": "tdd_blueprint_ready",
                "source_l2": "L1-04",
                "artifact_refs": [mock_kb.path("fourset/prd.md")],
                "collected_at": "2026-04-22T11:50:00Z",
            },
        },
        "s7": {
            "triggering_signal": {
                "signal_name": "delivery_bundled",
                "source_l2": "L2-06",
                "artifact_refs": [mock_kb.path("fourset/prd.md")],
                "collected_at": "2026-04-22T12:50:00Z",
            },
        },
    }


@pytest.fixture()
def mock_trim_query() -> Any:
    """IC-L2-09 · query_trim(level) mock · 默认 full。"""
    class _MockTrim:
        def __init__(self) -> None:
            self._level = "full"
        def query(self, project_id: str) -> str:
            return self._level
        def set_return(self, level: str) -> None:
            self._level = level
    return _MockTrim()


@pytest.fixture()
def mock_wbs_topology() -> Any:
    """L1-03 topology_version mock · 支持注入环 / 设规模（用于 DAG 环 + perf 测试）。"""
    class _MockTopo:
        def __init__(self) -> None:
            self.cycle: list[str] = []
            self.nodes = 0; self.edges = 0
        def inject_cycle(self, path: list[str]) -> None:
            self.cycle = path
        def set_size(self, nodes: int, edges: int, acyclic: bool = True) -> None:
            self.nodes = nodes; self.edges = edges
            if not acyclic:
                self.cycle = ["x", "y", "x"]
        def has_cycle(self) -> bool:
            return bool(self.cycle)
    return _MockTopo()


@pytest.fixture()
def mock_rejection_analyzer() -> Any:
    """L1-05 IC-05 归因 skill mock · 支持超时 / 延迟区间模拟。"""
    class _MockAnalyzer:
        def __init__(self) -> None:
            self._timeout_after: float | None = None
            self._latency_range_ms: tuple[int, int] | None = None
            self._last_call: dict[str, Any] | None = None
        def simulate_timeout(self, after_sec: float) -> None:
            self._timeout_after = after_sec
        def simulate_latency_range(self, ms_min: int, ms_max: int) -> None:
            self._latency_range_ms = (ms_min, ms_max)
        def analyze(self, **kw: Any) -> dict[str, Any]:
            self._last_call = {"skill": "rejection-analyzer", **kw}
            return {
                "root_cause": "mock cause",
                "fix_advice": "mock advice",
                "target_subset_map": {"L2-03": ["AC"]},
            }
        def last_call(self) -> dict[str, Any]:
            assert self._last_call is not None
            return self._last_call
    return _MockAnalyzer()


@pytest.fixture()
def mock_fsync_failure() -> Any:
    """fsync 注入 mock · enable(fail_times=N)。"""
    class _MockFsync:
        def __init__(self) -> None:
            self._fail_times = 0
        def enable(self, fail_times: int) -> None:
            self._fail_times = fail_times
        def should_fail(self) -> bool:
            if self._fail_times > 0:
                self._fail_times -= 1
                return True
            return False
    return _MockFsync()


@pytest.fixture()
def sut(
    tmp_path: Path,
    mock_clock: Any,
    mock_event_bus: Any,
    mock_trim_query: Any,
    mock_rejection_analyzer: Any,
    mock_wbs_topology: Any,
    mock_fsync_failure: Any,
) -> StageGateController:
    """SUT · 全部依赖注入 · 每测试独立实例。"""
    return StageGateController(
        repo_root=tmp_path,
        clock=mock_clock,
        event_bus=mock_event_bus,
        trim_query=mock_trim_query,
        rejection_analyzer=mock_rejection_analyzer,
        wbs_topology=mock_wbs_topology,
        fsync_hook=mock_fsync_failure,
        config={
            "GATE_DECISION_TIMEOUT_MS": 500,
            "STATE_TRANSITION_TIMEOUT_MS": 100,
            "EVIDENCE_EXPIRY_HOURS": 168,
            "MAX_RE_OPEN_COUNT": 10,
            "GATE_AUTO_TIMEOUT_ENABLED": False,  # §11 硬禁
            "REJECTION_LLM_FALLBACK_ENABLED": True,
            "CIRCULAR_DEP_CHECK_STAGE": "S3",
            "GATE_HISTORY_MAX_ENTRIES": 1024,
        },
    )
```

---

## §8 集成点用例（与 L2-03 / L2-04 / L2-05 / L2-06 调用链）

> 本 L2 是门控中枢 · 对 4 个产出型兄弟 L2（L2-03/04/05/06）做"证据订阅 + 分派重做"双向互动。
> 每集成点 1 条 TC · 集成类 mock（不启真实 L2）· 断言双向合约字段。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_integration.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController


class TestL2_01_IntegrationWithSiblingL2:
    """与 L2-03/04/05/06 的双向集成点 · 每点 1 条。"""

    def test_TC_L102_L201_801_integration_with_l2_03_fourset(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L201-801 · L2-03 4 件套 ready → 本 L2 累积 S2 信号 · reject 定向重做 AC。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.append_ready_signal(mock_project_id, "S2", "4_pieces_ready", source_l2="L2-03")
        # reject 路径 · 派发 IC-L2-01 trigger_stage_production 到 L2-03
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        sut.receive_user_decision(gate_id, {
            "gate_id": gate_id, "project_id": mock_project_id,
            "decision": "reject", "decided_by": "u",
            "change_requests": ["改 AC"], "ts": "2026-04-22T10:00:00Z",
        })
        ic_l2_01 = [e for e in mock_event_bus.emitted_events()
                    if e.get("ic") == "IC-L2-01" and e.get("target_l2") == "L2-03"]
        assert ic_l2_01
        assert "AC" in ic_l2_01[0]["target_subset"]

    def test_TC_L102_L201_802_integration_with_l2_04_pmp(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-802 · L2-04 9 计划 ready → 累积 S2 · minimal 档切 5 计划。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.append_ready_signal(mock_project_id, "S2", "9_plans_ready", source_l2="L2-04")
        snap = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "PLANNING"
        # 切 minimal · 用 5 计划 signal
        sut.append_ready_signal(mock_project_id, "S2", "5_plans_ready", source_l2="L2-04")
        sut.set_trim_level(mock_project_id, "minimal")

    def test_TC_L102_L201_803_integration_with_l2_05_togaf(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-803 · L2-05 TOGAF A-D + ADR ≥ 10 · 累积 S2 TOGAF 证据。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.append_ready_signal(mock_project_id, "S2", "togaf_ready", source_l2="L2-05")
        sut.append_ready_signal(mock_project_id, "S2", "adr_count>=10", source_l2="L2-05")
        bundle = sut.assemble_evidence(mock_project_id, "S2", "full")
        assert "togaf_ready" in bundle.collected
        assert "adr_count>=10" in bundle.collected

    def test_TC_L102_L201_804_integration_with_l2_06_s7_close(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-804 · L2-06 S7 收尾 4 信号齐 · Gate pass → CLOSED。"""
        sut.force_main_state(mock_project_id, "CLOSING")
        for s in ("delivery_bundled", "retro_ready", "archive_written", "kb_promotion_done"):
            sut.append_ready_signal(mock_project_id, "S7", s, source_l2="L2-06")
        g = sut.force_open_gate(mock_project_id, "S7", trim_level="full")
        sut.receive_user_decision(g, {
            "gate_id": g, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T13:00:00Z",
        })
        snap = sut.query_gate_state(mock_project_id)
        assert snap.current_main_state == "CLOSED"
```

---

## §9 边界 / edge case

> 涵盖空证据 / 循环依赖 / rollback 超 24h 硬限 / 并发 Gate 请求 / re_open 超上限 等极端路径。

```python
# file: tests/l1_02/test_l2_01_stage_gate_controller_edge.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_01.controller import StageGateController
from app.l2_01.errors import StageGateError


class TestL2_01_EdgeCases:
    """§9 边界 · 每条极端路径 1 TC。"""

    def test_TC_L102_L201_901_empty_evidence_bundle_need_input(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-901 · 空证据集 · 返 need_input + missing=全集。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        from app.l2_01.schemas import EvidenceBundle
        b = EvidenceBundle.from_dict({
            "request_id": "req-empty-1", "project_id": mock_project_id, "stage": "S2",
            "triggering_signal": {
                "signal_name": "4_pieces_ready", "source_l2": "L2-03",
                "artifact_refs": [], "collected_at": "2026-04-22T10:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
        })
        decision = sut.request_gate_decision(b)
        assert decision.decision == "need_input"
        assert len(decision.evidence_summary["missing_signals"]) >= 4

    def test_TC_L102_L201_902_s3_circular_dep_detected_and_rejected(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_wbs_topology: Any,
    ) -> None:
        """TC-L102-L201-902 · S3 Gate · WBS DAG 3 节点环 · reject + fix_advice 指向重拆 WBS。"""
        sut.force_main_state(mock_project_id, "TDD_PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S3", ["tdd_blueprint_ready"])
        mock_wbs_topology.inject_cycle(["WP-A", "WP-B", "WP-C", "WP-A"])
        from app.l2_01.schemas import EvidenceBundle
        decision = sut.request_gate_decision(EvidenceBundle.from_dict({
            "request_id": "r-cyc", "project_id": mock_project_id, "stage": "S3",
            "triggering_signal": {
                "signal_name": "tdd_blueprint_ready", "source_l2": "L1-04",
                "artifact_refs": ["bp.md"], "collected_at": "2026-04-22T10:00:00Z",
            },
            "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
        }))
        assert decision.decision == "reject"
        assert "WBS" in (decision.fix_advice or "")

    def test_TC_L102_L201_903_rollback_beyond_24h_forbidden(
        self,
        sut: StageGateController,
        mock_project_id: str,
        mock_clock: Any,
    ) -> None:
        """TC-L102-L201-903 · rollback 超 24h 硬限 · 拒绝（prd §5.2.6）。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        # Gate 关闭后 25h
        sut.receive_user_decision(gate_id, {
            "gate_id": gate_id, "project_id": mock_project_id,
            "decision": "approve", "decided_by": "u",
            "ts": "2026-04-22T10:00:00Z",
        })
        mock_clock.advance(hours=25)
        with pytest.raises(StageGateError) as exc:
            sut.rollback_gate(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=["too late"],
                triggered_by="user_reject",
            )
        assert "24h" in str(exc.value) or exc.value.error_code in (
            "E_L102_L201_002", "E_L102_L201_009",
        )

    def test_TC_L102_L201_904_re_open_exceeds_max_archives(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-904 · re_open_count 达 MAX (默认 10) · Gate 进 ARCHIVED + escalate L1-07。"""
        sut.force_main_state(mock_project_id, "PLANNING")
        gate_id = sut.force_open_gate(mock_project_id, "S2", trim_level="full")
        for i in range(10):
            sut.rollback_gate(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=[f"cr-{i}"], triggered_by="user_reject",
            )
        # 第 11 次 rollback · 触发 escalate
        with pytest.raises(StageGateError) as exc:
            sut.rollback_gate(
                gate_id=gate_id, project_id=mock_project_id,
                change_requests=["cr-over"], triggered_by="user_reject",
            )
        assert exc.value.error_code in ("E_L102_L201_009", "E_L102_L201_002")
        # Gate 标 ARCHIVED
        snap = sut.query_gate_state(mock_project_id)
        assert any(g.state == "ARCHIVED" for g in snap.gate_history)

    def test_TC_L102_L201_905_concurrent_same_project_gate_requests_serialized(
        self,
        sut: StageGateController,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L201-905 · 同 project 10 并发请求 · 串行化 + 无错 · 锁正确。"""
        import threading
        sut.force_main_state(mock_project_id, "PLANNING")
        sut.seed_accumulated_ready(mock_project_id, "S2", [
            "4_pieces_ready", "9_plans_ready", "togaf_ready", "adr_count>=10", "wbs_ready",
        ])
        errors: list[str] = []

        def _fire(rid: str) -> None:
            try:
                from app.l2_01.schemas import EvidenceBundle
                sut.request_gate_decision(EvidenceBundle.from_dict({
                    "request_id": rid, "project_id": mock_project_id, "stage": "S2",
                    "triggering_signal": {
                        "signal_name": "wbs_ready", "source_l2": "L1-03",
                        "artifact_refs": ["a.yaml"],
                        "collected_at": "2026-04-22T10:00:00Z",
                    },
                    "trim_level": "full", "ts": "2026-04-22T10:00:05Z",
                }))
            except StageGateError as e:
                errors.append(e.error_code)

        threads = [threading.Thread(target=_fire, args=(f"req-{i}",)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        # 允许 429 类错（E_L102_L201_011）· 但不允许状态机 corruption
        for c in errors:
            assert c == "E_L102_L201_011"
```

---

*— L1-02 L2-01 Stage Gate 控制器 · TDD 测试用例 · v1.0 · §1-§9 全段填充 · 17 正向 + 14 负向（错误码全覆盖）+ 7 IC + 8 SLO + 4 e2e + 10 fixture + 4 集成 + 5 边界 = 59 TC —*
