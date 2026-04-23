---
doc_id: dev-delta-impl-master-v1.0
doc_type: superpowers-implementation-plan-master
parent_doc:
  - docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-δ-L1-02-lifecycle.md
  - docs/MASTER-SESSION-DISPATCH.md
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/architecture.md
  - docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-01~07.md
  - docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-01~07-tests.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: in-progress
author: main-session
session: Dev-δ
wave: 2-3
estimated_duration: 7 天（δ1 · 4 + δ2 · 3）
estimated_loc: ~13300
estimated_tc: 409 + ≥15 集成
created_at: 2026-04-23
---

# Dev-δ L1-02 项目生命周期编排 · 实施计划（主索引）

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 harnessFlow L1-02 项目生命周期编排域（BC-02）的 7 个 L2 模块 + 组内集成，建立 PM-14 pid 唯一入口（L2-02 创建 · L2-06 归档）+ Stage Gate 硬门控 + PMP/TOGAF 双主干产出器 + 无状态模板引擎。

**Architecture:** 7 L2 都在 `app/l1_02/` 下，按职责分子包；L2-07 模板引擎（Jinja2 SandboxedEnvironment + jsonschema）是横切地基，先实现；L2-02 起点（PM-14 pid 创建入口）+ L2-01 Gate 控制器（IC-01 入口 + 硬禁自动放行）为控制骨架；L2-03/04/05 是产出器（4 件套 + PMP 9 + TOGAF 9 Phase）；L2-06 是收尾（tar.zst + PM-14 归档入口）。所有 L2 共用 `app/l1_02/common/` 的 schema / errors / event 发射工具。

**Tech Stack:** Python 3.11+ · Jinja2 sandboxed (>=3.1) · jsonschema (Draft 2020-12) · ulid-py · pydantic v2 · PyYAML · zstandard (tar.zst) · asyncio.gather（并发） · pytest + pytest-asyncio + pytest-benchmark · mypy 严模式（`app.l1_02` 加 packages）。

---

## §1 子计划文件索引（8 WP + infra）

每 WP 的详细 TDD 步骤分别独立成一份 `Dev-δ-WP0X-*.md` · 按依赖顺序执行。

| WP | 子计划文件 | 主题 | 状态 | 前置 | 估时 | TC |
|:---:|:---|:---|:---:|:---|:---:|:---:|
| Infra-0 | `Dev-δ-infra-0.md` | pyproject + app/l1_02 骨架 + templates/ 目录 | 📝 待写 | — | 0.25 天 | — |
| WP01 | `Dev-δ-WP01-L2-07-template-engine.md` | L2-07 模板引擎（Jinja2 sandboxed） | 📝 已写 | Infra-0 | 1 天 | 56 |
| WP02 | `Dev-δ-WP02-L2-02-kickoff.md` | L2-02 启动阶段 · PM-14 pid 创建 | 📝 待写 | WP01 | 1 天 | 61 |
| WP03 | `Dev-δ-WP03-L2-03-fourset.md` | L2-03 4 件套生产器（并发） | 📝 待写 | WP01+02 | 1 天 | 60 |
| WP04 | `Dev-δ-WP04-L2-01-stage-gate.md` | L2-01 Stage Gate 控制器 · IC-01 | 📝 待写 | WP01-03 | 1 天 | 60 |
| WP05 | `Dev-δ-WP05-L2-04-pmp.md` | L2-04 PMP 9 计划生产器（并发 + 分级降级） | 📝 待写 | WP01+04 | 1.25 天 | 63 |
| WP06 | `Dev-δ-WP06-L2-05-togaf.md` | L2-05 TOGAF ADM 架构生产器 · togaf_d_ready | 📝 待写 | WP01+05 | 1 天 | 55 |
| WP07 | `Dev-δ-WP07-L2-06-closing.md` | L2-06 收尾 · PM-14 归档 tar.zst | 📝 待写 | WP04 | 0.75 天 | 54 |
| WP08 | `Dev-δ-WP08-integration.md` | 组内 S1→S7 mock 全链集成 | 📝 待写 | WP01-07 | 0.5 天 | ≥15 |

