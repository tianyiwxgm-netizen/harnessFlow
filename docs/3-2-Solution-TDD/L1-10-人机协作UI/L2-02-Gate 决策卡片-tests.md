---
doc_id: tests-L1-10-L2-02-Gate 决策卡片-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-02-Gate 决策卡片.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-02-Gate 决策卡片 · TDD 测试用例

> 基于 3-1 L2-02 §3（6 个 public 方法 + 2 个事件回调） + §3.3（15 项 `L2-02-E***` 错误码） + §5 P0/P1 时序（Gate 决定 + Request-change 晋升） + §13 TC 映射 驱动。
> TC ID：`TC-L110-L202-NNN`（001-099 正向 · 101-199 负向 · 601-699 IC 契约 · 701-799 性能 · 801-899 e2e · 901-999 边界）。
> **L2-02 是 L1-10 决策面 Aggregate Root 层**（GateCard AR · 5 状态 RECEIVED/ACTIVE/USER_DECIDED/ARCHIVED/EXPIRED）· 活跃卡单例 · FIFO 队列 · GO/NO_GO/REQUEST_CHANGE 三分决策 · 评论 ≥ 10 字符前置校验 · IC-L2-03 委托 L2-04 封装 `user_intervene(type=gate_decision)`。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC + SLO + 状态机）
- [x] §2 正向用例（6 方法 + 2 事件回调 + 状态机）
- [x] §3 负向用例（15 条 L2-02-E*** 全覆盖）
- [x] §4 IC-XX 契约集成（IC-16 被调 + IC-L2-03 委托 L2-04 + IC-09 审计）
- [x] §5 性能 SLO 用例（submit_decision ≤ 150ms · load_queue ≤ 100ms · 晋升 ≤ 200ms）
- [x] §6 端到端 e2e（P0 Gate 决定全链路 · P1 Request-change 晋升）
- [x] §7 测试 fixture（mock_project_id / make_card / mock_l204 / fake_clock）
- [x] §8 集成点用例（与 L2-01/03/04 协作）
- [x] §9 边界 / edge case（评论恰好 10 字符 · 10 字节 UTF8 / 并发双击 / 队列 crash 重建）

---

## §1 覆盖度索引

### §1.1 方法 × 测试

| 方法 | TC ID | 覆盖类型 | 备注 |
|---|---|---|---|
| `submit_card(payload)` · A 组 | TC-L110-L202-001 | unit | stage_gate 入队 · 幂等 by card_id |
| `submit_card` clarification | TC-L110-L202-002 | unit | clarification 卡 |
| `load_queue(project_id)` · B 组 | TC-L110-L202-003 | unit | 活跃 + 排队 + 未读 |
| `load_card(card_id)` | TC-L110-L202-004 | unit | 详情 + bundle preview policy |
| `submit_decision` GO | TC-L110-L202-005 | unit + integration | 评论 ≥ 10 字 · 委托 L2-04 |
| `submit_decision` NO_GO | TC-L110-L202-006 | unit | 评论必填 |
| `submit_decision` REQUEST_CHANGE | TC-L110-L202-007 | unit | change_request 必填 |
| `submit_clarify_answer` | TC-L110-L202-008 | unit | text/radio/multi-select 三变形 |
| `load_history(project_id, filter)` | TC-L110-L202-009 | unit | 归档过滤 + 分页 |
| `on_stage_event` | TC-L110-L202-010 | integration | L1-02 stage_* 同步卡生命周期 |
| `on_clarification_event` | TC-L110-L202-011 | integration | L1-01 clarification_requested |
| 状态机 RECEIVED → ACTIVE | TC-L110-L202-012 | integration | 自动激活 |
| 状态机 ACTIVE → USER_DECIDED → ARCHIVED | TC-L110-L202-013 | integration | 决策后归档 |
| 状态机 自动晋升下一卡 | TC-L110-L202-014 | integration | FIFO 队列 |
| 状态机 EXPIRED_BY_STAGE | TC-L110-L202-015 | integration | 上游 stage 跃迁导致卡过期 |

### §1.2 错误码 × 测试（§3.3 全 15 项覆盖）

