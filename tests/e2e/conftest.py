"""tests/e2e/ pytest fixtures：playwright browser + dashboard 健康检查 skip 钩子。"""
from __future__ import annotations

import socket
import urllib.error
import urllib.request
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
    if _dashboard_alive():
        return
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