**执行规则**：
- 当前 session 先执行 Infra-0 + WP01。
- 每个后续 WP 启动前：先按 `§5 · 子计划骨架` 写对应 `Dev-δ-WP0X-*.md`，再走 TDD 循环。
- 每 WP 完成后 commit + TaskUpdate。

---

## §2 File Structure（全景）

### 2.1 代码目录（新建）

```
app/l1_02/
├── __init__.py
├── common/                      # 组内共享（约 400 行）
│   ├── __init__.py
│   ├── errors.py                # L1-02 错误码基类 + 所有 L2 错误类型
│   ├── event_emitter.py         # IC-09 发射（Dev-α mock）· buffer 降级
│   ├── pid_validator.py         # PM-14 pid 格式校验（ULID）
│   └── schemas.py               # 跨 L2 公共 schema（CallerL2Enum 等）
├── template_engine/             # L2-07 (~700 行)
│   ├── __init__.py
│   ├── engine.py                # TemplateEngine 入口
│   ├── renderer.py              # render_template 核心算法
│   ├── registry.py              # TemplateRegistry + TemplateLoader
│   ├── sandbox.py               # Jinja2 SandboxedEnvironment 配置 + 白名单 filter
│   ├── hashing.py               # slots_hash + output_sha256 规范化
│   ├── errors.py                # E_L102_L207_001~014
│   └── schemas.py               # RenderedOutput / ValidationResult / TemplateEntry
├── kickoff/                     # L2-02 (~800 行)
│   ├── __init__.py
│   ├── producer.py              # produce_kickoff 主入口
│   ├── anchor_hash.py           # compute_anchor_hash（goal+scope concat）
│   ├── activator.py             # activate_project_id (PM-14 硬锁)
│   ├── recovery.py              # recover_draft（崩溃恢复）
│   ├── errors.py                # E_L102_L202_*
│   └── schemas.py               # S1ProductionResult / ProjectManifest
├── four_set/                    # L2-03 (~650 行)
│   ├── __init__.py
│   ├── producer.py              # produce_four_set
│   ├── cross_ref_checker.py     # 交叉引用校验
│   ├── rework.py                # rework_items
│   ├── errors.py                # E_L102_L203_*
│   └── schemas.py               # FourSetResult
├── stage_gate/                  # L2-01 (~1100 行)
│   ├── __init__.py
│   ├── controller.py            # StageGateController · IC-01 主入口
│   ├── state_machine.py         # 7 状态 × 12 转换
│   ├── evidence_assembler.py    # 证据装配（artifacts bundle）
│   ├── rejection_analyzer.py    # LLM + 规则降级
│   ├── rollback.py              # rollback_gate（24h 硬限）
│   ├── errors.py                # E_L102_L201_*
│   └── schemas.py               # GateDecision / StateTransition / IC-01 schema
├── pmp/                         # L2-04 (~900 行)
│   ├── __init__.py
│   ├── producer.py              # produce_all_9
│   ├── worker_pool.py           # asyncio.gather 9 worker
│   ├── bundle_hash.py           # 9 md 固定顺序 concat sha256
│   ├── togaf_cross_check.py     # PMP × TOGAF 矩阵
│   ├── rework.py                # rework_plans
│   ├── errors.py                # E_L102_L204_*
│   └── schemas.py               # PmpBundleResult / KdaResult
├── togaf/                       # L2-05 (~1000 行)
│   ├── __init__.py
│   ├── producer.py              # produce_togaf
│   ├── phase_runner.py          # Phase 严格顺序运行
│   ├── adr_generator.py
│   ├── togaf_d_ready_emitter.py # 关键提前信号 P95 ≤ 200ms
│   ├── rework.py
│   ├── errors.py                # E_L102_L205_*
│   └── schemas.py               # TogafResult / AdrEntry / Profile
├── closing/                     # L2-06 (~850 行)
│   ├── __init__.py
│   ├── producer.py              # produce_closing
│   ├── archiver.py              # archive_project (tar.zst + sha256 + chmod 0444)
│   ├── purger.py                # purge_project (90 天 + 双确认)
│   ├── retro_aggregator.py      # 读 L1-09 audit events
│   ├── recovery.py              # 中断恢复
│   ├── errors.py                # E_L102_L206_*
│   └── schemas.py               # ClosingResult / ArchiveManifest
└── README.md                    # L1-02 组级说明
```

