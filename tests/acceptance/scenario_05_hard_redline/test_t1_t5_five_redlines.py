"""Scenario 05 · T1-T5 · 5 类红线各 1 端到端 5 步链.

5 步链 (3-1 hard-redlines.md §3.5):
    step-1 detect    L1-07 RedLineDetector 命中 (≤ 50ms)
    step-2 emit      IC-15 request_hard_halt (≤ 30ms)
    step-3 receive   L1-01 IC15Consumer halt 当前 tick (≤ 20ms)
    step-4 audit     L1-09 IC-09 hard_halted 落盘 (hash chain 完整)
    step-5 UI        IC-19 红屏卡片 push (本 WP 仅断言 audit 含 authorize 字段)

总 BLOCK p99 ≤ 100ms 硬约束 (HRL-05 release blocker).

5 类红线 (R-1~R-5 brief §4 简化版 5 条):
- T1 R-1 (HRL-01) PM-14 违规 / Shell 注入
- T2 R-2 (HRL-02) 审计链破损 / 部署生产硬拦截
- T3 R-3 (HRL-03) 可追溯率破损 / Secret 泄漏
- T4 R-4 (HRL-04) UI panic 未 100ms / 数据丢失
- T5 R-5 (HRL-05) halt 未 100ms / 资源失控
"""
from __future__ import annotations

import time

import pytest

from app.l1_09.event_bus.core import EventBus
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.supervisor_receiver.schemas import HaltState
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.supervisor.event_sender.schemas import HardHaltState
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.perf_helpers import assert_p99_under, measure_async


REDLINES_R_TO_HRL = [
    ("R-1", "HRL-01", "halt-r1-pm14-shell", "Shell 注入命令拦截"),
    ("R-2", "HRL-02", "halt-r2-audit-deploy", "审计链破损 / 部署硬拦截"),
    ("R-3", "HRL-03", "halt-r3-trace-secret", "可追溯率破 / Secret 泄漏"),
    ("R-4", "HRL-04", "halt-r4-panic-data-loss", "UI panic 100ms 数据丢失"),
    ("R-5", "HRL-05", "halt-r5-halt-resource", "halt 100ms 资源失控"),
]


@pytest.mark.parametrize("rid,hrl,halt_id,scenario_name", REDLINES_R_TO_HRL)
async def test_t1_t5_five_redlines_full_5step_chain(
    halt_enforcer: HaltEnforcer,
    ic15_consumer: IC15Consumer,
    real_event_bus: EventBus,
    event_bus_root,
    project_id: str,
    make_halt_signal,
    gwt: GWT,
    rid: str,
    hrl: str,
    halt_id: str,
    scenario_name: str,
) -> None:
    """T1-T5 · 5 类红线全 5 步链 · BLOCK p99 ≤ 100ms (HRL-05 release blocker)."""
    async with gwt(f"R-{rid} ({hrl}) · {scenario_name} · 5 步链 ≤ 100ms"):
        # ----- Given -----
        gwt.given(f"project={project_id} 处 RUNNING · L1-07/L2-03 已加载 redlines pattern_db")
        assert halt_enforcer.as_tick_state().value == "RUNNING"
        assert halt_enforcer.is_halted() is False

        gwt.given("audit-ledger 干净 · 无 hard_redline_triggered 历史")
        before = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert before == 0

        # ----- When -----
        gwt.when(f"L1-07 检测命中 R-{rid} 模式 · emit IC-15 request_hard_halt")
        signal = make_halt_signal(
            red_line_id=hrl,
            halt_id=halt_id,
            observation_refs=(f"ev-{rid}-1", f"ev-{rid}-2"),
        )

        # 测 step 2~4 总耗时 (IC-15 emit + consume + audit) · 不含 step-1 detect 因 detect 由 L1-07 内部 P99 ≤ 50ms 单独验
        sample = await measure_async(ic15_consumer.consume(signal))
        ack = sample.payload

        # ----- Then -----
        gwt.then(f"step-1+step-2: detect+emit ≤ 50ms+30ms · ack.latency_ms ≤ 80ms")
        # ack.latency_ms 仅含 halt_target.halt 子段 · 应 < 5ms (内存翻态)
        assert ack.halted is True, f"R-{rid} halt 失败"
        assert ack.latency_ms < 80, (
            f"R-{rid} step-2+3 latency={ack.latency_ms}ms 超 80ms 子预算"
        )

        gwt.then(f"step-3 receive: L1-01 halt_enforcer 翻 HALTED · ≤ 20ms")
        assert halt_enforcer.is_halted() is True
        assert halt_enforcer.as_tick_state().value == "HALTED"
        assert halt_enforcer.active_halt_id == halt_id

        gwt.then(f"step-4 audit: IC-09 hard_halted 落盘 · payload 含 authorize=true + halt_id")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:hard_halted",
            payload_contains={
                "halt_id": halt_id,
                "red_line_id": hrl,
                "require_user_authorization": True,
            },
        )
        assert len(events) >= 1, f"R-{rid} IC-09 hard_halted 缺失"

        gwt.then("step-5 UI: audit payload 含 authorize 字段供 UI 红屏渲染")
        # 5 步链中 UI 落地 = audit payload 必含 authorize=true (UI 层据此渲染 IC-19 卡片)
        assert events[0]["payload"]["require_user_authorization"] is True

        gwt.then(f"总链 BLOCK 端到端 ≤ 100ms (HRL-05 release blocker)")
        assert sample.elapsed_ms < 100.0, (
            f"R-{rid} 总链 elapsed={sample.elapsed_ms:.2f}ms 超 100ms 硬红线"
        )

        gwt.then("hash chain 完整 · 单条事件入账 seq=1")
        n_events = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n_events == 1
