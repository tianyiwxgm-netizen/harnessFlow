---
kind: fourset.goals
version: v1.0
slot_schema:
  type: object
  required: [project_id, goals_items]
  properties:
    project_id: {type: string}
    goals_items:
      type: array
      minItems: 1
      items:
        type: object
        required: [id, statement, linked_reqs]
        properties:
          id: {type: string, pattern: "^GOAL-\\d{3}$"}
          statement: {type: string}
          linked_reqs:
            type: array
            items: {type: string, pattern: "^REQ-\\d{3}$"}
description: S2 4 件套 · goals.md（GOAL-NNN · linked_reqs）
author: main-session
created_at: 2026-04-23
---

# Goals · {{ project_id }}

{% for g in goals_items %}
## {{ g.id }}

{{ g.statement | trim }}

- **linked_reqs**：{{ g.linked_reqs | join(", ") }}
{% endfor %}
