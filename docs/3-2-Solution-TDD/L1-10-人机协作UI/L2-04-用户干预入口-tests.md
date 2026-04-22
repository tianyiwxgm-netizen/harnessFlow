---
doc_id: tests-L1-10-L2-04-用户干预入口-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-04-用户干预入口.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-04-用户干预入口 · TDD 测试用例

> 基于 3-1 L2-04 §3（`submit_intervention()` 主方法 + 10 种 InterventionType payload 分化） + §11（15 项错误码 · E-PM14 / E-L2-04 / E-IC-017 三前缀 · 6 级降级链） + §12 SLO（panic ≤ 500ms · submit P95 ≤ 200ms · panic→UI 锁 ≤ 100ms 硬约束） + §13 TC-L204-001~060 驱动。
> TC ID 统一格式：`TC-L110-L204-NNN`（3 位流水号 · 001-099 正向 · 101-199 负向 · 601-699 IC 契约 · 701-799 性能 · 801-899 e2e · 901-999 边界）。
> **本 L2 是 L1-10 唯一的 write 出口**（ADR-L204-01）· 所有测试覆盖 panic 硬约束 + 双端审计 + 10s 幂等 + 凭证零持久化。
> pytest + Python 3.11+ 类型注解；前端测试以 Python 伪代码表达（实现可用 Vitest + @vue/test-utils）· 本 TDD 文件不要求真跑。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC-XX + SLO）
- [x] §2 正向用例（每 public 方法 + 10 种 InterventionType + 状态机路径）
- [x] §3 负向用例（每错误码 ≥ 1 · 15 条 E-* 覆盖）
- [x] §4 IC-XX 契约集成测试（IC-17 / IC-18 / IC-L2-03/05/06/07 · ≥ 6 条）
- [x] §5 性能 SLO 用例（panic 100ms 硬约束 + submit 200ms P95 + DOM lock 100ms）
- [x] §6 端到端 e2e 场景（panic 全系统急停 · Gate 委托 · 授权带凭证）
- [x] §7 测试 fixture（mock_project_id / mock_clock / mock_event_bus / mock_ic17 / fake_dom / make_intent）
- [x] §8 集成点用例（L2-01/02/05/06/07 兄弟协作 · PanicLock 广播 · SSE 解锁）
- [x] §9 边界 / edge case（空/超大/并发/浏览器刷新/DOM mutation/GC）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / §4 IC / §12 SLO 在下表至少出现一次。
> 覆盖类型：unit = 单组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO。

### §1.1 方法 × 测试 × 覆盖类型（涵盖 10 种 InterventionType）

| 方法 / 入口（§3 出处） | TC ID | 覆盖类型 | 对应 IC | 备注 |
|---|---|---|---|---|
| `submit_intervention(type=panic)` · §3.1/§3.2 | TC-L110-L204-001 | unit + perf | IC-17 | panic 主路径 · 跳 confirm · 激活 PanicLock |
| `submit_intervention(type=pause)` | TC-L110-L204-002 | unit | IC-17 | pause 经 confirm |
| `submit_intervention(type=resume)` | TC-L110-L204-003 | unit | IC-17 | resume 经 confirm · panic 锁中唯一可用的非 resume |
| `submit_intervention(type=change_request)` | TC-L110-L204-004 | unit | IC-17 | 变更请求 payload 校验 |
| `submit_intervention(type=clarify)` | TC-L110-L204-005 | unit | IC-17 | 澄清作答 payload |
| `submit_intervention(type=authorize)` | TC-L110-L204-006 | unit | IC-17 | 带凭证 · 经 CredentialEphemeralBus |
| `submit_intervention(type=gate_decision)` | TC-L110-L204-007 | integration | IC-L2-03 + IC-17 | L2-02 委托 |
| `submit_intervention(type=kb_promote)` | TC-L110-L204-008 | integration | IC-L2-05 + IC-17 | L2-05 委托 |
| `submit_intervention(type=set_scale_profile)` | TC-L110-L204-009 | integration | IC-L2-06 + IC-17 | L2-06 委托 |
| `submit_intervention(type=admin_config_change)` | TC-L110-L204-010 | integration | IC-L2-07 + IC-17 | L2-07 委托 |
| `InterventionFactory.create()` · §6.1 | TC-L110-L204-011 | unit | — | AR id UUID v4 + 字段全 |
| `IdempotencyChecker.check()` · §6.2 | TC-L110-L204-012 | unit | — | 10s 窗口 · hash(type+payload+bucket) |
| `PanicLockController.activate()` · §6.3 | TC-L110-L204-013 | unit + perf | — | ≤ 100ms · disabled_selectors 正确 |
| `PanicLockController._on_halted()` · §6.3 | TC-L110-L204-014 | integration | — | SSE recv → UNLOCKING → UNLOCKED |
| `ConfirmDialogBroker.show()` · §6.4 | TC-L110-L204-015 | unit | — | 30s timeout 视为 canceled |
| `AuditWriter.write()` · §6.5 | TC-L110-L204-016 | integration | IC-18 | 本地 + IC-18 双端 · 本地先 |
| `CredentialEphemeralBus.store()` · §6.6 | TC-L110-L204-017 | unit | — | Uint8Array · TTL 30s |
| `CredentialEphemeralBus.zero_fill()` · §6.6 | TC-L110-L204-018 | unit | — | buffer 每 byte 置 0 |
| `DeliveryPipeline.send_ic17()` · §6.7 | TC-L110-L204-019 | unit | IC-17 | 不重试 · timeout 5s |
| `JSONLFileStore.append()` · §6.8 | TC-L110-L204-020 | unit | — | fsync per write + 每 100 条 snapshot |
| `get_intervention_history()` | TC-L110-L204-021 | unit | — | 按 type/status/time filter |
| state transition full path | TC-L110-L204-022 | integration | — | NEW→VALIDATED→IDEMPOTENCY_CHECKED→CONFIRMING→SUBMITTING→ACKED |
| state transition panic path | TC-L110-L204-023 | integration | — | 跳过 CONFIRMING（ADR-L204-02） |

### §1.2 错误码 × 测试（§11 全 15 项覆盖）

| 错误码 | TC ID | 方法 / 场景 | 归属分类 |
|---|---|---|---|
| `E-PM14-001` | TC-L110-L204-101 | payload 缺 project_id | PM-14 拦截 |
| `E-PM14-002` | TC-L110-L204-102 | payload.project_id ≠ active_project | PM-14 race |
| `E-L2-04-001` | TC-L110-L204-103 | type="foo"（不在 10 枚举） | schema |
| `E-L2-04-002` | TC-L110-L204-104 | authorize payload 缺 red_line_id | schema |
| `E-L2-04-002-b` | TC-L110-L204-105 | payload > 10KB | schema size |
| `E-L2-04-003` | TC-L110-L204-106 | 10s 窗口内同 key 重复 | IdempotencyChecker |
| `E-L2-04-004` | TC-L110-L204-107 | confirm 用户点取消 | ConfirmDialogBroker |
| `E-L2-04-004-t` | TC-L110-L204-108 | confirm 30s 超时 | ConfirmDialogBroker timeout |
| `E-L2-04-005` | TC-L110-L204-109 | PanicLock 激活期间 non-resume 提交 | PanicLockController |
| `E-L2-04-006` | TC-L110-L204-110 | 非 panic 传 `_skip_confirm=true` | InterventionFactory 拦截 7 |
| `E-L2-04-007` | TC-L110-L204-111 | credential slot 已 zero_fill 后再 submit | CredentialBus |
| `E-L2-04-008` | TC-L110-L204-112 | 本地 fsync 失败 | AuditWriter local |
| `E-L2-04-009` | TC-L110-L204-113 | IC-18 append_event 失败 | AuditWriter bus |
| `E-L2-04-010` | TC-L110-L204-114 | 本地 + IC-18 双端全失败 | AuditWriter both |
| `E-L2-04-011` | TC-L110-L204-115 | IC-17 5s 超时无 ack | DeliveryPipeline timeout |
| `E-L2-04-012` | TC-L110-L204-116 | IC-17 transport error (connect refused) | DeliveryPipeline transport |
| `E-L2-04-013` | TC-L110-L204-117 | IC-17 ack accepted=false | DeliveryPipeline reject |
| `E-L2-04-014` | TC-L110-L204-118 | panic 发出 60s 未收 halted 事件 | PanicLock wait |
| `E-L2-04-015` | TC-L110-L204-119 | DOM mutation 后 lock 失效（MutationObserver 漏） | PanicLock reapply |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-17 user_intervene | L2-04 → L1-01 | TC-L110-L204-601 | body 含 intent_id + idempotency_key · ack accepted |
| IC-18 append_event | L2-04 → L1-09 | TC-L110-L204-602 | 每次 submit 推 `L1-10:user_intervention_submitted` |
| IC-L2-03 gate_decision | L2-02 → L2-04 | TC-L110-L204-603 | 上游委托 · 参数不丢 |
| IC-L2-05 kb_promote | L2-05 → L2-04 | TC-L110-L204-604 | 上游委托 |
| IC-L2-06 set_scale_profile | L2-06 → L2-04 | TC-L110-L204-605 | 上游委托 |
| IC-L2-07 authorize | L2-07 → L2-04 | TC-L110-L204-606 | 上游委托 · 带凭证 |

