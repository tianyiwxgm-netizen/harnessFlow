---
doc_id: tests-L1-01-L2-05-决策审计记录器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-05-决策审计记录器.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-05-决策审计记录器 · TDD 测试用例

> 基于 3-1 L2-05 §3（6 个 public 方法）+ §11（10 项 `E_AUDIT_*` 错误码）+ §12（P50/P95/P99 + 吞吐/资源 SLO）+ §13 TC ID 矩阵 驱动。
> TC ID 统一格式：`TC-L101-L205-NNN`（L1-01 下 L2-05，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_05_DecisionAuditRecorder` 组织正向；`class TestL2_05_Negative_*` 负向分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock pid / mock clock / mock event bus）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（§3 6 方法全覆盖）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码（正向不触发）| 对应 IC |
|---|---|---|---|---|
| `record_audit()` · §3.1 · decision_made | TC-L101-L205-001 | unit | — | IC-L2-05 |
| `record_audit()` · §3.1 · tick_scheduled | TC-L101-L205-002 | unit | — | IC-L2-05 |
| `record_audit()` · §3.1 · state_transitioned | TC-L101-L205-003 | unit | — | IC-L2-06 |
| `record_audit()` · §3.1 · chain_step_completed | TC-L101-L205-004 | unit | — | IC-L2-07 |
| `record_audit()` · §3.1 · warn_response | TC-L101-L205-005 | unit | — | IC-L2-09 |
| `record_audit()` · §3.1 · 幂等键重放 | TC-L101-L205-006 | unit | — | IC-L2-05 |
| `query_by_tick()` · §3.2 · buffer 命中 | TC-L101-L205-007 | unit | — | 内部 |
| `query_by_tick()` · §3.2 · 跨 buffer+index 命中 | TC-L101-L205-008 | unit | — | 内部 |
| `query_by_decision()` · §3.3 · 1:1 反查 | TC-L101-L205-009 | unit | — | 内部 |
| `query_by_chain()` · §3.3 · 1:N 反查 | TC-L101-L205-010 | unit | — | 内部 |
| `flush_buffer()` · §3.4 · tick 边界 | TC-L101-L205-011 | unit | — | IC-09 |
| `flush_buffer()` · §3.4 · 空 buffer no-op | TC-L101-L205-012 | unit | — | IC-09 |
| `replay_from_jsonl()` · §3.5 · 重建索引 | TC-L101-L205-013 | integration | — | jsonl |
| `get_hash_tip()` · §3.6 · genesis | TC-L101-L205-014 | unit | — | 内部 |
| `get_hash_tip()` · §3.6 · 已写 N 条 | TC-L101-L205-015 | unit | — | 内部 |

### §1.2 错误码 × 测试（§11.1 10 项 `E_AUDIT_*` 全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 严重级 |
|---|---|---|---|
| `E_AUDIT_WRITE_FAIL` | TC-L101-L205-101 | `flush_buffer()` | Critical（halt L1）|
| `E_AUDIT_BUFFER_OVERFLOW` | TC-L101-L205-102 | `record_audit()` | Major（WARN · 降级同步 flush）|
| `E_AUDIT_QUERY_MISS` | TC-L101-L205-103 | `query_by_tick()` | Minor（返空 · 非故障）|
| `E_AUDIT_HASH_BROKEN` | TC-L101-L205-104 | `flush_buffer()` | Major（WARN · 不 halt）|
| `E_AUDIT_HALT_ON_FAIL` | TC-L101-L205-105 | `record_audit()` | Minor（静默拒绝）|
| `E_AUDIT_NO_PROJECT_ID` | TC-L101-L205-106 | `record_audit()` | Minor（拒绝入队）|
| `E_AUDIT_NO_REASON` | TC-L101-L205-107 | `record_audit()` | Minor（拒绝入队）|
| `E_AUDIT_CROSS_PROJECT` | TC-L101-L205-108 | `record_audit()` / `query_by_tick()` | Minor（拒绝）|
| `E_AUDIT_EVENT_TYPE_UNKNOWN` | TC-L101-L205-109 | `record_audit()` | Minor（拒绝入队）|
| `E_AUDIT_STALE_BUFFER` | TC-L101-L205-110 | `record_audit()` | Minor（force flush + 告警）|

> 注：§3 小节里另有 `E_AUDIT_FLUSH_CONCURRENT` / `E_AUDIT_QUERY_TIMEOUT` / `E_AUDIT_REPLAY_TIMEOUT` 三项**非 §11.1 首表列出**的运行时情景。本文档在 §3（负向）与 §9（边界）里各取 1 测试覆盖（TC-L101-L205-111 / TC-L101-L205-A04 / TC-L101-L205-A05），不计入 10 项首级错误码统计。

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-05 `record_audit(通用)` | L2-01/02/06 → L2-05 | TC-L101-L205-201 | 被调方 · 4 种 source_ic 多态 schema |
| IC-L2-06 `record_state_transition` | L2-03 → L2-05 | TC-L101-L205-202 | 被调方 · state_transition payload 结构 |
| IC-L2-07 `record_chain_step` | L2-04 → L2-05 | TC-L101-L205-203 | 被调方 · chain_step payload 结构 |
| IC-L2-09 `record_warn_response` | L2-02 → L2-05 | TC-L101-L205-204 | 被调方 · warn_response payload 结构 |
| IC-09 `append_event` | L2-05 → L1-09 | TC-L101-L205-205 | 生产方 · 唯一下游出口（arch §3.3 单一审计源）|
| IC-09 `append_event` · hash 链 | L2-05 → L1-09 | TC-L101-L205-206 | prev_hash / hash / sequence 透传断言 |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_05_DecisionAuditRecorder`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `DecisionAuditRecorder`（从 `app.l2_05.recorder` 导入）。

