"""Deviation evaluator · 纯函数 · evaluate_deviation(snapshot) → DeviationVerdict[]。

规则（简化版 brief §3）：
- 对 snapshot.eight_dim_vector 每维调 _classify_dim · 生成 DeviationVerdict
- 维值 None → absent_is（默认 INFO）· 不崩
- 维值存在但未配置 threshold → INFO
- comparison=gt · value >= critical → CRITICAL（依次退 ERROR / WARN / INFO）
- verdict.evidence_refs 从 snapshot.dim_evidence_refs[dim] 复用

确定性：
- 不读 wall-clock · 用 snapshot.captured_at_ms
- 相同 snapshot + 相同 matrix → 8 条字节相同 verdict
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.supervisor.deviation_judge.schemas import (
    DeviationLevel,
    DeviationVerdict,
    DimensionKey,
    DimensionThreshold,
    ThresholdMatrix,
)
from app.supervisor.dim_collector.schemas import SupervisorSnapshot


_DIM_KEYS = (
    DimensionKey.PHASE,
    DimensionKey.ARTIFACTS,
    DimensionKey.WP_STATUS,
    DimensionKey.TOOL_CALLS,
    DimensionKey.LATENCY_SLO,
    DimensionKey.SELF_REPAIR_RATE,
    DimensionKey.ROLLBACK_COUNTER,
    DimensionKey.EVENT_BUS,
)


def evaluate_deviation(
    snapshot: SupervisorSnapshot, matrix: ThresholdMatrix
) -> list[DeviationVerdict]:
    """L2-02 主入口 · 纯函数 · 8 维 → 8 verdict。

    Args:
        snapshot: L2-01 产出的 SupervisorSnapshot
        matrix: ThresholdMatrix（default_matrix() 或 YAML 加载）

    Returns:
        按 _DIM_KEYS 顺序固定 8 条 verdict · INFO 也产（下游自行 skip）
    """
    vector = snapshot.eight_dim_vector
    verdicts: list[DeviationVerdict] = []
    for dim in _DIM_KEYS:
        dim_value = getattr(vector, dim.value)
        threshold = matrix.get(dim)
        evidence_refs = vector.dim_evidence_refs.get(dim.value, ())
        verdict = _classify_dim(
            snapshot=snapshot,
            dim=dim,
            dim_value=dim_value,
            threshold=threshold,
            evidence_refs=evidence_refs,
        )
        verdicts.append(verdict)
    return verdicts


def _classify_dim(
    *,
    snapshot: SupervisorSnapshot,
    dim: DimensionKey,
    dim_value: Any,
    threshold: DimensionThreshold | None,
    evidence_refs: tuple[str, ...],
) -> DeviationVerdict:
    """单维分级 · 推导 DeviationLevel + reason。

    注意 `phase` 维是 str · 其余 7 维是 dict · 对 phase 直接取 value 字符串比较（eq/ne 模式）。
    """
    # 1. 维缺 → absent_is（默认 INFO）
    if dim_value is None:
        level = threshold.absent_is if threshold is not None else DeviationLevel.INFO
        return _build_verdict(
            snapshot=snapshot,
            dim=dim,
            level=level,
            value=None,
            threshold_val=None,
            reason=(
                threshold.reason_template.format(
                    dim=dim.value, path="<absent>", value=None, level=level.value,
                    threshold=None,
                )
                if threshold is not None
                else f"dim={dim.value} absent · no_threshold"
            ),
            evidence_refs=evidence_refs,
        )

    # 2. 未配 threshold · INFO
    if threshold is None:
        return _build_verdict(
            snapshot=snapshot,
            dim=dim,
            level=DeviationLevel.INFO,
            value=dim_value,
            threshold_val=None,
            reason=f"dim={dim.value} no_threshold_config · INFO default",
            evidence_refs=evidence_refs,
        )

    # 3. 取路径上的 numeric value
    raw_value = _extract_metric(dim_value, threshold.metric_path)
    if raw_value is None:
        # 路径不存在 · 降级 INFO（不抛 · PRD 要求保守）
        return _build_verdict(
            snapshot=snapshot,
            dim=dim,
            level=DeviationLevel.INFO,
            value=dim_value,
            threshold_val=None,
            reason=f"dim={dim.value} metric_path={threshold.metric_path} missing · INFO fallback",
            evidence_refs=evidence_refs,
        )

    # 4. 按 comparison 判级
    level, hit_threshold = _apply_comparison(
        value=raw_value, threshold=threshold
    )
    reason = threshold.reason_template.format(
        dim=dim.value,
        path=threshold.metric_path,
        value=raw_value,
        level=level.value,
        threshold=hit_threshold,
    )
    return _build_verdict(
        snapshot=snapshot,
        dim=dim,
        level=level,
        value=raw_value,
        threshold_val=hit_threshold,
        reason=reason,
        evidence_refs=evidence_refs,
    )


def _extract_metric(dim_value: Any, path: str) -> float | int | None:
    """支持点号路径 · 如 'a.b.c'。失败返 None（不抛）。

    - dim_value 是 dict → 按 path 递归取值
    - dim_value 是 str（如 phase）→ path=='self' 时返回 hash(str) 的确定性数字（简化）·
      否则无法抽取 numeric → None（触发 INFO fallback）
    - 其他类型 → None
    """
    if isinstance(dim_value, str):
        # phase 特殊 · 只有 path='self' 才取 hash · 否则 None
        if path == "self":
            return sum(ord(c) for c in dim_value)
        return None
    if not isinstance(dim_value, dict):
        return None
    cur: Any = dim_value
    for seg in path.split("."):
        if not isinstance(cur, dict):
            return None
        if seg not in cur:
            return None
        cur = cur[seg]
    if isinstance(cur, bool):
        # bool 特判 · 避免 True==1 引发阈值比较
        return int(cur)
    if isinstance(cur, (int, float)):
        return cur
    return None


def _apply_comparison(
    value: float | int,
    threshold: DimensionThreshold,
) -> tuple[DeviationLevel, float | None]:
    """按 comparison 方向 + 3 阈值判级。返回 (level, 命中阈值)。"""
    # 依 comparison 决定严重度方向
    if threshold.comparison == "gt":
        # 越大越严重 · critical → error → warn → INFO
        if threshold.critical_threshold is not None and value >= threshold.critical_threshold:
            return DeviationLevel.CRITICAL, threshold.critical_threshold
        if threshold.error_threshold is not None and value >= threshold.error_threshold:
            return DeviationLevel.ERROR, threshold.error_threshold
        if threshold.warn_threshold is not None and value >= threshold.warn_threshold:
            return DeviationLevel.WARN, threshold.warn_threshold
        return DeviationLevel.INFO, None
    if threshold.comparison == "lt":
        # 越小越严重
        if threshold.critical_threshold is not None and value <= threshold.critical_threshold:
            return DeviationLevel.CRITICAL, threshold.critical_threshold
        if threshold.error_threshold is not None and value <= threshold.error_threshold:
            return DeviationLevel.ERROR, threshold.error_threshold
        if threshold.warn_threshold is not None and value <= threshold.warn_threshold:
            return DeviationLevel.WARN, threshold.warn_threshold
        return DeviationLevel.INFO, None
    if threshold.comparison == "eq":
        # 等于 critical 即 CRITICAL · 等于 error 即 ERROR · ...
        if threshold.critical_threshold is not None and value == threshold.critical_threshold:
            return DeviationLevel.CRITICAL, threshold.critical_threshold
        if threshold.error_threshold is not None and value == threshold.error_threshold:
            return DeviationLevel.ERROR, threshold.error_threshold
        if threshold.warn_threshold is not None and value == threshold.warn_threshold:
            return DeviationLevel.WARN, threshold.warn_threshold
        return DeviationLevel.INFO, None
    # ne · 不等于即命中
    if threshold.comparison == "ne":
        if threshold.critical_threshold is not None and value != threshold.critical_threshold:
            return DeviationLevel.CRITICAL, threshold.critical_threshold
        if threshold.error_threshold is not None and value != threshold.error_threshold:
            return DeviationLevel.ERROR, threshold.error_threshold
        if threshold.warn_threshold is not None and value != threshold.warn_threshold:
            return DeviationLevel.WARN, threshold.warn_threshold
        return DeviationLevel.INFO, None
    return DeviationLevel.INFO, None


def _build_verdict(
    *,
    snapshot: SupervisorSnapshot,
    dim: DimensionKey,
    level: DeviationLevel,
    value: Any,
    threshold_val: float | None,
    reason: str,
    evidence_refs: tuple[str, ...],
) -> DeviationVerdict:
    """组装单条 verdict · 派生确定性 verdict_id。"""
    verdict_id = _derive_verdict_id(
        snapshot_id=snapshot.snapshot_id,
        dim=dim.value,
        level=level.value,
    )
    return DeviationVerdict(
        project_id=snapshot.project_id,
        snapshot_id=snapshot.snapshot_id,
        dimension=dim,
        level=level,
        value=value,
        threshold=threshold_val,
        reason=reason,
        evidence_refs=tuple(evidence_refs),
        captured_at_ms=snapshot.captured_at_ms,
        verdict_id=verdict_id,
    )


def _derive_verdict_id(snapshot_id: str, dim: str, level: str) -> str:
    """确定性 verdict_id。相同 (snapshot_id, dim, level) 永远产出相同 id。"""
    h = hashlib.sha256(f"{snapshot_id}:{dim}:{level}".encode("utf-8")).hexdigest()[:12]
    return f"verdict-{snapshot_id[-8:]}-{dim}-{h}"


def filter_actionable(verdicts: list[DeviationVerdict]) -> list[DeviationVerdict]:
    """过滤掉 INFO（不走 IC 出口）· 返回 WARN/ERROR/CRITICAL 的 verdict。

    下游 subagent 调用这个做路由选择（level → IC 映射见 __init__.LEVEL_TO_IC）。
    """
    return [v for v in verdicts if v.level is not DeviationLevel.INFO]
