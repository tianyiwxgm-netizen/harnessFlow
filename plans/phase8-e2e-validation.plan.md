# Plan: harnessFlow Phase 8 — 端到端验证（MVP 真完成率 100%）

> 版本 v1.0（2026-04-17）；Phase 8 产出；PRP plan 格式（/prp-plan 驱动）。
> 依赖：Phase 1-7 全 complete（commit 39b3dca）；85 pytest 全绿。

## Summary

用三个真任务跑通 harnessFlow 全链路（skill 激活 → 澄清 → 路由 → 执行 → 监督 → 验证 → retro → 归档），证明 Phase 1-7 MVP 可用、真完成率达标、Phase 7 的 RETRO_CLOSE 强制链和 Stop gate 在真实场景下被触发且通过。

## User Story

As a harnessFlow 维护者（唯一用户），
I want 在三个代表性真任务（视频出片 XL / 后端 feature M / Vue 页面 M-L）上验证 harnessFlow 能无遗漏触发 Verifier + retro + archive，
So that 我能把 MVP 信心度从"pytest 过了"提升到"真任务过了"，并把 Phase 8 未覆盖的缺陷列进 Phase 9 候选。

## Problem → Solution

**Current state**（Phase 7 交付后）：
- 85 pytest 绿，Phase 1-7 所有 artifact 产出
- 但从未用一次真任务跑 harnessFlow 端到端
- P20 假完成事件是 harnessFlow 立项的唯一案例，且**尚未用 harnessFlow 自己复核过一次**（自举验证缺位）

**Desired state**（Phase 8 交付后）：
- 三任务各产出一份终态 task-board.json + 一份 verifier_report.json + 一份 11 段 retro markdown + 一条 failure-archive.jsonl entry
- Stop gate 在三任务收口时真实跑一次（非测试桩）
- auditor 在累积 ≥ 20 条 archive 前不会触发，但会在 dry-run 里验证逻辑
- MVP 真完成率 100%，用户打断 ≤ 1 次/任务

## Metadata

- **Complexity**: XL（拆 4 子 phase 执行）
- **Source PRD**: `harnessFlow /harness-flow.prd.md` Phase 8 行
- **PRD Phase**: Phase 8 — 端到端验证
- **Estimated Files**: 读 ~15 个 / 改 ~8 个 / 创建 ~12 个（不含 task-boards/retros/archive 运行产物）

---

## UX Design

**N/A — internal change**。Phase 8 是对 harnessFlow 本身的自举验证，用户（同一个人）体验没有变化。**但** Phase 8 会产生用户可直接读的"验证报告"作为交付 artifact（见 § Completion Checklist）。

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `harnessFlow /method3.md` | § 1.1 + § 6.1 + § 7.1-7.3 + § 8.1 | 真完成第一原则 + DoD 模板 + retro/archive 规则 + P20 事件定义 |
| P0 | `harnessFlow /harnessFlow-skill.md` | 全（~870 行） | 主 skill prompt；Phase 8 = 用它跑真任务 |
| P0 | `harnessFlow /state-machine.md` | § 1 + § 7 | 20 个状态枚举 + INSUFFICIENT_EVIDENCE cap=2 |
| P0 | `harnessFlow /delivery-checklist.md` | § 0 + § 3.2 + § 7.2 | 三段证据分类 + 视频出片专属 DoD + Phase 7 Stop gate 清单 |
| P0 | `harnessFlow /flow-catalog.md` | 全（A-F 6 路线） | 选路依据 |
| P0 | `harnessFlow /routing-matrix.md` | § 决策矩阵 | 42 cell 推荐 top-2 路线 |
| P0 | `harnessFlow /task-board-template.md` | § 1 完整字段 | task-board JSON 结构 |
| P1 | `harnessFlow /subagents/verifier.md` | § 3 Verifier 契约 | DoD eval + 3 段证据链 + verdict 输出 |
| P1 | `harnessFlow /subagents/supervisor.md` | § 6 类干预 + § 3 红线 | 监听 tool call + 干预判断 |
| P1 | `harnessFlow /subagents/retro-generator.md` | § 1-3 | retro markdown 生成契约 |
| P1 | `harnessFlow /subagents/failure-archive-writer.md` | § 1-3 | jsonl 归档 + audit 触发 |
| P1 | `harnessFlow /hooks/Stop-final-gate.sh` | 全 | Phase 7 门卫逻辑 |
| P1 | `harnessFlow /verifier_primitives/README.md` | 原语清单 | 可调用的 20+ DoD 原语 |
| P2 | `harnessFlow /archive/writer.py` | 头部 docstring + public API | write_archive_entry 签名 + `_line_no` 约定 |
| P2 | `harnessFlow /archive/auditor.py` | 头部 docstring | audit 签名 + 进化边界硬线 |
| P2 | `harnessFlow /schemas/failure-archive.schema.json` | 全 | 归档字段 enum |
| P2 | `aigc/backend/scripts/e2e_runner.py` | 1-100（入口 + API 调用模式） | P20 运行参考（POST /api/pipelines） |
| P2 | `aigc/backend/app/controllers/video.py` | 137-230（videos/generate 路由） | 后端 feature 任务的修改落点候选 |
| P2 | `aigc/frontend/playwright.config.ts` | 全 | fast/pipeline/acceptance 三项目配置 |

