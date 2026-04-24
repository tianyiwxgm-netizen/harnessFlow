"""Smoke: matrix_helpers · 10 L1 × 10 L1 pair 生成 + coverage 追踪."""
from __future__ import annotations

from tests.shared.matrix_helpers import (
    CaseType,
    L1_IDS,
    MatrixCoverage,
    matrix_params,
    pairs,
    undirected_pairs,
)


def test_l1_ids_count() -> None:
    assert len(L1_IDS) == 10
    assert L1_IDS[0] == "L1-01"
    assert L1_IDS[-1] == "L1-10"


def test_pairs_directed_90() -> None:
    p = pairs()
    assert len(p) == 90  # 10 * 9
    # 不含对角线 self-pair
    assert all(a != b for (a, b) in p)


def test_undirected_pairs_45() -> None:
    up = undirected_pairs()
    assert len(up) == 45
    # 字典序小的那一半
    for (a, b) in up:
        assert a < b


def test_matrix_params_count() -> None:
    mp = matrix_params()
    assert len(mp) == 90 * 4  # 360
    assert all(isinstance(ct, CaseType) for (_, _, ct) in mp)


def test_matrix_coverage_record_and_missing() -> None:
    cov = MatrixCoverage()
    assert cov.coverage_ratio() == 0.0
    assert len(cov.missing_pairs()) == 360

    cov.record("L1-04", "L1-09", CaseType.HAPPY)
    cov.record("L1-04", "L1-09", "negative")  # str 也可
    assert cov.is_covered("L1-04", "L1-09", CaseType.HAPPY)
    assert cov.is_covered("L1-04", "L1-09", CaseType.NEGATIVE)
    assert not cov.is_covered("L1-04", "L1-09", CaseType.PM14)
    assert cov.coverage_ratio() > 0
    assert len(cov.missing_pairs()) == 358


def test_matrix_coverage_summary() -> None:
    cov = MatrixCoverage()
    cov.record("L1-01", "L1-02", CaseType.HAPPY)
    s = cov.summary()
    assert "1/360" in s
    assert "missing=359" in s