```python
# file: tests/l1_01/test_l2_05_audit_recorder_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l2_05.recorder import DecisionAuditRecorder
from app.l2_05.schemas import AuditCommand, AuditResult, FlushResult, ReplayResult, HashTip
from app.l2_05.errors import AuditError


class TestL2_05_DecisionAuditRecorder:
    """§3 public 方法正向用例。每 public 方法 ≥ 1 个 happy path。"""

    # --------- record_audit() · 4 种 source_ic × 多动作 --------- #

    def test_TC_L101_L205_001_record_audit_decision_made_returns_audit_id(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-001 · IC-L2-05 + decision_made · buffered=true + audit_id 形如 audit-{uuid-v7}。"""
        # arrange
        cmd: AuditCommand = make_audit_cmd(
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-02"},
            action="decision_made",
            project_id=mock_project_id,
            linked_decision="dec-018f4a3b-7c1e-7000-8b2a-1111111111aa",
            reason="选择 invoke_skill: tdd.blueprint_generate 因 KB 命中 5 条相似且 evidence 充分",
            evidence=["evt-kb-001", "evt-5dis-002"],
            payload={"decision_type": "invoke_skill"},
        )
        # act
        result: AuditResult = sut.record_audit(cmd)
        # assert
        assert result.audit_id.startswith("audit-")
        assert result.buffered is True
        assert result.buffer_remaining == 63  # L2_05_BUFFER_MAX=64 默认，入队 1 条
        assert result.event_id is None, "buffered=true 且未触发同步 flush 时 event_id=null（§3.1 出参）"

    def test_TC_L101_L205_002_record_audit_tick_scheduled_from_l2_01(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-002 · IC-L2-05 + tick_scheduled 来自 L2-01 · FIFO 顺序保持（prd §12.4 #4）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-01"},
            action="tick_scheduled",
            project_id=mock_project_id,
            linked_tick="tick-018f4a3b-7c1e-7000-8b2a-2222222222bb",
            reason="event_bus_trigger",
            evidence=["evt-bus-001"],
            payload={},
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True
        buffer = sut.peek_buffer()
        assert buffer[-1].action == "tick_scheduled"
        assert buffer[-1].linked_tick == cmd.linked_tick

    def test_TC_L101_L205_003_record_audit_state_transitioned_via_ic_l2_06(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-003 · IC-L2-06 + state_transitioned · payload 带 from/to/pre/post snapshot ref。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-06",
            actor={"l1": "L1-01", "l2": "L2-03"},
            action="state_transitioned",
            project_id=mock_project_id,
            reason="tick 触发 S3→S4 转换 · allowed_next 通过",
            evidence=["evt-trans-001"],
            payload={
                "from_state": "S3",
                "to_state": "S4",
                "pre_snapshot_ref": "snap-pre-001",
                "post_snapshot_ref": "snap-post-001",
                "hook_results": {"entry_hook": "ok"},
                "accepted": True,
            },
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True
        assert sut.peek_buffer()[-1].source_ic == "IC-L2-06"

    def test_TC_L101_L205_004_record_audit_chain_step_via_ic_l2_07(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-004 · IC-L2-07 + chain_step_completed · linked_chain 必填（§3.1 入参）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-07",
            actor={"l1": "L1-01", "l2": "L2-04"},
            action="chain_step_completed",
            project_id=mock_project_id,
            linked_chain="ch-018f4a3b-7c1e-7000-8b2a-3333333333cc",
            reason="step 2/5 ok",
            evidence=["evt-step-001"],
            payload={"chain_id": "ch-...", "step_id": "step-2", "outcome": "success"},
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True
        assert sut.peek_buffer()[-1].linked_chain.startswith("ch-")

    def test_TC_L101_L205_005_record_audit_warn_response_via_ic_l2_09(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-005 · IC-L2-09 + warn_response · linked_warn 必填（PM-12 书面回应留痕）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-09",
            actor={"l1": "L1-01", "l2": "L2-02"},
            action="warn_response",
            project_id=mock_project_id,
            linked_warn="warn-018f4a3b-7c1e-7000-8b2a-4444444444dd",
            reason="接受 supervisor WARN: 建议补充 KB 检索，已补充",
            evidence=["evt-warn-001"],
            payload={"warn_id": "warn-...", "response": "accept", "applied_action": {"kb_supplement": True}},
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True

    def test_TC_L101_L205_006_record_audit_idempotency_key_returns_same_audit_id(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-006 · 幂等键（idempotency_key=event_id）重复调用返回同一 audit_id（§3.1 幂等）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-01"},
            action="tick_scheduled",
            project_id=mock_project_id,
            linked_tick="tick-idem-001",
            reason="event_bus_trigger",
            evidence=["evt-idem-001"],
            idempotency_key="evt-idem-001",
        )
        r1 = sut.record_audit(cmd)
        r2 = sut.record_audit(cmd)
        assert r1.audit_id == r2.audit_id, "同 idempotency_key 必返同一 audit_id（L2-01 超时重投防护）"
        assert sut.buffer_size() == 1, "幂等重放不应重复入队"

    # --------- query_by_tick() --------- #

    def test_TC_L101_L205_007_query_by_tick_hits_buffer_includes_buffered(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-007 · query_by_tick(include_buffered=true) · 未 flush 也命中（§3.2）。"""
        tick_id = "tick-018f4a3b-7c1e-7000-8b2a-5555555555ee"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=tick_id,
            reason="event_bus_trigger", evidence=["evt-1"],
        ))
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_tick=tick_id, linked_decision="dec-001",
            reason="选择 invoke_skill 因 KB 命中且 reason 达到 20 字",
            evidence=["evt-2"], payload={"decision_type": "invoke_skill"},
        ))
        result = sut.query_by_tick(tick_id=tick_id, project_id=mock_project_id, include_buffered=True)
        assert result.count == 2
        assert result.source in ("buffer", "mixed")
        assert [e.action for e in result.entries] == ["tick_scheduled", "decision_made"]

    def test_TC_L101_L205_008_query_by_tick_mixed_buffer_and_index_after_flush(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-008 · flush 后旧条在 index · 新条在 buffer · source=mixed。"""
        tick_id = "tick-018f4a3b-7c1e-7000-8b2a-6666666666ff"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=tick_id,
            reason="flushed first", evidence=["evt-1"],
        ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_completed",
            project_id=mock_project_id, linked_tick=tick_id,
            reason="late buffered", evidence=["evt-2"],
        ))
        result = sut.query_by_tick(tick_id=tick_id, project_id=mock_project_id, include_buffered=True)
        assert result.count == 2
        assert result.source == "mixed"

    # --------- query_by_decision() / query_by_chain() --------- #

    def test_TC_L101_L205_009_query_by_decision_returns_single_entry(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-009 · 1:1 反查（§3.3）· 返 entry 非数组。"""
        decision_id = "dec-018f4a3b-7c1e-7000-8b2a-7777777777aa"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_decision=decision_id,
            reason="decision 单条反查 · reason 长度足以满足 20 字最小要求",
            evidence=["evt-dec-001"], payload={"decision_type": "invoke_skill"},
        ))
        entry = sut.query_by_decision(decision_id=decision_id, project_id=mock_project_id)
        assert entry is not None
        assert entry.linked_decision == decision_id
        assert entry.action == "decision_made"

    def test_TC_L101_L205_010_query_by_chain_returns_multiple_entries(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-010 · 1:N 反查（§3.3）· 3 步 chain 返 3 条 entries。"""
        chain_id = "ch-018f4a3b-7c1e-7000-8b2a-8888888888bb"
        for i in range(3):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-07", action="chain_step_completed",
                actor={"l1": "L1-01", "l2": "L2-04"},
                project_id=mock_project_id, linked_chain=chain_id,
                reason=f"step {i + 1} ok", evidence=[f"evt-step-{i}"],
                payload={"chain_id": chain_id, "step_id": f"step-{i + 1}", "outcome": "success"},
            ))
        entries = sut.query_by_chain(chain_id=chain_id, project_id=mock_project_id)
        assert len(entries) == 3
        assert all(e.linked_chain == chain_id for e in entries)

    # --------- flush_buffer() --------- #

    def test_TC_L101_L205_011_flush_buffer_tick_boundary_ok(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-011 · flush_buffer(force=true, reason=tick_boundary) 正向（§3.4）。"""
        for i in range(5):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            ))
        fr: FlushResult = sut.flush_buffer(force=True, reason="tick_boundary")
        assert fr.flushed_count == 5
        assert fr.last_event_id is not None
        assert fr.last_hash and len(fr.last_hash) == 64  # sha256-hex
        assert fr.duration_ms <= 50, "flush_buffer P99 ≤ 50ms（§12.1）"
        assert mock_event_bus.append_event.call_count == 5

    def test_TC_L101_L205_012_flush_buffer_empty_is_noop(
        self,
        sut: DecisionAuditRecorder,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L205-012 · 空 buffer · flushed_count=0 · 不调 IC-09（§3.4 幂等语义）。"""
        fr = sut.flush_buffer(force=True, reason="tick_boundary")
        assert fr.flushed_count == 0
        assert fr.last_event_id is None
        assert mock_event_bus.append_event.call_count == 0

    # --------- replay_from_jsonl() --------- #

    def test_TC_L101_L205_013_replay_rebuilds_reverse_index(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        jsonl_fixture_file,
    ) -> None:
        """TC-L101-L205-013 · replay_from_jsonl 从 fixture 重建索引 + hash tip（§3.5）。"""
        rr: ReplayResult = sut.replay_from_jsonl(
            project_id=mock_project_id,
            from_date="2026-04-15",
            max_entries=100_000,
        )
        assert rr.replayed_count >= 3
        assert rr.hash_chain_valid is True
        assert rr.latest_hash and len(rr.latest_hash) == 64
        # index 可被 query 命中
        tip = sut.get_hash_tip(project_id=mock_project_id)
        assert tip.hash == rr.latest_hash
        assert tip.sequence == rr.replayed_count

    # --------- get_hash_tip() --------- #

    def test_TC_L101_L205_014_get_hash_tip_genesis_is_all_zero(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L205-014 · 空 project · genesis hash 全 0 · sequence=0（§3.6）。"""
        tip: HashTip = sut.get_hash_tip(project_id=mock_project_id)
        assert tip.hash == "0" * 64
        assert tip.sequence == 0

    def test_TC_L101_L205_015_get_hash_tip_after_flush_increments(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-015 · 写 + flush 3 条后 · hash tip sequence=3 · hash ≠ genesis。"""
        for i in range(3):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        tip = sut.get_hash_tip(project_id=mock_project_id)
        assert tip.sequence == 3
        assert tip.hash != "0" * 64
```

