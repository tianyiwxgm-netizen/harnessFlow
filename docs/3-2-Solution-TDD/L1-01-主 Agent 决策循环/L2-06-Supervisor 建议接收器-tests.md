---
doc_id: tests-L1-01-L2-06-Supervisor 建议接收器-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-06-Supervisor 建议接收器.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-G
created_at: 2026-04-22
---

# L1-01 L2-06-Supervisor 建议接收器 · TDD 测试用例

> 基于 3-1 L2-06 §3（6 个对外/内部方法：`receive_suggestion` / `broadcast_block` / `get_queue_snapshot` / `acknowledge_warn` / `clear_block` / `watchdog_tick`）+ §11（13 项 `E_SUP_*` 错误码）+ §12（延迟 / 吞吐 SLO · BLOCK 100ms 硬红线）+ §13 映射矩阵 驱动。
> TC ID 统一格式：`TC-L101-L206-NNN`（L1-01 下 L2-06，三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_06_SupervisorSuggestionReceiver` 组织；`class TestL2_06_Negative_*` 负向分组。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景
- [x] §7 测试 fixture（mock L1-07 / mock L2-01 / mock L2-05 / mock clock）
- [x] §8 集成点用例（与兄弟 L2 协作）
- [x] §9 边界 / edge case（空/超大/并发/崩溃）

---

## §1 覆盖度索引

> 每个 §3 对外方法 / §11 错误码 / 本 L2 参与的 IC-XX 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `receive_suggestion()` · §3.1 · INFO 级 | TC-L101-L206-001 | unit | — | IC-13 |
| `receive_suggestion()` · §3.1 · SUGG 级 | TC-L101-L206-002 | unit | — | IC-13 |
| `receive_suggestion()` · §3.1 · WARN 级 | TC-L101-L206-003 | unit | — | IC-13 |
| `receive_suggestion()` · §3.1 · 幂等 | TC-L101-L206-004 | unit | — | IC-13 |
| `receive_suggestion()` · §3.1 · IC-14 转 WARN | TC-L101-L206-005 | unit | — | IC-14 |
| `receive_suggestion()` · §3.1 · counter 只增 | TC-L101-L206-006 | unit | — | I-L2-06-04 |
| `broadcast_block()` · §3.2 · 正常 ≤100ms | TC-L101-L206-007 | unit | — | IC-15 / IC-L2-08 |
| `broadcast_block()` · §3.2 · active_blocks 追加 | TC-L101-L206-008 | unit | — | IC-15 |
| `get_queue_snapshot()` · §3.3 · 返回 snapshot | TC-L101-L206-009 | unit | — | — |
| `get_queue_snapshot()` · §3.3 · read-only 保证 | TC-L101-L206-010 | unit | — | — |
| `acknowledge_warn()` · §3.4 · 正常清除 | TC-L101-L206-011 | unit | — | — |
| `clear_block()` · §3.5 · 清除 + resume 信号 | TC-L101-L206-012 | unit | — | IC-17 |
| `clear_block()` · §3.5 · 部分清除不 resume | TC-L101-L206-013 | unit | — | IC-17 |
| `watchdog_tick()` · §3.6 · supervisor 沉默告警 | TC-L101-L206-014 | unit | — | — |

### §1.2 错误码 × 测试（§3.6 + §11 共 13 项全覆盖）

| 错误码 | TC ID | 方法 | 归属 §11 分类 |
|---|---|---|---|
| `E_SUP_LEVEL_INVALID` | TC-L101-L206-101 | `receive_suggestion()` | 入参校验 |
| `E_SUP_NO_PROJECT_ID` | TC-L101-L206-102 | `receive_suggestion()` | PM-14 根字段 |
| `E_SUP_CROSS_PROJECT` | TC-L101-L206-103 | `receive_suggestion()` | PM-14 违规 |
| `E_SUP_NO_EVIDENCE` (recv) | TC-L101-L206-104 | `receive_suggestion()` | 硬约束违规 |
| `E_SUP_CONTENT_TOO_SHORT` | TC-L101-L206-105 | `receive_suggestion()` | 格式违规 |
| `E_SUP_QUEUE_OVERFLOW` | TC-L101-L206-106 | `receive_suggestion()` | 容量 · 非静默 evict |
| `E_SUP_DUPLICATE_ID` | TC-L101-L206-107 | `receive_suggestion()` | 幂等 |
| `E_SUP_NO_EVIDENCE` (block) | TC-L101-L206-201 | `broadcast_block()` | 硬红线证据缺失 |
| `E_SUP_NO_CONFIRMATION` | TC-L101-L206-202 | `broadcast_block()` | IC-15 二次确认 |
| `E_SUP_BLOCK_SLO_VIOLATION` | TC-L101-L206-203 | `broadcast_block()` | 100ms 违反 · halted 仍生效 |
| `E_SUP_BLOCK_ALREADY_ACTIVE` | TC-L101-L206-204 | `broadcast_block()` | 幂等返回 |
| `E_SUP_L2_01_UNREACHABLE` | TC-L101-L206-205 | `broadcast_block()` | 下游不可达 · 降级 |
| `E_SUP_NOT_INITIALIZED` | TC-L101-L206-301 | `get_queue_snapshot()` | 启动时序 · 不抛 |
| `E_SUP_WARN_NOT_FOUND` | TC-L101-L206-401 | `acknowledge_warn()` | 幂等 · removed=false |
| `E_SUP_WARN_DEADLINE_EXCEEDED` | TC-L101-L206-402 | `acknowledge_warn()` | 迟到回应 · 仍移除 |
| `E_SUP_REASON_TOO_SHORT` | TC-L101-L206-403 | `acknowledge_warn()` | 格式 · reason < 20 |
| `E_SUP_UNAUTHORIZED_CLEAR` | TC-L101-L206-501 | `clear_block()` | I-L2-06-02 · 安全违规 |
| `E_SUP_BLOCK_NOT_FOUND` | TC-L101-L206-502 | `clear_block()` | 幂等返回 |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-13 `push_suggestion` | L1-07 → L2-06 | TC-L101-L206-601 | 消费方 · field-level schema 匹配 |
| IC-14 `push_rollback_route` | L1-07 → L2-06 | TC-L101-L206-602 | 消费方 · 转 WARN 内部 |
| IC-15 `request_hard_halt` | L1-07 → L2-06 | TC-L101-L206-603 | 消费方 · ≤100ms 端到端 + confirmation ≥ 2 |
| IC-17 `user_intervene(authorize)` | L1-10 → L2-01 → L2-06 | TC-L101-L206-604 | 经 L2-01 转发 · user_id 必填 |
| IC-L2-08 `propagate_hard_halt` | L2-06 → L2-01 | TC-L101-L206-605 | 生产方 · cancel_signal payload |
| IC-L2-05 `record_audit` | L2-06 → L2-05 | TC-L101-L206-606 | 生产方 · 每 public 动作 ≥ 1 条审计 |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_06_SupervisorSuggestionReceiver`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `SupervisorSuggestionReceiver`（从 `app.l2_06.receiver` 导入）。

