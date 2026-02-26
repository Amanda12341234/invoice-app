from __future__ import annotations

import logging

from app.core import queue_manager
from app.models.invoice import EngineType, RecognitionResult
from app.services.gemini_service import (
    GeminiQuotaError,
    GeminiService,
    GeminiUnavailableError,
)
from app.services.ollama_service import OllamaParseError, OllamaService
from app.services.paddleocr_service import PaddleOCRService

logger = logging.getLogger(__name__)


class AllEnginesFailedError(Exception):
    """Raised when both Gemini and PaddleOCR+Ollama fail."""
    retryable: bool = True


class OCROrchestrator:
    def __init__(self):
        self._gemini = GeminiService()
        self._paddle = PaddleOCRService()
        self._ollama = OllamaService()

    async def process(self, image_bytes: bytes, mime_type: str) -> RecognitionResult:
        """
        Main OCR processing pipeline with automatic fallback.

        1. Try Gemini (primary)
        2. On quota/unavailable → fallback to PaddleOCR + Ollama
        3. Both fail → raise AllEnginesFailedError (retryable)

        Image bytes are set to None after processing (憲章原則四).
        """
        active_engine = await queue_manager.get_active_engine()

        # Skip Gemini if quota already exhausted (US3 node)
        if active_engine == EngineType.GEMINI_PRIMARY:
            try:
                result = self._gemini.recognize(image_bytes, mime_type)
                await queue_manager.record_gemini_call()
                image_bytes = None  # 清除圖片參考 (憲章原則四)
                return result
            except (GeminiQuotaError, GeminiUnavailableError) as exc:
                logger.warning("Gemini failed (%s), switching to fallback.", type(exc).__name__)
                queue_manager.force_fallback_engine()

        # Fallback: PaddleOCR + Ollama
        try:
            result = await self._run_fallback(image_bytes, mime_type)
            image_bytes = None
            return result
        except Exception as exc:
            image_bytes = None
            logger.error("All OCR engines failed: %s", exc)
            raise AllEnginesFailedError("Both Gemini and PaddleOCR+Ollama failed") from exc

    async def _run_fallback(self, image_bytes: bytes, mime_type: str) -> RecognitionResult:
        """Run PaddleOCR text extraction then Ollama JSON parsing."""
        import asyncio

        raw_text = await asyncio.get_event_loop().run_in_executor(
            None, self._paddle.extract_text, image_bytes
        )
        if not raw_text.strip():
            from app.models.invoice import ConfidenceLevel
            return RecognitionResult(
                partial_failure_fields=["store_name", "date", "items", "total"],
                confidence=ConfidenceLevel.LOW,
                engine_used=EngineType.PADDLEOCR_FALLBACK,
            )

        result = await asyncio.get_event_loop().run_in_executor(
            None, self._ollama.parse_to_invoice, raw_text
        )
        return result
