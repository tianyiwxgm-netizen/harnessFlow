---
kind: pmp.integration
version: v1.0
slot_schema:
  type: object
  required: [integration_summary, change_control]
  properties:
    integration_summary:
      type: string
    change_control:
      type: array
      items: {type: string}
description: PMP 9 计划 · 整合管理
author: main-session
created_at: 2026-04-23
---

# PMP 整合管理计划

## 整合概述

{{ integration_summary | trim }}

## 变更控制

{% for c in change_control -%}
- {{ c }}
{% endfor %}
