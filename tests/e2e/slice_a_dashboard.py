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

    selected = page.evaluate(
        """() => {
            return document.querySelector('.task-card.active .task-id-small')?.textContent?.trim() || null;
        }"""
    )
    assert selected == PARTIAL_EMPTY_TASK

    empty_cards = page.evaluate(
        """async (tid) => {
            const r = await fetch('/api/tasks/' + encodeURIComponent(tid));
            const d = await r.json();
            return ((d._derived || {}).cards || []).filter(c => c.is_empty);
        }""",
        PARTIAL_EMPTY_TASK,
    )
    assert len(empty_cards) >= 1, "expected partial-empty task to expose ≥1 empty card via API"

    target_node = empty_cards[0]["waiting_for_node"]
    opened = page.evaluate(
        """(nid) => {
            const groups = document.querySelectorAll('.pipeline-svg-host svg g[style*="cursor"]');
            for (const g of groups) {
                const t = g.querySelector('text.pl-node-step')?.textContent || '';
                if (t.startsWith(nid + ' ')) {
                    g.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                    return true;
                }
            }
            return false;
        }""",
        target_node,
    )
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

    selected = page.evaluate(
        """() => {
            return document.querySelector('.task-card.active .task-id-small')?.textContent?.trim() || null;
        }"""
    )
    assert selected == ALL_FILLED_TASK
    assert page.locator(".card-empty-warning").count() == 0
    assert page.locator(".card-empty-hint").count() == 0


@pytest.mark.e2e
def test_pipeline_dag_renders_13_nodes_5_phases(loaded_dashboard, shots_dir):
    page = loaded_dashboard
    _select_task_by_id(page, ALL_FILLED_TASK)
    page.wait_for_timeout(1200)
    pl = page.evaluate(
        """() => {
            const svg = document.querySelector('.pipeline-svg-host svg');
            if (!svg) return {ok: false};
            return {
                ok: true,
                nodes: svg.querySelectorAll('.pl-node-rect').length,
                edges: svg.querySelectorAll('[class^="pl-edge-"]').length,
                phaseBands: svg.querySelectorAll('.pl-phase-band').length,
                progress: document.querySelector('.pipeline-progress')?.textContent?.trim() || null,
            };
        }"""
    )
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
