"""L1-08 L2-04 Path Safety · Symlink cycle and depth detector · Task 01.4."""

from __future__ import annotations

import os
from pathlib import Path

from app.multimodal.common.errors import L108Error


class SymlinkCycleDetector:
    """Detects symlink cycles and excessive depth."""

    MAX_DEPTH: int = 8

    def check(self, start_path: Path) -> None:
        """Check for symlink cycles and depth limits.

        Walks symlinks manually using os.readlink and path.is_symlink().
        Tracks visited symlinks (not final targets) to detect cycles.
        Enforces MAX_DEPTH limit.

        Args:
            start_path: Path to start checking from

        Raises:
            L108Error: If cycle detected (code="path_escape", detail="symlink_loop: ...")
            L108Error: If depth exceeded (code="path_escape", detail="symlink_depth_exceeded: ...")
        """
        current = Path(start_path)
        visited: set[str] = set()
        steps = 0

        while steps <= self.MAX_DEPTH:
            # If current is not a symlink, we're done
            if not current.is_symlink():
                return

            # Get the symlink target path (not resolved)
            current_str = str(current)
            if current_str in visited:
                raise L108Error(
                    "path_escape",
                    f"symlink_loop: {current_str}",
                )
            visited.add(current_str)

            # Follow the symlink
            try:
                link_target = os.readlink(current_str)
            except (OSError, ValueError):
                # Can't read symlink, stop here
                return

            # Resolve link_target relative to current's directory
            if os.path.isabs(link_target):
                current = Path(link_target)
            else:
                current = current.parent / link_target

            steps += 1

        # Exceeded MAX_DEPTH
        raise L108Error(
            "path_escape",
            f"symlink_depth_exceeded: {current}",
        )
