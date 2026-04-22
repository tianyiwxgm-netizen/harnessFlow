# 【F 会话微调任务】L1-09 × 4 · §13 三项一致性微调

## 审查结论（主会话）

F 会话 4 份交付 · 整体质量 **9/10 优秀**：

| 维度 | 状态 |
|:---|:---:|
| 14 段齐（§0-§13）| ✅ 4/4 · L2-02/05 结构修复已成功 |
| FILL=0 · Mermaid=0 · TBD/TODO=0 | ✅ 4/4 |
| PlantUML @startuml/@enduml 配对 | ✅ 25/25（L2-02 6/6 · L2-03 7/7 · L2-04 7/7 · L2-05 6/6） |
| IC-XX 引用密度（13-106）| ✅ 达标 |
| §11 错误码表（15-47 行）| ✅ 充足 |
| §13 结构丰富度（多子节：GWT/ADR/OQ/向上回写）| ✅ 深度超预期 |
| 段落结构无重复 | ✅ 4/4 |
| L2-04 TC ID 命名规范（`T-RECOVER-HAPPY-001`）| ✅ 单独优秀 |

**3 处需跨 L1 一致性微调**（纯格式统一 · 不动内容）。

---

## P1-1 修复 · §13 反向 prd 路径全部补完整（L2-02/04/05 共 3 份）

### 现状

| 文件 | `docs/2-prd/L1-09` 完整路径引用 | 简写引用 |
|:---|:---:|:---:|
| L2-02 锁管理器 | **0** 处 | "prd §9.9" / "prd §9.5/9.6" · 约 20 处 |
| L2-03 审计记录器 | 1 处（"在 `docs/2-prd/L1-09 韧性+审计/prd.md` 末尾新增"）| 其他处简写 |
| L2-04 检查点与恢复器 | **0** 处（全用 "prd §11.9 场景 X"）| 约 15 处 |
| L2-05 崩溃安全层 | **0** 处（全用 "prd.md §12.9"）| 约 20 处 |

### 期望（对齐 A/D/E 会话 + 主会话 L1-02 × 7 已用标准）

所有 `prd §X.X` / `prd.md §X.X` 引用补齐为完整路径：

```
docs/2-prd/L1-09 韧性+审计/prd.md §X.X
```

注意路径含空格 · 必须与实际目录名**一字不差**。

### 自动化修复脚本

```bash
python3 <<'PYEOF'
import re, os
BASE = "docs/3-1-Solution-Technical/L1-09-韧性+审计"
PRD_PATH = "docs/2-prd/L1-09 韧性+审计/prd.md"

def fix_file(fp):
    with open(fp, encoding="utf-8") as f: c = f.read()
    m = re.search(r"(?s)(^## §13\b.*?)(\Z|^## §\d+)", c, re.M)
    if not m:
        return False
    s13_start = m.start(1)
    s13_end = m.end(1)
    body = c[s13_start:s13_end]
    orig = body

    # 规则 1: "prd.md §N.M" → "`docs/2-prd/L1-09 韧性+审计/prd.md` §N.M"
    #   - 防止匹配到已正确路径里的 prd.md · 用 (?<!/) 负向后顾
    body = re.sub(
        r"(?<!/)(?<!`)\bprd\.md\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PATH}` {m.group(1)}",
        body,
    )
    # 规则 2: "prd §N.M" → "`docs/2-prd/L1-09 韧性+审计/prd.md` §N.M"
    #   - 必须在单词边界 · 且前面不是 "/" 或 "-"（避免 "docs/prd §" / "2-prd §" 重复加前缀）
    body = re.sub(
        r"(?<![/-])(?<!`)\bprd\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PATH}` {m.group(1)}",
        body,
    )
    # 规则 3: "2-prd §N.M"（如果还有） → 同上
    body = re.sub(
        r"(?<!docs/)\b2-prd\s+(§\d+(?:\.\d+)*)",
        lambda m: f"`{PRD_PATH}` {m.group(1)}",
        body,
    )

    if body == orig:
        return False
    new_c = c[:s13_start] + body + c[s13_end:]
    with open(fp, "w", encoding="utf-8") as f: f.write(new_c)
    return True

changed = []
for fn in sorted(os.listdir(BASE)):
    if not fn.startswith("L2-0") or not fn.endswith(".md"): continue
    fp = os.path.join(BASE, fn)
    if fix_file(fp):
        changed.append(fn)
        print(f"fixed: {fn}")
    else:
        print(f"no-op: {fn}")
print(f"\nchanged: {len(changed)}/5")
PYEOF
```

