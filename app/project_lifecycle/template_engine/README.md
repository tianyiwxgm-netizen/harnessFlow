# L2-07 产出物模板引擎

> **一句话**：L1-02 无状态 Domain Service · Jinja2 SandboxedEnvironment + jsonschema · 被 L2-02/03/04/05/06 通过 IC-L2-02 调用 · 产 md + frontmatter + output_sha256 + IC-09 审计事件。

## 对外 API（4 方法）

```python
from app.project_lifecycle.template_engine import TemplateEngine

eng = TemplateEngine.load_from_dir(
    template_dir="templates",
    event_emitter=ic09_bus,   # 可选 · 默认 in-memory
)

out = eng.render_template(
    request_id="req-1",
    project_id="01H...",             # ULID · PM-14
    kind="pmp.scope",                # 29 已注册 kind
    slots={...},                     # 按 slot_schema
    caller_l2="L2-04",               # 白名单 L2-01~06
    timeout_ms=2000,                 # 50-10000
    expected_version="v1.0",         # 可选 · 版本 pin 校验
    expected_slots_hash="abc...",    # 可选 · 中间层篡改检测
)
# out: RenderedOutput(request_id, template_id, template_version, slots_hash,
#                     output, body_sha256, lines, frontmatter, rendered_at, engine_version)

eng.list_available_templates()       # list[str]  · ≥29
eng.get_template_version("pmp.scope")  # "v1.0" | None
eng.validate_slots("kickoff.goal", slots)  # ValidationResult(ok, error_code, details)
```

## 29 注册 kind

| 子目录 | kind | 数量 | 调用方 |
|:---|:---|:---:|:---:|
| `templates/kickoff/` | `kickoff.goal` · `kickoff.scope` | 2 | L2-02 |
| `templates/fourset/` | `fourset.scope` · `fourset.prd` · `fourset.plan` · `fourset.tdd` | 4 | L2-03 |
| `templates/pmp/` | `pmp.{integration,scope,schedule,cost,quality,resource,communication,risk,procurement}` | 9 | L2-04 |
| `templates/togaf/` | `togaf.{preliminary,phase_a,phase_b,phase_c_data,phase_c_application,phase_d,phase_e,phase_f,phase_g,phase_h,adr}` | 11 | L2-05 |
| `templates/closing/` | `closing.{lessons_learned,delivery_manifest,retro_summary}` | 3 | L2-06 |

## 14 错误码（`E_L102_L207_001~014`）

| 错误码 | meaning | 可恢复性 |
|:---|:---|:---|
| E001 | TEMPLATE_NOT_FOUND | 调用方修 |
| E002 | SLOT_SCHEMA_VIOLATION | slot 调整 |
| E003 | SLOT_REQUIRED_MISSING | 补齐必填 |
| E004 | TEMPLATE_SYNTAX_ERROR | 运维修模板 + 重启 |
| **E005** | **TEMPLATE_CODE_EXEC** | **CRITICAL** · 立即报 L1-07 · 发 IC-09 CRITICAL 事件 |
| E006 | RENDER_TIMEOUT | 减 slot 体积 / 增 timeout |
| E007 | OUTPUT_TOO_LARGE | > 200KB 拒绝 |
| E008 | FRONTMATTER_PARSE_FAIL | 模板修 |
| E009 | VERSION_MISMATCH | 运维重启 |
| E010 | INVALID_KIND_NAME | 调用方按 `[a-z0-9._-]+` |
| E011 | CALLER_NOT_WHITELISTED | 调用方身份修正 · L2-01~06 |
| E012 | SLOTS_HASH_MISMATCH | 追查中间层篡改 |
| E013 | HASH_COMPUTE_FAIL | 重试 / 硬件问题 |
| E014 | AUDIT_EMIT_FAIL | buffer 降级 · 自恢复 |

## IC 边界

- **上游** IC-L2-02（被动接收）· L2-02/03/04/05/06 → 本 L2
- **下游** IC-09 append_event · 本 L2 → L1-09 EventBus
  - `L1-02/L2-07:template_rendered`（INFO · 每次成功渲染）
  - `L1-02/L2-07:template_code_exec_attempt`（CRITICAL · E005 触发）

## 不变量

| ID | 不变量 |
|:---|:---|
| I-L207-01 | 同 slots + 同 template_id → 同 output_sha256（幂等） |
| I-L207-02 | 模板必经 sandbox（禁任意代码执行） |
| I-L207-03 | 渲染结果含 frontmatter · 必含 `template_id` / `template_version` / `rendered_at` |
| I-L207-04 | slot 值类型必匹配 schema |
| I-L207-05 | 本 L2 不做 IO · 返 string 给调用方落盘 |

## SLO（warm-cache）

| 维度 | P50 | P95 | 硬上限 |
|:---|:---:|:---:|:---:|
| 单次 render_template | 20ms | 100ms | 2s |
| validate_slots | 1ms | 5ms | 100ms |
| Jinja2 sandbox 渲染 | 10ms | 50ms | 1s |
| output_sha256 (200KB) | 5ms | 20ms | 200ms |
| 启动加载 29 模板 | 200ms | 500ms | 3s（cold） |
| 并发 50 线程 | thread-safe | 幂等 sha | — |

## 实现约束

- Jinja2 `SandboxedEnvironment` + `StrictUndefined`（未定义变量即 raise）
- Filter 白名单：`upper · lower · title · trim · int · round · join · length · first · date_iso`
- 启动 pin 模板版本 · 不支持热更新
- 启动缺任一 required kind → `StartupError`
- 启动配置 `validate_slot_schemas=True` 时跑 jsonschema meta 校验（默认 off · perf）
- `FileSystemBytecodeCache` 在 `$TMPDIR/harnessflow-l207-jinja-bcache/`

## 测试套（56 TC · 全绿）

- `tests/project_lifecycle/test_l2_07_template_engine_positive.py` · 13 TC 正向
- `tests/project_lifecycle/test_l2_07_template_engine_negative.py` · 14 TC 错误码
- `tests/project_lifecycle/test_l2_07_template_engine_startup.py` · 6 TC 启动
- `tests/project_lifecycle/test_l2_07_ic_contracts.py` · 7 TC IC 契约
- `tests/project_lifecycle/test_l2_07_perf.py` · 6 TC SLO

Coverage ≥ 86.5%（target ≥ 85%）。
