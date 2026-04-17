"""Unit tests for schemas/failure-archive.schema.json.

Covers: schema meta-validity, valid sample roundtrip, and three classes of
malformed samples rejected.
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from jsonschema import Draft7Validator, ValidationError, validate  # noqa: E402


SCHEMA_PATH = HERE.parent.parent / "schemas" / "failure-archive.schema.json"


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def valid_sample():
    return {
        "task_id": "01HZXYABC123",
        "date": "2026-04-17",
        "ts": "2026-04-17T03:42:00Z",
        "project": "aigcv2",
        "task_type": "视频出片",
        "size": "XL",
        "risk": "中",
        "route": "C",
        "node": "verifier",
        "error_type": "DOD_GAP",
        "missing_subcontract": ["mp4.duration", "oss_head"],
        "retry_count": 3,
        "retry_levels_used": ["L0", "L1"],
        "final_outcome": "false_complete_reported",
        "frequency": 1,
        "root_cause": "Impl 声称 success 但 oss_head 未上传；ffprobe 拿不到 duration。",
        "fix": "L1 调 oss-upload-skill 重传 + 对比预期时长。",
        "prevention": "Impl 节点把 oss_head 加入 must_verify 子契约，不依赖自述。",
        "verifier_report_link": "verifier_reports/01HZXYABC123.json",
        "retro_link": "retros/01HZXYABC123.md",
        "supervisor_events_count": {"INFO": 2, "WARN": 1, "BLOCK": 0},
        "user_interrupts_count": {"DRIFT": 0, "DOD_GAP": 1, "IRREVERSIBLE": 0, "废问题": 0},
        "elapsed_min": 42.3,
        "token_used": 58000,
        "token_budget": 120000,
        "trap_matched": ["P20-oss-silent-skip"],
    }


def test_schema_meta_is_valid(schema):
    Draft7Validator.check_schema(schema)


def test_valid_sample_passes(schema, valid_sample):
    validate(valid_sample, schema)


def test_missing_task_id_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    del bad["task_id"]
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_non_enum_error_type_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["error_type"] = "UNKNOWN_NOT_IN_ENUM"
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_zero_frequency_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["frequency"] = 0
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_non_enum_size_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["size"] = "HUGE"
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_non_enum_route_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["route"] = "Z"
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_non_enum_final_outcome_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["final_outcome"] = "partially_done"
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_retry_count_negative_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["retry_count"] = -1
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_additional_property_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["surprise_field"] = "should fail"
    with pytest.raises(ValidationError):
        validate(bad, schema)


def test_empty_missing_subcontract_ok(schema, valid_sample):
    ok = dict(valid_sample)
    ok["missing_subcontract"] = []
    ok["error_type"] = "USER_ABORT"
    validate(ok, schema)


def test_optional_fields_absent_ok(schema, valid_sample):
    ok = dict(valid_sample)
    for field in ("verifier_report_link", "retro_link", "supervisor_events_count",
                  "user_interrupts_count", "elapsed_min", "token_used",
                  "token_budget", "trap_matched"):
        ok.pop(field, None)
    validate(ok, schema)


def test_root_cause_too_long_rejected(schema, valid_sample):
    bad = dict(valid_sample)
    bad["root_cause"] = "x" * 2001
    with pytest.raises(ValidationError):
        validate(bad, schema)