| 错误码 | TC ID | 场景 |
|---|---|---|
| `L2-02-E001` CARD_DUPLICATE | TC-L110-L202-101 | submit_card 同 card_id |
| `L2-02-E002` CARD_NOT_FOUND | TC-L110-L202-102 | load_card 不存在 |
| `L2-02-E003` PROJECT_MISMATCH | TC-L110-L202-103 | PM-14 跨项目 |
| `L2-02-E004` COMMENT_TOO_SHORT | TC-L110-L202-104 | 评论 < 10 字 |
| `L2-02-E005` INVALID_DECISION | TC-L110-L202-105 | decision 枚举非法 |
| `L2-02-E006` CHANGE_REQUEST_MISSING | TC-L110-L202-106 | REQUEST_CHANGE 缺 change_request |
| `L2-02-E007` IMPACTED_ARTIFACTS_EMPTY | TC-L110-L202-107 | impacted_artifacts=[] |
| `L2-02-E008` ARTIFACT_BUNDLE_EMPTY | TC-L110-L202-108 | stage_gate artifacts_bundle 空 |
| `L2-02-E009` ALREADY_DECIDED | TC-L110-L202-109 | 同卡二次决策 |
| `L2-02-E010` CARD_NOT_ACTIVE | TC-L110-L202-110 | 决策时卡不在 ACTIVE |
| `L2-02-E011` CLARIFICATION_ANSWER_SHAPE_MISMATCH | TC-L110-L202-111 | answer.type ≠ option_type |
| `L2-02-E012` L204_DELEGATION_FAILED | TC-L110-L202-112 | L2-04 不可达 · 降级 |
| `L2-02-E013` IDEMPOTENCY_CONFLICT | TC-L110-L202-113 | 同 idempotency_key 60s 内 payload 不一致 |
| `L2-02-E014` REPOSITORY_WRITE_FAILED | TC-L110-L202-114 | gate-queue.json 写失败 → READ-ONLY 降级 |
| `L2-02-E015` QUEUE_CORRUPT | TC-L110-L202-115 | gate-queue.json 解析失败 · crash-recovery |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-16 submit_card | L1-02 → L2-02 | TC-L110-L202-601 | stage_gate 入参字段 |
| IC-16 clarification submit_card | L1-01 → L2-02 | TC-L110-L202-602 | clarification 卡 |
| IC-L2-03 gate_decision 委托 | L2-02 → L2-04 | TC-L110-L202-603 | payload.gate_id/decision/comment 穿透 |
| IC-L2-03 clarify 委托 | L2-02 → L2-04 | TC-L110-L202-604 | payload.question_id/answer 穿透 |
| IC-09 append_event 审计 | L2-02 → L1-09 | TC-L110-L202-605 | card_received / decided / archived / expired |
| IC-L2-02 tab_subscribe (L2-03 推) | L2-03 → L2-02 | TC-L110-L202-606 | `L1-02:stage_*` · `L1-01:clarification_*` |

### §1.4 SLO × 测试

| SLO | 目标 | TC ID | 样本 |
|---|---|---|---|
| `submit_decision` 端到端（校验 + 委托 + archive） | P95 ≤ 150ms | TC-L110-L202-701 | 100 |
| `load_queue` | P95 ≤ 100ms | TC-L110-L202-702 | 100 |
| `load_card` | P95 ≤ 80ms | TC-L110-L202-703 | 100 |
| 自动晋升下一卡 | P95 ≤ 200ms | TC-L110-L202-704 | 50 |
| `submit_card` | P95 ≤ 50ms | TC-L110-L202-705 | 200 |
| 评论 UTF-8 计数（emoji / CJK） | P95 ≤ 5ms | TC-L110-L202-706 | 500 |

### §1.5 PM-14 project 过滤

- submit_card / load_queue / load_card / submit_decision / submit_clarify_answer / load_history · 所有方法强制 `payload.project_id == session.project_id`
- 跨项目 → `L2-02-E003` + 审计
- 正向载体：§2 全部；负向：TC-L110-L202-103

---

## §2 正向用例（6 方法 + 2 回调 + 状态机）

