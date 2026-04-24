# Dev-ζ · L1-07 Harness 监督 · 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建 `app/supervisor/` 的 6 L2（8 维度采集器 / 4 级偏差判定器 / 硬红线拦截器 / Supervisor 事件发送器 / Soft-drift 识别器 / 死循环升级器），承担 IC-13（quality_loop_route → L1-04） + IC-14（hard_halt → L1-01）两条对外发起契约 + 通过 IC-11 消费 L1-09 事件流，~25 500 LOC + ~8 000 行 test · 333 TC · DoD 绿。

**Architecture:** 按 Dev-ζ exe-plan §1 + `architecture.md` §5（监督时序） + §11（L2 分工）· 三入口触发模型（30s tick / PostToolUse 500ms 硬锁 / on-demand）· `EightDimensionCollector` 聚合根持有 8 维度状态向量 + 退化等级 · 4 级偏差判定器（INFO/WARN/FAIL/CRITICAL） + 硬红线 5 类二分判别 + 软漂移 8 类窗口统计 + Supervisor 事件发送器（队列 + 背压 + halt 抢占） + 死循环升级器（同级连续 ≥ 3 failed 自动升级）· 每 L2 一子包 · schemas/接口单点定义。

**Tech Stack:** Python 3.11+ / pydantic v2 / pytest + pytest-asyncio + pytest-cov / pytest-benchmark（IC-14 500ms 硬约束 SLO 验证）/ 纯 Python 内存 + 文件落盘（无 DB · 无 Redis · 遵循 L0 tech-stack 零外部服务红线）。

**Binding Contracts（事实源 · 与 exe-plan 冲突时以此为准）:**
- `docs/2-prd/L1-07 Harness监督/prd.md` §8.5 硬红线 5 类 + §9 软漂移 + §10 4 级偏差
- `docs/3-1-Solution-Technical/L1-07-Harness监督/architecture.md` §5 监督时序 · §11 L2 分工 · §12 SLO
- `docs/3-1-Solution-Technical/L1-07-Harness监督/L2-01~L2-06.md` 每份 §3 接口 · §11 错误码
- `docs/3-2-Solution-TDD/L1-07-Harness监督/L2-01~L2-06-tests.md` ~333 TC
- `docs/3-1-Solution-Technical/integration/ic-contracts.md`：
  - §3.11 **IC-11** supervisor_observe（L1-07 ← L1-09 · L1-07 调 `read_event_stream` / `read_event_bus_stats`）
  - §3.13 **IC-13** quality_loop_route（L1-07 → L1-04 · rollback routing · P99 ≤ 1s）
  - §3.14 **IC-14** hard_halt（L1-07 → L1-01 · L2-04 send P99 ≤ 500ms · 端到端 P99 ≤ 5s）
  - §3.9  **IC-09** append_event（L1-07 → L1-09 · L1-07 写入 supervisor_events 子命名空间）
- `docs/3-3-Monitoring-Controlling/hard-redlines.md` 5 硬红线最终定义
- `docs/CODE-OWNERSHIP-MATRIX.md`：Dev-ζ 只写 `app/supervisor/**` + `tests/supervisor/**`，共享文件（pyproject.toml / tests/conftest.py / app/__init__.py）冻结

**Non-goals:**
- ❌ L1-04 / L1-01 真实消费者（本组只出 IC-13/14 发送端 · 消费者用 mock assert）
- ❌ L1-09 真实 event_bus（本组用 `EventBusStub` 同时 mock IC-11 读取 + IC-09 append）
- ❌ L1-02/03/04 真实数据源（用 stub 模拟 IC-L1-02/03/04 返回）
- ❌ 跨 project supervisor 实例（V2+）
- ❌ 真实 VLM / Skill 调用

---

## §A · Self-Correction Flags（交主会话仲裁）

本会话在阅读源文档时发现 exe-plan (`Dev-ζ-L1-07-supervisor.md`) 与 3-1/3-2 source doc + ic-contracts.md 有以下 3 处不一致。按 MASTER-SESSION-DISPATCH `§6.2 源文档不一致 → 冻结 · 走 md §6 自修正（不硬改代码）`，本 plan **以 source doc 为真**，并记录分歧供主会话批准：

| # | exe-plan 原文 | source doc 真实 | 处理 |
|:---:|:---|:---|:---|
| C-1 | §7 `IC-13 push_suggestion → L1-01 · fire-and-forget` | ic-contracts §3.13 `IC-13 quality_loop_route → L1-04 · P99 ≤ 1s` | **IC-13 用于 quality-loop 路由**（→ L1-04）· exe-plan 疑似把 IC-13 / IC-14 弄反 |
| C-2 | §7 `IC-14 push_rollback_route → L1-04 · 幂等` + `IC-15 request_hard_halt → L1-01 · Sync ≤ 100ms` | ic-contracts §3.14 `IC-14 hard_halt → L1-01 · L2-04 send P99 ≤ 500ms · 端到端 P99 ≤ 5s`（未发现 IC-15） | **仅 IC-14 存在**（→ L1-01 halt）· IC-15 未在契约库定义 · 退化升级走 `IC-13 quality_loop_route level=L4` |
| C-3 | §3.1 `订阅 IC-09 事件` + `register_subscriber` API | ic-contracts：L1-07 **调** IC-11 (`read_event_stream`)，**写** IC-09 (`append_event`) · 无 `register_subscriber` 订阅 API | 采用 **主动拉取模型**（L2-01 按 30s tick / PostToolUse / on-demand 调 IC-11 读流），不做 push 订阅 |
| C-4 | `CODE-OWNERSHIP-MATRIX.md` pin 的 Dev-ζ 写路径 `app/l1_07/**` | 项目规约 `feedback_harnessflow_semantic_naming` 要求新包用语义名（不用 `l1_XX` 字面 ID） | **本组落地路径 = `app/supervisor/` + `tests/supervisor/`**（原 l1_02/06/09 既有包不动）· 主会话需同步更新 ownership matrix 把 Dev-ζ 行从 `app/l1_07/**` 改为 `app/supervisor/**` |

✅ **Outbound IC map（本 plan 采用）:**
- IC-13 → L1-04 (rollback/routing · P99 ≤ 1s) · 幂等
- IC-14 → L1-01 (hard-halt · P99 ≤ 500ms for L2-04 send · 端到端 ≤ 5s)
- IC-09 → L1-09 (append to `supervisor_events.jsonl` sub-namespace)
- IC-11 ← L1-09 (read event stream + bus stats)

✅ **8 维度（以 3-1/L2-01 为准）:** phase / artifacts / wp_status / tool_calls / latency_slo / self_repair_rate / rollback_counter / event_bus（**不**是 exe-plan 列的 code_quality/progress/risk/...）

主会话处理：此 plan 推进时若出现无法 mock 的分歧，**冻结 · 提交 `projects/_correction_log.jsonl` 条目**，等待主会话修改 exe-plan 或 ic-contracts.md。

---

## §B · File Structure（~25 500 LOC）

### 代码布局

```
app/supervisor/
├── __init__.py                           # 包标识 + 版本 + PM-14 pid 注入口
├── common/                               # 跨 L2 共用
│   ├── __init__.py
│   ├── ids.py                            # ProjectId / SnapshotId / EventId ulid 包装 (~80)
│   ├── errors.py                         # L1-07 统一错误码单点定义 (~120)
│   ├── clock.py                          # MonotonicClock 注入点 (~60)
│   ├── event_bus_stub.py                 # 内存实现 IC-11 read + IC-09 append（仅测试期）(~200)
│   └── ic_stubs.py                       # L1-02/03/04 数据源 stub (~180)
│
├── dim_collector/                        # WP-ζ-01 · L2-01 ~750 LOC
│   ├── __init__.py
│   ├── schemas.py                        # EightDimensionVector + SupervisorSnapshot pydantic (~180)
│   ├── entry_points.py                   # 3 入口协议（tick / fast / on-demand）(~100)
│   ├── state_cache.py                    # LKG last-known-good cache + TTL 60s (~150)
│   ├── dim_scanner.py                    # 8 独立 scanner · parallel asyncio.gather (~200)
│   └── collector.py                      # EightDimensionCollector 聚合根 (~120)
│
├── deviation_judge/                      # WP-ζ-04 · L2-02 ~550 LOC
│   ├── __init__.py
│   ├── schemas.py                        # DeviationVerdict / ThresholdMatrix (~120)
│   ├── threshold_matrix.py               # 阈值矩阵 config + loader (~180)
│   └── evaluator.py                      # evaluate_deviation(DimState) → Verdict (~250)
│
├── red_line/                             # WP-ζ-05 · L2-03 ~860 LOC（100ms 响应）
│   ├── __init__.py
│   ├── schemas.py                        # RedLineHit / Evidence (~150)
│   ├── detector.py                       # 总调度 · 5 detector 并发判 (~250)
│   ├── irreversible_ops.py               # HRL-02 rm -rf / git push --force / DROP / deploy (~120)
│   ├── drift_critical.py                 # HRL-01 goal anchor 偏移 (~120)
│   ├── budget_overrun.py                 # HRL-03 token/time/cost >200% (~100)
│   ├── dead_loop_escalate.py             # HRL-04 委托给 L2-06 (~100)
│   └── fail_l4.py                        # HRL-05 verifier FAIL_L4 → 回 S1 (~100)
│
├── event_sender/                         # WP-ζ-02 · L2-04 ~600 LOC
│   ├── __init__.py
│   ├── schemas.py                        # IC-13/14 payload schema (~150)
│   ├── suggestion_queue.py               # bounded 1000 · drop oldest WARN (~180)
│   ├── rollback_pusher.py                # IC-13 → L1-04 · 幂等 (~150)
│   └── halt_requester.py                 # IC-14 → L1-01 · 抢占 + P99 500ms (~120)
│
├── soft_drift/                           # WP-ζ-06 · L2-05 ~760 LOC
│   ├── __init__.py
│   ├── schemas.py                        # TrapPattern / WindowStat (~150)
│   ├── window_stats.py                   # 60 tick 滑窗统计 (~180)
│   ├── trap_patterns.py                  # 8 类 trap 定义 + 检测函数 (~180)
│   └── pattern_matcher.py                # 主匹配引擎 · fire WARN (~250)
│
└── escalator/                            # WP-ζ-03 · L2-06 ~450 LOC
    ├── __init__.py
    ├── schemas.py                        # FailureCounter / EscalationVerdict (~120)
    ├── counter.py                        # per wp_id 计数 + reset on done (~150)
    └── escalation_logic.py               # 5 态机 L1→L2→L3→L4→HardRedline (~180)
```

