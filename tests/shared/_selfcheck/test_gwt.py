"""Smoke: GWT DSL 形态 · 步骤链 · 上下文管理器."""
from __future__ import annotations

import pytest


def test_gwt_records_steps(gwt) -> None:
    gwt.given("empty project").and_("seed wbs")
    gwt.when("tick once")
    gwt.then("state = RUNNING")
    assert len(gwt.steps) == 4
    assert gwt.steps[0].phase == "given"
    assert gwt.steps[1].phase == "and"
    assert gwt.steps[2].phase == "when"
    assert gwt.steps[3].phase == "then"


def test_gwt_summary_contains_all_phases(gwt) -> None:
    gwt.given("g").when("w").then("t")
    s = gwt.summary()
    assert "GIVEN" in s
    assert "WHEN" in s
    assert "THEN" in s


@pytest.mark.asyncio
async def test_gwt_async_context_manager(gwt) -> None:
    async with gwt:
        gwt.given("ctx entered")
        gwt.when("inside async with")
        gwt.then("normal exit")
    assert len(gwt.steps) == 3


def test_gwt_sync_context_manager(gwt) -> None:
    with gwt:
        gwt.given("sync ctx")
        gwt.then("ok")
    assert len(gwt.steps) == 2


def test_gwt_scenario_defaults_to_test_name(gwt) -> None:
    # request.node.name = "test_gwt_scenario_defaults_to_test_name"
    assert "test_gwt_scenario_defaults_to_test_name" in gwt.scenario


def test_gwt_custom_scenario_name(gwt) -> None:
    gwt("my-custom-scenario")
    assert gwt.scenario == "my-custom-scenario"
