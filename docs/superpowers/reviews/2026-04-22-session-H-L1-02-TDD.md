# 【并发会话 H】3-2 TDD · L1-02 项目生命周期编排 × 7 份填充

## 背景

harnessFlow 3-2-Solution-TDD 镜像 3-1 给每个 L2 写 TDD 用例。
**G 会话已完成**：L1-01 × 6 + L1-04 × 7 共 13 份 depth-B 标杆（约 9000 行）。
**你（H 会话）负责**：L1-02 项目生命周期编排 × 7 份 TDD 用例（当前全是 70 行骨架）。

其他会话并发做 L1-03/05/06/07/08/09/10，彼此不冲突。

---

## 任务文件（只动 L1-02 目录）

```
docs/3-2-Solution-TDD/L1-02-项目生命周期编排/
├── L2-01-Stage Gate 控制器-tests.md              （1133 行 3-1 源 · 14 错误码）
├── L2-02-启动阶段产出器-tests.md                  （1227 行 3-1 源 · 15 错误码）
├── L2-03-4 件套生产器-tests.md                    （894 行 3-1 源 · 13 错误码）
├── L2-04-PMP 9 计划生产器-tests.md                （1273 行 3-1 源 · 16 错误码）
├── L2-05-TOGAF ADM 架构生产器-tests.md            （1173 行 3-1 源 · 15 错误码）
├── L2-06-收尾阶段执行器-tests.md                  （810 行 3-1 源 · 15 错误码）
└── L2-07-产出物模板引擎-tests.md                  （888 行 3-1 源 · 14 错误码）
```

---

## 必读参考（每份都要读）

1. **3-1 接口源**（主）：`docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-0X-XXX.md`（读 §3 接口 + §11 错误码 + §13 TC ID 矩阵）
2. **prd 负向用例**：`docs/2-prd/L1-02项目生命周期编排/prd.md`（搜对应 L2 + "GWT" / "验证大纲" / "场景"）
3. **G 会话标杆**：`docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-02-决策引擎-tests.md`（1357 行 · 68 test · 69 TC · 学风格）
4. **G 会话标杆（L1-04）**：`docs/3-2-Solution-TDD/L1-04-Quality Loop/L2-01-TDD 蓝图生成器-tests.md`（学同风格）
5. **整体规划**：`docs/superpowers/reviews/2026-04-22-M5-TDD-parallel-plan.md`（质量标杆 + 禁区 + 10 段模板）
6. **契约**：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（查 IC-01 · IC-16 · IC-19 · IC-09 · IC-17 等 L1-02 涉及）

---

## 硬必填（每份 500-1200 行）

遵循**总览 md 的 10 段模板** + 5 会话通用质量标杆：

| 段 | 硬要求 |
|:---|:---|
| §1 覆盖度索引 | 表格：方法 × TC ID × 覆盖类型 · ≥ 30 行 |
| §2 正向用例 | 每 public 方法 ≥ 1 · ≥ 80 行 pytest 代码 |
| §3 负向用例 | 每错误码 ≥ 1 · 覆盖 §11 全部 · ≥ 100 行 |
| §4 IC-XX 契约集成测试 | ≥ 3 个 · 覆盖 §4 依赖 · ≥ 50 行 |
| §5 性能 SLO 用例 | 基于 §12 SLO · ≥ 3 个 · ≥ 30 行 |
| §6 端到端 e2e | 映射 §5 P0 时序 · 2-3 个 · ≥ 50 行 |
| §7 fixture | ≥ 5 个 pytest fixture · ≥ 20 行 |
| §8 集成点用例 | 与兄弟 L2 协作 · ≥ 2 个 · ≥ 20 行 |
| §9 边界 / edge case | 空/超大/并发/崩溃 · ≥ 4 个 · ≥ 30 行 |

**TC ID 命名**（本 L1 专用）：`TC-L102-L20N-<类型>-NNN`（类型可省 · 如 `TC-L102-L201-001` 或 `TC-L102-L201-HAPPY-001`）

---