### 2.2 测试目录（新建）

```
tests/l1_02/
├── __init__.py
├── conftest.py                  # 跨 L2 公共 fixture (mock_project_id / mock_event_bus / tmp_projects_root)
├── test_l2_07_template_engine_positive.py  # 13 TC（正向）
├── test_l2_07_template_engine_negative.py  # 14+ TC（每 errorCode ≥1）
├── test_l2_07_template_engine_startup.py   # TC-115 等启动场景
├── test_l2_07_ic_contracts.py              # IC-L2-02 × 5 调用方 + IC-09 契约
├── test_l2_07_perf.py                      # §12 SLO 6 指标
├── test_l2_02_kickoff.py                   # 61 TC
├── test_l2_03_four_set.py                  # 60 TC
├── test_l2_01_stage_gate.py                # 60 TC
├── test_l2_04_pmp.py                       # 63 TC
├── test_l2_05_togaf.py                     # 55 TC
├── test_l2_06_closing.py                   # 54 TC
├── integration/
│   ├── __init__.py
│   ├── test_l1_02_e2e.py                   # S1→S7 mock 全链 ≥15 TC
│   ├── test_pm14_pid_lifecycle.py          # PM-14 创建/激活/归档唯一入口
│   └── test_ic_01_16_19.py                 # IC-01 + IC-16 + IC-19 发起测
└── perf/
    ├── bench_pmp_parallel.py               # L2-04 9 并行 P95 ≤ 30s
    ├── bench_togaf_d_ready.py              # togaf_d_ready P95 ≤ 200ms
    └── bench_archive.py                    # 1GB ≤ 60s
```

### 2.3 模板目录（新建 · L2-07 启动加载的 27 模板）

```
templates/
├── kickoff/
│   ├── goal.md                  # kickoff.goal.v1.0
│   └── scope.md                 # kickoff.scope.v1.0
├── fourset/
│   ├── scope.md · prd.md · plan.md · tdd.md  # fourset.*.v1.0 × 4
├── pmp/
│   ├── integration.md · scope.md · schedule.md · cost.md · quality.md
│   ├── resource.md · communication.md · risk.md · procurement.md  # pmp.*.v1.0 × 9
├── togaf/
│   ├── preliminary.md
│   ├── phase_a.md · phase_b.md · phase_c_data.md · phase_c_application.md
│   ├── phase_d.md · phase_e.md · phase_f.md · phase_g.md · phase_h.md
│   └── adr.md                   # togaf.*.v1.0 × 10 + adr × 1
└── closing/
    ├── lessons_learned.md · delivery_manifest.md · retro_summary.md  # closing.*.v1.0 × 3
```

**合计 27 模板文件**（对应 §3.5 清单）。

### 2.4 配置变更（`pyproject.toml`）

需追加：
- 依赖：`jinja2>=3.1`、`zstandard>=0.22`、`PyYAML>=6`、`python-dateutil>=2.9`
- `[tool.coverage.run].source` 加 `"app/l1_02"`
- `[tool.mypy].packages` 加 `"app.l1_02"`

### 2.5 projects/ 运行时目录（约定）

L2-02 创建 · L2-06 归档的项目物理根目录：
```
projects/
├── <pid>/                        # ULID · 每 project 一个
│   ├── state.json                # 主状态机（L2-02 创建 DRAFT · L2-01 驱动 · L2-06 归档）
│   ├── chart/
│   │   ├── HarnessFlowGoal.md
│   │   └── HarnessFlowPrdScope.md
│   ├── meta/
│   │   └── project_manifest.yaml # anchor_hash + created_at + manifest
│   ├── stage-gates/              # L2-01 Gate 记录
│   ├── four-set/                 # L2-03 scope/prd/plan/tdd.md
│   ├── pmp/                      # L2-04 9 md
│   ├── togaf/                    # L2-05 Phase md + adr/ 目录
│   └── closing/                  # L2-06 lessons_learned / manifest / retro
└── _archive/
    └── <pid>.tar.zst             # L2-06 归档 · sha256 manifest 伴随
```

`tests/` 里所有文件系统写通过 `tmp_path` fixture 隔离到临时目录。

---

## §3 跨 WP 共享约定

### 3.1 错误码命名（PM-14 规范兼容）

