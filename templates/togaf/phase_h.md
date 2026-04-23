---
kind: togaf.phase_h
version: v1.0
slot_schema:
  type: object
  required: [change_requests]
  properties:
    change_requests:
      type: array
      items:
        type: object
        required: [title, status]
        properties:
          title: {type: string}
          status: {type: string, enum: [OPEN, APPROVED, REJECTED]}
description: TOGAF ADM · Phase H (Architecture Change Management)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase H · Architecture Change Management

## 变更请求（{{ change_requests | length }} 项）

{% for c in change_requests -%}
- **{{ c.title }}** · `{{ c.status }}`
{% endfor %}
