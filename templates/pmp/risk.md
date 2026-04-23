---
kind: pmp.risk
version: v1.0
slot_schema:
  type: object
  required: [risks]
  properties:
    risks:
      type: array
      items:
        type: object
        required: [title, severity, mitigation]
        properties:
          title: {type: string}
          severity: {type: string, enum: [LOW, MEDIUM, HIGH, CRITICAL]}
          mitigation: {type: string}
description: PMP 9 计划 · 风险管理
author: main-session
created_at: 2026-04-23
---

# PMP 风险管理计划

## 风险（{{ risks | length }} 项）

{% for r in risks %}
### {{ loop.index }}. {{ r.title }}

- **严重度**：{{ r.severity }}
- **缓解**：{{ r.mitigation }}
{% endfor %}
