---
kind: pmp.resource
version: v1.0
slot_schema:
  type: object
  required: [roles, availability]
  properties:
    roles:
      type: array
      items:
        type: object
        required: [name, count]
        properties:
          name: {type: string}
          count: {type: integer}
    availability:
      type: array
      items: {type: string}
description: PMP 9 计划 · 资源管理
author: main-session
created_at: 2026-04-23
---

# PMP 资源管理计划

## 角色

{% for r in roles -%}
- **{{ r.name }}** × {{ r.count }}
{% endfor %}

## 可用性

{% for a in availability -%}
- {{ a }}
{% endfor %}
