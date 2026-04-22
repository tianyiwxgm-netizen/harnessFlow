# 跨 L1 一致性审计备忘（2026-04-22）

> 主会话 M4 达成前主动审计 · 记录跨 L1 现状 + 未来 3-2/3-3 批次的约束

---

## 1. IC-L2-XX 命名空间冲突（P1 · 治理建议 · 不阻塞 M4）

### 现状

`docs/3-1-Solution-Technical/integration/ic-contracts.md` 明确规范的是 **20 条全局跨 L1 契约**（IC-01 ~ IC-20）· 无 `IC-L2-XX` 命名空间。

但各 L1 的 L2 文档自创 `IC-L2-01` ~ `IC-L2-10` 作为**本 L1 内部契约**：

| IC 编号 | 被跨 L1 声明数 | 含义（举例冲突）|
|:---|:---:|:---|
| IC-L2-01 | 10 L1 / 29 文件 | L1-03: `load_topology` · L1-09: 锁管理器某契约 · L1-02: `trigger_kickoff` · **三者完全不同** |
| IC-L2-02 | 9 L1 / 25 文件 | L1-03: `read_snapshot` · L1-02: `render_template` · 不同契约 |
| IC-L2-03 | 9 L1 / 26 文件 | 类似冲突 |
| IC-L2-04 | 8 L1 / 16 文件 | 类似 |
| IC-L2-05 | 9 L1 / 26 文件 | 类似 |
| IC-L2-06 | 10 L1 / 27 文件 | 类似 |
| IC-L2-07 | 10 L1 / 24 文件 | 类似 |
| IC-L2-08 | 4 L1 / 9 文件 | 类似 |
| IC-L2-09 | 5 L1 / 8 文件 | 类似 |
| IC-L2-10 | 4 L1 / 7 文件 | 类似 |

### 严重度评估

**不阻塞 M4**（3-1 Technical 56/57 达成）· 因为：
- 每份 L2 文档**自带 L1 上下文**（读者打开 `L1-03/L2-01-WBS 拆解器.md` 看到 IC-L2-01 自然理解是 L1-03 内部契约）
- L2 内部契约本质是"实现细节" · 不同于全局跨 L1 契约（IC-01~20）

**影响 M5 后续**：
- 3-2 TDD 用例引用 L2 内部 IC 时需带 L1 前缀
- 3-3 Monitoring 跨 L1 抓取 IC 事件时会撞车
- 全局 grep `IC-L2-01` 会返回 29 处异构结果

### 未来批次命名约定（纳入 M5/M6 规范）

**方案 C · 前缀显式化**（推荐 · 最小改动）：

- **L1 文档内部**：继续用 `IC-L2-XX`（简洁 · 上下文明确）
- **跨 L1 引用**（3-2 TDD / 3-3 Monitoring / 集成测试）**必须用完整路径**：
  ```
  L1-03/IC-L2-01  (load_topology)
  L1-09/IC-L2-01  (lock_acquire)
  L1-02/IC-L2-01  (trigger_kickoff)
  ```
- **ic-contracts.md §6.5 补一条命名规范**（记录此约定）：

  ```markdown
  ### 6.5 本 L1 内部契约命名空间（IC-L2-XX）

  除 §2 的 20 条全局 IC（IC-01 ~ IC-20）外，各 L1 可在**本 L1 内部** L2 之间
  自定义契约，编号空间为 `IC-L2-01` ~ `IC-L2-NN`。

  - **L1 文档内**引用：直接写 `IC-L2-XX`（上下文已明确）
  - **跨 L1 文档引用**（3-2 TDD / 3-3 / 集成测试）：必须写 `L1-<NN>/IC-L2-XX`

  跨 L1 文档 grep `\bIC-L2-\d+\b` 时得到歧义结果 · 属已知局限 · 按上下文 L1 判别。
  ```

### 不建议的"激进方案"

- **方案 A**：把所有 `IC-L2-XX` 改名 `IC-L<NNN>-L2-XX` —— 需改 **50+ 份 L2 文档 × 每份 5-20 处 = 300+ 处 diff** · 回归风险高 · 收益小
- **方案 B**：全部升级为全局 IC-21~IC-100 —— 20 条全局契约的语义边界会被冲淡 · 违反 "全局 IC ≤ 20" 的架构原则

---

## 2. 错误码命名跨 L1 风格不一（P2 · 可接受 · 同 L1 内部一致即可）

### 现状

| L1 | 主风格 | 计数 |
|:---|:---|:---:|
| L1-01 | `E_SNAKE`（如 `E_AUDIT_NO_PROJECT_ID`）| 30 |
| L1-02 | `E_LNNN_LNNN_NNN`（如 `E_L102_L204_006`）| 23 |
| L1-03 | `E_LNNN_LNNN_NNN` | 21 |
| L1-04 | `E_SNAKE` | 25 |
| L1-05 | `E_SNAKE`（如 `E_INTENT_BOUNDARY_VIOLATION`）| 9 |
| L1-06 | `E_SNAKE` | 15 |
| L1-07 | `E_SNAKE` | 5 |
| L1-08 | `E_SNAKE`（如 `MD_FILE_NOT_FOUND`）| 10 |
| L1-09 | `E_SNAKE` | 16 |
| L1-10 | `E-LNNN-NNN` + 混合（如 `E-L203-001`, `E-10`）| 20 |

### 评估

