---
doc_id: prd-l1-04-quality-loop-v1.0
doc_type: l1-prd
parent_doc:
  - HarnessFlowGoal.md
  - docs/2-prd/businessFlow.md
  - docs/2-prd/scope.md#5.4
version: v1.0
status: ready_for_review
author: mixed
created_at: 2026-04-20
updated_at: 2026-04-20
traceability:
  goal_anchor: HarnessFlowGoal.md#2.2 五大纪律"质量"+"检验" / §3.5 硬约束 4（S5 未 PASS 不得进 S7）/ §4.1 "真完成质量达标率 ≥ 95%"
  business_flow: [BF-S3-01, BF-S3-02, BF-S3-03, BF-S3-04, BF-S3-05, BF-S4-03, BF-S4-04, BF-S5-01, BF-S5-02, BF-S5-03, BF-S5-04, BF-E-10]
  scope: [L1-04]
consumer:
  - docs/2-prd/flowOutInput.md#4.3
  - docs/2-prd/L1集成/prd.md
  - docs/2-prd/L1-01主 Agent 决策循环/prd.md（IC-03 消费侧）
  - docs/2-prd/L1-02项目生命周期/prd.md（S3/S4/S5 阶段消费侧）
  - docs/2-prd/L1-05 Skill子 Agent/prd.md（IC-20 委托 verifier 消费侧）
  - docs/2-prd/L1-07 Harness监督/prd.md（IC-14 回退路由消费侧）
  - docs/2-prd/L1-09 韧性审计/prd.md（verifier_report + verdict 落盘）
  - docs/2-prd/L1-10 人机协作UI/prd.md（TDD 质量 tab / Verifier 证据链 tab）
  - TDD 阶段（DoD 依据）
---

# L1-04 · Quality Loop 能力 · PRD

> **版本**：v1.0（7 个 L2 产品级完备；L3 实现设计留给 `docs/3-1-Solution-Technical/L1-04/tech-design.md`）
> **定位**：HarnessFlow 的**质量闭环脊柱** —— S3 蓝图定义 → S4 执行驱动 → S5 TDDExe 独立验证 → 4 级回退路由的**单一控制点**；是 Goal §2.2 五大纪律中"质量"与"检验"两项的落地唯一路径；保证**真完成质量达标率 ≥ 95%**（Goal §4.1）的红线守门员。
> **严格遵循**：本 PRD **不得与** `docs/2-prd/scope.md §5.4` 冲突。如冲突以 scope 为准。
> **严格边界**：本 PRD 只描述"要做什么"（职责 / 边界 / 约束 / 禁止 / 必须 / 交互 / 验收）；"怎么做"（DoD 表达式具体语法 / 状态机实现 / verifier 通信协议 / 回退判定阈值参数）迁到 `docs/3-1-Solution-Technical/L1-04/tech-design.md`。

---

## 0. 撰写进度

- [x] §1 L1-04 范围锚定（引用 scope §5.4）
- [x] §2 L2 清单（7 个）
- [x] §3 L2 整体架构 · 图 A 主干质量闭环面（S3 → S4 → S5 → 回退）
- [x] §4 L2 整体架构 · 图 B 横切 verdict 路由 & 4 级回退响应面
- [x] §5 L2 间业务流程（9 条）
- [x] §6 IC-L2 契约清单（11 条 · 一句话 + 方向）
- [x] §7 L2 定义模板（9 小节标准 · 严禁 §X.10）
- [x] §8 L2-01 · TDD 蓝图生成器（Master Test Plan + 蓝图骨架）
- [x] §9 L2-02 · DoD 表达式编译器（白名单 AST eval 安全盒）
- [x] §10 L2-03 · 测试用例生成器（骨架先红灯）
- [x] §11 L2-04 · 质量 Gate 编译器 + 验收 Checklist 生成器
- [x] §12 L2-05 · S4 执行驱动器（IMPL → 测试绿 → WP-DoD 自检 → commit）
- [x] §13 L2-06 · S5 TDDExe Verifier 编排器（独立 session 委托 + 三段证据链组装）
- [x] §14 L2-07 · 偏差判定 + 4 级回退路由器（接收 L1-07 verdict → 回退指令广播）
- [x] §15 对外 scope §8 IC 契约映射
- [x] §16 本 L1 retro 位点
- [x] 附录 A · 术语 · 附录 B · BF 映射

---

## 1. L1-04 范围锚定（引自 scope §5.4，不重复写）

| scope §5.4 子节 | 内容摘要 | 锚点 |
|---|---|---|
| §5.4.1 职责 | 运行 HarnessFlow 质量闭环：S3 TDD 蓝图 → S4 执行 → S5 TDDExe → 4 级回退路由 | scope#5.4.1 |
| §5.4.2 输入/输出 | 输入：4 件套（from L1-02）、WBS（from L1-03）、verifier 结果（from L1-05）、Supervisor 回退指令（from L1-07）<br>输出：S3 产出（Master Test Plan + DoD 表达式 + 用例 + 质量 gate + 验收 checklist）、S4 自检报告、S5 verifier_report 三段证据链、verdict + 回退路由指令 | scope#5.4.2 |
| §5.4.3 边界 | In：TDD 蓝图生成机制 / DoD 表达式编译 / 测试用例骨架生成 / 质量 gate 规则 / S4 执行驱动 / S5 verifier 编排 / 4 级回退路由<br>Out：不管 8 维度其他监督（仅"真完成质量"一维）/ 不管硬红线拦截（只管 4 级回退） | scope#5.4.3 |
| §5.4.4 约束 | PM-05 Stage Contract 机器可校验 / 4 条硬约束（S5 未 PASS 不得进 S7 / verifier 独立 session / DoD 白名单 AST / TDD 蓝图 S3 前全齐） | scope#5.4.4 |
| §5.4.5 🚫 禁止行为 | 6 条（禁 S5 未 PASS 进 S7 / 禁 verifier 主 session 跑 / 禁 DoD 含 arbitrary exec / 禁绕过 Quality Loop 报完成 / 禁 S3 蓝图 S4 边补 / 禁自做 4 级判定）| scope#5.4.5 |
| §5.4.6 ✅ 必须义务 | 5 条（必 S3 先行蓝图齐全 / 必委托 verifier 独立 session / 必组装三段证据链 / 必按 4 级回退精确路由 / 必向 L1-07 暴露死循环信号）| scope#5.4.6 |
| §5.4.7 与其他 L1 交互 | L1-01 主 loop 控制流 / L1-02 4 件套生产-消费 / L1-03 WP 进出 / L1-05 skill+子 Agent 调用 / L1-06 KB 读 / L1-07 回退路由+死循环 / L1-09 持久化 / L1-10 UI 展示 | scope#5.4.7 |
| 对外 IC 契约 | IC-03 `enter_quality_loop`（L1-01→L1-04）/ IC-14 `push_rollback_route`（L1-07→L1-04）/ IC-20 `delegate_verifier`（L1-04→L1-05）/ IC-09 持久化（L1-04→L1-09）| scope §8.2 |

**本 PRD 的职责**：把 L1-04 内部拆成 **7 个 L2** + 画清楚它们之间的**架构 / 业务流 / 契约 / 验收**。

---

## 2. L2 清单（7 个）

| L2 ID | 名称 | 一句话职责 | 聚合自 BF | 核心问题 |
|---|---|---|---|---|
| **L2-01** | TDD 蓝图生成器（Master Test Plan） | 在 S3 阶段读 4 件套 + WBS，产出完整 Master Test Plan：测试金字塔分层策略 / 用例矩阵映射 AC / 覆盖率目标 / 测试环境蓝图 —— 是后续 L2-02/03/04 的总指挥与验收尺 | BF-S3-01 | "这个项目该怎么测"的唯一答卷 |
| **L2-02** | DoD 表达式编译器 | 把 4 件套里"验收条件"的自然语言转成**白名单 AST 可 eval 表达式**（如"所有 P0 用例 PASS" / "覆盖率 ≥ 80%" / "lint 无 error"）；禁止 arbitrary exec；产出机器可校验 DoD 矩阵 | BF-S3-02 | "完成的定义"怎么做到机器可校验 |
| **L2-03** | 测试用例生成器（骨架先红灯） | 按 L2-01 蓝图 + AC 矩阵批量生成各层测试骨架（单元/集成/E2E）；**生成即红灯**（未实现），驱动 S4 走 TDD；禁止桩代码撒谎绿灯 | BF-S3-03 | 用例如何"先红后绿"驱动 TDD |
| **L2-04** | 质量 Gate 编译器 + 验收 Checklist 生成器 | 读 4 件套"质量标准" + AC 清单 → 产出 `quality-gates.yaml`（覆盖率阈值/性能/安全扫描/lint）+ `acceptance-checklist.md`（用户视角勾选清单）；双产出是 S3 Stage Gate 硬性凭证 | BF-S3-04 / BF-S3-05 | 质量阈值+验收checklist怎么落 |
| **L2-05** | S4 执行驱动器 | 在 S4 阶段接管当前 WP：驱动 L1-05 调 tdd/prp-implement skill 写代码 → 等待测试绿 → 对本 WP 跑 DoD 自检（基于 L2-02 编译的表达式）→ 自检 PASS 触发 commit → 推进下一 WP；不做独立验证 | BF-S4-03 / BF-S4-04 / BF-S4-05 | WP 粒度怎么从"空"到"测试绿+自检 PASS+commit" |
| **L2-06** | S5 TDDExe Verifier 编排器 | S4 全部 WP 完成 → 进 S5：通过 IC-20 委托 L1-05 起**独立 session 的 verifier 子 Agent** 跑 TDDExe；接收 verifier 返回 → 组装**三段证据链**（existence / behavior / quality）→ 落盘 `verifier_reports/*.json`；禁止 verifier 在主 session 跑 | BF-S5-01 / BF-S5-02 | 如何让"检验"独立于"执行" |
| **L2-07** | 偏差判定 + 4 级回退路由器 | 接收 L1-07 基于 verifier_report 的结构化 verdict（PASS / FAIL-L1 轻 / FAIL-L2 中 / FAIL-L3 重 / FAIL-L4 极重）→ 精确路由到 S4 / S3 / S2 / S1；向 L1-07 暴露同级 FAIL 计数（≥ 3 升级触发 BF-E-10 死循环保护）；不自做判定 | BF-S5-03 / BF-S5-04 / BF-E-10 | verdict 到 state 切换的精确映射 |

---

## 3. L2 整体架构 · 图 A 主干质量闭环面（S3 → S4 → S5 → 回退）

