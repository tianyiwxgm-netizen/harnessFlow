# harnessFlow 产出物模板库（L1-02 L2-07 加载源）

本目录为 L2-07 产出物模板引擎（`app/l1_02/template_engine/`）启动时加载的**唯一真实源**。

## 27 kind 必全清单

| 子目录 | kind | 调用方 L2 | 数量 |
|:---|:---|:---:|:---:|
| `kickoff/` | `kickoff.goal` · `kickoff.scope` | L2-02 | 2 |
| `fourset/` | `fourset.scope` · `fourset.prd` · `fourset.plan` · `fourset.tdd` | L2-03 | 4 |
| `pmp/` | `pmp.integration` · `pmp.scope` · `pmp.schedule` · `pmp.cost` · `pmp.quality` · `pmp.resource` · `pmp.communication` · `pmp.risk` · `pmp.procurement` | L2-04 | 9 |
| `togaf/` | `togaf.preliminary` · `togaf.phase_a~h` · `togaf.phase_c_data` · `togaf.phase_c_application` · `togaf.adr` | L2-05 | 11 |
| `closing/` | `closing.lessons_learned` · `closing.delivery_manifest` · `closing.retro_summary` | L2-06 | 3 |

**合计 29 文件 · 对应 29 kind**（Phase C 拆 data + application · 总数 27+2=29 · 以 `required_kinds` 清单为准）。

> 注：L2-07 tech §3.5 声称「~27 模板」· 含 TOGAF Phase C 拆分后实际为 29。`REQUIRED_KINDS_DEFAULT` 以代码清单为准。

## frontmatter 必填字段

每个 `*.md` 模板文件开头必含：

```yaml
---
kind: <string>               # e.g. "pmp.scope"
version: v1.0                # semver
slot_schema:                 # jsonschema Draft 2020-12
  type: object
  required: [...]
  properties:
    <slot_name>:
      type: string | number | array | object | boolean
      # ... 可加 pattern / enum / items
description: <string>
author: <string>
created_at: YYYY-MM-DD
---
```

## 正文语法白名单

- `{{ var }}` `{{ var | filter }}` `{% for %}` `{% if %}`
- Filter 白名单：`upper · lower · title · trim · int · round · join · length · first · date_iso`
- **禁用**：`{% import %}` · `{% include %}` · `__class__` · `getattr` · `eval`（Jinja2 SandboxedEnvironment 默认拦截）

## 产出约束

- 单次渲染产出 ≤ 200KB（`max_output_bytes`）
- 渲染后 frontmatter 必含 `template_id` / `template_version` / `rendered_at`（运行时由 engine 注入）

## 修改规则（PM-13 裁剪档 + PM-07 驱动）

- 模板版本升级走 `version: v1.0 → v2.0` · **不支持热更新**（启动 pin）
- 正文字段变更必同步 `slot_schema`
- 改模板后运行 `pytest tests/l1_02/test_l2_07_*` 验证

---

*加载入口：`app.l1_02.template_engine.registry.TemplateLoader.load_all()`*
