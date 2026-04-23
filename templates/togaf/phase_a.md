---
kind: togaf.phase_a
version: v1.0
slot_schema:
  type: object
  required: [vision, goals]
  properties:
    vision:
      type: string
    goals:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase A (Architecture Vision)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase A · Architecture Vision

## 架构愿景

{{ vision | trim }}

## 目标

{% for g in goals -%}
- {{ g }}
{% endfor %}