### 人工审核（脚本可能漏改/误改的角落）

1. **本文档内部 §引用**（如"本 L2 §5.1"、"§11.5 硬 halt"）**不要改** · 脚本已用 `prd` 前缀隔离
2. **Goal.md / scope.md 引用**（如"Goal §4.1"、"scope §5.9.4"）**不要改** · 非 prd.md
3. **architecture.md §引用**（如"architecture §7"）**不要改** · 非 prd.md
4. **已正确的路径保持**：`docs/2-prd/L1-09 韧性+审计/prd.md §X.X`（反复加前缀会破坏）

---

## P1-2 修复 · §13 前向 TDD 路径规范化（L2-02/05 共 2 份）

### 现状

| 文件 | §13 前向路径风格 |
|:---|:---|
| L2-02 | `tests/l1_09/l2_02/test_acquire_no_contention.py`（Python 代码路径）|
| L2-03 | `docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-03-tests.md` ✓ |
| L2-04 | `docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-04-tests.md` ✓ |
| L2-05 | `tests/l1_09/l2_05/test_append_happy_path.py`（Python 代码路径）|

### 期望（对齐其他 L1 / L2-03 / L2-04）

`§13` 应列 **3-2 TDD 文档路径**（md 规格 · 用例集），不是 **Python 代码路径**（pytest 文件）。

**两者并存是 OK 的**（代码路径是 TDD 实施层 · 文档路径是规格层），但至少要有 **一句话**明确指向 3-2 TDD 规格文档。

### 修复操作（L2-02）

在 L2-02 `§13.1 prd §9.9 GWT 场景 → 本文档章节 → 3-2 用例` 表格**上方**加一段：

