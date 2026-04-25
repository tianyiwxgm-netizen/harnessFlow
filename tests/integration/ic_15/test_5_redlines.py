"""IC-15 · 5 类硬红线 + SLO + 用户授权 · 8 TC.

5 类硬红线:
- HRL-01 PM-14 违规     · "R-1: Shell 注入"  (将 IC-15 命中映射 R-1)
- HRL-02 审计链破损     · "R-2: 部署"
- HRL-03 可追溯率破损   · "R-3: secret 泄漏"
- HRL-04 UI panic miss · "R-4: 数据丢失"
- HRL-05 halt miss     · "R-5: 资源失控"

每条 TC 验证:
- HaltRequester 阻塞返回 ack.halted=True
- ack.halt_latency_ms <= 100ms (SLO)
- IC-09 audit `L1-01:hard_halted` 命中
- target state 转 HALTED

3 用户授权场景:
- TC-6 同 red_line_id 重发 · 幂等 · 返同 halt_id
- TC-7 SLO 违反(slow_halt_ms=120) · 仍 halted=True · audit emit halt_slo_violated
- TC-8 跨 pid halt 拒(E_HALT_NO_PROJECT_ID)
"""
from __future__ import annotations

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.event_sender.schemas import HardHaltState


# 5 红线 × 5 R-* 场景 · halt_id 满足 ^halt-[A-Za-z0-9_-]{3,}
REDLINES_TO_RISKS = [
    ("HRL-01", "halt-r1-shell", "R-1: Shell 注入命令拦截"),
    ("HRL-02", "halt-r2-deploy", "R-2: 部署生产硬拦截"),
    ("HRL-03", "halt-r3-secret", "R-3: Secret 泄漏拦截"),
    ("HRL-04", "halt-r4-data-loss", "R-4: 数据丢失拦截"),
    ("HRL-05", "halt-r5-resource", "R-5: 资源失控拦截"),
]


@pytest.mark.parametrize("red_line_id,halt_id,scenario", REDLINES_TO_RISKS)
async def test_5_redlines_block_within_100ms(
    halt_requester: HaltRequester,
    halt_target: MockHardHaltTarget,
    supervisor_bus: EventBusStub,
    make_halt_command,
    project_id: str,
    red_line_id: str,
    halt_id: str,
    scenario: str,
) -> None:
    """5 类硬红线命中 · halt 返回 ≤ 100ms · IC-09 hard_halted 审计."""
    cmd = make_halt_command(
        red_line_id=red_line_id,
        halt_id=halt_id,
        observation_refs=(f"ev-{red_line_id}-1", f"ev-{red_line_id}-2"),
    )

    ack = await halt_requester.request_hard_halt(cmd)

    # SLO + halted 状态
    assert ack.halted is True
    assert ack.halt_latency_ms <= 100, (
        f"IC-15 SLO 违反 red_line={red_line_id} latency={ack.halt_latency_ms}ms"
    )
    assert ack.state_after == HardHaltState.HALTED
    assert ack.state_before == HardHaltState.RUNNING

    # target 翻态
    assert halt_target.current_state == HardHaltState.HALTED
    assert halt_target.halt_call_count == 1

    # IC-09 hard_halted audit emit
    audits = await supervisor_bus.read_event_stream(
        project_id=project_id, types=["L1-01:hard_halted"],
    )
    assert len(audits) == 1
    assert audits[0].payload["red_line_id"] == red_line_id
    assert audits[0].payload["halt_id"] == halt_id
    assert audits[0].payload["latency_ms"] <= 100
    assert audits[0].payload["require_user_authorization"] is True


# ============================================================================
# 用户授权 / 幂等 / SLO 违反 / 跨 pid 拒 · 3 TC
# ============================================================================


async def test_idempotent_same_red_line_returns_first_halt(
    halt_requester: HaltRequester,
    halt_target: MockHardHaltTarget,
    make_halt_command,
) -> None:
    """同 red_line_id 重复请求 · 返第一个 halt_id 的 ack(§3.15.5 幂等)."""
    cmd1 = make_halt_command(
        red_line_id="HRL-01", halt_id="halt-first-call",
    )
    cmd2 = make_halt_command(
        red_line_id="HRL-01", halt_id="halt-second-call",
    )

    ack1 = await halt_requester.request_hard_halt(cmd1)
    ack2 = await halt_requester.request_hard_halt(cmd2)

    assert ack1.halt_id == "halt-first-call"
    assert ack2.halt_id == "halt-first-call"  # 幂等返第一条
    # target 只 halt 一次
    assert halt_target.halt_call_count == 1


async def test_slo_violation_emits_halt_slo_violated(
    project_id: str,
    halt_target_slow: MockHardHaltTarget,
    supervisor_bus: EventBusStub,
    make_halt_command,
) -> None:
    """slow_halt_ms=120 · latency > 100ms · 仍 halted=True · audit halt_slo_violated."""
    requester = HaltRequester(
        session_pid=project_id,
        target=halt_target_slow,
        event_bus=supervisor_bus,
    )
    cmd = make_halt_command(red_line_id="HRL-05", halt_id="halt-slow-target")

    ack = await requester.request_hard_halt(cmd)

    # halt 仍成功(safety first) · 但 SLO 违反 audit
    assert ack.halted is True
    assert ack.halt_latency_ms > 100

    audits = await supervisor_bus.read_event_stream(
        project_id=project_id, types=["L1-07:halt_slo_violated"],
    )
    assert len(audits) == 1
    assert audits[0].payload["release_blocker"] == "HRL-05"
    assert audits[0].payload["slo_target_ms"] == 100


async def test_cross_project_halt_rejected(
    halt_requester: HaltRequester,
    make_halt_command,
    other_project_id: str,
) -> None:
    """跨 project halt 拒 · E_HALT_NO_PROJECT_ID(主会话仲裁)."""
    bad_cmd = make_halt_command(
        red_line_id="HRL-01",
        halt_id="halt-cross-pid",
        pid_override=other_project_id,  # 与 requester.session_pid 不一致
    )
    with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID"):
        await halt_requester.request_hard_halt(bad_cmd)