- 格式：`E_L102_L20N_NNN`（L1-02 · L2-0N · 三位流水号）
- 每 L2 自己的 `errors.py` 定义 `<L2Name>Error` 类 + 错误码枚举
- 全域 base：`app/l1_02/common/errors.py::L102Error`（带 `error_code`、`context`、`caller_l2`、`project_id` 字段）

### 3.2 事件发射（IC-09 mock）

- 接口：`app/l1_02/common/event_emitter.py::EventEmitter`
- 方法：`emit(project_id, event_type, payload, severity="INFO")`
- 降级：连续 3 次失败 → `DEGRADED_AUDIT` · 本地 buffer（默认 1024）· 恢复后 flush
- Dev-α IC-09 未就绪期间 mock：直接写到 in-memory 列表 + 可选 jsonl tmp 文件

### 3.3 PM-14 pid 约束

- pid 格式：ULID（26 char · lexicographic sortable · `app/l1_02/common/pid_validator.py` 校验）
- 唯一创建点：`L2-02.kickoff.producer.produce_kickoff()`
- 唯一激活点：`L2-02.kickoff.activator.activate_project_id()` · 调用方必是 `L2-01`（运行时检查）
- 唯一归档点：`L2-06.closing.archiver.archive_project()` · 调用方必是 `L2-01`（S7 Gate approve 后）
- 其他 L2 禁止 `projects/<pid>/` 结构创建/归档操作

### 3.4 Gate 硬约束（L2-01 WP04）

- `GATE_AUTO_TIMEOUT_ENABLED=false` 硬锁 · env 启动检查 · `true` 即 crash
- 状态转换必经 L1-01 路由（mock：同进程直接拒绝非 `L1-01` 调用方）

### 3.5 Async 契约

- L2-03（4 并发）、L2-04（9 并发）用 `asyncio.gather(*, return_exceptions=True)`
- L2-07 本身同步（纯计算 · 无 IO） · 被 async 调用方调
- 测试用 `pytest-asyncio`（`asyncio_mode = "auto"` 已配）

### 3.6 TDD 红线（Q-04）

- 每个 public 方法 · 先写失败测 · 再写实现
- 每 WP 结束：`pytest tests/l1_02/test_l2_0N_*` 全绿 + coverage ≥ 85%
- 每 step 单独 commit（prefix `feat(harnessFlow-code): δ-WPNN-stepX`）

---

## §4 Infra-0：项目基础设施（0.25 天）

### Infra-0.1 pyproject 扩依赖 + 加 L1-02 coverage/mypy

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1**：追加 runtime 依赖

```toml
# [project] dependencies 加
dependencies = [
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "jcs>=0.2.1",
    "ulid-py>=1.1",
    "jsonschema>=4.21",
    "jinja2>=3.1",              # NEW · L2-07 sandbox
    "zstandard>=0.22",          # NEW · L2-06 tar.zst
    "PyYAML>=6",                # NEW · frontmatter + manifest
    "python-dateutil>=2.9",     # NEW · ISO-8601 + 90 天计算
]
```

- [ ] **Step 2**：扩 coverage + mypy

```toml
[tool.coverage.run]
source = ["app/l1_09", "app/l1_02"]   # 扩
branch = true

[tool.mypy]
packages = ["app.l1_09", "app.l1_02"]  # 扩
```

- [ ] **Step 3**：标记 commit

```bash
git add pyproject.toml
git commit -m "feat(harnessFlow-code): δ-infra-0.1 pyproject 扩 L1-02 依赖 + coverage/mypy"
```

### Infra-0.2 建 app/l1_02/ 骨架

**Files:**
- Create: `app/__init__.py`（若已存在则跳过）
- Create: `app/l1_02/__init__.py`
- Create: `app/l1_02/README.md`
- Create: `app/l1_02/common/{__init__,errors,event_emitter,pid_validator,schemas}.py`
- Create: `app/l1_02/template_engine/__init__.py`
- Create: `app/l1_02/kickoff/__init__.py`
- Create: `app/l1_02/four_set/__init__.py`
- Create: `app/l1_02/stage_gate/__init__.py`
- Create: `app/l1_02/pmp/__init__.py`
- Create: `app/l1_02/togaf/__init__.py`
- Create: `app/l1_02/closing/__init__.py`
- Create: `tests/__init__.py`（若已存在则跳过）
- Create: `tests/l1_02/__init__.py`
- Create: `tests/l1_02/conftest.py`

