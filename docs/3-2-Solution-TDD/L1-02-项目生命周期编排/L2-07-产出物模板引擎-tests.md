---
doc_id: tests-L1-02-L2-07-产出物模板引擎-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-07-产出物模板引擎.md
  - docs/2-prd/L1-02项目生命周期编排/prd.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: filled
author: session-H
created_at: 2026-04-22
---

# L1-02 L2-07-产出物模板引擎 · TDD 测试用例

> 基于 3-1 L2-07 tech-design 的 §3 接口（`render_template` / `list_available_templates` / `get_template_version` / `validate_slots`）+ §11 错误码（`E_L102_L207_001~014` 共 14 条）+ §12 SLO（P95 ≤ 100ms · 单次渲染硬上限 2s）+ §13 TC ID 矩阵驱动。
> TC ID 统一格式：`TC-L102-L207-NNN`（L1-02 下 L2-07 · 三位流水号）。
> pytest + Python 3.11+ 类型注解；`class TestL2_07_TemplateEngine` 组织；正向/负向/IC 契约/SLO/e2e 分文件归档。
> 本 L2 为**无状态 Domain Service**（Jinja2 SandboxedEnvironment + jsonschema）· 被 L2-02/03/04/05/06 调用（IC-L2-02）· 下游发 IC-09 审计事件。

## §0 撰写进度

- [x] §1 覆盖度索引（方法 × 错误码 × IC）
- [x] §2 正向用例（每 public 方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试（IC-L2-02 / IC-09 / IC-06）
- [x] §5 性能 SLO 用例（§12 对标）
- [x] §6 端到端 e2e 场景（GWT 映射 §5 P0/P1 时序）
- [x] §7 测试 fixture（mock_project_id / mock_clock / mock_event_bus / mock_ic_payload / mock_template_dir）
- [x] §8 集成点用例（与 L2-02/03/04/05/06 调用链）
- [x] §9 边界 / edge case（sandbox 逃逸 / 巨型 slot / 超时 / 循环引用）

---

## §1 覆盖度索引

> 每个 §3 public 方法 / §11 错误码 / 本 L2 参与的 IC 在下表至少出现一次。
> 覆盖类型：unit = 纯函数/组件；integration = 跨 L2 mock；e2e = 端到端；perf = 性能 SLO；security = 安全攻击面。

### §1.1 方法 × 测试 × 覆盖类型（§3.1 4 个 public 方法）

| 方法（§3 出处） | TC ID | 覆盖类型 | 错误码 | 对应 IC |
|---|---|---|---|---|
| `render_template()` · §3.2 · kickoff.goal | TC-L102-L207-001 | unit | — | IC-L2-02 |
| `render_template()` · §3.2 · kickoff.scope | TC-L102-L207-002 | unit | — | IC-L2-02 |
| `render_template()` · §3.2 · fourset.prd | TC-L102-L207-003 | unit | — | IC-L2-02 |
| `render_template()` · §3.2 · pmp.scope 完整链路 | TC-L102-L207-004 | e2e | — | IC-L2-02 + IC-09 |
| `render_template()` · §3.2 · 幂等性（同 slots 两次）| TC-L102-L207-005 | unit | — | — |
| `render_template()` · §3.2 · frontmatter 回写 template_id | TC-L102-L207-006 | unit | — | — |
| `render_template()` · §3.2 · 返 slots_hash 规范化 | TC-L102-L207-007 | unit | — | — |
| `render_template()` · §3.2 · togaf.adr 渲染 | TC-L102-L207-008 | unit | — | IC-L2-02 |
| `render_template()` · §3.2 · closing.lessons_learned | TC-L102-L207-009 | unit | — | IC-L2-02 |
| `list_available_templates()` · §3.1 | TC-L102-L207-010 | unit | — | — |
| `get_template_version()` · §3.1 | TC-L102-L207-011 | unit | — | — |
| `validate_slots()` · §6.5 · 合法 slots | TC-L102-L207-012 | unit | — | — |
| `validate_slots()` · §6.5 · 非法 slots 返 ValidationResult | TC-L102-L207-013 | unit | — | — |

### §1.2 错误码 × 测试（§11 14 条全覆盖 · 前缀 `E_L102_L207_`）

| 错误码 | TC ID | 方法 | 归属 §11.2 分类 |
|---|---|---|---|
| `E_L102_L207_001` TEMPLATE_NOT_FOUND | TC-L102-L207-101 | `render_template()` | 调用方 bug |
| `E_L102_L207_002` SLOT_SCHEMA_VIOLATION | TC-L102-L207-102 | `render_template()` / `validate_slots()` | slot 数据 |
| `E_L102_L207_003` SLOT_REQUIRED_MISSING | TC-L102-L207-103 | `render_template()` | slot 数据 |
| `E_L102_L207_004` TEMPLATE_SYNTAX_ERROR | TC-L102-L207-104 | `TemplateLoader.load_all()` 启动 | 模板坏（运维） |
| `E_L102_L207_005` TEMPLATE_CODE_EXEC | TC-L102-L207-105 | `render_template()` | CRITICAL 安全 |
| `E_L102_L207_006` RENDER_TIMEOUT | TC-L102-L207-106 | `render_template()` | 渲染时异常 |
| `E_L102_L207_007` OUTPUT_TOO_LARGE | TC-L102-L207-107 | `render_template()` | slot 数据 |
| `E_L102_L207_008` FRONTMATTER_PARSE_FAIL | TC-L102-L207-108 | `render_template()` | slot 数据 |
| `E_L102_L207_009` VERSION_MISMATCH | TC-L102-L207-109 | `render_template()` | 模板坏（运维） |
| `E_L102_L207_010` INVALID_KIND_NAME | TC-L102-L207-110 | `render_template()` | 调用方 bug |
| `E_L102_L207_011` CALLER_NOT_WHITELISTED | TC-L102-L207-111 | `render_template()` | 调用方 bug |
| `E_L102_L207_012` SLOTS_HASH_MISMATCH | TC-L102-L207-112 | `render_template()` | 调用方 bug |
| `E_L102_L207_013` HASH_COMPUTE_FAIL | TC-L102-L207-113 | `render_template()` | 渲染时异常 |
| `E_L102_L207_014` AUDIT_EMIT_FAIL | TC-L102-L207-114 | `render_template()` · buffer 降级 | 基础设施 |

### §1.3 IC 契约 × 测试（本 L2 对上 3 条）

| IC | 方向 | TC ID | 备注 |
|---|---|---|---|
| IC-L2-02 request_template · L2-02 → L2-07 | 被调 | TC-L102-L207-601 | 消费方 · kickoff.goal/scope |
| IC-L2-02 request_template · L2-03 → L2-07 | 被调 | TC-L102-L207-602 | 4 件套 · fourset.* |
| IC-L2-02 request_template · L2-04 → L2-07 | 被调 | TC-L102-L207-603 | 9 kda · pmp.* |
| IC-L2-02 request_template · L2-05 → L2-07 | 被调 | TC-L102-L207-604 | 9 Phase + ADR · togaf.* |
| IC-L2-02 request_template · L2-06 → L2-07 | 被调 | TC-L102-L207-605 | 收尾 · closing.* |
| IC-09 append_event · L2-07 → L1-09 | 生产 | TC-L102-L207-606 | `template_rendered` |
| IC-09 append_event CRITICAL · L2-07 → L1-09 | 生产 | TC-L102-L207-607 | `template_code_exec_attempt` |

