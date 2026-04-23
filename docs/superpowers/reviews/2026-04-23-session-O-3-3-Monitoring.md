# 【并发会话 O】3-3 Monitoring & Controlling · 10 份填充（M6 主力）

## 背景

harnessFlow 分 3 层方案：
- **3-1 Technical**（完成 78/78 · 技术实现）
- **3-2 TDD**（完成 56/57 · 测试用例）
- **3-3 Monitoring & Controlling**（本会话 · 10 份 · 监督 + 判通过规约）

**3-3 定位**：3-1 讲"如何实现" · 3-2 讲"如何测" · **3-3 讲"如何监督与判通过"** —— 是整个 harnessFlow 的**质量契约源**。

**M6 里程碑**：3-3 完成 = 可交付状态达成。

---

## 任务文件（10 份 · 骨架已建 · commit 7d69edc）

```
docs/3-3-Monitoring-Controlling/
├── L0/overview.md                             (3-3 总览)
├── hard-redlines.md                           (★ 核心 · 5 类硬红线不可失真)
├── soft-drift-patterns.md                     (8 类软漂移模式库)
├── acceptance-criteria.md                     (最终交付验收)
├── quality-standards/coding-standards.md      (Python/Vue 编码标准)
├── dod-specs/
│   ├── general-dod.md                         (★ 核心 · 通用 DoD 规约)
│   ├── stage-dod.md                           (S1-S7 阶段 DoD)
│   └── wp-dod.md                              (WP/TDD/Verifier DoD)
└── monitoring-metrics/
    ├── system-metrics.md                      (系统指标)
    └── quality-metrics.md                     (质量指标)
```

每份当前骨架 63 行 · 含 frontmatter + §0-§6 + 9 FILL 占位。

---

## 质量标杆（每份 600-1500 行 · 按 3-1 架构文档风格）

| 维度 | 硬要求 |
|:---|:---|
| § 段数 | ≥ 6（可扩展到 §13 深度）|
| FILL | **0** |
| Mermaid | 禁 · PlantUML 或纯文本图 |
| 反向映射 | 每份 §6 必带完整路径 `docs/2-prd/L0/scope.md §X.X` 或 `docs/2-prd/L1-NN/prd.md §X.X` |
| 消费方对接 | §4 明确对接 L1-04（质量 Gate 编译器）/ L1-07（监督）/ L1-09（审计）|
| YAML schema | 关键规约必给字段级 YAML（如硬红线 payload · DoD 表达式）|
| 开源对标 | 建议（非必做）· 如有参考（Prometheus / OpenTelemetry / 其他）列出 |

---

## 必读参考（每份都要读）

| 优先级 | 文件 | 用途 |
|:---:|:---|:---|
| P0 | `docs/2-prd/L0/scope.md` | 硬红线 5 类 / 软漂移 / DoD 定义源（§8-§10）|
| P0 | `docs/2-prd/HarnessFlowGoal.md` | 顶层 Goal · 可追溯率 · PM 清单 |
| P0 | `docs/3-1-Solution-Technical/L1集成/architecture.md` | §7 失败传播 · §8 性能 · §11 测试框架（本 3-3 是它的消费者视角）|
| P0 | `docs/3-1-Solution-Technical/integration/ic-contracts.md` | §2 20 IC 总表 · §6 PM-14 规范 |
| P1 | `docs/3-1-Solution-Technical/L1-04-Quality Loop/architecture.md` | 质量环如何消费 DoD（对接点）|
| P1 | `docs/3-1-Solution-Technical/L1-07-Harness监督/architecture.md` | 监督如何订阅红线（对接点）|
| P1 | `docs/2-prd/L1-07 Harness监督/prd.md` | 硬红线 5 类 / 软漂移 8 类产品定义 |
| P1 | `docs/2-prd/L1-04 Quality Loop/prd.md` | DoD 表达式 · 5 级 verdict · 4 级回退 |

---

## 10 份速查表（各 L2 的重点覆盖）

### 1. `hard-redlines.md` ★★★ 最核心（主会话建议自己做 · 防失真）

**内容**：5 类硬红线完整清单（产品 scope §8.5）· 每条含：
- 触发条件（事件模式）
- 响应 SLO（≤ 100ms 硬约束）
- 拦截机制（L1-07 L2-03 → IC-15 → L1-01 state=HALTED）
- 用户文字授权放行协议（唯一入口）
- 审计 schema（IC-09 event_type="hard_red_line_*"）
- 反向追溯到 scope / L1-07 prd

**典型 5 类**（scope §8.5.1-§8.5.5 给出）：
- `HRL-01` 不可逆操作（rm -rf / drop / force push main）
- `HRL-02` 跨 project 数据泄漏
- `HRL-03` 硬编码 skill 名违规
- `HRL-04` 安全凭证泄漏
- `HRL-05` 审计绕过尝试

**行数预期**：800-1200 行

### 2. `dod-specs/general-dod.md` ★★★ 核心（主会话建议自己做 · 防失真）

