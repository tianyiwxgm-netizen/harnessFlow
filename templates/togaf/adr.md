---
kind: togaf.adr
version: v1.0
slot_schema:
  type: object
  required: [title, context, decision, alternatives, consequences]
  properties:
    title:
      type: string
    context:
      type: string
    decision:
      type: string
    alternatives:
      type: array
      items: {type: string}
    consequences:
      type: array
      items: {type: string}
description: TOGAF · Architecture Decision Record
author: main-session
created_at: 2026-04-23
---

# ADR · {{ title }}

## Context

{{ context | trim }}

## Decision

{{ decision | trim }}

## Alternatives

{% for a in alternatives -%}
- {{ a }}
{% endfor %}

## Consequences

{% for c in consequences -%}
- {{ c }}
{% endfor %}
