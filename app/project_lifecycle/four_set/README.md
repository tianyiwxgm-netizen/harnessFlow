# L2-03 4 件套生产器

> **一句话**：S2 阶段串行产出 requirements → goals → acceptance_criteria → quality_standards · 交叉引用闭包校验 · manifest 哈希锁定 · IC-19 触发 WBS。

## 4 步串行流程

```
REQ → GOAL → AC → QS
```

每步：
1. `skill.delegate_subagent(role=<role>)` · 返 items（结构化 id + 字段）
2. `template.render_template(kind=<fourset.x>)` · 渲染 md body
3. `atomic_write_chart(projects/<pid>/four-set/<doc>.md)` · 原子落盘
4. `event_bus.append_event("<doc>_ready")` · IC-09 审计

完成后：cross_ref 校验 + manifest.yaml 写入 + `4_pieces_ready` 总事件。

## Public API

```python
from app.project_lifecycle.four_set import FourPiecesProducer, FourSetRequest, FourSetContext

sut = FourPiecesProducer(template=l2_07_engine, skill=l1_05_client, event_bus=l1_09_bus)

resp = sut.assemble_four_set(
    FourSetRequest(
        project_id="p_...",
        request_id="r1", stage="S2",
        context=FourSetContext(charter_path=..., stakeholders_path=..., goal_anchor_hash="sha256:..."),
        caller_l2="L2-01",
    ),
    project_root="/var/harnessflow",
)
# resp.status = "ok" | "err"
# resp.result = FourSetManifest(manifest_path, manifest_hash, version, docs{4}, cross_check_report)

# Gate bundle 打包前
manifest = sut.query_artifact_refs(pid, project_root=...)

# S2 Gate 通过后
sut.request_wbs_decomposition(pid, manifest, trim_level="full")  # IC-19 发 L1-03
```

## 错误码（14 条 · E_L102_L203_001~014）

| 码 | 含义 | 触发 |
|:---|:---|:---|
| 001 UPSTREAM_MISSING | charter/scope 不存在 | L2-02 未完成 |
| 002 TEMPLATE_INVALID | L2-07 模板坏 | 运维修 |
| 003 TRACEABILITY_BROKEN | cross-ref errors 非空 | 断链 |
| 004 CROSS_REF_DEAD | 下游引用上游已删 id | 重做未级联 |
| 005 SECTION_DRIFT | LLM 漏章节 | 重试 |
| 006 PM14_PID_MISMATCH | context.path 不含 req.pid | 跨项目误入 |
| 007 AC_FORMAT_VIOLATION | AC 缺 Given/When/Then | LLM 重试 |
| 008 QC_FAILED_HARD | 单步 QC 3 次失败 | state=FAILED |
| 009 REDO_OUT_OF_SCOPE | rework 越界 | 内部 bug |
| 010 ID_PATTERN_VIOLATION | doc_id 不符正则 | LLM 重试 |
| 011 UPSTREAM_TIMEOUT | L2-07/L1-05 超时 | 重试 |
| 012 LLM_OUTPUT_EMPTY | skill 返空 items | 重试 |
| 013 CONFIG_ENDPOINTS_NONEMPTY | 运维误配 | 启动拒绝 |
| 014 DEPENDENCY_CLOSURE_EMPTY | 非法 target_subset | 拒绝 |

## IC 契约

- **入站** IC-L2-01 · L2-01 → L2-03 · `assemble_four_set(req)` + `query_artifact_refs(pid)`
- **出站** IC-L2-02 · L2-03 → L2-07 · render_template × 4（kind = `fourset.{requirements,goals,acceptance_criteria,quality_standards}`）
- **出站** IC-05 · L2-03 → L1-05 · delegate_subagent × 4（role = `{requirements-analysis, goals-writing, ac-scenario-writer, quality-audit}`）
- **出站** IC-06 · L2-03 → L1-06 · kb_read（可选 · trim_level=full 时）
- **出站** IC-09 · L2-03 → L1-09 · 5 事件（4 ready + 1 total）
- **出站** IC-19 · L2-03 → L1-03 · request_wbs_decomposition（S2 Gate 通过后）

## 不变量

- I-FS-01 · 4 步严格 REQ → GOAL → AC → QS 顺序（事件序列即证据）
- I-FS-02 · 每步落盘前 skill 返 items 非空 + id 正则合规
- I-FS-03 · AC 必含 Given/When/Then（不区分大小写）
- I-FS-04 · GOAL.linked_reqs ⊂ requirements.id · AC.linked_goal ∈ goals.id · QS.linked_ac ∈ acceptance_criteria.id
- I-FS-05 · manifest_hash = sha256(yaml dump of docs · sort_keys=True) · 同 4 doc 必等 hash
- I-FS-06 · 4_pieces_ready 事件带 manifest_hash + 4 paths

## 文件结构

```
app/project_lifecycle/four_set/
├── __init__.py                 # public API
├── schemas.py                  # FourSetRequest/Response/Manifest/DocRef/...
├── errors.py                   # FourSetError + 14 错误码
└── producer.py                 # FourPiecesProducer 串行 4 步
```

## 测试（15 TC · 全绿）

```
tests/project_lifecycle/
├── test_l2_03_four_set.py      · 6 TC（happy path + 3 错误码）
└── test_l2_03_extended.py      · 9 TC（query/WBS + 3 错误码 + IC 契约 3）
```

合计 15 TC · 覆盖 8/14 错误码 · 4 IC 契约。
