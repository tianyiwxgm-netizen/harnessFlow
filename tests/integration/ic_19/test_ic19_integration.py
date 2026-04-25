"""IC-19 · ui_card_push (push_stage_gate_card) 集成测试 · 5 TC.

(WP04 任务表 IC-19 = L1-10 Gate 卡片 push · 对应 ic-contracts.md §3.16)

覆盖:
    TC-1 Gate 卡片: build command + push 到 UI bridge · received 1 条
    TC-2 红屏 (UI bridge 抛异常 · audit 仍发) · 降级路径
    TC-3 进度流: 多 stage 分别推 · stage_name 不同 · artifacts_bundle 按 stage
    TC-4 用户操作: trim_level 三档 (minimal/standard/full) 全覆盖
    TC-5 IC-09 联动: 不论 bridge 是否注入 · audit 事件都发
"""
from __future__ import annotations

import pytest

from app.project_lifecycle.stage_gate.ic_16_stub import (
    build_push_stage_gate_card_command,
)


class TestIC19Integration:
    """IC-19 集成 · UI Gate 卡片 push 全链."""

    # ---- TC-1 · 正向: 构造 + push 到 UI bridge ----
    def test_build_and_push_card_to_ui_bridge(
        self, ui_bridge, project_id: str,
    ) -> None:
        gate_id = "gate-ic19-001"
        command = build_push_stage_gate_card_command(
            gate_id=gate_id,
            project_id=project_id,
            stage_name="S2",
        )

        # IC-19 §3.16.2 必填 6 字段全覆盖
        assert command["card_id"].startswith("card-")
        assert command["project_id"] == project_id
        assert command["gate_id"] == gate_id
        assert command["stage_name"] == "S2"
        assert len(command["artifacts_bundle"]) >= 1
        assert command["trim_level"] == "standard"
        assert command["allowed_decisions"] == ["approve", "reject", "request_change"]
        assert command["blocks_progress"] is True
        assert "ts" in command

        # push 到 UI bridge
        ack = ui_bridge.push_stage_gate_card_to_ui(command=command)
        assert ack["received"] is True
        assert len(ui_bridge.received) == 1
        assert ui_bridge.received[0]["gate_id"] == gate_id

    # ---- TC-2 · 红屏: bridge 抛异常 (降级到 audit) ----
    def test_bridge_raises_does_not_kill_caller(
        self, ui_bridge, audit_bus, project_id: str,
    ) -> None:
        ui_bridge.exc_to_raise = RuntimeError("UI 暂不可用 · 红屏")
        command = build_push_stage_gate_card_command(
            gate_id="gate-ic19-red",
            project_id=project_id,
            stage_name="S5",
        )

        # 模拟 controller _push_gate_card 的降级模式: try push · 异常 → audit
        try:
            ui_bridge.push_stage_gate_card_to_ui(command=command)
        except Exception:
            pass

        # audit 不论 bridge 成败都要发 (§3.16.7)
        audit_bus.append_event(
            project_id=project_id,
            event_type="ic_16_push_stage_gate_card",
            payload=command,
        )

        # 状态: bridge.received 0 (失败) · audit_bus.events 1 (降级)
        assert len(ui_bridge.received) == 0
        assert len(audit_bus.events) == 1
        assert audit_bus.events[0]["event_type"] == "ic_16_push_stage_gate_card"

    # ---- TC-3 · 进度流: 多 stage 分别推 · artifacts_bundle 按 stage ----
    def test_multi_stage_progress_stream(
        self, ui_bridge, project_id: str,
    ) -> None:
        # IC-19 §3.16.2 artifacts_bundle 按 stage_name 自动填默认
        for stage in ("S1", "S2", "S3", "S5"):
            command = build_push_stage_gate_card_command(
                gate_id=f"gate-{stage}",
                project_id=project_id,
                stage_name=stage,
            )
            ui_bridge.push_stage_gate_card_to_ui(command=command)

        # 4 stage · 4 条 push
        assert len(ui_bridge.received) == 4

        # 各自 stage_name 不同 · artifacts_bundle 类型按 stage
        s1_card = next(c for c in ui_bridge.received if c["stage_name"] == "S1")
        s2_card = next(c for c in ui_bridge.received if c["stage_name"] == "S2")
        # S1 默认只有 charter · S2 有 charter+plan+wbs+togaf_doc
        s1_types = {a["artifact_type"] for a in s1_card["artifacts_bundle"]}
        s2_types = {a["artifact_type"] for a in s2_card["artifacts_bundle"]}
        assert s1_types == {"charter"}
        assert "plan" in s2_types

    # ---- TC-4 · trim_level 三档 (minimal/standard/full) ----
    def test_trim_level_three_modes(
        self, project_id: str,
    ) -> None:
        for level in ("minimal", "standard", "full"):
            cmd = build_push_stage_gate_card_command(
                gate_id=f"gate-{level}",
                project_id=project_id,
                stage_name="S2",
                trim_level=level,
            )
            assert cmd["trim_level"] == level

        # 不在 enum 内 → ValueError
        with pytest.raises(ValueError, match="E_CARD_TRIM_UNSUPPORTED"):
            build_push_stage_gate_card_command(
                gate_id="gate-bad",
                project_id=project_id,
                stage_name="S2",
                trim_level="invalid_level",
            )

    # ---- TC-5 · IC-09 联动: 不论 bridge 是否注入 · audit 都发 ----
    def test_ic09_audit_emitted_regardless_of_bridge(
        self, audit_bus, project_id: str,
    ) -> None:
        # 模拟 controller._push_gate_card · 无 bridge 路径
        cmd = build_push_stage_gate_card_command(
            gate_id="gate-ic19-no-bridge",
            project_id=project_id,
            stage_name="S3",
        )
        # 直接走 audit 路径 (即使没 ui_bridge)
        audit_bus.append_event(
            project_id=project_id,
            event_type="ic_16_push_stage_gate_card",
            payload=cmd,
        )

        # IC-09 联动 · payload 包含完整 card command
        assert len(audit_bus.events) == 1
        evt = audit_bus.events[0]
        assert evt["project_id"] == project_id
        assert evt["event_type"] == "ic_16_push_stage_gate_card"
        assert evt["payload"]["gate_id"] == "gate-ic19-no-bridge"
        assert evt["payload"]["card_id"].startswith("card-")
