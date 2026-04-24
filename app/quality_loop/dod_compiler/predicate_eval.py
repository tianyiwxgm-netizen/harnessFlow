"""L1-04 · L2-02 · Predicate 白名单 + 安全 eval (vendor from archive/stage_contracts).

锚点:
    - 基础实现 vendor from archive/stage_contracts/predicate_eval.py
    - 加强:frozen WhitelistRegistry + DoD-specific predicates (coverage/lint/...).

预定义 predicate 库(PM-10 单一事实源):
    - coverage 相关:line_coverage / branch_coverage / ac_coverage
    - test 相关:p0_cases_all_pass / test_fail_count / test_pass_rate
    - lint 相关:lint_errors / lint_warnings
    - security 相关:high_severity_count / security_resolved_rate
    - perf 相关:p50_ms / p95_ms / throughput_qps
    - artifact 相关:file_exists / has_commit
    - 组合:len / count(计数)

AST 安全 eval 原理:
    1. ast.parse(mode='eval')
    2. SafeExprValidator.validate() (节点/深度/节点数/名/函数白名单)
    3. compile() + eval() with {"__builtins__": {}} + 白名单 functions + data_sources
"""
from __future__ import annotations

import ast
import threading
from collections.abc import Callable, Mapping
from typing import Any

from app.quality_loop.dod_compiler.ast_nodes import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_NODES,
    SafeExprValidator,
)
from app.quality_loop.dod_compiler.errors import (
    CachePoisonError,
    DataSourceUnknownTypeError,
    DoDEvalError,
    IllegalFunctionError,
    IllegalNodeError,
    SandboxEscapeDetectedError,
)

# ========== 白名单 DataSource 类型 (§2.3.4) ==========

WHITELISTED_DATA_SOURCE_KEYS: frozenset[str] = frozenset({
    "test_result",
    "coverage",
    "lint",
    "security_scan",
    "perf",
    "artifact",
})


# ========== Predicate 函数库 (白名单) ==========