- [ ] **Step 1**：建空子包 + 占位 docstring

每个 `__init__.py` 仅 2-3 行 docstring 标明职责。`app/l1_02/README.md` 列出 7 L2 + common 的分工（复用 Dev-δ md §1.2）。

- [ ] **Step 2**：`common/errors.py` 写 base `L102Error`

```python
"""L1-02 公共错误基类 · 所有 L2 的 ErrorCode 都从此派生。"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class L102Error(Exception):
    """基础异常 · 所有 L1-02 子 L2 错误继承。

    error_code: `E_L102_L20N_NNN` 格式。
    caller_l2 / project_id: 审计字段。
    context: 触发时快照（slots / state 等）。
    """
    error_code: str
    message: str = ""
    caller_l2: str | None = None
    project_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.project_id:
            base += f" (pid={self.project_id})"
        if self.caller_l2:
            base += f" (caller={self.caller_l2})"
        return base
```

- [ ] **Step 3**：`common/pid_validator.py` 写 ULID 校验

```python
"""PM-14 pid 格式校验 · ULID 26 char · Crockford base32。"""
from __future__ import annotations
import re

_ULID_REGEX = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def is_valid_pid(pid: str) -> bool:
    """ULID 格式硬校验 · 禁任意 UUID/随机字符串。"""
    return bool(pid and _ULID_REGEX.match(pid))


def ensure_pid(pid: str) -> str:
    """校验后返回 · 不合法 raise ValueError。"""
    if not is_valid_pid(pid):
        raise ValueError(f"invalid pid format (not ULID-26): {pid!r}")
    return pid
```

- [ ] **Step 4**：`common/event_emitter.py` 写 mock EventEmitter

```python
"""IC-09 append_event mock · Dev-α L1-09 未就绪期间的本地替代。

契约：
  - emit(project_id, event_type, payload, severity="INFO") -> None
  - 连续 3 次失败进 DEGRADED_AUDIT · buffer 默认 1024 · 不 raise
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
import time


EventSeverity = Literal["INFO", "WARN", "CRITICAL"]


@dataclass
class EmittedEvent:
    ts: float
    project_id: str
    event_type: str
    payload: dict[str, Any]
    severity: EventSeverity
    caller_l2: str | None = None


@dataclass
class EventEmitter:
    """In-memory · 测试 + mock 阶段用。真实 IC-09 就绪后换 adapter。"""
    events: list[EmittedEvent] = field(default_factory=list)
    state: str = "NORMAL"
    buffer: list[EmittedEvent] = field(default_factory=list)
    _fail_count: int = 0
    _fail_threshold: int = 3
    buffer_max: int = 1024

    def emit(
        self,
        project_id: str,
        event_type: str,
        payload: dict[str, Any],
        severity: EventSeverity = "INFO",
        caller_l2: str | None = None,
    ) -> None:
        evt = EmittedEvent(
            ts=time.time(),
            project_id=project_id,
            event_type=event_type,
            payload=payload,
            severity=severity,
            caller_l2=caller_l2,
        )
        # 正常路径：直接 append
        if self.state == "NORMAL":
            self.events.append(evt)
            return
        # DEGRADED：buffer，不 raise
        if len(self.buffer) < self.buffer_max:
            self.buffer.append(evt)

    def emitted_events(self) -> list[dict[str, Any]]:
        """返回事件列表 · 测试用（与 TDD fixture 对齐）。"""
        return [
            {
                "ts": e.ts,
                "project_id": e.project_id,
                "event_type": e.event_type,
                "payload": e.payload,
                "severity": e.severity,
                "caller_l2": e.caller_l2,
                **e.payload,  # 便于 tests 直接读字段
            }
            for e in self.events
        ]

    def force_fail(self) -> None:
        """测试辅助 · 模拟 IC-09 连续失败进 DEGRADED_AUDIT。"""
        self._fail_count += 1
        if self._fail_count >= self._fail_threshold:
            self.state = "DEGRADED_AUDIT"

    def recover(self) -> None:
        """测试辅助 · buffer flush 到 events 并回 NORMAL。"""
        self.events.extend(self.buffer)
        self.buffer.clear()
        self._fail_count = 0
        self.state = "NORMAL"
```

