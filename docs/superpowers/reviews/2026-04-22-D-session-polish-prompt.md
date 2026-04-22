# 【D 会话微调任务】L1-03 × 5 · §13 反向 prd 路径统一化

## 审查结论（主会话）

D 会话 5 份 L1-03 整体质量 **9.5/10 优秀**：

| 维度 | 状态 |
|:---|:---:|
| 14 段齐（§0-§13）| ✅ 5/5 |
| FILL=0 · Mermaid=0 | ✅ 5/5 |
| PlantUML `@startuml/@enduml` 配对 | ✅ 全配对（4-6 对/份 · 合计 25 对） |
| IC-XX 引用密度（100-187）| ✅ 远超要求 ≥ 5 |
| §3 字段级 YAML（7-11 blocks） | ✅ 超要求 ≥ 3 |
| §11 表格行数（22-45）| ✅ 错误码表丰富 |
| §13 TDD 前向路径带 L1 完整目录（无 A 会话坑）| ✅ 5/5（`bad_tdd=0`） |
| 段落结构无重复（无 A 会话 L2-03 坑）| ✅ `dupP=0` |
| TC ID ≥ 15 | ✅ 17-20/份 · 合计 93 |
| 跨 L2 基线一致（错误码命名 / IC / 聚合根 / 状态机）| ✅ 自报告已佐证 |

**发现 1 处系统性小瑕疵需统一**（与 E 会话此前同类问题）。

---

## P2 修复 · §13 反向 prd 使用简写（5 份都有）

### 现状（主会话正则扫描结果）

| 文件 | 完整路径（`docs/2-prd/...`）| 简写（`PRD §` / `2-prd §`）|
|:---|:---:|:---:|
| L2-01 WBS 拆解器 | 1 处 | 1 处 |
| L2-02 拓扑图管理器 | 1 处 | 1 处 |
| L2-03 WP 调度器 | 1 处 | 1 处 |
| L2-04 完成度追踪器 | 1 处 | 1 处 |
| L2-05 失败回退协调器 | 1 处 | 1 处 |

仅 frontmatter 里有 1 处完整路径 · §13 正文大量 `PRD §5.3` / `2-prd §5.3` 简写未带完整 `docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md` 路径前缀。

### 期望（对齐 A 会话 16 份 + L1-02 × 7 + L1-05 × 5 已修复的标准）

所有 `§X.X` / `PRD §X.X` / `2-prd §X.X` 引用改为完整路径：

```
docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md §X.X
```

**为什么要统一**：
1. 跨 57+ 份 L2 文档编辑器直接点击路径跳转
2. 未来 3-2 TDD / 3-3 Monitoring 批量 grep 能可靠找到所有引用
3. E 会话已完成此统一（commit fb05e86）· 主会话 L1-02 × 7 也是完整路径 · D 的 5 份是最后一批简写源

**对比参考**：E 会话修复后每份有 8-28 处完整路径引用，D 当前每份只有 1 处。

---

## 修复操作（每份 30-80 行 diff · 总计约 150-400 行）

### 自动化修复脚本

在项目根跑：

```bash
python3 <<'PYEOF'
import re, os

BASE = "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"
PRD_PATH = "docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md"

def fix_file(fp):
    with open(fp, encoding="utf-8") as f:
        c = f.read()
    # 锁定 §13 区域（从 "## §13" 到文件末或下一个 "## §N"）
    m = re.search(r"(?s)(^## §13\b.*?)(\Z|^## §\d+)", c, re.M)
    if not m:
        return False
    s13_start = m.start(1)
    s13_end = m.end(1)
    body = c[s13_start:s13_end]
    orig = body

    # 规则 1: "PRD §N.M" → "`docs/2-prd/.../prd.md` §N.M"
    body = re.sub(
        r"\bPRD\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PATH}` {m.group(1)}",
        body,
    )
    # 规则 2: "2-prd §N.M" → "`docs/2-prd/.../prd.md` §N.M"
    body = re.sub(
        r"(?<!docs/)\b2-prd\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PATH}` {m.group(1)}",
        body,
    )
    # 规则 3: Markdown 表格第一列孤立 "§N.N.N 描述" → 补前缀
    body = re.sub(
        r"^\|\s*§(\d+(?:\.\d+)+)\s+([^|]+?)\s*\|",
        lambda m: f"| `{PRD_PATH}` §{m.group(1)} {m.group(2).strip()} |",
        body,
        flags=re.M,
    )

    if body == orig:
        return False
    new_c = c[:s13_start] + body + c[s13_end:]
    with open(fp, "w", encoding="utf-8") as f:
        f.write(new_c)
    return True

changed = []
for fn in sorted(os.listdir(BASE)):
    if not (fn.startswith("L2-") and fn.endswith(".md")):
        continue
    fp = os.path.join(BASE, fn)
    if fix_file(fp):
        changed.append(fp)
        print(f"fixed: {fp}")
    else:
        print(f"no-op: {fp}")

