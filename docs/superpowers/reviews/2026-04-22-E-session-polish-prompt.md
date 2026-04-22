# 【E 会话微调任务】L1-05 × 5 · §13 反向 prd 路径统一化

> ## ✅ **已完成 · 2026-04-22**
>
> - 5 份 L1-05 × L2 全部 depth-B 交付（commits：6a2d570 / b0b8067 / e5d224b / d1164be / 4cd938e）
> - P2 微调完成（commit fb05e86）· §13 反向 prd 路径 5 份统一为完整 `docs/2-prd/...prd.md` 格式
> - Quality Gate 全绿 · 总计 ~7737 行 · 平均每份 1500+ 行 · IC-XX 引用 500+ 处
> - 对齐跨 55+ 份 L2 文档路径风格

## 审查结论（主会话）

E 会话完工 5 份 · 整体质量 **9/10 · 优秀**：

| 维度 | 状态 |
|:---|:---:|
| 14 段齐（§0-§13）| ✅ 5/5 |
| FILL=0 · Mermaid=0 · TDD 路径带 L1 编号 | ✅ 5/5 |
| PlantUML @startuml/@enduml 配对 | ✅ 全配对（4-6 对/份） |
| IC-XX 引用密度（66-162）| ✅ 远超要求 ≥ 5 |
| §3 字段级 YAML（4-7 blocks） | ✅ 超要求 ≥ 3 |
| §11 错误码 ≥ 12 条 | ✅ L2-01: 12 · L2-02: 14 分级 · L2-03: 37 · L2-04: 16 · L2-05: 14 分级 |
| §13 TDD 前向路径带 L1 完整目录（无 A 会话坑）| ✅ 5/5 |
| 段落结构无重复（无 A 会话 L2-03 坑）| ✅ 5/5 |

**发现 1 处系统性小瑕疵需统一**。

---

## P2 修复 · §13 反向 prd 使用简写（5 份都有）

### 现状

你在 §13 的反向映射表里用了简写形式：

| 文件 | 现状示例 |
|:---|:---|
| L2-01 §13 | `PRD §8.7` · `§8 硬约束 B2` |
| L2-02 §13 | `2-prd §9 L2-02` · `§9.9 P1` |
| L2-03 §13 | `PRD §10.x` · `§10.9 P1` |
| L2-04 §13 | `§5.5.1 职责定义` · `§5.5.2 隔离要求` |
| L2-05 §13 | `2-prd §12 L2-05 对应章节` |

### 期望（对齐 A 会话 + 主会话 + L1-01/04/06/07/08/10 标准）

所有 `§X.X` / `PRD §X.X` / `2-prd §X.X` 引用改为完整路径：

```
docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md §X.X
```

**为什么要统一**：跨 55+ 份 L2 文档在编辑器中可直接点击路径跳转；未来 3-2 TDD / 3-3 Monitoring 批量 grep 时能可靠找到所有引用。

---

## 修复操作（每份 30-80 行 diff · 总计约 150-300 行）

### 自动化修复脚本

在项目根跑：

```bash
python3 <<'PYEOF'
import re, os

BASE = "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度"
PRD_PREFIX = "docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md"

def fix_file(fp):
    with open(fp, encoding="utf-8") as f:
        c = f.read()
    # 只修 §13 区域
    m = re.search(r"(?s)(^## §13\b.*?)(\Z|^## §\d+)", c, re.M)
    if not m:
        return False
    s13_start = m.start(1)
    s13_end = m.end(1)
    s13_body = c[s13_start:s13_end]

    orig = s13_body

    # 规则 1: "PRD §N.M" → "docs/2-prd/.../prd.md §N.M"
    s13_body = re.sub(
        r"\bPRD\s+(§\d+(?:\.\d+)*(?:\.\d+)*)",
        lambda m: f"`{PRD_PREFIX}` {m.group(1)}",
        s13_body,
    )
    # 规则 2: "2-prd §N.M" → "docs/2-prd/.../prd.md §N.M"
    s13_body = re.sub(
        r"(?<!docs/)\b2-prd\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PREFIX}` {m.group(1)}",
        s13_body,
    )
    # 规则 3: 表头"§N.N 小节" 开头的单元格保持原样（无需改），但给"§5.5.1 职责定义"之类孤立引用补路径
    #   先找竖线分隔表格里的第一列，形如 "| §5.5.1 xxx |" → "| `docs/.../prd.md` §5.5.1 xxx |"
    #   为安全起见，只修 §13 表格内的特定模式（L2-04 PRD 映射表）
    s13_body = re.sub(
        r"^\|\s*§(\d+(?:\.\d+)+)\s+([^|]+?)\s*\|",
        lambda m: f"| `{PRD_PREFIX}` §{m.group(1)} {m.group(2).strip()} |",
        s13_body,
        flags=re.M,
    )

    if s13_body == orig:
        return False
    new_c = c[:s13_start] + s13_body + c[s13_end:]
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
# 1. 所有 §13 应有 docs/2-prd 完整路径引用
for f in "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度"/L2-*.md; do
    c=$(awk '/^## §13/,/^---$/' "$f" | grep -c "docs/2-prd/L1-05 Skill生态+子Agent调度/prd.md")
    echo "$(basename "$f"): docs/2-prd 引用=$c（期望 ≥ 3）"
done

# 2. 不应留遗漏的"PRD §" 或孤立"2-prd §"
for f in "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度"/L2-*.md; do
    remain=$(awk '/^## §13/,/^---$/' "$f" | grep -cE '\bPRD\s+§|(?<!docs/)\b2-prd\s+§')
    echo "$(basename "$f"): 残留简写=$remain（期望 0 或极少）"
done

# 3. 全局 Gate 全绿
./scripts/quality_gate.sh
```

### 人工审核（脚本可能漏改的角落）

脚本只处理常见模式。请人工 Read 每份 §13 确认以下边界情况：

1. **注释性文字里的"§N.M"**（非映射表）：保留原样不改
2. **Markdown table 多列引用**：例如 L2-04 的"| §5.5.1 职责定义 | §1 + §2 |" 第一列改了就够，第二列"§1 + §2"是本文档内部引用，不要改
3. **路径已正确的不要重复加前缀**：`docs/2-prd/...` 前缀的保持不动

### Commit

```bash
git add "docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度"/L2-*.md
git commit -m "fix(harnessFlow): L1-05 × 5 · §13 反向 prd 路径统一为完整 docs/2-prd/.../prd.md 格式"
git push
```

完成后回主会话：5 份 §13 路径已统一 + commit SHA。

---

## 非修任务（可忽略 · 记录存档）

- **§11 错误码表格式**：L2-02/L2-05 用"级别分组 3 列"· 其他用"errorCode 四列"。两种风格都合规，**无需统一**。
- **§13 结构层次**：5 份各有 5-6 个子节（13.1 ADR / 13.2 OQ / 13.3-13.6 映射）· 深度一致 · 无需动。

---

## 禁区

- **不要改 §1-§12 任何内容**（都已通过审查）
- **不要改 §13 里本文档内部引用**（`§6.4` / `§11.3` 这些指向本文档自身段落 · 不是跨文档路径）
- **不要改 `docs/3-2-Solution-TDD/...` 路径**（已正确）
- **不要碰 integration/** 或 **scripts/**

---

## 耗时估计

脚本跑 30 秒 · 人工审核 5 份 × 5 分钟 = 25 分钟 · commit + push 5 分钟 · **总计 ≤ 45 分钟**。
