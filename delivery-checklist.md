# delivery-checklist.md

**版本**: v1.0 (2026-04-16)
**Status**: DRAFT（Phase 4 产出）
**Readers**: 主 skill (Phase 5) / Verifier (Phase 6) / retro 模板

> 本文档按路线分组给出**收口证据清单**：artifact 存在证据 + 行为证据 + 质量证据 + retro 完整性证据。主 skill 在进入 `@COMMIT` 状态前必须过清单所有项；任一缺失 → 阻断 commit，转 `PAUSED_ESCALATED` 等用户决策。
>
> DoD 布尔表达式定义在 `method3.md § 6.1`（表达式库）；本文档提供的是**人类可读 checklist 视图**，Verifier 用 § 6.1 表达式做机器 eval，用户和 retro 用本文档做复核。

---

## § 0 三段证据链（所有路线共用）

任何路线收口都必须过**三段证据链**：

| 证据段 | 含义 | 典型证据形式 | Verifier 原语（method3 § 6.1） |
|---|---|---|---|
| **存在证据** | artifact 物理存在 | 文件存在 / HTTP 200 / OSS key HEAD 200 / PR URL 有效 | `file_exists` / `http_status_is` / `oss_head` / `pr_exists` |
| **行为证据** | artifact 可以被执行/消费 | pytest 跑过 / curl 返回预期 JSON / playback 可播 / 服务响应 | `pytest_exit_code` / `curl_status` / `curl_json` / `playback_check` / `uvicorn_started` |
| **质量证据** | artifact 符合语义预期 | schema_valid / review_verdict == PASS / diff 在范围 / screenshot 非空 | `schema_valid` / `code_review_verdict` / `diff_lines_net` / `screenshot_has_content` |

**收口 gate 硬规则**：
- 三段缺任一段 → Verifier 返回 `INSUFFICIENT_EVIDENCE` → state-machine E13 → `PAUSED_ESCALATED`
- 任何一段失败 → `FAIL` → state-machine E11 → `SANTA_LOOP`
- 三段全绿 → `PASS` → 若 `red_lines[] == []` 进 `COMMIT`（verifier_report § state-machine § 7）

---

## § 1 路线 A — 零 PRP 直改（XS）

**场景**: typo / docstring / 单函数 bug

### ✓ 存在证据
- [ ] diff 产出（git status 显示修改）
- [ ] 修改文件路径记录到 `artifacts[]`

### ✓ 行为证据
- [ ] `pytest <focused_test>` exit_code == 0
- [ ] 改动未破坏其他测试（`pytest` 全量或相邻模块）

### ✓ 质量证据
- [ ] diff 行数 < 50 且改动范围单文件
- [ ] 公共 API 签名未变（`no_public_api_breaking_change()`）

### ✓ retro 证据
- [ ] A 路线可跳过 retro，但 task-board 必须写 `final_outcome=success`

**DoD 表达式（引 flow-catalog § 2）**：
```
DoD = (pytest_exit_code(<focused_test>) == 0)
  AND (diff_lines_net < 50)
  AND (no_public_api_breaking_change())
```

---

## § 2 路线 B — 轻 PRP 快速交付（S-M）

**场景**: 单模块小 feature / 中等 bug fix

### ✓ 存在证据
- [ ] 改动文件列表 + 每文件 diff 入 `artifacts[]`
- [ ] plan 文件存在（`plans/<task>.plan.md`）

### ✓ 行为证据
- [ ] `pytest "<module>"` exit_code == 0
- [ ] 若含新 controller：`curl_status` 对应路由 == 200
- [ ] 若含 schema 变更：`schema_valid(curl_json, schemas/...)` == True

### ✓ 质量证据
- [ ] `code_review_verdict == "PASS"`（ECC code-reviewer）
- [ ] `diff_lines_net < 500`
- [ ] 无 critical review 反馈未解决

### ✓ retro 证据
- [ ] 轻量 retro 文件存在（≥ 100 字 + 至少覆盖"这次做对/做错/下次")
- [ ] task-board `retro_link` 非空

**DoD 表达式（引 flow-catalog § 3；按任务子类可选附加项）**：

