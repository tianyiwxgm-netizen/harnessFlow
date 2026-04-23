---
kind: fourset.scope
version: v1.0
slot_schema:
  type: object
  required: [scope_statement, in_scope, out_of_scope]
  properties:
    scope_statement:
      type: string
      description: "项目范围陈述"
    in_scope:
      type: array
      items: {type: string}
    out_of_scope:
      type: array
      items: {type: string}
description: S2 4 件套 · scope 文档模板
author: main-session
created_at: 2026-04-23
---

# Scope 文档

## 范围陈述

{{ scope_statement | trim }}

## 范围内

{% for s in in_scope -%}
- {{ s }}
{% endfor %}

## 范围外

{% for s in out_of_scope -%}
- {{ s }}
{% endfor %}
