---
kind: pmp.communication
version: v1.0
slot_schema:
  type: object
  required: [channels, cadence]
  properties:
    channels:
      type: array
      items: {type: string}
    cadence:
      type: array
      items: {type: string}
description: PMP 9 计划 · 沟通管理
author: main-session
created_at: 2026-04-23
---

# PMP 沟通管理计划

## 渠道

{% for c in channels -%}
- {{ c }}
{% endfor %}

## 节奏

{% for c in cadence -%}
- {{ c }}
{% endfor %}
