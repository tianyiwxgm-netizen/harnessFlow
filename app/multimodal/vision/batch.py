"""L2-03 batch · concurrent analyze with asyncio.Semaphore(3)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.multimodal.vision.schemas import BatchResult, VisionResult, VisionTask


async def batch_analyze(
    requests: list[tuple[str, str]],              # [(image_path, task), ...]
    analyze_fn: Callable[[str, str], Awaitable[VisionResult]],
    *,
    concurrency: int = 3,
) -> BatchResult:
    """Run analyze_fn over each request · <= concurrency in flight."""
    sem = asyncio.Semaphore(concurrency)

    async def _one(image_path: str, task: str) -> VisionResult:
        async with sem:
            try:
                return await analyze_fn(image_path, task)
            except Exception as e:
                # Use a safe task value — the raw task string may be invalid for the enum
                try:
                    safe_task = VisionTask(task)
                except ValueError:
                    safe_task = VisionTask.describe
                return VisionResult(success=False, task=safe_task, fallback_tier=4, error_message=str(e))

    results = await asyncio.gather(*(_one(p, t) for p, t in requests))
    ok = sum(1 for r in results if r.success)
    return BatchResult(
        total=len(requests),
        succeeded=ok,
        failed=len(requests) - ok,
        results=results,
    )
