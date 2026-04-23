"""WP-η-05 IC-11 contract tests · 6 errors + type×task matrix subset."""

from __future__ import annotations

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


def _make_deps(tmp_project_root: Path) -> ProcessContentDeps:
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
    )


def _cmd(**overrides: Any) -> ProcessContentCommand:
    base = dict(
        command_id="pc-01HYA1ABC",
        project_id="p-001",
        content_type="md",
        target_path="docs/a.md",
        task="summarize",
        caller_l1="L1-01",
        ts="2026-04-23T10:00:00Z",
    )
    base.update(overrides)
    return ProcessContentCommand(**base)  # type: ignore[arg-type]


# ── Error code tests ──────────────────────────────────────────────────────────


def test_ic11_error_no_project_id(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "a.md").write_text("---\ndoc_id: x\ndoc_type: p\n---\nhi\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(project_id="p-wrong"), deps)
    assert r.success is False
    assert r.error.code == "E_PC_NO_PROJECT_ID"


def test_ic11_error_path_out_of_project(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "a.md").write_text("hi\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="../../etc/passwd"), deps)
    assert r.success is False
    assert r.error.code == "E_PC_PATH_OUT_OF_PROJECT"


def test_ic11_error_path_not_found(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/missing.md"), deps)
    assert r.success is False
    assert r.error.code == "E_PC_PATH_NOT_FOUND"


def test_ic11_error_type_task_mismatch(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "a.md").write_text("hi\n")
    deps = _make_deps(tmp_project_root)
    # md + vision_describe is invalid per matrix
    r = process_content(_cmd(task="vision_describe"), deps)
    assert r.success is False
    assert r.error.code == "E_PC_TYPE_TASK_MISMATCH"


def test_ic11_error_type_task_mismatch_code_vision(tmp_project_root: Path) -> None:
    """code + vision_describe is also illegal."""
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "a.py").write_text("x = 1\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/a.py", content_type="code", task="vision_describe"), deps)
    assert r.success is False
    assert r.error.code == "E_PC_TYPE_TASK_MISMATCH"


# ── Happy path matrix subset ──────────────────────────────────────────────────


def test_ic11_happy_md_summarize(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "a.md").write_text("---\ndoc_id: x\ndoc_type: p\n---\n# hi\nl2\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(), deps)
    assert r.success is True
    assert r.structured_output["content_type"] == "md"


def test_ic11_happy_md_structure_extract(tmp_project_root: Path) -> None:
    """md + structure_extract is a legal combo."""
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    (tmp_project_root / "docs" / "b.md").write_text("---\ndoc_id: y\ndoc_type: plan\n---\n# Hello\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/b.md", task="structure_extract"), deps)
    assert r.success is True
    assert r.structured_output["content_type"] == "md"


def test_ic11_happy_code_small(tmp_project_root: Path) -> None:
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    code = tmp_project_root / "docs" / "a.py"
    code.write_text("def foo(): return 1\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/a.py", content_type="code", task="code_understand"), deps)
    assert r.success is True
    assert r.structured_output["lang"] == "python"


def test_ic11_happy_code_summarize(tmp_project_root: Path) -> None:
    """code + summarize is a legal combo."""
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    code = tmp_project_root / "docs" / "b.py"
    code.write_text("def bar(): return 2\n")
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/b.py", content_type="code", task="summarize"), deps)
    assert r.success is True
    assert r.structured_output["lang"] == "python"


def test_ic11_happy_image_describe(tmp_project_root: Path) -> None:
    from PIL import Image

    img_path = tmp_project_root / "docs" / "p.png"
    (tmp_project_root / "docs").mkdir(exist_ok=True)
    Image.new("RGB", (1, 1)).save(img_path)
    deps = _make_deps(tmp_project_root)
    r = process_content(_cmd(target_path="docs/p.png", content_type="image", task="vision_describe"), deps)
    assert r.success is True
    assert r.structured_output["content_type"] == "image"
