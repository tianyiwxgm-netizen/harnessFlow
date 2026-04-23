---
kind: pmp.quality
version: v1.0
slot_schema:
  type: object
  required: [quality_objectives, quality_checks]
  properties:
    quality_objectives:
      type: array
      items: {type: string}
    quality_checks:
      type: array
      items: {type: string}
description: PMP 9 计划 · 质量管理
author: main-session
created_at: 2026-04-23
---

# PMP 质量管理计划

## 质量目标

{% for o in quality_objectives -%}
- {{ o }}
{% endfor %}

## 质量检查

{% for c in quality_checks -%}
- {{ c }}
{% endfor %}
