"""Shared subprocess helpers."""

import shutil
import subprocess
from typing import Sequence

from .errors import DependencyMissing


def require_tool(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise DependencyMissing(tool, f"{tool} not found in PATH")
    return path


def run(
    cmd: Sequence[str],
    *,
    timeout: float = 30.0,
    require: str | None = None,
) -> dict:
    if require is not None:
        require_tool(require)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DependencyMissing(cmd[0], str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
            "exit_code": -1,
            "timed_out": True,
        }
    return {
        "command": " ".join(cmd),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "timed_out": False,
    }
