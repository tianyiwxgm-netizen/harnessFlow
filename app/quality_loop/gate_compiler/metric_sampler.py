"""L1-04 · L2-04 · MetricSampler · 外部 metric → `MetricSample`.

**职责**：
1. 接收 S4/S5 送入的 `{data_source: {field: value}}` 嵌套 dict（对齐 WP01
   `WHITELISTED_DATA_SOURCE_KEYS`:coverage / test_result / lint / security_scan /
   perf / artifact）。
2. 规范化为 frozen `MetricSample` VO（含稳定 sample_hash）。
3. 顶层 key 必须是 `WHITELISTED_DATA_SOURCE_KEYS` 的子集（与 WP01 对齐 · 防注入）。
4. 子 dict 内字段值只能是 scalar（int/float/bool/str/None）或 list(用于 artifact.files)。

**幂等 hash**：对 `(project_id, wp_id, sorted_values)` 做 sha256 · 截断 32 hex。
同一语义输入 → 同 hash。GateVerdict.verdict_id 消费此 hash 做幂等 key。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.quality_loop.dod_compiler.predicate_eval import (
    WHITELISTED_DATA_SOURCE_KEYS,
)
from app.quality_loop.gate_compiler.schemas import GateCompilerError


class MetricSamplerError(GateCompilerError):
    """MetricSampler 层错误（输入非法 / hash 计算失败）。"""


_ALLOWED_VALUE_TYPES: tuple[type, ...] = (int, float, bool, str, type(None), list)


class MetricSample(BaseModel):
    """规范化 metric 样本 · frozen VO。

    - `project_id`   · PM-14
    - `wp_id`        · 可空
    - `values`       · **嵌套** dict：顶层 key ∈ WHITELISTED_DATA_SOURCE_KEYS,值为
                       field dict（与 WP01 `_make_library` 预期一致）。
    - `sample_hash`  · 32 hex · 幂等 key
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(..., min_length=1)
    wp_id: str | None = None
    values: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sample_hash: str = Field(..., min_length=16, max_length=64)

    @field_validator("project_id")
    @classmethod
    def _pid_stripped(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_L204_NO_PROJECT_ID")
        return v


class MetricSampler:
    """Metric 规范化器 · 无状态。

    用法:
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={"coverage": {"line_rate": 0.85}, "lint": {"error_count": 0}},
        )
    """

    def sample(
        self,
        *,
        project_id: str,
        metrics: dict[str, Any],
        wp_id: str | None = None,
    ) -> MetricSample:
        """规范化嵌套 metric dict → `MetricSample`.

        Args:
            project_id: PM-14 · 必填。
            metrics: 嵌套 dict · 顶层 key ∈ WHITELISTED_DATA_SOURCE_KEYS。
                值是 `{field: scalar | list}` 子 dict。
            wp_id: 可空 WP 标识。

        Raises:
            MetricSamplerError:
                - `E_L204_NO_PROJECT_ID`        · project_id 空
                - `E_L204_MS_UNKNOWN_DATA_SRC`  · 顶层 key ∉ 白名单
                - `E_L204_MS_NESTED_VALUE`     · 子 dict 值是嵌套 dict
                - `E_L204_MS_BAD_VALUE`        · 值类型越界
                - `E_L204_MS_TOP_NOT_DICT`     · 顶层值非 dict
        """
        if not project_id or not project_id.strip():
            raise MetricSamplerError("E_L204_NO_PROJECT_ID: project_id must be non-empty")

        normalized: dict[str, dict[str, Any]] = {}
        for top_key, top_value in metrics.items():
            if not isinstance(top_key, str):
                raise MetricSamplerError(
                    f"E_L204_MS_UNKNOWN_DATA_SRC: top-level key must be str, got {type(top_key).__name__}",
                )
            if top_key not in WHITELISTED_DATA_SOURCE_KEYS:
                raise MetricSamplerError(
                    f"E_L204_MS_UNKNOWN_DATA_SRC: {top_key!r} not in "
                    f"WHITELISTED_DATA_SOURCE_KEYS={sorted(WHITELISTED_DATA_SOURCE_KEYS)}",
                )
            if not isinstance(top_value, dict):
                raise MetricSamplerError(
                    f"E_L204_MS_TOP_NOT_DICT: metrics[{top_key!r}] must be dict, "
                    f"got {type(top_value).__name__}",
                )
            field_dict: dict[str, Any] = {}
            for field_key, field_value in top_value.items():
                if not isinstance(field_key, str):
                    raise MetricSamplerError(
                        f"E_L204_MS_BAD_KEY: {top_key!r}.{field_key!r} key must be str",
                    )
                if isinstance(field_value, dict):
                    raise MetricSamplerError(
                        f"E_L204_MS_NESTED_VALUE: {top_key!r}.{field_key!r} "
                        f"disallows nested dict",
                    )
                if not isinstance(field_value, _ALLOWED_VALUE_TYPES):
                    raise MetricSamplerError(
                        f"E_L204_MS_BAD_VALUE: {top_key!r}.{field_key!r} has "
                        f"disallowed type {type(field_value).__name__}",
                    )
                field_dict[field_key] = field_value
            normalized[top_key] = field_dict

        sample_hash = _compute_hash(project_id, wp_id, normalized)
        return MetricSample(
            project_id=project_id,
            wp_id=wp_id,
            values=normalized,
            sample_hash=sample_hash,
        )


def _compute_hash(
    project_id: str,
    wp_id: str | None,
    values: dict[str, dict[str, Any]],
) -> str:
    """稳定 hash · sha256 前 32 hex（对 dict key 顺序不敏感）。"""
    sorted_values = {
        src: dict(sorted(field_dict.items()))
        for src, field_dict in sorted(values.items())
    }
    payload = {
        "pid": project_id,
        "wp": wp_id,
        "v": sorted_values,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


__all__ = [
    "MetricSample",
    "MetricSampler",
    "MetricSamplerError",
]