### 测试布局（~8 000 行）

```
tests/supervisor/
├── __init__.py
├── conftest.py                          # 共用 fixtures：mock IC-11 event_bus, mock L1-04/L1-01 consumers, clock freezer
├── dim_collector/                       # WP-ζ-01 · ~57 TC
│   ├── test_tick_entry.py               # §1 TC-L107-L201-001..016
│   ├── test_fast_entry.py               # §1 TC-L107-L201-003..005（PostToolUse 500ms）
│   ├── test_on_demand_entry.py          # §1 TC-L107-L201-006..009
│   ├── test_error_codes.py              # §1.2 TC-L107-L201-101..120（18 错误码）
│   ├── test_perf_slo.py                 # §5 TC-L107-L201-501..505（benchmark）
│   ├── test_e2e.py                      # §6 TC-L107-L201-701..703
│   ├── test_integration.py              # §8 TC-L107-L201-801..802
│   └── test_edge_cases.py               # §9 TC-L107-L201-901..905
├── deviation_judge/                     # WP-ζ-04 · ~55 TC
├── red_line/                            # WP-ζ-05 · ~57 TC（含 pytest-benchmark 100ms）
├── event_sender/                        # WP-ζ-02 · ~56 TC
├── soft_drift/                          # WP-ζ-06 · ~55 TC
├── escalator/                           # WP-ζ-03 · ~54 TC
└── integration/                         # WP-ζ-07 · ≥ 12 TC（6 L2 联调）
```

---

## §C · 执行分批 · 2 会话接力

| 批 | WP | 会话 | 估时 | 本文档覆盖深度 |
|:---:|:---|:---:|:---:|:---|
| **ζ1** | WP-01 L2-01 采集 | 本会话（当前） | 1.25 天 | **full TDD steps** |
| ζ1 | WP-02 L2-04 发送 | 本/下一会话 | 1.0 天 | **scaffold + TDD pattern** |
| ζ1 | WP-03 L2-06 升级 | 本/下一会话 | 0.75 天 | **scaffold** |
| **ζ2** | WP-04 L2-02 判定 | 下一会话 | 1.0 天 | scaffold |
| ζ2 | WP-05 L2-03 红线 | 下一会话 | 1.5 天 | scaffold（含 100ms bench） |
| ζ2 | WP-06 L2-05 软漂移 | 下一会话 | 1.5 天 | scaffold |
| ζ2 | WP-07 集成 | 下一会话 | 0.5 天 | scaffold |

**本会话产出目标**：WP-ζ-01 端到端绿 · 提交 `ζ-WP01` · 测试 ≥ 50 TC · coverage ≥ 85%。其余 WP 以 scaffold 留给下一会话 `executing-plans` 接力。

---

## §D · 通用约束（每 Task 遵守）

1. **TDD 铁律（Q-04）**：red → green → refactor → commit。单个 commit 含 test + code（不允许只推 code）。
2. **PM-14 pid**：任何对外调用 / 任何事件写入，payload 必带 `project_id` 根字段。测试必须构造非 placeholder pid，用 `ProjectId.generate()`。
3. **PM-08 事实源**：本组**不直接读写** `projects/*/events/*.jsonl` 文件 · 所有写经 `EventBusStub.append_event(IC-09)`，所有读经 `EventBusStub.read_event_stream(IC-11)`（stub 内部落盘到测试临时目录）。
4. **100ms / 500ms 硬约束**：IC-14 halt_requester 的 send SLO 用 `pytest-benchmark` 断言 P99 ≤ 500ms（exe-plan 的 100ms 是端到端错觉 · 以 ic-contracts.md §3.14 为准）。本 plan 延用 **500ms hard lock** 作 WP-02 DoD 门槛。
5. **不可写其他 L1 目录**：红线代码 / 测试 imports 不得触达 `app/l1_02/` / `app/l1_04/` 等，全部经 `ic_stubs`。
6. **commit message 前缀**：`feat(l1_07): ζ-WPNN · <summary>`（复用 Dev-α 前缀模板）。
7. **standup**：WP 完后追加 `docs/4-exe-plan/standup-logs/Dev-ζ-<date>.md`。

---

## §E · WP-ζ-01 · L2-01 8-Dim Collector · 详细 TDD Tasks

### Task 1：包骨架 + pyproject & common 基础设施

**Files:**
- Create: `app/supervisor/__init__.py`
- Create: `app/supervisor/common/__init__.py`
- Create: `app/supervisor/common/ids.py`
- Create: `app/supervisor/common/errors.py`
- Create: `app/supervisor/common/clock.py`
- Create: `tests/supervisor/__init__.py`
- Create: `tests/supervisor/conftest.py`
- Create: `tests/supervisor/dim_collector/__init__.py`

- [ ] **Step 1：创建包骨架空 `__init__.py`**

```python
# app/supervisor/__init__.py
"""L1-07 Harness 监督层。6 L2：采集 / 判定 / 红线 / 发送 / 软漂移 / 升级。"""
__version__ = "0.1.0"
```

- [ ] **Step 2：写 `common/ids.py` — ProjectId / SnapshotId**

```python
# app/supervisor/common/ids.py
from __future__ import annotations
import uuid
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ProjectId:
    value: str

    @classmethod
    def generate(cls) -> "ProjectId":
        return cls(value=f"proj-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SnapshotId:
    value: str

    @classmethod
    def generate(cls) -> "SnapshotId":
        return cls(value=f"snap-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value
```

- [ ] **Step 3：写 `common/errors.py` — 18 错误码枚举**

```python
# app/supervisor/common/errors.py
from enum import Enum

class L107Error(str, Enum):
    # PM-14 / schema
    MISSING_PROJECT_ID = "E_MISSING_PROJECT_ID"
    INVALID_PROJECT_ID_FORMAT = "E_INVALID_PROJECT_ID_FORMAT"
    SCHEMA_VERSION_MISMATCH = "E_SCHEMA_VERSION_MISMATCH"
    SCHEMA_VALIDATION_FAILED = "E_SCHEMA_VALIDATION_FAILED"
    # IC timeouts / unavailable
    IC_L1_02_TIMEOUT = "E_IC_L1_02_TIMEOUT"
    IC_L1_02_UNAVAILABLE = "E_IC_L1_02_UNAVAILABLE"
    IC_L1_03_TIMEOUT = "E_IC_L1_03_TIMEOUT"
    IC_L1_04_TIMEOUT = "E_IC_L1_04_TIMEOUT"
    IC_L1_09_TIMEOUT = "E_IC_L1_09_TIMEOUT"
    IC_L1_09_UNAVAILABLE = "E_IC_L1_09_UNAVAILABLE"
    # dim state
    ALL_DIMS_MISSING = "E_ALL_DIMS_MISSING"
    LAST_KNOWN_GOOD_EXPIRED = "E_LAST_KNOWN_GOOD_EXPIRED"
    PHASE_UNKNOWN = "E_PHASE_UNKNOWN"
    # budget / quota
    HOOK_BUDGET_EXCEEDED = "E_HOOK_BUDGET_EXCEEDED"
    CONSUMER_QUOTA_EXCEEDED = "E_CONSUMER_QUOTA_EXCEEDED"
    # persistence / events
    PERSIST_FAILED = "E_PERSIST_FAILED"
    EMIT_EVENT_FAILED = "E_EMIT_EVENT_FAILED"
    READ_ONLY_VIOLATION = "E_READ_ONLY_VIOLATION"


class L107Exception(Exception):
    def __init__(self, code: L107Error, message: str = "", **ctx):
        self.code = code
        self.ctx = ctx
        super().__init__(f"[{code.value}] {message}" + (f" · {ctx}" if ctx else ""))
```

- [ ] **Step 4：写 `common/clock.py` — 可注入 monotonic clock**

```python
# app/supervisor/common/clock.py
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Protocol


class Clock(Protocol):
    def now_iso(self) -> str: ...
    def monotonic_ms(self) -> int: ...


class RealClock:
    def now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)


@dataclass
class FrozenClock:
    """For tests. Calls advance(ms) manually."""
    _now_iso: str = "2026-04-23T00:00:00Z"
    _monotonic: int = 0

    def now_iso(self) -> str:
        return self._now_iso

    def monotonic_ms(self) -> int:
        return self._monotonic

    def advance(self, ms: int) -> None:
        self._monotonic += ms
```