```python
# file: tests/l1_01/test_l2_06_receiver_positive.py
from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import MagicMock

from app.l2_06.receiver import SupervisorSuggestionReceiver
from app.l2_06.schemas import (
    SupervisorSuggestion,
    BlockSignal,
    AcknowledgeWarnCmd,
    ClearBlockCmd,
    AuthorizePayload,
    QueueSnapshot,
    ReceiveAck,
    BroadcastBlockAck,
)
from app.l2_06.errors import SupError


class TestL2_06_SupervisorSuggestionReceiver:
    """§3 对外方法正向用例。每方法 ≥ 1 个 happy path。"""

    # --------- receive_suggestion() · 3 级分派 + 幂等 --------- #

    def test_TC_L101_L206_001_receive_info_audits_but_no_queue_append(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        mock_l2_05_client: MagicMock,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-001 · INFO 级 · 仅审计 · 不入 warn/sugg 队列（§13.10.2 "IC-13 按 level 分派"）。"""
        # arrange
        sugg: SupervisorSuggestion = make_suggestion(
            level="INFO",
            content="INFO 级建议 · 仅观察无需处理（≥10字）",
            project_id=mock_project_id,
        )
        # act
        ack: ReceiveAck = sut.receive_suggestion(sugg)
        # assert
        assert ack.enqueued is True
        assert ack.queue_len == 0, "INFO 级不入 queue · queue_len 仍为 0"
        assert sut.counter_snapshot().info == 1
        audit_actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        assert "suggestion_received" in audit_actions

    def test_TC_L101_L206_002_receive_sugg_enqueues_to_sugg_queue(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-002 · SUGG 级 · 入 sugg_queue FIFO · queue_len += 1。"""
        sugg = make_suggestion(
            level="SUGG",
            content="SUGG 级建议 · 建议重构此模块（≥10字）",
            project_id=mock_project_id,
        )
        ack = sut.receive_suggestion(sugg)
        assert ack.enqueued is True
        assert ack.queue_len == 1
        snapshot = sut.get_queue_snapshot(mock_project_id)
        assert len(snapshot.sugg_queue) == 1
        assert snapshot.sugg_queue[0].suggestion_id == sugg.suggestion_id

    def test_TC_L101_L206_003_receive_warn_enqueues_with_deadline_tick(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-003 · WARN 级 · 入 warn_queue · 记 response_deadline_tick（prd §9.4 #3）。"""
        sugg = make_suggestion(
            level="WARN",
            content="3 次 no_op + KB 降级 · 建议注入上下文（≥10字）",
            project_id=mock_project_id,
            require_ack_tick_delta=1,
        )
        ack = sut.receive_suggestion(sugg)
        assert ack.enqueued is True
        assert ack.queue_len == 1
        snapshot = sut.get_queue_snapshot(mock_project_id)
        assert len(snapshot.warn_queue) == 1
        stored = snapshot.warn_queue[0]
        assert stored.response_deadline_tick is not None, "WARN 必记 deadline tick（§5.1 读图要点 3）"

    def test_TC_L101_L206_004_receive_duplicate_id_idempotent(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-004 · 同 suggestion_id 二次入队 · 幂等返回（queue_len 不变）。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-dup-001")
        r1 = sut.receive_suggestion(sugg)
        r2 = sut.receive_suggestion(sugg)
        assert r1.enqueued is True and r1.queue_len == 1
        assert r2.enqueued is True and r2.queue_len == 1, "幂等 · queue_len 不变"

    def test_TC_L101_L206_005_receive_ic_14_rollback_maps_to_warn(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-005 · IC-14 push_rollback_route 内部映射为 WARN + dimension=risk。"""
        sugg = make_suggestion(
            level="WARN",
            dimension="risk",
            source_ic="IC-14",
            project_id=mock_project_id,
            content="rollback route suggested · revert commit abc (≥10字)",
        )
        ack = sut.receive_suggestion(sugg)
        assert ack.enqueued is True
        snapshot = sut.get_queue_snapshot(mock_project_id)
        assert snapshot.warn_queue[-1].dimension == "risk"

    def test_TC_L101_L206_006_counter_monotonically_increases_on_ack(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
        make_ack_cmd,
    ) -> None:
        """TC-L101-L206-006 · I-L2-06-04 · counter 只增不减（ack 后 counter 保持）。"""
        for i in range(3):
            sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-{i:03d}")
            sut.receive_suggestion(sugg)
        assert sut.counter_snapshot().warn == 3
        ack_cmd = make_ack_cmd(warn_id="sugg-000", project_id=mock_project_id)
        sut.acknowledge_warn(ack_cmd)
        assert sut.counter_snapshot().warn == 3, "I-L2-06-04 · ack 不减 counter"
        snap = sut.get_queue_snapshot(mock_project_id)
        assert len(snap.warn_queue) == 2, "但 queue 实际减 1"

    # --------- broadcast_block() --------- #

    def test_TC_L101_L206_007_broadcast_block_completes_within_100ms(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        mock_l2_01_client: MagicMock,
        make_block_signal,
    ) -> None:
        """TC-L101-L206-007 · IC-15 正常路径 · latency_ms ≤ 100 · halted=true（§12.1 硬 SLO）。"""
        sig: BlockSignal = make_block_signal(
            red_line_id="redline-rm-rf-system",
            project_id=mock_project_id,
        )
        mock_l2_01_client.on_hard_halt.return_value = {
            "halted": True,
            "halt_latency_ms": 60,
            "state_before": "RUNNING",
            "state_after": "HALTED",
            "interrupted_tick_id": "tk-001",
        }
        ack: BroadcastBlockAck = sut.broadcast_block(sig)
        assert ack.halted is True
        assert ack.latency_ms <= 100
        assert ack.state_after == "HALTED"
        assert ack.active_blocks_len == 1
        mock_l2_01_client.on_hard_halt.assert_called_once()

    def test_TC_L101_L206_008_broadcast_block_appends_active_blocks(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_block_signal,
    ) -> None:
        """TC-L101-L206-008 · 多红线 · active_blocks 追加（不同 red_line_id）。"""
        sig1 = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id)
        sig2 = make_block_signal(red_line_id="redline-data-loss", project_id=mock_project_id)
        sut.broadcast_block(sig1)
        sut.broadcast_block(sig2)
        snap = sut.get_queue_snapshot(mock_project_id)
        red_lines = [b["red_line_id"] for b in snap.active_blocks]
        assert set(red_lines) == {"redline-rm-rf-system", "redline-data-loss"}
        assert snap.block_pending_flag is True

    # --------- get_queue_snapshot() --------- #

    def test_TC_L101_L206_009_get_queue_snapshot_returns_all_fields(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-009 · snapshot 返回 warn/sugg/block/counter/ts 全字段（§3.3 schema）。"""
        sut.receive_suggestion(make_suggestion(level="WARN", project_id=mock_project_id))
        sut.receive_suggestion(make_suggestion(level="SUGG", project_id=mock_project_id))
        snap: QueueSnapshot = sut.get_queue_snapshot(mock_project_id)
        assert snap.project_id == mock_project_id
        assert len(snap.warn_queue) == 1
        assert len(snap.sugg_queue) == 1
        assert snap.block_pending_flag is False
        assert snap.counters.warn == 1
        assert snap.counters.sugg == 1
        assert snap.snapshot_ts is not None

    def test_TC_L101_L206_010_get_queue_snapshot_read_only_does_not_mutate(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
    ) -> None:
        """TC-L101-L206-010 · snapshot 是 shallow copy · 修改返回值不影响内部 queue（§5.1 读图要点 1）。"""
        sut.receive_suggestion(make_suggestion(level="WARN", project_id=mock_project_id))
        snap = sut.get_queue_snapshot(mock_project_id)
        snap.warn_queue.clear()  # 外部破坏
        snap2 = sut.get_queue_snapshot(mock_project_id)
        assert len(snap2.warn_queue) == 1, "内部状态应保留 · snapshot 不可变语义"

    # --------- acknowledge_warn() --------- #

    def test_TC_L101_L206_011_acknowledge_warn_removes_from_queue(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        make_suggestion,
        make_ack_cmd,
    ) -> None:
        """TC-L101-L206-011 · ack → warn 移出 queue · removed_from_queue=true · queue_len_after=0。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-001")
        sut.receive_suggestion(sugg)
        cmd = make_ack_cmd(warn_id="sugg-001", project_id=mock_project_id)
        ack = sut.acknowledge_warn(cmd)
        assert ack.removed_from_queue is True
        assert ack.queue_len_after == 0

    # --------- clear_block() --------- #

    def test_TC_L101_L206_012_clear_block_all_cleared_sends_resume_signal(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        mock_l2_01_client: MagicMock,
        make_block_signal,
        make_clear_cmd,
    ) -> None:
        """TC-L101-L206-012 · 清除最后一个 block · 全部 cleared → send_resume_signal()（§3.5）。"""
        sig = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id)
        sut.broadcast_block(sig)
        cmd = make_clear_cmd(red_line_id="redline-rm-rf-system", user_id="user-001")
        r = sut.clear_block(cmd)
        assert r.cleared is True
        assert r.all_cleared is True
        assert r.active_blocks_remaining == 0
        assert r.resume_signal_sent is True
        mock_l2_01_client.send_resume_signal.assert_called_once()

    def test_TC_L101_L206_013_clear_block_partial_does_not_resume(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        mock_l2_01_client: MagicMock,
        make_block_signal,
        make_clear_cmd,
    ) -> None:
        """TC-L101-L206-013 · 2 个 active_blocks · 清除 1 个 · 不发 resume · all_cleared=false。"""
        sut.broadcast_block(make_block_signal(red_line_id="redline-A", project_id=mock_project_id))
        sut.broadcast_block(make_block_signal(red_line_id="redline-B", project_id=mock_project_id))
        r = sut.clear_block(make_clear_cmd(red_line_id="redline-A", user_id="user-001"))
        assert r.cleared is True
        assert r.all_cleared is False
        assert r.active_blocks_remaining == 1
        assert r.resume_signal_sent is False
        mock_l2_01_client.send_resume_signal.assert_not_called()

    # --------- watchdog_tick() --------- #

    def test_TC_L101_L206_014_watchdog_detects_supervisor_silent(
        self,
        sut: SupervisorSuggestionReceiver,
        mock_project_id: str,
        mock_clock,
        mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L206-014 · supervisor 沉默 > 300s · watchdog 发 supervisor_silent_warn（§11.4）。"""
        # arrange · 初始化 last_suggestion_at，然后推进时钟
        sut._set_last_suggestion_at(mock_clock.monotonic_ms())
        mock_clock.advance(301_000)  # 301s · 超 300s 阈值
        # act
        sut.watchdog_tick()
        # assert
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        assert "supervisor_silent_warn" in actions
```