```
              L1-04 Quality Loop 能力（7 个 L2）
              ════════════════════════════════════

  【S3 阶段 · TDD 蓝图生成（Gate 前全齐，硬约束 4）】
  ───────────────────────────────────────────────────

  4 件套 (from L1-02) + WBS (from L1-03)
         │
         │  IC-03 enter_quality_loop{phase=S3}
         ▼
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ L2-01 TDD 蓝图生成器                             ┃
  ┃  · 读 4 件套 + WBS                              ┃
  ┃  · 产 Master Test Plan（分层/用例矩阵/覆盖率目标）┃
  ┃  · IC-L2-01 blueprint_ready                     ┃
  ┗━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┛
        │             │                    │
        ▼             ▼                    ▼
  ┏━━━━━━━━━━━┓ ┏━━━━━━━━━━━━━━━━━━━━┓ ┏━━━━━━━━━━━━━━━━━━━━┓
  ┃ L2-02      ┃ ┃ L2-03 测试用例     ┃ ┃ L2-04 质量 Gate    ┃
  ┃ DoD 表达式 ┃ ┃  生成器             ┃ ┃  + 验收 Checklist  ┃
  ┃  编译器    ┃ ┃ · 骨架先红灯        ┃ ┃ · quality-gates    ┃
  ┃ · 白名单   ┃ ┃ · 按 AC 矩阵批量   ┃ ┃   .yaml             ┃
  ┃   AST     ┃ ┃ · 禁止假绿          ┃ ┃ · acceptance-      ┃
  ┃ · 禁 exec ┃ ┃                     ┃ ┃   checklist.md      ┃
  ┗━━━━━┳━━━━┛ ┗━━━━━━━━━┳━━━━━━━━━━━┛ ┗━━━━━━━━┳━━━━━━━━━━┛
        │                │                      │
        └────────────────┴──────────┬───────────┘
                                    ▼
                      ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                      ┃ S3 Stage Gate (BF-S3-05)   ┃
                      ┃  · 5 件齐全才能过            ┃
                      ┃  · 过 Gate → 进 S4           ┃
                      ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                    │
  ─────────────────────────────────┼────────────────────────────
  【S4 阶段 · 执行驱动（WP 循环）】 │
  ─────────────────────────────────┼────────────────────────────
                                    ▼
                    (for each WP from L1-03)
                                    │
                                    ▼
              ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
              ┃ L2-05 S4 执行驱动器                  ┃
              ┃  · 调 L1-05 起 tdd/prp-implement      ┃
              ┃  · 等代码 + 测试变绿                  ┃
              ┃  · 用 L2-02 的 DoD 表达式跑 WP 自检   ┃
              ┃  · 自检 PASS → commit                 ┃
              ┃  · IC-L2-05 next_wp / wp_done         ┃
              ┗━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┛
                             │（WP 全完 → 进 S5）
                             ▼
  ─────────────────────────────────────────────────────────────
  【S5 阶段 · TDDExe 独立验证（硬约束 2）】
  ─────────────────────────────────────────────────────────────
                             │
                             ▼
              ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
              ┃ L2-06 S5 TDDExe Verifier 编排器      ┃
              ┃  · IC-20 delegate_verifier → L1-05    ┃
              ┃  · L1-05 起独立 session               ┃
              ┃  · 接 verifier_report                  ┃
              ┃  · 组装三段证据链                      ┃
              ┃    existence / behavior / quality      ┃
              ┃  · 落盘 verifier_reports/*.json        ┃
              ┗━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┛
                             │（report → L1-07 判 verdict）
                             ▼
                 ┌───────── L1-07 Supervisor ─────────┐
                 │ 读 verifier_report 判 4 级 verdict   │
                 │ IC-14 push_rollback_route            │
                 └────────────────┬───────────────────┘
                                  │
                                  ▼
              ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
              ┃ L2-07 偏差判定 + 4 级回退路由器      ┃
              ┃  · 接收 IC-14 结构化 verdict           ┃
              ┃  · PASS → 进 S7                        ┃
              ┃  · FAIL-L1 → 回 S4 自修                ┃
              ┃  · FAIL-L2 → 回 S3 补蓝图               ┃
              ┃  · FAIL-L3 → 回 S2 改架构               ┃
              ┃  · FAIL-L4 → 回 S1 重定义问题            ┃
              ┃  · 同级 FAIL ≥ 3 → BF-E-10 升级 L1-07   ┃
              ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**关键规则**：

- **L2-01 是总指挥**：Master Test Plan 是 L2-02/03/04 的共同上游；三个下游在同一规划窗口并行产出
- **L2-05 是执行唯一接口**：S4 所有 WP 循环的启停 / 自检 / commit 都走它；不允许主 loop 绕过它自行推进
- **L2-06 是"独立验证"的唯一路径**：verifier 子 Agent 必须通过它委托 L1-05；scope §5.4 硬约束 2 禁止主 session 自跑
- **L2-07 是"verdict → state"的唯一翻译器**：接收 L1-07 判定、做回退路由映射；自己**不做判定**（scope §5.4.5 禁止）
- **S3 蓝图 + S4 执行 + S5 验证 + 回退** 四个阶段严格单向，除了 L2-07 回退路由之外不允许下游回写上游

---

## 4. L2 整体架构 · 图 B 横切 verdict 路由 & 4 级回退响应面

```
 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 1 · S5 verdict = PASS（正常完成路径）                      ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-06 组装完三段证据链 → 落盘 verifier_reports/WP-X.json          ║
 ║   → L1-07 读 report → 判 verdict=PASS                             ║
 ║   → L1-07 IC-14 push_rollback_route{verdict=PASS}                 ║
 ║   → L2-07 接收 → 路由决定 "进 S7 收尾"                             ║
 ║   → 向 L1-01 请求 state 转换（经 IC-01）                           ║
 ║   → 向 L1-09 写 "quality_loop_pass" 事件（经 IC-09）                ║
 ║   → 向 L1-10 UI 推 "Quality Loop 完成" 卡片                        ║
 ║                                                                  ║
 ║ 关键保证：Goal §3.5 硬约束 4 在此点守门 —— PASS 才解锁 S7          ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 2 · 4 级回退路由矩阵（核心）                                ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ ┌────────────┬────────────────────┬───────────────────────────┐  ║
 ║ │ verdict    │ 语义                │ 路由目标 + 动作             │  ║
 ║ ├────────────┼────────────────────┼───────────────────────────┤  ║
 ║ │ FAIL-L1 轻 │ 某 WP 小 bug / 个别 │ 回 S4（同 WP 重跑 L2-05）   │  ║
 ║ │            │ 用例挂 / lint 小问  │ · 保留 TDD 蓝图不变         │  ║
 ║ │            │ 题                  │ · 保留其他 WP 进度           │  ║
 ║ ├────────────┼────────────────────┼───────────────────────────┤  ║
 ║ │ FAIL-L2 中 │ AC 覆盖漏 / 测试用  │ 回 S3（回到 L2-01/03 补蓝图）│  ║
 ║ │            │ 例不足 / DoD 有模   │ · 保留 S4 完成的 WP 代码     │  ║
 ║ │            │ 糊点                │ · 重跑 S3 后全部 WP 重验证    │  ║
 ║ ├────────────┼────────────────────┼───────────────────────────┤  ║
 ║ │ FAIL-L3 重 │ 架构级选择错 / 4 件│ 回 S2（L1-02 重做规划/架构）  │  ║
 ║ │            │ 套与真实差距大      │ · L1-04 本轮 Quality Loop     │  ║
 ║ │            │                     │   彻底终止等待 S2 新产物      │  ║
 ║ ├────────────┼────────────────────┼───────────────────────────┤  ║
 ║ │ FAIL-L4 极 │ 问题本身不成立 / 目│ 回 S1（L1-02 重新启动）       │  ║
 ║ │ 重         │ 标认知偏差           │ · 全部产出置为"待弃/重做"     │  ║
 ║ └────────────┴────────────────────┴───────────────────────────┘  ║
 ║                                                                  ║
 ║ 硬约束：                                                          ║
 ║  · L2-07 **不自做判定**（scope §5.4.5）：收到 verdict 后只做路由   ║
 ║  · 同级 FAIL 计数 ≥ 3 → 向 L1-07 触发 BF-E-10 死循环升级            ║
 ║  · 所有路由都需经 IC-01 请求 L1-01 做 state 切换，不得私自改 state ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 3 · DoD 表达式安全盒（scope §5.4.4 硬约束 3）               ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-02 接收自然语言 DoD 条款（from 4 件套"验收条件"）                ║
 ║   → 识别谓词（覆盖率 / lint / 用例通过 / 性能指标等）                ║
 ║   → 比对**白名单谓词表**（PM-05 机器可校验）                         ║
 ║     · 命中 → 转 AST 节点                                           ║
 ║     · 未命中 → 拒绝编译 + 告警 "非白名单谓词"                       ║
 ║   → 组合 AST（and / or / 比较 / 阈值）                              ║
 ║   → 校验 AST 无 arbitrary exec（无 Call/Exec/import/os 等节点）     ║
 ║   → 通过 → 固化为 DoD 矩阵 dod-expressions.yaml                    ║
 ║                                                                  ║
 ║ L2-05 在 WP 自检时 eval DoD 表达式：                                ║
 ║   · 在受限 evaluator 里跑（仅访问白名单数据源：测试结果、覆盖率 %、 ║
 ║     lint 报告等）                                                  ║
 ║   · 返 bool（PASS/FAIL）+ 失败原因                                 ║
 ║                                                                  ║
 ║ 硬约束：任何时刻 DoD eval 都**不调 shell / subprocess / exec**     ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 4 · verifier 独立 session 委托（硬约束 2）                  ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-06 组装 verifier 工作包：                                      ║
 ║   · S3 蓝图（Master Test Plan + DoD 矩阵 + 用例骨架）                ║
 ║   · S4 产出物（代码 commit 哈希 / 测试结果快照）                    ║
 ║   · AC 清单                                                       ║
 ║   → IC-20 delegate_verifier → L1-05                               ║
 ║   → L1-05 起**独立 session** 子 Agent（全新 context，禁止复用主     ║
 ║     Agent 记忆）                                                  ║
 ║   → verifier 子 Agent 跑：                                         ║
 ║     · existence 段：产出物是否真的存在（file / commit / deploy）     ║
 ║     · behavior 段：测试结果是否真的是声称的那个                     ║
 ║     · quality 段：DoD 矩阵是否全部 PASS（基于独立 eval）             ║
 ║   → 返 verifier_report.json 给 L2-06                              ║
 ║   → L2-06 落盘 + 转交 L1-07 判 verdict                             ║
 ║                                                                  ║
 ║ 降级：若 L1-05 独立 session 委托失败（API 限流 / 超时）              ║
 ║   → 记 soft-drift 软红线（经 L1-07）                               ║
 ║   → **禁止降级到主 session 跑简化 DoD**（违反硬约束 2）              ║
 ║   → 等待 backoff 后重试，仍失败 → 升级 BLOCK 由用户介入              ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 5 · 死循环保护（BF-E-10 触发通路）                          ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-07 维护"同级 FAIL 计数"（按 WP id × verdict 级别）：              ║
 ║   · 第 1 次 FAIL-L1 → 正常回退 S4                                  ║
 ║   · 第 2 次 FAIL-L1 → 正常回退 S4 + 记一次 WARN                    ║
 ║   · 第 3 次 FAIL-L1 → 触发 BF-E-10 死循环保护                      ║
 ║     → 向 L1-07 报告 "loop_exceeded: wp=X, level=L1, count=3"        ║
 ║     → L1-07 判升级到 BLOCK（硬暂停）                                ║
 ║     → L1-10 UI 弹告警 "Quality Loop 死循环，请人介入"                ║
 ║     → 等用户决策：继续 / 换方案 / 放弃 WP                            ║
 ║                                                                  ║
 ║ 同理：FAIL-L2 / FAIL-L3 / FAIL-L4 各独立计数；同一级累计 3 次触发    ║
 ╚══════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════╗
 ║ 响应面 6 · 测试用例"先红灯"硬性语义（scope §5.4 隐含）              ║
 ╠══════════════════════════════════════════════════════════════════╣
 ║                                                                  ║
 ║ L2-03 生成用例骨架时：                                              ║
 ║   · 每个用例函数体 = 空断言或 assertFail("未实现")                  ║
 ║   · 禁止 pass / return True / skip / mock 全通过                   ║
 ║   · 产出即 "所有用例红"                                             ║
 ║   → S4 L2-05 驱动 skill 写代码时，逐个用例从红变绿                  ║
 ║   → 每次 commit 前 L2-05 对比"未绿用例数"是否单调递减                ║
 ║     · 增加（之前绿的变红）→ 违规，立刻回滚 commit                   ║
 ║                                                                  ║
 ║ 保证：TDD 顺序严格（先红 → 实现 → 变绿），禁止"桩代码撒谎绿灯"      ║
 ╚══════════════════════════════════════════════════════════════════╝
```

---

## 5. L2 间业务流程（9 条）

### 流 A · S3 TDD 蓝图一次完整生成（正常路径，最高频入口）

```
L1-01 决策 = 进 S3 TDD 规划
    ↓
L1-01 → IC-03 enter_quality_loop{phase=S3, 4 件套路径, WBS 路径}
    ↓
L2-01 TDD 蓝图生成器启动：
   · 读 4 件套（需求 / 目标 / AC / 质量标准）
   · 读 WBS 拓扑
   · 推理测试金字塔分层（单元 / 集成 / E2E）
   · 为每条 AC 分配至少 1 个用例（100% AC 覆盖）
   · 产 docs/testing/master-test-plan.md
    ↓
广播 IC-L2-01 blueprint_ready 给下游 L2-02 / L2-03 / L2-04
    ↓