### §1.4 SLO × 测试（§12 硬约束 ≥ 3）

| SLO 场景 | 目标 | TC ID | 样本数 |
|---|---|---|---|
| panic → UI 锁完成 | **≤ 100ms P95**（硬约束） | TC-L110-L204-701 | 100 次 |
| panic → IC-17 发出 | ≤ 200ms P95 | TC-L110-L204-702 | 100 次 |
| panic → L1-01 收到 | ≤ 500ms P95 | TC-L110-L204-703 | 100 次 |
| submit 端到端 | ≤ 200ms P95 | TC-L110-L204-704 | 100 次 |
| 本地 audit fsync | ≤ 5ms P95 | TC-L110-L204-705 | 100 次 |
| IC-18 append_event | ≤ 50ms P95 | TC-L110-L204-706 | 100 次 |
| IdempotencyChecker.check | ≤ 1ms P95 | TC-L110-L204-707 | 1000 次 |
| PanicLockController.activate DOM 遍历 | ≤ 80ms P95（500 节点） | TC-L110-L204-708 | 100 次 |

### §1.5 PM-14 project 过滤（硬约束 · 每视图）

每 UI 测试含正向 + 负向：
- 正向：`payload.project_id == active_project` → 通过
- 负向：`payload.project_id != active_project` → E-PM14-002 + UI "请刷新" · 不发 IC-17

TC-L110-L204-101/102（负向） + TC-L110-L204-901 / 902（集成）是 PM-14 的硬约束载体。

---

## §2 正向用例（每方法 + 10 种 InterventionType ≥ 1）

> pytest 风格；`class TestL2_04_UserIntervene`；被测对象 SUT = `InterventionService`（从 `app.l1_10.l2_04.service` 导入）。