---

## §3 负向用例（每错误码 ≥ 1）

> §3.6 + §11 共 13 项 `E_SUP_*` 全覆盖。每测试用 `pytest.raises(SupError) as exc` + 断言 `exc.value.error_code == "E_SUP_..."`；幂等 / 降级类错误码断言返回对象（不抛）。

```python
# file: tests/l1_01/test_l2_06_receiver_negative.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_06.receiver import SupervisorSuggestionReceiver
from app.l2_06.errors import SupError


class TestL2_06_Negative_ReceiveSuggestion:
    """§3.1 receive_suggestion() 7 错误码（TC-L101-L206-101..107）。"""

    def test_TC_L101_L206_101_level_invalid_raises(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-101 · E_SUP_LEVEL_INVALID · level=BLOCK 错走本接口 → 拒绝。"""
        sugg = make_suggestion(level="BLOCK", project_id=mock_project_id)
        with pytest.raises(SupError) as exc:
            sut.receive_suggestion(sugg)
        assert exc.value.error_code == "E_SUP_LEVEL_INVALID"

    def test_TC_L101_L206_102_no_project_id_raises(
        self, sut: SupervisorSuggestionReceiver, make_suggestion,
    ) -> None:
        """TC-L101-L206-102 · E_SUP_NO_PROJECT_ID · PM-14 根字段校验（§1.6 不变量 #1）。"""
        sugg = make_suggestion(level="WARN", project_id=None)
        with pytest.raises(SupError) as exc:
            sut.receive_suggestion(sugg)
        assert exc.value.error_code == "E_SUP_NO_PROJECT_ID"

    def test_TC_L101_L206_103_cross_project_raises(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-103 · E_SUP_CROSS_PROJECT · project_id ≠ session.active_pid。"""
        sugg = make_suggestion(level="WARN", project_id="pid-018f4a3b-9999-OTHER")
        with pytest.raises(SupError) as exc:
            sut.receive_suggestion(sugg)
        assert exc.value.error_code == "E_SUP_CROSS_PROJECT"

    def test_TC_L101_L206_104_no_evidence_raises(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-104 · E_SUP_NO_EVIDENCE · observation_refs=[] 硬约束违规。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, observation_refs=[])
        with pytest.raises(SupError) as exc:
            sut.receive_suggestion(sugg)
        assert exc.value.error_code == "E_SUP_NO_EVIDENCE"

    def test_TC_L101_L206_105_content_too_short_raises(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-105 · E_SUP_CONTENT_TOO_SHORT · content < 10 字（IC-13 §3.13.4）。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, content="too short")
        with pytest.raises(SupError) as exc:
            sut.receive_suggestion(sugg)
        assert exc.value.error_code == "E_SUP_CONTENT_TOO_SHORT"

    def test_TC_L101_L206_106_queue_overflow_evicts_oldest_non_silent(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
        mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L206-106 · E_SUP_QUEUE_OVERFLOW · warn_cap=64 满 evict 最旧 · 非静默（§5.1 读图要点 4 + §11.1 "不阻塞"）。"""
        # arrange · 灌满 warn_queue（默认 cap=64）
        for i in range(64):
            sut.receive_suggestion(
                make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-old-{i:03d}"),
            )
        # act · 第 65 条应触发 evict
        new_sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-new-001")
        ack = sut.receive_suggestion(new_sugg)
        # assert · enqueued=true（不阻塞）· evicted_suggestion_id 非空 · 审计 queue_evict_oldest
        assert ack.enqueued is True
        assert ack.evicted_suggestion_id is not None
        assert ack.evicted_suggestion_id.startswith("sugg-old-"), "evict 最旧（FIFO）"
        evict_actions = [
            c.kwargs.get("action")
            for c in mock_l2_05_client.record_audit.call_args_list
            if c.kwargs.get("action") == "queue_evict_oldest"
        ]
        assert len(evict_actions) >= 1, "非静默 evict · 审计必达"

    def test_TC_L101_L206_107_duplicate_id_idempotent_no_second_enqueue(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-107 · E_SUP_DUPLICATE_ID · 同 suggestion_id 二次 · queue_len 不变（§3.1 幂等）。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-idem-001")
        sut.receive_suggestion(sugg)
        r2 = sut.receive_suggestion(sugg)
        assert r2.enqueued is True, "幂等返回 · 不抛"
        assert r2.queue_len == 1


class TestL2_06_Negative_BroadcastBlock:
    """§3.2 broadcast_block() 5 错误码（TC-L101-L206-201..205）。"""

    def test_TC_L101_L206_201_block_no_evidence_rejected(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_block_signal,
    ) -> None:
        """TC-L101-L206-201 · E_SUP_NO_EVIDENCE · evidence.observation_refs=[] · 安全优先不降级。"""
        sig = make_block_signal(
            red_line_id="redline-rm-rf-system",
            project_id=mock_project_id,
            evidence={"observation_refs": [], "confirmation_count": 2},
        )
        with pytest.raises(SupError) as exc:
            sut.broadcast_block(sig)
        assert exc.value.error_code == "E_SUP_NO_EVIDENCE"

    def test_TC_L101_L206_202_block_no_confirmation_rejected(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_block_signal,
    ) -> None:
        """TC-L101-L206-202 · E_SUP_NO_CONFIRMATION · confirmation_count < 2（IC-15 §3.15.4）。"""
        sig = make_block_signal(
            red_line_id="redline-rm-rf-system",
            project_id=mock_project_id,
            evidence={"observation_refs": ["evt-1"], "confirmation_count": 1},
        )
        with pytest.raises(SupError) as exc:
            sut.broadcast_block(sig)
        assert exc.value.error_code == "E_SUP_NO_CONFIRMATION"

    def test_TC_L101_L206_203_block_slo_violation_still_halted_true(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal, mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L206-203 · E_SUP_BLOCK_SLO_VIOLATION · latency_ms > 100 · halted 仍 true + 审计。"""
        mock_l2_01_client.on_hard_halt.return_value = {
            "halted": True, "halt_latency_ms": 120,  # > 100ms
            "state_before": "RUNNING", "state_after": "HALTED",
            "interrupted_tick_id": "tk-001",
        }
        sig = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id)
        ack = sut.broadcast_block(sig)
        assert ack.halted is True, "§11.1 · halted 仍生效"
        assert ack.latency_ms > 100
        slo_errs = [
            c.kwargs.get("error_code")
            for c in mock_l2_05_client.record_audit.call_args_list
            if c.kwargs.get("error_code") == "E_SUP_BLOCK_SLO_VIOLATION"
        ]
        assert len(slo_errs) >= 1

    def test_TC_L101_L206_204_block_already_active_idempotent(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal,
    ) -> None:
        """TC-L101-L206-204 · E_SUP_BLOCK_ALREADY_ACTIVE · 同 red_line_id 第二次 · 返回已有 ack · 不重复 broadcast。"""
        sig1 = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id,
                                 block_id="halt-001")
        sig2 = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id,
                                 block_id="halt-002")
        r1 = sut.broadcast_block(sig1)
        r2 = sut.broadcast_block(sig2)
        assert r1.halted is True
        assert r2.halted is True
        assert r2.block_id == "halt-001", "返回已有 block_id"
        assert mock_l2_01_client.on_hard_halt.call_count == 1, "不重复 broadcast 给 L2-01"

    def test_TC_L101_L206_205_l2_01_unreachable_degrades(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L101-L206-205 · E_SUP_L2_01_UNREACHABLE · L2-01 抛异常 → 降级：active_blocks 仍追加 + 发事件。"""
        mock_l2_01_client.on_hard_halt.side_effect = RuntimeError("L2-01 crashed")
        sig = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id)
        ack = sut.broadcast_block(sig)
        # §11.3 降级：halted=false + 错误码 + 事件发出
        assert ack.halted is False
        assert ack.error_code == "E_SUP_L2_01_UNREACHABLE"
        # 仍 append active_blocks（§11.3 行 2）
        snap = sut.get_queue_snapshot(mock_project_id)
        assert len(snap.active_blocks) == 1
        # 直发 L1-01:hard_halt 事件（经 L2-05 → L1-09）
        degraded = [
            c for c in mock_event_bus.append_event.call_args_list
            if c.kwargs.get("event_type") == "L1-01:supervisor_gateway_degraded"
        ]
        assert len(degraded) >= 1


class TestL2_06_Negative_GetQueueSnapshot:
    """§3.3 get_queue_snapshot() 1 错误码（TC-L101-L206-301）· E_SUP_CROSS_PROJECT 与 recv 共享 · 不重复测。"""

    def test_TC_L101_L206_301_not_initialized_returns_empty_snapshot(
        self, mock_project_id: str, uninitialized_receiver: SupervisorSuggestionReceiver,
    ) -> None:
        """TC-L101-L206-301 · E_SUP_NOT_INITIALIZED · AdviceQueue 尚未初始化 · 返回空 snapshot 不抛（§3.3 "L2-02 可容忍"）。"""
        snap = uninitialized_receiver.get_queue_snapshot(mock_project_id)
        assert snap.warn_queue == []
        assert snap.sugg_queue == []
        assert snap.block_pending_flag is False
        assert snap.counters.warn == 0


class TestL2_06_Negative_AcknowledgeWarn:
    """§3.4 acknowledge_warn() 3 错误码（TC-L101-L206-401..403）。"""

    def test_TC_L101_L206_401_warn_not_found_removed_false(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_ack_cmd,
    ) -> None:
        """TC-L101-L206-401 · E_SUP_WARN_NOT_FOUND · warn_id 不在 queue · removed=false 不抛（幂等）。"""
        cmd = make_ack_cmd(warn_id="sugg-ghost", project_id=mock_project_id)
        ack = sut.acknowledge_warn(cmd)
        assert ack.removed_from_queue is False
        assert ack.queue_len_after == 0

    def test_TC_L101_L206_402_warn_deadline_exceeded_still_removed(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        make_suggestion, make_ack_cmd, mock_clock, mock_l2_05_client: MagicMock,
    ) -> None:
        """TC-L101-L206-402 · E_SUP_WARN_DEADLINE_EXCEEDED · 超 deadline · 仍移除 + 审计 + WARN 回 L1-07。"""
        sugg = make_suggestion(
            level="WARN", project_id=mock_project_id, suggestion_id="sugg-late-001",
            require_ack_tick_delta=1,
        )
        sut.receive_suggestion(sugg)
        # 推进时钟，让 deadline_tick 已过
        sut._advance_tick(delta=5)
        cmd = make_ack_cmd(warn_id="sugg-late-001", project_id=mock_project_id)
        ack = sut.acknowledge_warn(cmd)
        assert ack.removed_from_queue is True, "仍移除（§11.1 "迟到回应"）"
        late_errs = [
            c.kwargs.get("error_code")
            for c in mock_l2_05_client.record_audit.call_args_list
            if c.kwargs.get("error_code") == "E_SUP_WARN_DEADLINE_EXCEEDED"
        ]
        assert len(late_errs) >= 1

    def test_TC_L101_L206_403_reason_too_short_rejected(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        make_suggestion, make_ack_cmd,
    ) -> None:
        """TC-L101-L206-403 · E_SUP_REASON_TOO_SHORT · reason < 20 字 · 拒绝（PRD §9.4 硬约束 #1）。"""
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-001")
        sut.receive_suggestion(sugg)
        cmd = make_ack_cmd(
            warn_id="sugg-001", project_id=mock_project_id,
            reason="too short",  # < 20 字
        )
        with pytest.raises(SupError) as exc:
            sut.acknowledge_warn(cmd)
        assert exc.value.error_code == "E_SUP_REASON_TOO_SHORT"


class TestL2_06_Negative_ClearBlock:
    """§3.5 clear_block() 2 错误码（TC-L101-L206-501..502）。"""

    def test_TC_L101_L206_501_unauthorized_clear_empty_user_id_rejected(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        make_block_signal, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-501 · E_SUP_UNAUTHORIZED_CLEAR · user_id 为空 → 拒绝（I-L2-06-02）。"""
        sut.broadcast_block(make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id))
        cmd = make_clear_cmd(red_line_id="redline-rm-rf-system", user_id="")
        with pytest.raises(SupError) as exc:
            sut.clear_block(cmd)
        assert exc.value.error_code == "E_SUP_UNAUTHORIZED_CLEAR"

    def test_TC_L101_L206_502_block_not_found_idempotent_cleared_true(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-502 · E_SUP_BLOCK_NOT_FOUND · red_line_id 不在 active_blocks · 幂等返回 cleared=true。"""
        cmd = make_clear_cmd(red_line_id="redline-never-active", user_id="user-001")
        r = sut.clear_block(cmd)
        assert r.cleared is True, "幂等 · 已是期望状态"
        assert r.active_blocks_remaining == 0
```

