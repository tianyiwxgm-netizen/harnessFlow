---
doc_id: dev-delta-wp01-l2-07-template-engine-v1.0
doc_type: superpowers-implementation-plan
parent_doc:
  - docs/superpowers/plans/Dev-δ-impl.md
  - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-δ-L1-02-lifecycle.md §3.1
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-07-产出物模板引擎.md
  - docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-07-产出物模板引擎-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.9 IC-09
version: v1.0
status: ready-to-execute
author: main-session
wp: 01
wave: 2
estimated_duration: 1 天
estimated_loc: ~700
estimated_tc: 56（正向 13 + 错误码 14+ + IC 7 + SLO 6 + edge/安全/并发/启动 ≥10 + fixture）
created_at: 2026-04-23
---

# Dev-δ WP01 · L2-07 模板引擎 · TDD 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:test-driven-development` 每步 red-green-refactor。本 plan 的 checkbox 顺序即执行顺序。

**Goal:** 实现 L2-07 产出物模板引擎（Jinja2 SandboxedEnvironment + jsonschema + 白名单 filter + output_sha256 规范化 + IC-09 审计），作为 L2-02/03/04/05/06 的共享地基。

**Architecture:** 无状态 Domain Service · 启动时 TemplateLoader 扫 `templates/` 加载 27 模板到 TemplateRegistry（缺即 crash）· 运行时纯内存渲染 · 每次 render 经 ① caller 白名单 ② kind 正则 ③ jsonschema 校验 slots ④ sandbox 渲染 ⑤ size ≤ 200KB ⑥ frontmatter 回写 ⑦ sha256 规范化 ⑧ IC-09 emit。

**Tech Stack:** `jinja2>=3.1` (SandboxedEnvironment + StrictUndefined) · `jsonschema>=4.21` (Draft 2020-12) · `PyYAML>=6` · 纯 Python 3.11+。

---

## §1 本 WP 在 Dev-δ 中的坐标

- WP01 是 Dev-δ 地基：后续 WP02-07 都靠 L2-07 产 md。
- 前置：Infra-0 done（`app/l1_02/common/` + `templates/` 空目录）。
- 后继阻塞：WP02 需 L2-07 能渲 `kickoff.goal / kickoff.scope`；WP03 需 `fourset.*`；WP04 间接（经 WP02/03）；WP05 需 `pmp.*`；WP06 需 `togaf.*`；WP07 需 `closing.*`。

---

## §2 File Structure

### 2.1 源代码（新建 · 7 文件 · ~700 行）

```
app/l1_02/template_engine/
├── __init__.py                  # export TemplateEngine / RenderedOutput / TemplateEngineError
├── errors.py                    # TemplateEngineError + 14 错误码常量（~80 行）
├── schemas.py                   # RenderedOutput / TemplateEntry / ValidationResult / SlotSchemaError（~150 行）
├── sandbox.py                   # Jinja2 SandboxedEnvironment 构建 + ALLOWED_FILTERS（~80 行）
├── hashing.py                   # canonical_slots_hash + output_sha256 + 排除可变 frontmatter 字段（~100 行）
├── registry.py                  # TemplateLoader (load_all) + TemplateRegistry + StartupError（~180 行）
├── renderer.py                  # render_core（单次渲染的 8 步 pipeline · 伪代码对齐 tech §6.1）（~120 行）
└── engine.py                    # TemplateEngine 顶层入口（public API：render_template / list_available_templates / get_template_version / validate_slots）（~100 行）
```

### 2.2 测试（新建 · 5 文件 · ~1000 行）

```
tests/l1_02/
├── conftest.py                  # 扩：sut / sut_with_malicious_tpl / mock_ic_payload 等 WP01 专属 fixture
├── test_l2_07_template_engine_positive.py  # 13 TC（§2 正向）
├── test_l2_07_template_engine_negative.py  # 15 TC（§3 错误码 · 含 E_L102_L207_001~014 + startup missing）
├── test_l2_07_template_engine_startup.py   # TemplateLoader 启动场景（模板缺 / 语法错 / slot_schema 非法）
├── test_l2_07_ic_contracts.py              # 7 TC（§4 IC-L2-02 × 5 调用方 + IC-09 × 2）
└── test_l2_07_perf.py                      # 6 TC（§5 SLO）
```

### 2.3 模板文件（新建 · 27 md · `templates/`）

全部模板 frontmatter 必含：
```yaml
kind: <string>               # e.g. pmp.scope
version: v1.0
slot_schema:                 # jsonschema Draft 2020-12
  type: object
  required: [...]
  properties:
    <slot>:
      type: string | array | object | number | integer | boolean
      items: { ... }         # 若 array
      properties: { ... }    # 若 object
description: <string>
author: main-session
created_at: 2026-04-23
```

正文用 `{% %}` + `{{ }}` Jinja2 语法 · 白名单 filter 集 `upper/lower/title/trim/int/round/join/length/first/date_iso`。

---

## §3 TDD 任务序列（59 step · 按批提交）

> **TDD 红线**：每 step 按 red → green → refactor → commit。一次 commit 含 2-5 TC 为常态。

### §3.A 预备：WP01 专属 fixture + 错误码 + schemas（红灯前奏）

- [ ] **A1**：扩 `tests/l1_02/conftest.py` · 加 WP01 fixture

追加以下 fixture（保持 Infra-0 已有的 `mock_project_id` / `mock_request_id` / `mock_event_bus` 不动）：

