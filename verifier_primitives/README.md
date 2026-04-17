# harnessFlow Verifier Primitive Library

Phase 6 产出。实现 method3 § 6.1 bootstrap 表里的 20+ 个 DoD 校验原语，供 `harnessFlow:verifier` subagent 直接 import 调用。

## 设计约束

1. 每个 primitive 是一个 Python 函数，签名对齐 method3 § 6.1 文档（`ffprobe_duration(path: str) -> (float, evidence_dict)`）
2. 返回 `(actual, evidence)` 二元组；**不抛业务异常**
3. **例外**：依赖工具缺失（ffprobe / curl / jsonschema / pytest / playwright / npm / git 未安装）→ 抛 `DependencyMissing` → Verifier 按 INSUFFICIENT_EVIDENCE 分支处理
4. 失败态统一用 sentinel：int/float → 负数或 999，bool → False，str → `"MISSING"`；evidence.error 字段记原因

## 文件结构

```
verifier_primitives/
  __init__.py              # 统一导出 + TIER_MAP + classify_tier
  errors.py                # DependencyMissing
  _shell.py                # subprocess 辅助
  fs.py                    # file_exists / dir_exists / wc_lines / grep_count / retro_exists
  video.py                 # ffprobe_duration / playback_check
  oss.py                   # oss_head
  http.py                  # curl_status / curl_json / uvicorn_started / vite_started
  test_tools.py            # pytest_exit_code / pytest_all_green / playwright_* / type_check_exit_code
  screenshot.py            # screenshot_has_content
  schema.py                # schema_valid
  git_tools.py             # diff_lines_net / no_public_api_breaking_change
  perf.py                  # benchmark_regression_delta
  docs.py                  # cross_refs_all_resolvable
  review.py                # code_review_verdict
  tests/
    test_primitives.py     # pytest 自检
```

## 使用方式（Verifier 调用示例）

```python
from verifier_primitives import file_exists, ffprobe_duration, oss_head, DependencyMissing

ok, ev = file_exists("media/p20.mp4")
dur, ev2 = ffprobe_duration("media/p20.mp4")
try:
    head, ev3 = oss_head("https://...signed.url")
    status_ok = head["status_code"] == 200
except DependencyMissing:
    # degrade to INSUFFICIENT_EVIDENCE
    status_ok = None
```

## 新增 primitive 的步骤

1. 在合适 module 文件加函数（若无合适 module 则新建，并在 `__init__.py` 导入 + `__all__` 增项）
2. `__init__.py` 的 `TIER_MAP` 里分类为 `existence` / `behavior` / `quality`
3. `tests/test_primitives.py` 加自检用例
4. 如需新的 method3 § 6.1 DoD 占位符支持，请更新 `method3.md` 表并 cross-ref

## 依赖矩阵

| primitive | 外部工具 | 可选依赖 |
|---|---|---|
| ffprobe_duration / playback_check | `ffprobe` / `ffmpeg` | - |
| oss_head / curl_* / uvicorn_started / vite_started | `curl` | - |
| pytest_* | `pytest` | 测试代码 |
| playwright_exit_code | `npx` + Playwright 已安装 | - |
| type_check_exit_code | `npm` + 项目 `package.json` 有 `type-check` script | - |
| schema_valid | python `jsonschema` package | - |
| git_tools | `git` | - |
| benchmark_regression_delta | 项目自定义 `scripts/perf_check.sh` | - |

缺失任一依赖 → 抛 `DependencyMissing` → Verifier 标 INSUFFICIENT_EVIDENCE（不是 FAIL）。

## 与 method3 § 6.1 DoD 模板映射

| DoD 模板 | 调到的 primitive |
|---|---|
| ① 视频出片 | `file_exists` / `ffprobe_duration` / `oss_head` / `playback_check` / `retro_exists` |
| ② 后端 feature | `uvicorn_started` / `curl_status` / `pytest_exit_code` / `schema_valid` / `code_review_verdict` |
| ③ UI feature | `vite_started` / `playwright_nav` / `screenshot_has_content` / `playwright_exit_code` / `type_check_exit_code` |
| ④ 文档 | `file_exists` / `wc_lines` / `grep_count` / `cross_refs_all_resolvable` / `retro_exists` (reader_5min_test 由人工 retro 记录) |
| ⑤ 重构 | `pytest_all_green` / `benchmark_regression_delta` / `code_review_verdict` / `diff_lines_net` / `no_public_api_breaking_change` |