## L2 定位速查（§2 正向用例 + §3 负向用例的覆盖重点）

### L2-01 Stage Gate 控制器
- **3-1 §3 方法**：`request_gate_decision` / `authorize_transition` / `assemble_evidence` / `emit_rejection_analysis` / `rollback_gate`
- **3-1 §11 错误码 14 条**：`E_L102_L201_001~014`（GATE_EVIDENCE_MISSING / TRANSITION_FORBIDDEN / CIRCULAR_DEP / STATE_CORRUPT / EVIDENCE_EXPIRED / PM14_OWNERSHIP_VIOLATION 等）
- **关键 IC**：IC-01 主状态机 · IC-06 硬红线 · IC-09 审计 · IC-16 Gate 证据
- **重点场景**：S2 Planning Gate pass/reject/need_input · S3 TDD Gate DAG 环检测 · rollback 24h 硬限

### L2-02 启动阶段产出器
- **3-1 §3 方法**：`produce_kickoff` / `activate_project_id` / `atomic_write_chart` / `compute_anchor_hash` / `recover_draft`
- **3-1 §11 错误码 15 条**：`E_L102_L202_001~015`（PID_DUPLICATE / USER_NOT_CONFIRMED / TEMPLATE_INVALID / CHART_ALREADY_EXISTS / ANCHOR_HASH_MISMATCH 等）
- **PM-14**：本 L2 是 project_id 生成唯一入口
- **关键场景**：S1 Kickoff 创建 pid → 落盘 2 章程 → 4 事件 → 激活

### L2-03 4 件套生产器
- **3-1 §3 方法**：`produce_scope` / `produce_prd` / `produce_plan` / `produce_tdd` / `assemble_four_set`
- **3-1 §11 错误码 13 条**：`E_L102_L203_001~013`（UPSTREAM_MISSING / TEMPLATE_INVALID / TRACEABILITY_BROKEN / CROSS_REF_DEAD 等）
- **关键场景**：4 件套串行产出 · 上游缺失回退 · Gate reject 局部重做

### L2-04 PMP 9 计划生产器
- **3-1 §3 方法**：`produce_all_9` / `rework_plans` / `cross_check_togaf_alignment` / `compute_pmp_bundle_hash`
- **3-1 §11 错误码 16 条**：`E_L102_L204_001~016`（CORE_PLAN_FAILED / TOO_MANY_FAILURES / TOGAF_ALIGNMENT_MISMATCH / UNKNOWN_KDA_NAME 等）
- **关键场景**：9 并行产出 · 核心 kda 失败整批 reject · PARTIAL 模式 · rework 保留 8 只重做 1

### L2-05 TOGAF ADM 架构生产器
- **3-1 §3 方法**：`produce_togaf` / `produce_phase` / `cross_check_togaf_alignment` / `rework_phase` / `emit_togaf_d_ready`
- **3-1 §11 错误码 15 条**：`E_L102_L205_001~015`（PHASE_ORDER_VIOLATION / CHARTER_HASH_MISMATCH / ARCHITECTURE_REVIEWER_TIMEOUT 等）
- **关键场景**：STANDARD 档 A-D · HEAVY 档 9 Phase · Phase D 完成即发 IC-L2-06 togaf_d_ready 解 PMP Group 2 阻塞 · Phase C reviewer 降级

### L2-06 收尾阶段执行器
- **3-1 §3 方法**：`produce_closing` / `archive_project` / `purge_project` / `restore_archive`
- **3-1 §11 错误码 15 条**：`E_L102_L206_001~015`（S5_GATE_NOT_PASSED / ARCHIVE_HASH_MISMATCH / ARCHIVE_TOO_LARGE / PURGE_TOO_SOON / PURGE_CONFIRM_MISMATCH 等）
- **PM-14**：本 L2 是 project_id 归档 + 删除唯一入口
- **关键场景**：S6 Closing 3 md + S7 Archive tar.zst · resume 续做 · 90 天后 purge 双重确认

