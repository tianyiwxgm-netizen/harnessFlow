"""Git-based primitives: diff_lines_net / no_public_api_breaking_change."""

from pathlib import Path

from ._shell import run


def diff_lines_net(base: str = "main") -> tuple[int, dict]:
    result = run(["git", "diff", "--shortstat", base], require="git", timeout=30.0)
    line = result["stdout"].strip()
    # e.g. "5 files changed, 123 insertions(+), 45 deletions(-)"
    ins = 0
    dels = 0
    for part in line.split(","):
        part = part.strip()
        if "insertion" in part:
            try:
                ins = int(part.split(" ", 1)[0])
            except ValueError:
                pass
        elif "deletion" in part:
            try:
                dels = int(part.split(" ", 1)[0])
            except ValueError:
                pass
    net = ins - dels
    return net, {"base": base, "git_shortstat": line, "insertions": ins, "deletions": dels, "net": net}


def no_public_api_breaking_change(
    spec_path: str = "openapi.yaml", base: str = "main"
) -> tuple[bool, dict]:
    if not Path(spec_path).exists():
        return True, {"spec_path": spec_path, "note": "spec not present; skipped"}
    result = run(["git", "diff", base, "--", spec_path], require="git", timeout=30.0)
    removed_lines = [
        ln for ln in result["stdout"].splitlines() if ln.startswith("-") and not ln.startswith("---")
    ]
    ok = len(removed_lines) == 0
    return ok, {
        "spec_path": spec_path,
        "base": base,
        "removed_line_count": len(removed_lines),
        "sample": removed_lines[:5],
    }
