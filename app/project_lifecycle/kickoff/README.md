# L2-02 启动阶段产出器（Kickoff · PM-14 pid 创建唯一入口）

> **一句话**：S1 阶段从"用户一句话"→ 澄清（IC-05） → 模板渲染（IC-L2-02） → 章程原子落盘 → anchor_hash 锁定 → 4 IC-09 事件 → activate 转 INITIALIZED。
>
> **PM-14 硬锁**：本 L2 是 `project_id` 创建 + 激活的**唯一入口**（越权即 E_L102_L202_010）。

## 对外 API

```python
from app.project_lifecycle.kickoff import (
    StartupProducer,
    KickoffRequest, KickoffResponse,
    ActivateRequest, ActivateResponse,
    activate_project_id,
    recover_draft,
)

# L2-01 调入口
sut = StartupProducer(
    brainstorm=l1_05_brainstorm_client,
    template=l2_07_template_engine,
    event_bus=l1_09_event_bus,
    project_root="/var/harnessflow",
)
resp = sut.kickoff_create_project(KickoffRequest(
    trigger_id="t-001", stage="S1",
    user_initial_goal="做内部 Wiki", caller_l2="L2-01",
))
# resp.status = "ok" | "degraded" | "err"
# resp.result: KickoffSuccess(project_id="p_...", charter_path=..., ..., events_published=(...))

# S1 Gate 通过后激活（PM-14 硬锁 · 必 L2-01 调）
act_resp = activate_project_id(
    ActivateRequest(
        project_id=resp.result.project_id,
        goal_anchor_hash=resp.result.goal_anchor_hash,
        user_confirmed=True,
        charter_path=resp.result.charter_path,
        stakeholders_path=resp.result.stakeholders_path,
        caller_l2="L2-01",  # 硬锁
    ),
    project_root="/var/harnessflow",
)
# act_resp.state == "INITIALIZED"

# L1-09 崩溃恢复
rec = recover_draft(pid, root_dir="/var/harnessflow", event_bus=bus)
# rec.action ∈ {"no_op", "resumed", "rolled_back"}
```

## 8 步主循环（produce_kickoff · tech §6.1）

1. 生成 pid（`p_{uuid4}` · 冲突重试 1 次 → E_PID_DUPLICATE）
2. 建 `projects/<pid>/{chart,meta,stage-gates}/`
3. 写 `meta/state.json`: `{"state": "DRAFT"}`
4. brainstorm.invoke · 澄清 ≤ 3 轮（> 3 → clarification_incomplete → status=degraded）
5. L2-07 render `kickoff.goal` + `kickoff.scope`（body 空 → E_TEMPLATE_INVALID）
6. atomic_write 2 份章程（tempfile + fsync + rename · 写后 sha 复核 · E_POST_WRITE_HASH_MISMATCH / E_CROSS_PROJECT_PATH / E_ATOMIC_WRITE_FAILED / E_CHART_ALREADY_EXISTS）
7. compute_anchor_hash（剥 frontmatter · Goal+Scope 正文 concat sha256）
8. atomic_write `meta/project_manifest.yaml` + 发 4 IC-09 事件按序：
   1. `project_created`
   2. `charter_ready`
   3. `stakeholders_ready`
   4. `goal_anchor_hash_locked`

## 15 错误码（E_L102_L202_001~015）

