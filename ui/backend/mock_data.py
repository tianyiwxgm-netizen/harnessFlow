"""Mock data loader — reads real task-boards + supplements v2 fields.

Real sources:
  - harnessFlow /task-boards/*.json (post-v1.1 + legacy p8-*)
  - harnessFlow /task-boards/cross-project/*.json
  - harnessFlow /task-boards/legacy/*.json (if any)
  - harnessFlow /retros/*.md
  - harnessFlow /verifier_reports/*.json
  - harnessFlow /failure-archive.jsonl
  - harnessFlow /supervisor-events/*.jsonl (if any)
  - harnessFlow /docs/superpowers/specs/*.md
  - harnessFlow /research/*.md
  - harnessFlow /plans/*.md
  - harnessFlow /sessions/*.md

Supplemented v2 fields (not yet written by real main skill):
  - tdd_cases[]
  - test_results{}
  - delivery_bundle{}
  - knowledge_refs[]
  - loop_history[]
  - progress_percentage (derived)

Knowledge-base entries: hard-coded mock seed (until real v2-B/C writes them).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline_catalog import derive_pipeline_view
from pipelines.card_emptiness import derive_card_states


HARNESS_ROOT = Path(__file__).resolve().parents[2]  # harnessFlow /


# ---------------- 中文正式描述 mock 映射 (task_id_prefix → 中文描述) ----------------
_MOCK_CN_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "p-harness-v1.3-supervisor-wake-hook": {
        "title_cn": "供应链采购 AI 预测项目",
        "summary_cn": "企业供应链采购板块基于 AI 大模型的智能需求预测系统（一期：核心 SKU）。",
        "description_cn": (
            "本项目为企业供应链采购板块构建一套基于 AI 大模型的智能需求预测系统，"
            "覆盖原材料、生产备件、MRO 三大品类的月度及季度采购量预测。"
            "系统从历史采购订单、出库记录、季节性趋势、供应商交付周期、"
            "外部大宗商品价格指数等多源数据出发，通过 LSTM + Transformer 混合时序模型生成需求预测，"
            "并附带不确定性置信区间，支撑采购经理的下单决策与安全库存优化。"
            "\n\n一期范围（本 Package）：完成核心品类（Top 200 SKU）历史数据接入 + 特征工程 + baseline 模型训练 "
            "+ 预测结果 BI 嵌入看板 + 与 SAP ERP 系统的双向联动（预测值写回 SAP MD61、实际采购量回流训练集）。"
            "\n\n交付标准：核心品类预测 MAPE ≤ 18%；覆盖 SKU ≥ 150 个；BI 看板可用性 MTBF ≥ 99%；"
            "与 SAP 对接零手工维护；一周一次的模型增量训练流水线稳定运行 ≥ 4 周。"
            "\n\n非目标（二期 / 三期推迟）：长尾 SKU 长期预测（数据量不足）、智能供应商推荐、"
            "自动下单闭环（合规与审计评估中）、跨厂区多工厂联合预测。"
        ),
    },
    "p-harness-v1.2-validate-stage-io": {
        "title_cn": "v1.2 stage_contracts 运行时校验器",
        "summary_cn": "实现 archive/stage_contracts/ Python 包，提供 v1.2 运行时阶段契约校验能力。",
        "description_cn": (
            "本项目实现 archive/stage_contracts/ Python 包，提供 harnessFlow v1.1 定义的 Stage Contract 运行时校验能力。"
            "\n\n交付 5 个模块：parser.py 读取 stage-contracts.md 的 yaml 代码块并解析为 StageContract 数据类列表；"
            "predicate_eval.py 以白名单 AST 子集安全求值 gate_predicate 字符串（拒绝 import / lambda / 任意函数调用）；"
            "validator.py 提供 validate_stage_io(task_board, stage_id, phase) 主入口，支持 enter 态检查 inputs 与 exit 态检查 outputs + gate_predicate；"
            "__main__.py 提供 python -m archive.stage_contracts list|validate CLI 子命令；__init__.py 导出公开 API。"
            "\n\n质量要求：至少 15 条 pytest 用例覆盖 parser / predicate_eval / validator / CLI，0 回归。"
            "\n\n非目标：Stop gate 集成、Supervisor 自动 DOD_GAP_ALERT（递延 v1.3）。路线 C-lite（省 prp-prd + santa-loop + mid-retro）。"
        ),
    },
    "p-assess-harnessFlow-deliverable": {
        "title_cn": "harnessFlow MVP 可交付评估",
        "summary_cn": "评估当前 harnessFlow MVP 对照自身 PRD Success Metrics 的达成情况，列出差距并给出交付路径建议。",
        "description_cn": (
            "本评估任务对当前 harnessFlow MVP 对照自身 PRD Success Metrics 进行完整差距分析，列出所有尚未完成项并给出明确的交付路径建议。"
            "\n\n走 F 路线（调研 → 决策文档）。主交付物：评估报告 markdown，覆盖 Phase 1-8 完成度、pytest 覆盖率、激活层状态、文档一致性、自举任务证据、剩余风险清单。"
            "\n\n次要需求两项："
            "\n（1）setup.sh 脚本自动检查与安装 Superpowers / everything-claude-code / gstack 三大前置 skill 生态；"
            "\n（2）将整个 harnessFlow/ 仓库上传至 GitHub 公有仓库 github.com/tianyiwxgm-netizen/harnessFlow.git 作为交付证据。"
        ),
    },
    "p-ai-video-seedance2": {
        "title_cn": "aigcv2 Package 1 Seedance 2.0 骨架",
        "summary_cn": "Package 1：seedance 2.0 AI-Agent 视频生成新项目骨架（A1 跑通骨架）。",
        "description_cn": (
            "本项目为 aigcv2 整体交付的 Package 1：seedance 2.0 AI-Agent 视频生成新项目骨架（代号 A1 跑通骨架）。"
            "新独立仓库路径 /Users/zhongtianyi/work/code/aiv2/。"
            "\n\n技术栈：后端 FastAPI + Python 3.11 + LangGraph + pydantic-settings；前端 Vue 3 + Element Plus + Vite + TypeScript；"
            "LLM 主编排选用 DeepSeek；视频 API 对接 Seedance 2.0（首轮 mock 模式，凭证延后）。"
            "\n\n交付骨架 DoD：pytest 全绿（mock 路径）；uvicorn app.main:app 启动后 curl /api/generate 返回 200 + mp4 URL；"
            "npm run dev 起 Vue 页面可提交 prompt 并展示结果；README.md 含启动指令与 Seedance 2.0 凭证接入说明。"
            "\n\n非目标：多 Agent 协作（留 Package 2）、TTS / 字幕 / OSS 上传（Package 3+）、抖音发布（Package 4+）、花钱硬拦截（Package 2）。"
            "\n\n注意：本 task 属于 aigcv2 项目 scope，不属 harnessFlow 本仓库 TODO。"
        ),
    },
    "p-harness-v2-ui-mock": {
        "title_cn": "v2-UI 最小可行任务管理页面",
        "summary_cn": "搭建 /harnessFlow-ui skill 的最小可行 UI，展示真实 task-boards 与 mock 填充的 v2 字段。",
        "description_cn": (
            "本项目为 /harnessFlow-ui skill 的最小可行版本（MVP），提供一个可视化的任务管理 Web 页面，展示本机所有 harnessFlow 任务与知识库。"
            "\n\n技术选型：后端 FastAPI（复用 aigc 环境已装）+ CDN Vue 3 + Element Plus（零 npm install，单 HTML 文件即可跑）。"
            "\n\n功能覆盖：任务列表（进行中 / 暂停 / 已完成三分组）、任务详情（项目交付目标 / 项目范围 / WBS / Harness 监督 / 执行时间轴 / 产出物链接 / TDD 质量 / Loop 历史 / Verifier 证据链 / 项目资料库 / 交付 Bundle 共 11 个 tab）、知识库视图（跨任务聚合的反模式 / 有效组合 / 外部引用 / 假完成陷阱）。"
            "\n\n交付：start.sh 一键启动 uvicorn 并自动打开浏览器；数据层由 mock_data.py 扫描真实 task-boards、retros、verifier_reports 并自动派生 v2 新字段（tdd_cases、test_results、delivery_bundle、knowledge_refs、loop_history）。"
            "\n\n非目标：真实后端写入、真 Supervisor 集成、WebSocket 实时推送、真实跨机器 kb 同步（均递延至 v2 后端 / v2-UI-B 后续切片）。"
        ),
    },
    "p-harness-phase9-p1-bundle": {
        "title_cn": "Phase 9 P1 批量缺陷修复",
        "summary_cn": "批量修复 5 个 P1 级缺陷，含 README 一致性、flaky test、self-test tail-5 bug、schema 程序化、task_type enum 扩展。",
        "description_cn": (
            "本项目批量修复 assessment-2026-04-17.md § 3 列出的 5 个 P1 级缺陷（route B / size M / risk 中）：\n"
            "（1）README.md Phase 8 状态对齐（pytest badge 89→100、加 v1.1 Stage Contract 行、测试段文字更新）；\n"
            "（2）archive/tests/test_writer.py::test_concurrent_writes_no_loss 加 3× retry + 60s timeout，修复全量 pytest 下偶发 flaky；\n"
            "（3）scripts/self-test.sh 模块 5 的 tail -5 裁剪 bug 改用 pytest exit code 判断；\n"
            "（4）新增 schemas/task-board.schema.json draft-07 严格 schema + archive/tests/test_task_board_schema.py 4 条自检（legacy p8-* 豁免）；\n"
            "（5）schemas/failure-archive.schema.json task_type enum 扩展加入 '元技能验证' 与 'meta-task' 两个值。\n\n"
            "DoD：5 修全部落地 + pytest 104/104 全绿 + 0 回归。"
        ),
    },
    "p-harness-phase9-p2-meta-bundle": {
        "title_cn": "Phase 9 P2 + 元一致性批量修复",
        "summary_cn": "批量修复 jsonschema deprecation / auditor 默认 dry-run / Stop gate 跨 session 过滤等 6 项缺陷。",
        "description_cn": (
            "本项目批量修复 Phase 9 P2 polish 级缺陷与 meta 一致性项（route B / size M / risk 中）：\n"
            "（1）scripts/self-test.sh 模块 4 使用 importlib.metadata.version 替换已废弃的 jsonschema.__version__；\n"
            "（2）archive/__main__.py cmd_audit 默认 dry-run，显式 --commit 才写 audit-reports/；\n"
            "（3）hooks/Stop-final-gate.sh 按 closed_at > session_start 过滤历史 CLOSED/ABORTED board 避免误阻；\n"
            "（4）将遗留 aiv2 task-board 归档至 task-boards/cross-project/ 子目录并写 README 说明跨项目约定；\n"
            "（5）method3.md § 8.12 新增反模式『schema 演化 legacy 豁免缺失』（5 条硬线 + P9-P1 案例研究）；\n"
            "（6）harness-flow.prd.md Phase 表扩展 v1.1 / v1.1-P1 / v1.1-P2 / v1.1-P3 四行。\n\n"
            "DoD：6 修全部落地 + pytest 104/104 + self-test 12/12 + CLI 回归 5/5。"
        ),
    },
    "p-harness-fix-p20-scope-drift": {
        "title_cn": "跨项目 scope 串误修复",
        "summary_cn": "修复 assessment / README / PRD 中将 P20 误列为 harnessFlow 自身 TODO 的跨项目串误。",
        "description_cn": (
            "本项目修复用户发现的一个重要跨项目 scope 串误缺陷（route A / size XS / risk 低）：assessment-2026-04-17.md / README.md / harness-flow.prd.md 中早期版本将 aigcv2 项目的 P20 真出片任务误列为 harnessFlow 自身 TODO。\n\n"
            "根因：将 PRD 的 MVP 验收手段（作为验证场景）误读为 harnessFlow 本项目的交付残项，导致 assessment 多处章节延续此串误。\n\n"
            "修复范围：\n"
            "（1）assessment § 1 加 ⚠ 纠偏 banner + § 3 P0 条删除 + § 4 L3 改跨项目应用场景 + § 5 路径 B/C 划除 + § 7 推荐重写；\n"
            "（2）README.md 的 P20 提及改成 '跨项目 handoff 工具，不是 harnessFlow 自身任务'；\n"
            "（3）method3.md § 8.11 新增反模式『跨项目 scope 串误』+ 4 条硬线防止未来再串。\n\n"
            "非目标：触碰 aigcv2 项目本身。"
        ),
    },
    "p-harness-stage-contract-v1": {
        "title_cn": "v1.1 Stage Contract 阶段契约层",
        "summary_cn": "为 A-F 六路线每阶段显式定义 inputs/outputs/gate_predicate，让上游产物等于下游输入。",
        "description_cn": (
            "本项目为 harnessFlow 新增 v1.1 Stage Contract 阶段契约层：对路线 A / B / C / D / E / F × 每个阶段（state）显式定义 "
            "inputs_required（来自上游阶段的 artifact_ref）+ outputs_produced（本阶段必产的 artifact_ref + schema）+ gate_predicate（机器可求值布尔）。\n\n"
            "核心不变量：上游阶段的 outputs 等于下游阶段的 inputs。任一阶段缺输入或缺输出或 gate 失败 → Supervisor 判 DOD_GAP_ALERT 红线 → PAUSED_ESCALATED。\n\n"
            "交付物：stage-contracts.md（~50 个 stage yaml 块，A-F 全覆盖） + schemas/stage-contract.schema.json（draft-07 严格）+ 挂接到 flow-catalog / state-machine / harnessFlow-skill / task-board-template 四处上游文档 + archive/tests/test_stage_contracts.py 自检 10 项。"
        ),
    },
    "p8-0-smoke": {
        "title_cn": "Phase 8.0 基础设施 smoke test",
        "summary_cn": "Phase 8.0：注册基础设施符号链接（skill / 4 subagent / 2 hook），运行 smoke 验证。",
        "description_cn": "本 task 为 Phase 8.0 基础设施登记：将 harnessFlow skill 符号链接至 .claude/skills/、4 个 subagent 链接至 .claude/agents/、2 个 hook 合并至 .claude/settings.local.json。route A（XS smoke test）豁免 retro 与 archive（按 delivery-checklist § 7.2 carve-out）。",
    },
    "p8-1-self-test": {
        "title_cn": "Phase 8.1 self-test.sh 自检脚本",
        "summary_cn": "Phase 8.1：新增 scripts/self-test.sh 一键自测脚本（6 模块 11 检查）。",
        "description_cn": "本 task 为 Phase 8.1 自检能力交付：新增 scripts/self-test.sh 一键自测（6 模块：skill / agents / hooks / python+jsonschema / pytest / auditor 边界，共 11 条检查）。作为 harnessFlow 自己的健康心跳 + CI smoke test 候选 + QUICKSTART 第一步。",
    },
    "p8-2-archive-cli": {
        "title_cn": "Phase 8.2 archive CLI 运维入口",
        "summary_cn": "Phase 8.2：新增 python -m archive list|audit|stats 三子命令 CLI 与 5 条 pytest。",
        "description_cn": "本 task 为 Phase 8.2 CLI 交付：新增 archive/__main__.py 实现 python -m archive list / audit / stats 三子命令，writer.py / auditor.py / retro_renderer.py 0 行改动，5 条 pytest 覆盖（3 happy + 1 empty + 1 bad-subcommand）。让 harnessFlow 从库升级到可运维工具。",
    },
}


def _cn_desc_for(task_id: str) -> dict | None:
    """按 task_id 前缀查找中文 mock 描述。"""
    for prefix, data in _MOCK_CN_DESCRIPTIONS.items():
        if task_id.startswith(prefix):
            return data
    return None


def _scope_dir_for(tb_path: Path) -> str:
    """Which subdir: root / cross-project / legacy"""
    parent_name = tb_path.parent.name
    if parent_name == "cross-project":
        return "cross-project"
    if parent_name == "legacy":
        return "legacy"
    return "main"


def list_all_task_boards() -> list[dict]:
    """Scan all task-boards and return enriched list."""
    boards: list[dict] = []
    patterns = [
        HARNESS_ROOT / "task-boards" / "*.json",
        HARNESS_ROOT / "task-boards" / "cross-project" / "*.json",
        HARNESS_ROOT / "task-boards" / "legacy" / "*.json",
    ]
    for pat in patterns:
        for p in sorted(Path(pat.parent).glob(pat.name)):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            enriched = _enrich_task_board(data, p)
            boards.append(enriched)

    # Sort: in-progress / paused first, closed last
    def sort_key(b: dict):
        state_order = {
            "INIT": 0, "CLARIFY": 0, "ROUTE_SELECT": 0, "PLAN": 0,
            "IMPL": 0, "VERIFY": 0, "COMMIT": 0,
            "PAUSED_ESCALATED": 1,
            "CLOSED": 2,
            "ABORTED": 2,
        }
        return (state_order.get(b.get("current_state", "CLOSED"), 2),
                -int(b.get("_updated_at_epoch", 0)))
    boards.sort(key=sort_key)
    return boards


def _enrich_task_board(data: dict, path: Path) -> dict:
    """Add mock v2 fields + derived fields to a real task-board."""
    tid = data.get("task_id", path.stem)
    stat = path.stat()
    data["_scope"] = _scope_dir_for(path)
    data["_path"] = str(path.relative_to(HARNESS_ROOT))
    data["_updated_at_epoch"] = int(stat.st_mtime)

    # derive progress_percentage from state_history length / expected route stages
    route = data.get("route_id") or data.get("route") or "?"
    expected_states = {
        "A": 4, "B": 7, "C": 10, "D": 6, "E": 8, "F": 5,
    }.get(route, 7)
    actual_states = len(data.get("state_history", []))
    current = data.get("current_state", "UNKNOWN")
    if current in ("CLOSED", "ABORTED"):
        progress = 100
    elif current == "PAUSED_ESCALATED":
        progress = min(90, int(actual_states / expected_states * 100))
    else:
        progress = min(95, int(actual_states / expected_states * 100))
    data["progress_percentage"] = progress

    # Supplement v2 fields if absent
    data.setdefault("tdd_cases", _mock_tdd_cases_for(data))
    data.setdefault("test_results", _mock_test_results_for(data))
    data.setdefault("delivery_bundle", _mock_delivery_bundle_for(data))
    data.setdefault("knowledge_refs", _mock_knowledge_refs_for(data))
    data.setdefault("loop_history", _mock_loop_history_for(data))

    # v2-UI PMP refactor: project-management aligned derivations
    data["_derived"] = {
        "summary": _derive_summary(data),
        "delivery_goal": _derive_delivery_goal(data),       # 项目交付目标 (100-2000字 + 交付标准)
        "scope": _derive_scope(data),                        # 项目范围 (included/excluded/dimensions)
        "wbs": _derive_wbs_packages(data),                   # WBS 工作包树 (5 PMP 过程组)
        "monitoring": _derive_pmp_monitoring(data),          # PMP 10 知识领域监督
        "project_library": _derive_project_library(data),    # 项目资料库
        "pipeline": derive_pipeline_view(data),               # Slice A: 13-node pipeline_graph view
        # legacy (kept for back-compat)
        "delivery_goals": _derive_delivery_goals(data),
        "plan": _derive_plan(data),
        "supervision": _derive_supervision(data),
    }
    # Slice A · Task 3.2: 6 卡 emptiness 状态（黄警示数据源）
    data["_derived"]["cards"] = derive_card_states(data)

    # Add artifact file pointers (for Artifacts Index view)
    data["_artifact_files"] = _discover_artifacts_for(tid, data)

    return data


# ---------------- v2-UI _derived builders ----------------

def _derive_summary(tb: dict) -> str:
    """产生 50-200 字摘要，优先用中文 mock title_cn/summary_cn。"""
    # 中文 mock 覆盖
    cn = _cn_desc_for(tb.get("task_id", ""))
    if cn and cn.get("title_cn"):
        # 标题用 title_cn（最简洁）
        return cn["title_cn"]

    text = (tb.get("goal_anchor") or {}).get("text") or tb.get("initial_user_input") or ""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "(暂无摘要)"

    # Cut before "Non-goal" etc
    for cutter in ["Non-goal", "Non-goals", "NOT doing", "Not doing", "不做", "不含", "非目标"]:
        idx = text.find(cutter)
        if 0 < idx < 400:
            text = text[:idx].rstrip(" ;,。.")
            break

    if len(text) <= 200:
        return text

    # Clamp to 200, prefer sentence boundaries; em-dash + colon are strong
    window = text[:200]
    for sep in ["。", ". ", "— ", " — ", "; ", "；", ": ", "：", ", ", ", "]:
        rpos = window.rfind(sep)
        if rpos > 60:
            return window[: rpos + 1].strip().rstrip("—:;,， ")
    # fallback: try to end at last word boundary
    last_space = window.rfind(" ")
    if last_space > 100:
        return window[:last_space].strip() + "…"
    return window.strip() + "…"


def _normalize_artifacts(raw: Any) -> list[dict]:
    """v1.6 fix defects #5: 把 task-board.artifacts 归一为 list[dict].

    schema 规定 artifacts 是 [{path, type, ...}]，但历史 LLM 写入存在
    [str, str, ...] / [{path}, "str", null, ...] 等违例形态；UI 后端遇到
    string 元素会 AttributeError ('str' has no .get) → /api/tasks 500 ISE
    → 整个 UI 列表挂掉。

    本函数把任意输入归一为 list[dict]：
      - dict           → 原样保留
      - str            → 降级 {"path": s, "type": "unknown"}
      - 其他（None/list/int 等） → 直接丢弃 (silent skip)

    UI 后端所有 artifacts 消费点必须先过本函数，避免 strict schema 没就位
    前老旧 task-board 让前端整体崩。
    """
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str):
            out.append({"path": item, "type": "unknown"})
        # 其他类型静默跳过，不让单条脏数据拖垮整个端点
    return out


def _derive_delivery_goals(tb: dict) -> list[dict]:
    """From artifacts_expected[] + dod_expression booleans."""
    out = []
    expected = tb.get("artifacts_expected") or []
    delivered = [a.get("path", "") for a in _normalize_artifacts(tb.get("artifacts"))]

    def is_done(item: str) -> bool:
        for d in delivered:
            if d and (d in item or item.endswith(d) or d.endswith(item.split("/")[-1])):
                return True
        return False

    for item in expected:
        status = "done" if is_done(item) else "planned"
        # Closed tasks → treat undelivered items as skipped
        if tb.get("current_state") in ("CLOSED",) and status == "planned":
            status = "done"  # closed means all originally-expected items landed (or were renegotiated)
        elif tb.get("current_state") == "PAUSED_ESCALATED" and status == "planned":
            status = "pending"
        out.append({"item": item, "status": status})
    return out


def _derive_scope(tb: dict) -> dict:
    """Parse Non-goal etc out of goal_anchor.text."""
    text = (tb.get("goal_anchor") or {}).get("text") or ""
    included, excluded = [], []

    # Simple: find "Non-goal" / "不做" section and split bullets
    for head in ["Non-goal", "Non-goals", "NOT doing", "Not doing", "不做", "非目标"]:
        idx = text.find(head)
        if idx > 0:
            tail = text[idx + len(head) :].strip(": \n")
            # split by common list separators
            for piece in re.split(r"[;；。\n]|\s+/\s+", tail):
                piece = piece.strip(" ;；,，.")
                if 3 < len(piece) < 200:
                    excluded.append(piece)
                if len(excluded) >= 5:
                    break
            break

    # Included = derived from summary
    included.append(_derive_summary(tb))

    # Also surface task_dimensions + route
    return {
        "included": included,
        "excluded": excluded,
        "dimensions": {
            "size": tb.get("size"),
            "task_type": tb.get("task_type"),
            "risk": tb.get("risk"),
            "route": tb.get("route_id") or tb.get("route"),
        },
    }


def _derive_plan(tb: dict) -> list[dict]:
    """Plan = stage sequence with status derived from state_history / current_state."""
    # Default plan skeleton by route (from flow-catalog.md)
    route = tb.get("route_id") or tb.get("route") or ""
    skeleton = {
        "A": [("CLARIFY", "澄清 + 三维识别"), ("IMPL", "直接改"), ("VERIFY", "pytest 验证"), ("COMMIT", "落地 commit")],
        "B": [("CLARIFY", "轻澄清 ≤ 2 轮"), ("PLAN", "prp-plan"), ("CHECKPOINT_SAVE", "save-session"),
              ("IMPL", "prp-implement + code-reviewer"), ("VERIFY", "Verifier 收口"),
              ("COMMIT", "prp-commit"), ("RETRO_CLOSE", "轻量 retro + archive")],
        "C": [("CLARIFY", "澄清 3 轮"), ("CLARIFY-PRD", "prp-prd"), ("PLAN", "prp-plan"),
              ("CHECKPOINT_SAVE", "save-session"), ("IMPL", "prp-implement + review"),
              ("MID_CHECKPOINT", "中途 checkpoint"), ("VERIFY", "Verifier 3 段证据链"),
              ("COMMIT", "prp-commit"), ("COMMIT-PR", "prp-pr"), ("RETRO_CLOSE", "retro 11 段 + archive")],
        "C-lite": [("CLARIFY", "澄清"), ("PLAN", "prp-plan"), ("CHECKPOINT_SAVE", "checkpoint"),
                   ("IMPL", "prp-implement"), ("VERIFY", "Verifier"), ("COMMIT", "prp-commit"),
                   ("RETRO_CLOSE", "retro + archive")],
        "D": [("CLARIFY", "视觉目标"), ("PLAN", "gan-design"), ("IMPL", "edit .vue/.css"),
              ("UI_SCREENSHOT", "playwright 截图"), ("VERIFY", "screenshot_has_content"),
              ("COMMIT", "prp-commit"), ("RETRO_CLOSE", "轻量 retro")],
        "E": [("CLARIFY", "graph 目标"), ("PLAN-GRAPHDIFF", "before/after graph"),
              ("PLAN", "prp-plan"), ("CHECKPOINT_SAVE", "checkpoint"),
              ("IMPL", "节点级 TDD"), ("EVAL", "eval regression"), ("VERIFY", "Verifier"),
              ("COMMIT", "prp-commit + PR"), ("RETRO_CLOSE", "retro + archive")],
        "F": [("CLARIFY", "问题定义"), ("RESEARCH", "调研"), ("DECISION_LOG", "决策文档"),
              ("VERIFY", "Verifier"), ("RETRO_CLOSE", "retro")],
    }
    stages = skeleton.get(route) or skeleton.get("B")

    # Map state_history to status
    visited_states = {entry.get("state"): entry for entry in (tb.get("state_history") or [])}
    current = tb.get("current_state", "")

    out = []
    passed_current = False
    for st, label in stages:
        if st in visited_states:
            status = "done"
        elif st == current or any(s in current for s in [st]):
            status = "in_progress"
            passed_current = True
        elif passed_current:
            status = "pending"
        else:
            status = "pending" if current not in ("CLOSED", "ABORTED") else "skipped"
        out.append({
            "stage": st,
            "label": label,
            "status": status,
            "timestamp": visited_states.get(st, {}).get("timestamp"),
            "trigger": visited_states.get(st, {}).get("trigger"),
        })

    # Mark overall done if CLOSED
    if current == "CLOSED":
        for o in out:
            if o["status"] in ("pending", "skipped"):
                o["status"] = "done"
    return out


def _derive_delivery_goal(tb: dict) -> dict:
    """项目交付目标：100-2000 字正式中文描述 + 交付标准 + 衡量方式。"""
    # 优先使用中文 mock 正式描述
    cn = _cn_desc_for(tb.get("task_id", ""))
    if cn:
        goal_text = cn["description_cn"]
    else:
        goal_text = (tb.get("goal_anchor") or {}).get("text") or tb.get("initial_user_input") or ""

    goal_text = goal_text.strip()
    summary = _derive_summary(tb)

    # 如果 description 少于 100 字，mock 扩展到合理长度
    if len(goal_text) < 100:
        tid = tb.get("task_id", "unknown-task")
        route = tb.get("route_id") or tb.get("route") or "?"
        task_type = tb.get("task_type") or "通用任务"
        goal_text = (goal_text + " ") if goal_text else ""
        goal_text += (
            f"\n\n【mock 扩展】本任务（{tid}）为 {task_type} 类任务，走 {route} 路线。"
            f"交付目标：围绕原始需求完成结构化交付（artifact 真存在 + 行为可验证 + 质量可审计）。"
            f"通过 Verifier 独立 eval DoD 布尔表达式，不依赖 agent 自报完成；"
            f"收口走 retro 11 段 + failure-archive schema-valid entry，"
            f"所有产出物登记进 project library，可跨 session resume。"
        )

    # 提取交付标准：从 dod_expression (boolean list) 或 artifacts_expected 构造
    standards: list[str] = []
    dod = tb.get("dod_expression") or ""
    if dod:
        # 把 AND 拆成独立断言
        for chunk in re.split(r"\s+AND\s+", dod):
            chunk = chunk.strip().strip("()")
            if 5 < len(chunk) < 200:
                standards.append(chunk)
    if not standards:
        for a in (tb.get("artifacts_expected") or [])[:8]:
            standards.append(f"交付 {a}")
    if not standards:
        # Mock 默认 DoD
        standards = [
            "所有 artifacts_expected 列出的产出全部交付到指定路径",
            "pytest 全量 pass（0 regression）",
            "Verifier 三段证据链（存在/行为/质量）全 PASS",
            "git commit 打包并推送到 GitHub",
            "retro + failure-archive entry 完整归档（schema-valid）",
        ]

    # 衡量方式
    route = tb.get("route_id") or tb.get("route") or "?"
    measurements = {
        "route": route,
        "size": tb.get("size"),
        "task_type": tb.get("task_type"),
        "risk": tb.get("risk"),
        "expected_artifacts_count": len(tb.get("artifacts_expected") or []),
        "final_outcome": tb.get("final_outcome") or "in-progress",
    }

    return {
        "summary_short": summary,
        "description": goal_text[:2000],           # 完整目标描述 (clamped 2000 字)
        "description_length": len(goal_text),
        "standards": standards,                    # 交付标准 list
        "measurements": measurements,
        "user_initial_prompt": tb.get("initial_user_input") or "",
    }


def _derive_wbs_packages(tb: dict) -> list[dict]:
    """WBS 工作包树：按 PMP 5 过程组分组。

    L1 过程组（启动/规划/执行/监控/收尾）
    L2 state 级工作包（state_history 衍生）
    L3+ 预留（真 v3 会按 skills_invoked 或 stage_artifacts 展开）
    """
    process_groups = [
        {"id": "WBS-1", "name": "1. 启动 (Initiating)", "states": ["INIT", "CLARIFY", "ROUTE_SELECT"],
         "color": "#409eff", "types": ["章程", "三维识别"]},
        {"id": "WBS-2", "name": "2. 规划 (Planning)", "states": ["PLAN", "CHECKPOINT_SAVE"],
         "color": "#67c23a", "types": ["PRD", "Plan", "WBS 分解", "save-session"]},
        {"id": "WBS-3", "name": "3. 执行 (Executing)", "states": ["IMPL", "MID_CHECKPOINT", "UI_SCREENSHOT", "RESEARCH"],
         "color": "#e6a23c", "types": ["实现", "代码", "调研"]},
        {"id": "WBS-4", "name": "4. 监控 (Monitoring & Controlling)", "states": ["MID_RETRO", "VERIFY", "SANTA_LOOP", "DECISION_LOG"],
         "color": "#8a2be2", "types": ["中途 retro", "Verifier", "纠偏 loop"]},
        {"id": "WBS-5", "name": "5. 收尾 (Closing)", "states": ["COMMIT", "RETRO_CLOSE", "CLOSED", "PAUSED_ESCALATED", "ABORTED"],
         "color": "#f56c6c", "types": ["commit", "retro 11 段", "archive", "closed"]},
    ]

    history = tb.get("state_history") or []
    visited = {}
    for e in history:
        if not isinstance(e, dict):
            continue
        st = e.get("state") or e.get("to") or e.get("state_label")
        if st:
            visited[st] = e
    current = tb.get("current_state", "")

    wbs_tree = []
    for pg in process_groups:
        # 本过程组是否有 state 已 visit
        pg_status = "pending"
        children = []
        for st in pg["states"]:
            if st in visited:
                st_status = "done"
                pg_status = "in_progress" if pg_status == "pending" else pg_status
            elif st == current:
                st_status = "in_progress"
                pg_status = "in_progress"
            else:
                st_status = "pending"
            children.append({
                "id": f"{pg['id']}.{st}",
                "level": 2,
                "name": st,
                "status": st_status,
                "timestamp": visited.get(st, {}).get("timestamp"),
                "trigger": visited.get(st, {}).get("trigger"),
                "reason": visited.get(st, {}).get("reason"),
                "deliverables": _wbs_deliverables_for(tb, st),   # 每 WBS 包的产出链接
            })
        # 过程组 status = 所有子 state 都 done?
        if all(c["status"] == "done" for c in children):
            pg_status = "done"
        elif any(c["status"] == "in_progress" for c in children):
            pg_status = "in_progress"
        elif any(c["status"] == "done" for c in children):
            pg_status = "in_progress"
        wbs_tree.append({
            "id": pg["id"],
            "level": 1,
            "name": pg["name"],
            "color": pg["color"],
            "pkg_types": pg["types"],
            "status": pg_status,
            "children": children,
        })

    return wbs_tree


def _wbs_deliverables_for(tb: dict, state: str) -> list[dict]:
    """每 WBS 包对应的产出链接（从 stage_artifacts / artifacts 取相关条目）。"""
    out = []
    stage_records = tb.get("stage_artifacts")
    if not isinstance(stage_records, list):
        return out
    for stage_rec in stage_records:
        if not isinstance(stage_rec, dict):
            continue
        stage_id = stage_rec.get("stage_id") or ""
        if not (stage_id.endswith(state) or state in stage_id):
            continue
        for art in _normalize_artifacts(stage_rec.get("artifacts")):
            out.append({"ref": art.get("artifact_ref"), "location": art.get("location", "")})
    return out


def _derive_pmp_monitoring(tb: dict) -> dict:
    """Harness 监督 — 8 大 agent-harness 监督维度（行业调研对齐）。

    参考 LangSmith / Langfuse / AgentOps / Arize / Datadog AI Agents Console
    等 2026 行业主流 agent observability 平台共性抽取。不照搬 PMP 10 项，
    改为对 AI agent 有意义的 8 维度：goal fidelity / plan alignment /
    true completion quality / red lines safety / progress pace / cost budget /
    retry loop / user collaboration。
    """
    from collections import Counter
    red_lines = tb.get("red_lines") or []
    interventions = tb.get("supervisor_interventions") or []
    retries = tb.get("retries") or []
    loop_history = tb.get("loop_history") or []
    warn_counter = tb.get("warn_counter") or 0
    route_changes = tb.get("route_changes") or []
    time_budget = tb.get("time_budget") or {}
    cost_budget = tb.get("cost_budget") or {}
    context_budget = tb.get("context_budget") or {}
    skills = tb.get("skills_invoked") or []
    state_history = tb.get("state_history") or []

    # Plan alignment
    route = tb.get("route_id") or tb.get("route") or "?"
    expected_states = {"A": 4, "B": 7, "C": 10, "D": 6, "E": 8, "F": 5, "C-lite": 7}.get(route, 7)
    actual_states = len(state_history)
    plan_variance_pct = round((actual_states - expected_states) / max(expected_states, 1) * 100, 1)
    skipped = max(0, expected_states - actual_states) if tb.get("current_state") == "CLOSED" else 0

    # Cost
    tokens_used = cost_budget.get("token_used", 0) or 0
    tokens_cap = cost_budget.get("token_cap", 0) or 0
    cost_util = round(tokens_used / tokens_cap, 3) if tokens_cap else None

    # True completion
    vr = tb.get("verifier_report") or {}
    checks = vr.get("evidence_checks", [])
    pass_count = sum(1 for c in checks if c.get("result") is True)
    verifier_pass_rate = round(pass_count / len(checks), 3) if checks else None
    three_segs = vr.get("three_segments") or {}
    evidence_filled = sum(1 for k in ("existence_evidence", "behavior_evidence", "quality_evidence") if three_segs.get(k))

    # Red lines 分类
    drift_critical = sum(1 for rl in red_lines if "DRIFT" in (rl.get("code") or ""))
    dod_gap = sum(1 for rl in red_lines if "DOD_GAP" in (rl.get("code") or ""))
    irrev_halt = sum(1 for rl in red_lines if "IRREVERSIBLE" in (rl.get("code") or ""))
    cross_proj = sum(1 for rl in red_lines if "CROSS_PROJECT" in (rl.get("code") or ""))

    # Retry / loop detection
    stuck_pattern = 0
    if retries:
        cnt = Counter(r.get("err_class") for r in retries)
        stuck_pattern = sum(1 for _, v in cnt.items() if v >= 3)

    # User collaboration
    user_interrupts = sum(1 for s in state_history if "user" in (s.get("trigger") or ""))
    if user_interrupts == 0 and tb.get("initial_user_input"):
        user_interrupts = 1
    clarify_rounds = sum(1 for s in state_history if s.get("state") == "CLARIFY")
    pause_events = sum(1 for s in state_history if s.get("state") == "PAUSED_ESCALATED")

    return {
        "goal_fidelity": {
            "label": "目标保真度",
            "desc": "goal_anchor sha256 漂移 / CLAUDE.md 篡改检测",
            "goal_anchor_hash_drift": drift_critical,
            "claude_md_tamper_count": drift_critical,
            "goal_preserved": "✓" if drift_critical == 0 else "✗",
            "health": "red" if drift_critical else "green",
        },
        "plan_alignment": {
            "label": "计划对齐",
            "desc": "实际 state 序列 vs 路线骨架偏差",
            "actual_states": actual_states,
            "expected_states": expected_states,
            "variance_pct": plan_variance_pct,
            "skipped_stages": skipped,
            "route_changes": len(route_changes),
            "health": "yellow" if abs(plan_variance_pct) > 30 or len(route_changes) > 0 else "green",
        },
        "true_completion": {
            "label": "真完成质量",
            "desc": "Verifier 通过率 / 三段证据链 / DoD 布尔 eval",
            "verifier_pass_rate": verifier_pass_rate if verifier_pass_rate is not None else "—",
            "tdd_cases_total": len(tb.get("tdd_cases") or []),
            "tdd_pass": sum(1 for c in (tb.get("tdd_cases") or []) if c.get("status") == "pass"),
            "evidence_segments_filled": f"{evidence_filled}/3",
            "flaky_count": len((tb.get("test_results") or {}).get("flaky_rerun", [])),
            "health": "red" if (verifier_pass_rate is not None and verifier_pass_rate < 0.8) else ("yellow" if verifier_pass_rate is None else "green"),
        },
        "red_lines_safety": {
            "label": "红线与安全",
            "desc": "3 红线触发 + 跨项目 scope drift",
            "drift_critical": drift_critical,
            "dod_gap_alert": dod_gap,
            "irreversible_halt": irrev_halt,
            "cross_project_creep": cross_proj,
            "total_red_lines": len(red_lines),
            "health": "red" if red_lines else "green",
        },
        "progress_pace": {
            "label": "进度与节奏",
            "desc": "耗时 / 工具调用密度 / subagent 负载",
            "elapsed_sec": time_budget.get("elapsed_sec") or "—",
            "cap_sec": time_budget.get("cap_sec") or "—",
            "tool_calls_total": len(skills),
            "avg_tools_per_stage": round(len(skills) / max(actual_states, 1), 1) if actual_states else 0,
            "subagents_spawned": sum(1 for s in skills if "harnessFlow:" in (s.get("source") or "")),
            "health": "green",
        },
        "cost_budget": {
            "label": "成本与预算",
            "desc": "token / $ / context 占用率",
            "tokens_used": tokens_used,
            "tokens_cap": tokens_cap or "—",
            "utilization": cost_util if cost_util is not None else "—",
            "context_tokens": context_budget.get("tokens_in_context") or "—",
            "context_threshold": context_budget.get("threshold") or "—",
            "health": "yellow" if cost_util and cost_util > 0.8 else "green",
        },
        "retry_loop": {
            "label": "重试与 Loop",
            "desc": "retry / santa-loop / replan 循环检测",
            "retry_count": len(retries),
            "santa_loop_rounds": sum(1 for lh in loop_history if "santa" in (lh.get("kind") or "").lower()),
            "replan_count": sum(1 for lh in loop_history if "replan" in (lh.get("kind") or "").lower()),
            "stuck_pattern_detected": stuck_pattern,
            "warn_counter": warn_counter,
            "health": "yellow" if (len(retries) >= 3 or stuck_pattern > 0 or warn_counter >= 5) else "green",
        },
        "user_collaboration": {
            "label": "用户协作",
            "desc": "用户打断 / 澄清轮次 / 废问题",
            "user_interrupts": user_interrupts,
            "clarify_rounds": clarify_rounds,
            "pause_events": pause_events,
            "waste_questions": 0,
            "health": "yellow" if pause_events > 0 else "green",
        },
    }


def _derive_project_library(tb: dict) -> dict:
    """项目资料库：仓库 + 文档 + UI + 过程文档汇聚。"""
    tid = tb.get("task_id", "")

    # repos — harnessFlow 主 repo + task 所属项目的关联仓库
    repos = [{
        "name": "harnessFlow",
        "url": "https://github.com/tianyiwxgm-netizen/harnessFlow",
        "branch": "main",
        "commit": tb.get("commit_sha") or "—",
        "role": "主 repo（监督与编排）",
    }]

    # 跨项目 task 还要加关联项目的 repo
    if tb.get("_scope") == "cross-project":
        repos.append({
            "name": "aigc (guess)",
            "url": "https://github.com/tianyiwxgm-netizen/aigc",
            "branch": "—",
            "commit": "—",
            "role": "本 task 属于的业务 repo（跨项目）",
        })

    # docs — 文件系统发现
    docs = []
    af = tb.get("_artifact_files") or []
    for f in af:
        kind = f.get("kind", "doc")
        docs.append({
            "name": f.get("name", ""),
            "url": f"/api/tasks/{tid}/md?path={f.get('path','')}",
            "type": kind,
            "local_path": f.get("path", ""),
            "size_bytes": f.get("size_bytes", 0),
        })

    # UI 本身也是资料
    ui_entries = [{
        "name": "harnessFlow-ui（本页）",
        "url": "http://localhost:8765",
        "type": "web_ui",
    }]

    # 过程文档：PRD / plan / retro / verifier_report
    process_docs = [
        {"kind": "PRD", "path": "harness-flow.prd.md", "description": "项目全局 PRD"},
        {"kind": "method3", "path": "method3.md", "description": "方法论根宪章"},
        {"kind": "harness", "path": "harnessFlow.md", "description": "顶层架构"},
        {"kind": "flow-catalog", "path": "flow-catalog.md", "description": "6 路线调度骨架"},
    ]

    return {
        "repos": repos,
        "docs": docs,
        "ui": ui_entries,
        "process_docs": process_docs,
    }


def _derive_supervision(tb: dict) -> dict:
    """Aggregate monitoring events: red_lines / interventions / warns / retries / replans."""
    red_lines = tb.get("red_lines") or []
    interventions = tb.get("supervisor_interventions") or []
    retries = tb.get("retries") or []
    loop_history = tb.get("loop_history") or []
    warn_counter = tb.get("warn_counter") or 0
    pause_reason = tb.get("pause_reason") or ""
    resume_when = tb.get("resume_when") or ""

    # Build a time-ordered event list
    events: list[dict] = []
    for r in red_lines:
        events.append({
            "kind": "red_line",
            "severity": "BLOCK",
            "code": r.get("code", "?"),
            "message": r.get("context") or r.get("resolution") or "",
            "timestamp": r.get("triggered_at"),
        })
    for i in interventions:
        events.append({
            "kind": "intervention",
            "severity": i.get("severity", "INFO"),
            "code": i.get("code", "?"),
            "message": i.get("diagnosis", ""),
            "timestamp": i.get("timestamp"),
        })
    for r in retries:
        events.append({
            "kind": "retry",
            "severity": "WARN",
            "code": r.get("err_class", "?"),
            "message": f"retry {r.get('level','L?')}: {r.get('outcome','?')}",
            "timestamp": r.get("timestamp"),
        })
    for lh in loop_history:
        events.append({
            "kind": "replan",
            "severity": "INFO",
            "code": lh.get("kind", "?"),
            "message": f"iteration {lh.get('iteration')}: {lh.get('trigger','')}",
            "timestamp": lh.get("started_at"),
        })
    events.sort(key=lambda e: e.get("timestamp") or "")

    # Health summary
    health = "green"
    if red_lines:
        health = "red"
    elif warn_counter > 0 or len([e for e in events if e["severity"] == "WARN"]) > 0:
        health = "yellow"

    return {
        "health": health,
        "red_lines_count": len(red_lines),
        "interventions_count": len(interventions),
        "warns_count": warn_counter,
        "retries_count": len(retries),
        "replans_count": len(loop_history),
        "pause_reason": pause_reason,
        "resume_when": resume_when,
        "events": events,
    }


def _mock_tdd_cases_for(tb: dict) -> list[dict]:
    """Synthesize TDD cases from verifier_report.evidence_checks if present."""
    vr = tb.get("verifier_report") or {}
    checks = vr.get("evidence_checks", [])
    if not checks:
        return []
    return [
        {
            "case_id": f"tc-{i+1:02}",
            "name": c.get("check", "?"),
            "target": str(c.get("target", "")),
            "expected": str(c.get("expected", "?"))[:100],
            "actual": str(c.get("actual", "?"))[:100],
            "status": "pass" if c.get("result") is True else ("fail" if c.get("result") is False else "pending"),
            "last_run": tb.get("closed_at") or tb.get("created_at"),
            "primitive": c.get("primitive"),
        }
        for i, c in enumerate(checks)
    ]


def _mock_test_results_for(tb: dict) -> dict:
    """Extract from verifier_report if available; else mock sensible defaults."""
    vr = tb.get("verifier_report") or {}
    for c in vr.get("evidence_checks", []):
        target_str = str(c.get("target", ""))
        # More permissive matching: any "pytest" or "test" check with tests_total
        if c.get("tests_total") is not None or "pytest" in target_str or "test" in target_str.lower():
            total = c.get("tests_total", 0) or 0
            passed = c.get("tests_passed", 0) or 0
            if total > 0:
                return {
                    "total": total,
                    "passed": passed,
                    "failed": max(0, total - passed),
                    "skipped": 0,
                    "flaky_rerun": [],
                    "coverage_pct": 0.0,
                    "last_run": tb.get("closed_at") or tb.get("created_at"),
                    "duration_sec": 11.7,
                }
    # Mock default for tasks without test info
    state = tb.get("current_state", "")
    if state in ("CLOSED",):
        return {
            "total": 104, "passed": 104, "failed": 0, "skipped": 0,
            "flaky_rerun": [], "coverage_pct": 0.0,
            "last_run": tb.get("closed_at") or tb.get("created_at"),
            "duration_sec": 11.7,
        }
    return {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0,
        "flaky_rerun": [], "coverage_pct": None, "last_run": None, "duration_sec": None,
    }


def _mock_delivery_bundle_for(tb: dict) -> dict:
    return {
        "primary_artifact": tb.get("retro_link") or "",
        "commit_sha": None,  # could be mined from git log but mock for now
        "pr_url": None,
        "retro_link": tb.get("retro_link"),
        "archive_entry_link": tb.get("archive_entry_link"),
        "user_consumable": tb.get("final_outcome") == "success",
        "delivered_at": tb.get("closed_at"),
    }


def _mock_knowledge_refs_for(tb: dict) -> list[dict]:
    """Mock knowledge_refs — pick some entries based on task_id/route heuristic."""
    task_id = tb.get("task_id", "")
    route = tb.get("route_id") or "?"
    refs = []
    if "phase9-p1" in task_id:
        refs.append({
            "kind": "anti_pattern",
            "ref": "kb-anti-legacy-carve-out",
            "used_at_stage": "IMPL",
            "why": "新增 task-board schema 要 legacy grandfather",
        })
    if "stage-contract" in task_id:
        refs.append({
            "kind": "effective_combo",
            "ref": "kb-combo-yaml-in-md-schema",
            "used_at_stage": "IMPL",
            "why": "schema + yaml-in-md + pytest closure 三件套",
        })
    if "p20" in task_id.lower() or "scope" in task_id:
        refs.append({
            "kind": "anti_pattern",
            "ref": "kb-anti-cross-project-drift",
            "used_at_stage": "CLARIFY",
            "why": "识别跨项目 scope 串误",
        })
    if route in ("B", "C", "C-lite"):
        refs.append({
            "kind": "external_ref",
            "ref": "kb-ref-anthropic-harness",
            "used_at_stage": "PLAN",
            "why": "Anthropic effective harnesses blog 作为 plan-anchor 参考",
        })
    if "bundle" in task_id.lower() or "phase9-p2" in task_id:
        refs.append({
            "kind": "effective_combo",
            "ref": "kb-combo-bundle-fix",
            "used_at_stage": "PLAN",
            "why": "多缺陷一次性修复复用模式",
        })
    if "ui" in task_id.lower() or "v2" in task_id:
        refs.append({
            "kind": "effective_combo",
            "ref": "kb-combo-yaml-in-md-schema",
            "used_at_stage": "IMPL",
            "why": "UI 原型 mock data 用同样 schema 驱动",
        })
    # Ensure every task has at least 1 mock ref
    if not refs:
        refs.append({
            "kind": "external_ref",
            "ref": "kb-ref-anthropic-harness",
            "used_at_stage": tb.get("current_state", "CLARIFY"),
            "why": "默认 mock：Anthropic long-running agent harness 参考",
        })
    return refs


def _mock_loop_history_for(tb: dict) -> list[dict]:
    """Derive from retries[] or return empty."""
    retries = tb.get("retries", []) or []
    history = []
    for i, r in enumerate(retries):
        history.append({
            "iteration": i + 1,
            "kind": "retry_ladder",
            "trigger": r.get("err_class", "unknown"),
            "started_at": r.get("timestamp"),
            "resolved_at": r.get("timestamp"),
            "outcome": r.get("outcome", "unknown"),
        })
    return history


def _discover_artifacts_for(task_id: str, tb: dict) -> list[dict]:
    """Scan well-known dirs for files linked to this task_id."""
    files = []
    patterns = [
        ("retro", HARNESS_ROOT / "retros", f"{task_id}.md"),
        ("retro_notes", HARNESS_ROOT / "retros", f"{task_id}.notes.json"),
        ("verifier_report", HARNESS_ROOT / "verifier_reports", f"{task_id}.json"),
        ("session_checkpoint", HARNESS_ROOT / "sessions", "v1.2-*.md"),  # loose match
    ]
    for kind, dir_, pat in patterns:
        if not dir_.exists():
            continue
        for p in dir_.glob(pat):
            if task_id in p.stem or pat.startswith("v1.2") and "v1.2" in task_id:
                files.append({
                    "kind": kind,
                    "path": str(p.relative_to(HARNESS_ROOT)),
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                })
    # Plans (by task_id fragment match)
    plans_dir = HARNESS_ROOT / "plans"
    if plans_dir.exists():
        tid_frag = task_id.replace("p-harness-", "").split("-")[0]
        for p in plans_dir.glob(f"*{tid_frag}*.md"):
            files.append({"kind": "plan", "path": str(p.relative_to(HARNESS_ROOT)),
                          "name": p.name, "size_bytes": p.stat().st_size})
    # Research
    research_dir = HARNESS_ROOT / "research"
    if research_dir.exists():
        for p in research_dir.glob("*.md"):
            if "v2" in task_id and "v2" in p.name:
                files.append({"kind": "research", "path": str(p.relative_to(HARNESS_ROOT)),
                              "name": p.name, "size_bytes": p.stat().st_size})
    # Specs
    specs_dir = HARNESS_ROOT / "docs" / "superpowers" / "specs"
    if specs_dir.exists():
        for p in specs_dir.glob("*.md"):
            if "v2" in task_id and "v2" in p.name:
                files.append({"kind": "spec", "path": str(p.relative_to(HARNESS_ROOT)),
                              "name": p.name, "size_bytes": p.stat().st_size})
    return files


def get_task_board(task_id: str) -> dict | None:
    """Return one task-board enriched."""
    for b in list_all_task_boards():
        if b.get("task_id") == task_id:
            return b
    return None


def read_markdown_file(relative_path: str) -> str | None:
    """Read a markdown file by harnessFlow-root-relative path."""
    full = HARNESS_ROOT / relative_path
    if not full.exists() or not full.is_file():
        return None
    # Only allow .md / .json / .txt files inside harnessFlow root
    try:
        full.resolve().relative_to(HARNESS_ROOT.resolve())
    except ValueError:
        return None
    if full.suffix not in (".md", ".json", ".txt", ".jsonl"):
        return None
    return full.read_text(encoding="utf-8", errors="replace")


# ------------------ Mock Knowledge Base ------------------

def mock_knowledge_base() -> list[dict]:
    """Hard-coded seed KB entries representing v2's knowledge-base output."""
    return [
        {
            "id": "kb-anti-legacy-carve-out",
            "kind": "anti_pattern",
            "scope": "project",
            "project_id": "harnessFlow-meta",
            "title": "schema 演化 legacy 豁免缺失",
            "description": "新增严格 schema 时若不给历史数据留豁免路径 → scope creep: 要么改老数据破坏审计历史，要么放宽 schema 让新契约失效。",
            "rule": "SCHEMA_ADD_NO_LEGACY_GRANDFATHER",
            "evidence": {
                "first_observed_in_task": "p-harness-phase9-p1-bundle-20260417T200000Z",
                "observed_count": 2,
                "last_observed_at": "2026-04-18T09:35:00Z",
            },
            "applicable_context": {"route": ["B", "C"], "task_type": ["重构"]},
            "references": ["method3 § 8.12"],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-17T20:30:00Z",
            "updated_at": "2026-04-18T09:35:00Z",
        },
        {
            "id": "kb-anti-cross-project-drift",
            "kind": "anti_pattern",
            "scope": "global",
            "project_id": None,
            "title": "跨项目 scope 串误",
            "description": "harness 把另一个项目的任务列为本项目 TODO；典型：harnessFlow 把 aigcv2 的 P20 列进自己 P0。根因：误把 MVP 验收手段当项目 TODO。",
            "rule": "CROSS_PROJECT_TODO_POLLUTION",
            "evidence": {
                "first_observed_in_task": "p-harness-fix-p20-scope-drift-20260417T205000Z",
                "observed_count": 1,
                "last_observed_at": "2026-04-17T21:00:00Z",
            },
            "applicable_context": {"route": ["A", "B", "C"], "task_type": ["文档", "重构"]},
            "references": ["method3 § 8.11"],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-17T21:00:00Z",
            "updated_at": "2026-04-17T21:00:00Z",
        },
        {
            "id": "kb-combo-yaml-in-md-schema",
            "kind": "effective_combo",
            "scope": "project",
            "project_id": "harnessFlow-meta",
            "title": "schema + yaml-in-md + pytest-closure 三件套",
            "description": "让文档级契约可机器校验：JSON Schema + markdown 内嵌 yaml block + pytest 自检，避免 '写了文档但没 enforce' 的假完成。",
            "rule": "STRUCTURED_DOC_CONTRACT_PATTERN",
            "evidence": {
                "first_observed_in_task": "p-harness-stage-contract-v1-20260417T185000Z",
                "observed_count": 2,
                "last_observed_at": "2026-04-18T10:00:00Z",
            },
            "applicable_context": {"route": ["B", "C"], "task_type": ["重构", "文档"]},
            "references": ["stage-contracts.md", "schemas/stage-contract.schema.json"],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-17T19:30:00Z",
            "updated_at": "2026-04-18T10:00:00Z",
        },
        {
            "id": "kb-combo-bundle-fix",
            "kind": "effective_combo",
            "scope": "project",
            "project_id": "harnessFlow-meta",
            "title": "Bundle-fix pattern（多个小缺陷一起修）",
            "description": "对同类多处缺陷清单，一次 B 路线 bundle 修 + 共用 commit + 共用 retro，效率 >> 单独修。cold-start 消除后第 2 次 0 retry。",
            "rule": "BUNDLE_FIX_MULTI_DEFECT",
            "evidence": {
                "first_observed_in_task": "p-harness-phase9-p1-bundle-20260417T200000Z",
                "observed_count": 3,
                "last_observed_at": "2026-04-18T09:35:00Z",
            },
            "applicable_context": {"route": ["B"], "task_type": ["重构"]},
            "references": [],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-17T20:30:00Z",
            "updated_at": "2026-04-18T09:35:00Z",
        },
        {
            "id": "kb-ref-anthropic-harness",
            "kind": "external_ref",
            "scope": "global",
            "project_id": None,
            "title": "Anthropic — Effective harnesses for long-running agents",
            "description": "Initializer + Coding agent 两阶段；feature_list.json canonical plan；claude-progress.txt 叙事；git commit 作 checkpoint；E2E 测试驱动 drift detection。",
            "rule": "ANTHROPIC_HARNESS_PATTERN",
            "evidence": {"observed_count": 1, "last_observed_at": "2026-04-18T11:00:00Z"},
            "applicable_context": {"route": ["C", "E"], "task_type": ["重构", "agent graph"]},
            "references": [
                "https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents"
            ],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-18T11:00:00Z",
            "updated_at": "2026-04-18T11:00:00Z",
        },
        {
            "id": "kb-trap-fake-completion-p20",
            "kind": "trap",
            "scope": "global",
            "project_id": None,
            "title": "P20 假完成陷阱（pipeline 无 error ≠ 真出片）",
            "description": "Agent 报 success 但实际没起服务、没 POST、没校验 mp4、没查 OSS key。AutoGen is_termination_msg 同系列陷阱。",
            "rule": "PIPELINE_OK_BUT_NO_ARTIFACT",
            "evidence": {"observed_count": 1, "last_observed_at": "2026-04-16T..."},
            "applicable_context": {"route": ["C"], "task_type": ["视频出片"]},
            "references": ["method3 § 8.1", "harness-flow.prd.md § Evidence"],
            "version": 1,
            "status": "active",
            "supersedes": [],
            "superseded_by": None,
            "expires_at": None,
            "created_at": "2026-04-16T...",
            "updated_at": "2026-04-18T11:00:00Z",
        },
    ]


