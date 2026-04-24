"""L2-03 pytest_renderer · 单 slot → pytest 骨架源码。

WP03 scope 裁：
  - §6 algo 2 · slug_from_text（英文 / ASCII · 中文回退 ac_<seq>）
  - §6 algo 3 · pytest 红灯断言体（raise NotImplementedError · 恒红灯）
  - §6 algo 4 · build_file_path（PM-14 分片）
  - §6 algo 5 · syntax_check（ast.parse）
  - §6 algo 8 · detect_stub_violation（pass / return True / assert True / skip mark / skip call）

不做：
  - §6 algo 9 atomic_write_file（留 generator 主入口·用 tempfile + os.rename 一行）
  - jest / go-test / cargo-test（framework_unsupported 已在 RenderOptions 兜）
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import jinja2

from .schemas import (
    DOCSTRING_MISSING,
    SKIP_MARK_DETECTED,
    STUB_CODE_DETECTED,
    SYNTAX_INVALID,
    CaseSlot,
    CaseState,
    RenderOptions,
    TestCaseGeneratorError,
    TestCaseSkeleton,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# §6 algo 2 · slug
# ---------------------------------------------------------------------------


_MAX_SLUG = 60


def slug_from_text(text: str, fallback_seq: int | str = 0) -> str:
    """把自由文本 → 文件系统安全 snake_slug。

    WP03 scope：
      - 英文 / 数字 / 下划线保留 · 其他转 `_`
      - 连续 `_` 折叠 · 首尾 `_` 去除
      - cap 60 字符
      - 若清理后为空（例如纯中文）· 回退 `ac_<fallback_seq>`

    **不**做：pypinyin / slugify（留给后续）。
    """
    if not isinstance(text, str):
        text = str(text or "")
    # 小写 · 非 [a-z0-9_] 全替 _
    raw = re.sub(r"[^a-z0-9_]", "_", text.lower())
    raw = re.sub(r"_+", "_", raw).strip("_")
    if len(raw) > _MAX_SLUG:
        raw = raw[:_MAX_SLUG].rstrip("_")
    if not raw:
        return f"ac_{fallback_seq}"
    return raw


# ---------------------------------------------------------------------------
# §6 algo 4 · PM-14 分片
# ---------------------------------------------------------------------------


def build_file_path(
    *,
    project_id: str,
    wp_id: str | None,
    layer: str,
    slug: str,
    ac_id: str,
    test_framework: str = "pytest",
) -> str:
    """按 PM-14 规则组装 pytest 文件路径。

    模板：`projects/<pid>/testing/generated/<wp_id or unassigned>/<layer>/test_<ac_id>_<slug>.py`
    """
    if layer not in ("unit", "integration", "e2e"):
        raise ValueError(f"illegal layer: {layer!r}")
    bucket = wp_id if wp_id else "unassigned"
    if ".." in project_id or ".." in bucket or ".." in slug or ".." in ac_id:
        raise TestCaseGeneratorError(
            code=SYNTAX_INVALID,
            message=f"path traversal detected in segments",
            severity="ERROR",
        )
    ext = "py" if test_framework == "pytest" else "txt"
    filename = f"test_{ac_id}_{slug}.{ext}"
    return f"projects/{project_id}/testing/generated/{bucket}/{layer}/{filename}"


# ---------------------------------------------------------------------------
# §6 algo 5 · syntax_check
# ---------------------------------------------------------------------------


def syntax_check(code: str, *, case_id: str) -> ast.Module:
    """ast.parse 做单 case 语法自检 · 失败抛 SYNTAX_INVALID CRITICAL。"""
    try:
        return ast.parse(code)
    except SyntaxError as e:
        raise TestCaseGeneratorError(
            code=SYNTAX_INVALID,
            message=f"syntax invalid for case {case_id}: {e.msg} at line {e.lineno}",
            severity="CRITICAL",
            case_id=case_id,
            lineno=e.lineno,
        ) from e


# ---------------------------------------------------------------------------
# §6 algo 8 · stub / skip / docstring 检测
# ---------------------------------------------------------------------------


_TRUTHY = {True, 1, "ok", "pass", "yes"}


def _is_truthy_constant(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            return v is True
        if isinstance(v, int):
            return v != 0
        if isinstance(v, str):
            return v in _TRUTHY
    return False


def _has_skip_decorator(fn: ast.FunctionDef) -> bool:
    for dec in fn.decorator_list:
        # @pytest.mark.skip / @pytest.mark.skipif / @skip / ...
        if isinstance(dec, ast.Attribute) and dec.attr.startswith("skip"):
            return True
        if isinstance(dec, ast.Name) and dec.id.startswith("skip"):
            return True
        # @pytest.mark.skip(...) 调用形态
        if isinstance(dec, ast.Call):
            f = dec.func
            if isinstance(f, ast.Attribute) and f.attr.startswith("skip"):
                return True
            if isinstance(f, ast.Name) and f.id.startswith("skip"):
                return True
    return False


def _has_skip_call(fn: ast.FunctionDef) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "skip":
                return True
            if isinstance(f, ast.Name) and f.id == "skip":
                return True
    return False


def _function_stub_violations(fn: ast.FunctionDef) -> list[str]:
    violations: list[str] = []
    body = fn.body

    # 剥掉 docstring 再判
    effective_body = body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        effective_body = body[1:]

    # Pattern 1: 只有 pass（含 docstring 后的 pass）
    if len(effective_body) == 1 and isinstance(effective_body[0], ast.Pass):
        violations.append(f"{fn.name}: `pass` 作为唯一函数体（红线违禁）")

    # Pattern 2: return 真值常量
    for stmt in effective_body:
        if isinstance(stmt, ast.Return) and stmt.value is not None and _is_truthy_constant(stmt.value):
            violations.append(f"{fn.name}: `return <truthy>` 假绿")

    # Pattern 3: assert 真值常量
    for stmt in effective_body:
        if isinstance(stmt, ast.Assert) and _is_truthy_constant(stmt.test):
            violations.append(f"{fn.name}: `assert <truthy>` 恒真")

    return violations


def detect_stub_violation(
    code: str,
    *,
    case_id: str,
    enforce_docstring: bool = True,
) -> None:
    """综合扫描：stub / skip / docstring。

    任何违规立刻 raise（fail-fast · 上游 generator 用 code 路由）。
    """
    tree = syntax_check(code, case_id=case_id)

    test_functions = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]

    for fn in test_functions:
        # skip mark 优先级最高（比 stub 更先抛）
        if _has_skip_decorator(fn) or _has_skip_call(fn):
            raise TestCaseGeneratorError(
                code=SKIP_MARK_DETECTED,
                message=f"`{fn.name}` 被 skip 标记 / 调用（红线违禁）",
                severity="CRITICAL",
                case_id=case_id,
            )

        stub_vios = _function_stub_violations(fn)
        if stub_vios:
            raise TestCaseGeneratorError(
                code=STUB_CODE_DETECTED,
                message=f"stub violations in {case_id}: {stub_vios}",
                severity="CRITICAL",
                case_id=case_id,
                violations=stub_vios,
            )

        if enforce_docstring:
            if not (
                fn.body
                and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)
                and isinstance(fn.body[0].value.value, str)
            ):
                raise TestCaseGeneratorError(
                    code=DOCSTRING_MISSING,
                    message=f"`{fn.name}` 缺 docstring（§10.5 硬性）",
                    severity="ERROR",
                    case_id=case_id,
                )


# ---------------------------------------------------------------------------
# PytestRenderer · jinja2 主入口
# ---------------------------------------------------------------------------


class PytestRenderer:
    """单 slot → TestCaseSkeleton · 渲染 + 自检一体。"""

    _env: jinja2.Environment

    def __init__(self, templates_dir: Path | None = None) -> None:
        loader_dir = templates_dir or _TEMPLATES_DIR
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(loader_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(
        self,
        slot: CaseSlot,
        *,
        intent_line: str,
        blueprint_id: str,
        blueprint_version: int,
        options: RenderOptions,
        wp_id: str | None = None,
    ) -> TestCaseSkeleton:
        ac_id = slot.ac_id
        ac_id_for_name = ac_id.replace("-", "_").replace(" ", "_").lower()
        slug = slug_from_text(intent_line, fallback_seq=slot.seq)
        func_name = f"test_{ac_id_for_name}_{slot.layer}_{slot.seq}"

        template = self._env.get_template("pytest_case.py.j2")
        code = template.render(
            include_header_comment=options.include_header_comment,
            blueprint_id=blueprint_id,
            blueprint_version=blueprint_version,
            ac_id=ac_id,
            layer=slot.layer,
            seq=slot.seq,
            priority=slot.priority,
            func_name=func_name,
            intent_line=intent_line.replace('"', "'").strip() or f"{ac_id} placeholder intent",
            slug=slug,
        )

        # 自检（生成即红灯 · 任何违规直接 raise）
        syntax_check(code, case_id=slot.slot_id)
        if options.enforce_docstring or options.enforce_assert:
            detect_stub_violation(
                code,
                case_id=slot.slot_id,
                enforce_docstring=options.enforce_docstring,
            )

        file_path = build_file_path(
            project_id=options.project_id,
            wp_id=wp_id,
            layer=slot.layer,
            slug=slug,
            ac_id=ac_id,
            test_framework="pytest",
        )

        return TestCaseSkeleton(
            case_id=f"case-{slot.slot_id}",
            slot_id=slot.slot_id,
            ac_id=ac_id,
            wp_id=wp_id,
            layer=slot.layer,
            code=code,
            docstring=intent_line,
            file_path=file_path,
            state=CaseState.RED,
            test_framework="pytest",
        )


__all__ = [
    "PytestRenderer",
    "build_file_path",
    "detect_stub_violation",
    "slug_from_text",
    "syntax_check",
]