## External Documentation

**N/A — Phase 8 不引入新外部依赖**。所有工具（uvicorn / playwright / ffprobe / curl / pytest）已在 Phase 1-7 内部 pattern 中使用。

---

## Patterns to Mirror

Phase 8 大量复用 Phase 1-7 的 pattern；下列 6 条是"写新文件"时必须镜像的模板。

### TASK_BOARD_INIT
// SOURCE: `harnessFlow /task-board-template.md` § 1
```json
{
  "task_id": "p8-<sub>-<short-name>",
  "project": "harnessFlow",
  "task_type": "视频出片 | 后端feature | UI页面 | 元技能验证",
  "size": "M | L | XL",
  "risk": "可逆 | 半可逆 | 不可逆",
  "route_id": "A | B | C | D",
  "initial_route_recommendation": "...",
  "current_state": "INIT",
  "dod_expression": "<boolean combination of verifier_primitives>",
  "time_budget": {"cap_sec": 3600, "elapsed_sec": 0},
  "cost_budget": {"token_cap": 100000, "token_used": 0},
  "state_history": [],
  "red_lines": [],
  "retries": [],
  "supervisor_interventions": [],
  "artifacts": []
}
```

### VERIFIER_REPORT_STRUCTURE
// SOURCE: `harnessFlow /subagents/verifier.md` § 3 + `archive/tests/test_writer.py:61-70`
```json
{
  "task_id": "...",
  "verdict": "PASS | FAIL | INSUFFICIENT_EVIDENCE",
  "priority_applied": "P0_red_line | P1_pass | P2_normal_fail | P3_insufficient",
  "failed_conditions": ["ffprobe_duration(\"p.mp4\") > 0", ...],
  "red_lines": ["DRIFT_CRITICAL | DOD_GAP_ALERT | IRREVERSIBLE_HALT"],
  "red_lines_detected": [],
  "evidence_chain": {
    "existence": [{"primitive": "file_exists", "arg": "...", "result": true}, ...],
    "behavior": [{"primitive": "curl_status", "arg": "...", "result": 200}, ...],
    "quality": [{"primitive": "ffprobe_duration", "arg": "...", "result": 12.4}, ...]
  },
  "insufficient_evidence_count_after_this": 0
}
```

### DOD_BOOLEAN_VIDEO
// SOURCE: `harnessFlow /delivery-checklist.md` § 3.2 + P20 事件反模式（method3 § 8.1）
```python
DoD_P20 = (
    file_exists("aigc/backend/media/videos/<task_id>/final.mp4")
    AND os_stat_size("aigc/backend/media/videos/<task_id>/final.mp4") > 1024
    AND ffprobe_duration("aigc/backend/media/videos/<task_id>/final.mp4") > 0
    AND playback_check("aigc/backend/media/videos/<task_id>/final.mp4")
    AND oss_head("oss://videoforge/<task_id>/final.mp4").status_code == 200
    AND uvicorn_started("localhost:8000")
    AND curl_status("POST /api/pipelines", ...).status_code == 200
    AND schema_valid(curl_json(...), "schemas/pipeline_response.json")
)
```

### DOD_BOOLEAN_BACKEND
// SOURCE: `harnessFlow /delivery-checklist.md` § 3.3（后端 feature）
```python
DoD_Backend = (
    uvicorn_started("localhost:8000")
    AND curl_status("<new_endpoint>", method="POST", body=<sample>).status_code == 200
    AND schema_valid(curl_json(...), "<new_schema>")
    AND pytest_exit_code("tests/test_<new>.py") == 0
    AND git_diff_lines("app/controllers/<module>.py") <= 150  # 防 scope creep
)
```

### DOD_BOOLEAN_UI
// SOURCE: `harnessFlow /delivery-checklist.md` § 3.4（UI 页面）
```python
DoD_UI = (
    dev_server_up("http://localhost:5173")
    AND playwright_exit_code("e2e/<new>.spec.ts") == 0
    AND screenshot_has_content("artifacts/<page>.png", min_bytes=10240)
    AND browser_console_errors_count("<page_url>") == 0
)
```