---

## §4 IC-XX 契约集成测试

> 本 L2 是 IC-13/14/15/17 **消费方** · IC-L2-08/IC-L2-05 **生产方**。
> 每测试 mock 对端 L1-07 / L2-01 / L2-05 / event_bus · 断言 payload 字段结构精确匹配 ic-contracts.md §3.13/§3.14/§3.15/§3.17 + L1-01 architecture.md §6。

```python
# file: tests/l1_01/test_l2_06_ic_contracts.py
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock

from app.l2_06.receiver import SupervisorSuggestionReceiver


class TestL2_06_IC_Contracts:
    """IC-13 / IC-14 / IC-15 / IC-17 / IC-L2-08 / IC-L2-05 六个契约集成测试。"""

    def test_TC_L101_L206_601_ic_13_push_suggestion_payload_matches_contract(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_suggestion,
    ) -> None:
        """TC-L101-L206-601 · IC-13 · field-level schema 匹配（ic-contracts §3.13）。

        契约必填：suggestion_id / project_id / level / content(≥10) / observation_refs(≥1) / ts
        """
        sugg = make_suggestion(
            level="WARN",
            project_id=mock_project_id,
            observation_refs=["evt-1", "evt-2", "evt-3"],
            content="3 次 no_op + KB 降级 · 建议注入权重（≥10字）",
            require_ack_tick_delta=1,
        )
        ack = sut.receive_suggestion(sugg)
        assert ack.enqueued is True
        # 审计 payload 必带 project_id（PM-14）+ level + evidence refs
        audit_calls = [
            c for c in mock_l2_05_client.record_audit.call_args_list
            if c.kwargs.get("action") == "suggestion_received"
        ]
        assert len(audit_calls) == 1
        payload = audit_calls[0].kwargs
        assert payload["project_id"] == mock_project_id
        assert payload.get("level") == "WARN"
        assert payload.get("evidence") == ["evt-1", "evt-2", "evt-3"]

    def test_TC_L101_L206_602_ic_14_rollback_route_mapped_to_warn_dimension_risk(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-602 · IC-14 push_rollback_route · 内部映射 level=WARN + dimension=risk。"""
        sugg = make_suggestion(
            level="WARN",
            dimension="risk",
            source_ic="IC-14",
            project_id=mock_project_id,
            content="rollback route: revert to commit abc · 执行回滚（≥10字）",
        )
        sut.receive_suggestion(sugg)
        snap = sut.get_queue_snapshot(mock_project_id)
        assert snap.warn_queue[-1].dimension == "risk"
        assert snap.warn_queue[-1].source_ic == "IC-14"

    def test_TC_L101_L206_603_ic_15_request_hard_halt_latency_within_100ms(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal,
    ) -> None:
        """TC-L101-L206-603 · IC-15 · confirmation ≥ 2 · 端到端 ≤ 100ms（arch §3.5 D-05 硬约束）。"""
        sig = make_block_signal(
            red_line_id="redline-rm-rf-system",
            project_id=mock_project_id,
            evidence={"observation_refs": ["evt-danger-1"], "confirmation_count": 2},
            supervisor_event_id="sup-evt-001",
        )
        mock_l2_01_client.on_hard_halt.return_value = {
            "halted": True, "halt_latency_ms": 50,
            "state_before": "RUNNING", "state_after": "HALTED",
            "interrupted_tick_id": "tk-running",
        }
        t0 = time.monotonic()
        ack = sut.broadcast_block(sig)
        end_to_end_ms = (time.monotonic() - t0) * 1000
        assert ack.halted is True
        assert ack.latency_ms <= 100
        assert end_to_end_ms <= 100.0, "端到端 ≤100ms 硬红线（prd §13.4 #1）"

    def test_TC_L101_L206_604_ic_17_authorize_clears_block_via_l2_01_forward(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-604 · IC-17 user_intervene(authorize) · 经 L2-01 转发 clear_block · user_id 必填。"""
        sut.broadcast_block(make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id))
        cmd = make_clear_cmd(
            red_line_id="redline-rm-rf-system",
            user_id="user-real",
            comment="确认已备份数据库 · 授权清除 BLOCK",
        )
        r = sut.clear_block(cmd)
        assert r.cleared is True
        assert r.all_cleared is True
        # resume 信号回到 L2-01（send_resume_signal 被调）
        mock_l2_01_client.send_resume_signal.assert_called_once()

    def test_TC_L101_L206_605_ic_l2_08_propagate_hard_halt_carries_cancel_signal(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal,
    ) -> None:
        """TC-L101-L206-605 · IC-L2-08 · L2-06 调 L2-01.on_hard_halt(cancel_signal) payload 字段。

        契约字段（arch §6 IC-L2-08）：cancel_id / tick_id / reason_type / red_line_id / ts
        """
        sig = make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id)
        sut.broadcast_block(sig)
        mock_l2_01_client.on_hard_halt.assert_called_once()
        payload = mock_l2_01_client.on_hard_halt.call_args.kwargs
        assert "cancel_id" in payload
        assert payload["reason_type"] == "supervisor_block"
        assert payload["red_line_id"] == "redline-rm-rf-system"
        assert "ts" in payload

    def test_TC_L101_L206_606_ic_l2_05_record_audit_per_action(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_suggestion, make_block_signal,
        make_ack_cmd, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-606 · IC-L2-05 · 每个可观测动作 ≥ 1 条审计（Partnership · §4.4 #3）。"""
        # receive_suggestion
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id="sugg-audit-001")
        sut.receive_suggestion(sugg)
        # broadcast_block
        sut.broadcast_block(make_block_signal(red_line_id="redline-rm-rf-system", project_id=mock_project_id))
        # acknowledge_warn
        sut.acknowledge_warn(make_ack_cmd(warn_id="sugg-audit-001", project_id=mock_project_id))
        # clear_block
        sut.clear_block(make_clear_cmd(red_line_id="redline-rm-rf-system", user_id="user-001"))

        actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        required = {"suggestion_received", "hard_halt_received", "warn_acknowledged", "hard_halt_cleared"}
        assert required.issubset(set(actions)), f"缺失审计动作：{required - set(actions)}"
        # 所有审计必带 actor=L2-06
        for call in mock_l2_05_client.record_audit.call_args_list:
            assert call.kwargs.get("actor") == "L2-06"
```

