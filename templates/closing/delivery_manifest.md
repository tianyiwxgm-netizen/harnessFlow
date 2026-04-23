---
kind: closing.delivery_manifest
version: v1.0
slot_schema:
  type: object
  required: [deliverables, checksums]
  properties:
    deliverables:
      type: array
      items: {type: string}
    checksums:
      type: array
      items:
        type: object
        required: [path, sha256]
        properties:
          path: {type: string}
          sha256: {type: string}
description: S6 交付清单模板
author: main-session
created_at: 2026-04-23
---

# Delivery Manifest

## 交付物

{% for d in deliverables -%}
- {{ d }}
{% endfor %}

## 校验和

{% for c in checksums -%}
- `{{ c.path }}` · sha256 = `{{ c.sha256 }}`
{% endfor %}
