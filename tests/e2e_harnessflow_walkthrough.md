# E2E 全链路验证用例 — /harnessFlow + /harnessFlow-ui

**目的**：用一个真实小任务跑完整 /harnessFlow 7 阶段流水线，验证每阶段的 task-board JSON、物理产物、hook 行为、UI 显示都符合预期。

**版本**：v1.0 (2026-04-26)
**主 skill**：harnessFlow-skill.md
**配套 UI**：http://localhost:8765
**Stop hook**：hooks/Stop-final-gate.sh
**PostToolUse hook**：hooks/PostToolUse-supervisor-wake.sh（如启用）

---

## 0. 测试任务定义（小任务）

| 字段 | 值 |
|---|---|
| 任务描述 | 在 harnessFlow 仓库添加 `examples/hello/` 目录，含 `say_hello.py`（函数 `say_hello()` 返回 `"hello, harnessflow"`）+ `test_say_hello.py`（pytest 验证） |
| 期望 size | `XS` 或 `S` |
| 期望 task_type | `纯代码` |
| 期望 risk | `低` |
| 期望路由 | `B` (XS-S × 纯代码 × 低 → 直执 + 单元测试) |
| 期望耗时 | < 10 min |
| 可逆性 | 完全可逆（新增隔离目录，无现存代码改动） |

**为什么挑这个**：触发 B 路线（最简非 A 路线，强制 pytest + retro + archive），同时不污染主代码。

---

## 1. 检查矩阵（7 状态 × 4 维度）

每个状态都核对：① task-board JSON 字段 ② 物理产物 ③ hook 行为 ④ UI 显示。

### 1.1 INIT
| 维度 | 期望 |
|---|---|
| JSON | `task_id`/`created_at`/`current_state="INIT"`/`state_history[0].state="INIT"` |
| 产物 | `task-boards/<task_id>.json` 存在；`task-boards/<task_id>.lock` 可选 |
| Hook | 无 |
| UI | `GET /api/tasks` 列表含此任务，`current_state="INIT"`；`GET /api/stats.by_state.INIT` 计数 +1 |

### 1.2 CLARIFY
| 维度 | 期望 |
|---|---|
| JSON | `current_state="CLARIFY"`；澄清问答轮次 ≥ 1（写到 `clarify_rounds`）；`goal_anchor.{text,hash}` 写入 |
| 产物 | 同 1.1 |
| Hook | 无 |
| UI | `goal_text` 字段渲染 goal_anchor.text |

### 1.3 ROUTE_SELECT
| 维度 | 期望 |
|---|---|
| JSON | `size`/`task_type`/`risk` 三维写好；`route_id="B"`；`routing_events[]` 至少一条（候选 Top-2 + 用户/默认 pick） |
| 产物 | 同 1.1 |
| Hook | 无 |
| UI | `route_id`/`size`/`task_type`/`risk` 列显示 |

### 1.4 PLAN
| 维度 | 期望 |
|---|---|
| JSON | `current_state="PLAN"`；`dod_expression` 字符串写好（含 `pytest_exit_code` + `file_exists`） |
| 产物 | 路线 B 计划极简；不强制写 plan.md（A/B 豁免重型计划文档） |
| Hook | 无 |
| UI | UI 显示 `progress_percentage` ≈ 30-40 |

### 1.5 IMPL
| 维度 | 期望 |
|---|---|
| JSON | `current_state="IMPL"`；`artifacts[]` 含 say_hello.py + test_say_hello.py 两条；`skills_invoked[]` 至少 1 条 |
| 产物 | `examples/hello/__init__.py` + `examples/hello/say_hello.py` + `tests/test_say_hello.py` 实际存在 |
| Hook | PostToolUse-supervisor-wake.sh 触发（如启用）；无 BLOCK |
| UI | `artifacts` 字段在详情页显示 2 条 |

### 1.6 VERIFY
| 维度 | 期望 |
|---|---|
| JSON | `current_state="VERIFY"`；`verifier_report.overall="PASS"`；`primitives_resolved[]` 至少 2 条（`pytest_exit_code` + `file_exists`）；`red_lines_detected==[]` |
| 产物 | `pytest tests/test_say_hello.py` 实际 exit=0 |
| Hook | 无 |
| UI | UI 详情页显示 verifier_report |

