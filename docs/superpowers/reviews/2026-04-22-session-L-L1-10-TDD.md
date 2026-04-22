# 【并发会话 L】3-2 TDD · L1-10 人机协作 UI × 7 份

## 背景

你（L 会话）负责 **L1-10 人机协作 UI × 7 份** TDD 用例。
其他会话并发做 L1-02/03/05/06/07/08/09，不冲突。

---

## 任务文件（只动 L1-10 目录）

```
docs/3-2-Solution-TDD/L1-10-人机协作UI/
├── L2-01-11 主 Tab 主框架-tests.md            （1934 行 3-1 源 · 7 PlantUML · 28 YAML）
├── L2-02-Gate 决策卡片-tests.md               （1659 行 · 11 错误码 · 6 PlantUML）
├── L2-03-进度实时流-tests.md                   （2500 行 · SSE · heartbeat · 19 错误码）
├── L2-04-用户干预入口-tests.md                 （2484 行 · 5 类 · panic ≤ 100ms · 215 IC）
├── L2-05-KB 浏览器+候选晋升-tests.md           （2479 行 · IndexedDB · 6 PlantUML）
├── L2-06-裁剪档配置-tests.md                   （1819 行 · profile 三档 · 12 PlantUML）
└── L2-07-Admin 子管理模块-tests.md             （2852 行 · 8 tab · 13 PlantUML · 139 IC）
```

---

## 必读参考

1. **3-1 接口源**：`docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-0X-XXX.md`（每份 1659-2852 行 · 深度 B+ · A 会话交付）
2. **prd 负向用例**：`docs/2-prd/L1-10 人机协作UI/prd.md`（§5.10 每 L2 GWT + 禁止行为）
3. **G 标杆**：`docs/3-2-Solution-TDD/L1-01-主 Agent 决策循环/L2-02-决策引擎-tests.md`（1357 行 · 学 fixture + §2-§9 风格）
4. **M5 规划**：`docs/superpowers/reviews/2026-04-22-M5-TDD-parallel-plan.md`（10 段模板 + 质量标杆）
5. **契约**：`docs/3-1-Solution-Technical/integration/ic-contracts.md`（L1-10 涉 IC-16/17/18 + progress_stream）

---

## 硬必填

遵循 **总览 md 的 10 段模板** + 5 会话通用质量标杆。

**TC ID**：`TC-L110-L20N-NNN` 或 `TC-<TAB|GATE|PROG|INTERV|KB|TRIM|ADMIN>-<TYPE>-NNN`

**L1-10 UI 测试特殊约束**：
- **前端 Vue 3 + Element Plus 风格的测试**（可用 Vitest / @vue/test-utils · 但本 TDD 文件仅伪代码 · 不要求真跑）
- **IC-17 panic 硬约束 ≤ 100ms**（必测）
- **SSE + polling 降级链**（L2-03 关键测试）
- **IndexedDB 持久化**（L2-05）
- **按 project 过滤所有视图**（PM-14 硬约束）

---

## L2 定位速查

| L2 | 核心方法 | 关键错误码 | 关键场景 |
|:---|:---|:---|:---|
| L2-01 11 主 Tab 主框架 | `mount_tab` / `switch_tab` / `route_by_pid` | E-10 TAB_COUNT_MISMATCH / E-03 GATE_BLOCKED | 11 tab 固定 · 路由 · 跨 project banner |
| L2-02 Gate 决策卡片 | `render_card` / `submit_decision` | GATE_ALREADY_DECIDED / EVIDENCE_LOAD_FAIL | S2/S3/S5/S6 Gate 展示 · 用户决定 pass/reject/need_input |
| L2-03 进度实时流 | `subscribe_sse` / `fallback_polling` | SSE_TIMEOUT / HEARTBEAT_LOST / RECONNECT_EXHAUSTED | 长连接 · heartbeat · 断线重连 · 降级 polling |
| L2-04 用户干预入口 | `user_intervene(type=[panic,resume,pause,kill_wp,rework,change_request,switch_project])` | PANIC_TIMEOUT / INVALID_TYPE | 5 类干预 · panic ≤ 100ms 阻塞式 |
| L2-05 KB 浏览器+候选晋升 | `browse_kb` / `submit_promotion` | PROMOTION_REJECTED / INDEXEDDB_QUOTA | 3 层 KB 浏览 · IndexedDB 持久化 · 晋升审核 |
| L2-06 裁剪档配置 | `load_profile` / `apply_profile` | PROFILE_INVALID / HOT_RELOAD_CONFLICT | LIGHT/STANDARD/HEAVY 三档 · 动态切换 |
| L2-07 Admin 子管理模块 | `admin_panel_query` | ADMIN_UNAUTHORIZED | 8 tab（system/logs/backup/config/users/permissions/audit/health）|