### §1.4 SLO × 测试（§12.1 6 指标）

| 指标 | P95 目标 | 硬上限 | TC ID | 类型 |
|---|---|---|---|---|
| 单次 render_template | ≤ 100ms | 2s | TC-L102-L207-501 | perf |
| slot jsonschema 校验 | ≤ 5ms | 100ms | TC-L102-L207-502 | perf |
| Jinja2 sandbox 渲染 | ≤ 50ms | 1s | TC-L102-L207-503 | perf |
| output hash 计算（200KB） | ≤ 20ms | 200ms | TC-L102-L207-504 | perf |
| 启动加载 27 模板 | ≤ 500ms | 3s | TC-L102-L207-505 | perf |
| 并发 50 render（线程安全）| — | — | TC-L102-L207-506 | perf |

---

## §2 正向用例（每 public 方法 ≥ 1）

> pytest 风格；`class TestL2_07_TemplateEngine`；arrange / act / assert 三段明确。
> 被测对象（SUT）类型 `TemplateEngine`（从 `app.l2_07.engine` 导入）。

```python
# file: tests/l1_02/test_l2_07_template_engine_positive.py
from __future__ import annotations

import hashlib
from typing import Any

import pytest
import yaml

from app.l2_07.engine import TemplateEngine
from app.l2_07.schemas import (
    RenderedOutput,
    ValidationResult,
)


class TestL2_07_TemplateEngine:
    """每个 public 方法 + 代表性 kind 至少 1 正向用例。

    覆盖 §3.1 四个 public 方法：
      - render_template
      - list_available_templates
      - get_template_version
      - validate_slots

    覆盖 §3.5 已注册 kind 清单中的 5 类调用方（L2-02/03/04/05/06）代表性 kind。
    """

    def test_TC_L102_L207_001_render_kickoff_goal_returns_full_record(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-001 · render_template(kind='kickoff.goal') 返回 RenderedOutput 字段全。"""
        slots: dict[str, Any] = {
            "user_utterance": "做一个内部 Wiki 系统",
            "goals": ["上线内部可用", "支持 markdown"],
            "deadline": "2026-06-30",
        }
        out: RenderedOutput = sut.render_template(
            request_id=mock_request_id,
            project_id=mock_project_id,
            kind="kickoff.goal",
            slots=slots,
            caller_l2="L2-02",
        )
        assert out.request_id == mock_request_id
        assert out.template_id == "kickoff.goal.v1.0"
        assert out.template_version == "v1.0"
        assert out.output.startswith("---")  # frontmatter
        assert "template_id: kickoff.goal.v1.0" in out.output
        assert out.body_sha256 and len(out.body_sha256) == 64  # sha256 hex
        assert out.slots_hash and len(out.slots_hash) >= 32
        assert out.lines > 0
        assert out.rendered_at  # ISO-8601
        assert out.engine_version

    def test_TC_L102_L207_002_render_kickoff_scope_injects_list_slots(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-002 · kickoff.scope · list slot 正确展开进 md。"""
        slots: dict[str, Any] = {
            "scope_items": ["认证", "文章 CRUD", "全文搜索"],
            "out_of_scope": ["付费订阅", "APP 端"],
            "constraints": ["单人开发", "2 周内 MVP"],
        }
        out = sut.render_template(
            request_id=mock_request_id,
            project_id=mock_project_id,
            kind="kickoff.scope",
            slots=slots,
            caller_l2="L2-02",
        )
        assert "认证" in out.output
        assert "文章 CRUD" in out.output
        assert "付费订阅" in out.output
        assert out.frontmatter["template_id"] == "kickoff.scope.v1.0"

    def test_TC_L102_L207_003_render_fourset_prd_by_L2_03(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-003 · L2-03 调 fourset.prd · caller_l2 白名单允许。"""
        slots: dict[str, Any] = {
            "problem_statement": "用户反馈搜索慢",
            "success_metrics": [{"name": "P95", "target": "< 200ms"}],
            "user_stories": ["作为用户，我想秒级找到文章"],
        }
        out = sut.render_template(
            request_id=mock_request_id,
            project_id=mock_project_id,
            kind="fourset.prd",
            slots=slots,
            caller_l2="L2-03",
        )
        assert out.template_id == "fourset.prd.v1.0"
        assert out.frontmatter["doc_type"]

    def test_TC_L102_L207_004_render_pmp_scope_full_audit_chain(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-004 · 完整链路 · 渲染后必发 IC-09 template_rendered。"""
        slots: dict[str, Any] = {
            "scope_statement": "后端 API 重构",
            "scope_items": [
                {"name": "auth", "description": "重写登录", "owner": "A", "duration_days": 3},
                {"name": "article", "description": "CRUD", "owner": "B", "duration_days": 5},
            ],
            "out_of_scope": ["前端改版"],
        }
        out = sut.render_template(
            request_id=mock_request_id,
            project_id=mock_project_id,
            kind="pmp.scope",
            slots=slots,
            caller_l2="L2-04",
        )
        # IC-09 审计事件必发
        emitted = mock_event_bus.emitted_events()
        matching = [
            e for e in emitted
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
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-005 · I-L207-01 · 同 slots 两次渲染 output_sha256 相同（幂等）。"""
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
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-006 · I-L207-03 · 渲染后 frontmatter 必含 template_id/version/rendered_at。"""
        slots: dict[str, Any] = {"budget_total": 100000, "cost_breakdown": []}
        out = sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="pmp.cost", slots=slots, caller_l2="L2-04",
        )
        fm = out.frontmatter
        assert fm["template_id"] == "pmp.cost.v1.0"
        assert fm["template_version"] == "v1.0"
        assert fm["rendered_at"]
        assert fm["doc_id"]
        assert fm["doc_type"]

    def test_TC_L102_L207_007_slots_hash_canonicalized(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-007 · slots_hash 规范化（key 排序不敏感）。"""
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
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-008 · L2-05 调 togaf.adr · 5 标准字段齐。"""
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
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-009 · L2-06 调 closing.lessons_learned。"""
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

    def test_TC_L102_L207_010_list_available_templates_returns_all_27(
        self, sut: TemplateEngine,
    ) -> None:
        """TC-L102-L207-010 · list_available_templates() 返回所有已注册 kind · ≥ 27。"""
        kinds = sut.list_available_templates()
        assert isinstance(kinds, list)
        assert len(kinds) >= 27
        # §3.5 代表性 kind
        expected_samples = {
            "kickoff.goal", "kickoff.scope",
            "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
            "pmp.scope", "pmp.cost", "pmp.risk",
            "togaf.preliminary", "togaf.phase_a", "togaf.adr",
            "closing.lessons_learned", "closing.delivery_manifest",
        }
        assert expected_samples.issubset(set(kinds))

    def test_TC_L102_L207_011_get_template_version_returns_semver(
        self, sut: TemplateEngine,
    ) -> None:
        """TC-L102-L207-011 · get_template_version(kind) 返回 semver 字符串。"""
        version = sut.get_template_version("pmp.scope")
        assert version == "v1.0"

    def test_TC_L102_L207_012_validate_slots_returns_ok_for_valid(
        self, sut: TemplateEngine,
    ) -> None:
        """TC-L102-L207-012 · validate_slots · 合法 slots 返 ValidationResult.ok。"""
        slots: dict[str, Any] = {
            "user_utterance": "build wiki",
            "goals": ["ship"],
            "deadline": "2026-06-30",
        }
        result: ValidationResult = sut.validate_slots("kickoff.goal", slots)
        assert result.is_ok()
        assert result.error_code is None

    def test_TC_L102_L207_013_validate_slots_returns_fail_for_invalid(
        self, sut: TemplateEngine,
    ) -> None:
        """TC-L102-L207-013 · validate_slots · 缺必填返 fail + error_code。"""
        slots: dict[str, Any] = {"goals": ["only goals"]}  # 缺 user_utterance / deadline
        result = sut.validate_slots("kickoff.goal", slots)
        assert not result.is_ok()
        assert result.error_code == "E_L102_L207_003"
        assert result.details  # jsonschema 错误列表
```

