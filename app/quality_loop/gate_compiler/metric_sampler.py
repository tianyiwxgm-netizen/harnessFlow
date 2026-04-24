"""L1-04 · L2-04 · MetricSampler · 外部 metric → `MetricSample`.

**职责**：
1. 接收 S4/S5 送入的 dict[str, scalar]（coverage / tests_passed / latency_ms 等）。
2. 规范化为 frozen `MetricSample` VO（含稳定 sample_hash）。
3. 类型约束：int / float / bool / str / None（禁嵌套 · 防注入）。
4. key 必须 Python identifier（与 DoD 表达式 AST 白名单对齐）。

**幂等 hash**：对 `(project_id, wp_id, sorted_values)` 做 sha256 · 截断 32 hex。
同一语义输入 → 同 hash。GateVerdict.verdict_id 消费此 hash 做幂等 key。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.quality_loop.gate_compiler.schemas import GateCompilerError


class MetricSamplerError(GateCompilerError):
    """MetricSampler 层错误（输入非法 / hash 计算失败）。"""


_ALLOWED_VALUE_TYPES: tuple[type, ...] = (int, float, bool, str, type(None))


class MetricSample(BaseModel):
    """规范化 metric 样本 · frozen VO.

    - `project_id`   · PM-14
    - `wp_id`        · 可空（L2-04 评估粒度一般是 WP）
    - `values`       · 扁平 dict · 值类型严格限制
    - `sample_hash`  · 32 hex · 幂等 key
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(..., min_length=1)
    wp_id: str | None = None
    values: dict[str, Any] = Field(default_factory=dict)
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
        sample = sampler.sample(project_id="p1", metrics={"coverage": 0.85})
    """

    def sample(
        self,
        *,
        project_id: str,
        metrics: dict[str, Any],
        wp_id: str | None = None,
    ) -> MetricSample:
        """规范化 metric dict → `MetricSample`.

        Raises:
            MetricSamplerError:
                - `E_L204_NO_PROJECT_ID`     · project_id 空
                - `E_L204_MS_NESTED_VALUE`   · 值是 dict/list/tuple/set
                - `E_L204_MS_BAD_KEY`        · key 非 Python identifier
                - `E_L204_MS_BAD_VALUE`      · 值类型越界
        """
        if not project_id or not project_id.strip():
            raise MetricSamplerError("E_L204_NO_PROJECT_ID: project_id must be non-empty")

        normalized: dict[str, Any] = {}
        for key, value in metrics.items():
            if not isinstance(key, str) or not key.isidentifier():
                raise MetricSamplerError(
                    f"E_L204_MS_BAD_KEY: metric key {key!r} must be Python identifier",
                )
            if isinstance(value, (dict, list, tuple, set)):
                raise MetricSamplerError(
                    f"E_L204_MS_NESTED_VALUE: metric {key!r} value has nested type "
                    f"{type(value).__name__}; flat scalars only",
                )
            if not isinstance(value, _ALLOWED_VALUE_TYPES):
                raise MetricSamplerError(
                    f"E_L204_MS_BAD_VALUE: metric {key!r} has disallowed type "
                    f"{type(value).__name__}",
                )
            normalized[key] = value

        sample_hash = _compute_hash(project_id, wp_id, normalized)
        return MetricSample(
            project_id=project_id,
            wp_id=wp_id,
            values=normalized,
            sample_hash=sample_hash,
        )


def _compute_hash(project_id: str, wp_id: str | None, values: dict[str, Any]) -> str:
    """稳定 hash · sha256 前 32 hex。

    payload 结构：
        {"pid": "...", "wp": "..." or None, "v": {sorted key → value}}
    """
    payload = {
        "pid": project_id,
        "wp": wp_id,
        "v": dict(sorted(values.items())),
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


__all__ = [
    "MetricSample",
    "MetricSampler",
    "MetricSamplerError",
]
