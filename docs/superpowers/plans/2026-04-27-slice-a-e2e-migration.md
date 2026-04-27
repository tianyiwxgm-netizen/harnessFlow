# Slice A E2E Migration — Implementation Plan

> task_id: p-harness-slice-a-e2e-migration-20260427T034235Z
> route: B (轻 PRP)
> size: S / 重构 / 低
> created: 2026-04-27

**Goal**: 把 `/tmp/slice_a_e2e.py` ad-hoc 脚本固化成 `tests/e2e/slice_a_dashboard.py` pytest 用例，截图归 `tests/e2e/artifacts/`，并用 pytest marker `e2e` 隔离这类需 dashboard 在线的真浏览器测试。

**Architecture**:
- `tests/e2e/` 作为 dedicated 目录，与 `tests/slice_a/` (单元) 隔离；后者跑 pytest 默认套，前者只在 `-m e2e` 时跑
- pytest.ini 加 `markers = e2e`；`testpaths` 维持 `tests/slice_a` 默认（不让 e2e 上 CI 默认套，因为 e2e 依赖 dashboard 在 :8765 跑）
- 用例本质就是 `/tmp/slice_a_e2e.py` 的 main() 拆成 6 个 pytest function（5 个验证 + 1 个 fixture），共享 page/browser fixture

**Tech**: Python 3.13 / pytest 8.x / playwright 1.57.0 sync_playwright / Vue 3 SPA dashboard at 127.0.0.1:8765

**Files**:
- Create: `tests/e2e/__init__.py`（空）
- Create: `tests/e2e/conftest.py`（playwright browser/page fixture + DASHBOARD URL constant + skip-if-dashboard-down hook）
- Create: `tests/e2e/slice_a_dashboard.py`（6 个 test function）
- Create: `tests/e2e/artifacts/.gitkeep`（占位让目录入 git）
- Create: `tests/e2e/README.md`（如何起 dashboard + 跑 e2e）
- Modify: `pytest.ini`（加 markers section + 维持 testpaths）

---

## Task 1: 写 conftest.py + __init__.py + .gitkeep

**Files**:
- Create: `tests/e2e/__init__.py` (empty)
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/artifacts/.gitkeep` (empty)

- [ ] **Step 1: 写 __init__.py** (empty file)

- [ ] **Step 2: 写 conftest.py**

```python
"""tests/e2e/ pytest fixtures：playwright browser + dashboard 健康检查 skip 钩子。"""
from __future__ import annotations
import os
import socket
import urllib.request
import urllib.error
from pathlib import Path
import pytest

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8765
DASHBOARD_URL = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def _dashboard_alive() -> bool:
    try:
        urllib.request.urlopen(DASHBOARD_URL + "/api/tasks", timeout=2)
        return True
    except (urllib.error.URLError, socket.timeout, ConnectionError):
        return False


def pytest_collection_modifyitems(config, items):
    if not _dashboard_alive():
        skip_marker = pytest.mark.skip(
            reason=f"dashboard {DASHBOARD_URL} 未在线；先 `cd ui/backend && uvicorn server:app --port 8765`"
        )
        for it in items:
            if "e2e" in it.keywords:
                it.add_marker(skip_marker)


@pytest.fixture(scope="session")
def playwright_instance():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance):
    b = playwright_instance.chromium.launch(headless=True)
    yield b
    b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    p = ctx.new_page()
    errors: list[str] = []
    p.on("pageerror", lambda exc: errors.append(str(exc)))
    p.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
    p._collected_errors = errors  # type: ignore[attr-defined]
    yield p
    ctx.close()


@pytest.fixture
def shots_dir() -> Path:
    return ARTIFACTS_DIR


@pytest.fixture
def dashboard_url() -> str:
    return DASHBOARD_URL