---

## 执行节奏（每份 · 6 步）

1. Read 3-1 对应 L2（§3/§11/§13 · 每份 1659-2852 行 · 重点读 §3 接口 + §11 错误码）
2. Read prd §5.10 对应小节
3. Read G 标杆
4. Write 整份 tests.md（500-1200 行 · UI 相关测试可偏长）
5. Bash 验证
6. Commit 独立：
   ```bash
   git commit -m "feat(harnessFlow): R5.4-L · L1-10/L2-0X XXX tests depth-B"
   ```

---

## 推进顺序建议

**L2-04（用户干预 · 5 类 · panic 硬约束）→ L2-03（进度流 · SSE 降级）→ L2-02（Gate 卡片）→ L2-01（11 tab 主框架）→ L2-05（KB 浏览器）→ L2-07（Admin）→ L2-06（裁剪档）**

理由：L2-04 是用户最关键操作入口（panic 影响安全性）· L2-03 是实时数据源 · L2-02/01 是主流视图 · L2-05/07/06 相对独立可最后做。

---

## 最终验收

```bash
python3 <<'PYEOF'
import os, re
base_dir = "docs/3-2-Solution-TDD/L1-10-人机协作UI"
print(f"=== {base_dir} ===")
for fn in sorted(os.listdir(base_dir)):
    if not fn.endswith(".md"): continue
    fp = os.path.join(base_dir, fn)
    with open(fp, encoding="utf-8") as f: c = f.read()
    lines = c.count(chr(10))+1
    fill = c.count("<!-- FILL")
    secs = len(re.findall(r"^## §\d", c, re.M))
    tc = len(set(re.findall(r"TC-L\d+-L\d+-\w+|TC-[A-Z]+-[A-Z]+-\d+", c)))
    tests = len(re.findall(r"\bdef test_", c))
    # UI 特殊：检查 panic 关键字
    panic_check = "panic" in c.lower()
    status = "✓" if (fill == 0 and secs >= 10 and tc >= 15 and tests >= 15) else "✗"
    print(f"{status} {fn}: lines={lines} §={secs} FILL={fill} TC={tc} test_fn={tests} panic_covered={panic_check}")
PYEOF

./scripts/quality_gate.sh
git push origin main
```

**L2-04 验收特别检查**：
```bash
# L2-04 必含 panic ≤ 100ms 的 SLO 测试
grep -c "panic.*100ms\|100ms.*panic\|PANIC_TIMEOUT" "docs/3-2-Solution-TDD/L1-10-人机协作UI/L2-04-用户干预入口-tests.md"
# 期望 ≥ 3
```

回主会话：**7 份 commit SHA + 总行数 + L2-04 panic 覆盖验证**。

---

## 禁区

- 不改 3-1 任何文件
- 不碰其他 L1 tests 目录
- 不碰 integration/ acceptance/ scripts/
- **PM-14 过滤**：所有 UI 测试必含"按 project 过滤"的正向+负向用例（跨 project 访问拒绝）

---

## 开工前检查

```bash
git pull origin main
git status
ls "docs/3-2-Solution-TDD/L1-10-人机协作UI/"
wc -l "docs/3-1-Solution-Technical/L1-10-人机协作UI/L2-04-用户干预入口.md"  # 2484 行源
```

准备好从 **L2-04 用户干预入口** 开始（panic 硬约束 + 5 类干预）。