---

## §5 性能 SLO 用例

> §12.1 延迟 SLO + §12.2 吞吐。`@pytest.mark.perf` · pytest-benchmark 可选。
> 重点验 BLOCK 100ms 硬红线（arch §3.5 D-05 · prd §13.4 #1）。

```python
# file: tests/l1_01/test_l2_06_perf.py
from __future__ import annotations

import time
import pytest

from app.l2_06.receiver import SupervisorSuggestionReceiver


@pytest.mark.perf
class TestL2_06_SLO:
    """§12 SLO 性能用例。"""

    def test_TC_L101_L206_701_receive_suggestion_p95_under_2ms(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-701 · receive_suggestion enqueue P95 ≤ 2ms / P99 ≤ 3ms / 硬 5ms（§12.1）。"""
        samples: list[float] = []
        for i in range(500):
            sugg = make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-perf-{i:04d}")
            t0 = time.monotonic()
            sut.receive_suggestion(sugg)
            samples.append((time.monotonic() - t0) * 1000)
            if i % 60 == 59:
                sut._drain_warn_queue()  # avoid overflow
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 2.0, f"receive_suggestion P95 = {p95:.2f}ms 超 2ms SLO"
        assert p99 <= 3.0, f"receive_suggestion P99 = {p99:.2f}ms 超 3ms SLO"
        assert max(samples) <= 5.0, "硬上限 5ms 被破（§12.1）"

    def test_TC_L101_L206_702_broadcast_block_p99_under_100ms_hard_redline(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client, make_block_signal,
    ) -> None:
        """TC-L101-L206-702 · broadcast_block 端到端 P99 ≤ 85ms · 硬上限 100ms（prd §13.4 #1 硬红线）。"""
        mock_l2_01_client.on_hard_halt.return_value = {
            "halted": True, "halt_latency_ms": 40,
            "state_before": "RUNNING", "state_after": "HALTED",
            "interrupted_tick_id": "tk-001",
        }
        samples: list[float] = []
        for i in range(100):
            sut._reset_active_blocks()
            sig = make_block_signal(
                red_line_id=f"redline-test-{i:03d}",
                project_id=mock_project_id,
                block_id=f"halt-{i:04d}",
            )
            t0 = time.monotonic()
            sut.broadcast_block(sig)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        p99 = samples[int(len(samples) * 0.99)]
        assert p95 <= 60.0, f"broadcast_block P95 = {p95:.2f}ms 超 60ms"
        assert p99 <= 85.0, f"broadcast_block P99 = {p99:.2f}ms 超 85ms"
        assert max(samples) <= 100.0, "100ms 是硬红线（arch §3.5 D-05 · 不可违反）"

    def test_TC_L101_L206_703_get_queue_snapshot_p99_under_2ms(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-703 · get_queue_snapshot P99 ≤ 2ms · 硬 5ms（§12.1 · 纯内存读）。"""
        # 预填 30 条 warn
        for i in range(30):
            sut.receive_suggestion(
                make_suggestion(level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-warm-{i:03d}"),
            )
        samples: list[float] = []
        for _ in range(1000):
            t0 = time.monotonic()
            sut.get_queue_snapshot(mock_project_id)
            samples.append((time.monotonic() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 <= 2.0, f"get_queue_snapshot P99 = {p99:.2f}ms 超 2ms"
        assert max(samples) <= 5.0, "硬 5ms（§12.1）"

    def test_TC_L101_L206_704_throughput_receive_suggestion_100_per_second(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-704 · receive_suggestion 吞吐 ≥ 100 条/s（§12.2）。"""
        N = 200
        t0 = time.monotonic()
        for i in range(N):
            sut.receive_suggestion(
                make_suggestion(level="SUGG", project_id=mock_project_id, suggestion_id=f"sugg-tp-{i:04d}"),
            )
            if (i + 1) % 200 == 0:
                sut._drain_sugg_queue()
        elapsed = time.monotonic() - t0
        tps = N / elapsed
        assert tps >= 100.0, f"实测吞吐 {tps:.1f} 条/s 低于 100 条/s SLO（§12.2）"
```