- **同一 L1 内部**基本一致 · ✅
- **跨 L1 不一致**（E_SNAKE vs E_LNNN_LNNN_NNN vs E-LNNN-NNN）· ⚠️
- **3-2 TDD 用例引用错误码时**：每 L2 独立识别自家错误码 · 不形成 grep 冲突（错误码命名唯一性好）

### 建议

**不统一**（已达标 · 同 L1 一致即可）。若 M6 整理时有精力再统一 · 成本不小。

---

## 3. PM-14 路径前缀 TOP 15

```
events/           × 11
audit/            × 8
ui/               × 5
wbs/              × 4
skills/           × 4
checkpoints/      × 3
task-boards/      × 3
kb/               × 3
quality/          × 3
tmp/              × 2
manifest/         × 2
supervisor_events/× 2
config/           × 2
task_board/       × 1    ← 与 task-boards/ 冲突（连字符 vs 下划线）
mirror/           × 1
```

### P3 · 路径命名风格不统一（共 4 组冲突 · 复盘发现）

**完整扫描结果**（全局 grep `projects/<pid>/*`）：

| 冲突组 | 变体 | 出现位置 |
|:---|:---|:---|
| task board | `task-boards/`（3）+ `task_board.json`（L1-09/L2-05:1403） | L1-09 两种混用 |
| WBS 拓扑 | `wbs/`（L1-03）+ `wbs_topology/` + `wbs-topology/` | 3 种表示 |
| 4 件套 | `four-pieces/` + `four-set/` | 2 种表示 · L1-02 自用 `four-set` · 其他地方 `four-pieces` |
| L2 前缀分片 | `l1-02-l2-02-*`（L1-02）vs 常规 `meta/` `chart/`（L1-02 其他地方）| 主会话 L2-02 风格 + L1-02 其他 L2 风格 |

**建议（M4 后统一修）**：
- `task_board.json` → `task-boards/main.json`（kebab-case 复数 · 与其他路径风格一致）
- `wbs_topology/` · `wbs-topology/` → 统一 `wbs/topology/`（两层结构）
- `four-pieces/` → `four-set/`（对齐 L1-02/L2-03 主会话约定）
- `l1-02-l2-02-*` 前缀建议保留（有唯一性语义）· 或迁到 `meta/` 语义归并

**不阻塞 M4**，但影响 3-2 TDD fixture（测试用例需用真实路径）· 建议在 **M5 prompt 里固定路径清单**：

```yaml
# 3-2 TDD fixture 路径白名单（M5 时 lock）
canonical_paths:
  task_board: "projects/<pid>/task-boards/main.json"
  wbs_topology: "projects/<pid>/wbs/topology.yaml"
  four_set: "projects/<pid>/four-set/{scope,prd,plan,tdd}.md"
```

---

## 4. 主会话建议的 M4 收敛动作

### M4 达成前（F 完工 L1-09/L2-03 后）

- [x] 3-1 56/57 · L1-09/L2-03 待 F 完
- [ ] **补 ic-contracts.md §6.5 命名空间规范**（新增 ~20 行）
- [ ] **修 `task_board/` → `task-boards/`**（1 处 · 5 min）

### M4 达成后（正式进入 3-2 TDD 批次）

- 3-2 TDD 全批次 prompt 里硬性写入："跨 L1 引用 IC-L2-XX 必带 `L1-XX/` 前缀"
- 3-3 Monitoring prompt 同约束

### M5 / M6 可选收尾

- 错误码命名跨 L1 统一（如改为 `E_L<NNN>_L<NNN>_<NNN>`）· 成本高 · 收益低 · 非必做

---

## 5. 附 · 本次审计脚本（可复用）

```python
import os, re, collections

base = "docs/3-1-Solution-Technical"
err_patterns = collections.Counter()
ic_decl = collections.defaultdict(list)
pm14_paths = collections.Counter()

for root, _, fs in os.walk(base):
    for fn in fs:
        if not (fn.startswith("L2-") and fn.endswith(".md")): continue
        fp = os.path.join(root, fn)
        with open(fp, encoding="utf-8") as f: c = f.read()
        # 错误码
        for code in re.findall(r"`(E[_-][A-Z][A-Z0-9_-]+)`", c)[:5]:
            if re.match(r"^E_L\d{3}_L\d{3}_\d+$", code):
                style = "E_LNNN_LNNN_NNN"
            elif re.match(r"^E-L\d+-\d+$", code):
                style = "E-LNNN-NNN"
            elif "_" in code:
                style = "E_SNAKE"
            else:
                style = "other"
            err_patterns[(fp.split("/")[2], style)] += 1
        # IC-L2-XX
        for ic in set(re.findall(r"IC-L2-\d+", c)):
            ic_decl[ic].append(fp)
        # PM-14
        s7 = re.search(r"^## §7\b.*?(?=^## §8\b|\Z)", c, re.M | re.S)
        if s7:
            for p in set(re.findall(r"projects/<pid>/([a-z][a-z0-9_-]*)", s7.group())):
                pm14_paths[p] += 1

# 输出冲突 + TOP 路径（同上文）
```

---

**备忘结论**：无阻塞 M4 的 P0 问题 · 所有问题都在 P1-P3 治理层 · 按本文档约定收尾即可。

F 完工 L1-09/L2-03 后主会话做 2 个小动作（ic-contracts §6.5 + task-boards/ 路径统一）即达 M4。
