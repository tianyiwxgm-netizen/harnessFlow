"""L2-01 Skill 注册表 · 共 ~40 TC.

文档参照:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md
  - docs/3-2-Solution-TDD/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表-tests.md
  - docs/superpowers/plans/Dev-γ-impl.md §3

错误码覆盖:
  E_REG_MISSING_CAPABILITY / E_REG_SINGLE_CANDIDATE / E_REG_NO_SCHEMA_POINTER /
  E_REG_RELOAD_CONFLICT / E_REG_FILE_NOT_FOUND
"""
from __future__ import annotations

import pytest


class TestRegistrySchemas:
    """Task 01.1 · Pydantic v2 schemas · PM-09 ≥2 candidates + builtin_fallback 硬约束."""

    def test_skill_spec_requires_skill_id(self):
        from app.l1_05.registry.schemas import SkillSpec

        with pytest.raises(ValueError):
            SkillSpec(skill_id="", availability=True, cost_usd=0.0, timeout_s=30)

    def test_capability_point_rejects_single_candidate(self):
        from app.l1_05.registry.schemas import CapabilityPoint, SkillSpec

        with pytest.raises(ValueError, match="at_least_2_candidates"):
            CapabilityPoint(
                name="x",
                description="d",
                schema_pointer="s.json",
                candidates=[
                    SkillSpec(skill_id="a", availability=True, cost_usd=0.0, timeout_s=30),
                ],
            )

    def test_capability_point_rejects_missing_builtin_fallback(self):
        from app.l1_05.registry.schemas import CapabilityPoint, SkillSpec

        with pytest.raises(ValueError, match="builtin_fallback_required"):
            CapabilityPoint(
                name="x",
                description="d",
                schema_pointer="s.json",
                candidates=[
                    SkillSpec(skill_id="a", availability=True, cost_usd=0.0, timeout_s=30),
                    SkillSpec(skill_id="b", availability=True, cost_usd=0.0, timeout_s=30),
                ],
            )

    def test_capability_point_accepts_valid_with_builtin(self):
        """Positive case · 2 candidates with one builtin_fallback = 通过校验."""
        from app.l1_05.registry.schemas import CapabilityPoint, SkillSpec

        cp = CapabilityPoint(
            name="write_test",
            description="TDD red tests",
            schema_pointer="s.json",
            candidates=[
                SkillSpec(skill_id="a", availability=True, cost_usd=0.01, timeout_s=30),
                SkillSpec(
                    skill_id="builtin:a_min",
                    availability=True,
                    cost_usd=0.0,
                    timeout_s=10,
                    is_builtin_fallback=True,
                ),
            ],
        )
        assert len(cp.candidates) == 2
        assert any(c.is_builtin_fallback for c in cp.candidates)

    def test_subagent_entry_role_enum(self):
        from app.l1_05.registry.schemas import SubagentEntry

        e = SubagentEntry(
            role="verifier",
            tool_whitelist=["Read"],
            timeout_s=1200,
            schema_pointer="v.json",
        )
        assert e.role == "verifier"

    def test_subagent_entry_rejects_unknown_role(self):
        from app.l1_05.registry.schemas import SubagentEntry

        with pytest.raises(ValueError):
            SubagentEntry(
                role="hacker",  # type: ignore[arg-type]
                tool_whitelist=["Read"],
                timeout_s=1200,
                schema_pointer="v.json",
            )

    def test_tool_entry_defaults_to_atomic(self):
        from app.l1_05.registry.schemas import ToolEntry

        te = ToolEntry()
        assert te.kind == "atomic"

    def test_ledger_entry_rejects_negative_counts(self):
        from app.l1_05.registry.schemas import LedgerEntry

        with pytest.raises(ValueError):
            LedgerEntry(
                capability="x",
                skill_id="y",
                success_count=-1,
                failure_count=0,
                last_attempt_ts=0,
                failure_reason=None,
            )

    def test_ledger_entry_accepts_zero_counts(self):
        from app.l1_05.registry.schemas import LedgerEntry

        e = LedgerEntry(
            capability="x",
            skill_id="y",
            success_count=0,
            failure_count=0,
            last_attempt_ts=1_700_000_000,
            failure_reason=None,
        )
        assert e.success_count == 0 and e.failure_count == 0

    def test_registry_snapshot_fields(self):
        from app.l1_05.registry.schemas import RegistrySnapshot

        snap = RegistrySnapshot(
            version="1.0",
            capability_points={},
            subagents={},
            tools={},
            loaded_at_ts_ns=0,
        )
        assert snap.version == "1.0"


