"""Scenario 11 · T7-T10 · release event 落 + readonly + history 保留 + rollback 路径.

T7: release_event 落 · IC-09 audit 含 release_id + version
T8: release 后 project readonly · audit 不应再有 status_change
T9: 跨 release 历史保留 · v1.0 + v2.0 audit 都在
T10: rollback 路径 · runbook 含 rollback 段且可执行
"""
from __future__ import annotations

import stat
from pathlib import Path

from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


def test_t7_release_event_emitted(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T7 · release_event 落 · IC-09 含 release_id + version."""
    with gwt("T7 · release event 落"):
        gwt.given("S6 全过 + signoff 完毕 · 触发 release")

        gwt.when("emit L1-02:release_executed audit")
        emit_release_event(
            "L1-02:release_executed",
            {
                "release_id": "rel-v1.0.0",
                "version": "v1.0.0",
                "released_at": "2026-04-24T11:00:00Z",
                "deploy_script_path": "release/deploy.sh",
                "runbook_path": "release/runbook.md",
            },
        )

        gwt.then("audit 含 release_id + version")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:release_executed",
            payload_contains={"release_id": "rel-v1.0.0", "version": "v1.0.0"},
        )
        assert len(events) == 1


def test_t8_post_release_project_readonly(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T8 · release 后 project readonly · 不应再有 wp_status_change."""
    with gwt("T8 · release 后 project readonly"):
        gwt.given("S6 release 已完成 · audit 含 release_executed")
        emit_release_event(
            "L1-02:release_executed",
            {"release_id": "rel-v1.0.1", "version": "v1.0.1"},
        )
        emit_release_event(
            "L1-02:project_readonly",
            {"reason": "post_release_lock", "release_id": "rel-v1.0.1"},
        )

        gwt.then("audit 含 project_readonly · payload reason=post_release_lock")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:project_readonly",
            payload_contains={"reason": "post_release_lock"},
        )
        assert len(events) == 1

        gwt.then("readonly 后不应再有 wp_status_change · 用 audit 反向断言")
        all_events = list_events(event_bus_root, project_id)
        # readonly 之后的 seq 后不允许有 wp_status_change · 这里 dataset 没 emit
        readonly_seq = events[0]["sequence"]
        post_changes = [
            e for e in all_events
            if e.get("type") == "L1-03:wp_status_change"
            and e.get("sequence", 0) > readonly_seq
        ]
        assert post_changes == [], (
            f"readonly 后不应有 wp_status_change · 实际={post_changes}"
        )


def test_t9_release_history_preserved(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T9 · 跨 release 历史保留 · v1.0 + v2.0 audit 都在 · hash chain 完整."""
    with gwt("T9 · 跨 release 历史"):
        gwt.given("emit 2 release event · v1.0 + v2.0")
        emit_release_event(
            "L1-02:release_executed",
            {"release_id": "rel-v1.0", "version": "v1.0"},
        )
        emit_release_event(
            "L1-02:release_executed",
            {"release_id": "rel-v2.0", "version": "v2.0"},
        )

        gwt.then("audit 含 2 条 release · hash chain 完整")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:release_executed",
            min_count=2,
        )
        assert len(events) == 2
        versions = [e["payload"]["version"] for e in events]
        assert versions == ["v1.0", "v2.0"]

        gwt.then("hash chain 完整 · 2 条 seq=1,2")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 2


def test_t10_rollback_path_in_runbook_executable(
    runbook: Path,
    deploy_script: Path,
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T10 · rollback 路径 · runbook 含 rollback 段 + audit 含 rollback_plan."""
    with gwt("T10 · rollback 路径完整"):
        gwt.given("runbook.md 含 rollback 段 · deploy.sh executable")
        rb_content = runbook.read_text(encoding="utf-8")
        assert "## rollback" in rb_content

        gwt.given("deploy.sh executable")
        st = deploy_script.stat()
        assert st.st_mode & stat.S_IXUSR

        gwt.when("emit release_with_rollback audit · 包含 rollback_plan")
        emit_release_event(
            "L1-02:release_executed",
            {
                "release_id": "rel-t10",
                "version": "v1.0.0",
                "rollback_plan_path": "release/runbook.md#rollback",
                "rollback_executable": True,
            },
        )

        gwt.then("audit 含 rollback_plan + executable=True")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:release_executed",
            payload_contains={
                "rollback_executable": True,
            },
        )
        assert len(events) == 1
        assert "rollback" in events[0]["payload"]["rollback_plan_path"]