- [ ] **Step 5**：`tests/l1_02/conftest.py` 写共享 fixture

```python
"""L1-02 跨 L2 共享测试 fixture。"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import uuid

import pytest

from app.l1_02.common.event_emitter import EventEmitter


@pytest.fixture
def mock_project_id() -> str:
    """ULID 格式的 pid · 每 test 唯一。"""
    # 生产用真实 ULID；测试用 ULID-like 固定前缀 + 随机尾
    import time
    # Crockford base32 字符集
    base32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    random_suffix = "".join(
        base32[b % 32] for b in uuid.uuid4().bytes[:16]
    )
    return ("01HXK" + random_suffix)[:26]


@pytest.fixture
def mock_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def mock_event_bus() -> EventEmitter:
    return EventEmitter()


@pytest.fixture
def tmp_projects_root(tmp_path: Path) -> Path:
    """隔离 projects/ 根 · PM-14 相关测试用。"""
    root = tmp_path / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root
```

- [ ] **Step 6**：跑一个烟测（确认基础设施可 import）

```bash
cd /Users/zhongtianyi/work/code/harnessFlow
source .venv/bin/activate
python -c "from app.l1_02.common.errors import L102Error; from app.l1_02.common.event_emitter import EventEmitter; from app.l1_02.common.pid_validator import is_valid_pid; print('import OK')"
pytest tests/l1_02/ -v --collect-only | head -5
```

预期：打印 `import OK`；pytest collect 不报错（即使 0 tests）。

- [ ] **Step 7**：commit infra-0

```bash
git add pyproject.toml app/l1_02 tests/l1_02
git commit -m "feat(harnessFlow-code): δ-infra-0 L1-02 骨架（7 L2 空包 + common/errors + event_emitter mock + pid_validator + conftest）"
```

### Infra-0.3 建 templates/ 根目录 + 占位结构

**Files:**
- Create: `templates/kickoff/`（空目录占位 · WP01 Step A 填充）
- Create: `templates/fourset/`
- Create: `templates/pmp/`
- Create: `templates/togaf/`
- Create: `templates/closing/`
- Create: `templates/README.md`

- [ ] **Step 1**：建 5 子目录 + README 说明

README 内容：说明 27 模板清单 + frontmatter 必填字段（kind / version / slot_schema / description / author / created_at） + 所有权（L2-07 启动加载 · L2-02~06 调用）。

- [ ] **Step 2**：commit

```bash
git add templates/
git commit -m "feat(harnessFlow-code): δ-infra-0.3 templates/ 根目录占位（WP01 填充 27 模板）"
```

---

## §5 子计划骨架（每 WP 启动时按此骨架写 Dev-δ-WP0X-*.md）

每 WP 的详细 plan 必含以下 7 段（严格 TDD red-green-refactor）：

1. **Header**：Goal / Architecture / Tech Stack / parent_doc 引 Dev-δ md §3.X + 对应 L2 tech + TDD
2. **File Structure**：L3/L4 粒度 · 每文件职责 + 行数估
3. **TDD 任务序列**（bite-sized steps）：
   - 按 TC ID 升序排 · 先写 red（测失败）· 再 green（最小实现）· 再 refactor
   - 每 batch 3-5 个 TC 为一次 commit（粒度：正向 / 错误码 / IC / SLO / edge 各一批）
4. **IC 契约对齐**：该 WP 涉及的 IC schema 引 `ic-contracts.md` 对应 §
5. **DoD 自检**：引 Dev-δ md §3.X DoD + 加 `pytest tests/l1_02/test_l2_0N_*.py -v` 全绿 + coverage
6. **commit 清单**：最终 commit 列表（预期 4-6 个/WP）
7. **自修正触发点**：可能的 source doc 不一致 + `_correction_log.jsonl` 记录位点

---

## §6 验证前置（写实现前必做）

所有 WP 共同前置：

