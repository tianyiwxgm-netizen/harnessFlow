---
kind: togaf.phase_d
version: v1.0
slot_schema:
  type: object
  required: [tech_components, standards]
  properties:
    tech_components:
      type: array
      items: {type: string}
    standards:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase D (Technology Architecture)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase D · Technology Architecture

## 技术组件

{% for c in tech_components -%}
- {{ c }}
{% endfor %}

## 技术标准

{% for s in standards -%}
- {{ s }}
{% endfor %}
