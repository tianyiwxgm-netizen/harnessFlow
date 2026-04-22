# 【并发会话 F】3-1/L1-09 韧性+审计 × 4 份 L2（2 修复 + 2 补齐）

> ## ✅ **已完成 · 2026-04-22**
>
> - 交付 4/4 份 depth-B+（7580 行 · 14 段齐 · FILL=0 · Mermaid=0 · 25 PlantUML 配对）
> - 修复策略：L2-02/L2-05 方案 A（段标题缺 §）· L2-03/L2-04 三 subagent 分批补齐 + 主会话接管 §5-§13
> - commits：ad8c7e2（L2-02）/ 4d5f615（L2-03）/ aa9b4d6（L2-04）/ 7565ee7（L2-05）
> - **质量评分：9/10 优秀** · L2-04 TC ID 规范化单独亮眼（`T-RECOVER-HAPPY-001` 风格 · 20 TC）
> - 主会话审查报告 + P1 微调 prompt：`docs/superpowers/reviews/2026-04-22-F-session-polish-prompt.md`
>   - P1-1 §13 反向 prd 完整路径（L2-02/04/05 共 3 份）
>   - P1-2 §13 前向 TDD 路径规范化（L2-02/05 共 2 份）
>   - P1-3 TC ID 命名跨 4 份统一（L2-02/03/05 补标准 TC）
> - 修完即 **M4 里程碑达成** 🎯（3-1 Technical 57/57 完工）

## 背景

harnessFlow 3-1-Solution-Technical 的 L1-09 韧性+审计共 5 份 L2。
- **L2-01 事件总线核心**：已 done（≥ 1000 行 depth-A · 不碰）
- **本会话 F 负责剩 4 份**：
  - **L2-02 锁管理器**：已有 1519 行内容但 `## §N` 结构异常 · 需**诊断+修复**
  - **L2-03 审计记录器+追溯查询**：189 行 · 基本骨架 · 需**填**
  - **L2-04 检查点与恢复器**：131 行骨架 · 需**填**
  - **L2-05 崩溃安全层**：已有 2052 行内容但 `## §N` 结构异常 · 需**诊断+修复**

其他会话并发做 L1-02/03/05，彼此不冲突。

## 任务文件（只动 L1-09 目录）

1. `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md`（**修复结构**）
2. `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-03-审计记录器+追溯查询.md`（**补齐**）
3. `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-04-检查点与恢复器.md`（**补齐**）
4. `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md`（**修复结构**）

## 各 L2 定位

- **L2-02 锁管理器**：BC-09 · project 级别资源锁（文件锁 / 状态锁 / IC-08 跨 L1 分布式锁 / 进程间 advisory lock）
- **L2-03 审计记录器+追溯查询**：IC-09 审计事件的落盘编排（append-only jsonl + rotation + index）+ 按 project/time/actor/type 追溯查询（写端 + 读端）
- **L2-04 检查点与恢复器**：project 级 snapshot（周期性 + 关键事件触发）+ crash 时的恢复回放（replay last-N events）· 对接 L2-05
- **L2-05 崩溃安全层**：WAL（Write-Ahead Log）· atomic write · fsync 调度 · 崩溃检测 + 恢复入口（本 L1 最底层的数据安全保证）

---

## 第 1 步：诊断 L2-02 和 L2-05 的结构问题

看 L2-02 和 L2-05 实际 §标题格式（可能是 `## 1. 定位` 或 `### §1` 或 `## §1.x`）：

```bash
# L2-02 诊断
echo "=== L2-02 ==="
grep -n "^## \|^### §\|^## §" "docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md" | head -40

# L2-05 诊断
echo "=== L2-05 ==="
grep -n "^## \|^### §\|^## §" "docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md" | head -40

# Python 统计
python3 <<'PYEOF'
import re
for fp in ['docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md',
          'docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md']:
    with open(fp, encoding='utf-8') as f: c = f.read()
    print(f'=== {fp.split("/")[-1]} ===')
    print(f'  行数: {c.count(chr(10))+1}')
    print(f'  ## §N 标题数: {len(re.findall(r"^## §\\d+", c, re.M))}')
    print(f'  ## 非 § 标题数: {len(re.findall(r"^## [^§]", c, re.M))}')
    print(f'  ### §标题数: {len(re.findall(r"^### §\\d+", c, re.M))}')
    print(f'  前 3 个 ## 开头行:')
    for m in re.finditer(r'^## .+', c, re.M):
        print(f'    行 {c[:m.start()].count(chr(10))+1}: {m.group()[:80]}')
        if c[:m.start()].count(chr(10)) > 200: break
PYEOF
```

