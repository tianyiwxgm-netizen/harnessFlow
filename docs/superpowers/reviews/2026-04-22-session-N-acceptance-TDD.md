# 【并发会话 N】3-2 TDD · acceptance/ × 12 份 · 端到端验收场景

## 背景

harnessFlow 3-2-Solution-TDD 已有 / 推进中：
- **57 份 L2 单元测试**（G 13 完 + M5 H-L 44 推进中）
- **24 份 integration 集成测试**（M 会话推进中）

**本会话（N）负责 `docs/3-2-Solution-TDD/acceptance/` 下 12 份端到端验收场景**。

与其他测试层的分工：

| 层级 | 范围 | 测什么 | 典型时长 |
|:---|:---|:---|:---|
| L2 unit | 单个 L2 内部 | 算法 / 状态 / 错误码 | ms 级 |
| Integration（M） | 跨 L2 契约 | IC 在生产/消费方两端一致 | 秒级 |
| **Acceptance（本会话）** | **端到端业务场景** | **真实用户流程 · 跨 L1 × 多阶段** | 秒-分-时级 |

---

## 任务文件清单（只动 `docs/3-2-Solution-TDD/acceptance/` 目录）

12 份 scenario tests.md · 严格对应 PRD `L1集成/prd.md §5` 的 12 场景 + L1集成 `architecture.md §6` 的技术组合：

| # | 文件 | 场景 | 涉 L1 | 时长 | 类型 |
|:---:|:---|:---|:---|:---|:---|
| 1 | `scenario-01-wp-quality-loop-tests.md` | WP 执行正常一轮 Quality Loop | 5 | 30 min | 正常 |
| 2 | `scenario-02-s1-to-s7-full-tests.md` | **项目从 S1 启动到 S7 交付完整流程** | 10 | 1-3 周（压缩版）| 正常 · **最长** |
| 3 | `scenario-03-s2-gate-rework-tests.md` | S2 Gate No-Go + 4 件套部分重做 | 4 | 10-30 min | 正常变体 |
| 4 | `scenario-04-change-request-tests.md` | 运行时 change_request（TOGAF H） | 5 | 10 min | 正常变体 |
| 5 | `scenario-05-hard-red-line-tests.md` | 硬红线触发（不可逆操作拦截） | 4 | < 1 min（硬约束） | 异常 |
| 6 | `scenario-06-panic-resume-tests.md` | 用户 panic + PAUSED + resume | 2 | < 1 min | 异常 |
| 7 | `scenario-07-verifier-fail-rollback-tests.md` | S5 verifier FAIL → 4 级回退路由 | 3 | 30-120 min | 异常 |
| 8 | `scenario-08-cross-session-recovery-tests.md` | 跨 session 重启恢复未决 Gate | 5 | 5-15 s | 异常 |
| 9 | `scenario-09-loop-escalation-tests.md` | 同级 FAIL ≥ 3 死循环升级 | 2 | 5-20 min | 异常 |
| 10 | `scenario-10-kb-promotion-tests.md` | KB 晋升仪式（S7 收尾时）| 2 | 2 min | 正常 |
| 11 | `scenario-11-multi-project-v2-tests.md` | 多项目并发切换（V2+ PM-14）| 10 | N × 1 周 | V2+ · **延后** |
| 12 | `scenario-12-large-codebase-onboarding-tests.md` | 大代码库 onboarding 委托 | 4 | 5-10 min | 正常变体 |

**V1 必做 11 份**（除 scenario-11 · V2+ 延后 · 但骨架要建）。

---

## 必读参考（强制 Read · 每份都要读）

| 优先级 | 文件 | 关键章节 |
|:---:|:---|:---|
| **P0** | `docs/2-prd/L1集成/prd.md` | §5 端到端集成场景（12 个 · 每场景含完整流程描述）|
| **P0** | `docs/3-1-Solution-Technical/L1集成/architecture.md` | §6 12 端到端场景的时序实现（每场景 20-40 行技术组合）|
| **P0** | `docs/3-1-Solution-Technical/integration/p0-seq.md` | 12 条 P0 主干时序（覆盖 scenario 1/2/10/12）|
| **P0** | `docs/3-1-Solution-Technical/integration/p1-seq.md` | 11 条 P1 异常时序（覆盖 scenario 3/5/6/7/8/9）|
| **P1** | `docs/3-1-Solution-Technical/integration/ic-contracts.md` | §3 各 IC 详规（每场景涉及的 IC 链）|
| **P1** | PRD 10 L1 prd.md | 对应 L1 章节（场景涉及的 L1 产品边界）|
| **P2** | G 会话标杆 | L1-01/L2-02 tests（学 fixture / pytest 结构）|
| **P2** | M5 规划 | `docs/superpowers/reviews/2026-04-22-M5-TDD-parallel-plan.md` |

