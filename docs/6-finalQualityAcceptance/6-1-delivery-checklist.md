---
doc_id: signoff-6-1-delivery-checklist-v1.0
doc_type: signoff-execution-plan
layer: 6-finalQualityAcceptance
parent_doc:
  - docs/4-exe-plan/4-0-master-execution-plan.md
  - docs/4-exe-plan/main-4-final-integration-exe-plan.md §3.7 WP07 打包
version: v1.0
status: draft
assignee: **Sign-1 · 独立会话**
wave: 7（main-4 WP06 全绿后 · 打包期）
priority: P0（release blocker）
estimated_duration: 1 天
---

# Sign-1 · 交付打包 Delivery Checklist Execution Plan

> **本 md 定位**：**独立会话** · 写**打包脚本** + 产 **deliverables checklist**。main-4 WP07 跑本脚本打包。
>
> **本组做什么**：
> 1. 写 `scripts/build_delivery.sh` · 产出 `releases/harnessflow-v1.0.tar.zst`
> 2. 写 `scripts/verify_delivery.py` · 验证 tar.zst 内容 + sha256 + 可解压 + 可 install + pytest 绿
> 3. 写 `manifest.json` schema + 生成器
> 4. 产交付 checklist（~40 条目 · 对齐 verify 脚本）
>
> **本组不做**：
> - ❌ 不写代码（harnessFlow 本体 · 已在 Dev/主 exe-plan）
> - ❌ 不跑打包（main-4 WP07 跑）
> - ❌ 不 release（Sign-2 负责）

---

## §1 范围

### 3 个脚本 + 1 个 checklist

**脚本 A · `scripts/build_delivery.sh`**：
```bash
#!/bin/bash
# build_delivery.sh - harnessFlow v1.0 delivery packager
set -euo pipefail

VERSION="v1.0.0"
OUT="releases/harnessflow-${VERSION}.tar.zst"
MANIFEST="releases/manifest-${VERSION}.json"

# 1. 清理
rm -rf build/
mkdir -p build/harnessflow-${VERSION}

# 2. 复制 · 排除黑名单
rsync -a --exclude-from=scripts/delivery_exclude.txt ./ build/harnessflow-${VERSION}/

# 3. 生成 manifest
python scripts/gen_manifest.py --version ${VERSION} --out ${MANIFEST}

# 4. 打 tar.zst
tar --zstd -cf ${OUT} -C build harnessflow-${VERSION}

# 5. sha256
sha256sum ${OUT} > ${OUT}.sha256

echo "✅ Delivery built: ${OUT}"
echo "   sha256: $(cat ${OUT}.sha256)"
echo "   size: $(du -h ${OUT} | cut -f1)"
```

**排除名单 `scripts/delivery_exclude.txt`**：
```
.git/
.venv/
node_modules/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
*.log
.env
secrets/
projects/*/workspace/      # V1 单 project 示例除外
e2e_artifacts/
build/
releases/
reports/
.DS_Store
.vscode/
.idea/
```

**脚本 B · `scripts/verify_delivery.py`**：
```python
# verify_delivery.py - 解压 + install + pytest 完整性验证
import hashlib
import subprocess
import tempfile
import json
from pathlib import Path

def verify(tarball_path: Path, sha256_path: Path, manifest_path: Path) -> dict:
    results = {}

    # 1. sha256
    expected = sha256_path.read_text().split()[0]
    actual = hashlib.sha256(tarball_path.read_bytes()).hexdigest()
    results['sha256'] = (expected == actual)

    # 2. 解压
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_call(['tar', '--zstd', '-xf', tarball_path, '-C', tmp])
        extracted = Path(tmp) / 'harnessflow-v1.0.0'

        # 3. 必需文件
        required = ['README.md', 'LICENSE', 'pyproject.toml',
                    'app/__init__.py', 'tests/']
        results['required_files'] = all((extracted / f).exists() for f in required)

        # 4. install
        subprocess.check_call(['pip', 'install', '-e', str(extracted)])

        # 5. pytest smoke
        proc = subprocess.run(['pytest', 'tests/smoke/', '-x'],
                              cwd=str(extracted), capture_output=True)
        results['pytest_smoke'] = (proc.returncode == 0)

    return results
```

**脚本 C · `scripts/gen_manifest.py`**：
```python
# gen_manifest.py - 生成 manifest.json
# manifest schema:
# {
#   "version": "v1.0.0",
#   "build_time": "2026-06-15T10:30:00Z",
#   "git_commit": "abc123...",
#   "python_version": "3.11.5",
#   "total_lines_of_code": 195000,
#   "total_test_cases": 4080,
#   "dependencies": [...],
#   "components": [
#     {"name": "L1-01", "lines": 23700, "tests": 881},
#     ...
#   ],
#   "sha256": "..."
# }
```