---

## §6 端到端 e2e

> 映射 §5.1 P0 时序（SUGG/WARN 入队 → 下 tick 消费）+ §5.2 P1 时序（BLOCK ≤100ms 抢占）+ prd §8.9 I1/I3。
> `@pytest.mark.e2e` · 半真实 L2-01 + L2-02 + L2-05 + L1-09 event_bus stub。

```python
# file: tests/l1_01/test_l2_06_e2e.py
from __future__ import annotations

import time
import pytest

from app.l2_06.receiver import SupervisorSuggestionReceiver


@pytest.mark.e2e
class TestL2_06_E2E:
    """端到端场景 · P0/P1 时序 · 8 GWT 对应。"""

    def test_TC_L101_L206_801_e2e_p0_warn_enqueue_then_l2_02_pull_and_ack(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        real_l2_02_mock, real_l2_05_mock, make_suggestion, make_ack_cmd,
    ) -> None:
        """TC-L101-L206-801 · P0 时序全链（§5.1）· L1-07 → L2-06 → L2-02 pull → warn_response → ack。

        GIVEN L1-07 推送 WARN 级建议（≥10字 + ≥1 evidence）
        WHEN L2-02 下 tick 调 get_queue_snapshot 拿到 WARN
            AND L2-02 产 warn_response 调 acknowledge_warn
        THEN warn 从 queue 移除 · counter 保持 · 审计链 3 条完整
        """
        # 1. L1-07 → L2-06: 推 WARN
        sugg = make_suggestion(
            level="WARN",
            project_id=mock_project_id,
            suggestion_id="sugg-e2e-001",
            content="3 次 no_op + KB 降级 · 建议注入权重（≥10字）",
            observation_refs=["evt-1", "evt-2", "evt-3"],
        )
        sut.receive_suggestion(sugg)

        # 2. 下 tick · L2-02 pull
        snap = sut.get_queue_snapshot(mock_project_id)
        assert len(snap.warn_queue) == 1
        pending = snap.warn_queue[0]

        # 3. L2-02 产 warn_response · 调 acknowledge_warn
        ack = sut.acknowledge_warn(make_ack_cmd(
            warn_id=pending.suggestion_id,
            project_id=mock_project_id,
            response="accept",
            reason="我们将立即提高 KB 注入权重并减少 no_op 决策（≥20字）",
        ))
        assert ack.removed_from_queue is True
        # 4. 验 counter 不减（I-L2-06-04）
        assert sut.counter_snapshot().warn == 1
        # 5. 审计链 3 条：suggestion_received + warn_acknowledged + 审计 meta
        actions = [c.kwargs.get("action") for c in real_l2_05_mock.record_audit.call_args_list]
        assert "suggestion_received" in actions
        assert "warn_acknowledged" in actions

    def test_TC_L101_L206_802_e2e_p1_block_end_to_end_under_100ms(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        real_l2_01_mock, real_l2_02_mock, real_l2_05_mock,
        make_block_signal,
    ) -> None:
        """TC-L101-L206-802 · P1 时序（§5.2）· BLOCK 端到端 ≤100ms · state=HALTED + L2-02 aborted。

        GIVEN L2-02 正在 decide Stage 3（5 纪律拷问）
        WHEN L1-07 检测硬红线 · IC-15 到本 L2
        THEN L2-06 → L2-01 on_hard_halt → L2-01 async_cancel → L2-02 AbortFlag set
            AND 全链 ≤100ms · state_after=HALTED · tick_interrupted=true
        """
        real_l2_01_mock.on_hard_halt.return_value = {
            "halted": True, "halt_latency_ms": 60,
            "state_before": "RUNNING", "state_after": "HALTED",
            "interrupted_tick_id": "tk-current", "tick_interrupted": True,
        }
        sig = make_block_signal(
            red_line_id="redline-rm-rf-system",
            project_id=mock_project_id,
            evidence={"observation_refs": ["evt-danger-1"], "confirmation_count": 2},
            supervisor_event_id="sup-evt-danger",
        )
        t0 = time.monotonic()
        ack = sut.broadcast_block(sig)
        latency_ms = (time.monotonic() - t0) * 1000
        # 硬红线断言
        assert ack.halted is True
        assert ack.state_after == "HALTED"
        assert ack.tick_interrupted is True
        assert latency_ms <= 100.0, "端到端 ≤100ms 硬红线"
        # 审计链：hard_halt_received
        actions = [c.kwargs.get("action") for c in real_l2_05_mock.record_audit.call_args_list]
        assert "hard_halt_received" in actions

    def test_TC_L101_L206_803_e2e_authorize_clear_block_chain(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        real_l2_01_mock, real_l2_05_mock, make_block_signal, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-803 · 用户授权清除 · IC-17 → L2-01 → L2-06 clear_block → resume_signal。

        GIVEN BLOCK 已 active · UI 用户点击 authorize
        WHEN L2-01 转发 user_authorize 给 L2-06
        THEN clear_block(red_line_id, payload) · all_cleared=true · L2-01 发 resume_signal → state=IDLE
        """
        real_l2_01_mock.on_hard_halt.return_value = {
            "halted": True, "halt_latency_ms": 40,
            "state_before": "RUNNING", "state_after": "HALTED",
            "interrupted_tick_id": "tk-001",
        }
        sut.broadcast_block(make_block_signal(
            red_line_id="redline-rm-rf-system", project_id=mock_project_id))
        # 用户授权到达（经 L2-01 转发）
        r = sut.clear_block(make_clear_cmd(
            red_line_id="redline-rm-rf-system",
            user_id="user-real-001",
            comment="已确认目录为临时目录 · 授权执行",
        ))
        assert r.cleared is True
        assert r.all_cleared is True
        assert r.resume_signal_sent is True
        real_l2_01_mock.send_resume_signal.assert_called_once()
        # 审计 hard_halt_cleared
        actions = [c.kwargs.get("action") for c in real_l2_05_mock.record_audit.call_args_list]
        assert "hard_halt_cleared" in actions
```

---

## §7 测试 fixture

> conftest.py 提供本 L2 复用 fixture。`mock_project_id` / `mock_clock` / `mock_event_bus` / L2-01/L2-05 client + suggestion / block / ack / clear 工厂。

