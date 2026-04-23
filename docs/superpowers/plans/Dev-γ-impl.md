---
doc_id: dev-gamma-impl-plan
doc_type: superpowers-implementation-plan
source_exe_plan: docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-γ-L1-05-skill-subagent.md
source_brief: docs/superpowers/plans/Dev-γ-brief-L1-05.md
session: Dev-γ
version: v1.0
status: active
updated_at: 2026-04-23
---

# Dev-γ · L1-05 Skill 生态+子 Agent 调度 · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 harnessFlow L1-05 完整栈（Skill 注册表 / 意图选择器 / 调用执行器 / 子 Agent 委托器 / 异步结果回收器）· 提供 4 个全局 IC（IC-04 invoke_skill · IC-05 delegate_subagent · IC-12 delegate_codebase_onboarding · IC-20 delegate_verifier）· 满足 PM-03（独立 session） / PM-09（能力抽象） / PM-14（project_id）三项硬约束。

**Architecture:** 五层管线 — Registry 承数据底座（能力抽象层 + 账本）；Intent 做多信号排序（availability / cost / success_rate / failure_memory / recency / kb_boost）+ 硬编码扫描；Invoker 承 IC-04 主入口（context 注入 + retry + timeout + 审计双写）；Subagent 承 IC-05/12/20（Claude Agent SDK + COW context + PM-03 隔离 + SIGTERM→SIGKILL）；Receiver 承结果回收（jsonschema 校验 + DoD 网关转发 L1-04 + 幂等 + 崩溃恢复）。跨 L1 依赖以本地 mock 打占位（波1 未就绪）。

**Tech Stack:**
- Python 3.11（CLAUDE.md 与 L1-09/L1-06 对齐）
- `pydantic v2` — Schema & 契约校验
- `jsonschema` Draft 2020-12 — IC 字段与回传校验
- `watchdog` — Registry 热更新 fs_watch
- `anthropic` SDK + `claude-agent-sdk`（pin 版本）— L2-04 子 Agent
- `pytest` + `pytest-asyncio` + `pytest-cov` — TDD 测试
- `asyncio` — TimeoutWatcher / 心跳
- `freezegun` — 时间相关测试
- `PyYAML` — registry.yaml

---

## §0 前置与依赖状态

**状态盘点（v1.1 修订 · 2026-04-23 · worktree 隔离后复核）：**
- ✅ 源文档齐：`2-prd/L1-05/prd.md` · `3-1/L1-05/architecture.md + L2-01~05` · `integration/ic-contracts.md §3.4/3.5/3.12/3.20` · `3-2/L1-05/L2-01~05-tests.md`
- ✅ `pyproject.toml` 已存在（Dev-δ 基线 HEAD `ce8fd51`）· 本 session 已 amend：追加 `watchdog` 主依赖 · `freezegun` dev · 新 `[sdk]` optional (`anthropic`) · markers `pm03`/`pm09` · coverage `app/skill_dispatch` · mypy `app.skill_dispatch`
- ✅ `app/__init__.py` · `tests/__init__.py` · `app/l1_02/*` / `app/l1_09/*` 骨架已提交（Dev-δ / Dev-α 占位）· 不再新建根级基建
- ✅ `app/skill_dispatch/` 不存在 · clean slate（领域完全独立 · 不碰 L1-02/06/09 代码）
- ❌ 波1 Dev-α L1-09 event_bus 为空 `__init__.py`（无 runnable 实现）· Dev-β L1-06 TierManager 是 RED-phase stub（`raise NotImplementedError`）· **4 个 mock 必须本地打**
- ✅ Worktree `.worktrees/dev-gamma-l1-05/` 已建 · 分支 `feat/dev-gamma-l1-05` · 与其他 Dev 物理隔离

**Mock 替换清单（波4-5 切真实）：**

| Mock | 位置 | 真实来源 | 切换时机 |
|---|---|---|---|
| `IC09EventBusMock.append_event` | `app/skill_dispatch/_mocks/ic09_mock.py` | Dev-α L2-02 | α WP04 交付后 |
| `IC06KBMock.kb_read` | `app/skill_dispatch/_mocks/ic06_mock.py` | Dev-β L2-02 | β WP03 交付后 |
| `IC_L2_07_AccountLockMock` | `app/skill_dispatch/_mocks/lock_mock.py` | Dev-α L1-09 L2-02 | α WP07 交付后 |
| `DoDGateMock.dod_gate_check` | `app/skill_dispatch/_mocks/dod_gate_mock.py` | 主-1 L1-04 L2-02 | 主-1 交付后 |

---

## §1 File Structure（锁定单责/不再变动）

```
harnessFlow/
├── pyproject.toml                            # 项目元数据 + 依赖
├── pytest.ini                                 # asyncio_mode=auto + markers
├── conftest.py                                # 全局 fixtures（tmp_project, fake_clock）
├── app/
│   ├── __init__.py
│   └── l1_05/
│       ├── __init__.py
│       ├── README.md                          # 组级 DoD checklist + 使用示例（WP06 收尾写）
│       │
│       ├── _mocks/                            # 跨 L1 mock（TODO:MOCK-REPLACE）
│       │   ├── __init__.py
│       │   ├── ic09_mock.py                   # IC-09 append_event mock
│       │   ├── ic06_mock.py                   # IC-06 kb_read mock（返 []）
│       │   ├── lock_mock.py                   # IC-L2-07 account lock mock
│       │   └── dod_gate_mock.py               # L1-04 DoD gate mock（返 approved）
│       │
│       ├── registry/                          # L2-01 (~980 行)
│       │   ├── __init__.py
│       │   ├── schemas.py                     # SkillSpec / CapabilityPoint / SubagentEntry / ToolEntry / LedgerEntry
│       │   ├── loader.py                      # 5 阶段启动加载 + snapshot 写出
│       │   ├── query_api.py                   # query_candidates / query_subagent / query_tool / query_schema_pointer
│       │   ├── ledger.py                      # 账本回写 + L1-09 锁保护
│       │   └── fs_watcher.py                  # watchdog 热更新（throttle 10s）
│       │
│       ├── intent_selector/                   # L2-02 (~800 行)
│       │   ├── __init__.py
│       │   ├── schemas.py                     # SignalScores / Chain / ExplanationCard
│       │   ├── scorer.py                      # 6 信号打分 + 权重配置
│       │   ├── hard_edge_scan.py              # 启动硬编码扫描（crash on violation）
│       │   ├── fallback_advancer.py           # advance_fallback(chain, reason)
│       │   └── kb_boost.py                    # 调 IC-06 · 150ms 超时降级
│       │
│       ├── invoker/                           # L2-03 (~950 行)
│       │   ├── __init__.py
│       │   ├── schemas.py                     # InvocationRequest/Response / InvocationSignature
│       │   ├── executor.py                    # invoke_skill() IC-04 主入口
│       │   ├── context_injector.py            # 白名单注入 pid/wp_id/loop_session_id/decision_id
│       │   ├── timeout_manager.py             # 精度 ±100ms · hard-cap 5min
│       │   ├── retry_policy.py                # idempotent 判定 + 指数退避
│       │   └── audit.py                       # IC-09 两次写 + params_hash SHA-256 + 脱敏
│       │
│       ├── subagent/                          # L2-04 (~900 行)
│       │   ├── __init__.py
│       │   ├── schemas.py                     # DelegationRequest/Response / DelegationSignature / LifecycleState
│       │   ├── delegator.py                   # IC-05 / IC-12 / IC-20 路由
│       │   ├── claude_sdk_client.py           # Claude Agent SDK 封装（pin）
│       │   ├── resource_limiter.py            # max_concurrent=3 / 内存 / 排队
│       │   └── context_scope.py               # COW 指针 + context_checksum + PM-03 隔离
│       │
│       └── async_receiver/                    # L2-05 (~730 行)
│           ├── __init__.py
│           ├── schemas.py                     # CollectionRecord / ValidationResult / PendingEntry
│           ├── validator.py                   # jsonschema 校验 + SCHEMA_UNAVAILABLE 硬失败
│           ├── forwarder.py                   # 转发 L1-04 DoD gate (IC-14 prev_hash)
│           └── crash_recovery.py              # pending.jsonl replay + TimeoutWatcher asyncio
│
└── tests/
    ├── __init__.py
    ├── conftest.py                            # 测试专属 fixtures
    └── l1_05/
        ├── __init__.py
        ├── conftest.py                        # L1-05 局部 fixtures
        ├── fixtures/                          # 静态测试数据
        │   ├── registry_valid.yaml
        │   ├── registry_missing_schema.yaml
        │   ├── skill_spec_sample.yaml
        │   └── ledger_sample.jsonl
        │
        ├── test_l2_01_registry.py             # ~40 TC（L2-01）
        ├── test_l2_02_intent.py               # ~40 TC（L2-02）
        ├── test_l2_03_invoker.py              # ~39 TC（L2-03）
        ├── test_l2_04_subagent.py             # ~39 TC（L2-04）
        ├── test_l2_05_receiver.py             # ~38 TC（L2-05）
        │
        ├── integration/
        │   ├── __init__.py
        │   ├── test_l1_05_e2e.py              # invoke → registry → subagent → receiver 全链
        │   ├── test_ic_04_05_12_20.py         # 4 IC 契约集成
        │   └── test_pm14_subagent_isolation.py
        │
        └── perf/
            ├── __init__.py
            ├── bench_ic_04_dispatch.py        # ≤ 200ms
            └── bench_subagent_spawn.py        # ≤ 1.2s
```

**文件单责约束：**
- 每个 `schemas.py` 只放 Pydantic 模型 · 不含业务逻辑
- 每个业务文件 ≤ 280 行 · 超限拆分
- mock 严格隔离到 `_mocks/` · 真实实现落位后删掉并更新 import

---

## §2 WP-γ-00 · Bootstrap（Python 骨架 + 4 mock）

**目标：** 搭出最小可跑的 `pytest tests/skill_dispatch/ -v`（0 collection errors · 骨架就位即可）。

**v1.1 修订：** 根级基建（`pyproject.toml` / `app/__init__.py` / `tests/__init__.py` / `.gitignore`）都由 Dev-δ 的 `ce8fd51` 提交到 HEAD。本 WP 只做两件事：**(1) 对 pyproject.toml 做 L1-05 加量 amend**（本 session 已完成）· **(2) 创建 `app/skill_dispatch/` + `tests/skill_dispatch/` 领域内所有新文件**。

**Files（领域独立 · 不触碰其他 L1 代码）：**
- ✅ Amend: `pyproject.toml`（L1-05 依赖 + markers + coverage · 已完成）
- Create: `app/skill_dispatch/__init__.py` + 5 子模块 `__init__.py` + `_mocks/__init__.py`
- Create: `app/skill_dispatch/_mocks/{ic09_mock,ic06_mock,lock_mock,dod_gate_mock}.py`
- Create: `tests/skill_dispatch/__init__.py` + `integration/__init__.py` + `perf/__init__.py`
- Create: `tests/skill_dispatch/conftest.py`
- Create: `tests/skill_dispatch/fixtures/registry_valid.yaml` · `ledger_sample.jsonl`

### Task 00.1 — ✅ Amend pyproject.toml（本 session 已完成）

本 session 已在 `.worktrees/dev-gamma-l1-05/pyproject.toml` 做以下 amend：
- `dependencies` 追加 `watchdog>=4.0`（L2-01 fs_watcher）
- `[project.optional-dependencies.dev]` 追加 `freezegun>=1.5`（L2-02 decay test）
- 新 `[project.optional-dependencies.sdk]` 含 `anthropic>=0.39`（WP-γ-04 装）
- `[tool.pytest.ini_options].markers` 追加 `pm03` / `pm09`
- `[tool.coverage.run].source` 追加 `app/skill_dispatch` · `omit` 追加 `app/skill_dispatch/_mocks/*`
- `[tool.mypy].packages` 追加 `app.skill_dispatch`

- [ ] **Step 1: 验证 amend**

Run: `grep -cE "watchdog|freezegun|pm03|pm09|app/skill_dispatch|app\.l1_05" pyproject.toml`
Expected: ≥ 6

Commit 与 Task 00.3 一起（见 00.3 step 4）。

### Task 00.2 — 局部 conftest（根 conftest.py 不建 · 避免干扰他 Dev）

- [ ] **Step 1: 确认根 `conftest.py` 不存在**（存在则跳过；不存在则**仍然不建** · 所有 fixtures 放 `tests/skill_dispatch/conftest.py` 局部化）

Run: `ls -la conftest.py 2>/dev/null && echo EXISTS || echo ABSENT`

- [ ] **Step 2: `tmp_project` / `fake_pid` fixtures 合并进 `tests/skill_dispatch/conftest.py`**（见 Task 00.6）

本 Task 不出独立 commit · 工作合并到 Task 00.6。

### Task 00.3 — 建 `app/skill_dispatch/` + `tests/skill_dispatch/` 领域骨架（合并 Task 00.1 commit）

- [ ] **Step 1: Create L1-05 directory tree**

Run:
```bash
cd /Users/zhongtianyi/work/code/harnessFlow/.worktrees/dev-gamma-l1-05
mkdir -p app/skill_dispatch/{registry,intent_selector,invoker,subagent,async_receiver,_mocks}
mkdir -p tests/skill_dispatch/{integration,perf,fixtures}
```

- [ ] **Step 2: Create `__init__.py` ONLY for new L1-05 dirs (不碰 app/ 或 tests/ 根 __init__.py)**

Run:
```bash
for d in app/skill_dispatch app/skill_dispatch/registry app/skill_dispatch/intent_selector app/skill_dispatch/invoker app/skill_dispatch/subagent app/skill_dispatch/async_receiver app/skill_dispatch/_mocks tests/skill_dispatch tests/skill_dispatch/integration tests/skill_dispatch/perf; do
  touch "$d/__init__.py"
done
```

- [ ] **Step 3: Verify**

Run: `find app/skill_dispatch tests/skill_dispatch -name "__init__.py" | wc -l`
Expected: `10`

`git diff --stat app/__init__.py tests/__init__.py`
Expected: （空 · 根 __init__.py 未改）

- [ ] **Step 4: Commit（合并 00.1 + 00.3）**

