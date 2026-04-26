"""Pipeline catalog — 13-node DAG ported from v5 visual companion.

Source: docs/superpowers/specs/_visuals/2026-04-26-pipeline-graph-A-options.html
  - NODE_DATA  (lines 815-994):  status / phase / owner_skill / inputs / outputs
  - NODE_TEMPLATES (lines 1001-1595):  internal_workflow + output_templates
  - SVG layout (lines 220-373):  node x/y/w/h + edges + labels

NODE_CATALOG is the single source of truth (`global shared`); per-task pipeline
view is computed by `derive_pipeline_view(task_board)` which overlays
status/timing/actual-outputs from the task-board's state_history + stage_artifacts.
"""
from __future__ import annotations

from typing import Any


# =============================================================================
# NODE_CATALOG — 13 nodes (Initiating ▸ Planning ▸ Executing ▸ M&C ▸ Closing)
# =============================================================================

NODE_CATALOG: list[dict] = [
    # -------------------- Initiating --------------------
    {
        "id": "N1",
        "name": "任务采集",
        "code": "task_intake",
        "phase": "Initiating",
        "owner_skill": "superpowers:brainstorming §1 + harnessFlow §2",
        "step": 1,
        "layout": {"x": 15, "y": 170, "w": 105, "h": 60},
        "inputs": [
            {"name": "user_request", "type": "string", "from": "user", "field": "cli:/harnessFlow + 原始描述", "required": True, "desc": "用户原始一句话请求"},
            {"name": "claude_md_existing", "type": "md", "from": "file", "field": "CLAUDE.md (if exists)", "required": False, "desc": "已有项目上下文"},
            {"name": "memory_feedback", "type": "string[]", "from": "memory", "field": "MEMORY.md → feedback_*.md", "required": False, "desc": "从 memory 取相关偏好"},
        ],
        "outputs": [
            {"path": "task-boards/<tid>.json#intake", "type": "json", "size_hint": "~1KB", "consumed_by": ["N2", "N3", "N5", "N9"], "schema": "{user_request, size?, task_type?, risk?, clarify_rounds}"},
            {"path": "_derived.intake", "type": "json", "size_hint": "~0.5KB", "consumed_by": ["N3", "N4"], "schema": "{task_id, headline, size_class}"},
        ],
        "internal_workflow": [
            "① 接收用户原始请求 (cli /harnessFlow + 描述文本)",
            "② 读 CLAUDE.md (若存在) + MEMORY.md feedback_*.md",
            "③ 从描述中提取 headline + 关键词 (≤ 10 个)",
            "④ 分配 task_id (UUID v4 or \"p-<slug>-<UTC>\")",
            "⑤ 初始化 task-board.intake，写 captured_at + 起 INIT 状态",
        ],
        "output_templates": [
            {
                "for": "task-boards/<tid>.json#intake",
                "framework": "task-board intake 字段",
                "skeleton": (
                    "{\n"
                    '  "user_request": "<用户原话, 不裁剪>",\n'
                    '  "task_id": "<uuid v4 or p-slug-utc>",\n'
                    '  "headline": "<≤ 30 字提炼>",\n'
                    '  "keywords": ["<kw1>","<kw2>", ...],\n'
                    '  "captured_at": "<UTC ISO 8601>",\n'
                    '  "claude_md_inherited": <bool>,\n'
                    '  "memory_pulled": ["feedback_real_completion.md", ...]\n'
                    "}"
                ),
            },
        ],
    },
    {
        "id": "N2",
        "name": "资料收集",
        "code": "library_collect",
        "phase": "Initiating",
        "owner_skill": "native:Agent(@Explore) + WebSearch + ECC:docs-lookup",
        "step": 2,
        "layout": {"x": 135, "y": 170, "w": 105, "h": 60},
        "inputs": [
            {"name": "raw_request", "type": "string", "from": "N1", "field": "outputs.intake.user_request", "required": True},
            {"name": "task_id", "type": "string", "from": "N1", "field": "outputs._derived.intake.task_id", "required": True},
            {"name": "search_keywords", "type": "string[]", "from": "N1", "field": "outputs._derived.intake.headline (extract)", "required": True, "desc": "从 headline 抽关键词"},
        ],
        "outputs": [
            {"path": "_derived.project_library.docs[]", "type": "json", "size_hint": "~3KB", "consumed_by": ["N3", "N5", "N7"], "schema": "[{url, summary, relevance, captured_at}]"},
            {"path": "_derived.project_library.repos[]", "type": "json", "size_hint": "~0.5KB", "consumed_by": ["N7"], "schema": "[{repo_url, lang, stars, why_relevant}]"},
            {"path": "docs/research/<topic>-references.md", "type": "md", "size_hint": "~2KB", "consumed_by": ["N5", "N7"]},
        ],
        "internal_workflow": [
            "① 从 headline + keywords 抽 5-10 search query",
            "② Agent(@Explore) 跑内部代码 / 文档搜索（仓内）",
            "③ WebSearch + Context7 docs-lookup 跑外部参考",
            "④ 给每条 hit 评估 relevance ≥ 0.7 才入库",
            "⑤ 写 _derived.project_library.{docs, repos, process_docs}",
            "⑥ 落 docs/research/<topic>-references.md（人可读汇总）",
        ],
        "output_templates": [
            {
                "for": "_derived.project_library",
                "framework": "资料登记三层结构",
                "skeleton": (
                    "{\n"
                    '  "docs": [\n'
                    '    { "url": "<https...>", "summary": "<1 句>", "relevance": 0.0-1.0, "captured_at": "<UTC>" }\n'
                    "  ],\n"
                    '  "repos": [\n'
                    '    { "repo_url": "<git>", "lang": "ts|py|...", "stars": <int>, "why_relevant": "<1 句>" }\n'
                    "  ],\n"
                    '  "process_docs": [\n'
                    '    { "path": "<.claude/skills/...>", "type": "skill|template|spec", "why": "<1 句>" }\n'
                    "  ]\n"
                    "}"
                ),
            },
            {
                "for": "docs/research/<topic>-references.md",
                "framework": "可读资料汇总（人查阅用）",
                "skeleton": (
                    "# <topic> 资料汇总\n\n"
                    "## 外部参考 (docs)\n"
                    "- [<title>](<url>) — relevance 0.95 — <1 句价值描述>\n\n"
                    "## 参考 repo\n"
                    "- <repo_url> (lang, stars) — <借鉴点>\n\n"
                    "## 内部 process docs (skill/template/spec)\n"
                    "- <path> — <类型> — <用法>\n"
                ),
            },
        ],
    },
    {
        "id": "N3",
        "name": "目标分析+锁定",
        "code": "goal_analyze_lock",
        "phase": "Initiating",
        "owner_skill": "superpowers:brainstorming + harnessFlow §3.3 goal-anchor",
        "step": 3,
        "layout": {"x": 255, "y": 170, "w": 115, "h": 60},
        "inputs": [
            {"name": "raw_request", "type": "string", "from": "N1", "field": "outputs.intake.user_request", "required": True},
            {"name": "project_library", "type": "json", "from": "N2", "field": "outputs._derived.project_library (全)", "required": True},
            {"name": "memory_clarify_rules", "type": "md", "from": "memory", "field": "feedback_real_completion.md", "required": False, "desc": "\"真完成\" 原则"},
        ],
        "outputs": [
            {"path": "CLAUDE.md#goal-anchor-<tid>", "type": "md", "size_hint": "~1.5KB", "consumed_by": ["N4", "N5", "N12", "N13", "drift hook"], "schema": "goal-anchor block + dimensions"},
            {"path": "_derived.delivery_goal", "type": "json", "size_hint": "~1KB", "consumed_by": ["N4", "N5", "N8", "N12"], "schema": "{purpose, success_criteria, out_of_scope, hash}"},
            {"path": "_derived.dimensions", "type": "json", "size_hint": "~0.2KB", "consumed_by": ["route_select", "N4", "N5"], "schema": "{size, task_type, risk}"},
        ],
        "internal_workflow": [
            "① 读 raw_request + project_library",
            "② superpowers:brainstorming 提问 ≤ 5 轮（multiple-choice 优先）",
            "③ 锁定 (size, task_type, risk) 三维 + out_of_scope 显式枚举",
            "④ 写 CLAUDE.md 新 block: <!-- goal-anchor-<tid> -->...<!-- /goal-anchor-<tid> -->",
            "⑤ 算 sha256(block 全文) → 写 task-board.goal_anchor.hash",
            "⑥ PostToolUse hook 注册 drift 监控 (Edit/Write 触发)",
        ],
        "output_templates": [
            {
                "for": "CLAUDE.md#goal-anchor-<tid>",
                "framework": "goal-anchor 三段式（drift hash 范围）",
                "skeleton": (
                    "<!-- goal-anchor-<tid> -->\n"
                    "## GOAL（受 PostToolUse drift hook 监控）\n"
                    "**一句话目标**: <用户原话提炼>\n\n"
                    "### 技术栈锁（不许偏移）\n"
                    "- <stack item 1>\n"
                    "- <stack item 2>\n\n"
                    "### DoD（VERIFY 阶段必过项）\n"
                    "| # | 验收点 | 验收方式 |\n"
                    "|---|---|---|\n"
                    "| 1 | <criterion> | <verification method> |\n\n"
                    "### Out of scope（本 task 明确不做）\n"
                    "- ❌ <explicit exclusion 1>\n"
                    "- ❌ <explicit exclusion 2>\n\n"
                    "### 风险评估\n"
                    "- size: XS/S/M/L/XL · task_type: <enum> · risk: <enum>\n"
                    "<!-- /goal-anchor-<tid> -->"
                ),
            },
            {
                "for": "_derived.delivery_goal",
                "framework": "goal JSON（drift 算 hash 时同源）",
                "skeleton": (
                    "{\n"
                    '  "purpose": "<text>",\n'
                    '  "success_criteria": ["<sentence 1>", "<sentence 2>"],\n'
                    '  "out_of_scope_explicit": ["<excl 1>", "<excl 2>"],\n'
                    '  "hash": "<sha256 of CLAUDE.md goal-anchor block 全文>",\n'
                    '  "claude_md_path": "<repo>/CLAUDE.md#goal-anchor-<tid>"\n'
                    "}"
                ),
            },
        ],
    },
    {
        "id": "N4",
        "name": "项目章程",
        "code": "project_charter",
        "phase": "Initiating",
        "owner_skill": "ECC:prp-prd §charter",
        "step": 4,
        "layout": {"x": 385, "y": 170, "w": 105, "h": 60},
        "inputs": [
            {"name": "goal_anchor + delivery_goal", "type": "json", "from": "N3", "field": "outputs._derived.delivery_goal + CLAUDE.md goal-anchor", "required": True},
            {"name": "dimensions", "type": "json", "from": "N3", "field": "outputs._derived.dimensions", "required": True, "desc": "决定 milestone 粒度"},
            {"name": "project_library", "type": "json", "from": "N2", "field": "outputs._derived.project_library", "required": False},
            {"name": "task_intake", "type": "json", "from": "N1", "field": "outputs.intake", "required": False},
        ],
        "outputs": [
            {"path": "docs/charter/project-charter.md", "type": "md", "size_hint": "~4KB", "consumed_by": ["N5", "N12"]},
            {"path": "_derived.charter", "type": "json", "size_hint": "~1.5KB", "consumed_by": ["N5", "N9", "N10", "N12"], "schema": "{milestones[], high_level_scope, initial_risks[], stakeholders[]}"},
        ],
        "internal_workflow": [
            "① 读 goal_anchor + dimensions + project_library",
            "② 按 size 派生 milestones 数量（XS→1, S→1-2, M→2-3, L→4-5, XL→6+）",
            "③ 派生 high_level_scope（一段话, 与 PRD §3 不重叠 — A/B 路线可 skip 本节点）",
            "④ 派生 initial_risks（library + dimensions.risk + 经验 5 类）",
            "⑤ 派生 stakeholders（含 supervisor / verifier 内置 + 用户 + 外部依赖人）",
            "⑥ 写 docs/charter/project-charter.md + _derived.charter",
        ],
        "output_templates": [
            {
                "for": "docs/charter/project-charter.md",
                "framework": "PMI Charter 8 章（PMBOK 风格）",
                "skeleton": (
                    "# Project Charter — <task_id>\n\n"
                    "## 1. 项目愿景 (Vision)\n"
                    '<1 段话, 答 "为什么这个项目存在">\n\n'
                    "## 2. 业务目标 (Business Objectives)\n"
                    "- 目标 1: <SMART>\n"
                    "- 目标 2: <SMART>\n\n"
                    "## 3. 范围 (High-Level Scope)\n"
                    "- IN: <高阶范围>\n"
                    "- OUT: <显式排除>\n\n"
                    "## 4. 里程碑 (Milestones)\n"
                    "| MS-ID | 名称 | 目标日期 | 验收门 |\n"
                    "|---|---|---|---|\n"
                    "| MS1 | <ms_name> | <date> | <gate> |\n\n"
                    "## 5. 关键利益相关方 (Stakeholders)\n"
                    "| 角色 | 职责 | 沟通频率 |\n\n"
                    "## 6. 假设与约束 (Assumptions & Constraints)\n"
                    "- 假设: <assumption>\n"
                    "- 约束: <constraint>\n\n"
                    "## 7. 初始风险登记册 (Initial Risk Register)\n"
                    "| RID | 风险描述 | 影响 | 概率 | 缓解策略 | Owner |\n\n"
                    "## 8. 授权 (Authorization)\n"
                    "- 由 user 在 INIT/CLARIFY 阶段隐式签字 (task-board.user_confirmed_at)"
                ),
            },
            {
                "for": "_derived.charter",
                "framework": "charter JSON 可程序化字段",
                "skeleton": (
                    "{\n"
                    '  "milestones": [{ "ms_id": "MS1", "name": "<>", "target_date": "<UTC>", "gate": "<>" }],\n'
                    '  "high_level_scope": { "in": "<text>", "out": "<text>" },\n'
                    '  "initial_risks": [{ "rid": "R1", "desc": "<>", "impact": "L|M|H", "prob": "L|M|H", "mitigation": "<>" }],\n'
                    '  "stakeholders": [{ "role": "<>", "responsibility": "<>" }]\n'
                    "}"
                ),
            },
        ],
    },
    # -------------------- Planning --------------------
    {
        "id": "N5",
        "name": "PRD 编写",
        "code": "prd_write",
        "phase": "Planning",
        "owner_skill": "ECC:prp-prd 阿里风 8 章节",
        "step": 5,
        "layout": {"x": 510, "y": 170, "w": 100, "h": 60},
        "inputs": [
            {"name": "charter", "type": "json+md", "from": "N4", "field": "outputs.charter.md + _derived.charter", "required": True},
            {"name": "goal_anchor", "type": "json", "from": "N3", "field": "outputs._derived.delivery_goal", "required": True},
            {"name": "project_library", "type": "json", "from": "N2", "field": "outputs._derived.project_library (全)", "required": True, "desc": "8章中\"技术方案概要\"和\"风险\"参考"},
        ],
        "outputs": [
            {"path": "docs/prd/prd.md", "type": "md", "size_hint": "~8KB", "consumed_by": ["N6", "N7", "N8"], "schema": "8章: 背景/目标/用户故事/功能需求/验收标准/原型/技术方案/风险"},
            {"path": "docs/prd/prototypes.svg", "type": "svg", "size_hint": "~12KB", "consumed_by": ["N7"]},
            {"path": "_derived.prd", "type": "json", "size_hint": "~6KB", "consumed_by": ["N6", "N7", "N8", "N9"], "schema": "{features[], acceptance_criteria[], user_stories[], risks[]}"},
        ],
        "internal_workflow": [
            "① 读 charter + delivery_goal + project_library (技术方案概要参考)",
            "② §1 背景 — 业务现状 / 痛点 / 机会",
            "③ §2 目标 — 业务目标 / 用户目标 / 衡量指标 (SMART)",
            "④ §3 用户故事 — As-a / I-want / So-that × N",
            "⑤ §4 功能需求 F-table（F1-Fn）",
            "⑥ §5 验收标准 AC-list（TDD 种子，每条对应 N6 的 ≥1 case）",
            "⑦ 🎨 §6 原型设计 — prototypes.svg 必含 ≥ 3 张 wireframe（标题 / 主流程 / 边界）",
            "⑧ §7 技术方案概要（详细方案 → N7）",
            "⑨ §8 风险评估 R-table",
            "⑩ user review + revise（≤ 2 轮 user_confirm 出口）",
        ],
        "output_templates": [
            {
                "for": "docs/prd/prd.md",
                "framework": "阿里风 PRD 8 章 + 强制原型 §6",
                "skeleton": (
                    "# PRD: <task_id>\n\n"
                    "## §1 背景 (Background)\n"
                    "- 业务现状 (current state)\n"
                    "- 痛点 (pain points) — bullet 列表\n"
                    "- 机会 (opportunity)\n\n"
                    "## §2 目标 (Goals)\n"
                    "- 业务目标: <SMART>\n"
                    "- 用户目标: <SMART>\n"
                    "- 衡量指标: <metric + target>\n\n"
                    "## §3 用户故事 (User Stories)\n"
                    "| US-ID | As a (role) | I want (feature) | So that (benefit) | Priority |\n"
                    "|---|---|---|---|---|\n"
                    "| US-01 | <role> | <feat> | <benefit> | P0 |\n\n"
                    "## §4 功能需求 (Features)\n"
                    "| FID | 名称 | 优先级 | 描述 | 关联 US |\n"
                    "|---|---|---|---|---|\n"
                    "| F1 | <name> | P0 | <1 段描述> | US-01,US-02 |\n\n"
                    "## §5 验收标准 (Acceptance Criteria) ← TDD 种子\n"
                    "| AC-ID | Given | When | Then | Priority |\n"
                    "|---|---|---|---|---|\n"
                    "| AC-01 | <前置> | <动作> | <期望> | P0 |\n\n"
                    "## §6 原型设计 (Prototype) — **必含**\n"
                    "- prototypes.svg (≥ 3 张 wireframe: 标题页 / 主流程页 / 边界态页)\n"
                    "- 关键交互 flow: <步骤 1 → 步骤 2 → 步骤 3>\n"
                    "- 状态切换: <space>\n\n"
                    "## §7 技术方案概要 (Tech Approach Summary)\n"
                    "- 选型摘要 (详见 N7 tech_design)\n"
                    "- 关键约束 (perf / security / 兼容性)\n\n"
                    "## §8 风险评估 (Risks)\n"
                    "| RID | 风险 | 影响 | 概率 | 缓解 | Owner |"
                ),
            },
            {
                "for": "docs/prd/prototypes.svg",
                "framework": "Wireframe-Spec（≥ 3 张）",
                "skeleton": (
                    '<svg viewBox="0 0 1280 800" xmlns="http://www.w3.org/2000/svg">\n'
                    "  <!-- 必含 ≥ 3 张:\n"
                    "       1) 标题/入口页 — 含主 CTA\n"
                    "       2) 主流程页 — 核心功能可视\n"
                    "       3) 边界态页 — 空 / 错误 / 完成\n"
                    "       UI 类任务额外要求: 含坐标系、关键控件、状态切换箭头 -->\n"
                    '  <g id="screen-1-title">...</g>\n'
                    '  <g id="screen-2-main">...</g>\n'
                    '  <g id="screen-3-edge">...</g>\n'
                    "</svg>"
                ),
            },
            {
                "for": "_derived.prd",
                "framework": "PRD 可程序化字段（喂下游）",
                "skeleton": (
                    "{\n"
                    '  "features": [{ "fid": "F1", "name": "<>", "priority": "P0", "linked_us": ["US-01"] }],\n'
                    '  "acceptance_criteria": [{ "ac_id": "AC-01", "given": "<>", "when": "<>", "then": "<>", "priority": "P0" }],\n'
                    '  "user_stories": [...],\n'
                    '  "risks": [{ "rid": "R1", "desc": "<>", "impact": "L|M|H", "prob": "L|M|H", "mitigation": "<>" }]\n'
                    "}"
                ),
            },
        ],
    },
    {
        "id": "N6",
        "name": "TDD 用例设计",
        "code": "tdd_design",
        "phase": "Planning ‖",
        "owner_skill": "ECC:tdd-guide (业务维度 + N7 augment 后追加技术维度)",
        "step": 6,
        "layout": {"x": 640, "y": 78, "w": 125, "h": 60},
        "inputs": [
            {"name": "acceptance_criteria", "type": "json", "from": "N5", "field": "outputs._derived.prd.acceptance_criteria", "required": True, "desc": "🎯 核心 SEED — 每条 AC 至少对应 1 条 TDD"},
            {"name": "features", "type": "json", "from": "N5", "field": "outputs._derived.prd.features", "required": True},
            {"name": "tech_design", "type": "json", "from": "N7", "field": "outputs._derived.tech_design (interfaces+perf_constraints)", "required": False, "augment": True, "desc": "⥃ 通过 augment edge e07 进入；触发 augmenting 状态后追加 perf/security/boundary TDD"},
        ],
        "outputs": [
            {"path": "tdd_cases.definitions[] (含 augment 增量)", "type": "json", "size_hint": "~6KB", "consumed_by": ["N8", "N11", "N12"], "schema": "[{case_id, given, when, then, expected_assertion, dimension∈{business,perf,security,boundary}, priority, verified_at}]"},
            {"path": "docs/tdd/test-plan.md", "type": "md", "size_hint": "~3KB", "consumed_by": ["N11"]},
            {"path": "augment_round_log[]", "type": "json", "size_hint": "~0.5KB", "consumed_by": ["N13 retro"], "schema": "[{round_id, triggered_by_node, added_cases[], at_ts}]"},
        ],
        "internal_workflow": [
            "① 读 acceptance_criteria (🎯 SEED) + features",
            "② 业务维度: BDD given-when-then 编写, 每条 AC ≥ 1 case",
            "③ 标 verified_at=\"N11\" (业务由 exec_node 即 N11 跑)",
            "④ 等待 N7 augment edge e07 触发 (lazy increment)",
            "⑤ ⥃ augmenting 状态: 追加 perf / security / boundary cases",
            "⑥ 新追加 cases verified_at=\"N12\" (Verifier subagent 跑)",
            "⑦ 写 augment_round_log (供 retro / dashboard 显示)",
        ],
        "output_templates": [
            {
                "for": "tdd_cases.definitions[]",
                "framework": "BDD given-when-then × dimension matrix",
                "skeleton": (
                    "[\n"
                    "  {\n"
                    '    "case_id": "T01_<short_name>",\n'
                    '    "dimension": "business" | "perf" | "security" | "boundary",\n'
                    '    "given": "<前置条件>",\n'
                    '    "when": "<行为 / 调用>",\n'
                    '    "then": "<期望结果>",\n'
                    '    "expected_assertion": "<可执行断言, eg player.x > initial_x>",\n'
                    '    "priority": "P0" | "P1" | "P2",\n'
                    '    "verified_at": "N11" | "N12",\n'
                    '    "augment_round": 0,\n'
                    '    "linked_ac": ["AC-01"],\n'
                    '    "linked_perf_constraint": "<from N7, 仅 dimension=perf 用>"\n'
                    "  }\n"
                    "]"
                ),
            },
            {
                "for": "docs/tdd/test-plan.md",
                "framework": "Test Plan + 覆盖矩阵",
                "skeleton": (
                    "# TDD Test Plan — <task_id>\n\n"
                    "## 业务维度 (verified_at=N11) — 主轨\n"
                    "- T01..Tnn: 每条对应 PRD §5 的 AC\n\n"
                    "## 技术维度 (verified_at=N12) — augment 增量\n"
                    "- 性能 (perf): T?? — 来自 N7 perf_constraints\n"
                    "- 安全 (security): T?? — 来自 N7 security_concerns\n"
                    "- 边界 (boundary): T?? — 来自 N7 interfaces 边界条件\n\n"
                    "## 覆盖矩阵 (AC → Case)\n"
                    "| AC-ID | Case-ID | dimension | verified_at |\n"
                    "|---|---|---|---|\n"
                    "| AC-01 | T01 | business | N11 |"
                ),
            },
            {
                "for": "augment_round_log",
                "framework": "augment 轮次回放",
                "skeleton": (
                    "[\n"
                    "  {\n"
                    '    "round_id": 1,\n'
                    '    "triggered_by_node": "N7",\n'
                    '    "trigger_reason": "tech_design completion",\n'
                    '    "added_cases": ["T09","T10","T11","T12"],\n'
                    '    "at_ts": "<UTC>",\n'
                    '    "case_dimensions": ["perf","perf","boundary","security"]\n'
                    "  }\n"
                    "]"
                ),
            },
        ],
    },
    {
        "id": "N7",
        "name": "详细技术方案",
        "code": "tech_design",
        "phase": "Planning ‖",
        "owner_skill": "ECC:prp-plan §architecture",
        "step": 6,
        "layout": {"x": 640, "y": 270, "w": 125, "h": 60},
        "inputs": [
            {"name": "prd", "type": "json+md", "from": "N5", "field": "outputs._derived.prd + docs/prd/prd.md", "required": True},
            {"name": "prototypes", "type": "svg", "from": "N5", "field": "outputs.docs/prd/prototypes.svg", "required": False, "desc": "UI 类任务必读"},
            {"name": "project_library_repos", "type": "json", "from": "N2", "field": "outputs._derived.project_library.repos[] + .process_docs[]", "required": True, "desc": "架构选型参考"},
        ],
        "outputs": [
            {"path": "docs/tech/architecture.md", "type": "md", "size_hint": "~5KB", "consumed_by": ["N8", "N9", "N11"], "schema": "TOGAF L0/L1/L2/L3 + 横切关注点 + ADR"},
            {"path": "docs/tech/architecture-diagram.svg", "type": "svg", "size_hint": "~9KB", "consumed_by": ["dashboard"]},
            {"path": "_derived.tech_design", "type": "json", "size_hint": "~3KB", "consumed_by": ["N6 (via augment)", "N8", "N9", "N11"], "schema": "{architecture, interfaces[], data_flow, tech_choices[], perf_constraints[], security_concerns[]}"},
            {"path": "api_contracts.yaml", "type": "json", "size_hint": "~3KB", "consumed_by": ["N9", "N11"], "schema": "OpenAPI 3.x or 内部 DSL"},
        ],
        "internal_workflow": [
            "① L0 业务架构: 业务能力图 + 价值流（link → N4 charter）",
            "② L1 系统架构: 全景图 + 集成视图 + 部署拓扑",
            "③ L2 组件设计: 组件分解 + 关键时序图（≥ 3 主流程）",
            "④ L3 类/接口/数据: 类图 + api_contracts.yaml + 数据模型",
            "⑤ 横切关注点: perf / security / observability / 容错",
            "⑥ ADR 决策日志（每个关键选型一条）",
            "⑦ ⥃ 触发 e07 augment edge → 通知 N6 追加 perf/security/boundary TDD",
        ],
        "output_templates": [
            {
                "for": "docs/tech/architecture.md",
                "framework": "TOGAF 风 L0/L1/L2/L3 + 横切关注点 + ADR",
                "skeleton": (
                    "# 详细技术方案 — <task_id> (TOGAF 风)\n\n"
                    "## L0 — 业务架构 (Business Architecture)\n"
                    "- 业务能力图 (Business Capability Map)\n"
                    "- 价值流 (Value Stream)\n"
                    "- 业务流程 (Business Process)\n"
                    "- 关键利益相关方（link → N4 charter §5）\n\n"
                    "## L1 — 系统架构 (System Architecture)\n"
                    "- 系统全景图 (System Landscape) — PlantUML\n"
                    "- 集成视图 (Integration View) — 含外部依赖\n"
                    "- 部署拓扑 (Deployment Topology)\n"
                    "- 技术选型决策表 (Tech Stack Matrix)\n\n"
                    "## L2 — 组件设计 (Component Architecture)\n"
                    "- 组件分解图 (Component Decomposition) — PlantUML\n"
                    "- 关键时序图 (Sequence Diagrams) — ≥ 3 主流程\n"
                    "- 状态图 (State Machines) — 必要时\n"
                    "- 内部接口 (Internal APIs)\n\n"
                    "## L3 — 类/接口/数据 (Detail Layer)\n"
                    "- 类图 / 模块依赖图 (Class Diagram or Module DAG)\n"
                    "- API 契约 → api_contracts.yaml (OpenAPI 3.x or 内部 DSL)\n"
                    "- 数据模型 (ERD / Schema)\n"
                    "- 错误码表 (Error Codes)\n\n"
                    "## 横切关注点 (Cross-Cutting Concerns)\n"
                    "- 性能预算 (Perf Budgets) → 喂 N6 augment perf TDD\n"
                    "- 安全威胁建模 (STRIDE) → 喂 N6 augment security TDD\n"
                    "- 可观测性 (log / trace / metric)\n"
                    "- 容错策略 (Error Handling + Recovery)\n\n"
                    "## ADR — Architecture Decision Records\n"
                    "| ADR-ID | 决策 | 候选方案 | 选定理由 | 后果 | 日期 |\n"
                    "|---|---|---|---|---|---|\n"
                    "| ADR-01 | <decision> | <opt A vs B> | <rationale> | <consequence> | <date> |"
                ),
            },
            {
                "for": "api_contracts.yaml",
                "framework": "OpenAPI 3.x (web) / 内部 DSL (lib/cli)",
                "skeleton": (
                    "openapi: 3.0.3\n"
                    'info: { title: "<service>", version: "1.0" }\n'
                    "paths:\n"
                    "  /<endpoint>:\n"
                    "    <method>:\n"
                    "      summary: ...\n"
                    "      requestBody:\n"
                    '        $ref: "#/components/schemas/<X>Request"\n'
                    "      responses:\n"
                    '        "200": { $ref: "#/components/schemas/<X>Response" }\n'
                    '        "4xx": { $ref: "#/components/schemas/Error" }\n'
                    "components:\n"
                    "  schemas:\n"
                    "    <X>Request: { type: object, properties: { ... }, required: [...] }\n"
                    "    <X>Response: { type: object, properties: { ... } }"
                ),
            },
            {
                "for": "_derived.tech_design",
                "framework": "tech_design JSON（喂 N6 augment / N9 / N11）",
                "skeleton": (
                    "{\n"
                    '  "architecture": "<L1 全景一句话>",\n'
                    '  "interfaces": [{ "name": "<>", "kind": "fn|api|param", "signature": "<>" }],\n'
                    '  "data_flow": "<input → process → output>",\n'
                    '  "tech_choices": [{ "tech": "<>", "rationale": "<>" }],\n'
                    '  "perf_constraints": ["<约束 1, eg 60fps stable>"],\n'
                    '  "security_concerns": ["<威胁 1>"],\n'
                    '  "boundary_conditions": ["<edge case 1>"],\n'
                    '  "adr_refs": ["ADR-01"]\n'
                    "}"
                ),
            },
        ],
    },
    {
        "id": "N8",
        "name": "范围收口",
        "code": "scope_finalize",
        "phase": "Planning",
        "owner_skill": "superpowers:brainstorming (派生 + user_confirm dod_expression)",
        "step": 7,
        "layout": {"x": 800, "y": 170, "w": 100, "h": 60},
        "inputs": [
            {"name": "features", "type": "json", "from": "N5", "field": "outputs._derived.prd.features", "required": True},
            {"name": "tdd_cases", "type": "json", "from": "N6", "field": "outputs.tdd_cases.definitions (含 augment)", "required": True, "desc": "验证维度计数"},
            {"name": "tech_design", "type": "json", "from": "N7", "field": "outputs._derived.tech_design.constraints", "required": True},
            {"name": "goal_out_of_scope", "type": "string[]", "from": "N3", "field": "outputs._derived.delivery_goal.out_of_scope_explicit", "required": True},
        ],
        "outputs": [
            {"path": "_derived.scope", "type": "json", "size_hint": "~2KB", "consumed_by": ["N9", "N11", "N12"], "schema": "{in_scope[], out_of_scope[], dod_expression, dod_variables, confirmed_by_user_at}"},
        ],
        "internal_workflow": [
            "① 派生 in_scope ← features ⊕ tdd_dimensions ⊕ tech_constraints",
            "② 派生 out_of_scope ← goal.out_of_scope_explicit + 新增推断",
            "③ 起草 dod_expression（布尔表达式, AST 可解析）",
            "④ 🔒 user_confirm dod_expression（强制人工 gate, requires_user_confirm=true）",
            "⑤ 写 _derived.scope + confirmed_by_user_at",
        ],
        "output_templates": [
            {
                "for": "_derived.scope",
                "framework": "Scope + DoD 布尔表达式 (eval 由 Verifier N12 跑)",
                "skeleton": (
                    "{\n"
                    '  "in_scope": [\n'
                    '    "F1: <feature 名>",\n'
                    '    "T01-T08: 业务维度 TDD (verified_at=N11)",\n'
                    '    "T09-T12: 技术维度 TDD (verified_at=N12 via N7 augment)"\n'
                    "  ],\n"
                    '  "out_of_scope": [\n'
                    '    "❌ <显式排除项 1>",\n'
                    '    "❌ <显式排除项 2>"\n'
                    "  ],\n"
                    '  "dod_expression": "(tdd_pass_rate >= 1.0 OR (tdd_failed_count == 0 AND verifier_overall == \'PASS\')) AND no_red_lines_detected AND user_confirmed_demo_runs",\n'
                    '  "dod_variables": {\n'
                    '    "tdd_pass_rate": "ratio of passed cases over total",\n'
                    '    "verifier_overall": "verifier_reports/<tid>.json#overall",\n'
                    '    "no_red_lines_detected": "supervisor-events/<tid>.jsonl 无 red_line entry",\n'
                    '    "user_confirmed_demo_runs": "task-board.user_confirmed_at_demo is set"\n'
                    "  },\n"
                    '  "confirmed_by_user_at": "<UTC>"\n'
                    "}"
                ),
            },
        ],
    },
    {
        "id": "N9",
        "name": "WBS 拆解",
        "code": "wbs_decompose",
        "phase": "Planning",
        "owner_skill": "ECC:prp-plan",
        "step": 8,
        "layout": {"x": 915, "y": 170, "w": 95, "h": 60},
        "inputs": [
            {"name": "scope_in", "type": "json", "from": "N8", "field": "outputs._derived.scope.in_scope", "required": True},
            {"name": "tech_interfaces", "type": "json", "from": "N7", "field": "outputs._derived.tech_design.interfaces + api_contracts", "required": True, "desc": "决定 deliverable 边界"},
            {"name": "features", "type": "json", "from": "N5", "field": "outputs._derived.prd.features", "required": True},
        ],
        "outputs": [
            {"path": "_derived.wbs", "type": "json", "size_hint": "~3KB", "consumed_by": ["N10", "N11"], "schema": "[{wp_id, parent_id, deliverable, est_hours, depends_on, owner_skill, linked_features, linked_tdd_cases}]"},
            {"path": "docs/wbs/wbs.md", "type": "md", "size_hint": "~2KB", "consumed_by": ["N10", "user"]},
        ],
        "internal_workflow": [
            "① 读 scope.in_scope + tech_interfaces + features",
            "② 按 deliverable 维度分解（深度 ≤ 3 层 — WP1.x.y）",
            "③ 标 WP-ID + 估工（小时）",
            "④ 标 depends_on（构建拓扑顺序）",
            "⑤ 标 owner_skill（调度提示, ECC:prp-implement / tdd-guide / reviewer / ...）",
            "⑥ 写 _derived.wbs + docs/wbs/wbs.md（树状视图）",
        ],
        "output_templates": [
            {
                "for": "_derived.wbs",
                "framework": "WBS 三层分解 + 依赖图（拓扑可序）",
                "skeleton": (
                    "[\n"
                    "  {\n"
                    '    "wp_id": "WP1.1",\n'
                    '    "parent_id": null,\n'
                    '    "name": "<deliverable 名>",\n'
                    '    "deliverable": "<具体可交付产物 path / artifact 描述>",\n'
                    '    "est_hours": <number>,\n'
                    '    "depends_on": ["<wp_id 1>", "<wp_id 2>"],\n'
                    '    "owner_skill": "ECC:prp-implement | ECC:tdd-guide | ECC:code-reviewer | ...",\n'
                    '    "linked_features": ["F1","F2"],\n'
                    '    "linked_tdd_cases": ["T01","T02"]\n'
                    "  }\n"
                    "]"
                ),
            },
            {
                "for": "docs/wbs/wbs.md",
                "framework": "WBS 树状视图（人可读）",
                "skeleton": (
                    "# WBS — <task_id>\n\n"
                    "- WP1 <名> (估工 nh)\n"
                    "  - WP1.1 <名> (估工 nh, depends [], features F1)\n"
                    "    - WP1.1.1 <名> (估工 nh)\n"
                    "  - WP1.2 <名> (估工 nh, depends [WP1.1])\n"
                    "- WP2 <名> (估工 nh, depends [WP1.2])\n\n"
                    "## 总估工: <sum> h\n"
                    "## 关键路径: WP1.1 → WP1.2 → WP2.1 (估工 <total> h)\n"
                    "## owner_skill 调度: ECC:prp-implement × N, tdd-guide × N, code-reviewer × N"
                ),
            },
        ],
    },
    {
        "id": "N10",
        "name": "执行计划",
        "code": "execution_plan",
        "phase": "Planning",
        "owner_skill": "ECC:prp-plan §execution-order",
        "step": 9,
        "layout": {"x": 1020, "y": 170, "w": 100, "h": 60},
        "inputs": [
            {"name": "wbs", "type": "json", "from": "N9", "field": "outputs._derived.wbs[]", "required": True},
            {"name": "milestones", "type": "json", "from": "N4", "field": "outputs._derived.charter.milestones", "required": True},
            {"name": "dimensions", "type": "json", "from": "N3", "field": "outputs._derived.dimensions (size→time_budget)", "required": True},
        ],
        "outputs": [
            {"path": "_derived.execution_plan", "type": "json", "size_hint": "~2KB", "consumed_by": ["N11"], "schema": "{order[], critical_path[], milestone_alignment, parallelizable_wps}"},
        ],
        "internal_workflow": [
            "① 读 wbs[] + milestones",
            "② 拓扑排序（depends_on → 执行序）",
            "③ 计算 critical_path（CPM 关键路径方法）",
            "④ 对齐 milestones（WP → MS 映射）",
            "⑤ 写 _derived.execution_plan（喂 N11 节点 loop driver）",
        ],
        "output_templates": [
            {
                "for": "_derived.execution_plan",
                "framework": "执行序 + 关键路径 + 里程碑映射（CPM）",
                "skeleton": (
                    "{\n"
                    '  "order": ["WP1.1","WP1.2","WP2.1", "..."],\n'
                    '  "critical_path": ["WP1.1","WP2.1","WP3.2"],\n'
                    '  "milestone_alignment": {\n'
                    '    "MS1": ["WP1.1","WP1.2"],\n'
                    '    "MS2": ["WP2.1","WP3.2"]\n'
                    "  },\n"
                    '  "earliest_start": { "<wp_id>": "<UTC>" },\n'
                    '  "estimated_total_hours": <sum>,\n'
                    '  "parallelizable_wps": [["WP1.1","WP1.3"], ["WP2.1","WP2.2"]]\n'
                    "}"
                ),
            },
        ],
    },
    # -------------------- Executing --------------------
    {
        "id": "N11",
        "name": "项目开发 LOOP",
        "code": "exec_node_loop",
        "phase": "Executing",
        "owner_skill": "ECC:prp-implement + ECC:tdd-guide + harnessFlow:verifier (per-WBS)",
        "step": 10,
        "layout": {"x": 1140, "y": 170, "w": 135, "h": 60},
        "inputs": [
            {"name": "wbs[]", "type": "json", "from": "N9", "field": "outputs._derived.wbs[] (per-package iteration driver)", "required": True},
            {"name": "tdd_cases", "type": "json", "from": "N6", "field": "outputs.tdd_cases.definitions (含 augment)", "required": True, "desc": "verified_at=\"N11\" 的本节点跑"},
            {"name": "tech_design", "type": "json", "from": "N7", "field": "outputs._derived.tech_design + api_contracts", "required": True},
            {"name": "execution_plan", "type": "json", "from": "N10", "field": "outputs._derived.execution_plan (执行序)", "required": True},
        ],
        "outputs": [
            {"path": "stage_artifacts/<wp_id>/", "type": "blob", "size_hint": "var", "consumed_by": ["N12", "N13"]},
            {"path": "loop_history[]", "type": "json", "size_hint": "var", "consumed_by": ["N13 retro"], "schema": "[{wp_id, started_at, completed_at, retries, tdd_results, commit_sha, code_review}]"},
        ],
        "internal_workflow": [
            "① 取下一 WP（per execution_plan.order）",
            "② TDD 红: 跑对应 cases (verified_at=N11) → 必须 fail",
            "③ implement minimal（写代码满足 cases）",
            "④ TDD 绿: 跑 cases → 必须 pass",
            "⑤ code-review subagent（per stack reviewer）",
            "⑥ commit (git, 含 trailer Co-Authored-By: Claude)",
            "⑦ append stage_artifacts/<wp_id>/ + loop_history",
            "⑧ 若 review fail / TDD fail → rollback 重 loop（同 WP retry）",
            "⑨ next WP（直至 wbs[] 全 done）",
        ],
        "output_templates": [
            {
                "for": "loop_history[]",
                "framework": "per-WP 执行回放（retro 用）",
                "skeleton": (
                    "[\n"
                    "  {\n"
                    '    "wp_id": "WP1.1",\n'
                    '    "started_at": "<UTC>",\n'
                    '    "completed_at": "<UTC>",\n'
                    '    "retries": <int>,\n'
                    '    "tdd_run_at_N11": ["T01","T02"],\n'
                    '    "tdd_results": [{ "case_id": "T01", "verdict": "PASS" }],\n'
                    '    "artifacts": ["stage_artifacts/WP1.1/<file 1>", "..."],\n'
                    '    "commit_sha": "<sha>",\n'
                    '    "code_review": { "reviewer": "ECC:typescript-reviewer", "outcome": "PASS|ISSUES", "comments_count": <n> }\n'
                    "  }\n"
                    "]"
                ),
            },
            {
                "for": "stage_artifacts/<wp_id>/",
                "framework": "per-WP 产物目录（Verifier 三段证据用）",
                "skeleton": (
                    "stage_artifacts/\n"
                    "└── WP1.1/\n"
                    "    ├── <source_files 实际产出>\n"
                    "    ├── <test_files>\n"
                    '    └── _meta.json    // { wp_id, files[], commit_sha, tdd_run_at, artifacts_kind: "code|doc|asset" }'
                ),
            },
        ],
    },
    # -------------------- M&C --------------------
    {
        "id": "N12",
        "name": "质量验证",
        "code": "quality_verify",
        "phase": "M&C",
        "owner_skill": "harnessFlow:verifier subagent + delivery-checklist 三段证据链",
        "step": 11,
        "layout": {"x": 1295, "y": 170, "w": 115, "h": 60},
        "inputs": [
            {"name": "execution_results", "type": "json", "from": "N11", "field": "outputs.tdd_cases.execution_results", "required": True, "desc": "verified_at=\"N12\" 的本节点跑（perf/security/acceptance）"},
            {"name": "stage_artifacts", "type": "blob", "from": "N11", "field": "outputs.stage_artifacts/", "required": True, "desc": "existence + behavior 三段证据"},
            {"name": "dod_expression", "type": "string", "from": "N8", "field": "outputs._derived.scope.dod_expression", "required": True, "desc": "🎯 布尔 eval 的 ground truth"},
            {"name": "goal_anchor", "type": "md", "from": "N3", "field": "outputs.CLAUDE.md goal-anchor (drift recheck)", "required": True, "desc": "验证期间 CLAUDE.md 不能漂"},
            {"name": "charter", "type": "json", "from": "N4", "field": "outputs._derived.charter (stakeholder + milestones)", "required": False},
        ],
        "outputs": [
            {"path": "verifier_reports/<tid>.json", "type": "json", "size_hint": "~2KB", "consumed_by": ["N13"], "schema": "{overall, evidence_checks[], dod_eval_trace, red_lines_detected[], goal_anchor_drift}"},
        ],
        "internal_workflow": [
            "① 独立读 dod_expression（不复用 N11 假设, fresh subagent）",
            "② 跑 verified_at=\"N12\" cases (perf/security/acceptance)",
            "③ 三段证据链: existence (文件在) / structure (契约对) / behavior (跑出来对)",
            "④ red_lines 扫描 (DRIFT_CRITICAL / DOD_GAP / IRREVERSIBLE_HALT)",
            "⑤ goal_anchor drift recheck (sha256 重算 vs N3 hash)",
            "⑥ verdict ∈ {PASS, FAIL, INSUFFICIENT_EVIDENCE}",
            "⑦ 写 verifier_reports/<tid>.json",
        ],
        "output_templates": [
            {
                "for": "verifier_reports/<tid>.json",
                "framework": "Verifier Report — 三段证据链 + DoD eval trace",
                "skeleton": (
                    "{\n"
                    '  "task_id": "<tid>",\n'
                    '  "overall": "PASS" | "FAIL" | "INSUFFICIENT_EVIDENCE",\n'
                    '  "completed_at": "<UTC>",\n'
                    '  "dod_eval_trace": {\n'
                    '    "expression": "(tdd_pass_rate >= 1.0) AND (no_red_lines)",\n'
                    '    "values": { "tdd_pass_rate": 1.0, "no_red_lines": true },\n'
                    '    "result": true\n'
                    "  },\n"
                    '  "evidence_checks": [\n'
                    '    { "check_id": "E1", "tier": "existence", "target": "<path>", "verdict": "PASS|FAIL", "evidence_paths": ["..."] },\n'
                    '    { "check_id": "E2", "tier": "structure", "target": "<path>::<schema>", "verdict": "PASS|FAIL" },\n'
                    '    { "check_id": "E3", "tier": "behavior", "target": "<assertion>", "verdict": "PASS|FAIL", "evidence_paths": ["artifacts/..."] }\n'
                    "  ],\n"
                    '  "tdd_run_at_N12": [{ "case_id": "T09", "dimension": "perf", "verdict": "PASS", "metrics": {} }],\n'
                    '  "red_lines_detected": [],\n'
                    '  "goal_anchor_drift": false,\n'
                    '  "goal_anchor_hash_recheck": "<sha256>"\n'
                    "}"
                ),
            },
        ],
    },
    # -------------------- Closing --------------------
    {
        "id": "N13",
        "name": "收尾归档",
        "code": "close_retro",
        "phase": "Closing",
        "owner_skill": "ECC:prp-commit + ECC:prp-pr + harnessFlow:retro-generator + harnessFlow:failure-archive-writer",
        "step": 12,
        "layout": {"x": 1430, "y": 170, "w": 210, "h": 60},
        "inputs": [
            {"name": "verifier_report", "type": "json", "from": "N12", "field": "outputs.verifier_reports/<tid>.json", "required": True, "desc": "🎯 must=PASS 才进 N13"},
            {"name": "commits", "type": "json", "from": "N11", "field": "outputs.commits[]", "required": True},
            {"name": "all_artifacts", "type": "blob", "from": "N11", "field": "outputs.stage_artifacts/", "required": True, "desc": "打 zip bundle"},
            {"name": "loop_history", "type": "json", "from": "N11", "field": "outputs.loop_history[]", "required": True, "desc": "写进 retro § 复盘"},
            {"name": "augment_log", "type": "json", "from": "N6", "field": "outputs.augment_round_log", "required": False, "desc": "写进 retro § 增量"},
            {"name": "task_board_full", "type": "json", "from": "all", "field": "task-boards/<tid>.json (全量)", "required": True},
        ],
        "outputs": [
            {"path": "retros/<tid>.md", "type": "md", "size_hint": "~3KB", "consumed_by": ["MEMORY", "user"]},
            {"path": "delivery_bundle/<tid>.zip", "type": "blob", "size_hint": "var", "consumed_by": ["user"]},
            {"path": "task-boards/<tid>.json#closed", "type": "json", "size_hint": "—", "consumed_by": ["dashboard"], "schema": "{closed_at, final_outcome}"},
        ],
        "internal_workflow": [
            "① ECC:prp-commit + ECC:prp-pr (size ≥ M 强制 PR)",
            "② harnessFlow:retro-generator 跑 11 项 section",
            "③ harnessFlow:failure-archive-writer (若失败路径)",
            "④ 打 delivery_bundle/<tid>.zip",
            "⑤ task-board state → CLOSED, 写 closed_at",
            "⑥ MEMORY 沉淀 evolution_suggestions （可选, 人审批后入）",
        ],
        "output_templates": [
            {
                "for": "retros/<tid>.md",
                "framework": "11 项 retro section（标准复盘模板）",
                "skeleton": (
                    "# Retro — <task_id>\n\n"
                    "## 1. 任务背景 + 目标\n"
                    "(link goal-anchor + delivery_goal)\n\n"
                    "## 2. 实际产出\n"
                    "- artifacts: stage_artifacts/* + commit_sha + pr_url\n\n"
                    "## 3. 时间消耗 (节点 breakdown)\n"
                    "| 节点 | started | completed | 耗时 | retries |\n\n"
                    "## 4. Loop 次数统计 (per WP retries)\n"
                    "## 5. TDD 通过率 + 增量轮 (augment_round_log)\n"
                    "## 6. Supervisor 干预记录 (INFO/WARN/BLOCK)\n"
                    "## 7. 偏移事件 (drift / route_change)\n"
                    "## 8. 失败/卡点根因（若有）\n"
                    "## 9. 学习点 (what worked / didn't / next time)\n"
                    "## 10. 遗留 (Out-of-scope 留白 + tech debt)\n"
                    "## 11. evolution_suggestions[] (供主 skill 进化, 人审批)"
                ),
            },
            {
                "for": "delivery_bundle/<tid>.zip",
                "framework": "可交付打包（zip 内目录结构）",
                "skeleton": (
                    "delivery_bundle/<tid>.zip 内含:\n"
                    "├── stage_artifacts/        # N11 全量产出\n"
                    "├── verifier_reports/       # N12 报告\n"
                    "├── docs/\n"
                    "│   ├── prd/                # N5\n"
                    "│   ├── tech/               # N7\n"
                    "│   ├── charter/            # N4\n"
                    "│   ├── wbs/                # N9\n"
                    "│   ├── tdd/                # N6\n"
                    "│   └── research/           # N2\n"
                    "├── retros/<tid>.md\n"
                    "├── task-boards/<tid>.json  # 全量状态机回放\n"
                    "└── MANIFEST.json           # { commit_sha, pr_url, closed_at, tools_used[] }"
                ),
            },
        ],
    },
]


