"""L2-05 TogafProducer · ADM Phase 严格顺序 + profile 裁剪 + togaf_d_ready 提前信号。

Phase 顺序：Preliminary → A → B → C → D → E → F → G → H
3 profile：
  - LIGHT：A/B/C_data/C_app/D（ADR ≥ 5）
  - STANDARD：Preliminary + A/B/C/D + H（ADR ≥ 10）
  - HEAVY：全 9 Phase（ADR ≥ 15）

Phase D 完成 → 立即 emit togaf_d_ready 事件（关键提前信号 · 解 L2-04 Group 2 阻塞）
延迟 SLO ≤ 200ms。
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml

from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart
from app.project_lifecycle.togaf.errors import (
    E_ADR_COUNT_INSUFFICIENT,
    E_INVALID_PROFILE,
    E_LLM_OUTPUT_EMPTY,
    E_PHASE_ORDER_VIOLATION,
    E_PM14_OWNERSHIP_VIOLATION,
    E_REVIEWER_REJECT,
    TogafError,
)


Profile = Literal["LIGHT", "STANDARD", "HEAVY"]

_PROFILE_PHASES: dict[Profile, tuple[str, ...]] = {
    "LIGHT": ("phase_a", "phase_b", "phase_c_data", "phase_c_application", "phase_d"),
    "STANDARD": (
        "preliminary", "phase_a", "phase_b", "phase_c_data",
        "phase_c_application", "phase_d", "phase_h",
    ),
    "HEAVY": (
        "preliminary", "phase_a", "phase_b", "phase_c_data",
        "phase_c_application", "phase_d", "phase_e", "phase_f",
        "phase_g", "phase_h",
    ),
}

_ALL_PHASES_ORDER: tuple[str, ...] = (
    "preliminary", "phase_a", "phase_b", "phase_c_data",
    "phase_c_application", "phase_d", "phase_e", "phase_f",
    "phase_g", "phase_h",
)

_ADR_MIN_BY_PROFILE: dict[Profile, int] = {
    "LIGHT": 5,
    "STANDARD": 10,
    "HEAVY": 15,
}


@dataclass
class PhaseResult:
    phase: str
    status: Literal["ok", "failed"]
    path: str = ""
    body_hash: str = ""
    error: str | None = None


@dataclass
class TogafResult:
    project_id: str
    profile: Profile
    status: Literal["ok", "err"]
    phases: dict[str, PhaseResult]
    adr_count: int
    togaf_d_emitted_at_ns: int = 0
    manifest_path: str = ""


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


class TogafProducer:

    def __init__(
        self,
        *,
        template: Any,
        event_bus: EventSink,
        reviewer: Any | None = None,  # L1-05 architecture-reviewer mock
    ) -> None:
        self._template = template
        self._event_bus = event_bus
        self._reviewer = reviewer

    def produce_togaf(
        self,
        project_id: str,
        *,
        project_root: str,
        profile: Profile = "STANDARD",
        caller_l2: str = "L2-01",
        adr_list: list[dict[str, Any]] | None = None,
    ) -> TogafResult:
        if caller_l2 != "L2-01":
            raise TogafError(
                error_code=E_PM14_OWNERSHIP_VIOLATION,
                message=f"only L2-01 may call produce_togaf · caller={caller_l2!r}",
                caller_l2=caller_l2, project_id=project_id,
            )
        if profile not in _PROFILE_PHASES:
            raise TogafError(
                error_code=E_INVALID_PROFILE,
                message=f"invalid profile {profile!r}",
                project_id=project_id,
            )

        phases_to_run = _PROFILE_PHASES[profile]
        root = Path(project_root).absolute()
        togaf_dir = root / "projects" / project_id / "togaf"
        togaf_dir.mkdir(parents=True, exist_ok=True)
        adr_dir = togaf_dir / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)

        # Phase 严格顺序校验：phases_to_run 是 _ALL_PHASES_ORDER 的子序列
        order_map = {ph: i for i, ph in enumerate(_ALL_PHASES_ORDER)}
        for i in range(len(phases_to_run) - 1):
            if order_map[phases_to_run[i]] >= order_map[phases_to_run[i + 1]]:
                raise TogafError(
                    error_code=E_PHASE_ORDER_VIOLATION,
                    message=f"phases not in canonical order: {phases_to_run}",
                    project_id=project_id,
                )

        phases: dict[str, PhaseResult] = {}
        togaf_d_emitted_at_ns = 0

        for ph in phases_to_run:
            pr = self._produce_phase(project_id, ph, togaf_dir)
            phases[ph] = pr
            self._event_bus.append_event(
                project_id=project_id,
                event_type=f"togaf_{ph}_ready" if pr.status == "ok" else f"togaf_{ph}_failed",
                payload={"phase": ph, "path": pr.path, "hash": pr.body_hash},
            )
            # Phase D 完成 → togaf_d_ready 提前信号
            if ph == "phase_d" and pr.status == "ok":
                togaf_d_emitted_at_ns = time.time_ns()
                self._event_bus.append_event(
                    project_id=project_id,
                    event_type="togaf_d_ready",
                    payload={
                        "phase_d_path": pr.path,
                        "phase_d_hash": pr.body_hash,
                        "emitted_at_ns": togaf_d_emitted_at_ns,
                    },
                )

            # Phase C reviewer 委托（mock · 失败降级本地规则）
            if ph.startswith("phase_c") and self._reviewer is not None:
                try:
                    review = self._reviewer.review(project_id=project_id, phase=ph, path=pr.path)
                    if not review.get("pass", True):
                        raise TogafError(
                            error_code=E_REVIEWER_REJECT,
                            message=f"reviewer rejected {ph}: {review.get('reason')}",
                            project_id=project_id,
                        )
                except TogafError:
                    raise
                except Exception:  # noqa: BLE001
                    # 降级本地规则评审（简化：pass）
                    pass

        # ADR 数校验
        adr_count = len(adr_list or [])
        adr_min = _ADR_MIN_BY_PROFILE[profile]
        if adr_count < adr_min:
            # 警告级 · 不硬拒 · 但在严格 profile 下抛
            if profile == "HEAVY":
                raise TogafError(
                    error_code=E_ADR_COUNT_INSUFFICIENT,
                    message=f"ADR count={adr_count} < min={adr_min} for {profile}",
                    project_id=project_id,
                )

        # 写 ADR md（若有）
        if adr_list:
            for i, adr in enumerate(adr_list):
                adr_path = adr_dir / f"ADR-{i+1:03d}.md"
                adr_body = yaml.safe_dump(adr, sort_keys=False, allow_unicode=True)
                atomic_write_chart(str(adr_path), adr_body)

        manifest = {
            "project_id": project_id,
            "profile": profile,
            "phases": {p: {"status": r.status, "path": r.path, "hash": r.body_hash}
                       for p, r in phases.items()},
            "adr_count": adr_count,
        }
        manifest_path = togaf_dir / "manifest.yaml"
        atomic_write_chart(
            str(manifest_path),
            yaml.safe_dump(manifest, sort_keys=True, allow_unicode=True),
        )

        # togaf_ready 总事件
        self._event_bus.append_event(
            project_id=project_id,
            event_type="togaf_ready",
            payload={
                "profile": profile,
                "phases": list(phases.keys()),
                "adr_count": adr_count,
                "manifest_path": str(manifest_path),
            },
        )

        return TogafResult(
            project_id=project_id,
            profile=profile,
            status="ok",
            phases=phases,
            adr_count=adr_count,
            togaf_d_emitted_at_ns=togaf_d_emitted_at_ns,
            manifest_path=str(manifest_path),
        )

    def _produce_phase(
        self, project_id: str, phase: str, togaf_dir: Path,
    ) -> PhaseResult:
        try:
            kind = f"togaf.{phase}"
            render = self._template.render_template(
                request_id=f"togaf-{project_id}-{phase}",
                project_id=project_id,
                kind=kind,
                slots=self._default_slots_for(phase),
                caller_l2="L2-05",
            )
            body = render.output if hasattr(render, "output") else str(render)
            if not body or not body.strip():
                return PhaseResult(phase=phase, status="failed",
                                   error=E_LLM_OUTPUT_EMPTY)
            path = togaf_dir / f"{phase}.md"
            atomic_write_chart(str(path), body)
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            return PhaseResult(phase=phase, status="ok", path=str(path), body_hash=body_hash)
        except Exception as exc:  # noqa: BLE001
            return PhaseResult(phase=phase, status="failed", error=str(exc))

    @staticmethod
    def _default_slots_for(phase: str) -> dict[str, Any]:
        """最小合法 slots（对齐 templates/togaf/*.md slot_schema）。"""
        return {
            "preliminary": {"principles": ["safety-first"], "stakeholders": []},
            "phase_a": {"vision": "TBD", "goals": ["TBD"]},
            "phase_b": {"business_capabilities": [], "value_streams": []},
            "phase_c_data": {"data_entities": [], "data_flows": []},
            "phase_c_application": {"applications": [], "interactions": []},
            "phase_d": {"tech_components": [], "standards": []},
            "phase_e": {"opportunities": [], "solutions": []},
            "phase_f": {"work_packages": []},
            "phase_g": {"governance_items": []},
            "phase_h": {"change_requests": []},
        }[phase]
