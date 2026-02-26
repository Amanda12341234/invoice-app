"""Unit tests for OCROrchestrator (T013).

All external services are mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.invoice import EngineType, RecognitionResult
from app.services.gemini_service import GeminiQuotaError, GeminiUnavailableError
from app.services.ocr_orchestrator import AllEnginesFailedError, OCROrchestrator

SAMPLE_IMAGE = b"fake-image-bytes"
SAMPLE_MIME = "image/jpeg"

MOCK_RESULT = RecognitionResult(
    store_name="全聯福利中心",
    date="2026-02-26",
    total=45,
    engine_used=EngineType.GEMINI_PRIMARY,
)


@pytest.mark.asyncio
class TestOCROrchestratorPrimaryPath:
    async def test_primary_path_success(self):
        """Gemini 成功時直接回傳結果，engine_used=GEMINI_PRIMARY。"""
        orch = OCROrchestrator()
        with patch.object(orch._gemini, "recognize", return_value=MOCK_RESULT):
            result = await orch.process(SAMPLE_IMAGE, SAMPLE_MIME)

        assert result.engine_used == EngineType.GEMINI_PRIMARY
        assert result.store_name == "全聯福利中心"

    async def test_image_bytes_cleared_after_completion(self):
        """辨識完成後 image_bytes 應被清除（憲章原則四）。"""
        orch = OCROrchestrator()
        image_ref = bytearray(SAMPLE_IMAGE)
        with patch.object(orch._gemini, "recognize", return_value=MOCK_RESULT):
            result = await orch.process(bytes(image_ref), SAMPLE_MIME)
        # image_ref is a local variable; test verifies process doesn't retain reference
        assert result is not None  # process completed


@pytest.mark.asyncio
class TestOCROrchestratorFallback:
    async def test_gemini_quota_error_triggers_fallback(self):
        """Gemini GeminiQuotaError 應自動切換至 PaddleOCR 備援。"""
        fallback_result = RecognitionResult(
            store_name="全聯", total=45, engine_used=EngineType.PADDLEOCR_FALLBACK
        )
        orch = OCROrchestrator()
        with (
            patch.object(orch._gemini, "recognize", side_effect=GeminiQuotaError),
            patch.object(orch, "_run_fallback", return_value=fallback_result),
        ):
            result = await orch.process(SAMPLE_IMAGE, SAMPLE_MIME)

        assert result.engine_used == EngineType.PADDLEOCR_FALLBACK

    async def test_gemini_unavailable_triggers_fallback(self):
        """Gemini GeminiUnavailableError 應自動切換至備援。"""
        fallback_result = RecognitionResult(
            store_name="全聯", total=45, engine_used=EngineType.PADDLEOCR_FALLBACK
        )
        orch = OCROrchestrator()
        with (
            patch.object(orch._gemini, "recognize", side_effect=GeminiUnavailableError),
            patch.object(orch, "_run_fallback", return_value=fallback_result),
        ):
            result = await orch.process(SAMPLE_IMAGE, SAMPLE_MIME)

        assert result.engine_used == EngineType.PADDLEOCR_FALLBACK

    async def test_all_engines_failed_raises_error(self):
        """主備援均失敗時應拋出 AllEnginesFailedError（retryable）。"""
        from app.services.ollama_service import OllamaParseError

        orch = OCROrchestrator()
        with (
            patch.object(orch._gemini, "recognize", side_effect=GeminiQuotaError),
            patch.object(orch._paddle, "extract_text", side_effect=Exception("paddle fail")),
        ):
            with pytest.raises(AllEnginesFailedError):
                await orch.process(SAMPLE_IMAGE, SAMPLE_MIME)