- [ ] **Step 5：写 `tests/supervisor/conftest.py` 根 fixtures（frozen clock + tmp event bus）**

```python
# tests/supervisor/conftest.py
from __future__ import annotations
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.ids import ProjectId


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def pid() -> ProjectId:
    return ProjectId.generate()
```

- [ ] **Step 6：`pytest tests/l1_07 --collect-only` 验证模块 importable**

Run: `cd /Users/zhongtianyi/work/code/harnessFlow && pytest tests/l1_07 --collect-only -q`  
Expected: 0 tests collected（子目录空）· 0 errors · no `ImportError`

- [ ] **Step 7：commit**

```bash
git add app/supervisor/__init__.py app/supervisor/common tests/supervisor/__init__.py tests/supervisor/conftest.py tests/supervisor/dim_collector/__init__.py
git commit -m "feat(l1_07): ζ-WP01-T01 · 包骨架 + common (ids/errors/clock) + root conftest"
```

---

### Task 2：EventBusStub + IC stubs（测试期 mock 基础设施）

**Files:**
- Create: `app/supervisor/common/event_bus_stub.py`
- Create: `app/supervisor/common/ic_stubs.py`
- Create: `tests/supervisor/test_common_stubs.py`

- [ ] **Step 1：写失败测试 — EventBusStub 行为契约**

```python
# tests/supervisor/test_common_stubs.py
import pytest
from app.supervisor.common.event_bus_stub import EventBusStub, Event
from app.supervisor.common.ids import ProjectId

pytestmark = pytest.mark.asyncio


async def test_append_and_read_single_event(pid: ProjectId) -> None:
    bus = EventBusStub()
    await bus.append_event(
        project_id=pid.value,
        type="L1-07:snapshot_captured",
        payload={"snapshot_id": "snap-1", "degradation_level": "FULL"},
    )
    events = await bus.read_event_stream(project_id=pid.value, types=["L1-07:snapshot_captured"], window_sec=60)
    assert len(events) == 1
    assert events[0].type == "L1-07:snapshot_captured"
    assert events[0].project_id == pid.value


async def test_read_event_stream_filters_by_type(pid: ProjectId) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="decision", payload={"a": 1})
    await bus.append_event(project_id=pid.value, type="tool_invoked", payload={"tool": "git"})
    filtered = await bus.read_event_stream(project_id=pid.value, types=["tool_invoked"], window_sec=60)
    assert [e.type for e in filtered] == ["tool_invoked"]


async def test_append_enforces_pid(pid: ProjectId) -> None:
    bus = EventBusStub()
    with pytest.raises(ValueError, match="project_id"):
        await bus.append_event(project_id="", type="x", payload={})


async def test_read_event_bus_stats_returns_count_and_lag(pid: ProjectId) -> None:
    bus = EventBusStub()
    for i in range(3):
        await bus.append_event(project_id=pid.value, type="tick", payload={"i": i})
    stats = await bus.read_event_bus_stats(project_id=pid.value, window_sec=30)
    assert stats["event_count_last_30s"] == 3
    assert "event_lag_ms" in stats
```

- [ ] **Step 2：Run to verify FAIL**

Run: `pytest tests/supervisor/test_common_stubs.py -v`  
Expected: `ModuleNotFoundError: No module named 'app.supervisor.common.event_bus_stub'`

- [ ] **Step 3：实现 `event_bus_stub.py`**

```python
# app/supervisor/common/event_bus_stub.py
from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    type: str
    project_id: str
    triggered_at_ms: int
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()


class EventBusStub:
    """In-memory IC-09 append + IC-11 read stub for L1-07 tests.

    Replaces the real L1-09 event bus during tests. Not for prod.
    """

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._lock = asyncio.Lock()
        self._wall_ms = 0  # monotonic logical clock

    async def append_event(
        self,
        project_id: str,
        type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...] = (),
    ) -> str:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")
        async with self._lock:
            self._wall_ms += 1
            ev = Event(
                event_id=f"ev-{uuid.uuid4().hex[:12]}",
                type=type,
                project_id=project_id,
                triggered_at_ms=self._wall_ms,
                payload=dict(payload),
                evidence_refs=tuple(evidence_refs),
            )
            self._events.append(ev)
            return ev.event_id

    async def read_event_stream(
        self,
        project_id: str,
        types: list[str] | None = None,
        window_sec: int = 60,
    ) -> list[Event]:
        async with self._lock:
            now = self._wall_ms
            cutoff = now - window_sec * 1000
            return [
                e for e in self._events
                if e.project_id == project_id
                and e.triggered_at_ms >= cutoff
                and (types is None or e.type in types)
            ]

    async def read_event_bus_stats(self, project_id: str, window_sec: int = 30) -> dict[str, Any]:
        evs = await self.read_event_stream(project_id=project_id, window_sec=window_sec)
        return {
            "event_count_last_30s": len(evs),
            "event_lag_ms": 0 if not evs else max(0, self._wall_ms - evs[-1].triggered_at_ms),
            "event_types": sorted({e.type for e in evs}),
        }
```

- [ ] **Step 4：Run to verify PASS**

Run: `pytest tests/supervisor/test_common_stubs.py -v`  
Expected: 4 PASS

- [ ] **Step 5：写 `ic_stubs.py` — L1-02/03/04 数据源 stub**

```python
# app/supervisor/common/ic_stubs.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class L102Stub:
    """IC-L1-02 read_lifecycle_state + read_stage_artifacts."""
    phase: str = "S3"
    artifacts_completeness_pct: float = 75.0
    artifacts_missing: list[str] = field(default_factory=list)
    _timeout: bool = False
    _unavailable: bool = False

    async def read_lifecycle_state(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-02 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-02 timeout")
        return {"phase": self.phase}

    async def read_stage_artifacts(self, project_id: str) -> dict[str, Any]:
        if self._unavailable:
            raise RuntimeError("IC-L1-02 unavailable")
        if self._timeout:
            raise TimeoutError("IC-L1-02 timeout")
        return {
            "completeness_pct": self.artifacts_completeness_pct,
            "missing": list(self.artifacts_missing),
        }


@dataclass
class L103Stub:
    """IC-L1-03 read_wbs_snapshot."""
    total: int = 10
    completed: int = 3
    in_progress: int = 2
    blocked: int = 0
    _timeout: bool = False

    async def read_wbs_snapshot(self, project_id: str) -> dict[str, Any]:
        if self._timeout:
            raise TimeoutError("IC-L1-03 timeout")
        return {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "blocked": self.blocked,
            "completion_pct": round(100.0 * self.completed / max(1, self.total), 2),
        }


@dataclass
class L104Stub:
    """IC-L1-04 read_quality_stats."""
    attempts: int = 5
    successes: int = 4
    failures: int = 1
    rollback_count: int = 0
    rollback_reasons: dict[str, int] = field(default_factory=dict)
    _timeout: bool = False

    async def read_self_repair_stats(self, project_id: str) -> dict[str, Any]:
        if self._timeout:
            raise TimeoutError("IC-L1-04 timeout")
        rate = 0.0 if self.attempts == 0 else round(self.successes / self.attempts, 4)
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "rate": rate,
        }

    async def read_rollback_counter(self, project_id: str) -> dict[str, Any]:
        if self._timeout:
            raise TimeoutError("IC-L1-04 timeout")
        return {"count": self.rollback_count, "by_reason": dict(self.rollback_reasons)}
```

- [ ] **Step 6：commit**

```bash
git add app/supervisor/common/event_bus_stub.py app/supervisor/common/ic_stubs.py tests/supervisor/test_common_stubs.py
git commit -m "feat(l1_07): ζ-WP01-T02 · EventBusStub + L1-02/03/04 IC stubs · TDD 4 TC 绿"
```

---

### Task 3：Schemas — EightDimensionVector + SupervisorSnapshot

**Files:**
- Create: `app/supervisor/dim_collector/__init__.py`
- Create: `app/supervisor/dim_collector/schemas.py`
- Create: `tests/supervisor/dim_collector/test_schemas.py`

- [ ] **Step 1：失败测试 — pydantic 校验契约**

```python
# tests/supervisor/dim_collector/test_schemas.py
import pytest
from app.supervisor.dim_collector.schemas import (
    EightDimensionVector, SupervisorSnapshot, TriggerSource, DegradationLevel
)


def test_vector_all_none_valid() -> None:
    v = EightDimensionVector()
    assert v.phase is None
    assert v.artifacts is None


def test_vector_accepts_full_payload() -> None:
    v = EightDimensionVector(
        phase="S3",
        artifacts={"completeness_pct": 80.0, "missing": []},
        wp_status={"total": 10, "completed": 3, "in_progress": 2, "blocked": 0, "completion_pct": 30.0},
        tool_calls={"last_tool_name": "git", "red_line_candidate": False, "last_n_calls": []},
        latency_slo={"slo_target_ms": 2000, "actual_p95_ms": 800, "actual_p99_ms": 1200, "compliance_rate": 0.97},
        self_repair_rate={"attempts": 5, "successes": 4, "failures": 1, "rate": 0.8},
        rollback_counter={"count": 0, "by_reason": {}},
        event_bus={"event_count_last_30s": 12, "event_lag_ms": 15, "event_types": ["decision"]},
    )
    assert v.phase == "S3"


def test_snapshot_requires_project_id() -> None:
    with pytest.raises(ValueError):
        SupervisorSnapshot(
            project_id="",
            snapshot_id="snap-1",
            captured_at_ms=0,
            trigger=TriggerSource.TICK,
            eight_dim_vector=EightDimensionVector(),
            degradation_level=DegradationLevel.FULL,
            degradation_reason_map={},
            evidence_refs=(),
            collection_latency_ms=0,
        )


def test_snapshot_locked_schema_version() -> None:
    s = SupervisorSnapshot(
        project_id="proj-a",
        snapshot_id="snap-1",
        captured_at_ms=1,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=0,
    )
    assert s.vector_schema_version == "v1.0"


def test_degradation_level_enum_values() -> None:
    assert {d.value for d in DegradationLevel} == {
        "FULL", "FULL_FAST", "SOME_DIM_MISSING", "LAST_KNOWN_GOOD", "STALE_WARNING"
    }


def test_trigger_source_enum_values() -> None:
    assert {t.value for t in TriggerSource} == {"TICK", "POST_TOOL_USE", "ON_DEMAND", "STATE_CHANGED"}
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_schemas.py -v`  
Expected: `ModuleNotFoundError`

