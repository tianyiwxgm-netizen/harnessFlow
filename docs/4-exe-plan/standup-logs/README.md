---
doc_id: standup-logs-readme
doc_type: logs-directory-guide
---

# Standup Logs 目录

> **用途**：各 Dev / main / QA / Sign 会话每日 standup 日志汇总。

## 命名规范

```
docs/4-exe-plan/standup-logs/<会话名>-<YYYY-MM-DD>.md
```

示例：
- `Dev-α-2026-04-23.md`
- `main-1-2026-05-28.md`
- `QA-1-2026-06-18.md`

## 每日 standup 模板

```markdown
---
session: Dev-α
date: 2026-04-23
wp_current: α-WP01
---

# Dev-α · 2026-04-23 · standup

## 昨日完成
- WP01 atomic_write red 阶段 · 5 test failing（期望）
- WP01 atomic_write green 阶段 · fsync + rename 实现 · 全绿

## 今日计划
- WP02 append+hash chain red
- WP02 green · prev_hash 验证

## 阻塞
- 无 · 或 `情形 D · IC-09 契约模糊 · 已汇报主会话`

## DoD 进度
- WP01: ✅ 绿（5/5 test + coverage 87%）
- WP02: 🟡 red 完 · green in progress

## 代码产出
- commits: 3 个
- LOC: +420 / -0
```

## 主会话汇总

主会话每日扫本目录 · 更新 `docs/4-exe-plan/PROGRESS.md`。

---

*— standup-logs/README · 各会话日志落盘规范 —*
