---
kind: pmp.scope
version: v1.0
slot_schema:
  type: object
  required: [scope_statement, scope_items, out_of_scope]
  properties:
    scope_statement:
      type: string
    scope_items:
      type: array
      items:
        type: object
        required: [name, description, owner, duration_days]
        properties:
          name: {type: string}
          description: {type: string}
          owner: {type: string}
          duration_days: {type: integer}
    out_of_scope:
      type: array
      items: {type: string}
description: PMP 9 计划 · 范围管理
author: main-session
created_at: 2026-04-23
---

# PMP 范围管理计划

## 目标

{{ scope_statement | trim }}

## 范围项（共 {{ scope_items | length }} 项）

{% for item in scope_items %}
### {{ loop.index }}. {{ item.name }}

{{ item.description }}

- **负责人**：{{ item.owner }}
- **工期**：{{ item.duration_days }} 天
{% endfor %}

## 不在范围

{% for out in out_of_scope -%}
- {{ out }}
{% endfor %}
