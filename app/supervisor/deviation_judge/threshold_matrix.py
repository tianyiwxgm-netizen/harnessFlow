"""ThresholdMatrix loader · YAML → pydantic ThresholdMatrix。

YAML schema 示例（config/threshold_matrix.yaml）：

```yaml
version: v1.0
dimensions:
  latency_slo:
    metric_path: p99_ms
    comparison: gt
    warn_threshold: 200
    error_threshold: 500
    critical_threshold: 1000
  self_repair_rate:
    metric_path: rate
    comparison: gt
    warn_threshold: 0.3
    error_threshold: 0.6
    critical_threshold: 0.9
```

加载流程：
1. 读 YAML · yaml.safe_load
2. 转 ThresholdMatrix · pydantic 校验（包含 monotonic + comparison 合法）
3. cache in memory（process 级 · 进程重启才重新加载）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.supervisor.deviation_judge.schemas import (
    DeviationError,
    DimensionKey,
    DimensionThreshold,
    ThresholdMatrix,
)


def load_matrix_from_yaml(path: Path | str) -> ThresholdMatrix:
    """从磁盘 YAML 加载并校验 ThresholdMatrix。

    失败抛 ValueError · 错误码在消息头部（E_THRESHOLD_MATRIX_*）。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{DeviationError.MATRIX_LOAD_FAIL.value}: file not found {p}"
        )
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(
            f"{DeviationError.MATRIX_YAML_CORRUPT.value}: {exc}"
        ) from exc
    return load_matrix_from_dict(raw)


def load_matrix_from_dict(raw: Any) -> ThresholdMatrix:
    """Dict → ThresholdMatrix。测试 / 构造期用。"""
    if not isinstance(raw, dict):
        raise ValueError(
            f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: root not dict"
        )
    version = str(raw.get("version", "v1.0"))
    dims_raw = raw.get("dimensions", {})
    if not isinstance(dims_raw, dict):
        raise ValueError(
            f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: dimensions not dict"
        )
    out: dict[DimensionKey, DimensionThreshold] = {}
    for dim_name, cfg in dims_raw.items():
        try:
            dim = DimensionKey(dim_name)
        except ValueError as exc:
            raise ValueError(
                f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: unknown dim {dim_name}"
            ) from exc
        if not isinstance(cfg, dict):
            raise ValueError(
                f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: {dim_name} cfg not dict"
            )
        out[dim] = DimensionThreshold(
            dimension=dim,
            metric_path=str(cfg.get("metric_path", "value")),
            comparison=str(cfg.get("comparison", "gt")),
            warn_threshold=_to_float_or_none(cfg.get("warn_threshold")),
            error_threshold=_to_float_or_none(cfg.get("error_threshold")),
            critical_threshold=_to_float_or_none(cfg.get("critical_threshold")),
            absent_is=_parse_absent(cfg.get("absent_is", "INFO")),
            reason_template=str(
                cfg.get(
                    "reason_template",
                    "dim={dim} path={path} value={value} level={level} threshold={threshold}",
                )
            ),
        )
    return ThresholdMatrix(version=version, dimensions=out)


def _to_float_or_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: non-numeric threshold {v!r}"
        ) from exc


def _parse_absent(v: Any) -> Any:
    """将 'INFO' / 'WARN' 字符串转回 DeviationLevel。"""
    from app.supervisor.deviation_judge.schemas import DeviationLevel

    if isinstance(v, DeviationLevel):
        return v
    try:
        return DeviationLevel(str(v))
    except ValueError as exc:
        raise ValueError(
            f"{DeviationError.MATRIX_SCHEMA_INVALID.value}: absent_is {v!r}"
        ) from exc


def default_matrix() -> ThresholdMatrix:
    """默认 8 维阈值矩阵（brief §3 简化版）。

    所有 8 维都给 sensible defaults · 可被 YAML 覆盖。
    """
    return load_matrix_from_dict(
        {
            "version": "v1.0-default",
            "dimensions": {
                "latency_slo": {
                    "metric_path": "p99_ms",
                    "comparison": "gt",
                    "warn_threshold": 200,
                    "error_threshold": 500,
                    "critical_threshold": 1000,
                },
                "self_repair_rate": {
                    "metric_path": "rate",
                    "comparison": "gt",
                    "warn_threshold": 0.3,
                    "error_threshold": 0.6,
                    "critical_threshold": 0.9,
                },
                "rollback_counter": {
                    "metric_path": "count_24h",
                    "comparison": "gt",
                    "warn_threshold": 2,
                    "error_threshold": 5,
                    "critical_threshold": 10,
                },
                "tool_calls": {
                    "metric_path": "error_rate",
                    "comparison": "gt",
                    "warn_threshold": 0.1,
                    "error_threshold": 0.3,
                    "critical_threshold": 0.5,
                },
                "event_bus": {
                    "metric_path": "lag_ms",
                    "comparison": "gt",
                    "warn_threshold": 500,
                    "error_threshold": 2000,
                    "critical_threshold": 5000,
                },
                # phase 是 str · 默认仅用 absent_is=INFO · 实际阈值留空 ·
                # 如需对 phase 做检查 · 用 comparison=eq + metric_path=self + 预期 hash
                "phase": {
                    "metric_path": "self",
                    "comparison": "gt",
                    "absent_is": "INFO",
                },
                "artifacts": {
                    "metric_path": "missing_count",
                    "comparison": "gt",
                    "warn_threshold": 1,
                    "error_threshold": 3,
                    "critical_threshold": 5,
                },
                "wp_status": {
                    "metric_path": "fail_count",
                    "comparison": "gt",
                    "warn_threshold": 1,
                    "error_threshold": 2,
                    "critical_threshold": 3,
                },
            },
        }
    )