### SUBAGENT_SPAWN
// SOURCE: `harnessFlow /harnessFlow-skill.md` § 6.1 + § 8.2 + § 8.6
```python
# Verifier（VERIFY 状态进入时）
verifier_out = Agent({
    "subagent_type": "harnessFlow:verifier",
    "task_id": task_id,
    "task_board_path": f"task-boards/{task_id}.json",
    "dod_expression": task_board["dod_expression"],
})
# 返回 verifier_report.json → 写回 task_board["verifier_report"]

# Retro + Archive（RETRO_CLOSE 状态，非 A 路线强制）
retro_out = Agent({"subagent_type": "harnessFlow:retro-generator", ...})
arc_out = Agent({"subagent_type": "harnessFlow:failure-archive-writer", ...})
task_board["retro_link"] = retro_out["retro_link"]
task_board["archive_entry_link"] = f"failure-archive.jsonl#L{arc_out['line_no']}"
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `.claude/settings.local.json` | UPDATE | 注册 2 个 hooks（PostToolUse-goal-drift + Stop-final-gate）；加 harnessFlow skill / subagent 所需权限 |
| `.claude/skills/harnessFlow.md` | CREATE（软链） | 让 Claude Code 识别 `/harnessFlow`；`ln -s harnessFlow\ /harnessFlow-skill.md .claude/skills/harnessFlow.md` |
| `.claude/agents/harnessFlow-supervisor.md` | CREATE（软链或复制） | 4 个 subagent 注册入口 |
| `.claude/agents/harnessFlow-verifier.md` | CREATE | 同上 |
| `.claude/agents/harnessFlow-retro-generator.md` | CREATE | 同上 |
| `.claude/agents/harnessFlow-failure-archive-writer.md` | CREATE | 同上 |
| `harnessFlow /plans/phase8-e2e-validation.plan.md` | CREATE | 本 plan |
| `harnessFlow /task-boards/p8-0-infra.json` | CREATE（运行时） | 8.0 infra 子 phase 运行产物 |
| `harnessFlow /task-boards/p8-1-vue-<name>.json` | CREATE（运行时） | 8.1 Vue 子 phase |
| `harnessFlow /task-boards/p8-2-backend-<name>.json` | CREATE（运行时） | 8.2 后端 feature |
| `harnessFlow /task-boards/p8-3-p20.json` | CREATE（运行时） | 8.3 P20 出片 |
| `harnessFlow /verifier_reports/p8-*.json` | CREATE（运行时） | 4 份 verifier_report |
| `harnessFlow /retros/p8-*.md` | CREATE（运行时） | 3 份 retro（非 A 路线；8.0 若走 A 可豁免） |
| `harnessFlow /failure-archive.jsonl` | APPEND（运行时） | 3-4 条 entry |
| `harnessFlow /phase8-validation-report.md` | CREATE（手写） | 最终 Phase 8 总交付：每子 phase 结果 + 三项指标（真完成率/打断次数/Verifier verdict）+ 缺陷清单 |
| `harnessFlow /harness-flow.prd.md` | UPDATE | Phase 8 行 pending → in-progress → complete |

## NOT Building

- **不引入新 skill / subagent**。Phase 8 只**使用** Phase 5-7 已有的编排器 + 4 个 subagent。
- **不重构 Phase 1-7 文档**。若验证期发现 Phase 1-7 有漏洞，写进 Phase 9 候选 retro，而非当场改。
- **不引入新 hook**。只注册现有两个（PostToolUse-goal-drift + Stop-final-gate）。
- **不做 mock 层重写**。三任务全部用真实后端/OSS/LLM，这是"真完成"的定义。
- **不跑 auditor 阈值触发**。每 20 条才触发，Phase 8 只产 3-4 条；仅在 § 8.0 dry-run 里跑一次 `audit(interval=2)` 证明链路。
- **不改 routing-matrix.json**。即使验证中发现 cell 推荐不准，也只在 retro 的"进化建议"里写，不自动改（method3 § 7.3 进化边界硬线）。

---

## Step-by-Step Tasks

四个子 phase 串行执行；每子 phase 独立 commit。所有子 phase 走 harnessFlow 自身流程（即：激活 /harnessFlow → 主 skill 接管 → 2-3 轮澄清 → 路由 → 执行 → 收口）。

### § 8.0 子 phase — Infrastructure + Smoke Test（预算 1h）

**目标**：让 Claude Code 能识别 `/harnessFlow` 及 4 个 subagent；hooks 生效；用一次最小任务（XS + 可逆）跑通全链路，不必产 retro（A 路线豁免）。

#### Task 8.0.1: 注册 harnessFlow skill 软链到 .claude/skills/
- **ACTION**: `ln -s "$(pwd)/harnessFlow /harnessFlow-skill.md" .claude/skills/harnessFlow.md`
- **IMPLEMENT**: 创建 `.claude/skills/` 目录（若不存在）；软链到项目根；**避免空格问题**，用绝对路径。
- **MIRROR**: 官方 skill 示例（如 superpowers-marketplace 的 writing-plans.md 组织方式）
- **GOTCHA**: 目录名带空格（`harnessFlow /`），软链目标要加引号；Claude Code 重启后才生效（见 Task 8.0.3）
- **VALIDATE**: `ls -la .claude/skills/harnessFlow.md` 显示 symlink，`readlink` 解析到正确目标

#### Task 8.0.2: 注册 4 个 subagent 到 .claude/agents/
- **ACTION**: 对 `harnessFlow /subagents/` 下 4 个 md 文件做软链或复制到 `.claude/agents/<name>.md`
- **IMPLEMENT**:
  ```bash
  mkdir -p .claude/agents
  for f in supervisor verifier retro-generator failure-archive-writer; do
    ln -s "$(pwd)/harnessFlow /subagents/$f.md" ".claude/agents/harnessFlow-$f.md"
  done
  ```
- **MIRROR**: superpowers 插件 agents 的 `name:` frontmatter = file basename 约定
- **GOTCHA**: subagent 文件内的 `name: harnessFlow:<x>` 要求调用方用完整 namespaced name（已在 Phase 6 落地）
- **VALIDATE**: `ls -la .claude/agents/` 4 条软链；读每个文件首行确认 `name:` 字段匹配

#### Task 8.0.3: 注册 2 个 hooks 到 .claude/settings.local.json
- **ACTION**: 用 update-config skill 合并 hooks 数组（不要覆盖现有 allow/mcp）
- **IMPLEMENT**:
  ```json
  {
    "hooks": {
      "PostToolUse": [{
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "bash \"$(pwd)/harnessFlow /hooks/PostToolUse-goal-drift-check.sh\""
        }]
      }],
      "Stop": [{
        "hooks": [{
          "type": "command",
          "command": "bash \"$(pwd)/harnessFlow /hooks/Stop-final-gate.sh\""
        }]
      }]
    }
  }
  ```
- **MIRROR**: `hooks/README.md`（Phase 4 产出）里的注册示例
- **GOTCHA**: hook 命令路径带空格必须用引号；`$(pwd)` 在 JSON 里会被字面存储，改用绝对路径；settings 改完 Claude Code 需要重启/重载
- **VALIDATE**: `jq '.hooks' .claude/settings.local.json` 输出两个 hook；手动触发一次 Edit，看 stderr 是否有 hook 输出

#### Task 8.0.4: Stop hook 自测（无 task-board 场景）
- **ACTION**: 手动运行 hook，确认无 task-boards 时 exit 0
- **IMPLEMENT**: `bash "harnessFlow /hooks/Stop-final-gate.sh"; echo "exit=$?"`
- **VALIDATE**: exit=0（因 `BOARDS_DIR` 为空或不存在时直接 exit 0）

#### Task 8.0.5: 8.0 Smoke task — 创建最小 task-board（A 路线）并跑过 Stop gate
- **ACTION**: 创建一个 task_id=p8-0-smoke，route=A，size=XS，task_type=元技能验证，current_state=CLOSED 的 board；final_outcome=success；验证 Stop gate 放行
- **IMPLEMENT**:
  ```bash
  # 手写 task-boards/p8-0-smoke.json 含：
  # {
  #   "task_id": "p8-0-smoke",
  #   "project": "harnessFlow",
  #   "route_id": "A",
  #   "size": "XS",
  #   "task_type": "元技能验证",
  #   "risk": "可逆",
  #   "current_state": "CLOSED",
  #   "final_outcome": "success",
  #   "verifier_report": {
  #     "verdict": "PASS", "red_lines_detected": [], "evidence_chain": {...}
  #   },
  #   "red_lines": [],
  #   "artifacts": [{"type": "smoke-test", "path": ".claude/skills/harnessFlow.md"}]
  # }
  bash "harnessFlow /hooks/Stop-final-gate.sh"
  ```
- **GOTCHA**: A 路线豁免 retro + archive_entry_link 检查；但 artifacts[] 不能空（非 F 路线强制）
- **VALIDATE**: Stop gate exit 0；无 FAIL 输出

#### Task 8.0.6: 8.0 Smoke task — auditor dry-run 测链路
- **ACTION**: 伪造 2 条 archive entry，跑 `audit(interval=2)` 证明审计链路能跑
- **IMPLEMENT**:
  ```python
  # 在 archive/tests/ 下临时跑：
  from archive.auditor import audit, need_audit
  # 先往 failure-archive.jsonl.tmp 写 2 条 dummy entry
  # 调 audit(archive_path="<tmp>", interval=2, ...)
  # 断言返回 AuditReport.report_path 非空，to_dict()["path"] 指向文件
  ```
- **VALIDATE**: 产出 `audit-reports/audit-*.json`；其中 `suggestions: []`（样本不够触发降权/升权）；**不改** `routing-matrix.json`（grep 验证 mtime 未变）
- **CLEANUP**: 删 tmp archive 和 audit-report（避免污染真实归档）

#### Task 8.0.7: 8.0 收尾 + commit
- **ACTION**: git add `.claude/` + `harnessFlow /task-boards/p8-0-smoke.json`；commit
- **IMPLEMENT**: `git commit -m "feat(harnessFlow Phase 8.0): skill/subagent/hooks 注册 + smoke test 跑通"`
- **VALIDATE**: `git log --oneline -1` 显示新 commit；下一次 Claude Code 启动能识别 `/harnessFlow`

---

### § 8.1 子 phase — self-test 脚本验证（预算 1.5h）

> **重新设计**：Phase 8 不污染任何被试项目。三个验证任务全部是 harnessFlow **自己真需要**的 feature。

**目标**：用 harnessFlow 跑通一次"元技能验证" + M 体量 + 可逆任务；被试任务 = **给 harnessFlow 加一份 self-test 脚本**（`harnessFlow /scripts/self-test.sh`），功能：
1. 验证 setup.sh 已跑（`.claude/skills/harnessFlow.md` symlink 存在 + readlink 有效）
2. 验证 4 个 subagent 软链 + 文件首行 `name:` 字段匹配
3. 验证 hooks 在 settings.local.json 里注册且命令路径文件存在
4. 验证 python3 + jsonschema 可 import
5. 验证 `python3 -m pytest` 85 个全绿
6. 输出 PASS/FAIL + 每项细节

预期走 **路线 B**（轻 PRP：plan → impl → unit test → 简易验证）。

#### Task 8.1.1: 被试任务定义
- **ACTION**: "给 harnessFlow 加一份 self-test 脚本 `scripts/self-test.sh`，输出设计见上文"
- **GOTCHA**: 这是 harnessFlow 的真 feature（README/QUICKSTART 都会引用），不是为验证造的假任务

#### Task 8.1.2: IMPL — 写脚本
- **ACTION**: 新建 `harnessFlow /scripts/self-test.sh`
- **IMPLEMENT**: 6 个检查模块，每个独立输出 `[PASS/FAIL] <desc>`；累计 fail_count 决定 exit 码
- **MIRROR**: `harnessFlow /setup.sh` 的 shell 风格（set -eu / 清晰输出）
- **VALIDATE**: `bash harnessFlow\ /scripts/self-test.sh; echo "exit=$?"` exit=0

#### Task 8.1.3: VERIFY — DoD 验证
- **DoD_SELF_TEST** 表达式（本 plan § Patterns to Mirror 应补充；这里先列）：
  ```python
  DoD_SelfTest = (
      file_exists("harnessFlow /scripts/self-test.sh")
      AND shell_exit_code("bash harnessFlow\\ /scripts/self-test.sh") == 0
      AND stdout_contains("[PASS]") >= 6  # 6 个模块全 PASS
      AND stdout_contains("[FAIL]") == 0
      AND pytest_exit_code("harnessFlow /") == 0  # 85 pytest 不回归
  )
  ```
- **VALIDATE**: verifier_report.verdict=PASS

#### Task 8.1.4: RETRO_CLOSE + commit
- **ACTION**: 产 retro 11 段 + archive 一条 entry
- **ARTIFACT**: 四件套 + self-test.sh 可被其他人独立跑

---

### § 8.2 子 phase — archive CLI 入口（预算 2h）

**目标**：用 harnessFlow 跑通一次"Python feature" + M 体量 + 半可逆任务；被试任务 = **给 archive/ 加 CLI 入口** `python -m archive <subcommand>`，支持：
1. `python -m archive list [--recent N]` — 列最近 N 条 failure-archive.jsonl 条目（summary）
2. `python -m archive audit --dry-run` — 手动触发审计（interval=1），不写文件，仅 stdout 展示 suggestions
3. `python -m archive stats` — 汇总各 `(task_type, size, risk, error_type)` 出现次数

这三个命令是 harnessFlow **日常运维**真需要的：用户想回头看 harnessFlow 最近识别了哪些假完成、哪条路线失败率高、建议降哪条的权重。

预期走 **路线 B**（轻 PRP）。

#### Task 8.2.1: 被试任务定义
- **ACTION**: "给 harnessFlow/archive/ 加 CLI 入口（Python __main__.py）支持 list/audit/stats 子命令"
- **GOTCHA**: 半可逆（新增模块，不改现有 public API）；若改动 writer.py/auditor.py 现有函数签名 → 视为不可逆 → 走 C 路线

#### Task 8.2.2: IMPL — 新建 __main__.py
- **ACTION**: 新建 `harnessFlow /archive/__main__.py`
- **IMPLEMENT**: `argparse` 分发 3 个子命令；`list` 读 jsonl 末 N 行；`audit` 调 `audit(dry_run=True)`（或临时 archive_path 技巧）；`stats` groupby 聚合
- **MIRROR**: Python `python -m <pkg>` 入口惯例；writer.py 的 fcntl lock pattern 不需要复用（只读操作）
- **GOTCHA**: `python -m archive` 需要 `archive/` 是 package（已是，__init__.py 存在）；CWD 依赖 archive_path 默认值要健壮（相对 `harnessFlow /failure-archive.jsonl`）

#### Task 8.2.3: 写单测
- **ACTION**: `archive/tests/test_cli.py` 三个 case：list/audit/stats 各 subprocess.run 一次，断言 exit=0 + stdout 非空
- **VALIDATE**: pytest 新增 3 个 case 全绿；总数 85 → 88

#### Task 8.2.4: VERIFY — DoD_ARCHIVE_CLI
```python
DoD_ArchiveCLI = (
    file_exists("harnessFlow /archive/__main__.py")
    AND shell_exit_code("python3 -m archive list --recent 1") == 0
    AND shell_exit_code("python3 -m archive audit --dry-run") == 0
    AND shell_exit_code("python3 -m archive stats") == 0
    AND pytest_exit_code("harnessFlow /archive/tests/test_cli.py") == 0
    AND git_diff_lines("harnessFlow /archive/writer.py") == 0  # 不改原库
    AND git_diff_lines("harnessFlow /archive/auditor.py") == 0
)
```

#### Task 8.2.5: RETRO_CLOSE + commit
- **ARTIFACT**: 四件套 + CLI 可在 README/QUICKSTART 里引用（"运维命令"章节）

**陷阱预期**：Supervisor 在 IMPL 阶段可能触发 INFO 级干预（如"`audit --dry-run` 是新参数吗？auditor 原 API 有吗"）→ 回答"不改原 API，在 __main__.py 里临时造一个内存 archive 跑"。**用户打断 = 0** 是目标。

---

### § 8.3 子 phase — P20 真出片验证（预算 4-6h，压轴）

**目标**：用 harnessFlow 跑通一次"视频出片" + XL 体量 + 不可逆任务；**被试任务 = 真正的 P20 出片**（即当年假完成的同一个任务）；预期走 **路线 C**（C 路线 = 全 PRP + 三段证据强验证）。

#### Task 8.3.1: 选被试任务
- **ACTION**: 定义任务："跑一次 aigcv2 完整出片流程：选一个素材话题 → 生成脚本 → 生成视频 → 上传 OSS → playback check"
- **IMPLEMENT**: 输入 query 选用中等复杂度（如 "开飞船炸月球"，参考 e2e_runner.py 默认示例）
- **GOTCHA**: P20 原始场景要求 15s-60s 视频，避免选过长导致 Phase 8 超预算

#### Task 8.3.2: 激活 /harnessFlow + 澄清
- **ACTION**: `/harnessFlow 请帮我跑一次真出片流程验证 Phase 8，素材 query = "开飞船炸月球"，长度 30s`
- **VALIDATE**: task-board 创建 `p8-3-p20.json`，`task_type=视频出片`, `size=XL`, `risk=不可逆`

#### Task 8.3.3: 路由决策 — **必走 C 路线**
- **ACTION**: routing-matrix (视频出片 × XL × 不可逆) → 推荐 C；用户选 C
- **GOTCHA**: 不可逆 + XL 触发 E_LEVEL_3_MAX_VIGILANCE（method3 § 5.2 + supervisor § 3）
- **VALIDATE**: `route_id="C"`; Supervisor 拉起

#### Task 8.3.4: PLAN 阶段
- **ACTION**: 主 skill 调本 plan 同款 /prp-plan 产出 `p8-3-p20-impl.plan.md`
- **IMPLEMENT**: plan 内容 = 调 e2e_runner.py --round N --query "..." 或直接 API 调用序列
- **VALIDATE**: plan 文件存在，含"启动 uvicorn"和"POST /api/pipelines"步骤

#### Task 8.3.5: CHECKPOINT_SAVE（不可逆前置）
- **ACTION**: 不可逆任务强制 checkpoint（state-machine § 3 + supervisor § 干预 6）
- **IMPLEMENT**: `git status`（确认工作区干净）；保存当前 task_board 快照
- **VALIDATE**: `sessions/p8-3-p20-checkpoint-<ts>.json` 产出

#### Task 8.3.6: IMPL 阶段 — 启动 uvicorn + 触发出片
- **ACTION**:
  ```bash
  cd aigc/backend && source .venv/bin/activate
  uvicorn app.main:app --port 8000 &  # 后台启
  sleep 5  # 等启动
  python scripts/e2e_runner.py --round 8 --query "开飞船炸月球"
  ```
- **IMPLEMENT**: 监控 pipeline 日志，记录每节点状态；预计 30-60 min
- **GOTCHA**: Seedance 配额 / 火山方舟限流 / OSS 网络问题都可能中断 — 触发 L1/L2 重试（见 state-machine § 7）；每次重试记 `task_board.retries[]`
- **VALIDATE**: 终态 mp4 在 `aigc/backend/media/videos/<video_id>/final.mp4`；OSS key 在数据库 `videos` 表（或 API 返回体）

#### Task 8.3.7: VERIFY 阶段 — 跑 DoD_P20 全套 8 个子契约
- **ACTION**: Verifier subagent 独立 spawn，eval DoD_P20（见 Patterns to Mirror）
- **IMPLEMENT**: 8 个 primitive 依次跑（file_exists → size → ffprobe → playback → oss_head → uvicorn → curl → schema_valid）
- **GOTCHA**: 任一失败 → verdict=FAIL → red_line=DOD_GAP_ALERT → 进 PAUSED_ESCALATED
- **VALIDATE**:
  - `verifier_report.verdict=PASS`（理想）或 `FAIL`（可接受，但必须有 retro 记录"为什么"）
  - `evidence_chain` 三段都非空

#### Task 8.3.8: RETRO_CLOSE — C 路线强制链
- **ACTION**: retro-generator + failure-archive-writer 两 subagent 顺序跑
- **IMPLEMENT**: 按 § 8.6 伪代码；retro 11 段要**手动填 8-11 项** retro_notes（C 路线强烈推荐，见 retro-generator.md § 4）
- **VALIDATE**:
  - `retros/p8-3-p20.md` 存在 + 11 段 + 8-11 项非 `<待人工补充>`（若全是占位符，说明用户没填 notes，Phase 8 交付不达标）
  - `failure-archive.jsonl` append 一条 `error_type` 合理（若 PASS 可能 `NO_ERROR`；若 FAIL 按实际原因归类）
  - `archive_entry_link` 含 `#L<n>`

