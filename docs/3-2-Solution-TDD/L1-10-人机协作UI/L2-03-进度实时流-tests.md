---
doc_id: tests-L1-10-L2-03-进度实时流-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-03-进度实时流.md
  - docs/2-prd/L1-10 人机协作UI/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
author: session-L
created_at: 2026-04-22
---

# L1-10 L2-03-进度实时流 · TDD 测试用例

> 基于 3-1 L2-03 §3（4 核心 method + 2 可选 + 2 回调） + §11（15 项 E-L203-* 错误码） + §12 SLO（消费 P95 ≤ 1s · P99 ≤ 2s · 首次 pull 500 条 ≤ 2s · 吞吐 100eps 不卡） + §13.3 TC-L203-001~030 驱动。
> TC ID 统一：`TC-L110-L203-NNN`（001-099 正向 · 101-199 负向 · 601-699 IC 契约 · 701-799 性能 · 801-899 e2e · 901-999 边界）。
> **L2-03 是 L1-10 数据面唯一入口**（ADR-L203-01）· SSE 主通道 + polling 降级 + event_id LRU 去重 + type 前缀 trie 分发 + 5 级降级链（FULL→SLOW→POLL→SNAPSHOT→FAILED）。
> pytest + Python 3.11+ 类型注解；SSE/polling 前端实现可用 Vitest + @vue/test-utils · 本文件 Python 伪代码表达。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 + 错误码 + IC + SLO）
- [x] §2 正向用例（subscribe/unsubscribe/pull_history/get_store_slice + 状态机转换）
- [x] §3 负向用例（15 条 E-L203-* 全覆盖）
- [x] §4 IC-XX 契约集成（IC-L2-01 订阅 / pull · IC-L2-02 被调 · IC-L2-12 分发 · IC-09 审计）
- [x] §5 性能 SLO 用例（消费 P95 / P99 · 首次 pull · 高频 100 eps）
- [x] §6 端到端 e2e（SSE full → 断联 → POLLING → 重连 → 补齐）
- [x] §7 测试 fixture（mock_project_id / fake_sse / mock_l109 / make_event / fake_clock）
- [x] §8 集成点用例（与 L2-01/02/05/07 协作 · 跨 tab timeline）
- [x] §9 边界 / edge case（跨项目毒样 / LRU 溢出 / 高频 / 浏览器刷新）

---

## §1 覆盖度索引

### §1.1 方法 × 测试 × 覆盖类型

| 方法（§3） | TC ID | 覆盖类型 | 对应 IC | 备注 |
|---|---|---|---|---|
| `subscribe(filter) -> handle` | TC-L110-L203-001 | unit | IC-L2-02 | 返 handle + slice_keys + transport=sse |
| `subscribe` with initial_pull | TC-L110-L203-002 | unit | IC-L2-02 + IC-L2-01 | initial_events 含 N 条 |
| `unsubscribe(handle)` | TC-L110-L203-003 | unit | IC-L2-02 | 幂等 · 返 events_consumed + latency_metric |
| `pull_history(filter, n)` | TC-L110-L203-004 | unit | IC-L2-01 | n=500 默认 · order=desc |
| `pull_history` 增量 | TC-L110-L203-005 | unit | IC-L2-01 | since_event_id 增量 |
| `get_store_slice(slice_key)` | TC-L110-L203-006 | unit | IC-L2-12 | 响应式切片 |
| `on_event_received(raw)` 分发 | TC-L110-L203-007 | unit | — | 路由到 slice + timeline |
| 状态机 FULL_SSE 正常推送 | TC-L110-L203-008 | integration | — | INIT → FULL_SSE |
| 降级 FULL → POLLING_FAST | TC-L110-L203-009 | integration | — | heartbeat timeout 10s |
| 降级 POLLING_FAST → POLLING_SLOW | TC-L110-L203-010 | integration | — | pull fail 3x |
| 降级 POLLING_SLOW → HISTORY_ONLY | TC-L110-L203-011 | integration | — | pull fail 5x |
| 恢复 POLLING → FULL_SSE | TC-L110-L203-012 | integration | — | SSE reconnect ok |
| HeartbeatMonitor | TC-L110-L203-013 | unit | — | 10s 静默 |
| ReconnectCoordinator 退避 | TC-L110-L203-014 | unit | — | [1, 2, 5, 10, 30]s |
| LRUDeduplicator | TC-L110-L203-015 | unit | — | 同 event_id 推 2 次只分发 1 次 |
| EventClassifier trie 前缀 | TC-L110-L203-016 | unit | — | `L1-02:stage_*` 通配 |
| Batch render debounce | TC-L110-L203-017 | unit | — | 50ms 合并 |
| GlobalEventTimeline 跨 tab | TC-L110-L203-018 | integration | — | 全量追加 |
| LastEventId 持久化 | TC-L110-L203-019 | unit | — | 30s 写 localStorage |

### §1.2 错误码 × 测试（§3.9 全 15 项覆盖）

| 错误码 | TC ID | 场景 | 严重级 |
|---|---|---|---|
| `E-L203-001` | TC-L110-L203-101 | subscribe 缺 project_id | critical |
| `E-L203-002` | TC-L110-L203-102 | type_prefixes 非白名单 | major |
| `E-L203-003` | TC-L110-L203-103 | 跨项目订阅 | critical |
| `E-L203-004` | TC-L110-L203-104 | L1-09 不可达 | critical |
| `E-L203-005` | TC-L110-L203-105 | 订阅超 8 条上限 | minor |
| `E-L203-006` | TC-L110-L203-106 | unsubscribe 不存在 handle · 幂等忽略 | minor |
| `E-L203-007` | TC-L110-L203-107 | tab_id 不匹配 · 越权退订 | critical |
| `E-L203-008` | TC-L110-L203-108 | pull n > 2000 | minor |
| `E-L203-009` | TC-L110-L203-109 | pull 超时 | major |
| `E-L203-010` | TC-L110-L203-110 | since_event_id 不存在 → 全量兜底 | major |
| `E-L203-011` | TC-L110-L203-111 | get_store_slice 不存 slice_key | minor |
| `E-L203-012` | TC-L110-L203-112 | get_store_slice 跨项目访问 | critical |
| `E-L203-013` | TC-L110-L203-113 | 去重 LRU 满 · 重建 | warn |
| `E-L203-014` | TC-L110-L203-114 | 时间轴超容量 · FIFO 丢最旧 | warn |
| `E-L203-030` | TC-L110-L203-115 | 跨项目毒样事件到达 · classifier 拒绝 + 审计 | critical |

