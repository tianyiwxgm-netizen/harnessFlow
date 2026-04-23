"""L2-02 启动硬编码扫描 · PM-09 红线.

规则:
  - 禁止 app/skill_dispatch 非 _mocks/非 tests 的 .py 源码中出现 skill 名字面量
  - 字面量定义: "superpowers:..." / "gstack:..." / "ecc:..." / "plugin:..." 形式的字符串
  - 违反 → startup assert fail (HardcodedSkillViolation) · 列出全部违规点（不是第一条）

默认 ignore 目录:
  _mocks / tests / __pycache__ / .venv / venv / .worktrees / node_modules

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-02-Skill 意图选择器.md §9.5 PRD 红线
  - docs/superpowers/plans/Dev-γ-impl.md §4 Task 02.2
"""
from __future__ import annotations

import pathlib
import re
from collections.abc import Iterable

_PATTERN = re.compile(r'["\'](?:superpowers|gstack|ecc|plugin):[a-zA-Z0-9_\-]+["\']')

_DEFAULT_IGNORE: frozenset[str] = frozenset(
    {"_mocks", "tests", "__pycache__", ".venv", "venv", ".worktrees", "node_modules"}
)


class HardcodedSkillViolation(RuntimeError):
    """E_INTENT_HARDCODED_SKILL · 启动期发现硬编码 skill 名 · 立即 crash."""


class HardEdgeScan:
    """启动硬编码扫描器 · 拒绝在非 mock/非 tests 的代码中出现 skill 字面量.

    典型用法（在 L2-02 进程启动时调）:
        HardEdgeScan(roots=[pathlib.Path("app/skill_dispatch")]).run()
    """

    def __init__(
        self,
        roots: Iterable[pathlib.Path],
        ignore: Iterable[str] | None = None,
    ) -> None:
        self.roots = [pathlib.Path(r) for r in roots]
        # 合并默认 ignore + 用户扩展
        self.ignore: set[str] = set(_DEFAULT_IGNORE)
        if ignore:
            self.ignore.update(ignore)

    def run(self) -> None:
        """扫全部 roots · 收集所有违规 · 统一 raise（非第一条 short-circuit）."""
        violations: list[str] = []
        for root in self.roots:
            for py in root.rglob("*.py"):
                if self._is_ignored(py):
                    continue
                try:
                    text = py.read_text(encoding="utf-8", errors="replace")
                except (OSError, UnicodeDecodeError):
                    continue
                for line_no, line in enumerate(text.splitlines(), start=1):
                    m = _PATTERN.search(line)
                    if m:
                        violations.append(f"{py}:{line_no} {m.group()}")
        if violations:
            raise HardcodedSkillViolation(
                "PM-09 violation · hardcoded skill literal detected:\n" + "\n".join(violations)
            )

    def _is_ignored(self, path: pathlib.Path) -> bool:
        return any(part in self.ignore for part in path.parts)
