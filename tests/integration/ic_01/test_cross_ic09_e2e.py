"""IC-01 · 跨 IC mini e2e · state_transition 触发 IC-09 审计落盘.

验证 L1-02 state_machine → L1-09 EventBus 协作:
    - 转换成功 · audit_sink 收到 TransitionResult · 可持久化到 IC-09
    - 转换失败(非法边) · 也会走 audit_sink 记录
    - audit_entry_id 回写到 TransitionResult
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.state_machine import StateMachineOrchestrator, TransitionResult


@pytest.fixture
def bus_root(tmp_path: Path) -> Path:
    return tmp_path / "bus_root"


@pytest.fixture
def real_bus(bus_root: Path) -> EventBus:
    return EventBus(bus_root)


class TestIC01CrossIC09MiniE2E:
    """IC-01 → IC-09: state_transition 成功时把 audit event 写真 EventBus."""

    def test_success_transition_emits_ic09_event(
        self, real_bus: EventBus, bus_root: Path, make_request, project_id: str,
    ) -> None:
        """audit_sink 注入 · 转换成功 → L1-02 state_transitioned 事件落盘.

        project_id 需用 L1-09 pattern (snake_case) · 这里构造系统级事件.
        """
        pid_pattern_ok = "proj_wp02_ic01_e2e"
        # 构造满足 L1-02 state_machine 格式要求的 pid(`pid-{hex}`)
        sm_pid = "pid-11111111-1111-1111-1111-111111111111"

        def audit_sink(res: TransitionResult) -> str:
            evt = Event(
                project_id=pid_pattern_ok,
                type="L1-02:state_transitioned",
                actor="main_loop",
                payload={
                    "transition_id": res.transition_id,
                    "new_state": res.new_state,
                    "accepted": res.accepted,
                    "sm_pid": sm_pid,
                },
                timestamp=datetime.now(UTC),
            )
            ret = real_bus.append(evt)
            return ret.event_id

        orch = StateMachineOrchestrator(
            project_id=sm_pid,
            initial_state="NOT_EXIST",
            audit_sink=audit_sink,
        )
        # 使用默认 make_request · 覆盖 pid 为 sm_pid
        req = make_request(
            project_id_override=sm_pid,
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
        )
        result = orch.transition(req)
        assert result.accepted is True
        assert result.audit_entry_id is not None
        assert result.audit_entry_id.startswith("evt_")

        # 真 bus 落盘
        events_path = bus_root / "projects" / pid_pattern_ok / "events.jsonl"
        assert events_path.exists()
        content = events_path.read_text()
        assert "L1-02:state_transitioned" in content
        assert result.transition_id in content

    def test_audit_sink_exception_does_not_break_transition(
        self, make_request, project_id: str,
    ) -> None:
        """审计失败不能回滚 state · TransitionResult.accepted 仍 True · audit_entry_id=None."""

        def broken_sink(_: TransitionResult) -> str:
            raise RuntimeError("audit bus down")

        orch = StateMachineOrchestrator(
            project_id=project_id,
            initial_state="NOT_EXIST",
            audit_sink=broken_sink,
        )
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
        )
        result = orch.transition(req)
        assert result.accepted is True
        assert result.new_state == "INITIALIZED"
        assert result.audit_entry_id is None   # 吞了异常 · 但状态机成功
        # state 已推进
        assert orch.get_current_state() == "INITIALIZED"
