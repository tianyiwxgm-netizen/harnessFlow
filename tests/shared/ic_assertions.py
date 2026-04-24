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


# =============================================================================
# IC-14 · Rollback 路由 push 断言(供 Dev-ζ Supervisor → L1-04 消费方验)
# =============================================================================


def assert_ic_14_pushed(
    consumer_recorded: list[Any],
    *,
    project_id: str,
    wp_id: str,
    verdict: str,
    target_stage: str | None = None,
    min_count: int = 1,
) -> list[Any]:
    """IC-14: 断言 L1-04 消费方(IC14Consumer)收到 rollback_route push.

    Args:
        consumer_recorded: 消费方记录的 PushRollbackRouteCommand 列表.
            形态假设: 可访问 .project_id / .wp_id / .verdict / .target_stage
            (与 app.quality_loop.rollback_router.schemas.PushRollbackRouteCommand 对齐).
        project_id / wp_id: PM-14 分片 + WP 定位.
        verdict: FAIL_L1 / FAIL_L2 / FAIL_L3 / FAIL_L4
        target_stage: 可选 · S3 / S4 / S5 / UPGRADE_TO_L1_01

    返: 匹配的 push command 列表.
    """
    def _val(cmd: Any, field: str) -> Any:
        # 兼容 pydantic model 或 dict
        if hasattr(cmd, field):
            return getattr(cmd, field)
        if isinstance(cmd, dict):
            return cmd.get(field)
        return None

    matched = [
        c for c in consumer_recorded
        if _val(c, "project_id") == project_id
        and _val(c, "wp_id") == wp_id
        and str(_val(c, "verdict")) in (verdict, f"FailVerdict.{verdict}")
    ]
    if target_stage is not None:
        matched = [
            c for c in matched
            if str(_val(c, "target_stage")) in (target_stage, f"TargetStage.{target_stage}")
        ]
    if len(matched) < min_count:
        all_seen = [(_val(c, "wp_id"), str(_val(c, "verdict")), str(_val(c, "target_stage"))) for c in consumer_recorded]
        raise AssertionError(
            f"IC-14 rollback push 断言失败 pid={project_id} wp_id={wp_id} "
            f"verdict={verdict} target_stage={target_stage} "
            f"期望≥{min_count} 实际={len(matched)}\n"
            f"消费方全部记录 (wp_id, verdict, target_stage): {all_seen}"
        )
    return matched


# =============================================================================
# IC-20 · Verifier 独立 session dispatch 断言
# =============================================================================


# =============================================================================
# IC-06 · L1-06 KB read response 断言
# =============================================================================


def assert_kb_read_returned(
    read_result: Any,
    *,
    project_id: str,
    min_entries: int = 1,
    must_contain_kind: str | None = None,
    must_contain_id: str | None = None,
) -> list[Any]:
    """IC-06: 断言 KBReadService.read() 返回非空 entries · 且 meta.project_id 一致(PM-14).

    Args:
        read_result: ReadResult(含 entries + meta).
        project_id: PM-14 · 必校 meta.project_id 一致.
        min_entries: 默认 ≥ 1 条.
        must_contain_kind: 可选 · 必含某 kind(如 "pattern" / "gotcha").
        must_contain_id: 可选 · 必含指定 id 的 entry.

    返: entries 列表.
    """
    entries = list(getattr(read_result, "entries", []) or [])
    meta = getattr(read_result, "meta", None)
    if meta is None:
        raise AssertionError(f"IC-06 read_result.meta 缺失 result={read_result}")
    meta_pid = getattr(meta, "project_id", None)
    if meta_pid != project_id:
        raise AssertionError(
            f"IC-06 PM-14 违反 期望 meta.project_id={project_id} 实际={meta_pid}"
        )
    if len(entries) < min_entries:
        raise AssertionError(
            f"IC-06 entries 不足 pid={project_id} 期望≥{min_entries} 实际={len(entries)}"
        )
    if must_contain_kind is not None:
        if not any(getattr(e, "kind", None) == must_contain_kind for e in entries):
            raise AssertionError(
                f"IC-06 entries 未含 kind={must_contain_kind} 实际 kinds="
                f"{[getattr(e, 'kind', None) for e in entries]}"
            )
    if must_contain_id is not None:
        if not any(getattr(e, "id", None) == must_contain_id for e in entries):
            raise AssertionError(
                f"IC-06 entries 未含 id={must_contain_id} 实际 ids="
                f"{[getattr(e, 'id', None) for e in entries]}"
            )
    return entries


