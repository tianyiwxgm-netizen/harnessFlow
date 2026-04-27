<!-- retro-p-harness-backfill-node-id-20260427T052300Z-2026-04-27T05:39:00Z -->

# Retro — p-harness-backfill-node-id-20260427T052300Z

- **Project**: harnessFlow (Slice A pipeline_graph 可视性收尾)
- **Task type**: 重构 / 数据迁移工具
- **Size / Risk**: S / 低
- **Route taken**: B 轻 PRP（auto-pick @0.92）
- **Final outcome**: success（verifier PASS 5/5，commit `770192e`）
- **Date**: 2026-04-27
- **Elapsed**: active ≈ 15 min（INIT 1 / CLARIFY 1 / PLAN 5 / IMPL+VERIFY 6 / COMMIT 1 / RETRO 1）
- **Token**: 未计量（仍走 task-board cost_budget 占位）

> 本 retro 由 main skill 内联渲染（self-driven walkthrough，未拉起 retro-generator subagent；S × 重构 不必重型）。
> 数据源：task-board p-harness-backfill-node-id-20260427T052300Z.json + verifier_report inline + 13 stage_artifacts。
> 11 项 section 对齐 method3 § 7.1。

---

## 1. DoD 实际 diff

**预期子契约**: 5 个 AND 子条件 — exists + pytest_pass + backfill_applied + sample5_50pct + default_suite_unchanged

| 子条件 | 预期 | 实际 | verdict |
| --- | --- | --- | --- |
| exists(scripts/backfill_node_id_in_stage_artifacts.py) | true | 290 行 / N1-N13 derive / argparse | PASS |
| pytest_run_passed(tests/unit/test_backfill_node_id.py) | true | 8 passed in 0.08s（5 plan + 3 edge cases） | PASS |
| backfill_applied_to_21_task_boards | true | 实际 23 changed + 1 skipped（e2e-migration 13/13） | PASS |
| sample5_50pct_nodes_have_outputs | ≥50% | 5/5 sample 全部 13/13 outputs_actual filled = 100% | PASS（远超） |
| default_suite_unchanged | 49/49 | 49 passed in 0.22s（pytest -m 'not e2e'） | PASS |

**verifier_report**: inline 在 task-board.verifier_report.overall=PASS（Self-driven inline verifier，5/5 evidence_checks）。

---

## 2. 路线偏差

- **初始推荐路线**: B 轻 PRP（routing-matrix S × 重构 × 低 → top-1=0.92）
- **实际走的路线**: B
- **是否偏离**: 否
- **偏离原因**: N/A

routing-events: 0（auto-pick 收敛，未触发任何 routing 事件）。

---

## 3. retry 路径

- **retry_count**: 0
- **retry_levels_used**: 无
- **L1/L2/L3 escalation**: 不需要 — 单次 IMPL→VERIFY→COMMIT 一镜到底

测试一次绿（红→绿一阶段完成），backfill 一次跑通 23 task-boards，default suite 不破。无任何 santa-loop / IMPL retry。

---

## 4. supervisor 干预统计

- **INFO**: 8（BOOTSTRAP / CLARIFY_LOCKED / ROUTE_AUTO_PICK / PLAN_LANDED / TDD_RED_GREEN / BACKFILL_APPLIED / DEFAULT_SUITE_UNCHANGED / COMMIT_LANDED）
- **WARN**: 0
- **BLOCK**: 0
- **red_lines_triggered**: 无

特别说明：本任务 self-driven，未拉起 supervisor subagent；intervention 由 main skill 在每个状态转移点内联记录，相当于 Slice A 静态轨迹（Slice B 上线后由 PIPELINE_EMIT runtime 自动填充）。

---

## 5. 用户中断计数

- **DRIFT 类**: 0
- **DOD_GAP 类**: 0
- **IRREVERSIBLE 类**: 0
- **废问题**: 0
- **总打断**: 0（self-walk，无用户实时打断；用户只在初始触发"A 真走"指令）

---

## 6. evolution_suggestions