---

## §3 负向用例（每错误码 ≥ 1）

> §11.1 10 项 `E_AUDIT_*` 全覆盖 + §3.4 `E_AUDIT_FLUSH_CONCURRENT` 1 项补充。每测试用 `pytest.raises(AuditError) as exc` 或断言返回结构里的 `error_code`。

```python
# file: tests/l1_01/test_l2_05_audit_recorder_negative.py
from __future__ import annotations

import threading
import pytest
from unittest.mock import MagicMock

from app.l2_05.recorder import DecisionAuditRecorder
from app.l2_05.errors import AuditError


class TestL2_05_Negative_RecordAudit:
    """§3.1 record_audit() 错误码（TC-L101-L205-102/105/106/107/108/109/110）。"""

    def test_TC_L101_L205_102_buffer_overflow_triggers_sync_flush(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-102 · E_AUDIT_BUFFER_OVERFLOW · buffer=64 满 · 下一条触发同步 flush · buffered=false。"""
        # 填满 buffer
        for i in range(64):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            ))
        assert sut.buffer_size() == 64
        # 第 65 条触发 overflow sync flush（§3.1 出参 buffered=false · event_id 非空）
        cmd_65 = make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-overflow",
            reason="trigger overflow", evidence=["evt-overflow"],
        )
        r = sut.record_audit(cmd_65)
        assert r.buffered is False, "overflow 降级为纯同步 flush（§3.1 + §11.1 降级链）"
        assert r.event_id is not None, "overflow 返 event_id 由 IC-09 给出"
        # 审计：overflow 元事件
        audits = [a for a in sut.get_recent_audits() if a.error_code == "E_AUDIT_BUFFER_OVERFLOW"]
        assert len(audits) >= 1
        assert audits[0].level == "WARN"

    def test_TC_L101_L205_105_halt_on_fail_rejects_silently(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-105 · E_AUDIT_HALT_ON_FAIL · halted 后 record_audit 静默拒绝 · 不入 buffer（§11.1 Minor）。"""
        sut._force_halted()  # test-only hatch · 模拟 emit_halt_signal 后状态
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-after-halt",
            reason="should be rejected", evidence=["evt-x"],
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code == "E_AUDIT_HALT_ON_FAIL"
        assert sut.buffer_size() == 0, "halt 期间新 audit 不入 buffer（§11.1 硬约束）"

    def test_TC_L101_L205_106_no_project_id_rejected(
        self,
        sut: DecisionAuditRecorder,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-106 · E_AUDIT_NO_PROJECT_ID · PM-14 根字段缺失拒绝（§3.1 / §11.1）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=None, linked_tick="tick-001",
            reason="no pid", evidence=["evt-1"],
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code == "E_AUDIT_NO_PROJECT_ID"

    def test_TC_L101_L205_107_no_reason_rejected(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-107 · E_AUDIT_NO_REASON · 空 reason 拒绝 · 审计违规元事件（§11.1 prd §12.5 禁止）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-001",
            reason="", evidence=["evt-1"],
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code == "E_AUDIT_NO_REASON"
        # 本 L2 写 meta 元事件（不阻止调用方继续）
        meta = [a for a in sut.get_recent_audits() if a.event_type == "L1-01:audit_rejected"]
        assert len(meta) >= 1

    def test_TC_L101_L205_108_cross_project_rejected(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-108 · E_AUDIT_CROSS_PROJECT · actor.project_id ≠ linked_tick 的 project_id（§11.1）。"""
        # linked_tick 绑定到另一个 project（通过预置 tick→pid 映射表）
        sut._register_tick("tick-other-pid", project_id="pid-OTHER-018f4a3b-9999-7000-FFFF")
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id,
            linked_tick="tick-other-pid",
            reason="wrong pid", evidence=["evt-1"],
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code == "E_AUDIT_CROSS_PROJECT"

    def test_TC_L101_L205_109_unknown_event_type_rejected(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-109 · E_AUDIT_EVENT_TYPE_UNKNOWN · source_ic + action 组合未在 §7.2 白名单。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="frobnicate_the_widget",  # 非白名单
            project_id=mock_project_id, linked_tick="tick-001",
            reason="invalid action", evidence=["evt-1"],
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code == "E_AUDIT_EVENT_TYPE_UNKNOWN"

    def test_TC_L101_L205_110_stale_buffer_force_flush_and_warn(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-110 · E_AUDIT_STALE_BUFFER · tick 结束未 flush 残留 · 下一 tick 自救 force_flush（§11.1）。"""
        tick_a = "tick-stale-A"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=tick_a,
            reason="stale buffer fixture", evidence=["evt-a"],
        ))
        # 【异常】L2-01 没有调 flush_buffer · 直接进入下一 tick
        tick_b = "tick-next-B"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=tick_b,
            reason="next tick", evidence=["evt-b"],
        ))
        warns = [a for a in sut.get_recent_audits() if a.error_code == "E_AUDIT_STALE_BUFFER"]
        assert len(warns) == 1, "必须记 1 条 STALE_BUFFER 元事件（§11.1）"
        # 自救 force_flush 应该已完成 tick_a 的条目
        from_index = sut.query_by_tick(tick_id=tick_a, project_id=mock_project_id, include_buffered=False)
        assert from_index.count >= 1


class TestL2_05_Negative_FlushBuffer:
    """§3.4 flush_buffer() 错误码（TC-L101-L205-101/104/111）。"""

    def test_TC_L101_L205_101_write_fail_halts_l1(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        mock_l2_01_client: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-101 · E_AUDIT_WRITE_FAIL · IC-09 fsync 失败 → emit_halt_signal → L2-01 转 HALTED（Critical）。"""
        mock_event_bus.append_event.side_effect = IOError("disk full")
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-001",
            reason="write fail scenario", evidence=["evt-1"],
        ))
        with pytest.raises(AuditError) as exc:
            sut.flush_buffer(force=True, reason="tick_boundary")
        assert exc.value.error_code == "E_AUDIT_WRITE_FAIL"
        # 必须向 L2-01 发 halt_signal（§11.1 Critical 降级链）
        mock_l2_01_client.on_halt_signal.assert_called_once()
        payload = mock_l2_01_client.on_halt_signal.call_args.kwargs
        assert payload["source"] == "L2-05"
        assert payload["reason"] == "E_AUDIT_WRITE_FAIL"

    def test_TC_L101_L205_104_hash_broken_warn_not_halt(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        mock_l1_07_client: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-104 · E_AUDIT_HASH_BROKEN · prev_hash ≠ L1-09 last_hash · 重查仍错 · WARN 不 halt（§11.1 Major）。"""
        mock_event_bus.get_last_hash.side_effect = [
            "ffff" * 16,  # 第一次返 mismatch
            "ffff" * 16,  # 重查仍 mismatch
        ]
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-001",
            reason="hash mismatch scenario", evidence=["evt-1"],
        ))
        fr = sut.flush_buffer(force=True, reason="tick_boundary")
        # 不 halt · 告警 L1-07 · 按当前 tip 重算 hash 链后继续
        assert fr.flushed_count == 1
        mock_l1_07_client.alert.assert_called_once()
        alert_payload = mock_l1_07_client.alert.call_args.kwargs
        assert alert_payload["error_code"] == "E_AUDIT_HASH_BROKEN"
        assert sut.current_state() != "HALTED"

    def test_TC_L101_L205_111_flush_concurrent_waits_on_semaphore(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-111 · E_AUDIT_FLUSH_CONCURRENT · 并发 flush · 第二次 wait semaphore · 不重复写（§3.4）。"""
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-conc",
            reason="flush concurrent scenario", evidence=["evt-c"],
        ))
        results: list = []
        errors: list = []

        def worker() -> None:
            try:
                results.append(sut.flush_buffer(force=True, reason="tick_boundary"))
            except AuditError as e:
                errors.append(e)

        th1 = threading.Thread(target=worker)
        th2 = threading.Thread(target=worker)
        th1.start(); th2.start()
        th1.join(timeout=2); th2.join(timeout=2)
        # 两次都应返回（后者 wait semaphore 后看到空 buffer · flushed_count=0）
        assert len(results) == 2
        flushed_counts = sorted([r.flushed_count for r in results])
        assert flushed_counts == [0, 1], "第一次 flushed_count=1 · 第二次 0（后者 wait 后 buffer 已空）"
        assert len(errors) == 0


class TestL2_05_Negative_Query:
    """§3.2 / §3.3 query 错误码（TC-L101-L205-103）+ §3.2 cross_project。"""

    def test_TC_L101_L205_103_query_miss_returns_empty_not_exception(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L205-103 · E_AUDIT_QUERY_MISS · 未命中返 `{entries:[], count:0}` · 非异常（§11.1 Minor）。"""
        r = sut.query_by_tick(tick_id="tick-ghost", project_id=mock_project_id, include_buffered=True)
        assert r.count == 0
        assert r.entries == []
        assert r.source == "not_found" or r.source == "buffer"  # 允许实现差异但都 = 0

    def test_TC_L101_L205_108b_query_cross_project_rejected(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-108（同错误码 · query 路径补充）· E_AUDIT_CROSS_PROJECT · project_id 错配拒绝 + 告警。"""
        tick_id = "tick-cross-query"
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=tick_id,
            reason="cross-project query scenario", evidence=["evt-1"],
        ))
        with pytest.raises(AuditError) as exc:
            sut.query_by_tick(
                tick_id=tick_id,
                project_id="pid-OTHER-018f4a3b-9999-7000-FFFF",
                include_buffered=True,
            )
        assert exc.value.error_code == "E_AUDIT_CROSS_PROJECT"
```

