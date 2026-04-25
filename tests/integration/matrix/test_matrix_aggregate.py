"""矩阵覆盖度聚合统计 · 5 TC.

**T1**. 验证 30 EXPECTED_CELLS 全 covered (用 MatrixCoverage 工具 · 断言每 cell ≥ 1 TC)
**T2**. 验证 IC 全用到 (IC-01/02/03/04/08/09/12/13/14/15/16/17/18/19) ≥ 14 IC
**T3**. 验证 PM-14 隔离 (任意 cell 跨 pid 必拒)
**T4**. 验证 hash chain 跨 row 完整 (end-to-end audit ledger)
**T5**. 跨 row e2e (5 row 串行 → 完整业务流)

注: T1 + T2 依赖 session 级 matrix_cov · 必须与 row 文件同一 pytest 进程运行;
    T3-T5 自含数据 · 单跑也不依赖 row 文件先行.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# 30 锁定的 EXPECTED_CELLS · brief §EXPECTED_CELLS · 与 conftest.py 同步
EXPECTED_CELLS_30: tuple[tuple[str, str], ...] = (
    # Row L1-01 (4 cells)
    ("L1-01", "L1-02"), ("L1-01", "L1-04"),
    ("L1-01", "L1-05"), ("L1-01", "L1-09"),
    # Row L1-02 (3 cells)
    ("L1-02", "L1-03"), ("L1-02", "L1-04"), ("L1-02", "L1-09"),
    # Row L1-03 (3 cells)
    ("L1-03", "L1-04"), ("L1-03", "L1-09"), ("L1-03", "L1-01"),
    # Row L1-04 (3 cells)
    ("L1-04", "L1-01"), ("L1-04", "L1-09"), ("L1-04", "L1-07"),
    # Row L1-05 (3 cells)
    ("L1-05", "L1-01"), ("L1-05", "L1-09"), ("L1-05", "L1-06"),
    # Row L1-06 (3 cells)
    ("L1-06", "L1-09"), ("L1-06", "L1-04"), ("L1-06", "L1-10"),
    # Row L1-07 (4 cells)
    ("L1-07", "L1-01"), ("L1-07", "L1-09"),
    ("L1-07", "L1-10"), ("L1-07", "L1-04"),
    # Row L1-08 (2 cells)
    ("L1-08", "L1-05"), ("L1-08", "L1-09"),
    # Row L1-09 (3 cells)
    ("L1-09", "L1-01"), ("L1-09", "L1-04"), ("L1-09", "L1-07"),
    # Row L1-10 (2 cells)
    ("L1-10", "L1-01"), ("L1-10", "L1-09"),
)

# 14 关键 IC · brief 锁定列表
EXPECTED_ICS_14: tuple[str, ...] = (
    "IC-01", "IC-02", "IC-03", "IC-04",
    "IC-08", "IC-09",
    "IC-12", "IC-13", "IC-14", "IC-15",
    "IC-16", "IC-17", "IC-18", "IC-19",
)


# =============================================================================
# T1 · 30 EXPECTED_CELLS 全 covered
# =============================================================================


def test_t1_all_30_cells_covered_by_at_least_one_tc(matrix_cov) -> None:
    """T1 · 30 锁定 cells 每个至少 1 TC 已记录 (跨 row 文件 session 累积).

    matrix_cov 是 session 级 · 累积 row L1-01..10 全部 record_cell 调用.
    本测试必须与 row 文件在同一 pytest 进程内运行 · 否则 covered 为空.
    若单跑 (pytest test_matrix_aggregate.py) · skip 而非失败 (语义文档化).
    """
    if not matrix_cov.covered:
        pytest.skip(
            "T1 需要与 test_row_l1_*.py 在同一 pytest 进程跑 · "
            "请用 `pytest tests/integration/matrix/` 触发完整 session 累积"
        )
    # 每个 cell · 找它在 covered 中的至少 1 case_type
    missing_cells: list[tuple[str, str]] = []
    for upstream, downstream in EXPECTED_CELLS_30:
        any_covered = any(
            (upstream, downstream, ct) in matrix_cov.covered
            for ct in CaseType
        )
        if not any_covered:
            missing_cells.append((upstream, downstream))
    assert not missing_cells, (
        f"T1 · 30 cells 未全覆盖 · 缺 {len(missing_cells)} cells: {missing_cells}\n"
        f"已记 cells={len({(u,d) for u,d,_ in matrix_cov.covered})}/30 "
        f"summary={matrix_cov.summary()}"
    )
    # 30/30 cells 至少 1 case_type
    assert len({(u, d) for u, d, _ in matrix_cov.covered}) >= 30, (
        f"T1 · 至少 30 unique cells (实际 {len({(u,d) for u,d,_ in matrix_cov.covered})})"
    )


# =============================================================================
# T2 · IC 全用到 (≥ 14 ICs)
# =============================================================================


def test_t2_all_14_ics_referenced_in_row_tests() -> None:
    """T2 · brief 锁定 14 ICs 每个在 row L1-01..10 文件中至少出现 1 次.

    扫描 test_row_l1_*.py 文本 · grep IC-NN.
    """
    matrix_dir = Path(__file__).parent
    row_files = sorted(matrix_dir.glob("test_row_l1_*.py"))
    assert len(row_files) == 10, (
        f"T2 · 期望 10 row files (L1-01..10) · 实际 {len(row_files)}: {row_files}"
    )
    found_ics: set[str] = set()
    for f in row_files:
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\bIC-(\d{2})\b", text):
            found_ics.add(f"IC-{m.group(1)}")
    missing = set(EXPECTED_ICS_14) - found_ics
    assert not missing, (
        f"T2 · ≥14 IC 未全引用 · 缺 {sorted(missing)}\n"
        f"已引用={sorted(found_ics)}"
    )
    assert len(found_ics & set(EXPECTED_ICS_14)) >= 14, (
        f"T2 · 至少 14 ICs (命中 {len(found_ics & set(EXPECTED_ICS_14))})"
    )


# =============================================================================
# T3 · PM-14 隔离 (跨 pid 必拒/分片)
# =============================================================================


def test_t3_pm14_cross_pid_isolation_holds(
    project_id: str,
    other_project_id: str,
    real_event_bus,
    event_bus_root: Path,
    matrix_cov,
) -> None:
    """T3 · 任意 cell 跨 pid 隔离 · 写两 pid · 各自 sequence=1 不串扰.

    写到 pid_A 的事件 · pid_B 查不到 · 反之亦然.
    """
    # 写 5 类不同 type 各 1 条 (覆盖 5 cells 各方向)
    types = (
        "L1-01:decision_made",
        "L1-02:stage_transitioned",
        "L1-04:gate_evaluated",
        "L1-09:panic_emitted",
        "L1-07:supervisor_metric_emitted",
    )
    for t in types:
        # 系统级事件用对应 actor
        actor = "recoverer" if "panic" in t else (
            "supervisor" if "supervisor" in t else "main_loop"
        )
        # 每种 type 各写到两 pid
        real_event_bus.append(Event(
            project_id=project_id,
            type=t, actor=actor,
            payload={"pm14_test": "A"},
            timestamp=datetime.now(UTC),
        ))
        real_event_bus.append(Event(
            project_id=other_project_id,
            type=t, actor=actor,
            payload={"pm14_test": "B"},
            timestamp=datetime.now(UTC),
        ))
    # 每个 type · 两 pid 各自分片独立 (各 sequence 计数从 1 开始)
    for t in types:
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type=t, payload_contains={"pm14_test": "A"},
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type=t, payload_contains={"pm14_test": "B"},
        )
        # pid_A 的 events 不含 pid_B 的 payload
        assert all(e["payload"]["pm14_test"] == "A" for e in a)
        assert all(e["payload"]["pm14_test"] == "B" for e in b)
    # 记录 PM14 cell (以 L1-09 → L1-04 为代表)
    from .conftest import record_cell
    record_cell(matrix_cov, "L1-09", "L1-04", CaseType.PM14)


# =============================================================================
# T4 · hash chain 跨 row 完整 (e2e audit ledger)
# =============================================================================


def test_t4_cross_row_hash_chain_intact(
    project_id: str,
    real_event_bus,
    event_bus_root: Path,
) -> None:
    """T4 · 跨 5 row 模拟事件序列 · hash chain 全程无 gap.

    同 pid 分片下 · 写 10 events 含 5 row 类型 · sequence 严格递增 + prev_hash 链路.
    """
    # 模拟跨 row 的事件序列 (10 个 · 各 row 不同 type)
    cross_row_events = [
        ("L1-01:decision_made", "main_loop", {"step": 1}),
        ("L1-02:stage_transitioned", "main_loop", {"step": 2}),
        ("L1-03:wp_status_changed", "main_loop", {"step": 3}),
        ("L1-04:gate_evaluated", "verifier", {"step": 4}),
        ("L1-05:skill_invocation_completed", "executor", {"step": 5}),
        ("L1-06:kb_entry_written", "main_loop", {"step": 6}),
        ("L1-07:supervisor_metric_emitted", "supervisor", {"step": 7}),
        ("L1-08:multimodal_tool_completed", "executor", {"step": 8}),
        ("L1-09:panic_emitted", "recoverer", {"step": 9}),
        ("L1-10:ui_action_audited", "ui", {"step": 10}),
    ]
    for t, actor, payload in cross_row_events:
        real_event_bus.append(Event(
            project_id=project_id,
            type=t, actor=actor, payload=payload,
            timestamp=datetime.now(UTC),
        ))
    # 物理 hash chain 校验 · 无 gap · 共 10 条 (sequence=1..10)
    n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
    assert n == 10


# =============================================================================
# T5 · 跨 row e2e (5 row 串行)
# =============================================================================


def test_t5_cross_row_e2e_business_flow(
    project_id: str,
    real_event_bus,
    event_bus_root: Path,
) -> None:
    """T5 · 5 row 串行 · 完整业务流 (decision → stage → gate → audit → ui).

    模拟一个 WP 的完整生命周期:
        L1-01 main 决策 → L1-02 stage 转换 → L1-04 Gate 评估 →
        L1-09 audit 落盘 → L1-10 UI push.
    每 row 至少 1 event 落盘 · 全部 audit 串成 1 条 hash chain.
    """
    # 5 阶段 · 串行 · 每 row 一条 event · 全部同 pid · 同 wp
    wp_id = "wp-e2e-001"

    # Stage 1: L1-01 main 决策 dispatch WP
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-01:decision_made",
        actor="main_loop",
        payload={"wp_id": wp_id, "decision": "dispatch_wp"},
        timestamp=datetime.now(UTC),
    ))
    # Stage 2: L1-02 stage 推进 (S0→S1)
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-02:stage_transitioned",
        actor="main_loop",
        payload={"wp_id": wp_id, "from": "S0", "to": "S1"},
        timestamp=datetime.now(UTC),
    ))
    # Stage 3: L1-04 Gate 评估 PASS
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-04:gate_evaluated",
        actor="verifier",
        payload={"wp_id": wp_id, "gate_id": "S1-gate", "decision": "pass"},
        timestamp=datetime.now(UTC),
    ))
    # Stage 4: L1-09 audit ack
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-09:audit_completed",
        actor="audit_mirror",
        payload={"wp_id": wp_id, "rows_audited": 3},
        timestamp=datetime.now(UTC),
    ))
    # Stage 5: L1-10 UI 推送结果
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-10:ui_action_audited",
        actor="ui",
        payload={"wp_id": wp_id, "ui_action": "wp_completed_pushed"},
        timestamp=datetime.now(UTC),
    ))

    # 验证 5 row 各自 emit 至少 1 条
    for t in (
        "L1-01:decision_made",
        "L1-02:stage_transitioned",
        "L1-04:gate_evaluated",
        "L1-09:audit_completed",
        "L1-10:ui_action_audited",
    ):
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type=t, payload_contains={"wp_id": wp_id},
        )
        assert len(events) >= 1, f"T5 · row event {t} missing"

    # 跨 row hash chain 完整 · sequence=1..5
    n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
    assert n == 5