```
# 基线（所有 B 任务必须满足）
DoD_base = (pytest_exit_code("<module>") == 0)
       AND (code_review_verdict == "PASS")
       AND (diff_lines_net < 500)

# 附加项（按子类叠加）
if has_new_controller:
    DoD = DoD_base AND (uvicorn_started("localhost:8000"))
                  AND (curl_status("<endpoint>") == 200)

if has_schema_change:
    DoD = DoD AND (schema_valid(curl_json("<endpoint>"), "<schema>"))
```

**scope 爆炸护栏**：diff > 500 行 → 阻断 commit，转升级到路线 C（flow-catalog § 8.1）。

---

## § 3 路线 C — 全 PRP 重验证（L-XL，**MVP 主路线**）

**场景**: 跨模块 feature / 视频出片 / 大重构 / 不可逆操作

按任务类型细分 checklist（与 method3 § 6.1 DoD 模板库对齐）：

### 3.1 通用 C 路线 checklist（所有 C 任务必过）

#### ✓ 存在证据
- [ ] plan 文件存在（`plans/<task>.plan.md`，≥ 50 行）
- [ ] PRD 文件存在（若 task 要求 prp-prd）
- [ ] 至少一次 `save-session` checkpoint（task-board `checkpoint_refs[]` 非空）
- [ ] `goal_anchor` 写入 CLAUDE.md 且 hash 与 task-board 一致

#### ✓ 行为证据
- [ ] `pytest` 相关模块全绿
- [ ] 关键 API/service 起动验证通过（见类型细分）
- [ ] 若存在 santa-loop 迭代：`retries[]` 完整记录，最后 retry 对应 `verifier_report.pass_all == True`

#### ✓ 质量证据
- [ ] `code_review_verdict == "PASS"`（并行 code-reviewer）
- [ ] `verifier_report.red_lines_detected == []`
- [ ] 若 size == XL：`mid_retro` 文件存在

#### ✓ retro 证据
- [ ] 强制 11 项 retro 完整填写
- [ ] 若有失败：`failure_archive_refs[]` 非空
- [ ] task-board `final_outcome == "success"`

### 3.2 视频出片专属 checklist（method3 § 6.1 模板 ① + 模板 ② 组合）

**口径声明**：视频出片任务同时消费两张 DoD 模板——模板 ① 管 mp4/OSS/playback 等"媒体 artifact 硬证据"，模板 ② 管后端 `POST /produce` API 的"起动+响应+schema"。本节把两张模板合并成一条 DoD 链（见本节末 DoD 表达式），不能把其中任一段当成"可选"。

叠加 § 3.1 之上：

#### ✓ 存在证据
- [ ] `file_exists("media/<task>.mp4")` == True
- [ ] `oss_head("s3://.../task>.mp4").status_code == 200`
- [ ] mp4 size > 0

#### ✓ 行为证据
- [ ] `ffprobe_duration("media/<task>.mp4") > 0`
- [ ] `playback_check("media/<task>.mp4")` == True（能被 ffplay/mpv 打开）
- [ ] `uvicorn_started("localhost:8000")`
- [ ] `curl_status("POST /produce") == 200`
- [ ] `schema_valid(curl_json("POST /produce"), "schemas/produce_response.json")`

#### ✓ 质量证据
- [ ] 视频分辨率/时长符合预期（`ffprobe_duration` 在 task plan 指定范围内）
- [ ] 无 ffmpeg/ffprobe 报错（`grep_count("error|failed", "logs/ffmpeg.log") == 0`）

#### ✓ retro 证据
- [ ] `retro_exists("harnessFlow /retros/<task>-retro.md")`
- [ ] retro 含"假完成 trap 是否触发"一项（P20 事故教训）

**DoD 表达式（method3 § 6.1 模板①）**：
```
DoD = (file_exists("media/<task>.mp4"))
  AND (ffprobe_duration("media/<task>.mp4") > 0)
  AND (oss_head("s3://.../<task>.mp4").status_code == 200)
  AND (playback_check("media/<task>.mp4"))
  AND (uvicorn_started("localhost:8000"))
  AND (curl_status("POST /produce") == 200)
  AND (schema_valid(curl_json("POST /produce"), "schemas/produce_response.json"))
  AND (retro_exists("harnessFlow /retros/<task>-retro.md"))
```

