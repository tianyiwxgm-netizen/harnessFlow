"""WP-η-01 L2-04 DegradationRouter · four-tier routing with three thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.multimodal.common.errors import L108Error
from app.multimodal.path_safety.schemas import RouteDecision


@dataclass(frozen=True)
class RouteInput:
    """Pre-validated path + type + file-level stats."""
    realpath: Path
    line_count: int | None = None     # for md / code
    size_bytes: int | None = None     # for image
    ext: str | None = None            # for image (lower-case, no dot)


class DegradationRouter:
    MD_PAGES_THRESHOLD: int = 2000
    CODE_LOC_THRESHOLD: int = 100_000
    IMAGE_SIZE_THRESHOLD_MB: int = 5
    IMAGE_ALLOWED_EXTS: frozenset[str] = frozenset({"png", "jpg", "jpeg", "webp", "gif"})

    def route_md(self, inp: RouteInput) -> RouteDecision:
        """md content routing → DIRECT (≤ threshold) | PAGED (> threshold)."""
        if inp.line_count is None:
            raise L108Error("invalid_path", "md route requires line_count")
        return RouteDecision.PAGED if inp.line_count > self.MD_PAGES_THRESHOLD else RouteDecision.DIRECT

    def route_code(self, inp: RouteInput) -> RouteDecision:
        """code content routing → DIRECT (≤ threshold) | DELEGATE (> threshold → IC-12)."""
        if inp.line_count is None:
            raise L108Error("invalid_path", "code route requires line_count")
        return RouteDecision.DELEGATE if inp.line_count > self.CODE_LOC_THRESHOLD else RouteDecision.DIRECT

    def route_image(self, inp: RouteInput) -> RouteDecision:
        """image content routing → DIRECT | REJECT (raises size_exceeded / format_unsupported)."""
        if inp.ext is None or inp.size_bytes is None:
            raise L108Error("invalid_path", "image route requires ext + size_bytes")
        ext = inp.ext.lower().lstrip(".")
        if ext not in self.IMAGE_ALLOWED_EXTS:
            raise L108Error("format_unsupported", f"image ext '{ext}' not allowed")
        max_bytes = self.IMAGE_SIZE_THRESHOLD_MB * 1024 * 1024
        if inp.size_bytes > max_bytes:
            raise L108Error("size_exceeded", f"image size {inp.size_bytes} > {max_bytes}")
        return RouteDecision.DIRECT
