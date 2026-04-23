---
kind: fourset.tdd
version: v1.0
slot_schema:
  type: object
  required: [layers, quality_gates]
  properties:
    layers:
      type: array
      items:
        type: object
        required: [name, test_count_target]
        properties:
          name: {type: string}
          test_count_target: {type: integer}
    quality_gates:
      type: array
      items: {type: string}
description: S2 4 件套 · TDD 文档模板
author: main-session
created_at: 2026-04-23
---

# TDD 文档

## 测试分层（{{ layers | length }} 层）

{% for l in layers -%}
- **{{ l.name }}** · test_count_target = `{{ l.test_count_target }}`
{% endfor %}

## 质量门

{% for g in quality_gates -%}
- {{ g }}
{% endfor %}
