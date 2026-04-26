"""v1.6 fix defects #5 — UI 后端 artifacts 类型容错 + schema 严格化双层防御.

层 1（运行时容错）：ui/backend/mock_data.py::_normalize_artifacts() 把任意类型
归一为 list[dict]，确保 _derive_delivery_goals + _wbs_deliverables_for 不再
对历史脏 task-board 抛 AttributeError。

层 2（写入时拦截）：schemas/task-board.schema.json::artifacts 改为
{type: array, items: {type: object, required: [path]}}，让 jsonschema 在
任务一开始往板子里追加 artifact 时即拒绝 string/null/int 等违例。

本文件 cover 9 case：normalize 4 + WBS 流转 2 + schema 严格 3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

try:
    import jsonschema  # type: ignore
except ImportError:
    jsonschema = None  # noqa: N816


HARNESS_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = HARNESS_DIR / "schemas" / "task-board.schema.json"

# 让 ui/backend 可 import
sys.path.insert(0, str(HARNESS_DIR / "ui" / "backend"))


# -- Layer 1: _normalize_artifacts ---------------------------------------- #


def test_normalize_pure_dict_list_passes_through() -> None:
    from mock_data import _normalize_artifacts  # type: ignore

    raw = [{"path": "a.py", "type": "code"}, {"path": "b.md", "type": "doc"}]
    out = _normalize_artifacts(raw)
    assert out == raw


def test_normalize_string_list_lifted_to_dicts() -> None:
    from mock_data import _normalize_artifacts  # type: ignore

    raw = ["foo.py", "bar.md"]
    out = _normalize_artifacts(raw)
    assert out == [
        {"path": "foo.py", "type": "unknown"},
        {"path": "bar.md", "type": "unknown"},
    ]


def test_normalize_mixed_list_keeps_dicts_lifts_strings_drops_others() -> None:
    from mock_data import _normalize_artifacts  # type: ignore

    raw = [{"path": "x.py"}, "y.md", None, 42, {"path": "z.json"}]
    out = _normalize_artifacts(raw)
    assert out == [
        {"path": "x.py"},
        {"path": "y.md", "type": "unknown"},
        {"path": "z.json"},
    ]


def test_normalize_non_list_returns_empty() -> None:
    from mock_data import _normalize_artifacts  # type: ignore

    assert _normalize_artifacts(None) == []
    assert _normalize_artifacts({}) == []
    assert _normalize_artifacts("a.py") == []
    assert _normalize_artifacts(42) == []


# -- Layer 1 in flow: _derive_delivery_goals + _wbs_deliverables_for ------ #


def test_derive_delivery_goals_robust_against_string_artifacts() -> None:
    """模拟 defects-report P1 #5 现场：tb.artifacts 是 list[str]，
    历史代码 a.get('path') → AttributeError → 整个 /api/tasks 500."""
    from mock_data import _derive_delivery_goals  # type: ignore

    tb = {
        "artifacts_expected": ["src/foo.py", "docs/bar.md"],
        "artifacts": ["src/foo.py", "docs/bar.md"],  # 违例：list[str]
        "current_state": "IMPL",
    }
    # 不应抛
    out = _derive_delivery_goals(tb)
    assert isinstance(out, list)
    assert len(out) == 2
    assert all("status" in g for g in out)
    # str 元素被 lift 后仍能匹配 expected → 应 done
    statuses = [g["status"] for g in out]
    assert "done" in statuses


def test_wbs_deliverables_for_robust_against_string_inner_artifacts() -> None:
    """stage_artifacts[*].artifacts 同样可能藏 str/null，必须不崩。"""
    from mock_data import _wbs_deliverables_for  # type: ignore

    tb = {
        "stage_artifacts": [
            {
                "stage_id": "stage_impl",
                "artifacts": [
                    "broken_string.md",  # 违例
                    None,  # 违例
                    {"artifact_ref": "ok.py", "location": "src/ok.py"},  # 正常
                ],
            },
            "not_a_dict",  # 违例：stage_rec 都不是 dict
        ],
    }
    out = _wbs_deliverables_for(tb, "impl")
    assert isinstance(out, list)
    # 至少能拿到那个正常 dict 的 ref
    refs = [d["ref"] for d in out]
    assert "ok.py" in refs


# -- Layer 2: jsonschema strict mode -------------------------------------- #


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def base_board() -> dict:
    return {
        "task_id": "p-test-20260426T180000Z",
        "created_at": "2026-04-26T18:00:00Z",
        "current_state": "INIT",
        "goal_anchor": {"text": "test", "hash": "deadbeef"},
    }


def test_schema_artifacts_accepts_proper_dict_list(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    base_board["artifacts"] = [
        {"path": "src/foo.py", "type": "code"},
        {"path": "docs/bar.md", "type": "doc", "note": "spec"},
    ]
    jsonschema.validate(base_board, schema)  # 不抛即可


def test_schema_artifacts_rejects_string_elements(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    base_board["artifacts"] = ["src/foo.py", "docs/bar.md"]  # 违例
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(base_board, schema)


def test_schema_artifacts_rejects_dict_without_path(schema: dict, base_board: dict) -> None:
    if jsonschema is None:
        pytest.skip("jsonschema not installed")
    base_board["artifacts"] = [{"type": "code"}]  # 缺 path
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(base_board, schema)