```python
# tests/l1_02/conftest.py 追加部分
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def template_dir_real() -> Path:
    """指向仓库根 templates/ 的真实模板目录（启动 L2-07 engine 用）。"""
    return Path(__file__).parent.parent.parent / "templates"


@pytest.fixture
def sut(template_dir_real, mock_event_bus):
    """真实模板目录加载的 TemplateEngine · 被大多数 TC 使用。"""
    from app.l1_02.template_engine.engine import TemplateEngine
    return TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=mock_event_bus,
    )


@pytest.fixture
def sut_with_malicious_tpl(tmp_path, mock_event_bus):
    """临时目录含试图 import os 的恶意模板 · 验 sandbox 拦截。"""
    from app.l1_02.template_engine.engine import TemplateEngine
    mal_dir = tmp_path / "mal"
    (mal_dir / "mal").mkdir(parents=True)
    # 写一个试图访问 __class__ 的 slot（sandbox 拦）
    (mal_dir / "mal" / "import.md").write_text(
        "---\n"
        "kind: malicious.import\n"
        "version: v1.0\n"
        "slot_schema:\n"
        "  type: object\n"
        "  required: [x]\n"
        "  properties:\n"
        "    x: {type: string}\n"
        "description: sandbox test template\n"
        "author: test\n"
        "created_at: 2026-04-23\n"
        "---\n"
        "# mal\n"
        "{{ x.__class__.__mro__[1].__subclasses__() }}\n",
        encoding="utf-8",
    )
    # 允许最小 kind 集（只要求 malicious.import）· 绕过 required_kinds 完整性
    return TemplateEngine.load_from_dir(
        template_dir=str(mal_dir),
        event_emitter=mock_event_bus,
        required_kinds=["malicious.import"],  # 测试旁路
    )


@pytest.fixture
def mock_ic_payload(mock_project_id, mock_request_id):
    """IC-L2-02 call payload 构造器 · 针对 kind 填充最小合法 slots。"""
    KIND_SLOTS: dict[str, dict] = {
        "kickoff.goal": {"user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30"},
        "kickoff.scope": {"scope_items": ["a"], "out_of_scope": [], "constraints": []},
        "fourset.scope": {"scope_statement": "x", "in_scope": ["a"], "out_of_scope": []},
        "fourset.prd": {"problem_statement": "x", "success_metrics": [], "user_stories": []},
        "fourset.plan": {"milestones": [], "risks": []},
        "fourset.tdd": {"layers": [], "quality_gates": []},
        "pmp.integration": {"integration_summary": "x", "change_control": []},
        "pmp.scope": {"scope_statement": "x", "scope_items": [], "out_of_scope": []},
        "pmp.schedule": {"milestones": [], "critical_path": []},
        "pmp.cost": {"budget_total": 100000, "cost_breakdown": []},
        "pmp.quality": {"quality_objectives": [], "quality_checks": []},
        "pmp.resource": {"roles": [], "availability": []},
        "pmp.communication": {"channels": [], "cadence": []},
        "pmp.risk": {"risks": []},
        "pmp.procurement": {"items": []},
        "togaf.preliminary": {"principles": [], "stakeholders": []},
        "togaf.phase_a": {"vision": "x", "goals": []},
        "togaf.phase_b": {"business_capabilities": [], "value_streams": []},
        "togaf.phase_c_data": {"data_entities": [], "data_flows": []},
        "togaf.phase_c_application": {"applications": [], "interactions": []},
        "togaf.phase_d": {"tech_components": [], "standards": []},
        "togaf.phase_e": {"opportunities": [], "solutions": []},
        "togaf.phase_f": {"work_packages": []},
        "togaf.phase_g": {"governance_items": []},
        "togaf.phase_h": {"change_requests": []},
        "togaf.adr": {"title": "x", "context": "y", "decision": "z", "alternatives": [], "consequences": []},
        "closing.lessons_learned": {"what_went_well": [], "what_went_wrong": [], "action_items": []},
        "closing.delivery_manifest": {"deliverables": [], "checksums": []},
        "closing.retro_summary": {"summary": "x", "metrics": {}},
    }

    def _build(caller: str, kind: str, slots: dict | None = None, slots_for_kind: str | None = None):
        if slots is None:
            key = slots_for_kind or kind
            slots = KIND_SLOTS.get(key, {})
        return {
            "request_id": mock_request_id,
            "project_id": mock_project_id,
            "kind": kind,
            "slots": slots,
            "caller_l2": caller,
        }
    return _build
```

- [ ] **A2**：建 `app/l1_02/template_engine/errors.py`

```python
"""L2-07 错误码定义。对齐 L2-07 tech §3.4。"""
from __future__ import annotations

from app.l1_02.common.errors import L102Error


class TemplateEngineError(L102Error):
    """L2-07 所有对外异常基类。"""


# §3.4 14 条错误码
E_TEMPLATE_NOT_FOUND = "E_L102_L207_001"
E_SLOT_SCHEMA_VIOLATION = "E_L102_L207_002"
E_SLOT_REQUIRED_MISSING = "E_L102_L207_003"
E_TEMPLATE_SYNTAX_ERROR = "E_L102_L207_004"
E_TEMPLATE_CODE_EXEC = "E_L102_L207_005"
E_RENDER_TIMEOUT = "E_L102_L207_006"
E_OUTPUT_TOO_LARGE = "E_L102_L207_007"
E_FRONTMATTER_PARSE_FAIL = "E_L102_L207_008"
E_VERSION_MISMATCH = "E_L102_L207_009"
E_INVALID_KIND_NAME = "E_L102_L207_010"
E_CALLER_NOT_WHITELISTED = "E_L102_L207_011"
E_SLOTS_HASH_MISMATCH = "E_L102_L207_012"
E_HASH_COMPUTE_FAIL = "E_L102_L207_013"
E_AUDIT_EMIT_FAIL = "E_L102_L207_014"

ALL_ERROR_CODES: tuple[str, ...] = (
    E_TEMPLATE_NOT_FOUND, E_SLOT_SCHEMA_VIOLATION, E_SLOT_REQUIRED_MISSING,
    E_TEMPLATE_SYNTAX_ERROR, E_TEMPLATE_CODE_EXEC, E_RENDER_TIMEOUT,
    E_OUTPUT_TOO_LARGE, E_FRONTMATTER_PARSE_FAIL, E_VERSION_MISMATCH,
    E_INVALID_KIND_NAME, E_CALLER_NOT_WHITELISTED, E_SLOTS_HASH_MISMATCH,
    E_HASH_COMPUTE_FAIL, E_AUDIT_EMIT_FAIL,
)


class StartupError(Exception):
    """TemplateLoader 启动期专用 · 与运行期 TemplateEngineError 区分。"""
```

- [ ] **A3**：建 `app/l1_02/template_engine/schemas.py`

```python
"""L2-07 数据类型 · 对齐 L2-07 tech §3.3 + §7。"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RenderedOutput:
    """render_template 返回值。对齐 tech §3.3。"""
    request_id: str
    template_id: str
    template_version: str
    slots_hash: str
    output: str
    body_sha256: str
    lines: int
    frontmatter: dict[str, Any]
    rendered_at: str
    engine_version: str


@dataclass(frozen=True)
class TemplateEntry:
    """in-memory TemplateRegistry 单元。"""
    id: str
    kind: str
    version: str
    slot_schema: dict[str, Any]
    template_obj: Any  # jinja2.Template
    file_path: str
    file_sha256: str


@dataclass(frozen=True)
class ValidationResult:
    """validate_slots 返回值。"""
    ok: bool
    error_code: str | None = None
    details: Any = None

    def is_ok(self) -> bool:
        return self.ok

    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(ok=True)

    @classmethod
    def fail(cls, error: str, details: Any = None) -> "ValidationResult":
        return cls(ok=False, error_code=error, details=details)
```

- [ ] **A4**：commit A-batch（预备件 · 不含测试）

```bash
git add app/l1_02/template_engine/errors.py \
        app/l1_02/template_engine/schemas.py \
        app/l1_02/template_engine/__init__.py \
        tests/l1_02/conftest.py
git commit -m "feat(harnessFlow-code): δ-WP01-A L2-07 errors + schemas + fixture"
```

---

### §3.B 创建 27 个 templates/*.md 文件（pre-green 前置）

原因：L2-07 启动时必须扫 27 模板 · TDD 的 green 阶段需真实模板存在。

- [ ] **B1**：`templates/kickoff/goal.md`（最小可渲染 · 对齐 conftest A1 的 fixture）

