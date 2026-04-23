---
doc_id: signoff-6-2-release-process-v1.0
doc_type: signoff-execution-plan
layer: 6-finalQualityAcceptance
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/main-4-final-integration-exe-plan.md §3.8 WP08 release + 签收
  - docs/6-finalQualityAcceptance/6-1-delivery-checklist.md（本组消费 Sign-1 打包结果）
version: v1.0
status: draft
assignee: **Sign-2 · 独立会话**
wave: 7
priority: P0（release 公共动作 · 不可逆）
estimated_duration: 0.5-1 天
---

# Sign-2 · Release 流程 Execution Plan

> **本 md 定位**：**独立会话** · 写 **release 流程脚本** + **git tag + GitHub release 上传 + 公告发送** SOP。
>
> **本组做什么**：
> 1. 写 `scripts/release.sh` · git tag + push + GitHub release 创建
> 2. 写 release notes 模板 · 交 Sign-4 填充内容
> 3. 写公告模板（邮件 / Slack · harnessFlow 用户群）
> 4. 写 `docs/RELEASE_CHECKLIST.md` · main-4 WP08 跑时 step-by-step 勾
> 5. 定义 rollback 策略（万一 release 后发现致命问题 · 撤 tag + patch release）
>
> **本组不做**：
> - ❌ 不 release（main-4 WP08 跑）
> - ❌ 不填 notes 内容（Sign-4 负责）
> - ❌ 不管签收审批（Sign-3 负责）

---

## §1 range

### release 流程步骤（11 步）

1. 确认 main-4 WP07 产 tar.zst + manifest（Sign-1 产出）
2. 确认 Sign-3 签收全勾（5 维度）
3. 确认 Sign-4 release notes ready
4. `git tag v1.0.0` + tag message
5. `git push origin v1.0.0`
6. GitHub release 创建（gh cli）
7. 上传 tar.zst + manifest.json + sha256
8. 上传 release notes（markdown body）
9. 发公告（邮件群 + Slack 频道）
10. 更新官网（`docs/USER_GUIDE.md` 链接）
11. 存档 release 记录到 `releases/release-v1.0.0.log`

---

## §2 范围 · 3 脚本 + 1 checklist + 1 rollback SOP

**脚本 A · `scripts/release.sh`**：
```bash
#!/bin/bash
set -euo pipefail
VERSION=${1:-v1.0.0}

# Step 1: pre-check
[[ -f "releases/harnessflow-${VERSION}.tar.zst" ]] || { echo "❌ tar.zst not found"; exit 1; }
[[ -f "releases/manifest-${VERSION}.json" ]] || { echo "❌ manifest not found"; exit 1; }
[[ -f "releases/signoff-${VERSION}.yaml" ]] || { echo "❌ signoff not found"; exit 1; }

# Step 2: git tag
git tag -a "${VERSION}" -m "harnessFlow ${VERSION} · $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push origin "${VERSION}"

# Step 3: GitHub release
gh release create "${VERSION}" \
    "releases/harnessflow-${VERSION}.tar.zst" \
    "releases/harnessflow-${VERSION}.tar.zst.sha256" \
    "releases/manifest-${VERSION}.json" \
    --title "harnessFlow ${VERSION}" \
    --notes-file "docs/RELEASE_NOTES-${VERSION}.md"

# Step 4: 公告（假设有 notify 脚本）
python scripts/notify_release.py --version "${VERSION}"

# Step 5: 存档
echo "release_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "releases/release-${VERSION}.log"
echo "✅ Release ${VERSION} complete"
```

**脚本 B · `scripts/notify_release.py`**（伪代码）：
```python
# 发 release 公告到 3 渠道：
# 1. 邮件（smtp）
# 2. Slack webhook
# 3. 内部 announcement 页面
# 内容来自 docs/RELEASE_NOTES-v1.0.0.md
```

**脚本 C · `scripts/rollback_release.sh`**：
```bash
#!/bin/bash
# 撤回 release（2h 内 · 发现致命问题）
VERSION=$1
gh release delete "${VERSION}" --yes
git push origin --delete "${VERSION}"
git tag -d "${VERSION}"
# 发撤回公告
python scripts/notify_rollback.py --version "${VERSION}"
```

### release checklist (`docs/RELEASE_CHECKLIST.md`)

前置：
- [ ] tar.zst + sha256 + manifest 齐（Sign-1）
- [ ] QA-5 R{final} release gate PASSED
- [ ] Sign-3 签收全勾
- [ ] Sign-4 release notes ready

执行：
- [ ] `scripts/release.sh v1.0.0` 全 5 步 exit 0
- [ ] GitHub release 页可访问
- [ ] 下载 tar.zst · 校 sha256 · 解压 · install 成功
- [ ] 公告到达（邮件 / Slack）
- [ ] 官网链接更新

事后（1-7 天）：
- [ ] 监控 issue tracker · 24h 无致命反馈
- [ ] 下载量监控（gh release view）
- [ ] 用户反馈收集

### Rollback 策略

触发条件（任一）：
- 用户报 P0 bug（数据丢失 · 安全漏洞 · 不可用）
- CI/CD 对下游 breaking change
- License / 合规问题

执行：
- 2h 内（tag 未固化）：`scripts/rollback_release.sh v1.0.0` · 撤 tag + release
- 2h 后（已下载）：发补丁 patch release `v1.0.1`（不撤 tag）

---

## §3 WP 拆解（2 WP · 0.5 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| S2-WP01 | 3 脚本 + checklist + rollback SOP | Sign-1 WP01 ready | 0.25 天 |
| S2-WP02 | 自测（mock tag 试跑） | WP01 | 0.25 天 |

---

## §4-§10 简版

```
Sign-1 ready
  ↓
S2-WP01 脚本 · checklist · SOP
  ↓
S2-WP02 自测
  ↓
main-4 WP08 跑 release · 本组 SOP 消费
```

- §5 standup · prefix `S2-WPNN`
- §6 自修正：若流程漏步 · 补
- §7 对外契约：main-4 WP08 入口 · Sign-3 签收预置
- §8 DoD：脚本 test · checklist 完整 · rollback SOP 可用
- §9 风险：GitHub 令牌失效 · 提前 2 天测 gh cli；notify 渠道配置漂移 · 提前测
- §10 交付：`scripts/release.sh` + `scripts/rollback_release.sh` + `scripts/notify_release.py` + `docs/RELEASE_CHECKLIST.md`

---

*— Sign-2 · Release 流程 · Execution Plan · v1.0 —*
