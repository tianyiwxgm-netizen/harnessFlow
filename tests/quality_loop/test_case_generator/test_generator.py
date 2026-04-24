"""main-1 WP03 · L2-03 generator 主入口 · TDD unit tests。

对齐 3-2 §2 正向 TC-L104-L203-004（factory.generate 主干）
    + §4 IC-06/09 契约占位（WP03 只做 IC-09 append_event 与 IC-16 push card 不做）
    + §6.10 algo 10 幂等
    + §8.1 状态机（INITIALIZING → GENERATING → READY / FAILED）。
"""

from __future__ import annotations

import pytest

from app.quality_loop.test_case_generator.generator import TestCaseGenerator
from app.quality_loop.test_case_generator.schemas import (
    AC_COVERAGE_NOT_100,
    CaseState,
    RenderOptions,
    SuiteState,
    TestCaseGeneratorError,
    TestSuite,
)


class TestGeneratorHappyPath:
    """§2 正向 · Factory.generate 主干（algo 1 → 3 → 4 → 5 → 6/7 → 8 → 9）。"""

    def test_TC_L104_L203_200_generate_returns_test_suite(self, tiny_blueprint) -> None:
        """TC-L104-L203-200 · generate 产 TestSuite 实例 · READY 状态。"""
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        assert isinstance(suite, TestSuite)
        assert suite.state == SuiteState.READY

    def test_TC_L104_L203_200b_suite_case_count_matches_slot_count(
        self,
        make_blueprint,
    ) -> None:
        """TC-L104-L203-200b · suite.cases 数 == slot 矩阵展开数。"""
        bp = make_blueprint(
            ac_rows=[
                ("AC-001", 2, 1, 0, "P1", "unit"),
                ("AC-002", 1, 1, 1, "P0", "unit"),
            ]
        )
        gen = TestCaseGenerator()
        suite = gen.generate(bp, options=RenderOptions(project_id="pid-wp03"))
        assert suite.total_count == 6

    def test_TC_L104_L203_200c_all_cases_are_red(self, tiny_blueprint) -> None:
        """TC-L104-L203-200c · §10.5 · 生成即红灯 · red_count == total_count。"""
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        assert suite.red_count == suite.total_count
        assert suite.green_count == 0
        for c in suite.cases:
            assert c.state == CaseState.RED

    def test_TC_L104_L203_200d_ac_coverage_is_100(self, tiny_blueprint) -> None:
        """TC-L104-L203-200d · §10.1 locked · ac_coverage_pct == 1.0。"""
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        assert suite.ac_coverage_pct == 1.0

    def test_TC_L104_L203_200e_suite_id_stable_for_same_blueprint(
        self,
        tiny_blueprint,
    ) -> None:
        """TC-L104-L203-200e · suite_id 以 hash_blueprint_signature 稳定（同输入两次等）。"""
        gen = TestCaseGenerator()
        s1 = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        s2 = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        assert s1.suite_id == s2.suite_id

    def test_TC_L104_L203_002_idempotent_returns_cached_suite(
        self,
        tiny_blueprint,
    ) -> None:
        """TC-L104-L203-002 · §6.10 algo 10 · 同 (blueprint_id, version) 幂等 · 只渲染一次。"""
        gen = TestCaseGenerator()
        opts = RenderOptions(project_id="pid-wp03")
        s1 = gen.generate(tiny_blueprint, options=opts)
        s2 = gen.generate(tiny_blueprint, options=opts)
        assert s1 is s2, "幂等 · 命中 cache 返回同一实例"
        assert gen.render_call_count == 1 * s1.total_count, \
            "render 只为首批 slot 被调用一次"

    def test_TC_L104_L203_200f_file_paths_under_project(self, tiny_blueprint) -> None:
        """TC-L104-L203-200f · PM-14 · 所有 case.file_path 前缀都落 projects/<pid>/。"""
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        for c in suite.cases:
            assert c.file_path.startswith("projects/pid-wp03/testing/generated/"), \
                "§7.5 PM-14 路径分片"

    def test_TC_L104_L203_200g_pytest_collect_can_parse_all_cases(
        self,
        tiny_blueprint,
    ) -> None:
        """TC-L104-L203-802（PRD §10.9 正向 2 微缩）· 每个 case.code 能被 ast.parse 通过。"""
        import ast
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        for c in suite.cases:
            ast.parse(c.code)  # 不抛即通过

    def test_TC_L104_L203_200h_each_case_func_unique(self, tiny_blueprint) -> None:
        """TC-L104-L203-200h · slot_id → case_id 稳定且唯一。"""
        gen = TestCaseGenerator()
        suite = gen.generate(tiny_blueprint, options=RenderOptions(project_id="pid-wp03"))
        ids = [c.case_id for c in suite.cases]
        assert len(ids) == len(set(ids))


class TestGeneratorFailFast:
    """§3 负向 · algo 1 ac coverage 未 100 必须 fail-fast · 不落 suite。"""

    def test_TC_L104_L203_103_uncovered_ac_rejects_build(self, make_blueprint) -> None:
        """TC-L104-L203-103 · AC 0 slot → AC_COVERAGE_NOT_100 CRITICAL。"""
        bp = make_blueprint(
            ac_rows=[
                ("AC-001", 1, 0, 0, "P1", "unit"),
                ("AC-999", 0, 0, 0, "P2", "unit"),
            ]
        )
        gen = TestCaseGenerator()
        with pytest.raises(TestCaseGeneratorError) as ei:
            gen.generate(bp, options=RenderOptions(project_id="pid-wp03"))
        assert ei.value.code == AC_COVERAGE_NOT_100
        # 失败不应留缓存条目
        assert gen._cache == {}
