"""Unit tests for archive/retro_renderer.py."""

import json
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from archive.retro_renderer import (  # noqa: E402
    TBD,
    derive_1_dod_diff,
    derive_2_route_drift,
    derive_3_retry_breakdown,
    derive_4_verifier_fail,
    derive_5_user_interrupts,
    derive_6_time,
    derive_7_cost,
    derive_8_traps,
    derive_9_combos,
    derive_10_evolution,
    derive_11_next,
    render_retro,
)


ELEVEN_SECTIONS = [
    "## 1. DoD 实际 diff",
    "## 2. 路线偏差",
    "## 3. 纠偏次数",
    "## 4. Verifier FAIL 次数",
    "## 5. 用户打断次数",
    "## 6. 耗时 vs 估算",
    "## 7. 成本 vs 估算",
    "## 8. 新发现的 trap",
    "## 9. 新发现的有效组合",
    "## 10. 进化建议",
    "## 11. 下次推荐",
]


@pytest.fixture
def p20_task_board(tmp_path):
    tb_path = tmp_path / "tb.json"
    tb = {
        "task_id": "p20-fake",
        "project": "aigcv2",
        "route_id": "C",
        "initial_route_recommendation": "B",
        "size": "XL",
        "task_type": "视频出片",
        "risk": "中",
        "current_state": "CLOSED",
        "dod_expression": 'file_exists("p.mp4") AND oss_head("u").status_code == 200',
        "route_changes": [
            {"from_route": "B", "to_route": "C", "reason": "视频路线需 seedance", "approved_by": "user"},
        ],
        "retries": [
            {"level": "L0", "state": "IMPL", "err_class": "tts_timeout", "trigger": "api_slow"},
            {"level": "L1", "state": "IMPL", "err_class": "oss_403", "trigger": "sign_fail"},
        ],
        "red_lines": [{"code": "DOD_GAP_ALERT"}, {"code": "DRIFT_CRITICAL"}],
        "supervisor_interventions": [{"severity": "WARN", "code": "slow_impl"}],
        "time_budget": {"cap_sec": 3600, "elapsed_sec": 1800},
        "cost_budget": {"token_used": 58000, "token_cap": 120000, "cost_usd": 0.42},
        "final_outcome": "failed",
    }
    tb_path.write_text(json.dumps(tb))
    return tb_path


@pytest.fixture
def p20_verifier_report(tmp_path):
    vr = tmp_path / "vr.json"
    vr.write_text(json.dumps({
        "task_id": "p20-fake",
        "verdict": "FAIL",
        "priority_applied": "P0_red_line",
        "failed_conditions": ['oss_head("u").status_code == 200'],
        "red_lines": ["DOD_GAP_ALERT"],
        "evidence_chain": {
            "existence": [{"primitive": "file_exists", "expected": True, "actual": True, "passed": True}],
            "behavior": [{"primitive": "oss_head", "expected": 200, "actual": 403, "passed": False}],
            "quality": [],
        },
        "insufficient_evidence_count_after_this": 0,
    }))
    return vr


def test_render_produces_all_eleven_sections(p20_task_board, p20_verifier_report, tmp_path):
    out_dir = tmp_path / "retros"
    path = render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        out_dir=out_dir,
    )
    text = Path(path).read_text(encoding="utf-8")
    for section in ELEVEN_SECTIONS:
        assert section in text, f"section missing: {section!r}"


def test_render_contains_retro_boundary(p20_task_board, p20_verifier_report, tmp_path):
    out_dir = tmp_path / "retros"
    path = render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        out_dir=out_dir,
    )
    text = Path(path).read_text(encoding="utf-8")
    assert "<!-- retro-p20-fake-" in text
    assert "<!-- /retro-p20-fake-" in text


