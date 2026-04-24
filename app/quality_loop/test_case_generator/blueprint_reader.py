"""L2-03 blueprint_reader · 从 WP02 TDDBlueprint 展开 CaseSlot 矩阵。

职责（WP03 裁）：
  - 读 TDDBlueprint（任意 state 允许 · PUBLISHED/READY 最常见）
  - 校验 ACMatrix 非空 + 每 AC 至少 1 slot（ac_coverage=1.0 硬锁）
  - 按 (ac_id, layer, seq) 展开 CaseSlot · slot_id 稳定可排序

故意不做：
  - 事件订阅 / L2-01 广播（留 generator）
  - WP 分片（PM-14 shard）· 由 pytest_renderer 组文件路径时处理
  - KB template lookup（WP03 scope 外）
"""

from __future__ import annotations

from app.quality_loop.tdd_blueprint.schemas import TDDBlueprint

from .schemas import (
    AC_COVERAGE_NOT_100,
    AC_MATRIX_INVALID,
    CaseSlot,
    TestCaseGeneratorError,
)


class BlueprintReader:
    """L2-03 · 蓝图 → CaseSlot 矩阵 · 纯函数封装在类里便于 generator 注入 mock。"""

    def read(self, blueprint: TDDBlueprint | None) -> list[CaseSlot]:
        """展开 CaseSlot 列表 · 按 ac_id + layer + seq 稳定排序。

        Raises:
          TestCaseGeneratorError(AC_MATRIX_INVALID) — bp 为 None / 矩阵空
          TestCaseGeneratorError(AC_COVERAGE_NOT_100) — 任一 AC 无 slot
        """
        if blueprint is None:
            raise TestCaseGeneratorError(
                code=AC_MATRIX_INVALID,
                message="blueprint is None · reader 需要合法 TDDBlueprint 实例",
            )
        if not blueprint.ac_matrix or not blueprint.ac_matrix.rows:
            raise TestCaseGeneratorError(
                code=AC_MATRIX_INVALID,
                message="ac_matrix.rows 为空 · WP02 蓝图未生成 slot",
            )

        missing = blueprint.ac_matrix.missing_ac_ids()
        if missing:
            raise TestCaseGeneratorError(
                code=AC_COVERAGE_NOT_100,
                message=f"AC 未覆盖（三层 slot 均 0）: {missing}",
                severity="CRITICAL",
                missing_ac_ids=missing,
            )

        slots: list[CaseSlot] = []
        for ac_id in sorted(blueprint.ac_matrix.rows):
            row = blueprint.ac_matrix.rows[ac_id]
            # unit
            for i in range(row.unit_slots):
                slots.append(
                    CaseSlot(
                        slot_id=f"slot-{ac_id}-u{i + 1}",
                        ac_id=ac_id,
                        layer="unit",
                        seq=i + 1,
                        priority=row.priority,
                    )
                )
            # integration
            for i in range(row.integration_slots):
                slots.append(
                    CaseSlot(
                        slot_id=f"slot-{ac_id}-i{i + 1}",
                        ac_id=ac_id,
                        layer="integration",
                        seq=i + 1,
                        priority=row.priority,
                    )
                )
            # e2e
            for i in range(row.e2e_slots):
                slots.append(
                    CaseSlot(
                        slot_id=f"slot-{ac_id}-e{i + 1}",
                        ac_id=ac_id,
                        layer="e2e",
                        seq=i + 1,
                        priority=row.priority,
                    )
                )
        return slots


__all__ = ["BlueprintReader"]