---

## 硬必填（每份 500-1500 行）

### 模板 · 每份 scenario-NN-tests.md 的 10 段结构

```markdown
---
doc_id: tests-acceptance-scenario-NN-v1.0
doc_type: e2e-acceptance-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/2-prd/L1集成/prd.md §5.NN（场景 NN 定义）
  - docs/3-1-Solution-Technical/L1集成/architecture.md §6.NN（场景 NN 技术实现）
  - docs/3-1-Solution-Technical/integration/p0-seq.md §<N>（若涉 P0 时序）
  - docs/3-1-Solution-Technical/integration/p1-seq.md §<N>（若涉 P1 异常）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md（涉及的 IC 详规）
version: v1.0
---

# 场景 NN · <场景名> · 端到端验收测试

> **场景类型**：正常 / 异常 / 变体
> **涉及 L1**：<列表>
> **典型时长**：<预期>
> **PRD 锚点**：`docs/2-prd/L1集成/prd.md §5.NN`

## §0 撰写进度

- [x] §1 场景概览（引 PRD §5.NN）
- [x] §2 前置条件 + Given 数据
- [x] §3 完整流程 When 步骤（按 p0/p1-seq 时序）
- [x] §4 主流程 Then 断言（正向 · GWT 用例 ≥ 3）
- [x] §5 异常分支 GWT 用例（≥ 3）
- [x] §6 PM-14 专项断言（project_id 透传 + 隔离）
- [x] §7 性能 SLO 断言（L1集成 arch §8 相关条目）
- [x] §8 跨 session 恢复（若涉及）
- [x] §9 测试 fixture + mock 策略

## §1 场景概览

> 一句话：<场景一句话描述>
>
> PRD 定义：引 `docs/2-prd/L1集成/prd.md §5.NN`（完整引用）
> 技术组合：引 `docs/3-1-Solution-Technical/L1集成/architecture.md §6.NN`（完整引用）

## §2 前置条件（Given）

项目状态 · 数据环境 · mock 配置：

```yaml
given:
  project_id: "proj-<hex>-<date>"
  project_state: "<state>"
  prerequisites:
    - <条件 1>
    - <条件 2>
  mock_services:
    llm: stub_skill_registry
    event_bus: in-memory（带 fsync mock）
    ui: off（本 e2e 仅测后端流程）
```

## §3 完整流程（When · 按时序分步）

```python
class TestScenarioNN:
    def test_scenario_NN_happy_path(self, e2e_env):
        """TC-SCENARIO-NN-HAPPY-001 · 正向完整流程"""
        # Step 1: <第一步动作>
        # 引 p0-seq.md §N.M 对应时序步骤
        result1 = e2e_env.l1_01.tick()
        assert result1.action == "get_next_wp"
        # ...逐步 N 步...
