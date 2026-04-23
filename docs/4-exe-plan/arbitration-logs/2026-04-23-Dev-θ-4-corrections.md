---
doc_id: arbitration-2026-04-23-dev-theta-4-corrections
arbitrator: 主会话
arbitrated_at: 2026-04-23
session_requesting: Dev-θ（feat/dev-theta-l1-10）
---

# 主会话仲裁 · Dev-θ 4 条 Self-Correction

## §1 逐条仲裁

### C-1 · tech_stack CDN → Vite（情形 A · 改 arch）

**背景**：`3-1/L1-10/architecture.md §4` 说 CDN Vue · 但现代前端标配 Vite。

**仲裁**：✅ **接受** · 改 arch.md §4 · `tech_stack: Vue 3 + Element Plus + Pinia + vue-router + Vite`

**理由**：
- Vite 是 Vue 3 官方推荐工具链 · CDN 仅适合 demo
- MASTER-SESSION-DISPATCH §2.1 Dev-θ 描述已默认 Vue 3 + Element Plus + Vite
- 不改 scope · 只技术栈对齐现实

### C-2 · pyproject.toml 加 fastapi/uvicorn[standard]/httpx（共享文件）

**仲裁**：✅ **接受** · 主会话夜晚合并期统一加入

**清单**：
```toml
# BFF group
fastapi = ">=0.110"
uvicorn = {extras = ["standard"], version = ">=0.30"}
httpx = ">=0.27"
```

### C-3 · L2-01 §1.5 D1/D2 vue-router + Pinia（对齐 exe-plan）

**仲裁**：✅ **接受** · 改 `3-1/L1-10/L2-01-*.md §1.5 D1/D2`

**说明**：原 tech-design 只提 Vue + Element Plus · 缺 vue-router + Pinia · exe-plan 和实现都用了 · 对齐文档。

### C-4 · L2-06 enum 分歧 full/lean/custom vs LIGHT/STANDARD/HEAVY

**事实源**：tech-design `3-1/L1-10/L2-06-*.md` 定义 `full/lean/custom`(语义名)· exe-plan 派生为 LIGHT/STANDARD/HEAVY(强度级)。

**仲裁**：✅ **以 tech-design 为准 · `full/lean/custom`**（驳回 exe-plan 的 LIGHT/STANDARD/HEAVY）

**理由**：tech-design 是上游 · exe-plan 是下游派生。语义名 `full/lean/custom` 更表意。

**处理**：
- 修 `docs/4-exe-plan/4-1-exe-DevelopmentExecutionPlan/Dev-θ-L1-10-ui.md` 对应段 · 统一到 `full/lean/custom`
- Dev-θ 当前实现"取两者交集" · 下轮简化为只 `full/lean/custom`

---

## §2 主会话执行清单

- [x] 判决 4 条
- [ ] 改 `3-1/L1-10/architecture.md §4` tech_stack
- [ ] 改 `3-1/L1-10/L2-01-*.md §1.5`
- [ ] 改 `Dev-θ-L1-10-ui.md` enum 段 → full/lean/custom
- [ ] pyproject.toml 加 3 BFF deps（夜晚合并期）
- [ ] 记 correction log 4 条 JSONL

---

## §3 给 Dev-θ 下轮的消息

```
主会话仲裁完成 · 4 条全接受：
C-1 Vite 合法（arch 已改）
C-2 pyproject 3 deps 加（主会话合并）
C-3 L2-01 §1.5 已改
C-4 以 tech-design full/lean/custom 为准 · 下轮简化实现 · 删 LIGHT/STANDARD/HEAVY 适配层

θ2 批延后合理（依赖 main-2 WebSocket / Dev-α WP04 / Dev-δ IC-16 / Dev-β IC-06 · 当前未 ready）· 等依赖绿后开 Dev-θ2 会话。
```

---

*— 主会话仲裁 · 2026-04-23 · Dev-θ 4 条 —*