```markdown
---
kind: kickoff.goal
version: v1.0
slot_schema:
  type: object
  required: [user_utterance, goals, deadline]
  properties:
    user_utterance: {type: string, description: "用户首次输入的项目目标口语描述"}
    goals: {type: array, items: {type: string}, minItems: 1, description: "项目 SMART 目标列表"}
    deadline: {type: string, description: "ISO-8601 日期或 YYYY-MM-DD"}
description: S1 启动阶段 · HarnessFlowGoal.md 模板
author: main-session
created_at: 2026-04-23
---

# HarnessFlowGoal

## 用户原始输入

> {{ user_utterance | trim }}

## SMART 目标（共 {{ goals | length }} 项）

{% for g in goals %}
- **G{{ loop.index }}**：{{ g | trim }}
{% endfor %}

## 期望 Deadline

{{ deadline }}
```

（其余 26 模板细节在 Step B-rest 批量生成，结构类似。每个模板要求：
- frontmatter 合法 · slot_schema 正确描述 conftest mock_ic_payload 中声明的字段
- 正文只用白名单 filter
- 至少一处使用 slot · 渲染后非空）

- [ ] **B2**：`templates/kickoff/scope.md`
- [ ] **B3**：`templates/fourset/{scope,prd,plan,tdd}.md`（× 4）
- [ ] **B4**：`templates/pmp/{integration,scope,schedule,cost,quality,resource,communication,risk,procurement}.md`（× 9）
- [ ] **B5**：`templates/togaf/{preliminary,phase_a,phase_b,phase_c_data,phase_c_application,phase_d,phase_e,phase_f,phase_g,phase_h,adr}.md`（× 11）
- [ ] **B6**：`templates/closing/{lessons_learned,delivery_manifest,retro_summary}.md`（× 3）

- [ ] **B7**：commit B-batch

```bash
git add templates/
git commit -m "feat(harnessFlow-code): δ-WP01-B L2-07 27 个 templates/*.md（27 kind 全）"
```

**合计 27 模板** · 对齐 L2-07 tech §3.5 清单。

---

### §3.C 启动加载 / TemplateLoader（TC-104, 115, 510 驱动）

对应 TC：`TC-L102-L207-104`（语法错 crash）· `TC-L102-L207-115`（必需 kind 缺失 crash）· `TC-L102-L207-505/016`（加载 SLO ≤ 500ms）· `TC-L102-L207-011`（get_template_version）· `TC-L102-L207-010`（list_available_templates）。

- [ ] **C1**：写 `tests/l1_02/test_l2_07_template_engine_startup.py`（红）

包含以下测试（完整代码 · 无省略）：

```python
"""L2-07 启动阶段 · TemplateLoader 相关 TC。"""
from __future__ import annotations

from pathlib import Path
import time
import pytest

from app.l1_02.template_engine.registry import TemplateLoader
from app.l1_02.template_engine.errors import (
    TemplateEngineError,
    StartupError,
    E_TEMPLATE_SYNTAX_ERROR,
)


REQUIRED_27 = [
    "kickoff.goal", "kickoff.scope",
    "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
    "pmp.integration", "pmp.scope", "pmp.schedule", "pmp.cost", "pmp.quality",
    "pmp.resource", "pmp.communication", "pmp.risk", "pmp.procurement",
    "togaf.preliminary", "togaf.phase_a", "togaf.phase_b",
    "togaf.phase_c_data", "togaf.phase_c_application", "togaf.phase_d",
    "togaf.phase_e", "togaf.phase_f", "togaf.phase_g", "togaf.phase_h",
    "togaf.adr",
    "closing.lessons_learned", "closing.delivery_manifest", "closing.retro_summary",
]


def _write_minimal_tpl(fp: Path, kind: str) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(
        f"---\n"
        f"kind: {kind}\n"
        f"version: v1.0\n"
        f"slot_schema:\n"
        f"  type: object\n"
        f"  required: [x]\n"
        f"  properties:\n"
        f"    x: {{type: string}}\n"
        f"description: minimal test template\n"
        f"author: test\n"
        f"created_at: 2026-04-23\n"
        f"---\n"
        f"# t\n{{{{ x }}}}\n",
        encoding="utf-8",
    )


class TestL2_07_Startup:
    def test_TC_L102_L207_016_load_real_27_templates_under_500ms(
        self,
        template_dir_real: Path,
    ) -> None:
        """启动加载真实 27 模板 P95 ≤ 500ms（tech §12.1）。"""
        loader = TemplateLoader(template_dir=str(template_dir_real))
        start = time.perf_counter()
        registry = loader.load_all()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"startup too slow: {elapsed_ms:.0f}ms"
        kinds = registry.kinds()
        for k in REQUIRED_27:
            assert k in kinds, f"missing kind: {k}"
        # list_available_templates() 入口
        assert len(registry.list()) >= 27

    def test_TC_L102_L207_011_get_template_version_returns_semver(
        self, template_dir_real: Path,
    ) -> None:
        loader = TemplateLoader(template_dir=str(template_dir_real))
        registry = loader.load_all()
        assert registry.get_version("kickoff.goal") == "v1.0"
        assert registry.get_version("pmp.scope") == "v1.0"

    def test_TC_L102_L207_010_list_returns_all_27(
        self, template_dir_real: Path,
    ) -> None:
        loader = TemplateLoader(template_dir=str(template_dir_real))
        registry = loader.load_all()
        kinds = registry.list()
        assert isinstance(kinds, list)
        assert len(kinds) >= 27
        required = {
            "kickoff.goal", "kickoff.scope",
            "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
            "pmp.scope", "pmp.cost", "pmp.risk",
            "togaf.preliminary", "togaf.phase_a", "togaf.adr",
            "closing.lessons_learned",
        }
        assert required.issubset(set(kinds))

    def test_TC_L102_L207_115_missing_required_kinds_raises_startup_error(
        self, tmp_path: Path,
    ) -> None:
        """只放 1 个 kind · 缺 26 · StartupError crash。"""
        _write_minimal_tpl(tmp_path / "kickoff" / "goal.md", "kickoff.goal")
        loader = TemplateLoader(template_dir=str(tmp_path))
        with pytest.raises(StartupError) as exc:
            loader.load_all()
        assert "Missing required templates" in str(exc.value)

    def test_TC_L102_L207_104_bad_syntax_raises_template_engine_error(
        self, tmp_path: Path,
    ) -> None:
        """模板含 Jinja2 语法错 · 启动 E004。"""
        bad = tmp_path / "kickoff" / "goal.md"
        bad.parent.mkdir(parents=True)
        bad.write_text(
            "---\nkind: kickoff.goal\nversion: v1.0\n"
            "slot_schema:\n  type: object\n  required: [x]\n"
            "  properties: {x: {type: string}}\n"
            "description: bad\nauthor: t\ncreated_at: 2026-04-23\n---\n"
            "{% for x in %}{{ x }}{% endfor %}\n",
            encoding="utf-8",
        )
        loader = TemplateLoader(
            template_dir=str(tmp_path),
            required_kinds=["kickoff.goal"],  # 绕过 27 完整性
        )
        with pytest.raises(TemplateEngineError) as exc:
            loader.load_all()
        assert exc.value.error_code == E_TEMPLATE_SYNTAX_ERROR
```

