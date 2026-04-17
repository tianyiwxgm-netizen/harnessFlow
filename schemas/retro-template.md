<!-- retro-${task_id}-${ts} -->

# Retro — ${task_id}

- **Project**: ${project}
- **Task type**: ${task_type}
- **Size / Risk**: ${size} / ${risk}
- **Route taken**: ${route}
- **Final outcome**: ${final_outcome}
- **Date**: ${date}
- **Elapsed**: ${elapsed_min} min
- **Token**: ${token_used} / ${token_budget}

> 本文档由 `harnessFlow:retro-generator` + `archive/retro_renderer.py` 自动渲染。
> 11 项 section 严格对齐 method3 § 7.1。数据源见 Phase 7 plan § 2。
> 未填字段标记为 `<待人工补充>`；用户补完可直接覆盖回本文件。

---

## 1. DoD 实际 diff

**预期子契约**: ${dod_expression}

| 子条件 | 预期 | 实际 | verdict |
| --- | --- | --- | --- |
${dod_diff_table}

**verifier_report 链接**: ${verifier_report_link}

---

## 2. 路线偏差

- **初始推荐路线**: ${initial_route_recommendation}
- **实际走的路线**: ${route}
- **是否偏离**: ${route_drifted}
- **偏离原因**: ${route_drift_reason}

routing-events 快照：
```
${routing_events_snapshot}
```

---

## 3. 纠偏次数

按 L0/L1/L2/L3 分级计数：

| 级别 | 次数 | 典型触发 |
| --- | --- | --- |
| L0（自修） | ${retry_l0_count} | ${retry_l0_example} |
| L1（换 skill） | ${retry_l1_count} | ${retry_l1_example} |
| L2（换路线） | ${retry_l2_count} | ${retry_l2_example} |
| L3（升级用户） | ${retry_l3_count} | ${retry_l3_example} |

**总 retry_count**: ${retry_count}

---

## 4. Verifier FAIL 次数

按子契约分类（跨 Verifier 多次调用累计）：

${verifier_fail_breakdown}

**红线触发**: ${red_lines_triggered}

---

## 5. 用户打断次数

| 类别 | 次数 |
| --- | --- |
| DRIFT | ${interrupt_drift_count} |
| DOD_GAP | ${interrupt_dod_gap_count} |
| IRREVERSIBLE | ${interrupt_irreversible_count} |
| 废问题（方法 3 反模式） | ${interrupt_wasted_question_count} |

> "废问题" 当前记次数即可，自动分类见 Phase 9+ 计划。

---

## 6. 耗时 vs 估算

- **估算**: ${time_budget_min} min
- **实际**: ${elapsed_min} min
- **偏差**: ${time_delta_pct}
- **主要时间花销**: ${time_hotspot}

---

## 7. 成本 vs 估算

- **Token 预算**: ${token_budget}
- **Token 实际**: ${token_used}
- **偏差**: ${token_delta_pct}
- **API 成本（可选）**: ${api_cost}

---

## 8. 新发现的 trap

${new_traps_found}

> 格式：`- <trap_id>: <一句话描述> / 命中节点: <node>`
> 未发现则写 `无`；待人工补充则 `<待人工补充>`。

---

## 9. 新发现的有效组合

${new_effective_combinations}

> 格式：`- <combo_name>: <skill_a> + <skill_b> → <目的/效果>`
> 供 `skill-combination-pool.jsonl` 候选入库（Phase 9+）。

---

## 10. 进化建议

${evolution_suggestions}

> 建议粒度：
> - routing-matrix 权重调整（引用 audit-report 链接）
> - 新 skill 引入 / 现有 skill 改进
> - 反模式补充（新加入 method3 § 反模式清单）

**关联 audit-report**: ${audit_report_link}

---

## 11. 下次推荐

${next_time_recommendation}

> 给未来同类任务的明确指引：
> - 路线：${next_route_hint}
> - 关键子契约预置：${next_must_verify}
> - 规避的 trap：${next_traps_to_avoid}

---

<!-- /retro-${task_id}-${ts} -->