| 码 | 意义 | 触发 |
|:---|:---|:---|
| 001 PID_DUPLICATE | pid 冲突重试耗尽 | FS 已占 · 极罕见 |
| 002 USER_NOT_CONFIRMED | S1 Gate 未通过就 activate | `user_confirmed=False` |
| 003 GOAL_MISSING_SECTIONS | charter 必填字段缺 | degrade 占位 · 标 incomplete |
| 004 SCOPE_NOT_LOCKED | scope.in_scope 空 | strict_scope_lock=True 时 |
| 005 TEMPLATE_INVALID | L2-07 render 返空 body | template 损坏或 slot 错 |
| 006 CLARIFICATION_EXCEEDED | brainstorm > 3 轮 | degrade 非 err · status=degraded |
| 007 STATE_NOT_DRAFT | 状态非 DRAFT 调 activate | 重复激活 · state 已 INITIALIZED |
| 008 CHART_ALREADY_EXISTS | O_EXCL 目标已存在 | `exclusive=True` 时 |
| 009 POST_WRITE_HASH_MISMATCH | 写后 sha 不符 | I/O 故障或外部篡改 |
| 010 PM14_OWNERSHIP_VIOLATION | 非 L2-01 调 activate | 越权 · PM-14 硬锁 |
| 011 ANCHOR_HASH_MISMATCH | 章程被改 activate 时复核 | 外部篡改检测 |
| 012 CROSS_PROJECT_PATH | 路径无 `projects/<pid>/` | 内部 bug |
| 013 ATOMIC_WRITE_FAILED | OSError during write | 磁盘满 / 权限 |
| 014 GOAL_ANCHOR_TAMPERING | 激活后回溯检测 | 长时间后章程被改 |
| 015 BRAINSTORM_SUBAGENT_FAILED | L1-05 subagent 崩 | retry 1 次后仍失败 |

## IC 契约

- **IC-L2-01**（接收）· L2-01 → L2-02 · `KickoffRequest`
- **IC-L2-02**（发起）· L2-02 → L2-07 · render_template × 2（goal + scope）
- **IC-05**（发起）· L2-02 → L1-05 · brainstorm.invoke
- **IC-09**（发起）· L2-02 → L1-09 · 4 事件按序
- **IC-17**（间接接收）· L1-10 → L1-01 → L2-02 · user_intervene(approve) 触发 activate

## SLO（warm-cache）

| 维度 | P95 | 硬上限 |
|:---|:---:|:---:|
| atomic_write_chart（单份 md）| ≤ 200ms | 1s |
| compute_anchor_hash | ≤ 30ms | 100ms |
| produce_kickoff 全流程（mock）| ≤ 180ms | 3s |
| activate_project_id | ≤ 60ms | 500ms |

## 文件结构

```
app/project_lifecycle/kickoff/
├── __init__.py                 # public API export
├── schemas.py                  # KickoffRequest/Response/ActivateRequest/Response/...
├── errors.py                   # KickoffError + 15 错误码常量
├── pid_gen.py                  # generate_pid() → 'p_{uuid4}'
├── atomic_writer.py            # atomic_write_chart(path, content, exclusive=False)
├── anchor_hash.py              # compute_anchor_hash(pid, root_dir) 剥 frontmatter
├── producer_core.py            # produce_kickoff 8 步主循环
├── producer.py                 # StartupProducer · L2-01 调入口
├── activator.py                # activate_project_id · PM-14 硬锁
├── recovery.py                 # recover_draft · L1-09 崩溃恢复调
└── algo.py                     # facade · re-export pure algos
```

## 测试（39 TC · 全绿）

```
tests/project_lifecycle/
├── test_l2_02_kickoff_algo.py   · 6 TC (atomic_write + anchor_hash + 跨项目路径)
├── test_l2_02_produce_kickoff.py · 8 TC (主循环 + pid gen + brainstorm 故障)
├── test_l2_02_activate.py       · 9 TC (PM-14 硬锁 + state 转换 + recover_draft)
├── test_l2_02_producer.py       · 7 TC (StartupProducer public API + validate)
├── test_l2_02_negative.py       · 9 TC (剩余 9 错误码)
└── test_l2_02_ic_and_slo.py     · 9 TC (IC 契约 × 5 + SLO × 4)
```

Coverage ≥ 85%（target · 跑 `pytest --cov=app/project_lifecycle/kickoff`）。

## 不变量（I-L202-01~08）

- I-L202-01 · pid 必 `p_[0-9a-f-]{36}` · 全局唯一
- I-L202-02 · state 转换顺序：DRAFT → ... → INITIALIZED（不可跳 · 不可逆）
- I-L202-03 · Charter 8 字段最小集（degrade 时标 incomplete）
- I-L202-04 · Stakeholders ≥ 1（默认补 project_owner）
- I-L202-05 · `goal_anchor_hash` 锁定后不可改
- I-L202-06 · 澄清轮数 ≤ 3（超即 degrade）
- I-L202-07 · 4 事件按序经 IC-09 发 · 缺一不可
- I-L202-08 · 章程 frontmatter 带 `template_id / project_id`