def mock_projects() -> list[dict]:
    return [
        {
            "project_id": "harnessFlow-meta",
            "name": "harnessFlow meta-skill",
            "domain": "AI agent harness / meta-orchestration",
            "linked_repos": ["harnessFlow "],
            "anchor_mode": "single_repo",
            "created_at": "2026-04-16T...",
            "task_count": 6,
        },
        {
            "project_id": "aigc-video-pipeline",
            "name": "aigc 视频生产流水线",
            "domain": "视频生成 / 内容创作",
            "linked_repos": ["aigc", "aiv2"],
            "anchor_mode": "multi_repo",
            "created_at": "2026-04-17T09:01:31Z",
            "task_count": 1,
        },
    ]


# ===================================================================
# 后台管理 Mock Data — 8 大模块（执行引擎 / 执行实例 / 知识库 / Harness 监督 /
#                               Verifier 原语库 / Subagents / Skills / 统计 / 诊断）
# ===================================================================

def _admin_engine_config() -> dict:
    """执行引擎配置：6 路线 + 20 状态 + 42-cell routing matrix + 3 红线 + retry 阶梯。"""
    routes = [
        {
            "id": "A",
            "name": "A · 快速修 Bug / 小改动",
            "size": "S",
            "risk": "低",
            "task_type": "bugfix / 小功能",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "IMPL", "VERIFY", "COMMIT", "RETRO_CLOSE", "CLOSED"],
            "skill_chain": ["superpowers:brainstorming", "superpowers:test-driven-development", "superpowers:verification-before-completion"],
            "description": "适合 < 1 小时可完成、无架构变更的小任务；跳过完整 PLAN，直接进 IMPL。",
        },
        {
            "id": "B",
            "name": "B · 标准功能开发",
            "size": "M",
            "risk": "中",
            "task_type": "新功能 / 模块改造",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "IMPL", "VERIFY", "COMMIT", "RETRO_CLOSE", "CLOSED"],
            "skill_chain": ["superpowers:brainstorming", "superpowers:writing-plans", "superpowers:test-driven-development", "superpowers:executing-plans", "superpowers:verification-before-completion"],
            "description": "最常用路线；含完整 plan + TDD + verifier 证据链，适合 1-8 小时的功能开发。",
        },
        {
            "id": "C",
            "name": "C · 复杂大项目（PRP 长周期）",
            "size": "L",
            "risk": "中 / 高",
            "task_type": "长周期 / 多 Package",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "IMPL", "VERIFY", "SANTA_LOOP", "COMMIT", "RETRO_CLOSE", "CLOSED"],
            "skill_chain": ["prp-prd", "prp-plan", "prp-implement", "santa-loop", "prp-commit", "prp-pr"],
            "description": "PRP 标准六步流程；含 santa-loop 质量兜底，适合跨多 session 的长周期项目。",
        },
        {
            "id": "D",
            "name": "D · UI / 视觉专线",
            "size": "M / L",
            "risk": "低",
            "task_type": "前端 UI / 设计",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "IMPL", "UI_SCREENSHOT", "VERIFY", "COMMIT", "RETRO_CLOSE", "CLOSED"],
            "skill_chain": ["gstack:brainstorm", "gan-design", "Edit", "gstack:browse", "design-review", "superpowers:verification-before-completion"],
            "description": "UI 专线；含 UI_SCREENSHOT 状态用 Playwright 真实浏览器截屏作为 verifier 证据。",
        },
        {
            "id": "E",
            "name": "E · 高风险 / 不可逆 / 生产改动",
            "size": "任意",
            "risk": "高",
            "task_type": "生产部署 / DB 迁移 / 不可逆操作",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "RISK_REVIEW", "USER_AUTHORIZE", "IMPL", "VERIFY", "COMMIT", "RETRO_CLOSE", "CLOSED"],
            "skill_chain": ["superpowers:brainstorming", "superpowers:writing-plans", "security-reviewer", "代码审查 subagent", "user 显式授权"],
            "description": "强制 USER_AUTHORIZE 状态，IRREVERSIBLE_HALT 红线兜底；force-push / DB drop / prod 部署走这条。",
        },
        {
            "id": "F",
            "name": "F · 调研 / 文档 / 无代码",
            "size": "S / M",
            "risk": "低",
            "task_type": "调研 / 文档",
            "skeleton": ["INIT", "CLARIFY", "ROUTE_SELECT", "RESEARCH", "DOC_WRITE", "COMMIT", "CLOSED"],
            "skill_chain": ["docs-lookup", "context7", "exa.web_search_exa", "WebFetch"],
            "description": "无 code 改动；产出 md 文档 + 引用列表；跳 TDD / VERIFY。",
        },
    ]

    states = [
        {"name": "INIT", "phase": "启动", "description": "task-board 初始化 + 读 CLAUDE.md + 加载 memory", "allowed_next": ["CLARIFY"]},
        {"name": "CLARIFY", "phase": "启动", "description": "用户意图澄清 + goal_anchor sha256 锁定", "allowed_next": ["ROUTE_SELECT"]},
        {"name": "ROUTE_SELECT", "phase": "规划", "description": "根据 size × type × risk 选 6 路线之一", "allowed_next": ["PLAN", "IMPL", "RESEARCH"]},
        {"name": "PLAN", "phase": "规划", "description": "详细实施计划 + DoD 锁定 + Stage Contract 生成", "allowed_next": ["IMPL", "RISK_REVIEW"]},
        {"name": "RISK_REVIEW", "phase": "规划", "description": "E 路线专用；security-reviewer 审核高风险改动", "allowed_next": ["USER_AUTHORIZE"]},
        {"name": "USER_AUTHORIZE", "phase": "规划", "description": "E 路线专用；用户显式文本授权不可逆操作", "allowed_next": ["IMPL", "ABORTED"]},
        {"name": "RESEARCH", "phase": "执行", "description": "F 路线专用；外部文档/网页调研", "allowed_next": ["DOC_WRITE"]},
        {"name": "DOC_WRITE", "phase": "执行", "description": "F 路线专用；产出 markdown 文档", "allowed_next": ["COMMIT"]},
        {"name": "IMPL", "phase": "执行", "description": "编码实施；TDD 先写测试后写代码", "allowed_next": ["UI_SCREENSHOT", "VERIFY"]},
        {"name": "UI_SCREENSHOT", "phase": "执行", "description": "D 路线专用；Playwright 截屏作 verifier 证据", "allowed_next": ["VERIFY"]},
        {"name": "VERIFY", "phase": "验证", "description": "verifier subagent 读 DoD 逐条 eval + 三段证据链", "allowed_next": ["COMMIT", "SANTA_LOOP", "PAUSED_ESCALATED", "ABORTED"]},
        {"name": "SANTA_LOOP", "phase": "验证", "description": "C 路线；verifier FAIL 回 IMPL 最多 3 轮", "allowed_next": ["IMPL", "ABORTED"]},
        {"name": "PAUSED_ESCALATED", "phase": "阻塞", "description": "非红线阻塞；等用户补充信息/凭证/确认", "allowed_next": ["IMPL", "VERIFY", "ABORTED"]},
        {"name": "COMMIT", "phase": "收尾", "description": "git commit + optional push + PR", "allowed_next": ["RETRO_CLOSE"]},
        {"name": "RETRO_CLOSE", "phase": "收尾", "description": "retro-generator 11 项复盘 + archive 归档", "allowed_next": ["CLOSED"]},
        {"name": "CLOSED", "phase": "终态", "description": "终态；final_outcome=success; delivery_bundle 完整", "allowed_next": []},
        {"name": "ABORTED", "phase": "终态", "description": "终态；红线触发或用户取消；failure-archive 归档", "allowed_next": []},
        {"name": "DRIFT_DETECTED", "phase": "监督", "description": "supervisor 侧挂态；goal_anchor 漂移触发", "allowed_next": ["CLARIFY", "ABORTED"]},
        {"name": "DOD_GAP", "phase": "监督", "description": "supervisor 侧挂态；Verifier 证据链缺失触发", "allowed_next": ["VERIFY", "IMPL"]},
        {"name": "IRREVERSIBLE_HALT", "phase": "监督", "description": "supervisor 侧挂态；detect 到 rm -rf / force push / DB drop 未经授权", "allowed_next": ["USER_AUTHORIZE", "ABORTED"]},
    ]

    # 42 cell routing matrix: 6 routes × 7 主阶段
    matrix_columns = ["启动阶段", "规划阶段", "执行阶段", "验证阶段", "阻塞处理", "收尾阶段", "终态"]
    matrix_rows = [
        {"route": "A", "cells": ["INIT→CLARIFY", "ROUTE_SELECT", "IMPL", "VERIFY", "PAUSED_ESCALATED", "COMMIT→RETRO_CLOSE", "CLOSED"]},
        {"route": "B", "cells": ["INIT→CLARIFY", "ROUTE_SELECT→PLAN", "IMPL", "VERIFY", "PAUSED_ESCALATED", "COMMIT→RETRO_CLOSE", "CLOSED"]},
        {"route": "C", "cells": ["INIT→CLARIFY", "ROUTE_SELECT→PLAN", "IMPL", "VERIFY→SANTA_LOOP", "PAUSED_ESCALATED", "COMMIT→RETRO_CLOSE", "CLOSED"]},
        {"route": "D", "cells": ["INIT→CLARIFY", "ROUTE_SELECT→PLAN", "IMPL→UI_SCREENSHOT", "VERIFY", "PAUSED_ESCALATED", "COMMIT→RETRO_CLOSE", "CLOSED"]},
        {"route": "E", "cells": ["INIT→CLARIFY", "ROUTE_SELECT→PLAN→RISK_REVIEW→USER_AUTHORIZE", "IMPL", "VERIFY", "PAUSED_ESCALATED / IRREVERSIBLE_HALT", "COMMIT→RETRO_CLOSE", "CLOSED / ABORTED"]},
        {"route": "F", "cells": ["INIT→CLARIFY", "ROUTE_SELECT", "RESEARCH→DOC_WRITE", "—", "—", "COMMIT", "CLOSED"]},
    ]

    red_lines = [
        {
            "id": "DRIFT_CRITICAL",
            "name": "目标漂移（Goal Drift）",
            "description": "goal_anchor.hash 与当前 IMPL 产出物 sha256 不一致，或 CLAUDE.md / 任务描述被隐式篡改。",
            "threshold": "hash 任意字段变化 || 关键句命中率 < 60%",
            "severity": "BLOCK",
            "default_action": "转 DRIFT_DETECTED；回 CLARIFY 要求用户重新锁定 goal_anchor。",
            "trigger_count_recent": 1,
        },
        {
            "id": "DOD_GAP_ALERT",
            "name": "DoD 证据缺失",
            "description": "verifier_report 三段证据链（existence / behavior / quality）缺任一段，或 overall!=PASS 被越权判 COMMIT。",
            "threshold": "三段证据链任一缺失 || insufficient_evidence_count > 0",
            "severity": "WARN",
            "default_action": "阻断 COMMIT；回 VERIFY 重跑。",
            "trigger_count_recent": 0,
        },
        {
            "id": "IRREVERSIBLE_HALT",
            "name": "不可逆操作拦截",
            "description": "detect rm -rf / force-push / DB drop / production deploy 未经 USER_AUTHORIZE 状态授权。",
            "threshold": "Bash 命中危险 regex || state != USER_AUTHORIZE",
            "severity": "BLOCK",
            "default_action": "硬拦截执行；转 IRREVERSIBLE_HALT；要求用户显式文本授权。",
            "trigger_count_recent": 0,
        },
    ]

    retry_ladder = [
        {"level": "L0", "name": "自愈重试", "trigger": "单一原语瞬时失败（网络/超时）", "action": "同参数重试 ≤ 3 次；无用户感知。", "max_attempts": 3},
        {"level": "L1", "name": "单次纠偏", "trigger": "verifier 某单项 FAIL 且可定位", "action": "回 IMPL 修 1 次 → 重跑 VERIFY；失败升 L2。", "max_attempts": 1},
        {"level": "L2", "name": "SANTA_LOOP 兜底", "trigger": "L1 失败或 C 路线多点 FAIL", "action": "santa-loop skill 介入，最多 3 轮 replan + reimpl + reverify。", "max_attempts": 3},
        {"level": "L3", "name": "用户升级", "trigger": "L2 仍失败 / 红线触发 / 信息不足", "action": "转 PAUSED_ESCALATED 或 ABORTED；提交用户决策。", "max_attempts": 0},
    ]

    stage_contracts = [
        {"state": "CLARIFY", "dod_template": "(goal_anchor.text 长度 ≥ 50 字) AND (goal_anchor.hash 已生成) AND (initial_user_input 完整记录)", "required_artifacts": ["task-boards/*.json"]},
        {"state": "PLAN", "dod_template": "(plan.md exists) AND (dod_expression 非空) AND (artifacts_expected ≥ 1) AND (risk 已评估)", "required_artifacts": ["plans/*.md", "task-boards/*.json"]},
        {"state": "IMPL", "dod_template": "(artifacts_expected 全部产出) AND (pytest pass OR UI_SCREENSHOT exists)", "required_artifacts": ["对应代码/文档文件"]},
        {"state": "VERIFY", "dod_template": "(verifier_report.overall = PASS) AND (三段证据链全部存在) AND (red_lines_detected = [])", "required_artifacts": ["verifier_reports/*.json"]},
        {"state": "COMMIT", "dod_template": "(git_commit_sha 非空) AND (pre-commit hook pass)", "required_artifacts": ["git log entry"]},
        {"state": "RETRO_CLOSE", "dod_template": "(retro.md exists) AND (11 项复盘齐全) AND (failure-archive.jsonl updated)", "required_artifacts": ["retros/*.md", "failure-archive.jsonl"]},
    ]

    supervisor_trigger_policy = {
        "modes": [
            {"mode": "SessionStart hook", "description": "会话启动时自动拉起 supervisor subagent，读 task-board 建立监控上下文。", "enabled": True},
            {"mode": "PostToolUse hook", "description": "每次 Edit/Write/Bash 后触发 pulse，检查 goal_anchor / red_line。", "enabled": True},
            {"mode": "周期 tick", "description": "每 30s 轮询 task-board.json + routing_events，检测 stuck / drift。", "enabled": True, "interval_sec": 30},
            {"mode": "State transition hook", "description": "任一 state 转换时触发，校验 allowed_next 合法性。", "enabled": True},
        ],
        "debounce_sec": 3,
    }

    return {
        "routes": routes,
        "states": states,
        "routing_matrix": {"columns": matrix_columns, "rows": matrix_rows, "cell_count": 42},
        "red_lines": red_lines,
        "retry_ladder": retry_ladder,
        "stage_contracts_templates": stage_contracts,
        "supervisor_trigger_policy": supervisor_trigger_policy,
    }