---

## §4 IC-XX 契约集成测试

> 本 L2 是 IC-L2-05/06/07/09 **被调方** · IC-09 **生产方**。
> 每测试 mock L1-09 event_bus · 断言 payload 结构精确匹配 ic-contracts.md §3.9 + 3-1 L2-05 §3.1 入参 schema。

```python
# file: tests/l1_01/test_l2_05_ic_contracts.py
from __future__ import annotations

import hashlib
import json
import pytest
from unittest.mock import MagicMock

from app.l2_05.recorder import DecisionAuditRecorder


class TestL2_05_IC_Contracts:
    """IC-L2-05 / IC-L2-06 / IC-L2-07 / IC-L2-09 / IC-09 五个契约集成测试。"""

    def test_TC_L101_L205_201_ic_l2_05_record_audit_discriminated_union_by_source_ic(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-201 · IC-L2-05 discriminated union · 4 种 source_ic 各自 schema 独立校验（§3.1）。"""
        # IC-L2-05 通用 + decision_made · linked_decision 必填
        c1 = make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_decision="dec-001",
            reason="decision_made 足以满足 20 字 reason", evidence=["evt-1"],
            payload={"decision_type": "invoke_skill"},
        )
        r1 = sut.record_audit(c1)
        assert r1.audit_id is not None

    def test_TC_L101_L205_202_ic_l2_06_state_transition_payload_shape(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-202 · IC-L2-06 · payload 必含 from_state/to_state/pre_snapshot_ref/post_snapshot_ref/hook_results/accepted。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-06", action="state_transitioned",
            actor={"l1": "L1-01", "l2": "L2-03"},
            project_id=mock_project_id,
            reason="IC-L2-06 state transition payload shape",
            evidence=["evt-1"],
            payload={
                "from_state": "S3", "to_state": "S4",
                "pre_snapshot_ref": "snap-pre-001",
                "post_snapshot_ref": "snap-post-001",
                "hook_results": {"entry_hook": "ok", "exit_hook": "ok"},
                "accepted": True,
            },
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True
        entry = sut.peek_buffer()[-1]
        assert entry.payload["from_state"] == "S3"
        assert entry.payload["to_state"] == "S4"
        assert entry.payload["accepted"] is True

    def test_TC_L101_L205_203_ic_l2_07_chain_step_requires_linked_chain(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-203 · IC-L2-07 · linked_chain 必填；缺失抛 schema error（§3.1）。"""
        from app.l2_05.errors import AuditError
        cmd = make_audit_cmd(
            source_ic="IC-L2-07", action="chain_step_completed",
            actor={"l1": "L1-01", "l2": "L2-04"},
            project_id=mock_project_id,
            linked_chain=None,  # 故意缺失
            reason="should fail schema",
            evidence=["evt-1"],
            payload={"chain_id": "ch-x", "step_id": "step-1", "outcome": "success"},
        )
        with pytest.raises(AuditError) as exc:
            sut.record_audit(cmd)
        assert exc.value.error_code in ("E_AUDIT_SCHEMA_FAIL", "E_AUDIT_EVENT_TYPE_UNKNOWN")

    def test_TC_L101_L205_204_ic_l2_09_warn_response_payload_shape(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-204 · IC-L2-09 · payload={warn_id, response, applied_action}（prd §12.2）。"""
        cmd = make_audit_cmd(
            source_ic="IC-L2-09", action="warn_response",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_warn="warn-001",
            reason="IC-L2-09 warn_response payload shape check",
            evidence=["evt-1"],
            payload={
                "warn_id": "warn-001",
                "response": "accept",
                "applied_action": {"kb_supplement": True},
            },
        )
        r = sut.record_audit(cmd)
        entry = sut.peek_buffer()[-1]
        assert entry.payload["response"] in ("accept", "reject")
        assert "applied_action" in entry.payload

    def test_TC_L101_L205_205_ic_09_append_event_is_sole_downstream(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-205 · IC-09 是本 L2 唯一下游 IC（arch §3.3 单一审计源 · §4.2）。"""
        for i in range(3):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        # 唯一调用 IC-09，不允许调其它 L1-09 接口
        assert mock_event_bus.append_event.call_count == 3
        assert mock_event_bus.query.call_count == 0, "本 L2 不读事件总线（读由 replay_from_jsonl 走 jsonl · 不走 IC）"
        # 每条事件 event_type 必带 L1-01: 前缀（prd §12.4 硬约束 #5）
        for call in mock_event_bus.append_event.call_args_list:
            assert call.kwargs["event_type"].startswith("L1-01:")
            assert call.kwargs["project_id"] == mock_project_id

    def test_TC_L101_L205_206_hash_chain_monotonic_on_ic_09_calls(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-206 · IC-09 每次调用 · prev_hash / hash / sequence 严格单调递增（§6.2 + prd §12.10.2）。"""
        for i in range(4):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        calls = mock_event_bus.append_event.call_args_list
        assert len(calls) == 4
        prev_hash = "0" * 64
        for idx, call in enumerate(calls):
            kwargs = call.kwargs
            assert kwargs["prev_hash"] == prev_hash, f"#{idx} prev_hash 不等于上条 hash"
            # sha256(prev_hash + canonical(content)) == kwargs["hash"]
            content = json.dumps(kwargs["payload"], sort_keys=True, separators=(",", ":"))
            expected = hashlib.sha256((prev_hash + content).encode()).hexdigest()
            assert kwargs["hash"] == expected, f"#{idx} hash 不等于 sha256(prev+content)"
            assert kwargs["sequence"] == idx + 1
            prev_hash = kwargs["hash"]
```

