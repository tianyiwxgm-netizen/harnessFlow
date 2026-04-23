"""L2-02 对外只读视图 · `TopologySnapshot` frozen VO。

供 L2-03 / L2-04 / L2-05 / L1-10 UI / L1-07 监督 消费。
外部对 snapshot 的任何改动都不会影响 manager 内部状态（frozen）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.l1_03.topology.state_machine import State


class TopologySnapshot(BaseModel):
    """L2-02 某时刻的拓扑快照 · 所有字段 immutable。"""

    model_config = ConfigDict(frozen=True)

    project_id: str
    topology_id: str
    topology_version: str
    wp_states: dict[str, State] = Field(default_factory=dict)
    """wp_id → State 的映射 · 只含本次快照要求的 wp_ids。"""
    wp_effort: dict[str, float] = Field(default_factory=dict)
    """wp_id → effort_estimate 的映射。"""
    deps: dict[str, list[str]] = Field(default_factory=dict)
    """wp_id → deps 列表。"""
    critical_path: list[str] = Field(default_factory=list)
    current_running_count: int = 0
    parallelism_limit: int = 2

    def is_ready(self, wp_id: str) -> bool:
        return self.wp_states.get(wp_id) == State.READY

    def is_running(self, wp_id: str) -> bool:
        return self.wp_states.get(wp_id) == State.RUNNING

    def is_done(self, wp_id: str) -> bool:
        return self.wp_states.get(wp_id) == State.DONE

    def deps_met(self, wp_id: str) -> bool:
        """wp 的所有 deps 都 DONE。空 deps 返 True。"""
        return all(
            self.wp_states.get(d) == State.DONE
            for d in self.deps.get(wp_id, [])
        )


def read_snapshot(
    manager: object,  # avoid circular import type hint
    wp_ids: list[str] | None = None,
) -> TopologySnapshot:
    """从 manager 取只读快照。`wp_ids=None` 表示全量。"""
    # 约定：manager 必须实现 _build_snapshot_payload(wp_ids) 返回 dict
    payload = manager._build_snapshot_payload(wp_ids)  # type: ignore[attr-defined]
    return TopologySnapshot(**payload)
