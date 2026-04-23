---
doc_id: signoff-6-3-signoff-templates-v1.0
doc_type: signoff-execution-plan
layer: 6-finalQualityAcceptance
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/3-3-Solution-Monitoring&Controlling/acceptance-criteria/（5 维度验收标准）
version: v1.0
status: draft
assignee: **Sign-3 · 独立会话**
wave: 7
priority: P0（release 前最终审批）
estimated_duration: 0.5 天
---

# Sign-3 · 签收模板 Execution Plan

> **本 md 定位**：**独立会话** · 写 **5 维度签收模板** · main-4 WP08 签收时填。
>
> **本组做什么**：
> 1. 写 5 维度签收 yaml 模板
> 2. 写签收权责矩阵（谁签哪维度）
> 3. 写签收审批流程 SOP
> 4. 写最终签收汇总模板
>
> **本组不做**：
> - ❌ 不签收（main-4 WP08 时真人签）
> - ❌ 不评审质量（QA-5 release gate 决定）

---

## §1 5 维度签收

| 维度 | 内容 | 权责人 | 来源 |
|:---:|:---|:---|:---|
| D1 · 功能完整 | 10 L1 + 集成层 + UI 代码交付 · 20 IC 齐 | 开发 lead（主会话代理）| Dev-α/θ + 主-1/2/3/4 DoD |
| D2 · 质量达标 | QA-5 release gate PASSED · 0 P0/P1 · 测试覆盖 ≥ 85% | QA lead（QA-5 代理）| QA-1~5 报告 |
| D3 · 性能 SLO | 18 项 benchmark · 3 硬约束 100% 达 · 其余 ≥ 85% | Perf lead（QA-3）| QA-3 SLO 矩阵 |
| D4 · 韧性 + 审计 | Tier 1-4 恢复 · 审计链 100% · 5 硬红线 100% | Resilience lead（QA-4）| QA-4 矩阵 |
| D5 · 文档 + 合规 | 用户手册 + 开发手册 + API 参考 · LICENSE · 无 CVE-HIGH | Doc lead（Sign-4）| Sign-4 产出 |

每维度：约 10 条目 · 共 ~50 条目。

---

## §2 签收模板

### 模板 1 · 5 维度 yaml（`releases/signoff-v1.0.0.yaml`）

```yaml
signoff:
  version: v1.0.0
  signed_at: 2026-06-15T15:00:00Z

  D1_functional:
    status: APPROVED
    criteria:
      - name: all_10_l1_delivered
        status: PASS
        evidence: Dev-α ~ θ + 主-1/2/3 DoD
      - name: integration_layer_delivered
        status: PASS
        evidence: main-3 + main-4 WP02-03
      - name: ui_complete
        status: PASS
        evidence: Dev-θ WP09 + scenario-06 pass
      - name: 20_ic_integrated
        status: PASS
      - name: pm14_single_root_field_100_percent
        status: PASS
      # ... 10 条
    signed_by: dev-lead
    signed_time: 2026-06-15T14:30:00Z
    notes: ""

  D2_quality:
    status: APPROVED
    criteria:
      - name: qa5_release_gate_passed
        status: PASS
      - name: zero_p0_p1_bugs
        status: PASS
      - name: test_coverage_85_plus
        status: PASS
        evidence: "overall 87.3%"
      - name: audit_trail_complete_100
        status: PASS
      # ... 10 条
    signed_by: qa-lead

  D3_performance:
    status: APPROVED
    criteria:
      - name: ic15_halt_100ms_hard
        status: PASS
        samples: 10000
        p99: 95ms
      - name: ic17_panic_100ms_hard
        status: PASS
      - name: tick_drift_100ms_hard
        status: PASS
      - name: 18_slo_85_percent_pass
        status: PASS
        pass_count: 17/18
      # ... 10 条

  D4_resilience:
    status: APPROVED
    criteria:
      - name: tier_1_recovery_60s
        status: PASS
      - name: tier_2_3_4_fallback
        status: PASS
      - name: pm14_isolation_verified
        status: PASS
      - name: hrl_01_05_all_triggered_correctly
        status: PASS
      # ... 10 条

  D5_docs_compliance:
    status: APPROVED
    criteria:
      - name: user_guide_complete
        status: PASS
      - name: developer_guide_complete
        status: PASS
      - name: api_reference_20_ic_complete
        status: PASS
      - name: license_mit
        status: PASS
      - name: no_cve_high
        status: PASS
      # ... 10 条

  overall:
    status: APPROVED_FOR_RELEASE
    signoff_count: 5/5
    blocker_count: 0
```

### 模板 2 · 签收审批流程

```
1. 各维度 lead 填 yaml 的对应 section（5 并行）
2. 每维度：
   - 全 criteria PASS → status: APPROVED
   - 任一 FAIL → status: BLOCKED（需修复后重签）
3. 全 5 维度 APPROVED → overall: APPROVED_FOR_RELEASE
4. 任一 BLOCKED → overall: REJECTED · 返 main-4 WP06
```

### 模板 3 · 签收权责矩阵

```yaml
responsibility:
  D1_functional:
    lead: 主会话（dev-lead 代理）
    signoff_authority: 主会话
  D2_quality:
    lead: QA-5（qa-lead 代理）
    signoff_authority: QA-5 会话 + 主会话 co-sign
  D3_performance:
    lead: QA-3
    signoff_authority: QA-3 会话
  D4_resilience:
    lead: QA-4
    signoff_authority: QA-4 会话
  D5_docs_compliance:
    lead: Sign-4
    signoff_authority: Sign-4 会话
  overall:
    final_authority: **主会话**（综合 5 个子签）
```

---

## §3 WP 拆解（2 WP · 0.5 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| S3-WP01 | 5 维度 yaml 模板 + 50 条 criteria | acceptance-criteria/ O 产物 ready | 0.25 天 |
| S3-WP02 | 审批流程 SOP + 权责矩阵 + 自测 | WP01 | 0.25 天 |

---

## §4-§10

- §5 standup · prefix `S3-WPNN`
- §6 自修正：若签收维度有遗漏（如 security）· 补第 6 维度
- §7 对外契约：main-4 WP08 消费 · Sign-2 release 前置
- §8 DoD：yaml 模板齐 · 50 条 criteria 完整 · 自测跑通
- §9 风险：D3 硬约束难达 · main-4 WP05 充分调优；D2 测试覆盖不达 · 加单元测试
- §10 交付：`templates/signoff-v1.0.0.yaml.tpl` + `docs/SIGNOFF_PROCESS.md`

---

*— Sign-3 · 签收模板 · Execution Plan · v1.0 —*
