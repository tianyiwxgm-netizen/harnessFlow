---
kind: closing.lessons_learned
version: v1.0
slot_schema:
  type: object
  required: [what_went_well, what_went_wrong, action_items]
  properties:
    what_went_well:
      type: array
      items: {type: string}
    what_went_wrong:
      type: array
      items: {type: string}
    action_items:
      type: array
      items: {type: string}
description: S6 Lessons Learned 模板
author: main-session
created_at: 2026-04-23
---

# Lessons Learned

## What Went Well

{% for w in what_went_well -%}
- {{ w }}
{% endfor %}

## What Went Wrong

{% for w in what_went_wrong -%}
- {{ w }}
{% endfor %}

## Action Items

{% for a in action_items -%}
- {{ a }}
{% endfor %}