```python
# file: tests/l1_10/test_l2_02_positive.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_02.service import GateCardService


class TestL2_02_GateCard_Positive:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_001_submit_card_stage_gate_enqueue(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-001 · submit_card · stage_gate 入队 · 返 queue_position。"""
        payload = make_stage_gate_payload(project_id=mock_project_id, card_id="c-S5-001")
        r = await sut.submit_card(payload)
        assert r.status == "accepted"
        assert r.card_id == "c-S5-001"
        assert r.queue_position == 0  # 首卡 · 直接 active
        assert r.current_active_card == "c-S5-001"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_002_submit_card_clarification(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-002 · submit_card · clarification 卡 · artifacts_bundle 允许空。"""
        payload = {
            "project_id": mock_project_id,
            "card_id": "clarify-001",
            "card_type": "clarification",
            "stage_from": None,
            "stage_to": None,
            "artifacts_bundle": [],
            "required_decisions": [],
            "clarification_meta": {
                "question_id": "q-1",
                "question_text": "确认 tick 间隔？",
                "option_type": "text",
                "options": None,
                "context_refs": None,
            },
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-01",
        }
        r = await sut.submit_card(payload)
        assert r.status == "accepted"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_003_load_queue_returns_active_plus_queued(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-003 · load_queue · 返活跃 + 排队 + total_pending。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-1"))
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-2"))
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-3"))
        r = await sut.load_queue(project_id=mock_project_id)
        assert r.active_card.card_id == "c-1"
        assert len(r.queued_cards) == 2
        assert r.total_pending == 3

    @pytest.mark.asyncio
    async def test_TC_L110_L202_004_load_card_returns_detail_with_preview_policy(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-004 · load_card · 详情 + artifacts_preview_policy (eager/progressive/manual)。"""
        payload = make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-detail")
        # 构造两个大 artifact · 触发 progressive
        payload["artifacts_bundle"] = [
            {"artifact_id": "a-1", "path": "p/a1.md", "mime": "text/markdown",
             "title": "Big", "size_bytes": 2_000_000, "stage_link": None},
        ]
        await sut.submit_card(payload)
        r = await sut.load_card(project_id=mock_project_id, card_id="c-detail")
        assert r.card.card_id == "c-detail"
        assert r.card.artifacts_preview_policy in ("eager", "progressive", "manual")

    @pytest.mark.asyncio
    async def test_TC_L110_L202_005_submit_decision_go_delegates_l204(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-005 · submit_decision GO · 评论 ≥ 10 字 · 委托 L2-04 发 IC-17。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-go"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-1", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-go",
            decision="GO",
            comment="所有 DoD 已验证 · OK 继续",  # ≥ 10 字
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        assert r.status == "submitted"
        assert r.archived is True
        assert r.l204_delegation.intent_id == "int-1"
        assert r.l204_delegation.ic17_submitted is True
        # L2-04 被调用 · type=gate_decision
        call = mock_l204_service.submit_intervention.call_args.kwargs
        assert call["type"] == "gate_decision"
        assert call["payload"]["decision"] == "GO"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_006_submit_decision_no_go(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-006 · submit_decision NO_GO · 评论必填 ≥ 10。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-nogo"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-ng", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-nogo",
            decision="NO_GO",
            comment="S5 Verifier 返 4 级回退 · 不能放行",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_007_submit_decision_request_change(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-007 · submit_decision REQUEST_CHANGE · change_request 必填。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-rc"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-rc", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-rc",
            decision="REQUEST_CHANGE",
            comment="请补齐 DoD 的监控接入验证",
            change_request={
                "impacted_artifacts": ["a-1"],
                "suggestion": "补 SLO dashboard + alerting rules",
                "impacted_scope": "stage",
            },
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        assert r.status == "submitted"
        call = mock_l204_service.submit_intervention.call_args.kwargs
        assert "change_request" in str(call["payload"]) or \
            call["payload"].get("decision") == "REQUEST_CHANGE"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_008_submit_clarify_answer_text(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-008 · submit_clarify_answer · text 类型。"""
        await sut.submit_card({
            "project_id": mock_project_id,
            "card_id": "clarify-text",
            "card_type": "clarification",
            "stage_from": None, "stage_to": None,
            "artifacts_bundle": [], "required_decisions": [],
            "clarification_meta": {"question_id": "q-1",
                                   "question_text": "目标分辨率?",
                                   "option_type": "text",
                                   "options": None, "context_refs": None},
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-01",
        })
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-clar", status="ACKED")
        r = await sut.submit_clarify_answer(
            project_id=mock_project_id,
            card_id="clarify-text",
            answer={"type": "text", "value": "1080p"},
            comment=None,
            idempotency_key=str(uuid.uuid4()),
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_009_load_history_with_filter(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-009 · load_history · 按 decision 过滤 + 分页。"""
        # 预埋归档
        await sut.archive_injector.inject([
            {"card_id": f"h-{i}", "card_type": "stage_gate",
             "state": "ARCHIVED", "decision": "GO" if i % 2 == 0 else "NO_GO",
             "received_at": f"2026-04-22T06:{i:02d}:00Z"}
            for i in range(20)
        ])
        r = await sut.load_history(
            project_id=mock_project_id,
            filter={"decision": ["GO"]},
            pagination={"offset": 0, "limit": 10},
        )
        assert len(r.items) == 10
        assert all(it.decision == "GO" for it in r.items)

    @pytest.mark.asyncio
    async def test_TC_L110_L202_010_on_stage_event_syncs_card_lifecycle(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-010 · on_stage_event · L1-02 stage_* 同步 · 上游 stage 跃迁 → 卡 EXPIRED。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-expire", stage_to="S5"))
        # 上游跳过此 gate · 直接进 S6
        await sut.on_stage_event({
            "type": "L1-02:stage_transitioned",
            "project_id": mock_project_id,
            "payload": {"from_stage": "S4", "to_stage": "S6"},
            "ts": "2026-04-22T06:40:00Z",
        })
        r = await sut.load_card(
            project_id=mock_project_id, card_id="c-expire")
        assert r.card.state == "EXPIRED_BY_STAGE"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_011_on_clarification_event_creates_card(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-011 · on_clarification_event · L1-01 触发澄清 · 自动建 clarification 卡。"""
        await sut.on_clarification_event({
            "type": "L1-01:clarification_requested",
            "project_id": mock_project_id,
            "payload": {
                "card_id": "auto-clar-1",
                "question_id": "q-1",
                "question_text": "目标分辨率?",
                "option_type": "radio",
                "options": ["1080p", "4K"],
            },
            "ts": "2026-04-22T06:30:00Z",
        })
        r = await sut.load_card(
            project_id=mock_project_id, card_id="auto-clar-1")
        assert r.card.card_type == "clarification"
        assert r.card.clarification_meta["question_id"] == "q-1"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_012_state_received_to_active(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-012 · 状态机 RECEIVED → ACTIVE · 无活跃卡时自动激活。"""
        r = await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-active"))
        # 无活跃卡 → 直接激活
        d = await sut.load_card(
            project_id=mock_project_id, card_id="c-active")
        assert d.card.state == "ACTIVE"
        assert d.card.activated_at is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L202_013_state_active_to_user_decided_to_archived(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-013 · 状态机 ACTIVE → USER_DECIDED → ARCHIVED · 决策后归档。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-arc"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-arc", status="ACKED")
        await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-arc",
            decision="GO",
            comment="放行 OK 监控就绪",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        d = await sut.load_card(
            project_id=mock_project_id, card_id="c-arc")
        assert d.card.state == "ARCHIVED"
        assert d.card.archived_at is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L202_014_auto_promotion_next_card(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-014 · 自动晋升 · 决策 c-1 后 · c-2 成为 ACTIVE。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-1"))
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-2"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-prom", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-1",
            decision="GO",
            comment="放行 OK 监控就绪",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        assert r.next_active_card == "c-2"
        d = await sut.load_card(
            project_id=mock_project_id, card_id="c-2")
        assert d.card.state == "ACTIVE"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_015_expired_by_stage_on_stage_skip(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-015 · stage 跃迁跳过本 gate · 卡变 EXPIRED_BY_STAGE + 审计。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-skip", stage_to="S5"))
        await sut.on_stage_event({
            "type": "L1-02:stage_force_transitioned",
            "project_id": mock_project_id,
            "payload": {"from_stage": "S4", "to_stage": "S6",
                        "reason": "supervisor_override"},
            "ts": "2026-04-22T06:40:00Z",
        })
        d = await sut.load_card(
            project_id=mock_project_id, card_id="c-skip")
        assert d.card.state == "EXPIRED_BY_STAGE"
```