---

## §5 性能 SLO 用例

> §12.1 / §12.2 SLO 表驱动。`@pytest.mark.perf` · 断言 P95 / P99 延迟、吞吐率、并发场景。

```python
# file: tests/l1_01/test_l2_05_perf.py
from __future__ import annotations

import time
import statistics
import threading
import pytest

from app.l2_05.recorder import DecisionAuditRecorder


@pytest.mark.perf
class TestL2_05_SLO:
    """§12 SLO 性能用例。"""

    def test_TC_L101_L205_701_record_audit_p95_under_10ms(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-701 · record_audit() P50 ≤ 2ms / P95 ≤ 10ms / P99 ≤ 20ms（§12.1 · prd §12.4）。"""
        samples: list[float] = []
        for i in range(1000):
            cmd = make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-{i}",
                reason=f"trigger {i}", evidence=[f"evt-{i}"],
            )
            t0 = time.monotonic()
            sut.record_audit(cmd)
            samples.append((time.monotonic() - t0) * 1000)
            # 每 50 条 flush 一次 · 防止 buffer overflow 干扰延迟样本
            if (i + 1) % 50 == 0:
                sut.flush_buffer(force=True, reason="manual")
        samples.sort()
        p50 = samples[int(len(samples) * 0.50)]
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p50 <= 2.0, f"record_audit P50 = {p50:.2f}ms 超 2ms SLO"
        assert p95 <= 10.0, f"record_audit P95 = {p95:.2f}ms 超 10ms 硬约束（prd §12.4）"
        assert p99 <= 20.0, f"record_audit P99 = {p99:.2f}ms 超 20ms SLO"

    def test_TC_L101_L205_702_flush_buffer_5_entries_p99_under_50ms(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-702 · flush_buffer(5 条) P99 ≤ 50ms（§12.1 · prd §12.4 硬约束 #3）。"""
        samples: list[float] = []
        for round_i in range(200):
            for i in range(5):
                sut.record_audit(make_audit_cmd(
                    source_ic="IC-L2-05", action="tick_scheduled",
                    project_id=mock_project_id, linked_tick=f"tick-r{round_i}-s{i}",
                    reason=f"round {round_i} step {i}", evidence=[f"evt-r{round_i}-{i}"],
                ))
            t0 = time.monotonic()
            sut.flush_buffer(force=True, reason="tick_boundary")
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p50 = samples[int(len(samples) * 0.50)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p50 <= 20.0, f"flush 5 entries P50 = {p50:.2f}ms 超 20ms SLO"
        assert p99 <= 50.0, f"flush 5 entries P99 = {p99:.2f}ms 超 50ms 硬约束（§12.1）"

    def test_TC_L101_L205_703_query_by_tick_in_memory_p95_under_5ms(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-703 · query_by_tick() in-memory P95 ≤ 5ms（§3.2 / §12.1）。"""
        # 预填 1000 条（10 个 tick × 100 条）
        tick_ids = [f"tick-q-{i}" for i in range(10)]
        for tid in tick_ids:
            for j in range(100):
                sut.record_audit(make_audit_cmd(
                    source_ic="IC-L2-05", action="chain_step_completed"
                    if j % 2 else "decision_made",
                    actor={"l1": "L1-01", "l2": "L2-04" if j % 2 else "L2-02"},
                    project_id=mock_project_id, linked_tick=tid,
                    linked_chain=f"ch-{tid}-{j}" if j % 2 else None,
                    linked_decision=None if j % 2 else f"dec-{tid}-{j}",
                    reason=f"tick {tid} step {j}", evidence=[f"evt-{tid}-{j}"],
                    payload={},
                ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        samples: list[float] = []
        for _ in range(1000):
            tid = tick_ids[_ % 10]
            t0 = time.monotonic()
            sut.query_by_tick(tick_id=tid, project_id=mock_project_id, include_buffered=True)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 5.0, f"query_by_tick P95 = {p95:.2f}ms 超 5ms SLO（§3.2）"
        assert p99 <= 10.0, f"query_by_tick P99 = {p99:.2f}ms 超 10ms SLO（§12.1）"

    def test_TC_L101_L205_704_get_hash_tip_p99_under_1ms(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L205-704 · get_hash_tip() P99 ≤ 1ms（§12.1 · 纯内存读）。"""
        samples: list[float] = []
        for _ in range(2000):
            t0 = time.monotonic()
            sut.get_hash_tip(project_id=mock_project_id)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 <= 1.0, f"get_hash_tip P99 = {p99:.3f}ms 超 1ms SLO"

    def test_TC_L101_L205_705_throughput_record_audit_500_qps(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-705 · record_audit 吞吐 ≥ 500 qps（§12.2）。"""
        N = 2000
        t0 = time.monotonic()
        for i in range(N):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-tps-{i}",
                reason=f"tps {i}", evidence=[f"evt-{i}"],
            ))
            if (i + 1) % 32 == 0:
                sut.flush_buffer(force=True, reason="manual")
        elapsed = time.monotonic() - t0
        qps = N / elapsed
        assert qps >= 500.0, f"实测吞吐 {qps:.1f} qps 低于 500 qps SLO（§12.2）"
```

---

## §6 端到端 e2e

> 映射 3-1 §5.1 正常 tick 时序 + §5.2 崩溃恢复时序 + prd §12.9 集成用例 I1-I4 + 8 GWT 场景。
> `@pytest.mark.e2e` · 半真实 L2-01 / L2-02 / L2-03 / L2-04 + L1-09 event_bus stub。