【并行】
  ├─ L2-02 DoD 表达式编译器：
  │   · 读 4 件套"验收条件"自然语言条款
  │   · 比对白名单谓词表
  │   · 未命中 → 回查 / 要求 L1-02 澄清
  │   · 命中 → 组装 AST → 校验无 exec → 固化 dod-expressions.yaml
  │
  ├─ L2-03 测试用例生成器：
  │   · 按 master-test-plan 分层 × AC 矩阵生成用例骨架
  │   · 每函数体空断言（先红灯）
  │   · 产 tests/generated/unit/*.py + integration/*.py + e2e/*.py
  │
  └─ L2-04 质量 Gate + Checklist 生成器：
      · 读 4 件套"质量标准"转 quality-gates.yaml（覆盖率/性能/安全）
      · 读 AC 转 acceptance-checklist.md（用户勾选清单）
    ↓
全部完成 → L2-01 回调 L1-01 "S3 产出齐全"
    ↓
L1-02 触发 BF-S3-05 Stage Gate（S3 末 Gate）
    ↓
用户审核 Go → 进 S4
用户审核 No-Go → 返工 L2-01/02/03/04 指定部分
```

### 流 B · S4 单个 WP 执行一轮（WP 级 mini-pipeline）

```
L1-03 IC-02 get_next_wp → 返 WP-X（定义：goal / DoD / 依赖 / 工时）
    ↓
L1-01 → IC-03 enter_quality_loop{phase=S4, wp=WP-X}
    ↓
L2-05 S4 执行驱动器接管 WP-X：
   1. 读 WP-X.DoD 对应的 DoD 表达式（from L2-02 编译产物）
   2. 读 WP-X 对应的红灯用例（from L2-03 生成产物）
   3. 调 L1-05 IC-04 invoke_skill{skill=tdd 或 prp-implement, context=WP-X}
    ↓
L1-05 起 skill → 写代码 → 跑测试
   · 若测试未绿 → skill 自循环（TDD 小循环）
   · 测试变绿 → skill 回调
    ↓
L2-05 接收"skill 完成"回调：
   1. 对比"未绿用例数"单调递减（响应面 6）
   2. eval WP-X DoD 表达式（在 L2-02 安全盒里）
      · PASS → 继续
      · FAIL → 记失败原因 → 回到步骤 3 重跑 skill（WP 内自修 ≤ 3 次）
   3. 自检 PASS → commit（git WP 粒度）
   4. 写事件 wp_done{wp_id, commit_hash, test_snapshot}（经 IC-09 → L1-09）
    ↓
L2-05 回调 L1-01 "WP-X done"
    ↓
L1-01 取下一 WP（回到流开头）
    ↓
全部 WP 完成 → L2-05 报告 "S4 done"
    ↓
L1-01 决策 = 进 S5
```

### 流 C · S5 TDDExe 独立验证一次完整组装

```
L1-01 → IC-03 enter_quality_loop{phase=S5}
    ↓
L2-06 S5 Verifier 编排器启动：
   1. 汇总 S3 蓝图（M-Test-Plan + DoD + 用例）
   2. 汇总 S4 产出（所有 WP 的 commit 哈希 + 测试快照）
   3. 汇总 AC 清单（from L1-02）
   4. 组装 verifier 工作包
    ↓
L2-06 → IC-20 delegate_verifier{工作包} → L1-05
    ↓
L1-05 起**独立 session 的 verifier 子 Agent**（全新 context / 禁继承主）
    ↓
verifier 子 Agent 工作：
   · existence 段：
     · 每个声称的产出物实际存在？file / commit / deploy_url
     · 每个 AC 条款对应产出是否真的生成
   · behavior 段：
     · 按 L2-03 用例独立跑一遍（不信任主 agent 声称的绿）
     · 采集行为证据：输出 / log / api 响应
   · quality 段：
     · 独立 eval L2-02 DoD 表达式
     · 独立跑覆盖率 / 性能 / 安全扫描
    ↓
verifier 回 verifier_report.json 给 L2-06（含三段）
    ↓
L2-06 组装三段证据链：
   · 把报告三段规整为 {existence, behavior, quality} 三键 JSON
   · 落盘 verifier_reports/<session_id>.json（经 IC-09）
   · 向 L1-07 推送 report（订阅式，经事件总线）
    ↓
L1-07 读 report → 判 4 级 verdict → IC-14 push_rollback_route → L2-07
```

### 流 D · 4 级回退路由（L2-07 精确映射 verdict → state）

```
L2-07 收 IC-14 push_rollback_route{verdict, reason, wp_id}
    ↓
L2-07 查表映射：
  ┌────────────┬───────────────────────────────────────┐
  │ verdict    │ 路由动作                               │
  ├────────────┼───────────────────────────────────────┤
  │ PASS       │ 请求 L1-01 进 S7（经 IC-01）            │
  │ FAIL-L1 轻 │ 请求 L1-01 回 S4 重跑 WP-X              │
  │ FAIL-L2 中 │ 请求 L1-01 回 S3 补蓝图（指定缺项）      │
  │ FAIL-L3 重 │ 请求 L1-01 回 S2 重规划                 │
  │ FAIL-L4 极 │ 请求 L1-01 回 S1 重定义                 │
  └────────────┴───────────────────────────────────────┘
    ↓
L2-07 更新"同级 FAIL 计数器"：
   · key=(wp_id, level) → count++
   · count ≥ 3 → 向 L1-07 触发 BF-E-10 死循环升级（流 E）
   · 否则按表执行回退
    ↓
L2-07 → IC-01 request_state_transition{target_state}
L2-07 → IC-09 append_event "rollback_routed"（落盘）
L2-07 → UI 推"回退执行中"卡片
    ↓
L1-01 执行 state 转换 → 对应阶段 L1 / L2 继续
```

### 流 E · 死循环保护触发（BF-E-10）

```
L2-07 检测到某 wp_id 的某 level 计数达 3
    ↓
L2-07 → IC-13（经 L1-07）push_suggestion{level=BLOCK, reason=loop_exceeded}
    ↓
L1-07 升级为硬暂停 → 广播 halt_soft 给 L1-01
    ↓
L1-01 停 tick
    ↓
L1-10 UI 弹告警 "Quality Loop 死循环：WP-X 连续 3 次 FAIL-L1；请介入"
   · 选项：A) 继续尝试（重置计数器）
   · 选项：B) 换方案（跳到 S3 重设计 WP-X）
   · 选项：C) 放弃 WP-X（标记为 skip，影响项目 DoD）
    ↓
用户选择 → L2-07 按选择处置 → 恢复循环或阻断
```

### 流 F · DoD 表达式编译失败回查 4 件套（BF-S3-02 异常分支）

```
L2-02 读 4 件套"验收条件" → 某条款无法映射白名单谓词
    ↓
L2-02 登记"未编译条款" → 回查路径：
   1. 找条款原始出处（需求 / AC 哪一行）
   2. 生成"澄清请求"：请补说明或选白名单同义词
    ↓
L2-02 → IC-13（经 L1-07）push_suggestion{level=INFO, reason=dod_unmappable}
   · 转给 L1-02 / 用户介入澄清
    ↓
用户（经 UI）更新 4 件套 → 回 L2-02 重编译
    ↓
编译通过 → 正常进 S3 Gate
    ↓
若连续 3 次澄清仍失败 → 升级为"规划阶段问题"（FAIL-L3 语义）→ 回 S2
```

### 流 G · verifier 委托失败（硬约束 2 保底）

```
L2-06 → IC-20 delegate_verifier → L1-05
    ↓
L1-05 起独立 session 失败：
   · 原因 1：API 限流（429）
   · 原因 2：子 Agent 超时
   · 原因 3：独立 session 上下文装载失败
    ↓
L2-06 策略：
   · 等 backoff 重试（由 L1-01 的 BF-E-04 限流降级支撑）
   · 重试成功 → 正常流 C
   · 连续 3 次失败 → 升级 L1-07 BLOCK
    ↓
**绝对不允许降级到主 session 跑简化 DoD**（scope §5.4.5 硬约束 2 + 禁 2）
    ↓
UI 提示 "verifier 不可用，已暂停 Quality Loop；请处理后重试"
```

### 流 H · S3 Stage Gate 过 / 不过 Go/No-Go（BF-S3-05）

```
S3 产出齐全 → L1-02 触发 BF-S3-05 Stage Gate
    ↓
L1-10 推待审卡片 "S3 产出 5 件：Master Test Plan + DoD + 用例骨架 +
              quality-gates.yaml + acceptance-checklist.md，请 Go/No-Go"
    ↓
用户审核：
   · Go → L1-02 发事件 stage_gate_s3_passed → L1-04 进 S4 流 B
   · No-Go（带修改意见）→ 意见分派到对应 L2：
     · 意见指向蓝图分层 → 回 L2-01 重做 Master Test Plan
     · 意见指向 DoD 条款 → 回 L2-02 重编译
     · 意见指向用例覆盖 → 回 L2-03 重生成骨架
     · 意见指向质量阈值 → 回 L2-04 调 quality-gates.yaml
   · 修改 → 再次过 Gate
    ↓
Gate 连续 2 次 No-Go → 升级 L1-07 INFO（规划阶段异常信号）
```

### 流 I · 三段证据链与 L1-10 UI 的对应展示

```
L2-06 落盘 verifier_reports/<session>.json
    ↓
事件 verifier_report_ready 经 IC-09 → L1-09 → 订阅推 L1-10
    ↓
L1-10 "Verifier 证据链" tab 渲染：
   · 时间轴节点：session 开始 / existence / behavior / quality / 结束
   · 每段展开：
     · existence：产出物清单 + 存在性 ✅/❌ 标记 + 路径/哈希
     · behavior：独立跑的测试结果对照表（主 agent 声称 vs verifier 实测）
     · quality：DoD 表达式逐条 eval 结果（PASS/FAIL + 理由）
   · 底部：verdict 标识（PASS / FAIL-L1~L4）+ "下一步路由"文字
    ↓
用户点"为什么 verdict 是 FAIL-L2" → 展开 L1-07 判定理由 + 相关 verifier 证据高亮
```

---

## 6. IC-L2 契约清单（11 条 · 一句话 + 方向）

| ID | 调用方 | 被调方 | 方法（一句话描述） | 方向 |
|---|---|---|---|---|
| **IC-L2-01** | L2-01 蓝图生成器 | L2-02 / L2-03 / L2-04 | 广播 `blueprint_ready`（携带 Master Test Plan 路径 + AC 矩阵） | 广播 · 并行触发下游 |
| **IC-L2-02** | L2-02 DoD 编译器 | L2-05 执行驱动器 | 提供 DoD 表达式安全盒（`eval_expression(expr_id, data_sources)` 接口），受限 evaluator | 同步 · 请求-响应 |
| **IC-L2-03** | L2-03 用例生成器 | L2-05 执行驱动器 | 提供"未绿用例清单"查询 + 单调递减校验接口 | 同步 · 读查询 |
| **IC-L2-04** | L2-05 执行驱动器 | L2-02 / L2-03 / L2-04 | WP 自检：对本 WP 涉及的 DoD 表达式 eval + 用例绿灯检查 + 质量阈值检查 | 同步 · 复合 |
| **IC-L2-05** | L2-05 执行驱动器 | L1-01 主 loop | 回调 "WP-X done"（经 IC-03 通路），请求调度下一 WP 或进 S5 | 异步 · 回调 |
| **IC-L2-06** | L2-06 验证编排器 | L1-05 Skill+子 Agent | 经 IC-20 委托 verifier 子 Agent 独立 session 跑 TDDExe | 异步 · 委托 |
| **IC-L2-07** | L2-06 验证编排器 | L1-09 审计 | 把 verifier_report 三段证据链落盘（经 IC-09 append_event） | 同步 · 落盘 |
| **IC-L2-08** | L2-06 验证编排器 | L1-07 Supervisor | 推送 report 完成事件供其判 verdict（订阅式） | 异步 · push |
| **IC-L2-09** | L1-07 Supervisor | L2-07 回退路由器 | 经 IC-14 push_rollback_route 传 4 级 verdict | 同步 · 请求-响应 |
| **IC-L2-10** | L2-07 回退路由器 | L1-01 主 loop | 经 IC-01 request_state_transition 请求回到目标 state | 同步 · 请求-响应 |
| **IC-L2-11** | L2-07 回退路由器 | L1-07 Supervisor | 同级 FAIL 计数 ≥ 3 → 升级 BF-E-10（经 IC-13 push_suggestion BLOCK） | 异步 · 升级 |

---

## 7. L2 定义模板（每 L2 必含 9 小节）

每个 L2 详细定义（§8-§14）严格按以下 9 小节模板。**严禁 §X.10**（L3 实现设计迁到 `docs/3-1-Solution-Technical/L1-04/tech-design.md`）。

| # | 小节 | 内容 |
|---|---|---|
| 1 | 职责 + 锚定 | 一句话职责 + Goal / BF / scope §5.4 锚点 |
| 2 | 输入 / 输出 | 输入事件 + 方法调用（文字描述，非 schema） / 产出事件 + 方法调用 |
| 3 | 边界 | In-scope / Out-of-scope / 边界规则 |
| 4 | 约束 | 业务模式引用 + 硬约束文字清单 + 性能约束文字清单 |
| 5 | 🚫 禁止行为 | 明确清单（5-8 条） |
| 6 | ✅ 必须职责 | 明确清单（5-8 条） |
| 7 | 🔧 可选功能职责 | 3-5 条 |
| 8 | 与其他 L2 / L1 交互 | IC-L2-XX 契约表（一句话 + 方向，非 schema）|
| 9 | 🎯 交付验证大纲 | Given-When-Then 正向 / 负向 / 集成 / 性能 验收场景 |

---

## 8. L2-01 · TDD 蓝图生成器（Master Test Plan） 详细定义

### 8.1 职责 + 锚定

**一句话职责**：在 S3 阶段读 L1-02 产出的 4 件套 + L1-03 产出的 WBS 拓扑，推导完整的测试金字塔分层策略（单元 / 集成 / E2E 的责任边界 + 用例配比），为每条 AC 映射至少 1 个用例，产出 `docs/testing/master-test-plan.md` —— 是 S3 阶段下游 L2-02 / L2-03 / L2-04 的**总指挥与共同输入**，也是 S5 TDDExe 独立验证的**验收尺**。

**上游锚定**：
- Goal §2.2 五大纪律"检验"（独立验证的前提是先有明确的蓝图）
- Goal §4.1 "真完成质量达标率 ≥ 95%"（没有蓝图 → 无法判断什么叫达标）
- PM-05 Stage Contract 机器可校验（蓝图是 S3 Gate 的核心凭证）
- scope §5.4.1 职责"S3 阶段：生成 Master Test Plan"
- scope §5.4.4 硬约束 4"TDD 蓝图必须在 S4 前全部生成"
- BF-S3-01 Master Test Plan 生成流

**下游服务**：
- L2-02 DoD 表达式编译器（消费 AC 矩阵）
- L2-03 测试用例生成器（消费分层策略 + 用例清单）
- L2-04 质量 Gate 编译器（消费覆盖率目标 + 分层配比）
- S3 Stage Gate（BF-S3-05）硬凭证之一
- L2-06 verifier 编排器（作为 verifier 工作包的蓝图输入）

---

### 8.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **4 件套文档**：from L1-02，包括：
  - 需求文档（业务问题 + 目标用户）
  - 目标文档（量化指标 + 非目标边界）
  - AC 清单（可验收条款列表）
  - 质量标准文档（覆盖率目标 / 性能指标 / 合规要求）
- **WBS 拓扑**：from L1-03，所有 WP 的清单 + 依赖关系 + 架构层归属（前端/后端/数据/接口）
- **触发信号**：`enter_quality_loop{phase=S3}` 由 L1-01 发起（经 IC-03）
- **KB 查询结果**：from L1-06（可选）—— 读历史相似项目的测试分层最佳实践 recipe

**输出（文字描述）**：

- **`docs/testing/master-test-plan.md`**（产品级，必产）：
  - 测试金字塔分层：每层的责任边界 + 适用 AC 类型 + 预期用例数配比
  - AC → 用例映射表：每条 AC 至少映射 1 个用例（100% 覆盖硬性）
  - 按 WP 分组的用例清单索引
  - 覆盖率目标（行 / 分支 / AC）+ 测试环境蓝图（mock 策略 / fixture 设计 / 数据准备）
  - 优先级标注（P0 必跑 / P1 建议 / P2 可选）
- **blueprint_ready 事件**：经 IC-L2-01 广播给 L2-02 / L2-03 / L2-04，携带 master-test-plan 路径 + AC 矩阵快照

---

### 8.3 边界

**In-scope（本 L2 做什么）**：

1. 读 4 件套 + WBS 作为单一输入源
2. 推导测试金字塔（哪些 AC 归哪层）
3. 为每条 AC 至少分配 1 个用例槽位（只定义，不生成代码 → L2-03）
4. 设定覆盖率目标（作为 L2-04 质量 Gate 的上游输入）
5. 产出 master-test-plan.md 产品级文档
6. 广播 blueprint_ready 事件给并行下游
7. 蓝图不全 / AC 有歧义时回查澄清（走 IC-13 INFO 通知 L1-07 / L1-02）
8. 记录 AC 覆盖率（100% 硬性）并在蓝图中展示

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不编译 DoD 表达式 → L2-02
- ❌ 不生成测试代码骨架 → L2-03
- ❌ 不编译 quality-gates.yaml / acceptance-checklist.md → L2-04
- ❌ 不驱动 S4 执行 → L2-05
- ❌ 不做独立验证 → L2-06
- ❌ 不做 verdict 判定 / 回退 → L2-07 + L1-07
- ❌ 不管 WBS 本身拓扑编排 → L1-03
- ❌ 不管 4 件套内容合法性 → L1-02

**边界规则**：

- 本 L2 是 S3 阶段的**唯一入口**；所有"怎么测"的总答卷只有它出；下游 L2-02/03/04 不得独立解释 4 件套
- AC 覆盖率硬性 100%：任一 AC 未被至少 1 个用例覆盖 → 蓝图不合格 / 不广播 blueprint_ready
- 产出的 master-test-plan 是**产品级文档**（用户可读），不是代码或中间态
- 蓝图一旦 S3 Gate 通过进入 S4 → **冻结**；S4 阶段若需改蓝图 → 必经 FAIL-L2 回退机制（经 L2-07）

---

### 8.4 约束

**业务模式引用**：
- **PM-05 Stage Contract 机器可校验**：master-test-plan 的 AC 覆盖率是首个机器可校验点
- **PM-10 单一事实源**：蓝图事件经 IC-09 落盘，不在 md 之外另存副本

**硬约束（文字清单）**：

1. **必 S4 前全齐**（scope §5.4.4 硬约束 4）：master-test-plan + DoD + 用例骨架 + quality-gates + acceptance-checklist 五件必须都在 S3 Gate 前全部完成，不允许"边执行 S4 边补"
2. **AC 覆盖率硬性 100%**：任一 AC 未映射到至少 1 个用例 → 蓝图拒绝产出
3. **蓝图冻结**：S3 Gate 后禁止静默修改；必经 L2-07 FAIL-L2 回退才能重建
4. **纯文本蓝图**：master-test-plan.md 是纯文字产物（md 表格 + 分层描述），不得嵌入可执行代码
5. **输入源只有两个**：4 件套 + WBS；禁止 L2-01 自行臆测需求（若 4 件套缺 → 走澄清回路而非猜）

**性能约束（文字清单）**：

- 蓝图生成耗时 ≤ 3 分钟（对 100 条 AC 规模的项目）
- 蓝图 md 文档 ≤ 1MB（超标 → WBS 过碎，倒逼 L1-03 重规划）
- blueprint_ready 广播延迟 ≤ 1 秒（保证 L2-02/03/04 可以及时并行起跑）

---

### 8.5 🚫 禁止行为

- 🚫 **禁止**在 4 件套不全 / AC 有歧义时强行生成蓝图（必须回澄清）
- 🚫 **禁止**漏映射任一 AC（覆盖率硬性 100%）
- 🚫 **禁止**在 S3 Gate 后静默修改 master-test-plan（必经 FAIL-L2 回退）
- 🚫 **禁止**直接生成测试代码（那是 L2-03 的事）
- 🚫 **禁止**自主改 WBS（只消费，不修改；要改 → 推建议给 L1-03）
- 🚫 **禁止**把用户的自然语言 AC 原文作为用例骨架（需重构为"测试意图"描述）
- 🚫 **禁止**跳过测试金字塔分层直接按 WP 切（分层独立于 WP 切分，是正交维度）

---

### 8.6 ✅ 必须职责

- ✅ **必须**读取完整 4 件套 + WBS 后再开始蓝图推导（不得部分输入开干）
- ✅ **必须**为 4 件套中每条 AC 至少分配 1 个用例槽位并在蓝图中声明
- ✅ **必须**在蓝图中明确测试金字塔三层（单元/集成/E2E）各自的责任边界
- ✅ **必须**标注每个用例槽位的优先级（P0/P1/P2）
- ✅ **必须**产出覆盖率目标（给 L2-04 作为 quality-gates.yaml 的输入）
- ✅ **必须**在蓝图完成后广播 blueprint_ready（给 L2-02/03/04 并行触发）
- ✅ **必须**在 AC 存在歧义时触发澄清（不得静默假设）
- ✅ **必须**把蓝图文档作为 S3 Stage Gate 的硬凭证之一推送给 BF-S3-05

---

### 8.7 🔧 可选功能职责

- 🔧 读 L1-06 知识库的"测试分层 recipe"提升蓝图质量（可选增强）
- 🔧 对比历史相似项目蓝图，为当前项目建议用例数基线（可选参考）
- 🔧 输出蓝图 diff 视图（若是 FAIL-L2 回退后的新版蓝图，展示与旧版差异）
- 🔧 蓝图可读性预览（L1-10 UI 查看器友好的 md 样式）
- 🔧 自动侦测 AC 之间的逻辑冲突（如"A 必须 < 10s" vs"A 的依赖步骤需 > 15s"），发 INFO 建议澄清

---

### 8.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-03（接收）| L1-01 | 控制流 ← | 接 enter_quality_loop{phase=S3}，启动蓝图生成 |
| IC-L2-01（发起） | L2-02 / L2-03 / L2-04 | 广播 → | blueprint_ready + master-test-plan 路径 + AC 矩阵 |
| IC-09（发起） | L1-09 | 持久化 → | 蓝图生成进度 / 完成事件落盘 |
| IC-13（发起） | L1-07（经事件） | 建议 → | AC 歧义 / 4 件套缺项时发 INFO 澄清建议 |
| IC-16（发起，经 L1-02） | L1-10 | 输出 → | master-test-plan.md 作为 S3 Gate 待审产出物 |
| IC-06（发起） | L1-06 KB | 读 ← | 查"测试分层 recipe"（可选增强） |

---

### 8.9 🎯 交付验证大纲

**正向场景 1 · 一次蓝图完整生成**
- Given：4 件套全齐 + WBS 10 个 WP + 50 条 AC
- When：收到 enter_quality_loop{phase=S3}
- Then：
  - 3 分钟内产出 master-test-plan.md
  - AC 覆盖率 = 100%（50 条 AC 全部有用例槽位）
  - 测试金字塔三层都有明确责任边界描述
  - 广播 blueprint_ready 给 L2-02/03/04 延迟 ≤ 1 秒

**正向场景 2 · 蓝图作为 S3 Gate 凭证**
- Given：master-test-plan.md 已生成 + 其他四件（DoD / 用例 / gates / checklist）也齐
- When：L1-02 发起 BF-S3-05 Stage Gate
- Then：蓝图文档作为待审产出物被正确展示在 L1-10 UI

**负向场景 3 · AC 覆盖率不达标**
- Given：50 条 AC 中 1 条被漏映射
- When：生成蓝图
- Then：
  - 蓝图不合格 → 拒绝产出 master-test-plan.md
  - 广播 blueprint_ready 不触发
  - 发 INFO 建议指出漏的 AC

**负向场景 4 · 4 件套缺失触发澄清**
- Given：质量标准文档为空
- When：L2-01 读输入
- Then：
  - 不强行生成蓝图
  - 发 push_suggestion{INFO, reason=missing_quality_standard}
  - 等待 L1-02 / 用户补齐后重跑

**集成场景 5 · 与 L2-02/03/04 并行下游**
- Given：blueprint_ready 广播已发
- When：L2-02/03/04 并行启动
- Then：三者都能读到 master-test-plan 的相同 AC 矩阵

**集成场景 6 · FAIL-L2 回退后重建蓝图**
- Given：verdict=FAIL-L2，L2-07 路由回 S3
- When：L2-01 重新启动
- Then：
  - 生成新蓝图（可与旧版本有 diff）
  - 广播新 blueprint_ready
  - 事件总线记录"蓝图重建原因 = L1-07 指示补 AC-X 漏覆盖"

**性能场景 7 · 大规模 AC（100+）**
- Given：500 条 AC + 30 个 WP
- When：蓝图生成
- Then：
  - 5 分钟内完成（可放宽）
  - 蓝图 md ≤ 1MB
  - AC 覆盖率仍 100%

---

## 9. L2-02 · DoD 表达式编译器 详细定义

### 9.1 职责 + 锚定

**一句话职责**：把 4 件套中"验收条件"的自然语言条款（如"所有 P0 用例必须 PASS"、"行覆盖率不低于 80%"、"lint 无 error"）转换为**白名单谓词 AST 表达式**（机器可 eval），固化到 `docs/testing/dod-expressions.yaml`；并为 L2-05 在 S4 WP 自检时提供**受限 evaluator**（仅访问白名单数据源，禁止任何 arbitrary exec / subprocess / shell）；是 PM-05 "Stage Contract 机器可校验"纪律的落地工程。

**上游锚定**：
- Goal §2.2 五大纪律"检验"：检验必须能机器自动化，自然语言不够用
- Goal §3.5 硬约束（隐含）：DoD 必须是可 eval 的契约，不是口头承诺
- PM-05 Stage Contract 机器可校验 —— 本 L2 是 PM-05 在 L1-04 内的唯一工程化入口
- scope §5.4.1 职责"S3 阶段：生成 DoD 表达式"
- scope §5.4.4 硬约束 3"verifier 独立 session"中的 DoD 白名单 AST 前置
- scope §5.4.5 禁 3"禁止 DoD 表达式含 arbitrary exec"
- BF-S3-02 DoD 表达式编译流

**下游服务**：
- L2-05 S4 执行驱动器（WP 自检时 eval DoD 表达式）
- L2-06 S5 验证编排器（验 quality 段时独立 eval 同一套 DoD）
- verifier 子 Agent（消费同一份 dod-expressions.yaml，在独立 session 独立 eval）
- L1-07 Supervisor（判 verdict 时读表达式失败原因）

---

### 9.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **4 件套的"验收条件"章节**：from L1-02，自然语言条款清单
- **master-test-plan 的 AC 矩阵**：from L2-01（blueprint_ready 事件）—— 用于交叉校验"每条 DoD 表达式都能映回至少 1 条 AC"
- **白名单谓词表**：本 L2 维护的固化词典（文字描述；具体元素和语法迁 3-1 技术设计），例如：
  - 覆盖率类：行覆盖率 / 分支覆盖率 / AC 覆盖率
  - 测试结果类：用例 PASS 数 / FAIL 数 / SKIP 数 / 某优先级全 PASS
  - 静态检查类：lint 告警级别 / 类型检查错误数 / 安全扫描高危数
  - 性能类：P95 延迟 / 吞吐 QPS / 内存峰值
  - 产出物类：file 存在 / commit 存在 / deploy_url 可访问
- **eval 请求**：来自 L2-05 / L2-06 / verifier 子 Agent，携带表达式 id + 数据源快照

**输出（文字描述）**：

- **`docs/testing/dod-expressions.yaml`**（产品级，必产）：按 WP × 表达式 id 组织的 DoD 矩阵；每条表达式含语义说明 + AST 结构文字描述 + 来源 AC 反向引用
- **eval 返回**：`{pass: bool, reason: str, evidence_snapshot}`（文字；每项失败原因清晰可读）
- **编译失败报告**：对未映射白名单的条款生成"不可编译清单"，触发回查 4 件套（流 F）

---

### 9.3 边界

**In-scope（本 L2 做什么）**：

1. 读 4 件套"验收条件"自然语言条款
2. 分词 + 谓词识别（比对白名单）
3. AST 组装（and / or / 比较 / 阈值）+ 无 exec 节点校验
4. 固化 dod-expressions.yaml 产出
5. 在 L2-05 / L2-06 / verifier 请求时提供**受限 evaluator**（白名单数据源访问）
6. 未命中白名单 → 触发"澄清请求"回查 L1-02（流 F）
7. 维护白名单谓词词典（随业务演进扩展，但所有扩展必须经过安全评审走 3-1 tech-design）
8. AST 语法校验（无模糊语义 / 无自引用循环）

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不生成测试代码 → L2-03
- ❌ 不定义覆盖率阈值具体值 → L2-04
- ❌ 不执行测试 → L2-05 / verifier
- ❌ 不做 verdict 判定 → L1-07
- ❌ 不维护数据源具体采集逻辑 → L2-05（采集测试结果）/ L1-05（通过 skill 采集扫描结果）
- ❌ 不解释 4 件套内容合法性 → L1-02
- ❌ 不做白名单谓词的运行时动态扩展（防止运行时污染）→ 所有扩展走离线 tech-design

**边界规则**：

- 本 L2 是 DoD 机器可校验的**唯一工程点**；任何 L 想跳过它直接 eval 自然语言 → 破坏 PM-05
- **白名单是硬红线**：任何未登记谓词 → 编译失败；不允许"先过再登记"
- evaluator 运行在**受限沙盒**（文字描述语义）：只能读取白名单数据源 snapshot，不能访问文件系统 / 网络 / shell
- dod-expressions.yaml 是**纯配置产物**（PRD 只说"是 yaml 格式的矩阵"，具体结构迁 3-1）

---

### 9.4 约束

**业务模式引用**：
- **PM-05 Stage Contract 机器可校验**：本 L2 是 PM-05 在 L1-04 的物化点
- **PM-10 单一事实源**：DoD 定义只在 dod-expressions.yaml 里，禁止在代码里写"第二份 DoD"

**硬约束（文字清单）**：

1. **白名单硬红线**（scope §5.4.5 禁 3）：任何含 arbitrary exec / Call / subprocess / shell / eval（python 动态）/ import / os / sys 节点的表达式 → 拒绝编译
2. **eval 必在受限 evaluator**：L2-05 / L2-06 / verifier 调 eval → 只能访问白名单数据源；访问外的 → 抛 SecurityError
3. **S4 前编译完成**（scope §5.4.4 硬约束 4）：dod-expressions.yaml 是 S3 Gate 五件套之一
4. **每条表达式必可反查 AC**：dod-expressions.yaml 每个条目必须带来源 AC 的引用；反查不到 → 编译失败
5. **eval 无副作用**：不写文件 / 不改内存外状态 / 不广播事件（广播由调用方做）

**性能约束（文字清单）**：

- 单次编译（50 条 DoD 条款规模）≤ 60 秒
- eval 单个表达式 ≤ 100 毫秒（给 L2-05 / verifier 频繁调用留余地）
- dod-expressions.yaml ≤ 500KB（超出 → WP 切分过碎）

---

### 9.5 🚫 禁止行为

- 🚫 **禁止**包含任何可执行动作节点（exec / subprocess / shell / import / 动态 eval）
- 🚫 **禁止**未登记的谓词绕过白名单"先过再补"
- 🚫 **禁止** evaluator 访问文件系统 / 网络 / 环境变量等白名单外资源
- 🚫 **禁止**在 S4 执行期间修改 dod-expressions.yaml（必经 FAIL-L2 回退）
- 🚫 **禁止**不经来源 AC 反查地写表达式（要求可追溯到原始需求）
- 🚫 **禁止** evaluator 返回"含糊 PASS"（任何 PASS 必须附完整 evidence_snapshot）
- 🚫 **禁止**表达式写自然语言占位（如"待定" / TODO / "人工判断"）—— 要么编译通过，要么回澄清

---

### 9.6 ✅ 必须职责

- ✅ **必须**在 S4 开始前完成所有 DoD 条款的编译（S3 Gate 硬件之一）
- ✅ **必须**把每条表达式反查到至少 1 条原始 AC
- ✅ **必须**提供受限 evaluator 接口给 L2-05 / L2-06 / verifier
- ✅ **必须**在未命中白名单时触发澄清回路（不得自行猜测谓词语义）
- ✅ **必须**在 eval 失败时返回可读的 reason（给 L1-07 判 verdict 用）
- ✅ **必须**保证 evaluator 无副作用（不写任何外部状态）
- ✅ **必须**发 blueprint_ready 后 60 秒内启动编译（与 L2-03/04 并行）
- ✅ **必须**向 L1-07 暴露"不可编译条款数"作为 S3 健康度信号

---

### 9.7 🔧 可选功能职责

- 🔧 AST 可视化输出（L1-10 UI 展示 DoD 矩阵的树形视图）
- 🔧 智能建议：当谓词未命中白名单时，基于词形相似度建议"是否指 X 谓词"（L1-10 提示）
- 🔧 DoD 冲突检测：同一 WP 的多条 DoD 互相矛盾 → 发 WARN
- 🔧 表达式复用挖掘：高频相同 AST 片段抽取为"宏"（长期演进，P2 优先级）
- 🔧 记录每次 eval 耗时分布（性能画像，给 3-1 tech-design 优化）

---

### 9.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-L2-01（接收） | L2-01 | 广播 ← | 接 blueprint_ready，启动编译 |
| IC-L2-02（发起） | L2-05 | 受限 eval → | 提供 eval_expression 接口，返 PASS/FAIL + reason |
| IC-L2-02（发起） | L2-06 | 受限 eval → | S5 验证时同一接口 eval |
| IC-09（发起） | L1-09 | 持久化 → | 编译完成 / 失败事件落盘 |
| IC-13（发起） | L1-07 | 建议 → | 不可编译条款 → INFO 澄清建议 |
| IC-16（经 L1-02） | L1-10 | 输出 → | dod-expressions.yaml 作为 S3 Gate 待审产出物 |

---

### 9.9 🎯 交付验证大纲

**正向场景 1 · 50 条 DoD 完整编译**
- Given：4 件套验收条件 50 条 + 全部命中白名单
- When：blueprint_ready 触发
- Then：
  - 60 秒内产 dod-expressions.yaml
  - 每条表达式反查到至少 1 条 AC
  - 无 exec 节点（AST 校验通过）

**正向场景 2 · 受限 eval 正常返回**
- Given：WP-X 执行完成，L2-05 请求 eval
- When：调 evaluator(expr_id, data_sources_snapshot)
- Then：
  - ≤ 100ms 返 {pass=true, evidence=...}
  - 无任何文件 / 网络访问

**负向场景 3 · 含 arbitrary exec 拒绝编译**
- Given：条款含 "执行脚本 xxx.sh 检查"
- When：编译尝试
- Then：
  - 编译失败 → 拒绝产出该条目
  - 发 push_suggestion{INFO, reason=exec_forbidden}
  - 告警回 L1-02 要求改写

**负向场景 4 · 未命中白名单**
- Given：条款 "UI 要好看"（无量化谓词）
- When：编译尝试
- Then：
  - 编译失败 → 记入不可编译清单
  - 流 F：触发回查 L1-02 澄清

**负向场景 5 · evaluator 试图访问文件系统**
- Given：某 eval 请求传入 data_source={type=file, path=/etc/passwd}
- When：evaluator 尝试访问
- Then：
  - 抛 SecurityError
  - 该表达式 eval 返 FAIL + reason=security_violation
  - 事件落盘 + L1-07 记风险

**集成场景 6 · S5 verifier 独立 eval 同一套 DoD**
- Given：主 loop L2-05 eval = PASS
- When：S5 verifier 子 Agent 独立 eval
- Then：
  - 得到相同结果（pure function 可重入语义）
  - 证据链 quality 段与 L2-05 自检一致

**性能场景 7 · 高频 eval 压力**
- Given：1000 次连续 eval 调用
- When：持续调用
- Then：
  - P95 ≤ 100ms
  - 无内存泄漏

---

## 10. L2-03 · 测试用例生成器（骨架先红灯） 详细定义

### 10.1 职责 + 锚定

**一句话职责**：按 L2-01 的 Master Test Plan + AC 矩阵，在 S3 阶段批量生成各层（单元 / 集成 / E2E）的测试骨架文件，放到 `tests/generated/`；**每个用例函数体是"先红灯"的断言失败骨架**（未实现 → FAIL）—— 强制驱动 S4 走 TDD（先红 → 实现 → 变绿），严禁"桩代码撒谎绿灯"。

**上游锚定**：
- Goal §2.2 五大纪律"质量"+"检验"（TDD 顺序严格保证质量）
- Goal §3.5 硬约束（隐含）：没有"先红"的用例，就没办法证明后续的"绿"是真绿
- PM-05 Stage Contract 机器可校验（用例骨架是 DoD 的代码化形式）
- scope §5.4.1 职责"全量测试用例生成"
- scope §5.4.4 硬约束 4"TDD 蓝图必须在 S4 前全部生成"
- BF-S3-03 全量测试用例生成流

**下游服务**：
- L2-05 S4 执行驱动器（调用 skill 逐个把用例从红变绿）
- L2-06 S5 Verifier 编排器（verifier 独立 session 复跑用例作为 behavior 段证据）
- L1-05（skill 写实现时读用例作为 TDD 输入）

---

### 10.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **Master Test Plan**：from L2-01（blueprint_ready 事件）—— 分层策略 + 用例清单索引
- **AC 矩阵**：同上；每条 AC 对应 ≥ 1 个用例槽位
- **WBS**：from L1-03（只读）—— 用于按 WP 分组用例
- **测试框架偏好**：from 4 件套"技术约束"或 L1-06 KB recipe（如项目选 pytest / jest / go test）

**输出（文字描述）**：

- **`tests/generated/unit/*.py`**（或对应语言 / 框架的单元测试骨架）
- **`tests/generated/integration/*.py`**（集成层骨架）
- **`tests/generated/e2e/*.py`**（E2E 骨架）
- 每个用例：函数名含 AC 引用（如 `test_ac_007_order_total_under_100ms`）+ 函数体为"空断言失败"（禁止 pass / return True / skip）
- **用例清单 manifest**：文字描述（由 L2-05 读取判"未绿用例数"单调递减）
- **cases_generated 事件**：广播给 L2-05 / L2-06

---

### 10.3 边界

**In-scope（本 L2 做什么）**：

1. 读 Master Test Plan 分层策略
2. 按 AC × 分层矩阵批量生成用例骨架
3. 函数体**强制红灯**（空断言失败语义）
4. 函数名规范化（AC 引用 + 语义关键词）
5. 按 WP 分组放置到 `tests/generated/<wp_id>/<layer>/`
6. 产用例清单 manifest（给 L2-05 做单调递减校验）
7. 广播 cases_generated 事件
8. 可读性保证（骨架文件有 docstring 描述测试意图）

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不写具体断言逻辑（那是 S4 实现阶段的事，交给 L2-05 + L1-05 skill）
- ❌ 不管 DoD 表达式 → L2-02
- ❌ 不管测试环境搭建 / fixture 实现 → L2-01 在蓝图中规划 + S4 实现
- ❌ 不管测试运行器配置 → 落到 4 件套"技术约束"
- ❌ 不生成"桩代码假绿"用例（红线禁区）
- ❌ 不负责测试数据填充 → L2-01 蓝图中规划 + S4 实现

**边界规则**：

- 本 L2 产出必须**语法可通过**（文件能被测试框架加载发现）但**运行必 FAIL**（红灯硬性）
- 用例文件路径结构固定：`tests/generated/<wp_id>/<layer>/test_<ac_id>_<slug>.py`（具体命名迁 3-1）
- 所有用例的"空断言"语义一致（具体实现风格迁 3-1 tech-design）

---

### 10.4 约束

**业务模式引用**：
- **PM-05 Stage Contract 机器可校验**：骨架文件的"红灯"状态本身是一条可 eval 的 DoD

**硬约束（文字清单）**：

1. **红灯硬性**：任何生成的用例函数体必须是"未实现 → FAIL" 语义；禁止 pass / True / skip / mock-PASS
2. **S4 前生成完成**（scope §5.4.4 硬约束 4）：tests/generated/ 是 S3 Gate 五件套之一
3. **AC 覆盖率 100%**：每条 AC 至少 1 个用例骨架（与 L2-01 蓝图一致）
4. **用例不可重写**（S4 阶段语义）：L2-03 生成后，S4 阶段 L1-05 skill 只能**填实现**，不能改用例断言目标
5. **骨架语法合法**：必须能被选定测试框架加载发现，否则"红灯"假阳

**性能约束（文字清单）**：

- 500 条用例骨架 ≤ 3 分钟生成完成
- 单个用例文件 ≤ 100 行（保证可读）

---

### 10.5 🚫 禁止行为

- 🚫 **禁止**生成桩代码假绿（`def test_xx(): pass` / `assert True`）
- 🚫 **禁止**用 skip / pytest.mark.skip 绕过红灯
- 🚫 **禁止**生成不可加载的语法错误文件
- 🚫 **禁止**遗漏任何 AC（覆盖率硬性 100%）
- 🚫 **禁止**在 S4 阶段改动用例断言目标（只允许 S4 填实现）
- 🚫 **禁止**生成无 docstring 的用例（可读性硬性）
- 🚫 **禁止**把自然语言 AC 原文直接当函数名（需语义化 slug）

---

### 10.6 ✅ 必须职责

- ✅ **必须**按 AC × 分层矩阵生成全部用例骨架
- ✅ **必须**函数体为"未实现"红灯语义
- ✅ **必须**在每个用例文件写 docstring 说明测试意图 + 来源 AC
- ✅ **必须**按 WP 组织路径结构
- ✅ **必须**产出用例清单 manifest（给 L2-05 单调递减校验用）
- ✅ **必须**广播 cases_generated 事件
- ✅ **必须**在测试框架可加载的前提下产出骨架（语法校验）
- ✅ **必须**与 L2-01 blueprint 保持一致（若蓝图改变 → 走 FAIL-L2 回退重建）

---

### 10.7 🔧 可选功能职责

- 🔧 从 L1-06 KB 读类似 AC 的历史骨架作为模板（提升骨架质量）
- 🔧 为每条骨架附带"参考实现提示"（不是实现，是思路指引给 S4 skill 读）
- 🔧 生成"验证套件"小程序，S4 阶段每次 commit 前 L2-05 跑一遍确认"未绿数单调递减"
- 🔧 覆盖率预估（基于骨架数 / WP 数）—— 为 L2-04 quality-gates 提供基线
- 🔧 骨架 diff 对比（S3 重建时新旧对比给用户看）

---

### 10.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-L2-01（接收） | L2-01 | 广播 ← | 接 blueprint_ready，启动用例骨架生成 |
| IC-L2-03（发起） | L2-05 | 读查询 → | 提供"未绿用例清单"查询 + 单调递减校验 |
| IC-09（发起） | L1-09 | 持久化 → | 用例生成 / 更新事件落盘 |
| IC-16（经 L1-02） | L1-10 | 输出 → | tests/generated/ 作为 S3 Gate 产出物预览 |
| IC-06（发起） | L1-06 KB | 读 ← | 查骨架模板（可选增强） |

---

### 10.9 🎯 交付验证大纲

**正向场景 1 · 100 条 AC × 三层用例批量生成**
- Given：Master Test Plan 标 100 条 AC × 分层配比（60 单元 / 30 集成 / 10 E2E）
- When：blueprint_ready 触发
- Then：
  - 3 分钟内产出 ~100-200 个用例骨架（考虑 AC 分层冗余）
  - 全部红灯（运行 pytest → 全 FAIL）
  - manifest 完整

**正向场景 2 · 骨架语法校验通过**
- Given：用例骨架已生成
- When：pytest collect
- Then：无 collect error，全部用例被发现

**负向场景 3 · 禁止桩代码假绿**
- Given：L2-03 内部某路径倾向生成 pass
- When：生成时
- Then：自检拦截 → 抛错 → 生成失败 + 事件上报

**负向场景 4 · 骨架语法错误**
- Given：某模板渲染错误导致语法不合法
- When：生成后自检
- Then：
  - 自检 FAIL → 拒绝广播 cases_generated
  - 发 INFO 建议回查模板

**集成场景 5 · S4 阶段用例从红变绿**
- Given：L2-05 调 tdd skill 跑 WP-X
- When：skill 填实现 → 跑测试
- Then：
  - WP-X 用例由红变绿
  - L2-05 读 manifest 确认"未绿用例数"递减
  - 单次 commit 不允许未绿数增加（响应面 6）

**集成场景 6 · S5 verifier 独立复跑用例**
- Given：S4 全完，进 S5
- When：verifier 子 Agent 独立 session 跑 pytest
- Then：
  - 得到与 L2-05 自检一致的绿灯结果
  - behavior 段证据链完整

**性能场景 7 · 大规模（500+ AC）**
- Given：500 条 AC
- When：生成
- Then：
  - 5 分钟内完成（可放宽）
  - 骨架数 ≥ 500（AC 覆盖率 100%）

---

## 11. L2-04 · 质量 Gate 编译器 + 验收 Checklist 生成器 详细定义

### 11.1 职责 + 锚定

**一句话职责**：读 4 件套的"质量标准"文档 + AC 清单，产出两份 S3 Gate 硬凭证：**`quality-gates.yaml`**（机器可校验的阈值矩阵：覆盖率 / 性能 / 安全扫描 / lint / 依赖合规）+ **`acceptance-checklist.md`**（用户视角可勾选的验收条款清单）。是 S3 Gate BF-S3-05 通过条件的最后两件产出。

**上游锚定**：
- Goal §2.2 五大纪律"质量"+"验收"（质量指标 + 用户验收是双保险）
- Goal §4.1"真完成质量达标率 ≥ 95%"（质量 gate 是达标判据）
- PM-05 Stage Contract 机器可校验（quality-gates 是机器判）
- scope §5.4.1 职责"质量 gate + 验收 checklist 生成"
- scope §5.4.4 硬约束 4"TDD 蓝图必须在 S4 前全部生成"
- BF-S3-04 质量 gate + 验收 checklist 生成流

**下游服务**：
- L2-05 S4 执行驱动器（commit 前跑 quality-gates 自检）
- L2-06 S5 Verifier 编排器（verifier 独立跑 quality-gates）
- L1-10 UI（展示 acceptance-checklist 给用户 S3 Gate 审核 / S7 收尾验收）
- 用户（直接勾选 acceptance-checklist 完成 S7 验收）

---

### 11.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **4 件套"质量标准"文档**：from L1-02，含覆盖率目标 / 性能指标 / 合规要求 / 代码风格
- **AC 清单**：from L1-02，用户视角条款
- **Master Test Plan 覆盖率目标**：from L2-01（作为 quality-gates 行/分支覆盖率阈值输入）
- **DoD 表达式矩阵**：from L2-02（作为 quality-gates 的谓词基础）

**输出（文字描述）**：

- **`docs/testing/quality-gates.yaml`**：机器可校验阈值矩阵，覆盖至少：
  - 覆盖率：行 / 分支 / AC 三类下限
  - 性能：P95 延迟 / 吞吐 / 内存上限
  - 安全：高危漏洞数 = 0 / 已知 CVE 处置率
  - 代码质量：lint error 数 / 类型检查错误数
  - 依赖：高危依赖 = 0 / 许可证合规
- **`docs/testing/acceptance-checklist.md`**：用户视角可读 markdown 清单：
  - 按 AC 大类组织
  - 每条条款勾选框 + 验收方式（自动 / 人工）+ 验收证据位置
  - S7 阶段用户逐条勾选
- **gates_ready 事件**：广播（非强下游）

---

### 11.3 边界

**In-scope（本 L2 做什么）**：

1. 读质量标准文档 + AC + 覆盖率目标 + DoD 矩阵
2. 编译 quality-gates.yaml（阈值矩阵）
3. 编译 acceptance-checklist.md（用户视角勾选清单）
4. 保证 quality-gates 所用谓词都在 L2-02 白名单内
5. 保证 acceptance-checklist 覆盖 100% AC（与 L2-01 AC 覆盖率一致）
6. 两个产出作为 S3 Gate 待审产出物推送
7. S7 阶段：提供 checklist 勾选进度查询接口给 L1-10 / L1-02

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不自己跑测试 / 扫描 → L2-05 / verifier / skill
- ❌ 不判 verdict → L1-07
- ❌ 不定义自然语言质量语义 → 要回查 L1-02
- ❌ 不管 Stage Gate 交互 → L1-02 / L1-10
- ❌ 不动态调阈值 → 阈值只在 S3 定，改需 FAIL-L2 回退

**边界规则**：

- quality-gates.yaml 所有谓词**必须在 L2-02 白名单**；未命中 → 编译失败
- acceptance-checklist.md 是**用户最终验收依据**；禁止写入 AC 以外的条款
- 两个产出是**S3 Gate 硬凭证**；缺一即 Gate 不过

---

### 11.4 约束

**业务模式引用**：
- **PM-05 Stage Contract 机器可校验**：quality-gates 是机器 Contract；acceptance-checklist 是用户 Contract
- **PM-10 单一事实源**：阈值只在 yaml，不重复写代码常量

**硬约束（文字清单）**：

1. **S4 前编译完成**（scope §5.4.4 硬约束 4）：两件都是 S3 Gate 凭证
2. **谓词白名单约束**：quality-gates 所有判别谓词必须在 L2-02 白名单
3. **AC 覆盖率 100%**：acceptance-checklist 覆盖 4 件套中所有 AC
4. **阈值可追溯**：每条阈值必须反查到 4 件套质量标准某条款
5. **Checklist 可勾选 + 可证据指向**：每条都有"验收方式"+"证据位置"字段

**性能约束**：
- 编译耗时 ≤ 60 秒
- quality-gates.yaml ≤ 200KB
- acceptance-checklist.md ≤ 500KB

---

### 11.5 🚫 禁止行为

- 🚫 **禁止** quality-gates 使用非白名单谓词
- 🚫 **禁止** acceptance-checklist 包含 4 件套外条款
- 🚫 **禁止**阈值无来源（每条必反查）
- 🚫 **禁止** S4 阶段改 quality-gates.yaml（必经 FAIL-L2 回退）
- 🚫 **禁止**把"主观判断"条款放入 quality-gates（应落在 checklist 人工验收侧）
- 🚫 **禁止**两个产出冲突（yaml 覆盖率 ≥ 80% 但 checklist 说 70% 可接受 → 不一致）
- 🚫 **禁止**用户未勾选任何 checklist 条款的情况下进 S7 收尾（S7 Gate 硬性）

---

### 11.6 ✅ 必须职责

- ✅ **必须**编译 quality-gates.yaml + acceptance-checklist.md 两件完整产出
- ✅ **必须**所有谓词在 L2-02 白名单内
- ✅ **必须** acceptance-checklist 覆盖 100% AC
- ✅ **必须**每条阈值 / 条款可反查 4 件套
- ✅ **必须**为每条 checklist 条款标注"自动 / 人工"验收方式
- ✅ **必须**提供 L2-05 跑自检的 quality-gates 接口（本 L2 提供读视图，不执行）
- ✅ **必须**把两件产出作为 S3 Stage Gate 待审产出物推送给 L1-02

---

### 11.7 🔧 可选功能职责

- 🔧 Checklist 勾选进度实时统计（给 L1-10 UI 渲染进度条）
- 🔧 阈值合理性提示（与 L1-06 KB 历史基线对比，异常偏离 → WARN）
- 🔧 多环境阈值差异化（dev / staging / prod 不同阈值，P2 优先级）
- 🔧 Checklist 导出（PDF / HTML 给用户线下审查）
- 🔧 质量 gate 失败时给出"差几分"的量化报告（help debug）

---

### 11.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-L2-01（接收） | L2-01 | 广播 ← | 接 blueprint_ready，启动编译 |
| IC-L2-02（读） | L2-02 | 依赖 ← | 读白名单谓词表校验 quality-gates 合规 |
| IC-L2-04（发起） | L2-05 | 读 → | 提供 quality-gates.yaml 读视图给 S4 WP 自检 |
| IC-09（发起） | L1-09 | 持久化 → | gates_ready 事件 + checklist 勾选进度落盘 |
| IC-16（经 L1-02） | L1-10 | 输出 → | 两件产出作为 S3 Gate 待审产出物展示 |

---

### 11.9 🎯 交付验证大纲

**正向场景 1 · 两件产出齐全**
- Given：质量标准文档 + 50 条 AC + 蓝图覆盖率目标
- When：blueprint_ready 触发
- Then：
  - 60 秒内产 quality-gates.yaml + acceptance-checklist.md
  - 所有谓词在 L2-02 白名单
  - AC 覆盖率 100%

**正向场景 2 · S3 Gate 作为凭证**
- Given：两件产出 + 其他三件（蓝图 / DoD / 用例）已齐
- When：BF-S3-05 Gate 启动
- Then：L1-10 UI 能完整展示两件作为待审产出物

**负向场景 3 · 谓词未命中白名单**
- Given：质量标准含"代码审美好"
- When：编译
- Then：
  - 编译失败
  - 发 INFO 建议回查 L1-02（同流 F 机制）

**负向场景 4 · AC 覆盖率漏项**
- Given：50 条 AC，checklist 只写 49 条
- When：自检
- Then：拒绝产出 + 发 INFO

**集成场景 5 · S4 WP 自检跑 quality-gates**
- Given：L2-05 进入 WP-X 自检
- When：读 quality-gates.yaml 里 WP-X 相关阈值
- Then：
  - 阈值可读
  - 通过 L2-02 evaluator eval
  - 返 PASS/FAIL

**集成场景 6 · S7 用户勾选 checklist**
- Given：项目进入 S7 收尾
- When：用户在 L1-10 UI 勾选 checklist
- Then：
  - 勾选进度落盘
  - 100% 勾选才满足 S7 Gate（与 L1-02 协同）

**性能场景 7 · 大规模 AC**
- Given：500 条 AC
- When：编译 checklist
- Then：checklist.md ≤ 500KB，可用浏览器快速加载

---

## 11. L2-04 · 质量 Gate 编译器 + 验收 Checklist 生成器 详细定义

⏸ 分段写入中

---

## 12. L2-05 · S4 执行驱动器 详细定义

### 12.1 职责 + 锚定

**一句话职责**：在 S4 阶段接管每一个 WP（从 L1-03 拿到下一 WP）→ 调 L1-05 起 `tdd` / `prp-implement` skill 写代码 → 等待测试从红变绿 → 对本 WP 跑 DoD 自检（用 L2-02 受限 evaluator eval）→ 自检 PASS 触发 git commit（WP 粒度）→ 汇报"WP-X done"继续下一 WP。是 S4 阶段全部"IMPL → 绿灯 → 自检 → commit"循环的**唯一驱动点**。

**上游锚定**：
- Goal §2.2 五大纪律"质量"（驱动 TDD 顺序严格）
- Goal §3.5 硬约束（隐含）：S4 工作必须 WP 粒度可追溯 / 可验证
- PM-05 Stage Contract 机器可校验（WP-DoD 自检是机器 Contract）
- PM-03 子 Agent 独立 session 委托（L2-05 调 L1-05 起 skill 走委托通道）
- scope §5.4.1 职责"S4 阶段：驱动每个 WP 的 IMPL → 单元/集成测试 → WP-DoD 自检 → commit"
- scope §5.4.3 边界"WP-DoD 自检（非独立验证）"
- BF-S4-03 TDD 驱动实现流 / BF-S4-04 WP-DoD 自检流 / BF-S4-05 WP commit 流

**下游服务**：
- L1-01 主 loop（接收"WP done"回调，决定下一步）
- L1-03 WP 调度（取下一 WP）
- L1-05 Skill+子 Agent（被调度写代码）
- L1-09（commit / 自检事件落盘）
- L1-10 UI（展示 WP 执行进度）

---

### 12.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **IC-03 触发**：`enter_quality_loop{phase=S4, wp=WP-X}` from L1-01
- **当前 WP 定义**：from L1-03（goal / DoD / 依赖 / 工时 / 推荐 skill）
- **用例骨架**：from L2-03（当前 WP 对应的红灯用例）
- **DoD 表达式子集**：from L2-02（当前 WP 对应的表达式）
- **quality-gates WP 子集**：from L2-04
- **skill 回调**：from L1-05（skill 写完代码 + 测试绿后通知）

**输出（文字描述）**：

- **skill 调用请求**：经 IC-04 `invoke_skill{skill=tdd|prp-implement, context=WP-X}` 到 L1-05
- **WP 自检报告**：`{wp_id, dod_eval_results, cases_green_count_before/after, pass/fail, reason}`
- **git commit**：WP 粒度（commit message 规范由 3-1 tech-design 定）
- **wp_done 事件**：经 IC-09 落盘 + 回调 L1-01
- **UI 进度推送**：进度条 / 当前 WP / 测试绿灯数

---

### 12.3 边界

**In-scope（本 L2 做什么）**：

1. 接 enter_quality_loop{phase=S4}
2. 循环：取下一 WP → 调 skill → 等绿 → 自检 → commit → 报 done
3. 每次 commit 前校验"未绿用例数单调递减"（响应面 6）
4. WP 自检调 L2-02 受限 evaluator eval DoD 表达式
5. WP 自检 FAIL → 最多 3 次 skill 重跑（WP 内自修）；仍 FAIL → 上报"需 S5 后再判"（不自做判定）
6. 全部 WP 完成 → 报告 "S4 done" 给 L1-01 推进 S5
7. 与 L1-03 协同 WP 依赖推进（不自己做拓扑，只取下一可执行）
8. 向 L1-10 实时推送 WP 执行进度

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不做独立验证 → L2-06（S5 阶段）
- ❌ 不做 verdict 判定 → L1-07
- ❌ 不做回退 → L2-07
- ❌ 不自己写代码 → 委托 L1-05 skill
- ❌ 不做 WBS 拓扑排序 → L1-03
- ❌ 不改 TDD 蓝图 → 需 FAIL-L2 回退
- ❌ 不做"跨 WP 集成测试" → 蓝图中的集成/E2E 用例由 verifier 独立跑

**边界规则**：

- 本 L2 是 S4 的**唯一驱动点**；L1-01 不允许绕过它直接调 skill
- WP 自检**不等于**验证（scope §5.4.3 边界明确）：自检 PASS 也可能在 S5 被 verifier 判 FAIL → 走回退
- WP 内自修次数上限（默认 3 次，具体值迁 3-1）
- commit 必须在自检 PASS 后发生；不允许"先 commit 再调自检"

---

### 12.4 约束

**业务模式引用**：
- **PM-03 子 Agent 独立 session 委托**：调 skill 走 IC-04（不复用主 session）
- **PM-05 Stage Contract 机器可校验**：WP-DoD 自检是机器化 Contract
- **PM-10 单一事实源**：commit / 自检事件全经 IC-09 落盘

**硬约束（文字清单）**：

1. **测试必须先绿才 commit**：未绿 → 禁止 commit
2. **未绿用例数单调递减**：本次 commit 前未绿数 ≤ 上次 commit 后未绿数（响应面 6）
3. **自检调用必走 L2-02 evaluator**：禁止直接解 yaml 自解释
4. **WP 粒度 commit**：一个 WP 一次 commit（或若干小 commit 合并 + 标记 WP id）
5. **不自做 verdict**（scope §5.4.5 禁 6）：WP 自检 FAIL → 报给 L1-07 判，不自己决定"可以跳过" 或 "重跑"

**性能约束**：
- 单 WP 平均驱动耗时 ≤ 项目规模 WP 工时估算的 1.2 倍
- WP 自检 ≤ 30 秒（用例跑 + DoD eval）
- skill 调用失败 backoff ≤ 5 分钟

---

### 12.5 🚫 禁止行为

- 🚫 **禁止**测试未绿时 commit
- 🚫 **禁止**未绿用例数增加（绿 → 红 回退）的 commit
- 🚫 **禁止**自己写代码（必须委托 L1-05 skill）
- 🚫 **禁止**改 TDD 蓝图（必经 FAIL-L2 回退）
- 🚫 **禁止**自做 verdict（把 WP 自检当最终验证）
- 🚫 **禁止**跳过 DoD 自检直接 commit
- 🚫 **禁止**越级调其他 L1 资源（如直接调 L1-05 IC-05 委托子 Agent；须通过 IC-04）
- 🚫 **禁止** WP 自修 ≥ 3 次仍 FAIL 后继续强推（必须上报）

---

### 12.6 ✅ 必须职责

- ✅ **必须**在 enter_quality_loop{phase=S4} 后按 L1-03 给的顺序循环执行 WP
- ✅ **必须**每个 WP 前读 L2-02 表达式 + L2-03 用例清单 + L2-04 gates
- ✅ **必须**每次 commit 前校验"未绿数单调递减"
- ✅ **必须**调 L2-02 受限 evaluator 做自检（不自解释）
- ✅ **必须**自检 PASS 才 commit（WP 粒度）
- ✅ **必须**所有 WP done 后报告 "S4 done" 给 L1-01
- ✅ **必须**向 L1-10 UI 实时推送执行进度
- ✅ **必须**持久化每次自检 / commit 事件（经 IC-09）

---

### 12.7 🔧 可选功能职责

- 🔧 WP 内自修失败根因提示（给 skill 的下次调用带上失败原因摘要，提升成功率）
- 🔧 与 L1-06 KB 读"TDD 最佳实践"recipe（提升 skill 调用质量）
- 🔧 预估下一 WP 耗时（基于历史 + 当前失败率）
- 🔧 commit 信息自动生成（含 WP id / 覆盖 AC / 绿灯数变化）
- 🔧 执行进度事件的 heart-beat（每 10 秒一次，便于 UI 活跃度感知）

---

### 12.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-03（接收） | L1-01 | 控制流 ← | 接 enter_quality_loop{phase=S4, wp=WP-X}，启动 WP 驱动 |
| IC-02（发起） | L1-03 | 调度 → | 取下一可执行 WP |
| IC-04（发起） | L1-05 | 调度 → | 调 `tdd` 或 `prp-implement` skill 写代码 |
| IC-L2-02（发起） | L2-02 | 受限 eval → | WP 自检 eval DoD 表达式 |
| IC-L2-03（发起） | L2-03 | 读查询 → | 读未绿用例清单 + 单调递减校验 |
| IC-L2-04（发起） | L2-04 | 读 → | 读 quality-gates WP 子集 |
| IC-L2-05（发起） | L1-01 | 回调 → | 报 "WP-X done" / "S4 done" |
| IC-09（发起） | L1-09 | 持久化 → | commit / 自检事件落盘 |
| IC-06（发起） | L1-06 KB | 读 ← | 查 TDD recipe（可选增强） |
| IC-13（发起） | L1-07 | 建议 → | WP 自修 ≥ 3 次 FAIL → INFO/WARN 升级 |

---

### 12.9 🎯 交付验证大纲

**正向场景 1 · 单 WP 驱动完整跑通**
- Given：WP-X 已锁定，蓝图 / DoD / 用例 / gates 全齐
- When：enter_quality_loop{phase=S4, wp=WP-X}
- Then：
  - 调 tdd skill → 代码写完 → 测试绿
  - DoD 自检 PASS
  - git commit 生成（WP-X 粒度）
  - 回调 "WP-X done"

**正向场景 2 · 全部 WP 完成**
- Given：10 个 WP
- When：顺序驱动
- Then：
  - 10 次 commit 生成
  - 未绿用例数最终为 0
  - 回调 "S4 done"

**负向场景 3 · 测试未绿强行 commit 被拒**
- Given：skill 回调"完成"但测试还红
- When：L2-05 尝试 commit
- Then：
  - commit 被拒
  - 重调 skill 继续写（WP 内自修）
  - 若 3 次仍未绿 → 升级 INFO 给 L1-07

**负向场景 4 · 绿变红回退被拒**
- Given：前次 commit 未绿数 = 20，本次 commit 前未绿数 = 22
- When：尝试 commit
- Then：
  - 拒绝 commit
  - 触发 WP 内自修（给 skill 带上"某用例变红"原因）

**负向场景 5 · DoD 自检 FAIL**
- Given：测试绿但 DoD 覆盖率 70% < 80% 阈值
- When：自检
- Then：
  - 自检 FAIL
  - 重调 skill 补测试（WP 内自修）
  - 3 次仍 FAIL → 上报 INFO 给 L1-07

**集成场景 6 · 跨 WP 顺序驱动**
- Given：WP-A 依赖 WP-B；WP-B 已 done
- When：取下一 WP
- Then：L1-03 返 WP-A，L2-05 正常接管

**集成场景 7 · WP 自修超限升级**
- Given：WP-X 自修 3 次仍 FAIL
- When：L2-05 判断
- Then：
  - 不强推
  - 向 L1-07 发 push_suggestion{WARN, reason=wp_self_repair_exhausted}
  - 等待 L1-07 决策（可能直接进 S5 + 等 verifier 判 L1 级 FAIL）

**性能场景 8 · 大规模 WP**
- Given：50 个 WP
- When：S4 全流程
- Then：
  - 总耗时 ≤ 50 × 平均 WP 工时 × 1.2
  - 每次 WP 自检 ≤ 30 秒

---

## 13. L2-06 · S5 TDDExe Verifier 编排器 详细定义

### 13.1 职责 + 锚定

**一句话职责**：S4 全部 WP 完成后，进入 S5 阶段 —— 组装 verifier 工作包（S3 蓝图 + S4 产出物 + AC 清单）→ 经 IC-20 委托 L1-05 起**独立 session 的 verifier 子 Agent** 跑 TDDExe 独立验证 → 接收 verifier 结果后**组装三段证据链**（existence / behavior / quality）→ 落盘到 `verifier_reports/*.json` → 推送给 L1-07 判 verdict。是 Goal §2.2 五大纪律"检验"在 L1-04 内的**唯一工程落地**。

**上游锚定**：
- Goal §2.2 五大纪律"检验"（独立验证是第五纪律的灵魂）
- Goal §3.5 硬约束 4"S5 未 PASS 不得进 S7"（本 L2 是 S5 唯一工作面）
- PM-03 子 Agent 独立 session 委托（scope §5.4.4 硬约束 2 "verifier 必独立 session"）
- scope §5.4.1 职责"S5 阶段：委托 verifier 子 Agent 跑独立验证 → 组装三段证据链"
- scope §5.4.4 硬约束 2 + 3
- scope §5.4.5 禁 2"禁止 verifier 主 session 跑"
- BF-S5-01 Verifier 独立调用流 / BF-S5-02 三段证据链组装流

**下游服务**：
- L1-05 Skill+子 Agent（被委托起独立 session verifier）
- L1-07 Supervisor（读 report 判 verdict）
- L1-09 审计（三段证据链落盘）
- L1-10 UI（Verifier 证据链 tab 实时展示）

---

### 13.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **IC-03 触发**：`enter_quality_loop{phase=S5}` from L1-01（S4 全完后）
- **S3 蓝图**：from L2-01（master-test-plan）+ L2-02（dod-expressions.yaml）+ L2-03（tests/generated/）+ L2-04（quality-gates.yaml + acceptance-checklist.md）
- **S4 产出物快照**：所有 WP 的 commit 哈希 + 测试结果快照 + 实际产物路径
- **AC 清单**：from L1-02
- **verifier 子 Agent 回调**：from L1-05（验证完成后返 report）

**输出（文字描述）**：

- **verifier 工作包**：组装好的数据包（文字描述；具体字段迁 3-1），含蓝图 + 产出快照 + AC + 执行环境指令
- **IC-20 委托请求**：`delegate_verifier{工作包}` 经 IC-04/IC-05 走 L1-05 路径
- **`verifier_reports/<session_id>.json`**：三段证据链 JSON
  - existence 段：每个声称产出物的实际存在证据（file / commit / deploy_url 等）
  - behavior 段：独立复跑测试结果（vs 主 agent 声称的绿）
  - quality 段：独立 eval DoD + quality-gates 结果
- **verifier_report_ready 事件**：经 IC-09 落盘 + 经事件总线广播给 L1-07
- **降级信号**：委托失败 3 次 → push_suggestion BLOCK 给 L1-07

---

### 13.3 边界

**In-scope（本 L2 做什么）**：

1. 接 enter_quality_loop{phase=S5}
2. 组装 verifier 工作包（三件蓝图 + S4 产出 + AC）
3. 经 IC-20 委托 L1-05 起独立 session verifier
4. 接 verifier 返回 → 组装三段证据链 JSON
5. 落盘 verifier_reports + 广播给 L1-07
6. 委托失败重试 / 降级（响应面 4）
7. 给 L1-10 UI 推送证据链节点进度（verifier 运行期间）
8. 处理多 verifier 子任务（若项目大到需要多个 verifier 并行）

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不做 verdict 判定 → L1-07
- ❌ 不做回退路由 → L2-07
- ❌ 不自己跑 verifier（必须独立 session 委托）→ L1-05
- ❌ 不主 session 自跑简化 DoD 作降级（硬禁止）
- ❌ 不改蓝图 / DoD / 用例（只读这些作为工作包）
- ❌ 不管 verifier 内部 prompt / skill 选择 → L1-05 负责

**边界规则**：

- 本 L2 是 S5 的**唯一工作面**；任何 L1 想绕过它直接判 PASS 都违反 Goal §3.5 硬约束 4
- verifier 调用**必须**经 L1-05 独立 session（scope §5.4.4 硬约束 2）
- 三段证据链格式**稳定**（existence + behavior + quality），空段需明确标记"empty"并说明原因
- report 落盘**先于**广播 L1-07（避免 L1-07 判完找不到证据的数据竞争）

---

### 13.4 约束

**业务模式引用**：
- **PM-03 子 Agent 独立 session 委托**（硬约束核心）
- **PM-05 Stage Contract 机器可校验**（三段证据链是 S5 阶段的 Contract）
- **PM-10 单一事实源**（report 经 IC-09 落盘到事件总线）

**硬约束（文字清单）**：

1. **必独立 session**（scope §5.4.4 硬约束 2）：verifier 必须经 L1-05 走 IC-20；禁止主 session 自跑
2. **三段证据链完整**：existence + behavior + quality 三段都必须产出；空 → 需明确标记空的原因（如"quality 段因 L2-02 evaluator 不可用而降级"）
3. **report 先落盘后广播**：L1-07 收到广播时必须能读到 report
4. **降级硬红线**：委托失败不允许降级主 session 自跑（流 G）
5. **verifier 工作包不含敏感凭证**：工作包只含文档路径 + commit 哈希 + AC 文字，不带 API key / secret

**性能约束**：
- 组装工作包 + 委托派发 ≤ 30 秒
- verifier 子 Agent 超时上限 ≤ 30 分钟（超时 → 记 WARN + 重试）
- 三段证据链落盘 ≤ 10 秒

---

### 13.5 🚫 禁止行为

- 🚫 **禁止** verifier 在主 session 跑（硬约束 2）
- 🚫 **禁止**委托失败时降级到主 session 自跑简化 DoD
- 🚫 **禁止**在未收到 verifier 返回前广播 verifier_report_ready
- 🚫 **禁止**产出不完整的三段证据链（缺段必须显式标空+原因）
- 🚫 **禁止**改 S3 蓝图 / S4 产出（只读）
- 🚫 **禁止**自己判 verdict
- 🚫 **禁止**工作包含敏感凭证 / PII（风险：verifier session 被污染或日志外泄）

---

### 13.6 ✅ 必须职责

- ✅ **必须**接到 enter_quality_loop{phase=S5} 后 30 秒内派发 verifier 工作包
- ✅ **必须**通过 IC-20 走 L1-05 起独立 session
- ✅ **必须**组装三段证据链完整（空段显式标原因）
- ✅ **必须** report 先落盘后广播（顺序依赖）
- ✅ **必须**在委托失败 3 次后升级 BLOCK（不得静默）
- ✅ **必须**向 L1-10 UI 推送 verifier 运行期间进度（existence 段跑完/behavior 段跑完/quality 段跑完）
- ✅ **必须**为每次 verifier 调用分配 session_id 并附在 report 里
- ✅ **必须**当蓝图 / S4 产出有缺失时拒绝启动（不把垃圾工作包给 verifier）

---

### 13.7 🔧 可选功能职责

- 🔧 verifier 并行分片（大项目把 WP 拆给多个并行 verifier，由本 L2 协调聚合）
- 🔧 与 L1-06 KB 读"verifier trap"库（防典型骗绿陷阱）
- 🔧 verifier 返回异常的结构化错误分类
- 🔧 三段证据链差异对比（与主 agent 声称的对照 diff 视图）
- 🔧 verifier 耗时画像（给 3-1 tech-design 优化参考）

---

### 13.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-03（接收） | L1-01 | 控制流 ← | 接 enter_quality_loop{phase=S5}，启动验证 |
| IC-L2-06（发起） | L1-05 | 委托 → | 经 IC-20 delegate_verifier 起独立 session |
| IC-L2-07（发起） | L1-09 | 持久化 → | 三段证据链落盘（经 IC-09） |
| IC-L2-08（发起） | L1-07 | push → | verifier_report_ready 事件供其判 verdict |
| IC-13（发起） | L1-07 | 建议 → | 委托失败连续 3 次 → BLOCK |
| IC-16（经 L1-02） | L1-10 | 输出 → | verifier 进度 / 证据链 tab 推送 |
| IC-06（发起） | L1-06 KB | 读 ← | 查 verifier trap 库（可选增强） |

---

### 13.9 🎯 交付验证大纲

**正向场景 1 · 一次完整 S5 验证**
- Given：S4 全完 + 蓝图齐
- When：enter_quality_loop{phase=S5}
- Then：
  - 30 秒内委托 verifier（经 IC-20）
  - verifier 独立 session 跑完 3 段
  - 组装三段证据链 JSON 落盘
  - 广播 verifier_report_ready 给 L1-07

**正向场景 2 · verifier 判真完成质量达标**
- Given：主 agent 自检 PASS + verifier 独立跑也 PASS
- When：L1-07 读 report
- Then：verdict=PASS → L2-07 路由进 S7

**负向场景 3 · verifier 主 session 自跑拦截**
- Given：L2-06 代码被人改为"直接在主 session eval DoD"
- When：静态校验
- Then：
  - 拒绝运行
  - 告警"硬约束 2 违反"

**负向场景 4 · 委托失败 3 次升级**
- Given：连续 3 次 IC-20 失败（API 限流）
- When：L2-06 累计
- Then：
  - 发 push_suggestion{BLOCK, reason=verifier_unavailable}
  - 不降级主 session 自跑
  - UI 红屏告警

**负向场景 5 · 证据链缺段**
- Given：verifier 只跑了 existence + behavior，quality 段因某原因失败
- When：组装 report
- Then：
  - quality 段显式标 "empty, reason=evaluator_unreachable"
  - 广播前先写好 + 落盘
  - L1-07 会按 INSUFFICIENT_EVIDENCE 判 FAIL-L2

**集成场景 6 · 证据链与主 agent 声称的 diff**
- Given：主 agent 自检说 "所有 WP 绿"，verifier 独立跑发现 WP-3 有 1 个 flaky 用例
- When：三段组装
- Then：
  - behavior 段显式标注该 flaky 用例 + 独立证据（log + run 次数）
  - L1-07 判 verdict 有数据依据（很可能 FAIL-L1）

**集成场景 7 · 与 L1-10 UI 进度推送**
- Given：verifier 运行中
- When：existence 段跑完
- Then：
  - 向 L1-10 UI 推进度"existence ✅ / behavior 运行中 / quality 待"
  - 用户可以实时看到 verifier 进展

**性能场景 8 · 大项目 verifier 超时**
- Given：verifier 跑 > 30 分钟未完成
- When：超时
- Then：
  - 记 WARN
  - 重启一次（或分片并行，若开启 13.7 可选）
  - 仍 FAIL → 升级 BLOCK

---

## 14. L2-07 · 偏差判定 + 4 级回退路由器 详细定义

### 14.1 职责 + 锚定

**一句话职责**：接收 L1-07 Supervisor 基于 verifier_report 产出的 4 级 verdict（PASS / FAIL-L1 轻 / FAIL-L2 中 / FAIL-L3 重 / FAIL-L4 极重）→ 按精确映射表路由到对应的 state 切换请求（进 S7 / 回 S4 / 回 S3 / 回 S2 / 回 S1）→ 经 IC-01 请求 L1-01 执行 state 转换；同时维护"同级 FAIL 计数器"，同级 ≥ 3 次触发 BF-E-10 死循环保护升级。**本 L2 不自做判定**（scope §5.4.5 禁 6）—— 判定权在 L1-07；本 L2 只做"verdict 到 state 的精确翻译"。

**上游锚定**：
- Goal §2.2 五大纪律"安全"（死循环 = 安全问题）
- Goal §3.5 硬约束（隐含）：偏差回退必须自动化、精确、无主观
- PM-06 偏差 4 级治理（文字引用）
- PM-10 单一事实源（回退事件经 IC-09 落盘）
- scope §5.4.1 职责"判定 verdict → 自动路由回退"
- scope §5.4.5 禁 6"禁止自己做偏差 4 级判定"
- scope §5.4.6 必 "按 4 级 verdict 精确触发 Quality Loop 回退"
- BF-S5-03 偏差等级判定流 / BF-S5-04 回退路由流 / BF-E-10 死循环保护流

**下游服务**：
- L1-01 主 loop（接收 state 转换请求）
- L1-02 生命周期（接收回退进对应 state）
- L1-07 Supervisor（升级 BF-E-10 死循环）
- L1-10 UI（回退卡片展示）
- L1-09（回退事件落盘）

---

### 14.2 输入 / 输出

**输入（文字描述，非 schema）**：

- **IC-14 push_rollback_route**：from L1-07，携带：
  - verdict ∈ {PASS, FAIL-L1, FAIL-L2, FAIL-L3, FAIL-L4}
  - target_state（L1-07 建议回到的目标 state，冗余字段，用于交叉校验）
  - reason（自然语言原因 + 结构化证据引用）
  - related_wp_id（可选）
- **verifier_report_ready 事件**（订阅）：用于同步更新本地"未决 verdict"上下文
- **用户决策**（死循环情景）：from L1-10 UI（继续 / 换方案 / 放弃）

**输出（文字描述）**：

- **IC-01 request_state_transition**：向 L1-01 请求 state 切换（S7 / S4 / S3 / S2 / S1）
- **rollback_routed 事件**：经 IC-09 落盘（含 verdict + 路由 + 计数器当前值）
- **BF-E-10 升级信号**：经 IC-13 push_suggestion{level=BLOCK} 给 L1-07（当同级计数 ≥ 3）
- **UI 推送**：回退路由卡片（展示 verdict + 路由 + 原因 + 同级 FAIL 次数）
- **同级 FAIL 计数器状态**：可查询 / 可订阅（L1-10 显示死循环风险）

---

### 14.3 边界

**In-scope（本 L2 做什么）**：

1. 接 IC-14 push_rollback_route
2. 查精确映射表（verdict → target_state）
3. 与 L1-07 传入的 target_state 交叉校验（防漂移）
4. 经 IC-01 请求 state 转换
5. 维护 (wp_id, verdict_level) → count 的计数器（本地状态 + 经 L1-09 持久化）
6. count ≥ 3 → 触发 BF-E-10 升级
7. 用户处置死循环后更新计数器（重置 / 维持）
8. 向 L1-10 UI 推回退事件卡片
9. PASS verdict 路由到 S7 收尾

**Out-of-scope（本 L2 不做，谁做）**：

- ❌ 不自做 verdict 判定（禁区硬性）→ L1-07 判
- ❌ 不决定"是否死循环" 的启发式 → 只按固定计数规则（≥ 3）
- ❌ 不执行 state 转换（只请求）→ L1-01 执行
- ❌ 不执行 stage 内部动作 → 目标 L2 自己推进
- ❌ 不做硬拦截 → L1-07
- ❌ 不改 verifier_report 内容 → 只读
- ❌ 不改 verdict 语义分级（4 级边界由 Goal + scope 定）

**边界规则**：

- 本 L2 是"verdict → state"翻译的**唯一点**；不允许 L1-01 / 其他 L1 自行翻译 verdict
- 同级计数 = 3 是**硬性阈值**；不允许临时调高（防绕过 BF-E-10）
- target_state 交叉校验：L1-07 传入的 target_state 与本 L2 映射表不一致时 → 记 ADR 风险事件 + 以本 L2 映射为准（防 L1-07 临时漂移）

---

### 14.4 约束

**业务模式引用**：
- **PM-06 偏差 4 级治理**（文字引用）
- **PM-10 单一事实源**（回退事件经 IC-09 落盘）

**硬约束（文字清单）**：

1. **不自做判定**（scope §5.4.5 禁 6）：verdict 只从 L1-07 来
2. **同级计数 ≥ 3 硬触发 BF-E-10**（scope §5.4.6 必 + BF-E-10）：不允许"再给一次机会"绕过
3. **路由必经 IC-01**：不得私自改 state；只能请求 L1-01 执行
4. **精确映射表稳定**：4 级 verdict 到 4 级 state 的映射是硬契约（参见流 D 的矩阵）
5. **所有路由事件必落盘**：经 IC-09 到 L1-09，含计数器值（审计完整）
6. **target_state 交叉校验**：与 L1-07 传入值不一致 → 以本 L2 表为准 + 记警告

**性能约束**：
- 接 IC-14 → 路由执行 ≤ 3 秒
- 计数器查询 ≤ 100ms
- UI 推送 ≤ 1 秒

---

### 14.5 🚫 禁止行为

- 🚫 **禁止**自做 verdict 判定（硬约束 1 禁区）
- 🚫 **禁止**绕过 IC-01 自己改 state
- 🚫 **禁止**同级 FAIL 计数 ≥ 3 时不触发 BF-E-10（硬性）
- 🚫 **禁止**临时调高计数阈值（防绕过）
- 🚫 **禁止**漏落盘回退事件
- 🚫 **禁止**接受 verdict 值不在 5 个枚举内（PASS + 4 级 FAIL）的 IC-14
- 🚫 **禁止**在未收 L1-07 IC-14 前主动路由（只响应，不主动）

---

### 14.6 ✅ 必须职责

- ✅ **必须**按 4 级映射表精确路由（PASS→S7 / L1→S4 / L2→S3 / L3→S2 / L4→S1）
- ✅ **必须**维护 (wp_id, verdict_level) → count 计数器并持久化
- ✅ **必须** count ≥ 3 时升级 BF-E-10 给 L1-07
- ✅ **必须**路由请求经 IC-01
- ✅ **必须**向 L1-10 推回退卡片
- ✅ **必须**持久化所有路由事件
- ✅ **必须**交叉校验 L1-07 的 target_state；不一致 → 以本 L2 映射为准 + 记风险
- ✅ **必须**用户决策死循环后正确更新计数器（继续 = 重置 / 换方案 = 重置 + 回 S3 / 放弃 = 终态）

---

### 14.7 🔧 可选功能职责

- 🔧 计数器趋势分析（给 L1-07 提前预警：某 WP 已两次 FAIL-L1，下次再挂就死循环）
- 🔧 回退路径可视化（L1-10 UI 画项目在 7 阶段间跳动的路线图）
- 🔧 回退影响面报告（回退到 S3 → 明示哪些 S4 产出需重验）
- 🔧 与 L1-06 KB 读 "TDDExe verdict 模板"（帮 L1-07 判更一致）
- 🔧 回退频度统计（retro 用）

---

### 14.8 与其他 L2 / L1 交互

| 契约 | 对端 | 方向 | 描述（一句话） |
|---|---|---|---|
| IC-L2-09（接收） | L1-07 | 接 ← | IC-14 push_rollback_route 接 4 级 verdict |
| IC-L2-10（发起） | L1-01 | 请求 → | 经 IC-01 request_state_transition |
| IC-L2-11（发起） | L1-07 | 升级 → | 同级计数 ≥ 3 → 经 IC-13 push_suggestion BLOCK |
| IC-09（发起） | L1-09 | 持久化 → | 路由 / 计数 / 升级事件落盘 |
| IC-16（经 L1-02） | L1-10 | 输出 → | 回退卡片 + 死循环告警 |
| IC-17（接收） | L1-10 | 用户决策 ← | 死循环时用户处置选项 |

---

### 14.9 🎯 交付验证大纲

**正向场景 1 · PASS 路由进 S7**
- Given：L1-07 IC-14 {verdict=PASS}
- When：L2-07 接
- Then：
  - 3 秒内经 IC-01 请求 state=S7
  - 事件 rollback_routed{verdict=PASS, target=S7} 落盘
  - UI 推"Quality Loop 完成，进 S7"

**正向场景 2 · FAIL-L1 回 S4**
- Given：L1-07 IC-14 {verdict=FAIL-L1, wp_id=WP-X}
- When：L2-07 接
- Then：
  - IC-01 请求回 S4（WP-X 重跑）
  - 计数器 (WP-X, L1) = 1
  - UI 推回退卡片

**正向场景 3 · FAIL-L2 回 S3**
- Given：verdict=FAIL-L2
- When：L2-07 接
- Then：IC-01 请求回 S3 → L2-01 重建蓝图

**正向场景 4 · FAIL-L3 回 S2**
- Given：verdict=FAIL-L3
- When：L2-07 接
- Then：IC-01 请求回 S2，L1-04 本轮 Quality Loop 终止等待新 4 件套

**正向场景 5 · FAIL-L4 回 S1**
- Given：verdict=FAIL-L4
- When：L2-07 接
- Then：IC-01 请求回 S1 + 全部产出标"待弃/重做"

**负向场景 6 · target_state 交叉校验不一致**
- Given：L1-07 传 verdict=FAIL-L2 但 target_state=S4
- When：L2-07 交叉校验
- Then：
  - 以本 L2 映射为准（FAIL-L2 → S3）
  - 事件记"target_state_mismatch"警告
  - 告知 L1-07 自检

**负向场景 7 · 同级 FAIL 计数 ≥ 3**
- Given：(WP-X, L1) 已计数 2，新的 IC-14 到
- When：count + 1 = 3
- Then：
  - 触发 BF-E-10 升级 push_suggestion{BLOCK}
  - UI 弹死循环告警
  - 等用户决策

**负向场景 8 · 非法 verdict**
- Given：IC-14 {verdict="WEIRD"}
- When：L2-07 接
- Then：
  - 拒绝路由
  - 返错给 L1-07
  - 记风险事件

**集成场景 9 · 用户选"换方案"**
- Given：死循环触发，用户选"换方案 → 回 S3"
- When：L2-07 接 IC-17
- Then：
  - 计数器 (WP-X, L1) 重置为 0
  - 路由回 S3
  - UI 展示"已切换方案"

**性能场景 10 · 高频回退（调试期）**
- Given：10 次 verdict 连续到
- When：L2-07 处理
- Then：
  - 每次 ≤ 3 秒路由
  - 计数器一致性保持
  - 死循环在正确时点触发（每级第 3 次）

---

## 15. L1-04 对外 scope §8 IC 契约映射（本 L1 实际承担）

⏸ 分段写入中

---

## 16. 本 L1 retro 位点

⏸ 分段写入中

---

## 附录 A · 术语（L1-04 本地）

⏸ 分段写入中

---

## 附录 B · businessFlow BF 映射

⏸ 分段写入中

---

*— L1-04 Quality Loop PRD v1.0 · 产品级（纯文字 · 无代码 · 无 schema · 无配置参数）·  2026-04-20 —*