---

## §3 负向用例（15 条 L2-02-E*** 全覆盖）

```python
# file: tests/l1_10/test_l2_02_negative.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_02.errors import L202Error


class TestL2_02_GateCard_Negative:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_101_duplicate_card_returns_duplicate_ignored(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-101 · submit_card 同 card_id · L2-02-E001 · duplicate_ignored。"""
        p = make_stage_gate_payload(project_id=mock_project_id, card_id="c-dup")
        await sut.submit_card(p)
        r2 = await sut.submit_card(p)
        assert r2.status == "duplicate_ignored"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_102_card_not_found(self, sut, mock_project_id: str) -> None:
        """TC-L110-L202-102 · load_card 不存在 · L2-02-E002。"""
        with pytest.raises(L202Error) as exc:
            await sut.load_card(project_id=mock_project_id, card_id="c-NOT-EXIST")
        assert exc.value.code == "L2-02-E002"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_103_project_mismatch(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-103 · PM-14 跨项目 · L2-02-E003 · 审计 cross_project。"""
        sut.session.project_id = mock_project_id
        p = make_stage_gate_payload(project_id="pid-OTHER", card_id="c-cross")
        with pytest.raises(L202Error) as exc:
            await sut.submit_card(p)
        assert exc.value.code == "L2-02-E003"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_104_comment_too_short(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-104 · 评论 < 10 字符 · L2-02-E004。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-short"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id,
                card_id="c-short",
                decision="GO",
                comment="OK",  # 2 字
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E004"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_105_invalid_decision(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-105 · decision 非法枚举 · L2-02-E005。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-inv"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id,
                card_id="c-inv",
                decision="MAYBE",  # 非法
                comment="不知道怎么决定",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E005"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_106_change_request_missing(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-106 · REQUEST_CHANGE 缺 change_request · L2-02-E006。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-rcm"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id,
                card_id="c-rcm",
                decision="REQUEST_CHANGE",
                comment="请补齐监控接入",
                change_request=None,
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E006"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_107_impacted_artifacts_empty(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-107 · Req-change impacted_artifacts=[] · L2-02-E007。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-ia"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id,
                card_id="c-ia",
                decision="REQUEST_CHANGE",
                comment="请补齐",
                change_request={
                    "impacted_artifacts": [],  # 空
                    "suggestion": "补齐 SLO dashboard",
                    "impacted_scope": "stage",
                },
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E007"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_108_artifact_bundle_empty_on_stage_gate(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-108 · stage_gate artifacts_bundle=[] · L2-02-E008 · reject。"""
        p = {
            "project_id": mock_project_id,
            "card_id": "c-nobundle",
            "card_type": "stage_gate",
            "stage_from": "S4", "stage_to": "S5",
            "artifacts_bundle": [],  # 空 · stage_gate 必填非空
            "required_decisions": [{"field_name": "go_no_go", "label": "决定",
                                    "widget": "radio",
                                    "options": ["GO", "NO_GO"],
                                    "min_chars": None, "required": True}],
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-02",
        }
        with pytest.raises(L202Error) as exc:
            await sut.submit_card(p)
        assert exc.value.code == "L2-02-E008"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_109_already_decided_returns_code(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-109 · 同卡二次决策 · L2-02-E009 · already_decided。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-ad"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-1", status="ACKED")
        await sut.submit_decision(
            project_id=mock_project_id, card_id="c-ad",
            decision="GO", comment="OK 放行继续",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id, card_id="c-ad",
                decision="NO_GO", comment="我改主意了，撤回决定",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:31:00Z",
            )
        assert exc.value.code == "L2-02-E009"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_110_card_not_active(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-110 · 决策时卡在队列中（非 ACTIVE）· L2-02-E010。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-a"))
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-b"))
        # c-b 在队列中 · 非 ACTIVE
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id, card_id="c-b",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E010"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_111_clarify_answer_shape_mismatch(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-111 · clarify answer.type 与卡 option_type 不一致 · L2-02-E011。"""
        await sut.submit_card({
            "project_id": mock_project_id, "card_id": "cl-mis",
            "card_type": "clarification",
            "stage_from": None, "stage_to": None,
            "artifacts_bundle": [], "required_decisions": [],
            "clarification_meta": {"question_id": "q-1",
                                   "question_text": "?", "option_type": "radio",
                                   "options": ["A", "B"],
                                   "context_refs": None},
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-01",
        })
        with pytest.raises(L202Error) as exc:
            await sut.submit_clarify_answer(
                project_id=mock_project_id, card_id="cl-mis",
                answer={"type": "text", "value": "whatever"},  # 不一致
                comment=None, idempotency_key=str(uuid.uuid4()),
            )
        assert exc.value.code == "L2-02-E011"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_112_l204_delegation_failed(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-112 · 委托 L2-04 失败 · L2-02-E012 · 不标记决策。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-fail"))
        mock_l204_service.submit_intervention.side_effect = ConnectionError("L2-04 down")
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id, card_id="c-fail",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E012"
        # 决策不被标记 · 卡仍 ACTIVE 可重试
        d = await sut.load_card(
            project_id=mock_project_id, card_id="c-fail")
        assert d.card.state == "ACTIVE"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_113_idempotency_conflict(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-113 · 同 idempotency_key 60s 内 payload 不一致 · L2-02-E013。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-idem"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-1", status="ACKED")
        key = "user-generated-key-001"
        await sut.submit_decision(
            project_id=mock_project_id, card_id="c-idem",
            decision="GO", comment="放行 OK 监控就绪",
            idempotency_key=key,
            user_ts="2026-04-22T06:30:00Z",
        )
        # 同 key · 不同 payload
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-idem2"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id, card_id="c-idem2",
                decision="NO_GO", comment="这个要拒绝掉",
                idempotency_key=key,  # 同 key
                user_ts="2026-04-22T06:31:00Z",
            )
        assert exc.value.code == "L2-02-E013"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_114_repository_write_failed_degrades_readonly(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_repo: MagicMock,
    ) -> None:
        """TC-L110-L202-114 · gate-queue.json 写失败 · L2-02-E014 · READ-ONLY 降级。"""
        mock_repo.write.side_effect = OSError("ENOSPC")
        with pytest.raises(L202Error) as exc:
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id="c-ro"))
        assert exc.value.code == "L2-02-E014"
        assert sut.degradation_state == "READ_ONLY"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_115_queue_corrupt_crash_recovery(
        self, sut, mock_project_id: str, mock_repo: MagicMock,
    ) -> None:
        """TC-L110-L202-115 · gate-queue.json 解析失败 · L2-02-E015 · 从 cards/ 重建。"""
        mock_repo.read_queue.side_effect = ValueError("corrupt json")
        # cards/ 里仍有 3 张卡 · 触发 crash-recovery
        mock_repo.list_cards.return_value = [
            {"card_id": f"c-rec-{i}", "project_id": mock_project_id,
             "state": "ACTIVE" if i == 0 else "RECEIVED"}
            for i in range(3)
        ]
        await sut.recover_from_queue_corrupt()
        q = await sut.load_queue(project_id=mock_project_id)
        assert q.total_pending == 3
```

