"""L1-08 L2 content router · sync · content_type → sub-orchestrator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.multimodal.code_structure.ast_parser import ASTParser
from app.multimodal.common.errors import L108Error
from app.multimodal.doc_io.md_reader import MDReader
from app.multimodal.path_safety.schemas import (
    ProcessContentCommand,
    RouteDecision,
    ValidationResult,
)
from app.multimodal.vision.orchestrator import ImageOrchestrator
from app.multimodal.vision.schemas import VisionTask


@dataclass
class MultimodalDeps:
    md_reader: MDReader
    ast_parser: ASTParser
    image_orchestrator: ImageOrchestrator


# task ↔ content_type validity matrix (IC-11 contract §3.11.4 E_PC_TYPE_TASK_MISMATCH)
_VALID_COMBOS: dict[str, set[str]] = {
    "md":              {"summarize", "structure_extract"},
    "code":            {"code_understand", "structure_extract", "summarize"},
    "image":           {"vision_describe", "structure_extract"},
    "pdf":             {"summarize"},
    "markdown_batch":  {"summarize", "diff_analyze"},
}


def check_type_task_compatibility(content_type: str, task: str) -> None:
    """Raise type_mismatch if task is not valid for the given content_type."""
    allowed = _VALID_COMBOS.get(content_type, set())
    if task not in allowed:
        raise L108Error(
            "type_mismatch",
            f"task '{task}' not valid for content_type '{content_type}'; allowed: {sorted(allowed)}",
        )


class ContentRouter:
    """Sync router · returns structured_output dict when route=DIRECT/PAGED · DELEGATE sentinel for IC-12."""

    def __init__(self, deps: MultimodalDeps) -> None:
        self.deps = deps

    def route(
        self,
        cmd: ProcessContentCommand,
        validation: ValidationResult,
        route: RouteDecision,
    ) -> dict[str, Any]:
        check_type_task_compatibility(cmd.content_type.value, cmd.task.value)

        if route == RouteDecision.DELEGATE:
            # DELEGATE signals large-code · caller (process_content.py) handles IC-12 dispatch.
            return {"route": "DELEGATE"}

        ctype = cmd.content_type.value
        if ctype == "md":
            assert validation.realpath is not None
            content = self.deps.md_reader.read(cmd.target_path)
            return {
                "content_type": "md",
                "route": route.value,
                "total_lines": content.total_lines,
                "paged": content.is_paged,
                "frontmatter_keys": sorted(content.frontmatter.keys()),
            }
        if ctype == "code":
            assert validation.realpath is not None
            real = Path(validation.realpath)
            if real.is_file():
                tree = self.deps.ast_parser.parse(real, "python", pid=cmd.project_id)
                return {
                    "content_type": "code",
                    "route": route.value,
                    "lang": tree.lang,
                    "root_type": tree.root_type,
                    "loc": tree.loc,
                }
            # directory · simple summary
            return {"content_type": "code", "route": route.value, "repo_dir": str(real)}
        if ctype == "image":
            assert validation.realpath is not None
            real = Path(validation.realpath)
            vtask = (
                VisionTask(cmd.task.value)
                if cmd.task.value in [t.value for t in VisionTask]
                else VisionTask.describe
            )
            result = asyncio.run(
                self.deps.image_orchestrator.analyze(real, vtask, project_id=cmd.project_id)
            )
            return {
                "content_type": "image",
                "route": route.value,
                "fallback_tier": result.fallback_tier,
                "output": result.structured_output or {},
            }
        # pdf / markdown_batch · stub pass-through for now
        return {"content_type": ctype, "route": route.value, "stub": True}