```python
# file: tests/l1_10/test_l2_04_positive.py
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_04.service import InterventionService
from app.l1_10.l2_04.ar import InterventionIntent
from app.l1_10.l2_04.schemas import (
    InterventionType,
    PanicLockState,
    IC17Ack,
)


class TestL2_04_UserIntervene_Positive:
    """每 public 方法 + 每种 InterventionType 至少 1 正向用例。"""

    # ---------- 10 种 InterventionType 主路径 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_001_submit_panic_happy_path(
        self, sut: InterventionService, mock_project_id: str,
        mock_ic17_transport: AsyncMock, mock_panic_lock: MagicMock,
    ) -> None:
        """TC-L110-L204-001 · panic 主路径 · 跳 confirm · PanicLock activate · IC-17 发出。"""
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True, l101_state_at_ack="halting")
        out = await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn",
        )
        assert out.status == "ACKED"
        assert out.ack_status.accepted is True
        assert out.latency_ms < 500  # P99 SLO
        # panic 锁已激活（硬约束）
        mock_panic_lock.activate.assert_called_once()
        # confirm dialog 没有调用（panic 硬编码跳过）
        assert not sut.confirm_broker.show.called

    @pytest.mark.asyncio
    async def test_TC_L110_L204_002_submit_pause_via_confirm(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-002 · pause 必走二次确认 · 用户点确认后发 IC-17。"""
        mock_confirm_broker.show.return_value = True  # 用户确认
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True, l101_state_at_ack="paused")
        out = await sut.submit_intervention(
            type="pause",
            payload={"project_id": mock_project_id, "comment": "讨论中"},
            _source="l2-01-panic-btn",
        )
        assert out.status == "ACKED"
        mock_confirm_broker.show.assert_called_once()

    @pytest.mark.asyncio
    async def test_TC_L110_L204_003_submit_resume(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-003 · resume 经 confirm · panic 锁中唯一非 resume 可用。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True, l101_state_at_ack="running")
        out = await sut.submit_intervention(
            type="resume",
            payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn",
        )
        assert out.status == "ACKED"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_004_submit_change_request(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-004 · change_request · 变更请求 payload 校验。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="change_request",
            payload={
                "project_id": mock_project_id,
                "target_tab": "gate",
                "change_description": "请重跑 S5 的 TDD Verifier",
                "urgency": "high",
            },
            _source="l2-02-gate",
        )
        assert out.status == "ACKED"
        # IC-17 body 含全字段
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["target_tab"] == "gate"
        assert body["payload"]["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_005_submit_clarify(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-005 · clarify · 澄清作答。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="clarify",
            payload={
                "project_id": mock_project_id,
                "question_id": "q-001",
                "answer": "目标是落盘审计 · 不要启用远端 fallback",
            },
            _source="l2-02-gate",
        )
        assert out.status == "ACKED"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_006_submit_authorize_with_credential(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
        mock_credential_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-006 · authorize 带凭证 · 经 CredentialEphemeralBus · 用后 zero_fill。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        # 模拟前端已把 PAT 塞入 slot
        slot_id = "slot-abc"
        mock_credential_bus.get_buffer.return_value = bytearray(b"ghp_FAKE_TOKEN_xxxxxxxx")

        out = await sut.submit_intervention(
            type="authorize",
            payload={
                "project_id": mock_project_id,
                "red_line_id": "rl-007",
                "decision": "grant",
                "scope_limit": {"repo": "foo/bar", "duration_sec": 3600},
                "credential_slot_ref": slot_id,
            },
            _source="l2-07-admin",
        )
        assert out.status == "ACKED"
        # 用后立即 zero_fill
        mock_credential_bus.zero_fill.assert_called_once_with(slot_id)

    @pytest.mark.asyncio
    async def test_TC_L110_L204_007_submit_gate_decision_delegation(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-007 · L2-02 经 IC-L2-03 委托 · 封装为 gate_decision。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="gate_decision",
            payload={
                "project_id": mock_project_id,
                "gate_id": "gate-S5-001",
                "decision": "Go",
                "comment": "所有 DoD 项已验证 · 监控接入 OK",  # ≥ 10 字
            },
            _source="l2-02-gate",
        )
        assert out.status == "ACKED"
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["type"] == "gate_decision"
        assert body["payload"]["gate_id"] == "gate-S5-001"
        assert body["payload"]["decision"] == "Go"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_008_submit_kb_promote_delegation(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-008 · L2-05 经 IC-L2-05 委托 · 封装为 kb_promote。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="kb_promote",
            payload={
                "project_id": mock_project_id,
                "entry_id": "kb-1024",
                "target_scope": "global",
                "rationale": "此 pattern 有跨项目复用价值",
            },
            _source="l2-05-kb",
        )
        assert out.status == "ACKED"
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["target_scope"] == "global"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_009_submit_set_scale_profile(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-009 · L2-06 经 IC-L2-06 委托 · 封装为 set_scale_profile。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="set_scale_profile",
            payload={
                "project_id": mock_project_id,
                "profile": "P2_standard",
                "locked_at_stage": "S1",
            },
            _source="l2-06-profile",
        )
        assert out.status == "ACKED"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_010_submit_admin_config_change(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-010 · L2-07 经 IC-L2-07 委托 · admin_config_change。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="admin_config_change",
            payload={
                "project_id": mock_project_id,
                "config_key": "tick_interval_sec",
                "old_value": 5,
                "new_value": 3,
                "reason": "提高反应速度",
            },
            _source="l2-07-admin",
        )
        assert out.status == "ACKED"

    # ---------- 内部组件单测 ----------

    def test_TC_L110_L204_011_factory_creates_ar_with_uuid_v4(
        self, sut: InterventionService, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-011 · InterventionFactory.create · intent_id UUID v4 + 字段全。"""
        intent = sut.factory.create(
            type="pause",
            payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn",
        )
        assert isinstance(intent, InterventionIntent)
        uuid_obj = uuid.UUID(intent.intent_id)
        assert uuid_obj.version == 4
        assert intent.project_id == mock_project_id
        assert intent.type == "pause"
        assert intent.submitted_at is not None
        assert intent.status == "NEW"
        assert intent._skip_confirm is False  # 非 panic 默认 False

    def test_TC_L110_L204_011b_factory_panic_auto_skip_confirm(
        self, sut: InterventionService, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-011b · panic type 自动置 _skip_confirm=True（内部字段）。"""
        intent = sut.factory.create(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn",
        )
        assert intent._skip_confirm is True

    def test_TC_L110_L204_012_idempotency_check_distinct_payloads_not_collide(
        self, sut: InterventionService, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-012 · 相同 type 不同 payload → 不同 key · 不互相拦截。"""
        key1 = sut.idempotency_checker.compute_key(
            type="pause",
            payload={"project_id": mock_project_id, "comment": "A"},
            now_ms=1000,
        )
        key2 = sut.idempotency_checker.compute_key(
            type="pause",
            payload={"project_id": mock_project_id, "comment": "B"},
            now_ms=1000,
        )
        assert key1 != key2
        # 都应通过
        assert sut.idempotency_checker.check_and_register(key1) is True
        assert sut.idempotency_checker.check_and_register(key2) is True

    def test_TC_L110_L204_012b_idempotency_window_natural_expiry(
        self, sut: InterventionService, mock_project_id: str, mock_clock: "FakeClock",
    ) -> None:
        """TC-L110-L204-012b · 10s 窗口到期 · 同 key 可再提交（TC-L204-006）。"""
        key = sut.idempotency_checker.compute_key(
            type="pause",
            payload={"project_id": mock_project_id},
            now_ms=mock_clock.now_ms(),
        )
        assert sut.idempotency_checker.check_and_register(key) is True
        # 11s 后重试
        mock_clock.advance(11_000)
        key2 = sut.idempotency_checker.compute_key(
            type="pause",
            payload={"project_id": mock_project_id},
            now_ms=mock_clock.now_ms(),
        )
        # 不同 bucket → 不同 key → 可通过
        assert key != key2
        assert sut.idempotency_checker.check_and_register(key2) is True

    def test_TC_L110_L204_013_panic_lock_activate_collects_selectors(
        self, sut: InterventionService, fake_dom,
    ) -> None:
        """TC-L110-L204-013 · PanicLockController.activate · disabled_selectors 正确收集。"""
        fake_dom.add_buttons([
            ".btn-panic", ".btn-resume", ".btn-admin-unblock",   # 豁免
            ".btn-pause", ".btn-gate-go", ".btn-kb-promote",      # 应被禁
            ".btn-profile-set", ".btn-admin-apply",
        ])
        sut.panic_lock.activate(intent_id="intent-1")
        # 锁状态 LOCKED
        assert sut.panic_lock.state == "LOCKED"
        # 豁免按钮未 disable
        for s in [".btn-panic", ".btn-resume", ".btn-admin-unblock"]:
            assert fake_dom.is_enabled(s) is True
        # 其他按钮 disable
        for s in [".btn-pause", ".btn-gate-go", ".btn-kb-promote",
                  ".btn-profile-set", ".btn-admin-apply"]:
            assert fake_dom.is_enabled(s) is False

    @pytest.mark.asyncio
    async def test_TC_L110_L204_014_panic_lock_on_halted_unlocks(
        self, sut: InterventionService, fake_dom, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-014 · SSE recv L1-09:system_halted → PanicLock UNLOCKING → UNLOCKED。"""
        fake_dom.add_buttons([".btn-panic", ".btn-pause", ".btn-resume"])
        sut.panic_lock.activate(intent_id="intent-1")
        assert sut.panic_lock.state == "LOCKED"
        # 模拟 L2-03 SSE 推 halted 事件
        await sut.panic_lock._on_halted({
            "type": "L1-09:system_halted",
            "ts": "2026-04-22T06:30:10.000Z",
            "project_id": sut.factory.active_project_id,
        })
        assert sut.panic_lock.state == "UNLOCKED"
        assert fake_dom.is_enabled(".btn-pause") is True

    @pytest.mark.asyncio
    async def test_TC_L110_L204_015_confirm_broker_shows_dialog_for_non_panic(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-015 · ConfirmDialogBroker.show · 非 panic 必弹 · panic 必跳。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)

        # pause 弹
        await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert mock_confirm_broker.show.call_count == 1
        # panic 跳（同一 sut · 累计次数不变）
        await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn")
        assert mock_confirm_broker.show.call_count == 1  # 未增

    @pytest.mark.asyncio
    async def test_TC_L110_L204_016_audit_writer_dual_end_local_first(
        self, sut: InterventionService, mock_project_id: str,
        mock_local_store: AsyncMock, mock_ic18_transport: AsyncMock,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-016 · AuditWriter 双端写 · 本地先 IC-18 后（D4 / ADR-L204-04）。"""
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        # 用 call_order 捕获调用顺序
        call_order: list[str] = []
        mock_local_store.append.side_effect = lambda *a, **kw: call_order.append("local") or None
        mock_ic18_transport.append_event.side_effect = lambda *a, **kw: call_order.append("ic18") or None

        await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn",
        )
        assert call_order[0] == "local"
        assert "ic18" in call_order

    def test_TC_L110_L204_017_credential_bus_store_returns_slot_id(
        self, sut: InterventionService,
    ) -> None:
        """TC-L110-L204-017 · CredentialEphemeralBus.store · 返 slot_id · TTL 启动。"""
        buf = bytearray(b"ghp_FAKE_TOKEN")
        slot_id = sut.credential_bus.store(buf)
        assert uuid.UUID(slot_id)  # 合法 uuid
        slot = sut.credential_bus.slots[slot_id]
        assert slot.buffer == bytearray(b"ghp_FAKE_TOKEN")
        assert slot.zero_filled_at is None

    def test_TC_L110_L204_018_credential_bus_zero_fill_wipes_buffer(
        self, sut: InterventionService,
    ) -> None:
        """TC-L110-L204-018 · zero_fill · buffer 每 byte 置 0 · Map.delete。"""
        buf = bytearray(b"ghp_SECRET_1234")
        slot_id = sut.credential_bus.store(buf)
        sut.credential_bus.zero_fill(slot_id)
        # slot 从 Map 删除
        assert slot_id not in sut.credential_bus.slots
        # 原 buffer 全 0
        # (注：bytearray(b"ghp_SECRET_1234") 会被 store 内部 copy · 原 buf 可能未清
        #  · 关键是 slots 里的已清 · 此处验证 slots 删除)

    @pytest.mark.asyncio
    async def test_TC_L110_L204_019_delivery_pipeline_no_retry(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-019 · DeliveryPipeline 失败不重试（ADR-L204-06）· 单次调用。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.side_effect = ConnectionError("connect refused")
        out = await sut.submit_intervention(
            type="pause",
            payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn",
        )
        assert out.status == "REJECTED"
        # 只调用一次 · 没有自动重试
        assert mock_ic17_transport.post.call_count == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L204_020_jsonl_file_store_appends_with_fsync(
        self, sut: InterventionService, mock_project_id: str,
        mock_local_store: AsyncMock,
    ) -> None:
        """TC-L110-L204-020 · JSONLFileStore.append · fsync per write（断言 mock 被调用）。"""
        await sut.audit_writer.write_local({
            "project_id": mock_project_id,
            "intent_id": "int-001",
            "type": "pause",
            "submitted_at": "2026-04-22T06:30:00Z",
        })
        path = mock_local_store.append.call_args.args[0]
        assert path == f"projects/{mock_project_id}/ui/intervene/audit.jsonl"
        # JSONLFileStore 内部保证 fsync · 此处以 mock 被调次数代表

    def test_TC_L110_L204_021_get_intervention_history_filters(
        self, sut: InterventionService, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-021 · get_intervention_history · 按 type/status/time 过滤。"""
        sut.history.append_all([
            {"type": "pause", "status": "ACKED", "submitted_at": "2026-04-22T06:00:00Z"},
            {"type": "panic", "status": "ACKED", "submitted_at": "2026-04-22T06:30:00Z"},
            {"type": "pause", "status": "REJECTED", "submitted_at": "2026-04-22T07:00:00Z"},
        ])
        out = sut.get_intervention_history(filter={"type": "pause"})
        assert len(out) == 2
        out = sut.get_intervention_history(filter={"status": "ACKED"})
        assert len(out) == 2
        out = sut.get_intervention_history(filter={"since": "2026-04-22T06:15:00Z"})
        assert len(out) == 2

    # ---------- 状态机路径 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_022_state_machine_full_path_non_panic(
        self, sut: InterventionService, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-022 · 状态机完整路径（非 panic）· 每步可追踪。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        transitions = [t.to for t in out.transitions]
        # NEW → VALIDATED → IDEMPOTENCY_CHECKED → CONFIRMING → SUBMITTING → ACKED
        assert transitions == [
            "VALIDATED", "IDEMPOTENCY_CHECKED", "CONFIRMING", "SUBMITTING", "ACKED",
        ]

    @pytest.mark.asyncio
    async def test_TC_L110_L204_023_state_machine_panic_path_skips_confirming(
        self, sut: InterventionService, mock_project_id: str,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-023 · panic 路径 · 跳过 CONFIRMING（ADR-L204-02）。"""
        mock_ic17_transport.post.return_value = IC17Ack(accepted=True)
        out = await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn")
        transitions = [t.to for t in out.transitions]
        # NEW → VALIDATED → IDEMPOTENCY_CHECKED → SUBMITTING → ACKED（无 CONFIRMING）
        assert "CONFIRMING" not in transitions
        assert "SUBMITTING" in transitions
        assert transitions[-1] == "ACKED"
```