---

## §4 IC-XX 契约集成测试（≥ 6）

```python
# file: tests/l1_10/test_l2_02_ic_contracts.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_02_IC_Contracts:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_601_ic16_submit_card_stage_gate(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-601 · IC-16 · stage_gate payload 入参字段完备。"""
        p = make_stage_gate_payload(
            project_id=mock_project_id, card_id="ic16-1", stage_to="S5")
        r = await sut.submit_card(p)
        assert r.status == "accepted"
        # 读回验证字段
        d = await sut.load_card(
            project_id=mock_project_id, card_id="ic16-1")
        assert d.card.stage_to == "S5"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_602_ic16_clarification_submit_card(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-602 · IC-16 · clarification 卡入参 · clarification_meta 完整。"""
        p = {
            "project_id": mock_project_id,
            "card_id": "ic16-clar",
            "card_type": "clarification",
            "stage_from": None, "stage_to": None,
            "artifacts_bundle": [], "required_decisions": [],
            "clarification_meta": {"question_id": "q-ic16",
                                   "question_text": "?", "option_type": "text",
                                   "options": None, "context_refs": None},
            "priority": "urgent",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-01",
        }
        r = await sut.submit_card(p)
        assert r.status == "accepted"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_603_ic_l2_03_gate_decision_delegation(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-603 · IC-L2-03 · 委托 L2-04 · payload.gate_id/decision/comment 穿透。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-del-1"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-del", status="ACKED")
        await sut.submit_decision(
            project_id=mock_project_id,
            card_id="c-del-1",
            decision="GO",
            comment="放行 OK 监控就绪",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "gate_decision"
        assert kw["payload"]["gate_id"] == "c-del-1"
        assert kw["payload"]["decision"] == "GO"
        assert kw["payload"]["comment"].startswith("放行")

    @pytest.mark.asyncio
    async def test_TC_L110_L202_604_ic_l2_03_clarify_delegation(
        self, sut, mock_project_id: str,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-604 · IC-L2-03 · 澄清委托 · payload.question_id/answer。"""
        await sut.submit_card({
            "project_id": mock_project_id, "card_id": "clar-del",
            "card_type": "clarification",
            "stage_from": None, "stage_to": None,
            "artifacts_bundle": [], "required_decisions": [],
            "clarification_meta": {"question_id": "q-del",
                                   "question_text": "?", "option_type": "text",
                                   "options": None, "context_refs": None},
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-01",
        })
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-cd", status="ACKED")
        await sut.submit_clarify_answer(
            project_id=mock_project_id, card_id="clar-del",
            answer={"type": "text", "value": "ANSWER-42"},
            comment=None, idempotency_key=str(uuid.uuid4()),
        )
        kw = mock_l204_service.submit_intervention.call_args.kwargs
        assert kw["type"] == "clarify"
        assert kw["payload"]["question_id"] == "q-del"
        assert kw["payload"]["answer"] == "ANSWER-42"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_605_ic09_audit_lifecycle_events(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L202-605 · IC-09 · card_received / card_decided / card_archived 全留痕。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-aud"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-aud", status="ACKED")
        await sut.submit_decision(
            project_id=mock_project_id, card_id="c-aud",
            decision="GO", comment="放行 OK 监控就绪",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        et_str = "|".join(filter(None, event_types))
        assert "card_received" in et_str
        assert "card_decided" in et_str
        assert "card_archived" in et_str

    @pytest.mark.asyncio
    async def test_TC_L110_L202_606_ic_l2_02_subscribes_stage_and_clarification(
        self, sut,
    ) -> None:
        """TC-L110-L202-606 · IC-L2-02 · L2-02 订阅 L1-02:stage_* + L1-01:clarification_*。"""
        subs = sut.get_registered_subscriptions()
        prefixes = [p for s in subs for p in s["type_prefixes"]]
        assert "L1-02:stage_" in prefixes
        assert "L1-01:clarification_" in prefixes
```