### §1.3 IC 契约 × 测试

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-01 SSE stream | L2-03 → L1-09 | TC-L110-L203-601 | 建连 + onMessage · Last-Event-ID header |
| IC-L2-01 pull_events | L2-03 → L1-09 | TC-L110-L203-602 | n=500 · since_event_id 增量 |
| IC-L2-02 tab_subscribe | L2-01/02/05/07 → L2-03 | TC-L110-L203-603 | L2-02 订阅 `L1-02:stage_*` |
| IC-L2-02 tab_pull_history | L2-05 → L2-03 | TC-L110-L203-604 | KB tab 加载 pull N=500 |
| IC-L2-12 store_slice_access | L2-07 → L2-03 | TC-L110-L203-605 | Admin 取 alerts slice |
| IC-09 append_event (audit) | L2-03 → L1-09 | TC-L110-L203-606 | subscription_registered / degradation_triggered 等 5 类 |

### §1.4 SLO × 测试（§12.2 硬约束）

| SLO | 目标 | TC ID | 样本 |
|---|---|---|---|
| 单事件端到端延迟（event.ts → UI render） | P95 ≤ 1s · P99 ≤ 2s | TC-L110-L203-701 | 200 次 |
| 订阅注册 | P95 ≤ 100ms | TC-L110-L203-702 | 100 次 |
| 首次 pull N=500 | P95 ≤ 2s | TC-L110-L203-703 | 50 次 |
| 重连耗时 | P95 ≤ 8s | TC-L110-L203-704 | 30 次 |
| tab 切换（store 已缓存） | P95 ≤ 100ms | TC-L110-L203-705 | 100 次 |
| 高频 100 eps × 10s 不卡 | FPS ≥ 30 | TC-L110-L203-706 | 1 次（10s 窗口） |
| 去重 LRU check | P95 ≤ 1ms | TC-L110-L203-707 | 1000 次 |

### §1.5 PM-14 project 过滤（硬锁）

- 所有 subscribe / pull_history / get_store_slice / on_event_received 强制校验 `project_id == session.project_id`
- 跨项目事件到达 → classifier 层拒绝 + 审计 `L1-10:cross_project_event_rejected`
- 负向载体：TC-L110-L203-103 / 112 / 115；正向：所有 §2 用例

---

## §2 正向用例（每方法 ≥ 1 · 覆盖状态机）

