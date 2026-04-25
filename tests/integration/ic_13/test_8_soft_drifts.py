"""IC-13 · 8 类软漂移 emit · 8 TC.

每类映射的 SDP id + 典型 content:
1. SDP-01 gate_overrun        · "FILE_TOO_LONG"
2. SDP-02 wp_loop             · "FUNC_TOO_LONG"
3. SDP-03 skill_fallback      · "NAMING_DRIFT"
4. SDP-04 kb_miss             · "DUPLICATE_CODE"
5. SDP-05 audit_tail          · "COVERAGE_DECREASE"
6. SDP-06 ui_panic            · "DOC_BROKEN_LINK"
7. SDP-07 verifier_reject     · "TODO_FIXME_ACCUMULATION"
8. SDP-08 state_reverse       · "PERFORMANCE_REGRESSION"

每条 TC 验证:
- pusher.push_suggestion 不抛
- ack.enqueued=True · ack.queue_len ≥ 1
- IC-09 audit `L1-07:suggestion_pushed` emitted (pid 一致)
- 严禁升格 IC-15 (level != BLOCK · BLOCK 在 schema 层就被拒)
"""
from __future__ import annotations

import asyncio

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import SuggestionLevel
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)


# 8 SDP × 8 软漂移内容 · 每条独立 TC
SOFT_DRIFTS = [
    ("SDP-01", "sugg-001", "FILE_TOO_LONG: file.py 超 800 行 · 建议拆模块"),
    ("SDP-02", "sugg-002", "FUNC_TOO_LONG: foo() 超 100 行 · 建议拆函数"),
    ("SDP-03", "sugg-003", "NAMING_DRIFT: 变量命名风格漂移 · camelCase 混 snake_case"),
    ("SDP-04", "sugg-004", "DUPLICATE_CODE: 检测到 5+ 处重复代码块"),
    ("SDP-05", "sugg-005", "COVERAGE_DECREASE: 测试覆盖率从 85% 降到 72%"),
    ("SDP-06", "sugg-006", "DOC_BROKEN_LINK: README 含 3 条失效链接"),
    ("SDP-07", "sugg-007", "TODO_FIXME_ACCUMULATION: TODO 累积超 50 条"),
    ("SDP-08", "sugg-008", "PERFORMANCE_REGRESSION: P99 延迟从 100ms 涨到 350ms"),
]


@pytest.mark.parametrize("sdp_id,sugg_id,content", SOFT_DRIFTS)
async def test_soft_drift_pushed_via_ic13(
    pusher: SuggestionPusher,
    consumer: MockSuggestionConsumer,
    supervisor_bus: EventBusStub,
    make_suggestion_command,
    project_id: str,
    sdp_id: str,
    sugg_id: str,
    content: str,
) -> None:
    """8 类软漂移分别 emit · IC-13 fire-and-forget · IC-09 审计 emit."""
    cmd = make_suggestion_command(
        suggestion_id=sugg_id,
        sdp_id=sdp_id,
        content=content,
        observation_refs=(f"ev-obs-{sdp_id}",),
    )

    ack = await pusher.push_suggestion(cmd)

    # ack 立即返回(fire-and-forget · 不等 consumer)
    assert ack.enqueued is True
    assert ack.queue_len >= 1
    assert ack.suggestion_id == sugg_id

    # IC-09 审计 · L1-07:suggestion_pushed
    audit_events = await supervisor_bus.read_event_stream(
        project_id=project_id,
        types=["L1-07:suggestion_pushed"],
    )
    assert len(audit_events) >= 1, (
        f"IC-13 不应跳过 IC-09 审计 · sdp={sdp_id} sugg={sugg_id}"
    )
    last = audit_events[-1]
    assert last.payload["suggestion_id"] == sugg_id
    assert last.payload["level"] == SuggestionLevel.WARN.value
    assert last.project_id == project_id

    # 让 drain task 完成 · consumer 也应被 deliver
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    # 严禁升格 IC-15: level 必须 != BLOCK
    assert cmd.level != "BLOCK"  # schema 已硬拦
    # 接收方记录(consumer 仅记录不阻断)
    assert any(
        d.suggestion_id == sugg_id for d in consumer.delivered
    ), f"接收方 L1-01/L2-06 应只记录 sugg={sugg_id}"