1. **Slice B PIPELINE_EMIT runtime 上线后，backfill 工具变 deprecated** — 应在 main skill § 2.5 PIPELINE_EMIT 完成后给本工具加 `--legacy-only` flag，新任务走 emit；本工具仅用于跨版本数据迁移
2. **derive 函数的 fallback 数据应有"FALLBACK_PLACEHOLDER"标识** — 当前 N2 用常量 ref list、N6 默认空 list 时无法区分"任务真没做这步"vs"backfill 没找到证据"，建议在 outputs 里加 `_derived_from: "fallback"` 元字段，让 dashboard 区分实证 vs 推断
3. **跑 backfill 后应自动重启 dashboard 后端 / 重置 mock_data 缓存** — 当前 mock_data 在进程内 dict 有引用 mutate，但 cache 行为未严格定义；多次跑 backfill 后 API 输出可能滞后；建议加 `python3 scripts/backfill_node_id_in_stage_artifacts.py --then-bounce-dashboard` flag 自动 kill+restart uvicorn
4. **测试覆盖：N2/N5/N6 derive 路径只测了 happy path** — 没测"existing stage_artifacts.plan_path 来源 N5"分支 / "verifier evidence_checks 取首 5 项"分支；后续 Slice B 实施前应补 3 个 edge case 测试
5. **commit message 没引用 task_id** — 建议 commit hook 自动从 active task-board.task_id 注入 footer `task_id: <id>`，方便 git log → task-board reverse lookup（tank-battle retro 也提过类似建议）

---

## 7. failure_archive_links

- **本任务 archive**: `archive/failure-archive/p-harness-backfill-node-id-20260427T052300Z.jsonl`
- **error_type**: OTHER（success path，无 retry / 无 BLOCK；archive 仅记 lessons-learned）
- **trap_matched**: ["pipeline-graph-data-shape-derived-from-history", "self-driven-walk-validates-slice-a-mvp"]

---

## 8. 时间预算 vs 实际

- **预算 soft / hard**: 60 / 120 min
- **实际**: 15 min（active execution；wall-clock 含 2-3 min 思考）
- **token**: 未计量
- **无超预算**

主要时间分配：
- INIT/CLARIFY: 1 min（已有上下文，clarify_rounds=1）
- PLAN: 5 min（plan markdown 落盘 + 13-node derive 策略表）
- IMPL+VERIFY: 6 min（写 test + script 一气；pytest 0.08s + backfill 跑 23 板 < 1s + sample 5 task 验证）
- COMMIT+RETRO: 3 min

---

## 9. context drift / goal_anchor 漂移

- **goal_anchor.hash 变化**: 无（c039f5e 全程不变）
- **PostToolUse-supervisor-wake hook 触发**: 0 次 drift_critical
- **CLAUDE.md 修改**: 1 次（INIT 阶段写入新 goal-anchor block；非漂移，是新任务装载）

---

## 10. checkpoint_refs

- **save-session 调用**: 0（B 路 + S size 不强制 mid-checkpoint；context 未临界）
- **checkpoint files**: 无

---

## 11. 改进项 follow-up（指给 Slice B / Slice C）

- **Slice B 启动前**：在 main skill § 2.5 PIPELINE_EMIT 写 runtime 时，参考本工具的 derive 策略表（13 行 N1→N13 mapping），但**反向**——runtime 在节点完成时主动 emit，而非事后 derive
- **Slice C 启动前**：本工具数据可作为 supervisor pulse 的"基线快照"——pulse 触发时若发现 stage_artifacts 缺某 node_id 但 state_history 已转移，应 BLOCK，强制 emit 兜底
- **Dashboard 前端**：本工具填的 outputs 已经让 N5 抽屉从 "outputs（静态 3 / 实际 0）" 变成 "实际 1+"；但前端是否在 outputs_actual 为空时显示黄色 "未填写" 警示？建议 Slice A pipeline_graph 验收 checklist 加一条
- **重要 invariant**: 本工具 idempotent 必须始终保持。每次跑两遍 n_added 第二次必须 0。配 CI 跑 pytest tests/unit/test_backfill_node_id.py::test_idempotent_second_run_no_change 守住这条线

---

<!-- /retro-p-harness-backfill-node-id-20260427T052300Z -->
