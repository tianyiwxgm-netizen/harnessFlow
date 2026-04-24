"""main-1 WP03 · L2-03 pytest_renderer · TDD unit tests。

对齐 3-2 §2.040（pytest 渲染）+ §3.104（SYNTAX_INVALID）+ §3.105/106/107（桩/skip/docstring）
+ §6 algo 2 slug · algo 3 红灯断言 · algo 4 路径 · algo 5 语法自检。

WP03 only pytest · jest/go/cargo 不测（framework_unsupported 单独覆盖）。
"""

from __future__ import annotations

import ast

import pytest

from app.quality_loop.test_case_generator.pytest_renderer import (
    PytestRenderer,
    build_file_path,
    detect_stub_violation,
    slug_from_text,
    syntax_check,
)
from app.quality_loop.test_case_generator.schemas import (
    DOCSTRING_MISSING,
    FRAMEWORK_UNSUPPORTED,
    SKIP_MARK_DETECTED,
    STUB_CODE_DETECTED,
    SYNTAX_INVALID,
    CaseSlot,
    RenderOptions,
    TestCaseGeneratorError,
)


# ---------------------------------------------------------------------------
# slug · §6 algo 2 子集（pytest 只做英文 + 数字/下划线 · 中文走简化 ASCII 过滤）
# ---------------------------------------------------------------------------


class TestSlugFromText:
    def test_TC_L104_L203_030_english_basic(self) -> None:
        """TC-L104-L203-030 · 英文 AC 文本 → snake slug。"""
        assert slug_from_text("Order total computed under 100ms") == "order_total_computed_under_100ms"

    def test_TC_L104_L203_030b_strips_punctuation(self) -> None:
        """TC-L104-L203-030b · 标点/特殊字符被 `_` 替换并折叠。"""
        slug = slug_from_text("Price, really?! -- NEW value / @todo")
        assert slug == "price_really_new_value_todo"

    def test_TC_L104_L203_032_length_cap_60(self) -> None:
        """TC-L104-L203-032 · 长文本 cap 60 字符。"""
        slug = slug_from_text("very_long_description_" * 10)
        assert len(slug) <= 60

    def test_TC_L104_L203_031_non_ascii_falls_back_to_seq(self) -> None:
        """TC-L104-L203-031 · 纯中文 → ASCII 过滤后若空 · 回退 `ac_<seq>`（WP03 简化策略）。"""
        slug = slug_from_text("订单总价计算", fallback_seq=7)
        assert slug == "ac_7" or slug.startswith("ac_")


# ---------------------------------------------------------------------------
# build_file_path · §6 algo 4
# ---------------------------------------------------------------------------


class TestBuildFilePath:
    def test_TC_L104_L203_050_pm14_sharding(self) -> None:
        """TC-L104-L203-050 · PM-14 分片 · projects/<pid>/testing/generated/<wp>/<layer>/。"""
        path = build_file_path(
            project_id="pid-x", wp_id="WP-001", layer="unit",
            slug="order_total", ac_id="AC-007", test_framework="pytest",
        )
        assert path == "projects/pid-x/testing/generated/WP-001/unit/test_AC-007_order_total.py"
        assert ".." not in path and not path.startswith("/")

    def test_TC_L104_L203_050b_null_wp_uses_unassigned_bucket(self) -> None:
        """TC-L104-L203-050b · wp_id=None 落 `unassigned/` · 不是 WP03 scope 爆破。"""
        path = build_file_path(
            project_id="pid-x", wp_id=None, layer="unit",
            slug="x", ac_id="AC-001", test_framework="pytest",
        )
        assert "unassigned" in path


# ---------------------------------------------------------------------------
# PytestRenderer · §6 algo 3 红灯断言体 + §10.5 红线
# ---------------------------------------------------------------------------


