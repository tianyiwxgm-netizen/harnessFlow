# 【M5 · 3-2 TDD 并发会话规划总览】

> 主会话 2026-04-22 分派 · 基于 G 会话已完成的 L1-01 × 6 + L1-04 × 7 TDD depth-B 标杆

---

## 现状

| 层 | 进度 | 说明 |
|:---|:---:|:---|
| 已完成 | **13 / 57** | G 会话 · L1-01 × 6 + L1-04 × 7 · depth-B 标杆（15+ TC / ≥10 段 / FILL=0）|
| 待做 | **44 / 57** | L1-02/03/05/06/07/08/09/10 全骨架 · 70 行 × 9 FILL |
| integration/acceptance | 0 / 36 | 未建（延后 · 等 L2 tests 稳定）|

---

## 并发分工（5 会话 · 44 份 L2 tests）

| 会话 | 范围 | 文件数 | 独立性 | md prompt |
|:---|:---|:---:|:---|:---|
| **H** | L1-02 项目生命周期编排 × 7 | 7 | ✅ 只动 L1-02 目录 | `2026-04-22-session-H-L1-02-TDD.md` |
| **I** | L1-03 WBS+WP 拓扑 × 5 + L1-05 Skill+子 Agent × 5 | 10 | ✅ 只动 L1-03/05 | `2026-04-22-session-I-L1-03-05-TDD.md` |
| **J** | L1-06 3 层 KB × 5 + L1-07 Harness 监督 × 6 | 11 | ✅ 只动 L1-06/07 | `2026-04-22-session-J-L1-06-07-TDD.md` |
| **K** | L1-08 多模态 × 4 + L1-09 韧性+审计 × 5 | 9 | ✅ 只动 L1-08/09 | `2026-04-22-session-K-L1-08-09-TDD.md` |
| **L** | L1-10 人机协作 UI × 7 | 7 | ✅ 只动 L1-10 | `2026-04-22-session-L-L1-10-TDD.md` |

---

## 统一质量标杆（参照 G 会话的 L1-01 × 6 交付）

| 维度 | 硬要求 |
|:---|:---|
| 文件行数 | 300-600 行（精简风格）· 或 1200-1800 行（深度风格 · 参 G 的 L1-01）|
| § 段数 | 10（§0-§9） |
| FILL | **0** |
| PlantUML / Mermaid | 禁 Mermaid · 允许引用 3-1 的 §5 时序 |
| TC ID | **≥ 15**（`TC-LNNN-L20N-NNN` 或 `TC-<DOMAIN>-<CATEGORY>-NNN`）|
| `def test_` 函数 | **≥ 15** |
| 每 public 方法 | **≥ 1 正向用例**（覆盖 3-1 对应 L2 的 §3 接口）|
| 每错误码 | **≥ 1 负向用例**（覆盖 3-1 对应 L2 的 §11 错误码）|
| IC-XX 契约集成测试 | **≥ 3 个**（覆盖 3-1 对应 L2 的 §4 依赖）|
| 性能 SLO 用例 | **≥ 3 个**（覆盖 3-1 对应 L2 的 §12 SLO）|
| e2e 场景 | **≥ 2 个**（覆盖 3-1 对应 L2 的 §5 P0 时序）|
| pytest fixture | **≥ 5 个**（mock_project_id / mock_event_bus / mock_clock / mock_ic_payload 等）|
| 测试代码风格 | pytest + Python 3.11+ 类型注解 + Python-like 伪代码（不要求真跑）|

---

## 统一硬约束（5 会话通用）

### 禁区

- ❌ **不修改 3-1 任何文件** · 3-1 是只读源
- ❌ **不修改 `docs/2-prd/` 任何文件** · 只读
- ❌ **不修改 `docs/3-1-Solution-Technical/integration/`** · 只读
- ❌ **不修改 `scripts/quality_gate.sh`**
- ❌ **不碰 3-2 里其他 L1 目录**（H 只动 L1-02 · I 只动 L1-03/05 · 等）
- ❌ **禁止同时多份并发 Write**（每份独立 commit · 5-10 份串行写）

### TDD 路径规范（学 A 会话教训）

- 本文件位于 `docs/3-2-Solution-TDD/<L1 全目录名>/L2-0N-XXX-tests.md`
- 反向引用 3-1 必带完整路径：`docs/3-1-Solution-Technical/<L1 全目录名>/L2-0N-XXX.md §X.X`
- 反向引用 prd 必带完整路径：`docs/2-prd/<L1 全目录名>/prd.md §X.X`
- TC ID 命名**同一 L2 文件内保持一致**（标准 `TC-LNNN-L20N-NNN` 或语义 `TC-<DOMAIN>-<CATEGORY>-NNN`）