- [ ] 本会话 + 未来 session 都读过 `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-δ-L1-02-lifecycle.md` 完整 § 1-10
- [ ] 本会话读过 `architecture.md` + 对应 WP 的 L2 tech + L2 TDD md（至少对应 WP 那份）
- [ ] `templates/` 目录有 27 模板（L2-07 启动不 crash）
- [ ] `app/l1_02/common/` import 通过（Infra-0 done）
- [ ] Dev-α IC-09 / Dev-β IC-06 / Dev-γ L1-05 / Dev-θ IC-16 / Dev-ε IC-19 按 §3.2 用 mock 替代（真实实现后切换）

---

## §7 跨会话接力约定（δ1 → δ2）

- **δ1 产出**：WP01-04（L2-07 / L2-02 / L2-03 / L2-01）· commit tag `δ1-done`
- **δ2 起点**：读 `git log --oneline δ1-done..HEAD` + 本 master impl plan + 各 WP 子 plan
- **切换节点**：δ1 最后一个 commit 信息加 `## 交接 δ2：下一会话执行 WP05-08`

---

## §8 自检（writing-plans skill 要求）

### 8.1 Spec 覆盖

| Dev-δ md §3 WP | 本 plan 对应 | 备注 |
|:---:|:---|:---|
| WP01 L2-07 | §1 表 + `Dev-δ-WP01-*.md`（已写） | ✅ |
| WP02 L2-02 | §1 表 + 待写 `Dev-δ-WP02-*.md` | 📝 |
| WP03 L2-03 | §1 表 + 待写 `Dev-δ-WP03-*.md` | 📝 |
| WP04 L2-01 | §1 表 + 待写 `Dev-δ-WP04-*.md` | 📝 |
| WP05 L2-04 | §1 表 + 待写 `Dev-δ-WP05-*.md` | 📝 |
| WP06 L2-05 | §1 表 + 待写 `Dev-δ-WP06-*.md` | 📝 |
| WP07 L2-06 | §1 表 + 待写 `Dev-δ-WP07-*.md` | 📝 |
| WP08 集成 | §1 表 + 待写 `Dev-δ-WP08-*.md` | 📝 |
| §8 组级 DoD | §3.6 + §6 + 每 WP 子 plan §5 | ✅ |
| §9 风险 R-δ-01~04 | 每 WP 子 plan 的 fallback 段 | 📝 |

**无遗漏**。WP02-08 子 plan 在对应 WP 启动前按 §5 骨架按需展开（避免单次撰写超 20k 行 · 同时保证每 WP 有最新的 source doc 映射）。

### 8.2 Placeholder 扫描

已扫：无 "TBD / TODO / implement later / fill in details"。
每 step 都有具体代码或 bash 命令或 file_path。
❗ WP02-08 的"子 plan 待写"是**管理状态**（"status: 📝 待写"），非 step 级占位 — 各 WP 启动前生成详细 plan 是流程设计，不是 Placeholder。

### 8.3 类型一致性

- `EventEmitter.emit` 签名：在 Infra-0 定义 · WP01 test_l2_07 调用时字段名对齐（`mock_event_bus.emitted_events()`）· 测试里直接读 `e["event_type"]` · `e["project_id"]` · `e["template_id"]` 等，由 `EventEmitter.emitted_events()` 扁平化注入 payload key 保证可读。
- `RenderedOutput` · `TemplateEngineError` 等由 WP01 子 plan 权威定义。

---

## §9 执行入口 / 下一步

本会话：
1. ✅ 已写本 master impl plan
2. ✅ 已写 `Dev-δ-WP01-L2-07-template-engine.md` 详细子 plan
3. ⏩ 立即执行 Infra-0（pyproject + 骨架 + templates 占位）
4. ⏩ 立即开始 WP01 TDD 循环（至少完成 L2-07 的前 3-5 TC 红绿循环 + 首个 commit）
5. 剩余 WP01 + WP02-08 在后续 session 继续

**跨 session 续命**：下次 session 读：
- `docs/superpowers/plans/Dev-δ-impl.md`（本 plan）
- `docs/superpowers/plans/Dev-δ-WP0X-*.md`（当前 WP 子 plan）
- `git log --oneline | head -30` 看最近进度
- `pytest tests/l1_02/ -v` 看当前绿的 TC
- 按 TaskList 找 `in_progress` / `pending` 项继续

---

*— Dev-δ L1-02 实施主计划 · v1.0 · 主会话 writing-plans skill · 2026-04-23 —*