class TestPytestRendererBasic:
    def _slot(self, **kw) -> CaseSlot:
        defaults = dict(slot_id="slot-AC-001-u1", ac_id="AC-001", layer="unit", seq=1, priority="P1")
        defaults.update(kw)
        return CaseSlot(**defaults)

    def test_TC_L104_L203_040_render_contains_raise_not_implemented(self) -> None:
        """TC-L104-L203-040 · D1 决策 · pytest 用 raise NotImplementedError。"""
        renderer = PytestRenderer()
        case = renderer.render(self._slot(), intent_line="order total", blueprint_id="bp-x",
                               blueprint_version=1, options=RenderOptions(project_id="pid-x"))
        assert "raise NotImplementedError" in case.code
        assert "AC-001" in case.code

    def test_TC_L104_L203_040b_render_has_docstring(self) -> None:
        """§10.5 禁 6 · 渲染后必须含 triple-quoted docstring。"""
        renderer = PytestRenderer()
        case = renderer.render(self._slot(), intent_line="x", blueprint_id="bp-x",
                               blueprint_version=1, options=RenderOptions(project_id="pid-x"))
        assert '"""' in case.code

    def test_TC_L104_L203_040c_render_no_pass_no_return_true_no_assert_true(self) -> None:
        """§10.5 禁 6/7 · 渲染体不含 pass / return True / assert True。"""
        renderer = PytestRenderer()
        case = renderer.render(self._slot(), intent_line="x", blueprint_id="bp-x",
                               blueprint_version=1, options=RenderOptions(project_id="pid-x"))
        # 去掉 docstring 再看
        body = case.code.split('"""', 2)[-1] if '"""' in case.code else case.code
        assert "\n    pass" not in body
        assert "return True" not in body
        assert "assert True" not in body

    def test_TC_L104_L203_040d_func_name_follows_convention(self) -> None:
        """命名 test_<ac_id_snake>_<layer>_<seq> · ac_id 中 `-` → `_`。"""
        renderer = PytestRenderer()
        case = renderer.render(
            self._slot(ac_id="AC-007", layer="unit", seq=2),
            intent_line="x", blueprint_id="bp-x",
            blueprint_version=1, options=RenderOptions(project_id="pid-x"),
        )
        assert "def test_ac_007_unit_2(" in case.code.lower()

    def test_TC_L104_L203_040e_file_path_uses_pm14_sharding(self) -> None:
        """渲染结果的 file_path 遵循 §6 algo 4。"""
        renderer = PytestRenderer()
        case = renderer.render(
            self._slot(), intent_line="order", blueprint_id="bp-x",
            blueprint_version=1, options=RenderOptions(project_id="pid-x"),
        )
        assert case.file_path.startswith("projects/pid-x/testing/generated/")
        assert case.file_path.endswith(".py")


class TestPytestRendererNegative:
    def test_TC_L104_L203_108_framework_unsupported_raises(self) -> None:
        """TC-L104-L203-108 · options.test_framework=jest 且不降级 → FRAMEWORK_UNSUPPORTED。"""
        with pytest.raises(TestCaseGeneratorError) as ei:
            RenderOptions(test_framework="jest", project_id="pid-x")
        assert ei.value.code == FRAMEWORK_UNSUPPORTED

    def test_TC_L104_L203_108b_framework_unsupported_with_fallback_ok(self) -> None:
        """TC-L104-L203-108b · fallback_on_unsupported_framework=True 则 WARNING 不抛。"""
        # 没 exception（构造成功）即通过
        opt = RenderOptions(test_framework="jest", fallback_on_unsupported_framework=True,
                            project_id="pid-x")
        assert opt.test_framework == "jest"


# ---------------------------------------------------------------------------
# syntax_check · §6 algo 5
# ---------------------------------------------------------------------------


class TestSyntaxCheck:
    def test_TC_L104_L203_060_valid_python_passes(self) -> None:
        """TC-L104-L203-060 · 合法 py 函数 → OK。"""
        code = 'def test_ac_001_unit_1():\n    """AC."""\n    raise NotImplementedError("x")\n'
        syntax_check(code, case_id="c-001")  # 不抛即通过

    def test_TC_L104_L203_104_broken_syntax_raises(self) -> None:
        """TC-L104-L203-104 · `def test_@@( pass` → SYNTAX_INVALID CRITICAL。"""
        bad = "def test_@@( pass"
        with pytest.raises(TestCaseGeneratorError) as ei:
            syntax_check(bad, case_id="c-bad")
        assert ei.value.code == SYNTAX_INVALID
        assert ei.value.severity == "CRITICAL"

    def test_TC_L104_L203_104b_returns_ast_on_success(self) -> None:
        """合法代码返回 ast.Module · 便于下游 stub detector 复用。"""
        tree = syntax_check("x = 1\n", case_id="c-ok")
        assert isinstance(tree, ast.Module)