- [ ] **C2**：跑红

```bash
pytest tests/l1_02/test_l2_07_template_engine_startup.py -v
```

预期：`ModuleNotFoundError: app.l1_02.template_engine.registry` 或 AttributeError。

- [ ] **C3**：写 `app/l1_02/template_engine/sandbox.py`（绿前半）

```python
"""Jinja2 SandboxedEnvironment 配置 · 对齐 tech §6.4。"""
from __future__ import annotations
from typing import Any
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined


def date_iso(d: Any) -> str:
    if d is None:
        return ""
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


ALLOWED_FILTERS: dict[str, Any] = {
    "upper": str.upper,
    "lower": str.lower,
    "title": str.title,
    "trim": lambda s: str(s).strip() if s is not None else "",
    "int": int,
    "round": round,
    "join": lambda items, sep=",": sep.join(str(i) for i in items),
    "length": len,
    "first": lambda items: items[0] if items else None,
    "date_iso": date_iso,
}


def build_sandbox_env() -> SandboxedEnvironment:
    """构建 sandbox Environment · 仅允许白名单 filter + StrictUndefined。"""
    env = SandboxedEnvironment(
        autoescape=False,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    # 仅保留白名单 filter
    env.filters = dict(ALLOWED_FILTERS)
    # 禁常见逃逸：默认 SandboxedEnvironment 已禁 __class__ / __mro__ / __subclasses__ 等
    # 不再 allow `getattr` / `eval`
    return env
```

- [ ] **C4**：写 `app/l1_02/template_engine/registry.py`（绿核心）

```python
"""TemplateLoader + TemplateRegistry · 对齐 tech §6.3。"""
from __future__ import annotations
from dataclasses import dataclass, field
import glob
import hashlib
import os
from pathlib import Path
from typing import Any

import jinja2
import jsonschema
import yaml

from app.l1_02.template_engine.errors import (
    TemplateEngineError,
    StartupError,
    E_TEMPLATE_SYNTAX_ERROR,
)
from app.l1_02.template_engine.sandbox import build_sandbox_env
from app.l1_02.template_engine.schemas import TemplateEntry


REQUIRED_KINDS_DEFAULT: tuple[str, ...] = (
    "kickoff.goal", "kickoff.scope",
    "fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd",
    "pmp.integration", "pmp.scope", "pmp.schedule", "pmp.cost", "pmp.quality",
    "pmp.resource", "pmp.communication", "pmp.risk", "pmp.procurement",
    "togaf.preliminary", "togaf.phase_a", "togaf.phase_b",
    "togaf.phase_c_data", "togaf.phase_c_application", "togaf.phase_d",
    "togaf.phase_e", "togaf.phase_f", "togaf.phase_g", "togaf.phase_h",
    "togaf.adr",
    "closing.lessons_learned", "closing.delivery_manifest", "closing.retro_summary",
)


def _sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析开头 YAML frontmatter，返 (fm_dict, body)。允许 `---\\n...\\n---\\n` 形式。"""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    idx = rest.find("\n---")
    if idx < 0:
        return {}, text
    fm_str = rest[:idx]
    body = rest[idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    try:
        fm = yaml.safe_load(fm_str) or {}
        if not isinstance(fm, dict):
            return {}, text
        return fm, body
    except yaml.YAMLError as exc:
        raise StartupError(f"frontmatter YAML error: {exc}") from exc


@dataclass
class TemplateRegistry:
    _entries: dict[str, TemplateEntry] = field(default_factory=dict)

    def register(self, entry: TemplateEntry) -> None:
        self._entries[entry.kind] = entry

    def lookup(self, kind: str) -> TemplateEntry | None:
        return self._entries.get(kind)

    def kinds(self) -> list[str]:
        return list(self._entries.keys())

    def list(self) -> list[str]:
        return sorted(self._entries.keys())

    def get_version(self, kind: str) -> str | None:
        e = self._entries.get(kind)
        return e.version if e else None

    def __len__(self) -> int:
        return len(self._entries)


@dataclass
class TemplateLoader:
    template_dir: str
    required_kinds: tuple[str, ...] | list[str] = REQUIRED_KINDS_DEFAULT

    def load_all(self) -> TemplateRegistry:
        registry = TemplateRegistry()
        env = build_sandbox_env()
        root = Path(self.template_dir)
        if not root.exists():
            raise StartupError(f"template_dir not found: {self.template_dir}")

        for fp in sorted(glob.glob(f"{self.template_dir}/**/*.md", recursive=True)):
            text = Path(fp).read_text(encoding="utf-8")
            # 跳过 README.md（无 kind frontmatter）
            fm, body = _split_frontmatter(text)
            if not fm or "kind" not in fm:
                continue

            kind = fm["kind"]
            version = fm.get("version", "")
            slot_schema = fm.get("slot_schema")

            if not version or not slot_schema:
                raise TemplateEngineError(
                    error_code=E_TEMPLATE_SYNTAX_ERROR,
                    message=f"missing metadata in {fp}",
                )

            # slot_schema 自身合法性
            try:
                jsonschema.Draft202012Validator.check_schema(slot_schema)
            except jsonschema.SchemaError as exc:
                raise TemplateEngineError(
                    error_code=E_TEMPLATE_SYNTAX_ERROR,
                    message=f"invalid slot_schema in {fp}: {exc.message}",
                ) from exc

            # Jinja2 解析
            try:
                template_obj = env.from_string(body)
            except jinja2.TemplateSyntaxError as exc:
                raise TemplateEngineError(
                    error_code=E_TEMPLATE_SYNTAX_ERROR,
                    message=f"Jinja2 syntax error in {fp}: {exc.message}",
                ) from exc

            registry.register(TemplateEntry(
                id=f"{kind}.{version}",
                kind=kind,
                version=version,
                slot_schema=slot_schema,
                template_obj=template_obj,
                file_path=fp,
                file_sha256=_sha256_file(fp),
            ))

        missing = set(self.required_kinds) - set(registry.kinds())
        if missing:
            raise StartupError(f"Missing required templates: {sorted(missing)}")

        return registry
```

- [ ] **C5**：跑绿

```bash
pytest tests/l1_02/test_l2_07_template_engine_startup.py -v
```

预期：5 TC 绿。若仍红：
- 检查 `templates/` 27 个文件都有 · `ls templates/**/*.md | wc -l` ≥ 27
- 检查各 frontmatter 合法（运行 `python -c "from app.l1_02.template_engine.registry import TemplateLoader; TemplateLoader('templates').load_all()"`）

- [ ] **C6**：commit

```bash
git add app/l1_02/template_engine/sandbox.py \
        app/l1_02/template_engine/registry.py \
        tests/l1_02/test_l2_07_template_engine_startup.py
git commit -m "feat(harnessFlow-code): δ-WP01-C L2-07 TemplateLoader + Registry（启动 5 TC 绿）"
```