#### Task 8.3.9: Stop gate + commit + 8.3 retro 总结
- **ACTION**: Stop hook 自动校验；git commit
- **VALIDATE**:
  - Stop gate 全绿（retro 11 段 + archive_entry_link + schema valid + final_outcome ∈ enum）
  - 若 Stop gate FAIL：调查原因，修 task-board 字段（不改 hook 逻辑），再跑
- **ARTIFACT**: 8.3 四件套 + 真实 mp4 本地路径 + OSS URL 截图

---

### § 8.4 Phase 8 总收口（预算 30min）

#### Task 8.4.1: 写 Phase 8 validation report
- **ACTION**: 创建 `harnessFlow /phase8-validation-report.md`，汇总：
  - 每子 phase 结果（4 个表格：8.0/8.1/8.2/8.3）
  - 三项指标统计（真完成率 / 用户打断次数 / Verifier verdict 分布）
  - 发现的 Phase 9 候选改进项（期望 3-5 条）
  - P20 事件自举验证结论：harnessFlow 这次跑 P20 是 PASS 了吗？如果没 PASS，是不是 Phase 7 之前的系统也会错过？
- **IMPLEMENT**: 用 markdown 表格 + 短小结；避免长文
- **VALIDATE**: 文件存在，含上述 4 个章节

