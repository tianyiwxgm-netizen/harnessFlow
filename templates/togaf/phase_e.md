---
kind: togaf.phase_e
version: v1.0
slot_schema:
  type: object
  required: [opportunities, solutions]
  properties:
    opportunities:
      type: array
      items: {type: string}
    solutions:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase E (Opportunities & Solutions)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase E · Opportunities & Solutions

## 机会

{% for o in opportunities -%}
- {{ o }}
{% endfor %}

## 解决方案

{% for s in solutions -%}
- {{ s }}
{% endfor %}