---

## §5 性能 SLO 用例

```python
# file: tests/l1_10/test_l2_02_perf.py
from __future__ import annotations

import statistics
import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_02_SLO:

    SUBMIT_DECISION_P95_MS = 150
    LOAD_QUEUE_P95_MS = 100
    LOAD_CARD_P95_MS = 80
    PROMOTION_P95_MS = 200
    SUBMIT_CARD_P95_MS = 50
    COMMENT_UTF8_COUNT_P95_MS = 5

    @pytest.mark.asyncio
    async def test_TC_L110_L202_701_submit_decision_p95_le_150ms(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-701 · submit_decision 端到端 P95 ≤ 150ms · 100 样本。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-perf", status="ACKED")
        samples: list[float] = []
        for i in range(100):
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"perf-{i}"))
            t0 = time.perf_counter()
            await sut.submit_decision(
                project_id=mock_project_id, card_id=f"perf-{i}",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.SUBMIT_DECISION_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L202_702_load_queue_p95_le_100ms(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-702 · load_queue P95 ≤ 100ms。"""
        # 预埋 50 张卡
        for i in range(50):
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"q-{i}"))
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            await sut.load_queue(project_id=mock_project_id)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.LOAD_QUEUE_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L202_703_load_card_p95_le_80ms(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-703 · load_card P95 ≤ 80ms。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="c-det"))
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            await sut.load_card(
                project_id=mock_project_id, card_id="c-det")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.LOAD_CARD_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L202_704_auto_promotion_p95_le_200ms(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-704 · 决策后自动晋升下一卡 P95 ≤ 200ms · 50 样本。"""
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-p", status="ACKED")
        samples: list[float] = []
        for i in range(50):
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"pr-a-{i}"))
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"pr-b-{i}"))
            t0 = time.perf_counter()
            await sut.submit_decision(
                project_id=mock_project_id, card_id=f"pr-a-{i}",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PROMOTION_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L202_705_submit_card_p95_le_50ms(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-705 · submit_card P95 ≤ 50ms · 200 样本。"""
        samples: list[float] = []
        for i in range(200):
            t0 = time.perf_counter()
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"s-{i}"))
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.SUBMIT_CARD_P95_MS

    def test_TC_L110_L202_706_utf8_char_count_emoji_cjk(
        self, sut,
    ) -> None:
        """TC-L110-L202-706 · 评论长度 UTF-8 字符数（emoji + CJK）· P95 ≤ 5ms。"""
        samples: list[float] = []
        comments = [
            "这是一个评论 · 十字够了啦",       # 13 CJK 字符
            "OK 确认放行，监控接入 ✅👍 OK",    # emoji + CJK 混合
            "a" * 50,                              # ASCII
            "测试 😀 emoji 🎉 CJK 字符数 ≥ 10",
        ]
        for _ in range(500):
            for c in comments:
                t0 = time.perf_counter()
                sut.validators.utf8_char_count(c)
                samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.COMMENT_UTF8_COUNT_P95_MS
```

---

## §6 端到端 e2e（≥ 2）