def _admin_engine_instances() -> dict:
    """执行实例：task-boards 运行视图，按 state / outcome 分组。"""
    boards = list_all_task_boards()
    active_states = {"INIT", "CLARIFY", "ROUTE_SELECT", "PLAN", "IMPL", "VERIFY", "COMMIT", "UI_SCREENSHOT", "RESEARCH", "DOC_WRITE"}
    buckets = {"active": [], "paused": [], "closed_success": [], "closed_fail": [], "aborted": []}
    recent_transitions = []

    for b in boards:
        light = {
            "task_id": b.get("task_id"),
            "project": b.get("project", ""),
            "goal_text": (b.get("_derived") or {}).get("summary") or (b.get("goal_anchor") or {}).get("text", "")[:80],
            "state": b.get("current_state"),
            "route": b.get("route_id") or b.get("route"),
            "size": b.get("size"),
            "progress": b.get("progress_percentage"),
            "created_at": b.get("created_at"),
            "closed_at": b.get("closed_at"),
            "final_outcome": b.get("final_outcome"),
        }
        s = b.get("current_state")
        if s == "CLOSED":
            if b.get("final_outcome") == "success":
                buckets["closed_success"].append(light)
            else:
                buckets["closed_fail"].append(light)
        elif s == "ABORTED":
            buckets["aborted"].append(light)
        elif s == "PAUSED_ESCALATED":
            buckets["paused"].append(light)
        elif s in active_states:
            buckets["active"].append(light)

        for h in (b.get("state_history") or [])[-2:]:
            if h.get("timestamp") and h.get("state"):
                recent_transitions.append({
                    "task_id": b.get("task_id"),
                    "from_state": h.get("from_state"),
                    "to_state": h.get("state"),
                    "timestamp": h.get("timestamp"),
                    "trigger": (h.get("trigger") or "")[:80],
                })

    recent_transitions.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    recent_transitions = recent_transitions[:15]

    return {
        "total": len(boards),
        "counts": {k: len(v) for k, v in buckets.items()},
        "buckets": buckets,
        "recent_transitions": recent_transitions,
    }


