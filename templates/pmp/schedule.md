---
kind: pmp.schedule
version: v1.0
slot_schema:
  type: object
  required: [milestones, critical_path]
  properties:
    milestones:
      type: array
      items:
        type: object
        required: [name, due_date]
        properties:
          name: {type: string}
          due_date: {type: string}
    critical_path:
      type: array
      items: {type: string}
description: PMP 9 计划 · 进度管理
author: main-session
created_at: 2026-04-23
---

# PMP 进度管理计划

## 里程碑（{{ milestones | length }} 项）

{% for m in milestones -%}
- **{{ m.name }}** · `{{ m.due_date }}`
{% endfor %}

## 关键路径

{% for p in critical_path -%}
- {{ p }}
{% endfor %}
