---
kind: fourset.requirements
version: v1.0
slot_schema:
  type: object
  required: [project_id, requirements_items]
  properties:
    project_id: {type: string}
    requirements_items:
      type: array
      minItems: 1
      items:
        type: object
        required: [id, description]
        properties:
          id: {type: string, pattern: "^REQ-\\d{3}$"}
          description: {type: string}
          priority: {type: string, enum: [P0, P1, P2]}
description: S2 4 件套 · requirements.md（REQ-NNN）
author: main-session
created_at: 2026-04-23
---

# Requirements · {{ project_id }}

{% for r in requirements_items %}
## {{ r.id }}

{{ r.description | trim }}

{% if r.priority %}- **优先级**：{{ r.priority }}{% endif %}
{% endfor %}