# =============================================================================
# EDGES_DELIVERY — DAG edges (forward / augment / rollback)
# =============================================================================

EDGES_DELIVERY: list[dict] = [
    # forward edges (12) — 主轨
    {"id": "e01", "kind": "forward", "from": "N1", "to": "N2", "label": "三维✓"},
    {"id": "e02", "kind": "forward", "from": "N2", "to": "N3", "label": "docs≥3"},
    {"id": "e03", "kind": "forward", "from": "N3", "to": "N4", "label": "hash✓"},
    {"id": "e04", "kind": "forward", "from": "N4", "to": "N5", "label": "章程✓"},
    {"id": "e05a", "kind": "forward", "from": "N5", "to": "N6", "label": "8章✓ split"},
    {"id": "e05b", "kind": "forward", "from": "N5", "to": "N7", "label": "8章✓ split"},
    {"id": "e06a", "kind": "forward", "from": "N6", "to": "N8", "label": "tdd✓"},
    {"id": "e06b", "kind": "forward", "from": "N7", "to": "N8", "label": "tech✓"},
    {"id": "e08", "kind": "forward", "from": "N8", "to": "N9", "label": "scope✓"},
    {"id": "e09", "kind": "forward", "from": "N9", "to": "N10", "label": "wbs✓"},
    {"id": "e10", "kind": "forward", "from": "N10", "to": "N11", "label": "DAG✓"},
    {"id": "e11", "kind": "forward", "from": "N11", "to": "N12", "label": "∀ec=PASS"},
    {"id": "e12", "kind": "forward", "from": "N12", "to": "N13", "label": "verifier=PASS"},
    # augment (1) — N7 完成后回灌 N6 追加 perf/security/boundary TDD
    {"id": "e07", "kind": "augment", "from": "N7", "to": "N6", "label": "⥃ 补技术 TDD"},
    # rollback (4) — 失败回退路径
    {"id": "r01", "kind": "rollback", "from": "N3", "to": "N2", "label": "资料/任务不清"},
    {"id": "r02", "kind": "rollback", "from": "N5", "to": "N4", "label": "PRD 写不出"},
    {"id": "r03", "kind": "rollback", "from": "N12", "to": "N11", "label": "FAIL → 重 loop"},
    {"id": "r04", "kind": "rollback", "from": "N13", "to": "N12", "label": "commit/PR fail"},
]


