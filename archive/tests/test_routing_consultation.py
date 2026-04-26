"""v1.8 fix defects #3 — archive.routing_consultation 单测.

cover：
- build_consultation 正常构造
- validate happy path
- validate 各类违例 → 正确 reason_code
- schema 端 accept proper / reject 缺字段 / reject < 2 candidates / reject 短 rationale
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from archive.routing_consultation import (
    REQUIRED_FIELDS,
    REQUIRED_CANDIDATE_FIELDS,
    build_consultation,
    validate_consultation_record,
)

try:
    import jsonschema  # type: ignore
except ImportError:
    jsonschema = None  # noqa: N816


HARNESS_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = HARNESS_REPO_ROOT / "schemas" / "task-board.schema.json"


def _good_record() -> dict:
    return build_consultation(
        size="L",
        task_type="后端feature",
        risk="中",
        top_candidates=[
            {"route_id": "C", "raw_score": 0.95, "adjusted_score": 0.95, "reason": "L 后端 feature 主路线"},
            {"route_id": "B", "raw_score": 0.75, "adjusted_score": 0.65, "reason": "备选轻 PRP"},
        ],
        decision="C",
        rationale="L size 后端 feature 中风险 → 走完整 PRP（C）;B 作为备选已用 risk overlay 降到 0.65。",
        risk_overlay_applied=True,
        auto_pick_top1=False,
    )


# ---- build_consultation 正常构造 ------------------------------------------ #


def test_build_consultation_returns_full_record() -> None:
    r = _good_record()
    for f in REQUIRED_FIELDS:
        assert f in r and r[f] is not None
    assert r["task_dimensions"]["size"] == "L"
    assert len(r["top_candidates"]) == 2
    assert r["decision"] == "C"


# ---- validate happy path ------------------------------------------------- #


def test_validate_full_record_complete() -> None:
    r = _good_record()
    out = validate_consultation_record(r)
    assert out["complete"] is True
    assert out["missing"] == []
    assert out["reason_code"] is None


# ---- validate 违例 ------------------------------------------------------- #


def test_validate_root_not_dict_returns_malformed() -> None:
    out = validate_consultation_record(None)
    assert out["complete"] is False
    assert out["reason_code"] == "ROUTING_CONSULTATION_MALFORMED"


def test_validate_missing_top_field_returns_missing_code() -> None:
    r = _good_record()
    del r["top_candidates"]
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert out["reason_code"] == "ROUTING_CONSULTATION_MISSING"
    assert "top_candidates" in out["missing"]


def test_validate_only_one_candidate_flags_min_2() -> None:
    r = _good_record()
    r["top_candidates"] = [r["top_candidates"][0]]
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert any("≥2" in m for m in out["missing"])


def test_validate_candidate_missing_score_field() -> None:
    r = _good_record()
    del r["top_candidates"][0]["adjusted_score"]
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert "top_candidates[0].adjusted_score" in out["missing"]


def test_validate_dimension_missing() -> None:
    r = _good_record()
    del r["task_dimensions"]["risk"]
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert "task_dimensions.risk" in out["missing"]


def test_validate_short_rationale_flagged() -> None:
    r = _good_record()
    r["rationale"] = "ok"
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert any("rationale" in m for m in out["missing"])


def test_validate_candidate_not_a_dict() -> None:
    r = _good_record()
    r["top_candidates"][1] = "broken-string"
    out = validate_consultation_record(r)
    assert out["complete"] is False
    assert any("top_candidates[1]" in m for m in out["missing"])


# ---- schema 端 ----------------------------------------------------------- #


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def base_board() -> dict:
    return {
        "task_id": "p-test-routing-20260426T200000Z",
        "created_at": "2026-04-26T20:00:00Z",
        "current_state": "ROUTE_SELECT",
        "goal_anchor": {"text": "test", "hash": "deadbeef"},
    }


def test_schema_accepts_proper_consultation(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    base_board["routing_matrix_consultation"] = _good_record()
    jsonschema.validate(base_board, schema)


def test_schema_rejects_consultation_with_one_candidate(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    rec = _good_record()
    rec["top_candidates"] = [rec["top_candidates"][0]]
    base_board["routing_matrix_consultation"] = rec
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(base_board, schema)


def test_schema_rejects_consultation_short_rationale(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    rec = _good_record()
    rec["rationale"] = "ok"
    base_board["routing_matrix_consultation"] = rec
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(base_board, schema)


def test_schema_rejects_candidate_missing_score(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    rec = _good_record()
    del rec["top_candidates"][0]["adjusted_score"]
    base_board["routing_matrix_consultation"] = rec
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(base_board, schema)