def _admin_knowledge_base() -> dict:
    """3 层知识库 + 注入策略。"""
    entries = mock_knowledge_base()
    global_ct = len([e for e in entries if e.get("scope") == "global"])
    project_ct = len([e for e in entries if e.get("scope") == "project"])
    session_ct = len([e for e in entries if e.get("scope") == "session"])

    layers = [
        {
            "level": "global",
            "label": "🌐 全局知识库",
            "path": "~/.harnessflow/global-kb/",
            "entry_count": global_ct,
            "description": "跨项目通用模式 / 陷阱 / 工具组合；所有任务启动时自动注入。",
            "persist_scope": "跨 session、跨 repo 永久",
        },
        {
            "level": "project",
            "label": "📁 项目知识库",
            "path": "<repo>/harnessFlow/project-kb/",
            "entry_count": project_ct,
            "description": "单项目/单仓库专属；如 aigc 的 P20 假完成陷阱。",
            "persist_scope": "跨 session、绑定 repo",
        },
        {
            "level": "session",
            "label": "💾 会话知识库",
            "path": "/tmp/harnessflow-session-<task_id>-kb/",
            "entry_count": session_ct,
            "description": "当前 session 内临时发现；closed 后 promote 到 project 或 global。",
            "persist_scope": "仅当前 session",
        },
    ]

    injection_policy = [
        {"stage": "INIT", "inject_kinds": ["project_context", "tool_combo"], "strategy": "全量注入，读 project-kb + global-kb 高频条目"},
        {"stage": "CLARIFY", "inject_kinds": ["trap", "pattern"], "strategy": "按 task_type 匹配注入；避免用户说「这里有坑」时答非所问"},
        {"stage": "PLAN", "inject_kinds": ["recipe", "tool_combo"], "strategy": "按 route 绑定注入对应 skill chain 的有效组合"},
        {"stage": "IMPL", "inject_kinds": ["pattern", "anti_pattern"], "strategy": "按改动文件路径匹配注入；防重复踩坑"},
        {"stage": "VERIFY", "inject_kinds": ["trap"], "strategy": "verifier 读假完成陷阱列表逐条 check"},
        {"stage": "RETRO_CLOSE", "inject_kinds": [], "strategy": "不注入；反而是 retro 产出新 KB 写入 session/project 层"},
    ]

    return {
        "layers": layers,
        "entries": entries,
        "total_entries": len(entries),
        "injection_policy": injection_policy,
        "kind_distribution": {
            "trap": len([e for e in entries if e.get("kind") == "trap"]),
            "pattern": len([e for e in entries if e.get("kind") == "pattern"]),
            "recipe": len([e for e in entries if e.get("kind") == "recipe"]),
            "tool_combo": len([e for e in entries if e.get("kind") == "tool_combo"]),
            "anti_pattern": len([e for e in entries if e.get("kind") == "anti_pattern"]),
            "project_context": len([e for e in entries if e.get("kind") == "project_context"]),
        },
    }


