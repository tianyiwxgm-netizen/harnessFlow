---
kind: fourset.prd
version: v1.0
slot_schema:
  type: object
  required: [problem_statement, success_metrics, user_stories]
  properties:
    problem_statement:
      type: string
    success_metrics:
      type: array
      items:
        type: object
        required: [name, target]
        properties:
          name: {type: string}
          target: {type: string}
    user_stories:
      type: array
      items: {type: string}
description: S2 4 件套 · PRD 文档模板
author: main-session
created_at: 2026-04-23
---

# PRD 文档

## 问题陈述

{{ problem_statement | trim }}

## 成功指标（{{ success_metrics | length }} 项）

{% for m in success_metrics -%}
- **{{ m.name }}** · target = `{{ m.target }}`
{% endfor %}

## 用户故事（{{ user_stories | length }} 项）

{% for s in user_stories -%}
- {{ s }}
{% endfor %}