def test_dod_diff_contains_oss_head_fail(p20_task_board, p20_verifier_report, tmp_path):
    out_dir = tmp_path / "retros"
    path = render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        out_dir=out_dir,
    )
    text = Path(path).read_text(encoding="utf-8")
    # oss_head primitive row should show FAIL
    assert "oss_head" in text
    # At least one row with verdict FAIL
    assert "FAIL" in text


def test_empty_retro_notes_use_placeholder(p20_task_board, p20_verifier_report, tmp_path):
    out_dir = tmp_path / "retros"
    path = render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        retro_notes_path=None,
        out_dir=out_dir,
    )
    text = Path(path).read_text(encoding="utf-8")
    # Items 8-11 should show <待人工补充> since no retro_notes supplied
    assert "<待人工补充>" in text


def test_idempotent_two_calls_two_blocks(p20_task_board, p20_verifier_report, tmp_path):
    out_dir = tmp_path / "retros"
    render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        out_dir=out_dir,
    )
    time.sleep(1.1)  # ensure different ts
    render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        out_dir=out_dir,
    )
    text = (out_dir / "p20-fake.md").read_text(encoding="utf-8")
    opens = text.count("<!-- retro-p20-fake-")
    closes = text.count("<!-- /retro-p20-fake-")
    assert opens == 2, f"expected 2 open boundaries; got {opens}"
    assert closes == 2


def test_derive_1_dod_diff_handles_no_report(p20_task_board):
    tb = json.loads(p20_task_board.read_text())
    out = derive_1_dod_diff(tb, None)
    assert "dod_expression" in out
    assert "dod_diff_table" in out


def test_derive_2_detects_drift(p20_task_board):
    tb = json.loads(p20_task_board.read_text())
    out = derive_2_route_drift(tb, [])
    assert out["route_drifted"] == "是"
    assert out["initial_route_recommendation"] == "B"
    assert out["route"] == "C"


def test_derive_3_retry_levels(p20_task_board):
    tb = json.loads(p20_task_board.read_text())
    out = derive_3_retry_breakdown(tb)
    assert out["retry_count"] == "2"
    assert out["retry_l0_count"] == "1"
    assert out["retry_l1_count"] == "1"
    assert out["retry_l2_count"] == "0"


def test_derive_5_counts_red_lines(p20_task_board):
    tb = json.loads(p20_task_board.read_text())
    out = derive_5_user_interrupts(tb)
    assert out["interrupt_drift_count"] == "1"
    assert out["interrupt_dod_gap_count"] == "1"


def test_retro_notes_fill_items_8_11(p20_task_board, p20_verifier_report, tmp_path):
    notes_path = tmp_path / "notes.json"
    notes_path.write_text(json.dumps({
        "new_traps": ["trap-oss-silent"],
        "new_combinations": ["combo-seedance+oss"],
        "evolution_suggestions": ["降 C 权重 *= 0.8"],
        "next_recommendation": "先验证 oss 再过 VERIFY",
        "next_route_hint": "B",
        "next_must_verify": "oss_head, ffprobe_duration",
        "next_traps_to_avoid": "trap-oss-silent",
    }))
    out_dir = tmp_path / "retros"
    path = render_retro(
        task_id="p20-fake",
        task_board_path=p20_task_board,
        verifier_report_path=p20_verifier_report,
        retro_notes_path=notes_path,
        out_dir=out_dir,
    )
    text = Path(path).read_text(encoding="utf-8")
    assert "trap-oss-silent" in text
    assert "combo-seedance+oss" in text
    assert "先验证 oss 再过 VERIFY" in text


# --- Phase 7 P1-5 follow-up: helper-level happy + failure coverage ---


def test_derive_4_handles_no_report():
    out = derive_4_verifier_fail(None)
    assert out["verifier_fail_breakdown"] == TBD
    assert out["red_lines_triggered"] == TBD


