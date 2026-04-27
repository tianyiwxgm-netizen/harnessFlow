# tests/e2e/

Slice A dashboard 浏览器 E2E。需 dashboard 在 :8765 在线。

## 跑法

```bash
# 终端 1：起 dashboard
cd ui/backend && uvicorn server:app --port 8765

# 终端 2：跑 e2e
pytest -m e2e tests/e2e/slice_a_dashboard.py -v
```

截图落 `tests/e2e/artifacts/`。dashboard 不在线时 conftest 会自动 skip 整个文件。

## 与 ad-hoc 脚本的关系

`/tmp/slice_a_e2e.py` 是 Slice A 验收期间 ad-hoc 跑的一次性脚本，保留作 fallback。
本目录是它的 pytest 化固化版，作为 Slice A 浏览器验收的回归基线。