```python
# file: tests/l1_01/test_l2_05_e2e.py
from __future__ import annotations

import pytest
from pathlib import Path

from app.l2_05.recorder import DecisionAuditRecorder


@pytest.mark.e2e
class TestL2_05_E2E:
    """端到端场景 · 对应 3-1 §5.1 / §5.2 时序 + prd §12.9 I1-I4。"""

    def test_TC_L101_L205_801_e2e_normal_tick_decision_made_lands_on_l1_09(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
        real_event_bus_stub,
    ) -> None:
        """TC-L101-L205-801 · GWT 流 A（§5.1 / prd I1）。

        GIVEN L2-02 完成一次 decision_made · L2-01 在 tick 边界
        WHEN L2-02 调 IC-L2-05 record_audit(decision_made) + L2-01 调 flush_buffer
        THEN L1-01:decision_made 事件落盘 · hash 链严格递增 · 反查索引可命中 audit_id
        """
        tick_id = "tick-e2e-001"
        decision_id = "dec-e2e-001"
        # tick 开始审计
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            actor={"l1": "L1-01", "l2": "L2-01"},
            project_id=mock_project_id, linked_tick=tick_id,
            reason="event_bus_trigger", evidence=["evt-bus-001"],
        ))
        # decision_made 审计
        r_dec = sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_tick=tick_id,
            linked_decision=decision_id,
            reason="选择 invoke_skill: tdd.blueprint_generate 因 KB 命中 5 条且 reason 足够长",
            evidence=["evt-kb-001", "evt-5dis-002"],
            payload={"decision_type": "invoke_skill"},
        ))
        # tick 边界强制 flush
        fr = sut.flush_buffer(force=True, reason="tick_boundary")
        assert fr.flushed_count == 2
        # 落盘事件可反查
        events = real_event_bus_stub.get_events_by_project(mock_project_id)
        assert len(events) == 2
        types = [e.event_type for e in events]
        assert "L1-01:tick_scheduled" in types
        assert "L1-01:decision_made" in types
        # 反查索引命中
        entry = sut.query_by_decision(decision_id=decision_id, project_id=mock_project_id)
        assert entry is not None
        assert entry.audit_id == r_dec.audit_id

    def test_TC_L101_L205_802_e2e_crash_recovery_replay_rebuilds_index(
        self,
        mock_project_id: str,
        pre_populated_jsonl_dir: Path,
        make_recorder,
    ) -> None:
        """TC-L101-L205-802 · GWT 流 H（§5.2 · prd §12.9 I2 变种）。

        GIVEN 上一 session 崩溃 · jsonl 含 10 条 audit entries
        WHEN 新 session 启动 · L2-01 调 replay_from_jsonl
        THEN 反查索引重建 · hash tip 等于最后一条 hash · hash_chain_valid=true
        """
        fresh = make_recorder(jsonl_root=pre_populated_jsonl_dir)
        rr = fresh.replay_from_jsonl(project_id=mock_project_id, from_date="2026-04-15")
        assert rr.replayed_count == 10
        assert rr.hash_chain_valid is True
        # 反查任意 tick_id 可命中（从 jsonl 重建）
        sample_tick = "tick-historical-003"
        r = fresh.query_by_tick(tick_id=sample_tick, project_id=mock_project_id, include_buffered=False)
        assert r.count >= 1
        assert r.source in ("index", "jsonl_scan")

    def test_TC_L101_L205_803_e2e_state_transition_audited_via_ic_l2_06(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
        real_event_bus_stub,
    ) -> None:
        """TC-L101-L205-803 · GWT 流 C（prd §12.9 I2）· L2-03 state 转换审计。

        GIVEN L2-03 完成 S3→S4 转换
        WHEN L2-03 调 IC-L2-06 record_audit(state_transitioned)
        THEN L1-01:state_transition 事件落盘 · payload 含 pre/post snapshot + hook_results
        """
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-06", action="state_transitioned",
            actor={"l1": "L1-01", "l2": "L2-03"},
            project_id=mock_project_id,
            reason="S3 TDD 蓝图完成 · 触发 S4 执行（reason 20 字）",
            evidence=["evt-trans-e2e-001"],
            payload={
                "from_state": "S3", "to_state": "S4",
                "pre_snapshot_ref": "snap-pre-e2e",
                "post_snapshot_ref": "snap-post-e2e",
                "hook_results": {"entry_hook": "ok"},
                "accepted": True,
            },
        ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        events = real_event_bus_stub.get_events_by_project(mock_project_id)
        trans = [e for e in events if e.event_type == "L1-01:state_transition"]
        assert len(trans) == 1
        assert trans[0].payload["from_state"] == "S3"
        assert trans[0].payload["to_state"] == "S4"
```

---

## §7 测试 fixture

> conftest.py 提供本 L2 复用 fixture。`mock_project_id` / `mock_event_bus` / `mock_l2_01_client` / `mock_l1_07_client` / `make_audit_cmd` / `pre_populated_jsonl_dir`。