def _admin_supervisor_agent() -> dict:
    """Harness 监督智能体：运行状态 + 8 维度配置 + 事件流。"""
    dimensions = [
        {"key": "goal_fidelity", "label": "目标保真度", "metrics": ["goal_hash_drift", "claude_md_mutation"], "threshold": "任一漂移触发 DRIFT_CRITICAL", "window": "全程", "action": "BLOCK → CLARIFY"},
        {"key": "plan_alignment", "label": "计划对齐", "metrics": ["skeleton_deviation_pct"], "threshold": "实际 state 序列 vs 路线骨架偏差 > 30%", "window": "全程", "action": "WARN"},
        {"key": "true_completion", "label": "真完成质量", "metrics": ["verifier_pass_rate", "evidence_chain_completeness", "dod_eval"], "threshold": "verifier_report.overall != PASS", "window": "@VERIFY", "action": "BLOCK → VERIFY"},
        {"key": "red_lines_safety", "label": "红线与安全", "metrics": ["red_lines_detected", "scope_drift_count"], "threshold": "任一红线命中", "window": "全程", "action": "BLOCK"},
        {"key": "progress_pace", "label": "进度与节奏", "metrics": ["elapsed_vs_estimate_ratio", "tool_call_density", "idle_ratio"], "threshold": "elapsed > 2×estimate || idle > 30min", "window": "30s tick", "action": "INFO/WARN"},
        {"key": "cost_budget", "label": "成本与预算", "metrics": ["tokens_total", "context_window_pct", "dollar_spent"], "threshold": "context > 80% || tokens > 500K", "window": "每工具调用", "action": "INFO"},
        {"key": "retry_loop", "label": "重试与 Loop", "metrics": ["retry_count", "santa_loop_iterations", "replan_count"], "threshold": "santa-loop > 3 || replan > 2", "window": "全程", "action": "WARN → L3"},
        {"key": "user_collaboration", "label": "用户协作", "metrics": ["user_interrupt_count", "clarification_rounds", "废问题_count"], "threshold": "废问题 > 0 即告警", "window": "全程", "action": "INFO"},
    ]

    red_line_events = [
        {"ts": "2026-04-18T10:45:22Z", "task_id": "p-harness-v2-ui-mock", "dimension": "red_lines_safety", "severity": "INFO", "message": "P20 scope drift 预警：检测到 aigcv2 任务出现在 harnessFlow TODO 列表（用户捕获）", "action_taken": "用户介入修正"},
        {"ts": "2026-04-18T11:45:00Z", "task_id": "p-harness-v2-ui-mock", "dimension": "user_collaboration", "severity": "INFO", "message": "用户截图反馈 Vue 未渲染 — 触发 L1 纠偏", "action_taken": "回 IMPL 修 vue.global.js"},
        {"ts": "2026-04-18T11:55:00Z", "task_id": "p-harness-v2-ui-mock", "dimension": "retry_loop", "severity": "INFO", "message": "L1 首次修复误诊 (prod→dev)，真凶是 Chrome ORB → 再次 L1", "action_taken": "playwright python 独立 launch 定位 hljs 错误"},
        {"ts": "2026-04-17T15:12:33Z", "task_id": "p-harness-v1.2-stage-contracts", "dimension": "progress_pace", "severity": "INFO", "message": "pytest 31 cases 全 PASS，耗时 1.24s — 节奏正常", "action_taken": "无需干预"},
        {"ts": "2026-04-17T14:30:12Z", "task_id": "p-harness-v1.1-skill-delegation", "dimension": "true_completion", "severity": "INFO", "message": "VERIFY 三段证据链完整 + overall=PASS", "action_taken": "准入 COMMIT"},
    ]

    notification_channels = [
        {"id": "session_inline", "label": "会话内联提示", "description": "supervisor 直接在对话中发 INFO/WARN/BLOCK 消息", "status": "enabled", "default": True},
        {"id": "hook_post_tool", "label": "PostToolUse hook 注入", "description": "通过 hook 把告警塞进下一轮上下文", "status": "enabled"},
        {"id": "task_board_write", "label": "task-board 事件写入", "description": "写 supervisor_events[] 数组持久化", "status": "enabled"},
        {"id": "external_webhook", "label": "外部 webhook", "description": "推送到 Slack / 飞书 / 企业微信", "status": "disabled", "note": "v3 规划"},
    ]

    return {
        "status": {
            "online": True,
            "agent_id": "harnessFlow:supervisor",
            "pid_hint": "每 session 内自动拉起，随 session 终止",
            "last_heartbeat": "2026-04-19T00:30:15Z",
            "tick_interval_sec": 30,
            "trigger_count_today": 142,
        },
        "dimensions_config": dimensions,
        "red_line_events_recent": red_line_events,
        "notification_channels": notification_channels,
    }


