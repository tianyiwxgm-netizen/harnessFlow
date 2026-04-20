---
description: Launch harnessFlow-ui (任务管理页 + 知识库视图 + 流水线时间轴 + 产出物 MD 浏览器). 默认启动 uvicorn 后端 (port 8765) + 打开浏览器. 零 npm install — Vue3/Element Plus 从 CDN 加载.
allowed-tools: Bash, Read
---

# /harnessFlow-ui

启动 harnessFlow 的任务管理 Web UI.

## 使用

```
/harnessFlow-ui               # 启动并打开浏览器（前台运行）
/harnessFlow-ui daemon        # 后台 daemon 模式
/harnessFlow-ui stop          # 停止 daemon
```

## 做什么

1. 扫全机 harnessFlow 任务（`task-boards/` + `cross-project/` + `legacy/`）
2. 汇聚每个任务的：时间轴、产出物 MD、TDD cases、pytest 结果、Loop 历史、知识库引用、交付 Bundle、Verifier 三段证据
3. 知识库视图：跨任务聚合 anti-patterns / effective-combos / external-refs / traps
4. 项目视图：按领域划分的 project-kb 登记

## 实现

- Backend: FastAPI @ `ui/backend/server.py`（读真 task-boards + mock v2 字段）
- Frontend: 单文件 `ui/frontend/index.html` + Vue3/ElementPlus/marked.js CDN
- 启动: `ui/start.sh`

## Mock 说明（v2-A-UI 阶段）

以下字段 backend mock 合成（真实装等 v2-B/C）:
- `tdd_cases[]` ← verifier_report.evidence_checks 衍生
- `test_results{}` ← verifier_report pytest 检查项
- `delivery_bundle{}` ← retro_link + archive_entry_link 组合
- `knowledge_refs[]` ← task_id 启发式
- `loop_history[]` ← retries[] 映射
- `knowledge-base/` entries ← 6 条硬编码 seed
- `projects[]` ← 2 条硬编码

## 为什么这样设计

- UX-first MVP：看到 UI 再决定 backend 具体形态
- 零 npm install：CDN Vue3 = 5 秒启动
- FastAPI + uvicorn：你 aigc 环境已装
- 只读：UI 不写任何 task-board / kb 文件