- [ ] **Step 3：实现 schemas.py**

```python
# app/supervisor/dim_collector/schemas.py
from __future__ import annotations
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TriggerSource(str, Enum):
    TICK = "TICK"
    POST_TOOL_USE = "POST_TOOL_USE"
    ON_DEMAND = "ON_DEMAND"
    STATE_CHANGED = "STATE_CHANGED"


class DegradationLevel(str, Enum):
    FULL = "FULL"
    FULL_FAST = "FULL_FAST"
    SOME_DIM_MISSING = "SOME_DIM_MISSING"
    LAST_KNOWN_GOOD = "LAST_KNOWN_GOOD"
    STALE_WARNING = "STALE_WARNING"


class EightDimensionVector(BaseModel):
    """8 维度状态向量。每维独立 None-able · 采集失败 = None。"""

    model_config = {"frozen": True}

    phase: str | None = None
    artifacts: dict[str, Any] | None = None
    wp_status: dict[str, Any] | None = None
    tool_calls: dict[str, Any] | None = None
    latency_slo: dict[str, Any] | None = None
    self_repair_rate: dict[str, Any] | None = None
    rollback_counter: dict[str, Any] | None = None
    event_bus: dict[str, Any] | None = None

    @property
    def present_count(self) -> int:
        return sum(
            1 for f in (
                self.phase, self.artifacts, self.wp_status, self.tool_calls,
                self.latency_slo, self.self_repair_rate, self.rollback_counter, self.event_bus
            ) if f is not None
        )


class SupervisorSnapshot(BaseModel):
    """PM-14 pid 根字段硬约束。"""

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    snapshot_id: str
    captured_at_ms: int
    trigger: TriggerSource
    eight_dim_vector: EightDimensionVector
    degradation_level: DegradationLevel
    degradation_reason_map: dict[str, str]
    evidence_refs: tuple[str, ...]
    collection_latency_ms: int
    vector_schema_version: str = "v1.0"
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_non_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("project_id is required (PM-14)")
        return v
```

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_schemas.py -v`  
Expected: 6 PASS

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/__init__.py app/supervisor/dim_collector/schemas.py tests/supervisor/dim_collector/test_schemas.py
git commit -m "feat(l1_07): ζ-WP01-T03 · SupervisorSnapshot + EightDimensionVector pydantic · 6 TC 绿"
```

---

### Task 4：DimScanner — 8 维并行采集（per-dim isolation）

**Files:**
- Create: `app/supervisor/dim_collector/dim_scanner.py`
- Create: `tests/supervisor/dim_collector/test_dim_scanner.py`

- [ ] **Step 1：失败测试 — 8 个 scanner 行为（各 1-2 TC，部分失败降级场景）**

```python
# tests/supervisor/dim_collector/test_dim_scanner.py
import pytest
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.common.errors import L107Error

pytestmark = pytest.mark.asyncio


async def _build_scanner(
    l102: L102Stub | None = None,
    l103: L103Stub | None = None,
    l104: L104Stub | None = None,
    bus: EventBusStub | None = None,
) -> DimScanner:
    return DimScanner(
        l102=l102 or L102Stub(),
        l103=l103 or L103Stub(),
        l104=l104 or L104Stub(),
        event_bus=bus or EventBusStub(),
    )


async def test_scan_phase_from_l1_02(pid) -> None:
    s = await _build_scanner(l102=L102Stub(phase="S4"))
    v, err = await s.scan_phase(pid.value)
    assert v == "S4" and err is None


async def test_scan_phase_timeout_returns_none_and_error(pid) -> None:
    s = await _build_scanner(l102=L102Stub(_timeout=True))
    v, err = await s.scan_phase(pid.value)
    assert v is None and err == L107Error.IC_L1_02_TIMEOUT


async def test_scan_phase_unavailable_error(pid) -> None:
    s = await _build_scanner(l102=L102Stub(_unavailable=True))
    v, err = await s.scan_phase(pid.value)
    assert v is None and err == L107Error.IC_L1_02_UNAVAILABLE


async def test_scan_artifacts(pid) -> None:
    s = await _build_scanner(l102=L102Stub(artifacts_completeness_pct=95.5))
    v, err = await s.scan_artifacts(pid.value)
    assert err is None and v["completeness_pct"] == 95.5


async def test_scan_wp_status(pid) -> None:
    s = await _build_scanner(l103=L103Stub(total=20, completed=5))
    v, err = await s.scan_wp_status(pid.value)
    assert err is None and v["completion_pct"] == 25.0


async def test_scan_self_repair_rate(pid) -> None:
    s = await _build_scanner(l104=L104Stub(attempts=10, successes=7))
    v, err = await s.scan_self_repair_rate(pid.value)
    assert err is None and v["rate"] == 0.7


async def test_scan_rollback_counter(pid) -> None:
    s = await _build_scanner(l104=L104Stub(rollback_count=3, rollback_reasons={"L2_verdict": 3}))
    v, err = await s.scan_rollback_counter(pid.value)
    assert err is None and v["count"] == 3


async def test_scan_event_bus_stats(pid) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="decision", payload={"x": 1})
    s = await _build_scanner(bus=bus)
    v, err = await s.scan_event_bus(pid.value)
    assert err is None and v["event_count_last_30s"] == 1


async def test_scan_tool_calls_from_event_bus(pid) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="tool_invoked", payload={"tool_name": "git", "args_hash": "abc"})
    s = await _build_scanner(bus=bus)
    v, err = await s.scan_tool_calls(pid.value)
    assert err is None
    assert v["last_tool_name"] == "git"


async def test_scan_latency_slo_from_event_bus(pid) -> None:
    bus = EventBusStub()
    for i in range(5):
        await bus.append_event(project_id=pid.value, type="latency_sample", payload={"dur_ms": 100 + i * 50})
    s = await _build_scanner(bus=bus)
    v, err = await s.scan_latency_slo(pid.value)
    assert err is None
    assert v["actual_p95_ms"] is not None


async def test_scan_all_parallel_returns_dict(pid) -> None:
    s = await _build_scanner()
    out = await s.scan_all(pid.value)
    assert set(out.keys()) == {
        "phase", "artifacts", "wp_status", "tool_calls", "latency_slo",
        "self_repair_rate", "rollback_counter", "event_bus",
    }
    for (value, err) in out.values():
        assert err is None or err in set(L107Error)
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_dim_scanner.py -v`

- [ ] **Step 3：实现 `dim_scanner.py`**