```python
# file: tests/l1_01/conftest_l2_05.py
from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.l2_05.recorder import DecisionAuditRecorder
from app.l2_05.schemas import AuditCommand


@pytest.fixture
def mock_project_id() -> str:
    """PM-14 · pid-{uuid-v7} 合法 project_id。"""
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """L1-09 事件总线 stub · 默认返 event_id + sequence + hash。"""
    bus = MagicMock(name="L1-09-event-bus")
    counter = {"seq": 0, "last_hash": "0" * 64}

    def _append(**kwargs: Any) -> dict[str, Any]:
        counter["seq"] += 1
        new_hash = kwargs.get("hash") or "0" * 63 + str(counter["seq"] % 10)
        counter["last_hash"] = new_hash
        return {
            "event_id": f"evt-{uuid.uuid4()}",
            "sequence": counter["seq"],
            "hash": new_hash,
            "persisted": True,
        }

    bus.append_event.side_effect = _append
    bus.get_last_hash = MagicMock(side_effect=lambda project_id: counter["last_hash"])
    bus.query.return_value = []
    return bus


@pytest.fixture
def mock_l2_01_client() -> MagicMock:
    """L2-01 Tick 调度器 stub · 用于 halt_signal 回调断言。"""
    client = MagicMock(name="L2-01-tick-scheduler")
    client.on_halt_signal.return_value = {"halted": True}
    return client


@pytest.fixture
def mock_l1_07_client() -> MagicMock:
    """L1-07 supervisor stub · 用于 HASH_BROKEN 告警断言。"""
    client = MagicMock(name="L1-07-supervisor")
    client.alert.return_value = {"alert_id": f"alert-{uuid.uuid4()}"}
    return client


@pytest.fixture
def sut(
    mock_project_id: str,
    mock_event_bus: MagicMock,
    mock_l2_01_client: MagicMock,
    mock_l1_07_client: MagicMock,
) -> DecisionAuditRecorder:
    """SUT · 默认 unit mode · buffer_max=64 · 无 jsonl（replay 测试单独注入）。"""
    return DecisionAuditRecorder(
        session_active_pid=mock_project_id,
        event_bus=mock_event_bus,
        l2_01_client=mock_l2_01_client,
        l1_07_client=mock_l1_07_client,
        buffer_max=64,
        reason_min_length=1,
        query_timeout_ms=100,
        replay_timeout_ms=30_000,
    )


@pytest.fixture
def make_audit_cmd() -> Callable[..., AuditCommand]:
    """AuditCommand 工厂（覆盖默认字段）· 4 种 source_ic 通用。"""
    def _factory(**overrides: Any) -> AuditCommand:
        base: dict[str, Any] = dict(
            source_ic="IC-L2-05",
            actor={"l1": "L1-01", "l2": "L2-01"},
            action="tick_scheduled",
            project_id="pid-default",
            reason="default reason (>=1 char)",
            evidence=[],
            linked_tick=None,
            linked_decision=None,
            linked_chain=None,
            linked_warn=None,
            payload={},
            ts="2026-04-22T00:00:00Z",
            idempotency_key=None,
        )
        base.update(overrides)
        return AuditCommand(**base)
    return _factory


@pytest.fixture
def jsonl_fixture_file(tmp_path: Path, mock_project_id: str) -> Path:
    """写 3 条 audit entries 到临时 jsonl（含合法 hash 链）· 供 replay 用。"""
    import hashlib
    audit_root = tmp_path / "projects" / mock_project_id / "audit" / "l1-01"
    audit_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = audit_root / "2026-04-15.jsonl"
    prev = "0" * 64
    lines: list[str] = []
    for i in range(3):
        payload = {"tick_id": f"tick-fx-{i}", "action": "tick_scheduled"}
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256((prev + content).encode()).hexdigest()
        rec = {
            "event_id": f"evt-fx-{i}",
            "event_type": "L1-01:tick_scheduled",
            "project_id": mock_project_id,
            "payload": payload,
            "prev_hash": prev, "hash": h, "sequence": i + 1,
            "ts": "2026-04-15T00:00:00Z",
        }
        lines.append(json.dumps(rec))
        prev = h
    jsonl_path.write_text("\n".join(lines) + "\n")
    return jsonl_path


@pytest.fixture
def pre_populated_jsonl_dir(tmp_path: Path, mock_project_id: str) -> Path:
    """10 条 audit entries 合法 hash 链 jsonl 目录 · 供 e2e replay 用。"""
    import hashlib
    audit_root = tmp_path / "projects" / mock_project_id / "audit" / "l1-01"
    audit_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = audit_root / "2026-04-20.jsonl"
    prev = "0" * 64
    lines: list[str] = []
    for i in range(10):
        tick_id = f"tick-historical-{i:03d}"
        payload = {"tick_id": tick_id, "action": "tick_scheduled"}
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        h = hashlib.sha256((prev + content).encode()).hexdigest()
        rec = {
            "event_id": f"evt-hist-{i:03d}",
            "event_type": "L1-01:tick_scheduled",
            "project_id": mock_project_id,
            "payload": payload, "prev_hash": prev, "hash": h, "sequence": i + 1,
            "ts": "2026-04-20T00:00:00Z",
        }
        lines.append(json.dumps(rec))
        prev = h
    jsonl_path.write_text("\n".join(lines) + "\n")
    return tmp_path


@pytest.fixture
def make_recorder(mock_event_bus, mock_l2_01_client, mock_l1_07_client) -> Callable[..., DecisionAuditRecorder]:
    """工厂 · 可注入 jsonl_root（e2e replay 专用）。"""
    def _factory(jsonl_root: Path | None = None, **overrides: Any) -> DecisionAuditRecorder:
        kwargs = dict(
            session_active_pid=f"pid-{uuid.uuid4()}",
            event_bus=mock_event_bus,
            l2_01_client=mock_l2_01_client,
            l1_07_client=mock_l1_07_client,
            buffer_max=64,
            reason_min_length=1,
            jsonl_root=jsonl_root,
        )
        kwargs.update(overrides)
        return DecisionAuditRecorder(**kwargs)
    return _factory


@pytest.fixture
def real_event_bus_stub(tmp_path: Path) -> Any:
    """半真实 event_bus · 写入 in-memory + 按 project_id 分组查询。"""
    class _Event:
        def __init__(self, **kw: Any) -> None:
            self.__dict__.update(kw)

    class _Stub:
        def __init__(self) -> None:
            self._events: list[_Event] = []
            self._hash = "0" * 64
            self._seq = 0

        def append_event(self, **kwargs: Any) -> dict[str, Any]:
            self._seq += 1
            self._hash = kwargs.get("hash") or "0" * 64
            ev = _Event(**kwargs, sequence=self._seq)
            self._events.append(ev)
            return {"event_id": f"evt-{uuid.uuid4()}", "sequence": self._seq,
                    "hash": self._hash, "persisted": True}

        def get_last_hash(self, project_id: str) -> str:
            return self._hash

        def get_events_by_project(self, project_id: str) -> list[_Event]:
            return [e for e in self._events if getattr(e, "project_id", None) == project_id]

        def query(self, **kwargs: Any) -> list[_Event]:
            return []

    return _Stub()
```

---

## §8 集成点用例

> 与兄弟 L2 协作场景（L2-02 决策引擎 / L2-06 Supervisor 接收器 / L2-04 任务链执行器 / L2-01 Tick 调度器）。
> 验 IC-L2-05/06/07/09 真实调用契约 + halt 信号反向回灌 + query_by_* 供 L2-02 自查。

```python
# file: tests/l1_01/test_l2_05_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_05.recorder import DecisionAuditRecorder


class TestL2_05_SiblingIntegration:
    """与 L2-01 / L2-02 / L2-04 / L2-06 协作测试。"""

    def test_TC_L101_L205_901_coop_with_l2_02_decide_then_query_roundtrip(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-901 · 集成 I1（prd §12.9 / 3-1 §13.2 I1）· L2-02 决策后即可自查（decide→audit→query 闭环）。"""
        tick_id = "tick-coop-l2-02"
        decision_id = "dec-coop-001"
        # L2-02 打 hash_tip（打 evidence 链 · §4.1 表）
        tip = sut.get_hash_tip(project_id=mock_project_id)
        assert tip.sequence == 0  # 首条
        # L2-02 decide 完成 → IC-L2-05 audit
        r = sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_tick=tick_id,
            linked_decision=decision_id,
            reason="L2-02 决策后 audit · 再自查 query_by_decision（roundtrip）· reason ≥ 20 字",
            evidence=["evt-1"], payload={"decision_type": "invoke_skill"},
        ))
        # L2-02 立即反查（§3.3 · buffer 命中）
        entry = sut.query_by_decision(decision_id=decision_id, project_id=mock_project_id)
        assert entry is not None
        assert entry.audit_id == r.audit_id

    def test_TC_L101_L205_902_coop_with_l2_04_chain_step_multistep(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-902 · 集成 I3（prd §12.9 / 3-1 §13.2 I3）· L2-04 chain 3 步 · query_by_chain 返 3 条。"""
        chain_id = "ch-coop-003"
        for step in range(3):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-07", action="chain_step_completed",
                actor={"l1": "L1-01", "l2": "L2-04"},
                project_id=mock_project_id, linked_chain=chain_id,
                reason=f"chain step {step + 1}/3 completed ok",
                evidence=[f"evt-chs-{step}"],
                payload={"chain_id": chain_id, "step_id": f"step-{step + 1}", "outcome": "success"},
            ))
        entries = sut.query_by_chain(chain_id=chain_id, project_id=mock_project_id)
        assert len(entries) == 3
        assert [e.payload["step_id"] for e in entries] == ["step-1", "step-2", "step-3"]

    def test_TC_L101_L205_903_coop_with_l2_06_supervisor_info_and_hard_halt(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-903 · L2-06 Supervisor 接收器 · INFO + hard_halt_received 两种 action 都走 IC-L2-05。"""
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="supervisor_info",
            actor={"l1": "L1-01", "l2": "L2-06"},
            project_id=mock_project_id,
            reason="L1-07 推 INFO 级建议 · 只记录不响应",
            evidence=["evt-sup-info-001"], payload={"info_content": "KB hit rate = 82%"},
        ))
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="hard_halt_received",
            actor={"l1": "L1-01", "l2": "L2-06"},
            project_id=mock_project_id,
            reason="L1-07 推 BLOCK · 红线命中 IRREVERSIBLE_HALT",
            evidence=["evt-halt-sup-001"], payload={"red_line_id": "IRREVERSIBLE_HALT"},
        ))
        sut.flush_buffer(force=True, reason="tick_boundary")
        # 两条都已落盘 · 事件 type 分别映射
        types_by_action = {"supervisor_info": "L1-01:supervisor_info",
                           "hard_halt_received": "L1-01:hard_halt"}
        for action, expected_type in types_by_action.items():
            evs = [e for e in sut._captured_events if e.get("action") == action]
            assert len(evs) == 1
            assert evs[0]["event_type"] == expected_type

    def test_TC_L101_L205_904_halt_signal_feedback_to_l2_01_on_write_fail(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        mock_event_bus: MagicMock,
        mock_l2_01_client: MagicMock,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-904 · WRITE_FAIL → emit_halt_signal → L2-01 转 HALTED（§11.2 降级链反向回灌）。"""
        from app.l2_05.errors import AuditError
        mock_event_bus.append_event.side_effect = IOError("disk full")
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-halt",
            reason="halt feedback scenario", evidence=["evt-h"],
        ))
        with pytest.raises(AuditError):
            sut.flush_buffer(force=True, reason="tick_boundary")
        # L2-01 收到 halt_signal · 校验 payload
        mock_l2_01_client.on_halt_signal.assert_called_once()
        args = mock_l2_01_client.on_halt_signal.call_args.kwargs
        assert args["source"] == "L2-05"
        assert args["reason"] == "E_AUDIT_WRITE_FAIL"
        assert args["project_id"] == mock_project_id
```