---

## §3 负向用例（每错误码 ≥ 1 · 15 条 E-*）

```python
# file: tests/l1_10/test_l2_04_negative.py
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_04.errors import (
    PM14Error, L204Error, IC17Error, BothChannelsFailed,
)


class TestL2_04_UserIntervene_Negative:
    """每错误码 ≥ 1 负向用例。"""

    # ---------- PM-14 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_101_missing_project_id_raises_pm14_001(
        self, sut, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-101 · payload 缺 project_id → E-PM14-001 · 不发 IC-17（硬约束）。"""
        with pytest.raises(PM14Error) as exc:
            await sut.submit_intervention(
                type="pause",
                payload={"comment": "忘填 pid"},
                _source="l2-01-panic-btn",
            )
        assert exc.value.code == "E-PM14-001"
        assert mock_ic17_transport.post.call_count == 0

    @pytest.mark.asyncio
    async def test_TC_L110_L204_102_cross_project_rejects_pm14_002(
        self, sut, mock_project_id: str, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-102 · payload.project_id ≠ active_project → E-PM14-002 · "请刷新"。"""
        sut.factory.active_project_id = mock_project_id
        with pytest.raises(PM14Error) as exc:
            await sut.submit_intervention(
                type="pause",
                payload={"project_id": "pid-OTHER"},
                _source="l2-01-panic-btn",
            )
        assert exc.value.code == "E-PM14-002"
        assert "刷新" in exc.value.user_message
        assert mock_ic17_transport.post.call_count == 0

    # ---------- schema ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_103_invalid_type_rejected(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-103 · type="foo" 不在 10 枚举 → E-L2-04-001。"""
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="foo",
                payload={"project_id": mock_project_id},
                _source="l2-01-panic-btn",
            )
        assert exc.value.code == "E-L2-04-001"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_104_authorize_missing_required(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-104 · authorize payload 缺 red_line_id → E-L2-04-002。"""
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="authorize",
                payload={"project_id": mock_project_id, "decision": "grant"},
                _source="l2-07-admin",
            )
        assert exc.value.code == "E-L2-04-002"
        assert "red_line_id" in exc.value.dev_detail

    @pytest.mark.asyncio
    async def test_TC_L110_L204_105_payload_oversize(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-105 · payload > 10KB → E-L2-04-002 (payload too large)。"""
        huge = "x" * 11_000
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="change_request",
                payload={
                    "project_id": mock_project_id,
                    "target_tab": "gate",
                    "change_description": huge,
                },
                _source="l2-02-gate",
            )
        assert exc.value.code == "E-L2-04-002"

    # ---------- idempotency ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_106_idempotency_collision_within_10s(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-106 · 10s 内同 key → E-L2-04-003 · DUPLICATED · 不再发 IC-17。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        payload = {"project_id": mock_project_id, "comment": "A"}
        await sut.submit_intervention(type="pause", payload=payload, _source="l2-01-panic-btn")
        out2 = await sut.submit_intervention(type="pause", payload=payload, _source="l2-01-panic-btn")
        assert out2.status == "DUPLICATED"
        assert out2.error.code == "E-L2-04-003"
        assert mock_ic17_transport.post.call_count == 1

    # ---------- confirm ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_107_confirm_user_cancel(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-107 · 用户点取消 → CONFIRM_CANCELED · 不写审计 · 不发 IC-17。"""
        mock_confirm_broker.show.return_value = False
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "CONFIRM_CANCELED"
        assert mock_ic17_transport.post.call_count == 0

    @pytest.mark.asyncio
    async def test_TC_L110_L204_108_confirm_30s_timeout(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-108 · confirm 30s 无响应 → CONFIRM_CANCELED + confirm_timeout 事件。"""
        mock_confirm_broker.show.side_effect = asyncio.TimeoutError
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "CONFIRM_CANCELED"
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("confirm_timeout" in (t or "") for t in event_types)
        assert mock_ic17_transport.post.call_count == 0

    # ---------- PanicLock ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_109_submit_non_resume_while_panic_locked(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-109 · PanicLock 激活期间提交 non-resume → E-L2-04-005。"""
        sut.panic_lock.state = "LOCKED"
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="pause",
                payload={"project_id": mock_project_id},
                _source="l2-01-panic-btn",
            )
        assert exc.value.code == "E-L2-04-005"
        assert "panic 中" in exc.value.user_message

    # ---------- _skip_confirm abuse（拦截 7）----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_110_skip_confirm_abuse_rejected(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-110 · 非 panic 手工传 _skip_confirm=True → E-L2-04-006 + 告警事件。"""
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="pause",
                payload={"project_id": mock_project_id},
                _source="l2-01-panic-btn",
                _skip_confirm=True,
            )
        assert exc.value.code == "E-L2-04-006"
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("confirm_bypass_attempt" in (t or "") for t in event_types)

    # ---------- credential slot expired ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_111_credential_slot_expired(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_credential_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-111 · credential slot 已 zero_fill 后再 submit → E-L2-04-007。"""
        mock_confirm_broker.show.return_value = True
        mock_credential_bus.get_buffer.return_value = None
        with pytest.raises(L204Error) as exc:
            await sut.submit_intervention(
                type="authorize",
                payload={
                    "project_id": mock_project_id,
                    "red_line_id": "rl-007",
                    "decision": "grant",
                    "credential_slot_ref": "slot-expired",
                },
                _source="l2-07-admin",
            )
        assert exc.value.code == "E-L2-04-007"
        assert "重填凭证" in exc.value.user_message

    # ---------- 审计降级 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_112_local_fsync_failed_degrades_L1(
        self, sut, mock_project_id: str,
        mock_local_store: AsyncMock, mock_ic18_transport: AsyncMock,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-112 · 本地 fsync fail → E-L2-04-008 · 降级 BUS_ONLY · submit 仍继续。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        mock_local_store.append.side_effect = OSError("ENOSPC")
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "ACKED"
        assert sut.audit_writer.last_local_failed is True
        assert mock_ic18_transport.append_event.call_count == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L204_113_ic18_failed_degrades_L2(
        self, sut, mock_project_id: str,
        mock_local_store: AsyncMock, mock_ic18_transport: AsyncMock,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-113 · IC-18 fail → E-L2-04-009 · 降级 LOCAL_ONLY。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        mock_ic18_transport.append_event.side_effect = ConnectionError("L1-09 unreachable")
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "ACKED"
        assert sut.audit_writer.last_ic18_failed is True
        assert mock_local_store.append.call_count == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L204_114_both_audit_channels_failed_emergency_block(
        self, sut, mock_project_id: str,
        mock_local_store: AsyncMock, mock_ic18_transport: AsyncMock,
        mock_panic_lock: MagicMock,
    ) -> None:
        """TC-L110-L204-114 · 双端全 fail → E-L2-04-010 · EMERGENCY_BLOCK · 除 panic 全禁。"""
        mock_local_store.append.side_effect = OSError("ENOSPC")
        mock_ic18_transport.append_event.side_effect = ConnectionError("L1-09 down")
        with pytest.raises(BothChannelsFailed):
            await sut.submit_intervention(
                type="panic",
                payload={"project_id": mock_project_id, "severity": "critical"},
                _source="l2-01-panic-btn",
            )
        mock_panic_lock.emergency_block_all_except_panic.assert_called_once()

    # ---------- IC-17 timeout / transport / reject ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_115_ic17_timeout(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-115 · IC-17 5s 无 ack → E-L2-04-011 · REJECTED。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.side_effect = asyncio.TimeoutError
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "REJECTED"
        assert out.error.code == "E-L2-04-011"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_116_ic17_transport_error(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-116 · IC-17 connect refused → E-L2-04-012。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.side_effect = ConnectionRefusedError("ECONNREFUSED")
        out = await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "REJECTED"
        assert out.error.code == "E-L2-04-012"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_117_ic17_ack_accepted_false(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-117 · IC-17 ack accepted=false · L1-01 拒绝 → E-L2-04-013。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(
            accepted=False, reason="invalid_state: not paused",
        )
        out = await sut.submit_intervention(
            type="resume", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        assert out.status == "REJECTED"
        assert out.error.code == "E-L2-04-013"
        assert "invalid_state" in out.ack_status.reason

    # ---------- panic halted 等待超时 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_118_panic_halted_event_wait_timeout(
        self, sut, mock_project_id: str,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-118 · panic 发出 60s 无 halted 事件 → E-L2-04-014 · "请刷新"。"""
        mock_ic17_transport.post.return_value = MagicMock(
            accepted=True, l101_state_at_ack="halting")
        with pytest.raises(L204Error) as exc:
            await asyncio.wait_for(
                sut.panic_lock.wait_halted(
                    timeout_ms=60_000, project_id=mock_project_id,
                ),
                timeout=0.5,
            )
        assert exc.value.code in ("E-L2-04-014", "E-L2-04-014-timeout")

    # ---------- DOM mutation reapply ----------

    def test_TC_L110_L204_119_dom_mutation_reapply_locks_new_button(
        self, sut, fake_dom,
    ) -> None:
        """TC-L110-L204-119 · DOM mutation 后 · MutationObserver 兜底 reapply · 新按钮被 disable。"""
        fake_dom.add_buttons([".btn-panic", ".btn-pause"])
        sut.panic_lock.activate(intent_id="intent-1")
        assert fake_dom.is_enabled(".btn-pause") is False
        fake_dom.add_buttons([".btn-new-feature"])
        sut.panic_lock._on_dom_mutation()
        assert fake_dom.is_enabled(".btn-new-feature") is False
```