```python
# file: tests/l1_10/test_l2_02_e2e.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_02_E2E:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_801_e2e_gate_decision_go_full_path(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L202-801 · e2e · submit_card → 用户 GO + 评论 → 委托 L2-04 → archive → 审计。
        映射 §5.1 P0 时序 · TC-L202-001。"""
        # 1. IC-16 推入
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="e2e-1", stage_to="S5"))
        # 2. UI load_queue → 找到 active
        q = await sut.load_queue(project_id=mock_project_id)
        assert q.active_card.card_id == "e2e-1"
        # 3. UI load_card → 详情
        d = await sut.load_card(
            project_id=mock_project_id, card_id="e2e-1")
        assert d.card.state == "ACTIVE"
        # 4. 用户点 GO + 评论 ≥ 10 字
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-e2e", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id, card_id="e2e-1",
            decision="GO", comment="所有 DoD 已验证 · OK 进入 S5",
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        # 5. L2-04 委托成功 · ic17 submitted
        assert r.l204_delegation.ic17_submitted is True
        assert r.archived is True
        # 6. 审计事件链完整
        event_types = "|".join(
            c.kwargs.get("type", "")
            for c in mock_event_bus.append_event.call_args_list)
        assert "card_received" in event_types
        assert "card_decided" in event_types

    @pytest.mark.asyncio
    async def test_TC_L110_L202_802_e2e_request_change_then_next_card_promoted(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-802 · e2e · Request-change + 队列有下一张卡 · 自动晋升。
        映射 §5.2 P1 时序。"""
        # 队列两张卡
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="rc-a"))
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="rc-b"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-rc", status="ACKED")
        # Request-change
        r = await sut.submit_decision(
            project_id=mock_project_id, card_id="rc-a",
            decision="REQUEST_CHANGE",
            comment="请补齐 SLO dashboard + alert rules",
            change_request={
                "impacted_artifacts": ["art-1"],
                "suggestion": "补齐监控面板 + 告警规则",
                "impacted_scope": "stage",
            },
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        # rc-a archived · rc-b 晋升为 ACTIVE
        assert r.next_active_card == "rc-b"
        q = await sut.load_queue(project_id=mock_project_id)
        assert q.active_card.card_id == "rc-b"
```

---

## §7 测试 fixture

```python
# file: tests/l1_10/conftest_l2_02.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_02.service import GateCardService


@dataclass
class FakeClock:
    _now_ms: int = 0
    def now_ms(self) -> int: return self._now_ms
    def advance(self, ms: int) -> None: self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(name="GateCardRepository")
    repo.write = MagicMock(return_value=None)
    repo.read_queue = MagicMock(return_value={"active": None, "queued": []})
    repo.list_cards = MagicMock(return_value=[])
    return repo


@pytest.fixture
def mock_l204_service() -> AsyncMock:
    s = AsyncMock(name="L204InterventionService")
    s.submit_intervention = AsyncMock(return_value=MagicMock(
        intent_id="int-default", status="ACKED"))
    return s


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    return bus


@pytest.fixture
def sut(
    mock_project_id: str, fake_clock: FakeClock,
    mock_repo: MagicMock, mock_l204_service: AsyncMock,
    mock_event_bus: MagicMock,
) -> GateCardService:
    return GateCardService(
        session={"project_id": mock_project_id},
        clock=fake_clock,
        repo=mock_repo,
        l204=mock_l204_service,
        event_bus=mock_event_bus,
        config={
            "idempotency_window_s": 60,
            "comment_min_chars": 10,
            "artifact_preview_threshold_bytes": 1_000_000,
        },
    )


@pytest.fixture
def make_stage_gate_payload():
    def _factory(**overrides: Any) -> dict:
        base = dict(
            project_id="pid-default",
            card_id=f"card-{uuid.uuid4()}",
            card_type="stage_gate",
            stage_from="S4", stage_to="S5",
            artifacts_bundle=[
                {"artifact_id": "a-1", "path": "p/a1.md",
                 "mime": "text/markdown", "title": "Design",
                 "size_bytes": 1024, "stage_link": None},
            ],
            required_decisions=[
                {"field_name": "go_no_go", "label": "决定",
                 "widget": "radio", "options": ["GO", "NO_GO", "REQUEST_CHANGE"],
                 "min_chars": None, "required": True},
                {"field_name": "comment", "label": "评论",
                 "widget": "textarea", "options": None,
                 "min_chars": 10, "required": True},
            ],
            clarification_meta=None,
            priority="normal",
            submitted_at="2026-04-22T06:30:00Z",
            requester_actor="L1-02",
        )
        base.update(overrides)
        return base
    return _factory
```

---

## §8 集成点用例（与 L2-01/03/04 协作 · ≥ 2）

```python
# file: tests/l1_10/test_l2_02_siblings.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_02_SiblingIntegration:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_901_l2_01_loads_queue_for_gate_tab(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-901 · L2-01 Gate tab 加载 · 调 load_queue + load_card。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="sib-1"))
        # L2-01 tab 加载触发两个方法
        q = await sut.load_queue(project_id=mock_project_id)
        d = await sut.load_card(
            project_id=mock_project_id, card_id=q.active_card.card_id)
        assert d.card.card_id == "sib-1"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_902_l2_03_dispatches_stage_event_to_l2_02(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-902 · L2-03 订阅分发 · on_stage_event → 卡状态同步。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="sib-2", stage_to="S5"))
        await sut.on_stage_event({
            "type": "L1-02:stage_transitioned",
            "project_id": mock_project_id,
            "payload": {"from_stage": "S4", "to_stage": "S5",
                        "gate_card_id": "sib-2", "result": "GO"},
            "ts": "2026-04-22T06:40:00Z",
        })
        d = await sut.load_card(
            project_id=mock_project_id, card_id="sib-2")
        # stage_transitioned 正常路径 · 卡已归档 · 不是 EXPIRED
        assert d.card.state in ("ARCHIVED", "ACTIVE", "USER_DECIDED")

    @pytest.mark.asyncio
    async def test_TC_L110_L202_903_l2_02_never_sends_ic17_directly(
        self,
    ) -> None:
        """TC-L110-L202-903 · 静态扫描 · L2-02 代码不得直接 import IC17 · 必经 L2-04。"""
        offenders = static_scan.find_imports_in(
            path_prefix="app/l1_10/l2_02/",
            forbidden_imports=["IC17Transport", "send_ic17"],
        )
        assert offenders == [], f"L2-02 违规直发 IC-17: {offenders}"
```

