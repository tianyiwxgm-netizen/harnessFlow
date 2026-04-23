---
kind: togaf.phase_c_application
version: v1.0
slot_schema:
  type: object
  required: [applications, interactions]
  properties:
    applications:
      type: array
      items: {type: string}
    interactions:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase C (Application Architecture)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase C · Application Architecture

## 应用清单

{% for a in applications -%}
- {{ a }}
{% endfor %}

## 应用交互

{% for i in interactions -%}
- {{ i }}
{% endfor %}