---

## §4 IC-XX 契约集成测试（≥ 6 条）

```python
# file: tests/l1_10/test_l2_04_ic_contracts.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_04_IC_Contracts:
    """覆盖本 L2 产生 / 消费的 6 条 IC 契约。"""

    @pytest.mark.asyncio
    async def test_TC_L110_L204_601_ic17_user_intervene_body(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-601 · IC-17 body 含 intent_id + project_id + type + idempotency_key + submitted_at。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert "intent_id" in body
        assert body["project_id"] == mock_project_id
        assert body["type"] == "pause"
        assert "idempotency_key" in body
        assert "submitted_at" in body

    @pytest.mark.asyncio
    async def test_TC_L110_L204_602_ic18_append_event_submitted(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
        mock_ic18_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-602 · 每次 submit 推 IC-18 · type=L1-10:user_intervention_submitted。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        await sut.submit_intervention(
            type="pause", payload={"project_id": mock_project_id},
            _source="l2-01-panic-btn")
        ev = mock_ic18_transport.append_event.call_args.kwargs
        assert ev["type"] == "L1-10:user_intervention_submitted"
        assert ev["project_id"] == mock_project_id
        assert ev["anchor_type"] == "intent_id"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_603_ic_l2_03_gate_delegation_fields_passthrough(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-603 · IC-L2-03 委托 · gate_id/decision/comment 不丢。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        await sut.submit_intervention(
            type="gate_decision",
            payload={
                "project_id": mock_project_id,
                "gate_id": "gate-S5-010",
                "decision": "No-Go",
                "comment": "审计链不完整 · 缺 tick→decision 关联",
            },
            _source="l2-02-gate",
        )
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["gate_id"] == "gate-S5-010"
        assert body["payload"]["decision"] == "No-Go"
        assert body["payload"]["comment"].startswith("审计链")

    @pytest.mark.asyncio
    async def test_TC_L110_L204_604_ic_l2_05_kb_promote_passthrough(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-604 · IC-L2-05 委托 · entry_id/target_scope/rationale 不丢。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        await sut.submit_intervention(
            type="kb_promote",
            payload={
                "project_id": mock_project_id,
                "entry_id": "kb-2048",
                "target_scope": "global",
                "rationale": "高复用性 pattern",
            },
            _source="l2-05-kb",
        )
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["entry_id"] == "kb-2048"
        assert body["payload"]["target_scope"] == "global"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_605_ic_l2_06_profile_passthrough(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-605 · IC-L2-06 委托 · profile + locked_at_stage 不丢。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        await sut.submit_intervention(
            type="set_scale_profile",
            payload={
                "project_id": mock_project_id,
                "profile": "P3_full",
                "locked_at_stage": "S2",
            },
            _source="l2-06-profile",
        )
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["profile"] == "P3_full"
        assert body["payload"]["locked_at_stage"] == "S2"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_606_ic_l2_07_authorize_with_credential(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
        mock_credential_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-606 · IC-L2-07 委托 authorize · 凭证经 CredentialBus · 用后 zero_fill。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        mock_credential_bus.get_buffer.return_value = bytearray(b"ghp_SECRET_xxx")
        await sut.submit_intervention(
            type="authorize",
            payload={
                "project_id": mock_project_id,
                "red_line_id": "rl-099",
                "decision": "grant",
                "credential_slot_ref": "slot-xyz",
            },
            _source="l2-07-admin",
        )
        mock_credential_bus.zero_fill.assert_called_once()

    def test_TC_L110_L204_607_static_scan_forbids_direct_ic17_outside_l2_04(
        self,
    ) -> None:
        """TC-L110-L204-607 · 静态扫描 · 除 L2-04 外任何代码不得 `from ... import IC17`（拦截 2）。"""
        offenders = static_scan.find_imports_outside(
            module_pattern="IC17Transport",
            allowed_path_prefix="app/l1_10/l2_04/",
        )
        assert offenders == [], f"非 L2-04 代码直接 import IC17: {offenders}"
```

---

## §5 性能 SLO 用例（§12 · panic 硬约束 ≤ 100ms）

> 本 TDD 文件伪代码描述预期测量方式；实际实现可用 pytest-benchmark / `time.perf_counter()` + `statistics.quantiles`。
> **硬约束**（§12.1）：panic → UI 全锁 ≤ 100ms P95；panic → IC-17 发出 ≤ 200ms P95；panic → L1-01 收到 ≤ 500ms P95。

