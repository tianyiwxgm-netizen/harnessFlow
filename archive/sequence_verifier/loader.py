"""archive.sequence_verifier.loader — 列出 + 读 must-load memory 文件.

主 skill § 2.1 step 3 在 bootstrap 阶段必须装载所有 feedback_workflow_* +
feedback_prp_* 类 memory，以避免 v1.4 以前的"PRP 流程偏好被忽略"缺陷
（defects-report P1 #2）。

解析规则：扫 MEMORY.md（用户 auto-memory 索引），匹配 markdown 链接
`[标题](文件名.md)`，挑出文件名以 `feedback_workflow_` 或 `feedback_prp_` 开头的项。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

# 必须装载的 memory 文件名前缀清单
MUST_LOAD_PREFIXES = ("feedback_workflow_", "feedback_prp_")

# MEMORY.md 中标准 markdown 链接 pattern
# 形如：- [aigcv2 长周期推进用方案 C 混搭工作流](feedback_workflow_scheme_c.md) — ...
MEMORY_FILE_PATTERN = re.compile(
    r"\[[^\]]+\]\((feedback_(?:workflow|prp)_[A-Za-z0-9_\-]+\.md)\)"
)


def list_must_load_memories(memory_dir: Path) -> List[Path]:
    """解析 MEMORY.md，返回必须 Read 的 memory 文件绝对路径列表.

    Args:
        memory_dir: 用户 memory 目录，含 MEMORY.md 与各 *.md 子文件。

    Returns:
        list of Path（已去重，按文件名字母序）。MEMORY.md 不存在或无匹配 → 空 list。

    Raises:
        FileNotFoundError: memory_dir 不存在。
    """
    memory_dir = Path(memory_dir)
    if not memory_dir.is_dir():
        raise FileNotFoundError(f"memory_dir does not exist: {memory_dir}")

    index = memory_dir / "MEMORY.md"
    if not index.is_file():
        return []

    content = index.read_text(encoding="utf-8")
    filenames = set(MEMORY_FILE_PATTERN.findall(content))
    paths = []
    for name in sorted(filenames):
        candidate = memory_dir / name
        if candidate.is_file():
            paths.append(candidate)
    return paths


def read_must_load_memories(memory_dir: Path) -> Dict[str, str]:
    """读 must-load memory 文件内容。

    Args:
        memory_dir: 用户 memory 目录。

    Returns:
        dict {basename: content}，不含路径前缀，便于主 skill 按文件名引用。
        缺失/解析失败的文件不在返回中（loader 不 raise，让主 skill 决定如何处理缺失）。
    """
    out: Dict[str, str] = {}
    try:
        paths = list_must_load_memories(memory_dir)
    except FileNotFoundError:
        return out
    for p in paths:
        try:
            out[p.name] = p.read_text(encoding="utf-8")
        except OSError:
            continue
    return out


def routing_decision_basis_record(
    memory_dir: Path,
    loaded_files: Optional[List[str]] = None,
) -> Dict:
    """生成可写入 task-board.routing_decision_basis 的证据 dict.

    Args:
        memory_dir: 用户 memory 目录。
        loaded_files: 主 skill 实际 Read 过的文件 basename 列表（可信任 trace）。
                      None 时回退用 list_must_load_memories() 的全集（best-effort）。

    Returns:
        dict {
            "must_load_memories": [basename, ...],   # 应该装载的清单
            "loaded_memories": [basename, ...],      # 实际装载的清单
            "missing": [basename, ...],              # 应载未载
            "complete": bool,                        # 是否全部装载
        }
    """
    try:
        must = [p.name for p in list_must_load_memories(memory_dir)]
    except FileNotFoundError:
        must = []
    actual = list(loaded_files) if loaded_files is not None else list(must)
    must_set = set(must)
    actual_set = set(actual)
    missing = sorted(must_set - actual_set)
    return {
        "must_load_memories": must,
        "loaded_memories": sorted(actual_set),
        "missing": missing,
        "complete": len(missing) == 0 and len(must) > 0,
    }
