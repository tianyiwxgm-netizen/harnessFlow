"""L1-04 · L2-04 · MetricSampler tests · 嵌套 data-source 输入规范化.

映射:
- brief · metric_sampler.py(接收 PRD §7 SLO)
- `app.quality_loop.gate_compiler.metric_sampler`

职责:
- 接收外部 S4/S5 送入的嵌套 dict (顶层 key ∈ WHITELISTED_DATA_SOURCE_KEYS)
- 规范化为 `MetricSample`
- sample_hash 稳定计算（幂等 key）
- project_id 必填（PM-14）
- 类型限制: 顶层 dict · 子 dict 值 scalar / list
"""
from __future__ import annotations

import pytest

from app.quality_loop.gate_compiler.metric_sampler import (
    MetricSample,
    MetricSampler,
    MetricSamplerError,
)


class TestMetricSamplerHappyPath:
    def test_TC_L204_MS_001_sample_from_nested_dict_basic(self) -> None:
        """TC-L204-MS-001 · 嵌套 metric dict → MetricSample · hash 非空。"""
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={
                "coverage": {"line_rate": 0.85, "ac_coverage": 1.0},
                "lint": {"error_count": 0},
            },
            wp_id="wp-01",
        )
        assert isinstance(sample, MetricSample)
        assert sample.project_id == "p1"
        assert sample.wp_id == "wp-01"
        assert sample.values == {
            "coverage": {"line_rate": 0.85, "ac_coverage": 1.0},
            "lint": {"error_count": 0},
        }
        assert len(sample.sample_hash) >= 16

    def test_TC_L204_MS_002_sample_hash_stable_for_same_input(self) -> None:
        """TC-L204-MS-002 · 同 (pid, wp, metrics) · hash 一致（幂等）。"""
        sampler = MetricSampler()
        s1 = sampler.sample(
            project_id="p1",
            metrics={"coverage": {"line_rate": 0.9, "ac_coverage": 1.0}},
            wp_id="wp1",
        )
        s2 = sampler.sample(
            project_id="p1",
            metrics={"coverage": {"ac_coverage": 1.0, "line_rate": 0.9}},  # 顺序不同
            wp_id="wp1",
        )
        assert s1.sample_hash == s2.sample_hash, "hash 应对 dict key 顺序不敏感"

    def test_TC_L204_MS_003_sample_hash_differs_on_value_change(self) -> None:
        """TC-L204-MS-003 · 值变化 · hash 不同。"""
        sampler = MetricSampler()
        s1 = sampler.sample(project_id="p1", metrics={"coverage": {"line_rate": 0.8}})
        s2 = sampler.sample(project_id="p1", metrics={"coverage": {"line_rate": 0.9}})
        assert s1.sample_hash != s2.sample_hash

    def test_TC_L204_MS_004_sample_hash_includes_project_id(self) -> None:
        """TC-L204-MS-004 · 不同 project_id · 相同 metric · hash 不同。"""
        sampler = MetricSampler()
        s1 = sampler.sample(project_id="p1", metrics={"coverage": {"line_rate": 0.8}})
        s2 = sampler.sample(project_id="p2", metrics={"coverage": {"line_rate": 0.8}})
        assert s1.sample_hash != s2.sample_hash

    def test_TC_L204_MS_005_accepts_bool_none_str_list(self) -> None:
        """TC-L204-MS-005 · bool / None / str / list 全通过（artifact.files 用 list）。"""
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={
                "test_result": {
                    "p0_all_pass": True,
                    "note": None,
                    "status": "green",
                    "fail_count": 0,
                    "pass_count": 10,
                },
                "artifact": {"files": ["a.py", "b.py"]},
            },
        )
        assert sample.values["test_result"]["p0_all_pass"] is True
        assert sample.values["test_result"]["note"] is None
        assert sample.values["artifact"]["files"] == ["a.py", "b.py"]

    def test_TC_L204_MS_006_all_whitelisted_sources_allowed(self) -> None:
        """TC-L204-MS-006 · 6 个白名单 data source 全接受。"""
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={
                "coverage": {"line_rate": 0.9},
                "test_result": {"pass_count": 5, "fail_count": 0},
                "lint": {"error_count": 0},
                "security_scan": {"high_severity_count": 0},
                "perf": {"p95_ms": 100.0},
                "artifact": {"files": []},
            },
        )
        assert len(sample.values) == 6