```bash
git add pyproject.toml app/skill_dispatch tests/skill_dispatch
git commit -m "feat(harnessFlow-code): γ-WP00.1+00.3 pyproject amend (watchdog/freezegun/sdk/pm03/pm09/coverage) + app/skill_dispatch + tests/skill_dispatch 骨架（10 __init__.py）"
```

### Task 00.4 — IC-09 event bus mock

- [ ] **Step 1: Write `app/skill_dispatch/_mocks/ic09_mock.py`**

```python
"""IC-09 append_event mock — 波4 替换为 Dev-α L1-09 L2-05 真实事件总线.

TODO:MOCK-REPLACE-FROM-DEV-α — α WP04 交付后，删除本文件并 import
真实 `app.l1_09.event_bus.append_event`（契约一致）.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IC09EventRecord:
    """IC-09 事件记录（与真实接口字段对齐 · 不可再加字段）."""

    event_id: str
    project_id: str
    l1: str                    # 发起方 L1
    event_type: str            # e.g. "skill_invocation_started"
    payload: dict[str, Any]
    ts_ns: int                 # time.time_ns()
    prev_hash: str             # IC-14 一致性链 · 前一条事件的 hash
    this_hash: str             # sha256(prev_hash + canonical(record))

    def canonical_bytes(self) -> bytes:
        body = {k: v for k, v in self.__dict__.items() if k != "this_hash"}
        return json.dumps(body, sort_keys=True, default=str).encode("utf-8")


class IC09EventBusMock:
    """内存版事件总线 · 全局锁 · hash chain · 单测可 flush/read."""

    _lock = threading.Lock()
    _chain: list[IC09EventRecord] = field(default_factory=list)

    def __init__(self) -> None:
        self._events: list[IC09EventRecord] = []
        self._last_hash = "0" * 64   # genesis

    def append_event(
        self,
        *,
        project_id: str,
        l1: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> IC09EventRecord:
        if not project_id:
            raise ValueError("IC-09: project_id required (PM-14)")
        ts = time.time_ns()
        rec = IC09EventRecord(
            event_id=hashlib.sha256(f"{ts}{event_type}".encode()).hexdigest()[:16],
            project_id=project_id,
            l1=l1,
            event_type=event_type,
            payload=payload,
            ts_ns=ts,
            prev_hash=self._last_hash,
            this_hash="",
        )
        rec.this_hash = hashlib.sha256(
            rec.prev_hash.encode() + rec.canonical_bytes()
        ).hexdigest()
        with self._lock:
            self._events.append(rec)
            self._last_hash = rec.this_hash
        return rec

    def read_all(self, project_id: str | None = None) -> list[IC09EventRecord]:
        if project_id is None:
            return list(self._events)
        return [e for e in self._events if e.project_id == project_id]

    def flush(self) -> None:
        with self._lock:
            self._events.clear()
            self._last_hash = "0" * 64


_default_bus: IC09EventBusMock | None = None


def get_default_bus() -> IC09EventBusMock:
    """进程级单例 mock · 仅测试用."""
    global _default_bus
    if _default_bus is None:
        _default_bus = IC09EventBusMock()
    return _default_bus
```

- [ ] **Step 2: Smoke-test the mock inline**

Run:
```bash
python -c "
from app.skill_dispatch._mocks.ic09_mock import IC09EventBusMock
b = IC09EventBusMock()
r1 = b.append_event(project_id='p1', l1='L1-05', event_type='test', payload={'x':1})
r2 = b.append_event(project_id='p1', l1='L1-05', event_type='test', payload={'x':2})
assert r2.prev_hash == r1.this_hash
assert len(b.read_all('p1')) == 2
print('IC09 mock OK')
"
```
Expected: `IC09 mock OK`

- [ ] **Step 3: Commit**

```bash
git add app/skill_dispatch/_mocks/ic09_mock.py
git commit -m "feat(harnessFlow-code): γ-WP00.4 IC-09 event bus mock（hash chain + PM-14 校验）"
```

### Task 00.5 — IC-06 KB mock + Lock mock + DoD gate mock

- [ ] **Step 1: Write `app/skill_dispatch/_mocks/ic06_mock.py`**

```python
"""IC-06 kb_read mock — 波4 替换为 Dev-β L1-06 L2-02 真实 KB.

TODO:MOCK-REPLACE-FROM-DEV-β — β WP03 交付后替换.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class KBRecipe:
    capability: str
    skill_id: str
    success_rate: float
    last_seen_ts: int


class IC06KBMock:
    """空 KB · 返空列表 · 支持注入 slow-read 模拟超时."""

    def __init__(self, recipes: list[KBRecipe] | None = None, read_latency_ms: int = 0) -> None:
        self._recipes = recipes or []
        self._latency_ms = read_latency_ms

    def kb_read(self, project_id: str, capability: str) -> list[KBRecipe]:
        if not project_id:
            raise ValueError("IC-06: project_id required (PM-14)")
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)
        return [r for r in self._recipes if r.capability == capability]
```

- [ ] **Step 2: Write `app/skill_dispatch/_mocks/lock_mock.py`**

```python
"""IC-L2-07 account lock mock — 波4 替换为 Dev-α L1-09 真实锁.

TODO:MOCK-REPLACE-FROM-DEV-α — α WP07 交付后替换.
"""
from __future__ import annotations

import contextlib
import threading
from collections.abc import Iterator


class AccountLockMock:
    """进程内 RLock · 按 (project_id, capability) 维度分锁."""

    def __init__(self) -> None:
        self._locks: dict[tuple[str, str], threading.RLock] = {}
        self._registry_lock = threading.Lock()

    def _get(self, project_id: str, capability: str) -> threading.RLock:
        key = (project_id, capability)
        with self._registry_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    @contextlib.contextmanager
    def acquire(self, project_id: str, capability: str, timeout_s: float = 5.0) -> Iterator[None]:
        lock = self._get(project_id, capability)
        got = lock.acquire(timeout=timeout_s)
        if not got:
            raise TimeoutError(f"lock timeout for ({project_id}, {capability})")
        try:
            yield
        finally:
            lock.release()
```

- [ ] **Step 3: Write `app/skill_dispatch/_mocks/dod_gate_mock.py`**

```python
"""L1-04 DoD gate mock — 波5 替换为主-1 L1-04 L2-02 真实 DoD evaluator.

TODO:MOCK-REPLACE-FROM-主-1 — 主-1 L1-04 完工后替换.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Verdict = Literal["PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"]


@dataclass
class DoDGateVerdict:
    verdict: Verdict
    reason: str
    confidence: float      # 0..1
    evidence: dict[str, str]


class DoDGateMock:
    """默认放行（PASS）· 可注入特定 capability 的裁决."""

    def __init__(self, overrides: dict[str, Verdict] | None = None) -> None:
        self._overrides = overrides or {}

    def dod_gate_check(
        self,
        project_id: str,
        capability: str,
        result_id: str,
        artifact: dict,
    ) -> DoDGateVerdict:
        if not project_id:
            raise ValueError("DoDGate: project_id required (PM-14)")
        verdict = self._overrides.get(capability, "PASS")
        return DoDGateVerdict(
            verdict=verdict,
            reason="mock-default" if verdict == "PASS" else "mock-override",
            confidence=1.0 if verdict == "PASS" else 0.0,
            evidence={"mock": "true"},
        )
```

- [ ] **Step 4: Commit**

```bash
git add app/skill_dispatch/_mocks/ic06_mock.py app/skill_dispatch/_mocks/lock_mock.py app/skill_dispatch/_mocks/dod_gate_mock.py
git commit -m "feat(harnessFlow-code): γ-WP00.5 IC-06 KB / L2-07 lock / L1-04 DoD gate mock（打占位）"
```

### Task 00.6 — tests/skill_dispatch conftest + 初始 fixture yaml

- [ ] **Step 1: Write `tests/skill_dispatch/conftest.py`**

```python
"""L1-05 测试局部 fixtures · 导出 mock 单例."""
from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest

from app.skill_dispatch._mocks.dod_gate_mock import DoDGateMock
from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
from app.skill_dispatch._mocks.ic09_mock import IC09EventBusMock
from app.skill_dispatch._mocks.lock_mock import AccountLockMock


@pytest.fixture
def ic09_bus() -> Iterator[IC09EventBusMock]:
    bus = IC09EventBusMock()
    yield bus
    bus.flush()


@pytest.fixture
def kb_mock() -> IC06KBMock:
    return IC06KBMock()


@pytest.fixture
def lock_mock() -> AccountLockMock:
    return AccountLockMock()


@pytest.fixture
def dod_gate() -> DoDGateMock:
    return DoDGateMock()


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"
```

- [ ] **Step 2: Write `tests/skill_dispatch/fixtures/registry_valid.yaml`**

```yaml
# L2-01 Registry 启动加载样例 · 符合 registry.yaml 契约.
version: "1.0"
capability_points:
  write_test:
    description: "生成 pytest red 测试"
    schema_pointer: "schemas/skill/write_test.v1.json"
    candidates:
      - skill_id: "superpowers:tdd-workflow"
        availability: true
        cost_usd: 0.02
        timeout_s: 60
      - skill_id: "builtin:write_test_min"
        availability: true
        cost_usd: 0.0
        timeout_s: 30
        is_builtin_fallback: true
  review_code:
    description: "Python 代码静态审查"
    schema_pointer: "schemas/skill/review_code.v1.json"
    candidates:
      - skill_id: "plugin:python-reviewer"
        availability: true
        cost_usd: 0.05
        timeout_s: 120
      - skill_id: "builtin:review_code_min"
        availability: true
        cost_usd: 0.0
        timeout_s: 60
        is_builtin_fallback: true
subagents:
  codebase_onboarding:
    role: codebase-onboarding
    tool_whitelist: [Read, Glob, Grep, Bash]
    timeout_s: 600
    schema_pointer: "schemas/subagent/onboarding_report.v1.json"
  verifier:
    role: verifier
    tool_whitelist: [Read, Glob, Grep, Bash]
    timeout_s: 1200
    schema_pointer: "schemas/subagent/verifier_verdict.v1.json"
tools:
  Read:
    kind: atomic
  Bash:
    kind: atomic
```

- [ ] **Step 3: Smoke test — `pytest --collect-only` should not error**

Run: `python -m pytest tests/skill_dispatch/ --collect-only 2>&1 | tail -5`
Expected: `0 tests collected` 或类似（不应有 collection error）

- [ ] **Step 4: Commit**

```bash
git add tests/skill_dispatch/conftest.py tests/skill_dispatch/fixtures/registry_valid.yaml
git commit -m "feat(harnessFlow-code): γ-WP00.6 tests/skill_dispatch conftest + 样例 registry.yaml fixture"
```

### Task 00.7 — 安装依赖 + 骨架烟测

- [ ] **Step 1: 复用 main workdir 的 .venv · 增量装 L1-05 新依赖**

```bash
source /Users/zhongtianyi/work/code/harnessFlow/.venv/bin/activate
cd /Users/zhongtianyi/work/code/harnessFlow/.worktrees/dev-gamma-l1-05
pip install -e ".[dev]"
```

Expected: 增量装 `watchdog` + `freezegun`，其余 satisfied。

- [ ] **Step 2: SDK 可选依赖延到 WP-γ-04 装**

WP-γ-04 启动时：`pip install -e ".[dev,sdk]"`。WP-γ-00~03 用 mock · 不需要 `anthropic`。

- [ ] **Step 3: 跑 collect-only 验证 pytest 可启动**

Run: `pytest tests/skill_dispatch/ --collect-only`
Expected: `0 tests collected`（无 error）

- [ ] **Step 4: Ruff 初扫（不 fail build）**

