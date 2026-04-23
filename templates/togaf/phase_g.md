---
kind: togaf.phase_g
version: v1.0
slot_schema:
  type: object
  required: [governance_items]
  properties:
    governance_items:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase G (Implementation Governance)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase G · Implementation Governance

{% for g in governance_items -%}
- {{ g }}
{% endfor %}