```python
# file: tests/l1_01/conftest.py
from __future__ import annotations

import uuid
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.l2_06.receiver import SupervisorSuggestionReceiver
from app.l2_06.schemas import SupervisorSuggestion, BlockSignal, AcknowledgeWarnCmd, ClearBlockCmd


class VirtualClock:
    """§9 Mock 策略 · unit 模式 · 手动推进 ms 的假时钟。"""
    def __init__(self) -> None:
        self._now_ms: int = 0
    def monotonic_ms(self) -> int:
        return self._now_ms
    def advance(self, ms: int) -> None:
        self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_clock() -> VirtualClock:
    return VirtualClock()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="L1-09-event-bus")
    bus.append_event.return_value = {"event_id": f"evt-{uuid.uuid4()}", "sequence": 1}
    return bus


@pytest.fixture
def mock_l2_01_client() -> MagicMock:
    client = MagicMock(name="L2-01-tick-scheduler")
    client.on_hard_halt.return_value = {
        "halted": True, "halt_latency_ms": 50,
        "state_before": "RUNNING", "state_after": "HALTED",
        "interrupted_tick_id": None, "tick_interrupted": False,
    }
    client.send_resume_signal.return_value = {"resumed": True}
    return client


@pytest.fixture
def mock_l2_05_client() -> MagicMock:
    client = MagicMock(name="L2-05-audit-recorder")
    client.record_audit.return_value = {"audit_id": f"aud-{uuid.uuid4()}"}
    return client


@pytest.fixture
def sut(mock_project_id, mock_clock, mock_event_bus,
        mock_l2_01_client, mock_l2_05_client) -> SupervisorSuggestionReceiver:
    return SupervisorSuggestionReceiver(
        session_active_pid=mock_project_id,
        clock=mock_clock,
        event_bus=mock_event_bus,
        l2_01_client=mock_l2_01_client,
        l2_05_client=mock_l2_05_client,
        warn_cap=64, sugg_cap=256, info_cap=0,
        supervisor_silent_threshold_sec=300,
    )


@pytest.fixture
def uninitialized_receiver(mock_clock, mock_event_bus,
                           mock_l2_01_client, mock_l2_05_client) -> SupervisorSuggestionReceiver:
    """用于 TC-L101-L206-301 · AdviceQueue 尚未初始化场景。"""
    r = SupervisorSuggestionReceiver.__new__(SupervisorSuggestionReceiver)
    r._initialized = False
    r._clock = mock_clock
    return r


@pytest.fixture
def make_suggestion() -> Callable[..., SupervisorSuggestion]:
    def _factory(**overrides: Any) -> SupervisorSuggestion:
        base = dict(
            suggestion_id=f"sugg-{uuid.uuid4()}",
            project_id="pid-default",
            level="WARN",
            content="Supervisor 建议内容（≥10字）默认填充",
            dimension="quality",
            suggested_action=None,
            observation_refs=["evt-default-1"],
            priority="P2",
            require_ack_tick_delta=1,
            source_ic="IC-13",
            ts="2026-04-22T00:00:00Z",
        )
        base.update(overrides)
        return SupervisorSuggestion(**base)
    return _factory


@pytest.fixture
def make_block_signal() -> Callable[..., BlockSignal]:
    def _factory(**overrides: Any) -> BlockSignal:
        base = dict(
            block_id=f"halt-{uuid.uuid4()}",
            project_id="pid-default",
            red_line_id="redline-default",
            supervisor_event_id=f"sup-evt-{uuid.uuid4()}",
            message="red line triggered · default message（≥10 chars）",
            evidence={"observation_refs": ["evt-danger-1"], "confirmation_count": 2},
            require_user_authorization=True,
            ts="2026-04-22T00:00:00Z",
        )
        base.update(overrides)
        return BlockSignal(**base)
    return _factory


@pytest.fixture
def make_ack_cmd() -> Callable[..., AcknowledgeWarnCmd]:
    def _factory(**overrides: Any) -> AcknowledgeWarnCmd:
        base = dict(
            warn_id="sugg-default",
            project_id="pid-default",
            response="accept",
            reason="默认回应理由 · 我们将立即处理此建议（≥20字）",
            responded_at_tick="tk-default",
            ts="2026-04-22T00:00:00Z",
        )
        base.update(overrides)
        return AcknowledgeWarnCmd(**base)
    return _factory


@pytest.fixture
def make_clear_cmd() -> Callable[..., ClearBlockCmd]:
    def _factory(**overrides: Any) -> ClearBlockCmd:
        red_line_id = overrides.pop("red_line_id", "redline-default")
        user_id = overrides.pop("user_id", "user-default-001")
        comment = overrides.pop("comment", "授权清除理由（≥5字）")
        return ClearBlockCmd(
            red_line_id=red_line_id,
            authorize_payload={
                "user_id": user_id,
                "comment": comment,
                "ts": "2026-04-22T00:00:00Z",
            },
        )
    return _factory


@pytest.fixture
def real_l2_01_mock(mock_l2_01_client) -> MagicMock:
    return mock_l2_01_client


@pytest.fixture
def real_l2_02_mock() -> MagicMock:
    client = MagicMock(name="L2-02-decision-engine")
    client.on_async_cancel.return_value = {"aborted": True, "abort_latency_ms": 35}
    return client


@pytest.fixture
def real_l2_05_mock(mock_l2_05_client) -> MagicMock:
    return mock_l2_05_client
```

---

## §8 集成点用例

> 与兄弟 L2 协作场景（L2-02 决策引擎 pull · L2-05 审计记录器 Partnership）。
> 对齐 §13.3 核心映射：L2-06 ↔ L2-02 的"pull 消费" + "BLOCK 抢占" 两条关键耦合。

```python
# file: tests/l1_01/test_l2_06_integration_siblings.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.l2_06.receiver import SupervisorSuggestionReceiver


class TestL2_06_SiblingIntegration:
    """与 L2-02 / L2-05 / L2-01 的协作测试。"""

    def test_TC_L101_L206_901_coop_with_l2_02_pull_snapshot_in_context_assembler(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-901 · L2-02 ContextAssembler.assemble() → L2-06.get_queue_snapshot · pull 模式。

        对齐 §13.3 关键耦合 1："pull 消费"。
        """
        # L1-07 → L2-06 推 WARN
        sut.receive_suggestion(make_suggestion(
            level="WARN", project_id=mock_project_id, suggestion_id="sugg-pull-001",
        ))
        # L2-02 ContextAssembler 模拟 pull（每 tick 1 次）
        snap = sut.get_queue_snapshot(mock_project_id)
        assert len(snap.warn_queue) == 1
        assert snap.warn_queue[0].suggestion_id == "sugg-pull-001"
        # pull 不改 queue 状态（read-only · §3.3）
        snap2 = sut.get_queue_snapshot(mock_project_id)
        assert len(snap2.warn_queue) == 1, "pull 不消费 · 多次 pull 结果一致"

    def test_TC_L101_L206_902_coop_with_l2_02_warn_response_chain(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        make_suggestion, make_ack_cmd,
    ) -> None:
        """TC-L101-L206-902 · L2-02 warn_response 决策 → L2-06.acknowledge_warn · queue 减 1 / counter 不减。"""
        for i in range(3):
            sut.receive_suggestion(make_suggestion(
                level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-chain-{i:03d}",
            ))
        # L2-02 逐条 ack
        for i in range(3):
            sut.acknowledge_warn(make_ack_cmd(
                warn_id=f"sugg-chain-{i:03d}", project_id=mock_project_id,
            ))
        snap = sut.get_queue_snapshot(mock_project_id)
        assert len(snap.warn_queue) == 0, "3 条都移除"
        assert sut.counter_snapshot().warn == 3, "I-L2-06-04 · counter 保持"

    def test_TC_L101_L206_903_coop_with_l2_05_audit_partnership_buffers_on_crash(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_05_client: MagicMock, make_suggestion,
    ) -> None:
        """TC-L101-L206-903 · L2-05 crash → local_buffer · 恢复后 flush（§11.3 Partnership 降级）。"""
        # 第一次 audit 失败
        mock_l2_05_client.record_audit.side_effect = [
            RuntimeError("L2-05 down"),
            {"audit_id": "aud-001"},
        ]
        sut.receive_suggestion(make_suggestion(
            level="WARN", project_id=mock_project_id, suggestion_id="sugg-buf-001",
        ))
        # 本地 buffer ≥ 1
        assert sut.local_audit_buffer_size() >= 1
        # L2-05 恢复 · flush
        mock_l2_05_client.record_audit.side_effect = None
        mock_l2_05_client.record_audit.return_value = {"audit_id": "aud-ok"}
        sut.flush_local_audit_buffer()
        assert sut.local_audit_buffer_size() == 0

    def test_TC_L101_L206_904_coop_with_l2_01_resume_signal_after_all_cleared(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_l2_01_client: MagicMock, make_block_signal, make_clear_cmd,
    ) -> None:
        """TC-L101-L206-904 · 多 BLOCK 全部 clear 后 · L2-06 发 send_resume_signal → L2-01 state=IDLE。"""
        sut.broadcast_block(make_block_signal(red_line_id="redline-A", project_id=mock_project_id))
        sut.broadcast_block(make_block_signal(red_line_id="redline-B", project_id=mock_project_id))
        # clear A · 未全部 cleared
        r1 = sut.clear_block(make_clear_cmd(red_line_id="redline-A", user_id="user-001"))
        assert r1.resume_signal_sent is False
        mock_l2_01_client.send_resume_signal.assert_not_called()
        # clear B · 全部 cleared
        r2 = sut.clear_block(make_clear_cmd(red_line_id="redline-B", user_id="user-001"))
        assert r2.resume_signal_sent is True
        mock_l2_01_client.send_resume_signal.assert_called_once()
```