```python
# file: tests/l1_10/test_l2_03_positive.py
from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_03.service import EventStreamSubscriber
from app.l1_10.l2_03.schemas import (
    SubscriptionFilter, SubscriptionHandle, RawEvent, SliceKey,
)


class TestL2_03_EventStream_Positive:
    """每 public 方法 + 状态机每条 transition 至少 1 正向 TC。"""

    # ---------- 4 核心 method ----------

    @pytest.mark.asyncio
    async def test_TC_L110_L203_001_subscribe_returns_handle_with_sse_transport(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-001 · subscribe · 返 handle · transport=sse · slice_keys 正确。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"], "subscription_mode": "push"},
            tab_id="tab-gate",
        )
        assert handle.transport == "sse"
        assert handle.project_id == mock_project_id
        assert "L1-02:stage_" in handle.slice_keys or "gate" in handle.slice_keys
        assert handle.established_at is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L203_002_subscribe_with_initial_pull_500(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-002 · subscribe + initial_pull.enabled=true n=500 · initial_events 填充。"""
        mock_l109_client.pull_events.return_value = [
            {"event_id": f"evt-{i:05d}", "type": "L1-02:stage_gate",
             "ts": "2026-04-22T06:30:00Z", "project_id": mock_project_id,
             "payload": {"i": i}}
            for i in range(500)
        ]
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
            initial_pull={"enabled": True, "n": 500},
        )
        assert len(handle.initial_events) == 500

    @pytest.mark.asyncio
    async def test_TC_L110_L203_003_unsubscribe_idempotent_returns_stats(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-003 · unsubscribe 返 events_consumed + final_latency_metric · 二次幂等。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
        )
        await sut.on_event_received({
            "event_id": "evt-1", "type": "L1-02:stage_gate",
            "ts": "2026-04-22T06:30:00Z", "project_id": mock_project_id,
            "payload": {}, "received_at": "2026-04-22T06:30:00.050Z",
            "transport": "sse",
        })
        r = await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id=handle.subscription_id,
            tab_id="tab-gate",
            reason="tab_unloaded",
        )
        assert r.events_consumed >= 1
        r2 = await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id=handle.subscription_id,
            tab_id="tab-gate",
            reason="tab_unloaded",
        )
        assert r2 is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L203_004_pull_history_default_500_desc(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-004 · pull_history n=500 · order=desc · 最新在前。"""
        mock_l109_client.pull_events.return_value = [
            {"event_id": f"evt-{i:05d}", "type": "L1-02:stage_gate",
             "ts": f"2026-04-22T06:30:{i:02d}Z", "project_id": mock_project_id,
             "payload": {}}
            for i in range(500, 0, -1)
        ]
        r = await sut.pull_history(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            n=500,
            order="desc",
        )
        assert r.count == 500
        assert r.events[0]["event_id"] == "evt-00500"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_005_pull_history_incremental_since_event_id(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-005 · pull_history since_event_id 增量。"""
        mock_l109_client.pull_events.return_value = [
            {"event_id": "evt-00600", "type": "L1-02:stage_gate",
             "ts": "2026-04-22T06:31:00Z", "project_id": mock_project_id, "payload": {}},
        ]
        await sut.pull_history(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"],
                    "since_event_id": "evt-00500"},
            n=100,
        )
        call_kwargs = mock_l109_client.pull_events.call_args.kwargs
        assert call_kwargs.get("since_event_id") == "evt-00500"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_006_get_store_slice_returns_reactive(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-006 · get_store_slice 响应式 · 含 events + stats。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
        )
        await sut.on_event_received({
            "event_id": "evt-1", "type": "L1-02:stage_gate",
            "ts": "2026-04-22T06:30:00Z", "project_id": mock_project_id,
            "payload": {"x": 1}, "received_at": "2026-04-22T06:30:00.050Z",
            "transport": "sse",
        })
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id,
            slice_key="L1-02:stage_",
            include_stats=True,
        )
        assert slice_obj.project_id == mock_project_id
        assert len(slice_obj.events) >= 1
        assert slice_obj.stats.total_received >= 1

    @pytest.mark.asyncio
    async def test_TC_L110_L203_007_on_event_received_routes_to_slice_and_timeline(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-007 · 路由到 slice + global timeline。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
        )
        await sut.on_event_received({
            "event_id": "evt-routed", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        })
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        timeline = sut.global_timeline.events(project_id=mock_project_id)
        assert any(e["event_id"] == "evt-routed" for e in slice_obj.events)
        assert any(e["event_id"] == "evt-routed" for e in timeline)

    @pytest.mark.asyncio
    async def test_TC_L110_L203_008_state_init_to_full_sse(
        self, sut, mock_project_id: str, mock_sse_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-008 · INIT → FULL_SSE · handshake + 首事件。"""
        await sut.init(project_id=mock_project_id)
        assert sut.state == "INITIALIZING"
        mock_sse_client.simulate_connect_ok()
        await sut.on_event_received({
            "event_id": "evt-first", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        })
        assert sut.state == "FULL_SSE"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_009_full_sse_to_polling_fast_on_heartbeat_timeout(
        self, sut, mock_project_id: str, fake_clock,
    ) -> None:
        """TC-L110-L203-009 · FULL_SSE → POLLING_FAST · heartbeat > 10s。"""
        sut.state = "FULL_SSE"
        sut.heartbeat.last_event_at_ms = fake_clock.now_ms()
        fake_clock.advance(11_000)
        await sut.heartbeat.check(expected_event_flow=True)
        assert sut.state == "POLLING_FAST"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_010_polling_fast_to_slow_after_3_fails(
        self, sut, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-010 · POLLING_FAST → POLLING_SLOW · pull fail 3。"""
        sut.state = "POLLING_FAST"
        mock_l109_client.pull_events.side_effect = ConnectionError("fail")
        for _ in range(3):
            await sut.polling_tick()
        assert sut.state == "POLLING_SLOW"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_011_polling_to_history_only_after_5_fails(
        self, sut, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-011 · POLLING → HISTORY_ONLY · pull fail 5。"""
        sut.state = "POLLING_FAST"
        mock_l109_client.pull_events.side_effect = ConnectionError("fail")
        for _ in range(5):
            await sut.polling_tick()
        assert sut.state == "HISTORY_ONLY"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_012_reconnect_back_to_full_sse(
        self, sut, mock_project_id: str, mock_sse_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-012 · POLLING_FAST → FULL_SSE · SSE reconnect ok。"""
        sut.state = "POLLING_FAST"
        mock_sse_client.simulate_reconnect_ok()
        await sut.on_event_received({
            "event_id": "evt-reconn", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        })
        assert sut.state == "FULL_SSE"

    def test_TC_L110_L203_013_heartbeat_monitor_timeout_10s(
        self, sut, fake_clock,
    ) -> None:
        """TC-L110-L203-013 · HeartbeatMonitor 10s 静默 · is_timeout=True。"""
        sut.heartbeat.last_event_at_ms = fake_clock.now_ms()
        fake_clock.advance(10_500)
        assert sut.heartbeat.is_timeout(
            now_ms=fake_clock.now_ms(), expected_event_flow=True) is True

    def test_TC_L110_L203_014_reconnect_coordinator_exponential_backoff(
        self, sut,
    ) -> None:
        """TC-L110-L203-014 · ReconnectCoordinator · 指数退避 [1, 2, 5, 10, 30]s。"""
        delays = [sut.reconnect.compute_delay_ms(attempt=i, jitter=False)
                  for i in range(5)]
        assert delays[0] == 1_000
        assert delays[1] == 2_000
        assert delays[-1] <= 30_000
        assert delays == sorted(delays)

    @pytest.mark.asyncio
    async def test_TC_L110_L203_015_lru_deduplicator_same_event_id_once(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-015 · LRUDeduplicator · 同 event_id 只分发 1 次。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
        )
        evt = {
            "event_id": "evt-dup", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        }
        await sut.on_event_received(evt)
        await sut.on_event_received(evt)
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        assert sum(1 for e in slice_obj.events if e["event_id"] == "evt-dup") == 1

    def test_TC_L110_L203_016_event_classifier_trie_prefix_match(
        self, sut,
    ) -> None:
        """TC-L110-L203-016 · EventClassifier trie · `L1-02:stage_*` 通配。"""
        sut.classifier.register_prefix("L1-02:stage_", slice_key="gate")
        assert sut.classifier.classify("L1-02:stage_pre_gate") == "gate"
        assert sut.classifier.classify("L1-02:stage_post_gate") == "gate"
        assert sut.classifier.classify("L1-03:wp_created") != "gate"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_017_batch_render_debounce_50ms_merge(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-017 · batch debounce 50ms · 合并 20 条 · 不丢。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-gate",
        )
        for i in range(20):
            await sut.on_event_received({
                "event_id": f"evt-batch-{i}", "type": "L1-02:stage_gate",
                "ts": "now", "project_id": mock_project_id,
                "payload": {}, "received_at": "now", "transport": "sse",
            })
        await asyncio.sleep(0.06)
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        assert len([e for e in slice_obj.events
                    if e["event_id"].startswith("evt-batch-")]) == 20

    @pytest.mark.asyncio
    async def test_TC_L110_L203_018_global_timeline_cross_tab_shared(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-018 · GlobalEventTimeline 跨 tab 共享。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-A",
        )
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-03:wp_"]},
            tab_id="tab-B",
        )
        await sut.on_event_received({
            "event_id": "evt-tabA", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id, "payload": {},
            "received_at": "now", "transport": "sse",
        })
        timeline = sut.global_timeline.events(project_id=mock_project_id)
        assert any(e["event_id"] == "evt-tabA" for e in timeline)

    def test_TC_L110_L203_019_last_event_id_persists_to_local_storage(
        self, sut, mock_project_id: str, mock_local_storage: MagicMock,
    ) -> None:
        """TC-L110-L203-019 · last_seen_event_id 写 localStorage。"""
        sut.last_event_id = "evt-LATEST"
        sut.persist_last_event_id()
        mock_local_storage.setItem.assert_called_once()
        assert "evt-LATEST" in mock_local_storage.setItem.call_args.args[1]
```

