"""L2-01 · ProjectMeta 持久化 · 按 project 分片.

每 project 有一份 `<root>/projects/<pid>/events.meta.json`（HEADER_CHECKSUM 格式）
记录 last_sequence + last_hash · 供 append() 生成下一条 event.

复用 L2-05 write_atomic · 保证 meta 更新也原子（PM-14 硬约束）.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.l1_09.crash_safety import compose_header, write_atomic
from app.l1_09.crash_safety.integrity_checker import HEADER_SIZE
from app.l1_09.event_bus.schemas import ProjectMeta


def meta_path(project_dir: Path) -> Path:
    """project 的 meta 文件路径."""
    return project_dir / "events.meta.json"


def load_meta(project_dir: Path, *, project_id: str) -> ProjectMeta:
    """读 meta · 若不存在返 initial（last_seq=-1 · last_hash=GENESIS）."""
    path = meta_path(project_dir)
    if not path.exists():
        return ProjectMeta(project_id=project_id)

    content = path.read_bytes()
    # meta 用 HEADER_CHECKSUM · body 部分是 JSON
    if len(content) < HEADER_SIZE:
        # 旧格式或损坏 · 返 initial · 调用方会 bootstrap 补
        return ProjectMeta(project_id=project_id)
    body = content[HEADER_SIZE:]
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return ProjectMeta(project_id=project_id)
    return ProjectMeta(**data)


def save_meta(project_dir: Path, meta: ProjectMeta) -> None:
    """原子写 meta · 走 L2-05 write_atomic（HEADER_CHECKSUM 格式）."""
    project_dir.mkdir(parents=True, exist_ok=True)
    meta.updated_at = datetime.now(tz=UTC)
    body = json.dumps(
        {
            "project_id": meta.project_id,
            "last_sequence": meta.last_sequence,
            "last_hash": meta.last_hash,
            "updated_at": meta.updated_at.isoformat().replace("+00:00", "Z"),
        },
        sort_keys=True,
    ).encode("utf-8")
    header = compose_header(body)
    write_atomic(meta_path(project_dir), header + body)
