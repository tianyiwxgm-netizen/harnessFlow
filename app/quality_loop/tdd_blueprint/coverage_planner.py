"""覆盖规划器 · 按 GWT × 边界 × 错误码构建 TestPyramid / ACMatrix / CoverageTarget。

对齐 3-1 §6.4 / §6.5 算法：
  stage_2 derive_pyramid   · 默认 0.7/0.2/0.1 + AC 类型微调 + clamp + 归一化
  stage_3 build_matrix     · 按 pyramid × kind 分配三层槽位，硬规则 unit ≥ 1
  stage_4 compute_coverage · 硬锁 ac=1.0，冗余率作为诊断信息
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.quality_loop.tdd_blueprint.schemas import (
    ACItem,
    ACMatrix,
    ACMatrixRow,
    CoverageTarget,
    TestPyramid,
    TestEnvBlueprint,
    TDDBlueprintError,
)


# ---------------------------------------------------------------------------
# 默认配置（§10）· 可被 request.config_overrides 覆盖
# ---------------------------------------------------------------------------

DEFAULT_PYRAMID = (0.70, 0.20, 0.10)
PYRAMID_MIN = 0.05
PYRAMID_MAX = 0.85

DEFAULT_LINE_COVERAGE = 0.80
DEFAULT_BRANCH_COVERAGE = 0.70

MAX_TEST_CASES_PER_AC = 8
MAX_TEST_CASES_TOTAL_CAP = 2000  # 超过即走 BLUEPRINT_TOO_LARGE


# ---------------------------------------------------------------------------
# 纯函数：pyramid 推导
# ---------------------------------------------------------------------------


def derive_pyramid(
    ac_items: list[ACItem],
    *,
    default: tuple[float, float, float] = DEFAULT_PYRAMID,
    lo: float = PYRAMID_MIN,
    hi: float = PYRAMID_MAX,
) -> TestPyramid:
    u, i, e = default
    for ac in ac_items:
        if ac.kind == "data":
            u += 0.02
        elif ac.kind == "collab":
            i += 0.02
        elif ac.kind == "ui":
            e += 0.01
    u, i, e = _clamp_and_normalize(u, i, e, lo=lo, hi=hi)
    return TestPyramid(unit_ratio=u, integration_ratio=i, e2e_ratio=e)


def _clamp_and_normalize(
    u: float, i: float, e: float, *, lo: float, hi: float
) -> tuple[float, float, float]:
    vals = [max(lo, min(hi, v)) for v in (u, i, e)]
    total = sum(vals)
    if total <= 0:
        return DEFAULT_PYRAMID
    return tuple(v / total for v in vals)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 纯函数：矩阵构建
# ---------------------------------------------------------------------------


def _kind_weight(kind: str, layer: str) -> float:
    """§6.4 kind × layer 权重表。"""
    table = {
        "data":  {"unit": 1.2, "integration": 0.7, "e2e": 0.4},
        "collab":{"unit": 0.8, "integration": 1.3, "e2e": 0.7},
        "ui":    {"unit": 0.7, "integration": 0.9, "e2e": 1.4},
        "mixed": {"unit": 1.0, "integration": 1.0, "e2e": 1.0},
    }
    return table.get(kind, table["mixed"])[layer]


def build_matrix(
    ac_items: list[ACItem],
    pyramid: TestPyramid,
    *,
    max_per_ac: int = MAX_TEST_CASES_PER_AC,
    total_cap: int = MAX_TEST_CASES_TOTAL_CAP,
    forced_unmapped_ac_ids: list[str] | None = None,
    case_explosion_ac_index: int | None = None,
) -> tuple[ACMatrix, dict[str, Any]]:
    """构建 AC → slot 矩阵。返回 (matrix, build_meta)。

    forced_unmapped_ac_ids · 注入指定 AC 零槽位（用于错误路径测试）。
    case_explosion_ac_index · 模拟单 AC 派生超限 · 产生 WARN。
    """
    rows: dict[str, ACMatrixRow] = {}
    used = 0
    warnings: list[dict[str, Any]] = []
    truncated_slots = 0
    forced = set(forced_unmapped_ac_ids or [])

    for idx, ac in enumerate(ac_items):
        if ac.id in forced:
            # 注入：零槽 · 走 AC_MISSING
            rows[ac.id] = ACMatrixRow(
                ac_id=ac.id, unit_slots=0, integration_slots=0, e2e_slots=0,
                priority="P0", layer="unit",
            )
            continue

        # 按 pyramid × kind 推导各层槽位
        u = max(1, round(pyramid.unit_ratio * _kind_weight(ac.kind, "unit") * 3))
        i = max(0, round(pyramid.integration_ratio * _kind_weight(ac.kind, "integration") * 3))
        e = max(0, round(pyramid.e2e_ratio * _kind_weight(ac.kind, "e2e") * 3))

        total = u + i + e
        over_explosion = (idx == case_explosion_ac_index)
        if over_explosion:
            # 模拟爆炸 · 人为放大
            u += max_per_ac * 2
            total = u + i + e

        if total > max_per_ac:
            before = total
            u, i, e = _shrink_to_cap(u, i, e, cap=max_per_ac)
            after = u + i + e
            truncated_slots += max(0, before - after)
            if over_explosion:
                warnings.append({
                    "code": "E_L204_L201_AC_CASE_EXPLOSION",
                    "ac_id": ac.id,
                    "truncated": before - after,
                })

        if used + u + i + e > total_cap:
            # 全局预算耗尽 · 降至 (1, 0, 0)
            u, i, e = 1, 0, 0

        # 主层级：取最大槽位数对应的层
        if e >= max(u, i):
            layer = "e2e"
        elif i >= u:
            layer = "integration"
        else:
            layer = "unit"

        # 优先级：data=P1, collab/ui=P0, mixed=P2（粗策略，WP02 足够）
        priority = {"ui": "P0", "collab": "P0", "data": "P1", "mixed": "P2"}.get(
            ac.kind, "P2"
        )

        rows[ac.id] = ACMatrixRow(
            ac_id=ac.id,
            unit_slots=u,
            integration_slots=i,
            e2e_slots=e,
            priority=priority,
            layer=layer,
        )
        used += u + i + e

    meta = {
        "warnings": warnings,
        "truncated_slots_count": truncated_slots,
        "total_slots": used,
        "total_cap": total_cap,
    }
    if used > total_cap * 0.95:
        # 接近预算上限 · 视为可能 TOO_LARGE 候选
        meta["near_cap"] = True
    return ACMatrix(rows=rows), meta


def _shrink_to_cap(u: int, i: int, e: int, *, cap: int) -> tuple[int, int, int]:
    """保 unit ≥ 1 前提下按比例缩减到 cap 以内。"""
    total = u + i + e
    if total <= cap:
        return u, i, e
    # 优先缩 e2e，再 integration，unit 最低保 1
    room = cap
    new_u = max(1, min(u, room))
    room -= new_u
    new_i = max(0, min(i, room))
    room -= new_i
    new_e = max(0, min(e, room))
    return new_u, new_i, new_e


# ---------------------------------------------------------------------------
# 覆盖率计算
# ---------------------------------------------------------------------------


@dataclass
class CoverageSnapshot:
    ac_coverage: float
    redundancy_ratio: float
    total_test_cases: int
    missing_ac_ids: list[str]

    def valid(self) -> bool:
        return self.ac_coverage >= 1.0 and not self.missing_ac_ids


def compute_coverage(matrix: ACMatrix, ac_items: list[ACItem]) -> CoverageSnapshot:
    if not ac_items:
        return CoverageSnapshot(
            ac_coverage=0.0, redundancy_ratio=0.0, total_test_cases=0, missing_ac_ids=[]
        )
    covered = sum(1 for r in matrix.rows.values() if r.total_slots() > 0)
    redundant = sum(1 for r in matrix.rows.values() if r.total_slots() > 2)
    total_ac = len(ac_items)
    return CoverageSnapshot(
        ac_coverage=covered / total_ac,
        redundancy_ratio=redundant / total_ac,
        total_test_cases=matrix.total_slots(),
        missing_ac_ids=matrix.missing_ac_ids(),
    )


# ---------------------------------------------------------------------------
# CoverageTarget · §10 + §3.2 出参
# ---------------------------------------------------------------------------


def build_coverage_target(
    config_overrides: dict[str, Any] | None = None,
) -> CoverageTarget:
    overrides = config_overrides or {}
    line = float(overrides.get("line_coverage", DEFAULT_LINE_COVERAGE))
    branch = float(overrides.get("branch_coverage", DEFAULT_BRANCH_COVERAGE))
    # ac 硬锁 1.0 · 配置里即便给其他值也忽略
    return CoverageTarget(line=line, branch=branch, ac=1.0)


# ---------------------------------------------------------------------------
# TestEnvBlueprint 装配（§6.5 S5）
# ---------------------------------------------------------------------------


def assemble_test_env(
    ac_items: list[ACItem],
    matrix: ACMatrix,
    *,
    project_id: str,
) -> TestEnvBlueprint:
    profiles: list[dict[str, Any]] = []
    for ac in ac_items:
        row = matrix.rows.get(ac.id)
        if row is None:
            continue
        if row.unit_slots > 0:
            profiles.append(
                {"ac_id": ac.id, "tier": "unit", "strategy": "stub"}
            )
        if row.integration_slots > 0:
            profiles.append(
                {"ac_id": ac.id, "tier": "integration", "strategy": "contract"}
            )
        if row.e2e_slots > 0:
            profiles.append(
                {"ac_id": ac.id, "tier": "e2e", "strategy": "chaos"}
            )
    fixtures = {
        "normal": [ac.id for ac in ac_items if ac.kind == "mixed"],
        "boundary": [ac.id for ac in ac_items if ac.kind == "data"],
        "failure": [ac.id for ac in ac_items if ac.kind == "collab"],
        "adversarial": [ac.id for ac in ac_items if ac.kind == "ui"],
    }
    return TestEnvBlueprint(
        mock_profiles=profiles,
        fixtures=fixtures,
        isolation_prefix=f"proj-{project_id}",
    )


# ---------------------------------------------------------------------------
# Priority 完整性检查
# ---------------------------------------------------------------------------


def priority_annotation_complete(matrix: ACMatrix) -> bool:
    return all(
        row.priority in ("P0", "P1", "P2") and row.total_slots() > 0
        for row in matrix.rows.values()
    )


__all__ = [
    "CoverageSnapshot",
    "DEFAULT_PYRAMID",
    "DEFAULT_LINE_COVERAGE",
    "DEFAULT_BRANCH_COVERAGE",
    "MAX_TEST_CASES_PER_AC",
    "MAX_TEST_CASES_TOTAL_CAP",
    "derive_pyramid",
    "build_matrix",
    "compute_coverage",
    "build_coverage_target",
    "assemble_test_env",
    "priority_annotation_complete",
]