---

## §2 交付 Checklist（~40 条目）

### 2.1 代码完整性（10 条）

- [ ] `app/l1_01/` ~ `app/l1_10/` 全 10 L1 目录存在
- [ ] `app/l1_integration/` 集成层存在
- [ ] `app/bff/` BFF 存在
- [ ] `frontend/` Vue 骨架存在（L1-10 UI）
- [ ] `tests/unit/` 57 L2 单元测试存在（估 3000+ TC）
- [ ] `tests/integration/` 24 套集成测试存在
- [ ] `tests/acceptance/` 12 场景存在
- [ ] `tests/smoke/` 冒烟测试存在
- [ ] `docs/` 完整设计文档
- [ ] `scripts/` 启动 + 工具脚本齐

### 2.2 依赖完整性（8 条）

- [ ] `pyproject.toml` 正确
- [ ] `requirements.txt`（或 poetry.lock）锁定版本
- [ ] Python >= 3.11 声明
- [ ] 外部 Skill 依赖声明（Claude Agent SDK 版本）
- [ ] frontend `package.json` 锁定
- [ ] 无多余依赖（bandit 检查通过）
- [ ] 依赖安全扫描（pip-audit）无 CVE-HIGH
- [ ] `.env.example` 存在

### 2.3 文档完整性（8 条）

- [ ] `README.md` 起步指南完整
- [ ] `LICENSE` MIT（或协议）
- [ ] `CHANGELOG.md` v1.0.0 条目
- [ ] `CONTRIBUTING.md` 贡献指南
- [ ] `docs/USER_GUIDE.md`（用户手册）
- [ ] `docs/DEVELOPER_GUIDE.md`（开发者手册）
- [ ] `docs/API_REFERENCE.md`（API 参考 · 20 IC）
- [ ] `docs/ARCHITECTURE.md`（L1 集成架构）

### 2.4 质量证据（10 条）

- [ ] `reports/QA1-final-bug-report.yaml` · 0 P0/P1
- [ ] `reports/QA2-scenario-summary.yaml` · 11 PASS
- [ ] `reports/QA3-slo-matrix.yaml` · 3 硬约束 PASS
- [ ] `reports/QA4-resilience-matrix.yaml` · 42 用例 PASS
- [ ] `reports/QA5-regression-final.yaml` · release gate PASSED
- [ ] `reports/audit-chain-integrity.log` · 100% 完整
- [ ] `reports/traceability-matrix.yaml` · 可追溯率 100%
- [ ] `reports/security-scan.yaml` · 无 HIGH
- [ ] `reports/license-compliance.yaml` · 依赖协议清
- [ ] `reports/test-coverage.html` · ≥ 85%

### 2.5 发布资产（4 条）

- [ ] `releases/harnessflow-v1.0.0.tar.zst` 存在
- [ ] `releases/harnessflow-v1.0.0.tar.zst.sha256` 存在
- [ ] `releases/manifest-v1.0.0.json` 存在
- [ ] verify_delivery.py 3 项全 PASS

---

## §3 WP 拆解（3 WP · 1 天）

| WP | 主题 | 前置 | 估时 |
|:---:|:---|:---|:---:|
| S1-WP01 | 脚本 A+B+C + 排除名单 | main-3 ready（结构稳定）| 0.5 天 |
| S1-WP02 | checklist markdown + 对齐 verify | WP01 | 0.25 天 |
| S1-WP03 | 自测 · 跑一次 build + verify（在 current HEAD） | WP01-02 | 0.25 天 |

---

## §4 依赖 · §5-§10

```
main-3 ready（main-4 WP06 还未跑 · 本组可前置准备）
  ↓
S1-WP01 脚本
S1-WP02 checklist
S1-WP03 自测
  ↓
main-4 WP07 跑 · 本组产物消费
```

- §5 standup · prefix `S1-WPNN`
- §6 自修正：若发现打包 issue · 改脚本 · 重跑
- §7 对外契约：main-4 WP07 入口 · Sign-2 WP01 消费
- §8 DoD：脚本可跑 · checklist 40 条全列 · verify 自测通过
- §9 风险：排除名单遗漏（泄漏 secrets）· bandit + 人工 review
- §10 交付：`scripts/build_delivery.sh` + `scripts/verify_delivery.py` + `scripts/gen_manifest.py` + `scripts/delivery_exclude.txt` + 本 md 的 §2 checklist

---

*— Sign-1 · 交付打包 · Execution Plan · v1.0 —*
