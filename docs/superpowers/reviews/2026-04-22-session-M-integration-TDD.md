# 【并发会话 M】3-2 TDD · integration/ × 24 份 · 跨 L2/跨 L1 集成测试

## 背景

harnessFlow 3-2-Solution-TDD 已有：
- **13 份 L2 单元测试**（G 会话交付 · L1-01 × 6 + L1-04 × 7）
- **44 份 L2 单元测试**（M5 H-L 五会话并行推进中）

**本会话（M）负责 `docs/3-2-Solution-TDD/integration/` 下 24 份跨 L2/跨 L1 集成测试**：
- 20 份 IC-XX-tests.md（每个全局 IC 契约的端到端测试）
- 4 份专项测试（10×10 矩阵 · PM-14 违规 · 失败传播 · 性能集成）

---

## 角色定位：与 L2 单元测试的分工

| 层级 | 目录 | 测什么 | 典型 fixture |
|:---|:---|:---|:---|
| **L2 unit tests**（已有 57 份骨架 · G + H-L 做） | `L1-NN/L2-*-tests.md` | 单个 L2 内部逻辑 | mock 所有对端 |
| **Integration tests**（本会话 · 24 份） | `integration/*.md` | **≥ 2 个 L2 的真实协作** · 契约落地 | mock 部分 / 真实调 |
| **Acceptance tests**（N 会话 · 12 份） | `acceptance/scenario-*.md` | 端到端业务场景 | 全真环境 mock 外部依赖 |

**关键原则**：本会话的测试**不重复** L2 unit 测试的单元边界，而是测**契约在生产方/消费方两侧同时成立**。

---

## 任务文件清单（只动 `docs/3-2-Solution-TDD/integration/` 目录）

### 20 份 IC-XX-tests.md（每 IC 契约的端到端测试）

| 文件名 | 契约源 | 生产方 L1 | 消费方 L1 | 核心测试点 |
|:---|:---|:---|:---|:---|
| `ic-01-tests.md` | IC-01 request_state_transition | L1-01 | L1-02 | 状态机合法转换 / 非法转换拒绝 / Gate 阻塞响应 |
| `ic-02-tests.md` | IC-02 get_next_wp | L1-01 | L1-03 | 拓扑依赖判定 / 并发上限 / 跨 pid 拒绝 |
| `ic-03-tests.md` | IC-03 enter_quality_loop | L1-01 | L1-04 | 异步启动 / 完成回调 / 并发 ≤ 2 |
| `ic-04-tests.md` | IC-04 invoke_skill | 多 L1 | L1-05 | fallback 链 / 超时 / capability 不存在 |
| `ic-05-tests.md` | IC-05 delegate_subagent | 多 L1 | L1-05 | PM-03 独立 session / context copy / 结果回收 |
| `ic-06-tests.md` | IC-06 kb_read | 多 L1 | L1-06 | scope 默认合并 / 降级无 KB / rerank |
| `ic-07-tests.md` | IC-07 kb_write_session | 多 L1 | L1-06 | 幂等（dedup_key） / schema 验证 |
| `ic-08-tests.md` | IC-08 kb_promote | 多 L1 | L1-06 | 晋升源标注 / 用户审核 / 回放 |
| `ic-09-tests.md` | IC-09 append_event | **全部 L1** | L1-09 | **最重** · 幂等 · fsync · 系统级 halt · hash chain |
| `ic-10-tests.md` | IC-10 replay_from_event | L1-09 内部 | L1-09 | 按 pid 回放 / tier 1-4 降级 |
| `ic-11-tests.md` | IC-11 process_content | 多 L1 | L1-08 | md / code / image 分路由 · 降级 |
| `ic-12-tests.md` | IC-12 delegate_codebase_onboarding | L1-08 | L1-05 | 大代码库异步 · 超时 10min |
| `ic-13-tests.md` | IC-13 push_suggestion | L1-07 | L1-01 | fire-and-forget · 队列背压 · BLOCK 抢占 |
| `ic-14-tests.md` | IC-14 push_rollback_route | L1-07 | L1-04 | 4 级回退 · 同级 ≥ 3 升级 · 幂等 |
| `ic-15-tests.md` | IC-15 request_hard_halt | L1-07 | L1-01 | **阻塞 ≤ 100ms 硬约束** · 幂等 · red_line_id |
| `ic-16-tests.md` | IC-16 push_stage_gate_card | L1-02 | L1-10 | 幂等（gate_id） · UI 渲染 ≤ 500ms |
| `ic-17-tests.md` | IC-17 user_intervene | L1-10 | L1-01 | 5 类干预 · panic ≤ 100ms · 跨 project 切换 |
| `ic-18-tests.md` | IC-18 query_audit_trail | L1-10 | L1-09 | 按 pid 过滤 · 大结果分页 |
| `ic-19-tests.md` | IC-19 request_wbs_decomposition | L1-02 | L1-03 | Sync 启动 + Async 执行 · 回调路由 |
| `ic-20-tests.md` | IC-20 delegate_verifier | L1-04 | L1-05 | 独立 session · verifier 超时 · 三段证据链 |