class TestMetricSamplerValidation:
    def test_TC_L204_MS_010_empty_project_id_raises(self) -> None:
        """TC-L204-MS-010 · project_id 空 · E_L204_NO_PROJECT_ID。"""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_NO_PROJECT_ID"):
            sampler.sample(project_id="", metrics={"coverage": {"line_rate": 0.8}})

    def test_TC_L204_MS_011_whitespace_project_id_raises(self) -> None:
        """TC-L204-MS-011 · project_id 仅空格 · E_L204_NO_PROJECT_ID。"""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_NO_PROJECT_ID"):
            sampler.sample(project_id="   ", metrics={"coverage": {"line_rate": 0.8}})

    def test_TC_L204_MS_012_nested_field_value_rejected(self) -> None:
        """TC-L204-MS-012 · 子 dict 中再嵌套 dict · E_L204_MS_NESTED_VALUE。"""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_MS_NESTED_VALUE"):
            sampler.sample(
                project_id="p1",
                metrics={"coverage": {"nested": {"k": 1}}},
            )

    def test_TC_L204_MS_013_top_level_non_dict_rejected(self) -> None:
        """TC-L204-MS-013 · 顶层值非 dict · E_L204_MS_TOP_NOT_DICT。"""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_MS_TOP_NOT_DICT"):
            sampler.sample(project_id="p1", metrics={"coverage": 0.85})

    def test_TC_L204_MS_014_unknown_data_source_rejected(self) -> None:
        """TC-L204-MS-014 · 顶层 key 非白名单 · E_L204_MS_UNKNOWN_DATA_SRC."""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_MS_UNKNOWN_DATA_SRC"):
            sampler.sample(project_id="p1", metrics={"unknown_source": {"a": 1}})

    def test_TC_L204_MS_015_empty_metrics_dict_allowed(self) -> None:
        """TC-L204-MS-015 · 空 metric dict · 允许（返 hash 稳定 · 用作占位）。"""
        sampler = MetricSampler()
        sample = sampler.sample(project_id="p1", metrics={})
        assert sample.values == {}
        assert sample.sample_hash  # 有 hash

    def test_TC_L204_MS_016_bytes_value_rejected(self) -> None:
        """TC-L204-MS-016 · bytes 值 · E_L204_MS_BAD_VALUE."""
        sampler = MetricSampler()
        with pytest.raises(MetricSamplerError, match="E_L204_MS_BAD_VALUE"):
            sampler.sample(
                project_id="p1",
                metrics={"coverage": {"raw": b"bytes"}},
            )


class TestMetricSampleVO:
    def test_TC_L204_MS_020_sample_is_frozen(self) -> None:
        """TC-L204-MS-020 · MetricSample frozen · 不可变。"""
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={"coverage": {"line_rate": 0.9}},
        )
        with pytest.raises((TypeError, ValueError)):
            sample.project_id = "p2"  # type: ignore[misc]

    def test_TC_L204_MS_021_sample_hash_hex_format(self) -> None:
        """TC-L204-MS-021 · sample_hash 十六进制字符。"""
        sampler = MetricSampler()
        sample = sampler.sample(
            project_id="p1",
            metrics={"coverage": {"line_rate": 0.9}},
        )
        assert all(c in "0123456789abcdef" for c in sample.sample_hash)

    def test_TC_L204_MS_022_extra_fields_forbidden(self) -> None:
        """TC-L204-MS-022 · 构造 MetricSample 直传未知字段 · ValidationError。"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MetricSample(
                project_id="p1",
                wp_id=None,
                values={"coverage": {"line_rate": 0.9}},
                sample_hash="abc12345678901234567890123456789",
                extra_field="nope",  # type: ignore[call-arg]
            )
