"""L2-07 模板引擎 · 正向用例。

对齐 docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-07-产出物模板引擎-tests.md §2
+ tech §3.1 (render_template / list_available_templates / get_template_version / validate_slots)。

TC-L102-L207-001~013 共 13 条 · arrange-act-assert 三段式。
"""
from __future__ import annotations

from typing import Any

import pytest

from app.project_lifecycle.template_engine.engine import TemplateEngine
from app.project_lifecycle.template_engine.schemas import RenderedOutput, ValidationResult


@pytest.fixture
def sut(template_dir_real, mock_event_bus) -> TemplateEngine:
    """真实模板目录加载的 TemplateEngine。"""
    return TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=mock_event_bus,
    )


class TestL2_07_TemplateEngine:
    """每个 public 方法 + 代表性 kind 至少 1 正向用例（tech §3.5 5 L2 调用方）。"""

    def test_TC_L102_L207_001_render_kickoff_goal_returns_full_record(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        slots: dict[str, Any] = {
            "user_utterance": "做一个内部 Wiki 系统",
            "goals": ["上线内部可用", "支持 markdown"],
            "deadline": "2026-06-30",
        }
        out: RenderedOutput = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="kickoff.goal", slots=slots, caller_l2="L2-02",
        )
        assert out.request_id == mock_request_id
        assert out.template_id == "kickoff.goal.v1.0"
        assert out.template_version == "v1.0"
        assert out.output.startswith("---")  # frontmatter
        assert "template_id: kickoff.goal.v1.0" in out.output
        assert out.body_sha256 and len(out.body_sha256) == 64
        assert out.slots_hash and len(out.slots_hash) >= 32
        assert out.lines > 0
        assert out.rendered_at
        assert out.engine_version

    def test_TC_L102_L207_002_render_kickoff_scope_injects_list_slots(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        slots: dict[str, Any] = {
            "scope_items": ["认证", "文章 CRUD", "全文搜索"],
            "out_of_scope": ["付费订阅", "APP 端"],
            "constraints": ["单人开发", "2 周内 MVP"],
        }
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="kickoff.scope", slots=slots, caller_l2="L2-02",
        )
        assert "认证" in out.output
        assert "文章 CRUD" in out.output
        assert "付费订阅" in out.output
        assert out.frontmatter["template_id"] == "kickoff.scope.v1.0"

    def test_TC_L102_L207_003_render_fourset_prd_by_L2_03(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        slots: dict[str, Any] = {
            "problem_statement": "用户反馈搜索慢",
            "success_metrics": [{"name": "P95", "target": "< 200ms"}],
            "user_stories": ["作为用户，我想秒级找到文章"],
        }
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="fourset.prd", slots=slots, caller_l2="L2-03",
        )
        assert out.template_id == "fourset.prd.v1.0"
        assert "doc_type" in out.frontmatter

    def test_TC_L102_L207_004_render_pmp_scope_full_audit_chain(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        slots: dict[str, Any] = {
            "scope_statement": "后端 API 重构",
            "scope_items": [
                {"name": "auth", "description": "重写登录", "owner": "A", "duration_days": 3},
                {"name": "article", "description": "CRUD", "owner": "B", "duration_days": 5},
            ],
            "out_of_scope": ["前端改版"],
        }
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="pmp.scope", slots=slots, caller_l2="L2-04",
        )
        # IC-09 审计事件必发
        matching = [
            e for e in mock_event_bus.emitted_events()
            if e["event_type"] == "L1-02/L2-07:template_rendered"
            and e["project_id"] == mock_project_id
        ]
        assert len(matching) == 1
        payload = matching[0]
        assert payload["template_id"] == "pmp.scope.v1.0"
        assert payload["caller_l2"] == "L2-04"
        assert payload["slots_hash"] == out.slots_hash
        assert payload["output_sha256"] == out.body_sha256

    def test_TC_L102_L207_005_render_idempotent_same_slots_same_hash(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """I-L207-01 幂等 · 同 slots 两次渲染 output_sha256 相等。"""
        slots: dict[str, Any] = {
            "scope_statement": "数据迁移项目",
            "scope_items": [{"name": "schema", "description": "建表", "owner": "X", "duration_days": 2}],
            "out_of_scope": [],
        }
        out1 = sut.render_template(
            request_id="req-1", project_id=mock_project_id, kind="pmp.scope",
            slots=slots, caller_l2="L2-04",
        )
        out2 = sut.render_template(
            request_id="req-2", project_id=mock_project_id, kind="pmp.scope",
            slots=slots, caller_l2="L2-04",
        )
        assert out1.body_sha256 == out2.body_sha256
        assert out1.slots_hash == out2.slots_hash

    def test_TC_L102_L207_006_frontmatter_template_id_injected(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """I-L207-03 · 渲染后 frontmatter 必含 template_id/version/rendered_at。"""
        slots: dict[str, Any] = {"budget_total": 100000, "cost_breakdown": []}
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="pmp.cost", slots=slots, caller_l2="L2-04",
        )
        fm = out.frontmatter
        assert fm["template_id"] == "pmp.cost.v1.0"
        assert fm["template_version"] == "v1.0"
        assert fm["rendered_at"]
        assert "doc_id" in fm
        assert "doc_type" in fm

    def test_TC_L102_L207_007_slots_hash_canonicalized(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """slots_hash 规范化（key 顺序不敏感）。"""
        slots_a: dict[str, Any] = {"goals": ["a", "b"], "user_utterance": "x", "deadline": "2026-06-30"}
        slots_b: dict[str, Any] = {"deadline": "2026-06-30", "user_utterance": "x", "goals": ["a", "b"]}
        out_a = sut.render_template(
            request_id="r1", project_id=mock_project_id, kind="kickoff.goal",
            slots=slots_a, caller_l2="L2-02",
        )
        out_b = sut.render_template(
            request_id="r2", project_id=mock_project_id, kind="kickoff.goal",
            slots=slots_b, caller_l2="L2-02",
        )
        assert out_a.slots_hash == out_b.slots_hash

    def test_TC_L102_L207_008_render_togaf_adr(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        slots: dict[str, Any] = {
            "title": "Use PostgreSQL over MySQL",
            "context": "大量 JSON 字段场景",
            "decision": "选 Postgres",
            "alternatives": ["MySQL", "SQLite"],
            "consequences": ["运维复杂 +1", "JSON 查询 +1"],
        }
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="togaf.adr", slots=slots, caller_l2="L2-05",
        )
        assert "Use PostgreSQL over MySQL" in out.output
        assert out.template_id == "togaf.adr.v1.0"

    def test_TC_L102_L207_009_render_closing_lessons_learned(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        slots: dict[str, Any] = {
            "what_went_well": ["按时交付"],
            "what_went_wrong": ["需求变更 3 次"],
            "action_items": ["需求冻结机制"],
        }
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="closing.lessons_learned", slots=slots, caller_l2="L2-06",
        )
        assert "按时交付" in out.output

    def test_TC_L102_L207_010_list_available_templates_returns_all_29(
        self, sut: TemplateEngine,
    ) -> None:
        kinds = sut.list_available_templates()
        assert isinstance(kinds, list)
        assert len(kinds) >= 29
        expected = {
            "kickoff.goal", "kickoff.scope",
            "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
            "pmp.scope", "pmp.cost", "pmp.risk",
            "togaf.preliminary", "togaf.phase_a", "togaf.adr",
            "closing.lessons_learned", "closing.delivery_manifest",
        }
        assert expected.issubset(set(kinds))

    def test_TC_L102_L207_011_get_template_version_returns_semver(
        self, sut: TemplateEngine,
    ) -> None:
        assert sut.get_template_version("pmp.scope") == "v1.0"
        assert sut.get_template_version("nonexistent.kind") is None

    def test_TC_L102_L207_012_validate_slots_returns_ok_for_valid(
        self, sut: TemplateEngine,
    ) -> None:
        slots: dict[str, Any] = {
            "user_utterance": "build wiki",
            "goals": ["ship"],
            "deadline": "2026-06-30",
        }
        result: ValidationResult = sut.validate_slots("kickoff.goal", slots)
        assert result.is_ok()
        assert result.error_code is None

    def test_TC_L102_L207_013_validate_slots_returns_fail_for_missing_required(
        self, sut: TemplateEngine,
    ) -> None:
        slots: dict[str, Any] = {"goals": ["only goals"]}  # 缺 user_utterance / deadline
        result = sut.validate_slots("kickoff.goal", slots)
        assert not result.is_ok()
        assert result.error_code == "E_L102_L207_003"
        assert result.details