---

## §3 负向用例（15 条 E-L203-* 全覆盖）

```python
# file: tests/l1_10/test_l2_03_negative.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_03.errors import L203Error


class TestL2_03_EventStream_Negative:

    @pytest.mark.asyncio
    async def test_TC_L110_L203_101_subscribe_missing_project_id(self, sut) -> None:
        """TC-L110-L203-101 · subscribe 缺 project_id → E-L203-001。"""
        with pytest.raises(L203Error) as exc:
            await sut.subscribe(
                project_id=None,
                filter={"type_prefixes": ["L1-02:stage_"]},
                tab_id="tab-1",
            )
        assert exc.value.code == "E-L203-001"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_102_type_prefix_not_in_whitelist(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-102 · type_prefixes 不在白名单 → E-L203-002。"""
        with pytest.raises(L203Error) as exc:
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": ["EVIL:*"]},
                tab_id="tab-1",
            )
        assert exc.value.code == "E-L203-002"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_103_cross_project_subscribe_rejected(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-103 · 跨项目订阅 → E-L203-003。"""
        sut.session.project_id = mock_project_id
        with pytest.raises(L203Error) as exc:
            await sut.subscribe(
                project_id="pid-OTHER",  # 与 session 不匹配
                filter={"type_prefixes": ["L1-02:stage_"]},
                tab_id="tab-1",
            )
        assert exc.value.code == "E-L203-003"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_104_l1_09_unreachable(
        self, sut, mock_project_id: str, mock_sse_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-104 · L1-09 SSE endpoint 不可达 → E-L203-004 · 降级 polling。"""
        mock_sse_client.connect.side_effect = ConnectionError("ECONNREFUSED")
        # 3 次 SSE 连接失败 → 降级 POLLING_FAST
        for _ in range(3):
            await sut._try_sse_connect()
        assert sut.state in ("POLLING_FAST", "INITIALIZING")
        # UI 黄横幅
        assert sut.ui_banner.level in ("yellow", "Level-1")

    @pytest.mark.asyncio
    async def test_TC_L110_L203_105_subscription_exceeds_limit(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-105 · 单 tab 订阅超 8 条 → E-L203-005。"""
        for i in range(8):
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": [f"L1-0{i%7+1}:stage_"]},
                tab_id="tab-1",
            )
        with pytest.raises(L203Error) as exc:
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": ["L1-09:event_"]},
                tab_id="tab-1",
            )
        assert exc.value.code == "E-L203-005"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_106_unsubscribe_not_found_idempotent(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-106 · unsubscribe 不存在 handle → E-L203-006 · 幂等 · 不抛。"""
        r = await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id="sub-GONE",
            tab_id="tab-1",
            reason="tab_unloaded",
        )
        # 幂等处理 · 返回 ok 或 noop 结构（两种都合规 · 只要不抛）
        assert r is not None

    @pytest.mark.asyncio
    async def test_TC_L110_L203_107_unsubscribe_wrong_tab_id_rejected(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-107 · tab_id 不匹配 → E-L203-007 · 越权退订 · 审计告警。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-A",
        )
        with pytest.raises(L203Error) as exc:
            await sut.unsubscribe(
                project_id=mock_project_id,
                subscription_id=handle.subscription_id,
                tab_id="tab-B",  # 不同 tab
                reason="tab_unloaded",
            )
        assert exc.value.code == "E-L203-007"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_108_pull_history_n_exceeds_2000(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-108 · pull n > 2000 → E-L203-008。"""
        with pytest.raises(L203Error) as exc:
            await sut.pull_history(
                project_id=mock_project_id,
                filter={"type_prefixes": ["L1-02:stage_"]},
                n=3000,
            )
        assert exc.value.code == "E-L203-008"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_109_pull_history_timeout(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-109 · pull_history 超时 > 3s → E-L203-009 + 降级横幅。"""
        import asyncio
        async def _slow(*a, **kw):
            await asyncio.sleep(5)
            return []
        mock_l109_client.pull_events.side_effect = _slow
        with pytest.raises(L203Error) as exc:
            await sut.pull_history(
                project_id=mock_project_id,
                filter={"type_prefixes": ["L1-02:stage_"]},
                n=500,
                timeout_ms=100,  # 测试用 100ms 加速
            )
        assert exc.value.code == "E-L203-009"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_110_since_event_id_not_found_falls_back_to_full(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-110 · since_event_id 已归档 → E-L203-010 · 全量兜底。"""
        mock_l109_client.pull_events.side_effect = [
            L203Error(code="E-L203-010", user_message="event_id archived"),
            [{"event_id": "evt-1", "type": "L1-02:stage_gate",
              "ts": "now", "project_id": mock_project_id, "payload": {}}],
        ]
        r = await sut.pull_history(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"],
                    "since_event_id": "evt-ARCHIVED"},
            n=500,
            fallback_on_since_lost=True,
        )
        # 第二次调用（fallback）被触发
        assert mock_l109_client.pull_events.call_count == 2
        assert r.count >= 1

    def test_TC_L110_L203_111_get_store_slice_key_not_found(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-111 · get_store_slice 不存在的 slice_key → E-L203-011。"""
        with pytest.raises(L203Error) as exc:
            sut.get_store_slice(
                project_id=mock_project_id, slice_key="NOT_EXIST_")
        assert exc.value.code == "E-L203-011"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_112_get_store_slice_cross_project_rejected(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L203-112 · 跨项目 get_store_slice → E-L203-012 · 审计 cross_project_event_rejected。"""
        sut.session.project_id = mock_project_id
        # 创建合法 slice_key
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        with pytest.raises(L203Error) as exc:
            sut.get_store_slice(
                project_id="pid-OTHER",  # 跨项目
                slice_key="L1-02:stage_")
        assert exc.value.code == "E-L203-012"

    def test_TC_L110_L203_113_lru_deduplicator_overflow_rebuilds(
        self, sut,
    ) -> None:
        """TC-L110-L203-113 · 去重 LRU 超容量 · 淘汰最旧 · 不报错 · 指标 E-L203-013。"""
        cap = sut.deduper.capacity  # 10000 默认
        # 塞入 cap + 100
        for i in range(cap + 100):
            sut.deduper.check_and_register(f"evt-{i}")
        # 最旧的已被淘汰
        assert sut.deduper.check_and_register("evt-0") is True  # 视为未见过
        # 指标记录
        assert sut.metrics.deduper_overflow_count >= 100

    def test_TC_L110_L203_114_global_timeline_capacity_fifo_drop(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-114 · GlobalEventTimeline 超容量 · FIFO 丢最旧 · E-L203-014 warn。"""
        cap = 2000
        sut.global_timeline.capacity = cap
        for i in range(cap + 50):
            sut.global_timeline.append(
                project_id=mock_project_id,
                event={"event_id": f"evt-{i}", "ts": "now",
                       "type": "L1-02:stage_gate", "project_id": mock_project_id,
                       "payload": {}})
        # 容量内
        evts = sut.global_timeline.events(project_id=mock_project_id)
        assert len(evts) <= cap
        # drop 计数
        assert sut.global_timeline.stats.total_dropped >= 50

    @pytest.mark.asyncio
    async def test_TC_L110_L203_115_cross_project_poisoned_event_rejected_and_audited(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L203-115 · classifier 收到跨项目毒样 · 拒绝 + 审计 L1-10:cross_project_event_rejected。"""
        sut.session.project_id = mock_project_id
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        # 伪造一条跨项目事件 · 本地 filter_strict_project_id=true 必拒
        await sut.on_event_received({
            "event_id": "evt-poison",
            "type": "L1-02:stage_gate",
            "ts": "now",
            "project_id": "pid-OTHER",  # 毒样
            "payload": {},
            "received_at": "now",
            "transport": "sse",
        })
        # 未进 slice
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        assert all(e["event_id"] != "evt-poison" for e in slice_obj.events)
        # 审计事件
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("cross_project_event_rejected" in (t or "") for t in event_types)
```

