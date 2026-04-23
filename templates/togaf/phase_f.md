---
kind: togaf.phase_f
version: v1.0
slot_schema:
  type: object
  required: [work_packages]
  properties:
    work_packages:
      type: array
      items:
        type: object
        required: [name, duration_days]
        properties:
          name: {type: string}
          duration_days: {type: integer}
description: TOGAF ADM · Phase F (Migration Planning)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase F · Migration Planning

## WorkPackage（{{ work_packages | length }} 项）

{% for wp in work_packages -%}
- **{{ wp.name }}** · {{ wp.duration_days }} 天
{% endfor %}