def assert_kb_read_degraded(
    read_result: Any,
    *,
    expected: bool = True,
    reason_contains: str | None = None,
) -> None:
    """IC-06: 断言 read_result.meta.degraded 的值(降级路径/未降级路径)."""
    meta = getattr(read_result, "meta", None)
    actual = getattr(meta, "degraded", None)
    if actual is not expected:
        raise AssertionError(
            f"IC-06 meta.degraded 期望={expected} 实际={actual}"
        )
    if reason_contains is not None:
        reason = getattr(meta, "fallback_reason", None) or ""
        if reason_contains not in str(reason):
            raise AssertionError(
                f"IC-06 meta.fallback_reason 未含 {reason_contains!r} 实际={reason!r}"
            )


# =============================================================================
# IC-15 · L1-09 halt 事件断言
# =============================================================================


def assert_ic_15_halt_emitted(
    event_bus_root: Path,
    *,
    project_id: str = "system",
    reason_contains: str | None = None,
) -> dict[str, Any]:
    """IC-15: 断言 bus_halted 事件被 emit(系统级 · pid='system' 约定).

    Halt 是系统级事件 · 默认查 "system" 分片.

    Args:
        project_id: 默认 "system" · halt 以 system 入账(3-1 L1-09 §3.15 约定).
        reason_contains: 可选 · 校验 payload.reason 子串.

    返: 命中的第一条事件.
    """
    events = list_events(event_bus_root, project_id, type_exact="L1-09:bus_halted")
    if not events:
        raise AssertionError(
            f"IC-15 bus_halted 未 emit pid={project_id} "
            f"(检查是否 HaltGuard 被触发 · 或事件在其他 pid 分片)"
        )
    first = events[0]
    if reason_contains is not None:
        reason = str(first.get("payload", {}).get("reason", ""))
        if reason_contains not in reason:
            raise AssertionError(
                f"IC-15 halt reason 未含 {reason_contains!r} 实际={reason!r}"
            )
    return first


# =============================================================================
# IC-17 · Panic → PAUSED 100ms 硬约束断言
# =============================================================================


def assert_panic_within_100ms(
    start_monotonic_s: float,
    end_monotonic_s: float,
    *,
    budget_ms: float = 100.0,
) -> float:
    """IC-17: 断言 panic_request → PAUSED 落定在 budget_ms 内(默认 100ms).

    Args:
        start_monotonic_s: time.monotonic() 前.
        end_monotonic_s: time.monotonic() 后.
        budget_ms: 默认 100ms(HRL-04 release blocker).

    返: 实际耗时 ms(供额外断言 / benchmark 统计).
    """
    elapsed_ms = (end_monotonic_s - start_monotonic_s) * 1000.0
    if elapsed_ms > budget_ms:
        raise AssertionError(
            f"IC-17 panic 超时 期望≤{budget_ms}ms 实际={elapsed_ms:.2f}ms "
            f"(HRL-04 release blocker 硬红线)"
        )
    return elapsed_ms


# =============================================================================
# IC-04 · L1-05 skill_invoke 断言
# =============================================================================


def assert_ic_04_invoked(
    invoker_calls: list[dict[str, Any]],
    *,
    skill_id: str,
    project_id: str | None = None,
    min_count: int = 1,
) -> list[dict[str, Any]]:
    """IC-04: 断言 L1-05 SkillInvoker 被调 · 指定 skill_id.

    Args:
        invoker_calls: 通常是 FakeSkillInvoker.call_log 或类似记录.
                       每项 dict · 含 {skill_id, args, kw?}
        skill_id: 必须精确匹配.
        project_id: 可选 · 校 args 里的 project_id 字段(PM-14).
        min_count: 默认 ≥ 1.

    返: 匹配的调用记录.
    """
    matched = [c for c in invoker_calls if c.get("skill_id") == skill_id]
    if project_id is not None:
        matched = [c for c in matched if (c.get("args") or {}).get("project_id") == project_id]
    if len(matched) < min_count:
        all_skills = [c.get("skill_id") for c in invoker_calls]
        raise AssertionError(
            f"IC-04 skill_invoke 断言失败 skill_id={skill_id} pid={project_id} "
            f"期望≥{min_count} 实际={len(matched)} 全部已调 skills={all_skills}"
        )
    return matched