print(f"\nchanged: {len(changed)}/5")
PYEOF
```

### 验证

```bash
# 1. 每份 §13 应有 docs/2-prd 完整路径 ≥ 3 次
for f in "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"/L2-*.md; do
    c=$(awk '/^## §13/,/^---$/' "$f" | grep -c "docs/2-prd/L1-03 WBS+WP 拓扑调度/prd.md")
    echo "$(basename "$f"): docs/2-prd 引用=$c（期望 ≥ 3）"
done

# 2. 残留简写应降为极少（只允许表格 ID 列里的 "P1" / "N1" / "I1" 之类场景编号 · 非路径引用）
for f in "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"/L2-*.md; do
    remain=$(awk '/^## §13/,/^---$/' "$f" | grep -cE '\bPRD\s+§|(^| )2-prd\s+§')
    echo "$(basename "$f"): 残留简写=$remain（期望 0）"
done

# 3. 全局 Gate 全绿
./scripts/quality_gate.sh

# 4. 本批 5 份结构完整性复查（§数 / FILL / 路径 bug）
python3 <<'PYEOF'
import os, re
base = "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"
for f in sorted(os.listdir(base)):
    if not (f.startswith("L2-") and f.endswith(".md")): continue
    fp = os.path.join(base, f)
    with open(fp, encoding="utf-8") as fh: c = fh.read()
    secs = len(re.findall(r"^## §\d", c, re.M))
    fill = c.count("<!-- FILL")
    bad_tdd = "docs/3-2-Solution-TDD/L1/L2-" in c
    paired = len(re.findall(r"^@startuml", c, re.M)) == len(re.findall(r"^@enduml", c, re.M))
    status = "✓" if (secs == 14 and fill == 0 and not bad_tdd and paired) else "✗"
    print(f"{status} {f}: §={secs} FILL={fill} badTDD={bad_tdd} paired={paired}")
PYEOF
```

### 人工审核（脚本可能漏改的角落）

脚本只处理常见模式。请人工 Read 每份 §13 确认以下边界情况：

1. **表格 ID 列里的场景编号**（例如 `| P1 | 正向... |` / `| N1 | 负向... |` / `| I1 | 集成... |`）**不要改**——这是 PRD §X.9 G-W-T 八场景的场景 ID · 非 prd 章节路径
2. **Markdown 表格多列引用**：如果第一列改了，第二列若是"本文档内部 §引用"（如 `§6.4`）**不要改**
3. **本文档内部引用**（如"本 L2 §5.1"）**保留原样**——这些指向本文档自身段落 · 不是跨文档路径
4. **已正确的路径**（`docs/2-prd/...` 前缀）**不要重复加前缀**

### Commit

```bash
git add "docs/3-1-Solution-Technical/L1-03-WBS+WP 拓扑调度"/L2-*.md
git commit -m "fix(harnessFlow): L1-03 × 5 · §13 反向 prd 路径统一为完整 docs/2-prd/.../prd.md 格式"
git push
```

完成后回主会话：5 份 §13 路径已统一 + commit SHA。

---

## 非修任务（记录存档 · 无需修）

所有其他维度**全部达标**，包括：

- ✅ §11 表格组织方式（分级表格 + 细化表格混用 · L2-02/05 的 22/45 行已足够）
- ✅ §7 PM-14 分片（L2-03 的 4 处已达标 · 虽比其他偏少）
- ✅ 错误码命名 `E_L103_L20N_NNN` 5 份跨文件统一（自报告已佐证）
- ✅ IC 契约命名（IC-L2-01~08 8 条跨 L2 一致）
- ✅ 六状态机 `LEGAL_TRANSITIONS` 在 L2-02 §8 单点定义（单一事实源）
- ✅ TC 命名 `TC-L103-L20N-{P/N/I/B}NN` 5 份统一
- ✅ ADR / OQ 命名统一

**OQ-L103-L202-01 / L205-0X / L201-0X** 三条上送已记录到 §13.3（正确归档）· 无需本次处理 · R5 TDD 阶段追踪。

---

## 禁区

- **不要改 §1-§12 任何内容**（都已通过审查）
- **不要改 §13 里本文档内部引用**（`§6.4` / `§11.3` 指向本文档自身段落 · 不是跨文档路径）
- **不要改 `docs/3-2-Solution-TDD/...` 前向路径**（已正确）
- **不要改表格 ID 列的场景编号**（P1/N1/I1 等 · 不是路径）
- **不要碰 `integration/`** / **`scripts/`** / 其他 L1 目录

---

## 耗时估计

脚本跑 30 秒 · 人工审核 5 份 × 5 分钟 = 25 分钟 · commit + push 5 分钟 · **总计 ≤ 45 分钟**。

---

## 参考先例

- E 会话此类修复 commit `fb05e86` · 方法完全一致
- 主会话审查报告 E 会话：`docs/superpowers/reviews/2026-04-22-E-session-polish-prompt.md`
- 修复后跨 57+ 份 L2 文档路径风格全统一 · **D 是最后一批简写源**