**可能的结构问题类型**：
- **类型 A**：段标题用了 `## 1. 定位` 而非 `## §1 定位`（需给每个 ## N 前加 §）
- **类型 B**：段标题是 `### §N` 三级（需提升到 `## §N` 二级）
- **类型 C**：内容分了 20+ 个大节而非 13 个（需按 §0-§13 框架合并/重组）
- **类型 D**：用的是别的 Unicode 字符假装 §（罕见）

**诊断目标**：识别是哪种类型，然后决定修复策略。

---

## 第 2 步：修复 L2-02 / L2-05

根据诊断结果选修复方案：

### 方案 A（最常见 · 段标题缺 §）

```python
import re
fp = 'docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md'
with open(fp, encoding='utf-8') as f: c = f.read()
# ## N. xxx → ## §N xxx
c2 = re.sub(r'^## (\d+)\. ', r'## §\1 ', c, flags=re.M)
# 验证修后 §数
new_count = len(re.findall(r'^## §\d+', c2, re.M))
assert new_count == 14 or new_count == 13, f"expected 13-14, got {new_count}"
with open(fp, 'w', encoding='utf-8') as f: f.write(c2)
```

### 方案 B（三级 §提二级）

```python
c2 = re.sub(r'^### (§\d+)', r'## \1', c, flags=re.M)
```

### 方案 C（需要合并/重组）

先 `grep -n "^## "` 看所有大节 → 手工 Edit 合并多余的大节到 §0-§13 框架。例如：
- 若有 `## 概述`、`## 介绍`、`## 背景` 三个大节 → 都合并到 `## §1 定位 + 2-prd 映射`
- 若有 `## 实现 A`、`## 实现 B` → 都归到 `## §6 内部核心算法`

**修复后一律验证**：

```bash
grep -c "^## §" "docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-02-锁管理器.md"   # 期望 14
grep -c "^## §" "docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-05-崩溃安全层.md"  # 期望 14
```

若修复后 § 数仍不对（例如有 §0-§15 多出来），需补 Edit 继续合并或拆分。

---

## 第 3 步：补齐 L2-03 + L2-04（精简 B 模板 · 500-800 行/份）

### 必读参考

1. **质量标杆**：`docs/3-1-Solution-Technical/L1-01-主 Agent 决策循环/L2-02-决策引擎.md`
2. **L1-09 同胞**：`docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md`（**直接对齐它的风格** · 同 BC 同 L1）
3. **精简 B 范本**：`docs/3-1-Solution-Technical/L1-08-多模态内容处理/L2-03-图片视觉理解编排器.md`
4. **L1-09 架构**：`docs/3-1-Solution-Technical/L1-09-韧性+审计/architecture.md`
5. **PRD**：`docs/2-prd/L1-09 韧性+审计/prd.md`（路径含空格）
6. **契约**：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（IC-08 锁 / IC-09 审计 / IC-10 健康）

### 各段硬约束

- §3 字段级 YAML ≥ 3 + 错误码 ≥ 8 条四列
- §5 PlantUML ≥ 2 张
- §7 PM-14 分片：
  - L2-03：`projects/<pid>/audit/{events.jsonl|index/*.jsonl|rotations/*}`
  - L2-04：`projects/<pid>/checkpoints/{snapshots/*.tar.zst|manifests/*.yaml|restore-logs/*}`
- §9 ≥ 3 开源对标 Adopt-Learn-Reject：
  - L2-03 审计建议：OpenTelemetry / Grafana Loki / Vector.dev / Fluent Bit / Elastic Beat
  - L2-04 检查点建议：etcd snapshot / Raft snapshot / Redis RDB / PostgreSQL WAL / zfs snapshot