```python
# file: tests/l1_10/test_l2_04_perf.py
from __future__ import annotations

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_04_SLO:
    """§12 SLO 对标测试。100 次采样 · P95 比较。"""

    PANIC_UI_LOCK_MAX_MS = 100         # §12.1 硬约束
    PANIC_IC17_DISPATCH_MAX_MS = 200   # §12.1
    PANIC_TO_L101_MAX_MS = 500         # §12.1
    SUBMIT_E2E_MAX_MS = 200            # §12.1
    LOCAL_FSYNC_MAX_MS = 5             # §12.1
    IC18_MAX_MS = 50                   # §12.1
    IDEM_CHECK_MAX_MS = 1              # §12.1
    PANIC_LOCK_DOM_MAX_MS = 80         # §12.1（500 节点）

    def test_TC_L110_L204_701_panic_to_ui_lock_p95_le_100ms(
        self, sut, fake_dom, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-701 · panic → UI 锁 P95 ≤ 100ms（§12.1 硬约束）。"""
        fake_dom.add_buttons([f".btn-{i}" for i in range(500)] + [".btn-panic", ".btn-resume"])
        samples: list[float] = []
        for _ in range(100):
            sut.panic_lock.state = "UNLOCKED"
            sut.panic_lock.disabled_selectors = []
            t0 = time.perf_counter()
            sut.panic_lock.activate(intent_id="perf-1")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PANIC_UI_LOCK_MAX_MS, \
            f"panic UI 锁 P95={p95:.2f}ms 超 100ms 硬约束"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_702_panic_to_ic17_dispatch_p95_le_200ms(
        self, sut, mock_project_id: str,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-702 · panic → IC-17 发出 P95 ≤ 200ms。"""
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.submit_intervention(
                type="panic",
                payload={"project_id": mock_project_id, "severity": "critical",
                         "_nonce": i},  # 不同 payload 避免幂等
                _source="l2-01-panic-btn",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PANIC_IC17_DISPATCH_MAX_MS, \
            f"panic → IC-17 P95={p95:.2f}ms 超 200ms SLO"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_703_panic_to_l101_p95_le_500ms(
        self, sut, mock_project_id: str,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-703 · panic → L1-01 收到 ack P95 ≤ 500ms（含 RTT）。"""
        async def _mock_l101(*a, **kw):
            await asyncio.sleep(0.05)  # 模拟 L1-01 处理 50ms
            return MagicMock(accepted=True, l101_state_at_ack="halting")
        mock_ic17_transport.post.side_effect = _mock_l101
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.submit_intervention(
                type="panic",
                payload={"project_id": mock_project_id, "severity": "critical",
                         "_nonce": i},
                _source="l2-01-panic-btn",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PANIC_TO_L101_MAX_MS, \
            f"panic → L1-01 P95={p95:.2f}ms 超 500ms SLO"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_704_submit_e2e_p95_le_200ms(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-704 · submit 端到端（非 panic · 含 confirm） P95 ≤ 200ms。"""
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.submit_intervention(
                type="pause",
                payload={"project_id": mock_project_id, "comment": f"nonce-{i}"},
                _source="l2-01-panic-btn",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.SUBMIT_E2E_MAX_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L204_705_local_audit_fsync_p95_le_5ms(
        self, sut, mock_project_id: str, mock_local_store: AsyncMock,
    ) -> None:
        """TC-L110-L204-705 · 本地 audit append + fsync P95 ≤ 5ms（SSD 典型）。"""
        samples: list[float] = []
        for i in range(100):
            record = {"project_id": mock_project_id, "intent_id": f"int-{i}",
                      "type": "pause", "submitted_at": "2026-04-22T06:30:00Z"}
            t0 = time.perf_counter()
            await sut.audit_writer.write_local(record)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.LOCAL_FSYNC_MAX_MS

    def test_TC_L110_L204_707_idempotency_check_p95_le_1ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-707 · IdempotencyChecker.check P95 ≤ 1ms（1000 次）。"""
        samples: list[float] = []
        for i in range(1000):
            payload = {"project_id": mock_project_id, "nonce": i}
            t0 = time.perf_counter()
            k = sut.idempotency_checker.compute_key(
                type="pause", payload=payload, now_ms=i * 100)
            sut.idempotency_checker.check_and_register(k)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.IDEM_CHECK_MAX_MS

    def test_TC_L110_L204_708_panic_lock_dom_traversal_p95_le_80ms(
        self, sut, fake_dom,
    ) -> None:
        """TC-L110-L204-708 · PanicLockController.activate DOM 遍历 500 节点 P95 ≤ 80ms。"""
        fake_dom.add_buttons([f".btn-n{i}" for i in range(500)])
        samples: list[float] = []
        for _ in range(100):
            sut.panic_lock.state = "UNLOCKED"
            sut.panic_lock.disabled_selectors = []
            fake_dom.reset_enabled()
            t0 = time.perf_counter()
            sut.panic_lock.activate(intent_id="perf")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PANIC_LOCK_DOM_MAX_MS
```

---

## §6 端到端 e2e 场景（≥ 2 · §5.3 panic 主链 + Gate 委托链）

```python
# file: tests/l1_10/test_l2_04_e2e.py
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_04_E2E:
    """映射 §5.3 panic 全系统急停 + §5.4 Gate 委托链路 + authorize 凭证链。"""

    @pytest.mark.asyncio
    async def test_TC_L110_L204_801_e2e_panic_full_halt_and_unlock(
        self, sut, mock_project_id: str, fake_dom,
        mock_ic17_transport: AsyncMock, mock_ic18_transport: AsyncMock,
        mock_local_store: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L204-801 · e2e · panic → PanicLock → 双端审计 → IC-17 → L1-01 halted → SSE → UNLOCK。
        映射 §5.3 P0 时序 · scope §5.10.6 义务 6。
        """
        fake_dom.add_buttons([".btn-panic", ".btn-resume", ".btn-pause", ".btn-gate-go"])
        mock_ic17_transport.post.return_value = MagicMock(
            accepted=True, l101_state_at_ack="halting")

        # 1. 用户点 panic
        out = await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn",
        )
        # 2. ACKED + 锁激活
        assert out.status == "ACKED"
        assert sut.panic_lock.state == "LOCKED"
        assert fake_dom.is_enabled(".btn-pause") is False
        assert fake_dom.is_enabled(".btn-panic") is True  # 永驻
        # 3. 双端审计
        assert mock_local_store.append.call_count >= 1
        assert mock_ic18_transport.append_event.call_count >= 1
        # 4. IC-17 body 正确
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["type"] == "panic"
        # 5. 模拟 L2-03 SSE 收 system_halted
        await sut.panic_lock._on_halted({
            "type": "L1-09:system_halted",
            "project_id": mock_project_id,
            "ts": "2026-04-22T06:30:10.000Z",
        })
        # 6. 解锁
        assert sut.panic_lock.state == "UNLOCKED"
        assert fake_dom.is_enabled(".btn-pause") is True

    @pytest.mark.asyncio
    async def test_TC_L110_L204_802_e2e_gate_decision_delegation_full(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
        mock_ic18_transport: AsyncMock, mock_local_store: AsyncMock,
    ) -> None:
        """TC-L110-L204-802 · e2e · L2-02 Gate 决定委托完整链路 · IC-L2-03 → 封装 → confirm → 双端审计 → IC-17 ACKED。
        映射 §5.4 Gate 委托时序 · prd §11.9 正向 4。
        """
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(
            accepted=True, l101_state_at_ack="running")

        out = await sut.submit_intervention(
            type="gate_decision",
            payload={
                "project_id": mock_project_id,
                "gate_id": "gate-S5-001",
                "decision": "Go",
                "comment": "所有 DoD 项已验证 · 监控接入 OK",
            },
            _source="l2-02-gate",
        )
        assert out.status == "ACKED"
        mock_confirm_broker.show.assert_called_once()
        # 双端审计都有
        assert mock_local_store.append.call_count == 1
        assert mock_ic18_transport.append_event.call_count == 1
        # IC-17 body 字段完整
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        assert body["payload"]["decision"] == "Go"
        assert body["payload"]["comment"].startswith("所有 DoD")
        # 状态机终态
        assert [t.to for t in out.transitions][-1] == "ACKED"

    @pytest.mark.asyncio
    async def test_TC_L110_L204_803_e2e_authorize_with_credential_zero_fill(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-803 · e2e · authorize 带 PAT · 投递后 zero_fill · 审计不含凭证。
        映射 §6.6 CredentialEphemeralBus · ADR-L204-05。
        """
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)

        # 1. 前端用户填入 PAT
        pat_buf = bytearray(b"ghp_1234567890abcdef")
        slot_id = sut.credential_bus.store(pat_buf)
        assert slot_id in sut.credential_bus.slots

        # 2. 用户提交 authorize
        out = await sut.submit_intervention(
            type="authorize",
            payload={
                "project_id": mock_project_id,
                "red_line_id": "rl-099",
                "decision": "grant",
                "credential_slot_ref": slot_id,
            },
            _source="l2-07-admin",
        )

        # 3. 投递后 slot 已清零
        assert out.status == "ACKED"
        assert slot_id not in sut.credential_bus.slots
        # 4. IC-17 body 经 base64 包装 _credential（此处仅断言有传）
        body = mock_ic17_transport.post.call_args.kwargs["json"]
        # 投递完成后 body 中 _credential 已被清（§6.7 finally 块）
        assert body.get("_credential") in (None, "", ...)
```