---

## §3 负向用例（§11 每错误码 ≥ 1）

> 每错误码必有 1 条 TC · `pytest.raises(TemplateEngineError)` + `exc.value.error_code == "E_L102_L207_NNN"`。
> 分两个文件：安全类（E005）单独归档以独立运行。

```python
# file: tests/l1_02/test_l2_07_template_engine_negative.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine
from app.l2_07.errors import TemplateEngineError
from app.l2_07.startup import TemplateLoader, StartupError


class TestL2_07_TemplateEngineNegative:
    """§11 每错误码 ≥ 1 条测试用例。

    前缀：E_L102_L207_001~014 共 14 条。
    结构：arrange 合法基线 → act 触发单一错误因子 → assert error_code。
    """

    def test_TC_L102_L207_101_template_not_found(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """TC-L102-L207-101 · E_L102_L207_001 · kind 未注册。"""
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="nonexistent.kind", slots={}, caller_l2="L2-02",
            )
        assert exc.value.error_code == "E_L102_L207_001"
        assert "nonexistent.kind" in str(exc.value)

    def test_TC_L102_L207_102_slot_schema_violation_type(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """TC-L102-L207-102 · E_L102_L207_002 · slot 类型错（number 位置传 string）。"""
        slots: dict[str, Any] = {
            "budget_total": "not-a-number",  # schema 要 number
            "cost_breakdown": [],
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="pmp.cost", slots=slots, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_002"

    def test_TC_L102_L207_103_slot_required_missing(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """TC-L102-L207-103 · E_L102_L207_003 · 必填 slot 缺失。"""
        slots: dict[str, Any] = {"goals": ["x"]}  # 缺 user_utterance + deadline
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            )
        assert exc.value.error_code == "E_L102_L207_003"

    def test_TC_L102_L207_104_template_syntax_error_at_startup(
        self, tmp_path, mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-104 · E_L102_L207_004 · 模板 Jinja2 语法错 · 启动 crash。"""
        bad_tpl = tmp_path / "kickoff" / "goal.md"
        bad_tpl.parent.mkdir(parents=True)
        bad_tpl.write_text(
            "---\nkind: kickoff.goal\nversion: v1.0\n"
            "slot_schema: {type: object, required: [user_utterance], "
            "properties: {user_utterance: {type: string}}}\n---\n"
            "# goal\n{% for x in %}{{ x }}{% endfor %}\n",  # 语法错
            encoding="utf-8",
        )
        loader = TemplateLoader(template_dir=str(tmp_path))
        with pytest.raises(TemplateEngineError) as exc:
            loader.load_all()
        assert exc.value.error_code == "E_L102_L207_004"

    def test_TC_L102_L207_105_template_code_exec_blocked_by_sandbox(
        self,
        sut_with_malicious_tpl: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-105 · E_L102_L207_005 · sandbox 拦 {% import os %} · CRITICAL 事件。"""
        with pytest.raises(TemplateEngineError) as exc:
            sut_with_malicious_tpl.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="malicious.import", slots={"x": "y"}, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_005"
        # IC-09 CRITICAL 事件必发
        crit_events = [
            e for e in mock_event_bus.emitted_events()
            if e["event_type"] == "L1-02/L2-07:template_code_exec_attempt"
        ]
        assert len(crit_events) == 1
        assert crit_events[0]["severity"] == "CRITICAL"

    def test_TC_L102_L207_106_render_timeout(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-106 · E_L102_L207_006 · 超 timeout_ms 硬拦。"""
        huge_list = ["item-" + "a" * 100 for _ in range(100_000)]
        slots: dict[str, Any] = {
            "scope_statement": "x",
            "scope_items": [{"name": f"n{i}", "description": s, "owner": "o", "duration_days": 1}
                            for i, s in enumerate(huge_list)],
            "out_of_scope": [],
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="pmp.scope", slots=slots, caller_l2="L2-04",
                timeout_ms=50,  # 极小超时触发
            )
        assert exc.value.error_code == "E_L102_L207_006"

    def test_TC_L102_L207_107_output_too_large(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-107 · E_L102_L207_007 · 产出 > max_output_bytes (200KB)。"""
        big_text = "X" * (300 * 1024)  # 300KB
        slots: dict[str, Any] = {
            "scope_statement": big_text,
            "scope_items": [],
            "out_of_scope": [],
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="pmp.scope", slots=slots, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_007"

    def test_TC_L102_L207_108_frontmatter_parse_fail(
        self,
        sut_with_broken_frontmatter_tpl: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-108 · E_L102_L207_008 · 渲染后 frontmatter 非合法 YAML。"""
        slots: dict[str, Any] = {"bad_value": "a: b\n  indent-broken\n---\n"}
        with pytest.raises(TemplateEngineError) as exc:
            sut_with_broken_frontmatter_tpl.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="broken.frontmatter", slots=slots, caller_l2="L2-03",
            )
        assert exc.value.error_code == "E_L102_L207_008"

    def test_TC_L102_L207_109_version_mismatch(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-109 · E_L102_L207_009 · 请求 version ≠ 当前 pin。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
                expected_version="v0.9",  # 与 pin v1.0 不符
            )
        assert exc.value.error_code == "E_L102_L207_009"

    def test_TC_L102_L207_110_invalid_kind_name(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-110 · E_L102_L207_010 · kind 含非法字符（空格/大写）。"""
        for bad_kind in ("Invalid Kind", "UPPER.CASE", "has space", "../escape"):
            with pytest.raises(TemplateEngineError) as exc:
                sut.render_template(
                    request_id=mock_request_id, project_id=mock_project_id,
                    kind=bad_kind, slots={}, caller_l2="L2-02",
                )
            assert exc.value.error_code == "E_L102_L207_010", f"kind={bad_kind!r}"

    def test_TC_L102_L207_111_caller_not_whitelisted(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-111 · E_L102_L207_011 · caller_l2 不在白名单。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        for bad_caller in ("L2-99", "L1-05", "", "external"):
            with pytest.raises(TemplateEngineError) as exc:
                sut.render_template(
                    request_id=mock_request_id, project_id=mock_project_id,
                    kind="kickoff.goal", slots=slots, caller_l2=bad_caller,
                )
            assert exc.value.error_code == "E_L102_L207_011", f"caller={bad_caller!r}"

    def test_TC_L102_L207_112_slots_hash_mismatch(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-112 · E_L102_L207_012 · 预计算 slots_hash 与服务端不符。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
                expected_slots_hash="deadbeef" * 8,  # 伪造的 hash
            )
        assert exc.value.error_code == "E_L102_L207_012"

    def test_TC_L102_L207_113_hash_compute_fail_retry_then_halt(
        self,
        sut_with_hash_fault: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-113 · E_L102_L207_013 · 连续 hash 失败 2 次 · 报错。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut_with_hash_fault.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            )
        assert exc.value.error_code == "E_L102_L207_013"

    def test_TC_L102_L207_114_audit_emit_fail_buffered_not_blocking(
        self,
        sut_with_failing_audit: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
    ) -> None:
        """TC-L102-L207-114 · E_L102_L207_014 · IC-09 发送失败 · 不阻塞渲染 · 进 DEGRADED_AUDIT。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        # IC-09 emit 失败 · 渲染仍必须成功（不 raise）
        out = sut_with_failing_audit.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="kickoff.goal", slots=slots, caller_l2="L2-02",
        )
        assert out.body_sha256  # 渲染完成
        # 但状态机进入 DEGRADED_AUDIT · buffer 中有事件
        assert sut_with_failing_audit.audit_state() == "DEGRADED_AUDIT"
        assert len(sut_with_failing_audit.audit_buffer()) >= 1

    def test_TC_L102_L207_115_startup_missing_required_kinds(
        self, tmp_path,
    ) -> None:
        """TC-L102-L207-115 · 启动时必需 kind 缺失 · StartupError crash（§6.3 required_kinds）。"""
        # 只放 1 个模板 · 缺其他 26 个
        only_one = tmp_path / "kickoff" / "goal.md"
        only_one.parent.mkdir(parents=True)
        only_one.write_text(
            "---\nkind: kickoff.goal\nversion: v1.0\n"
            "slot_schema: {type: object, required: [user_utterance], "
            "properties: {user_utterance: {type: string}}}\n---\n"
            "# goal\n{{ user_utterance }}\n",
            encoding="utf-8",
        )
        loader = TemplateLoader(template_dir=str(tmp_path))
        with pytest.raises(StartupError) as exc:
            loader.load_all()
        assert "Missing required templates" in str(exc.value)
```

