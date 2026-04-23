"""L2-03 FourPiecesProducer · 4 件套串行装配 · 对齐 tech §3/§6。

4 步：REQ → GOAL → AC → QS（严格顺序 · 下一步依赖上一步的 items id）。
每步：skill.delegate_subagent（获取 items）+ template.render_template（产 md body）+ atomic_write 落盘。
完成后 cross_ref 校验（AC.linked_goal / GOAL.linked_reqs / QS.linked_ac 都要在上游存在）。
"""
from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml

from app.project_lifecycle.four_set.errors import (
    E_AC_FORMAT_VIOLATION,
    E_CROSS_REF_DEAD,
    E_DEPENDENCY_CLOSURE_EMPTY,
    E_ID_PATTERN_VIOLATION,
    E_LLM_OUTPUT_EMPTY,
    E_PM14_PID_MISMATCH,
    E_REDO_OUT_OF_SCOPE,
    E_TRACEABILITY_BROKEN,
    E_UPSTREAM_MISSING,
    FourSetError,
)
from app.project_lifecycle.four_set.schemas import (
    CrossCheckReport,
    DocRef,
    DocType,
    FourSetManifest,
    FourSetRequest,
    FourSetResponse,
    StructuredErr,
)
from app.project_lifecycle.kickoff.atomic_writer import atomic_write_chart


_DOC_TYPES: tuple[DocType, ...] = (
    "requirements", "goals", "acceptance_criteria", "quality_standards",
)

_ROLE_FOR_DOC: dict[DocType, str] = {
    "requirements": "requirements-analysis",
    "goals": "goals-writing",
    "acceptance_criteria": "ac-scenario-writer",
    "quality_standards": "quality-audit",
}

_TEMPLATE_KIND_FOR_DOC: dict[DocType, str] = {
    "requirements": "fourset.requirements",
    "goals": "fourset.goals",
    "acceptance_criteria": "fourset.acceptance_criteria",
    "quality_standards": "fourset.quality_standards",
}

_EVENT_FOR_DOC: dict[DocType, str] = {
    "requirements": "requirements_ready",
    "goals": "goals_ready",
    "acceptance_criteria": "ac_ready",
    "quality_standards": "quality_ready",
}


class SkillClient(Protocol):
    def delegate_subagent(
        self,
        *,
        project_id: str,
        delegation_id: str,
        role: str,
        task_brief: str,
        context_copy: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]: ...


class EventSink(Protocol):
    def append_event(
        self, *, project_id: str, event_type: str, payload: dict[str, Any],
    ) -> None: ...


