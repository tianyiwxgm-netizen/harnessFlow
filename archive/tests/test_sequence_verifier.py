"""Tests for archive.sequence_verifier.{loader, verifier} v1.5 — defects #2.

Coverage:
  loader:
    - list_must_load_memories: 解析 MEMORY.md 链接，过滤前缀
    - read_must_load_memories: dict {basename: content}
    - routing_decision_basis_record: complete / missing 计算
    - 边界：MEMORY.md 不存在；memory_dir 不存在；空 MEMORY.md
  verifier:
    - parse_flow_catalog_route: 提取 expected sequence
    - verify_route_sequence: match / missing / extra / reordered / route 不存在
    - allow_missing_steps（C-lite 降级路径）
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from archive.sequence_verifier.loader import (
    list_must_load_memories,
    read_must_load_memories,
    routing_decision_basis_record,
)
from archive.sequence_verifier.verifier import (
    parse_flow_catalog_route,
    verify_route_sequence,
)


# ---------------------------------------------------------------- loader fixtures
def _make_mem_dir(tmp_path: Path, mem_index: str, files: dict[str, str]) -> Path:
    md = tmp_path / "memory"
    md.mkdir()
    (md / "MEMORY.md").write_text(mem_index, encoding="utf-8")
    for name, body in files.items():
        (md / name).write_text(body, encoding="utf-8")
    return md


# ---------------------------------------------------------------- loader tests
def test_list_must_load_memories_extracts_workflow_and_prp(tmp_path):
    idx = textwrap.dedent("""\
    # Memory Index
    - [scheme c](feedback_workflow_scheme_c.md) — workflow scheme
    - [prp flow](feedback_prp_flow.md) — prp standard
    - [unrelated](feedback_real_completion.md) — not in scope
    - [no link](some text)
    """)
    md = _make_mem_dir(
        tmp_path,
        idx,
        {
            "feedback_workflow_scheme_c.md": "scheme c body",
            "feedback_prp_flow.md": "prp body",
            "feedback_real_completion.md": "completion body",
        },
    )
    paths = list_must_load_memories(md)
    names = sorted(p.name for p in paths)
    assert names == ["feedback_prp_flow.md", "feedback_workflow_scheme_c.md"]


def test_list_must_load_memories_skips_missing_files(tmp_path):
    idx = "- [phantom](feedback_workflow_phantom.md)\n"
    md = _make_mem_dir(tmp_path, idx, {})  # phantom file not actually written
    paths = list_must_load_memories(md)
    assert paths == []


def test_list_must_load_memories_no_index(tmp_path):
    md = tmp_path / "memory"
    md.mkdir()
    paths = list_must_load_memories(md)
    assert paths == []


def test_list_must_load_memories_dir_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        list_must_load_memories(tmp_path / "nonexistent")


def test_read_must_load_memories_returns_basename_keyed_dict(tmp_path):
    idx = "- [a](feedback_workflow_a.md)\n- [b](feedback_prp_b.md)\n"
    md = _make_mem_dir(
        tmp_path, idx,
        {"feedback_workflow_a.md": "AAA", "feedback_prp_b.md": "BBB"},
    )
    out = read_must_load_memories(md)
    assert out == {"feedback_workflow_a.md": "AAA", "feedback_prp_b.md": "BBB"}


def test_routing_decision_basis_complete_path(tmp_path):
    idx = "- [a](feedback_workflow_a.md)\n- [b](feedback_prp_b.md)\n"
    md = _make_mem_dir(
        tmp_path, idx,
        {"feedback_workflow_a.md": "x", "feedback_prp_b.md": "y"},
    )
    rec = routing_decision_basis_record(md, loaded_files=["feedback_workflow_a.md", "feedback_prp_b.md"])
    assert rec["complete"] is True
    assert rec["missing"] == []
    assert sorted(rec["must_load_memories"]) == ["feedback_prp_b.md", "feedback_workflow_a.md"]


def test_routing_decision_basis_missing_one(tmp_path):
    idx = "- [a](feedback_workflow_a.md)\n- [b](feedback_prp_b.md)\n"
    md = _make_mem_dir(
        tmp_path, idx,
        {"feedback_workflow_a.md": "x", "feedback_prp_b.md": "y"},
    )
    rec = routing_decision_basis_record(md, loaded_files=["feedback_workflow_a.md"])
    assert rec["complete"] is False
    assert rec["missing"] == ["feedback_prp_b.md"]


# ---------------------------------------------------------------- verifier fixtures
@pytest.fixture
def fake_flow_catalog(tmp_path: Path) -> Path:
    body = textwrap.dedent("""\
    # flow-catalog (test fixture)

    ## § 2 路线 A — 零 PRP 直改提交（XS）

    **调度序列**：
    ```
    1. native:Read
    2. native:Edit
    3. native:Bash
    4. ECC:prp-commit
    ```

    ## § 3 路线 B — 轻 PRP 快速交付（S-M）

    **调度序列**：
    ```
    1. SP:brainstorming
    2. ECC:prp-plan
    3. ECC:save-session
    4. ECC:prp-implement
       → ECC:code-reviewer
    5. harnessFlow:verifier
    6. ECC:prp-commit
    7. ECC:retro
    ```

    ## § 4 路线 C — 全 PRP 重验证（L-XL）

    **调度序列**（完整 5 步）：
    ```
    1. SP:brainstorming
    2. ECC:prp-prd
    3. ECC:prp-plan
    4. ECC:prp-implement
    5. ECC:prp-commit
    ```
    """)
    p = tmp_path / "flow-catalog.md"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------- verifier tests
def test_parse_route_a_returns_sequence(fake_flow_catalog):
    seq = parse_flow_catalog_route(fake_flow_catalog, "A")
    assert seq == ["native:Read", "native:Edit", "native:Bash", "ECC:prp-commit"]


def test_parse_route_b_includes_arrow_nested(fake_flow_catalog):
    seq = parse_flow_catalog_route(fake_flow_catalog, "B")
    assert "ECC:code-reviewer" in seq
    assert seq[0] == "SP:brainstorming"


def test_parse_route_not_found_returns_empty(fake_flow_catalog):
    assert parse_flow_catalog_route(fake_flow_catalog, "Z") == []


def test_parse_flow_catalog_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_flow_catalog_route(tmp_path / "nope.md", "A")


def test_verify_match_route_c(fake_flow_catalog):
    result = verify_route_sequence(
        "C",
        [
            "SP:brainstorming",
            "ECC:prp-prd",
            "ECC:prp-plan",
            "ECC:prp-implement",
            "ECC:prp-commit",
        ],
        fake_flow_catalog,
    )
    assert result["match"] is True
    assert result["reason_code"] == "OK"


def test_verify_missing_step_route_c(fake_flow_catalog):
    result = verify_route_sequence(
        "C",
        ["SP:brainstorming", "ECC:prp-plan", "ECC:prp-implement", "ECC:prp-commit"],
        fake_flow_catalog,
    )
    assert result["match"] is False
    assert result["missing"] == ["ECC:prp-prd"]
    assert "missing" in result["reason_code"]
    assert "missing=" in result["reason_msg"]


def test_verify_extra_step_route_c(fake_flow_catalog):
    result = verify_route_sequence(
        "C",
        [
            "SP:brainstorming",
            "ECC:prp-prd",
            "ECC:prp-plan",
            "SP:writing-plans",  # ← 违反 memory 偏好
            "ECC:prp-implement",
            "ECC:prp-commit",
        ],
        fake_flow_catalog,
    )
    assert result["match"] is False
    assert result["extra"] == ["SP:writing-plans"]
    assert "extra" in result["reason_code"]


def test_verify_reordered_when_no_missing_or_extra(fake_flow_catalog):
    result = verify_route_sequence(
        "C",
        [
            "SP:brainstorming",
            "ECC:prp-plan",  # 应该在 prp-prd 之后
            "ECC:prp-prd",
            "ECC:prp-implement",
            "ECC:prp-commit",
        ],
        fake_flow_catalog,
    )
    assert result["match"] is False
    assert result["reordered"] is True


def test_verify_allow_missing_steps_for_c_lite(fake_flow_catalog):
    """C-lite 降级路径允许省略 prp-prd"""
    result = verify_route_sequence(
        "C",
        ["SP:brainstorming", "ECC:prp-plan", "ECC:prp-implement", "ECC:prp-commit"],
        fake_flow_catalog,
        allow_missing_steps=["ECC:prp-prd"],
    )
    assert result["match"] is True
    assert result["missing"] == []


def test_verify_route_not_found_returns_specific_code(fake_flow_catalog):
    result = verify_route_sequence("Z", ["SP:brainstorming"], fake_flow_catalog)
    assert result["match"] is False
    assert result["reason_code"] == "ROUTE_NOT_FOUND"


def test_verify_against_real_flow_catalog():
    """Smoke test against actual flow-catalog.md to catch parse regressions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    fc = repo_root / "flow-catalog.md"
    if not fc.is_file():
        pytest.skip("flow-catalog.md missing in this checkout")
    seq = parse_flow_catalog_route(fc, "C")
    assert len(seq) >= 10, f"route C should have ≥ 10 steps, got {len(seq)}: {seq}"
    assert "SP:brainstorming" in seq
    assert "ECC:prp-prd" in seq
    assert "harnessFlow:verifier" in seq


def test_verify_real_route_a_skeletal_sequence():
    """A 路线在真实 flow-catalog 应至少含 ECC:prp-commit."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    fc = repo_root / "flow-catalog.md"
    if not fc.is_file():
        pytest.skip("flow-catalog.md missing")
    seq = parse_flow_catalog_route(fc, "A")
    assert "ECC:prp-commit" in seq