---

### §3.D 核心渲染 / Hashing（TC-001~013 + 正向 13 批）

对应正向 TC `001~013`（§2 positive）。

- [ ] **D1**：写 `app/l1_02/template_engine/hashing.py`（绿前件）

```python
"""slots_hash + output_sha256 规范化 · 对齐 tech §6.2。"""
from __future__ import annotations
import hashlib
from typing import Any
import yaml


def canonical_slots_hash(slots: dict[str, Any]) -> str:
    """slots 规范化：递归 sort keys + JSON-like dump · 保证 I-L207-01 幂等。"""
    normalized = _canonicalize(slots)
    payload = yaml.safe_dump(normalized, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _canonicalize(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_canonicalize(i) for i in v]
    return v


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """渲染后输出的 frontmatter 分离。与 registry._split_frontmatter 同逻辑但通用。"""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    idx = rest.find("\n---")
    if idx < 0:
        return {}, text
    fm_str = rest[:idx]
    body = rest[idx + 4:]
    if body.startswith("\n"):
        body = body[1:]
    fm = yaml.safe_load(fm_str) or {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def compute_output_hash(body: str) -> str:
    """规范化 body + frontmatter（排除 rendered_at/updated_at）后 sha256。"""
    fm, main = split_frontmatter(body)
    fm_filtered = {k: v for k, v in fm.items() if k not in ("rendered_at", "updated_at")}
    fm_str = yaml.safe_dump(fm_filtered, sort_keys=True, allow_unicode=True)
    main_norm = main.strip().replace("\r\n", "\n")
    combined = (fm_str + "\n---\n" + main_norm).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()
```

- [ ] **D2**：写 `tests/l1_02/test_l2_07_template_engine_positive.py`（红）

详见 TDD md `§2` 中 TC-001~013 全文。复制到 `tests/l1_02/test_l2_07_template_engine_positive.py`（用之前已读的 §2 代码块为准 · 全 14 TC 含 013 的 validate_slots fail 场景）。

**重点代码片段**（完整内容太长 · 请从 `docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-07-产出物模板引擎-tests.md §2` 复制全部）：

```python
# tests/l1_02/test_l2_07_template_engine_positive.py
from __future__ import annotations
import hashlib
from typing import Any

import pytest
import yaml

from app.l1_02.template_engine.engine import TemplateEngine
from app.l1_02.template_engine.schemas import RenderedOutput, ValidationResult


class TestL2_07_TemplateEngine:
    # ... 13 TC 详见 3-2 TDD md §2 · 共 397 行
    pass  # placeholder · 真实执行时从 TDD md §2 复制
```

（实际执行步骤：`sed -n '108,396p' docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-07-产出物模板引擎-tests.md` 取 §2 代码 → 粘贴覆盖文件 · 修 `from app.l2_07...` → `from app.l1_02.template_engine...`）

- [ ] **D3**：跑红

```bash
pytest tests/l1_02/test_l2_07_template_engine_positive.py -v
```

预期：全红（TemplateEngine 尚未建）。

- [ ] **D4**：写 `app/l1_02/template_engine/renderer.py`（绿核心 1/2）