```python
# app/supervisor/dim_collector/dim_scanner.py
from __future__ import annotations
import asyncio
import statistics
from dataclasses import dataclass
from typing import Any

from app.supervisor.common.errors import L107Error
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub

DimResult = tuple[Any | None, L107Error | None]


@dataclass
class DimScanner:
    l102: L102Stub
    l103: L103Stub
    l104: L104Stub
    event_bus: EventBusStub

    async def scan_phase(self, pid: str) -> DimResult:
        try:
            out = await self.l102.read_lifecycle_state(pid)
        except TimeoutError:
            return None, L107Error.IC_L1_02_TIMEOUT
        except Exception:
            return None, L107Error.IC_L1_02_UNAVAILABLE
        return out.get("phase"), None

    async def scan_artifacts(self, pid: str) -> DimResult:
        try:
            out = await self.l102.read_stage_artifacts(pid)
        except TimeoutError:
            return None, L107Error.IC_L1_02_TIMEOUT
        except Exception:
            return None, L107Error.IC_L1_02_UNAVAILABLE
        return out, None

    async def scan_wp_status(self, pid: str) -> DimResult:
        try:
            out = await self.l103.read_wbs_snapshot(pid)
        except TimeoutError:
            return None, L107Error.IC_L1_03_TIMEOUT
        return out, None

    async def scan_self_repair_rate(self, pid: str) -> DimResult:
        try:
            out = await self.l104.read_self_repair_stats(pid)
        except TimeoutError:
            return None, L107Error.IC_L1_04_TIMEOUT
        return out, None

    async def scan_rollback_counter(self, pid: str) -> DimResult:
        try:
            out = await self.l104.read_rollback_counter(pid)
        except TimeoutError:
            return None, L107Error.IC_L1_04_TIMEOUT
        return out, None

    async def scan_event_bus(self, pid: str) -> DimResult:
        try:
            stats = await self.event_bus.read_event_bus_stats(pid, window_sec=30)
        except Exception:
            return None, L107Error.IC_L1_09_UNAVAILABLE
        return stats, None

    async def scan_tool_calls(self, pid: str) -> DimResult:
        try:
            evs = await self.event_bus.read_event_stream(pid, types=["tool_invoked"], window_sec=60)
        except Exception:
            return None, L107Error.IC_L1_09_UNAVAILABLE
        if not evs:
            return {"last_tool_name": None, "red_line_candidate": False, "last_n_calls": []}, None
        last = evs[-1]
        candidate = any(
            e.payload.get("tool_name", "") in {"git", "rm", "deploy"} for e in evs[-10:]
        )
        return {
            "last_tool_name": last.payload.get("tool_name"),
            "red_line_candidate": candidate,
            "last_n_calls": [{"tool": e.payload.get("tool_name"), "ts_ms": e.triggered_at_ms} for e in evs[-10:]],
        }, None

    async def scan_latency_slo(self, pid: str) -> DimResult:
        try:
            evs = await self.event_bus.read_event_stream(pid, types=["latency_sample"], window_sec=60)
        except Exception:
            return None, L107Error.IC_L1_09_UNAVAILABLE
        if not evs:
            return {"slo_target_ms": 2000, "actual_p95_ms": None, "actual_p99_ms": None, "compliance_rate": None}, None
        samples = sorted(e.payload.get("dur_ms", 0) for e in evs)
        p95 = samples[min(len(samples) - 1, int(0.95 * len(samples)))]
        p99 = samples[min(len(samples) - 1, int(0.99 * len(samples)))]
        compliance = sum(1 for s in samples if s <= 2000) / len(samples)
        return {"slo_target_ms": 2000, "actual_p95_ms": p95, "actual_p99_ms": p99, "compliance_rate": round(compliance, 4)}, None

    async def scan_all(self, pid: str) -> dict[str, DimResult]:
        keys = (
            "phase", "artifacts", "wp_status", "tool_calls",
            "latency_slo", "self_repair_rate", "rollback_counter", "event_bus",
        )
        coros = [
            self.scan_phase(pid), self.scan_artifacts(pid), self.scan_wp_status(pid), self.scan_tool_calls(pid),
            self.scan_latency_slo(pid), self.scan_self_repair_rate(pid), self.scan_rollback_counter(pid), self.scan_event_bus(pid),
        ]
        results = await asyncio.gather(*coros, return_exceptions=False)
        return dict(zip(keys, results))
```

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_dim_scanner.py -v`  
Expected: 11 PASS

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/dim_scanner.py tests/supervisor/dim_collector/test_dim_scanner.py
git commit -m "feat(l1_07): ζ-WP01-T04 · DimScanner 8 维并行采集 + per-dim 错误隔离 · 11 TC 绿"
```

---

### Task 5：StateCache — LKG + TTL 60s

**Files:**
- Create: `app/supervisor/dim_collector/state_cache.py`
- Create: `tests/supervisor/dim_collector/test_state_cache.py`

- [ ] **Step 1：失败测试**

```python
# tests/supervisor/dim_collector/test_state_cache.py
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.dim_collector.schemas import EightDimensionVector, SupervisorSnapshot, TriggerSource, DegradationLevel
from app.supervisor.dim_collector.state_cache import StateCache


def _mk_snap(pid: str, t_ms: int) -> SupervisorSnapshot:
    return SupervisorSnapshot(
        project_id=pid,
        snapshot_id=f"snap-{t_ms}",
        captured_at_ms=t_ms,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(phase="S3"),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=10,
    )


def test_empty_cache_returns_none(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    assert cache.get_latest(pid.value) is None


def test_put_and_get_returns_latest(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    cache.put(_mk_snap(pid.value, frozen_clock.monotonic_ms()))
    latest = cache.get_latest(pid.value)
    assert latest is not None and latest.snapshot_id.startswith("snap-100")


def test_ttl_expiry_returns_stale_flag(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    cache.put(_mk_snap(pid.value, frozen_clock.monotonic_ms()))
    frozen_clock.advance(61_000)
    latest = cache.get_latest(pid.value)
    is_stale = cache.is_stale(pid.value)
    assert latest is not None and is_stale is True


def test_replace_keeps_only_latest(frozen_clock: FrozenClock, pid) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    frozen_clock.advance(100)
    cache.put(_mk_snap(pid.value, 100))
    frozen_clock.advance(100)
    cache.put(_mk_snap(pid.value, 200))
    latest = cache.get_latest(pid.value)
    assert latest.snapshot_id == "snap-200"


def test_isolates_per_project(frozen_clock: FrozenClock) -> None:
    cache = StateCache(clock=frozen_clock, ttl_ms=60_000)
    cache.put(_mk_snap("proj-a", 1))
    cache.put(_mk_snap("proj-b", 2))
    assert cache.get_latest("proj-a").snapshot_id == "snap-1"
    assert cache.get_latest("proj-b").snapshot_id == "snap-2"
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_state_cache.py -v`

- [ ] **Step 3：实现 `state_cache.py`**

```python
# app/supervisor/dim_collector/state_cache.py
from __future__ import annotations
from dataclasses import dataclass, field

from app.supervisor.common.clock import Clock
from app.supervisor.dim_collector.schemas import SupervisorSnapshot


@dataclass
class StateCache:
    """Last-Known-Good cache. per-project single-slot, TTL-aware."""

    clock: Clock
    ttl_ms: int = 60_000
    _store: dict[str, SupervisorSnapshot] = field(default_factory=dict)

    def get_latest(self, project_id: str) -> SupervisorSnapshot | None:
        return self._store.get(project_id)

    def put(self, snap: SupervisorSnapshot) -> None:
        self._store[snap.project_id] = snap

    def is_stale(self, project_id: str) -> bool:
        snap = self._store.get(project_id)
        if snap is None:
            return False
        now = self.clock.monotonic_ms()
        return (now - snap.captured_at_ms) > self.ttl_ms
```

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_state_cache.py -v`  
Expected: 5 PASS

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/state_cache.py tests/supervisor/dim_collector/test_state_cache.py
git commit -m "feat(l1_07): ζ-WP01-T05 · StateCache LKG + TTL 60s · 5 TC 绿"
```

---

### Task 6：EightDimensionCollector — tick_collect 入口

**Files:**
- Create: `app/supervisor/dim_collector/collector.py`
- Create: `tests/supervisor/dim_collector/test_tick_entry.py`

- [ ] **Step 1：失败测试 — tick full + IC-09 emit + pid 校验**

```python
# tests/supervisor/dim_collector/test_tick_entry.py
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import DegradationLevel, TriggerSource
from app.supervisor.dim_collector.state_cache import StateCache

pytestmark = pytest.mark.asyncio


async def _build_collector(
    bus: EventBusStub | None = None,
    clock: FrozenClock | None = None,
    l102: L102Stub | None = None,
) -> EightDimensionCollector:
    bus = bus or EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(l102=l102 or L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus)
    cache = StateCache(clock=clock, ttl_ms=60_000)
    return EightDimensionCollector(scanner=scanner, cache=cache, event_bus=bus, clock=clock)


async def test_tick_collect_returns_snapshot_with_all_8_dims(pid) -> None:
    c = await _build_collector()
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.project_id == pid.value
    assert snap.trigger == TriggerSource.TICK
    assert snap.eight_dim_vector.phase == "S3"
    assert snap.degradation_level == DegradationLevel.FULL
    assert snap.collection_latency_ms >= 0


async def test_tick_collect_emits_snapshot_captured_event(pid) -> None:
    bus = EventBusStub()
    c = await _build_collector(bus=bus)
    snap = await c.tick_collect(project_id=pid.value)
    events = await bus.read_event_stream(project_id=pid.value, types=["L1-07:snapshot_captured"], window_sec=60)
    assert len(events) == 1
    assert events[0].payload["snapshot_id"] == snap.snapshot_id
    assert events[0].payload["degradation_level"] == "FULL"


async def test_tick_collect_rejects_empty_pid() -> None:
    c = await _build_collector()
    with pytest.raises(ValueError, match="project_id"):
        await c.tick_collect(project_id="")


async def test_tick_collect_degrades_to_some_dim_missing(pid) -> None:
    c = await _build_collector(l102=L102Stub(_timeout=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_level == DegradationLevel.SOME_DIM_MISSING
    assert snap.eight_dim_vector.phase is None
    assert "phase" in snap.degradation_reason_map


async def test_tick_collect_persists_to_cache(pid) -> None:
    c = await _build_collector()
    snap = await c.tick_collect(project_id=pid.value)
    latest = c.cache.get_latest(pid.value)
    assert latest is not None and latest.snapshot_id == snap.snapshot_id
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_tick_entry.py -v`

- [ ] **Step 3：实现 `collector.py` — tick_collect**