---

## §9 边界 / edge case

> 空输入 / 超大 / 并发 / 超时 / 崩溃恢复 / 脏数据 至少 5 个。

```python
# file: tests/l1_01/test_l2_06_edge_cases.py
from __future__ import annotations

import threading
import pytest

from app.l2_06.receiver import SupervisorSuggestionReceiver
from app.l2_06.errors import SupError


class TestL2_06_EdgeCases:
    """边界 / edge case · 空输入 / 超大 / 并发 / 超时 / 崩溃 / 脏数据。"""

    def test_TC_L101_L206_A01_empty_queue_snapshot_returns_zero_counts(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
    ) -> None:
        """TC-L101-L206-A01 · 空队列 · snapshot.warn_queue=[] · counters 全 0 · 不崩。"""
        snap = sut.get_queue_snapshot(mock_project_id)
        assert snap.warn_queue == []
        assert snap.sugg_queue == []
        assert snap.active_blocks == []
        assert snap.counters.info == 0
        assert snap.counters.sugg == 0
        assert snap.counters.warn == 0
        assert snap.counters.block == 0

    def test_TC_L101_L206_A02_oversize_content_10kb_still_enqueued(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-A02 · content 10KB（极端）· 仍入队 · 触发 WARN（内存占用 §12.2 ≤ 50MB）。"""
        big_content = "x" * 10_000
        sugg = make_suggestion(level="WARN", project_id=mock_project_id, content=big_content)
        ack = sut.receive_suggestion(sugg)
        assert ack.enqueued is True

    def test_TC_L101_L206_A03_concurrent_receive_suggestion_thread_safe(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-A03 · 20 线程并发 × 10 入队 · 无 race · 200 次调用 queue 状态一致。"""
        errors: list[Exception] = []

        def worker(worker_id: int) -> None:
            for i in range(10):
                try:
                    sut.receive_suggestion(make_suggestion(
                        level="SUGG", project_id=mock_project_id,
                        suggestion_id=f"sugg-w{worker_id:02d}-{i:03d}",
                    ))
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(wid,)) for wid in range(20)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=5)
        assert not errors, f"并发出错：{errors[:3]}"
        # counter 应为 200（counter 只增 · I-L2-06-04）
        assert sut.counter_snapshot().sugg == 200

    def test_TC_L101_L206_A04_warn_queue_overflow_cap_64_evicts_on_65th(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-A04 · warn_cap=64 · 第 65 条 evict 最旧（§5.1 读图要点 4）。"""
        for i in range(64):
            sut.receive_suggestion(make_suggestion(
                level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-cap-{i:03d}",
            ))
        assert len(sut.get_queue_snapshot(mock_project_id).warn_queue) == 64
        # 第 65 条触发 evict
        ack = sut.receive_suggestion(make_suggestion(
            level="WARN", project_id=mock_project_id, suggestion_id="sugg-cap-064",
        ))
        assert ack.enqueued is True
        assert ack.evicted_suggestion_id == "sugg-cap-000", "FIFO · 最旧被 evict"
        snap = sut.get_queue_snapshot(mock_project_id)
        ids = [s.suggestion_id for s in snap.warn_queue]
        assert "sugg-cap-000" not in ids
        assert "sugg-cap-064" in ids

    def test_TC_L101_L206_A05_watchdog_silent_warn_exact_threshold_300s(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        mock_clock, mock_l2_05_client,
    ) -> None:
        """TC-L101-L206-A05 · supervisor_silent_threshold_sec=300 边界 · 301s 触发 · 299s 不触发（§10 参数）。"""
        sut._set_last_suggestion_at(mock_clock.monotonic_ms())
        mock_clock.advance(299_000)
        sut.watchdog_tick()
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        assert "supervisor_silent_warn" not in actions, "299s 不触发"
        mock_clock.advance(2_000)  # 301s
        sut.watchdog_tick()
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        assert "supervisor_silent_warn" in actions, "301s 触发"

    def test_TC_L101_L206_A06_dirty_suggestion_id_format_rejected(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str, make_suggestion,
    ) -> None:
        """TC-L101-L206-A06 · 脏数据 · suggestion_id 非 sugg-{uuid-v7} 格式 · 拒绝（§7.1 schema）。"""
        sugg = make_suggestion(
            level="WARN",
            project_id=mock_project_id,
            suggestion_id="not-a-valid-id",
        )
        with pytest.raises(SupError):
            sut.receive_suggestion(sugg)

    def test_TC_L101_L206_A07_crash_recovery_rebuilds_queue_from_jsonl(
        self, mock_project_id: str, mock_clock, mock_event_bus,
        mock_l2_01_client, mock_l2_05_client, tmp_path,
    ) -> None:
        """TC-L101-L206-A07 · 崩溃重启 · jsonl replay 重建 warn_queue + active_blocks（§7 持久化）。"""
        jsonl_path = tmp_path / "supervisor_gateway.jsonl"
        # session 1 · 写入
        r1 = SupervisorSuggestionReceiver(
            session_active_pid=mock_project_id,
            clock=mock_clock,
            event_bus=mock_event_bus,
            l2_01_client=mock_l2_01_client,
            l2_05_client=mock_l2_05_client,
            persist_jsonl_path=str(jsonl_path),
            warn_cap=64, sugg_cap=256, info_cap=0,
            supervisor_silent_threshold_sec=300,
        )
        r1._persist_snapshot(warn=[{"suggestion_id": "sugg-persist-001"}],
                             active_blocks=[{"red_line_id": "redline-persist-A"}])
        # session 2 · 重建
        r2 = SupervisorSuggestionReceiver(
            session_active_pid=mock_project_id,
            clock=mock_clock,
            event_bus=mock_event_bus,
            l2_01_client=mock_l2_01_client,
            l2_05_client=mock_l2_05_client,
            persist_jsonl_path=str(jsonl_path),
            warn_cap=64, sugg_cap=256, info_cap=0,
            supervisor_silent_threshold_sec=300,
        )
        r2.replay_from_jsonl()
        snap = r2.get_queue_snapshot(mock_project_id)
        ids = [s.get("suggestion_id") if isinstance(s, dict) else s.suggestion_id for s in snap.warn_queue]
        assert "sugg-persist-001" in ids
        red_lines = [b["red_line_id"] for b in snap.active_blocks]
        assert "redline-persist-A" in red_lines

    def test_TC_L101_L206_A08_block_pending_with_queue_full_most_dangerous_state(
        self, sut: SupervisorSuggestionReceiver, mock_project_id: str,
        make_suggestion, make_block_signal, mock_l2_05_client,
    ) -> None:
        """TC-L101-L206-A08 · §8.4 最危险组合态 · queue 满 + BLOCK pending · 升级告警 queue_full_during_block_warn。"""
        # BLOCK pending
        sut.broadcast_block(make_block_signal(
            red_line_id="redline-danger", project_id=mock_project_id,
        ))
        # warn queue 灌满
        for i in range(65):
            sut.receive_suggestion(make_suggestion(
                level="WARN", project_id=mock_project_id, suggestion_id=f"sugg-full-{i:03d}",
            ))
        # watchdog 升级告警
        sut.watchdog_tick()
        actions = [c.kwargs.get("action") for c in mock_l2_05_client.record_audit.call_args_list]
        assert any("queue_full_during_block_warn" in a for a in actions if a), \
            "§11.4 最危险组合 · 必须升级告警"
```

---

*— L1-01 L2-06 Supervisor 建议接收器 · TDD 测试用例 · 深度 B 全段完整 · 18 错误码 × 14 正向 × 6 IC × 4 SLO × 3 e2e × 4 集成 × 8 边界 —*