### 4 份专项测试

| 文件名 | 测试主题 | 源 |
|:---|:---|:---|
| `matrix-10x10-tests.md` | 10×10 集成矩阵 · 45 对（25 必测 ● + 20 弱依赖 ○）| PRD §4 + L1集成 arch §5 |
| `pm14-violation-tests.md` | PM-14 违规专项（跨 IC）· 缺 project_id · 跨 pid 越权 · 系统级例外 | PRD §3 每 IC 的 PM-14 行 + ic-contracts.md §6.1 |
| `failure-propagation-tests.md` | 失败传播链（10 L1 单失败 + 级联）· PM-14 隔离 · 系统级 halt 唯一入口 | PRD §6 + L1集成 arch §7 |
| `performance-integration-tests.md` | 端到端时延 / 吞吐 / 资源（7 条阈值）| PRD §7 + L1集成 arch §8 |

---

## 必读参考（强制 Read · 每份文件都要读）

| 优先级 | 文件 | 关键章节 |
|:---:|:---|:---|
| **P0** | `docs/3-1-Solution-Technical/integration/ic-contracts.md` | §2 20 IC 总表 · §3 每 IC 详规（6 小节）· §6 PM-14 规范 |
| **P0** | `docs/3-1-Solution-Technical/L1集成/architecture.md` | §4 20 IC 实现总览 · §5 10×10 矩阵 · §7 失败传播 · §8 性能 |
| **P0** | `docs/2-prd/L1集成/prd.md` | §3 每 IC 一致性测试点 · §4 10×10 矩阵 · §6 失败传播 · §7 性能 |
| **P1** | `docs/3-1-Solution-Technical/integration/cross-l1-integration.md` | DDD BC 依赖矩阵 · 一致性审计钩子 |
| **P1** | `docs/3-1-Solution-Technical/integration/p0-seq.md` | 12 条 P0 主干时序（作 IC 调用链参考）|
| **P1** | `docs/3-1-Solution-Technical/integration/p1-seq.md` | 11 条 P1 异常时序（作失败路径参考）|
| **P2** | G 会话标杆 | `docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-02-决策引擎-tests.md`（学 fixture / pytest 风格）|
| **P2** | M5 规划总览 | `docs/superpowers/reviews/2026-04-22-M5-TDD-parallel-plan.md`（10 段模板）|

---

## 硬必填（每份 400-800 行）

### IC-XX-tests.md 模板（20 份）