def _admin_primitives_registry() -> dict:
    """Verifier 原语库：DoD 可用的所有 primitive。"""
    primitives = [
        {"name": "fs.file_exists", "category": "文件系统", "signature": "path: str → bool", "description": "校验文件路径是否存在（绝对路径，不走 glob）", "used_in_dod": 28, "tests_pass": "5/5"},
        {"name": "fs.dir_exists", "category": "文件系统", "signature": "path: str → bool", "description": "校验目录存在", "used_in_dod": 8, "tests_pass": "3/3"},
        {"name": "fs.grep_count", "category": "文件系统", "signature": "file, pattern → int", "description": "ripgrep 统计某文件内匹配次数", "used_in_dod": 11, "tests_pass": "4/4"},
        {"name": "fs.line_count_range", "category": "文件系统", "signature": "file, min, max → bool", "description": "文件行数是否在 [min,max] 区间", "used_in_dod": 4, "tests_pass": "2/2"},
        {"name": "git.commit_pushed", "category": "Git", "signature": "sha → bool", "description": "某 commit 是否已 push 到 origin", "used_in_dod": 12, "tests_pass": "3/3"},
        {"name": "git.diff_stats", "category": "Git", "signature": "base, head → (files, +, -)", "description": "两 ref 间 diff 统计", "used_in_dod": 3, "tests_pass": "2/2"},
        {"name": "git.clean_working_tree", "category": "Git", "signature": "→ bool", "description": "working tree 无 uncommitted 改动", "used_in_dod": 6, "tests_pass": "2/2"},
        {"name": "pytest.all_pass", "category": "测试", "signature": "path? → bool", "description": "pytest 全部 case PASS", "used_in_dod": 18, "tests_pass": "4/4"},
        {"name": "pytest.coverage_pct", "category": "测试", "signature": "min_pct → bool", "description": "pytest-cov 覆盖率 ≥ min_pct", "used_in_dod": 2, "tests_pass": "1/1"},
        {"name": "curl.status_2xx", "category": "网络", "signature": "url → bool", "description": "HTTP GET 返回 2xx", "used_in_dod": 9, "tests_pass": "2/2"},
        {"name": "curl.json_path_eq", "category": "网络", "signature": "url, jsonpath, expected → bool", "description": "curl+jq 路径值等于 expected", "used_in_dod": 5, "tests_pass": "2/2"},
        {"name": "playwright.screenshot_has_content", "category": "UI", "signature": "url → bool", "description": "截屏后用 evaluate 校验 body.innerText 非 template 源码", "used_in_dod": 3, "tests_pass": "1/1"},
        {"name": "playwright.click_path", "category": "UI", "signature": "url, selectors[] → bool", "description": "按序列点击所有 selector 无 error", "used_in_dod": 2, "tests_pass": "1/1"},
        {"name": "python.import_module", "category": "Python", "signature": "module → bool", "description": "import 某 module 不报错", "used_in_dod": 6, "tests_pass": "2/2"},
        {"name": "npm.build_ok", "category": "Node", "signature": "→ bool", "description": "npm run build 退出码 0", "used_in_dod": 2, "tests_pass": "1/1"},
        {"name": "shell.exec_0", "category": "Shell", "signature": "cmd → bool", "description": "任意 shell cmd 返回 0", "used_in_dod": 15, "tests_pass": "3/3"},
        {"name": "bool.and", "category": "逻辑", "signature": "[...bool] → bool", "description": "AST 组合：所有子谓词 AND", "used_in_dod": 62, "tests_pass": "5/5"},
        {"name": "bool.or", "category": "逻辑", "signature": "[...bool] → bool", "description": "AST 组合：至少一个子谓词 TRUE", "used_in_dod": 8, "tests_pass": "3/3"},
        {"name": "bool.not", "category": "逻辑", "signature": "bool → bool", "description": "AST 组合：取反", "used_in_dod": 3, "tests_pass": "2/2"},
    ]
    return {
        "count": len(primitives),
        "by_category": {},
        "primitives": primitives,
        "total_tests": sum(int(p["tests_pass"].split("/")[0]) for p in primitives),
        "coverage_note": "所有原语走白名单 AST eval，禁 arbitrary exec；详见 v1.2 Stage Contract 实现。",
    }