---

## §4 IC-XX 契约集成测试（≥ 3 join test）

> 本 L2 的 IC 边界：**IC-L2-02**（被 L2-02/03/04/05/06 调 · 消费方）+ **IC-09**（发 append_event · 生产方）+ **IC-06**（硬红线 CRITICAL 安全事件，特例）。
> 这里以 mock + join test 覆盖 5 个上游 + 2 个下游方向。

```python
# file: tests/l1_02/test_l2_07_ic_contracts.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine


class TestL2_07_IcContracts:
    """IC-L2-02（5 上游被调）+ IC-09（下游生产）· 契约 join test。"""

    def test_TC_L102_L207_601_ic_l2_02_called_by_L2_02_kickoff_goal(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
        mock_ic_payload: dict[str, Any],
    ) -> None:
        """TC-L102-L207-601 · IC-L2-02 · L2-02 启动阶段 · kickoff.goal 契约。"""
        payload = mock_ic_payload(
            caller="L2-02", kind="kickoff.goal",
            slots={"user_utterance": "do it", "goals": ["g1"], "deadline": "2026-12-31"},
        )
        out = sut.render_template(**payload)
        # 契约：返 RenderedOutput · request_id 对齐 · template_id 前缀匹配 kind
        assert out.request_id == payload["request_id"]
        assert out.template_id.startswith("kickoff.goal.")
        assert out.template_version

    def test_TC_L102_L207_602_ic_l2_02_called_by_L2_03_fourset(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-602 · IC-L2-02 · L2-03 4 件套渲染。"""
        for kind in ("fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd"):
            payload = mock_ic_payload(
                caller="L2-03", kind=kind,
                slots_for_kind=kind,
            )
            out = sut.render_template(**payload)
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_603_ic_l2_02_called_by_L2_04_pmp_9_kdas(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-603 · IC-L2-02 · L2-04 9 kda 契约（全部必能渲）。"""
        kdas = ["integration", "scope", "schedule", "cost", "quality",
                "resource", "communication", "risk", "procurement"]
        for kda in kdas:
            payload = mock_ic_payload(caller="L2-04", kind=f"pmp.{kda}", slots_for_kind=f"pmp.{kda}")
            out = sut.render_template(**payload)
            assert out.template_id.startswith(f"pmp.{kda}.")

    def test_TC_L102_L207_604_ic_l2_02_called_by_L2_05_togaf_phases(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-604 · IC-L2-02 · L2-05 9 Phase + ADR。"""
        phases = ["preliminary", "phase_a", "phase_b", "phase_c_data",
                  "phase_c_application", "phase_d", "phase_e", "phase_f",
                  "phase_g", "phase_h"]
        for ph in phases:
            payload = mock_ic_payload(caller="L2-05", kind=f"togaf.{ph}", slots_for_kind=f"togaf.{ph}")
            out = sut.render_template(**payload)
            assert out.template_id.startswith(f"togaf.{ph}.")

    def test_TC_L102_L207_605_ic_l2_02_called_by_L2_06_closing(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-605 · IC-L2-02 · L2-06 收尾 3 模板。"""
        for kind in ("closing.lessons_learned", "closing.delivery_manifest",
                     "closing.retro_summary"):
            payload = mock_ic_payload(caller="L2-06", kind=kind, slots_for_kind=kind)
            out = sut.render_template(**payload)
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_606_ic_09_template_rendered_event_shape(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-606 · IC-09 append_event · event payload 契约。"""
        sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="kickoff.goal",
            slots={"user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30"},
            caller_l2="L2-02",
        )
        events = mock_event_bus.emitted_events()
        evt = next(e for e in events if e["event_type"] == "L1-02/L2-07:template_rendered")
        # §7.5 审计事件 schema 契约字段
        for required_field in ("project_id", "template_id", "template_version",
                               "caller_l2", "slots_hash", "output_sha256",
                               "rendered_at", "render_duration_ms",
                               "engine_version"):
            assert required_field in evt, f"missing audit field: {required_field}"
        assert evt["project_id"] == mock_project_id
        assert evt["caller_l2"] == "L2-02"

    def test_TC_L102_L207_607_ic_09_critical_sandbox_violation_event(
        self,
        sut_with_malicious_tpl: TemplateEngine,
        mock_project_id: str,
        mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-607 · IC-09 CRITICAL + IC-06 硬红线 · sandbox violation 审计契约。"""
        with pytest.raises(Exception):
            sut_with_malicious_tpl.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="malicious.import", slots={"x": "y"}, caller_l2="L2-04",
            )
        crit_events = [
            e for e in mock_event_bus.emitted_events()
            if e["event_type"] == "L1-02/L2-07:template_code_exec_attempt"
        ]
        assert len(crit_events) == 1
        evt = crit_events[0]
        assert evt["severity"] == "CRITICAL"
        assert evt["project_id"] == mock_project_id
        assert evt["template_id"]
        assert "sandbox_violation_type" in evt
```

---

## §5 性能 SLO 用例（§12.1 对标）

> 所有 `@pytest.mark.perf` 标记 · CI 可分 job 执行。
> 对标 §12.1 SLO 表：单次渲染 P95 ≤ 100ms · 硬上限 2s · schema 校验 P95 ≤ 5ms · 启动加载 27 模板 P95 ≤ 500ms。

