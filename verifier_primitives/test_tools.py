"""Test / typecheck primitives."""

from pathlib import Path

from ._shell import run


def pytest_exit_code(target: str) -> tuple[int, dict]:
    result = run(
        ["pytest", target, "-q", "--no-header"],
        require="pytest",
        timeout=300.0,
    )
    return result["exit_code"], {"target": target, "pytest": result}


def pytest_all_green() -> tuple[bool, dict]:
    result = run(
        ["pytest", "-q", "--no-header"],
        require="pytest",
        timeout=600.0,
    )
    ok = result["exit_code"] == 0
    return ok, {"pytest": result}


def playwright_nav(url: str) -> tuple[dict, dict]:
    """Minimal nav probe via curl (full Playwright exec goes through
    playwright_exit_code). Phase 6 v1 keeps this thin."""
    from .http import curl_status

    code, ev = curl_status(url, timeout=10.0)
    ok = 200 <= code < 400
    return {"status": "ok" if ok else "fail", "http_code": code}, {"url": url, "probe": ev}


def playwright_exit_code(spec: str, cwd: str | None = None) -> tuple[int, dict]:
    cmd = ["npx", "playwright", "test", spec]
    result = run(cmd, require="npx", timeout=600.0)
    return result["exit_code"], {"spec": spec, "cwd": cwd, "playwright": result}


def type_check_exit_code(project_dir: str = ".") -> tuple[int, dict]:
    package_json = Path(project_dir) / "package.json"
    if not package_json.is_file():
        return -1, {"project_dir": project_dir, "error": "package.json not found"}
    result = run(
        ["npm", "--prefix", project_dir, "run", "type-check", "--silent"],
        require="npm",
        timeout=300.0,
    )
    return result["exit_code"], {"project_dir": project_dir, "npm": result}
