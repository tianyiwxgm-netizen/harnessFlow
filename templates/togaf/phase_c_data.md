---
kind: togaf.phase_c_data
version: v1.0
slot_schema:
  type: object
  required: [data_entities, data_flows]
  properties:
    data_entities:
      type: array
      items: {type: string}
    data_flows:
      type: array
      items: {type: string}
description: TOGAF ADM · Phase C (Data Architecture)
author: main-session
created_at: 2026-04-23
---

# TOGAF Phase C · Data Architecture

## 数据实体

{% for e in data_entities -%}
- {{ e }}
{% endfor %}

## 数据流

{% for f in data_flows -%}
- {{ f }}
{% endfor %}