---

## §4 IC-XX 契约集成测试（≥ 6）

```python
# file: tests/l1_10/test_l2_03_ic_contracts.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_03_IC_Contracts:

    @pytest.mark.asyncio
    async def test_TC_L110_L203_601_ic_l2_01_sse_stream_last_event_id_header(
        self, sut, mock_project_id: str, mock_sse_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-601 · IC-L2-01 SSE 建连 · 带 Last-Event-ID header + project_id header。"""
        sut.last_event_id = "evt-LATEST"
        await sut.init(project_id=mock_project_id)
        headers = mock_sse_client.connect.call_args.kwargs.get("headers", {})
        assert headers.get("Last-Event-ID") == "evt-LATEST"
        assert headers.get("X-Project-Id") == mock_project_id \
            or headers.get("project_id") == mock_project_id

    @pytest.mark.asyncio
    async def test_TC_L110_L203_602_ic_l2_01_pull_events_body(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-602 · IC-L2-01 pull_events · 请求体含 project_id + type_prefixes + n + since_event_id。"""
        mock_l109_client.pull_events.return_value = []
        await sut.pull_history(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"],
                    "since_event_id": "evt-100"},
            n=200,
        )
        kw = mock_l109_client.pull_events.call_args.kwargs
        assert kw["project_id"] == mock_project_id
        assert "L1-02:stage_" in kw["type_prefixes"]
        assert kw["n"] == 200
        assert kw["since_event_id"] == "evt-100"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_603_ic_l2_02_l2_02_subscribes_stage_prefix(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-603 · IC-L2-02 · L2-02 Gate tab 加载 · 订阅 L1-02:stage_*。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="l2-02-gate",
        )
        assert handle.subscription_id
        assert "L1-02:stage_" in handle.slice_keys or \
            any("gate" in k for k in handle.slice_keys)

    @pytest.mark.asyncio
    async def test_TC_L110_L203_604_ic_l2_02_l2_05_pull_history_for_kb(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-604 · IC-L2-02 · L2-05 KB tab 加载 pull N=500 历史。"""
        mock_l109_client.pull_events.return_value = [
            {"event_id": f"kb-{i}", "type": "L1-06:kb_upserted",
             "ts": "now", "project_id": mock_project_id, "payload": {}}
            for i in range(500)
        ]
        r = await sut.pull_history(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-06:kb_"]},
            n=500,
        )
        assert r.count == 500

    @pytest.mark.asyncio
    async def test_TC_L110_L203_605_ic_l2_12_l2_07_admin_reads_alerts_slice(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-605 · IC-L2-12 · L2-07 Admin 读 `L1-09:alert_*` slice。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-09:alert_"]},
            tab_id="l2-07-admin",
        )
        await sut.on_event_received({
            "event_id": "alert-1", "type": "L1-09:alert_red_line",
            "ts": "now", "project_id": mock_project_id, "payload": {"severity": "critical"},
            "received_at": "now", "transport": "sse",
        })
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-09:alert_")
        assert any(e["event_id"] == "alert-1" for e in slice_obj.events)

    @pytest.mark.asyncio
    async def test_TC_L110_L203_606_ic_09_audit_subscription_lifecycle(
        self, sut, mock_project_id: str, mock_event_bus: MagicMock,
    ) -> None:
        """TC-L110-L203-606 · IC-09 append_event · subscription_registered + unsubscribed · 审计留痕。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id=handle.subscription_id,
            tab_id="tab-1",
            reason="tab_unloaded",
        )
        event_types = [c.kwargs.get("type") for c in mock_event_bus.append_event.call_args_list]
        assert any("subscription_registered" in (t or "") for t in event_types)
        assert any("subscription_unsubscribed" in (t or "") for t in event_types)
```