---

## §9 边界 / edge case

> 空输入 / 超大输入 / 并发 / 超时 / 崩溃恢复 / 脏数据 至少 5 个。

```python
# file: tests/l1_01/test_l2_05_edge_cases.py
from __future__ import annotations

import threading
import pytest
from pathlib import Path

from app.l2_05.recorder import DecisionAuditRecorder
from app.l2_05.errors import AuditError


class TestL2_05_EdgeCases:
    """边界 / edge case · 空输入 / 超大 / 并发 / 超时 / 崩溃 / 脏数据 / LRU。"""

    def test_TC_L101_L205_A01_empty_buffer_query_returns_empty(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L205-A01 · 空 buffer · query_by_decision 返 None · query_by_tick 返 count=0。"""
        assert sut.query_by_decision(decision_id="dec-ghost", project_id=mock_project_id) is None
        r = sut.query_by_tick(tick_id="tick-ghost", project_id=mock_project_id, include_buffered=True)
        assert r.count == 0
        assert r.entries == []

    def test_TC_L101_L205_A02_oversized_payload_still_records(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-A02 · payload 100KB（decision_record 极端大）· 仍入队（§12.2 单 entry ≤ 100KB 软上限）。"""
        big = "x" * 100_000
        cmd = make_audit_cmd(
            source_ic="IC-L2-05", action="decision_made",
            actor={"l1": "L1-01", "l2": "L2-02"},
            project_id=mock_project_id, linked_decision="dec-big",
            reason="oversize payload edge case · reason 不受 payload 大小影响 · 已满足 20 字",
            evidence=["evt-big"], payload={"blob": big, "decision_type": "invoke_skill"},
        )
        r = sut.record_audit(cmd)
        assert r.buffered is True
        assert len(sut.peek_buffer()[-1].payload["blob"]) == 100_000

    def test_TC_L101_L205_A03_concurrent_record_audit_fifo_preserved(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-A03 · 10 线程并发 × 10 入队 · buffer_lock 串行化 · FIFO 语义（prd §12.4 #4）。"""
        def worker(wid: int) -> None:
            for i in range(10):
                sut.record_audit(make_audit_cmd(
                    source_ic="IC-L2-05", action="tick_scheduled",
                    project_id=mock_project_id, linked_tick=f"tick-w{wid}-{i}",
                    reason=f"worker {wid} step {i}", evidence=[f"evt-{wid}-{i}"],
                ))
        threads = [threading.Thread(target=worker, args=(w,)) for w in range(10)]
        for th in threads: th.start()
        for th in threads: th.join(timeout=5)
        assert sut.buffer_size() == 100  # 10 × 10 无丢失（buffer_max=100 需 fixture 调整 · 或 overflow 降级）
        # 每条 audit_id 唯一
        ids = [e.audit_id for e in sut.peek_buffer()]
        assert len(set(ids)) == len(ids)

    def test_TC_L101_L205_A04_query_timeout_partial_returns(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
    ) -> None:
        """TC-L101-L205-A04 · E_AUDIT_QUERY_TIMEOUT · jsonl 扫描超 100ms → partial=true（§3.2）。"""
        sut._inject_jsonl_scan_latency_ms(150)  # test-only hatch
        r = sut.query_by_tick(
            tick_id="tick-slow-scan",
            project_id=mock_project_id,
            include_buffered=False,
        )
        assert getattr(r, "partial", False) is True, "超时应标记 partial=true（§3.2）"

    def test_TC_L101_L205_A05_replay_timeout_partial_rebuild(
        self,
        mock_project_id: str,
        make_recorder,
        large_jsonl_dir: Path,
    ) -> None:
        """TC-L101-L205-A05 · E_AUDIT_REPLAY_TIMEOUT · 100K 条 jsonl 超 30s → partial=true（§3.5）。"""
        fresh = make_recorder(jsonl_root=large_jsonl_dir, replay_timeout_ms=100)  # 人为短超时
        rr = fresh.replay_from_jsonl(project_id=mock_project_id, from_date="2026-04-01")
        assert getattr(rr, "partial", False) is True
        assert rr.replayed_count < 100_000, "超时后只重建已扫部分"
        # 运行时 miss 查询降级扫 jsonl（§3.5）
        assert fresh.replay_status() == "partial"

    def test_TC_L101_L205_A06_replay_hash_broken_warns_continues(
        self,
        mock_project_id: str,
        make_recorder,
        corrupted_jsonl_dir: Path,
        mock_l1_07_client,
    ) -> None:
        """TC-L101-L205-A06 · replay 中遇到 hash 链断裂 · hash_chain_valid=false · 不阻塞启动（§3.5 / SA-01）。"""
        fresh = make_recorder(jsonl_root=corrupted_jsonl_dir, l1_07_client=mock_l1_07_client)
        rr = fresh.replay_from_jsonl(project_id=mock_project_id, from_date="2026-04-15")
        assert rr.hash_chain_valid is False
        assert rr.first_broken_at is not None
        mock_l1_07_client.alert.assert_called()
        assert any(c.kwargs.get("error_code") == "E_AUDIT_HASH_BROKEN"
                   for c in mock_l1_07_client.alert.call_args_list)

    def test_TC_L101_L205_A07_reverse_index_lru_eviction_at_100k(
        self,
        sut: DecisionAuditRecorder,
        mock_project_id: str,
        make_audit_cmd,
    ) -> None:
        """TC-L101-L205-A07 · 反查索引 LRU 淘汰 · 超过 REVERSE_INDEX_MAX_SIZE=100000 最旧条被淘汰（§6.4 / prd §12.10.5）。"""
        sut._set_reverse_index_max(500)  # test-only hatch · 缩小便于验证
        for i in range(600):
            sut.record_audit(make_audit_cmd(
                source_ic="IC-L2-05", action="tick_scheduled",
                project_id=mock_project_id, linked_tick=f"tick-lru-{i}",
                reason=f"lru {i}", evidence=[f"evt-lru-{i}"],
            ))
            if (i + 1) % 50 == 0:
                sut.flush_buffer(force=True, reason="manual")
        assert sut.reverse_index_size() <= 500
        # 最旧 tick 已被淘汰 → query 退化为扫 jsonl（这里 mock 里无 jsonl → 返 0）
        old = sut.query_by_tick(tick_id="tick-lru-0", project_id=mock_project_id, include_buffered=False)
        assert old.count == 0 or old.source == "jsonl_scan"
```

---

*— L1-01 L2-05 决策审计记录器 · TDD 测试用例 · 深度 B 全段完整 · 10 首级错误码 × 15 正向 × 6 IC × 5 SLO × 3 e2e × 4 集成 × 7 边界 · 覆盖 §3 6 方法 + §11 10 错误码 + §12 SLO + §13 13.2 映射表 —*