#### Task 8.4.2: 更新 PRD Phase 8 行 → complete
- **ACTION**: edit `harness-flow.prd.md` Phase 8 行 `in-progress` → `complete`；在 Phase Details 加 Delivered 小节（模仿 Phase 7）
- **VALIDATE**: `grep "Phase 8" harness-flow.prd.md` 显示 `complete`

#### Task 8.4.3: Phase 8 整体 commit + PR
- **ACTION**:
  ```bash
  git commit -m "docs(harnessFlow): Phase 8 — 端到端验证 3 真任务 MVP 真完成率 100%"
  gh pr create --title "..." --body "..."
  ```
- **VALIDATE**: git log 最新 commit；PR URL 返回给用户

---

## Testing Strategy

### 单元测试

Phase 8 不引入新 pytest 测试（Phase 1-7 的 85 个测试已 green），但每子 phase 结束时**全量重跑**一次 pytest 防回归：

```bash
cd "/Users/zhongtianyi/work/code/harnessFlow " && python3 -m pytest -x -q
```
EXPECT: 85 passed

### Edge Cases Checklist

- [ ] Skill 不激活（`/harnessFlow` 打错 / symlink 断）
- [ ] Subagent 拉不起来（name namespace 不匹配）
- [ ] Hook 路径空格问题（settings.json 里 bash 命令引用）
- [ ] Stop gate 在 PAUSED_ESCALATED 状态被触发（应 exit 0 通过）
- [ ] P20 跑一半 Ctrl-C（检查 task-board 是否落到 ABORTED + archive 一条 `final_outcome=aborted`）
- [ ] Verifier 返 INSUFFICIENT_EVIDENCE 两次 → IMPL↔VERIFY 死循环 → 应被 cap=2 打破（state-machine § 7 P3 分支）
- [ ] 用户跨 session 继续 8.x（通过 sessions/ 保存的 checkpoint 恢复）

