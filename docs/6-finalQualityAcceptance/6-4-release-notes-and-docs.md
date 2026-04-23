---
doc_id: signoff-6-4-release-notes-and-docs-v1.0
doc_type: signoff-execution-plan
layer: 6-finalQualityAcceptance
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/main-4-final-integration-exe-plan.md §3.8 WP08（release notes 消费）
  - docs/6-finalQualityAcceptance/6-1-delivery-checklist.md（tar.zst 内包含用户手册等）
version: v1.0
status: draft
assignee: **Sign-4 · 独立会话**
wave: 7
priority: P0（release blocker · 无文档不可 release）
estimated_duration: 1-2 天
---

# Sign-4 · Release Notes + 文档 Execution Plan

> **本 md 定位**：**独立会话** · 写 **release notes** + **用户手册** + **开发者手册** + **API 参考**（20 IC）。main-4 WP07 打包时含本组产物。
>
> **本组做什么**：
> 1. `docs/RELEASE_NOTES-v1.0.0.md` · release 公告主文档
> 2. `docs/USER_GUIDE.md` · 用户手册（起步 + 典型流程 + FAQ）
> 3. `docs/DEVELOPER_GUIDE.md` · 开发者手册（起步 + 架构总览 + 扩展）
> 4. `docs/API_REFERENCE.md` · API 参考（20 IC + BFF endpoint）
> 5. `docs/ARCHITECTURE.md` · 简版架构图（来自 3-1/L1集成 · 提炼）
> 6. `README.md` · 更新 · 对外宣传 + 起步
> 7. `CHANGELOG.md` · v1.0.0 条目
>
> **本组不做**：
> - ❌ 不重写 3-1/3-2/3-3（那些是内部设计文档）
> - ❌ 不 release（Sign-2 负责）
> - ❌ 不签收（Sign-3 负责）

---

## §1 7 篇文档清单

### 1.1 `RELEASE_NOTES-v1.0.0.md`（公告 · 2000 字）

- 标题 · 版本号 · 发布日期
- Highlights（核心能力 · 3-5 条）
- Feature matrix（10 L1 + 集成）
- Breaking changes（v0.x → v1.0 · 如有）
- Known limitations（scenario-11 V2+ 延后 · 单 project · etc.）
- Migration guide（无 · v1.0 首发）
- Acknowledgments
- License + 联系

### 1.2 `USER_GUIDE.md`（用户手册 · ~5000 字）

- 1. 起步（install + .env 配置）
- 2. 首个 project（用 CLI / UI 创建第 1 个 project · 跑一次 S1→S7）
- 3. UI 导航（4 Tab · 项目看板 · 质量环可视化 · 审计查询 · 日志流）
- 4. 常见流程（Change Request · 回滚 · 跨 session 恢复）
- 5. 配置（tick 间隔 · SLO 开关 · Skill 白名单 · KB 路径）
- 6. 故障排查 FAQ（~15 条）
- 7. 性能调优建议

### 1.3 `DEVELOPER_GUIDE.md`（开发者手册 · ~8000 字）

- 1. 架构总览（10 L1 + 20 IC · 图）
- 2. 起步（install + dev · 跑测试）
- 3. 10 L1 职责 + 交互（每 L1 ~200 字）
- 4. 20 IC 契约（简介 + 链接到 API Reference）
- 5. 加新 L1（step-by-step · 含 IC 注册）
- 6. 加新 Skill（到 L1-05 白名单）
- 7. 加新场景（到 tests/acceptance/）
- 8. 贡献指南（PR 规范 + test 要求 + DCO）

### 1.4 `API_REFERENCE.md`（20 IC + BFF · ~6000 字）

**IC 部分**（20 × ~250 字）：
- 每 IC：
  - 名字 + 编号
  - 生产方 / 消费方
  - 输入 schema（Python dataclass · JSON 示例）
  - 输出 schema
  - SLO
  - PM-14 约束
  - 失败处理
  - 示例代码

**BFF 部分**（~15 REST endpoint）：
- GET /projects
- POST /projects
- GET /projects/{pid}/state
- GET /projects/{pid}/wbs
- GET /audit/query
- etc.

### 1.5 `ARCHITECTURE.md`（简版 · ~3000 字）

- V-model 全景图
- 10 L1 + 集成图
- 20 IC 生产-消费图（PlantUML）
- S1→S7 状态机图
- 质量环循环图
- 监督链图（L1-07 → L1-01）

### 1.6 `README.md`（对外 · ~1500 字）

- Tagline（1 句）
- Why harnessFlow（3-5 差异点 · vs 其他 Agent 框架）
- Quick start（3 命令）
- Features（核心能力 · 5-8 条）
- Screenshots（UI 3 张图）
- Documentation links
- Community + License

### 1.7 `CHANGELOG.md`（版本日志）

- v1.0.0 条目：
  - `Added`：10 L1 + 20 IC + Web UI + 12 场景
  - `Changed`：无（首发）
  - `Fixed`：main-4 WP06 P0/P1 bug 列表
  - `Known`：scenario-11 V2+ 延后

---

## §2 WP 拆解（5 WP · 1.5 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| S4-WP01 | RELEASE_NOTES + CHANGELOG（依赖 main-4 fix log）| main-4 WP06 完 | 0.25 天 |
| S4-WP02 | README 更新 + ARCHITECTURE 简版 | 3-1/L1集成 稳定 | 0.25 天 |
| S4-WP03 | USER_GUIDE（含 UI 截图）| L1-10 UI ready | 0.5 天 |
| S4-WP04 | DEVELOPER_GUIDE + API_REFERENCE（20 IC）| ic-contracts.md 稳定 | 0.5 天 |
| S4-WP05 | 自审 + 链接校验 · 终版 | 全 WP | 0.25 天 |

---

## §3 依赖 · §4-§10

```
ic-contracts.md 稳定 + 3-1/L1集成 稳定 + L1-10 UI ready + main-4 WP06 fix log ready
  ↓
S4-WP01/02/03/04（并行）
  ↓
S4-WP05 自审
  ↓
main-4 WP07 打包吸收
```

- §5 standup · prefix `S4-WPNN`
- §6 自修正：若文档与代码不一致 · 以代码为准 · 改文档
- §7 对外契约：Sign-1 打包 · Sign-2 release 消费
- §8 DoD：7 篇全齐 · 内链无死链 · 终端能跑起步流程成功
- §9 风险：UI 截图依赖 L1-10 ready · 可临时用 mock；文档与代码漂移 · 自审期统一校对
- §10 交付：7 篇 markdown · 终版位于 repo root 和 `docs/`

---

*— Sign-4 · Release Notes + 文档 · Execution Plan · v1.0 —*