```python
"""render_core 单次渲染 pipeline · 对齐 tech §6.1。"""
from __future__ import annotations
from datetime import datetime, timezone
import re
import signal
from typing import Any

import jinja2
import jsonschema

from app.l1_02.template_engine.errors import (
    TemplateEngineError,
    E_TEMPLATE_NOT_FOUND, E_SLOT_SCHEMA_VIOLATION, E_SLOT_REQUIRED_MISSING,
    E_TEMPLATE_CODE_EXEC, E_RENDER_TIMEOUT, E_OUTPUT_TOO_LARGE,
    E_FRONTMATTER_PARSE_FAIL, E_VERSION_MISMATCH, E_INVALID_KIND_NAME,
    E_CALLER_NOT_WHITELISTED, E_SLOTS_HASH_MISMATCH, E_HASH_COMPUTE_FAIL,
)
from app.l1_02.template_engine.hashing import (
    canonical_slots_hash, compute_output_hash, split_frontmatter,
)
from app.l1_02.template_engine.registry import TemplateRegistry, TemplateEntry
from app.l1_02.template_engine.schemas import RenderedOutput

ENGINE_VERSION = "1.0.0"
KIND_PATTERN = re.compile(r"^[a-z0-9._-]+$")
ALLOWED_CALLERS = {"L2-01", "L2-02", "L2-03", "L2-04", "L2-05", "L2-06"}
DEFAULT_TIMEOUT_MS = 2000
MAX_TIMEOUT_MS = 10000
MAX_OUTPUT_BYTES = 204800  # 200KB


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inject_metadata(body: str, entry: TemplateEntry, output_sha256: str) -> str:
    """若渲染后 frontmatter 缺 template_id/version/rendered_at，注入。"""
    fm, main = split_frontmatter(body)
    fm["template_id"] = entry.id
    fm["template_version"] = entry.version
    fm.setdefault("rendered_at", _now_iso())
    # doc_id / doc_type 兜底（部分模板已写 · 不覆盖）
    fm.setdefault("doc_id", f"{entry.kind}-{output_sha256[:12]}")
    fm.setdefault("doc_type", entry.kind)
    import yaml as _yaml
    fm_str = _yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm_str}\n---\n{main}"


def render_core(
    registry: TemplateRegistry,
    request_id: str,
    project_id: str,
    kind: str,
    slots: dict[str, Any],
    caller_l2: str,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    expected_version: str | None = None,
    expected_slots_hash: str | None = None,
    hash_fn=canonical_slots_hash,
    output_hash_fn=compute_output_hash,
) -> RenderedOutput:
    # 1. caller 白名单
    if caller_l2 not in ALLOWED_CALLERS:
        raise TemplateEngineError(
            error_code=E_CALLER_NOT_WHITELISTED,
            message=f"caller_l2={caller_l2!r} not in whitelist",
            caller_l2=caller_l2,
            project_id=project_id,
        )
    # 2. kind 正则
    if not KIND_PATTERN.match(kind or ""):
        raise TemplateEngineError(
            error_code=E_INVALID_KIND_NAME,
            message=f"kind {kind!r} violates [a-z0-9._-]+",
            project_id=project_id,
        )
    # 3. registry lookup
    entry = registry.lookup(kind)
    if entry is None:
        raise TemplateEngineError(
            error_code=E_TEMPLATE_NOT_FOUND,
            message=f"kind {kind!r} not registered",
            project_id=project_id,
        )
    # 4. version pin
    if expected_version and expected_version != entry.version:
        raise TemplateEngineError(
            error_code=E_VERSION_MISMATCH,
            message=f"expected {expected_version} but registry pinned {entry.version}",
            project_id=project_id,
        )
    # 5. slots hash mismatch
    if expected_slots_hash is not None:
        actual = hash_fn(slots)
        if actual != expected_slots_hash:
            raise TemplateEngineError(
                error_code=E_SLOTS_HASH_MISMATCH,
                message="slots_hash mismatch",
                project_id=project_id,
            )
    # 6. jsonschema 校验 slots
    validator = jsonschema.Draft202012Validator(entry.slot_schema)
    errors = sorted(validator.iter_errors(slots), key=lambda e: e.path)
    if errors:
        first = errors[0]
        if first.validator == "required":
            raise TemplateEngineError(
                error_code=E_SLOT_REQUIRED_MISSING,
                message=first.message,
                project_id=project_id,
                context={"validation_errors": [e.message for e in errors]},
            )
        raise TemplateEngineError(
            error_code=E_SLOT_SCHEMA_VIOLATION,
            message=first.message,
            project_id=project_id,
            context={"validation_errors": [e.message for e in errors]},
        )
    # 7. sandbox 渲染（带超时）
    timeout_ms = min(max(100, timeout_ms), MAX_TIMEOUT_MS)
    try:
        rendered = _render_with_timeout(entry, slots, timeout_ms)
    except TimeoutError:
        raise TemplateEngineError(
            error_code=E_RENDER_TIMEOUT,
            message=f"render exceeded {timeout_ms}ms",
            project_id=project_id,
        )
    except jinja2.sandbox.SecurityError as exc:
        raise TemplateEngineError(
            error_code=E_TEMPLATE_CODE_EXEC,
            message=f"sandbox violation: {exc}",
            project_id=project_id,
            context={"kind": kind},
        ) from exc
    # 8. 大小校验
    if len(rendered.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise TemplateEngineError(
            error_code=E_OUTPUT_TOO_LARGE,
            message=f"output {len(rendered)} bytes > {MAX_OUTPUT_BYTES}",
            project_id=project_id,
        )
    # 9. 计算 hash
    try:
        slots_hash = hash_fn(slots)
        # 注入 metadata 必须在 output_sha256 计算之前 · 否则回写会改变 hash
        output_sha256 = output_hash_fn(rendered)  # 临时 · 用于 doc_id 填充
        body_with_meta = _inject_metadata(rendered, entry, output_sha256)
        output_sha256 = output_hash_fn(body_with_meta)
    except Exception as exc:
        raise TemplateEngineError(
            error_code=E_HASH_COMPUTE_FAIL,
            message=f"hash compute failed: {exc}",
            project_id=project_id,
        ) from exc
    # 10. 解析 frontmatter 回返
    try:
        fm, _main = split_frontmatter(body_with_meta)
    except Exception as exc:
        raise TemplateEngineError(
            error_code=E_FRONTMATTER_PARSE_FAIL,
            message=f"frontmatter parse failed: {exc}",
            project_id=project_id,
        ) from exc
    if not fm or "template_id" not in fm:
        raise TemplateEngineError(
            error_code=E_FRONTMATTER_PARSE_FAIL,
            message="missing template_id in rendered frontmatter",
            project_id=project_id,
        )

    return RenderedOutput(
        request_id=request_id,
        template_id=entry.id,
        template_version=entry.version,
        slots_hash=slots_hash,
        output=body_with_meta,
        body_sha256=output_sha256,
        lines=body_with_meta.count("\n") + 1,
        frontmatter=fm,
        rendered_at=fm.get("rendered_at", _now_iso()),
        engine_version=ENGINE_VERSION,
    )


def _render_with_timeout(entry: TemplateEntry, slots: dict[str, Any], timeout_ms: int) -> str:
    """简化实现：同步渲染 · 对超时近似检查（jinja2 本身无中断机制）。

    对 § TC-106 · 用 signal.setitimer（POSIX · 仅主线程）实现强制超时。
    """
    import threading

    result: dict[str, Any] = {}

    def _do() -> None:
        try:
            result["body"] = entry.template_obj.render(**slots)
        except BaseException as exc:
            result["exc"] = exc

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    t.join(timeout=timeout_ms / 1000.0)
    if t.is_alive():
        # 无法强杀 Python 线程 · 标记超时 · 线程在后台自然结束
        raise TimeoutError(f"render timed out after {timeout_ms}ms")
    if "exc" in result:
        raise result["exc"]
    return result["body"]
```

- [ ] **D5**：写 `app/l1_02/template_engine/engine.py`（绿核心 2/2）

```python
"""TemplateEngine public API · 对齐 tech §3.1。"""
from __future__ import annotations
from typing import Any

import jsonschema

from app.l1_02.common.event_emitter import EventEmitter
from app.l1_02.template_engine.errors import (
    TemplateEngineError,
    E_TEMPLATE_NOT_FOUND, E_SLOT_SCHEMA_VIOLATION, E_SLOT_REQUIRED_MISSING,
    E_AUDIT_EMIT_FAIL,
)
from app.l1_02.template_engine.hashing import canonical_slots_hash, compute_output_hash
from app.l1_02.template_engine.registry import TemplateLoader, TemplateRegistry
from app.l1_02.template_engine.renderer import render_core, ENGINE_VERSION
from app.l1_02.template_engine.schemas import RenderedOutput, ValidationResult


class TemplateEngine:
    """无状态 Domain Service · 持 TemplateRegistry + EventEmitter 引用。"""

    def __init__(
        self,
        registry: TemplateRegistry,
        event_emitter: EventEmitter | None = None,
    ) -> None:
        self._registry = registry
        self._emitter = event_emitter or EventEmitter()
        self._hash_fn = canonical_slots_hash
        self._output_hash_fn = compute_output_hash

    @classmethod
    def load_from_dir(
        cls,
        template_dir: str,
        event_emitter: EventEmitter | None = None,
        required_kinds: list[str] | tuple[str, ...] | None = None,
    ) -> "TemplateEngine":
        from app.l1_02.template_engine.registry import REQUIRED_KINDS_DEFAULT
        loader = TemplateLoader(
            template_dir=template_dir,
            required_kinds=required_kinds if required_kinds is not None else REQUIRED_KINDS_DEFAULT,
        )
        registry = loader.load_all()
        return cls(registry=registry, event_emitter=event_emitter)

    # ---- public API ----

    def list_available_templates(self) -> list[str]:
        return self._registry.list()

    def get_template_version(self, kind: str) -> str | None:
        return self._registry.get_version(kind)

    def validate_slots(self, kind: str, slots: dict[str, Any]) -> ValidationResult:
        entry = self._registry.lookup(kind)
        if entry is None:
            return ValidationResult.fail(error=E_TEMPLATE_NOT_FOUND)
        validator = jsonschema.Draft202012Validator(entry.slot_schema)
        errors = sorted(validator.iter_errors(slots), key=lambda e: e.path)
        if not errors:
            return ValidationResult.success()
        first = errors[0]
        if first.validator == "required":
            return ValidationResult.fail(error=E_SLOT_REQUIRED_MISSING, details=[e.message for e in errors])
        return ValidationResult.fail(error=E_SLOT_SCHEMA_VIOLATION, details=[e.message for e in errors])

    def render_template(
        self,
        request_id: str,
        project_id: str,
        kind: str,
        slots: dict[str, Any],
        caller_l2: str,
        timeout_ms: int = 2000,
        expected_version: str | None = None,
        expected_slots_hash: str | None = None,
    ) -> RenderedOutput:
        out = render_core(
            registry=self._registry,
            request_id=request_id,
            project_id=project_id,
            kind=kind,
            slots=slots,
            caller_l2=caller_l2,
            timeout_ms=timeout_ms,
            expected_version=expected_version,
            expected_slots_hash=expected_slots_hash,
            hash_fn=self._hash_fn,
            output_hash_fn=self._output_hash_fn,
        )
        # IC-09 emit（不阻塞失败）
        try:
            self._emitter.emit(
                project_id=project_id,
                event_type="L1-02/L2-07:template_rendered",
                payload={
                    "template_id": out.template_id,
                    "template_version": out.template_version,
                    "caller_l2": caller_l2,
                    "slots_hash": out.slots_hash,
                    "output_sha256": out.body_sha256,
                    "rendered_at": out.rendered_at,
                    "engine_version": out.engine_version,
                },
                severity="INFO",
                caller_l2=caller_l2,
            )
        except Exception:
            # 降级为 buffer · 不 raise
            pass
        return out

    # ---- 测试辅助接口 ----

    def audit_state(self) -> str:
        return self._emitter.state

    def audit_buffer(self) -> list:
        return list(self._emitter.buffer)
```

