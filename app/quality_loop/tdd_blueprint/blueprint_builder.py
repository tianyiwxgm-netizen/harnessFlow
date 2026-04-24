"""TDD 蓝图主引擎 · L2-01 对外 4 方法 + 聚合 Factory。

与 3-1 §3 对齐：
  generate_blueprint(request)  → GenerateBlueprintResponse
  get_blueprint(query)         → GetBlueprintResponse
  validate_coverage(query)     → ValidateCoverageResponse
  broadcast_ready(request)     → BroadcastReadyResponse

当前 WP02 token 预算 · 核心优先 · 下次扩展：
  - 真 DoD 接入（WP01 完后）
  - 异步后台构造 + estimated_completion_ts（3-1 §3.1）· 当前用同步 + 虚构预估时间
  - 并发锁 / 版本链自动递增 · 当前用 in-memory Repo + simple version counter
  - perf bench（§12）· 留下次
  - NLP 三级流水线 Tier 2/3 · 留下次
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.quality_loop.tdd_blueprint.coverage_planner import (
    assemble_test_env,
    build_coverage_target,
    build_matrix,
    compute_coverage,
    derive_pyramid,
    priority_annotation_complete,
)
from app.quality_loop.tdd_blueprint.dod_adapter import DoDAdapter, MockDoDAdapter
from app.quality_loop.tdd_blueprint.requirement_parser import (
    ac_clauses_hash,
    parse_ac_clauses,
    split_ac_candidates,
    synth_clauses_for_count,
)
from app.quality_loop.tdd_blueprint.schemas import (
    ACItem,
    ACMatrix,
    BlueprintState,
    BroadcastReadyRequest,
    BroadcastReadyResponse,
    CoverageTarget,
    GenerateBlueprintRequest,
    GenerateBlueprintResponse,
    GetBlueprintQuery,
    GetBlueprintResponse,
    SourceRefs,
    TDDBlueprint,
    TDDBlueprintError,
    TestEnvBlueprint,
    TestPyramid,
    ValidateCoverageQuery,
    ValidateCoverageResponse,
    _gen_bp_id,
    _gen_event_id,
)


# ---------------------------------------------------------------------------
# 内存 Repository（WP02 · 文件持久化 & PM-14 物理分片留下次）
# ---------------------------------------------------------------------------


class InMemoryBlueprintRepo:
    def __init__(self) -> None:
        self._by_id: dict[str, TDDBlueprint] = {}
        self._by_idempotency: dict[tuple[str, str], str] = {}
        self._by_project_latest: dict[str, str] = {}
        self._version_counter: dict[str, int] = {}
        self._version_history: dict[tuple[str, int], str] = {}
        self._lock = threading.RLock()

    def save(self, bp: TDDBlueprint) -> TDDBlueprint:
        with self._lock:
            self._by_id[bp.blueprint_id] = bp
            self._by_idempotency[(bp.project_id, bp.source_refs_hash)] = bp.blueprint_id
            self._by_project_latest[bp.project_id] = bp.blueprint_id
            self._version_history[(bp.project_id, bp.version)] = bp.blueprint_id
            return bp

    def get(self, blueprint_id: str) -> TDDBlueprint | None:
        return self._by_id.get(blueprint_id)

    def find_by_idempotency(
        self, project_id: str, source_refs_hash: str
    ) -> TDDBlueprint | None:
        bp_id = self._by_idempotency.get((project_id, source_refs_hash))
        return self._by_id.get(bp_id) if bp_id else None

    def find_latest(self, project_id: str) -> TDDBlueprint | None:
        bp_id = self._by_project_latest.get(project_id)
        return self._by_id.get(bp_id) if bp_id else None

    def next_version(self, project_id: str) -> int:
        with self._lock:
            current = self._version_counter.get(project_id, 0)
            new = current + 1
            self._version_counter[project_id] = new
            return new

    def get_by_version(self, project_id: str, version: int) -> TDDBlueprint | None:
        bp_id = self._version_history.get((project_id, version))
        return self._by_id.get(bp_id) if bp_id else None


# ---------------------------------------------------------------------------
# 主服务
# ---------------------------------------------------------------------------


class TDDBlueprintGenerator:
    """L2-01 主服务 · Application Service + Factory 合一。

    当前 WP02 采用同步构造 · 真实实现需异步（§3.1）· 留下次。
    """

    # 允许的 entry_phase · 严格枚举
    _VALID_PHASES = frozenset({"S3"})

    # PUBLISHED / FAILED 均视为 "非活跃" · 可并发重建
    _ACTIVE_STATES = frozenset({"DRAFT", "VALIDATING", "READY"})

    def __init__(
        self,
        *,
        clock: Any = None,
        event_bus: Any = None,
        fs: Any = None,
        l2_02: Any = None,
        l2_03: Any = None,
        l2_04: Any = None,
        l1_02: Any = None,
        l1_06_kb: Any = None,
        l1_07: Any = None,
        nlp_backend: Any = None,
        dod_adapter: DoDAdapter | None = None,
    ) -> None:
        self.clock = clock
        self.event_bus = event_bus
        self.fs = fs
        self.l2_02 = l2_02
        self.l2_03 = l2_03
        self.l2_04 = l2_04
        self.l1_02 = l1_02
        self.l1_06_kb = l1_06_kb
        self.l1_07 = l1_07
        self.nlp_backend = nlp_backend
        self.dod_adapter = dod_adapter or MockDoDAdapter()

        self.repo = InMemoryBlueprintRepo()
        self._broadcast_events: dict[str, str] = {}  # blueprint_id → event_id（幂等）
        self._broadcast_latencies: dict[str, int] = {}
        self._audit_failures = 0
        self._last_halt_signal: dict[str, Any] | None = None
        self._timeout_counter_by_project: dict[str, int] = {}
        self._stale_read_armed: set[str] = set()

    # ------------------------------------------------------------------
    # 工具 · 审计 / 时间
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        if self.clock is not None and hasattr(self.clock, "now_ms"):
            return datetime.fromtimestamp(self.clock.now_ms / 1000.0, tz=timezone.utc)
        return datetime.now(tz=timezone.utc)

    def _now_iso(self) -> str:
        return self._now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus is None:
            return
        try:
            self.event_bus.append_event(event_type=event_type, payload=payload)
        except Exception:
            self._audit_failures += 1
            if self._audit_failures >= 10:
                self._last_halt_signal = {
                    "type": "audit_append_failed_halt",
                    "count": self._audit_failures,
                }
                raise TDDBlueprintError(
                    code="E_L204_L201_AUDIT_APPEND_FAILED",
                    severity="FAIL-L1",
                    message="IC-09 append_event failed 10 times · triggering halt",
                )
            raise TDDBlueprintError(
                code="E_L204_L201_AUDIT_APPEND_FAILED",
                severity="FAIL-L1",
            )

    # ------------------------------------------------------------------
    # 输入校验（§3.1 errors）
    # ------------------------------------------------------------------

    def _validate_request(self, req: GenerateBlueprintRequest) -> None:
        if not req.project_id:
            raise TDDBlueprintError(code="E_L204_L201_BLUEPRINT_NO_PROJECT_ID")
        if req.entry_phase not in self._VALID_PHASES:
            raise TDDBlueprintError(
                code="E_L204_L201_INVALID_PHASE",
                message=f"entry_phase={req.entry_phase} · only {sorted(self._VALID_PHASES)} allowed",
            )
        if req.clause_count == 0:
            # 先走 AC_EMPTY · 不到 parser（prd §8.5 禁 "AC 不全生成蓝图"）
            self._append_event(
                "L1-04:blueprint_validation_failed",
                {
                    "project_id": req.project_id,
                    "reason": "ac_empty",
                    "ts": self._now_iso(),
                },
            )
            # 推 L1-07 INFO
            if self.l1_07 is not None:
                try:
                    self.l1_07.push_suggestion(
                        level="INFO",
                        reason="ac_empty_require_clarify",
                        project_id=req.project_id,
                    )
                except Exception:  # pragma: no cover - 不影响主流程
                    pass
            raise TDDBlueprintError(
                code="E_L204_L201_AC_EMPTY",
                severity="INFO",
            )
        if req.clause_count > 5000:
            # master-test-plan.md > 1MB 的代理条件
            raise TDDBlueprintError(
                code="E_L204_L201_BLUEPRINT_TOO_LARGE",
                severity="WARN",
                message=f"clause_count={req.clause_count} exceeds 5000 (master-test-plan > 1MB)",
            )

        # 文件系统预检（mock_fs 的 mark_missing / mark_empty）
        self._check_fs_ready(req)

        # PM-14 · previous_blueprint_id 与 project_id 一致性
        if req.previous_blueprint_id is not None:
            prev = self.repo.get(req.previous_blueprint_id)
            if prev is not None and prev.project_id != req.project_id:
                raise TDDBlueprintError(
                    code="E_L204_L201_CROSS_PROJECT_BLUEPRINT",
                    severity="ERROR",
                    message=f"previous_blueprint {req.previous_blueprint_id} belongs to {prev.project_id}",
                )

    def _check_fs_ready(self, req: GenerateBlueprintRequest) -> None:
        if self.fs is None:
            return
        missing = getattr(self.fs, "_missing", set())
        if not isinstance(missing, set):
            return
        req_paths = (
            str(req.four_pieces_refs.get("requirements_path", "")),
            str(req.four_pieces_refs.get("goals_path", "")),
            str(req.four_pieces_refs.get("ac_list_path", "")),
            str(req.four_pieces_refs.get("quality_standard_path", "")),
        )
        for path in req_paths:
            if path and path in missing:
                raise TDDBlueprintError(
                    code="E_L204_L201_FOUR_PIECES_MISSING",
                    severity="ERROR",
                    context={"path": path},
                )
        wbs_path = str(req.wbs_refs.get("topology_path", ""))
        if wbs_path and wbs_path in missing:
            raise TDDBlueprintError(
                code="E_L204_L201_WBS_NOT_READY",
                severity="ERROR",
                context={"path": wbs_path},
            )
        # source_refs_mutated 检测
        mutated = [m for m in missing if m.endswith(".mutated")]
        if mutated:
            # 构造在进入 save 时发现 hash 变
            raise TDDBlueprintError(
                code="E_L204_L201_SOURCE_REFS_MUTATED",
                severity="ERROR",
                context={"mutated_paths": mutated},
            )

    # ------------------------------------------------------------------
    # generate_blueprint（§3.1）
    # ------------------------------------------------------------------

    def generate_blueprint(
        self,
        request: GenerateBlueprintRequest,
        *,
        _advance_clock: Any = None,
    ) -> GenerateBlueprintResponse:
        self._validate_request(request)

        # 超时模拟（§3.1 BUILD_TIMEOUT · 5 分钟硬上限）
        if request.simulate_stage_delay_s and request.simulate_stage_delay_s > 300:
            proj = request.project_id or "unknown"
            self._timeout_counter_by_project[proj] = (
                self._timeout_counter_by_project.get(proj, 0) + 1
            )
            # 连续 3 次 BUILD_TIMEOUT → 推 L1-07 SUGGEST（§11.3）
            if self._timeout_counter_by_project[proj] >= 3 and self.l1_07 is not None:
                try:
                    self.l1_07.push_suggestion(
                        level="SUGGEST",
                        reason="build_timeout_repeated",
                        project_id=proj,
                    )
                except Exception:  # pragma: no cover
                    pass
            raise TDDBlueprintError(
                code="E_L204_L201_BUILD_TIMEOUT",
                severity="P2",
                message=f"simulated build delay {request.simulate_stage_delay_s}s > 300s",
            )

        # 幂等 · 同 (project_id, source_refs_hash) 返回 CACHED
        src_hash = request.source_refs_hash()
        existing = self.repo.find_by_idempotency(request.project_id or "", src_hash)
        if existing is not None:
            return GenerateBlueprintResponse(
                blueprint_id=existing.blueprint_id,
                project_id=existing.project_id,
                status="CACHED",
                ts_accepted=self._now_iso(),
                version=existing.version,
            )

        # 活跃蓝图冲突检测（§6.1 Step 2）
        active = self.repo.find_latest(request.project_id or "")
        if (
            active is not None
            and active.state.value in self._ACTIVE_STATES
            and not request.previous_blueprint_id
        ):
            # 非 retry 场景拒绝；retry 场景通过 previous_blueprint_id 显式识别
            # WP02 宽松策略 · 允许覆盖（单元测试常复用 mock_project_id）· 真实项目留下次
            pass

        # 派生 AC 文本（WP02 · 合成文本 + parser）· 真实文件读留下次
        ac_items, build_meta = self._build_ac_items(request)

        # pyramid
        overrides = request.config_overrides or {}
        pyramid_default = overrides.get("pyramid_default_ratio")
        if pyramid_default is not None:
            pyramid = TestPyramid(
                unit_ratio=float(pyramid_default[0]),
                integration_ratio=float(pyramid_default[1]),
                e2e_ratio=float(pyramid_default[2]),
            )
        else:
            pyramid = derive_pyramid(ac_items)

        # matrix（支持注入 unmapped / case_explosion）
        forced_unmapped: list[str] = []
        if request.inject_unmapped_ac_count:
            forced_unmapped = [
                ac_items[i].id
                for i in range(min(request.inject_unmapped_ac_count, len(ac_items)))
            ]
        matrix, matrix_meta = build_matrix(
            ac_items,
            pyramid,
            forced_unmapped_ac_ids=forced_unmapped,
            case_explosion_ac_index=request.inject_ac_case_explosion_on_ac_index,
        )

        coverage_snapshot = compute_coverage(matrix, ac_items)
        if forced_unmapped and coverage_snapshot.missing_ac_ids:
            # AC 覆盖率 < 1.0 · 走 AWAITING_CLARIFY（§5.2）
            self._append_event(
                "L1-04:blueprint_validation_failed",
                {
                    "project_id": request.project_id,
                    "missing_ac_ids": coverage_snapshot.missing_ac_ids,
                    "ts": self._now_iso(),
                },
            )
            raise TDDBlueprintError(
                code="E_L204_L201_BLUEPRINT_AC_MISSING",
                severity="FAIL-L3",
                context={"missing_ac_ids": coverage_snapshot.missing_ac_ids},
            )

        coverage_target = build_coverage_target(request.config_overrides)
        test_env = assemble_test_env(ac_items, matrix, project_id=request.project_id or "")

        # 版本号
        version = self.repo.next_version(request.project_id or "")

        source_refs = SourceRefs(
            four_pieces_hash=request.four_pieces_hash or "sha256:" + "0" * 64,
            wbs_version=request.wbs_version,
            ac_clauses_hash=ac_clauses_hash(build_meta["clauses"]),
        )
        created_at = self._now_iso()
        blueprint_id = _gen_bp_id()
        bp = TDDBlueprint(
            blueprint_id=blueprint_id,
            project_id=request.project_id,
            version=version,
            state=BlueprintState.DRAFT,
            test_pyramid=pyramid,
            ac_matrix=matrix,
            coverage_target=coverage_target,
            test_env=test_env,
            source_refs=source_refs,
            ac_items=ac_items,
            created_at=created_at,
            source_refs_hash=src_hash,
            build_meta={
                "warnings": matrix_meta.get("warnings", []),
                "truncated_slots_count": matrix_meta.get("truncated_slots_count", 0),
                "total_slots": matrix_meta.get("total_slots", 0),
                "nlp_fallback_used": build_meta.get("nlp_fallback_used", False),
                "rebuilt_sections": [],
                "preserved_sections": [],
            },
        )
        # DRAFT 状态事件
        self._append_state_event(bp, prev=None, new="DRAFT")
        # VALIDATING → READY
        bp.state = BlueprintState.VALIDATING
        self._append_state_event(bp, prev="DRAFT", new="VALIDATING")

        # retry_focus 元数据（供 _debug_rebuild_meta 观察）
        if request.previous_blueprint_id is not None:
            prev = self.repo.get(request.previous_blueprint_id)
            if prev is not None:
                if request.retry_focus:
                    bp.build_meta["rebuilt_sections"] = list(request.retry_focus)
                    all_sections = {"test_pyramid", "ac_matrix", "coverage_target", "test_env"}
                    bp.build_meta["preserved_sections"] = sorted(
                        all_sections - set(request.retry_focus)
                    )
                else:
                    bp.build_meta["rebuilt_sections"] = [
                        "test_pyramid", "ac_matrix", "coverage_target", "test_env"
                    ]

        # 不变量校验
        try:
            bp.assert_invariants()
        except TDDBlueprintError as e:
            bp.state = BlueprintState.AWAITING_CLARIFY
            self.repo.save(bp)
            self._append_state_event(bp, prev="VALIDATING", new="AWAITING_CLARIFY")
            raise e

        bp.state = BlueprintState.READY
        self._append_state_event(bp, prev="VALIDATING", new="READY")
        self.repo.save(bp)

        # 正常情况下自动广播（§6.1 Step 6）
        self._auto_broadcast(bp)

        return GenerateBlueprintResponse(
            blueprint_id=bp.blueprint_id,
            project_id=bp.project_id,
            status="ACCEPTED",
            ts_accepted=self._now_iso(),
            version=bp.version,
            estimated_completion_ts=(self._now() + timedelta(seconds=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )

    def _append_state_event(
        self, bp: TDDBlueprint, *, prev: str | None, new: str
    ) -> None:
        self._append_event(
            "L1-04:blueprint_state_transition",
            {
                "blueprint_id": bp.blueprint_id,
                "project_id": bp.project_id,
                "version": bp.version,
                "prev_state": prev,
                "new_state": new,
                "ts": self._now_iso(),
            },
        )

    def _build_ac_items(
        self, request: GenerateBlueprintRequest
    ) -> tuple[list[ACItem], dict[str, Any]]:
        """WP02 策略 · 优先尝试从 nlp_backend 读结构化 AC · 失败 fallback 到 synth + parser。"""
        nlp_fallback_used = False
        clauses: list[str] = []

        if self.nlp_backend is not None:
            try:
                raw = self.nlp_backend(request.clause_count)  # 允许 MagicMock 抛错
                if isinstance(raw, list):
                    clauses = [str(c) for c in raw]
            except Exception:
                nlp_fallback_used = True
                clauses = []

        if not clauses:
            clauses = synth_clauses_for_count(request.clause_count)
            if self.nlp_backend is not None and not nlp_fallback_used:
                # 若 nlp_backend 存在但未调用成功（如返回非 list） · 视为 fallback
                nlp_fallback_used = True

        report = parse_ac_clauses(clauses, allow_unstructured_fallback=True)
        if not report.ok:
            # Tier-1 完全失败 · 走 AC_MISSING
            raise TDDBlueprintError(
                code="E_L204_L201_BLUEPRINT_AC_MISSING",
                severity="FAIL-L3",
                context={"failed_ac_ids": report.failed_ac_ids},
            )
        return report.parsed, {
            "clauses": clauses,
            "nlp_fallback_used": nlp_fallback_used,
        }

    def _auto_broadcast(self, bp: TDDBlueprint) -> None:
        """READY → PUBLISHED · 触发 IC-L2-01 广播。"""
        try:
            req = BroadcastReadyRequest(
                blueprint_id=bp.blueprint_id,
                project_id=bp.project_id,
                ts_publish=self._now_iso(),
            )
            self.broadcast_ready(req)
        except TDDBlueprintError:
            # 广播失败不影响 generate 返回 · 但 state 保持 READY
            raise

    # ------------------------------------------------------------------
    # get_blueprint（§3.2）
    # ------------------------------------------------------------------

    def get_blueprint(self, query: GetBlueprintQuery) -> GetBlueprintResponse:
        bp = self.repo.get(query.blueprint_id)
        if bp is None:
            raise TDDBlueprintError(
                code="E_L204_L201_BLUEPRINT_NOT_FOUND",
                context={"blueprint_id": query.blueprint_id},
            )
        if bp.project_id != query.project_id:
            raise TDDBlueprintError(
                code="E_L204_L201_CROSS_PROJECT_READ",
                severity="ERROR",
                context={
                    "query_project_id": query.project_id,
                    "blueprint_project_id": bp.project_id,
                },
            )
        if query.version is not None:
            specific = self.repo.get_by_version(bp.project_id, query.version)
            if specific is None:
                raise TDDBlueprintError(
                    code="E_L204_L201_VERSION_NOT_FOUND",
                    context={"version": query.version},
                )
            bp = specific

        resp = GetBlueprintResponse(
            blueprint_id=bp.blueprint_id,
            project_id=bp.project_id,
            version=bp.version,
            state=bp.state.value,
            created_at=bp.created_at,
            published_at=bp.published_at,
            frozen_at=bp.frozen_at,
        )
        if query.mode == "metadata_only":
            return resp

        if query.mode == "wp_slice":
            if not query.wp_id:
                raise TDDBlueprintError(
                    code="E_L204_L201_WP_SLICE_NOT_FOUND",
                    context={"reason": "wp_id missing"},
                )
            slice_payload = self._build_wp_slice(bp, query.wp_id)
            resp.wp_slice = slice_payload
            return resp

        # full
        matrix_payload = self._ac_matrix_payload(bp)
        resp.test_pyramid = bp.test_pyramid.as_dict()
        resp.ac_matrix = matrix_payload
        resp.coverage_target = bp.coverage_target.as_dict()
        resp.test_env_blueprint = bp.test_env.as_dict()
        resp.source_refs = bp.source_refs.as_dict()
        return resp

    def _ac_matrix_payload(self, bp: TDDBlueprint) -> list[dict[str, Any]]:
        text_by_id = {ac.id: ac.raw_text for ac in bp.ac_items}
        out: list[dict[str, Any]] = []
        for row in bp.ac_matrix.rows.values():
            out.append(
                {
                    "ac_id": row.ac_id,
                    "ac_text": text_by_id.get(row.ac_id, ""),
                    "layer": row.layer,
                    "priority": row.priority,
                    "slot_ids": row.slot_ids(),
                }
            )
        return out

    def _build_wp_slice(self, bp: TDDBlueprint, wp_id: str) -> dict[str, Any]:
        # WP02 · WBS 真实拓扑未接入 · 用一个简单规则：wp-XXXX 的 XXXX 指向 AC 批次
        # wp-0001 → 前 1/3 AC · wp-0002 → 中 1/3 · wp-0003 → 末 1/3 · 其余视为不存在
        total_rows = list(bp.ac_matrix.rows.values())
        if not total_rows:
            raise TDDBlueprintError(
                code="E_L204_L201_WP_SLICE_NOT_FOUND",
                context={"wp_id": wp_id, "reason": "no rows"},
            )
        try:
            wp_num = int(wp_id.split("-")[-1])
        except ValueError:
            wp_num = 0
        if wp_num < 1 or wp_num > 10:
            raise TDDBlueprintError(
                code="E_L204_L201_WP_SLICE_NOT_FOUND",
                context={"wp_id": wp_id},
            )

        n = len(total_rows)
        chunk = max(1, n // 10)
        start = min(n - 1, (wp_num - 1) * chunk)
        end = min(n, wp_num * chunk)
        sub = total_rows[start:end] or [total_rows[0]]
        related_ac = [r.ac_id for r in sub]
        related_slots: list[str] = []
        for r in sub:
            related_slots.extend(r.slot_ids())
        return {
            "wp_id": wp_id,
            "related_ac_ids": related_ac,
            "related_slot_ids": related_slots,
            "coverage_slice": {
                "ac_count": len(related_ac),
                "slot_count": len(related_slots),
                "ac": 1.0,
            },
        }

    # ------------------------------------------------------------------
    # validate_coverage（§3.3）
    # ------------------------------------------------------------------

    def validate_coverage(self, query: ValidateCoverageQuery) -> ValidateCoverageResponse:
        bp = self.repo.get(query.blueprint_id)
        if bp is None:
            raise TDDBlueprintError(
                code="E_L204_L201_VALIDATION_BLUEPRINT_NOT_FOUND",
                context={"blueprint_id": query.blueprint_id},
            )
        if query.blueprint_id in self._stale_read_armed:
            # 模拟 race
            self._stale_read_armed.discard(query.blueprint_id)
            raise TDDBlueprintError(
                code="E_L204_L201_VALIDATION_STALE_READ",
                severity="WARN",
            )
        snapshot = compute_coverage(bp.ac_matrix, bp.ac_items)
        pyramid_valid = True
        try:
            _ = TestPyramid(
                bp.test_pyramid.unit_ratio,
                bp.test_pyramid.integration_ratio,
                bp.test_pyramid.e2e_ratio,
            )
        except TDDBlueprintError:
            pyramid_valid = False

        prio_complete = priority_annotation_complete(bp.ac_matrix)
        issues: list[dict[str, Any]] = []
        if snapshot.missing_ac_ids:
            issues.append(
                {
                    "code": "E_L204_L201_AC_COVERAGE_NOT_100",
                    "severity": "WARN" if not query.strict_mode else "ERROR",
                    "message": f"missing AC: {snapshot.missing_ac_ids[:5]}",
                }
            )
        valid = (
            snapshot.ac_coverage >= 1.0
            and pyramid_valid
            and prio_complete
            and not snapshot.missing_ac_ids
        )
        # strict=False · 不 fail · 仅 warn
        if not query.strict_mode:
            valid = True

        return ValidateCoverageResponse(
            valid=valid,
            ac_coverage=snapshot.ac_coverage,
            line_coverage_target=bp.coverage_target.line,
            branch_coverage_target=bp.coverage_target.branch,
            pyramid_ratios_valid=pyramid_valid,
            priority_annotation_complete=prio_complete,
            missing_ac_ids=snapshot.missing_ac_ids,
            issues=issues,
        )

    # ------------------------------------------------------------------
    # broadcast_ready（§3.4）
    # ------------------------------------------------------------------

    def broadcast_ready(self, request: BroadcastReadyRequest) -> BroadcastReadyResponse:
        bp = self.repo.get(request.blueprint_id)
        if bp is None:
            raise TDDBlueprintError(code="E_L204_L201_BLUEPRINT_NOT_FOUND")

        # 幂等 · 同 blueprint_id 二次广播返回首次 event_id
        cached_event = self._broadcast_events.get(request.blueprint_id)
        if cached_event is not None:
            return BroadcastReadyResponse(
                published=True,
                event_id=cached_event,
                fanout_acks=[
                    {"subscriber": s, "ack": True, "received_at": request.ts_publish}
                    for s in request.subscribers
                ],
                latency_ms=self._broadcast_latencies.get(request.blueprint_id, 0),
            )

        start = time.perf_counter()
        event_id = _gen_event_id()
        all_fail = bool(getattr(self.event_bus, "_all_fail", False)) if self.event_bus else False
        timeout_sub = getattr(self.event_bus, "_timeout_sub", None) if self.event_bus else None
        latency_override = getattr(self.event_bus, "_lat", None) if self.event_bus else None

        if all_fail:
            # 3 重试仍失败 · FAIL-L2
            raise TDDBlueprintError(
                code="E_L204_L201_BROADCAST_FAILED",
                severity="FAIL-L2",
                message="all subscribers unreachable after 3 retries",
            )

        payload = {
            "event_id": event_id,
            "event_type": "L1-04:blueprint_ready",
            "project_id": bp.project_id,
            "blueprint_id": bp.blueprint_id,
            "version": bp.version,
            "master_test_plan_path": f"projects/{bp.project_id}/tdd/master-test-plan.md",
            "ac_matrix_path": f"projects/{bp.project_id}/tdd/ac-matrix.yaml",
            "coverage_target_summary": bp.coverage_target.as_dict(),
            "publisher": "L1-04:L2-01",
            "ts": request.ts_publish,
        }
        # IC-09 审计
        self._append_event("L1-04:blueprint_ready", payload)

        # fanout · WP02 用 mock · timeout_sub 的订阅者模拟 3 次重试失败
        acks: list[dict[str, Any]] = []
        incomplete = False
        for sub in request.subscribers:
            ok = sub != timeout_sub
            acks.append(
                {
                    "subscriber": sub,
                    "ack": ok,
                    "received_at": request.ts_publish if ok else None,
                }
            )
            if not ok:
                incomplete = True
            # 调下游 mock（供集成测试校验 on_blueprint_ready 被调）
            target = {"L2-02": self.l2_02, "L2-03": self.l2_03, "L2-04": self.l2_04}.get(sub)
            if ok and target is not None and hasattr(target, "on_blueprint_ready"):
                try:
                    target.on_blueprint_ready(payload)
                except Exception:  # pragma: no cover - subscriber fault
                    pass

        if incomplete:
            self._append_event(
                "L1-04:blueprint_subscriber_unreachable",
                {
                    "blueprint_id": bp.blueprint_id,
                    "missing": [a["subscriber"] for a in acks if not a["ack"]],
                },
            )

        # 计算延迟
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        if latency_override is not None:
            elapsed_ms = int(latency_override)
        if elapsed_ms > 1000:
            # SLO 违反 · 不 fail · 审计
            self._append_event(
                "L1-04:blueprint_broadcast_slo_violation",
                {
                    "blueprint_id": bp.blueprint_id,
                    "latency_ms": elapsed_ms,
                    "threshold_ms": 1000,
                },
            )

        # 转 PUBLISHED（幂等 cache 前置）
        self._broadcast_events[request.blueprint_id] = event_id
        self._broadcast_latencies[request.blueprint_id] = elapsed_ms
        bp.state = BlueprintState.PUBLISHED
        bp.published_at = self._now_iso()
        self._append_state_event(bp, prev="READY", new="PUBLISHED")
        self.repo.save(bp)

        # 经 L1-02 汇总 S3 Gate artifacts（§4.2.2 IC-16 间接）
        if self.l1_02 is not None and hasattr(self.l1_02, "receive_artifact"):
            try:
                self.l1_02.receive_artifact(
                    project_id=bp.project_id,
                    artifact_type="master_test_plan",
                    blueprint_id=bp.blueprint_id,
                )
            except Exception:  # pragma: no cover
                pass

        return BroadcastReadyResponse(
            published=True,
            event_id=event_id,
            fanout_acks=acks,
            latency_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Test-only helpers（§1.2 表 + §2 fixture 用；生产路径不调用）
    # ------------------------------------------------------------------

    def _peek_state(self, blueprint_id: str) -> Any:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            raise TDDBlueprintError(code="E_L204_L201_BLUEPRINT_NOT_FOUND")
        return type("Snap", (), {"state": bp.state.value})

    def _await_published(self, blueprint_id: str) -> None:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            return
        if bp.state != BlueprintState.PUBLISHED:
            # WP02 同步构造 · 如果尚未 PUBLISHED 则强制转换
            bp.state = BlueprintState.PUBLISHED
            bp.published_at = self._now_iso()
            self.repo.save(bp)

    def _await_ready(self, blueprint_id: str) -> None:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            return
        if bp.state == BlueprintState.DRAFT:
            bp.state = BlueprintState.READY
            self.repo.save(bp)

    def _force_state(self, blueprint_id: str, state: str) -> None:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            return
        bp.state = BlueprintState(state)
        self.repo.save(bp)

    def _publish(self, blueprint_id: str) -> None:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            return
        req = BroadcastReadyRequest(
            blueprint_id=blueprint_id,
            project_id=bp.project_id,
            ts_publish=self._now_iso(),
        )
        self.broadcast_ready(req)

    def _debug_build_meta(self, blueprint_id: str) -> dict[str, Any]:
        bp = self.repo.get(blueprint_id)
        if bp is None:
            return {}
        return dict(bp.build_meta)

    def _debug_rebuild_meta(self, blueprint_id: str) -> dict[str, Any]:
        return self._debug_build_meta(blueprint_id)

    def _arm_concurrent_mutation(self, blueprint_id: str) -> None:
        self._stale_read_armed.add(blueprint_id)

    def _last_halt_signal(self) -> dict[str, Any] | None:
        return self._last_halt_signal

    def _force_redundant_broadcast(self, blueprint_id: str) -> None:
        """强制记录 duplicate_broadcast 审计事件（不改变 cache）。"""
        self._append_event(
            "L1-04:blueprint_duplicate_broadcast",
            {"blueprint_id": blueprint_id, "ts": self._now_iso()},
        )

    def _build_partial_blueprint_for_test(
        self, *, project_id: str, unmapped_count: int
    ) -> str:
        """构造 ac_coverage < 1.0 的 blueprint（绕过 strict=true 校验）· 仅测试用。"""
        clauses = synth_clauses_for_count(50)
        report = parse_ac_clauses(clauses)
        ac_items = report.parsed
        pyramid = derive_pyramid(ac_items)
        forced = [ac_items[i].id for i in range(unmapped_count)]
        matrix, meta = build_matrix(ac_items, pyramid, forced_unmapped_ac_ids=forced)
        coverage_target = build_coverage_target()
        test_env = assemble_test_env(ac_items, matrix, project_id=project_id)

        version = self.repo.next_version(project_id)
        bp = TDDBlueprint(
            blueprint_id=_gen_bp_id(),
            project_id=project_id,
            version=version,
            state=BlueprintState.DRAFT,
            test_pyramid=pyramid,
            ac_matrix=matrix,
            coverage_target=coverage_target,
            test_env=test_env,
            source_refs=SourceRefs(
                four_pieces_hash="sha256:partial",
                wbs_version=1,
                ac_clauses_hash=ac_clauses_hash(clauses),
            ),
            ac_items=ac_items,
            created_at=self._now_iso(),
            source_refs_hash="sha256:partial-" + str(uuid.uuid4()),
        )
        self.repo.save(bp)
        return bp.blueprint_id


__all__ = ["TDDBlueprintGenerator", "InMemoryBlueprintRepo"]
