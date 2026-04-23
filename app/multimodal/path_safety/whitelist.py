"""L1-08 L2-04 Path Safety · Whitelist validator · Task 01.3."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.multimodal.common.errors import L108Error
from app.multimodal.path_safety.schemas import ValidationResult


class PathWhitelistValidator:
    """Validates file paths against a project whitelist."""

    def __init__(self, project_root: Path, project_id: str, allowlist: list[str]) -> None:
        """Initialize validator.

        Args:
            project_root: Root directory of the project (e.g., /projects/p-001)
            project_id: Project identifier (e.g., "p-001")
            allowlist: List of allowed directory prefixes (e.g., ["docs/", "tests/"])
        """
        self.project_root = Path(project_root)
        self.project_id = project_id
        self.allowlist = allowlist

    def validate(self, path: Optional[str], action: str) -> ValidationResult:
        """Validate a path against whitelist.

        Algorithm (in order):
        1. path is None/empty/has control char → raise invalid_path
        2. Resolve candidate to realpath
        3. Try to get relative_to project_root
           - If ValueError: check if cross_project or path_escape
        4. If rel.parts empty or first part not in allowlist → raise path_forbidden
        5. Return ValidationResult(ok=True, realpath=str(real), allowlist_match=rel.parts[0] + "/")

        Args:
            path: File path to validate (relative to project_root)
            action: Action type (e.g., "read")

        Returns:
            ValidationResult with ok=True and resolved paths

        Raises:
            L108Error: If path violates whitelist or security constraints
        """
        # Step 1: Check for invalid paths
        if path is None or path == "" or "\x00" in path:
            raise L108Error("invalid_path", f"invalid path: {path!r}")

        # Step 2: Resolve to realpath
        candidate = self.project_root / path
        real = Path(os.path.realpath(str(candidate)))

        # Step 3: Try to make relative to project_root
        try:
            rel = real.relative_to(self.project_root)
        except ValueError:
            # Not under project_root; check if cross_project or path_escape
            if self._is_cross_project(real):
                raise L108Error("cross_project", str(real))
            else:
                raise L108Error("path_escape", str(real))

        # Step 4: Check if path is allowed
        if not rel.parts or (rel.parts[0] + "/") not in self.allowlist:
            raise L108Error("path_forbidden", f"path {rel} not in allowlist")

        # Step 5: Return success
        return ValidationResult(
            ok=True,
            realpath=str(real),
            allowlist_match=rel.parts[0] + "/",
        )

    def _is_cross_project(self, realpath: Path) -> bool:
        """Check if realpath escapes to a sibling project.

        Returns True if realpath is under <project_root>.parent (the projects/ dir)
        with a different p-* project name.
        """
        projects_dir = self.project_root.parent
        try:
            rel_to_projects = realpath.relative_to(projects_dir)
        except ValueError:
            # Not even under projects dir
            return False

        # Check if first component is a different p-* project
        if rel_to_projects.parts:
            first_part = rel_to_projects.parts[0]
            return first_part != self.project_root.name and first_part.startswith("p-")

        return False
