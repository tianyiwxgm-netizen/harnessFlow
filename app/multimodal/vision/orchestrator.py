"""L2-03 ImageOrchestrator · 4-tier fallback chain (VLM -> VLM lite -> OCR -> rule)."""

from __future__ import annotations

from pathlib import Path

from app.multimodal.common.errors import L108Error
from app.multimodal.vision.cache import VisionCache, hash_image
from app.multimodal.vision.ocr_fallback import extract_text
from app.multimodal.vision.schemas import VisionResult, VisionTask
from app.multimodal.vision.vlm_invoker import VLMInvoker


class ImageOrchestrator:
    """Orchestrates VLM + OCR tiers · returns best-available VisionResult."""

    def __init__(
        self,
        primary: VLMInvoker,
        lite: VLMInvoker | None = None,
        *,
        cache: VisionCache | None = None,
    ) -> None:
        self.primary = primary
        self.lite = lite
        self.cache = cache or VisionCache()

    async def analyze(
        self,
        image_path: Path,
        task: VisionTask,
        *,
        project_id: str = "default",
    ) -> VisionResult:
        if not image_path.exists():
            raise L108Error("not_found", str(image_path))

        img_hash = hash_image(image_path)
        cached: VisionResult | None = self.cache.get(project_id, img_hash, task.value)
        if cached is not None:
            return cached.model_copy(update={"cache_hit": True})

        # Tier 1 · primary VLM
        try:
            out = await self.primary.invoke(image_path, task)
            result = VisionResult(success=True, task=task, structured_output=out, fallback_tier=1)
            self.cache.put(project_id, img_hash, task.value, result)
            return result
        except L108Error:
            pass

        # Tier 2 · lite VLM
        if self.lite is not None:
            try:
                out = await self.lite.invoke(image_path, task)
                result = VisionResult(success=True, task=task, structured_output=out, fallback_tier=2)
                self.cache.put(project_id, img_hash, task.value, result)
                return result
            except L108Error:
                pass

        # Tier 3 · OCR (only useful for extract_text)
        if task == VisionTask.extract_text:
            text = extract_text(image_path)
            if text:
                result = VisionResult(
                    success=True, task=task,
                    structured_output={"text": text}, fallback_tier=3,
                )
                self.cache.put(project_id, img_hash, task.value, result)
                return result

        # Tier 4 · pure-rule fallback
        result = VisionResult(
            success=False, task=task,
            structured_output={"description": "[无可用分析]"}, fallback_tier=4,
            error_message="all VLM tiers and OCR exhausted",
        )
        return result