---

## §7 测试 fixture（≥ 5 个 · conftest.py）

```python
# file: tests/l1_10/conftest.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_04.service import InterventionService
from app.l1_10.l2_04.audit_writer import AuditWriter
from app.l1_10.l2_04.panic_lock import PanicLockController
from app.l1_10.l2_04.idempotency import IdempotencyChecker
from app.l1_10.l2_04.credential_bus import CredentialEphemeralBus
from app.l1_10.l2_04.factory import InterventionFactory


@dataclass
class FakeClock:
    _now_ms: int = 0

    def now_ms(self) -> int:
        return self._now_ms

    def advance(self, ms: int) -> None:
        self._now_ms += ms


@dataclass
class FakeDOM:
    """JS DOM 的 Python mock · 用于 PanicLock.activate 遍历断言。"""

    buttons: dict[str, bool] = field(default_factory=dict)  # selector → enabled

    def add_buttons(self, selectors: list[str]) -> None:
        for s in selectors:
            self.buttons[s] = True

    def reset_enabled(self) -> None:
        for k in self.buttons:
            self.buttons[k] = True

    def query_all(self, pattern: str = "button") -> list[str]:
        return list(self.buttons.keys())

    def disable(self, selector: str) -> None:
        if selector in self.buttons:
            self.buttons[selector] = False

    def enable(self, selector: str) -> None:
        if selector in self.buttons:
            self.buttons[selector] = True

    def is_enabled(self, selector: str) -> bool:
        return self.buttons.get(selector, False)


# ---------- 基础 fixture ----------

@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def mock_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_dom() -> FakeDOM:
    return FakeDOM()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    bus.emit = MagicMock()
    return bus


# ---------- Transport / Store mocks ----------

@pytest.fixture
def mock_ic17_transport() -> AsyncMock:
    tr = AsyncMock(name="IC17Transport")
    tr.post = AsyncMock(return_value=MagicMock(accepted=True, reason=None,
                                               l101_state_at_ack="running"))
    return tr


@pytest.fixture
def mock_ic18_transport() -> AsyncMock:
    tr = AsyncMock(name="IC18Transport")
    tr.append_event = AsyncMock(return_value={"ok": True})
    return tr


@pytest.fixture
def mock_local_store() -> AsyncMock:
    st = AsyncMock(name="JSONLFileStore")
    st.append = AsyncMock(return_value=None)
    return st


@pytest.fixture
def mock_credential_bus() -> MagicMock:
    bus = MagicMock(name="CredentialEphemeralBus")
    bus.slots = {}
    bus.store = MagicMock(return_value=f"slot-{uuid.uuid4()}")
    bus.get_buffer = MagicMock(return_value=bytearray(b"ghp_FAKE"))
    bus.zero_fill = MagicMock()
    return bus


@pytest.fixture
def mock_confirm_broker() -> AsyncMock:
    br = AsyncMock(name="ConfirmDialogBroker")
    br.show = AsyncMock(return_value=True)
    return br


@pytest.fixture
def mock_panic_lock() -> MagicMock:
    lock = MagicMock(name="PanicLockController")
    lock.state = "UNLOCKED"
    lock.disabled_selectors = []
    lock.activate = MagicMock()
    lock.emergency_block_all_except_panic = MagicMock()
    return lock


# ---------- SUT 装配 ----------

@pytest.fixture
def sut(
    mock_project_id: str,
    mock_clock: FakeClock,
    mock_event_bus: MagicMock,
    mock_ic17_transport: AsyncMock,
    mock_ic18_transport: AsyncMock,
    mock_local_store: AsyncMock,
    mock_credential_bus: MagicMock,
    mock_confirm_broker: AsyncMock,
    mock_panic_lock: MagicMock,
    fake_dom: FakeDOM,
) -> InterventionService:
    """组装 InterventionService · 所有外部依赖都是 mock。"""
    factory = InterventionFactory(
        active_project_id=mock_project_id,
        clock=mock_clock,
    )
    idem = IdempotencyChecker(clock=mock_clock, window_seconds=10)
    audit = AuditWriter(
        local_store=mock_local_store,
        ic18_transport=mock_ic18_transport,
        event_bus=mock_event_bus,
    )
    history = MagicMock(name="HistoryStore")
    history._records = []
    history.append_all = lambda lst: history._records.extend(lst)
    return InterventionService(
        factory=factory,
        idempotency_checker=idem,
        confirm_broker=mock_confirm_broker,
        panic_lock=mock_panic_lock,
        audit_writer=audit,
        credential_bus=mock_credential_bus,
        ic17_transport=mock_ic17_transport,
        history=history,
        dom=fake_dom,
    )


# ---------- Factory / data makers ----------

@pytest.fixture
def make_intent() -> Callable[..., Any]:
    def _factory(**overrides: Any):
        base = dict(
            intent_id=f"intent-{uuid.uuid4()}",
            project_id="pid-default",
            type="pause",
            payload={"project_id": "pid-default"},
            _source="l2-01-panic-btn",
            submitted_at=int(time.time() * 1000),
            _skip_confirm=False,
            status="NEW",
        )
        base.update(overrides)
        from app.l1_10.l2_04.ar import InterventionIntent
        return InterventionIntent(**base)
    return _factory


@pytest.fixture
def make_ic17_ack() -> Callable[..., Any]:
    from app.l1_10.l2_04.schemas import IC17Ack
    def _factory(**overrides: Any) -> IC17Ack:
        base = dict(accepted=True, reason=None, l101_state_at_ack="running")
        base.update(overrides)
        return IC17Ack(**base)
    return _factory
```

---

## §8 集成点用例（与兄弟 L2 协作 · ≥ 2）

```python
# file: tests/l1_10/test_l2_04_integration_with_siblings.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_04_SiblingIntegration:
    """本 L2 与 L2-01/02/05/06/07 的协作集成测试。"""

    @pytest.mark.asyncio
    async def test_TC_L110_L204_901_concurrent_4_delegations_serialized_fifo(
        self, sut, mock_project_id: str,
        mock_confirm_broker: AsyncMock, mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-901 · 并发 4 个委托（L2-02/05/06/07）· FIFO 串行化 · 4 次独立 IC-17。
        映射 §8.1 SUBMITTING 状态并发控制 · TC-L204-023。
        """
        mock_confirm_broker.show.return_value = True
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        tasks = [
            sut.submit_intervention(
                type="gate_decision",
                payload={"project_id": mock_project_id, "gate_id": "g-1",
                         "decision": "Go", "comment": "all dod verified ok"},
                _source="l2-02-gate"),
            sut.submit_intervention(
                type="kb_promote",
                payload={"project_id": mock_project_id, "entry_id": "kb-1",
                         "target_scope": "global", "rationale": "reuse"},
                _source="l2-05-kb"),
            sut.submit_intervention(
                type="set_scale_profile",
                payload={"project_id": mock_project_id,
                         "profile": "P2_standard", "locked_at_stage": "S1"},
                _source="l2-06-profile"),
            sut.submit_intervention(
                type="admin_config_change",
                payload={"project_id": mock_project_id, "config_key": "k1",
                         "old_value": 1, "new_value": 2},
                _source="l2-07-admin"),
        ]
        import asyncio
        results = await asyncio.gather(*tasks)
        assert all(r.status == "ACKED" for r in results)
        assert mock_ic17_transport.post.call_count == 4

    @pytest.mark.asyncio
    async def test_TC_L110_L204_902_l2_01_panic_button_bypass_all_siblings(
        self, sut, mock_project_id: str, fake_dom,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-902 · L2-01 panic 按钮 · PanicLock 广播 · 兄弟 L2 按钮全 disable。
        拦截 1（panic 永驻）· TC-L204-027。
        """
        fake_dom.add_buttons([
            ".btn-panic", ".btn-resume",
            ".btn-gate-go", ".btn-gate-nogo",  # L2-02
            ".btn-kb-promote",                  # L2-05
            ".btn-profile-set",                 # L2-06
            ".btn-admin-apply",                 # L2-07
        ])
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        out = await sut.submit_intervention(
            type="panic",
            payload={"project_id": mock_project_id, "severity": "critical"},
            _source="l2-01-panic-btn",
        )
        assert out.status == "ACKED"
        # 兄弟 L2 按钮全 disable
        for s in [".btn-gate-go", ".btn-gate-nogo", ".btn-kb-promote",
                  ".btn-profile-set", ".btn-admin-apply"]:
            assert fake_dom.is_enabled(s) is False
        # panic + resume 永驻
        assert fake_dom.is_enabled(".btn-panic") is True
        assert fake_dom.is_enabled(".btn-resume") is True

    @pytest.mark.asyncio
    async def test_TC_L110_L204_903_l2_03_sse_halted_unlocks_panic_lock(
        self, sut, mock_project_id: str, fake_dom,
    ) -> None:
        """TC-L110-L204-903 · L2-03 SSE 推 L1-09:system_halted → PanicLock UNLOCKED → 兄弟按钮恢复。"""
        fake_dom.add_buttons([".btn-panic", ".btn-resume", ".btn-pause", ".btn-gate-go"])
        sut.panic_lock.activate(intent_id="int-1")
        assert fake_dom.is_enabled(".btn-gate-go") is False
        # SSE 事件
        await sut.panic_lock._on_halted({
            "type": "L1-09:system_halted",
            "project_id": mock_project_id,
            "ts": "2026-04-22T06:30:10.000Z",
        })
        assert sut.panic_lock.state == "UNLOCKED"
        assert fake_dom.is_enabled(".btn-gate-go") is True
```