**内容**：
- DoD 定义（Definition of Done）
- DoD 表达式语法（AST 白名单 · 引 L1-04 L2-02 DoD 表达式编译器 §3）
- DoD 维度矩阵（功能性 / 可追溯 / PM-14 / 审计 / 性能）
- 评估时机（WP 完成 / Stage Gate / S5 Integration）
- 证据要求（指向具体文件 / 事件 ID / 测试结果）
- pass/reject/need_input 判据

**行数预期**：600-1000 行

### 3. `dod-specs/stage-dod.md`

**内容**：S1-S7 每阶段的 DoD（引 L1-02 stage-gate 控制器 §8 状态机）：
- S1 Kickoff DoD（章程齐 · anchor_hash ok）
- S2 Planning Gate（4 件套 + PMP 9 + TOGAF）
- S3 TDD Gate（蓝图齐 · DAG 无环）
- S4 Executing（N/A · 是动态过程）
- S5 Integration Gate（Verifier 全 PASS · 回归过）
- S6 Closing Gate（lessons + delivery_manifest + retro）
- S7 Archive（tar.zst + sha256 + chmod 0444）

每 Stage 含：前置证据 / pass 判据 / reject 判据 / need_input 判据

**行数预期**：800-1200 行

### 4. `dod-specs/wp-dod.md`

**内容**：WP 粒度 DoD（引 L1-04 质量环 5 段）：
- TDD 蓝图 DoD（GWT 齐 · 测试覆盖 ≥ 80%）
- TDD 用例 DoD（每方法 ≥ 1 正向 · 每错误码 ≥ 1 负向）
- 质量 Gate 编译 DoD（DoD 表达式 AST 校验 + evidence 映射）
- S4 执行驱动 DoD（代码 commit · lint + format pass）
- S5 Verifier 报告 DoD（三段证据链）
- 5 级 verdict（PASS / PASS_WITH_WARNINGS / INSUFFICIENT / FAIL_L1~L4 / HARD_FAIL）

**行数预期**：600-1000 行

### 5. `soft-drift-patterns.md`

**内容**：8 类软漂移模式库（引 L1-07 L2-05 Soft-drift 识别器 + scope §8.6）：
- 温水煮青蛙型（slow burn）
- 范围蔓延型（scope creep）
- 优化僵局型（over-optimization）
- 伪同意型（fake agreement）
- 测试作弊型（test skip）
- 证据薄弱型（evidence thin）
- 性能退化型（perf decay）
- 审计遗漏型（audit gap）

每类含：识别窗口（滑窗统计）· trap 模式（正则/事件序列）· 4 级告警升级（INFO/WARN/FAIL/CRITICAL）

**行数预期**：700-1000 行

### 6. `acceptance-criteria.md`

**内容**：最终交付验收标准
- Definition of Delivery（可交付定义）
- 5 维度验收（功能性 / 可追溯 / 安全 / 性能 / 文档）
- M1-M6 里程碑验收表
- 签收流程（引 L1-02 S7 归档）
- V2+ 演进路径（延后项）

**行数预期**：500-800 行

### 7. `L0/overview.md`

**内容**：3-3 层总览
- 本层定位（与 3-1/3-2 关系）
- 10 份组织
- 消费方清单
- 版本治理
- 冲突解决优先级

**行数预期**：400-600 行

### 8. `quality-standards/coding-standards.md`

**内容**：
- Python 3.11+ 编码规范（PEP 8 + 类型注解 + black/isort）
- Vue 3 + TypeScript + Element Plus 编码规范
- 命名（变量 / 函数 / 类 / 文件）
- 注释 / docstring
- lint 工具链（ruff / mypy / eslint）
- 代码评审 Checklist

**行数预期**：500-800 行

### 9. `monitoring-metrics/system-metrics.md`

**内容**：系统级指标
- tick/s · event QPS · 延迟分位
- 资源（内存 / CPU / 磁盘 / IO）
- 背压指标（队列深度 · 反压触发次数）
- Prometheus 指标命名规范
- SLO/SLI 对照（引 L1集成 arch §8）

**行数预期**：500-700 行

### 10. `monitoring-metrics/quality-metrics.md`

**内容**：质量级指标
- 决策可追溯率（100% 硬约束）
- Gate 通过率（按 Stage 分）
- 回滚频次（L1-04 4 级回退）
- 软漂移检测命中率
- 硬红线触发次数
- DoD 评估通过率
- 引 Goal.md §4.1 / scope §4.6 PM-14 衍生约束

**行数预期**：500-700 行

---

## 执行节奏

### 选项 A · 单会话串行（推荐给 O 会话）

按重要性分 3 波：

**波 1 · 核心 2 份（最不可失真 · 先写）**
1. `hard-redlines.md`（600 分钟工作量 · 最复杂）
2. `dod-specs/general-dod.md`（500 分钟）

**波 2 · 依赖 3 份（依赖波 1 的 DoD 基线）**
3. `dod-specs/stage-dod.md`
4. `dod-specs/wp-dod.md`
5. `soft-drift-patterns.md`