class TestLoaderStages1to3:
    """Task 01.2 · RegistryLoader 启动 5 阶段中的前 3 阶段（fs scan / yaml parse / validate）."""

    def test_stage1_missing_file_raises_E_REG_FILE_NOT_FOUND(self, tmp_project):
        from app.l1_05.registry.loader import RegistryLoadError, RegistryLoader

        loader = RegistryLoader(project_root=tmp_project)
        with pytest.raises(RegistryLoadError, match="E_REG_FILE_NOT_FOUND"):
            loader.load()

    def test_stage2_parses_capability_points_from_fixtures(self, tmp_project, fixtures_dir):
        import shutil

        from app.l1_05.registry.loader import RegistryLoader

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        assert "write_test" in snap.capability_points
        assert "review_code" in snap.capability_points
        assert snap.capability_points["write_test"].schema_pointer == "schemas/skill/write_test.v1.json"

    def test_stage2_parses_subagents_and_tools(self, tmp_project, fixtures_dir):
        import shutil

        from app.l1_05.registry.loader import RegistryLoader

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        assert "verifier" in snap.subagents
        assert snap.subagents["verifier"].tool_whitelist == ["Read", "Glob", "Grep", "Bash"]
        assert "Read" in snap.tools
        assert snap.tools["Read"].kind == "atomic"

    def test_stage3_reject_capability_without_schema_pointer(self, tmp_path):
        from app.l1_05.registry.loader import RegistryLoadError, RegistryLoader

        cache = tmp_path / "skills" / "registry-cache"
        cache.mkdir(parents=True)
        (cache / "registry.yaml").write_text(
            "version: '1.0'\n"
            "capability_points:\n"
            "  x:\n"
            "    description: d\n"
            "    schema_pointer: ''\n"
            "    candidates: []\n",
            encoding="utf-8",
        )
        loader = RegistryLoader(project_root=tmp_path)
        with pytest.raises(RegistryLoadError, match="E_REG_NO_SCHEMA_POINTER"):
            loader.load()

    def test_stage3_capability_with_builtin_fallback_passes(self, tmp_project, fixtures_dir):
        """fixture 里每 capability 都有 builtin_fallback · 应 Stage 3 通过."""
        import shutil

        from app.l1_05.registry.loader import RegistryLoader

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        for cp in snap.capability_points.values():
            assert any(c.is_builtin_fallback for c in cp.candidates), (
                f"capability {cp.name} missing builtin_fallback"
            )

    def test_stage2_invalid_yaml_raises_E_REG_YAML_PARSE(self, tmp_path):
        from app.l1_05.registry.loader import RegistryLoadError, RegistryLoader

        cache = tmp_path / "skills" / "registry-cache"
        cache.mkdir(parents=True)
        (cache / "registry.yaml").write_text("version: 1.0\n  bad indent: :\n", encoding="utf-8")
        loader = RegistryLoader(project_root=tmp_path)
        with pytest.raises(RegistryLoadError, match="E_REG_YAML_PARSE"):
            loader.load()

    def test_stage3_rejects_single_candidate_without_builtin(self, tmp_path):
        """PM-09 · 单候选 + 无 builtin → CapabilityPoint model_validator 触发 · 包装成 E_REG_VALIDATION."""
        from app.l1_05.registry.loader import RegistryLoadError, RegistryLoader

        cache = tmp_path / "skills" / "registry-cache"
        cache.mkdir(parents=True)
        (cache / "registry.yaml").write_text(
            "version: '1.0'\n"
            "capability_points:\n"
            "  x:\n"
            "    description: d\n"
            "    schema_pointer: s.json\n"
            "    candidates:\n"
            "      - skill_id: only_one\n"
            "        availability: true\n"
            "        cost_usd: 0.0\n"
            "        timeout_s: 10\n",
            encoding="utf-8",
        )
        loader = RegistryLoader(project_root=tmp_path)
        with pytest.raises(RegistryLoadError, match="E_REG_VALIDATION|at_least_2_candidates"):
            loader.load()

    def test_load_startup_within_500ms_slo(self, tmp_project, fixtures_dir):
        """SLO · 启动加载 P99 ≤ 500ms（样例 registry 应远低于此）."""
        import shutil
        import time

        from app.l1_05.registry.loader import RegistryLoader

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        loader = RegistryLoader(project_root=tmp_project)
        t0 = time.perf_counter()
        loader.load()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500.0, f"startup load exceeded 500ms SLO: {elapsed_ms:.1f}ms"


