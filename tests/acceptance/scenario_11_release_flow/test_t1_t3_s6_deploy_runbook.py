"""Scenario 11 · T1-T3 · S6 准备 + deploy dry-run + runbook 校验.

T1: S6 已通过 acceptance-criteria · audit 含 acceptance_passed
T2: deploy script dry-run 绿 · executable + 语法合法
T3: runbook 完整 · 含 prerequisites / steps / rollback 三段
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


def test_t1_s6_acceptance_criteria_passed(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_release_event,
    gwt: GWT,
) -> None:
    """T1 · S6 已通过 acceptance criteria · audit 落 acceptance_passed."""
    with gwt("T1 · S6 acceptance criteria passed"):
        gwt.given("S5 verifier 全 PASS · S6 acceptance check 准备")

        gwt.when("emit acceptance_criteria_passed audit")
        emit_release_event(
            "L1-02:acceptance_criteria_passed",
            {
                "stage": "S6",
                "criteria_count": 7,
                "criteria_passed": 7,
                "ready_for_release": True,
            },
        )

        gwt.then("audit 含 ready_for_release=True · 全 7 项过")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:acceptance_criteria_passed",
            payload_contains={
                "stage": "S6",
                "ready_for_release": True,
                "criteria_passed": 7,
            },
        )
        assert len(events) == 1


def test_t2_deploy_script_dry_run_green(
    deploy_script: Path,
    gwt: GWT,
) -> None:
    """T2 · deploy.sh executable + dry-run (bash -n 语法检查) 绿."""
    with gwt("T2 · deploy script dry-run 绿"):
        gwt.given(f"deploy.sh 存在 · 路径={deploy_script}")
        assert deploy_script.exists()

        gwt.then("deploy.sh executable bit 已置 (硬约束)")
        st = deploy_script.stat()
        assert st.st_mode & stat.S_IXUSR, "deploy.sh missing executable bit"

        gwt.when("bash -n dry-run · 语法检查")
        result = subprocess.run(
            ["bash", "-n", str(deploy_script)],
            capture_output=True,
            text=True,
        )

        gwt.then("dry-run rc=0 · 语法合法")
        assert result.returncode == 0, (
            f"deploy.sh syntax error · stderr={result.stderr}"
        )


def test_t3_runbook_required_sections(
    runbook: Path,
    gwt: GWT,
) -> None:
    """T3 · runbook 必含 prerequisites / steps / rollback 三段."""
    with gwt("T3 · runbook 三段完整"):
        gwt.given(f"runbook.md 存在 · 路径={runbook}")
        assert runbook.exists()

        content = runbook.read_text(encoding="utf-8")

        gwt.then("含 prerequisites / steps / rollback 三段")
        for section in ["## prerequisites", "## steps", "## rollback"]:
            assert section in content, (
                f"runbook 缺 {section} 段 · 实际 content[:200]={content[:200]}"
            )
