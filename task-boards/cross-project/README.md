# task-boards/cross-project/

跨项目 task-board 暂存处。

**什么放这里**：task-board 的 `project` 字段指向 **非 harnessFlow** 项目（如 aigcv2 / aipdd / 化学课件等）。这些任务由 harnessFlow 做编排 skill，但任务本身归属另一个 repo。

**为什么要分离**（v1.1 P9-P2 固化）：
- 避免 Stop gate / test_task_board_schema.py 扫描 harnessFlow 自身 task-board 时被跨项目遗留数据干扰
- 遵守 method3 § 8.11 "跨项目 scope 串误" 反模式：harnessFlow 的验收标准只看自身 scope
- 移动到此目录 = 从 harnessFlow 项目 TODO 里明确"搬走"，免得下次 assessment 又被当自家 P0

**处理规则**：
- 本目录下 task-board 不属 harnessFlow 发布验收范围
- `.gitignore` 已排除 `task-boards/cross-project/*.json`（本地保留作任务历史，不进公共 repo）
- 若用户切到对应下游项目继续推进，可 resume 这些 task（`/harnessFlow resume <task_id>`）

**清单**：
- `p-ai-video-seedance2-20260417T090131Z.json` — aigcv2 P1 视频生成新项目骨架（CLARIFY 轮 1 后 PAUSED_ESCALATED，等待用户澄清）
