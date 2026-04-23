"""WP-η-05 e2e · 4 主路径（md / code small / code large DELEGATE / image）."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.multimodal.code_structure.ast_parser import ASTParser
from app.multimodal.common.event_bus_stub import EventBusStub
from app.multimodal.doc_io.md_reader import MDReader
from app.multimodal.path_safety.schemas import ProcessContentCommand
from app.multimodal.path_safety.whitelist import PathWhitelistValidator
from app.multimodal.process_content import ProcessContentDeps, process_content
from app.multimodal.router import MultimodalDeps
from app.multimodal.vision.orchestrator import ImageOrchestrator
from app.multimodal.vision.schemas import VisionTask
from app.multimodal.vision.vlm_invoker import VLMInvoker


class _VLMStub:
    async def call(self, image_bytes: bytes, task: VisionTask, *, timeout_s: float) -> dict[str, Any]:
        return {"description": "stub"}


class _MockL1_05:
    async def dispatch_codebase_onboarding(self, cmd: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.001)
        return {"dispatched": True, "subagent_session_id": "sub-e2e"}


def _build_deps(tmp_project_root: Path, *, with_l1_05: bool = False) -> ProcessContentDeps:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    validator = PathWhitelistValidator(tmp_project_root, "p-001", ["docs/"])
    mm = MultimodalDeps(
        md_reader=MDReader(validator),
        ast_parser=ASTParser(),
        image_orchestrator=ImageOrchestrator(primary=VLMInvoker(client=_VLMStub())),
    )
    return ProcessContentDeps(
        facade_project_root=tmp_project_root,
        facade_project_id="p-001",
        facade_allowlist=["docs/"],
        multimodal_deps=mm,
        bus=EventBusStub(),
        l1_05_client=_MockL1_05() if with_l1_05 else None,
    )


def test_e2e_md_happy(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "intro.md").write_text(
        "---\ndoc_id: a\ndoc_type: plan\n---\n# Hello\nline two\n"
    )
    deps = _build_deps(tmp_project_root)
    cmd = ProcessContentCommand(
        command_id="pc-01E2E1", project_id="p-001",
        content_type="md", target_path="docs/intro.md",
        task="summarize", caller_l1="L1-01", ts="2026-04-23T00:00:00Z",
    )
    r = process_content(cmd, deps)
    assert r.success is True
    assert r.structured_output["total_lines"] >= 2


def test_e2e_code_small_direct(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "mod.py").write_text("def add(a, b):\n    return a + b\n")
    deps = _build_deps(tmp_project_root)
    cmd = ProcessContentCommand(
        command_id="pc-01E2E2", project_id="p-001",
        content_type="code", target_path="docs/mod.py",
        task="code_understand", caller_l1="L1-01", ts="2026-04-23T00:00:00Z",
    )
    r = process_content(cmd, deps)
    assert r.success is True
    assert r.structured_output["lang"] == "python"
    assert r.structured_output["route"] == "DIRECT"


def test_e2e_code_large_delegate_to_ic_12(tmp_project_root: Path) -> None:
    """File with >100k lines triggers DELEGATE → IC-12 → async_task_id."""
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    big_file = tmp_project_root / "docs" / "huge.py"
    big_file.write_text("\n".join(f"x_{i} = {i}" for i in range(100_001)) + "\n")
    deps = _build_deps(tmp_project_root, with_l1_05=True)
    cmd = ProcessContentCommand(
        command_id="pc-01E2E3", project_id="p-001",
        content_type="code", target_path="docs/huge.py",
        task="code_understand", caller_l1="L1-01", ts="2026-04-23T00:00:00Z",
    )
    r = process_content(cmd, deps)
    assert r.success is True
    assert r.async_task_id is not None
    assert r.async_task_id.startswith("async-")
    assert r.structured_output["dispatched"] is True


def test_e2e_image_happy(tmp_project_root: Path) -> None:
    from PIL import Image

    (tmp_project_root / "docs").mkdir(exist_ok=True)
    img_path = tmp_project_root / "docs" / "pic.png"
    Image.new("RGB", (1, 1)).save(img_path)
    deps = _build_deps(tmp_project_root)
    cmd = ProcessContentCommand(
        command_id="pc-01E2E4", project_id="p-001",
        content_type="image", target_path="docs/pic.png",
        task="vision_describe", caller_l1="L1-01", ts="2026-04-23T00:00:00Z",
    )
    r = process_content(cmd, deps)
    assert r.success is True
    assert r.structured_output["content_type"] == "image"