```markdown
> **3-2 TDD 规格文件**：`docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-02-锁管理器-tests.md`（待建 · 本文档所有 GWT 场景 + §11 错误码 + §12 SLO 的用例清单）
>
> 下表的 `tests/l1_09/l2_02/*.py` 是 TDD 实施层 pytest 文件路径 · 在 3-2 TDD 规格文件中按 TC ID 组织。
```

在 L2-05 `§13.1 prd.md §12.9 交付验证大纲 → 3-2 TDD 测试文件` 表格**上方**加类似段：

```markdown
> **3-2 TDD 规格文件**：`docs/3-2-Solution-TDD/L1-09-韧性+审计/L2-05-崩溃安全层-tests.md`（待建 · 本文档 7 场景 + §11 错误码 + §12 SLO 的用例清单）
>
> 下表 `tests/l1_09/l2_05/*.py` 是 TDD 实施层 pytest 文件路径 · 在 3-2 TDD 规格文件中按 TC ID 组织。
```

**手工 Edit 即可**（每份加 ~3 行 · 不脚本化）。

---

## P1-3 修复 · TC ID 命名跨 4 份统一（L2-02/03/05 共 3 份）

### 现状

| 文件 | TC 命名风格 |
|:---|:---|
| L2-02 锁管理器 | **无 TC ID** · 只用文件名 `test_acquire_no_contention.py` 作为场景标识 |
| L2-03 审计记录器 | **无标准 TC ID**（主会话 grep 未匹配）|
| L2-04 检查点与恢复器 | **`T-RECOVER-HAPPY-001` / `T-RECOVER-CORRUPT-001`** 等（规范 · 5 类 × ≥3 个 = 20 TC）✓ |
| L2-05 崩溃安全层 | **无 TC ID** · 只用文件名 |

### 期望（跨 L1 统一 · 对齐 L1-01/02/03/05 标准）

全局 TC 命名规范：**`TC-L109-L20N-NNN`** 或保留 L2-04 的 **`T-RECOVER-<CATEGORY>-NNN`** 风格（L1-09 底层组件特殊域）。

**推荐方案**：两套并存（允许 L1-09 底层组件用语义化分类命名），但**每份 L2 必须至少有一套标准 TC ID**（方便 3-2 TDD 反向定位）。

### 修复操作

**L2-02 锁管理器**（在 §13.1 表格前加一列 TC ID · 或在 §13.5 3-2 任务清单里加 TC 编号）：

```markdown
建议每条 3-2 任务加 TC ID（L1-09 底层组件 · 参考 L2-04 语义化风格）：

| TC ID | 3-2 Task |
|:---|:---|
| TC-LOCK-HAPPY-001 | `test_acquire_no_contention.py` |
| TC-LOCK-HAPPY-002 | `test_release_idempotent.py` |
| TC-LOCK-VALIDATION-001 | `test_resource_validation.py` |
| TC-LOCK-FIFO-001 | `test_fifo_10_contenders.py` |
| TC-LOCK-TIMEOUT-001 | `test_timeout.py` |
| TC-LOCK-DEADLOCK-001 | `test_deadlock_detect.py` |
| TC-LOCK-SHUTDOWN-001 | `test_shutdown.py` |
| TC-LOCK-JANITOR-001 | `test_janitor_ttl.py` |
| TC-LOCK-FSERR-001 | `test_fs_error.py` |
| TC-LOCK-BENCH-001 | `bench_acquire_release.py` |
| TC-LOCK-BENCH-002 | `bench_10_contenders.py` |
| TC-LOCK-BENCH-003 | `bench_20_starvation.py` |
```

**L2-03 审计记录器**：为每个 GWT 场景 + 每个错误码加 TC ID · 命名 `TC-AUDIT-<CATEGORY>-NNN`。

**L2-05 崩溃安全层**：在 §13.1 的 7 场景表格**新增一列 TC ID** · 命名 `TC-CRASH-HAPPY-001` / `TC-CRASH-CORRUPT-001` / `TC-CRASH-DISK-001` 等。

示例修改：

```markdown
| # | TC ID | prd 场景 | 测试用例文件（3-2 路径）| ...
|---|---|---|---|
| 1 | TC-CRASH-HAPPY-001 | 原子追加正常 | `tests/l1_09/l2_05/test_append_happy_path.py` | ...
| 2 | TC-CRASH-CORRUPT-001 | 中断不坏数据 | `tests/l1_09/l2_05/test_crash_safety_simulation.py` | ...
| 3 | TC-CRASH-DISK-001 | 磁盘满触发硬 halt | ...
| 4 | TC-CRASH-HASH-001 | hash 链断裂检测 | ...
| 5 | TC-CRASH-HEADER-001 | checkpoint header 损坏 | ...
| 6 | TC-CRASH-SHUTDOWN-001 | shutdown 末自检 | ...
| 7 | TC-CRASH-PERF-001 | 一万事件校验延迟 | ...
```

**总计新增 TC ID 数**：
- L2-02 ~12 条
- L2-03 ~15 条（按现有表格规模）
- L2-05 ~7 条（7 场景对应）

### 命名风格选择

**推荐** L2-04 的语义化风格（`T-<DOMAIN>-<CATEGORY>-NNN`）· 理由：
- L1-09 是底层组件 · 按功能域分类（LOCK / AUDIT / RECOVER / CRASH）更直观
- 与 L2-04 的 `T-RECOVER-XXX` 对齐 · 跨 4 份一致
- 3-2 TDD 反向定位时按功能域 grep 更高效

**次选**：数字化统一 `TC-L109-L20N-NNN` · 与其他 L1 对齐更死板。

两种都可 · 重点是**同一 L2 内用一套命名**。

---

## 验证

修完 3 项后：

```bash
# 1. §13 反向 prd 完整路径检查
for f in "docs/3-1-Solution-Technical/L1-09-韧性+审计"/L2-0{2,3,4,5}*.md; do
    full=$(awk '/^## §13/,0' "$f" | grep -c "docs/2-prd/L1-09 韧性+审计/prd.md")
    short=$(awk '/^## §13/,0' "$f" | grep -cE '(?<!/)(?<!`)\bprd(\.md)?\s+§')
    echo "$(basename "$f"): 完整路径=$full · 残留简写=$short"
done

# 2. 3-2 TDD 路径检查（每份 §13 至少 1 处 docs/3-2-Solution-TDD/L1-09）
for f in "docs/3-1-Solution-Technical/L1-09-韧性+审计"/L2-0{2,3,4,5}*.md; do
    tdd=$(awk '/^## §13/,0' "$f" | grep -c "docs/3-2-Solution-TDD/L1-09-韧性+审计")
    echo "$(basename "$f"): 3-2 TDD 文档路径=$tdd（期望 ≥ 1）"
done

# 3. TC ID 统计
python3 <<'PYEOF'
import os, re
base = "docs/3-1-Solution-Technical/L1-09-韧性+审计"
for fn in sorted(os.listdir(base)):
    if not fn.startswith("L2-0") or not fn.endswith(".md"): continue
    fp = os.path.join(base, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    tc_std = len(set(re.findall(r"TC-L\d+-L\d+-\d+", c)))
    tc_sem = len(set(re.findall(r"T[C]?-[A-Z]+-[A-Z]+-\d{3}", c)))
    print(f"{fn}: 标准 TC={tc_std} · 语义 TC={tc_sem}（合计 ≥ 10 达标）")
PYEOF

# 4. 全局 Gate
./scripts/quality_gate.sh

# 5. 4 份整体结构自检
python3 <<'PYEOF'
import re, os
base = "docs/3-1-Solution-Technical/L1-09-韧性+审计"
for fn in sorted(os.listdir(base)):
    if not fn.startswith("L2-0") or not fn.endswith(".md"): continue
    fp = os.path.join(base, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    secs = len(re.findall(r"^## §\d", c, re.M))
    fill = c.count("<!-- FILL")
    paired = len(re.findall(r"^@startuml", c, re.M)) == len(re.findall(r"^@enduml", c, re.M))
    status = "✓" if (secs == 14 and fill == 0 and paired) else "✗"
    print(f"{status} {fn}: §={secs} FILL={fill} paired={paired}")
PYEOF
```

### Commit

```bash
git add "docs/3-1-Solution-Technical/L1-09-韧性+审计"/L2-0{2,3,4,5}*.md
git commit -m "fix(harnessFlow): L1-09 × 4 · §13 三项一致性微调 (prd 完整路径 + 3-2 TDD 规格路径 + TC ID 命名)"
git push
```

---

## 非修任务（记录存档）

以下维度**合格**，无需改：

- ✅ §3 schema 风格（L2-02/05 Python 契约式 vs L2-03/04 YAML · 两种都合理 · L1-09 底层组件用契约式更严谨）
- ✅ 错误码命名（L1-09 内部 `E_SNAKE` 同族一致）
- ✅ IC-L2-XX 本地命名（与其他 L1 一致 · 已记录到 `docs/superpowers/reviews/2026-04-22-cross-L1-consistency-memo.md` · 不在本次修复范围）
- ✅ L2-05 ICg=5 全局 IC 引用偏少（底层组件特性 · 合理）
- ✅ §13 其他子节结构丰富（GWT/ADR/OQ/向上回写）

---

## 禁区

- **不要改 §1-§12 任何内容**（全部通过审查）
- **不要改本文档内部 §引用**（如"本 L2 §5.1"、"§11.5 硬 halt"）
- **不要改 Goal/scope/architecture §引用**（只改 prd.md 引用）
- **不要改已正确的 docs/3-2-Solution-TDD/L1-09-韧性+审计/... 路径**（L2-03/04 已对）
- **不要碰 L2-01**（上一轮已 done · 不在本次 F 交付内）

---

## 耗时估计

- P1-1 脚本跑 30s · 人工审核 4 份 × 5 min = 20 min
- P1-2 手工 Edit L2-02/05 各加 3 行 = 5 min
- P1-3 手工加 TC ID 表格（L2-02 12 条 · L2-03 15 条 · L2-05 7 条）= 20 min
- Commit + push + 验证 = 10 min
- **总计 ≤ 60 分钟**

---

## 修完即可 M4 达成 🎯

F 这批是 M4 里程碑前最后 4 份 L2。修完后：

- 3-1 Technical **57/57** 完工（100%）
- 总行数约 **79000 行**
- 全局 IC 引用 **7408 次 · 100% 合规**
- 质量 Gate 全 PASS
- **M4 里程碑正式达成**

可进入 M5（3-2 TDD 剩 62 份）+ M6（3-3 Monitoring × 10）批次。

---

## 参考先例

- A 会话类似修复：`docs/superpowers/reviews/2026-04-22-A-session-fix-prompt.md`（commit 8ae7703）
- E 会话类似修复：`docs/superpowers/reviews/2026-04-22-E-session-polish-prompt.md`（commit fb05e86）
- D 会话类似修复：`docs/superpowers/reviews/2026-04-22-D-session-polish-prompt.md`（commit 8ae7703）
- 跨 L1 治理备忘：`docs/superpowers/reviews/2026-04-22-cross-L1-consistency-memo.md`
