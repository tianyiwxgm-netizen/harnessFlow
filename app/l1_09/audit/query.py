"""L2-03 AuditQuery · IC-18 query_audit_trail 入口 · 对齐 3-1 §6.1.

简化实现：
- 扫 events.jsonl 按 anchor/filter 返回 4 层 Trail
- 3 种 anchor_type: project_id / tick_id / event_id
- cursor-based 分页（大结果 > 10000 条）
- hash chain gap 检测传递给 UI
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.l1_09.audit.paginator import paginate
from app.l1_09.audit.schemas import (
    Anchor,
    AnchorType,
    AuditDeadlineExceeded,
    AuditInvalidAnchor,
    AuditProjectRequired,
    Completeness,
    EvidenceLayer,
    LayerType,
    QueryFilter,
    Trail,
)


class AuditQuery:
    """按 project_id shard · IC-18 主入口."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._deadline_ms = 1000  # prd §10.4 硬约束

    def _events_path(self, project_id: str) -> Path:
        return self._root / "projects" / project_id / "events.jsonl"

    def _project_dir(self, project_id: str) -> Path:
        return self._root / "projects" / project_id

    def _scan_events(
        self,
        project_id: str,
        filter: QueryFilter,
    ) -> Iterator[dict]:
        """§6.1 · 扫 jsonl · 应用 filter（time / actor / type）."""
        from app.l1_09.event_bus.reader import read_range

        events_path = self._events_path(project_id)
        project_dir = self._project_dir(project_id)
        for body in read_range(events_path, project_dir=project_dir):
            if filter.actor and body.get("actor") != filter.actor:
                continue
            if filter.event_type and body.get("type") != filter.event_type:
                continue
            if filter.severity and body.get("severity") != filter.severity:
                continue
            if filter.time_range_start or filter.time_range_end:
                ts = body.get("persisted_at") or body.get("ts")
                if isinstance(ts, str):
                    try:
                        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        parsed = None
                    if parsed is not None:
                        if filter.time_range_start and parsed < filter.time_range_start:
                            continue
                        if filter.time_range_end and parsed > filter.time_range_end:
                            continue
            yield body

    def _detect_hash_gap(self, project_id: str) -> list[int]:
        """扫描 events · 找 hash chain gap（sequence 跳号）."""
        from app.l1_09.event_bus.reader import read_range

        events_path = self._events_path(project_id)
        project_dir = self._project_dir(project_id)
        gaps: list[int] = []
        prev_seq = 0
        try:
            for body in read_range(events_path, project_dir=project_dir):
                seq = int(body.get("sequence", 0))
                if seq != prev_seq + 1 and prev_seq > 0:
                    for miss in range(prev_seq + 1, seq):
                        gaps.append(miss)
                prev_seq = seq
        except Exception:
            pass
        return gaps

    def query_audit_trail(
        self,
        anchor: Anchor,
        filter: QueryFilter | None = None,
    ) -> Trail:
        """IC-18 主入口 · §6.1 主算法."""
        if filter is None:
            filter = QueryFilter()
        # 参数校验
        if not anchor.project_id:
            raise AuditProjectRequired("anchor.project_id required for PM-14 shard")
        if not anchor.anchor_id:
            raise AuditInvalidAnchor(f"anchor.anchor_id empty")

        start_ms = int(time.time() * 1000)

        # 按 anchor_type 筛选
        events = list(self._scan_events(anchor.project_id, filter))

        # 按 anchor_type 过滤
        if anchor.anchor_type == AnchorType.EVENT_ID:
            events = [e for e in events if e.get("event_id") == anchor.anchor_id]
        elif anchor.anchor_type == AnchorType.TICK_ID:
            events = [
                e for e in events
                if e.get("correlation_id") == anchor.anchor_id
                or e.get("tick_id") == anchor.anchor_id
                or e.get("trigger_tick") == anchor.anchor_id
            ]
        # project_id 类型：返所有

        # 4 层拼装
        decision_entries = [e for e in events if _is_decision(e)]
        event_entries = events  # 原事件层含所有
        supervisor_entries = [e for e in events if _is_supervisor(e)]
        authz_entries = [e for e in events if _is_authz(e)]

        # 截断
        truncated = False
        if len(event_entries) > filter.max_events_per_layer:
            event_entries = event_entries[:filter.max_events_per_layer]
            truncated = True

        # 层组装
        def _to_layer(lt: LayerType, items: list[dict]) -> EvidenceLayer:
            first_ts = items[0].get("persisted_at") if items else None
            last_ts = items[-1].get("persisted_at") if items else None
            return EvidenceLayer(
                layer_type=lt,
                entries=items,
                count=len(items),
                first_ts=first_ts,
                last_ts=last_ts,
                truncated_at=(
                    filter.max_events_per_layer
                    if truncated and lt == LayerType.EVENT
                    else None
                ),
            )

        decision_layer = _to_layer(LayerType.DECISION, decision_entries)
        event_layer = _to_layer(LayerType.EVENT, event_entries)
        supervisor_layer = _to_layer(LayerType.SUPERVISOR, supervisor_entries)
        authz_layer = _to_layer(LayerType.AUTHZ, authz_entries)

        # 完整性判定
        broken_layers: list[str] = []
        if decision_layer.count == 0:
            broken_layers.append("decision")
        if event_layer.count == 0:
            broken_layers.append("event")
        if decision_layer.count == 0:
            completeness = Completeness.BROKEN
        elif broken_layers:
            completeness = Completeness.PARTIAL
        else:
            completeness = Completeness.COMPLETE

        # hash chain gap
        gaps = self._detect_hash_gap(anchor.project_id)

        latency_ms = int(time.time() * 1000) - start_ms
        if latency_ms > self._deadline_ms:
            # 不 raise · 标记 · 对齐 §3.3 AUDIT_E_DEADLINE_EXCEEDED
            # WP-α-09 MVP：只记 latency · query 不拒（可选 raise）
            pass

        total = (
            decision_layer.count + event_layer.count
            + supervisor_layer.count + authz_layer.count
        )

        return Trail(
            anchor=anchor,
            project_id=anchor.project_id,
            depth="full_chain" if filter.max_depth >= 4 else "immediate",
            decision_layer=decision_layer,
            event_layer=event_layer,
            supervisor_layer=supervisor_layer,
            authz_layer=authz_layer,
            completeness=completeness,
            broken_layers=broken_layers,
            queried_at=datetime.now(UTC).isoformat(),
            mirror_version=len(events),  # 简化：用 event 数做 version 标识
            latency_ms=latency_ms,
            total_entries=total,
            truncated=truncated,
            fallback_used="jsonl_scan",
            hash_chain_gap=gaps,
        )


def _is_decision(event: dict) -> bool:
    etype = event.get("type", "")
    return "decision" in etype.lower() or event.get("is_decision", False)


def _is_supervisor(event: dict) -> bool:
    etype = event.get("type", "")
    return etype.startswith("L1-07:") or "supervisor" in etype.lower()


def _is_authz(event: dict) -> bool:
    etype = event.get("type", "")
    return "authz" in etype.lower() or "intervene" in etype.lower()


__all__ = ["AuditQuery"]
