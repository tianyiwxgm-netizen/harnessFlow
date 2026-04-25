"""Scenario 11 · T4-T6 · changelog + user signoff + acceptance checklist 签字.

T4: changelog 完整 · 含 version + change list
T5: user_signoff (PM, S6) · audit 含 user_id + role
T6: acceptance_checklist 签字 · 全 7 criteria 必带 signed_by
"""
from __future__ import annotations

from pathlib import Path

from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


def test_t4_changelog_complete(changelog: Path, gwt: GWT) -> None:
    """T4 · CHANGELOG.md 含 version + change list."""
    with gwt("T4 · CHANGELOG 完整"):
        gwt.given(f"changelog.md 存在 · 路径={changelog}")
        assert changelog.exists()
        content = changelog.read_text(encoding="utf-8")

        gwt.then("含 version 标记 (## v 开头) + 至少 1 条 change item")
        assert "## v" in content, f"CHANGELOG 缺 version 标记 · {content[:200]}"
        # change list 用 - 开头
        items = [ln for ln in content.splitlines() if ln.startswith("- ")]
        assert len(items) >= 1, "CHANGELOG 缺 change item · 应 ≥ 1 条"


def test_t5_user_signoff_pm_s6(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T5 · user_signoff · S6 阶段 PM 角色签字 · audit 含 user_id + role."""
    with gwt("T5 · user_signoff (PM, S6)"):
        gwt.given("project 在 S6 准备 release · PM 需 user signoff")

        gwt.when("PM 在 UI 签字 · emit user_signoff")
        emit_release_event(
            "L1-02:user_signoff",
            {
                "stage": "S6",
                "role": "PM",
                "user_id": "pm-user-1",
                "signoff_at": "2026-04-24T10:00:00Z",
                "signoff_decision": "approved",
            },
        )

        gwt.then("audit 含 stage=S6 + role=PM + user_id + decision=approved")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:user_signoff",
            payload_contains={
                "stage": "S6",
                "role": "PM",
                "signoff_decision": "approved",
            },
        )
        assert len(events) == 1
        assert events[0]["payload"]["user_id"] == "pm-user-1"


def test_t6_acceptance_checklist_signed(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T6 · acceptance_checklist 7 项全签字 · 每项必带 signed_by."""
    with gwt("T6 · acceptance_checklist 7 项签字"):
        gwt.given("7 项 acceptance criteria 待签 · 各自 signed_by 必填")
        criteria = [
            ("ac-1", "deploy_script_executable"),
            ("ac-2", "runbook_exists"),
            ("ac-3", "changelog_complete"),
            ("ac-4", "test_suite_green"),
            ("ac-5", "documentation_updated"),
            ("ac-6", "rollback_path_verified"),
            ("ac-7", "acceptance_passed"),
        ]

        gwt.when("依次 emit 7 项 checklist_signed audit · signer=user-pm")
        for ac_id, name in criteria:
            emit_release_event(
                "L1-02:checklist_signed",
                {
                    "criteria_id": ac_id,
                    "criteria_name": name,
                    "signed_by": "user-pm",
                    "signed": True,
                },
            )

        gwt.then("7 条 audit · 全 signed=True · 每条 signed_by=user-pm")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:checklist_signed",
            min_count=7,
        )
        assert len(events) == 7
        for evt in events:
            assert evt["payload"]["signed"] is True
            assert evt["payload"]["signed_by"] == "user-pm"