```

## §4 主流程 Then 断言（≥ 3 GWT 用例）

每个 Then 断言点独立 TC · 覆盖主要产出物 / 状态转换 / 审计事件。

## §5 异常分支 GWT（≥ 3 用例）

覆盖 PRD §5.NN 的异常分支 · 引 p1-seq.md 对应时序。

## §6 PM-14 专项断言

- `project_id` 在全链 IC payload 中透传
- 所有产出物落 `projects/<pid>/*`
- 审计事件（IC-09）每条含 project_id
- 跨 project 访问拒绝（本场景 mock 第二 pid · 验证隔离）

## §7 性能 SLO 断言

基于 L1集成 arch §8 对应条目（如 panic ≤ 100ms · Gate ≤ 2s · 单 tick ≤ 5s）。

## §8 跨 session 恢复（若涉）

场景 2/8 必测 · 其他可选。模拟进程 kill · bootstrap · 校验恢复后状态与 kill 前一致。

## §9 测试 fixture + mock 策略

```python
@pytest.fixture
def e2e_env():
    """端到端环境 fixture · mock 所有外部依赖 · 真实跑 L1 逻辑"""
    return E2EEnv(
        mock_llm=StubLLM(),
        mock_fs=InMemoryFS(),
        mock_time=FakeClock(),
    )
```

## 附录 · 场景涉及的 IC 链

<IC-N → IC-M → IC-X ... 的完整调用链表 · 引 ic-contracts.md 锚点>

---

*— Acceptance · 场景 NN · depth-B · v1.0 —*
```

---

## 每份场景的重点 GWT 覆盖矩阵

| # | 场景 | 核心 Then | 性能硬约束 |
|:---:|:---|:---|:---|
| 1 | WP Quality Loop | 5 阶段全跑完 · verdict=PASS/FAIL · 审计齐 | 单 WP Quality Loop ≤ 30 min |
| 2 | S1→S7 完整 | 7 阶段 × 4 Gate 全通 · 归档 tar.zst · sha256 | （压缩版测试）|
| 3 | S2 Gate rework | reject → 用户 rework → 第二次 pass | 影响面 ≤ 5s |
| 4 | change_request | Phase H · 影响面分析 · diff WBS | ≤ 5s 影响面 |
| 5 | 硬红线 | 不可逆操作拦截 · state=HALTED · IC-15 | **≤ 100ms 硬约束** |
| 6 | panic | state=PAUSED · 所有 in-flight 挂起 | **≤ 100ms 硬约束** |
| 7 | Verifier FAIL | 4 级回退路由 · IC-14 推送 | — |
| 8 | 跨 session 恢复 | Tier 1-4 恢复 · 状态与 halt 前一致 | bootstrap ≤ 5s |
| 9 | 死循环升级 | 同级 ≥ 3 · 自动升下一级 · 审计 | — |
| 10 | KB 晋升 | session→project→global · IC-08 | — |
| 11 | 多 project（V2+） | 并发 ≥ 3 project · 隔离 | 多 project ≥ 10 吞吐 |
| 12 | 大代码库 onboarding | 独立 subagent · 10min 超时 | ≤ 10 min |

---

## 执行节奏（每份 · 6 步）

1. Read PRD §5.NN 完整（100-300 行）
2. Read L1集成 arch §6.NN + 相关 p0/p1-seq 章节
3. Read 涉及的 IC 详规（ic-contracts.md §3.N × 3-8 个 IC）
4. Write 整份 scenario-NN-tests.md（500-1500 行 · 一次性）
5. Bash 验证：
   ```bash
   fp="docs/3-2-Solution-TDD/acceptance/scenario-NN-xxx-tests.md"
   echo "行=$(wc -l < "$fp") · §=$(grep -c '^## §' "$fp") · FILL=$(grep -c '<!-- FILL' "$fp") · test=$(grep -cE '\bdef test_' "$fp") · GWT=$(grep -cE 'given|when|then' "$fp")"
   ```
6. Commit：
   ```bash
   git add "docs/3-2-Solution-TDD/acceptance/scenario-NN-xxx-tests.md"
   git commit -m "feat(harnessFlow): R5.6-N · acceptance/scenario-NN <场景名> depth-B"
   ```

---

## 推进顺序（按复杂度 · 由简到难）

**波 1 · 短场景（4 份 · 练手）**：
1. `scenario-05-hard-red-line-tests.md`（硬约束 · 逻辑清晰 · ≤ 100ms）
2. `scenario-06-panic-resume-tests.md`（同 · 100ms 硬约束）
3. `scenario-09-loop-escalation-tests.md`（计数器 · 简单）
4. `scenario-10-kb-promotion-tests.md`（KB 单流）

**波 2 · 中等复杂度（4 份）**：
5. `scenario-01-wp-quality-loop-tests.md`（5 L1 × 5 阶段）
6. `scenario-03-s2-gate-rework-tests.md`（Gate rework）
7. `scenario-04-change-request-tests.md`（TOGAF H）
8. `scenario-12-large-codebase-onboarding-tests.md`（subagent 超时）

**波 3 · 最复杂（3 份 V1 必做）**：
9. `scenario-07-verifier-fail-rollback-tests.md`（4 级回退）
10. `scenario-08-cross-session-recovery-tests.md`（Tier 1-4 · bootstrap）
11. `scenario-02-s1-to-s7-full-tests.md`（**最长 · 含所有 Gate · 压缩为测试友好版本**）

**波 4 · V2+（1 份 · 建骨架即可）**：
12. `scenario-11-multi-project-v2-tests.md`（标记 V2+ · FILL § 骨架 · 待 V2 填）

---

## 硬约束（禁区红线）

- ❌ **不修改 3-1 任何文件** · 只读
- ❌ **不修改 `docs/2-prd/`** · 只读
- ❌ **不改 `docs/3-2-Solution-TDD/L1-*/`**（H-L 领地）
- ❌ **不改 `docs/3-2-Solution-TDD/integration/`**（M 领地）
- ❌ **不改 scripts/quality_gate.sh**
- ❌ **不要在多份 scenario 中复制粘贴相同 fixture**（提取到 `acceptance/conftest.py` 规格层 · 用 `@pytest.fixture` 注入）

### 命名规范

- 文件：`scenario-NN-<kebab-slug>-tests.md`（NN 01-12）
- TC ID：`TC-SCENARIO-NN-<类型>-NNN`（类型：HAPPY / NEG / PM14 / PERF / RECOVERY）
- fixture：`e2e_env` / `mock_user` / `mock_project_id` / `fake_clock`

---

## 最终验收

```bash
# 1. 自检 12 份
python3 <<'PYEOF'
import os, re
base = "docs/3-2-Solution-TDD/acceptance"
for fn in sorted(os.listdir(base)):
    if not fn.endswith(".md"): continue
    fp = os.path.join(base, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    lines = c.count(chr(10))+1
    fill = c.count("<!-- FILL")
    secs = len(re.findall(r"^## §\d", c, re.M))
    tc = len(set(re.findall(r"TC-SCENARIO-\d+-[A-Z]+-\d+", c)))
    tests = len(re.findall(r"\bdef test_", c))
    # GWT 模式检查（场景测试必含 Given/When/Then 语义）
    has_gwt = all(kw in c.lower() for kw in ["given", "when", "then"])
    status = "✓" if (fill == 0 and secs >= 9 and tc >= 10 and tests >= 10 and has_gwt) else "✗"
    print(f"{status} {fn}: lines={lines} §={secs} FILL={fill} TC={tc} test_fn={tests} GWT={has_gwt}")
PYEOF

# 2. 12 场景齐全检查
for n in 01 02 03 04 05 06 07 08 09 10 11 12; do
    f=$(ls "docs/3-2-Solution-TDD/acceptance/scenario-$n-"*.md 2>/dev/null | head -1)
    [ -n "$f" ] && echo "✓ scenario-$n: $(basename "$f")" || echo "✗ 缺 scenario-$n"
done

# 3. 硬约束关键字检查
grep -l "100ms" "docs/3-2-Solution-TDD/acceptance/scenario-05-"* && echo "✓ 硬红线 100ms 覆盖"
grep -l "100ms" "docs/3-2-Solution-TDD/acceptance/scenario-06-"* && echo "✓ panic 100ms 覆盖"

# 4. Gate
./scripts/quality_gate.sh

# 5. push
git push origin main
```

**完成后回主会话**：12 份 commit SHA · 总行数 · 总 TC · 波 1-4 各完成数。

---

## 开工前检查

```bash
git pull origin main
git status
ls "docs/3-2-Solution-TDD/acceptance/" 2>/dev/null || echo "目录不存在 · 你将创建它"
# 确认源文件就位
wc -l "docs/2-prd/L1集成/prd.md"                           # ≈ 1100 行
wc -l "docs/3-1-Solution-Technical/L1集成/architecture.md"  # 1377 行
wc -l "docs/3-1-Solution-Technical/integration/p0-seq.md"   # 1819 行
wc -l "docs/3-1-Solution-Technical/integration/p1-seq.md"   # 1912 行
```

准备好后从 **波 1 · scenario-05 硬红线**（100ms 硬约束 · 逻辑清晰 · 最佳练手）开始。