```

- [ ] **Step 3: 写 .gitkeep** (empty file)

- [ ] **Step 4: Commit**
```bash
git add tests/e2e/__init__.py tests/e2e/conftest.py tests/e2e/artifacts/.gitkeep
git commit -m "feat(slice-a): add tests/e2e/ scaffold + playwright fixtures"
```

---

## Task 2: 迁移 slice_a_e2e.py → tests/e2e/slice_a_dashboard.py

**Files**:
- Create: `tests/e2e/slice_a_dashboard.py`

- [ ] **Step 1: 写完整测试文件**

```python
"""Slice A dashboard 浏览器 E2E（pytest 版）。

跑法：先起 dashboard `cd ui/backend && uvicorn server:app --port 8765`，
然后 `pytest -m e2e tests/e2e/slice_a_dashboard.py -v`。
"""
from __future__ import annotations
import pytest

PARTIAL_EMPTY_TASK = "e2e-hello-walkthrough-20260426T062858Z"
ALL_FILLED_TASK = "p-tank-battle-20260426T082459Z"


def _select_task_by_id(page, task_id: str) -> None:
    page.evaluate(
        """(tid) => {
            const cards = Array.from(document.querySelectorAll('.task-card'));
            for (const c of cards) {
                const id = c.querySelector('.task-id-small')?.textContent?.trim();
                if (id === tid) { c.click(); return true; }
            }
            return false;
        }""",
        task_id,
    )
    page.wait_for_timeout(2500)


@pytest.fixture
def loaded_dashboard(page, dashboard_url, shots_dir):
    page.goto(dashboard_url, wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=str(shots_dir / "01_dashboard_home.png"), full_page=False)
    return page


@pytest.mark.e2e
def test_dashboard_loads_with_task_cards(loaded_dashboard):
    page = loaded_dashboard
    assert page.title()
    n = page.locator(".task-card").count()
    assert n >= 5, f"expected ≥5 task cards, got {n}"


@pytest.mark.e2e
def test_partial_empty_task_drawer_shows_yellow_warning(loaded_dashboard, shots_dir):
    page = loaded_dashboard
    _select_task_by_id(page, PARTIAL_EMPTY_TASK)
    page.screenshot(path=str(shots_dir / "02_partial_empty_overview.png"), full_page=True)

    selected = page.evaluate("""() => {
        return document.querySelector('.task-card.active .task-id-small')?.textContent?.trim() || null;
    }""")
    assert selected == PARTIAL_EMPTY_TASK

    empty_cards = page.evaluate("""async (tid) => {
        const r = await fetch('/api/tasks/' + encodeURIComponent(tid));
        const d = await r.json();
        return ((d._derived || {}).cards || []).filter(c => c.is_empty);
    }""", PARTIAL_EMPTY_TASK)
    assert len(empty_cards) >= 1, "expected partial-empty task to expose ≥1 empty card via API"

    target_node = empty_cards[0]["waiting_for_node"]
    opened = page.evaluate("""(nid) => {
        const groups = document.querySelectorAll('.pipeline-svg-host svg g[style*="cursor"]');
        for (const g of groups) {
            const t = g.querySelector('text.pl-node-step')?.textContent || '';
            if (t.startsWith(nid + ' ')) {
                g.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                return true;
            }
        }
        return false;
    }""", target_node)
    assert opened, f"could not click pipeline node {target_node}"
    page.wait_for_timeout(1200)
    page.screenshot(path=str(shots_dir / "02b_partial_drawer_node.png"), full_page=True)

    assert page.locator(".card-empty-warning").count() >= 1, "drawer should show ≥1 yellow warning border"
    assert page.locator(".card-empty-hint").count() >= 1, "drawer should show ≥1 ⚠️ hint"

    page.keyboard.press("Escape")
    page.wait_for_timeout(400)


@pytest.mark.e2e
def test_all_filled_task_no_warnings(loaded_dashboard, shots_dir):
    page = loaded_dashboard
    _select_task_by_id(page, ALL_FILLED_TASK)
    page.screenshot(path=str(shots_dir / "03_all_filled.png"), full_page=True)

    selected = page.evaluate("""() => {
        return document.querySelector('.task-card.active .task-id-small')?.textContent?.trim() || null;
    }""")
    assert selected == ALL_FILLED_TASK
    assert page.locator(".card-empty-warning").count() == 0
    assert page.locator(".card-empty-hint").count() == 0


