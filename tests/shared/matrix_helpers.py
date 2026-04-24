"""tests/shared/matrix_helpers.py · 10×10 矩阵覆盖 helper(M3-WP01).

**定位**:
    给 M3-WP05 matrix-10x10-tests 用的覆盖率追踪 + 参数化工厂.
    10 L1 × 10 L1 · 除对角线外 45 pair · 每 pair × 4 用例 = 180 TC.

**M3 计划 §3**:
    M3-WP05 matrix-10x10-tests(45 对)· 每对 4 TC(正向 / 负向 / PM-14 / 降级).
    必测 25 对各 ≥ 4 TC · 弱依赖 20 对各 1 smoke · 覆盖率 100%.

**核心**:
    - `L1_IDS` / `pairs()` · 生成 45 对 · 含方向(上游→下游)
    - `matrix_case` 参数化元组 · pytest.mark.parametrize 用
    - `MatrixCoverage` · 收集 + 报告实际已写的 TC pair × case_type 覆盖矩阵
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from itertools import permutations


# 10 L1 · 对应 architecture.md §2 / prd.md §4
L1_IDS: tuple[str, ...] = (
    "L1-01",  # main-decision-loop(main-2)
    "L1-02",  # project-lifecycle / stage_gate(Dev-δ)
    "L1-03",  # wbs / topology(Dev-ε)
    "L1-04",  # quality-loop(main-1)
    "L1-05",  # skill-dispatch(Dev-γ)
    "L1-06",  # knowledge-base(Dev-β)
    "L1-07",  # supervisor(Dev-ζ)
    "L1-08",  # multimodal(Dev-η)
    "L1-09",  # resilience/audit(Dev-α)
    "L1-10",  # UI/BFF(Dev-θ)
)


class CaseType(StrEnum):
    """4 种用例分类 · matrix-10x10 每对至少覆盖这 4 种."""

    HAPPY = "happy"         # 正向 · 契约成功路径
    NEGATIVE = "negative"   # 负向 · 参数非法 / 边界
    PM14 = "pm14"           # 跨 pid 隔离 · PM-14 根字段违反
    DEGRADE = "degrade"     # 降级 · 下游超时 / 失败 → 上游优雅降级


def pairs() -> list[tuple[str, str]]:
    """10×10 的所有**有向** pair · 不含对角线(self-pair).

    返: 90 对 · [(upstream, downstream)...]
    注: 45 对"无向" pair 只保留字典序小的(若需无向用 `undirected_pairs`).
    """
    return [(a, b) for a, b in permutations(L1_IDS, 2)]


def undirected_pairs() -> list[tuple[str, str]]:
    """45 对无向 pair · 返字典序小的那一份(a, b) · a < b."""
    out: set[tuple[str, str]] = set()
    for a, b in permutations(L1_IDS, 2):
        if a < b:
            out.add((a, b))
    return sorted(out)


def matrix_params() -> list[tuple[str, str, CaseType]]:
    """给 pytest.mark.parametrize 用的 (upstream, downstream, case_type).

    覆盖: 90 对有向 × 4 case_type = 360 组(下游 WP 按需取 slice).

    示例:
        @pytest.mark.parametrize("upstream,downstream,case_type", matrix_params())
        def test_pair(upstream, downstream, case_type):
            ...
    """
    return [
        (a, b, ct)
        for (a, b) in pairs()
        for ct in CaseType
    ]


@dataclass
class MatrixCoverage:
    """追踪已覆盖的 (upstream, downstream, case_type) · 测尾报告缺口.

    用法:
        @pytest.fixture(scope="module")
        def matrix_cov() -> MatrixCoverage:
            return MatrixCoverage()

        def test_ic_09_happy(matrix_cov):
            matrix_cov.record("L1-04", "L1-09", CaseType.HAPPY)
            ...
            # 最后在 conftest module_finalizer 里打印 matrix_cov.missing_pairs()
    """

    covered: set[tuple[str, str, CaseType]] = field(default_factory=set)

    def record(self, upstream: str, downstream: str, case_type: CaseType | str) -> None:
        ct = CaseType(case_type) if not isinstance(case_type, CaseType) else case_type
        self.covered.add((upstream, downstream, ct))

    def is_covered(self, upstream: str, downstream: str, case_type: CaseType) -> bool:
        return (upstream, downstream, case_type) in self.covered

    def coverage_ratio(self) -> float:
        total = len(pairs()) * len(CaseType)
        return len(self.covered) / total if total else 0.0

    def missing_pairs(self) -> list[tuple[str, str, CaseType]]:
        """返回所有**还未覆盖**的(upstream, downstream, case_type)."""
        all_pairs = {(a, b, ct) for (a, b) in pairs() for ct in CaseType}
        return sorted(all_pairs - self.covered)

    def summary(self) -> str:
        pct = self.coverage_ratio() * 100.0
        return (
            f"Matrix coverage: {len(self.covered)}/"
            f"{len(pairs()) * len(CaseType)} ({pct:.1f}%) · "
            f"missing={len(self.missing_pairs())}"
        )
