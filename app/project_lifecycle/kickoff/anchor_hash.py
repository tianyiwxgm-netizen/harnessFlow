"""L2-02 compute_anchor_hash · 对齐 tech §6.4 + §7.5。

组装 Goal + PrdScope 两份章程的正文（排除 frontmatter 可变字段）· sha256 hex。
PM-14 锁定后全生命周期不可改 · 后续任意 activate/monitor 必复核 hash 一致。
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def _strip_frontmatter(text: str) -> str:
    """剥离开头 `---\\n<yaml>\\n---\\n` frontmatter · 返正文。"""
    if not text.startswith("---"):
        return text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    idx = rest.find("\n---")
    if idx < 0:
        return text
    body = rest[idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    return body


def _read_chart_body(path: Path) -> str:
    """读章程文件 · 剥 frontmatter · 规范换行（CRLF → LF · strip 末尾空白）。"""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    return body.replace("\r\n", "\n").strip()


def compute_anchor_hash(project_id: str, *, root_dir: str) -> str:
    """组合 `projects/<pid>/chart/{HarnessFlowGoal,HarnessFlowPrdScope}.md` 正文 sha256。

    规范：
      1. 剥 frontmatter（updated_at / rendered_at 等可变字段不影响 hash）
      2. 正文 strip + CRLF → LF
      3. 固定顺序 `goal_body + "\\n---\\n" + scope_body`
      4. sha256 hex（64 char · 无 "sha256:" 前缀）
    """
    chart_root = Path(root_dir) / "projects" / project_id / "chart"
    goal_body = _read_chart_body(chart_root / "HarnessFlowGoal.md")
    scope_body = _read_chart_body(chart_root / "HarnessFlowPrdScope.md")
    combined = (goal_body + "\n---\n" + scope_body).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()
