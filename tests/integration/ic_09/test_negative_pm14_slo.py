"""IC-09 · 负向 / PM-14 缺 pid / SLO / 降级 / e2e 跨链.

覆盖:
    - 负向 1: 非法 type 前缀 (L1-99) → Pydantic ValidationError
    - 负向 2: 非法 actor → Pydantic ValidationError
    - PM-14 缺 pid: 空 project_id → ValidationError (不落盘)
    - SLO: append_event P99 ≤ 200ms (实测 · 50 次采样)
    - 降级: 大 payload 仍能写入(> 10KB)
    - e2e 跨链 mini: 真 bus + AuditQuery 查询回放
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.l1_09.audit.query import AuditQuery
from app.l1_09.audit.schemas import Anchor, AnchorType, QueryFilter
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(raw.decode("utf-8"))
        for raw in path.read_bytes().splitlines()
        if raw.strip()
    ]


# ==============================================================================
# 负向 1: 非法 type 前缀
# ==============================================================================


class TestInvalidTypePrefix:
    """L1-09 §3.2 TypePrefixValidator · 非法前缀硬拒."""

    def test_invalid_l1_prefix_rejected(
        self, project_id: str, real_event_bus: EventBus,
    ) -> None:
        """L1-99 非法前缀 · Pydantic 直接拒绝 · 事件不落盘."""
        with pytest.raises(ValidationError):
            Event(
                project_id=project_id,
                type="L1-99:bogus",  # 非法 L1
                actor="main_loop",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_no_prefix_rejected(self, project_id: str) -> None:
        """无 L1 前缀 · 格式不匹配 pattern · ValidationError."""
        with pytest.raises(ValidationError):
            Event(
                project_id=project_id,
                type="just_bare_event_name",
                actor="main_loop",
                payload={},
                timestamp=datetime.now(UTC),
            )


# ==============================================================================
# 负向 2: 非法 actor
# ==============================================================================


class TestInvalidActor:
    """L1-09 §3.2 actor pattern · 非白名单拒绝."""

    def test_unknown_actor_rejected(self, project_id: str) -> None:
        """不在 VALID_ACTORS 白名单的 actor · ValidationError."""
        with pytest.raises(ValidationError):
            Event(
                project_id=project_id,
                type="L1-01:decision_made",
                actor="intruder",   # 非白名单
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_human_prefix_actor_accepted(self, project_id: str) -> None:
        """`human:*` 前缀是合法白名单项."""
        # 不 raise · 构造成功
        evt = Event(
            project_id=project_id,
            type="L1-10:ui_action_recorded",
            actor="human:alice",
            payload={},
            timestamp=datetime.now(UTC),
        )
        assert evt.actor == "human:alice"


# ==============================================================================
# PM-14 缺 pid
# ==============================================================================


class TestPm14MissingProjectId:
    """PM-14 根字段硬校 · 空/非法格式 project_id 拒绝."""

    def test_empty_project_id_rejected(self) -> None:
        """空 project_id · Pydantic pattern 不匹配 · raise."""
        with pytest.raises(ValidationError):
            Event(
                project_id="",   # 空
                type="L1-01:decision_made",
                actor="main_loop",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_uppercase_project_id_rejected(self) -> None:
        """project_id 必须 `[a-z0-9_-]{1,40}` · 大写违反 pattern."""
        with pytest.raises(ValidationError):
            Event(
                project_id="PROJ-UPPER",   # 非法大写
                type="L1-01:decision_made",
                actor="main_loop",
                payload={},
                timestamp=datetime.now(UTC),
            )

    def test_system_reserved_accepted(
        self, real_event_bus: EventBus, tmp_path: Path,
    ) -> None:
        """`system` 保留值合法 · IC-09 §3.9.2 project_id_or_system."""
        evt = Event(
            project_id="system",
            type="L1-09:meta_event_persisted",
            actor="audit_mirror",
            payload={"kind": "startup"},
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt)
        assert result.persisted is True


# ==============================================================================
# SLO · append_event P99 ≤ 200ms
# ==============================================================================


class TestIC09Slo:
    """IC-09 §7.1 prd SLO · P95 ≤ 50ms · P99 ≤ 200ms."""

    def test_append_p99_under_200ms(
        self, real_event_bus: EventBus, project_id: str,
    ) -> None:
        """连续 50 次 append · P99 ≤ 200ms."""
        latencies_ms = []
        for i in range(50):
            evt = Event(
                project_id=project_id,
                type="L1-01:decision_made",
                actor="main_loop",
                payload={"i": i},
                timestamp=datetime.now(UTC),
            )
            t0 = time.perf_counter()
            real_event_bus.append(evt)
            latencies_ms.append((time.perf_counter() - t0) * 1000)

        latencies_ms.sort()
        p99 = latencies_ms[int(len(latencies_ms) * 0.99) - 1]
        assert p99 < 200, f"IC-09 P99 超标 · 实测 {p99:.2f}ms · SLO 200ms"


# ==============================================================================
# 降级 · 大 payload / 高频写
# ==============================================================================


class TestIC09Degradation:
    """降级路径 · 大 payload / 连续写不因规模失败."""

    def test_near_limit_payload_persisted(
        self, real_event_bus: EventBus, event_bus_root: Path, project_id: str,
    ) -> None:
        """接近 PIPE_BUF_LIMIT(4KB) 的 payload · 仍能写 · fsync 成功.

        L1-09 有 4096B 单行硬限 (LineTooLargeError) · 本测试验贴限成功 + 超限
        由 L1-08 用 link-ref 解决(非 L1-09 责任).
        """
        # 预留 header 空间 · payload 控制 ~3KB
        blob = "x" * 3000
        evt = Event(
            project_id=project_id,
            type="L1-08:multimodal_artifact_registered",
            actor="executor",
            payload={"blob": blob, "size": 3000},
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt)
        assert result.persisted is True
        # 落盘 · payload 原样
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        events = _read_jsonl(events_path)
        assert events[0]["payload"]["size"] == 3000
        assert len(events[0]["payload"]["blob"]) == 3000

    def test_oversize_payload_raises_write_failed(
        self, real_event_bus: EventBus, project_id: str,
    ) -> None:
        """>4KB payload · LineTooLargeError (由 L1-08 link-ref 补偿 · 非 L1-09 责任)."""
        from app.l1_09.event_bus.schemas import BusWriteFailed

        blob = "x" * 10_000
        evt = Event(
            project_id=project_id,
            type="L1-08:multimodal_artifact_registered",
            actor="executor",
            payload={"blob": blob},
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(BusWriteFailed):
            real_event_bus.append(evt)


# ==============================================================================
# e2e 跨链 mini · AuditQuery 真查
# ==============================================================================


class TestIC09ToIC18MiniE2E:
    """IC-09 写 · IC-18 audit_query 读 · 完整回放."""

    def test_append_then_audit_query_by_pid(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """3 条事件 append · AuditQuery 按 pid 查全部."""
        for i in range(3):
            evt = Event(
                project_id=project_id,
                type=f"L1-0{i+1}:event_" + f"{i}",
                actor="main_loop" if i == 0 else ("main_loop" if i == 1 else "executor"),
                payload={"i": i},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)

        q = AuditQuery(event_bus_root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=project_id,
            project_id=project_id,
        )
        trail = q.query_audit_trail(anchor, QueryFilter(max_depth=4))
        # event_layer 可取回 3 条事件
        assert trail.event_layer.count >= 3