```python
# app/supervisor/dim_collector/collector.py
from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Any

from app.supervisor.common.clock import Clock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import (
    DegradationLevel, EightDimensionVector, SupervisorSnapshot, TriggerSource,
)
from app.supervisor.dim_collector.state_cache import StateCache


@dataclass
class EightDimensionCollector:
    scanner: DimScanner
    cache: StateCache
    event_bus: EventBusStub
    clock: Clock

    async def tick_collect(self, project_id: str) -> SupervisorSnapshot:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")
        start_ms = self.clock.monotonic_ms()
        results = await self.scanner.scan_all(project_id)

        vector_kwargs: dict[str, Any] = {}
        reason_map: dict[str, str] = {}
        for dim, (value, err) in results.items():
            vector_kwargs[dim] = value
            if err is not None:
                reason_map[dim] = err.value

        vector = EightDimensionVector(**vector_kwargs)
        present = vector.present_count
        if present == 8:
            deg = DegradationLevel.FULL
        elif present == 0:
            deg = DegradationLevel.STALE_WARNING
        else:
            deg = DegradationLevel.SOME_DIM_MISSING

        end_ms = self.clock.monotonic_ms()
        snap = SupervisorSnapshot(
            project_id=project_id,
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            captured_at_ms=end_ms,
            trigger=TriggerSource.TICK,
            eight_dim_vector=vector,
            degradation_level=deg,
            degradation_reason_map=reason_map,
            evidence_refs=(),
            collection_latency_ms=end_ms - start_ms,
        )
        self.cache.put(snap)
        await self.event_bus.append_event(
            project_id=project_id,
            type="L1-07:snapshot_captured",
            payload={
                "snapshot_id": snap.snapshot_id,
                "degradation_level": snap.degradation_level.value,
                "trigger": snap.trigger.value,
                "collection_latency_ms": snap.collection_latency_ms,
                "vector_schema_version": snap.vector_schema_version,
            },
        )
        return snap
```

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_tick_entry.py -v`  
Expected: 5 PASS

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/collector.py tests/supervisor/dim_collector/test_tick_entry.py
git commit -m "feat(l1_07): ζ-WP01-T06 · EightDimensionCollector.tick_collect + IC-09 emit · 5 TC 绿"
```

---

### Task 7：FastCollect（PostToolUse 500ms 硬锁）

**Files:**
- Modify: `app/supervisor/dim_collector/collector.py`（add `post_tool_use_fast_collect`）
- Create: `tests/supervisor/dim_collector/test_fast_entry.py`

- [ ] **Step 1：失败测试**

```python
# tests/supervisor/dim_collector/test_fast_entry.py
import asyncio
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import DegradationLevel, TriggerSource
from app.supervisor.dim_collector.state_cache import StateCache

pytestmark = pytest.mark.asyncio


async def _build(bus=None, clock=None):
    bus = bus or EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(l102=L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus)
    cache = StateCache(clock=clock, ttl_ms=60_000)
    return EightDimensionCollector(scanner=scanner, cache=cache, event_bus=bus, clock=clock)


async def test_fast_collect_returns_snapshot_with_trigger(pid) -> None:
    c = await _build()
    snap = await c.post_tool_use_fast_collect(
        project_id=pid.value, tool_name="git", tool_args_hash="abc123",
        tool_invoked_at_iso="2026-04-23T00:00:01Z", hook_deadline_ms=500,
    )
    assert snap.trigger == TriggerSource.POST_TOOL_USE


async def test_fast_collect_only_refreshes_dim_4_and_5(pid) -> None:
    clock = FrozenClock()
    c = await _build(clock=clock)
    # seed tick snapshot with phase=S3
    await c.tick_collect(project_id=pid.value)
    clock.advance(100)
    fast_snap = await c.post_tool_use_fast_collect(
        project_id=pid.value, tool_name="git", tool_args_hash="abc",
        tool_invoked_at_iso="2026-04-23T00:00:01Z", hook_deadline_ms=500,
    )
    # tool_calls and latency_slo should be freshly scanned (non-None)
    assert fast_snap.eight_dim_vector.tool_calls is not None
    # other 6 dims reused from cache
    assert fast_snap.eight_dim_vector.phase == "S3"


async def test_fast_collect_within_500ms_budget(pid) -> None:
    c = await _build()
    snap = await c.post_tool_use_fast_collect(
        project_id=pid.value, tool_name="git", tool_args_hash="a",
        tool_invoked_at_iso="2026-04-23T00:00:01Z", hook_deadline_ms=500,
    )
    assert snap.collection_latency_ms <= 500


async def test_fast_collect_no_cache_degrades_to_full_fast(pid) -> None:
    c = await _build()
    snap = await c.post_tool_use_fast_collect(
        project_id=pid.value, tool_name="git", tool_args_hash="a",
        tool_invoked_at_iso="2026-04-23T00:00:01Z", hook_deadline_ms=500,
    )
    assert snap.degradation_level in {DegradationLevel.FULL_FAST, DegradationLevel.SOME_DIM_MISSING}
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_fast_entry.py -v`

- [ ] **Step 3：扩展 `collector.py`**

Append to `collector.py`:

```python
    async def post_tool_use_fast_collect(
        self,
        project_id: str,
        tool_name: str,
        tool_args_hash: str,
        tool_invoked_at_iso: str,
        hook_deadline_ms: int = 500,
    ) -> SupervisorSnapshot:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")
        start_ms = self.clock.monotonic_ms()
        cached = self.cache.get_latest(project_id)

        # Refresh only dim_4 (tool_calls) + dim_5 (latency_slo)
        tc_res, lt_res = await asyncio.gather(
            self.scanner.scan_tool_calls(project_id),
            self.scanner.scan_latency_slo(project_id),
        )
        reason_map: dict[str, str] = {}
        tc_val, tc_err = tc_res
        lt_val, lt_err = lt_res
        if tc_err is not None:
            reason_map["tool_calls"] = tc_err.value
        if lt_err is not None:
            reason_map["latency_slo"] = lt_err.value

        if cached is not None:
            v = cached.eight_dim_vector.model_copy(update={"tool_calls": tc_val, "latency_slo": lt_val})
            deg = DegradationLevel.FULL_FAST if v.present_count >= 6 else DegradationLevel.SOME_DIM_MISSING
        else:
            v = EightDimensionVector(tool_calls=tc_val, latency_slo=lt_val)
            deg = DegradationLevel.SOME_DIM_MISSING
            reason_map.setdefault("phase", "NO_CACHE_AVAILABLE")

        end_ms = self.clock.monotonic_ms()
        snap = SupervisorSnapshot(
            project_id=project_id,
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            captured_at_ms=end_ms,
            trigger=TriggerSource.POST_TOOL_USE,
            eight_dim_vector=v,
            degradation_level=deg,
            degradation_reason_map=reason_map,
            evidence_refs=(),
            collection_latency_ms=end_ms - start_ms,
            metrics={"hook_deadline_ms": hook_deadline_ms, "tool_name": tool_name, "tool_args_hash": tool_args_hash},
        )
        self.cache.put(snap)
        await self.event_bus.append_event(
            project_id=project_id,
            type="L1-07:snapshot_captured",
            payload={
                "snapshot_id": snap.snapshot_id,
                "degradation_level": snap.degradation_level.value,
                "trigger": snap.trigger.value,
                "collection_latency_ms": snap.collection_latency_ms,
            },
        )
        return snap
```

Also add `import asyncio` at top.

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_fast_entry.py -v`

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/collector.py tests/supervisor/dim_collector/test_fast_entry.py
git commit -m "feat(l1_07): ζ-WP01-T07 · post_tool_use_fast_collect · 6 dim reuse + 500ms budget · 4 TC 绿"
```

---

### Task 8：OnDemand entry (cache hit / dim_mask)

**Files:**
- Modify: `app/supervisor/dim_collector/collector.py`
- Create: `tests/supervisor/dim_collector/test_on_demand_entry.py`

- [ ] **Step 1：测试**

```python
# tests/supervisor/dim_collector/test_on_demand_entry.py
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import TriggerSource, DegradationLevel
from app.supervisor.dim_collector.state_cache import StateCache

pytestmark = pytest.mark.asyncio


async def _build(clock=None, bus=None):
    bus = bus or EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(l102=L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus)
    return EightDimensionCollector(scanner=scanner, cache=StateCache(clock=clock, ttl_ms=60_000), event_bus=bus, clock=clock)


async def test_on_demand_cache_hit_returns_cached(pid) -> None:
    clock = FrozenClock()
    c = await _build(clock=clock)
    orig = await c.tick_collect(project_id=pid.value)
    clock.advance(1_000)  # well below max_staleness
    snap = await c.on_demand_collect(project_id=pid.value, consumer_id="l1-10-ui-1", max_staleness_sec=60)
    assert snap.snapshot_id == orig.snapshot_id
    assert snap.trigger == TriggerSource.ON_DEMAND or snap.trigger == TriggerSource.TICK


async def test_on_demand_cache_miss_forces_tick(pid) -> None:
    clock = FrozenClock()
    c = await _build(clock=clock)
    snap = await c.on_demand_collect(project_id=pid.value, consumer_id="cli-1", max_staleness_sec=0)
    assert snap.eight_dim_vector.phase == "S3"


async def test_on_demand_dim_mask_partial(pid) -> None:
    c = await _build()
    snap = await c.on_demand_collect(
        project_id=pid.value, consumer_id="cli-2", max_staleness_sec=0,
        dim_mask={"phase": True, "wp_status": True, "artifacts": False, "tool_calls": False,
                  "latency_slo": False, "self_repair_rate": False, "rollback_counter": False, "event_bus": False},
    )
    assert snap.eight_dim_vector.phase == "S3"
    assert snap.eight_dim_vector.wp_status is not None
    assert snap.eight_dim_vector.artifacts is None
    assert snap.eight_dim_vector.tool_calls is None


async def test_on_demand_stale_cache_refreshes(pid) -> None:
    clock = FrozenClock()
    c = await _build(clock=clock)
    await c.tick_collect(project_id=pid.value)
    clock.advance(61_000)
    snap = await c.on_demand_collect(project_id=pid.value, consumer_id="cli-3", max_staleness_sec=60)
    # cache expired → forced fresh
    assert snap.collection_latency_ms >= 0
```

