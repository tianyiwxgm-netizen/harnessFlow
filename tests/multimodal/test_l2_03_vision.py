"""WP-η-04 L2-03 vision tests · 6 modules."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.multimodal.common.errors import L108Error
from app.multimodal.vision.batch import batch_analyze
from app.multimodal.vision.cache import VisionCache, hash_image
from app.multimodal.vision.ocr_fallback import extract_text
from app.multimodal.vision.orchestrator import ImageOrchestrator
from app.multimodal.vision.schemas import BatchResult, VisionRequest, VisionResult, VisionTask
from app.multimodal.vision.vlm_invoker import VLMInvoker

# --- fixture · minimal PNG file ---

@pytest.fixture
def tmp_image(tmp_path: Path) -> Path:
    p = tmp_path / "pic.png"
    # Smallest valid 1x1 PNG
    p.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452"
        "00000001000000010806000000"
        "1f15c4890000000d49444154789c626000"
        "0000000002000100"
        "cffca9020000000049454e44ae426082"
    ))
    return p


# --- schemas ---

def test_vision_request_defaults() -> None:
    r = VisionRequest(image_path="a.png", project_id="p-001", task="describe")
    assert r.timeout_s == 15.0
    assert r.task == VisionTask.describe


def test_vision_task_enum_values() -> None:
    assert {t.value for t in VisionTask} == {"describe", "extract_text", "structured_extract"}


def test_vision_result_shape() -> None:
    r = VisionResult(success=True, task=VisionTask.describe, fallback_tier=1, structured_output={"x": 1})
    assert r.fallback_tier == 1


def test_batch_result_shape() -> None:
    b = BatchResult(total=2, succeeded=1, failed=1, results=[])
    assert b.total == 2


# --- cache ---

def test_cache_basic(tmp_image: Path) -> None:
    c = VisionCache(max_size=4)
    h = hash_image(tmp_image)
    c.put("p-001", h, "describe", "RESULT")
    assert c.get("p-001", h, "describe") == "RESULT"


def test_cache_pid_isolation(tmp_image: Path) -> None:
    c = VisionCache(max_size=4)
    h = hash_image(tmp_image)
    c.put("p-001", h, "describe", "A")
    c.put("p-002", h, "describe", "B")
    assert c.get("p-001", h, "describe") == "A"
    assert c.get("p-002", h, "describe") == "B"


def test_cache_task_isolation(tmp_image: Path) -> None:
    c = VisionCache(max_size=4)
    h = hash_image(tmp_image)
    c.put("p-001", h, "describe", "X")
    c.put("p-001", h, "extract_text", "Y")
    assert c.get("p-001", h, "describe") != c.get("p-001", h, "extract_text")


def test_cache_lru_eviction() -> None:
    c = VisionCache(max_size=2)
    c.put("p", "h1", "describe", 1)
    c.put("p", "h2", "describe", 2)
    c.put("p", "h3", "describe", 3)
    assert c.get("p", "h1", "describe") is None


def test_cache_rejects_zero_size() -> None:
    with pytest.raises(ValueError):
        VisionCache(max_size=0)


def test_hash_image_stable(tmp_image: Path) -> None:
    h1 = hash_image(tmp_image)
    h2 = hash_image(tmp_image)
    assert h1 == h2
    assert len(h1) == 64


# --- VLM invoker (mock client) ---

class _MockClient:
    def __init__(self, *, response: dict[str, Any] | None = None, should_fail: bool = False,
                 should_timeout: bool = False, delay: float = 0.0) -> None:
        self.response = response or {"description": "A cat"}
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.delay = delay
        self.call_count = 0

    async def call(self, image_bytes: bytes, task: VisionTask, *, timeout_s: float) -> dict[str, Any]:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("boom")
        if self.should_timeout:
            await asyncio.sleep(timeout_s + 1)
        if self.delay:
            await asyncio.sleep(self.delay)
        return dict(self.response)


async def test_vlm_invoker_describe(tmp_image: Path) -> None:
    inv = VLMInvoker(client=_MockClient(response={"description": "cat"}))
    out = await inv.invoke(tmp_image, VisionTask.describe)
    assert out["description"] == "cat"


async def test_vlm_invoker_extract_text(tmp_image: Path) -> None:
    inv = VLMInvoker(client=_MockClient(response={"text": "HELLO"}))
    out = await inv.invoke(tmp_image, VisionTask.extract_text)
    assert out["text"] == "HELLO"


async def test_vlm_invoker_structured_extract(tmp_image: Path) -> None:
    inv = VLMInvoker(client=_MockClient(response={"fields": {"a": 1}}))
    out = await inv.invoke(tmp_image, VisionTask.structured_extract)
    assert out["fields"]["a"] == 1


async def test_vlm_invoker_timeout_raises(tmp_image: Path) -> None:
    inv = VLMInvoker(client=_MockClient(should_timeout=True), default_timeout_s=0.05)
    with pytest.raises(L108Error) as ei:
        await inv.invoke(tmp_image, VisionTask.describe)
    assert ei.value.code == "E_PC_VISION_API_FAIL"


async def test_vlm_invoker_runtime_error_maps_to_vision_api_fail(tmp_image: Path) -> None:
    inv = VLMInvoker(client=_MockClient(should_fail=True))
    with pytest.raises(L108Error) as ei:
        await inv.invoke(tmp_image, VisionTask.describe)
    assert ei.value.code == "E_PC_VISION_API_FAIL"


async def test_vlm_invoker_missing_file_raises(tmp_path: Path) -> None:
    inv = VLMInvoker(client=_MockClient())
    with pytest.raises(L108Error) as ei:
        await inv.invoke(tmp_path / "nope.png", VisionTask.describe)
    assert ei.value.code == "not_found"


# --- OCR fallback ---

def test_ocr_fallback_returns_str_on_missing_binary(tmp_image: Path) -> None:
    """Whether tesseract is installed or not, extract_text should return a str (possibly empty)."""
    out = extract_text(tmp_image)
    assert isinstance(out, str)


# --- Orchestrator · 4-tier chain ---

async def test_orchestrator_tier1_primary_succeeds(tmp_image: Path) -> None:
    primary = VLMInvoker(client=_MockClient(response={"description": "cat"}))
    orch = ImageOrchestrator(primary=primary)
    r = await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    assert r.success is True
    assert r.fallback_tier == 1
    assert r.structured_output == {"description": "cat"}


async def test_orchestrator_tier2_lite_when_primary_fails(tmp_image: Path) -> None:
    primary = VLMInvoker(client=_MockClient(should_fail=True))
    lite = VLMInvoker(client=_MockClient(response={"description": "small"}))
    orch = ImageOrchestrator(primary=primary, lite=lite)
    r = await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    assert r.success is True
    assert r.fallback_tier == 2


async def test_orchestrator_tier3_ocr_for_extract_text(tmp_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When both VLMs fail for extract_text, OCR tier3 kicks in."""
    primary = VLMInvoker(client=_MockClient(should_fail=True))
    lite = VLMInvoker(client=_MockClient(should_fail=True))
    orch = ImageOrchestrator(primary=primary, lite=lite)
    # Patch OCR extractor to return predictable text
    import app.multimodal.vision.orchestrator as orch_mod
    monkeypatch.setattr(orch_mod, "extract_text", lambda _p: "OCR OUTPUT")
    r = await orch.analyze(tmp_image, VisionTask.extract_text, project_id="p-001")
    assert r.success is True
    assert r.fallback_tier == 3
    assert r.structured_output == {"text": "OCR OUTPUT"}