```markdown
---
doc_id: tests-integration-ic-NN-v1.0
doc_type: integration-ic-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.NN（IC-NN 详规）
  - docs/2-prd/L1集成/prd.md §3.NN（IC-NN 一致性测试点）
  - docs/3-1-Solution-Technical/L1集成/architecture.md §4
  - 3-1 生产方 L1 对应 L2 tech-design
  - 3-1 消费方 L1 对应 L2 tech-design
version: v1.0
---

# IC-NN · <IC 名> · 集成测试

> 测试范围：**生产方 L2 → 消费方 L2 的真实协作**（不是单 L2 的 mock 对端）

## §0 撰写进度

- [x] §1 契约概览（引 ic-contracts.md）
- [x] §2 生产方 / 消费方 L2 清单
- [x] §3 正向用例（契约字段完整 · 生产 + 消费两端验证）
- [x] §4 负向用例（每错误码 · 两端行为一致）
- [x] §5 PM-14 专项（根字段 · 跨 pid 越权）
- [x] §6 幂等性验证（若 IC 声明幂等）
- [x] §7 SLO 验证（P95 达标）
- [x] §8 失败降级（被调超时 / 5xx / IC-09 失败）
- [x] §9 跨 L1 场景（≥ 2 条端到端 mini-e2e）

## §1 契约概览

字段 schema · 幂等性 · SLO · From/To · 引 `docs/3-1-Solution-Technical/integration/ic-contracts.md §3.NN`。

## §2 生产方 / 消费方 L2 清单

本 IC 的调用方 / 被调方 L2 详细位置 · 字段 schema 对齐验证。

## §3 正向用例（每字段场景 ≥ 1）

pytest 代码 · 含 arrange/act/assert · TC ID `TC-IC-NN-HAPPY-NNN`。

## §4 负向用例（每错误码 ≥ 1）

覆盖 ic-contracts.md §3.NN.4 所有错误码 · TC ID `TC-IC-NN-NEG-NNN`。

## §5 PM-14 专项

缺 project_id / 跨 pid / system scope 例外 · TC ID `TC-IC-NN-PM14-NNN`。

## §6 幂等性（若声明）

重复调用同 payload 必返相同结果 · 副作用不重复 · TC ID `TC-IC-NN-IDEM-NNN`。

## §7 SLO 验证

P50/P95/P99 采样测试 · 基于 ic-contracts.md §2 SLO 列 · TC ID `TC-IC-NN-PERF-NNN`。

## §8 失败降级

被调超时 · 5xx · IC-09 失败 · TC ID `TC-IC-NN-DEGRADE-NNN`。

## §9 跨 L1 端到端（≥ 2 条）

串联 ≥ 3 个 L2 的协作场景 · TC ID `TC-IC-NN-E2E-NNN`。
```

**行数**：400-800 行/份 · **TC 总数**：每 IC ≥ 15 个 TC（跨 5-9 段分布）

### 4 份专项测试

**matrix-10x10-tests.md**（约 1000-1500 行）：
- 引 PRD §4 + L1集成 arch §5
- 45 对每对 ≥ 1 冒烟测试
- 25 必测对每对 ≥ 4 用例（正向/负向/PM-14/降级）
- **总 TC ≥ 120 个**

**pm14-violation-tests.md**（约 500-800 行）：
- 所有 20 IC 的 PM-14 违规用例（每 IC 2-3 个 · 总 ≥ 50 TC）
- 跨 pid 越权 / 缺 project_id / system scope 例外

**failure-propagation-tests.md**（约 800-1200 行）：
- 10 L1 每个失败 → 传播链测试（10 × 3 = 30 TC）
- PM-14 隔离（project foo 失败不影响 project bar · ≥ 10 TC）
- 系统级 halt（L1-09 失败 · 全局 halt · ≥ 5 TC）
- **总 TC ≥ 50**

**performance-integration-tests.md**（约 500-800 行）：
- PRD §7.1 端到端时延（11 个阈值 · 每阈值 ≥ 2 采样 TC）
- PRD §7.2 吞吐（5 指标）
- PRD §7.3 资源（2 维度）
- pytest-benchmark 风格 · **总 TC ≥ 40**

---

## 执行节奏

### 每份 IC-XX-tests.md · 6 步

1. Read ic-contracts.md §3.NN（限 300 行切片）
2. Read PRD §3.NN 对应节
3. Read 生产方 + 消费方 L2 的 §3 接口（2 个 3-1 文件）
4. Write 整份（400-800 行 · 一次性）
5. Bash 验证：
   ```bash
   fp="docs/3-2-Solution-TDD/integration/ic-NN-tests.md"
   echo "行=$(wc -l < "$fp") · §=$(grep -c '^## §' "$fp") · FILL=$(grep -c '<!-- FILL' "$fp") · test=$(grep -cE '\bdef test_' "$fp") · TC=$(grep -cE 'TC-IC-\d+' "$fp")"
   ```
6. Commit：
   ```bash
   git add "docs/3-2-Solution-TDD/integration/ic-NN-tests.md"
   git commit -m "feat(harnessFlow): R5.5-M · integration/ic-NN-tests depth-B"
   ```

### 推进顺序（按重要性）

**波 1 · 最热 IC（5 份）**：
1. `ic-09-tests.md`（全 L1 生产 · 系统级 halt）
2. `ic-01-tests.md`（状态机控制源）
3. `ic-15-tests.md`（硬红线 · 100ms 硬约束）
4. `ic-17-tests.md`（用户 panic · 100ms）
5. `ic-04-tests.md`（skill 最高频调用）

