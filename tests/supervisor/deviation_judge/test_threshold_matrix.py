"""L2-02 · YAML ThresholdMatrix loader TC。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.supervisor.deviation_judge.schemas import DeviationLevel, DimensionKey
from app.supervisor.deviation_judge.threshold_matrix import (
    default_matrix,
    load_matrix_from_dict,
    load_matrix_from_yaml,
)


class TestLoadFromDict:
    def test_valid_raw(self) -> None:
        raw = {
            "version": "v1.0-test",
            "dimensions": {
                "latency_slo": {
                    "metric_path": "p99_ms",
                    "comparison": "gt",
                    "warn_threshold": 100,
                    "error_threshold": 200,
                    "critical_threshold": 500,
                },
            },
        }
        matrix = load_matrix_from_dict(raw)
        assert matrix.version == "v1.0-test"
        th = matrix.get(DimensionKey.LATENCY_SLO)
        assert th is not None
        assert th.warn_threshold == 100

    def test_root_not_dict_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_SCHEMA_INVALID"):
            load_matrix_from_dict(["a", "b"])

    def test_unknown_dim_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_SCHEMA_INVALID"):
            load_matrix_from_dict(
                {
                    "dimensions": {
                        "unknown_dim": {
                            "metric_path": "x",
                        }
                    }
                }
            )

    def test_non_numeric_threshold_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_SCHEMA_INVALID"):
            load_matrix_from_dict(
                {
                    "dimensions": {
                        "latency_slo": {
                            "metric_path": "p99_ms",
                            "warn_threshold": "abc",  # 非数字
                        }
                    }
                }
            )

    def test_absent_is_parsed(self) -> None:
        matrix = load_matrix_from_dict(
            {
                "dimensions": {
                    "phase": {
                        "metric_path": "drift_count",
                        "comparison": "gt",
                        "absent_is": "WARN",
                    }
                }
            }
        )
        th = matrix.get(DimensionKey.PHASE)
        assert th is not None
        assert th.absent_is is DeviationLevel.WARN

    def test_absent_is_invalid_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_SCHEMA_INVALID"):
            load_matrix_from_dict(
                {
                    "dimensions": {
                        "phase": {
                            "metric_path": "x",
                            "absent_is": "WTF",
                        }
                    }
                }
            )

    def test_dims_not_dict_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_SCHEMA_INVALID"):
            load_matrix_from_dict({"dimensions": ["bad"]})


class TestLoadFromYaml:
    def test_valid_yaml_file(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "matrix.yaml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "version": "v1-file",
                    "dimensions": {
                        "latency_slo": {
                            "metric_path": "p99_ms",
                            "comparison": "gt",
                            "warn_threshold": 100,
                        }
                    },
                }
            )
        )
        matrix = load_matrix_from_yaml(yaml_path)
        assert matrix.version == "v1-file"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="E_THRESHOLD_MATRIX_LOAD_FAIL"):
            load_matrix_from_yaml(tmp_path / "nope.yaml")

    def test_corrupt_yaml_raises(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text("a: [unclosed")
        with pytest.raises(ValueError, match="E_THRESHOLD_MATRIX_YAML_CORRUPT"):
            load_matrix_from_yaml(yaml_path)


class TestDefaultMatrix:
    def test_default_matrix_has_all_8_dims(self) -> None:
        matrix = default_matrix()
        assert len(matrix.dimensions) == 8
        for dim in DimensionKey:
            assert matrix.get(dim) is not None

    def test_default_thresholds_monotonic(self) -> None:
        # 触发 ThresholdMatrix 的 validator · 构造成功即可
        m = default_matrix()
        th = m.get(DimensionKey.LATENCY_SLO)
        assert th is not None
        assert th.warn_threshold is not None
        assert th.error_threshold is not None
        assert th.critical_threshold is not None
        assert th.warn_threshold < th.error_threshold < th.critical_threshold