# ---------------------------------------------------------------------------
# detect_stub_violation · §6 algo 8（WP03 核心红线）
# ---------------------------------------------------------------------------


class TestStubDetector:
    def test_TC_L104_L203_070_clean_red_passes(self) -> None:
        """TC-L104-L203-070 · 纯 raise NotImplementedError 骨架 · 无违禁。"""
        code = (
            'def test_ac_001():\n'
            '    """AC-001."""\n'
            '    raise NotImplementedError("x")\n'
        )
        detect_stub_violation(code, case_id="c-001")  # 不抛即通过

    def test_TC_L104_L203_105_pass_only_raises_stub(self) -> None:
        """TC-L104-L203-105 · `def test_x(): pass` → STUB_CODE_DETECTED。"""
        code = 'def test_ac_001():\n    pass\n'
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-001")
        assert ei.value.code == STUB_CODE_DETECTED
        assert ei.value.severity == "CRITICAL"

    def test_TC_L104_L203_105b_return_true_raises_stub(self) -> None:
        """TC-L104-L203-105b · `return True` 假绿 → STUB_CODE_DETECTED。"""
        code = 'def test_ac_002():\n    """x."""\n    return True\n'
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-002")
        assert ei.value.code == STUB_CODE_DETECTED

    def test_TC_L104_L203_105c_assert_true_raises_stub(self) -> None:
        """TC-L104-L203-105c · `assert True` 假绿 → STUB_CODE_DETECTED。"""
        code = 'def test_ac_003():\n    """x."""\n    assert True\n'
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-003")
        assert ei.value.code == STUB_CODE_DETECTED

    def test_TC_L104_L203_105d_return_constant_int_raises_stub(self) -> None:
        """TC-L104-L203-105d · `return 1` 亦属 STUB（任何真值常量）。"""
        code = 'def test_ac_004():\n    """x."""\n    return 1\n'
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-004")
        assert ei.value.code == STUB_CODE_DETECTED

    def test_TC_L104_L203_106_skip_mark_raises_skip(self) -> None:
        """TC-L104-L203-106 · `@pytest.mark.skip` → SKIP_MARK_DETECTED。"""
        code = (
            "import pytest\n"
            "@pytest.mark.skip\n"
            "def test_ac_010():\n"
            '    """x."""\n'
            '    raise NotImplementedError("x")\n'
        )
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-010")
        assert ei.value.code == SKIP_MARK_DETECTED

    def test_TC_L104_L203_106b_skip_call_raises_skip(self) -> None:
        """TC-L104-L203-106b · `pytest.skip("oops")` 调用 → SKIP_MARK_DETECTED。"""
        code = (
            "import pytest\n"
            "def test_ac_011():\n"
            '    """x."""\n'
            '    pytest.skip("oops")\n'
        )
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-011")
        assert ei.value.code == SKIP_MARK_DETECTED

    def test_TC_L104_L203_107_docstring_missing_raises(self) -> None:
        """TC-L104-L203-107 · 渲染后缺 docstring → DOCSTRING_MISSING · enforce=True。"""
        code = 'def test_ac_020():\n    raise NotImplementedError("x")\n'
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="c-020", enforce_docstring=True)
        assert ei.value.code == DOCSTRING_MISSING

    def test_TC_L104_L203_107b_docstring_present_no_raise(self) -> None:
        """有 docstring + 有抛异常 · 不触发 DOCSTRING_MISSING。"""
        code = (
            'def test_ac_020():\n'
            '    """AC-020: 正常 docstring。"""\n'
            '    raise NotImplementedError("x")\n'
        )
        detect_stub_violation(code, case_id="c-020", enforce_docstring=True)

    def test_TC_L104_L203_070b_multi_function_file_all_checked(self) -> None:
        """多函数文件 · 任一 test_* 违规即抛。"""
        code = (
            'def test_ac_a():\n    """A."""\n    raise NotImplementedError("x")\n\n'
            'def test_ac_b():\n    pass\n'
        )
        with pytest.raises(TestCaseGeneratorError) as ei:
            detect_stub_violation(code, case_id="multi")
        assert ei.value.code == STUB_CODE_DETECTED
