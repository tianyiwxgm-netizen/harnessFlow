"""L2-03 VLMInvoker · abstract VLM client + primary/lite tiers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol

from app.multimodal.common.errors import L108Error
from app.multimodal.vision.schemas import VisionTask


class VLMClient(Protocol):
    """Protocol any VLM backend (real 豆包, mocks, etc.) must implement."""
    async def call(self, image_bytes: bytes, task: VisionTask, *, timeout_s: float) -> dict[str, Any]: ...


class VLMInvoker:
    """Wraps a VLMClient · applies asyncio timeout · raises E_PC_VISION_API_FAIL on timeout/failure."""

    def __init__(self, client: VLMClient, *, default_timeout_s: float = 15.0) -> None:
        self.client = client
        self.default_timeout_s = default_timeout_s

    async def invoke(self, image_path: Path, task: VisionTask, *, timeout_s: float | None = None) -> dict[str, Any]:
        t_s = timeout_s if timeout_s is not None else self.default_timeout_s
        try:
            data = image_path.read_bytes()
        except FileNotFoundError:
            raise L108Error("not_found", str(image_path))
        try:
            result = await asyncio.wait_for(self.client.call(data, task, timeout_s=t_s), timeout=t_s)
        except TimeoutError as e:
            raise L108Error("E_PC_VISION_API_FAIL", f"VLM timeout > {t_s}s") from e
        except Exception as e:
            raise L108Error("E_PC_VISION_API_FAIL", f"VLM call failed: {e}") from e
        return result