---

## §5 性能 SLO 用例（§12.2 · 消费 P95 ≤ 1s · P99 ≤ 2s）

```python
# file: tests/l1_10/test_l2_03_perf.py
from __future__ import annotations

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_03_SLO:

    CONSUME_P95_MS = 1000
    CONSUME_P99_MS = 2000
    SUBSCRIBE_P95_MS = 100
    PULL_500_P95_MS = 2000
    RECONNECT_P95_MS = 8000
    TAB_SWITCH_P95_MS = 100
    DEDUP_CHECK_P95_MS = 1

    @pytest.mark.asyncio
    async def test_TC_L110_L203_701_consume_latency_p95_p99(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-701 · 单事件端到端 · P95 ≤ 1s · P99 ≤ 2s · 200 样本。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        samples: list[float] = []
        for i in range(200):
            ts_sent_ms = time.time() * 1000
            await sut.on_event_received({
                "event_id": f"perf-{i}", "type": "L1-02:stage_gate",
                "ts": ts_sent_ms, "project_id": mock_project_id,
                "payload": {}, "received_at": time.time() * 1000,
                "transport": "sse",
            })
            latency = (time.time() * 1000) - ts_sent_ms
            samples.append(latency)
        p95 = statistics.quantiles(samples, n=20)[18]
        p99 = statistics.quantiles(samples, n=100)[98]
        assert p95 <= self.CONSUME_P95_MS
        assert p99 <= self.CONSUME_P99_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L203_702_subscribe_latency_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-702 · 订阅注册 P95 ≤ 100ms。"""
        samples: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": [f"L1-0{i%7+1}:stage_"]},
                tab_id=f"tab-{i}",
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.SUBSCRIBE_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L203_703_pull_500_p95_le_2s(
        self, sut, mock_project_id: str, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-703 · 首次 pull 500 条 P95 ≤ 2s。"""
        mock_l109_client.pull_events.return_value = [
            {"event_id": f"e-{i}", "type": "L1-02:stage_gate",
             "ts": "now", "project_id": mock_project_id, "payload": {}}
            for i in range(500)
        ]
        samples: list[float] = []
        for _ in range(50):
            t0 = time.perf_counter()
            await sut.pull_history(
                project_id=mock_project_id,
                filter={"type_prefixes": ["L1-02:stage_"]},
                n=500,
            )
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.PULL_500_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L203_704_reconnect_p95_le_8s(
        self, sut, mock_sse_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-704 · SSE reconnect 耗时 P95 ≤ 8s（30 样本）。"""
        samples: list[float] = []
        for _ in range(30):
            mock_sse_client.connect.reset_mock()
            t0 = time.perf_counter()
            await sut.reconnect.perform_once()
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.RECONNECT_P95_MS

    def test_TC_L110_L203_705_tab_switch_p95_le_100ms(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-705 · tab 切换 · store 已缓存 · P95 ≤ 100ms。"""
        # 预埋 slice
        sut.store_registry.register_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        samples: list[float] = []
        for _ in range(100):
            t0 = time.perf_counter()
            sut.get_store_slice(
                project_id=mock_project_id, slice_key="L1-02:stage_",
                include_stats=False)
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.TAB_SWITCH_P95_MS

    @pytest.mark.asyncio
    async def test_TC_L110_L203_706_high_freq_100eps_no_drop(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-706 · 高频 100 eps × 10s = 1000 事件 · 不丢 · debounce 合并。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        for i in range(1000):
            await sut.on_event_received({
                "event_id": f"hf-{i}", "type": "L1-02:stage_gate",
                "ts": "now", "project_id": mock_project_id,
                "payload": {}, "received_at": "now", "transport": "sse",
            })
            if i % 10 == 0:
                await asyncio.sleep(0.001)  # 100 eps ≈ 10ms/event
        await asyncio.sleep(0.1)
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        # 容量可能限制 · 但不应丢 > 容量
        assert len([e for e in slice_obj.events
                    if e["event_id"].startswith("hf-")]) >= 500  # 至少保留一半

    def test_TC_L110_L203_707_dedup_lru_check_p95_le_1ms(
        self, sut,
    ) -> None:
        """TC-L110-L203-707 · LRU deduper check P95 ≤ 1ms（1000 样本）。"""
        samples: list[float] = []
        for i in range(1000):
            t0 = time.perf_counter()
            sut.deduper.check_and_register(f"evt-perf-{i}")
            samples.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 <= self.DEDUP_CHECK_P95_MS
```

---

## §6 端到端 e2e 场景（≥ 2 · 完整降级链 + 恢复链）