---

## 通用模板（每份 tests.md 的 10 段结构）

```markdown
---
doc_id: tests-L1-NN-L2-0X-v1.0
doc_type: l2-tdd-tests
layer: 3-2-Solution-TDD
parent_doc:
  - docs/3-1-Solution-Technical/<L1>/<L2>.md（接口源 · 错误码源 · §13 TC ID 矩阵源）
  - docs/2-prd/<L1>/prd.md（负向用例 GWT 源）
  - docs/3-1-Solution-Technical/integration/ic-contracts.md
version: v1.0
status: depth-B-complete
---

# <L1> <L2> · TDD 测试用例

> 基于 3-1 L2 tech-design 的 §3 接口 + §11 错误码 + §13 TC ID 矩阵驱动

## §0 撰写进度

- [x] §1 覆盖度索引
- [x] §2 正向用例（每方法 ≥ 1）
- [x] §3 负向用例（每错误码 ≥ 1）
- [x] §4 IC-XX 契约集成测试
- [x] §5 性能 SLO 用例
- [x] §6 端到端 e2e
- [x] §7 测试 fixture
- [x] §8 集成点用例
- [x] §9 边界 / edge case

## §1 覆盖度索引

（表格 · public 方法 / 错误码 / IC 对应的 TC ID 矩阵）

## §2 正向用例（每方法 ≥ 1）

```python
class TestXXX:
    @pytest.fixture
    def sut(self, mock_pid, mock_event_bus):
        return XXXService(project_id=mock_pid, event_bus=mock_event_bus)
    
    def test_xxx_happy_path(self, sut):
        """TC-LNNN-L20N-001 · 正向"""
        # Arrange / Act / Assert
```

## §3 负向用例（每错误码 ≥ 1）

（每错误码至少 1 负向 TC · pytest.raises）

## §4 IC-XX 契约集成测试

（至少 3 个 join test · mock 对端）

## §5 性能 SLO 用例

（基于 3-1 §12 · pytest-benchmark 风格 · 至少 3 个）

## §6 端到端 e2e

（2-3 个 · 映射 3-1 §5 P0 时序）

## §7 测试 fixture

（pytest fixtures · mock 对象 · 至少 5 个）

## §8 集成点用例

（与兄弟 L2 协作测试 · 至少 2 个）

## §9 边界 / edge case

（空/超大/并发/超时/崩溃 · 至少 4 个）

---

*— TDD · depth-B · v1.0 · <date> —*
```

---

## 验收（每会话完工必跑）

```bash
# 1. 质量自检
python3 <<'PYEOF'
import os, re
base = "docs/3-2-Solution-TDD/<L1 目录>"
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

# 2. Gate 全绿
./scripts/quality_gate.sh

# 3. 每份独立 commit + push
git push origin main
```

---

## 推进建议

### 顺序

**可完全并行** · 5 会话同时启动 · 彼此不冲突：
- H 只动 L1-02（7 份）
- I 只动 L1-03/05（10 份）
- J 只动 L1-06/07（11 份）
- K 只动 L1-08/09（9 份）
- L 只动 L1-10（7 份）

### 预计耗时

参考 G 做 L1-01 × 6 + L1-04 × 7 用时：单份 tests.md 约 15-30 分钟（depth-B 精简 · 不追求 1800 行）· 每会话 7-11 份 ≈ 2-4 小时完。

### 会话限额风险

单会话做 7-11 份 · 若遇配额限 · **先做前 5 份 commit · 剩余下轮继续**（已完成的每份都是独立 commit · 不会丢）。

---

## 完成后（M5 剩余）

5 会话完工后：
- 3-2 TDD 57/57 全完成 ✅（L2 tests）
- 剩 integration/ + acceptance/ 36 份新建（**延后到下一波 M · 需 L2 tests 稳定做基线**）

---

## 6 份独立 prompt md 路径清单

```
docs/superpowers/reviews/2026-04-22-M5-TDD-parallel-plan.md       （本文件 · 总览）
docs/superpowers/reviews/2026-04-22-session-H-L1-02-TDD.md         （H · L1-02 × 7）
docs/superpowers/reviews/2026-04-22-session-I-L1-03-05-TDD.md      （I · L1-03 × 5 + L1-05 × 5）
docs/superpowers/reviews/2026-04-22-session-J-L1-06-07-TDD.md      （J · L1-06 × 5 + L1-07 × 6）
docs/superpowers/reviews/2026-04-22-session-K-L1-08-09-TDD.md      （K · L1-08 × 4 + L1-09 × 5）
docs/superpowers/reviews/2026-04-22-session-L-L1-10-TDD.md         （L · L1-10 × 7）
```

每份 prompt 直接复制整段给新会话即可。