### 1.7 COMMIT
| 维度 | 期望 |
|---|---|
| JSON | `current_state="COMMIT"`；`commit_sha` 写入；可选 `pr_url=null`（B 路线小任务无 PR） |
| 产物 | `git log` 含此次 commit（含 examples/hello + tests/test_say_hello.py） |
| Hook | 无 |
| UI | UI 显示 commit_sha |

### 1.8 RETRO_CLOSE → CLOSED
| 维度 | 期望 |
|---|---|
| JSON | `current_state="CLOSED"`；`final_outcome="success"`；`retro_link="retros/<task_id>.md"`；`archive_entry_link="failure-archive.jsonl#L<n>"`；`closed_at` 写入 |
| 产物 | `retros/<task_id>.md` 存在且含 11 段 `## 1.` ~ `## 11.`；`failure-archive.jsonl` 末尾新增一条 entry，pass schema 校验 |
| Hook | Stop hook 退出码 0（无 FAIL 输出） |
| UI | `final_outcome="success"`，`retro_link`/`archive_entry_link` 都有值 |

---

## 2. 终态前 Stop hook 全检查清单（hooks/Stop-final-gate.sh § 7.2）

| 检查项 | 期望 |
|---|---|
| `current_state in {CLOSED, ABORTED, PAUSED_ESCALATED}` | ✅ CLOSED |
| `red_lines==[]` | ✅ |
| `verifier_report` 非空 + `red_lines_detected==[]` | ✅ |
| `artifacts[]` 非空（B 路线必须） | ✅ 至少 2 条 |
| `final_outcome ∈ {success,failed,aborted,false_complete_reported}` | ✅ success |
| 非 A 路线 → `retro_link` 文件存在 | ✅ retros/<task_id>.md |
| 非 A 路线 → retro 含 11 段 `## N.` 标题 | ✅ |
| 非 A 路线 → `archive_entry_link` 必填 + 指向的 jsonl 行 schema 通过 | ✅ |

---

## 3. UI 显示核对（curl）

```bash
# 任务列表，确认新任务出现
curl -s http://localhost:8765/api/tasks | python3 -c "import json,sys; d=json.load(sys.stdin); print([t for t in d['tasks'] if 'e2e-hello' in t['task_id']])"

# 详情页
curl -s "http://localhost:8765/api/tasks/<task_id>" | python3 -m json.tool | head -80

# stats 应反映 +1 closed/success
curl -s http://localhost:8765/api/stats | python3 -m json.tool

# retro markdown 可拉取
curl -s "http://localhost:8765/api/tasks/<task_id>/md?path=retros/<task_id>.md" | head -20
```

---

## 4. 通过标准（DoD）

全部满足才算 PASS：

- [ ] task-board JSON 经历 INIT → CLARIFY → ROUTE_SELECT → PLAN → IMPL → VERIFY → COMMIT → RETRO_CLOSE → CLOSED 全部 9 个 state_history 条目
- [ ] examples/hello/say_hello.py + tests/test_say_hello.py 实际可被 `pytest tests/test_say_hello.py` 跑过
- [ ] retros/<task_id>.md 含 11 段 `## N.` 标题
- [ ] failure-archive.jsonl 新增一条 schema-valid 的 entry
- [ ] git log 含本次 commit
- [ ] UI 4 个 endpoint 都返回正确数据（health/tasks/tasks/{id}/stats）
- [ ] Stop hook 直接 exit 0（不输出 FAIL）

---

## 5. 失败回放预案

若任意阶段 FAIL：
1. 立即在 task-board 写 `red_lines[]` + `supervisor_interventions[]`
2. 转 PAUSED_ESCALATED 并写 `pause_reason`
3. 不强行 CLOSED（Stop hook 会拦截）
4. 在最终验收报告里把 FAIL 项 + 根因 + 修复建议都列出

---

*— v1.0 end —*