class TestLedgerAndQuery:
    """Task 01.3 · Loader Stage 4-5 + query_api 4 接口."""

    def _prepare(self, tmp_project, fixtures_dir, *, with_ledger=True):
        import shutil

        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        if with_ledger:
            shutil.copy(fixtures_dir / "ledger_sample.jsonl", cache / "ledger.jsonl")
        return cache

    def test_stage4_loads_ledger_entries(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader

        self._prepare(tmp_project, fixtures_dir)
        snap = RegistryLoader(project_root=tmp_project).load()
        rec = snap.ledger_get("write_test", "superpowers:tdd-workflow")
        assert rec is not None
        assert rec.success_count == 12
        assert rec.failure_count == 1

    def test_stage4_handles_missing_ledger_as_empty(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        assert snap.ledger_index == {}

    def test_stage5_writes_snapshot_file(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader

        cache = self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        RegistryLoader(project_root=tmp_project).load()
        snapshots = list(cache.glob("snapshot-*.yaml"))
        assert len(snapshots) >= 1
        assert snapshots[0].stat().st_size > 0

    def test_query_candidates_returns_builtin_fallback_last(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        cands = api.query_candidates("write_test")
        assert len(cands) == 2
        assert cands[-1].is_builtin_fallback, "builtin_fallback 必须排末尾"
        assert cands[0].skill_id == "superpowers:tdd-workflow"

    def test_query_candidates_unknown_raises_E_REG_MISSING_CAPABILITY(
        self, tmp_project, fixtures_dir
    ):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import CapabilityNotFoundError, RegistryQueryAPI

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        with pytest.raises(CapabilityNotFoundError, match="E_REG_MISSING_CAPABILITY"):
            api.query_candidates("no_such_capability")

    def test_query_subagent_returns_entry(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        v = api.query_subagent("verifier")
        assert v.role == "verifier"
        assert v.timeout_s == 1200

    def test_query_subagent_unknown_raises(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI, SubagentNotFoundError

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        with pytest.raises(SubagentNotFoundError):
            api.query_subagent("hacker")

    def test_query_tool_atomic(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        assert api.query_tool("Read").kind == "atomic"

    def test_query_schema_pointer(self, tmp_project, fixtures_dir):
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        assert api.query_schema_pointer("write_test") == "schemas/skill/write_test.v1.json"

    def test_swap_replaces_snapshot_atomically(self, tmp_project, fixtures_dir):
        """Registry hot-reload · swap() 原子替换 · 旧查询到新 snapshot."""
        from app.l1_05.registry.loader import RegistryLoader
        from app.l1_05.registry.query_api import RegistryQueryAPI
        from app.l1_05.registry.schemas import RegistrySnapshot

        self._prepare(tmp_project, fixtures_dir, with_ledger=False)
        snap1 = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap1)
        assert "write_test" in api.snapshot.capability_points

        empty = RegistrySnapshot(
            version="0",
            capability_points={},
            subagents={},
            tools={},
            loaded_at_ts_ns=0,
        )
        api.swap(empty)
        from app.l1_05.registry.query_api import CapabilityNotFoundError
        with pytest.raises(CapabilityNotFoundError):
            api.query_candidates("write_test")