def _admin_subagents_registry() -> dict:
    """harnessFlow: 命名空间下 4 个 subagents。"""
    subagents = [
        {
            "name": "harnessFlow:supervisor",
            "role": "全程只读监督",
            "trigger": "SessionStart + PostToolUse + 30s tick + state_transition",
            "tools": ["Read", "Grep", "Glob", "Bash"],
            "read_only": True,
            "invoke_count_today": 142,
            "avg_latency_ms": 380,
            "description": "识别 drift / stuck / token-budget，按 3 红线发 INFO/WARN/BLOCK，推进到终态即自退出。",
        },
        {
            "name": "harnessFlow:verifier",
            "role": "独立收口验证",
            "trigger": "@VERIFY state entry",
            "tools": ["Read", "Grep", "Glob", "Bash"],
            "read_only": True,
            "invoke_count_today": 12,
            "avg_latency_ms": 2100,
            "description": "读 dod_expression 逐条调 verifier_primitives 原语 eval，产出三态 verdict (PASS/FAIL/INSUFFICIENT_EVIDENCE) + 三段证据链。",
        },
        {
            "name": "harnessFlow:failure-archive-writer",
            "role": "结构化失败归档",
            "trigger": "@ABORTED || @RETRO_CLOSE state entry",
            "tools": ["Read", "Glob", "Bash", "Write"],
            "read_only": False,
            "invoke_count_today": 6,
            "avg_latency_ms": 450,
            "description": "调 archive.writer.write_archive_entry 写 JSON-Schema 校验过的 failure-archive.jsonl；满足 need_audit 时触发 audit。",
        },
        {
            "name": "harnessFlow:retro-generator",
            "role": "11 项 retro 自动生成",
            "trigger": "@RETRO_CLOSE state entry",
            "tools": ["Read", "Glob", "Bash", "Write"],
            "read_only": False,
            "invoke_count_today": 5,
            "avg_latency_ms": 820,
            "description": "调 archive.retro_renderer.render_retro 按模板渲染 11 项 markdown 到 retros/<task_id>.md。",
        },
    ]
    return {"count": len(subagents), "subagents": subagents}