@pytest.mark.e2e
def test_pipeline_dag_renders_13_nodes_5_phases(loaded_dashboard, shots_dir):
    page = loaded_dashboard
    _select_task_by_id(page, ALL_FILLED_TASK)
    page.wait_for_timeout(1200)
    pl = page.evaluate("""() => {
        const svg = document.querySelector('.pipeline-svg-host svg');
        if (!svg) return {ok: false};
        return {
            ok: true,
            nodes: svg.querySelectorAll('.pl-node-rect').length,
            edges: svg.querySelectorAll('[class^="pl-edge-"]').length,
            phaseBands: svg.querySelectorAll('.pl-phase-band').length,
            progress: document.querySelector('.pipeline-progress')?.textContent?.trim() || null,
        };
    }""")
    assert pl["ok"], "pipeline svg should mount"
    assert pl["nodes"] == 13, f"expected 13 nodes, got {pl['nodes']}"
    assert pl["phaseBands"] == 5, f"expected 5 PMP phase bands, got {pl['phaseBands']}"
    assert pl["edges"] >= 13, f"expected ≥13 edges, got {pl['edges']}"
    page.screenshot(path=str(shots_dir / "04_pipeline_dag.png"), full_page=True)


@pytest.mark.e2e
def test_no_console_errors(loaded_dashboard):
    page = loaded_dashboard
    _select_task_by_id(page, ALL_FILLED_TASK)
    page.wait_for_timeout(800)
    errs = getattr(page, "_collected_errors", [])
    benign_substrings = ("favicon", "DevTools")
    real = [e for e in errs if not any(b in e for b in benign_substrings)]
    assert real == [], f"unexpected console errors: {real[:3]}"
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/slice_a_dashboard.py
git commit -m "feat(slice-a): migrate ad-hoc /tmp E2E into tests/e2e/slice_a_dashboard.py"
```

---

## Task 3: pytest.ini 加 e2e marker + tests/e2e/README.md

**Files**:
- Modify: `pytest.ini`
- Create: `tests/e2e/README.md`

- [ ] **Step 1: 改 pytest.ini**

旧：
```ini
[pytest]
testpaths = tests/slice_a
pythonpath = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
```

新：
```ini
[pytest]
testpaths = tests/slice_a
pythonpath = .
python_files = test_*.py slice_a_dashboard.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
markers =
    e2e: 真浏览器 E2E（依赖 dashboard 在 127.0.0.1:8765 在线，默认 collection 跳过；用 `-m e2e tests/e2e/...` 显式跑）
```

注意 testpaths 故意不含 `tests/e2e`，因为 conftest hook 会在 dashboard down 时整体 skip；显式跑用 `pytest -m e2e tests/e2e/...`。

- [ ] **Step 2: 写 tests/e2e/README.md**

```markdown
# tests/e2e/

Slice A dashboard 浏览器 E2E。需 dashboard 在 :8765 在线。

## 跑法
\`\`\`bash
# 终端 1：起 dashboard
cd ui/backend && uvicorn server:app --port 8765

# 终端 2：跑 e2e
pytest -m e2e tests/e2e/slice_a_dashboard.py -v
\`\`\`

截图落 tests/e2e/artifacts/。dashboard 不在线时 conftest 会 skip 整个文件。
```

- [ ] **Step 3: Commit**

```bash
git add pytest.ini tests/e2e/README.md
git commit -m "feat(slice-a): pytest e2e marker + tests/e2e/README.md"
```

---

## Verification (post-implementation)

```bash
pytest -m e2e tests/e2e/slice_a_dashboard.py -v
```

Expected: 5 PASS, screenshots in `tests/e2e/artifacts/`. dashboard 必须在 :8765 在线，否则全 skipped。

Self-review:
- 全部 step 含真实代码块 ✓
- 无 placeholder ✓
- 文件路径精确 ✓
- DoD 5 条全有任务覆盖 ✓
