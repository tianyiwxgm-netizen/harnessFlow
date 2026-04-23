"""L2-01 启动 5 阶段加载器.

Stages:
  1. Load registry.yaml (filesystem)
  2. Parse capability_points / subagents / tools
  3. Validate + inject builtin fallback（若缺 · 留给后续 hook）
  4. Load ledger.jsonl                      (Task 01.3)
  5. Create snapshot-{ts}.yaml 原子快照     (Task 01.3)

错误码:
  E_REG_FILE_NOT_FOUND     — registry.yaml 不存在
  E_REG_YAML_PARSE         — YAML 语法错
  E_REG_NO_SCHEMA_POINTER  — capability 缺 schema_pointer
  E_REG_VALIDATION         — Pydantic 层校验失败（含 PM-09 ≥2 + builtin_fallback）

源:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md §6
  - docs/superpowers/plans/Dev-γ-impl.md §3 Task 01.2
"""
from __future__ import annotations

import pathlib
import time

import yaml
from pydantic import ValidationError

from .schemas import (
    CapabilityPoint,
    RegistrySnapshot,
    SkillSpec,
    SubagentEntry,
    ToolEntry,
)


class RegistryLoadError(Exception):
    """L2-01 加载期所有致命错误 · `code` 属性携带错误码."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class RegistryLoader:
    """启动加载器 · 读 `projects/<pid>/skills/registry-cache/registry.yaml`.

    单实例单次 load · 可 reload() 重复调用（热更新路径由 fs_watcher 驱动 · Task 01.5）.
    """

    def __init__(self, project_root: pathlib.Path) -> None:
        self.project_root = pathlib.Path(project_root)
        self.yaml_path = self.project_root / "skills" / "registry-cache" / "registry.yaml"

    def load(self) -> RegistrySnapshot:
        raw = self._stage1_read_yaml()
        caps = self._stage2_parse_capabilities(raw.get("capability_points") or {})
        subs = self._stage2_parse_subagents(raw.get("subagents") or {})
        tools = self._stage2_parse_tools(raw.get("tools") or {})
        caps = self._stage3_validate_and_fill(caps)
        ledger_idx = self._stage4_load_ledger()
        snap = RegistrySnapshot(
            version=str(raw.get("version", "0")),
            capability_points=caps,
            subagents=subs,
            tools=tools,
            loaded_at_ts_ns=time.time_ns(),
            ledger_index=ledger_idx,
        )
        self._stage5_write_snapshot(snap)
        return snap

    # ------------------------------------------------------------------ Stage 1
    def _stage1_read_yaml(self) -> dict:
        if not self.yaml_path.exists():
            raise RegistryLoadError("E_REG_FILE_NOT_FOUND", str(self.yaml_path))
        try:
            data = yaml.safe_load(self.yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise RegistryLoadError("E_REG_YAML_PARSE", str(e)) from e
        return data or {}

    # ------------------------------------------------------------------ Stage 2
    def _stage2_parse_capabilities(self, raw: dict) -> dict[str, CapabilityPoint]:
        out: dict[str, CapabilityPoint] = {}
        for name, body in raw.items():
            if not body.get("schema_pointer"):
                raise RegistryLoadError("E_REG_NO_SCHEMA_POINTER", f"capability {name!r}")
            try:
                candidates = [SkillSpec(**c) for c in body.get("candidates", [])]
                out[name] = CapabilityPoint(
                    name=name,
                    description=body.get("description", ""),
                    schema_pointer=body["schema_pointer"],
                    candidates=candidates,
                )
            except ValidationError as e:
                raise RegistryLoadError("E_REG_VALIDATION", f"{name}: {e}") from e
            except ValueError as e:
                # model_validator 抛的 ValueError（PM-09 约束）也归 E_REG_VALIDATION
                raise RegistryLoadError("E_REG_VALIDATION", f"{name}: {e}") from e
        return out

    def _stage2_parse_subagents(self, raw: dict) -> dict[str, SubagentEntry]:
        try:
            return {k: SubagentEntry(**v) for k, v in raw.items()}
        except ValidationError as e:
            raise RegistryLoadError("E_REG_VALIDATION", f"subagents: {e}") from e

    def _stage2_parse_tools(self, raw: dict) -> dict[str, ToolEntry]:
        try:
            return {k: ToolEntry(**v) for k, v in raw.items()}
        except ValidationError as e:
            raise RegistryLoadError("E_REG_VALIDATION", f"tools: {e}") from e

    # ------------------------------------------------------------------ Stage 3
    def _stage3_validate_and_fill(
        self, caps: dict[str, CapabilityPoint]
    ) -> dict[str, CapabilityPoint]:
        """已由 CapabilityPoint.model_validator 校验 PM-09（≥2 + builtin_fallback）.

        本阶段预留给"自动注入内建兜底"的未来逻辑（若 registry.yaml 没给出但允许自动补全）.
        当前严格策略：不自动补 · 要求上游（registry.yaml 作者）必须提供 builtin_fallback.
        """
        return caps

    # ------------------------------------------------------------------ Stage 4
    def _stage4_load_ledger(self) -> dict[str, "LedgerEntry"]:
        """从 ledger.jsonl 恢复 success/failure 历史 · key = 'capability|skill_id'."""
        import json

        from .schemas import LedgerEntry

        path = self.project_root / "skills" / "registry-cache" / "ledger.jsonl"
        idx: dict[str, LedgerEntry] = {}
        if not path.exists():
            return idx
        for ln_no, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            try:
                rec = LedgerEntry(**json.loads(raw_line))
            except (ValidationError, ValueError, json.JSONDecodeError) as e:
                raise RegistryLoadError(
                    "E_REG_VALIDATION",
                    f"ledger.jsonl line {ln_no}: {e}",
                ) from e
            # 若同 (capability, skill_id) 多条 · 后写覆盖前写（最新 attempt）.
            idx[f"{rec.capability}|{rec.skill_id}"] = rec
        return idx

    # ------------------------------------------------------------------ Stage 5
    def _stage5_write_snapshot(self, snap: RegistrySnapshot) -> None:
        """落盘 snapshot-{ts}.yaml 作为 last-known-good 兜底（启动加载完成后即写）."""
        out_path = (
            self.project_root
            / "skills"
            / "registry-cache"
            / f"snapshot-{snap.loaded_at_ts_ns}.yaml"
        )
        body = snap.model_dump(mode="json")
        out_path.write_text(yaml.safe_dump(body, sort_keys=True), encoding="utf-8")