### L2-07 产出物模板引擎
- **3-1 §3 方法**：`render_template` / `list_available_templates` / `validate_slots`
- **3-1 §11 错误码 14 条**：`E_L102_L207_001~014`（TEMPLATE_NOT_FOUND / SLOT_SCHEMA_VIOLATION / TEMPLATE_CODE_EXEC / RENDER_TIMEOUT 等）
- **关键**：无状态 Domain Service · Jinja2 SandboxedEnvironment · 被 L2-02/03/04/05/06 调
- **关键场景**：27 个已注册 kind · sandbox 拦截 · slot schema 校验 · 幂等性

---

## 执行节奏（每份 tests.md · 6 步）

1. **Read 3-1 对应 L2**（§3 + §11 + §13 · 3 次 Read · 并行 · limit=200）
2. **Read prd 对应小节**（§12.N.Y · 1 次 Read）
3. **Read G 标杆** `L1-01/L2-02-决策引擎-tests.md` 前 200 行（看 fixture + §2 模板 · 1 次 Read）
4. **Write 整份 tests.md**（一次性 · 500-1200 行 · 不分批）
5. **Bash 验证**：
   ```bash
   fp="docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-0X-XXX-tests.md"
   echo "行=$(wc -l < "$fp") · §=$(grep -c '^## §' "$fp") · FILL=$(grep -c '<!-- FILL' "$fp") · test=$(grep -cE '\bdef test_' "$fp") · TC=$(grep -cE 'TC-L\d+-L\d+' "$fp")"
   ```
6. **Commit**（每份独立 · 不 bundle）：
   ```bash
   git add "docs/3-2-Solution-TDD/L1-02-项目生命周期编排/L2-0X-XXX-tests.md"
   git commit -m "feat(harnessFlow): R5.4-H · L1-02/L2-0X XXX tests 用例 depth-B"
   ```

---

## 推进顺序建议

**L2-07（地基·无状态）→ L2-02（PM-14 起点）→ L2-03（4 件套）→ L2-04（PMP）→ L2-05（TOGAF）→ L2-01（Gate 控制器）→ L2-06（收尾）**

理由：L2-07 模板引擎是所有 L2 的被调方 · L2-02 是 PM-14 起点 · L2-01 是 Gate 控制器依赖其他 L2 · L2-06 收尾需前置全齐。

---

## 最终验收

```bash
# 1. 自检 7 份
python3 <<'PYEOF'
import os, re
base = "docs/3-2-Solution-TDD/L1-02-项目生命周期编排"
for fn in sorted(os.listdir(base)):
    if not fn.endswith(".md"): continue
    fp = os.path.join(base, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    lines = c.count(chr(10))+1
    fill = c.count("<!-- FILL")
    secs = len(re.findall(r"^## §\d", c, re.M))
    tc = len(set(re.findall(r"TC-L\d+-L\d+-\w+|TC-[A-Z]+-[A-Z]+-\d+", c)))
    tests = len(re.findall(r"\bdef test_", c))
    status = "✓" if (fill == 0 and secs >= 10 and tc >= 15 and tests >= 15) else "✗"
    print(f"{status} {fn}: lines={lines} §={secs} FILL={fill} TC={tc} test_fn={tests}")
PYEOF

# 2. Gate
./scripts/quality_gate.sh

# 3. push
git push origin main
```

完成后回主会话：**7 份全部 depth-B 完成 · commit SHA 列表 · 总行数**。

---

## 禁区

- **不要改 3-1 任何文件** · 只读
- 不碰 L1-03/05/06/07/08/09/10 的 tests 目录
- 不碰 3-2 的 integration/ 和 acceptance/
- 不碰 scripts/quality_gate.sh

---

## 开工前检查

```bash
git pull origin main
git status                                                  # 应干净
ls "docs/3-2-Solution-TDD/L1-02-项目生命周期编排/"           # 确认 7 份骨架在
wc -l "docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-02-决策引擎-tests.md"  # 1357 行 · G 标杆
```

准备好后从 **L2-07 产出物模板引擎** 开始。