# =============================================================================
# State machine ↔ node step mapping
# =============================================================================

# Each main-skill state corresponds to a 1..13 node step index. Nodes whose step
# is < current_step → passed; == current_step → running; > → pending.
STATE_TO_STEP: dict[str, int] = {
    "INIT": 1,
    "CLARIFY": 3,            # 包含 N1→N2→N3 三节点（goal lock）
    "ROUTE_SELECT": 4,       # N4 charter
    "PLAN": 9,               # 折叠 N5..N10（PRD/TDD/Tech/Scope/WBS/Plan）
    "CHECKPOINT_SAVE": 9,
    "IMPL": 10,              # N11 LOOP
    "MID_CHECKPOINT": 10,
    "MID_RETRO": 10,
    "VERIFY": 11,            # N12
    "SANTA_LOOP": 10,        # 回退到 N11
    "COMMIT": 12,            # N13 part 1
    "RETRO_CLOSE": 12,
    "CLOSED": 13,
    "ABORTED": 13,
}

# Nodes that map 1:1 to a state can have started/completed timestamps lifted
# directly from state_history. Folded nodes (step ∈ {2, 5, 6, 7, 8}) leave
# timestamps null in MVP.
NODE_STATE_BOUNDS: dict[int, tuple[str, str]] = {
    1: ("INIT", "CLARIFY"),
    3: ("CLARIFY", "ROUTE_SELECT"),
    4: ("ROUTE_SELECT", "PLAN"),
    9: ("PLAN", "CHECKPOINT_SAVE"),
    10: ("IMPL", "VERIFY"),
    11: ("VERIFY", "COMMIT"),
    12: ("COMMIT", "CLOSED"),
}


