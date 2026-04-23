---
kind: togaf.phase_b
version: v1.0
slot_schema:
  type: object
  required: [business_capabilities, value_streams]
  properties:
    business_capabilities:
      type: array
      items: {type: string}
    value_streams:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase B (Business Architecture)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase B · Business Architecture

## 业务能力

{% for c in business_capabilities -%}
- {{ c }}
{% endfor %}

## 价值流

{% for v in value_streams -%}
- {{ v }}
{% endfor %}