**波 3 · 外围 5 份（相对独立 · 可并行 subagent）**
6. `L0/overview.md`
7. `quality-standards/coding-standards.md`
8. `monitoring-metrics/system-metrics.md`
9. `monitoring-metrics/quality-metrics.md`
10. `acceptance-criteria.md`

**预计耗时**：单会话 3-5 小时

### 选项 B · 2 会话并行（若 O 时间紧）

- O1：核心 5 份（波 1 + 波 2）
- O2：外围 5 份（波 3）

---

## 每份写作 6 步

1. **Read** `docs/2-prd/L0/scope.md` 对应章节（如 §8.5 硬红线）
2. **Read** `docs/2-prd/L1-NN/prd.md` 相关章节
3. **Read** 消费方 3-1 架构（如 L1-04/L1-07 architecture）
4. **Write** 整份（按本 prompt 清单 · 一次性）
5. **Bash 验证**：
   ```bash
   fp="docs/3-3-Monitoring-Controlling/xxx.md"
   echo "行=$(wc -l < "$fp") · §=$(grep -c '^## §' "$fp") · FILL=$(grep -c '<!-- FILL' "$fp") · @UML=$(grep -c '^@startuml' "$fp")/$(grep -c '^@enduml' "$fp") · Mermaid=$(grep -c '```mermaid' "$fp")"
   ```
6. **Commit 独立**：
   ```bash
   git add docs/3-3-Monitoring-Controlling/xxx.md
   git commit -m "feat(harnessFlow): R6.N-O · 3-3/xxx.md depth-B"
   ```

---

## 硬约束（禁区红线）

- ❌ **不改 3-1 任何文件** · 3-1 是 3-3 的上游
- ❌ **不改 2-prd** · 只读源
- ❌ **不改 3-2 TDD** · 独立层
- ❌ **不改 integration/** · 契约已锁
- ❌ **不改 scripts/quality_gate.sh**
- ❌ **禁 Mermaid**（用 PlantUML 或 ASCII 图）
- ❌ **硬红线规约不得失真**（5 类必齐 · 不可增删 · 仅可深化细节）

### 命名规范

- §X.Y 反向映射必带完整路径：
  ```
  docs/2-prd/L0/scope.md §8.5.1
  docs/2-prd/L1-07 Harness监督/prd.md §X.Y
  docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-02-DoD 表达式编译器.md §3
  ```
- 规约 ID 命名：
  - 硬红线 `HRL-01 ~ HRL-05`
  - 软漂移 `SDP-01 ~ SDP-08`
  - DoD `DOD-<层级>-<编号>`（如 DOD-STAGE-S2 · DOD-WP-TDD · DOD-GENERAL-01）

---

## 最终验收

```bash
# 1. 自检 10 份
python3 <<'PYEOF'
import os, re
base = "docs/3-3-Monitoring-Controlling"
for root, _, fs in os.walk(base):
    for fn in sorted(fs):
        if not fn.endswith(".md"): continue
        fp = os.path.join(root, fn)
        with open(fp, encoding="utf-8") as f: c = f.read()
        lines = c.count("\n")+1
        fill = c.count("<!-- FILL")
        secs = len(re.findall(r"^## §\d", c, re.M))
        mermaid = c.count("```mermaid")
        paired = len(re.findall(r"^@startuml", c, re.M)) == len(re.findall(r"^@enduml", c, re.M))
        status = "✓" if (fill == 0 and lines >= 400 and mermaid == 0 and paired) else "✗"
        print(f"{status} {fp.replace(base+'/','')}: lines={lines} §={secs} FILL={fill} Mer={mermaid}")
PYEOF

# 2. Gate 全绿
./scripts/quality_gate.sh

# 3. push
git push origin main
```

完成后回主会话：**10 份全部 depth-B · commit SHA 列表 · 总行数 · hard-redlines 5 类清单齐 · DoD 3 层齐**。

---

## 开工前检查

```bash
git pull origin main
git status                                                   # 应干净
ls docs/3-3-Monitoring-Controlling/                          # 10 份骨架在（commit 7d69edc 已建）
wc -l docs/3-3-Monitoring-Controlling/*.md docs/3-3-Monitoring-Controlling/*/*.md  # 当前每份 63 行骨架

# 必读源就位
wc -l docs/2-prd/L0/scope.md                                 # ≈ 1100+ 行
wc -l "docs/3-1-Solution-Technical/L1集成/architecture.md"    # 1377 行
```

准备好后从 **hard-redlines.md**（5 类硬红线 · 不可失真 · 最难也最核心）开始。

---

## 🎯 完工即 M6 里程碑达成

3-3 完工后：
- 3-1 + 3-2 + 3-3 三层全齐
- **可交付状态达成**
- 下一步：M6.1 端到端验收 · M6.2 交付包打包

---

## 参考先例

- G 会话 L1-01/L2-02 TDD 标杆：`docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-02-决策引擎-tests.md`
- L1集成 架构标杆：`docs/3-1-Solution-Technical/L1集成/architecture.md`
- 跨 L1 治理 memo：`docs/superpowers/reviews/2026-04-22-cross-L1-consistency-memo.md`
