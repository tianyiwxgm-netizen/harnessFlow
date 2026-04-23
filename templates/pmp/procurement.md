---
kind: pmp.procurement
version: v1.0
slot_schema:
  type: object
  required: [items]
  properties:
    items:
      type: array
      items:
        type: object
        required: [name, vendor]
        properties:
          name: {type: string}
          vendor: {type: string}
description: PMP 9 计划 · 采购管理
author: main-session
created_at: 2026-04-23
---

# PMP 采购管理计划

## 采购项

{% for i in items -%}
- **{{ i.name }}** ← {{ i.vendor }}
{% endfor %}