- §11 ≥ 12 错误码 + 4 级降级链（含 PlantUML 降级图）
- §13 反向 prd + 前向 TDD（**必带 L1 完整目录名**：`docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-0N-tests.md`）· ≥ 15 TC ID + 2-3 ADR + 2-3 OQ
- IC-XX ≥ 5 处（L2-03 主要 IC-09 · L2-04 主要 IC-10 + IC-06）

### 执行节奏（每份 L2 · 6 步）

1. **Read 骨架 + 标杆 + L2-01（L1-09 同胞）+ architecture + prd + ic-contracts**（并行 4-5 call）
2. **Edit §1 + §3**（≤ 400 行）
3. **Edit §5 + §11**（≤ 400 行）
4. **Edit §13 + 剩余 8 段 bullet**（≤ 300 行）
5. **Bash 验证**（同 L2-02/05 修复后的校验）
6. **Commit**：
   ```bash
   git add "docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-0N-XXX.md"
   git commit -m "feat(harnessFlow): R4.4-F · L1-09/L2-0N XXX depth-B 完成"
   ```

---

## 硬约束（所有 4 份都适用）

- 图一律 PlantUML · **禁止 Mermaid**
- 所有 `@startuml` 必配 `@enduml`
- 无 `<!-- FILL`、无 `TBD`、无 `TODO`、无 `待填`
- TDD 占位路径**必带 L1 完整目录名**：`docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-0N-tests.md`
- 同一 L2 文件内错误码命名风格保持一致

---

## 推进顺序建议

**L2-02（锁管理器修复）→ L2-05（崩溃安全层修复）→ L2-04（检查点与恢复补齐）→ L2-03（审计记录器+追溯查询补齐）**

理由：先修结构异常的两份（内容已在 · 优先稳定）· 再补骨架（新写需要 context）· L2-04 依赖 L2-05（WAL）· L2-03 最后因为它引用 L2-04/L2-05 已完成态。

---

## 最终验收

```bash
# Gate
./scripts/quality_gate.sh

# 本批 4 份结构校验
python3 <<'PYEOF'
import os, re
files = [
    'L2-02-锁管理器.md',
    'L2-03-审计记录器+追溯查询.md',
    'L2-04-检查点与恢复器.md',
    'L2-05-崩溃安全层.md',
]
for fn in files:
    fp = f'docs/3-1-Solution-Technical/L1-09-韧性+审计/{fn}'
    with open(fp, encoding='utf-8') as f: c = f.read()
    lines = c.count(chr(10))+1
    secs = len(re.findall(r'^## §\d', c, re.M))
    fill = c.count('<!-- FILL')
    bad_tdd = 'docs/3-2-Solution-TDD/L1/L2-' in c
    paired = len(re.findall(r'^@startuml', c, re.M)) == len(re.findall(r'^@enduml', c, re.M))
    status = '✓' if (secs == 14 and fill == 0 and not bad_tdd and paired) else '✗'
    print(f'{status} {fn}: lines={lines} §={secs} FILL={fill} badTDD={bad_tdd} paired={paired}')
PYEOF

git push
```

完成后回主会话：
- 4 份全部结构齐（§=14 · FILL=0）
- commit SHA 列表
- 总行数
- 修复 L2-02/05 时用的策略（A/B/C · 便于主会话记录）

---

## 禁区（不要碰）

- `docs/3-1-Solution-Technical/L1-02/`、`L1-03/`、`L1-05/` —— 其他会话在做
- `docs/3-1-Solution-Technical/L1-09-韧性+审计/L2-01-事件总线核心.md` —— 已 done
- `docs/3-1-Solution-Technical/integration/` —— 契约已锁定
- `docs/3-2-Solution-TDD/` —— G 会话在建
- `scripts/quality_gate.sh` —— 主会话维护
- 任何 `L1-01/04/06/07/08/10` 已完工 L2 —— 只读参考

---

## 开工前检查

```bash
git pull origin main
git status
ls docs/3-1-Solution-Technical/L1-09-韧性+审计/    # 确认 5 份文件在（L2-01 done · 你动剩 4）
```

准备好后先**诊断** L2-02 和 L2-05 的 § 格式，再决定修复策略。
