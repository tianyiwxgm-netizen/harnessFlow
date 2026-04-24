"""main-1 WP02 · L2-01 TDD 蓝图生成器 · 共享 fixture。

对齐 3-2 §7 · autouse 的只开 event bus · 其余 opt-in。
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

import pytest
from unittest.mock import MagicMock

from app.quality_loop.tdd_blueprint import TDDBlueprintGenerator
from app.quality_loop.tdd_blueprint.schemas import GenerateBlueprintRequest


@pytest.fixture
def mock_project_id() -> str:
    return "pid-default"


@pytest.fixture
def other_project_id() -> str:
    return "pid-other-foreign"


@pytest.fixture
def mock_clock() -> MagicMock:
    clk = MagicMock()
    clk.now_ms = 1_713_744_000_000  # 2026-04-22T00:00:00Z

    def _advance(delta_ms: int) -> None:
        clk.now_ms += delta_ms

    clk.advance = _advance
    return clk


@pytest.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.append_event.return_value = {"ok": True}
    bus._lat = None
    bus._timeout_sub = None
    bus._all_fail = False

    def _set_latency(ms: int) -> None:
        bus._lat = ms

    def _set_timeout(sub: str) -> None:
        bus._timeout_sub = sub

    def _set_all_fail() -> None:
        bus._all_fail = True

    bus.set_broadcast_latency_ms = _set_latency
    bus.set_subscriber_timeout = _set_timeout
    bus.set_broadcast_all_fail = _set_all_fail
    return bus


@pytest.fixture
def mock_fs() -> MagicMock:
    fs = MagicMock()
    fs._missing: set[str] = set()

    def _mark_missing(p: str) -> None:
        fs._missing.add(p)

    def _mark_empty(p: str) -> None:
        fs._missing.add(p)

    def _mutate(p: str) -> None:
        fs._missing.add(p + ".mutated")

    def _write(p: str, _content: str = "") -> None:
        fs._missing.discard(p)

    fs.mark_missing = _mark_missing
    fs.mark_empty = _mark_empty
    fs.mutate_after_load = _mutate
    fs.write = _write
    return fs


@pytest.fixture
def mock_l2_02() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l2_03() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l2_04() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l1_02() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l1_06_kb() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_l1_07() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_nlp_backend() -> MagicMock:
    # 默认返回 None · 让 builder 走 synth 路径
    return MagicMock(return_value=None)


@pytest.fixture
def sut(
    mock_clock: MagicMock,
    mock_event_bus: MagicMock,
    mock_fs: MagicMock,
    mock_l2_02: MagicMock,
    mock_l2_03: MagicMock,
    mock_l2_04: MagicMock,
    mock_l1_02: MagicMock,
    mock_l1_06_kb: MagicMock,
    mock_l1_07: MagicMock,
    mock_nlp_backend: MagicMock,
) -> TDDBlueprintGenerator:
    return TDDBlueprintGenerator(
        clock=mock_clock,
        event_bus=mock_event_bus,
        fs=mock_fs,
        l2_02=mock_l2_02,
        l2_03=mock_l2_03,
        l2_04=mock_l2_04,
        l1_02=mock_l1_02,
        l1_06_kb=mock_l1_06_kb,
        l1_07=mock_l1_07,
        nlp_backend=mock_nlp_backend,
    )


@pytest.fixture
def make_generate_request() -> Callable[..., GenerateBlueprintRequest]:
    def _factory(**overrides: Any) -> GenerateBlueprintRequest:
        pid = overrides.pop("project_id", "pid-default")
        clause_count = overrides.pop("clause_count", 50)
        entry_phase = overrides.pop("entry_phase", "S3")
        prev = overrides.pop("previous_blueprint_id", None)
        retry_focus = overrides.pop("retry_focus", None)
        config_overrides = overrides.pop("config_overrides", None)
        inject_unmapped = overrides.pop("inject_unmapped_ac_count", 0)
        inject_explosion = overrides.pop("inject_ac_case_explosion_on_ac_index", None)
        simulate_delay = overrides.pop("simulate_stage_delay_s", 0.0)
        wp_count = overrides.pop("wp_count", 10)
        nonce = overrides.pop("nonce", None)

        base_project_id = pid or "pid-default"
        four_pieces_refs = overrides.pop(
            "four_pieces_refs",
            {
                "requirements_path": f"projects/{base_project_id}/four-pieces/requirements.md",
                "goals_path": f"projects/{base_project_id}/four-pieces/goals.md",
                "ac_list_path": f"projects/{base_project_id}/four-pieces/ac-list.md",
                "quality_standard_path": f"projects/{base_project_id}/four-pieces/quality-standard.md",
                "four_pieces_hash": "sha256:" + "a" * 64,
            },
        )
        wbs_refs = overrides.pop(
            "wbs_refs",
            {
                "topology_path": f"projects/{base_project_id}/wbs/topology.yaml",
                "wbs_version": 1,
                "wp_count": wp_count,
            },
        )
        ac_clauses_refs = overrides.pop(
            "ac_clauses_refs",
            {
                "ac_manifest_path": f"projects/{base_project_id}/four-pieces/ac-manifest.yaml",
                "clause_count": clause_count,
            },
        )
        # 保证 clause_count 与 refs 一致
        ac_clauses_refs["clause_count"] = clause_count

        return GenerateBlueprintRequest(
            command_id=f"cmd-{uuid.uuid4()}",
            project_id=pid,
            entry_phase=entry_phase,
            four_pieces_refs=four_pieces_refs,
            wbs_refs=wbs_refs,
            ac_clauses_refs=ac_clauses_refs,
            previous_blueprint_id=prev,
            retry_focus=retry_focus,
            config_overrides=config_overrides,
            trigger_tick_id=f"tick-{uuid.uuid4()}",
            inject_unmapped_ac_count=inject_unmapped,
            inject_ac_case_explosion_on_ac_index=inject_explosion,
            simulate_stage_delay_s=simulate_delay,
            nonce=nonce,
        )

    return _factory


@pytest.fixture
def ready_blueprint_id(
    sut: TDDBlueprintGenerator,
    mock_project_id: str,
    make_generate_request: Callable[..., GenerateBlueprintRequest],
) -> str:
    req = make_generate_request(project_id=mock_project_id, clause_count=50)
    resp = sut.generate_blueprint(req)
    sut._await_published(resp.blueprint_id)
    return resp.blueprint_id


@pytest.fixture
def fresh_ready_blueprint_factory(
    sut: TDDBlueprintGenerator,
    mock_project_id: str,
    make_generate_request: Callable[..., GenerateBlueprintRequest],
) -> Callable[[], str]:
    counter = {"n": 0}

    def _make() -> str:
        counter["n"] += 1
        req = make_generate_request(
            project_id=f"{mock_project_id}-fresh-{counter['n']}", clause_count=50
        )
        r = sut.generate_blueprint(req)
        sut._await_published(r.blueprint_id)
        return r.blueprint_id

    return _make


@pytest.fixture
def sample_wp_id() -> str:
    return "wp-0001"


@pytest.fixture
def blueprint_id_with_missing_ac(
    sut: TDDBlueprintGenerator, mock_project_id: str
) -> str:
    return sut._build_partial_blueprint_for_test(
        project_id=mock_project_id, unmapped_count=1
    )


@pytest.fixture
def ready_blueprint_id_of_other_project(
    sut: TDDBlueprintGenerator,
    other_project_id: str,
    make_generate_request: Callable[..., GenerateBlueprintRequest],
) -> str:
    req = make_generate_request(project_id=other_project_id, clause_count=50)
    r = sut.generate_blueprint(req)
    sut._await_published(r.blueprint_id)
    return r.blueprint_id