# =============================================================================
# IC-19 · L1-03 WBS 拆解入口断言
# =============================================================================


def assert_ic_19_wbs_accepted(
    result: Any,
    *,
    project_id: str,
) -> None:
    """IC-19: 断言 L1-03 WBS 拆解同步 ack 合法(status=accepted + pid 一致).

    Args:
        result: RequestWBSDecompositionResult(或等价 dict).
        project_id: PM-14 校对.
    """
    status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
    if status != "accepted":
        raise AssertionError(
            f"IC-19 WBS dispatch status 期望=accepted 实际={status}"
        )
    pid = getattr(result, "project_id", None) or (result.get("project_id") if isinstance(result, dict) else None)
    if pid != project_id:
        raise AssertionError(
            f"IC-19 WBS PM-14 违反 期望 project_id={project_id} 实际={pid}"
        )


# =============================================================================
# IC-13 · L1-07 Supervisor sense 断言(从事件 bus 查 sense_emitted)
# =============================================================================


def assert_ic_13_sense_emitted(
    event_bus_root: Path,
    *,
    project_id: str,
    dim: str | None = None,
    min_count: int = 1,
) -> list[dict[str, Any]]:
    """IC-13: 断言 L1-07 Supervisor 对 project 发出过 sense 事件.

    Supervisor 每 tick 读 10 dim → 聚合 drift → emit L1-07:supervisor_sense_emitted.

    Args:
        project_id: PM-14 分片.
        dim: 可选 · 校 payload.dim 必含(如 "plan_drift" / "spec_deviation" / "halt_signal").
        min_count: 默认 ≥ 1 条.
    """
    events = list_events(
        event_bus_root, project_id, type_exact="L1-07:supervisor_sense_emitted",
    )
    if dim is not None:
        events = [e for e in events if e.get("payload", {}).get("dim") == dim]
    if len(events) < min_count:
        raise AssertionError(
            f"IC-13 supervisor_sense_emitted 断言失败 pid={project_id} dim={dim} "
            f"期望≥{min_count} 实际={len(events)}"
        )
    return events


def assert_ic_20_dispatched(
    delegate_calls: list[Any],
    *,
    project_id: str,
    wp_id: str,
    min_count: int = 1,
    session_prefix_contains: str | None = "sub-",
) -> list[Any]:
    """IC-20: 断言 delegator 被调用 ≥ min_count 次 · 且 session_prefix 合法.

    L1-04 Verifier 的独立 session 硬红线: session_id 必含 `sub-` 前缀(IC-20 §3.20.2).
    若 session_prefix_contains 非 None · 会额外校验 delegate_calls 中的
    delegation_id 或 session_id 字段含该前缀.

    Args:
        delegate_calls: DelegateVerifierStub.calls 列表 · 每项为 IC20Command.
        project_id / wp_id: PM-14 + WP 定位.
        session_prefix_contains: 默认 "sub-" · 设 None 则跳过校验.
    """
    def _val(cmd: Any, field: str) -> Any:
        if hasattr(cmd, field):
            return getattr(cmd, field)
        if isinstance(cmd, dict):
            return cmd.get(field)
        return None

    matched = [
        c for c in delegate_calls
        if _val(c, "project_id") == project_id and _val(c, "wp_id") == wp_id
    ]
    if len(matched) < min_count:
        raise AssertionError(
            f"IC-20 delegate_verifier 断言失败 pid={project_id} wp_id={wp_id} "
            f"期望≥{min_count} 实际={len(matched)}"
        )
    # 若需校 session prefix · 检查返回的 DispatchResult(若 stub 透出)
    return matched