### 3.3 后端 feature 专属 checklist（method3 § 6.1 模板②对齐）

叠加 § 3.1 之上：

#### ✓ 存在证据
- [ ] 新/改 controller 文件存在
- [ ] 若新 DB 表：migration 脚本存在（`scripts/migrate_*.py`）
- [ ] 若新 schema：`schemas/<name>.json` 文件存在

#### ✓ 行为证据
- [ ] `uvicorn_started("localhost:8000")`
- [ ] `curl_status("<endpoint>") == 200`（happy path）
- [ ] `curl_status("<endpoint>") == 4xx`（错误输入 happy path，若 task 设计含校验）
- [ ] `schema_valid(curl_json("<endpoint>"), "schemas/<response>.json")`
- [ ] `pytest tests/test_<module>.py` 全绿

#### ✓ 质量证据
- [ ] `code_review_verdict == "PASS"`（含 security-reviewer / python-reviewer）
- [ ] 若 migration：`alembic_check` 或等价命令不报 pending

#### ✓ retro 证据
- [ ] 11 项 retro 完整；重点含"API 契约是否外显"（给前端）

### 3.4 不可逆操作 C 路线附加（risk == 不可逆）

叠加前述之上：

#### ✓ 前置检查证据（routing-matrix § 3.2 + method3 § 5.2 IRREVERSIBLE_HALT）

**OSS 生产 bucket 写入（拆成两条互斥条件，必须只满足其一）**：
- [ ] 条件 A — 视频出片豁免：task 属 **method3 § 5.2 豁免清单**（视频出片，幂等覆盖旧 key） **且** DoD 含 `oss_head(<key>).status_code == 200` 证明写入落地
- [ ] 条件 B — 其他生产 bucket 写：用户显式 `/approve irreversible-<task_id>` 登记在 `red_lines[]` **且** DoD 含 `oss_head.status_code == 200`

其他不可逆动作：
- [ ] 若 DB migration destructive：migration 脚本含 downgrade 或备份命令
- [ ] 若 prod push：PR 已过 review + CI 绿
- [ ] 若删数据/`rm -rf`：task-board `red_lines[]` 含用户显式授权 entry

---

## § 4 路线 D — UI 视觉专线（S-M UI）

**场景**: Vue 页面 / Vue Flow / 组件视觉

### ✓ 存在证据
- [ ] 改动 .vue / .ts / .css 文件列表入 `artifacts[]`
- [ ] `screenshot_file_exists("artifacts/<page>.png")`

### ✓ 行为证据
- [ ] `vite_started("localhost:5173")` == True
- [ ] `playwright_nav("http://localhost:5173/<page>").status == "ok"`
- [ ] `playwright_exit_code("e2e/<page>.spec.ts") == 0`
- [ ] `type_check_exit_code == 0`（`npm run type-check`）

### ✓ 质量证据
- [ ] `screenshot_has_content("artifacts/<page>.png")` == True（非空非纯色）
- [ ] `code_review_verdict == "PASS"`（前端 reviewer）
- [ ] 无 console error（`playwright_console_errors == []`）

### ✓ retro 证据
- [ ] 轻量 retro；含"视觉对比 before/after 截图链接"

**DoD 表达式（method3 § 6.1 模板③）**：
```
DoD = (vite_started("localhost:5173"))
  AND (playwright_nav("http://localhost:5173/<new-page>").status == "ok")
  AND (screenshot_has_content("artifacts/<page>.png"))
  AND (playwright_exit_code("e2e/<page>.spec.ts") == 0)
  AND (type_check_exit_code == 0)
```

**screenshot 作假防护**：`screenshot_has_content` 必须验证 SHA 不同于"全白/全黑基准图"，且 pixel entropy > 阈值（flow-catalog § 5 风险点）。

---

## § 5 路线 E — agent graph 专线（L-XL）

**场景**: LangGraph 节点 / subgraph / 编排调整

### ✓ 存在证据
- [ ] 改动 graph/node 文件 + state TypedDict 文件入 `artifacts[]`
- [ ] `graph_diff.md` 文件存在（before/after graph 对照）
- [ ] 若 state 新增字段：migration 脚本存在