# =============================================================================
# derive_pipeline_view — overlay task-board status/timing onto NODE_CATALOG
# =============================================================================

def derive_pipeline_view(tb: dict) -> dict:
    """Build a per-task pipeline graph view by overlaying task-board state on
    the global NODE_CATALOG.

    Returns:
        {
          "task_id": ...,
          "kind": "delivery",
          "current_node_id": <str|None>,
          "current_state": <str>,
          "progress": {"completed": int, "total": 13, "percentage": int},
          "nodes": [...13 nodes with status overlay...],
          "edges": EDGES_DELIVERY,
          "legend": {...},
        }
    """
    state = tb.get("current_state", "INIT") or "INIT"
    state_history = tb.get("state_history") or []
    is_aborted = state == "ABORTED"
    is_paused = state == "PAUSED_ESCALATED"

    # Build state→first-occurrence-timestamp map
    state_ts: dict[str, str] = {}
    for entry in state_history:
        s = entry.get("state")
        ts = entry.get("timestamp")
        if s and ts and s not in state_ts:
            state_ts[s] = ts

    # Determine current step
    if is_paused:
        # Use the last non-paused state for step lookup
        last_real_state: str | None = None
        for entry in reversed(state_history):
            s = entry.get("state")
            if s and s != "PAUSED_ESCALATED":
                last_real_state = s
                break
        current_step = STATE_TO_STEP.get(last_real_state or "", 0)
    else:
        current_step = STATE_TO_STEP.get(state, 0)

    # stage_artifacts → per-node actual outputs
    stage_artifacts = tb.get("stage_artifacts") or []
    artifacts_by_node: dict[str, list[dict]] = {}
    for sa in stage_artifacts:
        if not isinstance(sa, dict):
            continue
        nid = sa.get("node_id") or sa.get("stage_id") or sa.get("stage")
        if isinstance(nid, str):
            artifacts_by_node.setdefault(nid, []).append(sa)

    nodes_view: list[dict] = []
    current_node_id: str | None = None
    completed_count = 0

    for node in NODE_CATALOG:
        node_step = node["step"]
        nv = {
            "id": node["id"],
            "name": node["name"],
            "code": node["code"],
            "phase": node["phase"],
            "owner_skill": node["owner_skill"],
            "step": node_step,
            "layout": dict(node["layout"]),
            "inputs": node["inputs"],
            "outputs_static": node["outputs"],
            "internal_workflow": node["internal_workflow"],
            "output_templates": node["output_templates"],
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "outputs_actual": list(artifacts_by_node.get(node["id"], [])),
        }

        # Status overlay
        if state == "CLOSED":
            nv["status"] = "passed"
            completed_count += 1
        elif is_aborted:
            if node_step < current_step:
                nv["status"] = "passed"
                completed_count += 1
            elif node_step == current_step:
                nv["status"] = "failed"
                current_node_id = node["id"]
            # else: pending
        elif is_paused:
            if current_step and node_step < current_step:
                nv["status"] = "passed"
                completed_count += 1
            elif current_step and node_step == current_step:
                nv["status"] = "failed"
                current_node_id = node["id"]
        elif current_step:
            if node_step < current_step:
                nv["status"] = "passed"
                completed_count += 1
            elif node_step == current_step:
                nv["status"] = "running"
                current_node_id = node["id"]

        # Timestamp overlay (only for 1:1 mapped nodes)
        bounds = NODE_STATE_BOUNDS.get(node_step)
        if bounds and nv["status"] in ("passed", "running", "failed"):
            start_state, end_state = bounds
            nv["started_at"] = state_ts.get(start_state)
            if nv["status"] == "passed":
                nv["completed_at"] = state_ts.get(end_state)

        nodes_view.append(nv)

    total = len(NODE_CATALOG)
    progress_pct = int(completed_count / total * 100) if total else 0

    return {
        "task_id": tb.get("task_id"),
        "kind": "delivery",
        "current_node_id": current_node_id,
        "current_state": state,
        "progress": {
            "completed": completed_count,
            "total": total,
            "percentage": progress_pct,
        },
        "nodes": nodes_view,
        "edges": EDGES_DELIVERY,
        "legend": {
            "phases": ["Initiating", "Planning", "Executing", "M&C", "Closing"],
            "edge_kinds": {
                "forward": "正向推进 (灰)",
                "augment": "增量补充 N7→N6 (绿虚)",
                "rollback": "失败回滚 (红虚)",
            },
            "node_status": {
                "pending": "未开始",
                "running": "进行中",
                "passed": "已通过",
                "failed": "失败",
                "rolled_back": "回滚中",
            },
        },
    }


# Convenience: expose layout viewBox for the frontend SVG.
LAYOUT_VIEWBOX: dict[str, Any] = {
    "min_x": 0,
    "min_y": 0,
    "width": 1660,
    "height": 400,
}
