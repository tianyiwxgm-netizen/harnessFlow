---
kind: pmp.cost
version: v1.0
slot_schema:
  type: object
  required: [budget_total, cost_breakdown]
  properties:
    budget_total:
      type: number
    cost_breakdown:
      type: array
      items:
        type: object
        required: [category, amount]
        properties:
          category: {type: string}
          amount: {type: number}
description: PMP 9 计划 · 成本管理
author: main-session
created_at: 2026-04-23
---

# PMP 成本管理计划

## 总预算

**{{ budget_total }}**

## 分项成本（{{ cost_breakdown | length }} 项）

{% for c in cost_breakdown -%}
- **{{ c.category }}** · {{ c.amount }}
{% endfor %}