### ✓ 行为证据
- [ ] `pytest_exit_code("tests/test_graph_<name>.py") == 0`
- [ ] `pytest_exit_code("tests/test_<node>_unit.py") == 0`（每节点独立单测）
- [ ] `graph_compile_success("app.graphs.<graph_name>") == True`
- [ ] 若含真出片：叠加 § 3.2 视频 checklist

### ✓ 质量证据
- [ ] `eval_regression_delta("<downstream_nodes>") < 0.05`（回归）
- [ ] `code_review_verdict == "PASS"`
- [ ] 无 graph 环路（`graph_has_cycle` == False）

### ✓ retro 证据
- [ ] 11 项 retro；含"节点输入/输出 schema 是否外显"

**DoD 表达式（flow-catalog § 6）**：
```
DoD = (pytest_exit_code("tests/test_graph_<name>.py") == 0)
  AND (pytest_exit_code("tests/test_<node>_unit.py") == 0)
  AND (eval_regression_delta("<downstream_nodes>") < 0.05)
  AND (graph_compile_success("app.graphs.<graph_name>") == True)
  AND (code_review_verdict == "PASS")
```

---

## § 6 路线 F — 研究方案探索

**场景**: 选型 / 调研 / 决策前置

### ✓ 存在证据
- [ ] `file_exists("<decision_log>.md")` == True
- [ ] 决策 log 含时间戳 + retrieved 日期
- [ ] 若 WebSearch 引用：URL 列表入决策 log

### ✓ 行为证据
- [ ] F 不写代码，行为证据 = 决策 log 可被读 + 可被后续路线引用
- [ ] `wc_lines("<decision_log>.md") >= 200`

### ✓ 质量证据
- [ ] `grep_count("^## 选项", "<decision_log>.md") >= 2`（至少 2 个方案对比）
- [ ] `grep_count("^## 决策", "<decision_log>.md") == 1`（唯一决策结论）
- [ ] 若决策涉及外部库：`docs-lookup` 至少引 1 条官方文档

### ✓ retro 证据
- [ ] 决策型 retro；含"本次调研是否需要 POC 验证"

**DoD 表达式（flow-catalog § 7）**：
```
DoD = (file_exists("<decision_log>.md"))
  AND (wc_lines("<decision_log>.md") >= 200)
  AND (grep_count("^## 选项", "<decision_log>.md") >= 2)
  AND (grep_count("^## 决策", "<decision_log>.md") == 1)
  AND (retro_exists("harnessFlow /retros/<task_id>.md"))
```

---

## § 7 retro 触发 gate（证据缺失 → 阻断 commit）

### 7.1 gate 决策树

**口径同 state-machine § 7**（三态 verdict + 红线优先）。checklist 视角的"三段证据"最终被 Verifier 编译成 PASS / FAIL / INSUFFICIENT_EVIDENCE 三种 verdict 之一：

```
Verifier 产出 verifier_report 后：
│
├── P0 [红线优先]: red_lines_detected != []
│      → PAUSED_ESCALATED（无论 overall，红线不可被 DoD 绕过）
│
├── P1 [PASS]: overall == "PASS"
│      → 允许 prp-commit（本 checklist 全绿）
│
├── P2 [FAIL]: overall == "FAIL"（存在证据 OR 行为证据 OR 质量证据中任一段有 FAIL）
│      ├── route_id == A        → PAUSED_ESCALATED（A 无 santa-loop）
│      ├── ladder 未耗尽        → SANTA_LOOP（进 retry 修 IMPL）
│      └── ladder 耗尽          → PAUSED_ESCALATED
│
└── P3 [INSUFFICIENT_EVIDENCE]: overall == "INSUFFICIENT_EVIDENCE"（artifact/证据缺失但布尔表达式 True）
       ├── 计数 < 2 → 回 IMPL 补证据（红线 append DOD_GAP_ALERT）
       └── 计数 ≥ 2 → PAUSED_ESCALATED（模板或 DoD 表达式本身有漏洞）
```

**checklist 对 verdict 的贡献**：
- 存在证据缺 / retro 证据缺 → 映射 INSUFFICIENT_EVIDENCE（artifact 或 retro_link 字段物理缺失）
- 行为证据 / 质量证据 FAIL → 映射 FAIL（DoD 原语 eval 为 False）
- 任何段触发红线（§ 3.4 不可逆） → 红线登记进 `red_lines_detected`