async def test_orchestrator_tier4_pure_rule_when_all_fail(tmp_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """For `describe` task with no OCR path, all tiers exhaust -> tier4 stub result."""
    primary = VLMInvoker(client=_MockClient(should_fail=True))
    lite = VLMInvoker(client=_MockClient(should_fail=True))
    orch = ImageOrchestrator(primary=primary, lite=lite)
    r = await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    assert r.success is False
    assert r.fallback_tier == 4
    assert r.structured_output == {"description": "[无可用分析]"}


async def test_orchestrator_cache_hit_skips_tiers(tmp_image: Path) -> None:
    primary = VLMInvoker(client=_MockClient(response={"description": "cat"}))
    orch = ImageOrchestrator(primary=primary)
    r1 = await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    r2 = await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    assert r1.fallback_tier == 1
    assert r2.cache_hit is True
    # primary client should have been called exactly once
    assert primary.client.call_count == 1


async def test_orchestrator_cache_pid_isolation(tmp_image: Path) -> None:
    client = _MockClient(response={"description": "cat"})
    primary = VLMInvoker(client=client)
    orch = ImageOrchestrator(primary=primary)
    await orch.analyze(tmp_image, VisionTask.describe, project_id="p-001")
    await orch.analyze(tmp_image, VisionTask.describe, project_id="p-002")
    assert client.call_count == 2   # different pid -> separate cache -> separate call


async def test_orchestrator_missing_image_raises(tmp_path: Path) -> None:
    primary = VLMInvoker(client=_MockClient())
    orch = ImageOrchestrator(primary=primary)
    with pytest.raises(L108Error) as ei:
        await orch.analyze(tmp_path / "nope.png", VisionTask.describe, project_id="p-001")
    assert ei.value.code == "not_found"


# --- Batch ---

async def test_batch_semaphore_concurrency(tmp_image: Path) -> None:
    """Assert that no more than `concurrency` tasks run in parallel."""
    active = 0
    peak = 0

    async def fake_analyze(image_path: str, task: str) -> VisionResult:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return VisionResult(success=True, task=task, fallback_tier=1, structured_output={})

    requests = [(str(tmp_image), "describe")] * 10
    result = await batch_analyze(requests, fake_analyze, concurrency=3)
    assert result.total == 10
    assert result.succeeded == 10
    assert peak <= 3


async def test_batch_one_failure_doesnt_fail_others(tmp_image: Path) -> None:
    async def fake_analyze(image_path: str, task: str) -> VisionResult:
        if task == "fail":
            raise RuntimeError("boom")
        return VisionResult(success=True, task="describe", fallback_tier=1, structured_output={})

    requests = [("a.png", "describe"), ("b.png", "fail"), ("c.png", "describe")]
    result = await batch_analyze(requests, fake_analyze, concurrency=2)
    assert result.total == 3
    assert result.succeeded == 2
    assert result.failed == 1


async def test_batch_empty_requests() -> None:
    async def _never(path: str, task: str) -> VisionResult:
        raise AssertionError("should not be called")

    result = await batch_analyze([], _never)
    assert result.total == 0
    assert result.succeeded == 0
