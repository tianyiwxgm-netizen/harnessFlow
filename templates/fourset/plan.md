---
kind: fourset.plan
version: v1.0
slot_schema:
  type: object
  required: [milestones, risks]
  properties:
    milestones:
      type: array
      items:
        type: object
        required: [name, due_date]
        properties:
          name: {type: string}
          due_date: {type: string}
    risks:
      type: array
      items:
        type: object
        required: [title, severity]
        properties:
          title: {type: string}
          severity: {type: string, enum: [LOW, MEDIUM, HIGH]}
description: S2 4 件套 · plan 文档模板
author: main-session
created_at: 2026-04-23
---

# Plan 文档

## 里程碑（{{ milestones | length }} 项）

{% for m in milestones -%}
- **{{ m.name }}** · due = `{{ m.due_date }}`
{% endfor %}

## 风险（{{ risks | length }} 项）

{% for r in risks -%}
- **{{ r.title }}** · severity = `{{ r.severity }}`
{% endfor %}