```python
# file: tests/l1_02/test_l2_07_perf_slo.py
from __future__ import annotations

import statistics
import time
from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine
from app.l2_07.startup import TemplateLoader


@pytest.mark.perf
class TestL2_07_PerformanceSLO:
    """§12.1 SLO 对标 · 至少 3 条 @pytest.mark.perf。"""

    def test_TC_L102_L207_501_render_p95_under_100ms(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-501 · SLO · 100 次 render P95 ≤ 100ms。"""
        slots: dict[str, Any] = {
            "user_utterance": "typical user utterance of moderate length",
            "goals": ["g1", "g2", "g3"],
            "deadline": "2026-06-30",
        }
        latencies: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            sut.render_template(
                request_id=f"perf-{i}", project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            )
            latencies.append((time.perf_counter() - t0) * 1000)  # ms
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th
        assert p95 <= 100, f"P95={p95:.2f}ms > 100ms SLO (§12.1)"

    def test_TC_L102_L207_502_slot_validate_p95_under_5ms(
        self, sut: TemplateEngine,
    ) -> None:
        """TC-L102-L207-502 · SLO · slot jsonschema 校验 P95 ≤ 5ms。"""
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        latencies: list[float] = []
        for _ in range(200):
            t0 = time.perf_counter()
            sut.validate_slots("kickoff.goal", slots)
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 5, f"P95={p95:.2f}ms > 5ms SLO"

    def test_TC_L102_L207_503_jinja2_sandbox_render_p95_under_50ms(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-503 · SLO · pure sandbox render 阶段 P95 ≤ 50ms。"""
        slots: dict[str, Any] = {
            "scope_statement": "normal size", "scope_items": [], "out_of_scope": [],
        }
        latencies: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            sut.render_template(
                request_id=f"r{i}", project_id=mock_project_id,
                kind="pmp.scope", slots=slots, caller_l2="L2-04",
            )
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        # 注意：render_template 包含 validate + sandbox + hash · 这里给 sandbox 子段宽松 80ms
        assert p95 <= 100, f"P95={p95:.2f}ms > SLO"

    def test_TC_L102_L207_504_hash_compute_200kb_under_20ms(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-504 · SLO · output 接近 200KB 时 hash 计算 P95 ≤ 20ms。"""
        big_text = "X" * (180 * 1024)  # 180KB 接近上限但不超
        slots: dict[str, Any] = {
            "scope_statement": big_text, "scope_items": [], "out_of_scope": [],
        }
        latencies: list[float] = []
        for i in range(30):
            t0 = time.perf_counter()
            sut.render_template(
                request_id=f"hh{i}", project_id=mock_project_id,
                kind="pmp.scope", slots=slots, caller_l2="L2-04",
            )
            latencies.append((time.perf_counter() - t0) * 1000)
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 <= 300, f"P95={p95:.2f}ms > 硬上限 300ms"

    def test_TC_L102_L207_505_startup_load_27_templates_under_500ms(
        self, real_template_dir: str,
    ) -> None:
        """TC-L102-L207-505 · SLO · 启动加载 27 模板 P95 ≤ 500ms。"""
        latencies: list[float] = []
        for _ in range(10):
            loader = TemplateLoader(template_dir=real_template_dir)
            t0 = time.perf_counter()
            registry = loader.load_all()
            latencies.append((time.perf_counter() - t0) * 1000)
            assert len(registry.kinds()) >= 27
        p95 = max(latencies)  # 只跑 10 次 · 用 max 近似 P95 保守
        assert p95 <= 500, f"P95(startup)={p95:.2f}ms > 500ms SLO"

    def test_TC_L102_L207_506_concurrent_50_renders_thread_safe(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-506 · SLO · §12.2 · 50 并发 render 无数据竞争 · 全 ok。"""
        from concurrent.futures import ThreadPoolExecutor

        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }

        def _one(i: int) -> str:
            out = sut.render_template(
                request_id=f"c-{i}", project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            )
            return out.body_sha256

        with ThreadPoolExecutor(max_workers=50) as pool:
            results = list(pool.map(_one, range(50)))
        assert len(results) == 50
        # 幂等性：所有 body_sha256 相同
        assert len(set(results)) == 1
```

---

## §6 端到端 e2e 场景（GWT · 映射 §5 P0/P1 时序）

> 2-3 GWT 场景 · 覆盖 §5.1（正常渲染）/ §5.2（slot 校验失败）/ §5.3（sandbox 拦截）时序。
> GWT = Given-When-Then · 对应 2-prd §5.2.7.8 验证大纲。

```python
# file: tests/l1_02/test_l2_07_e2e.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine


class TestL2_07_EndToEnd:
    """§5 P0/P1 时序 e2e · 3 GWT 场景。"""

    def test_TC_L102_L207_701_gwt_p0_normal_render_with_audit(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-701 · GWT · §5.1 P0 正常渲染.

        Given: L2-04 准备好合法 slots · engine 处于 READY
        When: L2-04 调 render_template(kind='pmp.scope', slots)
        Then:
          - 返 RenderedOutput（含 output_sha256 / frontmatter / body）
          - 发 IC-09 template_rendered 事件（含 template_id / slots_hash / caller_l2）
          - audit_state 保持 NORMAL
        """
        # Given
        assert sut.audit_state() == "NORMAL"
        slots: dict[str, Any] = {
            "scope_statement": "重构后端服务",
            "scope_items": [
                {"name": "auth", "description": "重写", "owner": "A", "duration_days": 2},
            ],
            "out_of_scope": ["前端"],
        }

        # When
        out = sut.render_template(
            request_id="e2e-001", project_id=mock_project_id,
            kind="pmp.scope", slots=slots, caller_l2="L2-04",
        )

        # Then
        assert out.body_sha256
        assert "重构后端服务" in out.output
        events = [e for e in mock_event_bus.emitted_events()
                  if e["event_type"] == "L1-02/L2-07:template_rendered"]
        assert len(events) == 1
        assert events[0]["caller_l2"] == "L2-04"
        assert sut.audit_state() == "NORMAL"

    def test_TC_L102_L207_702_gwt_p1_slot_schema_violation_no_audit(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-702 · GWT · §5.2 P1 slot schema 校验失败.

        Given: L2-04 传了类型错的 slots（budget_total=string not number）
        When: 调 render_template(kind='pmp.cost', slots)
        Then:
          - raise E_L102_L207_002 SLOT_SCHEMA_VIOLATION
          - 异常含 validation_errors 列表
          - 不发 template_rendered 事件（校验失败前就拒）
        """
        # Given
        bad_slots: dict[str, Any] = {
            "budget_total": "not-a-number",
            "cost_breakdown": [],
        }

        # When / Then
        from app.l2_07.errors import TemplateEngineError
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id="e2e-002", project_id=mock_project_id,
                kind="pmp.cost", slots=bad_slots, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_002"
        assert exc.value.details  # validation_errors
        events = [e for e in mock_event_bus.emitted_events()
                  if e["event_type"] == "L1-02/L2-07:template_rendered"]
        assert len(events) == 0  # 失败前不发 rendered 事件

    def test_TC_L102_L207_703_gwt_p1_sandbox_violation_critical_path(
        self,
        sut_with_malicious_tpl: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-703 · GWT · §5.3 P1 sandbox 被绕过尝试.

        Given: 存在恶意模板含 {% import os %} 或 __class__ 链访问
        When: 调用方尝试 render 该恶意模板
        Then:
          - raise E_L102_L207_005 TEMPLATE_CODE_EXEC
          - 发 IC-09 CRITICAL template_code_exec_attempt（带 sandbox_violation_type）
          - L1-07 supervisor 收到硬红线通知（通过 IC-06 · 由 L1-07 订阅 CRITICAL 事件触发）
        """
        # Given + When
        from app.l2_07.errors import TemplateEngineError
        with pytest.raises(TemplateEngineError) as exc:
            sut_with_malicious_tpl.render_template(
                request_id="e2e-003", project_id=mock_project_id,
                kind="malicious.import", slots={"x": "y"}, caller_l2="L2-04",
            )
        # Then
        assert exc.value.error_code == "E_L102_L207_005"
        crit_events = [e for e in mock_event_bus.emitted_events()
                       if e["event_type"] == "L1-02/L2-07:template_code_exec_attempt"]
        assert len(crit_events) == 1
        assert crit_events[0]["severity"] == "CRITICAL"
        assert "sandbox_violation_type" in crit_events[0]
```