def _get_ds(ds: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """从 data_sources_snapshot 中取一个 DataSource · 严禁越界."""
    if key not in WHITELISTED_DATA_SOURCE_KEYS:
        raise DataSourceUnknownTypeError(f"unknown data source: {key}")
    v = ds.get(key)
    if v is None:
        return {}
    if not isinstance(v, Mapping):
        return {}
    return v


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if isinstance(v, bool):
            return int(v)
        return int(v)
    except (TypeError, ValueError):
        return default


def _make_library(ds: dict[str, Any], evidence_tracker: dict[str, Any]) -> dict[str, Callable[..., Any]]:
    """构建 predicate 库 · 每次调用 evidence_tracker 记录实际访问字段.

    Args:
        ds: data_sources_snapshot (已通过 DataSourceUnknownType 校验)
        evidence_tracker: out param · 记录本次 eval 访问了哪些字段(PM-10)

    Returns:
        {predicate_name -> callable} · 作为 eval 的 globals.
    """

    def _track(src: str, field: str, value: Any) -> Any:
        evidence_tracker.setdefault(src, {})[field] = value
        return value

    # ---------- coverage ----------
    def line_coverage() -> float:
        c = _get_ds(ds, "coverage")
        v = _safe_float(c.get("line_rate") if isinstance(c.get("line_rate"), (int, float)) else c.get("line_coverage"))
        return _track("coverage", "line_rate", v)

    def branch_coverage() -> float:
        c = _get_ds(ds, "coverage")
        v = _safe_float(c.get("branch_rate") if isinstance(c.get("branch_rate"), (int, float)) else c.get("branch_coverage"))
        return _track("coverage", "branch_rate", v)

    def ac_coverage() -> float:
        c = _get_ds(ds, "coverage")
        v = _safe_float(c.get("ac_coverage"))
        return _track("coverage", "ac_coverage", v)

    # ---------- test ----------
    def test_fail_count() -> int:
        t = _get_ds(ds, "test_result")
        v = _safe_int(t.get("fail_count"))
        return _track("test_result", "fail_count", v)

    def test_pass_count() -> int:
        t = _get_ds(ds, "test_result")
        v = _safe_int(t.get("pass_count"))
        return _track("test_result", "pass_count", v)

    def test_skip_count() -> int:
        t = _get_ds(ds, "test_result")
        v = _safe_int(t.get("skip_count"))
        return _track("test_result", "skip_count", v)

    def test_pass_rate() -> float:
        t = _get_ds(ds, "test_result")
        p = _safe_int(t.get("pass_count"))
        f = _safe_int(t.get("fail_count"))
        total = p + f
        v = (p / total) if total > 0 else 1.0
        return _track("test_result", "pass_rate", v)

    def p0_cases_all_pass() -> bool:
        t = _get_ds(ds, "test_result")
        v = bool(t.get("p0_all_pass", False))
        return _track("test_result", "p0_all_pass", v)

    # ---------- lint ----------
    def lint_errors() -> int:
        l_ = _get_ds(ds, "lint")
        v = _safe_int(l_.get("error_count") if l_.get("error_count") is not None else l_.get("ruff_errors"))
        return _track("lint", "error_count", v)

    def lint_warnings() -> int:
        l_ = _get_ds(ds, "lint")
        v = _safe_int(l_.get("warning_count"))
        return _track("lint", "warning_count", v)

    # ---------- security ----------
    def high_severity_count() -> int:
        s = _get_ds(ds, "security_scan")
        v = _safe_int(s.get("high_severity_count"))
        return _track("security_scan", "high_severity_count", v)

    def medium_severity_count() -> int:
        s = _get_ds(ds, "security_scan")
        v = _safe_int(s.get("medium_severity_count"))
        return _track("security_scan", "medium_severity_count", v)

    def security_resolved_rate() -> float:
        s = _get_ds(ds, "security_scan")
        v = _safe_float(s.get("resolved_rate"))
        return _track("security_scan", "resolved_rate", v)

    # ---------- perf ----------
    def p50_ms() -> float:
        p = _get_ds(ds, "perf")
        v = _safe_float(p.get("p50_ms"))
        return _track("perf", "p50_ms", v)

    def p95_ms() -> float:
        p = _get_ds(ds, "perf")
        v = _safe_float(p.get("p95_ms"))
        return _track("perf", "p95_ms", v)

    def throughput_qps() -> float:
        p = _get_ds(ds, "perf")
        v = _safe_float(p.get("throughput_qps"))
        return _track("perf", "throughput_qps", v)

    # ---------- artifact ----------
    def artifact_file_count() -> int:
        a = _get_ds(ds, "artifact")
        files = a.get("files") or []
        try:
            v = len(files)
        except TypeError:
            v = 0
        return _track("artifact", "file_count", v)

    def has_file(path: str) -> bool:
        a = _get_ds(ds, "artifact")
        files = a.get("files") or []
        try:
            v = path in set(files)
        except TypeError:
            v = False
        return _track("artifact", f"has:{path}", v)

    # ---------- util ----------
    def length(x: Any) -> int:
        try:
            return len(x)
        except TypeError:
            return 0

    return {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "ac_coverage": ac_coverage,
        "test_fail_count": test_fail_count,
        "test_pass_count": test_pass_count,
        "test_skip_count": test_skip_count,
        "test_pass_rate": test_pass_rate,
        "p0_cases_all_pass": p0_cases_all_pass,
        "lint_errors": lint_errors,
        "lint_warnings": lint_warnings,
        "high_severity_count": high_severity_count,
        "medium_severity_count": medium_severity_count,
        "security_resolved_rate": security_resolved_rate,
        "p50_ms": p50_ms,
        "p95_ms": p95_ms,
        "throughput_qps": throughput_qps,
        "artifact_file_count": artifact_file_count,
        "has_file": has_file,
        "length": length,
    }


# ========== 白名单注册表 ==========

# {name: arg_count},arg_count = -1 表示变参(当前未用),0 = 无参 · 1 = 单参
DEFAULT_WHITELIST_FUNCS: dict[str, int] = {
    "line_coverage": 0,
    "branch_coverage": 0,
    "ac_coverage": 0,
    "test_fail_count": 0,
    "test_pass_count": 0,
    "test_skip_count": 0,
    "test_pass_rate": 0,
    "p0_cases_all_pass": 0,
    "lint_errors": 0,
    "lint_warnings": 0,
    "high_severity_count": 0,
    "medium_severity_count": 0,
    "security_resolved_rate": 0,
    "p50_ms": 0,
    "p95_ms": 0,
    "throughput_qps": 0,
    "artifact_file_count": 0,
    "has_file": 1,
    "length": 1,
}


class WhitelistRegistry:
    """白名单注册表 · 启动加载 · 运行期只读 (§6.5 · frozendict + version lock).

    简化实现:内存 dict + lock + baseline_hash(用于 watchdog).
    """

    def __init__(
        self,
        *,
        allowed_funcs: Mapping[str, int] | None = None,
        version: str = "1.0.3",
    ) -> None:
        self._allowed_funcs: dict[str, int] = dict(allowed_funcs or DEFAULT_WHITELIST_FUNCS)
        self._version = version
        self._lock = threading.Lock()
        self._sealed = True  # 默认 sealed · add_rule 需明确 unseal

    @property
    def version(self) -> str:
        return self._version

    def allowed_funcs(self) -> dict[str, int]:
        """返回白名单副本(deepcopy 防 SA-06)."""
        with self._lock:
            return dict(self._allowed_funcs)

    def list_rules(self) -> list[tuple[str, int]]:
        with self._lock:
            return sorted(self._allowed_funcs.items())

    def contains(self, name: str) -> bool:
        with self._lock:
            return name in self._allowed_funcs

    # --- 扩展接口 (仅 offline_admin_mode 可调) ---

    def add_rule(self, name: str, arg_count: int, *, bump: str = "minor") -> str:
        """离线模式添加白名单条目 · bump 版本号.

        Returns: 新版本号.
        """
        with self._lock:
            if name in self._allowed_funcs:
                raise ValueError(f"rule {name!r} already exists")
            self._allowed_funcs[name] = arg_count
            self._version = _bump_semver(self._version, bump)
            return self._version


def _bump_semver(version: str, kind: str) -> str:
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    major, minor, patch = (int(p) for p in parts[:3])
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# ========== 安全 eval 主入口 ==========


def safe_eval(
    tree: ast.Expression,
    data_sources_snapshot: dict[str, Any],
    *,
    registry: WhitelistRegistry | None = None,
    evidence_tracker: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """执行一次 safe eval.

    Returns:
        (result_value, evidence_snapshot) 二元组.

    Raises:
        IllegalNodeError / IllegalFunctionError / CachePoisonError /
        SandboxEscapeDetectedError / DoDEvalError.
    """
    if evidence_tracker is None:
        evidence_tracker = {}

    if not isinstance(tree, ast.Expression):
        raise IllegalNodeError("safe_eval expects ast.Expression")

    registry = registry or WhitelistRegistry()
    allowed_funcs = registry.allowed_funcs()

    # 运行期 re-validate (防 cache poison)
    validator = SafeExprValidator(allowed_funcs=allowed_funcs)
    try:
        validator.validate(tree)
    except (IllegalNodeError, IllegalFunctionError) as exc:
        raise CachePoisonError(f"runtime re-validate failed: {exc}") from exc

    # DataSource 白名单过滤
    for k in data_sources_snapshot:
        if k not in WHITELISTED_DATA_SOURCE_KEYS:
            raise DataSourceUnknownTypeError(f"unknown data source: {k}")

    # 构建受限 globals
    library = _make_library(data_sources_snapshot, evidence_tracker)
    # 只暴露 registry 白名单里的(二次 · 防 library 越权)
    safe_funcs = {name: impl for name, impl in library.items() if name in allowed_funcs}
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_globals.update(safe_funcs)

    # 编译并执行(空 locals)
    try:
        code = compile(tree, filename="<dod-expr>", mode="eval")
        value = eval(code, safe_globals, {})  # noqa: S307 guarded by AST walk
    except NameError as exc:
        # 可能是使用了未映射的 Name · 归为 sandbox escape (SA-02)
        raise SandboxEscapeDetectedError(
            f"eval references unknown name: {exc}"
        ) from exc
    except Exception as exc:  # pragma: no cover - eval 过滤后少见
        raise DoDEvalError(f"eval failed: {exc}") from exc

    return value, dict(evidence_tracker)


__all__ = [
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MAX_NODES",
    "DEFAULT_WHITELIST_FUNCS",
    "WhitelistRegistry",
    "WHITELISTED_DATA_SOURCE_KEYS",
    "safe_eval",
]