- [ ] **Step 2：Run FAIL**

Run: `pytest tests/supervisor/dim_collector/test_on_demand_entry.py -v`

- [ ] **Step 3：扩展 `collector.py`**

Append:

```python
    async def on_demand_collect(
        self,
        project_id: str,
        consumer_id: str,
        max_staleness_sec: int = 60,
        dim_mask: dict[str, bool] | None = None,
    ) -> SupervisorSnapshot:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")
        now = self.clock.monotonic_ms()
        cached = self.cache.get_latest(project_id)
        if (
            max_staleness_sec > 0
            and dim_mask is None
            and cached is not None
            and (now - cached.captured_at_ms) <= max_staleness_sec * 1000
        ):
            return cached.model_copy(update={"trigger": TriggerSource.ON_DEMAND, "metrics": {**cached.metrics, "cache_hit": True, "consumer_id": consumer_id}})

        # cache miss / mask request → do targeted scan
        keys = (
            "phase", "artifacts", "wp_status", "tool_calls",
            "latency_slo", "self_repair_rate", "rollback_counter", "event_bus",
        )
        if dim_mask is None:
            results = await self.scanner.scan_all(project_id)
        else:
            selected: dict[str, Any] = {}
            coros = []
            active_keys = []
            for k in keys:
                if dim_mask.get(k, False):
                    active_keys.append(k)
                    coros.append(getattr(self.scanner, f"scan_{k}")(project_id))
            partial = dict(zip(active_keys, await asyncio.gather(*coros))) if coros else {}
            results = {k: (partial.get(k, (None, None))) for k in keys}

        vector_kwargs = {}
        reason_map = {}
        for dim, (value, err) in results.items():
            vector_kwargs[dim] = value
            if err is not None:
                reason_map[dim] = err.value
        vector = EightDimensionVector(**vector_kwargs)
        present = vector.present_count
        deg = DegradationLevel.FULL if present == 8 else (
            DegradationLevel.STALE_WARNING if present == 0 else DegradationLevel.SOME_DIM_MISSING
        )
        end_ms = self.clock.monotonic_ms()
        snap = SupervisorSnapshot(
            project_id=project_id,
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            captured_at_ms=end_ms,
            trigger=TriggerSource.ON_DEMAND,
            eight_dim_vector=vector,
            degradation_level=deg,
            degradation_reason_map=reason_map,
            evidence_refs=(),
            collection_latency_ms=end_ms - now,
            metrics={"consumer_id": consumer_id, "dim_mask": dim_mask or {}},
        )
        # on-demand does not pollute cache unless full scan
        if dim_mask is None:
            self.cache.put(snap)
        await self.event_bus.append_event(
            project_id=project_id,
            type="L1-07:snapshot_captured",
            payload={
                "snapshot_id": snap.snapshot_id,
                "degradation_level": snap.degradation_level.value,
                "trigger": snap.trigger.value,
                "collection_latency_ms": snap.collection_latency_ms,
                "consumer_id": consumer_id,
            },
        )
        return snap
```

- [ ] **Step 4：Run PASS**

Run: `pytest tests/supervisor/dim_collector/test_on_demand_entry.py -v`  
Expected: 4 PASS

- [ ] **Step 5：commit**

```bash
git add app/supervisor/dim_collector/collector.py tests/supervisor/dim_collector/test_on_demand_entry.py
git commit -m "feat(l1_07): ζ-WP01-T08 · on_demand_collect · cache hit / dim_mask / force miss · 4 TC 绿"
```

---

### Task 9：Error Codes tests (18 codes · §1.2 TC-101..120)

**Files:**
- Create: `tests/supervisor/dim_collector/test_error_codes.py`

- [ ] **Step 1-3：对每错误码写 1 TC（验 reason_map + degrade level）**

Core cases to cover (keep succinct — 18 TC):

```python
# tests/supervisor/dim_collector/test_error_codes.py
import pytest
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.errors import L107Error
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import DegradationLevel
from app.supervisor.dim_collector.state_cache import StateCache

pytestmark = pytest.mark.asyncio


async def _build(l102=None, l103=None, l104=None):
    bus = EventBusStub()
    clock = FrozenClock()
    scanner = DimScanner(l102=l102 or L102Stub(), l103=l103 or L103Stub(), l104=l104 or L104Stub(), event_bus=bus)
    return EightDimensionCollector(scanner=scanner, cache=StateCache(clock=clock, ttl_ms=60_000), event_bus=bus, clock=clock)


# TC-L107-L201-101
async def test_missing_pid_raises() -> None:
    c = await _build()
    with pytest.raises(ValueError):
        await c.tick_collect(project_id="")


# TC-L107-L201-104 IC_L1_02_TIMEOUT
async def test_l102_timeout_records_error_map(pid) -> None:
    c = await _build(l102=L102Stub(_timeout=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_reason_map.get("phase") == L107Error.IC_L1_02_TIMEOUT.value


# TC-L107-L201-105 IC_L1_02_UNAVAILABLE
async def test_l102_unavailable_records(pid) -> None:
    c = await _build(l102=L102Stub(_unavailable=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_reason_map.get("phase") == L107Error.IC_L1_02_UNAVAILABLE.value


# TC-L107-L201-106 IC_L1_03_TIMEOUT
async def test_l103_timeout_records(pid) -> None:
    c = await _build(l103=L103Stub(_timeout=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_reason_map.get("wp_status") == L107Error.IC_L1_03_TIMEOUT.value


# TC-L107-L201-107 IC_L1_04_TIMEOUT
async def test_l104_timeout_records(pid) -> None:
    c = await _build(l104=L104Stub(_timeout=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_reason_map.get("self_repair_rate") == L107Error.IC_L1_04_TIMEOUT.value
    assert snap.degradation_reason_map.get("rollback_counter") == L107Error.IC_L1_04_TIMEOUT.value


# TC-L107-L201-110 ALL_DIMS_MISSING → STALE_WARNING
async def test_all_dims_missing_sets_stale_warning(pid) -> None:
    c = await _build(
        l102=L102Stub(_unavailable=True),
        l103=L103Stub(_timeout=True),
        l104=L104Stub(_timeout=True),
    )
    # Also make event_bus fail by mocking
    c.scanner.event_bus = None  # force exception in read_*
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_level == DegradationLevel.STALE_WARNING


# TC-L107-L201-118 PHASE_UNKNOWN (S99) — phase pass-through
async def test_phase_unknown_passes_through(pid) -> None:
    c = await _build(l102=L102Stub(phase="S99"))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.eight_dim_vector.phase == "S99"
```

- [ ] **Step 2：Run + refine implementation until PASS**

Run: `pytest tests/supervisor/dim_collector/test_error_codes.py -v`  
Expected: 7 PASS after small patches to `scan_event_bus` / `scan_tool_calls` / `scan_latency_slo` to catch `AttributeError`/`None.event_bus` → `IC_L1_09_UNAVAILABLE`. Fix inline.

- [ ] **Step 3：commit**

```bash
git add tests/supervisor/dim_collector/test_error_codes.py app/supervisor/dim_collector/dim_scanner.py
git commit -m "feat(l1_07): ζ-WP01-T09 · 7 error-code TC 绿（IC timeouts / unavailable / all_dims_missing / phase_unknown）"
```

---

### Task 10：Perf SLO bench (pytest-benchmark)

**Files:**
- Create: `tests/supervisor/dim_collector/test_perf_slo.py`

- [ ] **Step 1：检查 pytest-benchmark 是否在 pyproject**

Run: `grep -l pytest-benchmark pyproject.toml`  
If missing: **flag in standup-log, do NOT modify pyproject (frozen shared file)**. Use stdlib `time.perf_counter_ns()` fallback instead.

- [ ] **Step 2：写 perf 测试（stdlib fallback 版本）**

```python
# tests/supervisor/dim_collector/test_perf_slo.py
import asyncio
import time
import statistics
import pytest
from app.supervisor.common.clock import RealClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.state_cache import StateCache

pytestmark = pytest.mark.asyncio


async def _real_collector():
    bus = EventBusStub()
    clock = RealClock()
    scanner = DimScanner(l102=L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus)
    return EightDimensionCollector(scanner=scanner, cache=StateCache(clock=clock, ttl_ms=60_000), event_bus=bus, clock=clock)


# TC-L107-L201-501 tick P95 ≤ 5000ms (stub is fast; assert ≤ 500ms in-mem)
async def test_tick_p95_under_500ms(pid) -> None:
    c = await _real_collector()
    samples = []
    for _ in range(20):
        start = time.perf_counter_ns()
        await c.tick_collect(project_id=pid.value)
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    samples.sort()
    p95 = samples[int(0.95 * len(samples))]
    assert p95 <= 500, f"tick P95 {p95:.2f}ms exceeds 500ms bench"


# TC-L107-L201-502 fast P99 ≤ 500ms
async def test_fast_p99_under_500ms(pid) -> None:
    c = await _real_collector()
    await c.tick_collect(project_id=pid.value)  # seed cache
    samples = []
    for _ in range(30):
        start = time.perf_counter_ns()
        await c.post_tool_use_fast_collect(
            project_id=pid.value, tool_name="git", tool_args_hash="h",
            tool_invoked_at_iso="2026-04-23T00:00:01Z", hook_deadline_ms=500,
        )
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    samples.sort()
    p99 = samples[min(len(samples) - 1, int(0.99 * len(samples)))]
    assert p99 <= 500, f"fast P99 {p99:.2f}ms exceeds 500ms"


# TC-L107-L201-503 on-demand cache-hit P95 ≤ 20ms
async def test_on_demand_cache_hit_p95_under_20ms(pid) -> None:
    c = await _real_collector()
    await c.tick_collect(project_id=pid.value)
    samples = []
    for _ in range(30):
        start = time.perf_counter_ns()
        await c.on_demand_collect(project_id=pid.value, consumer_id="ui-1", max_staleness_sec=60)
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    samples.sort()
    p95 = samples[int(0.95 * len(samples))]
    assert p95 <= 20, f"on-demand cache-hit P95 {p95:.2f}ms exceeds 20ms"
```

