---
kind: kickoff.goal
version: v1.0
slot_schema:
  type: object
  required: [user_utterance, goals, deadline]
  properties:
    user_utterance:
      type: string
      description: "用户首次输入的项目目标口语描述"
    goals:
      type: array
      items: {type: string}
      minItems: 1
      description: "SMART 目标列表"
    deadline:
      type: string
      description: "ISO-8601 日期或 YYYY-MM-DD"
description: S1 启动阶段 HarnessFlowGoal.md 模板
author: main-session
created_at: 2026-04-23
---

# HarnessFlowGoal

## 用户原始输入

> {{ user_utterance | trim }}

## SMART 目标（共 {{ goals | length }} 项）

{% for g in goals -%}
- **G{{ loop.index }}**：{{ g | trim }}
{% endfor %}

## 期望 Deadline

{{ deadline }}