**波 2 · 数据类（5 份）**：IC-02/03/11/19/20

**波 3 · KB + 多模态（5 份）**：IC-05/06/07/08/12

**波 4 · 监督 + UI（5 份）**：IC-10/13/14/16/18

**波 5 · 4 份专项**（顺序）：
1. `pm14-violation-tests.md`（先 · 因为 20 IC 都涉及）
2. `failure-propagation-tests.md`
3. `matrix-10x10-tests.md`
4. `performance-integration-tests.md`

---

## 硬约束（禁区红线）

- ❌ **不修改 3-1 任何文件** · 只读
- ❌ **不修改 `docs/2-prd/`** · 只读
- ❌ **不修改 `docs/3-1-Solution-Technical/integration/`** · 只读
- ❌ **不改 `docs/3-2-Solution-TDD/L1-*/`**（L2 unit 测试 · H-L 五会话的领地）
- ❌ **不改 `docs/3-2-Solution-TDD/acceptance/`**（N 会话领地）
- ❌ **不改 scripts/quality_gate.sh**

### 命名规范

- 文件：`ic-NN-tests.md`（NN 两位数 01-20） · 4 专项用描述性名
- TC ID：
  - IC 单项：`TC-IC-NN-<类型>-NNN`（类型：HAPPY / NEG / PM14 / IDEM / PERF / DEGRADE / E2E）
  - 专项：`TC-MATRIX-<对>-NNN` / `TC-PM14-<IC>-NNN` / `TC-FAIL-<L1>-NNN` / `TC-PERF-<指标>-NNN`
- 测试函数：`test_ic_NN_<场景简述>`

### 契约引用必带锚点

所有 IC 字段引用必带完整锚点：

```
docs/3-1-Solution-Technical/integration/ic-contracts.md §3.NN.3（入参 schema）
docs/3-1-Solution-Technical/integration/ic-contracts.md §3.NN.4（错误码）
docs/2-prd/L1集成/prd.md §3.<IC 段>
```

---

## 最终验收

```bash
# 1. 自检 24 份
python3 <<'PYEOF'
import os, re
base = "docs/3-2-Solution-TDD/integration"
for fn in sorted(os.listdir(base)):
    if not fn.endswith(".md"): continue
    fp = os.path.join(base, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    lines = c.count(chr(10))+1
    fill = c.count("<!-- FILL")
    secs = len(re.findall(r"^## §\d", c, re.M))
    tc = len(set(re.findall(r"TC-[A-Z0-9]+-[A-Z0-9-]+-\d+", c)))
    tests = len(re.findall(r"\bdef test_", c))
    status = "✓" if (fill == 0 and secs >= 9 and tc >= 15 and tests >= 15) else "✗"
    print(f"{status} {fn}: lines={lines} §={secs} FILL={fill} TC={tc} test_fn={tests}")
PYEOF

# 2. 20 IC 全覆盖检查
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20; do
    [ -f "docs/3-2-Solution-TDD/integration/ic-$n-tests.md" ] && echo "✓ IC-$n" || echo "✗ 缺 IC-$n"
done

# 3. 4 专项检查
for f in matrix-10x10-tests.md pm14-violation-tests.md failure-propagation-tests.md performance-integration-tests.md; do
    [ -f "docs/3-2-Solution-TDD/integration/$f" ] && echo "✓ $f" || echo "✗ 缺 $f"
done

# 4. Gate
./scripts/quality_gate.sh

# 5. push
git push origin main
```

**完成后回主会话**：24 份全部 depth-B · commit SHA 列表 · 总行数 · 总 TC 数。

---

## 开工前检查

```bash
git pull origin main
git status                                                  # 应干净
ls "docs/3-2-Solution-TDD/integration/" 2>/dev/null || echo "目录不存在 · 你将创建它"
# 必备源文件行数
wc -l "docs/3-1-Solution-Technical/integration/ic-contracts.md"   # 2504 行
wc -l "docs/3-1-Solution-Technical/L1集成/architecture.md"       # 1377 行
```

准备好后从 **波 1 / ic-09-tests.md**（最热 · 全 L1 生产 · 系统级 halt）开始。
