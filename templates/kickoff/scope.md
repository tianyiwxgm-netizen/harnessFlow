---
kind: kickoff.scope
version: v1.0
slot_schema:
  type: object
  required: [scope_items, out_of_scope, constraints]
  properties:
    scope_items:
      type: array
      items: {type: string}
      description: "本项目纳入范围的工作项"
    out_of_scope:
      type: array
      items: {type: string}
      description: "显式排除的范围"
    constraints:
      type: array
      items: {type: string}
      description: "硬约束"
description: S1 启动阶段 HarnessFlowPrdScope.md 模板
author: main-session
created_at: 2026-04-23
---

# HarnessFlowPrdScope

## 范围内（{{ scope_items | length }} 项）

{% for item in scope_items -%}
- {{ item | trim }}
{% endfor %}

## 范围外（{{ out_of_scope | length }} 项）

{% for out in out_of_scope -%}
- {{ out | trim }}
{% endfor %}

## 约束（{{ constraints | length }} 项）

{% for c in constraints -%}
- {{ c | trim }}
{% endfor %}