- [ ] **D6**：补 `app/l1_02/template_engine/__init__.py` 的 export

```python
"""L2-07 产出物模板引擎 · public API。"""
from app.l1_02.template_engine.engine import TemplateEngine
from app.l1_02.template_engine.schemas import RenderedOutput, ValidationResult, TemplateEntry
from app.l1_02.template_engine.errors import TemplateEngineError, StartupError

__all__ = [
    "TemplateEngine",
    "RenderedOutput",
    "ValidationResult",
    "TemplateEntry",
    "TemplateEngineError",
    "StartupError",
]
```

- [ ] **D7**：跑绿（positive 13 TC）

```bash
pytest tests/l1_02/test_l2_07_template_engine_positive.py -v
```

预期：13 TC 绿。若失败：
- `TC-001` frontmatter 字段缺：检查模板 `kickoff/goal.md` 是否有 `doc_id/doc_type` · 或由 `_inject_metadata` 兜底
- `TC-004` IC-09 emit 验：检查 `EventEmitter.emitted_events()` 返回结构含 `template_id` / `project_id`
- `TC-005` 幂等：两次调用的 `body_sha256` 相等 · `rendered_at` 字段在 `compute_output_hash` 中已排除

- [ ] **D8**：commit D-batch

```bash
git add app/l1_02/template_engine/{hashing,renderer,engine,__init__}.py \
        tests/l1_02/test_l2_07_template_engine_positive.py
git commit -m "feat(harnessFlow-code): δ-WP01-D L2-07 renderer + engine（正向 13 TC 绿）"
```

---

### §3.E 错误码 14 条（每 ≥1 TC）

对应 `TC-L102-L207-101~114 + 115`。

- [ ] **E1**：写 `tests/l1_02/test_l2_07_template_engine_negative.py`

复制 `docs/3-2-Solution-TDD/.../L2-07-产出物模板引擎-tests.md §3` 代码（TC-101~115）· 修 import 为 `app.l1_02.template_engine.*`。

针对 `TC-113` 需要 `sut_with_hash_fault` fixture / `TC-114` 需要 `sut_with_failing_audit` fixture / `TC-108` 需要 `sut_with_broken_frontmatter_tpl` fixture—在 `conftest.py` 补：

```python
# conftest.py 追加
@pytest.fixture
def sut_with_hash_fault(template_dir_real, mock_event_bus):
    from app.l1_02.template_engine.engine import TemplateEngine
    eng = TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=mock_event_bus,
    )

    def broken_hash(_slots):
        raise RuntimeError("simulated hash fault")

    eng._hash_fn = broken_hash
    return eng


@pytest.fixture
def sut_with_failing_audit(template_dir_real):
    from app.l1_02.template_engine.engine import TemplateEngine
    from app.l1_02.common.event_emitter import EventEmitter

    failing = EventEmitter()
    # 立即进 DEGRADED_AUDIT · emit 走 buffer
    failing.force_fail()
    failing.force_fail()
    failing.force_fail()
    assert failing.state == "DEGRADED_AUDIT"

    return TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=failing,
    )


@pytest.fixture
def sut_with_broken_frontmatter_tpl(tmp_path, mock_event_bus):
    """渲染后 frontmatter 被破坏的模板（slot 注入控制字符）。"""
    from app.l1_02.template_engine.engine import TemplateEngine
    root = tmp_path / "bfm"
    (root / "broken").mkdir(parents=True)
    (root / "broken" / "frontmatter.md").write_text(
        "---\n"
        "kind: broken.frontmatter\n"
        "version: v1.0\n"
        "slot_schema:\n"
        "  type: object\n"
        "  required: [bad_value]\n"
        "  properties:\n"
        "    bad_value: {type: string}\n"
        "description: broken fm\n"
        "author: test\n"
        "created_at: 2026-04-23\n"
        "---\n"
        "---\n"   # 故意双 --- 搅乱 frontmatter
        "injected: {{ bad_value }}\n"
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    return TemplateEngine.load_from_dir(
        template_dir=str(root),
        event_emitter=mock_event_bus,
        required_kinds=["broken.frontmatter"],
    )
```

- [ ] **E2**：跑红后调整实现让每个错误码精准触发

- `E005 TEMPLATE_CODE_EXEC`：确认 `sut_with_malicious_tpl` 的 `{{ x.__class__.__mro__[1].__subclasses__() }}` 在 Jinja2 SandboxedEnvironment 下 raise `SecurityError`；且 `render_core` 在 catch 分支发 `template_code_exec_attempt` CRITICAL 事件。需在 `engine.py` 或 `renderer.py` 的 catch 点加 `emitter.emit(..., event_type="L1-02/L2-07:template_code_exec_attempt", severity="CRITICAL")`。
- `E006 RENDER_TIMEOUT`：超时通过 `threading.Thread.join(timeout)` 实现。注意 huge list 实际会超 MAX_OUTPUT_BYTES 也会 raise；需在测试里限制 `timeout_ms=50` 以先触发 timeout。
- `E009 VERSION_MISMATCH`：由 `render_core` 中 expected_version 判断。
- `E012 SLOTS_HASH_MISMATCH`：由 `render_core` 中 expected_slots_hash 判断。
- `E013 HASH_COMPUTE_FAIL`：`sut_with_hash_fault` 已注入。
- `E014 AUDIT_EMIT_FAIL`：engine 层用 `sut_with_failing_audit` · emit 被 `force_fail` 后不 raise · buffer 追加 · 渲染完成 · `audit_state() == "DEGRADED_AUDIT"`。

