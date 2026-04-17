"""OSS primitives: oss_head (HEAD request on signed URL)."""

from ._shell import run


def oss_head(url: str) -> tuple[dict, dict]:
    """HEAD an OSS object via curl and return status_code + headers snapshot.

    Returns (actual, evidence) where actual is a small dict the Verifier can
    compare: `actual.status_code == 200`.
    """
    result = run(
        ["curl", "-I", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url],
        require="curl",
        timeout=15.0,
    )
    code_str = result["stdout"].strip()
    try:
        code = int(code_str)
    except ValueError:
        code = -1
    actual = {"status_code": code}
    return actual, {"url": url, "curl": result, "status_code": code}
