"""tests/integration/matrix/ · 矩阵测试本地 fixtures.

**定位**:
    main-3 WP05 · 10×10 跨 L1 矩阵集成测试本地 conftest.

    复用 tests/shared/conftest.py 的全局 fixture(project_id / event_bus /
    state_spy / 等)· 仅在此添加 matrix 专属 fixture(MatrixCoverage 模块级
    单例 + EXPECTED_CELLS 30 关键 cells 列表).

**MatrixCoverage 单例**:
    所有 row 测试文件共享同一个 MatrixCoverage 实例 · 在 test_matrix_aggregate.py
    最末断言全 30 cells 至少 1 TC 已覆盖.

**EXPECTED_CELLS** (cross-l1-integration.md §2 / brief 矩阵 cell 清单):
    30 个有真实 IC 调用关系的有向 cell · 每 cell ≥ 1 TC.
"""
from __future__ import annotations

import pytest

# Re-export shared fixtures
from tests.shared.conftest import (  # noqa: F401
    audit_sink,
    callback_waiter,
    ckpt_root,
    delegate_stub,
    event_bus_root,
    fake_kb_repo,
    fake_llm,
    fake_reranker,
    fake_scope_checker,
    fake_skill_invoker,
    fake_tool_client,
    kb_root,
    lock_root,
    no_sleep,
    other_project_id,
    project_id,
    projects_root,
    real_event_bus,
    state_spy,
    tmp_root,
)
from tests.shared.matrix_helpers import CaseType, MatrixCoverage
from tests.shared.project_factory import project_factory, project_workspace  # noqa: F401


# =============================================================================
# 30 关键 cells · brief 锁定的有真实 IC 调用关系的有向 pair
# =============================================================================
# 格式: (upstream/producer, downstream/consumer)
EXPECTED_CELLS: tuple[tuple[str, str], ...] = (
    # Row L1-01 (4 cells)
    ("L1-01", "L1-02"),  # IC-01 触发 stage_transition
    ("L1-01", "L1-04"),  # IC-14 trigger Gate
    ("L1-01", "L1-05"),  # IC-04 调 skill
    ("L1-01", "L1-09"),  # IC-09 append_event
    # Row L1-02 (3 cells)
    ("L1-02", "L1-03"),  # IC-02 trigger WBS
    ("L1-02", "L1-04"),  # IC-14 stage_gate verdict
    ("L1-02", "L1-09"),  # IC-03 stage_artifact_emitted
    # Row L1-03 (3 cells)
    ("L1-03", "L1-04"),  # IC-14 wp_complete trigger gate
    ("L1-03", "L1-09"),  # IC-02 wp_status_change
    ("L1-03", "L1-01"),  # IC-16 任务链 step
    # Row L1-04 (3 cells)
    ("L1-04", "L1-01"),  # IC-14 verdict via response
    ("L1-04", "L1-09"),  # IC-09 gate_evaluated audit
    ("L1-04", "L1-07"),  # IC-13 (旁路) Supervisor 观察
    # Row L1-05 (3 cells)
    ("L1-05", "L1-01"),  # IC-04 (response) 调用结果回返
    ("L1-05", "L1-09"),  # IC-09 invoke_audit
    ("L1-05", "L1-06"),  # IC-08 子 Agent 委托使用 KB
    # Row L1-06 (3 cells)
    ("L1-06", "L1-09"),  # IC-09 kb_audit
    ("L1-06", "L1-04"),  # IC-08 → Gate KB predicate 数据源
    ("L1-06", "L1-10"),  # IC-19 KB 浏览器 push
    # Row L1-07 (4 cells)
    ("L1-07", "L1-01"),  # IC-15 hard_halt request
    ("L1-07", "L1-09"),  # IC-12 metric_emit
    ("L1-07", "L1-10"),  # IC-19 dashboard_push
    ("L1-07", "L1-04"),  # 监督触发 Gate (新增 4th 替代 push_suggestion 重号)
    # Row L1-08 (2 cells)
    ("L1-08", "L1-05"),  # IC-04 (impl) tool 调用结果
    ("L1-08", "L1-09"),  # IC-09 tool_audit
    # Row L1-09 (3 cells)
    ("L1-09", "L1-01"),  # IC-17 panic
    ("L1-09", "L1-04"),  # IC-18 audit_query 用于 Gate
    ("L1-09", "L1-07"),  # IC-09 →supervisor 反馈(新增第 3 cell)
    # Row L1-10 (2 cells)
    ("L1-10", "L1-01"),  # IC-19 (response) user_intervention
    ("L1-10", "L1-09"),  # IC-09 ui_audit
)


@pytest.fixture(scope="session")
def matrix_cov() -> MatrixCoverage:
    """会话级单例 · 累积所有 row 文件的 cell 覆盖记录.

    用法:
        def test_l1_01_to_l1_02_happy(matrix_cov):
            matrix_cov.record("L1-01", "L1-02", CaseType.HAPPY)
            ...

    在 test_matrix_aggregate.py 中读取 matrix_cov.summary() / missing_pairs()
    断言 30 cells 已覆盖.
    """
    return MatrixCoverage()


def record_cell(
    matrix_cov: MatrixCoverage,
    upstream: str,
    downstream: str,
    case_type: CaseType | str,
) -> None:
    """登记一次 cell 覆盖 · 测试函数体内直接调用.

    参数顺序: upstream(producer) → downstream(consumer).
    """
    matrix_cov.record(upstream, downstream, case_type)