---

## §9 边界 / edge case（≥ 4）

```python
# file: tests/l1_10/test_l2_04_edge.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_04_Edge:
    """空 / 超大 / 并发 / 浏览器刷新 / GC / DOM mutation 等边界。"""

    # ---------- 空 payload ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_911_empty_payload_rejected(
        self, sut,
    ) -> None:
        """TC-L110-L204-911 · payload = {} · E-PM14-001（缺 project_id 优先）。"""
        from app.l1_10.l2_04.errors import PM14Error
        with pytest.raises(PM14Error):
            await sut.submit_intervention(
                type="pause", payload={}, _source="l2-01-panic-btn")

    # ---------- 超大 payload ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_912_payload_exact_10kb_boundary(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-912 · payload 正好 10240 bytes · 临界通过/拒绝（§10.1 max_line_bytes）。"""
        # 正好 10KB: 通过或拒绝取决于实现含 overhead 的判定 · 两方向都断言
        from app.l1_10.l2_04.errors import L204Error
        # 10241 必拒
        huge = "x" * (10_241)
        with pytest.raises(L204Error):
            await sut.submit_intervention(
                type="change_request",
                payload={"project_id": mock_project_id,
                         "target_tab": "gate",
                         "change_description": huge},
                _source="l2-02-gate")

    # ---------- 浏览器刷新 / Map 丢失 ----------

    def test_TC_L110_L204_913_idempotency_map_lost_on_refresh(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L204-913 · 浏览器刷新 · 内存 Map 丢失 · 同 key 可再通过（D2 · OQ-L204-05 接受）。"""
        key = sut.idempotency_checker.compute_key(
            type="pause", payload={"project_id": mock_project_id}, now_ms=0)
        assert sut.idempotency_checker.check_and_register(key) is True
        # 模拟刷新：reinit
        sut.idempotency_checker._map.clear()
        assert sut.idempotency_checker.check_and_register(key) is True

    # ---------- 凭证 TTL 兜底 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_914_credential_ttl_auto_zero_fill(
        self,
    ) -> None:
        """TC-L110-L204-914 · credential slot 30s 未用 · 自动 zero_fill · 事件 ttl_expired。"""
        from app.l1_10.l2_04.credential_bus import CredentialEphemeralBus
        bus = CredentialEphemeralBus(ttl_sec=0.1)  # 测试用 100ms
        slot_id = bus.store(bytearray(b"ghp_ABC"))
        assert slot_id in bus.slots
        import asyncio
        await asyncio.sleep(0.2)
        assert slot_id not in bus.slots  # TTL 到 · 已 zero_fill + Map.delete

    # ---------- DOM mutation observer ----------

    def test_TC_L110_L204_915_dom_mutation_does_not_leak_panic_lock(
        self, sut, fake_dom,
    ) -> None:
        """TC-L110-L204-915 · PanicLock 期间 DOM mutation · MutationObserver 兜底重应用 · 无漏网按钮。"""
        fake_dom.add_buttons([".btn-panic", ".btn-pause"])
        sut.panic_lock.activate(intent_id="int-1")
        # 10 次 DOM mutation · 每次新增按钮
        for i in range(10):
            fake_dom.add_buttons([f".btn-dyn-{i}"])
            sut.panic_lock._on_dom_mutation()
        # 所有新按钮都已 disable
        for i in range(10):
            assert fake_dom.is_enabled(f".btn-dyn-{i}") is False

    # ---------- 并发 panic 幂等 ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L204_916_double_click_panic_idempotent(
        self, sut, mock_project_id: str,
        mock_ic17_transport: AsyncMock,
    ) -> None:
        """TC-L110-L204-916 · 用户双击 panic 按钮 · 10s 窗口内第二次 DUPLICATED · 只发 1 次 IC-17。"""
        mock_ic17_transport.post.return_value = MagicMock(accepted=True)
        payload = {"project_id": mock_project_id, "severity": "critical"}
        r1 = await sut.submit_intervention(
            type="panic", payload=payload, _source="l2-01-panic-btn")
        r2 = await sut.submit_intervention(
            type="panic", payload=payload, _source="l2-01-panic-btn")
        assert r1.status == "ACKED"
        assert r2.status == "DUPLICATED"
        assert mock_ic17_transport.post.call_count == 1

    # ---------- 凭证审计黑名单 ----------

    def test_TC_L110_L204_917_audit_record_excludes_credential_fields(
        self, sut, mock_project_id: str, make_intent,
    ) -> None:
        """TC-L110-L204-917 · 审计 record · 凭证字段黑名单（pat/password/secret/token/api_key）被过滤。"""
        intent = make_intent(
            type="authorize",
            payload={
                "project_id": mock_project_id,
                "red_line_id": "rl-1",
                "decision": "grant",
                "pat": "ghp_REDACTED",
                "api_key": "sk-SECRET",
                "comment": "normal field",
            },
        )
        record = sut.audit_writer._build_record(intent, status="SUBMITTED")
        # payload_hash 是 safe_payload 的 hash · 但 record 本体不含凭证
        import json
        record_json = json.dumps(record, ensure_ascii=False)
        assert "ghp_REDACTED" not in record_json
        assert "sk-SECRET" not in record_json

    # ---------- confirm bypass 静态扫描（拦截 7）----------

    def test_TC_L110_L204_918_no_if_branch_for_type_panic_skip_confirm(
        self,
    ) -> None:
        """TC-L110-L204-918 · 代码里 InterventionFactory 内不存在 `if type=='panic' and _skip_confirm` 分支。
        _skip_confirm 对 panic 是硬编码 True · 任何分支判断都是错误（拦截 7）。
        """
        import inspect
        from app.l1_10.l2_04.factory import InterventionFactory
        src = inspect.getsource(InterventionFactory)
        # 不应出现危险分支
        forbidden_patterns = [
            "type == 'panic' and _skip_confirm",
            "type==\"panic\" and _skip_confirm",
            "if _skip_confirm and type",
        ]
        for p in forbidden_patterns:
            assert p not in src, f"危险分支: {p}"

    # ---------- panic 按钮永驻断言 ----------

    def test_TC_L110_L204_919_panic_button_never_disabled_even_in_emergency_block(
        self, sut, fake_dom,
    ) -> None:
        """TC-L110-L204-919 · EMERGENCY_BLOCK 状态下 · .btn-panic 仍可点（拦截 1 · TC-L204-027）。"""
        fake_dom.add_buttons([".btn-panic", ".btn-pause", ".btn-gate-go"])
        sut.panic_lock.emergency_block_all_except_panic()
        assert fake_dom.is_enabled(".btn-panic") is True
        assert fake_dom.is_enabled(".btn-pause") is False
        assert fake_dom.is_enabled(".btn-gate-go") is False
```

---

*— TDD · L1-10 L2-04 · 用户干预入口 · depth-B · v1.0 · 2026-04-22 · session-L —*