def test_derive_4_counts_primitive_frequencies():
    vr = {
        "verdict": "FAIL",
        "failed_conditions": [
            'oss_head("u").status_code == 200',
            'oss_head("v").status_code == 200',
            'ffprobe_duration("p.mp4") > 0',
        ],
        "red_lines": ["DOD_GAP_ALERT"],
    }
    out = derive_4_verifier_fail(vr)
    assert "oss_head" in out["verifier_fail_breakdown"]
    assert "2 次" in out["verifier_fail_breakdown"]
    assert "ffprobe_duration" in out["verifier_fail_breakdown"]
    assert out["red_lines_triggered"] == "DOD_GAP_ALERT"


def test_derive_6_time_missing_budget():
    # cap=0 触发除零；全缺应返回 TBD 不 crash
    out = derive_6_time({})
    assert out["time_budget_min"] == TBD
    assert out["elapsed_min"] == TBD
    assert out["time_delta_pct"] == TBD


def test_derive_6_time_zero_cap_no_divzero():
    out = derive_6_time({"time_budget": {"cap_sec": 0, "elapsed_sec": 120}})
    # cap_min 会被 round(0/60)=0，falsy 走 TBD 分支，不 crash
    assert out["time_delta_pct"] == TBD


def test_derive_7_cost_missing_budget():
    out = derive_7_cost({})
    assert out["token_budget"] == TBD
    assert out["token_used"] == TBD
    assert out["token_delta_pct"] == TBD
    assert out["api_cost"] == TBD


def test_derive_7_cost_normal_case():
    out = derive_7_cost({
        "cost_budget": {"token_used": 12000, "token_cap": 10000, "cost_usd": 0.42}
    })
    assert out["token_used"] == "12000"
    assert out["token_budget"] == "10000"
    assert out["token_delta_pct"] == "+20.0%"
    assert out["api_cost"] == "$0.42"


def test_derive_8_traps_empty_notes():
    assert derive_8_traps(None)["new_traps_found"] == TBD
    assert derive_8_traps({})["new_traps_found"] == TBD


def test_derive_8_traps_list_and_string():
    out_list = derive_8_traps({"new_traps": ["trap-a", "trap-b"]})
    assert "trap-a" in out_list["new_traps_found"]
    assert "trap-b" in out_list["new_traps_found"]
    out_str = derive_8_traps({"new_traps": "single-trap"})
    assert out_str["new_traps_found"] == "single-trap"


def test_derive_9_combos_empty_and_list():
    assert derive_9_combos(None)["new_effective_combinations"] == TBD
    out = derive_9_combos({"new_combinations": ["seedance+oss"]})
    assert "seedance+oss" in out["new_effective_combinations"]


def test_derive_10_evolution_with_and_without_audit():
    # 无 notes + 无 audit link
    a = derive_10_evolution(None, None)
    assert a["evolution_suggestions"] == TBD
    assert a["audit_report_link"] == TBD
    # 有 notes list + 有 audit link
    b = derive_10_evolution(
        {"evolution_suggestions": ["降 C 权重 *= 0.8", "补 must_verify"]},
        "audit-reports/audit-20260417T010000Z.json",
    )
    assert "降 C 权重" in b["evolution_suggestions"]
    assert "audit-20260417T010000Z" in b["audit_report_link"]


def test_derive_11_next_all_missing_returns_tbd():
    out = derive_11_next(None, {})
    assert out["next_time_recommendation"] == TBD
    assert out["next_route_hint"] == TBD
    assert out["next_must_verify"] == TBD
    assert out["next_traps_to_avoid"] == TBD


def test_derive_11_next_partial_notes():
    # 部分填写：别的字段不应 crash，只补自己有的
    out = derive_11_next(
        {"next_recommendation": "下次先起 uvicorn", "next_route_hint": "B"},
        {},
    )
    assert out["next_time_recommendation"] == "下次先起 uvicorn"
    assert out["next_route_hint"] == "B"
    assert out["next_must_verify"] == TBD
    assert out["next_traps_to_avoid"] == TBD