class FourPiecesProducer:
    """L2-03 public API · DI 模式 · template + skill + event_bus。"""

    def __init__(
        self,
        *,
        template: Any,
        skill: SkillClient,
        event_bus: EventSink,
    ) -> None:
        self._template = template
        self._skill = skill
        self._event_bus = event_bus

    def assemble_four_set(
        self,
        req: FourSetRequest,
        *,
        project_root: str,
    ) -> FourSetResponse:
        t0 = time.perf_counter()
        try:
            self._validate_upstream(req, project_root)
        except FourSetError as exc:
            return self._err_response(req, exc, t0)

        try:
            items_by_type = self._produce_all_items(req)
            # cross_ref 校验
            self._cross_ref_check(items_by_type)
            # 每步 template render + atomic_write + ready event
            docs = self._write_docs(req, items_by_type, project_root)
            manifest = self._build_manifest(req, docs, project_root)
            # 总事件
            self._event_bus.append_event(
                project_id=req.project_id,
                event_type="4_pieces_ready",
                payload={
                    "manifest_hash": manifest.manifest_hash,
                    "paths": [d.path for d in docs.values()],
                    "version": manifest.version,
                },
            )
        except FourSetError as exc:
            return self._err_response(req, exc, t0)

        return FourSetResponse(
            project_id=req.project_id,
            request_id=req.request_id,
            status="ok",
            result=manifest,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    def query_artifact_refs(
        self,
        project_id: str,
        *,
        project_root: str,
    ) -> FourSetManifest | None:
        """Gate bundle 索引查询 · 返最新 manifest 或 None。"""
        manifest_path = Path(project_root).absolute() / "projects" / project_id / "four-set" / "manifest.yaml"
        if not manifest_path.exists():
            return None
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        docs_raw = data.get("docs", {})
        docs: dict[DocType, DocRef] = {}
        for dt in _DOC_TYPES:
            d = docs_raw.get(dt, {})
            docs[dt] = DocRef(
                doc_type=dt,
                doc_id=f"{dt}-{project_id[:8]}",
                path=d.get("path", ""),
                hash=d.get("hash", ""),
                version=data.get("version", "v1"),
                item_count=d.get("item_count", 0),
            )
        body = yaml.safe_dump(data, sort_keys=True, allow_unicode=True)
        return FourSetManifest(
            manifest_path=str(manifest_path),
            manifest_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            version=data.get("version", "v1"),
            docs=docs,
            cross_check_report=CrossCheckReport(total_refs_checked=len(docs)),
            produced_at_ns=0,
        )

    def request_wbs_decomposition(
        self,
        project_id: str,
        manifest: FourSetManifest,
        *,
        trim_level: str = "full",
        artifacts_4_pack: dict[str, Any] | None = None,
        architecture_output: dict[str, Any] | None = None,
        target_wp_granularity: str = "medium",
    ) -> dict[str, Any]:
        """IC-19 发起 · S2 Gate 通过后调 L1-03 触发 WBS 拆解。

        对齐 ic-contracts.md §3.19.2 required:
          [command_id, project_id, artifacts_4_pack, architecture_output]

        - command_id 格式 wbs-req-{uuid} · §3.19.5 Non-idempotent 每次产新值
        - artifacts_4_pack 4 子字段: charter_path/plan_path/requirements_path/risk_path
        - architecture_output 子字段: togaf_phases / adr_path
        """
        # §3.19.2 入参校验 · 缺字段 raise（E_WBS_4_PACK_INCOMPLETE / E_WBS_ARCH_OUTPUT_MISSING）
        if artifacts_4_pack is None:
            msg = (
                "§3.19.2 E_WBS_4_PACK_INCOMPLETE · artifacts_4_pack required "
                "(charter_path/plan_path/requirements_path/risk_path)"
            )
            raise ValueError(msg)
        _required_4pack = {"charter_path", "plan_path", "requirements_path", "risk_path"}
        _missing_4pack = _required_4pack - set(artifacts_4_pack.keys())
        if _missing_4pack:
            msg = f"§3.19.2 E_WBS_4_PACK_INCOMPLETE · missing {_missing_4pack}"
            raise ValueError(msg)

        if architecture_output is None:
            msg = "§3.19.2 E_WBS_ARCH_OUTPUT_MISSING · architecture_output required"
            raise ValueError(msg)
        _required_arch = {"togaf_phases", "adr_path"}
        _missing_arch = _required_arch - set(architecture_output.keys())
        if _missing_arch:
            msg = f"§3.19.2 E_WBS_ARCH_OUTPUT_MISSING · missing {_missing_arch}"
            raise ValueError(msg)

        if target_wp_granularity not in ("fine", "medium", "coarse"):
            msg = f"§3.19.2 · target_wp_granularity={target_wp_granularity!r} not in [fine,medium,coarse]"
            raise ValueError(msg)

        ts = (
            datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
        payload = {
            "project_id": project_id,
            "command_id": f"wbs-req-{uuid.uuid4()}",  # §3.19.2 uuid 格式
            "artifacts_4_pack": dict(artifacts_4_pack),
            "architecture_output": dict(architecture_output),
            "target_wp_granularity": target_wp_granularity,
            "ts": ts,
            # 保留 four_set_manifest 作 audit 补充（非 §3.19.2 require）
            "four_set_manifest": {
                "manifest_path": manifest.manifest_path,
                "manifest_hash": manifest.manifest_hash,
                "version": manifest.version,
            },
            "trim_level": trim_level,
        }
        self._event_bus.append_event(
            project_id=project_id,
            event_type="ic_19_request_wbs_decomposition",
            payload=payload,
        )
        return payload

    # ---- 4 step pipeline ----

    def _produce_all_items(
        self, req: FourSetRequest,
    ) -> dict[DocType, list[dict[str, Any]]]:
        """按 REQ → GOAL → AC → QS 顺序 delegate skill · 返 items。

        - LLM 返空 items → E_LLM_OUTPUT_EMPTY
        - doc_id 正则不符 → E_ID_PATTERN_VIOLATION
        - AC 缺 given/when/then → E_AC_FORMAT_VIOLATION
        """
        import re
        id_patterns: dict[DocType, re.Pattern] = {
            "requirements": re.compile(r"^REQ-\d{3}$"),
            "goals": re.compile(r"^GOAL-\d{3}$"),
            "acceptance_criteria": re.compile(r"^AC-\d{3}$"),
            "quality_standards": re.compile(r"^QS-\d{3}$"),
        }

        items_by_type: dict[DocType, list[dict[str, Any]]] = {}
        for doc_type in _DOC_TYPES:
            role = _ROLE_FOR_DOC[doc_type]
            result = self._skill.delegate_subagent(
                project_id=req.project_id,
                delegation_id=f"{req.request_id}-{doc_type}",
                role=role,
                task_brief=f"produce {doc_type}",
                context_copy={
                    "charter_path": req.context.charter_path,
                    "stakeholders_path": req.context.stakeholders_path,
                    "goal_anchor_hash": req.context.goal_anchor_hash,
                    "previous_docs": list(items_by_type.keys()),
                },
            )
            items = list(result.get("items", []))
            if not items:
                raise FourSetError(
                    error_code=E_LLM_OUTPUT_EMPTY,
                    message=f"skill returned empty items for {doc_type}",
                    project_id=req.project_id,
                    context={"doc_type": doc_type},
                )
            # doc_id 正则
            id_re = id_patterns[doc_type]
            for it in items:
                if not id_re.match(str(it.get("id", ""))):
                    raise FourSetError(
                        error_code=E_ID_PATTERN_VIOLATION,
                        message=f"{doc_type} id={it.get('id')!r} violates pattern {id_re.pattern}",
                        project_id=req.project_id,
                        context={"doc_type": doc_type, "bad_id": it.get("id")},
                    )
            # AC 必含 Given/When/Then
            if doc_type == "acceptance_criteria":
                for ac in items:
                    for k in ("given", "when", "then"):
                        if not ac.get(k):
                            raise FourSetError(
                                error_code=E_AC_FORMAT_VIOLATION,
                                message=f"AC {ac.get('id')!r} missing {k!r}",
                                project_id=req.project_id,
                                context={"ac_id": ac.get("id"), "missing": k},
                            )
            items_by_type[doc_type] = items
        return items_by_type

    def _cross_ref_check(
        self, items_by_type: dict[DocType, list[dict[str, Any]]],
    ) -> None:
        """校验 cross-ref 合法性：
        - GOAL.linked_reqs ⊂ requirements.id
        - AC.linked_goal ∈ goals.id
        - QS.linked_ac ∈ acceptance_criteria.id
        破环即 E_TRACEABILITY_BROKEN。
        """
        req_ids = {i["id"] for i in items_by_type.get("requirements", [])}
        goal_ids = {i["id"] for i in items_by_type.get("goals", [])}
        ac_ids = {i["id"] for i in items_by_type.get("acceptance_criteria", [])}

        errors: list[str] = []
        for g in items_by_type.get("goals", []):
            for lr in g.get("linked_reqs", []):
                if lr not in req_ids:
                    errors.append(f"{g['id']}.linked_reqs={lr!r} not in requirements")
        for ac in items_by_type.get("acceptance_criteria", []):
            lg = ac.get("linked_goal")
            if lg and lg not in goal_ids:
                errors.append(f"{ac['id']}.linked_goal={lg!r} not in goals")
        for qs in items_by_type.get("quality_standards", []):
            la = qs.get("linked_ac")
            if la and la not in ac_ids:
                errors.append(f"{qs['id']}.linked_ac={la!r} not in acceptance_criteria")

        if errors:
            raise FourSetError(
                error_code=E_TRACEABILITY_BROKEN,
                message=f"cross-ref errors: {'; '.join(errors)}",
                context={"dead_refs": errors},
            )

    def _write_docs(
        self,
        req: FourSetRequest,
        items_by_type: dict[DocType, list[dict[str, Any]]],
        project_root: str,
    ) -> dict[DocType, DocRef]:
        """逐个 render + atomic_write + 发 ready 事件（严格顺序）。"""
        root = Path(project_root).absolute()
        four_set_dir = root / "projects" / req.project_id / "four-set"
        four_set_dir.mkdir(parents=True, exist_ok=True)

        docs: dict[DocType, DocRef] = {}
        for doc_type in _DOC_TYPES:
            items = items_by_type.get(doc_type, [])
            kind = _TEMPLATE_KIND_FOR_DOC[doc_type]
            slot_key = self._slot_key_for(doc_type)
            render = self._template.render_template(
                request_id=f"{req.request_id}-{doc_type}",
                project_id=req.project_id,
                kind=kind,
                slots={"project_id": req.project_id, slot_key: items},
                caller_l2="L2-03",
            )
            body = self._render_body(render)
            file_path = four_set_dir / f"{doc_type}.md"
            atomic_write_chart(str(file_path), body)
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

            docs[doc_type] = DocRef(
                doc_type=doc_type,
                doc_id=f"{doc_type}-{req.project_id[:8]}",
                path=str(file_path),
                hash=body_hash,
                version="v1",
                item_count=len(items),
                qc_status="pass",
            )

            self._event_bus.append_event(
                project_id=req.project_id,
                event_type=_EVENT_FOR_DOC[doc_type],
                payload={
                    "path": str(file_path),
                    "hash": body_hash,
                    "item_count": len(items),
                },
            )
        return docs

    def _build_manifest(
        self,
        req: FourSetRequest,
        docs: dict[DocType, DocRef],
        project_root: str,
    ) -> FourSetManifest:
        root = Path(project_root).absolute()
        manifest_path = root / "projects" / req.project_id / "four-set" / "manifest.yaml"
        manifest_data = {
            "project_id": req.project_id,
            "version": "v1",
            "docs": {
                dt: {"path": d.path, "hash": d.hash, "item_count": d.item_count}
                for dt, d in docs.items()
            },
            "produced_by": "L2-03",
        }
        body = yaml.safe_dump(manifest_data, sort_keys=True, allow_unicode=True)
        manifest_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        atomic_write_chart(str(manifest_path), body)
        return FourSetManifest(
            manifest_path=str(manifest_path),
            manifest_hash=manifest_hash,
            version="v1",
            docs=docs,
            cross_check_report=CrossCheckReport(errors=(), warnings=(), total_refs_checked=len(docs)),
            produced_at_ns=time.time_ns(),
        )

    # ---- helpers ----

    def _validate_upstream(self, req: FourSetRequest, project_root: str) -> None:
        """校验 upstream 章程存在 + PM-14 pid 一致（check 顺序：存在优先 · pid 其次）。"""
        # 先测文件存在 · UPSTREAM_MISSING 优先
        if not Path(req.context.charter_path).exists():
            raise FourSetError(
                error_code=E_UPSTREAM_MISSING,
                message=f"charter not found: {req.context.charter_path}",
                project_id=req.project_id,
            )
        if not Path(req.context.stakeholders_path).exists():
            raise FourSetError(
                error_code=E_UPSTREAM_MISSING,
                message=f"stakeholders not found: {req.context.stakeholders_path}",
                project_id=req.project_id,
            )

        # PM-14 pid mismatch · 路径里必须含 req.project_id
        if f"/projects/{req.project_id}/" not in str(req.context.charter_path):
            raise FourSetError(
                error_code=E_PM14_PID_MISMATCH,
                message=(
                    f"req.project_id={req.project_id!r} not found in "
                    f"context.charter_path={req.context.charter_path!r}"
                ),
                project_id=req.project_id,
            )

    def _err_response(
        self, req: FourSetRequest, exc: FourSetError, t0: float,
    ) -> FourSetResponse:
        return FourSetResponse(
            project_id=req.project_id,
            request_id=req.request_id,
            status="err",
            result=StructuredErr(
                err_type=exc.error_code,
                reason=exc.message,
                project_id=req.project_id,
                context=exc.context,
            ),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    @staticmethod
    def _slot_key_for(doc_type: DocType) -> str:
        return {
            "requirements": "requirements_items",
            "goals": "goals_items",
            "acceptance_criteria": "ac_items",
            "quality_standards": "qs_items",
        }[doc_type]

    @staticmethod
    def _render_body(render_result: Any) -> str:
        if hasattr(render_result, "output"):
            return str(render_result.output)
        if isinstance(render_result, dict):
            return str(render_result.get("template_body") or render_result.get("output") or "")
        return str(render_result)
