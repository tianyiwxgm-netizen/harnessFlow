---
kind: closing.retro_summary
version: v1.0
slot_schema:
  type: object
  required: [summary, metrics]
  properties:
    summary:
      type: string
    metrics:
      type: object
description: S6 Retro 汇总模板
author: main-session
created_at: 2026-04-23
---

# Retro Summary

## 汇总

{{ summary | trim }}

## 指标

{% for k, v in metrics.items() -%}
- **{{ k }}** · `{{ v }}`
{% endfor %}
