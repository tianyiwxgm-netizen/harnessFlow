"""HTTP / service-up primitives."""

import json

from ._shell import run


def curl_status(url: str, timeout: float = 10.0) -> tuple[int, dict]:
    result = run(
        ["curl", "-o", "/dev/null", "-s", "-w", "%{http_code}", "--max-time", str(int(timeout)), url],
        require="curl",
        timeout=timeout + 2,
    )
    try:
        code = int(result["stdout"].strip())
    except ValueError:
        code = -1
    return code, {"url": url, "curl": result, "status_code": code}


def curl_json(url: str, timeout: float = 10.0):
    result = run(
        ["curl", "-sS", "--max-time", str(int(timeout)), url],
        require="curl",
        timeout=timeout + 2,
    )
    body = result["stdout"]
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        return None, {"url": url, "curl": result, "error": f"invalid_json: {exc}"}
    return parsed, {"url": url, "curl": result, "parsed_keys_sample": list(parsed.keys())[:10] if isinstance(parsed, dict) else None}


def uvicorn_started(host_port: str) -> tuple[bool, dict]:
    """Heuristic: curl /health first; fallback to /."""
    for path in ("/health", "/"):
        url = f"http://{host_port}{path}"
        code, ev = curl_status(url, timeout=5.0)
        if 200 <= code < 500:
            return True, {"url": url, "status_code": code, "probe": ev}
    return False, {"host_port": host_port, "probed": ["/health", "/"], "last_probe": ev}


def vite_started(host_port: str) -> tuple[bool, dict]:
    url = f"http://{host_port}/"
    code, ev = curl_status(url, timeout=5.0)
    ok = 200 <= code < 500
    return ok, {"url": url, "status_code": code, "probe": ev}