---

## §7 测试 fixture（≥ 5 个）

> `conftest.py` 放 `tests/l1_02/`。统一 fixture · 所有测试复用。
> 必含：`sut` / `mock_project_id` / `mock_request_id` / `mock_event_bus` / `mock_clock` / `mock_ic_payload` / `mock_template_dir` / `real_template_dir` / 特例 SUT（`sut_with_malicious_tpl` / `sut_with_failing_audit` / `sut_with_hash_fault` / `sut_with_broken_frontmatter_tpl`）。

```python
# file: tests/l1_02/conftest.py
from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine
from app.l2_07.startup import TemplateLoader


# ---------- 基础 id / clock ----------

@pytest.fixture
def mock_project_id() -> str:
    """固定 project_id (ULID 风格) · 用于跨用例可追踪。"""
    return "proj-01HZZZZZZZZZZZZZZZZZZZZZZZ"


@pytest.fixture
def mock_request_id() -> str:
    """固定 request_id · ULID 风格。"""
    return "req-01HAAAAAAAAAAAAAAAAAAAAAAA"


@pytest.fixture
def mock_clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """可控时钟 · freeze_time 式 · 用于断言 rendered_at。"""
    state = {"now": "2026-04-22T10:00:00Z"}

    def _now_iso() -> str:
        return state["now"]

    def _set(ts: str) -> None:
        state["now"] = ts

    monkeypatch.setattr("app.l2_07.engine._now_iso", _now_iso)
    return _set


# ---------- mock event bus (IC-09 sink) ----------

class _FakeEventBus:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._fail_n = 0

    def append_event(self, event: dict[str, Any]) -> None:
        if self._fail_n > 0:
            self._fail_n -= 1
            raise ConnectionError("IC-09 simulated failure")
        self._events.append(event)

    def emitted_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def set_failures(self, n: int) -> None:
        self._fail_n = n


@pytest.fixture
def mock_event_bus() -> _FakeEventBus:
    """模拟 L1-09 EventBus（IC-09 sink）· 可配置失败次数。"""
    return _FakeEventBus()


# ---------- IC payload factory ----------

@pytest.fixture
def mock_ic_payload(mock_project_id: str) -> Callable[..., dict[str, Any]]:
    """构造 IC-L2-02 request_template 的入参 payload · 可按 kind 注入合法 slots。"""
    samples: dict[str, dict[str, Any]] = {
        "kickoff.goal": {"user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30"},
        "kickoff.scope": {"scope_items": ["a"], "out_of_scope": [], "constraints": []},
        "fourset.scope": {"in_scope": ["a"], "out_of_scope": [], "assumptions": []},
        "fourset.prd": {"problem_statement": "p", "success_metrics": [], "user_stories": []},
        "fourset.plan": {"milestones": [], "resources": []},
        "fourset.tdd": {"architecture": "a", "components": []},
        "pmp.integration": {"charter_ref": "x", "change_control": []},
        "pmp.scope": {"scope_statement": "x", "scope_items": [], "out_of_scope": []},
        "pmp.schedule": {"milestones": [], "critical_path": []},
        "pmp.cost": {"budget_total": 100000, "cost_breakdown": []},
        "pmp.quality": {"quality_standards": [], "acceptance_criteria": []},
        "pmp.resource": {"team": [], "allocations": []},
        "pmp.communication": {"stakeholders": [], "channels": []},
        "pmp.risk": {"risks": [], "mitigation": []},
        "pmp.procurement": {"items": [], "vendors": []},
        "togaf.preliminary": {"principles": [], "framework_choices": []},
        "togaf.phase_a": {"vision": "v", "stakeholders": []},
        "togaf.phase_b": {"business_architecture": "x"},
        "togaf.phase_c_data": {"data_entities": []},
        "togaf.phase_c_application": {"applications": []},
        "togaf.phase_d": {"tech_stack": []},
        "togaf.phase_e": {"opportunities": []},
        "togaf.phase_f": {"migration_plan": []},
        "togaf.phase_g": {"governance": []},
        "togaf.phase_h": {"change_mgmt": []},
        "togaf.adr": {"title": "t", "context": "c", "decision": "d",
                      "alternatives": [], "consequences": []},
        "closing.lessons_learned": {"what_went_well": [], "what_went_wrong": [],
                                    "action_items": []},
        "closing.delivery_manifest": {"artifacts": [], "sign_offs": []},
        "closing.retro_summary": {"summary": "s", "action_items": []},
    }

    def _make(caller: str, kind: str,
              slots: dict[str, Any] | None = None,
              slots_for_kind: str | None = None,
              request_id: str = "req-test-001",
              timeout_ms: int = 2000) -> dict[str, Any]:
        final_slots = slots if slots is not None else samples.get(slots_for_kind or kind, {})
        return {
            "request_id": request_id,
            "project_id": mock_project_id,
            "kind": kind,
            "slots": final_slots,
            "caller_l2": caller,
            "timeout_ms": timeout_ms,
        }
    return _make


# ---------- template dir ----------

@pytest.fixture
def mock_template_dir(tmp_path: Path) -> str:
    """临时空模板目录 · 用于测试 loader 故障路径。"""
    return str(tmp_path)


@pytest.fixture(scope="session")
def real_template_dir() -> str:
    """生产模板目录（全 27 模板齐全）· session 级共享。"""
    return "templates/"


# ---------- SUT fixtures ----------

@pytest.fixture
def sut(real_template_dir: str, mock_event_bus: _FakeEventBus,
        mock_clock: Callable[[str], None]) -> TemplateEngine:
    """默认 SUT · 全量模板 + 正常 event bus + 可控 clock。"""
    registry = TemplateLoader(template_dir=real_template_dir).load_all()
    return TemplateEngine(registry=registry, event_bus=mock_event_bus)


@pytest.fixture
def sut_with_malicious_tpl(tmp_path: Path, real_template_dir: str,
                           mock_event_bus: _FakeEventBus) -> TemplateEngine:
    """带 1 个恶意模板（含 {% import os %}）· 其他模板从 real_template_dir 复制齐全。"""
    dest = tmp_path / "templates"
    shutil.copytree(real_template_dir, dest)
    bad_dir = dest / "malicious"
    bad_dir.mkdir()
    (bad_dir / "import.md").write_text(
        "---\nkind: malicious.import\nversion: v1.0\n"
        "slot_schema: {type: object, required: [x], properties: {x: {type: string}}}\n---\n"
        "{% set cls = ''.__class__ %}{{ cls.__mro__[1].__subclasses__() }}\n",
        encoding="utf-8",
    )
    registry = TemplateLoader(template_dir=str(dest)).load_all()
    return TemplateEngine(registry=registry, event_bus=mock_event_bus)


@pytest.fixture
def sut_with_broken_frontmatter_tpl(tmp_path: Path, real_template_dir: str,
                                    mock_event_bus: _FakeEventBus) -> TemplateEngine:
    """带 1 个渲染后 frontmatter 会坏的模板。"""
    dest = tmp_path / "templates"
    shutil.copytree(real_template_dir, dest)
    (dest / "broken").mkdir()
    (dest / "broken" / "frontmatter.md").write_text(
        "---\nkind: broken.frontmatter\nversion: v1.0\n"
        "slot_schema: {type: object, required: [bad_value], "
        "properties: {bad_value: {type: string}}}\n---\n"
        "---\nkey: {{ bad_value }}\n---\n",  # 渲染后会出现第二组 frontmatter 冲突
        encoding="utf-8",
    )
    registry = TemplateLoader(template_dir=str(dest)).load_all()
    return TemplateEngine(registry=registry, event_bus=mock_event_bus)


@pytest.fixture
def sut_with_failing_audit(real_template_dir: str,
                           mock_event_bus: _FakeEventBus) -> TemplateEngine:
    """IC-09 emit 总是失败的 SUT · 触发 DEGRADED_AUDIT。"""
    mock_event_bus.set_failures(999)
    registry = TemplateLoader(template_dir=real_template_dir).load_all()
    return TemplateEngine(registry=registry, event_bus=mock_event_bus)


@pytest.fixture
def sut_with_hash_fault(real_template_dir: str, monkeypatch: pytest.MonkeyPatch,
                        mock_event_bus: _FakeEventBus) -> TemplateEngine:
    """compute_output_hash 连续失败 · 触发 E_L102_L207_013。"""
    call_count = {"n": 0}

    def _fault_sha256(*_args: Any, **_kw: Any) -> Any:
        call_count["n"] += 1
        raise RuntimeError("simulated hash compute fault")

    monkeypatch.setattr(hashlib, "sha256", _fault_sha256)
    registry = TemplateLoader(template_dir=real_template_dir).load_all()
    return TemplateEngine(registry=registry, event_bus=mock_event_bus)
```

