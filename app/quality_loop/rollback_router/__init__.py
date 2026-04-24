"""L2-07 · 偏差判定 + 4 级回退路由器 · IC-14 消费端。

**定位**：Quality Loop 闭环的 router · 消费 Dev-ζ（L1-07 supervisor）产的
`push_rollback_route_command` · 精确翻译 `verdict → target_stage` · 执行回退。

**4 级回退（Dev-ζ IC-14 schema 对齐 · `app/supervisor/event_sender/schemas.py`）**：

| verdict  | 常规 target_stage | 同级 ≥ 3 升级 target_stage |
|:---------|:------------------|:---------------------------|
| FAIL_L1  | S3 (retry_s3)     | UPGRADE_TO_L1_01           |
| FAIL_L2  | S4 (retry_s4)     | UPGRADE_TO_L1_01           |
| FAIL_L3  | S5 (retry_s5)     | UPGRADE_TO_L1_01           |
| FAIL_L4  | UPGRADE_TO_L1_01  | UPGRADE_TO_L1_01           |

本包只负责**消费** Dev-ζ 产的 command，通过 `verdict_classifier` 分级
+ `stage_mapper` 决策 target，`retry_coordinator` 维护同级连续失败计数（≥ 3
升级 · 与 Dev-ε 的 `_escalated_wps` dedup 模式对齐），最后由 `executor`
调 L1-02 IC-01 `state_transition`（当前为 mock Dev-δ）。

**约束**：
- PM-14：所有回退必带 `project_id`；跨 pid 拒绝。
- 幂等：同 `route_id`（Dev-ζ 用作 idempotency_key）多次 → 单次执行。
- 本 WP 核心：`verdict_classifier` + `stage_mapper` + `executor`（edge case 留后续）。
"""
