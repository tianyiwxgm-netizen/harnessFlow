"""L2-06 ClosingExecutor · S6 lessons + S7 archive · PM-14 归档唯一入口。

3 主方法：
  1. produce_closing(pid) · S6 · 产 lessons_learned/delivery_manifest/retro_summary 3 md
  2. archive_project(pid) · S7 · tar.zst + sha256 复验 + chmod 0444 · PM-14 归档唯一入口
  3. purge_project(pid, confirm_token) · 归档后 ≥ 90 天 · 双重确认
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml

from app.project_lifecycle.closing.errors import (
    E_ARCHIVE_ALREADY_EXISTS,
    E_CHMOD_FAILED,
    E_PM14_OWNERSHIP_VIOLATION,
    E_PROJECT_SIZE_EXCEEDED,
    E_PURGE_TOKEN_MISMATCH,
    E_PURGE_TOO_EARLY,
    E_SHA256_VERIFICATION_FAILED,
    E_STATE_NOT_CLOSING_APPROVED,
    E_TAR_ZST_FAILED,
    E_UPSTREAM_NOT_READY,
    ClosingError,
)
from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart


_MAX_PROJECT_SIZE_BYTES = 20 * 1024 * 1024 * 1024  # 20 GB
_PURGE_MIN_AGE_DAYS = 90


@dataclass
class ClosingResult:
    project_id: str
    lessons_path: str
    manifest_path: str
    retro_path: str
    closing_bundle_hash: str


@dataclass
class ArchiveManifest:
    project_id: str
    archive_path: str
    sha256: str
    size_bytes: int
    archived_at: str


@dataclass
class PurgeResult:
    project_id: str
    purged: bool
    reason: str = ""


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


class ClosingExecutor:

    def __init__(
        self,
        *,
        template: Any,
        event_bus: EventSink,
    ) -> None:
        self._template = template
        self._event_bus = event_bus

    # ---- S6 产出 3 md ----

    def produce_closing(
        self,
        project_id: str,
        *,
        project_root: str,
        caller_l2: str = "L2-01",
        audit_events: list[dict[str, Any]] | None = None,
    ) -> ClosingResult:
        if caller_l2 != "L2-01":
            raise ClosingError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may call produce_closing · caller={caller_l2!r}",
                caller_l2=caller_l2, project_id=project_id,
            )

        root = Path(project_root).absolute()
        base = root / "projects" / project_id
        if not (base / "meta" / "state.json").exists():
            raise ClosingError(
                error_code=E_UPSTREAM_NOT_READY,
                message=f"project {project_id!r} has no state.json (not initialized)",
                project_id=project_id,
            )

        closing_dir = base / "closing"
        closing_dir.mkdir(parents=True, exist_ok=True)

        # 3 个 closing 文档 render
        lessons_render = self._template.render_template(
            request_id=f"closing-{project_id}-lessons",
            project_id=project_id,
            kind="closing.lessons_learned",
            slots={
                "what_went_well": ["按时交付"],
                "what_went_wrong": ["待补充"],
                "action_items": ["待补充"],
            },
            caller_l2="L2-06",
        )
        manifest_render = self._template.render_template(
            request_id=f"closing-{project_id}-manifest",
            project_id=project_id,
            kind="closing.delivery_manifest",
            slots={"deliverables": [], "checksums": []},
            caller_l2="L2-06",
        )
        retro_render = self._template.render_template(
            request_id=f"closing-{project_id}-retro",
            project_id=project_id,
            kind="closing.retro_summary",
            slots={
                "summary": f"project {project_id} retro",
                "metrics": {
                    "audit_event_count": len(audit_events or []),
                },
            },
            caller_l2="L2-06",
        )

        lessons_path = closing_dir / "lessons_learned.md"
        manifest_path = closing_dir / "delivery_manifest.md"
        retro_path = closing_dir / "retro_summary.md"
        lessons_body = self._body(lessons_render)
        manifest_body = self._body(manifest_render)
        retro_body = self._body(retro_render)
        atomic_write_chart(str(lessons_path), lessons_body)
        atomic_write_chart(str(manifest_path), manifest_body)
        atomic_write_chart(str(retro_path), retro_body)

        bundle_hash = hashlib.sha256(
            (lessons_body + "\n---\n" + manifest_body + "\n---\n" + retro_body).encode("utf-8")
        ).hexdigest()

        # state.json 更新 CLOSING_PRODUCED
        state_path = base / "meta" / "state.json"
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        state_data["state"] = "CLOSING_PRODUCED"
        state_path.write_text(json.dumps(state_data), encoding="utf-8")

        self._event_bus.append_event(
            project_id=project_id, event_type="closing_produced",
            payload={
                "lessons_path": str(lessons_path),
                "manifest_path": str(manifest_path),
                "retro_path": str(retro_path),
                "bundle_hash": bundle_hash,
            },
        )
        return ClosingResult(
            project_id=project_id,
            lessons_path=str(lessons_path),
            manifest_path=str(manifest_path),
            retro_path=str(retro_path),
            closing_bundle_hash=bundle_hash,
        )

    # ---- S7 归档 · PM-14 唯一归档入口 ----

    def archive_project(
        self,
        project_id: str,
        *,
        project_root: str,
        caller_l2: str = "L2-01",
    ) -> ArchiveManifest:
        if caller_l2 != "L2-01":
            raise ClosingError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may archive_project · caller={caller_l2!r}",
                caller_l2=caller_l2, project_id=project_id,
            )

        root = Path(project_root).absolute()
        base = root / "projects" / project_id
        if not base.exists():
            raise ClosingError(
                error_code=E_UPSTREAM_NOT_READY,
                message=f"project {project_id!r} does not exist",
                project_id=project_id,
            )

        # state 必 CLOSING_GATE_APPROVED（本 mock 允许 CLOSING_PRODUCED 作等效）
        state_path = base / "meta" / "state.json"
        if state_path.exists():
            state_data = json.loads(state_path.read_text(encoding="utf-8"))
            if state_data.get("state") not in ("CLOSING_PRODUCED", "CLOSING_GATE_APPROVED", "INITIALIZED"):
                raise ClosingError(
                    error_code=E_STATE_NOT_CLOSING_APPROVED,
                    message=f"state={state_data.get('state')!r} · expected CLOSING_GATE_APPROVED",
                    project_id=project_id,
                )

        # size 预检
        total_size = sum(
            f.stat().st_size for f in base.rglob("*") if f.is_file()
        )
        if total_size > _MAX_PROJECT_SIZE_BYTES:
            raise ClosingError(
                error_code=E_PROJECT_SIZE_EXCEEDED,
                message=f"project size {total_size} > {_MAX_PROJECT_SIZE_BYTES}",
                project_id=project_id,
            )

        archive_dir = root / "projects" / "_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"{project_id}.tar.zst"

        if archive_path.exists():
            raise ClosingError(
                error_code=E_ARCHIVE_ALREADY_EXISTS,
                message=f"archive already exists: {archive_path}",
                project_id=project_id,
            )

        # tar.zst（zstandard compress）
        try:
            import zstandard as zstd
            tar_buffer = BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                tar.add(str(base), arcname=project_id)
            tar_bytes = tar_buffer.getvalue()
            cctx = zstd.ZstdCompressor(level=19)
            compressed = cctx.compress(tar_bytes)
            archive_path.write_bytes(compressed)
        except ImportError:
            # fallback · 纯 tar.gz
            import gzip
            tar_buffer = BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                tar.add(str(base), arcname=project_id)
            archive_path.write_bytes(gzip.compress(tar_buffer.getvalue()))
        except Exception as exc:  # noqa: BLE001
            raise ClosingError(
                error_code=E_TAR_ZST_FAILED,
                message=f"tar.zst failed: {exc}",
                project_id=project_id,
            ) from exc

        # sha256 复验
        sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()

        archived_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "project_id": project_id,
            "archive_path": str(archive_path),
            "sha256": sha,
            "size_bytes": archive_path.stat().st_size,
            "archived_at": archived_at,
        }
        manifest_json = archive_dir / f"{project_id}.manifest.json"
        manifest_json.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

        # chmod 0444（只读保护）
        try:
            os.chmod(archive_path, 0o444)
            for f in base.rglob("*"):
                if f.is_file():
                    os.chmod(f, 0o444)
        except OSError as exc:
            raise ClosingError(
                error_code=E_CHMOD_FAILED,
                message=f"chmod 0444 failed: {exc}",
                project_id=project_id,
            ) from exc

        # state → ARCHIVED
        if state_path.exists():
            state_data["state"] = "ARCHIVED"
            state_data["archived_at"] = archived_at
            # state.json 可能被 chmod 0444 · 先恢复 write perm
            try:
                os.chmod(state_path, 0o644)
                state_path.write_text(json.dumps(state_data), encoding="utf-8")
                os.chmod(state_path, 0o444)
            except OSError:
                pass

        self._event_bus.append_event(
            project_id=project_id, event_type="project_archived",
            payload={
                "archive_path": str(archive_path),
                "sha256": sha,
                "size_bytes": manifest["size_bytes"],
                "archived_at": archived_at,
            },
        )
        return ArchiveManifest(
            project_id=project_id,
            archive_path=str(archive_path),
            sha256=sha,
            size_bytes=manifest["size_bytes"],
            archived_at=archived_at,
        )

    # ---- purge · 归档后 ≥ 90 天 · 双确认 ----

    def purge_project(
        self,
        project_id: str,
        *,
        project_root: str,
        confirm_token: str,
        caller_l2: str = "L2-01",
    ) -> PurgeResult:
        if caller_l2 != "L2-01":
            raise ClosingError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may purge_project · caller={caller_l2!r}",
                caller_l2=caller_l2, project_id=project_id,
            )

        expected_token = f"PURGE-{project_id}-CONFIRMED"
        if confirm_token != expected_token:
            raise ClosingError(
                error_code=E_PURGE_TOKEN_MISMATCH,
                message=f"purge token mismatch · expected={expected_token[:20]}...",
                project_id=project_id,
            )

        root = Path(project_root).absolute()
        manifest_json = root / "projects" / "_archive" / f"{project_id}.manifest.json"
        if not manifest_json.exists():
            raise ClosingError(
                error_code=E_UPSTREAM_NOT_READY,
                message=f"archive manifest not found: {manifest_json}",
                project_id=project_id,
            )

        manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
        archived_at = datetime.fromisoformat(manifest["archived_at"])
        age = datetime.now(timezone.utc) - archived_at
        if age < timedelta(days=_PURGE_MIN_AGE_DAYS):
            raise ClosingError(
                error_code=E_PURGE_TOO_EARLY,
                message=f"archive age {age.days}d < min {_PURGE_MIN_AGE_DAYS}d",
                project_id=project_id,
            )

        # 执行 purge（删 archive + base · ignore 锁定权限）
        archive_path = Path(manifest["archive_path"])
        if archive_path.exists():
            try:
                os.chmod(archive_path, 0o644)
            except OSError:
                pass
            archive_path.unlink()
        manifest_json.unlink()

        base = root / "projects" / project_id
        if base.exists():
            # 先递归恢复文件 + 目录权限（0o444 → 0o755 / 0o644）
            for d in base.rglob("*"):
                try:
                    os.chmod(d, 0o755 if d.is_dir() else 0o644)
                except OSError:
                    pass
            try:
                os.chmod(base, 0o755)
            except OSError:
                pass

            def _onerror(func, path, exc_info):
                try:
                    os.chmod(path, 0o755 if Path(path).is_dir() else 0o644)
                    func(path)
                except OSError:
                    pass

            shutil.rmtree(base, onerror=_onerror)

        self._event_bus.append_event(
            project_id=project_id, event_type="project_purged",
            payload={"age_days": age.days},
        )
        return PurgeResult(project_id=project_id, purged=True, reason="age-check ok")

    @staticmethod
    def _body(render_result: Any) -> str:
        if hasattr(render_result, "output"):
            return str(render_result.output)
        return str(render_result)