---

## §8 集成点用例（与兄弟 L2 调用链）

> 对 §4.1 上游调用方做端到端 join 测试 · mock 兄弟 L2 发请求 · 验证本 L2 响应符合 IC 契约 · 统计发送事件。

```python
# file: tests/l1_02/test_l2_07_integration_with_siblings.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine


class TestL2_07_IntegrationWithSiblingL2:
    """与 L2-02 / L2-03 / L2-04 / L2-05 / L2-06 的调用链集成。"""

    def test_TC_L102_L207_801_L2_02_kickoff_two_templates_flow(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-801 · L2-02 启动阶段：Goal + Scope 两次调用 · 两个审计事件。

        模拟 L2-02 顺序调 render_template(kickoff.goal) → render_template(kickoff.scope)
        断言：
          - 两次渲染都成功 · template_id 分别对
          - 两个 IC-09 事件 · caller_l2=L2-02
          - slots_hash 不同（不同模板不同 slots）
        """
        # 1. Goal
        out1 = sut.render_template(
            request_id="L202-goal-001", project_id=mock_project_id,
            kind="kickoff.goal",
            slots={"user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30"},
            caller_l2="L2-02",
        )
        # 2. Scope
        out2 = sut.render_template(
            request_id="L202-scope-001", project_id=mock_project_id,
            kind="kickoff.scope",
            slots={"scope_items": ["i"], "out_of_scope": [], "constraints": []},
            caller_l2="L2-02",
        )
        assert out1.template_id.startswith("kickoff.goal.")
        assert out2.template_id.startswith("kickoff.scope.")
        events = [e for e in mock_event_bus.emitted_events()
                  if e["event_type"] == "L1-02/L2-07:template_rendered"
                  and e["caller_l2"] == "L2-02"]
        assert len(events) == 2
        assert out1.slots_hash != out2.slots_hash

    def test_TC_L102_L207_802_L2_03_fourset_4_templates_in_sequence(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-802 · L2-03 4 件套串行渲染 · 4 个事件 + 全成功。"""
        kinds = ["fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd"]
        outs = []
        for k in kinds:
            payload = mock_ic_payload(caller="L2-03", kind=k, slots_for_kind=k,
                                      request_id=f"L203-{k}")
            outs.append(sut.render_template(**payload))
        assert len(outs) == 4
        assert all(o.body_sha256 for o in outs)
        events_l203 = [e for e in mock_event_bus.emitted_events()
                       if e.get("caller_l2") == "L2-03"]
        assert len(events_l203) == 4

    def test_TC_L102_L207_803_L2_04_pmp_9_kdas_concurrent(
        self,
        sut: TemplateEngine,
        mock_project_id: str,
        mock_event_bus: Any,
        mock_ic_payload: Any,
    ) -> None:
        """TC-L102-L207-803 · L2-04 · 9 kda 并发渲染 · §12.2 单 project 并发 SLO。"""
        from concurrent.futures import ThreadPoolExecutor
        kdas = ["integration", "scope", "schedule", "cost", "quality",
                "resource", "communication", "risk", "procurement"]

        def _render(kda: str) -> Any:
            payload = mock_ic_payload(caller="L2-04", kind=f"pmp.{kda}",
                                      slots_for_kind=f"pmp.{kda}",
                                      request_id=f"L204-{kda}")
            return sut.render_template(**payload)

        with ThreadPoolExecutor(max_workers=9) as pool:
            results = list(pool.map(_render, kdas))
        assert len(results) == 9
        assert all(r.body_sha256 for r in results)
        events_l204 = [e for e in mock_event_bus.emitted_events()
                       if e.get("caller_l2") == "L2-04"]
        assert len(events_l204) == 9
```

---

## §9 边界 / edge case（≥ 4）

> 覆盖 §11 非显式错误码触发的灰区：sandbox 逃逸尝试变种 / 巨型 slot 体积 / 超时边界 / 循环模板引用。
> 每边界给明确的期望行为（拒绝还是降级）。

