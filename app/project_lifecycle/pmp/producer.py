"""L2-04 PmpPlansProducer · 9 并发 + 分级降级。

9 kda：integration / scope / schedule / cost / quality / resource / communication / risk / procurement
核心 kda（scope / schedule / cost）任一失败 → E_CORE_KDA_FAILED（整批 reject）
非核心失败 ≤ 4 → PARTIAL（evidence 标 degraded）
失败 ≥ 5 → E_NON_CORE_LIMIT_EXCEEDED
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml

from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart
from app.project_lifecycle.pmp.errors import (
    E_CORE_KDA_FAILED,
    E_LLM_OUTPUT_EMPTY,
    E_NON_CORE_LIMIT_EXCEEDED,
    E_PLAN_UPSTREAM_MISSING,
    E_PM14_OWNERSHIP_VIOLATION,
    PmpError,
)


PMP_9_KDAS: tuple[str, ...] = (
    "integration", "scope", "schedule", "cost", "quality",
    "resource", "communication", "risk", "procurement",
)
CORE_KDAS: frozenset[str] = frozenset({"scope", "schedule", "cost"})


@dataclass
class PmpKdaResult:
    kda: str
    status: Literal["ok", "failed"]
    path: str = ""
    body_hash: str = ""
    error: str | None = None


@dataclass
class PmpBundleResult:
    project_id: str
    status: Literal["ok", "partial", "err"]
    kdas: dict[str, PmpKdaResult]
    bundle_hash: str
    manifest_path: str
    togaf_alignment: bool = True
    degraded_kdas: tuple[str, ...] = ()


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


class PmpPlansProducer:

    def __init__(
        self,
        *,
        template: Any,
        event_bus: EventSink,
        togaf_cross_check: Any | None = None,  # L2-05 mock
    ) -> None:
        self._template = template
        self._event_bus = event_bus
        self._togaf = togaf_cross_check

    async def produce_all_9(
        self,
        project_id: str,
        *,
        project_root: str,
        caller_l2: str = "L2-01",
        upstream_four_set_manifest: str | None = None,
    ) -> PmpBundleResult:
        # PM-14 caller 校验
        if caller_l2 != "L2-01":
            raise PmpError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may call produce_all_9 · caller={caller_l2!r}",
                caller_l2=caller_l2, project_id=project_id,
            )

        # 上游 4 件套 manifest 校验
        if upstream_four_set_manifest:
            if not Path(upstream_four_set_manifest).exists():
                raise PmpError(
                    error_code=E_PLAN_UPSTREAM_MISSING,
                    message=f"upstream 4-set manifest missing: {upstream_four_set_manifest}",
                    project_id=project_id,
                )

        root = Path(project_root).absolute()
        pmp_dir = root / "projects" / project_id / "pmp"
        pmp_dir.mkdir(parents=True, exist_ok=True)

        # 9 并发 producer
        tasks = [
            self._produce_one(project_id, kda, pmp_dir)
            for kda in PMP_9_KDAS
        ]
        results: list[PmpKdaResult] = await asyncio.gather(*tasks, return_exceptions=False)

        kdas: dict[str, PmpKdaResult] = {r.kda: r for r in results}

        # 分级降级
        core_failed = [k for k in CORE_KDAS if kdas[k].status == "failed"]
        if core_failed:
            raise PmpError(
                error_code=E_CORE_KDA_FAILED,
                message=f"core kda failed: {core_failed}",
                project_id=project_id,
                context={"core_failed": core_failed},
            )

        non_core_failed = [
            r.kda for r in results
            if r.status == "failed" and r.kda not in CORE_KDAS
        ]
        if len(non_core_failed) >= 5:
            raise PmpError(
                error_code=E_NON_CORE_LIMIT_EXCEEDED,
                message=f"non-core failures ≥ 5: {non_core_failed}",
                project_id=project_id,
                context={"non_core_failed": non_core_failed},
            )

        # cross_check_togaf_alignment
        alignment = True
        if self._togaf is not None:
            alignment = bool(self._togaf.check_alignment(project_id, kdas))

        # bundle hash（9 md 固定顺序 concat · sha256）
        bundle_hash = self._compute_bundle_hash(kdas)

        # manifest
        manifest_data = {
            "project_id": project_id,
            "bundle_hash": bundle_hash,
            "kdas": {k: {"status": r.status, "path": r.path, "hash": r.body_hash}
                     for k, r in kdas.items()},
            "core_ok": not core_failed,
            "degraded_kdas": non_core_failed,
            "togaf_alignment": alignment,
        }
        manifest_path = pmp_dir / "manifest.yaml"
        atomic_write_chart(
            str(manifest_path),
            yaml.safe_dump(manifest_data, sort_keys=True, allow_unicode=True),
        )

        status: Literal["ok", "partial", "err"] = "partial" if non_core_failed else "ok"

        # IC-09 事件
        self._event_bus.append_event(
            project_id=project_id,
            event_type="9_plans_ready",
            payload={
                "bundle_hash": bundle_hash,
                "status": status,
                "degraded_kdas": non_core_failed,
                "manifest_path": str(manifest_path),
            },
        )

        return PmpBundleResult(
            project_id=project_id,
            status=status,
            kdas=kdas,
            bundle_hash=bundle_hash,
            manifest_path=str(manifest_path),
            togaf_alignment=alignment,
            degraded_kdas=tuple(non_core_failed),
        )

    async def _produce_one(
        self, project_id: str, kda: str, pmp_dir: Path,
    ) -> PmpKdaResult:
        """单 kda 异步产出 · 调 template + 落盘。"""
        try:
            kind = f"pmp.{kda}"
            render = self._template.render_template(
                request_id=f"pmp-{project_id}-{kda}",
                project_id=project_id,
                kind=kind,
                slots=self._default_slots_for(kda),
                caller_l2="L2-04",
            )
            body = self._render_body(render)
            if not body or not body.strip():
                return PmpKdaResult(kda=kda, status="failed",
                                    error=E_LLM_OUTPUT_EMPTY)
            path = pmp_dir / f"{kda}.md"
            atomic_write_chart(str(path), body)
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            return PmpKdaResult(
                kda=kda, status="ok", path=str(path), body_hash=body_hash,
            )
        except Exception as exc:  # noqa: BLE001
            return PmpKdaResult(kda=kda, status="failed", error=str(exc))

    @staticmethod
    def _compute_bundle_hash(kdas: dict[str, PmpKdaResult]) -> str:
        """固定 PMP_9_KDAS 顺序 concat hash · 保证幂等。"""
        parts: list[str] = []
        for k in PMP_9_KDAS:
            r = kdas.get(k)
            if r and r.status == "ok":
                parts.append(f"{k}:{r.body_hash}")
            else:
                parts.append(f"{k}:FAILED")
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def _default_slots_for(kda: str) -> dict[str, Any]:
        """按 templates/pmp/*.md slot_schema 填最小合法值。"""
        return {
            "integration": {"integration_summary": "TBD", "change_control": ["standard"]},
            "scope": {"scope_statement": "TBD", "scope_items": [], "out_of_scope": []},
            "schedule": {"milestones": [], "critical_path": []},
            "cost": {"budget_total": 0, "cost_breakdown": []},
            "quality": {"quality_objectives": [], "quality_checks": []},
            "resource": {"roles": [], "availability": []},
            "communication": {"channels": [], "cadence": []},
            "risk": {"risks": []},
            "procurement": {"items": []},
        }[kda]

    @staticmethod
    def _render_body(render_result: Any) -> str:
        if hasattr(render_result, "output"):
            return str(render_result.output)
        if isinstance(render_result, dict):
            return str(render_result.get("output") or render_result.get("template_body") or "")
        return str(render_result)