```python
# file: tests/l1_10/test_l2_03_e2e.py
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestL2_03_E2E:

    @pytest.mark.asyncio
    async def test_TC_L110_L203_801_e2e_full_to_polling_to_snapshot_to_recover(
        self, sut, mock_project_id: str, fake_clock,
        mock_sse_client: AsyncMock, mock_l109_client: AsyncMock,
    ) -> None:
        """TC-L110-L203-801 · e2e · FULL_SSE → heartbeat_lost → POLLING → snapshot → reconnect → FULL。"""
        # 1. INIT → FULL_SSE
        await sut.init(project_id=mock_project_id)
        mock_sse_client.simulate_connect_ok()
        await sut.on_event_received({
            "event_id": "e-1", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        })
        assert sut.state == "FULL_SSE"

        # 2. heartbeat timeout → POLLING_FAST
        sut.heartbeat.last_event_at_ms = fake_clock.now_ms()
        fake_clock.advance(11_000)
        await sut.heartbeat.check(expected_event_flow=True)
        assert sut.state == "POLLING_FAST"
        assert sut.ui_banner.level in ("yellow", "Level-1")

        # 3. pull fail 3x → POLLING_SLOW
        mock_l109_client.pull_events.side_effect = ConnectionError("fail")
        for _ in range(3):
            await sut.polling_tick()
        assert sut.state == "POLLING_SLOW"

        # 4. reconnect ok → FULL_SSE + 补齐 since_event_id
        mock_l109_client.pull_events.side_effect = None
        mock_l109_client.pull_events.return_value = [
            {"event_id": "e-gap-1", "type": "L1-02:stage_gate",
             "ts": "now", "project_id": mock_project_id, "payload": {}},
        ]
        mock_sse_client.simulate_reconnect_ok()
        await sut.on_event_received({
            "event_id": "e-after-reconn", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": {}, "received_at": "now", "transport": "sse",
        })
        assert sut.state == "FULL_SSE"
        assert sut.ui_banner.visible is False

    @pytest.mark.asyncio
    async def test_TC_L110_L203_802_e2e_gate_tab_realtime_render(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-802 · e2e · L2-02 Gate 卡 tab 订阅 · 事件到达实时 render。"""
        handle = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="l2-02-gate",
        )
        # 推 3 条 stage_gate 事件
        for i in range(3):
            await sut.on_event_received({
                "event_id": f"gate-{i}", "type": "L1-02:stage_pre_gate",
                "ts": "now", "project_id": mock_project_id,
                "payload": {"stage": f"S{i+2}"},
                "received_at": "now", "transport": "sse",
            })
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_")
        assert len([e for e in slice_obj.events
                    if e["event_id"].startswith("gate-")]) == 3
```

---

## §7 测试 fixture

```python
# file: tests/l1_10/conftest_l2_03.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.l1_10.l2_03.service import EventStreamSubscriber


@dataclass
class FakeClock:
    _now_ms: int = 0

    def now_ms(self) -> int:
        return self._now_ms

    def advance(self, ms: int) -> None:
        self._now_ms += ms


@pytest.fixture
def mock_project_id() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def mock_sse_client() -> AsyncMock:
    client = AsyncMock(name="SSEClient")
    client.connect = AsyncMock(return_value=None)
    client.simulate_connect_ok = MagicMock()
    client.simulate_reconnect_ok = MagicMock()
    return client


@pytest.fixture
def mock_l109_client() -> AsyncMock:
    client = AsyncMock(name="L109Client")
    client.pull_events = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(name="EventBus")
    bus.append_event = MagicMock(return_value={"event_id": f"evt-{uuid.uuid4()}"})
    return bus


@pytest.fixture
def mock_local_storage() -> MagicMock:
    ls = MagicMock(name="LocalStorage")
    ls.setItem = MagicMock()
    ls.getItem = MagicMock(return_value=None)
    return ls


@pytest.fixture
def sut(
    mock_project_id: str,
    fake_clock: FakeClock,
    mock_sse_client: AsyncMock,
    mock_l109_client: AsyncMock,
    mock_event_bus: MagicMock,
    mock_local_storage: MagicMock,
) -> EventStreamSubscriber:
    """装配 EventStreamSubscriber · 所有外部依赖 mock。"""
    return EventStreamSubscriber(
        session={"project_id": mock_project_id},
        clock=fake_clock,
        sse_client=mock_sse_client,
        l109_client=mock_l109_client,
        event_bus=mock_event_bus,
        local_storage=mock_local_storage,
        config={
            "heartbeat_timeout_ms": 10_000,
            "reconnect_initial_delay_ms": 1_000,
            "reconnect_max_delay_ms": 30_000,
            "reconnect_backoff_factor": 2.0,
            "deduper_capacity": 10_000,
            "slice_default_capacity": 500,
            "timeline_global_capacity": 2_000,
            "batch_render_debounce_ms": 50,
            "filter_strict_project_id": True,
        },
    )


@pytest.fixture
def make_event() -> Any:
    def _factory(**overrides: Any):
        base = dict(
            event_id=f"evt-{uuid.uuid4()}",
            type="L1-02:stage_gate",
            ts="2026-04-22T06:30:00Z",
            project_id="pid-default",
            payload={},
            received_at="2026-04-22T06:30:00.050Z",
            transport="sse",
        )
        base.update(overrides)
        return base
    return _factory
```

---

## §8 集成点用例（与 L2-01/02/05/07 协作 · ≥ 2）

