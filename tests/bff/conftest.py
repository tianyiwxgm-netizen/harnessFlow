import pytest


@pytest.fixture
def pid_header() -> dict[str, str]:
    return {"X-Harness-Pid": "pj-test-001"}
