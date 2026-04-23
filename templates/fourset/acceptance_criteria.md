---
kind: fourset.acceptance_criteria
version: v1.0
slot_schema:
  type: object
  required: [project_id, ac_items]
  properties:
    project_id: {type: string}
    ac_items:
      type: array
      minItems: 1
      items:
        type: object
        required: [id, given, when, then, linked_goal]
        properties:
          id: {type: string, pattern: "^AC-\\d{3}$"}
          given: {type: string}
          when: {type: string}
          then: {type: string}
          linked_goal: {type: string, pattern: "^GOAL-\\d{3}$"}
description: S2 4 件套 · acceptance_criteria.md（AC-NNN · GWT）
author: main-session
created_at: 2026-04-23
---

# Acceptance Criteria · {{ project_id }}

{% for ac in ac_items %}
## {{ ac.id }}

- **Given**：{{ ac.given | trim }}
- **When**：{{ ac.when | trim }}
- **Then**：{{ ac.then | trim }}
- **linked_goal**：{{ ac.linked_goal }}
{% endfor %}