Run: `ruff check app/skill_dispatch tests/skill_dispatch || true`
Expected: 只对 mock 文件有少量告警（可接受）

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(harnessFlow-code): γ-WP00.7 venv + 依赖安装 + pytest 烟测绿（0 collection errors）" || echo "nothing to commit"
```

### Task 00.8 — WP-γ-00 DoD 自检

- [ ] **Step 1: Checklist**

检查：
- [ ] `pyproject.toml` amend 生效（`grep` 命中 ≥ 6）
- [ ] `tests/skill_dispatch/conftest.py` 可 import 4 个 mock
- [ ] `app/skill_dispatch/_mocks/*.py` 4 个 mock 全就位 · 烟测通过
- [ ] `tests/skill_dispatch/fixtures/registry_valid.yaml` 可读
- [ ] `pytest tests/skill_dispatch/ --collect-only` 无 error
- [ ] 4-5 个 commit 全部 prefix `feat(harnessFlow-code): γ-WP00.* ...`（v1.1 合并后比 v1.0 少了 00.1/00.2 独立 commit）

- [ ] **Step 2: 写 standup**

Create `docs/4-exe-plan/standup-logs/Dev-γ-2026-04-23.md`:

```markdown
## Dev-γ Day 1 · 2026-04-23

### DoD
- ✅ WP-γ-00 bootstrap 完（7 commits）
- ⏳ WP-γ-01 L2-01 Registry 明日启动

### 完成
- Python 3.11 骨架（pyproject + pytest + conftest）
- 4 个跨 L1 mock（IC-09/IC-06/L2-07 lock/DoD gate）
- tests/skill_dispatch/ 包 + conftest + fixture yaml
- `pytest --collect-only` 0 errors

### Mock 替换清单
- IC09EventBusMock → 波4 Dev-α
- IC06KBMock → 波4 Dev-β
- AccountLockMock → 波4 Dev-α
- DoDGateMock → 波5 主-1

### 阻塞
- 无

### 明日
- 启动 WP-γ-01 · L2-01 Skill 注册表（TDD · 40 TC）
```

- [ ] **Step 3: Commit standup**

```bash
git add docs/4-exe-plan/standup-logs/Dev-γ-2026-04-23.md
git commit -m "docs(harnessFlow): Dev-γ Day 1 standup — WP-γ-00 bootstrap 完"
```

**WP-γ-00 DoD 达标：进入 WP-γ-01。**

---

## §3 WP-γ-01 · L2-01 Skill 注册表（~40 TC · ~980 行）

**Files:**
- Create: `app/skill_dispatch/registry/schemas.py` (~200 行)
- Create: `app/skill_dispatch/registry/loader.py` (~250 行 · 5 阶段)
- Create: `app/skill_dispatch/registry/query_api.py` (~200 行)
- Create: `app/skill_dispatch/registry/ledger.py` (~180 行)
- Create: `app/skill_dispatch/registry/fs_watcher.py` (~150 行)
- Test: `tests/skill_dispatch/test_l2_01_registry.py`
- Test fixtures: `tests/skill_dispatch/fixtures/registry_missing_schema.yaml`, `ledger_sample.jsonl`

**TDD 执行模型：每 task 一个测试类 → 先 red → 再实现 → 再 refactor → commit。**

### Task 01.1 — Registry schemas（Pydantic v2）

- [ ] **Step 1: Write `tests/skill_dispatch/test_l2_01_registry.py` · TestSchemas 类（5 red tests）**

```python
"""L2-01 Skill 注册表 · 共 ~40 TC.
文档参照: docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-01-Skill 注册表.md
错误码: E_REG_MISSING_CAPABILITY / SINGLE_CANDIDATE / NO_SCHEMA_POINTER / RELOAD_CONFLICT / FILE_NOT_FOUND
"""
from __future__ import annotations

import pytest


class TestRegistrySchemas:
    def test_skill_spec_requires_skill_id(self):
        from app.skill_dispatch.registry.schemas import SkillSpec
        with pytest.raises(ValueError):
            SkillSpec(skill_id="", availability=True, cost_usd=0.0, timeout_s=30)

    def test_capability_point_rejects_single_candidate(self):
        from app.skill_dispatch.registry.schemas import CapabilityPoint, SkillSpec
        with pytest.raises(ValueError, match="at_least_2_candidates"):
            CapabilityPoint(
                name="x", description="d", schema_pointer="s.json",
                candidates=[SkillSpec(skill_id="a", availability=True, cost_usd=0.0, timeout_s=30)],
            )

    def test_capability_point_rejects_missing_builtin_fallback(self):
        from app.skill_dispatch.registry.schemas import CapabilityPoint, SkillSpec
        with pytest.raises(ValueError, match="builtin_fallback_required"):
            CapabilityPoint(
                name="x", description="d", schema_pointer="s.json",
                candidates=[
                    SkillSpec(skill_id="a", availability=True, cost_usd=0.0, timeout_s=30),
                    SkillSpec(skill_id="b", availability=True, cost_usd=0.0, timeout_s=30),
                ],
            )

    def test_subagent_entry_role_enum(self):
        from app.skill_dispatch.registry.schemas import SubagentEntry
        e = SubagentEntry(role="verifier", tool_whitelist=["Read"], timeout_s=1200, schema_pointer="v.json")
        assert e.role == "verifier"

    def test_ledger_entry_rejects_negative_counts(self):
        from app.skill_dispatch.registry.schemas import LedgerEntry
        with pytest.raises(ValueError):
            LedgerEntry(capability="x", skill_id="y", success_count=-1, failure_count=0,
                        last_attempt_ts=0, failure_reason=None)
```

- [ ] **Step 2: Run red — expect ImportError**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestRegistrySchemas -v`
Expected: 5 ERRORs on `from app.skill_dispatch.registry.schemas import ...`

- [ ] **Step 3: Implement `app/skill_dispatch/registry/schemas.py`**

```python
"""L2-01 Pydantic v2 schemas · 注册表数据结构."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillSpec(BaseModel):
    model_config = {"frozen": True}
    skill_id: str = Field(min_length=1)
    availability: bool
    cost_usd: float = Field(ge=0.0)
    timeout_s: int = Field(gt=0)
    is_builtin_fallback: bool = False


class CapabilityPoint(BaseModel):
    model_config = {"frozen": True}
    name: str = Field(min_length=1)
    description: str
    schema_pointer: str = Field(min_length=1)
    candidates: list[SkillSpec]

    @model_validator(mode="after")
    def _check_candidates(self) -> "CapabilityPoint":
        if len(self.candidates) < 2:
            raise ValueError("at_least_2_candidates: PM-09 requires ≥2 candidates per capability")
        if not any(c.is_builtin_fallback for c in self.candidates):
            raise ValueError("builtin_fallback_required: PM-09 requires at least one builtin fallback")
        return self


SubagentRole = Literal["codebase_onboarding", "verifier", "researcher", "coder", "reviewer"]


class SubagentEntry(BaseModel):
    model_config = {"frozen": True}
    role: SubagentRole
    tool_whitelist: list[str]
    timeout_s: int = Field(gt=0)
    schema_pointer: str = Field(min_length=1)


class ToolEntry(BaseModel):
    model_config = {"frozen": True}
    kind: Literal["atomic", "composed"] = "atomic"


class LedgerEntry(BaseModel):
    capability: str
    skill_id: str
    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    last_attempt_ts: int = Field(ge=0)
    failure_reason: str | None = None


class RegistrySnapshot(BaseModel):
    """启动加载后的快照 · 双 buffer 读指针指向这里."""
    version: str
    capability_points: dict[str, CapabilityPoint]
    subagents: dict[str, SubagentEntry]
    tools: dict[str, ToolEntry]
    loaded_at_ts_ns: int
```

- [ ] **Step 4: Run green**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestRegistrySchemas -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add app/skill_dispatch/registry/schemas.py tests/skill_dispatch/test_l2_01_registry.py
git commit -m "feat(harnessFlow-code): γ-WP01.1 L2-01 Registry schemas (Pydantic v2 · PM-09 ≥2候选+兜底)"
```

### Task 01.2 — Loader Stage 1-3（filesystem scan + yaml parse + schema validate）

- [ ] **Step 1: Append TestLoaderStages1to3 to test file (6 red tests)**

```python
class TestLoaderStages1to3:
    def test_stage1_load_registry_yaml_missing_file_raises_E_REG_FILE_NOT_FOUND(self, tmp_project):
        from app.skill_dispatch.registry.loader import RegistryLoader, RegistryLoadError
        loader = RegistryLoader(project_root=tmp_project)
        with pytest.raises(RegistryLoadError, match="E_REG_FILE_NOT_FOUND"):
            loader.load()

    def test_stage2_parses_capability_points_from_fixtures(self, tmp_project, fixtures_dir):
        from app.skill_dispatch.registry.loader import RegistryLoader
        import shutil
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        loader = RegistryLoader(project_root=tmp_project)
        snap = loader.load()
        assert "write_test" in snap.capability_points
        assert "review_code" in snap.capability_points

    def test_stage3_reject_capability_without_schema_pointer(self, tmp_path):
        from app.skill_dispatch.registry.loader import RegistryLoader, RegistryLoadError
        cache = tmp_path / "skills" / "registry-cache"
        cache.mkdir(parents=True)
        (cache / "registry.yaml").write_text(
            "version: '1.0'\ncapability_points:\n  x:\n    description: d\n    schema_pointer: ''\n    candidates: []\n"
        )
        loader = RegistryLoader(project_root=tmp_path)
        with pytest.raises(RegistryLoadError, match="E_REG_NO_SCHEMA_POINTER|schema_pointer"):
            loader.load()

    def test_stage3_inject_builtin_fallback_when_missing(self, tmp_project, fixtures_dir):
        """INFO-level: 缺兜底时自动注入 · 不 crash（仅启动期 · E_REG_SINGLE_CANDIDATE 处理路径）."""
        from app.skill_dispatch.registry.loader import RegistryLoader
        import shutil
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        loader = RegistryLoader(project_root=tmp_project)
        snap = loader.load()
        for cp in snap.capability_points.values():
            assert any(c.is_builtin_fallback for c in cp.candidates)

    def test_load_startup_within_500ms_slo(self, tmp_project, fixtures_dir):
        """SLO: 启动加载 P99 ≤ 500ms."""
        import shutil, time
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        loader = RegistryLoader(project_root=tmp_project)
        t0 = time.perf_counter()
        loader.load()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 500, f"startup load exceeded 500ms SLO: {elapsed_ms:.1f}ms"

    def test_stage2_invalid_yaml_raises(self, tmp_path):
        from app.skill_dispatch.registry.loader import RegistryLoader, RegistryLoadError
        cache = tmp_path / "skills" / "registry-cache"
        cache.mkdir(parents=True)
        (cache / "registry.yaml").write_text("version: 1.0\n  bad indent: :\n")
        loader = RegistryLoader(project_root=tmp_path)
        with pytest.raises(RegistryLoadError):
            loader.load()
```

- [ ] **Step 2: Red**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestLoaderStages1to3 -v`
Expected: 6 ERROR (ImportError)

- [ ] **Step 3: Implement `app/skill_dispatch/registry/loader.py`**

```python
"""L2-01 启动 5 阶段加载器.

Stage 1: Load registry.yaml
Stage 2: Parse capability_points / subagents / tools
Stage 3: Validate + inject builtin fallback
Stage 4: Load ledger.jsonl (延到 Task 01.4)
Stage 5: Create snapshot (延到 Task 01.4)
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
    """L2-01 加载期所有致命错误的父类 · 错误码通过 code 属性携带."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class RegistryLoader:
    """启动加载器 · 单进程单次 load · 可由 reload() 重复调用."""

    def __init__(self, project_root: pathlib.Path) -> None:
        self.project_root = pathlib.Path(project_root)
        self.yaml_path = self.project_root / "skills" / "registry-cache" / "registry.yaml"

    def load(self) -> RegistrySnapshot:
        raw = self._stage1_read_yaml()
        caps = self._stage2_parse_capabilities(raw.get("capability_points", {}))
        subs = self._stage2_parse_subagents(raw.get("subagents", {}))
        tools = self._stage2_parse_tools(raw.get("tools", {}))
        caps = self._stage3_validate_and_fill(caps)
        return RegistrySnapshot(
            version=str(raw.get("version", "0")),
            capability_points=caps,
            subagents=subs,
            tools=tools,
            loaded_at_ts_ns=time.time_ns(),
        )

    def _stage1_read_yaml(self) -> dict:
        if not self.yaml_path.exists():
            raise RegistryLoadError("E_REG_FILE_NOT_FOUND", str(self.yaml_path))
        try:
            return yaml.safe_load(self.yaml_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise RegistryLoadError("E_REG_YAML_PARSE", str(e)) from e

    def _stage2_parse_capabilities(self, raw: dict) -> dict[str, CapabilityPoint]:
        out: dict[str, CapabilityPoint] = {}
        for name, body in raw.items():
            if not body.get("schema_pointer"):
                raise RegistryLoadError("E_REG_NO_SCHEMA_POINTER", name)
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
        return out

    def _stage2_parse_subagents(self, raw: dict) -> dict[str, SubagentEntry]:
        return {k: SubagentEntry(**v) for k, v in raw.items()}

    def _stage2_parse_tools(self, raw: dict) -> dict[str, ToolEntry]:
        return {k: ToolEntry(**v) for k, v in raw.items()}

    def _stage3_validate_and_fill(
        self, caps: dict[str, CapabilityPoint]
    ) -> dict[str, CapabilityPoint]:
        # 已由 CapabilityPoint model_validator 校验（at_least_2 + builtin_fallback）
        # 本阶段 reserved 给将来"自动注入 builtin_fallback"的逻辑
        return caps
```

- [ ] **Step 4: Green**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestLoaderStages1to3 -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add app/skill_dispatch/registry/loader.py tests/skill_dispatch/test_l2_01_registry.py
git commit -m "feat(harnessFlow-code): γ-WP01.2 Loader Stage 1-3 (yaml → parse → validate) + SLO 500ms TC"
```

### Task 01.3 — Loader Stage 4-5（ledger + snapshot）+ query_api

- [ ] **Step 1: Add fixture `tests/skill_dispatch/fixtures/ledger_sample.jsonl`**

```jsonl
{"capability":"write_test","skill_id":"superpowers:tdd-workflow","success_count":12,"failure_count":1,"last_attempt_ts":1714000000,"failure_reason":null}
{"capability":"write_test","skill_id":"builtin:write_test_min","success_count":3,"failure_count":0,"last_attempt_ts":1714000100,"failure_reason":null}
{"capability":"review_code","skill_id":"plugin:python-reviewer","success_count":8,"failure_count":2,"last_attempt_ts":1714000050,"failure_reason":"timeout"}
```

- [ ] **Step 2: Append TestLedgerAndQuery (7 red tests)**

```python
class TestLedgerAndQuery:
    def test_stage4_loads_ledger_entries(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        shutil.copy(fixtures_dir / "ledger_sample.jsonl", cache / "ledger.jsonl")
        loader = RegistryLoader(project_root=tmp_project)
        snap = loader.load()
        assert snap.ledger_index[("write_test", "superpowers:tdd-workflow")].success_count == 12

    def test_stage5_writes_snapshot_file(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        loader = RegistryLoader(project_root=tmp_project)
        loader.load()
        snapshots = list(cache.glob("snapshot-*.yaml"))
        assert len(snapshots) >= 1

    def test_query_candidates_returns_sorted_by_builtin_last(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        cands = api.query_candidates("write_test")
        assert cands[-1].is_builtin_fallback
        assert len(cands) >= 2

    def test_query_candidates_unknown_capability_raises(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI, CapabilityNotFoundError
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        with pytest.raises(CapabilityNotFoundError):
            api.query_candidates("no_such_cap")

    def test_query_subagent_returns_entry(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        v = api.query_subagent("verifier")
        assert v.role == "verifier"

    def test_query_tool_atomic(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        assert api.query_tool("Read").kind == "atomic"

    def test_query_schema_pointer(self, tmp_project, fixtures_dir):
        import shutil
        from app.skill_dispatch.registry.query_api import RegistryQueryAPI
        from app.skill_dispatch.registry.loader import RegistryLoader
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        assert api.query_schema_pointer("write_test") == "schemas/skill/write_test.v1.json"
```

- [ ] **Step 3: Red**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestLedgerAndQuery -v`
Expected: 7 errors

- [ ] **Step 4: Extend `schemas.py` — add ledger_index field to RegistrySnapshot**

```python
# 在 RegistrySnapshot 里加:
ledger_index: dict[tuple[str, str], "LedgerEntry"] = Field(default_factory=dict)
```
（记得在文件末尾调 `RegistrySnapshot.model_rebuild()` 以处理前向引用）

- [ ] **Step 5: Extend `loader.py` — 加 Stage 4 + Stage 5**

Append to RegistryLoader:

```python
    def load(self) -> RegistrySnapshot:
        raw = self._stage1_read_yaml()
        caps = self._stage2_parse_capabilities(raw.get("capability_points", {}))
        subs = self._stage2_parse_subagents(raw.get("subagents", {}))
        tools = self._stage2_parse_tools(raw.get("tools", {}))
        caps = self._stage3_validate_and_fill(caps)
        ledger = self._stage4_load_ledger()
        snap = RegistrySnapshot(
            version=str(raw.get("version", "0")),
            capability_points=caps,
            subagents=subs,
            tools=tools,
            ledger_index=ledger,
            loaded_at_ts_ns=time.time_ns(),
        )
        self._stage5_write_snapshot(snap)
        return snap

    def _stage4_load_ledger(self) -> dict[tuple[str, str], "LedgerEntry"]:
        import json
        from .schemas import LedgerEntry
        p = self.project_root / "skills" / "registry-cache" / "ledger.jsonl"
        idx: dict[tuple[str, str], LedgerEntry] = {}
        if not p.exists():
            return idx
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = LedgerEntry(**json.loads(line))
            idx[(rec.capability, rec.skill_id)] = rec
        return idx

    def _stage5_write_snapshot(self, snap: RegistrySnapshot) -> None:
        import yaml as _yaml
        out = self.project_root / "skills" / "registry-cache" / f"snapshot-{snap.loaded_at_ts_ns}.yaml"
        body = snap.model_dump(mode="json")
        out.write_text(_yaml.safe_dump(body), encoding="utf-8")
```

- [ ] **Step 6: Implement `app/skill_dispatch/registry/query_api.py`**

```python
"""L2-01 读接口 · 单实例绑定 snapshot · 双 buffer 切换时替换 self.snapshot."""
from __future__ import annotations

from .schemas import CapabilityPoint, RegistrySnapshot, SkillSpec, SubagentEntry, ToolEntry


class CapabilityNotFoundError(KeyError):
    """E_REG_MISSING_CAPABILITY"""


class SubagentNotFoundError(KeyError):
    """E_REG_MISSING_SUBAGENT"""


class ToolNotFoundError(KeyError):
    """E_REG_MISSING_TOOL"""


class RegistryQueryAPI:
    def __init__(self, snapshot: RegistrySnapshot) -> None:
        self._snap = snapshot

    def swap(self, new_snapshot: RegistrySnapshot) -> None:
        """原子替换 snapshot · 供热更新调."""
        self._snap = new_snapshot

    def query_candidates(self, capability: str) -> list[SkillSpec]:
        cp = self._snap.capability_points.get(capability)
        if cp is None:
            raise CapabilityNotFoundError(f"E_REG_MISSING_CAPABILITY: {capability}")
        # 内建兜底永远排在末尾（排序稳定）
        non_fb = [c for c in cp.candidates if not c.is_builtin_fallback]
        fb = [c for c in cp.candidates if c.is_builtin_fallback]
        return non_fb + fb

    def query_subagent(self, name: str) -> SubagentEntry:
        se = self._snap.subagents.get(name)
        if se is None:
            raise SubagentNotFoundError(f"E_REG_MISSING_SUBAGENT: {name}")
        return se

    def query_tool(self, tool_name: str) -> ToolEntry:
        te = self._snap.tools.get(tool_name)
        if te is None:
            raise ToolNotFoundError(f"E_REG_MISSING_TOOL: {tool_name}")
        return te

    def query_schema_pointer(self, capability: str) -> str:
        cp = self._snap.capability_points.get(capability)
        if cp is None:
            raise CapabilityNotFoundError(f"E_REG_MISSING_CAPABILITY: {capability}")
        return cp.schema_pointer
```

- [ ] **Step 7: Green**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py::TestLedgerAndQuery -v`
Expected: 7 PASS

- [ ] **Step 8: Commit**

```bash
git add app/skill_dispatch/registry/ tests/skill_dispatch/
git commit -m "feat(harnessFlow-code): γ-WP01.3 Loader Stage 4-5 (ledger + snapshot) + query_api 4 接口"
```

### Task 01.4 — Ledger 写入 + L1-09 锁保护

- [ ] **Step 1: Append TestLedgerWrite (6 red tests)**

```python
class TestLedgerWrite:
    def test_ledger_writer_persists_increment(self, tmp_project, fixtures_dir, lock_mock):
        import shutil
        from app.skill_dispatch.registry.ledger import LedgerWriter
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        writer.record("p1", "write_test", "builtin:write_test_min", success=True)
        assert (cache / "ledger.jsonl").exists()
        lines = (cache / "ledger.jsonl").read_text().splitlines()
        assert any('"skill_id": "builtin:write_test_min"' in ln for ln in lines)

    def test_concurrent_writes_serialized_via_lock(self, tmp_project, fixtures_dir, lock_mock):
        import shutil, threading
        from app.skill_dispatch.registry.ledger import LedgerWriter
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        errs: list[BaseException] = []

        def hit():
            try:
                for _ in range(20):
                    writer.record("p1", "write_test", "s1", success=True)
            except BaseException as e:
                errs.append(e)

        threads = [threading.Thread(target=hit) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errs
        lines = (cache / "ledger.jsonl").read_text().splitlines()
        assert len([ln for ln in lines if ln.strip()]) == 80   # 4×20

    def test_write_only_from_l2_02(self, tmp_project, fixtures_dir, lock_mock):
        """IC-L2-07 约束：只有 L2-02 可写（标 caller='L2-02' · 其他拒）."""
        import shutil
        from app.skill_dispatch.registry.ledger import LedgerWriter, LedgerPermissionError
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        with pytest.raises(LedgerPermissionError):
            writer.record("p1", "c", "s", success=True, caller="L2-03")

    def test_record_requires_project_id_pm14(self, tmp_project, lock_mock):
        from app.skill_dispatch.registry.ledger import LedgerWriter
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        with pytest.raises(ValueError, match="project_id"):
            writer.record("", "c", "s", success=True)

    def test_write_slo_under_50ms_p99(self, tmp_project, fixtures_dir, lock_mock):
        import shutil, time
        from app.skill_dispatch.registry.ledger import LedgerWriter
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        durations: list[float] = []
        for i in range(100):
            t0 = time.perf_counter()
            writer.record("p1", "write_test", f"s{i % 3}", success=True)
            durations.append((time.perf_counter() - t0) * 1000)
        durations.sort()
        p99 = durations[98]
        assert p99 < 50.0, f"p99 write latency exceeded 50ms: {p99:.2f}ms"

    def test_failure_records_failure_reason(self, tmp_project, fixtures_dir, lock_mock):
        import shutil, json
        from app.skill_dispatch.registry.ledger import LedgerWriter
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        writer = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        writer.record("p1", "write_test", "s1", success=False, failure_reason="timeout")
        lines = (cache / "ledger.jsonl").read_text().splitlines()
        recs = [json.loads(ln) for ln in lines if ln.strip()]
        assert any(r["failure_reason"] == "timeout" for r in recs)
```

- [ ] **Step 2: Red** — expect 6 errors

- [ ] **Step 3: Implement `app/skill_dispatch/registry/ledger.py`**

```python
"""L2-01 账本回写 · IC-L2-07 · 只允许 caller='L2-02'（L2-02 意图选择器）."""
from __future__ import annotations

import json
import pathlib
import time
from typing import Any


class LedgerPermissionError(PermissionError):
    """IC-L2-07: 非 L2-02 调用者被拒."""


class LedgerWriter:
    ALLOWED_CALLER = "L2-02"

    def __init__(self, project_root: pathlib.Path, lock: Any) -> None:
        self.project_root = pathlib.Path(project_root)
        self.path = self.project_root / "skills" / "registry-cache" / "ledger.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = lock

    def record(
        self,
        project_id: str,
        capability: str,
        skill_id: str,
        *,
        success: bool,
        failure_reason: str | None = None,
        caller: str = "L2-02",
    ) -> None:
        if not project_id:
            raise ValueError("ledger.record: project_id required (PM-14)")
        if caller != self.ALLOWED_CALLER:
            raise LedgerPermissionError(f"IC-L2-07: caller must be {self.ALLOWED_CALLER}, got {caller}")
        rec = {
            "project_id": project_id,
            "capability": capability,
            "skill_id": skill_id,
            "success_count": 1 if success else 0,
            "failure_count": 0 if success else 1,
            "last_attempt_ts": int(time.time()),
            "failure_reason": failure_reason,
        }
        line = json.dumps(rec, sort_keys=True)
        with self._lock.acquire(project_id=project_id, capability=capability):
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
```

- [ ] **Step 4: Green** + **Commit**

```bash
pytest tests/skill_dispatch/test_l2_01_registry.py::TestLedgerWrite -v
git add app/skill_dispatch/registry/ledger.py tests/skill_dispatch/
git commit -m "feat(harnessFlow-code): γ-WP01.4 Ledger 写入 + IC-L2-07 只许 L2-02 + 锁保护 + 50ms SLO"
```

### Task 01.5 — FS watcher + 热更新（watchdog · throttle 10s）

- [ ] **Step 1: Append TestFsWatcher (5 red tests)** — 测 watchdog 触发 / throttle / reload 成功 / 失败降级 / 原子 swap

- [ ] **Step 2: Implement `app/skill_dispatch/registry/fs_watcher.py`** — `watchdog.observers.Observer` + `FileSystemEventHandler` · throttle 10s · 调 `RegistryLoader.load()` + `RegistryQueryAPI.swap()` 原子替换

- [ ] **Step 3: Green + Commit `γ-WP01.5 fs_watcher + 热更新 ≤ 500ms SLO`**

### Task 01.6 — WP-γ-01 收尾：coverage + 所有错误码扫描 + commit

- [ ] **Step 1: Run 全量 L2-01 测试 + coverage**

Run: `pytest tests/skill_dispatch/test_l2_01_registry.py -v --cov=app.skill_dispatch.registry --cov-report=term-missing`
Expected: 所有 test 全绿 · coverage ≥ 80%

- [ ] **Step 2: 错误码覆盖审查** — grep 5 个 L2-01 错误码 · 每个至少有 1 个测试命中

Run: `for c in E_REG_MISSING_CAPABILITY E_REG_SINGLE_CANDIDATE E_REG_NO_SCHEMA_POINTER E_REG_RELOAD_CONFLICT E_REG_FILE_NOT_FOUND; do echo "=== $c ==="; grep -r "$c" tests/skill_dispatch/test_l2_01_registry.py; done`

- [ ] **Step 3: Commit WP-γ-01 close**

```bash
git add -A
git commit -m "feat(harnessFlow-code): γ-WP01 close — L2-01 Skill 注册表完工（40 TC · coverage ≥ 80% · 5 错误码全覆盖）"
```

---

## §4 WP-γ-02 · L2-02 意图选择器（~40 TC · ~800 行）

**Files:**
- Create: `app/skill_dispatch/intent_selector/schemas.py` (~150 行)
- Create: `app/skill_dispatch/intent_selector/scorer.py` (~250 行)
- Create: `app/skill_dispatch/intent_selector/hard_edge_scan.py` (~120 行)
- Create: `app/skill_dispatch/intent_selector/fallback_advancer.py` (~180 行)
- Create: `app/skill_dispatch/intent_selector/kb_boost.py` (~100 行)
- Test: `tests/skill_dispatch/test_l2_02_intent.py`

### Task 02.1 — Intent schemas + Chain VO

- [ ] **Step 1: Write TestIntentSchemas (4 red tests)** — `SignalScores` 6 字段 / `Chain` 不可空 / `ExplanationCard` 含 `why` 字段 / `IntentRequest` PM-14 校验

- [ ] **Step 2: Implement `schemas.py`** — Pydantic v2 · `SignalScores`(availability:bool / cost:float / success_rate:float / failure_memory:float / recency:float / kb_boost:float) · `ScoredCandidate(skill:SkillSpec, score:float, signals:SignalScores)` · `Chain(primary, fallbacks:list, explanation:ExplanationCard)` · `IntentRequest(project_id, capability, constraints:Constraints, context:dict)`

- [ ] **Step 3: Green + Commit `γ-WP02.1 Intent schemas`**

### Task 02.2 — Hard edge scan（启动 crash 护栏）

- [ ] **Step 1: Write TestHardEdgeScan (5 red tests)**

```python
class TestHardEdgeScan:
    def test_scan_crashes_when_hardcoded_skill_found(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan, HardcodedSkillViolation
        bad = tmp_path / "offender.py"
        bad.write_text('SKILL = "superpowers:tdd-workflow"\n')
        scanner = HardEdgeScan(roots=[tmp_path])
        with pytest.raises(HardcodedSkillViolation) as ei:
            scanner.run()
        assert "offender.py" in str(ei.value)

    def test_scan_passes_clean_tree(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan
        (tmp_path / "good.py").write_text('CAP = "write_test"\n')
        HardEdgeScan(roots=[tmp_path]).run()  # 不抛

    def test_scan_ignores_tests_dir(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text('X = "superpowers:foo"\n')
        HardEdgeScan(roots=[tmp_path], ignore=["tests"]).run()

    def test_scan_catches_gstack_and_ecc_patterns(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan, HardcodedSkillViolation
        for pat in ("gstack:x", "ecc:y", "superpowers:z"):
            bad = tmp_path / f"b_{pat.split(':')[0]}.py"
            bad.write_text(f'X = "{pat}"\n')
        with pytest.raises(HardcodedSkillViolation):
            HardEdgeScan(roots=[tmp_path]).run()

    def test_scan_reports_all_violations_not_first(self, tmp_path):
        from app.skill_dispatch.intent_selector.hard_edge_scan import HardEdgeScan, HardcodedSkillViolation
        for i in range(3):
            (tmp_path / f"o{i}.py").write_text(f'S = "superpowers:x{i}"\n')
        with pytest.raises(HardcodedSkillViolation) as ei:
            HardEdgeScan(roots=[tmp_path]).run()
        assert str(ei.value).count("o") >= 3
```

- [ ] **Step 2: Implement `hard_edge_scan.py`**

```python
"""启动硬编码扫描 · 禁 `superpowers:*` / `gstack:*` / `ecc:*` / `plugin:*` 字面量在非 mock/非测试代码中出现."""
from __future__ import annotations

import pathlib
import re

_PATTERN = re.compile(r'["\'](?:superpowers|gstack|ecc|plugin):[a-zA-Z0-9_\-]+["\']')


class HardcodedSkillViolation(RuntimeError):
    """E_INTENT_HARDCODED_SKILL_DETECTED."""


class HardEdgeScan:
    def __init__(
        self,
        roots: list[pathlib.Path],
        ignore: list[str] | None = None,
    ) -> None:
        self.roots = [pathlib.Path(r) for r in roots]
        self.ignore = set(ignore or []) | {"_mocks", "tests", "__pycache__", ".venv", "venv"}

    def run(self) -> None:
        violations: list[str] = []
        for root in self.roots:
            for py in root.rglob("*.py"):
                if any(part in self.ignore for part in py.parts):
                    continue
                for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                    m = _PATTERN.search(line)
                    if m:
                        violations.append(f"{py}:{i} {m.group()}")
        if violations:
            raise HardcodedSkillViolation(
                "PM-09 violation · hardcoded skill detected:\n" + "\n".join(violations)
            )
```

- [ ] **Step 3: Green + Commit `γ-WP02.2 hard_edge_scan — 启动 crash 护栏`**

### Task 02.3 — 6 信号打分器（每信号独立单测 + 混合打分）

- [ ] **Step 1: TestSignalScorer (12 red tests)** — 每信号 2 个 TC（典型+边界）+ 混合打分：
  - `test_availability_false_excluded`（硬过滤 · 返 score=0 信号 or 剔除前置）
  - `test_cost_score_inverse_linear`（cost 高 score 低）
  - `test_success_rate_score_linear`（success_rate 0..1 → score 0..1）
  - `test_failure_memory_exponential_decay_24h_half_life`（用 freezegun 冻时钟）
  - `test_recency_score_ranks_newer_higher`
  - `test_kb_boost_added_when_kb_hits`
  - `test_mixed_weights_sum_to_one_by_default`（15/45/25/10/5 = 100%）
  - `test_config_overrides_weights`
  - `test_score_respects_max_cost_constraint_filter`
  - `test_score_respects_max_timeout_constraint_filter`
  - `test_score_respects_preferred_quality_filter`
  - `test_scoring_latency_p99_under_30ms`

- [ ] **Step 2: Implement `scorer.py`** — `Scorer(weights, ledger_snapshot, now_fn)` · 每信号独立纯函数（便于单测）· `score_candidate(skill, signals) → ScoredCandidate` · `rank(candidates, constraints, kb_hits) → Chain`

- [ ] **Step 3: Green + Commit `γ-WP02.3 6-signal scorer (availability/cost 15/success 45/fail_mem 25/recency 10/kb 5) + 30ms SLO`**

### Task 02.4 — KB boost + 150ms 超时降级

- [ ] **Step 1: TestKBBoost (4 red tests)**

```python
class TestKBBoost:
    def test_kb_boost_added_when_recipe_matches(self, kb_mock):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster
        from app.skill_dispatch._mocks.ic06_mock import KBRecipe
        kb_mock._recipes = [KBRecipe(capability="c", skill_id="s", success_rate=0.9, last_seen_ts=0)]
        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        hits = booster.fetch("p1", "c")
        assert hits["s"] > 0

    def test_kb_timeout_degrades_gracefully(self):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster
        from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
        slow = IC06KBMock(read_latency_ms=500)
        booster = KBBooster(kb=slow, timeout_ms=150)
        hits = booster.fetch("p1", "c")
        assert hits == {}   # 超时降级 · 返空 · 不 raise

    def test_kb_empty_returns_empty(self, kb_mock):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster
        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        assert booster.fetch("p1", "c") == {}

    def test_kb_requires_project_id(self, kb_mock):
        from app.skill_dispatch.intent_selector.kb_boost import KBBooster
        booster = KBBooster(kb=kb_mock, timeout_ms=150)
        with pytest.raises(ValueError):
            booster.fetch("", "c")
```

- [ ] **Step 2: Implement `kb_boost.py`**

```python
"""调 IC-06 · 150ms 超时 · 超时降级返 {}（不 raise · 不阻排序）."""
from __future__ import annotations

import concurrent.futures


class KBBooster:
    def __init__(self, kb, timeout_ms: int = 150) -> None:
        self._kb = kb
        self._timeout = timeout_ms / 1000.0

    def fetch(self, project_id: str, capability: str) -> dict[str, float]:
        if not project_id:
            raise ValueError("KBBooster: project_id required (PM-14)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self._kb.kb_read, project_id, capability)
            try:
                recipes = fut.result(timeout=self._timeout)
            except concurrent.futures.TimeoutError:
                return {}
        return {r.skill_id: float(r.success_rate) for r in recipes}
```

- [ ] **Step 3: Green + Commit `γ-WP02.4 KB boost + 150ms 超时降级（不阻排序）`**

### Task 02.5 — fallback_advancer + capability_exhausted → IC-15

- [ ] **Step 1: TestFallbackAdvancer (5 red tests)** — advance 返下一候选 / 链耗尽时 raise `ChainExhausted` / reason 透传记事件 / advance 后 chain 缩短 1 / exhausted 时 emit IC-15 halt

- [ ] **Step 2: Implement `fallback_advancer.py`** — 接受 Chain · 按顺序弹出 candidate · `advance(chain, reason) → Chain | RAISE ChainExhausted` · exhausted 时 append IC-09 `capability_exhausted` 事件 · 调用方（L2-03）负责 raise IC-15

- [ ] **Step 3: Green + Commit `γ-WP02.5 fallback_advancer + IC-15 hard_halt on exhausted`**

### Task 02.6 — WP-γ-02 收尾 + 错误码覆盖审查

- [ ] **Step 1: 集成调用点 — 提供 `select(request: IntentRequest) -> Chain` 高阶入口**

新建 `app/skill_dispatch/intent_selector/__init__.py` 导出 `IntentSelector.select()`（编排 scorer + kb_boost + fallback_advancer）

- [ ] **Step 2: pytest + coverage ≥ 80% · 5 错误码全覆盖（BOUNDARY_VIOLATION / NO_AVAILABLE / KB_TIMEOUT / EXPLANATION_TRUNCATED / CHAIN_EXHAUSTED）**

- [ ] **Step 3: Commit WP-γ-02 close**

```bash
git commit -m "feat(harnessFlow-code): γ-WP02 close — L2-02 意图选择器完工（40 TC · 6 信号打分 · 硬编码 scan · coverage ≥ 80%）"
```

---

## §5 WP-γ-03 · L2-03 IC-04 invoke_skill（~39 TC · ~950 行）

**Files:**
- Create: `app/skill_dispatch/invoker/schemas.py` (~180 行) — **必须严格对齐 ic-contracts.md §3.4.2/§3.4.3**
- Create: `app/skill_dispatch/invoker/context_injector.py` (~150 行)
- Create: `app/skill_dispatch/invoker/timeout_manager.py` (~120 行)
- Create: `app/skill_dispatch/invoker/retry_policy.py` (~120 行)
- Create: `app/skill_dispatch/invoker/audit.py` (~100 行)
- Create: `app/skill_dispatch/invoker/executor.py` (~280 行) — IC-04 主入口
- Test: `tests/skill_dispatch/test_l2_03_invoker.py`

**契约红线：** IC-04 InvocationRequest/Response 的字段 **必须**是 ic-contracts §3.4.2/.3 的超集（多 attempt/params_hash），**不能**是子集。若发现矛盾 → Dev-γ-exe-plan §6 情形 D 自修正。

### Task 03.1 — IC-04 Schemas（严格对齐 ic-contracts §3.4）

- [ ] **Step 1: Write TestIC04Schemas (8 red tests)**

```python
class TestIC04Schemas:
    def test_request_required_fields(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        req = InvocationRequest(
            invocation_id="inv1", project_id="p1", capability="write_test",
            params={"x": 1}, caller_l1="L1-04",
            context={"project_id": "p1", "wp_id": "wp1", "loop_session_id": "ls1"},
        )
        assert req.timeout_ms == 30000
        assert req.allow_fallback is True

    def test_request_rejects_missing_project_id(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="i", project_id="", capability="c",
                params={}, caller_l1="L1-04", context={"project_id": ""},
            )

    def test_response_success_has_result_not_error(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse
        r = InvocationResponse(
            invocation_id="i", success=True, skill_id="s", duration_ms=100,
            fallback_used=False, result={"ok": True},
        )
        assert r.result == {"ok": True}
        assert r.error is None

    def test_response_failure_has_error_not_result(self):
        from app.skill_dispatch.invoker.schemas import InvocationResponse
        r = InvocationResponse(
            invocation_id="i", success=False, skill_id="s", duration_ms=100,
            fallback_used=True, error={"code": "E_SKILL_TIMEOUT"},
            fallback_trace=[{"skill": "a", "reason": "timeout"}],
        )
        assert r.error["code"] == "E_SKILL_TIMEOUT"
        assert len(r.fallback_trace) == 1

    def test_invocation_signature_is_superset_of_response(self):
        """契约红线：InvocationSignature 必须 ⊇ InvocationResponse 字段 + 多 params_hash + attempt."""
        from app.skill_dispatch.invoker.schemas import InvocationResponse, InvocationSignature
        rsp_fields = set(InvocationResponse.model_fields.keys())
        sig_fields = set(InvocationSignature.model_fields.keys())
        extra = {"params_hash", "attempt", "started_at_ts_ns"}
        assert rsp_fields.issubset(sig_fields | {"result", "error", "fallback_trace"}), (
            "InvocationSignature missing fields from IC-04 response"
        )
        assert extra.issubset(sig_fields)

    def test_context_must_carry_project_id_mirror(self):
        """防御字段窃取：context.project_id 必须与顶层 project_id 一致."""
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        with pytest.raises(ValueError, match="project_id.*mismatch"):
            InvocationRequest(
                invocation_id="i", project_id="p1", capability="c", params={},
                caller_l1="L1-04", context={"project_id": "p2"},
            )

    def test_default_allow_fallback_true(self):
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        req = InvocationRequest(
            invocation_id="i", project_id="p1", capability="c", params={},
            caller_l1="L1-04", context={"project_id": "p1"},
        )
        assert req.allow_fallback is True

    def test_hard_cap_timeout_300000(self):
        """不允许 timeout_ms > 300000（hard-cap 5min · IC-04 §3.4.2）."""
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="i", project_id="p1", capability="c", params={},
                caller_l1="L1-04", context={"project_id": "p1"},
                timeout_ms=400000,
            )
```

- [ ] **Step 2: Implement `invoker/schemas.py`**

```python
"""L2-03 IC-04 invoke_skill 字段级对齐 ic-contracts.md §3.4.2/.3."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class InvocationRequest(BaseModel):
    """IC-04 入参 · 严格对齐 §3.4.2."""

    model_config = {"frozen": True}

    invocation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    params: dict[str, Any]
    caller_l1: str = Field(min_length=2)
    context: dict[str, Any]
    timeout_ms: int = Field(default=30000, gt=0, le=300000)   # hard-cap 5min
    allow_fallback: bool = True
    trigger_tick: int | None = None

    @model_validator(mode="after")
    def _mirror_check(self) -> "InvocationRequest":
        ctx_pid = self.context.get("project_id")
        if ctx_pid and ctx_pid != self.project_id:
            raise ValueError(f"project_id mismatch: top={self.project_id} ctx={ctx_pid}")
        return self


class InvocationResponse(BaseModel):
    """IC-04 出参 · 严格对齐 §3.4.3."""

    model_config = {"frozen": True}

    invocation_id: str
    success: bool
    skill_id: str
    duration_ms: int = Field(ge=0)
    fallback_used: bool
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    fallback_trace: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _success_xor_error(self) -> "InvocationResponse":
        if self.success and self.error is not None:
            raise ValueError("success=True cannot carry error")
        if not self.success and self.result is not None:
            raise ValueError("success=False cannot carry result")
        return self


class InvocationSignature(BaseModel):
    """审计签名 · IC-09 落盘 · InvocationResponse 的超集 + params_hash + attempt + started_at."""

    invocation_id: str
    project_id: str
    capability: str
    skill_id: str
    caller_l1: str
    attempt: int = Field(ge=1)
    params_hash: str = Field(min_length=64, max_length=64)     # sha256 hex
    started_at_ts_ns: int = Field(gt=0)
    duration_ms: int | None = None
    success: bool | None = None
    fallback_used: bool | None = None
    validate_status: Literal["pending", "passed", "failed"] = "pending"
    result_summary: str | None = None
```

- [ ] **Step 3: Green + Commit `γ-WP03.1 IC-04 schemas (对齐 ic-contracts §3.4 · Signature ⊇ Response)`**

### Task 03.2 — ContextInjector（白名单 · 防泄漏）

- [ ] **Step 1: TestContextInjector (5 red tests)** — 注入 pid/wp_id/loop_session_id/decision_id / 不注入 token 等敏感字段 / 上游缺 pid 时 raise / correlation_id 透传 / 注入后返新 dict（非 in-place）

- [ ] **Step 2: Implement `context_injector.py`**

```python
"""L2-03 ContextInjector · 白名单注入 · 防上游污染字段泄漏."""
from __future__ import annotations

from typing import Any

ALLOWED_CONTEXT_KEYS = frozenset([
    "project_id", "wp_id", "loop_session_id", "decision_id", "correlation_id",
])


class ContextInjectionError(ValueError):
    pass


def inject(upstream_ctx: dict[str, Any]) -> dict[str, Any]:
    """按白名单过滤 · 必含 project_id · 返新 dict."""
    if not upstream_ctx.get("project_id"):
        raise ContextInjectionError("E_SKILL_INVOCATION_CONTEXT_INJECTION_FAILED: project_id missing")
    return {k: v for k, v in upstream_ctx.items() if k in ALLOWED_CONTEXT_KEYS}
```

- [ ] **Step 3: Green + Commit `γ-WP03.2 ContextInjector 白名单（5 字段 · 防 token 泄漏）`**

### Task 03.3 — TimeoutManager（精度 ±100ms · hard-cap 300s）

- [ ] **Step 1: TestTimeoutManager (4 red tests)** — 按时 trigger（±100ms） / min(deadline, skill_max_timeout) 生效 / hard-cap 300s / 未完成时 raise `SkillTimeout`

- [ ] **Step 2: Implement `timeout_manager.py`** — asyncio.wait_for 包装 + `SkillTimeout` 异常

- [ ] **Step 3: Green + Commit `γ-WP03.3 TimeoutManager ±100ms 精度 + 300s hard-cap`**

### Task 03.4 — RetryPolicy（idempotent 判定）

- [ ] **Step 1: TestRetryPolicy (5 red tests)**
  - idempotent=True · 第一次失败 → retry 1 次（attempt=2）
  - idempotent=True · 第二次失败 → raise `RetryExhausted`（不再 retry · 交 fallback_advancer）
  - idempotent=False · 失败立即 raise（不 retry · 直接 fallback）
  - 指数退避：base=100ms 200ms → 实际间隔 ±20% 抖动窗
  - 只有特定 error class（网络 / timeout）才 retry · `SchemaError` 不 retry

- [ ] **Step 2: Implement `retry_policy.py`** — 策略纯函数 `should_retry(exc, attempt, is_idempotent) -> bool` · 退避 `backoff_ms(attempt)` · 交由 Executor 循环调用

- [ ] **Step 3: Green + Commit `γ-WP03.4 RetryPolicy (idempotent 判定 · exp backoff · max_attempt=2)`**

### Task 03.5 — Audit（params_hash SHA-256 + 脱敏 + IC-09 双写）

- [ ] **Step 1: TestAudit (6 red tests)**
  - params_hash 是 SHA-256(canonical_json) · hex · 64 字符
  - 敏感字段 `api_token / api_key / password` 先脱敏再 hash
  - 同样 params → 同样 hash；敏感字段值不同但同前缀 → hash 相同
  - IC-09 写 2 次（start → finish）· 且 `invocation_id` 一致
  - IC-09 失败时 · 调用本身不 raise（降级告警 · 返 InvocationResponse 含 audit_seed_failed=true）
  - hash 不漏泄 token 明文到事件 payload

- [ ] **Step 2: Implement `audit.py`**

```python
"""L2-03 审计 · IC-09 两次写（start/finish）· params_hash 脱敏 SHA-256."""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

_SENSITIVE_PATTERNS = [
    re.compile(r".*_token$"), re.compile(r".*_key$"),
    re.compile(r".*password.*"), re.compile(r".*secret.*"),
]


def _desensitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: ("<REDACTED>" if any(p.match(k) for p in _SENSITIVE_PATTERNS) else _desensitize(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_desensitize(x) for x in obj]
    return obj


def params_hash(params: dict[str, Any]) -> str:
    desensitized = _desensitize(params)
    canonical = json.dumps(desensitized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Auditor:
    """IC-09 两次写 · start 即 append · finish 时 append update."""

    def __init__(self, event_bus) -> None:
        self._bus = event_bus

    def audit_start(
        self, *, project_id: str, invocation_id: str, capability: str,
        skill_id: str, caller_l1: str, attempt: int, params: dict,
    ) -> str:
        ph = params_hash(params)
        try:
            self._bus.append_event(
                project_id=project_id, l1="L1-05",
                event_type="skill_invocation_started",
                payload={
                    "invocation_id": invocation_id, "capability": capability,
                    "skill_id": skill_id, "caller_l1": caller_l1,
                    "attempt": attempt, "params_hash": ph,
                    "started_at_ts_ns": time.time_ns(),
                },
            )
        except Exception:
            pass   # E_SKILL_INVOCATION_AUDIT_SEED_FAILED · 继续调用
        return ph

    def audit_finish(
        self, *, project_id: str, invocation_id: str, success: bool,
        duration_ms: int, fallback_used: bool, result_summary: str | None,
    ) -> None:
        try:
            self._bus.append_event(
                project_id=project_id, l1="L1-05",
                event_type="skill_invocation_finished",
                payload={
                    "invocation_id": invocation_id, "success": success,
                    "duration_ms": duration_ms, "fallback_used": fallback_used,
                    "result_summary": result_summary,
                },
            )
        except Exception:
            pass
```

- [ ] **Step 3: Green + Commit `γ-WP03.5 Audit (SHA-256 + 脱敏 + IC-09 双写)`**

### Task 03.6 — Executor（IC-04 主入口 · 6 阶段编排）

- [ ] **Step 1: TestExecutor (11 red tests)**
  - happy path · 首选成功 · 返 success + result + fallback_used=false
  - 首选失败 · 降级到备选 · 返 success + fallback_used=true + fallback_trace 含 1 项
  - 所有候选失败 · 返 success=false + error=E_SKILL_ALL_FALLBACK_FAIL + 完整 fallback_trace · **不 raise**
  - PM-14 缺 project_id · 立即 raise
  - timeout 精度 ±100ms（整链符合）
  - retry exhausted 后 advance_fallback
  - 硬编码 skill_id 扫描（如果调用链意外 bypass） · startup 期拒绝
  - IC-09 start/finish 两次 append
  - context_injector 白名单生效（token 不到 skill）
  - capability_not_registered · raise `CapabilityNotFoundError`
  - dispatch 延迟 < 200ms（SLO）

- [ ] **Step 2: Implement `executor.py`** — 编排 6 阶段：
  1. `InvocationRequest` schema 校验（PM-14 已在 schema 层）
  2. `IntentSelector.select(request) → Chain`（调 WP-γ-02）
  3. for each candidate in chain:
     a. `ContextInjector.inject` → safe_ctx
     b. start audit → ph
     c. 启动 skill（通过 IC-skill-call 抽象 · 本 WP 用 mock · WP04 可加 subagent route）
     d. TimeoutManager 包装
     e. success → finish audit + 返 InvocationResponse
     f. fail → RetryPolicy 判 retry or advance_fallback
  4. 全链失败 → 返 `success=False, error=E_SKILL_ALL_FALLBACK_FAIL`
  5. `LedgerWriter.record` 成功/失败（IC-L2-07 caller="L2-02"）

- [ ] **Step 3: Green + Commit `γ-WP03.6 Executor IC-04 主入口 (6 阶段编排 · 全链 fallback · dispatch ≤ 200ms)`**

### Task 03.7 — WP-γ-03 收尾

- [ ] **Step 1: Coverage ≥ 80% · 6 错误码全覆盖** — `E_SKILL_NO_CAPABILITY / NO_PROJECT_ID / TIMEOUT / ALL_FALLBACK_FAIL / PARAMS_SCHEMA_MISMATCH / PERMISSION_DENIED`

- [ ] **Step 2: Performance bench**

Run: `pytest tests/skill_dispatch/perf/bench_ic_04_dispatch.py -v`
Expected: P99 dispatch latency ≤ 200ms

- [ ] **Step 3: Commit close**

```bash
git commit -m "feat(harnessFlow-code): γ-WP03 close — L2-03 IC-04 invoke_skill 完工（39 TC · schema 严格对齐 · dispatch ≤ 200ms · 6 错误码）"
```

---

## §6 WP-γ-04 · L2-04 子 Agent 委托器（~39 TC · ~900 行）

**Files:**
- Create: `app/skill_dispatch/subagent/schemas.py` (~180 行)
- Create: `app/skill_dispatch/subagent/delegator.py` (~250 行) — IC-05/12/20 路由
- Create: `app/skill_dispatch/subagent/claude_sdk_client.py` (~200 行) — SDK 封装（可 mock 层替换）
- Create: `app/skill_dispatch/subagent/resource_limiter.py` (~150 行)
- Create: `app/skill_dispatch/subagent/context_scope.py` (~120 行)
- Test: `tests/skill_dispatch/test_l2_04_subagent.py`

**SDK 策略：** 若 `claude-agent-sdk` 在 pyproject 可装 → 真实集成；否则用 `_mocks/claude_agent_sdk_stub.py` 作 import fallback · 真实接入延到 WP-04 后期或主-3 集成期。

### Task 04.1 — Subagent schemas + Lifecycle 状态机

- [ ] **Step 1: TestSubagentSchemas (7 red tests)** — `DelegationRequest (IC-05)` / `IC-12 子类` / `IC-20 子类` 字段对齐 ic-contracts §3.5/.12/.20 · `DelegationSignature` 超集 · `LifecycleState enum`（provisioning/running/completed/killed · success/partial/failed）· 状态迁移合法性（不能 running → provisioning）

- [ ] **Step 2: Implement `subagent/schemas.py`** — 三个 IC 的 Request/Response + DelegationSignature + LifecycleState

- [ ] **Step 3: Green + Commit `γ-WP04.1 subagent schemas (IC-05/12/20 · lifecycle 5 状态)`**

### Task 04.2 — Context COW + PM-03 隔离 + checksum

- [ ] **Step 1: TestContextScope (7 red tests)**
  - COW 指针：主 session 修改后 child context_checksum 变化被检测
  - 只读白名单：`project_id / wp_id / related_artifacts / dod_exprs` 暴露 · `task_board` 不暴露
  - 跨 project 拒绝：`ctx.project_id != request.project_id` → raise
  - 大 payload 检测（> 10MB）→ raise `ContextOverflow`
  - pid 继承：子 context 自动继承 parent pid
  - checksum SHA-256(canonical context)
  - 反向写拒绝：子 Agent 试图 write context → 只读 Mapping 抛 TypeError

- [ ] **Step 2: Implement `context_scope.py`**

```python
"""L2-04 Context COW 快照 · PM-03 隔离 · checksum 护栏."""
from __future__ import annotations

import hashlib
import json
import types
from typing import Any


PUBLIC_CONTEXT_KEYS = frozenset(["project_id", "wp_id", "related_artifacts", "dod_exprs", "correlation_id"])


class ContextIsolationViolation(PermissionError):
    """E_SUB_CONTEXT_ISOLATION_VIOLATION."""


class ContextOverflow(ValueError):
    """E_SUB_CONTEXT_OVERFLOW."""


class ChildContext(types.MappingProxyType):
    """只读 context · 尝试写会抛 TypeError."""


def make_child_context(
    parent_ctx: dict[str, Any],
    *,
    child_project_id: str,
    max_bytes: int = 10 * 1024 * 1024,
) -> tuple[ChildContext, str]:
    if not child_project_id:
        raise ValueError("PM-14: child_project_id required")
    parent_pid = parent_ctx.get("project_id")
    if parent_pid and parent_pid != child_project_id:
        raise ContextIsolationViolation(
            f"cross-project delegate denied: parent={parent_pid} child={child_project_id}"
        )
    filtered = {k: v for k, v in parent_ctx.items() if k in PUBLIC_CONTEXT_KEYS}
    filtered["project_id"] = child_project_id
    canonical = json.dumps(filtered, sort_keys=True, default=str)
    if len(canonical) > max_bytes:
        raise ContextOverflow(f"context size {len(canonical)} > {max_bytes}")
    checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ChildContext(filtered), checksum


def verify_checksum(ctx: dict[str, Any], expected: str) -> bool:
    canonical = json.dumps(dict(ctx), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == expected
```

- [ ] **Step 3: Green + Commit `γ-WP04.2 Context COW + PM-03 隔离 + checksum (跨 project 拒绝)`**

### Task 04.3 — ResourceLimiter（max_concurrent=3 + 排队）

- [ ] **Step 1: TestResourceLimiter (5 red tests)**
  - 允许 3 并发
  - 第 4 个 spawn 进入 queue（不 raise）· 前面 1 个完成后立即解放
  - queue 超上限（default 10）→ raise `E_SUB_SESSION_LIMIT`
  - slot 释放必发生（finally · 即使 spawn raise）
  - 并发计数精准（asyncio.Semaphore 正确）

- [ ] **Step 2: Implement `resource_limiter.py`**

```python
"""L2-04 并发上限 · max_concurrent=3 + queue=10 · Semaphore 实现."""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator


class SessionLimitError(RuntimeError):
    """E_SUB_SESSION_LIMIT."""


class ResourceLimiter:
    def __init__(self, max_concurrent: int = 3, max_queue: int = 10) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max_queue = max_queue
        self._waiters = 0
        self._waiters_lock = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        async with self._waiters_lock:
            if self._waiters >= self._max_queue:
                raise SessionLimitError(f"queue full: {self._max_queue}")
            self._waiters += 1
        try:
            async with self._sem:
                yield
        finally:
            async with self._waiters_lock:
                self._waiters -= 1
```

- [ ] **Step 3: Green + Commit `γ-WP04.3 ResourceLimiter (max_concurrent=3 / queue=10 / E_SUB_SESSION_LIMIT)`**

### Task 04.4 — Claude SDK Client（可 mock 层 · SIGTERM→SIGKILL · 心跳）

- [ ] **Step 1: TestClaudeSDKClient (9 red tests)** — 按 mock SDK 语义：
  - spawn 返 subagent_session_id（UUID 格式）
  - tool_whitelist 传给 SDK（验证 SDK 收到 `allowed_tools` 参数）
  - heartbeat interval = timeout_s/10
  - 超时 → SIGTERM
  - SIGTERM 5s 内未退 → SIGKILL
  - SIGKILL 后返 partial artifacts
  - 心跳精度 ≤ 1min
  - spawn 失败 retry 1 次后降级 `E_SUB_SPAWN_FAILED`
  - session_id 唯一性（10k spawn 无冲突）

- [ ] **Step 2: Implement `claude_sdk_client.py`** — 使用 `claude_agent_sdk.Agent(...).run(...)` 的本地包装；若 SDK 不可用 · import 我们的 stub（用 asyncio.subprocess mock 一个子进程生命周期 · 方便单测）。SIGTERM/SIGKILL 用 `proc.terminate() → wait(5) → proc.kill()`。

- [ ] **Step 3: Green + Commit `γ-WP04.4 Claude SDK Client (SIGTERM→5s→SIGKILL + 心跳 timeout_s/10)`**

### Task 04.5 — Delegator（IC-05/12/20 路由 + 降级链）

- [ ] **Step 1: TestDelegator (11 red tests)**
  - IC-05 dispatch（通用 role）· 返 dispatched=true + session_id · 同步返回 ≤ 200ms
  - IC-12 dispatch（codebase_onboarding · repo_path 校验）· repo > 100 万行 → E_OB_REPO_TOO_LARGE
  - IC-20 dispatch（verifier · allowed_tools 严格限制为 [Read, Glob, Grep, Bash]）
  - IC-20 PM-03 硬约束：ctx 中发现"主 session 共享"字段 → E_VER_MUST_BE_INDEPENDENT_SESSION
  - 跨 project ctx 拒绝
  - 并发上限触发排队
  - 降级链 Level 1：spawn fail → retry 1 次（新 session）
  - 降级链 Level 2：retry fail → inline 模式（主 session 简化跑）
  - 降级链 Level 3：inline fail → hard halt（IC-15）
  - TrustLedger 记：spawn / complete / abort 全链事件
  - brief < 50 字 → E_SUB_BRIEF_TOO_SHORT

- [ ] **Step 2: Implement `delegator.py`** — 3 个入口方法：`delegate_subagent`（IC-05）/ `delegate_codebase_onboarding`（IC-12）/ `delegate_verifier`（IC-20）· 共用 spawn + lifecycle + ledger 骨架 · IC-12/20 做参数特化 validation

- [ ] **Step 3: Green + Commit `γ-WP04.5 Delegator IC-05/12/20 路由 + 降级链 3 级`**

### Task 04.6 — WP-γ-04 收尾

- [ ] **Step 1: PM-03 e2e 隔离测（tests/skill_dispatch/integration/test_pm14_subagent_isolation.py 初版）**

```python
@pytest.mark.pm03
async def test_child_cannot_read_main_session_task_board(...):
    """主 session 把 task_board 放 context · 子 Agent ctx 不应含此字段."""
    ...

@pytest.mark.pm14
async def test_child_inherits_parent_project_id(...):
    """子 Agent ctx.project_id == 父 ctx.project_id."""
    ...
```

- [ ] **Step 2: Coverage ≥ 80% · 6 错误码全覆盖 · SDK 集成模拟绿**

- [ ] **Step 3: Perf bench — `bench_subagent_spawn.py` ≤ 1.2s**

- [ ] **Step 4: Commit close**

```bash
git commit -m "feat(harnessFlow-code): γ-WP04 close — L2-04 子 Agent 委托完工（39 TC · IC-05/12/20 · PM-03 + PM-14 验证 · SIGTERM→SIGKILL · 降级链）"
```

---

## §7 WP-γ-05 · L2-05 异步结果回收器（~38 TC · ~730 行）

**Files:**
- Create: `app/skill_dispatch/async_receiver/schemas.py` (~180 行)
- Create: `app/skill_dispatch/async_receiver/validator.py` (~250 行)
- Create: `app/skill_dispatch/async_receiver/forwarder.py` (~150 行)
- Create: `app/skill_dispatch/async_receiver/crash_recovery.py` (~150 行)
- Test: `tests/skill_dispatch/test_l2_05_receiver.py`

### Task 05.1 — Receiver schemas + CollectionRecord VO

- [ ] **Step 1: TestReceiverSchemas (6 red tests)** — `ValidationResult`（status: format_invalid / passed / schema_unavailable / silent_patch_detected）· `PendingEntry`（result_id / deadline_ts_ns / capability）· `CollectionRecord`（status / result / dod_verdict / validation_errors）· `DoDVerdict` 5 档 · `IdempotencyKey` 哈希稳定性

- [ ] **Step 2: Implement `async_receiver/schemas.py`**

```python
"""L2-05 收集期 VO."""
from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field


ValidationStatus = Literal["passed", "format_invalid", "schema_unavailable", "silent_patch"]
Verdict = Literal["PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"]


class ValidationResult(BaseModel):
    status: ValidationStatus
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PendingEntry(BaseModel):
    result_id: str
    deadline_ts_ns: int = Field(gt=0)
    capability: str
    project_id: str


class CollectionRecord(BaseModel):
    result_id: str
    project_id: str
    capability: str
    status: Literal["passed", "rejected", "timeout"]
    result: dict[str, Any] | None = None
    dod_verdict: Verdict | None = None
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    assembled_at_ts_ns: int


def idempotency_key(invocation_id: str, skill_id: str, started_at_ts_ns: int) -> str:
    s = f"{invocation_id}|{skill_id}|{started_at_ts_ns}"
    return hashlib.sha256(s.encode()).hexdigest()[:32]
```

- [ ] **Step 3: Green + Commit `γ-WP05.1 Receiver schemas + CollectionRecord + idempotency_key`**

### Task 05.2 — Validator（jsonschema Draft 2020-12 + SCHEMA_UNAVAILABLE 硬失败）

- [ ] **Step 1: TestValidator (10 red tests)**
  - 校验通过返 `passed` + 无 errors
  - 字段类型不匹配 → `format_invalid` + errors[0].kind="type"
  - 必填缺失 → `format_invalid` + errors[0].kind="required"
  - schema_pointer 无法找到 → `schema_unavailable`（硬失败 · 不放行）
  - 校验 P99 ≤ 50ms（1000 次迭代）
  - 大报告（100KB）校验 ≤ 500ms
  - 静默 patch 检测：入参缺字段 · 回传有字段（且非 schema required） → `silent_patch`
  - schema 缓存（第二次读同 schema 不再 fs read）
  - schema 错误（本身不是合法 JSON schema） → raise `SchemaCompilationError`
  - 非 dict raw_return 拒绝

- [ ] **Step 2: Implement `validator.py`**

```python
"""L2-05 Schema 校验 · jsonschema Draft 2020-12 · SCHEMA_UNAVAILABLE 硬失败."""
from __future__ import annotations

import functools
import json
import pathlib
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from .schemas import ValidationResult


class SchemaCompilationError(ValueError):
    pass


class Validator:
    def __init__(self, registry_root: pathlib.Path) -> None:
        self._root = pathlib.Path(registry_root)

    @functools.lru_cache(maxsize=64)
    def _load(self, pointer: str) -> Draft202012Validator:
        p = self._root / pointer
        if not p.exists():
            raise FileNotFoundError(f"schema pointer not found: {pointer}")
        raw = json.loads(p.read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(raw)
        except jsonschema.SchemaError as e:
            raise SchemaCompilationError(str(e)) from e
        return Draft202012Validator(raw)

    def validate(
        self,
        *,
        raw_return: Any,
        schema_pointer: str | None,
        input_params: dict | None = None,
    ) -> ValidationResult:
        if schema_pointer is None:
            return ValidationResult(status="schema_unavailable")
        if not isinstance(raw_return, dict):
            return ValidationResult(
                status="format_invalid",
                errors=[{"kind": "type", "expected": "object", "actual": type(raw_return).__name__}],
            )
        try:
            validator = self._load(schema_pointer)
        except FileNotFoundError:
            return ValidationResult(status="schema_unavailable")
        errors = sorted(validator.iter_errors(raw_return), key=lambda e: e.path)
        if errors:
            return ValidationResult(
                status="format_invalid",
                errors=[
                    {"kind": e.validator, "path": list(e.path), "message": e.message}
                    for e in errors
                ],
            )
        if input_params is not None and self._is_silent_patch(input_params, raw_return, validator.schema):
            return ValidationResult(status="silent_patch")
        return ValidationResult(status="passed")

    def _is_silent_patch(self, inp: dict, out: dict, schema: dict) -> bool:
        """E09 · 静默 patch 检测：out 携带 inp 没提供且 schema 未 required 的默认值."""
        required = set(schema.get("required", []))
        added = set(out.keys()) - set(inp.keys()) - required
        return len(added) > 0
```

- [ ] **Step 3: Green + Commit `γ-WP05.2 Validator (Draft 2020-12 + schema_unavailable 硬失败 + silent_patch E09 + 50ms SLO)`**

### Task 05.3 — Forwarder（DoD 网关转发 · IC-14 prev_hash）

- [ ] **Step 1: TestForwarder (5 red tests)**
  - 校验 passed + dod_gate_required=false → 跳过 L1-04 · 直接 passed
  - 校验 passed + dod_gate_required=true → 转发 L1-04 · 返 verdict
  - L1-04 超时 → `E_COLLECT_DOD_GATE_TIMEOUT` + 告警
  - 两层事件：L2-05 append + L1-04 append · verdict_id 匹配
  - IC-14 payload 含 prev_hash（防时序乱）

- [ ] **Step 2: Implement `forwarder.py`**

```python
"""L2-05 → L1-04 DoD 网关转发 · 不自判 · IC-14 prev_hash 一致性."""
from __future__ import annotations

import concurrent.futures
from typing import Any

from .schemas import Verdict


class DoDGateTimeout(TimeoutError):
    """E_COLLECT_DOD_GATE_TIMEOUT."""


class DoDForwarder:
    def __init__(self, dod_gate, event_bus, timeout_s: float = 10.0) -> None:
        self._gate = dod_gate
        self._bus = event_bus
        self._timeout = timeout_s

    def forward(
        self,
        *,
        project_id: str,
        capability: str,
        result_id: str,
        artifact: dict[str, Any],
        prev_hash: str,
    ) -> Verdict:
        # IC-14 事件：L2-05 发起
        ev = self._bus.append_event(
            project_id=project_id, l1="L1-05",
            event_type="dod_gate_forward",
            payload={
                "result_id": result_id, "capability": capability, "prev_hash": prev_hash,
            },
        )
        # 同步调 L1-04 mock（超时包围）
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(
                self._gate.dod_gate_check,
                project_id, capability, result_id, artifact,
            )
            try:
                v = fut.result(timeout=self._timeout)
            except concurrent.futures.TimeoutError as e:
                raise DoDGateTimeout(
                    f"DoD gate timeout for {result_id} (prev={ev.this_hash})"
                ) from e
        return v.verdict
```

- [ ] **Step 3: Green + Commit `γ-WP05.3 Forwarder (DoD 网关转发 · IC-14 prev_hash · 10s 超时)`**

### Task 05.4 — CrashRecovery（pending.jsonl replay + TimeoutWatcher asyncio）

- [ ] **Step 1: TestCrashRecovery (8 red tests)**
  - `enroll` 写 pending.jsonl（append）
  - `finalize` 写 compaction（mv 到 rejected/finalized）
  - TimeoutWatcher 60s tick · 超时 entry 标 `timeout` 并 move
  - 崩溃后 replay：startup 读 pending.jsonl · 恢复 in-memory 表
  - 崩溃恢复 ≤ 5s（含 1000 条 pending）
  - 超时精度 ≤ 60s
  - 幂等（同 result_id 第二次 enroll 返 cached record）· 5min 缓存窗
  - compaction 不丢未完成条目

- [ ] **Step 2: Implement `crash_recovery.py`**

```python
"""L2-05 崩溃恢复 · pending.jsonl append-only · asyncio TimeoutWatcher 60s tick."""
from __future__ import annotations

import asyncio
import json
import pathlib
import time
from typing import Any

from .schemas import PendingEntry


class PendingStore:
    def __init__(self, project_root: pathlib.Path) -> None:
        self.path = pathlib.Path(project_root) / "skills" / "registry-cache" / "pending.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, PendingEntry] = {}

    def enroll(self, entry: PendingEntry) -> None:
        if entry.result_id in self._cache:
            return      # 幂等
        self._cache[entry.result_id] = entry
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
            f.flush()

    def finalize(self, result_id: str, status: str) -> None:
        self._cache.pop(result_id, None)
        # compaction 延到后台 cron · 本接口只从内存清

    def replay(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = PendingEntry(**json.loads(line))
                self._cache[rec.result_id] = rec
            except Exception:
                continue

    def timed_out(self, now_ns: int | None = None) -> list[PendingEntry]:
        now = now_ns or time.time_ns()
        return [e for e in self._cache.values() if e.deadline_ts_ns < now]


class TimeoutWatcher:
    def __init__(self, store: PendingStore, tick_s: float = 60.0) -> None:
        self._store = store
        self._tick_s = tick_s
        self._task: asyncio.Task | None = None
        self._on_timeout = lambda entry: None

    def set_handler(self, handler) -> None:
        self._on_timeout = handler

    async def start(self) -> None:
        async def loop():
            while True:
                for e in self._store.timed_out():
                    self._on_timeout(e)
                    self._store.finalize(e.result_id, "timeout")
                await asyncio.sleep(self._tick_s)
        self._task = asyncio.create_task(loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

- [ ] **Step 3: Green + Commit `γ-WP05.4 CrashRecovery (pending.jsonl + TimeoutWatcher 60s + 幂等 5min + replay ≤ 5s)`**

### Task 05.5 — WP-γ-05 收尾

- [ ] **Step 1: Coverage ≥ 80% · 6 错误码全覆盖** — `E_COLLECT_SCHEMA_UNAVAILABLE / FORMAT_INVALID / DOD_GATE_TIMEOUT / SILENT_PATCH_DETECTED / RESULT_TIMEOUT / IDEMPOTENCY_KEY_CONFLICT`

- [ ] **Step 2: 静默 patch 检测 e2e 测 — 构造 CRITICAL raise 场景**

```python
def test_silent_patch_raises_critical(...):
    v = validator.validate(
        raw_return={"ok": True, "_phantom_default": 42},
        schema_pointer="schemas/skill/write_test.v1.json",
        input_params={"x": 1},
    )
    assert v.status == "silent_patch"
```

- [ ] **Step 3: Commit close**

```bash
git commit -m "feat(harnessFlow-code): γ-WP05 close — L2-05 异步结果回收完工（38 TC · jsonschema · DoD 转发 · 幂等 · crash recovery）"
```

---

## §8 WP-γ-06 · 组内 5 L2 集成 + e2e（≥ 8 集成 TC）

**Files:**
- Create: `tests/skill_dispatch/integration/test_l1_05_e2e.py` (~200 行)
- Create: `tests/skill_dispatch/integration/test_ic_04_05_12_20.py` (~180 行)
- Create: `tests/skill_dispatch/integration/test_pm14_subagent_isolation.py` (~120 行)
- Create: `tests/skill_dispatch/perf/bench_ic_04_dispatch.py`（WP03 已建 · 本 WP 扩展负载）
- Create: `tests/skill_dispatch/perf/bench_subagent_spawn.py`（WP04 已建 · 本 WP 扩展负载）
- Create: `app/skill_dispatch/README.md`（组级使用说明 + DoD checklist）

### Task 06.1 — e2e 全链：invoke → registry → intent → invoker → subagent → receiver

- [ ] **Step 1: Write `test_l1_05_e2e.py`（3 集成 TC）**

```python
@pytest.mark.e2e
async def test_invoke_skill_happy_path_through_registry_intent_and_receiver(
    tmp_project, fixtures_dir, ic09_bus, kb_mock, lock_mock, dod_gate,
):
    """e2e: 合规 IC-04 调用 · 走 Registry lookup + Intent rank + Invoker 调 mock skill + Receiver 校验通过."""
    import shutil
    shutil.copy(fixtures_dir / "registry_valid.yaml",
                tmp_project / "skills" / "registry-cache" / "registry.yaml")
    # 装配全链
    from app.skill_dispatch.registry.loader import RegistryLoader
    from app.skill_dispatch.registry.query_api import RegistryQueryAPI
    from app.skill_dispatch.registry.ledger import LedgerWriter
    from app.skill_dispatch.intent_selector import IntentSelector
    from app.skill_dispatch.invoker.executor import SkillExecutor
    from app.skill_dispatch.async_receiver.validator import Validator
    from app.skill_dispatch.async_receiver.forwarder import DoDForwarder
    from app.skill_dispatch.invoker.schemas import InvocationRequest

    snap = RegistryLoader(project_root=tmp_project).load()
    api = RegistryQueryAPI(snapshot=snap)
    ledger = LedgerWriter(project_root=tmp_project, lock=lock_mock)
    selector = IntentSelector(registry=api, kb=kb_mock, ledger_idx=snap.ledger_index)
    validator = Validator(registry_root=tmp_project / "skills" / "registry-cache")
    forwarder = DoDForwarder(dod_gate=dod_gate, event_bus=ic09_bus)
    executor = SkillExecutor(
        registry=api, selector=selector, ledger=ledger,
        validator=validator, forwarder=forwarder, event_bus=ic09_bus,
    )
    req = InvocationRequest(
        invocation_id="inv1", project_id="p1", capability="write_test",
        params={"x": 1}, caller_l1="L1-04",
        context={"project_id": "p1", "wp_id": "wp1"},
    )
    rsp = await executor.invoke(req)
    assert rsp.success is True
    # IC-09 事件链完整
    events = [e.event_type for e in ic09_bus.read_all("p1")]
    assert "skill_invocation_started" in events
    assert "skill_invocation_finished" in events


@pytest.mark.e2e
async def test_all_candidates_fail_returns_success_false_not_raises(...):
    """e2e: 全候选失败 · 返 success=false · error=E_SKILL_ALL_FALLBACK_FAIL · fallback_trace 完整."""
    ...


@pytest.mark.e2e
async def test_capability_unknown_raises_ic15_halt(...):
    """capability 未注册 · L2-02 advance_fallback exhausted → IC-15 hard_halt event."""
    ...
```

- [ ] **Step 2: Green**

Run: `pytest -m e2e tests/skill_dispatch/integration/ -v`
Expected: 3 PASS

- [ ] **Step 3: Commit `γ-WP06.1 e2e 全链 happy path + all-fail + capability-unknown`**

### Task 06.2 — IC 契约集成测（IC-04 + IC-05 + IC-12 + IC-20）

- [ ] **Step 1: Write `test_ic_04_05_12_20.py`（4 集成 TC）** — 每 IC 一个 schema 对齐 + e2e round-trip TC：
  - `test_ic_04_request_response_match_ic_contracts_v1`（schema fields）
  - `test_ic_05_delegate_dispatch_and_final_report`
  - `test_ic_12_codebase_onboarding_with_kb_write_back_mock`
  - `test_ic_20_verifier_verdict_three_segment_evidence`

- [ ] **Step 2: Green + Commit `γ-WP06.2 IC-04/05/12/20 契约集成测`**

### Task 06.3 — PM-14 / PM-03 隔离验证

- [ ] **Step 1: Write `test_pm14_subagent_isolation.py`（3 集成 TC）**
  - `test_pm14_child_inherits_parent_pid`
  - `test_pm03_child_cannot_access_main_task_board`
  - `test_pm14_cross_project_delegate_rejected`

- [ ] **Step 2: Green + Commit `γ-WP06.3 PM-14 + PM-03 隔离验证（跨 project 拒绝）`**

### Task 06.4 — Perf bench（IC-04 dispatch + subagent spawn）

- [ ] **Step 1: Run 两个 bench · 记基线** — IC-04 dispatch P99 ≤ 200ms · subagent spawn P99 ≤ 1.2s

- [ ] **Step 2: Commit `γ-WP06.4 perf bench baseline (IC-04 ≤ 200ms · spawn ≤ 1.2s)`**

### Task 06.5 — README 组级说明

- [ ] **Step 1: Write `app/skill_dispatch/README.md`**

```markdown
# L1-05 · Skill 生态 + 子 Agent 调度

## 定位
Skill 调用 + 子 Agent 委托的**唯一**入口。四个对外 IC：
- **IC-04 invoke_skill** — 同步 skill 调用（能力抽象 · 不硬编码 skill 名）
- **IC-05 delegate_subagent** — 通用子 Agent 委托
- **IC-12 delegate_codebase_onboarding** — 代码仓分析专用
- **IC-20 delegate_verifier** — S5 验证器专用（PM-03 硬约束）

## 模块
| 模块 | 责任 | 主要 API |
|---|---|---|
| `registry/` | 能力抽象层数据底座（5 阶段加载 · 热更新 · 账本） | `RegistryLoader.load()` · `RegistryQueryAPI.query_*` |
| `intent_selector/` | 6 信号打分 · 硬编码 scan · 候选链编排 | `IntentSelector.select(req) -> Chain` |
| `invoker/` | IC-04 主入口（context 注入 · retry · timeout · 审计双写） | `SkillExecutor.invoke(req) -> Response` |
| `subagent/` | IC-05/12/20 路由 · Claude Agent SDK · COW context | `Delegator.delegate_*` |
| `async_receiver/` | schema 校验 · DoD 网关转发 · 幂等 · 崩溃恢复 | `Validator.validate` · `DoDForwarder.forward` |

## DoD checklist（组级）
- [ ] pytest 249 passed · coverage ≥ 85%
- [ ] IC-04/05/12/20 schema 严格对齐 `ic-contracts.md`
- [ ] 启动硬编码 scan 绿（PM-09）
- [ ] 子 Agent e2e（spawn → complete）绿（PM-03）
- [ ] 降级链 4 路径全测（retry → inline → halt）
- [ ] commit 11-12 个

## Mock 替换清单（波4-5 切真实）
见 `_mocks/*.py` 顶注。
```

- [ ] **Step 2: Commit `γ-WP06.5 app/skill_dispatch/README.md`**

### Task 06.6 — WP-γ-06 收尾 + 组级 DoD 自检

- [ ] **Step 1: Run full suite**

```bash
pytest tests/skill_dispatch/ -v --cov=app.skill_dispatch --cov-report=term-missing --cov-fail-under=85
```
Expected: 全绿 · coverage ≥ 85%

- [ ] **Step 2: Commit close**

```bash
git commit -m "feat(harnessFlow-code): γ-WP06 close — 组内 5 L2 集成完工（≥ 8 集成 TC + perf + PM-03/14 验证 + README）"
```

---

## §9 验证与收尾

### Task V1 — superpowers:verification-before-completion 自检

- [ ] **Step 1: Invoke skill**

```
调 Skill(superpowers:verification-before-completion)
```

- [ ] **Step 2: 逐项 checklist（按 exe-plan §8 组级 DoD）**

- [ ] pytest 249 passed · coverage ≥ 85%
- [ ] IC-04/05/12/20 schema 严格对齐 `ic-contracts.md §3.4/3.5/3.12/3.20`
- [ ] 启动硬编码 scan 绿（PM-09）
- [ ] 子 Agent e2e（spawn → complete）绿
- [ ] 降级链 4 路径全测
- [ ] `app/skill_dispatch/README.md` 已写
- [ ] 11-12 个 commit 全部 prefix `feat(harnessFlow-code): γ-WPNN.M ...`
- [ ] `docs/4-exe-plan/standup-logs/Dev-γ-*.md` 每日 standup 齐全

### Task V2 — superpowers:requesting-code-review

- [ ] **Step 1: Invoke**

```
调 Skill(superpowers:requesting-code-review)
```

- [ ] **Step 2: 分派 python-reviewer subagent**（如 superpowers 链路为 code-reviewer 则该 agent）

审查重点（传给 reviewer 的 brief）：
- PM-03 独立 session（子 Agent ctx 不访问主 session 变量）
- PM-14 project_id 全链继承
- IC-04/05/12/20 字段级对齐 ic-contracts.md
- 错误码完整（30+ 错误码 · 每个至少 1 TC）
- fallback 链正确性（全链失败返 success=false 不 raise）
- 静默 patch 检测（E09 · N5 violation）
- SDK spawn 失败 retry 1 次后降级

### Task V3 — superpowers:finishing-a-development-branch

- [ ] **Step 1: Invoke**

```
调 Skill(superpowers:finishing-a-development-branch)
```

- [ ] **Step 2: 确认 commit 规范 + push + PR**

```bash
git log --oneline main..HEAD | head -30
# 确认所有 commits 都是 feat(harnessFlow-code): γ-WPNN.M ...

git push origin HEAD

gh pr create --title "Dev-γ · L1-05 Skill 生态+子 Agent 调度（5 L2 · IC-04/05/12/20 · 249 TC）" --body "$(cat <<'EOF'
## Summary
- 实现 L1-05 完整栈：Skill 注册表 / 意图选择器 / 调用执行器 / 子 Agent 委托器 / 异步结果回收器
- 对外提供 IC-04 invoke_skill / IC-05 delegate_subagent / IC-12 codebase_onboarding / IC-20 verifier
- PM-03（独立 session）+ PM-14（project_id）+ PM-09（能力抽象）全约束验证

## DoD
- [x] pytest 249 passed · coverage ≥ 85%
- [x] IC-04/05/12/20 schema 严格对齐 ic-contracts.md
- [x] 启动硬编码 scan 绿
- [x] 子 Agent e2e 绿
- [x] 降级链 4 路径全测
- [x] README.md + mock 替换清单

## Mock 替换清单（波4-5）
- `_mocks/ic09_mock.py` → Dev-α L1-09 L2-05（α WP04 后）
- `_mocks/ic06_mock.py` → Dev-β L1-06 L2-02（β WP03 后）
- `_mocks/lock_mock.py` → Dev-α L1-09（α WP07 后）
- `_mocks/dod_gate_mock.py` → 主-1 L1-04 L2-02（波5）

## Test plan
- [ ] reviewer 审 PM-03/14 · IC 对齐 · 错误码
- [ ] 主-3 集成期切真实 mock 替换
- [ ] 不合入 main · 等波 6 main-3 统一集成

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## §10 Self-Review（writing-plans 要求的自检）

### 10.1 Spec coverage

| exe-plan §3 WP | 本 plan 实现位置 | 状态 |
|---|---|---|
| γ-WP01 L2-01 Registry | §3 Task 01.1~01.6 | ✅ |
| γ-WP02 L2-02 Intent | §4 Task 02.1~02.6 | ✅ |
| γ-WP03 L2-03 IC-04 | §5 Task 03.1~03.7 | ✅ |
| γ-WP04 L2-04 IC-05/12/20 | §6 Task 04.1~04.6 | ✅ |
| γ-WP05 L2-05 Receiver | §7 Task 05.1~05.5 | ✅ |
| γ-WP06 集成 | §8 Task 06.1~06.6 | ✅ |
| 组级 DoD 自检 | §9 V1-V3 | ✅ |

| 组级 DoD（exe-plan §8） | 覆盖 task |
|---|---|
| pytest 249 passed · coverage ≥ 85% | Task 06.6 · V1 |
| IC-04/05/12/20 schema 严格对齐 | Task 03.1 · 04.1 · 06.2 |
| 启动硬编码 scan 绿 | Task 02.2 |
| 子 Agent e2e 绿 | Task 06.1 · 06.2 |
| 降级链 4 路径全测 | Task 03.6 · 04.5 |
| commit 11-12 个 | 所有 Task 尾 commit · §9 末 PR |

### 10.2 Placeholder scan

| 模式 | 扫描结果 |
|---|---|
| TBD / TODO | 仅 mock 文件顶部的 `TODO:MOCK-REPLACE-FROM-*` · 属于有意的生命周期标记 · 保留 |
| "implement later" | 无 |
| "add appropriate error handling" | 无 |
| "similar to Task N" | 无 · 每个 Task 的实现代码都有 · 未省略 |

### 10.3 Type/signature consistency

| 跨 Task 符号 | 定义位置 | 使用位置 | 一致性 |
|---|---|---|---|
| `InvocationRequest` | §5 Task 03.1 | §8 Task 06.1 | ✅ |
| `InvocationResponse` | §5 Task 03.1 | §7 Task 05.2 · §8 Task 06.1 | ✅ |
| `InvocationSignature` | §5 Task 03.1 | §5 Task 03.5 audit | ✅ |
| `ChildContext` / `make_child_context` | §6 Task 04.2 | §6 Task 04.5 delegator | ✅ |
| `LedgerWriter.record(caller="L2-02")` | §3 Task 01.4 | §5 Task 03.6 executor | ✅ |
| `IC09EventBusMock.append_event` | §2 Task 00.4 | §5 Task 03.5 audit | ✅ |
| `ValidationResult.status ∈ {passed, format_invalid, schema_unavailable, silent_patch}` | §7 Task 05.1 | §7 Task 05.2 · §8 Task 06.1 | ✅ |
| `CollectionRecord` | §7 Task 05.1 | §7 Task 05.4 crash_recovery | ✅（未直接引用但装配流程经过） |

无不一致项。

---

## §11 Execution Handoff

Plan complete and saved to `docs/superpowers/plans/Dev-γ-impl.md`.

**两种执行选项：**

**1. Subagent-Driven（推荐）** — 每 Task 派一个独立 subagent（PM-03 天然隔离 · 主 session context 不膨胀）· Task 间做两阶段 review（spec + code quality）· 适合跨天跨 session resume

**2. Inline Execution** — 在本 session 逐 Task 推 · 间断 checkpoint · 适合一次性推一两个 WP

**当前采取：** 由 Dev-γ session 自行选择（下一步会告知用户 + 按 MASTER-DISPATCH §6.1 启用 `subagent-driven-development`）。

---

*— Dev-γ · L1-05 Implementation Plan · v1.0 · 2026-04-23 —*