---

## Validation Commands

### 全链路 smoke（§ 8.0 末尾）
```bash
ls -la .claude/skills/harnessFlow.md .claude/agents/harnessFlow-*.md
jq '.hooks' .claude/settings.local.json
bash "harnessFlow /hooks/Stop-final-gate.sh"; echo "smoke exit=$?"
```
EXPECT: symlinks 4 个 + hooks 2 个 + Stop gate exit 0

### 子 phase 收口（每个 8.x 末尾）
```bash
jq '.current_state, .final_outcome, .retro_link, .archive_entry_link' "harnessFlow /task-boards/p8-<N>-<name>.json"
cat "harnessFlow /verifier_reports/p8-<N>-<name>.json" | jq '.verdict, .red_lines_detected'
grep -c "^## " "harnessFlow /retros/p8-<N>-<name>.md"  # 应 >= 11
```
EXPECT: state=CLOSED, final_outcome=success/failed/aborted/false_complete_reported, retro ≥ 11 段

### Phase 8 全局（§ 8.4.2 前）
```bash
cd "/Users/zhongtianyi/work/code/harnessFlow " && python3 -m pytest -x -q
ls retros/p8-*.md | wc -l  # 应 >= 3（8.1/8.2/8.3；8.0 豁免）
wc -l failure-archive.jsonl  # 应 >= 3
```
EXPECT: 85 passed, 3 retros, 3+ archive entries