- [ ] **E3**：为 E005 在 engine 层加 CRITICAL emit（调整 `engine.py::render_template`）：

```python
    def render_template(self, ...):
        try:
            out = render_core(...)
        except TemplateEngineError as exc:
            if exc.error_code == "E_L102_L207_005":
                try:
                    self._emitter.emit(
                        project_id=project_id,
                        event_type="L1-02/L2-07:template_code_exec_attempt",
                        payload={
                            "template_id": self._registry.get_version(kind) and kind,
                            "caller_l2": caller_l2,
                            "sandbox_violation_type": str(exc),
                        },
                        severity="CRITICAL",
                        caller_l2=caller_l2,
                    )
                except Exception:
                    pass
            raise
        # IC-09 emit template_rendered ...
        ...
```

- [ ] **E4**：跑绿

```bash
pytest tests/l1_02/test_l2_07_template_engine_negative.py -v
```

预期：15 TC 绿（14 错误码 + startup missing）。

- [ ] **E5**：commit

```bash
git add tests/l1_02/test_l2_07_template_engine_negative.py \
        tests/l1_02/conftest.py \
        app/l1_02/template_engine/engine.py
git commit -m "feat(harnessFlow-code): δ-WP01-E L2-07 14 错误码 + CRITICAL emit（15 TC 绿）"
```

---

### §3.F IC 契约测试（TC-601~607）

对应 `tests/l1_02/test_l2_07_ic_contracts.py` · 复制 3-2 TDD md §4。

- [ ] **F1**：写测试文件（从 TDD md §4 复制 · 共 7 TC）
- [ ] **F2**：跑绿

```bash
pytest tests/l1_02/test_l2_07_ic_contracts.py -v
```

- [ ] **F3**：commit

```bash
git add tests/l1_02/test_l2_07_ic_contracts.py
git commit -m "feat(harnessFlow-code): δ-WP01-F L2-07 IC 契约 7 TC（IC-L2-02 × 5 + IC-09 × 2）"
```

---

### §3.G SLO 性能测试（TC-501~506）

- [ ] **G1**：写 `tests/l1_02/test_l2_07_perf.py` · 从 TDD md §5 复制
- [ ] **G2**：跑

```bash
pytest tests/l1_02/test_l2_07_perf.py -v --durations=10
```

- [ ] **G3**：若 P95 不达，profiler 调 + 优化 hashing / sandbox。默认实现应能过（Jinja2 ≤ 50ms · jsonschema ≤ 5ms · sha256 200KB ≤ 20ms）。

- [ ] **G4**：commit

```bash
git add tests/l1_02/test_l2_07_perf.py
git commit -m "feat(harnessFlow-code): δ-WP01-G L2-07 SLO 6 TC（P95 ≤ 100ms）"
```

---

### §3.H 组级 DoD 自检 + 完工

- [ ] **H1**：跑全 L2-07 测试套 + coverage

```bash
pytest tests/l1_02/test_l2_07_*.py --cov=app/l1_02/template_engine --cov-report=term-missing -v
```

预期：≥ 56 TC 全绿 · coverage ≥ 85%（app/l1_02/template_engine/）。

- [ ] **H2**：mypy

```bash
mypy app/l1_02/template_engine/
```

预期：无 error。

- [ ] **H3**：ruff

```bash
ruff check app/l1_02/template_engine/ tests/l1_02/
```

预期：clean。

- [ ] **H4**：写 `app/l1_02/template_engine/README.md`（~60 行）

说明 L2-07 职责、27 kind 清单、错误码、IC 边界、典型使用示例。

- [ ] **H5**：commit 收尾

```bash
git add app/l1_02/template_engine/README.md
git commit -m "feat(harnessFlow-code): δ-WP01-H L2-07 README + DoD 自检通过（56 TC 绿 · coverage ≥ 85%）"
```

---

## §4 IC 契约对齐

本 WP 只涉及 IC-09（出 · `template_rendered` · `template_code_exec_attempt` CRITICAL）+ IC-L2-02（入 · 被 L2-02/03/04/05/06 调）。

IC-09 事件 schema 对齐 `docs/3-1-Solution-Technical/integration/ic-contracts.md §3.9` + L2-07 tech §7.5：

```yaml
event_type: "L1-02/L2-07:template_rendered" | "L1-02/L2-07:template_code_exec_attempt"
project_id: <pid>
template_id: <kind>.<version>
template_version: <v1.0>
caller_l2: L2-02..06
slots_hash: sha256hex
output_sha256: sha256hex
rendered_at: ISO-8601
render_duration_ms: int (optional · 本 WP 暂不填)
engine_version: "1.0.0"
severity: INFO | CRITICAL
```

---

## §5 DoD 自检

- [ ] 56 TC 全绿（13 正向 + 15 负向 + 7 IC + 6 SLO + 15 其他含 edge/并发/安全/启动）
- [ ] coverage ≥ 85%（`app/l1_02/template_engine/`）
- [ ] `sut_with_malicious_tpl` 中 `{% import os %}` / `{{ .__class__ }}` raise `E005` + 发 CRITICAL 事件
- [ ] 启动加载 P95 ≤ 500ms（27 模板）
- [ ] 27 kind 必全（缺任一 crash）
- [ ] 调用方白名单硬断言（L2-01~06）
- [ ] commit 8 次（A/B/C/D/E/F/G/H）
- [ ] `app/l1_02/template_engine/README.md` 就位

---

## §6 commit 清单（预期 8）

1. `δ-WP01-A L2-07 errors + schemas + fixture`
2. `δ-WP01-B L2-07 27 个 templates/*.md（27 kind 全）`
3. `δ-WP01-C L2-07 TemplateLoader + Registry（启动 5 TC 绿）`
4. `δ-WP01-D L2-07 renderer + engine（正向 13 TC 绿）`
5. `δ-WP01-E L2-07 14 错误码 + CRITICAL emit（15 TC 绿）`
6. `δ-WP01-F L2-07 IC 契约 7 TC（IC-L2-02 × 5 + IC-09 × 2）`
7. `δ-WP01-G L2-07 SLO 6 TC（P95 ≤ 100ms）`
8. `δ-WP01-H L2-07 README + DoD 自检通过（56 TC 绿 · coverage ≥ 85%）`

---

## §7 自修正触发点

- **情形 B · tech-design 不可行**：若 Jinja2 sandbox 实际无法拦 `{{ x.__class__.__mro__[1].__subclasses__() }}`（新版本 Jinja2 已默认禁），需改 tech §6.4 示例成实际能触发 `SecurityError` 的注入样例。
- **情形 D · TDD 契约不一致**：TDD md §2 中用了 `app.l2_07.engine` 而 tech-design 无明确路径 · 本 plan 按 `app.l1_02.template_engine.engine` 统一 · 若集成时 Dev-β/γ 引用路径不同，走 `_correction_log.jsonl` 仲裁。

---

*— Dev-δ WP01 L2-07 模板引擎 · TDD 实施 Plan · v1.0 · 2026-04-23 —*