### 7.2 Stop hook 兜底

若主 skill 异常绕过 gate 直接进 `CLOSED`（bug 或 人为），Stop hook（Phase 6 落地，Phase 7 升级）在 session 结束前读 `task-board.verifier_report` + `artifacts[]` + `retro_link` + `archive_entry_link` + `final_outcome`：

- `verifier_report` 为 `null` → force escalate（红线 log + 阻断 session 正常退出）
- `artifacts[] == []` **且** `route_id != F` → force escalate（F 路线仅需 decision_log artifact，其他路线必须有硬证据）
- `retro_link` 为 `null` **且** `route_id != A` → force escalate（A 路线按 § 1 允许跳过 retro，其他路线强制）
- `retro_link` 存在但 `retros/<task_id>.md` **缺任一 11 项 section 标题**（`grep "^## <n>\."` 计数 < 11） → force escalate（Phase 7：retro 必须 11 项齐全；标题见 `schemas/retro-template.md` § 1-11）
- `archive_entry_link` 为 `null` **且** `route_id != A` → force escalate（Phase 7：非 A 路线必写 `failure-archive.jsonl`）
- `archive_entry_link` 指向的 jsonl 行**未通过 `schemas/failure-archive.schema.json` 校验**（Stop hook 调 `jsonschema.validate`） → force escalate
- `final_outcome` 不在 `{success, failed, aborted, false_complete_reported}` → force escalate（未写终结即宣告关闭违反 GATE_PREDICATES["CLOSED"]；`false_complete_reported` 是 Phase 7 新增枚举值，专记 "impl 声称 PASS 但 Verifier 捞出 DoD_GAP"）
- `verifier_report.red_lines_detected != []` → force escalate（红线任务不能进 CLOSED）

### 7.3 IRREVERSIBLE_HALT 交叉引用

不可逆风险任务在进 `@COMMIT` 前**额外**过 routing-matrix § 3.2 前置检查：

| 动作类别 | 前置 | 本 checklist 对应 |
|---|---|---|
| OSS 非幂等覆盖写（生产 bucket） | `oss_head.status_code == 200` | § 3.4 |
| DB migration（destructive） | migration 含 downgrade/备份 | § 3.4 |
| prod push | PR 已 review + CI 绿 | § 3.4 |
| 删数据 / `rm -rf` | 用户显式授权 | § 3.4 + red_lines[] |

---

## § 8 checklist 使用协议（主 skill / Verifier 流程）

### 8.1 主 skill 进入 @VERIFY 状态时

1. 读 `task-board.route_id` → 查本文档对应 § 1-6 checklist
2. 读 `task-board.task_type` + `risk` → 叠加细分 checklist（§ 3.2/3.3/3.4）
3. 生成 `dod_expression`（method3 § 6.1 表达式）
4. 调 `harnessFlow:verifier` 执行 eval

### 8.2 Verifier 产出 `verifier_report` 字段对应

- `primitives_resolved[]` ↔ 本文档每 checklist item 的 Verifier 原语
- `failed_conditions[]` ↔ 本文档 checklist 的 ❌ 项
- `red_lines_detected[]` ↔ 本文档 § 3.4 / § 7.3 不可逆检查失败

### 8.3 retro 写入契约

retro（Phase 7 产出 auto-retro 模板）必须含：
- 每 checklist item 对应的实际证据记录
- 未过项的原因 + 修复 commit SHA
- 若 red_line 触发：case 归因 + 后续进化建议写 `evolution_suggestions[]`

---

## § 9 扩展位（新路线 checklist）

新增路线（G+）引入本文档新章节，遵循统一结构：
1. 场景描述
2. 三段证据清单（存在 / 行为 / 质量 / retro）
3. DoD 表达式（引 method3 § 6.1）
4. 路线特有风险点

变更必须与 `flow-catalog.md` + `routing-matrix.md` + `method3.md § 6.1` 同步（见 flow-catalog § 9.2 版本化规则）。

---

*本文档定义 6 条路线的收口证据清单 + 三段证据链。DoD 表达式见 method3.md § 6.1；状态机转移见 state-machine.md；字段 schema 见 task-board-template.md。*

*— v1.0 end —*