### 手动验证清单
- [ ] 8.0 Smoke 成功（skill 被识别 + hook 跑了）
- [ ] 8.1 Vue 页面能在浏览器真访问 + screenshot 有内容
- [ ] 8.2 后端端点能 curl + pytest 绿
- [ ] 8.3 mp4 能本地播放 + OSS URL 能 HEAD 200
- [ ] 每子 phase 的 retro 11 段都非空（至少 1-7 项；8-11 项若未手填允许占位）
- [ ] Stop gate 在每子 phase 收口时都 exit 0

---

## Acceptance Criteria

- [ ] 4 子 phase 全部走完（8.0/8.1/8.2/8.3），不可跳过
- [ ] 三任务（8.1/8.2/8.3）**真完成率 = 100%**（verdict=PASS 且 artifact 可被第三方独立验证）
- [ ] 三任务各自**用户打断 ≤ 1 次**（task_board.red_lines 含 `废问题` 或 `supervisor_interventions` 含"用户主动打断"事件最多 1 条）
- [ ] 三任务 Verifier 全 **verdict=PASS**，`red_lines_detected=[]`
- [ ] 三任务 retro 全**自动生成**（主 skill 不经用户手催自动拉起 retro-generator）+ 含 11 段
- [ ] failure-archive.jsonl **schema 合法**（jsonschema 能 validate 所有新增行）
- [ ] Stop gate 每次 **exit 0**
- [ ] 85 pytest 全绿，无回归
- [ ] Phase 8 validation report 产出（不是自动生成，手写 + 引用四件套）
- [ ] PRD Phase 8 行 `complete`；commit + PR（非必需但推荐）