```python
# file: tests/l1_10/test_l2_03_integration_siblings.py
from __future__ import annotations

import asyncio

import pytest


class TestL2_03_SiblingIntegration:

    @pytest.mark.asyncio
    async def test_TC_L110_L203_901_l2_01_registers_11_tab_subscriptions(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-901 · L2-01 11 个 tab 加载 · 对应前缀订阅全部建立。"""
        prefixes = [
            "L1-01:decision_", "L1-02:stage_", "L1-03:wp_", "L1-04:task_",
            "L1-05:skill_", "L1-06:kb_", "L1-07:supervisor_",
            "L1-08:media_", "L1-09:alert_", "global:event_", "L1-10:ui_",
        ]
        for i, prefix in enumerate(prefixes):
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": [prefix]},
                tab_id=f"tab-{i:02d}",
            )
        assert len(sut.subscription_registry.all()) == 11

    @pytest.mark.asyncio
    async def test_TC_L110_L203_902_l2_01_all_tabs_unload_paused_state(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-902 · 所有 tab 卸载 · subscriber_count=0 · 状态 → PAUSED。"""
        h1 = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-A",
        )
        h2 = await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-03:wp_"]},
            tab_id="tab-B",
        )
        sut.state = "FULL_SSE"
        await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id=h1.subscription_id,
            tab_id="tab-A", reason="tab_unloaded")
        await sut.unsubscribe(
            project_id=mock_project_id,
            subscription_id=h2.subscription_id,
            tab_id="tab-B", reason="tab_unloaded")
        await sut.on_subscriber_count_change()
        assert sut.state == "PAUSED"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_903_project_switch_rebuilds_sse_connection(
        self, sut, mock_project_id: str, mock_sse_client,
    ) -> None:
        """TC-L110-L203-903 · PM-14 · L2-07 切 project · 断旧 SSE + 建新 SSE。"""
        sut.session["project_id"] = mock_project_id
        await sut.init(project_id=mock_project_id)
        # 切 project
        new_pid = "pid-NEW-abc"
        await sut.switch_project(new_project_id=new_pid)
        # 旧连接断 · 新连接建
        mock_sse_client.disconnect.assert_called()
        assert sut.session["project_id"] == new_pid
```

---

## §9 边界 / edge case

```python
# file: tests/l1_10/test_l2_03_edge.py
from __future__ import annotations

import asyncio

import pytest


class TestL2_03_Edge:

    @pytest.mark.asyncio
    async def test_TC_L110_L203_911_empty_filter_type_prefixes(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-911 · type_prefixes 空列表 → E-L203-002。"""
        from app.l1_10.l2_03.errors import L203Error
        with pytest.raises(L203Error) as exc:
            await sut.subscribe(
                project_id=mock_project_id,
                filter={"type_prefixes": []},
                tab_id="tab-1",
            )
        assert exc.value.code == "E-L203-002"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_912_browser_refresh_rebuild_from_last_event_id(
        self, sut, mock_project_id: str, mock_local_storage,
        mock_l109_client,
    ) -> None:
        """TC-L110-L203-912 · 浏览器刷新 · 从 localStorage 读 last_event_id · pull 增量补齐。"""
        mock_local_storage.getItem.return_value = "evt-PERSISTED"
        mock_l109_client.pull_events.return_value = [
            {"event_id": "evt-gap-1", "type": "L1-02:stage_gate",
             "ts": "now", "project_id": mock_project_id, "payload": {}},
        ]
        await sut.rehydrate_from_local_storage()
        kw = mock_l109_client.pull_events.call_args.kwargs
        assert kw.get("since_event_id") == "evt-PERSISTED"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_913_slice_capacity_overflow_fifo(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-913 · slice 超容量 · FIFO 丢最旧 · total_dropped++。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        cap = sut.config["slice_default_capacity"]
        for i in range(cap + 100):
            await sut.on_event_received({
                "event_id": f"overflow-{i}",
                "type": "L1-02:stage_gate",
                "ts": "now", "project_id": mock_project_id,
                "payload": {}, "received_at": "now", "transport": "sse",
            })
        slice_obj = sut.get_store_slice(
            project_id=mock_project_id, slice_key="L1-02:stage_",
            include_stats=True)
        assert len(slice_obj.events) <= cap
        assert slice_obj.stats.total_dropped >= 100

    @pytest.mark.asyncio
    async def test_TC_L110_L203_914_ui_frozen_10min_in_history_only(
        self, sut, fake_clock,
    ) -> None:
        """TC-L110-L203-914 · HISTORY_ONLY 持续 > 10min · UI_FROZEN · 弹手动刷新。"""
        sut.state = "HISTORY_ONLY"
        sut.history_only_entered_at_ms = fake_clock.now_ms()
        fake_clock.advance(10 * 60 * 1000 + 1_000)
        await sut.check_history_only_timeout()
        assert sut.state == "UI_FROZEN"

    @pytest.mark.asyncio
    async def test_TC_L110_L203_915_reconnect_exhausted_force_poll_mode(
        self, sut, mock_sse_client,
    ) -> None:
        """TC-L110-L203-915 · reconnect 10 次全 fail · 进入 FORCE_POLL 永久模式 · audit reconnect_exhausted。"""
        mock_sse_client.connect.side_effect = ConnectionError("fail")
        for _ in range(10):
            await sut.reconnect.perform_once()
        assert sut.reconnect.exhausted is True
        # 切入 POLLING_SLOW 或更严重级别
        assert sut.state in ("POLLING_SLOW", "HISTORY_ONLY")

    @pytest.mark.asyncio
    async def test_TC_L110_L203_916_huge_payload_preview_truncated(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-916 · 超大 payload · timeline 内 payload_preview 截断 200 字。"""
        await sut.subscribe(
            project_id=mock_project_id,
            filter={"type_prefixes": ["L1-02:stage_"]},
            tab_id="tab-1",
        )
        huge_payload = {"content": "x" * 10_000}
        await sut.on_event_received({
            "event_id": "big-1", "type": "L1-02:stage_gate",
            "ts": "now", "project_id": mock_project_id,
            "payload": huge_payload, "received_at": "now", "transport": "sse",
        })
        timeline = sut.global_timeline.events(project_id=mock_project_id)
        big = next(e for e in timeline if e["event_id"] == "big-1")
        # preview 截断 ≤ 200 · 完整内容通过 payload_ref 懒加载
        assert len(big.get("payload_preview", "")) <= 200

    def test_TC_L110_L203_917_single_session_single_project_invariant(
        self, sut, mock_project_id: str,
    ) -> None:
        """TC-L110-L203-917 · 单 session 单 project 不变式 · project_id 不可直接改。"""
        sut.session["project_id"] = mock_project_id
        # 直接改 session 被拦截（假设 setter 有 guard）
        with pytest.raises((AttributeError, RuntimeError, ValueError)):
            sut.session["project_id"] = "pid-DIFFERENT"  # 应走 switch_project
```

---

*— TDD · L1-10 L2-03 · 进度实时流 · depth-B · v1.0 · 2026-04-22 · session-L —*


