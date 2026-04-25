"""Scenario 01 · T10 · 全程 < 5min (用 mock LLM · 不调真 LLM).

happy-path 跑完 7 stage + 14 verdict 不应超 5min (300s).
本 TC 用 wall clock 测 emit 14 verdict + 7 stage 的 audit 总耗时
(mock LLM 替代下应 < 1s · 留 5min budget 完全富余).
"""
from __future__ import annotations

import time

from app.l1_09.event_bus.core import EventBus
from tests.acceptance.scenario_01_normal_flow.conftest import (
    HAPPY_STAGES,
    HAPPY_VERDICTS,
)
from tests.shared.gwt_helpers import GWT


def test_t10_full_happy_path_under_5min(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_audit,
    gwt: GWT,
) -> None:
    """T10 · happy-path 7 stage + 14 verdict 全跑 < 5min (mock LLM)."""
    with gwt("T10 · happy-path 全程 < 5min"):
        gwt.given("audit 干净 · LLM mock (本 TC 不调外部)")

        gwt.when("跑 7 stage_gate + 14 verdict_decided · 测 wall clock 总耗时")
        t0 = time.monotonic()

        for i, stage in enumerate(HAPPY_STAGES):
            emit_audit(
                "L1-02:gate_decision",
                {"stage": stage, "decision": "pass", "seq": i},
            )
        for vid, stage, signal in HAPPY_VERDICTS:
            emit_audit(
                "L1-02:verdict_decided",
                {
                    "verdict_id": f"v{vid:02d}",
                    "stage": stage,
                    "signal": signal,
                    "verdict": "PASS",
                },
            )

        elapsed_s = time.monotonic() - t0

        gwt.then(f"全程 elapsed={elapsed_s:.3f}s ≤ 300s (5min · happy-path SLO)")
        assert elapsed_s < 300.0, (
            f"happy-path 全程 {elapsed_s:.2f}s 超 5min budget"
        )
        # mock 路径下应远快于 1s · 留全部 budget 给真 LLM 替换后的 SLO
        assert elapsed_s < 5.0, (
            f"mock 路径不应 > 5s · 实际 {elapsed_s:.3f}s · 检查 audit 慢路径"
        )