---

## Completion Checklist

- [ ] `.claude/skills/harnessFlow.md` 软链生效
- [ ] `.claude/agents/harnessFlow-*.md` × 4 生效
- [ ] `.claude/settings.local.json` hooks 两条注册（合并不覆盖）
- [ ] 8.0 smoke task-board CLOSED + Stop gate 过
- [ ] 8.1/8.2/8.3 四件套 × 3 完整
- [ ] `harnessFlow /phase8-validation-report.md` 写完
- [ ] PRD Phase 8 更新为 complete + Delivered 小节
- [ ] 85 pytest 全绿
- [ ] 两次 git commit（8.0 infra + Phase 8 收口）
- [ ] 若发现 Phase 1-7 的 bug：不当场改，只记进 phase8-validation-report.md 的 Phase 9 候选清单

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `/harnessFlow` 不被识别（skill symlink 问题） | 中 | 阻塞 8.1 起 | Task 8.0.1 手工验证 symlink + Claude Code 重启 |
| 目录名带空格导致 hook shell 脚本路径破 | 高 | 阻塞 8.0 起 | 所有命令用 `"..."` 引号包路径，避免 `$(pwd)` 字面存储 |
| P20 真出片 Seedance 配额耗尽 | 中 | 8.3 失败 | 提前检查配额 / 选短视频 / 允许 verdict=FAIL 但 retro 完整（失败也算 Phase 8 交付） |
| OSS 上传超时 | 中 | 8.3 verifier FAIL | retry L1 两次（state-machine § 7）；若持续失败，retro 记 trap `P20-oss-upload-timeout` |
| 跨 session 恢复失败（sessions/ 数据丢失） | 低 | 8.3 重跑 | checkpoint 放 git；每子 phase 独立 commit 降低 blast radius |
| 用户打断超 1 次 | 中 | 打断次数指标不达标 | 任务选"明确可操作"（不选纯开放性探索）；提前读本 plan 知道要做什么 |
| Verifier FAIL 但被接受为"Phase 8 pass" | 中 | 真完成率指标虚高 | 采信 verifier.verdict，不人为改判；FAIL 也算交付（进 retro）但记入真完成率分母 |
| Stop gate 因非 Phase 8 相关 board 误阻 | 低 | 阻塞收口 | hook 会遍历所有 boards；如果历史 board 未清理，先 mv 到 archive 目录 |

---

## Notes

### 自举验证的特殊性

Phase 8 是一次**自举验证**（bootstrapping validation）：用 harnessFlow 自己验证 harnessFlow。这有两个好处：
- 如果 harnessFlow 连自己都验证不通，一定不能验证别的东西 → 强信号
- Phase 8 过程本身就是一次 P20 类任务的"正例"（Phase 8 = 元技能验证 × XL × 半可逆），P20 事件即是本项目立项动因，用它当被试任务 = 闭环

### 成败判据的非对称性

> 真完成率 100% 是硬指标，但 verdict=FAIL 不等于 Phase 8 失败。

如果 8.3 P20 跑完 Verifier 返 FAIL（例如 Seedance 配额耗尽），但**harnessFlow 正确识别 FAIL + 拉起 retro + 归档 + Stop gate 不误放**，那 Phase 8 本身是**成功的**（证明 harnessFlow 识别假完成的机制有效）。真完成率分母在这种情况下也按 1/3 计（即 8.3 不算真完成），但 Phase 8 可以 `complete`。

这个判据差异要在 phase8-validation-report.md 里明确写出来，避免混淆"MVP 真完成率"和"harnessFlow 识别能力"。

### Phase 9 候选的主要来源

Phase 8 跑下来，**一定**会发现 Phase 1-7 的若干缺陷。期望来源：
- Supervisor 规则粒度（太细/太粗）
- Verifier DoD 表达式模板不够（某些任务类型缺模板）
- retro 11 段中 8-11 项手填门槛太高（LLM 辅助填写候选）
- auditor 阈值（每 20 条是否太宽/太紧）
- Stop gate 跨 session 状态持久化（sessions/ 目前只做 checkpoint）
- trap catalog 结构化（method3 § 6.4 只在文档里，Phase 8 可能产出 3-5 个 trap 进 trap-catalog.jsonl 候选）

这些都不在 Phase 8 scope 内（见 NOT Building），但 Phase 8 的 validation-report 要**列出来**，Phase 9 主理。

### 与 Claude Code effortLevel=xhigh 的交互

本 session 已配置 max effort，这意味着 Claude Code 会自动用 Opus 模型跑完整 harnessFlow + verifier 的深推理。这对 Phase 8 是必要的（P20 类任务在 sonnet 上经常触发假完成）。若 Phase 8 跑到一半切 haiku 或 low effort，**立刻停止**并升档。
