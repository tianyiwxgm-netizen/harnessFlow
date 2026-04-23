---
kind: fourset.quality_standards
version: v1.0
slot_schema:
  type: object
  required: [project_id, qs_items]
  properties:
    project_id: {type: string}
    qs_items:
      type: array
      minItems: 1
      items:
        type: object
        required: [id, measurable_criteria, verification_method, linked_ac]
        properties:
          id: {type: string, pattern: "^QS-\\d{3}$"}
          measurable_criteria: {type: string}
          verification_method: {type: string, enum: [unit_test, integration_test, e2e_test, manual, perf_benchmark, audit]}
          linked_ac: {type: string, pattern: "^AC-\\d{3}$"}
description: S2 4 件套 · quality_standards.md（QS-NNN · measurable + verification）
author: main-session
created_at: 2026-04-23
---

# Quality Standards · {{ project_id }}

{% for qs in qs_items %}
## {{ qs.id }}

- **measurable_criteria**：{{ qs.measurable_criteria | trim }}
- **verification_method**：{{ qs.verification_method }}
- **linked_ac**：{{ qs.linked_ac }}
{% endfor %}