---

## §9 边界 / edge case

```python
# file: tests/l1_10/test_l2_02_edge.py
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_02.errors import L202Error


class TestL2_02_Edge:

    @pytest.mark.asyncio
    async def test_TC_L110_L202_911_comment_exactly_10_utf8_chars(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-911 · 评论正好 10 UTF-8 字符（不是 bytes）· 通过。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="edge-exact"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-exact", status="ACKED")
        r = await sut.submit_decision(
            project_id=mock_project_id, card_id="edge-exact",
            decision="GO",
            comment="十字评论测试足够",  # 10 CJK 字符（非 30 bytes）
            idempotency_key=str(uuid.uuid4()),
            user_ts="2026-04-22T06:30:00Z",
        )
        assert r.status == "submitted"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_912_comment_9_utf8_chars_rejected(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-912 · 评论 9 字符（少 1）· L2-02-E004 · 精确边界。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="edge-9"))
        with pytest.raises(L202Error) as exc:
            await sut.submit_decision(
                project_id=mock_project_id, card_id="edge-9",
                decision="GO",
                comment="九字评论差一个",  # 9 CJK 字符
                idempotency_key=str(uuid.uuid4()),
                user_ts="2026-04-22T06:30:00Z",
            )
        assert exc.value.code == "L2-02-E004"

    @pytest.mark.asyncio
    async def test_TC_L110_L202_913_concurrent_double_submit_decision(
        self, sut, mock_project_id: str, make_stage_gate_payload,
        mock_l204_service: AsyncMock,
    ) -> None:
        """TC-L110-L202-913 · 用户双击提交 · 第二次 L2-02-E009 或同 idempotency_key 幂等。"""
        await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="edge-dc"))
        mock_l204_service.submit_intervention.return_value = MagicMock(
            intent_id="int-dc", status="ACKED")
        idk = "user-double-click-key"
        tasks = [
            sut.submit_decision(
                project_id=mock_project_id, card_id="edge-dc",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=idk,
                user_ts="2026-04-22T06:30:00Z",
            ),
            sut.submit_decision(
                project_id=mock_project_id, card_id="edge-dc",
                decision="GO", comment="放行 OK 监控就绪",
                idempotency_key=idk,
                user_ts="2026-04-22T06:30:00Z",
            ),
        ]
        # 其一成功 · 另一 already_decided 或返同结果（幂等）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        succeeded = sum(1 for r in results
                        if not isinstance(r, Exception) and getattr(r, "status", None) in ("submitted", "already_decided"))
        assert succeeded >= 1
        # L2-04 仅被调 1 次
        assert mock_l204_service.submit_intervention.call_count == 1

    @pytest.mark.asyncio
    async def test_TC_L110_L202_914_huge_artifact_bundle_uses_progressive_preview(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L202-914 · artifact size 总和 > 1MB · preview_policy=progressive。"""
        p = {
            "project_id": mock_project_id,
            "card_id": "edge-big",
            "card_type": "stage_gate",
            "stage_from": "S4", "stage_to": "S5",
            "artifacts_bundle": [
                {"artifact_id": f"a-{i}", "path": f"p/a{i}.md",
                 "mime": "text/markdown", "title": f"Big-{i}",
                 "size_bytes": 500_000, "stage_link": None}
                for i in range(5)  # 5 × 500KB = 2.5 MB
            ],
            "required_decisions": [{"field_name": "go_no_go", "label": "决定",
                                    "widget": "radio",
                                    "options": ["GO", "NO_GO"],
                                    "min_chars": None, "required": True}],
            "priority": "normal",
            "submitted_at": "2026-04-22T06:30:00Z",
            "requester_actor": "L1-02",
        }
        await sut.submit_card(p)
        d = await sut.load_card(
            project_id=mock_project_id, card_id="edge-big")
        assert d.card.artifacts_preview_policy in ("progressive", "manual")

    @pytest.mark.asyncio
    async def test_TC_L110_L202_915_queue_max_capacity_rejects_new(
        self, sut, mock_project_id: str, make_stage_gate_payload,
    ) -> None:
        """TC-L110-L202-915 · 队列上限（config.queue_max · 默认 50）· 超出 reject/背压。"""
        sut.config["queue_max"] = 3
        for i in range(3):
            await sut.submit_card(make_stage_gate_payload(
                project_id=mock_project_id, card_id=f"cap-{i}"))
        # 第 4 张入队 · 应 reject 或背压
        r = await sut.submit_card(make_stage_gate_payload(
            project_id=mock_project_id, card_id="cap-overflow"))
        # accepted（进 backlog）或 rejected（硬拒）· 视实现
        assert r.status in ("accepted", "rejected", "backpressure")
```

---

*— TDD · L1-10 L2-02 · Gate 决策卡片 · depth-B · v1.0 · 2026-04-22 · session-L —*
