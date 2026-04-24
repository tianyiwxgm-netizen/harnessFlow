"""tests/shared/ic_assertions.py · 公共 IC 契约断言库(M3-WP01).

**定位**:
    给 20 IC × 15 TC + 12 acceptance 的通用断言抽象层 · 避免每 TC 里手写
    "读 events.jsonl → 过滤 type → 字段比对"的重复 boilerplate.

**断言分 3 层**:
    1. **IC-09 审计**(最热 · 全 L1 生产方): `assert_ic_09_emitted` · 查真实落盘 events.jsonl
    2. **IC-01 state_transition** : `assert_state_transition_to` · L1-02 spy 验签
    3. **PM-14 跨 pid 隔离**: `assert_no_events_for_pid` · 防止事件泄分片

**PM-14 铁律**: 所有断言默认 scoped by project_id · 查其他分片必须显式传 pid.

**核心契约依据**:
    - 3-1 L1-09 §3.2 Event schema(type 前缀白名单 L1-01..10)
    - 3-1 L1-09 §5.1 project-shard 物理落盘: projects/<pid>/events.jsonl
    - 3-1 L1-02 §3.1 state_transition 必填: project_id + wp_id + new_wp_state + escalated + route_id
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


# =============================================================================
# IC-09 · L1-09 EventBus 审计事件断言
# =============================================================================


def _load_pid_events(event_bus_root: Path, project_id: str) -> list[dict[str, Any]]:
    """直读项目分片下 events.jsonl · 不走 AuditQuery 过滤(严格校落盘).

    物理路径: event_bus_root/projects/<pid>/events.jsonl
    """
    events_path = event_bus_root / "projects" / project_id / "events.jsonl"
    if not events_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in events_path.read_bytes().splitlines():
        if raw.strip():
            out.append(json.loads(raw.decode("utf-8")))
    return out


def list_events(
    event_bus_root: Path,
    project_id: str,
    *,
    type_prefix: str | None = None,
    type_exact: str | None = None,
) -> list[dict[str, Any]]:
    """列出 pid 分片下符合过滤条件的事件 · 供断言失败时诊断打印.

    Args:
        event_bus_root: conftest.event_bus_root fixture.
        project_id:     PM-14 分片 · 必显式传(无默认).
        type_prefix:    如 "L1-04:" · 只返该 L1 的事件.
        type_exact:     精确匹配 event.type.
    """
    events = _load_pid_events(event_bus_root, project_id)
    if type_exact is not None:
        events = [e for e in events if e.get("type") == type_exact]
    elif type_prefix is not None:
        events = [e for e in events if str(e.get("type", "")).startswith(type_prefix)]
    return events


def assert_ic_09_emitted(
    event_bus_root: Path,
    *,
    project_id: str,
    event_type: str,
    min_count: int = 1,
    payload_contains: dict[str, Any] | None = None,
    actor: str | None = None,
) -> list[dict[str, Any]]:
    """L1-09 IC-09: 断言 pid 分片内产生了特定 type 事件(≥ min_count 个).

    - event_type: 必带 L1-XX: 前缀(白名单)· 精确匹配 event.type
    - payload_contains: 子字典 key=value 全匹配(e.g. {"wp_id": "wp-1"})
    - actor: 若指定 · 校验 event.actor 精确匹配

    返: 匹配的事件列表(供继续校验 sequence/hash/ts).

    失败时 message 含: pid / event_type / min_count / 实际命中数 + 该 pid 下所有 type 列表(诊断).
    """
    matched = list_events(event_bus_root, project_id, type_exact=event_type)
    if payload_contains:
        matched = [
            e for e in matched
            if all(e.get("payload", {}).get(k) == v for k, v in payload_contains.items())
        ]
    if actor is not None:
        matched = [e for e in matched if e.get("actor") == actor]

    if len(matched) < min_count:
        all_types = sorted({e.get("type", "<missing>") for e in _load_pid_events(event_bus_root, project_id)})
        raise AssertionError(
            f"IC-09 事件断言失败 pid={project_id} type={event_type} "
            f"期望≥{min_count} 实际={len(matched)} "
            f"(含 payload_contains={payload_contains} actor={actor})\n"
            f"该 pid 下所有 type: {all_types}"
        )
    return matched


def assert_ic_09_hash_chain_intact(
    event_bus_root: Path,
    *,
    project_id: str,
) -> int:
    """IC-09 hash-chain: 断言 pid 分片 events.jsonl 的 sequence 连续 + prev_hash 串正确.

    返: 事件总条数(便于上游链长度断言).

    校验规则:
        1. sequence 从 1 连续递增 · 无 gap / 重复
        2. 第 1 条 prev_hash == GENESIS
        3. 第 N 条 prev_hash == 第 N-1 条的 hash
    """
    from app.l1_09.crash_safety.hash_chain import GENESIS_HASH

    events = _load_pid_events(event_bus_root, project_id)
    last_hash = GENESIS_HASH
    for i, evt in enumerate(events, start=1):
        seq = evt.get("sequence")
        if seq != i:
            raise AssertionError(
                f"IC-09 hash-chain sequence gap pid={project_id} "
                f"期望 seq={i} 实际 seq={seq}"
            )
        prev = evt.get("prev_hash")
        if prev != last_hash:
            raise AssertionError(
                f"IC-09 hash-chain prev_hash 不匹配 pid={project_id} seq={seq} "
                f"期望 prev_hash={last_hash!r} 实际={prev!r}"
            )
        last_hash = evt.get("hash")
    return len(events)


# =============================================================================
# PM-14 · 跨 pid 隔离断言
# =============================================================================


def assert_no_events_for_pid(
    event_bus_root: Path,
    *,
    project_id: str,
    allow_types: Iterable[str] = (),
) -> None:
    """PM-14 隔离断言: pid 分片下**不应有**任何事件(或只允许白名单 type).

    用于"foo pid 失败不泄 bar pid"矩阵隔离场景.

    Args:
        project_id: 被校验**无**事件的 pid.
        allow_types: 白名单(如 system startup 事件 · 默认空 = 不允许任何).
    """
    events = _load_pid_events(event_bus_root, project_id)
    if not events:
        return
    allow = set(allow_types)
    leaked = [e for e in events if e.get("type") not in allow]
    if leaked:
        leaked_types = [e.get("type") for e in leaked]
        raise AssertionError(
            f"PM-14 隔离违反 pid={project_id} 期望无事件 实际={len(leaked)} 条: "
            f"{leaked_types}"
        )


def assert_events_only_for_pid(
    event_bus_root: Path,
    *,
    expected_pid: str,
    checked_pids: Iterable[str],
) -> None:
    """PM-14 对偶断言: 在一组 pid 里 · 只有 expected_pid 允许有事件 · 其他必空.

    典型用法: 跨 pid 矩阵场景 · 校验只有受影响 pid 收事件:
        assert_events_only_for_pid(bus_root, expected_pid="proj-foo",
                                   checked_pids=["proj-foo","proj-bar","proj-baz"])
    """
    for pid in checked_pids:
        if pid == expected_pid:
            continue
        assert_no_events_for_pid(event_bus_root, project_id=pid)


# =============================================================================
# IC-01 · L1-02 state_transition 断言(基于 StateTransitionSpy 调用记录)
# =============================================================================


def assert_state_transition_to(
    spy_calls: list[dict[str, Any]],
    *,
    wp_id: str,
    new_wp_state: str,
    project_id: str | None = None,
    escalated: bool | None = None,
    route_id: str | None = None,
    min_count: int = 1,
) -> list[dict[str, Any]]:
    """IC-01: 断言 StateTransitionSpy 收到 wp_id → new_wp_state 的调用.

    spy_calls 形态: [{"project_id":..., "wp_id":..., "new_wp_state":..., ...}, ...]
    (与 tests/integration/l1_04_cross_l1/conftest.py 的 StateTransitionSpy 对齐)

    返: 匹配的调用列表.

    必填:
        wp_id / new_wp_state
    选填:
        project_id(PM-14 分片) / escalated / route_id
    """
    matched = [c for c in spy_calls if c.get("wp_id") == wp_id and c.get("new_wp_state") == new_wp_state]
    if project_id is not None:
        matched = [c for c in matched if c.get("project_id") == project_id]
    if escalated is not None:
        matched = [c for c in matched if c.get("escalated") == escalated]
    if route_id is not None:
        matched = [c for c in matched if c.get("route_id") == route_id]
    if len(matched) < min_count:
        raise AssertionError(
            f"IC-01 state_transition 断言失败 wp_id={wp_id} -> {new_wp_state} "
            f"期望≥{min_count} 实际={len(matched)} "
            f"(pid={project_id} escalated={escalated} route_id={route_id})\n"
            f"spy 实际调用数={len(spy_calls)} calls={spy_calls}"
        )
    return matched


def assert_no_state_transition(spy_calls: list[dict[str, Any]]) -> None:
    """IC-01 负向断言: spy 未收到任何调用(如 verifier 直接 PASS 无 rollback).

    失败时 message 含全部 spy 调用快照便于诊断.
    """
    if spy_calls:
        raise AssertionError(
            f"IC-01 期望 spy 无调用 实际={len(spy_calls)} calls={spy_calls}"
        )