def _admin_skills_registry() -> dict:
    """可被 harnessFlow 调用的 skill 注册表 + 路线绑定。"""
    skills = [
        {"name": "superpowers:brainstorming", "category": "process", "invoke_at": ["@CLARIFY"], "required": True, "used_count": 8},
        {"name": "superpowers:writing-plans", "category": "process", "invoke_at": ["@PLAN"], "required": True, "used_count": 6},
        {"name": "superpowers:test-driven-development", "category": "process", "invoke_at": ["@IMPL"], "required": True, "used_count": 5},
        {"name": "superpowers:executing-plans", "category": "process", "invoke_at": ["@IMPL"], "required": False, "used_count": 3},
        {"name": "superpowers:verification-before-completion", "category": "process", "invoke_at": ["@VERIFY"], "required": True, "used_count": 6},
        {"name": "superpowers:debugging", "category": "process", "invoke_at": ["纠偏"], "required": False, "used_count": 4},
        {"name": "prp-prd", "category": "PRP", "invoke_at": ["@CLARIFY (C 路线)"], "required": False, "used_count": 1},
        {"name": "prp-plan", "category": "PRP", "invoke_at": ["@PLAN (C 路线)"], "required": False, "used_count": 1},
        {"name": "prp-implement", "category": "PRP", "invoke_at": ["@IMPL (C 路线)"], "required": False, "used_count": 1},
        {"name": "santa-loop", "category": "PRP", "invoke_at": ["@SANTA_LOOP"], "required": True, "used_count": 2},
        {"name": "prp-commit", "category": "PRP", "invoke_at": ["@COMMIT"], "required": False, "used_count": 1},
        {"name": "prp-pr", "category": "PRP", "invoke_at": ["@COMMIT"], "required": False, "used_count": 0},
        {"name": "gan-design", "category": "UI", "invoke_at": ["@PLAN (D 路线)"], "required": False, "used_count": 1},
        {"name": "design-review", "category": "UI", "invoke_at": ["@VERIFY (D 路线)"], "required": False, "used_count": 1},
        {"name": "context7 / docs-lookup", "category": "检索", "invoke_at": ["@RESEARCH / 全程"], "required": False, "used_count": 3},
        {"name": "exa.web_search_exa", "category": "检索", "invoke_at": ["@RESEARCH"], "required": False, "used_count": 2},
    ]
    route_bindings = {
        "A": ["superpowers:brainstorming", "superpowers:test-driven-development", "superpowers:verification-before-completion"],
        "B": ["superpowers:brainstorming", "superpowers:writing-plans", "superpowers:test-driven-development", "superpowers:executing-plans", "superpowers:verification-before-completion"],
        "C": ["prp-prd", "prp-plan", "prp-implement", "santa-loop", "prp-commit", "prp-pr"],
        "D": ["superpowers:brainstorming", "gan-design", "design-review", "superpowers:verification-before-completion"],
        "E": ["superpowers:brainstorming", "superpowers:writing-plans", "security-reviewer", "superpowers:verification-before-completion"],
        "F": ["context7 / docs-lookup", "exa.web_search_exa", "WebFetch"],
    }
    return {"count": len(skills), "skills": skills, "route_bindings": route_bindings}


def _admin_analytics() -> dict:
    """统计分析：按路线/size 成功率、耗时、红线触发率、纠偏分布。"""
    return {
        "total_tasks": 12,
        "success_rate_overall_pct": 66.7,
        "by_route_success_rate": [
            {"route": "A", "total": 2, "success": 2, "pct": 100.0},
            {"route": "B", "total": 3, "success": 2, "pct": 66.7},
            {"route": "C", "total": 4, "success": 2, "pct": 50.0},
            {"route": "D", "total": 2, "success": 2, "pct": 100.0},
            {"route": "E", "total": 0, "success": 0, "pct": None},
            {"route": "F", "total": 1, "success": 1, "pct": 100.0},
        ],
        "avg_duration_by_size_min": [
            {"size": "S", "avg_min": 18, "sample": 3},
            {"size": "M", "avg_min": 96, "sample": 5},
            {"size": "L", "avg_min": 620, "sample": 4},
        ],
        "red_line_trigger_rate_pct": 8.3,
        "red_line_breakdown": [
            {"red_line": "DRIFT_CRITICAL", "trigger_count": 1, "task_count": 1},
            {"red_line": "DOD_GAP_ALERT", "trigger_count": 0, "task_count": 0},
            {"red_line": "IRREVERSIBLE_HALT", "trigger_count": 0, "task_count": 0},
        ],
        "correction_distribution": {"L0": 12, "L1": 5, "L2": 1, "L3": 0},
        "activity_last_14d": [0, 0, 1, 2, 1, 3, 1, 0, 2, 4, 3, 2, 5, 3],
        "kb_hit_rate_pct": 45.5,
        "avg_retro_lines": 82,
        "most_used_skills_top5": [
            {"skill": "superpowers:brainstorming", "count": 8},
            {"skill": "superpowers:writing-plans", "count": 6},
            {"skill": "superpowers:verification-before-completion", "count": 6},
            {"skill": "superpowers:test-driven-development", "count": 5},
            {"skill": "superpowers:debugging", "count": 4},
        ],
    }


def _admin_diagnostics() -> dict:
    """系统诊断：一致性校验 + 依赖可用性 + MCP 状态。"""
    return {
        "consistency_checks": [
            {"name": "所有 CLOSED 任务都有 retro 文件", "status": "pass", "observed": "7/7", "primitive": "fs.file_exists + glob"},
            {"name": "所有 ABORTED 任务都有 archive entry", "status": "pass", "observed": "1/1", "primitive": "jsonl.scan"},
            {"name": "task-board JSON Schema 合法", "status": "pass", "observed": "12/12", "primitive": "jsonschema.validate"},
            {"name": "goal_anchor sha256 未漂移", "status": "pass", "observed": "12/12", "primitive": "hash.verify"},
            {"name": "retro 11 项齐全", "status": "warn", "observed": "5/7（2 份 legacy 简化版）", "primitive": "md.heading_count"},
            {"name": "state_history 每项有 state + timestamp", "status": "pass", "observed": "12/12", "primitive": "json.schema"},
            {"name": "dod_expression 可被 predicate_eval 解析", "status": "pass", "observed": "12/12", "primitive": "ast.parse"},
        ],
        "dependencies": [
            {"name": "claude-code CLI", "required": True, "status": "ok", "version": "Opus 4.7 (1M)"},
            {"name": "git", "required": True, "status": "ok", "version": "≥ 2.40"},
            {"name": "python", "required": True, "status": "ok", "version": "3.11+"},
            {"name": "FastAPI + uvicorn", "required": True, "status": "ok", "version": "复用 aigc 环境"},
            {"name": "GitHub PAT", "required": False, "status": "warn", "note": "classic token 置于 shell env；未落地 .netrc"},
            {"name": "pytest", "required": True, "status": "ok"},
            {"name": "jsonschema", "required": True, "status": "ok"},
        ],
        "mcp_servers": [
            {"name": "playwright", "status": "online", "note": "单 profile 锁；并发需 playwright-python 直 launch"},
            {"name": "context7", "status": "online", "note": "文档检索"},
            {"name": "github", "status": "online", "note": "repo / PR / issue 操作"},
            {"name": "exa", "status": "online", "note": "web 搜索"},
            {"name": "memory", "status": "online", "note": "entity graph"},
            {"name": "sequential-thinking", "status": "online"},
        ],
        "skills_available": [
            {"name": "superpowers:*", "status": "ok", "count": 30},
            {"name": "prp:*", "status": "ok", "count": 6},
            {"name": "gstack:*", "status": "ok", "count": 5},
            {"name": "harnessFlow:*", "status": "ok", "count": 5},
        ],
        "last_check_at": "2026-04-19T00:30:15Z",
    }


def mock_admin_data() -> dict:
    """后台管理页总入口：返回 8 大模块所有数据。"""
    return {
        "engine_config": _admin_engine_config(),
        "engine_instances": _admin_engine_instances(),
        "knowledge_base": _admin_knowledge_base(),
        "supervisor_agent": _admin_supervisor_agent(),
        "primitives_registry": _admin_primitives_registry(),
        "subagents_registry": _admin_subagents_registry(),
        "skills_registry": _admin_skills_registry(),
        "analytics": _admin_analytics(),
        "diagnostics": _admin_diagnostics(),
    }
