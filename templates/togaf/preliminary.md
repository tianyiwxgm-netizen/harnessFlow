---
kind: togaf.preliminary
version: v1.0
slot_schema:
  type: object
  required: [principles, stakeholders]
  properties:
    principles:
      type: array
      items: {type: string}
    stakeholders:
      type: array
      items:
        type: object
        required: [name, role]
        properties:
          name: {type: string}
          role: {type: string}
description: TOGAF ADM · Preliminary Phase
author: main-session
created_at: 2026-04-23
---

# TOGAF Preliminary Phase

## 架构原则

{% for p in principles -%}
- {{ p }}
{% endfor %}

## 干系人

{% for s in stakeholders -%}
- **{{ s.name }}** · {{ s.role }}
{% endfor %}