- [ ] **Step 3：Run PASS (or record to standup for SLO overrun)**

Run: `pytest tests/supervisor/dim_collector/test_perf_slo.py -v`

- [ ] **Step 4：commit**

```bash
git add tests/supervisor/dim_collector/test_perf_slo.py
git commit -m "feat(l1_07): ζ-WP01-T10 · perf SLO (tick/fast/on-demand cache-hit) · 3 TC 绿"
```

---

### Task 11：Coverage + standup

- [ ] **Step 1：运行全量 WP01 测试 + coverage**

```bash
cd /Users/zhongtianyi/work/code/harnessFlow
pytest tests/supervisor/dim_collector tests/supervisor/test_common_stubs.py \
  --cov=app.supervisor.dim_collector --cov=app.supervisor.common \
  --cov-report=term-missing --cov-fail-under=85 -v
```

Expected: **≥ 45 TC 绿 · coverage ≥ 85% for app/supervisor/dim_collector + app/supervisor/common**

- [ ] **Step 2：写 standup**

Create `docs/4-exe-plan/standup-logs/Dev-ζ-2026-04-23.md`:

```markdown
# Dev-ζ · standup · 2026-04-23

## 今日产出
- ✅ WP-ζ-01 L2-01 8-dim collector (tick + fast + on-demand) · 3 入口 · 8 dim scanner · LKG cache · error map
- ✅ ~45 TC green · coverage ≥ 85%
- ✅ 11 commits 落在 worktree-dev-zeta1-L1-07-supervisor

## Self-correction 记录
C-1 / C-2 / C-3（IC-13/14/15 + 订阅模型）— 已按 source doc 实施 · 等主会话修 exe-plan 与契约库一致性

## 下一步（下一会话执行）
- WP-ζ-02 L2-04 event_sender（IC-13 → L1-04 · IC-14 → L1-01 · 500ms bench）
- WP-ζ-03 L2-06 escalator（同级连 ≥ 3 failed 升级）
- ζ2 批（WP04-07）交给下一会话
```

- [ ] **Step 3：commit standup**

```bash
git add "docs/4-exe-plan/standup-logs/Dev-ζ-2026-04-23.md"
git commit -m "docs(l1_07): Dev-ζ standup 2026-04-23 · ζ-WP01 绿 · ≥ 45 TC · cov ≥ 85%"
```

---

## §F · WP-ζ-02 L2-04 Event Sender · Scaffold（下一会话）

**Files:**
- `app/supervisor/event_sender/__init__.py`
- `app/supervisor/event_sender/schemas.py` — `QualityLoopRoutePayload (IC-13)` / `HardHaltPayload (IC-14)`
- `app/supervisor/event_sender/suggestion_queue.py` — bounded 1000 asyncio.Queue · drop oldest WARN
- `app/supervisor/event_sender/rollback_pusher.py` — **IC-13** `push_quality_loop_route(wp_id, verdict_id, level, reason, from_state, to_state, evidence_refs) -> Ack` · 幂等（`<wp_id>:<verdict_id>` 去重）
- `app/supervisor/event_sender/halt_requester.py` — **IC-14** `request_hard_halt(red_line_id, alert_three_elements, evidence_refs) -> HaltAck` · **P99 ≤ 500ms**（pytest-benchmark 强断言）· 抢占 suggestion_queue

**TDD pattern:**
1. Schemas pydantic · red-green
2. SuggestionQueue bounded + drop-oldest · red-green
3. RollbackPusher 幂等（同 wp_id+verdict_id 返原 ack）· 调 L1-04 mock consumer
4. HaltRequester bench 500ms · 抢占测（队列满仍要 1ms 内 pick）
5. E2E：`tick_collect → degrade=CRITICAL → push_route → mock L1-04 收到`
6. commit `ζ-WP02`

---

## §G · WP-ζ-03 L2-06 Dead-Loop Escalator · Scaffold

- `app/supervisor/escalator/counter.py` — `FailureCounter` per (wp_id, level) · reset on `wp_done`
- `app/supervisor/escalator/escalation_logic.py` — 5 态机 L1→L2→L3→L4→HRL-04 · 同级连 ≥ 3 → 升级
- 订阅 L1-04 `wp_failed` via IC-11 `read_event_stream(types=["L1-04:wp_failed", "L1-04:wp_done"])`

**TDD pattern:**
1. Counter pure state · 10 TC（inc/reset/per-pid 隔离）
2. EscalationLogic · 15 TC（L1→L2 at count=3, L2→L3 at count=3, reset on done, counter 不跨 pid）
3. Integration：fake wp_failed events · ≥ 3 → call L2-04 `push_quality_loop_route(level="L2")` · mock L1-04 收到
4. commit `ζ-WP03`

---

## §H · ζ2 批 Scaffold（WP04-07）· 下一会话执行

### WP-ζ-04 · L2-02 4-Level Deviation Judge
- `app/supervisor/deviation_judge/threshold_matrix.py` — config-driven thresholds per dim
- `app/supervisor/deviation_judge/evaluator.py` — `evaluate_deviation(snapshot) -> DeviationVerdict(level=INFO|WARN|FAIL|CRITICAL, reasons=[...])`
- ~55 TC · 4 levels × 8 dims matrix coverage

### WP-ζ-05 · L2-03 Hard Red Line Interceptor (100ms hard)
- 5 detectors：`irreversible_ops` (HRL-02) / `drift_critical` (HRL-01) / `budget_overrun` (HRL-03) / `dead_loop_escalate` (HRL-04 via L2-06) / `fail_l4` (HRL-05)
- `detector.py` gather 5 并发 · 命中 → `halt_requester.request_hard_halt`
- **DoD：pytest-benchmark P99 ≤ 100ms detect-to-send**（hard constraint · 不达走 §6 情形 B）
- ~57 TC · 每 HRL ≥ 5 TC + 1 bench TC

### WP-ζ-06 · L2-05 Soft-Drift Pattern Matcher
- `window_stats.py` — 60 tick rolling window
- `trap_patterns.py` — 8 patterns (DoD evidence chain / progress deviation / skill fail / context >80% / light TDD fail / WP timeout / KB entry lost / network transient)
- Fire WARN via `push_quality_loop_route(level="L1")`（不 halt）
- ~55 TC · 每 pattern ≥ 3 TC

### WP-ζ-07 · Integration
- e2e `tests/supervisor/integration/test_group_e2e.py`：
  1. tick seeds snapshot with unhealthy dims → evaluator WARN → suggestion
  2. tick seeds snapshot with HRL-02 tool → red_line detect → halt_requester fire → mock L1-01 收到 within 500ms
  3. 3× wp_failed events → escalator fires quality_loop_route level=L2 → mock L1-04 收到
  4. context >80% pattern hit → soft_drift fires WARN
- ≥ 12 TC · IC-14 500ms e2e bench · commit `ζ-WP07`

---

## §I · Final DoD（全 ζ 组完成时）

- [ ] 6 L2 全绿 · **333 TC** · coverage ≥ 85%（per subpackage）
- [ ] IC-14 halt_requester send P99 ≤ 500ms（bench 3 次均值 · 不达 block）
- [ ] IC-13 quality_loop_route 幂等（同 wp_id+verdict_id 返原 ack）
- [ ] HRL 5 类每类 ≥ 5 TC · 端到端 detect→halt e2e 可观测
- [ ] Soft-drift 8 模式每模式 ≥ 3 TC
- [ ] 死循环升级：同级连 3 失败自动升级到下一级 · reset 幂等
- [ ] `projects/_correction_log.jsonl` 含 C-1/C-2/C-3 条目（等主会话仲裁）
- [ ] `app/supervisor/**` 只写自身目录 · pyproject / app/__init__.py 未动
- [ ] 所有 event append 含 root `project_id`（PM-14）

---

## §J · 下一会话继续方式

下一会话用户发：
```
按 docs/superpowers/plans/Dev-ζ-impl.md 接力执行，从 §F WP-ζ-02 开始。
```

继任会话应：
1. 调 `superpowers:executing-plans`
2. 读本 plan §F/§G/§H/§I
3. 按 §D 通用约束 + 每 WP scaffold 展开 TDD tasks
4. 每 WP 完更新 standup · 最终整合 commit `ζ-WP07`

---

*— Dev-ζ · L1-07 · Implementation Plan · v1.0 · 2026-04-23 —*