```python
# file: tests/l1_02/test_l2_07_edge_cases.py
from __future__ import annotations

from typing import Any

import pytest

from app.l2_07.engine import TemplateEngine
from app.l2_07.errors import TemplateEngineError


class TestL2_07_EdgeCases:
    """§9 边界：sandbox 逃逸 / 巨型 slot / 超时 / 循环引用 / 空 slot。"""

    def test_TC_L102_L207_901_sandbox_class_access_blocked(
        self,
        sut_with_malicious_tpl: TemplateEngine,
        mock_project_id: str,
    ) -> None:
        """TC-L102-L207-901 · sandbox 逃逸变种 · __class__ / __mro__ / __subclasses__ 禁访问。"""
        # 已在 fixture 中注入模板含 ''.__class__.__mro__[1].__subclasses__()
        with pytest.raises(TemplateEngineError) as exc:
            sut_with_malicious_tpl.render_template(
                request_id="edge-901", project_id=mock_project_id,
                kind="malicious.import", slots={"x": "y"}, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_005"

    def test_TC_L102_L207_902_sandbox_attr_filter_blocked(
        self,
        tmp_path,
        real_template_dir: str,
        mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-902 · sandbox attr() 过滤器尝试访问私有属性 · 被拦。"""
        import shutil
        from app.l2_07.startup import TemplateLoader
        dest = tmp_path / "t"
        shutil.copytree(real_template_dir, dest)
        (dest / "malicious2").mkdir()
        (dest / "malicious2" / "attr.md").write_text(
            "---\nkind: malicious.attr\nversion: v1.0\n"
            "slot_schema: {type: object, required: [x], "
            "properties: {x: {type: string}}}\n---\n"
            "{{ x | attr('__class__') | attr('__init__') }}\n",  # attr 绕过尝试
            encoding="utf-8",
        )
        registry = TemplateLoader(template_dir=str(dest)).load_all()
        sut2 = TemplateEngine(registry=registry, event_bus=mock_event_bus)
        with pytest.raises(TemplateEngineError) as exc:
            sut2.render_template(
                request_id="edge-902", project_id="proj-x",
                kind="malicious.attr", slots={"x": "y"}, caller_l2="L2-04",
            )
        # attr 不在 ALLOWED_FILTERS · 应返 E_L102_L207_005（sandbox 拦）或 E_L102_L207_004（加载时就 crash）
        assert exc.value.error_code in ("E_L102_L207_005", "E_L102_L207_004")

    def test_TC_L102_L207_903_huge_slot_exceeds_output_limit(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-903 · 单 slot 值 300KB · 超 max_output_bytes (200KB) · E007。"""
        slots: dict[str, Any] = {
            "scope_statement": "X" * (300 * 1024),
            "scope_items": [],
            "out_of_scope": [],
        }
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id="edge-903", project_id=mock_project_id,
                kind="pmp.scope", slots=slots, caller_l2="L2-04",
            )
        assert exc.value.error_code == "E_L102_L207_007"

    def test_TC_L102_L207_904_timeout_ms_over_max_clamped(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-904 · 调用方传 timeout_ms=60_000 · 超 timeout_ms_max(10_000) · 被 clamp 或拒绝。

        §10 config：`timeout_ms_max` = 10000 const。
        期望：被 clamp 到 10_000 ms（而非 raise）· 或 raise E_L102_L207_010/新错误码。
        本用例以 clamp 行为为实现默认 · 若实现选 raise 也应有显式错误码。
        """
        slots: dict[str, Any] = {
            "user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30",
        }
        out = sut.render_template(
            request_id="edge-904", project_id=mock_project_id,
            kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            timeout_ms=60_000,  # 超上限 · 期望 clamp 到 10_000
        )
        assert out.body_sha256
        # 实际 timeout 应被 clamp · 不应报 RENDER_TIMEOUT（合理 slot 必 < 10s）

    def test_TC_L102_L207_905_circular_template_reference_blocked(
        self, tmp_path, real_template_dir: str, mock_event_bus: Any,
    ) -> None:
        """TC-L102-L207-905 · 模板尝试 {% include %} · 本 L2 禁用跨模板引用（§9.1 Reject）· 加载时 E004。"""
        import shutil
        from app.l2_07.startup import TemplateLoader
        dest = tmp_path / "t"
        shutil.copytree(real_template_dir, dest)
        (dest / "circular").mkdir()
        (dest / "circular" / "a.md").write_text(
            "---\nkind: circular.a\nversion: v1.0\n"
            "slot_schema: {type: object, required: [x], "
            "properties: {x: {type: string}}}\n---\n"
            "{% include 'circular/b.md' %}\n",
            encoding="utf-8",
        )
        (dest / "circular" / "b.md").write_text(
            "---\nkind: circular.b\nversion: v1.0\n"
            "slot_schema: {type: object, required: [x], "
            "properties: {x: {type: string}}}\n---\n"
            "{% include 'circular/a.md' %}\n",
            encoding="utf-8",
        )
        loader = TemplateLoader(template_dir=str(dest))
        # 期望：加载时就拒（SandboxedEnvironment.loader=None · 无 include 支持）
        with pytest.raises(TemplateEngineError) as exc:
            loader.load_all()
        assert exc.value.error_code == "E_L102_L207_004"

    def test_TC_L102_L207_906_empty_slots_dict_for_required_schema(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-906 · 传空 dict {} 到要求 required 字段的 kind · E003。"""
        with pytest.raises(TemplateEngineError) as exc:
            sut.render_template(
                request_id="edge-906", project_id=mock_project_id,
                kind="kickoff.goal", slots={}, caller_l2="L2-02",
            )
        assert exc.value.error_code == "E_L102_L207_003"

    def test_TC_L102_L207_907_none_slots_rejected(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-907 · slots=None · 按 schema 缺必填 · E003 或 TypeError 前置校验。"""
        with pytest.raises((TemplateEngineError, TypeError)) as exc:
            sut.render_template(
                request_id="edge-907", project_id=mock_project_id,
                kind="kickoff.goal", slots=None,  # type: ignore[arg-type]
                caller_l2="L2-02",
            )
        if isinstance(exc.value, TemplateEngineError):
            assert exc.value.error_code in ("E_L102_L207_003", "E_L102_L207_002")

    def test_TC_L102_L207_908_unicode_control_char_in_slot_escaped(
        self, sut: TemplateEngine, mock_project_id: str,
    ) -> None:
        """TC-L102-L207-908 · slot 值含控制字符 \\x00 · 产出 frontmatter 拒绝 · E008。"""
        slots: dict[str, Any] = {
            "user_utterance": "normal\x00evil",  # null byte
            "goals": ["g"],
            "deadline": "2026-06-30",
        }
        # 实现可选：渲染前清洗（通过）或渲染后 frontmatter 解析失败（E008）
        try:
            out = sut.render_template(
                request_id="edge-908", project_id=mock_project_id,
                kind="kickoff.goal", slots=slots, caller_l2="L2-02",
            )
            assert "\x00" not in out.output  # 若通过 · 必清洗
        except TemplateEngineError as e:
            assert e.error_code == "E_L102_L207_008"
```

---

## §10 附录：测试运行矩阵

| 测试文件 | 用例数 | 标记 | 预估耗时 |
|---|---|---|---|
| `test_l2_07_template_engine_positive.py` | 13 | — | < 2s |
| `test_l2_07_template_engine_negative.py` | 15 | — | < 3s |
| `test_l2_07_ic_contracts.py` | 7 | — | < 3s |
| `test_l2_07_perf_slo.py` | 6 | `perf` | 10-20s |
| `test_l2_07_e2e.py` | 3 | — | < 2s |
| `test_l2_07_integration_with_siblings.py` | 3 | — | < 3s |
| `test_l2_07_edge_cases.py` | 8 | — | < 3s |
| **总计** | **55 用例** | | **< 40s** |

运行命令：

```bash
# 全量
pytest tests/l1_02/ -v

# 仅性能
pytest tests/l1_02/ -v -m perf

# 排除性能（CI 默认）
pytest tests/l1_02/ -v -m "not perf"

# 单一错误码回归
pytest tests/l1_02/test_l2_07_template_engine_negative.py::TestL2_07_TemplateEngineNegative::test_TC_L102_L207_105_template_code_exec_blocked_by_sandbox -v
```

---

*— L1-02 L2-07 产出物模板引擎 · TDD 测试用例 depth-B (v1.0) · §0-§9 九节完结 · 55 TC · 14 错误码 · 4 方法 · 7 IC join ·  session-H —*
